"""
core/checkpointer.py — SDD-SURVIVAL-07 / SDD-SURVIVAL-20

Persistência de Checkpoints e Time-Travel Agnóstico para Estados e Sessões de Agentes.

Cartucho de salvamento genérico que persiste dicionários de estado e snapshots de FSM
de qualquer agente de IA como JSON stringizado no SQLite WAL, isolado por
chave primária composta (session_id, checkpoint_id) em fsm_checkpoints e
(agent_id, session_id, checkpoint_id) em agent_checkpoints.

Princípios de design:
  - Zero acoplamento: não conhece variáveis ou FSMs de agentes específicos
  - Isolamento hermético: chave composta garante separação total entre
    agentes, sessões e linhas do tempo concorrentes
  - Resiliência JSON: sanitiza objetos complexos não serializáveis (locks, sockets)
  - Time-Travel Determinístico: ordenação cronológica crescente viabiliza rollback
    cognitivo e marca arquivos associados como dirty para re-sincronização no disco
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgnosticCheckpointer:
    """
    Gerenciador de estados agnóstico que persiste e recupera dicionários
    de variáveis de IA como blobs JSON no SQLite WAL, viabilizando
    Time-Travel Debugging e isolamento multi-agente.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager
        self.db = db_manager

    # ── Sanitização de Objetos Não-Serializáveis ──────────────────

    @staticmethod
    def _sanitize_for_json(obj: Any) -> Any:
        """
        Converte recursivamente objetos não-serializáveis em strings representativas,
        garantindo persistência resiliente sem falhas de runtime.
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

    # ── Gravação de Estado (SDD-20 & SDD-07 Híbrido) ──────────────

    def save_checkpoint(
        self,
        *args,
        **kwargs,
    ) -> bool:
        """
        Salva atomicamente o snapshot completo de variáveis e estado mental
        da FSM do agente no SQLite WAL.

        Suporta tanto a assinatura estendida FSM (SDD-20):
            save_checkpoint(session_id, checkpoint_id, agent_id, state_name, shared_state, task_id=None)
        quanto a assinatura agnóstica legada (SDD-07):
            save_checkpoint(agent_id, session_id, checkpoint_id, state_dict)
        """
        is_sdd20 = (
            "state_name" in kwargs
            or "shared_state" in kwargs
            or len(args) >= 5
            or (len(args) == 4 and isinstance(args[3], str))
        )

        if is_sdd20:
            # Assinatura SDD-20
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

            # Sanitização segura de objetos não-serializáveis (ex: locks, sockets)
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
            # Assinatura legada SDD-07
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

    # ── Recuperação de Estado (SDD-20) ───────────────────────────

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera e desserializa o snapshot de variáveis de um checkpoint específico da FSM.
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

    # ── Time-Travel Operacional (SDD-20) ─────────────────────────

    def execute_time_travel(self, session_id: str, target_checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Executa a reversão física e cognitiva (Time-Travel) para um checkpoint anterior.
        Deleta checkpoints futuros criados após o alvo para preservar o determinismo cronológico linear.
        Marca o arquivo associado à tarefa (task_id) como sujo (is_dirty = 1) no banco relacional.
        """
        # 1. Recupera os dados do checkpoint alvo
        target_data = self.load_checkpoint(session_id, target_checkpoint_id)
        if not target_data:
            return None

        # 2. Busca data de criação do checkpoint de destino
        time_query = "SELECT created_at, task_id FROM fsm_checkpoints WHERE session_id = ? AND checkpoint_id = ?;"
        read_fn = getattr(self.db, "read_query")
        time_rows = read_fn(time_query, (session_id, target_checkpoint_id))
        if not time_rows:
            return None
        created_at, task_id = time_rows[0]

        # 3. Transação Atômica: Remove os checkpoints "futuros" e marca o arquivo associado como sujo
        queries = [
            ("DELETE FROM fsm_checkpoints WHERE session_id = ? AND created_at > ?;", (session_id, created_at)),
        ]

        if task_id:
            # Força re-indexação do arquivo associado na borda (Watcher/DeltaManager)
            queries.append(("UPDATE files SET is_dirty = 1, last_modified = ? WHERE path = ?;", (time.time(), task_id)))

        write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))
        try:
            for q, params in queries:
                write_fn(q, params)
            return target_data
        except Exception as e:
            logger.error("[TIME-TRAVEL] Falha de reversão no SQLite WAL: %s", str(e))
            return None

    # ── Métodos Legados SDD-07 ────────────────────────────────────

    def get_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: str,
    ) -> Dict[str, Any]:
        """
        Recupera o estado salvo sob a chave composta (agent_id, session_id, checkpoint_id)
        e decodifica o JSON de volta para dicionário Python.

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
