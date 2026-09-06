"""
core/alias_tracker.py — SDD-SURVIVAL-18 (Hardened & Resilient)

Structural Signature Hash (SSH) Alias Tracking for Historical Trajectory Preservation.

Intercepts physical file renames and moves across the workspace, associating deletions
and creations that share the exact same Structural Signature Hash (SSH) within a temporal
reconciliation buffer, atomically migrating database paths without losing historical context,
topological graph edges, or agent checkpoints.

Shielding Guarantees:
  - Strict rejection of empty or boilerplate payloads ("e3b0c4...", "", "deleted_hash").
  - Asynchronous timeout with automatic purge: if no matching creation occurs within the window,
    invokes on_purge_callback to avoid orphan zombie records in SQLite.
  - Thread-safe synchronization via threading.Lock and active timer cancellation.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EMPTY_SSH_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
INVALID_HASHES = {EMPTY_SSH_HASH, "deleted_hash", "", None}


class AliasTracker:
    """
    Temporal structural alias tracker preserving historical trajectories
    and topology during file rename and move operations.
    """

    def __init__(
        self,
        db_manager: Any,
        hash_generator_callback: Any,
        buffer_window_seconds: float = 1.0,
        on_purge_callback: Optional[Callable[[str], None]] = None,
    ):
        self.db = db_manager
        self.hash_gen = hash_generator_callback
        self.buffer_window = buffer_window_seconds
        self.on_purge_callback = on_purge_callback

        # Pending deletions buffer: {old_path: (structural_hash, timestamp_of_deletion)}
        self.pending_deletions: Dict[str, Tuple[str, float]] = {}
        # Pending timers for post-timeout auto-purge: {old_path: threading.Timer}
        self.pending_timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    @staticmethod
    def is_valid_hash(structural_hash: Optional[str]) -> bool:
        """Validates whether hash represents a non-trivial syntactic structure."""
        if not structural_hash:
            return False
        if len(structural_hash) < 5:
            return False
        if structural_hash in INVALID_HASHES:
            return False
        return True

    def register_deletion(self, path: str, structural_hash: str) -> None:
        """
        Registers a pending deletion in temporal alias buffer.
        If hash is invalid/empty, immediately purges node via callback.
        Otherwise stores deletion and arms async timer for purge upon timeout.
        """
        if not self.is_valid_hash(structural_hash):
            logger.debug("[ALIAS-TRACKER] Invalid or empty hash for %s. Purging immediately.", path)
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Error in immediate purge of invalid hash for %s: %s", path, e)
            return

        with self._lock:
            # Cancel previous timer if already registered for this path
            old_timer = self.pending_timers.pop(path, None)
            if old_timer:
                old_timer.cancel()

            self.pending_deletions[path] = (structural_hash, time.time())

            # Schedule asynchronous purge if no creation occurs within window
            timer = threading.Timer(self.buffer_window, self._on_timeout_expire, args=[path])
            timer.daemon = True
            timer.start()
            self.pending_timers[path] = timer

    def _on_timeout_expire(self, path: str) -> None:
        """Invoked by timer when buffer window expires without creation resolution."""
        with self._lock:
            self.pending_timers.pop(path, None)
            entry = self.pending_deletions.pop(path, None)

        if entry is not None and self.on_purge_callback:
            logger.info("[ALIAS-TRACKER] Alias timeout expired for '%s'. Purging node from database.", path)
            try:
                self.on_purge_callback(path)
            except Exception as e:
                logger.error("[ALIAS-TRACKER] Error invoking on_purge_callback on timeout for %s: %s", path, e)

    def check_and_resolve_creation(
        self, new_path: str, new_structural_hash: str
    ) -> Optional[str]:
        """
        Checks whether creation of a new file matches a recently deleted file
        sharing identical Structural Signature Hash (SSH). Returns old path if resolved as alias.
        """
        if not self.is_valid_hash(new_structural_hash):
            return None

        current_time = time.time()
        matched_old_path: Optional[str] = None
        candidates = []
        expired_paths: List[str] = []

        with self._lock:
            for old_path, (old_hash, deleted_at) in list(self.pending_deletions.items()):
                if current_time - deleted_at > self.buffer_window:
                    expired_paths.append(old_path)
                elif old_hash == new_structural_hash:
                    candidates.append(old_path)

            # Evict expired items from buffer
            for path in expired_paths:
                timer = self.pending_timers.pop(path, None)
                if timer:
                    timer.cancel()
                self.pending_deletions.pop(path, None)

            # If exactly one exclusive candidate matches, resolve the alias!
            if len(candidates) == 1:
                matched_old_path = candidates[0]
                timer = self.pending_timers.pop(matched_old_path, None)
                if timer:
                    timer.cancel()
                self.pending_deletions.pop(matched_old_path, None)

        # Trigger purge for unmatched expired paths
        for path in expired_paths:
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Error in purge of expired path %s: %s", path, e)

        return matched_old_path

    def purge_expired(self, current_time: Optional[float] = None) -> List[str]:
        """Manually purges all items whose timeout has expired."""
        if current_time is None:
            current_time = time.time()
        expired: List[str] = []
        with self._lock:
            for old_path, (_, deleted_at) in list(self.pending_deletions.items()):
                if current_time - deleted_at > self.buffer_window:
                    timer = self.pending_timers.pop(old_path, None)
                    if timer:
                        timer.cancel()
                    self.pending_deletions.pop(old_path, None)
                    expired.append(old_path)

        for path in expired:
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Error purging expired path %s: %s", path, e)
        return expired

    def cancel_all_timers(self) -> None:
        """Cancels all pending timers (for teardown and shutdown)."""
        with self._lock:
            for timer in self.pending_timers.values():
                try:
                    timer.cancel()
                except Exception:
                    pass
            self.pending_timers.clear()

    def apply_alias_migration(self, old_path: str, new_path: str) -> bool:
        """Executes atomic mutation of physical file path while preserving historical relations."""
        timestamp = time.time()

        # Discover ast_edges column names (parent_node_id vs parent_node)
        parent_col = "parent_node_id"
        child_col = "child_node_id"
        try:
            cols = [
                r[1]
                for r in self.db.read_query("PRAGMA table_info(ast_edges);")
            ]
            if "parent_node" in cols and "parent_node_id" not in cols:
                parent_col = "parent_node"
                child_col = "child_node"
        except Exception:
            pass

        # Discover existing database tables
        existing_tables = set()
        try:
            t_rows = self.db.read_query(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            existing_tables = {r[0] for r in t_rows}
        except Exception:
            pass

        queries = []
        if "files" in existing_tables:
            queries.append((
                "UPDATE files SET path = ?, last_modified = ?, is_dirty = 1 WHERE path = ?;",
                (new_path, timestamp, old_path),
            ))
        if "nodes" in existing_tables:
            queries.append((
                "UPDATE nodes SET label = ? WHERE label = ?;",
                (new_path, old_path),
            ))

        if "ast_edges" in existing_tables:
            queries.extend([
                (
                    f"UPDATE ast_edges SET {parent_col} = ? WHERE {parent_col} = ?;",
                    (new_path, old_path),
                ),
                (
                    f"UPDATE ast_edges SET {child_col} = ? WHERE {child_col} = ?;",
                    (new_path, old_path),
                ),
            ])

        if "fsm_checkpoints" in existing_tables:
            queries.append((
                "UPDATE fsm_checkpoints SET task_id = ? WHERE task_id = ?;",
                (new_path, old_path),
            ))

        try:
            for query, params in queries:
                if hasattr(self.db, "execute_write"):
                    success, res = self.db.execute_write(query, params)
                    if not success:
                        raise Exception(f"Transaction failed: {res}")
                else:
                    self.db.write_query(query, params)
            return True
        except Exception as e:
            logger.error(
                "[ALIAS-TRACKER] Critical failure migrating alias %s -> %s: %s",
                old_path,
                new_path,
                e,
            )
            return False
