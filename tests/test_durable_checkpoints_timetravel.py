"""
tests/test_durable_checkpoints_timetravel.py — SDD-SURVIVAL-20

Suíte de testes TDD para Durable Checkpoints & Lógica de Time-Travel.

Valida:
  1. Serialização segura de variáveis complexas e sanitização de objetos não-serializáveis.
  2. Execução determinística de Time-Travel:
     - Expurgando checkpoints futuros para manter a linha do tempo cronológica linear.
     - Marcando o arquivo associado à tarefa (task_id) como is_dirty = 1 no SQLite WAL.
  3. Endpoints REST da Telemetry API:
     - GET /api/checkpoints/{session_id}
     - POST /api/checkpoints/time-travel
"""

import unittest
import tempfile
import os
import time
from fastapi.testclient import TestClient

from core.database import ConciergeDatabaseManager
from core.checkpointer import AgnosticCheckpointer
from interface.telemetry_api import app, get_db_manager


class TestDurableCheckpointsTimeTravel(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)
        self.checkpointer = AgnosticCheckpointer(self.db_manager)

        # Criação dos schemas necessários para os testes
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
            "shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (session_id, checkpoint_id)"
            ");"
        )

        # Override da dependência do FastAPI para testes de endpoints
        app.dependency_overrides[get_db_manager] = lambda: self.db_manager
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                p = self.db_path + ext
                if os.path.exists(p):
                    os.unlink(p)
        except OSError:
            pass

    def test_should_save_and_load_complex_state_checkpoint(self):
        """Valida se dados lógicos e não-serializáveis sofrem limpeza e gravação segura."""
        complex_variables = {
            "token_count": 4200,
            "system_prompt": "Identidade Canônica",
            "active_lock": object(),  # Objeto não-serializável em JSON clássico!
            "status_list": ["PLANNING", "DISCOVERY"],
        }

        # 1. Salva o checkpoint na sessão
        success = self.checkpointer.save_checkpoint(
            session_id="session_001",
            checkpoint_id="init_state",
            agent_id="HermesAgent",
            state_name="PLANNING",
            shared_state=complex_variables,
            task_id="src/core.py",
        )
        self.assertTrue(success)

        # 2. Recupera o checkpoint
        data = self.checkpointer.load_checkpoint("session_001", "init_state")
        self.assertIsNotNone(data)
        self.assertEqual(data["agent_id"], "HermesAgent")
        self.assertEqual(data["state_name"], "PLANNING")
        self.assertEqual(data["task_id"], "src/core.py")

        # O objeto complexo (object()) deve ter sofrido stringificação segura
        self.assertIn("active_lock", data["shared_state"])
        self.assertTrue(isinstance(data["shared_state"]["active_lock"], str))
        self.assertEqual(data["shared_state"]["token_count"], 4200)

    def test_should_execute_time_travel_and_purge_future_checkpoints(self):
        """Valida se o Time-Travel remove checkpoints futuros e marca arquivos como sujos."""
        # Inserir arquivo
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty) VALUES ('src/core.py', 'core', 0);"
        )

        # Grava Checkpoint 1 (Passado)
        self.checkpointer.save_checkpoint(
            "session_abc", "cp_1", "Hermes", "PLANNING", {"x": 10}, "src/core.py"
        )
        time.sleep(1.1)  # Pausa garantidora de cronologia para o 'created_at' do SQLite

        # Grava Checkpoint 2 (Futuro)
        self.checkpointer.save_checkpoint(
            "session_abc", "cp_2", "Hermes", "EXECUTION", {"x": 20}, "src/core.py"
        )

        # Valida que existem 2 checkpoints salvos
        checkpoints_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM fsm_checkpoints WHERE session_id = 'session_abc';"
        )[0][0]
        self.assertEqual(checkpoints_count, 2)

        # Dispara Viagem no Tempo para o cp_1 (Passado)
        restored = self.checkpointer.execute_time_travel("session_abc", "cp_1")
        self.assertIsNotNone(restored)
        self.assertEqual(restored["shared_state"]["x"], 10)

        # Checkpoint cp_2 (futuro) deve ter sido expurgado cronologicamente
        remaining_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM fsm_checkpoints WHERE session_id = 'session_abc';"
        )[0][0]
        self.assertEqual(remaining_count, 1)

        # O arquivo 'src/core.py' associado ao checkpoint deve ter sido marcado como sujo (is_dirty = 1) para re-sincronizar
        file_dirty = self.db_manager.read_query(
            "SELECT is_dirty FROM files WHERE path = 'src/core.py';"
        )[0][0]
        self.assertEqual(file_dirty, 1)

    def test_telemetry_api_checkpoints_endpoints(self):
        """Valida os endpoints REST /api/checkpoints/{session_id} e /api/checkpoints/time-travel."""
        # 1. Salva 2 checkpoints via checkpointer
        self.checkpointer.save_checkpoint(
            "sess_rest", "cp_start", "RestAgent", "IDLE", {"state": "init"}, "src/app.py"
        )
        time.sleep(1.1)
        self.checkpointer.save_checkpoint(
            "sess_rest", "cp_mid", "RestAgent", "RUNNING", {"state": "mid"}, "src/app.py"
        )

        # 2. Testa listagem de checkpoints da sessão
        resp_list = self.client.get("/api/checkpoints/sess_rest")
        self.assertEqual(resp_list.status_code, 200)
        items = resp_list.json()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["checkpoint_id"], "cp_start")
        self.assertEqual(items[1]["checkpoint_id"], "cp_mid")

        # 3. Testa disparo de time-travel via POST
        resp_tt = self.client.post(
            "/api/checkpoints/time-travel",
            json={"session_id": "sess_rest", "target_checkpoint_id": "cp_start"},
        )
        self.assertEqual(resp_tt.status_code, 200)
        data = resp_tt.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["restored_state"]["checkpoint_id"], "cp_start")

        # 4. Testa time-travel para checkpoint inexistente (retorna 404)
        resp_404 = self.client.post(
            "/api/checkpoints/time-travel",
            json={"session_id": "sess_rest", "target_checkpoint_id": "cp_ghost"},
        )
        self.assertEqual(resp_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
