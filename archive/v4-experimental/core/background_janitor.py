"""
core/background_janitor.py — SDD-SURVIVAL-06 / SDD-SURVIVAL-12 / SDD-SURVIVAL-14

Background Community Summarizer (SLM Offloading),
Smart Checkpoint Pruning (Smart LRU per Session), and
Thermal & IOPS Throttler (Hardware-Aware RateGovernor).

Responsibilities:
  1. Offloads DIRTY community summary generation to free local models
     (SLM via Ollama) during idle periods, protecting the user from cloud
     token costs. (SDD-06)
  2. Cleans up obsolete intermediate agent session checkpoints while
     preserving the immutable point-zero ("init") and the N most recent snapshots,
     preventing unbounded growth in state.db. (SDD-12)
  3. Monitors host thermal integrity via psutil before invoking local SLMs
     (Ollama), guaranteeing that background summarization never degrades
     developer experience (DX). (SDD-14)

Summarization Flow (SDD-06):
  1. Identifies communities where is_dirty = 1
  2. For each: aggregates associated file contents
  3. Dispatches local free SLM callback
  4. Persists summary, resets dirty flags, returns audit log

Pruning Flow (SDD-12):
  1. Identifies all checkpoints for a session ordered chronologically
  2. Protects the initial checkpoint (immutable point-zero)
  3. Retains the latest N checkpoints (keep_limit)
  4. Deletes intermediate obsolete checkpoints via SerializedWriteQueue

Thermal Throttler Flow (SDD-14):
  1. Checks overall host CPU usage (< 40%)
  2. Verifies developer idle period (quiet period)
  3. Lowers Python process scheduling priority to background
"""

