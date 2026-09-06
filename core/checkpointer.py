"""
core/checkpointer.py — SDD-SURVIVAL-07 / SDD-SURVIVAL-20

Checkpoint Persistence and Agent State/Session Time-Travel.

Generic cartridge persisting state dictionaries and FSM snapshots of any AI agent
as stringified JSON in SQLite WAL, isolated by composite primary key:
(session_id, checkpoint_id) in fsm_checkpoints, and
(agent_id, session_id, checkpoint_id) in agent_checkpoints.

Design Invariants:
  - Zero coupling: agnostic of specific agent variables or FSM structures
  - Hermetic isolation: composite key ensures total isolation between
    concurrent agents, sessions, and branching timelines
  - JSON resilience: sanitizes complex non-serializable objects (locks, sockets)
  - Deterministic Time-Travel: chronological ordering enables cognitive rollback
    and marks associated task files as dirty for edge re-synchronization
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgnosticCheckpointer:
    """
    Agnostic state manager that persists and retrieves AI variable dictionaries
    as JSON blobs in SQLite WAL, powering Time-Travel Debugging and multi-agent isolation.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager
        self.db = db_manager

    # ── Non-Serializable Object Sanitization ───────────────────────

    @staticmethod
    def _sanitize_for_json(obj: Any) -> Any:
        """
        Recursively converts non-serializable objects into representative strings,
        guaranteeing resilient persistence without runtime exceptions.
        """
        if isinstance(obj, dict):
            return {str(k): AgnosticCheckpointer._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AgnosticCheckpointer._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, set):
            return [AgnosticCheckpointer._sanitize_for_json(item) for item in sorted(list(obj), key=str)]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)

    # ── State Recording (SDD-20 & SDD-07 Hybrid) ───────────────────

    def save_checkpoint(
        self,
        *args,
        **kwargs,
    ) -> bool:
        """
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL.

        Supports both extended FSM signature (SDD-20):
            save_checkpoint(session_id, checkpoint_id, agent_id, state_name, shared_state, task_id=None)
        and legacy agnostic signature (SDD-07):
            save_checkpoint(agent_id, session_id, checkpoint_id, state_dict)
        """
        is_sdd20 = (
            "state_name" in kwargs
            or "shared_state" in kwargs
            or len(args) >= 5
            or (len(args) == 4 and isinstance(args[3], str))
        )

        if is_sdd20:
            # SDD-20 Signature
            if len(args) >= 5:
                session_id = args[0]
                checkpoint_id = args[1]
                agent_id = args[2]
                state_name = args[3]
                shared_state = args[4]
                task_id = args[5] if len(args) > 5 else kwargs.get("task_id")
            else:
                session_id = kwargs.get("session_id", args[0] if len(args) > 0 else "")
                checkpoint_id = kwargs.get("checkpoint_id", args[1] if len(args) > 1 else "")
                agent_id = kwargs.get("agent_id", args[2] if len(args) > 2 else "")
                state_name = kwargs.get("state_name", args[3] if len(args) > 3 else "")
                shared_state = kwargs.get("shared_state", args[4] if len(args) > 4 else {})
                task_id = kwargs.get("task_id")

            # Resilient sanitization of complex objects (e.g. locks, sockets)
            try:
                shared_state_json = json.dumps(shared_state, ensure_ascii=False)
            except (TypeError, ValueError):
                cleaned_state = self._sanitize_for_json(shared_state)
                shared_state_json = json.dumps(cleaned_state, ensure_ascii=False)

            query = """
                INSERT INTO fsm_checkpoints (checkpoint_id, session_id, agent_id, state_name, shared_state_blob, task_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, checkpoint_id) DO UPDATE SET
                    state_name = excluded.state_name,
                    shared_state_blob = excluded.shared_state_blob,
                    task_id = excluded.task_id;
            """
            write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))
            success, _ = write_fn(
                query,
                (checkpoint_id, session_id, agent_id, state_name, shared_state_json, task_id),
            )
            return bool(success)
        else:
            # Legacy SDD-07 Signature
            if len(args) >= 4:
                agent_id = args[0]
                session_id = args[1]
                checkpoint_id = args[2]
                state_dict = args[3]
            else:
                agent_id = kwargs.get("agent_id", "")
                session_id = kwargs.get("session_id", "")
                checkpoint_id = kwargs.get("checkpoint_id", "")
                state_dict = kwargs.get("state_dict", {})

            try:
                state_blob = json.dumps(state_dict, ensure_ascii=False)
            except (TypeError, ValueError):
                cleaned = self._sanitize_for_json(state_dict)
                state_blob = json.dumps(cleaned, ensure_ascii=False)

            write_fn = getattr(self.db, "write_query", getattr(self.db, "execute_write", None))
            success, _ = write_fn(
                "INSERT OR REPLACE INTO agent_checkpoints "
                "(agent_id, session_id, checkpoint_id, state_blob) "
                "VALUES (?, ?, ?, ?);",
                (agent_id, session_id, checkpoint_id, state_blob),
            )
            return bool(success)

    # ── State Retrieval (SDD-20) ───────────────────────────────────

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves and deserializes variable snapshot for a specific FSM checkpoint.
        """
        query = "SELECT state_name, shared_state_blob, agent_id, task_id FROM fsm_checkpoints WHERE session_id = ? AND checkpoint_id = ?;"
        read_fn = getattr(self.db, "read_query")
        rows = read_fn(query, (session_id, checkpoint_id))
        if not rows:
            return None

        state_name, blob, agent_id, task_id = rows[0]
        try:
            shared_state = json.loads(blob)
        except Exception:
            shared_state = {}

        return {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "state_name": state_name,
            "task_id": task_id,
            "shared_state": shared_state,
        }

    # ── Operational Time-Travel (SDD-20) ───────────────────────────

    def execute_time_travel(self, session_id: str, target_checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Executes physical and cognitive rollback (Time-Travel) to an earlier checkpoint.
        Deletes future checkpoints created after the target to maintain linear determinism.
        Marks task file (task_id) as dirty (is_dirty = 1) in relational store for re-indexing.
        """
        # 1. Retrieve target checkpoint data
        target_data = self.load_checkpoint(session_id, target_checkpoint_id)
        if not target_data:
            return None

        # 2. Retrieve creation timestamp of destination checkpoint
        time_query = "SELECT created_at, task_id FROM fsm_checkpoints WHERE session_id = ? AND checkpoint_id = ?;"
        read_fn = getattr(self.db, "read_query")
        time_rows = read_fn(time_query, (session_id, target_checkpoint_id))
        if not time_rows:
            return None
        created_at, task_id = time_rows[0]

        # 3. Atomic Transaction: Delete "future" checkpoints and mark associated file as dirty
        queries = [
            ("DELETE FROM fsm_checkpoints WHERE session_id = ? AND created_at > ?;", (session_id, created_at)),
        ]

        if task_id:
            # Force edge re-indexing for associated file (Watcher/DeltaManager)
            queries.append(("UPDATE files SET is_dirty = 1, last_modified = ? WHERE path = ?;", (time.time(), task_id)))

        write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))
        try:
            for q, params in queries:
                write_fn(q, params)
            return target_data
        except Exception as e:
            logger.error("[TIME-TRAVEL] Rollback failure in SQLite WAL: %s", str(e))
            return None

    # ── Legacy SDD-07 Methods ──────────────────────────────────────

    def get_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieves saved state under composite key (agent_id, session_id, checkpoint_id)
        and decodes JSON back to Python dict.

        Returns {} if checkpoint does not exist (agnostic fail-safe).
        """
        rows = self.db_manager.read_query(
            "SELECT state_blob FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ?;",
            (agent_id, session_id, checkpoint_id),
        )
        if not rows:
            return {}
        return json.loads(rows[0][0])

    def list_checkpoints(
        self,
        agent_id: str,
        session_id: str,
    ) -> List[Dict[str, str]]:
        """
        Lists all checkpoints for an agent/session ordered chronologically
        (created_at ASC), enabling Time-Travel navigation.

        Returns list of dicts with checkpoint_id and created_at.
        """
        rows = self.db_manager.read_query(
            "SELECT checkpoint_id, created_at FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ? "
            "ORDER BY created_at ASC;",
            (agent_id, session_id),
        )
        return [
            {"checkpoint_id": row[0], "created_at": row[1]}
            for row in rows
        ]
