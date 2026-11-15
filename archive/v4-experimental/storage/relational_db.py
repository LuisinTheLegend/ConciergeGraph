"""
storage/relational_db.py — SDD-SURVIVAL-20

Relational schema and persistence operations for Durable Checkpointing & Time-Travel.

Defines the `fsm_checkpoints` table with composite primary key (session_id, checkpoint_id)
for strict concurrent session isolation and agent FSM snapshot retention.
"""

from typing import Any

# SQL DDL for durable FSM checkpoints table
FSM_CHECKPOINTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fsm_checkpoints (
    checkpoint_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,
    state_name TEXT NOT NULL,
    shared_state_blob TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, checkpoint_id)
);
"""


def init_fsm_checkpoints_schema(db_manager: Any) -> bool:
    """
    Initializes the fsm_checkpoints table in the SQLite WAL database.
    """
    write_fn = getattr(db_manager, "execute_write", getattr(db_manager, "write_query", None))
    if write_fn:
        success, _ = write_fn(FSM_CHECKPOINTS_TABLE_SQL)
        return bool(success)
    return False
