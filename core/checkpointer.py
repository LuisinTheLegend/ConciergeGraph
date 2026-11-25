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

import hashlib
import hmac
import json
import sqlite3
import threading
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
        self._write_lock = threading.Lock()

    @staticmethod
    def _hash_owner_token(owner_token: Optional[str]) -> str:
        """Returns SHA-256 hex digest of owner_token, or empty string when absent."""
        if not owner_token:
            return ""
        return hashlib.sha256(owner_token.encode("utf-8")).hexdigest()

    def _read_namespace_hashes(self, agent_id: str, session_id: str) -> List[str]:
        """Reads distinct owner_hash values for (agent_id, session_id), migrating 5-column tables if needed."""
        query = (
            "SELECT DISTINCT owner_hash FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ?;"
        )
        try:
            rows = self.db_manager.read_query(query, (agent_id, session_id))
        except sqlite3.OperationalError as exc:
            err_lower = str(exc).lower()
            if "no such column" in err_lower and "owner_hash" in err_lower:
                write_fn = getattr(self.db, "write_query", getattr(self.db, "execute_write", None))
                if callable(write_fn):
                    write_fn(
                        "ALTER TABLE agent_checkpoints ADD COLUMN owner_hash TEXT NOT NULL DEFAULT '';",
                        (),
                    )
                rows = self.db_manager.read_query(query, (agent_id, session_id))
            else:
                raise
        if not rows or not isinstance(rows, (list, tuple)):
            return []
        hashes: List[str] = []
        for row in rows:
            val = row[0] if isinstance(row, (list, tuple)) and row else ""
            hashes.append("" if val is None else str(val))
        return hashes

    def _verify_namespace_ownership(
        self,
        agent_id: str,
        session_id: str,
        owner_token: Optional[str],
    ) -> None:
        """Verifies caller ownership for an existing (agent_id, session_id) namespace."""
        existing_hashes = self._read_namespace_hashes(agent_id, session_id)
        if not existing_hashes:
            return
        if len(existing_hashes) > 1:
            raise PermissionError(
                "Access denied: inconsistent checkpoint ownership metadata for this agent/session namespace."
            )
        caller_hash = self._hash_owner_token(owner_token)
        stored_hash = existing_hashes[0]
        if not hmac.compare_digest(stored_hash, caller_hash):
            raise PermissionError(
                "Access denied: checkpoint ownership verification failed for this agent/session namespace."
            )

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
        owner_token: Optional[str] = None,
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
            legacy_fields = (
                ("agent_id", ""),
                ("session_id", ""),
                ("checkpoint_id", ""),
                ("state_dict", {}),
            )
            resolved: Dict[str, Any] = {}
            for idx, (field_name, default_val) in enumerate(legacy_fields):
                has_pos = idx < len(args)
                has_kw = field_name in kwargs
                if has_pos and has_kw:
                    return (
                        False,
                        f"Duplicate argument for '{field_name}': "
                        "provided both positionally and as keyword argument.",
                    )
                if has_pos:
                    resolved[field_name] = args[idx]
                elif has_kw:
                    resolved[field_name] = kwargs[field_name]
                else:
                    resolved[field_name] = default_val

            agent_id = resolved["agent_id"]
            session_id = resolved["session_id"]
            checkpoint_id = resolved["checkpoint_id"]
            state_dict = resolved["state_dict"]

            try:
                state_blob = json.dumps(state_dict, ensure_ascii=False)
            except (TypeError, ValueError):
                cleaned = self._sanitize_for_json(state_dict)
                state_blob = json.dumps(cleaned, ensure_ascii=False)

            write_fn = getattr(self.db, "write_query", getattr(self.db, "execute_write", None))
            owner_hash = self._hash_owner_token(owner_token)
            with self._write_lock:
                try:
                    self._verify_namespace_ownership(agent_id, session_id, owner_token)
                except sqlite3.OperationalError as exc:
                    if "no such table" in str(exc).lower():
                        return (False, str(exc))
                    raise
                success, res = write_fn(
                    "INSERT OR REPLACE INTO agent_checkpoints "
                    "(agent_id, session_id, checkpoint_id, state_blob, owner_hash) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (agent_id, session_id, checkpoint_id, state_blob, owner_hash),
                )
            err = None if success else (str(res) if res is not None else "Unknown write error")
            return bool(success), err

    def save_checkpoint(
        self,
        *args,
        owner_token: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL.

        Legacy wrapper returning bool, updating self.last_error for backward compatibility.
        """
        success, err = self.save_checkpoint_detailed(*args, owner_token=owner_token, **kwargs)
        self.last_error = err
        return success

    # ── Legacy SDD-07 Methods ──────────────────────────────────────

    def get_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: str,
        *,
        owner_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves saved state under composite key (agent_id, session_id, checkpoint_id)
        and decodes JSON back to Python dict.

        Returns {} if checkpoint does not exist (agnostic fail-safe).
        """
        self._verify_namespace_ownership(agent_id, session_id, owner_token)
        caller_hash = self._hash_owner_token(owner_token)
        rows = self.db_manager.read_query(
            "SELECT state_blob FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ? AND owner_hash = ?;",
            (agent_id, session_id, checkpoint_id, caller_hash),
        )
        if not rows:
            return {}
        try:
            return json.loads(rows[0][0])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Corrupted checkpoint state_blob for agent_id='{agent_id}', "
                f"session_id='{session_id}', checkpoint_id='{checkpoint_id}'"
            ) from exc

    def list_checkpoints(
        self,
        agent_id: str,
        session_id: str,
        *,
        owner_token: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Lists all checkpoints for an agent/session ordered chronologically
        (created_at ASC), enabling Time-Travel navigation.

        Returns list of dicts with checkpoint_id and created_at.
        """
        self._verify_namespace_ownership(agent_id, session_id, owner_token)
        caller_hash = self._hash_owner_token(owner_token)
        rows = self.db_manager.read_query(
            "SELECT checkpoint_id, created_at FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ? AND owner_hash = ? "
            "ORDER BY created_at ASC, rowid ASC;",
            (agent_id, session_id, caller_hash),
        )
        return [
            {"checkpoint_id": row[0], "created_at": row[1]}
            for row in rows
        ]
