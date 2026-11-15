"""
tests/test_durable_checkpoints_timetravel.py — SDD-SURVIVAL-20

TDD Test Suite for Durable Checkpoints & Cognitive Time-Travel Logic.

Validates:
  1. Safe serialization of complex variables and recursive sanitization of non-serializable objects.
  2. Deterministic execution of Time-Travel:
     - Purging future checkpoints to preserve linear chronological timeline continuity.
     - Marking task-associated files (task_id) as is_dirty = 1 in SQLite WAL.
  3. Telemetry API REST Endpoints:
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

        # Create necessary schemas for test execution
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

        # Override FastAPI dependency injection for API endpoint tests
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
        """Validates that logical and non-serializable objects undergo sanitization and safe persistence."""
        complex_variables = {
            "token_count": 4200,
            "system_prompt": "Canonical Identity",
            "active_lock": object(),  # Non-serializable object in standard JSON!
            "status_list": ["PLANNING", "DISCOVERY"],
        }

        # 1. Save checkpoint for the session
        success = self.checkpointer.save_checkpoint(
            session_id="session_001",
            checkpoint_id="init_state",
            agent_id="CognitiveAgent",
            state_name="PLANNING",
            shared_state=complex_variables,
            task_id="src/core.py",
        )
        self.assertTrue(success)

        # 2. Retrieve checkpoint
        data = self.checkpointer.load_checkpoint("session_001", "init_state")
        self.assertIsNotNone(data)
        self.assertEqual(data["agent_id"], "CognitiveAgent")
        self.assertEqual(data["state_name"], "PLANNING")
        self.assertEqual(data["task_id"], "src/core.py")

        # The non-serializable object (object()) must have undergone defensive string conversion
        self.assertIn("active_lock", data["shared_state"])
        self.assertTrue(isinstance(data["shared_state"]["active_lock"], str))
        self.assertEqual(data["shared_state"]["token_count"], 4200)

    def test_should_execute_time_travel_and_purge_future_checkpoints(self):
        """Validates that Time-Travel purges future checkpoints and marks affected files as dirty."""
        # Insert target file
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty) VALUES ('src/core.py', 'core', 0);"
        )

        # Save Checkpoint 1 (Past)
        self.checkpointer.save_checkpoint(
            "session_abc", "cp_1", "PrimaryAgent", "PLANNING", {"x": 10}, "src/core.py"
        )
        time.sleep(1.1)  # Ensure SQLite created_at timestamp differentiation

        # Save Checkpoint 2 (Future)
        self.checkpointer.save_checkpoint(
            "session_abc", "cp_2", "PrimaryAgent", "EXECUTION", {"x": 20}, "src/core.py"
        )

        # Verify 2 checkpoints exist in database
        checkpoints_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM fsm_checkpoints WHERE session_id = 'session_abc';"
        )[0][0]
        self.assertEqual(checkpoints_count, 2)

        # Trigger Time-Travel rollback to cp_1 (Past)
        restored = self.checkpointer.execute_time_travel("session_abc", "cp_1")
        self.assertIsNotNone(restored)
        self.assertEqual(restored["shared_state"]["x"], 10)

        # Checkpoint cp_2 (future) must be chronologically purged
        remaining_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM fsm_checkpoints WHERE session_id = 'session_abc';"
        )[0][0]
        self.assertEqual(remaining_count, 1)

        # Associated file 'src/core.py' must be flagged dirty (is_dirty = 1) for graph re-synchronization
        file_dirty = self.db_manager.read_query(
            "SELECT is_dirty FROM files WHERE path = 'src/core.py';"
        )[0][0]
        self.assertEqual(file_dirty, 1)

    def test_telemetry_api_checkpoints_endpoints(self):
        """Validates REST endpoints /api/checkpoints/{session_id} and /api/checkpoints/time-travel."""
        # 1. Save 2 checkpoints via checkpointer
        self.checkpointer.save_checkpoint(
            "sess_rest", "cp_start", "RestAgent", "IDLE", {"state": "init"}, "src/app.py"
        )
        time.sleep(1.1)
        self.checkpointer.save_checkpoint(
            "sess_rest", "cp_mid", "RestAgent", "RUNNING", {"state": "mid"}, "src/app.py"
        )

        # 2. Test listing session checkpoints
        resp_list = self.client.get("/api/checkpoints/sess_rest")
        self.assertEqual(resp_list.status_code, 200)
        items = resp_list.json()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["checkpoint_id"], "cp_start")
        self.assertEqual(items[1]["checkpoint_id"], "cp_mid")

        # 3. Test triggering time-travel via POST
        resp_tt = self.client.post(
            "/api/checkpoints/time-travel",
            json={"session_id": "sess_rest", "target_checkpoint_id": "cp_start"},
        )
        self.assertEqual(resp_tt.status_code, 200)
        data = resp_tt.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["restored_state"]["checkpoint_id"], "cp_start")

        # 4. Test time-travel for nonexistent checkpoint (returns 404)
        resp_404 = self.client.post(
            "/api/checkpoints/time-travel",
            json={"session_id": "sess_rest", "target_checkpoint_id": "cp_ghost"},
        )
        self.assertEqual(resp_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