import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class BackgroundJanitor:
    """
    Idle-time janitor that summarizes dirty communities utilizing exclusively
    free local models (SLM), guaranteeing zero cloud API bills. Also performs
    smart checkpoint auto-pruning to prevent database bloat. (SDD-06 / SDD-12 / SDD-14)
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager
        self.is_running = False

    # ── Community Summarization (SDD-06) ───────────────────────────

    def run_idle_summarization(
        self, local_slm_callback: Callable[[str], str]
    ) -> Dict[str, str]:
        """
        Processes all DIRTY communities in the background.

        For each dirty community:
          - Aggregates content of associated files
          - Dispatches free local SLM callback
          - Persists new summary into database
          - Resets is_dirty flags to 0

        Returns audit log: {community_id: generated_summary}
        """
        audit_log: Dict[str, str] = {}

        # Locate all dirty communities
        dirty_communities = self.db_manager.read_query(
            "SELECT id FROM communities WHERE is_dirty = 1;"
        )

        for (community_id,) in dirty_communities:
            summary = self._summarize_community(community_id, local_slm_callback)
            audit_log[community_id] = summary

        return audit_log

    def _summarize_community(
        self, community_id: str, local_slm_callback: Callable[[str], str]
    ) -> str:
        """
        Aggregates community file contents, generates summary via local SLM,
        and persists result while resetting dirty flags.
        """
        # Aggregate content of all files in the community
        files = self.db_manager.read_query(
            "SELECT content FROM files WHERE community_id = ?;",
            (community_id,),
        )
        payload = "\n".join(row[0] for row in files)

        # Dispatch free local SLM
        new_summary = local_slm_callback(payload)

        # Persist summary and reconcile flags
        self.db_manager.write_query(
            "UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;",
            (new_summary, community_id),
        )
        self.db_manager.write_query(
            "UPDATE files SET is_dirty = 0 WHERE community_id = ?;",
            (community_id,),
        )

        return new_summary

    # ── Checkpoint Auto-Pruning (SDD-12) ───────────────────────────

    def prune_session_checkpoints(
        self,
        session_id: Optional[str] = None,
        keep_limit: int = 10,
    ) -> int:
        """
        Executes smart checkpoint pruning per session.

        Smart LRU per Session Algorithm:
          1. Identifies all session checkpoints ordered by created_at
          2. Protects the first checkpoint (point zero / "init") — immutable
          3. From remaining, retains the latest `keep_limit` snapshots
          4. Physically deletes intermediate obsolete checkpoints

        If session_id is None, processes all existing sessions.

        Returns total number of deleted checkpoints.
        """
        total_pruned = 0

        if session_id is not None:
            sessions = [(session_id,)]
        else:
            sessions = self.db_manager.read_query(
                "SELECT DISTINCT session_id FROM agent_checkpoints;"
            )

        for (sid,) in sessions:
            pruned = self._prune_single_session(sid, keep_limit)
            total_pruned += pruned

        return total_pruned

    def _prune_single_session(self, session_id: str, keep_limit: int) -> int:
        """
        Executes pruning for an individual session.

        Identifies checkpoint_ids that must be preserved (point zero +
        the N most recent) and deletes all other intermediate records.
        """
        # Select all session checkpoints in chronological order
        all_checkpoints = self.db_manager.read_query(
            "SELECT checkpoint_id FROM agent_checkpoints "
            "WHERE session_id = ? "
            "ORDER BY created_at ASC;",
            (session_id,),
        )

        if not all_checkpoints:
            return 0

        all_ids = [row[0] for row in all_checkpoints]

        # Protect initial checkpoint (immutable point zero)
        init_checkpoint = all_ids[0]
        remaining = all_ids[1:]

        # From remaining, preserve latest keep_limit
        if len(remaining) <= keep_limit:
            # Nothing to prune — all fit within limit
            return 0

        # IDs to preserve: init + latest keep_limit
        recent_ids = remaining[-keep_limit:]
        preserve_set = {init_checkpoint} | set(recent_ids)

        # IDs to delete: all that are not in preserve set
        ids_to_delete = [cid for cid in all_ids if cid not in preserve_set]

        if not ids_to_delete:
            return 0

        # Batch delete via SerializedWriteQueue
        placeholders = ", ".join("?" for _ in ids_to_delete)
        self.db_manager.write_query(
            f"DELETE FROM agent_checkpoints "
            f"WHERE session_id = ? AND checkpoint_id IN ({placeholders});",
            (session_id, *ids_to_delete),
        )

        logger.info(
            "SDD-12: Session '%s' pruning complete — %d checkpoints deleted, "
            "%d preserved (1 init + %d recent).",
            session_id,
            len(ids_to_delete),
            len(preserve_set),
            len(recent_ids),
        )

        return len(ids_to_delete)

    # ── Thermal Throttler & Hardware-Aware Governor (SDD-14) ────────

    def check_hardware_clearance(
        self,
        max_cpu_percent: float = 40.0,
        quiet_period_seconds: float = 180.0,
    ) -> bool:
        """
        Verifies whether local host has thermal and compute headroom
        for safe local SLM execution (Ollama).

        Clearance conditions (all must be True):
          1. Host overall CPU usage below max_cpu_percent (0.5s sample average)
          2. No file modified within the last quiet_period_seconds
             (developer idle period)

        Returns True if hardware clearance is granted, False otherwise.
        """
        # 1. Check overall host CPU usage
        current_cpu = psutil.cpu_percent(interval=0.5)
        if current_cpu > max_cpu_percent:
            logger.debug(
                "SDD-14: Hardware clearance denied — CPU at %.1f%% (threshold: %.1f%%)",
                current_cpu,
                max_cpu_percent,
            )
            return False

        # 2. Check idle period (Quiet Period)
        result = self.db_manager.read_query(
            "SELECT MAX(last_modified) FROM files;"
        )
        latest_change = result[0][0] if result and result[0][0] is not None else 0

        if (time.time() - latest_change) < quiet_period_seconds:
            logger.debug(
                "SDD-14: Hardware clearance denied — file modified %.1fs ago "
                "(quiet period: %.1fs)",
                time.time() - latest_change,
                quiet_period_seconds,
            )
            return False

        return True

    def process_community_summaries_frugal(self) -> str:
        """
        Executes summary generation for detected communities applying process
        priority demotion and thermal throttling.

        Flow:
          1. Lowers current Python process priority to background
             (IDLE_PRIORITY_CLASS on Windows, nice(15) on Unix)
          2. Verifies hardware clearance barrier (CPU + quiet period)
          3. If cleared, processes summaries via local SLM

        Returns:
          - "skipped_due_to_hardware_constraints" if blocked by barrier
          - "success" if processed successfully
        """
        # Demote current process priority to background
        try:
            p = psutil.Process(os.getpid())
            if sys.platform == "win32":
                p.nice(psutil.IDLE_PRIORITY_CLASS)
            else:
                p.nice(15)
        except Exception:
            pass  # Ignore if OS lacks permission

        # Execute hardware barrier
        if not self.check_hardware_clearance():
            return "skipped_due_to_hardware_constraints"

        self.is_running = True

        # Process local summaries via Ollama...
        # (Ollama client implementation to be integrated in future SDD)

        self.is_running = False
        return "success"
