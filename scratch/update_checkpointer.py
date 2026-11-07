import os

file_path = r"core\checkpointer.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_block = """    def save_checkpoint(
        self,
        *args,
        **kwargs,
    ) -> bool:
        \"\"\"
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL.

        Supports both extended FSM signature (SDD-20):
            save_checkpoint(session_id, checkpoint_id, agent_id, state_name, shared_state, task_id=None)
        and legacy agnostic signature (SDD-07):
            save_checkpoint(agent_id, session_id, checkpoint_id, state_dict)
        \"\"\"
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

            query = \"\"\"
                INSERT INTO fsm_checkpoints (checkpoint_id, session_id, agent_id, state_name, shared_state_blob, task_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, checkpoint_id) DO UPDATE SET
                    state_name = excluded.state_name,
                    shared_state_blob = excluded.shared_state_blob,
                    task_id = excluded.task_id;
            \"\"\"
            write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))
            success, res = write_fn(
                query,
                (checkpoint_id, session_id, agent_id, state_name, shared_state_json, task_id),
            )
            self.last_error = None if success else (str(res) if res is not None else "Unknown write error")
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
            success, res = write_fn(
                "INSERT OR REPLACE INTO agent_checkpoints "
                "(agent_id, session_id, checkpoint_id, state_blob) "
                "VALUES (?, ?, ?, ?);",
                (agent_id, session_id, checkpoint_id, state_blob),
            )
            self.last_error = None if success else (str(res) if res is not None else "Unknown write error")
            return bool(success)"""

new_block = """    def save_checkpoint_detailed(
        self,
        *args,
        **kwargs,
    ) -> Tuple[bool, Optional[str]]:
        \"\"\"
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL, returning (success, error_message) per call to eliminate
        shared state concurrency race conditions.
        \"\"\"
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

            query = \"\"\"
                INSERT INTO fsm_checkpoints (checkpoint_id, session_id, agent_id, state_name, shared_state_blob, task_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, checkpoint_id) DO UPDATE SET
                    state_name = excluded.state_name,
                    shared_state_blob = excluded.shared_state_blob,
                    task_id = excluded.task_id;
            \"\"\"
            write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))
            success, res = write_fn(
                query,
                (checkpoint_id, session_id, agent_id, state_name, shared_state_json, task_id),
            )
            err = None if success else (str(res) if res is not None else "Unknown write error")
            return bool(success), err
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
        \"\"\"
        Atomically saves complete snapshot of agent variables and FSM mental state
        into SQLite WAL.

        Legacy wrapper returning bool, updating self.last_error for backward compatibility.
        \"\"\"
        success, err = self.save_checkpoint_detailed(*args, **kwargs)
        self.last_error = err
        return success"""

assert target_block in content, "target_block not found in core/checkpointer.py"
content = content.replace(target_block, new_block)

# Ensure Tuple is imported from typing
if "Tuple" not in content[:500]:
    content = content.replace("from typing import Dict, Any, List, Optional, Union", "from typing import Dict, Any, List, Optional, Union, Tuple")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated core/checkpointer.py with save_checkpoint_detailed successfully.")

