"""
tests/test_telemetry_api.py — SDD-SURVIVAL-13

Suíte de Testes TDD para a Camada de API REST e Telemetria em Tempo Real.

Valida que as rotas estão funcionando de forma consistente e que o canal
de streaming SSE entrega os dados de alteração de forma assíncrona.

Testes:
    1. test_get_telemetry_snapshot — Snapshot consolida contadores do SQLite
    2. test_janitor_manual_reconcile_trigger — Janitor retorna 'accepted'
    3. test_telemetry_stream_sse_emits_updates — SSE transmite payload válido
"""

import unittest
import tempfile
import os
import sqlite3
import time
import json
from fastapi.testclient import TestClient
from interface.telemetry_api import app, get_db_manager
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager


class TestTelemetryAPI(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Cria as tabelas mínimas necessárias para o Snapshot de Telemetria
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT, session_id TEXT, "
            "checkpoint_id TEXT, timestamp REAL"
            ");"
        )
        time.sleep(0.1)

        # Injeta o db_manager de teste na aplicação FastAPI
        app.dependency_overrides[get_db_manager] = lambda: self.db_manager
        self.client = TestClient(app)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        app.dependency_overrides.clear()

    def test_get_telemetry_snapshot(self):
        """Valida se o snapshot consolida os contadores do SQLite com sucesso"""
        # Insere dados de controle
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty, last_modified) VALUES (?, ?, ?, ?);",
            ("src/core.py", "core_module", 1, time.time())
        )
        self.db_manager.write_query(
            "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, timestamp) VALUES (?, ?, ?, ?);",
            ("NexusAgent", "session_001", "init", time.time())
        )
        time.sleep(0.1)

        response = self.client.get("/api/telemetry/snapshot")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["sqlite_total_files"], 1)
        self.assertEqual(len(data["dirty_queue"]), 1)
        self.assertEqual(data["dirty_queue"][0]["path"], "src/core.py")
        self.assertEqual(len(data["agent_sessions"]), 1)
        self.assertEqual(data["agent_sessions"][0]["session_id"], "session_001")

    def test_janitor_manual_reconcile_trigger(self):
        """Valida que o acionamento do Janitor retorna resposta aceita síncrona"""
        response = self.client.post("/api/janitor/reconcile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")

    def test_telemetry_stream_sse_emits_updates(self):
        """Valida que o canal SSE transmite o snapshot validado na inicialização"""
        # Abre a stream SSE usando o cliente de teste
        with self.client.stream("GET", "/api/telemetry/stream") as response:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                response.headers["content-type"].startswith("text/event-stream"),
                f"Expected text/event-stream, got {response.headers['content-type']}"
            )

            # Lê o primeiro evento transmitido
            for line in response.iter_lines():
                if line.startswith("data:"):
                    json_str = line.replace("data: ", "").strip()
                    payload = json.loads(json_str)

                    # O Payload SSE deve conter a estrutura de dados de telemetria
                    self.assertIn("integrity_score", payload)
                    self.assertIn("sqlite_total_files", payload)
                    self.assertIn("dirty_queue", payload)
                    break


if __name__ == "__main__":
    unittest.main()
