"""
core/checkpointer.py — SDD-SURVIVAL-07

Persistência de Checkpoints e Time-Travel Agnóstico.

Cartucho de salvamento genérico que persiste dicionários de estado de
qualquer agente de IA como JSON stringizado no SQLite WAL, isolado por
chave primária composta (agent_id, session_id, checkpoint_id).

Princípios de design:
  - Zero acoplamento: não conhece variáveis ou FSMs de agentes específicos
  - Isolamento hermético: chave composta garante separação total entre
    agentes, sessões e linhas do tempo concorrentes
  - Time-Travel: ordenação cronológica crescente viabiliza navegação
    temporal para depuração e rollback de estados
"""

import json
from typing import Any, Dict, List


class AgnosticCheckpointer:
    """
    Gerenciador de estados agnóstico que persiste e recupera dicionários
    de variáveis de IA como blobs JSON no SQLite WAL, viabilizando
    Time-Travel Debugging e isolamento multi-agente.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Gravação de Estado ────────────────────────────────────────

    def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: str,
        state_dict: Dict[str, Any],
    ) -> bool:
        """
        Converte o dicionário de estado em JSON e persiste no SQLite WAL
        sob a chave primária composta (agent_id, session_id, checkpoint_id).

        Usa INSERT OR REPLACE para permitir sobrescrita idempotente de
        checkpoints com a mesma chave (upsert agnóstico).
        """
        state_blob = json.dumps(state_dict, ensure_ascii=False)
        success, _ = self.db_manager.write_query(
            "INSERT OR REPLACE INTO agent_checkpoints "
            "(agent_id, session_id, checkpoint_id, state_blob) "
            "VALUES (?, ?, ?, ?);",
            (agent_id, session_id, checkpoint_id, state_blob),
        )
        return success

    # ── Recuperação de Estado ─────────────────────────────────────

    def get_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: str,
    ) -> Dict[str, Any]:
        """
        Recupera o estado salvo sob a chave composta e decodifica o JSON
        de volta para dicionário Python.

        Retorna {} se o checkpoint não existir (fail-safe agnóstico).
        """
        rows = self.db_manager.read_query(
            "SELECT state_blob FROM agent_checkpoints "
            "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ?;",
            (agent_id, session_id, checkpoint_id),
        )
        if not rows:
            return {}
        return json.loads(rows[0][0])

    # ── Linha do Tempo (Time-Travel) ──────────────────────────────

    def list_checkpoints(
        self,
        agent_id: str,
        session_id: str,
    ) -> List[Dict[str, str]]:
        """
        Lista todos os checkpoints de um agente/sessão ordenados
        cronologicamente (created_at ASC), viabilizando Time-Travel.

        Retorna lista de dicionários com checkpoint_id e created_at.
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
