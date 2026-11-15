"""
tests/test_telemetry_api.py — SDD-SURVIVAL-13

TDD Test Suite for the REST API Layer and Real-Time Telemetry.

Validates that routes operate consistently and that the SSE streaming channel
delivers change payloads asynchronously.

Tests:
    1. test_get_telemetry_snapshot — Snapshot aggregates SQLite counters
    2. test_janitor_manual_reconcile_trigger — Janitor returns 'accepted'
    3. test_telemetry_stream_sse_emits_updates — SSE broadcasts valid payload
    4. test_get_gating_config — Returns active gating configuration
    5. test_update_gating_config_transitions — Dynamic mode switching & validation
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

        # Create minimal required tables for Telemetry Snapshot
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

        # Inject test db_manager into FastAPI application dependency container
        app.dependency_overrides[get_db_manager] = lambda: self.db_manager
        self.client = TestClient(app)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        app.dependency_overrides.clear()

    def test_get_telemetry_snapshot(self):
        """Validates that the snapshot aggregates SQLite counters accurately."""
        # Insert control data
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty, last_modified) VALUES (?, ?, ?, ?);",
            ("src/core.py", "core_module", 1, time.time())
        )
        self.db_manager.write_query(
            "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, timestamp) VALUES (?, ?, ?, ?);",
            ("CognitiveAgent", "session_001", "init", time.time())
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
        """Validates that triggering the Janitor returns an accepted status immediately."""
        response = self.client.post("/api/janitor/reconcile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")

    def test_telemetry_stream_sse_emits_updates(self):
        """Validates that the SSE channel streams the initial validated snapshot."""
        # Open SSE stream using test client
        with self.client.stream("GET", "/api/telemetry/stream") as response:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                response.headers["content-type"].startswith("text/event-stream"),
                f"Expected text/event-stream, got {response.headers['content-type']}"
            )

            # Read first emitted event
            for line in response.iter_lines():
                if line.startswith("data:"):
                    json_str = line.replace("data: ", "").strip()
                    payload = json.loads(json_str)

                    # SSE payload must contain telemetry data structure
                    self.assertIn("integrity_score", payload)
                    self.assertIn("sqlite_total_files", payload)
                    self.assertIn("dirty_queue", payload)
                    break

    def test_get_gating_config(self):
        """Validates that GET /api/gating/config returns current mode and project root."""
        response = self.client.get("/api/gating/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("active_mode", data)
        self.assertIn("project_root", data)
        self.assertIn(data["active_mode"], ["plan-only", "ask", "auto-approve"])

    def test_update_gating_config_transitions(self):
        """Validates dynamic mode transitions and rejection of invalid modes."""
        # Valid transition to auto-approve
        resp = self.client.post("/api/gating/config", json={"mode": "auto-approve"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["new_mode"], "auto-approve")

        # Verify persistence via GET
        get_resp = self.client.get("/api/gating/config")
        self.assertEqual(get_resp.json()["active_mode"], "auto-approve")

        # Valid transition back to ask
        resp_ask = self.client.post("/api/gating/config", json={"mode": "ask"})
        self.assertEqual(resp_ask.status_code, 200)
        self.assertEqual(resp_ask.json()["new_mode"], "ask")

        # Invalid mode must return HTTP 400
        resp_inv = self.client.post("/api/gating/config", json={"mode": "yolo-mode"})
        self.assertEqual(resp_inv.status_code, 400)


if __name__ == "__main__":
    unittest.main()
