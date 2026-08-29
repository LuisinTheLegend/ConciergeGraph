"""
storage/relational_db.py — SDD-SURVIVAL-20

Schema relacional e operações de persistência para Durable Checkpointing & Time-Travel.

Define a tabela `fsm_checkpoints` com chave primária composta (session_id, checkpoint_id)
para isolamento estrito de sessões concorrentes e retenção de snapshots de FSM do agente.
"""

from typing import Any

# SQL DDL para a tabela de checkpoints duráveis de FSM
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
    Inicializa a tabela fsm_checkpoints no banco de dados SQLite WAL.
    """
    write_fn = getattr(db_manager, "execute_write", getattr(db_manager, "write_query", None))
    if write_fn:
        success, _ = write_fn(FSM_CHECKPOINTS_TABLE_SQL)
        return bool(success)
    return False
