"""
tests/test_agent_checkpointer.py — SDD-SURVIVAL-07

Suíte de Testes TDD para Persistência de Checkpoints e Time-Travel Agnóstico.

Valida os quatro contratos de isolamento e integridade:
  1. Save/Retrieve: estado genérico é persistido e recuperado perfeitamente.
  2. Fail-Safe: checkpoints inexistentes retornam dicionário vazio.
  3. Timeline: checkpoints são listados em ordem cronológica crescente.
  4. Isolation: agentes/sessões diferentes jamais leem dados uns dos outros.

Integra com a infraestrutura real de concorrência (SDD-02).
"""

import unittest
import os
import sys
import importlib
import tempfile
import json


# ── Importação cirúrgica: carrega módulos diretamente sem acionar
#    os __init__.py dos pacotes (que puxam dependências pesadas). ──

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1) interface.queue_writer
_qw_spec = importlib.util.spec_from_file_location(
    "interface.queue_writer",
    os.path.join(_project_root, "interface", "queue_writer.py"),
)
_qw_mod = importlib.util.module_from_spec(_qw_spec)
sys.modules["interface.queue_writer"] = _qw_mod
_qw_spec.loader.exec_module(_qw_mod)
SerializedWriteQueue = _qw_mod.SerializedWriteQueue

# 2) core.database
_db_spec = importlib.util.spec_from_file_location(
    "core.database",
    os.path.join(_project_root, "core", "database.py"),
)
_db_mod = importlib.util.module_from_spec(_db_spec)
sys.modules["core.database"] = _db_mod
_db_spec.loader.exec_module(_db_mod)
ConciergeDatabaseManager = _db_mod.ConciergeDatabaseManager

# 3) core.checkpointer
_cp_spec = importlib.util.spec_from_file_location(
    "core.checkpointer",
    os.path.join(_project_root, "core", "checkpointer.py"),
)
_cp_mod = importlib.util.module_from_spec(_cp_spec)
sys.modules["core.checkpointer"] = _cp_mod
_cp_spec.loader.exec_module(_cp_mod)
AgnosticCheckpointer = _cp_mod.AgnosticCheckpointer


class TestAgnosticCheckpointerAndTimeTravel(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa infraestrutura de concorrência síncrona da Fase 1
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação da tabela de checkpoints no SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "agent_id TEXT, "
            "session_id TEXT, "
            "checkpoint_id TEXT, "
            "state_blob TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
            ");"
        )

        # Inicializa o checkpointer agnóstico
        self.checkpointer = AgnosticCheckpointer(self.db_manager)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                wal_path = self.db_path + ext
                if os.path.exists(wal_path):
                    os.unlink(wal_path)
        except OSError:
            pass

    def test_should_save_and_retrieve_checkpoint_successfully(self):
        """Garante que estados genéricos de agentes são persistidos e recuperados perfeitamente."""
        state_data = {
            "active_node": "PLANNING",
            "tokens_consumed": 1542,
            "kanban_todo": ["task1", "task2"],
            "variables": {"project_name": "Nexus"},
        }

        # Grava o checkpoint para o 'nexus_agent'
        saved = self.checkpointer.save_checkpoint(
            agent_id="nexus_agent",
            session_id="sess_01",
            checkpoint_id="step_01",
            state_dict=state_data,
        )
        self.assertTrue(
            saved,
            "O salvamento do checkpoint deveria ter sido executado com sucesso.",
        )

        # Recupera o checkpoint gravado
        retrieved_state = self.checkpointer.get_checkpoint(
            agent_id="nexus_agent",
            session_id="sess_01",
            checkpoint_id="step_01",
        )

        # Asserções de Integridade dos Dados
        self.assertEqual(retrieved_state["active_node"], "PLANNING")
        self.assertEqual(retrieved_state["tokens_consumed"], 1542)
        self.assertEqual(retrieved_state["kanban_todo"], ["task1", "task2"])
        self.assertEqual(retrieved_state["variables"]["project_name"], "Nexus")

    def test_should_return_empty_for_nonexistent_checkpoint(self):
        """Garante retorno seguro e vazio caso o agente tente buscar um estado fantasma."""
        state = self.checkpointer.get_checkpoint("ghost_agent", "sess_99", "step_99")
        self.assertEqual(
            state, {}, "Checkpoints inexistentes devem retornar um dicionário vazio."
        )

    def test_should_list_checkpoints_ordered_chronologically(self):
        """Valida que o checkpointer organiza a linha do tempo cronológica para Time-Travel."""
        agent = "hermes_agent"
        session = "sess_42"

        # Salva checkpoints sequenciais na linha do tempo
        self.checkpointer.save_checkpoint(agent, session, "init", {"step": 0})
        self.checkpointer.save_checkpoint(agent, session, "loop_1", {"step": 1})
        self.checkpointer.save_checkpoint(agent, session, "loop_2", {"step": 2})

        # Coleta a linha do tempo de checkpoints do banco
        timeline = self.checkpointer.list_checkpoints(agent, session)

        # O retorno deve listar 3 checkpoints ordenados por criação (crescente)
        self.assertEqual(
            len(timeline),
            3,
            "Deveria listar exatamente os 3 checkpoints gravados.",
        )

        checkpoint_ids = [item["checkpoint_id"] for item in timeline]
        self.assertEqual(
            checkpoint_ids,
            ["init", "loop_1", "loop_2"],
            "A ordenação cronológica foi violada.",
        )

    def test_should_isolate_multiple_agents_and_sessions(self):
        """Garante isolamento estrito: um agente/sessão jamais lê checkpoints de outros vizinhos."""
        # Salva o mesmo checkpoint_id em agentes e sessões distintas
        self.checkpointer.save_checkpoint(
            "nexus", "session_A", "step_1", {"owner": "nexus_A"}
        )
        self.checkpointer.save_checkpoint(
            "nexus", "session_B", "step_1", {"owner": "nexus_B"}
        )
        self.checkpointer.save_checkpoint(
            "hermes", "session_A", "step_1", {"owner": "hermes_A"}
        )

        # Valida que cada busca é cirúrgica e isolada
        state_nexus_a = self.checkpointer.get_checkpoint(
            "nexus", "session_A", "step_1"
        )
        self.assertEqual(state_nexus_a["owner"], "nexus_A")

        state_nexus_b = self.checkpointer.get_checkpoint(
            "nexus", "session_B", "step_1"
        )
        self.assertEqual(state_nexus_b["owner"], "nexus_B")

        state_hermes_a = self.checkpointer.get_checkpoint(
            "hermes", "session_A", "step_1"
        )
        self.assertEqual(state_hermes_a["owner"], "hermes_A")


if __name__ == "__main__":
    unittest.main()
