"""
core/checkpointer.py — SDD-SURVIVAL-07

Checkpoint Persistence for Agnostic Agent State Dictionaries.

Generic cartridge persisting state dictionaries of any AI agent
as stringified JSON in SQLite WAL, isolated by composite primary key:
(agent_id, session_id, checkpoint_id) in agent_checkpoints.

Design Invariants:
  - Zero coupling: agnostic of specific agent variables
  - Hermetic isolation: composite key ensures total isolation between
    concurrent agents, sessions, and checkpoints
  - JSON resilience: sanitizes complex non-serializable objects (locks, sockets)
  - Note: legacy SDD-20 / fsm_checkpoints time-travel signatures were archived
    in V4 (D0) and fail explicitly without writing to SQLite.
"""

import json
from typing import Any, Dict, List, Optional, Tuple


class AgnosticCheckpointer:
    """
    Agnostic state manager that persists and retrieves AI variable dictionaries
    as JSON blobs in SQLite WAL, powering Time-Travel Debugging and multi-agent isolation.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager
        self.db = db_manager
        self.last_error: Optional[str] = None

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

    def save_checkpoint_detailed(
        self,
        *args,
        **kwargs,
    ) -> Tuple[bool, Optional[str]]:
        """
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL, returning (success, error_message) per call to eliminate
        shared state concurrency race conditions.
        """
        is_sdd20 = (
            "state_name" in kwargs
            or "shared_state" in kwargs
            or len(args) >= 5
            or (len(args) == 4 and isinstance(args[3], str))
        )

        if is_sdd20:
            return (
                False,
                "SDD-20 / fsm_checkpoints signature is archived in V4 (D0); "
                "use legacy agent_checkpoints (agent_id, session_id, checkpoint_id, state_dict).",
            )
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
            success, res = write_fn(
                "INSERT OR REPLACE INTO agent_checkpoints "
                "(agent_id, session_id, checkpoint_id, state_blob) "
                "VALUES (?, ?, ?, ?);",
                (agent_id, session_id, checkpoint_id, state_blob),
            )
            err = None if success else (str(res) if res is not None else "Unknown write error")
            return bool(success), err

    def save_checkpoint(
        self,
        *args,
        **kwargs,
    ) -> bool:
        """
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL.

        Legacy wrapper returning bool, updating self.last_error for backward compatibility.
        """
        success, err = self.save_checkpoint_detailed(*args, **kwargs)
        self.last_error = err
        return success

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
            "ORDER BY created_at ASC, rowid ASC;",
            (agent_id, session_id),
        )
        return [
            {"checkpoint_id": row[0], "created_at": row[1]}
            for row in rows
        ]
