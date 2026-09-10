"""
tests/test_agent_checkpointer.py — SDD-SURVIVAL-07

TDD Test Suite for Agnostic State Checkpointing and Time-Travel.

Validates four isolation and integrity contracts:
  1. Save/Retrieve: Generic state is persisted and restored reliably.
  2. Fail-Safe: Nonexistent checkpoints return an empty dictionary.
  3. Timeline: Checkpoints are listed in ascending chronological order.
  4. Isolation: Distinct agents/sessions never leak or read each other's data.

Integrates with the live concurrency infrastructure (SDD-02).
"""

import unittest
import os
import sys
import importlib
import tempfile
import json


# ── Surgical Import: loads modules directly without triggering package __init__.py ──

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

        # Initialize Phase 1 synchronous concurrency infrastructure
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Ensure creation of the agent_checkpoints table in SQLite WAL
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

        # Initialize the agnostic checkpointer
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
        """Ensures that generic agent states are persisted and retrieved successfully."""
        state_data = {
            "active_node": "PLANNING",
            "tokens_consumed": 1542,
            "kanban_todo": ["task1", "task2"],
            "variables": {"project_name": "ConciergeCore"},
        }

        # Save checkpoint for 'primary_agent'
        saved = self.checkpointer.save_checkpoint(
            agent_id="primary_agent",
            session_id="sess_01",
            checkpoint_id="step_01",
            state_dict=state_data,
        )
        self.assertTrue(
            saved,
            "Checkpoint save operation should complete successfully.",
        )

        # Retrieve saved checkpoint
        retrieved_state = self.checkpointer.get_checkpoint(
            agent_id="primary_agent",
            session_id="sess_01",
            checkpoint_id="step_01",
        )

        # Data integrity assertions
        self.assertEqual(retrieved_state["active_node"], "PLANNING")
        self.assertEqual(retrieved_state["tokens_consumed"], 1542)
        self.assertEqual(retrieved_state["kanban_todo"], ["task1", "task2"])
        self.assertEqual(retrieved_state["variables"]["project_name"], "ConciergeCore")

    def test_should_return_empty_for_nonexistent_checkpoint(self):
        """Ensures safe empty return when querying a nonexistent checkpoint."""
        state = self.checkpointer.get_checkpoint("ghost_agent", "sess_99", "step_99")
        self.assertEqual(
            state, {}, "Nonexistent checkpoints must return an empty dictionary."
        )

    def test_should_list_checkpoints_ordered_chronologically(self):
        """Validates that the checkpointer organizes the timeline in ascending chronological order for time-travel."""
        agent = "cognitive_agent"
        session = "sess_42"

        # Save sequential checkpoints along the timeline
        self.checkpointer.save_checkpoint(agent, session, "init", {"step": 0})
        self.checkpointer.save_checkpoint(agent, session, "loop_1", {"step": 1})
        self.checkpointer.save_checkpoint(agent, session, "loop_2", {"step": 2})

        # Fetch chronological checkpoints from database
        timeline = self.checkpointer.list_checkpoints(agent, session)

        # Expected 3 checkpoints sorted by creation timestamp (ascending)
        self.assertEqual(
            len(timeline),
            3,
            "Should list exactly 3 recorded checkpoints.",
        )

        checkpoint_ids = [item["checkpoint_id"] for item in timeline]
        self.assertEqual(
            checkpoint_ids,
            ["init", "loop_1", "loop_2"],
            "Chronological ordering was violated.",
        )

    def test_should_isolate_multiple_agents_and_sessions(self):
        """Ensures strict multi-tenant isolation: distinct agents and sessions never leak checkpoints."""
        # Save identical checkpoint_id across distinct agents and sessions
        self.checkpointer.save_checkpoint(
            "agent_alpha", "session_A", "step_1", {"owner": "alpha_A"}
        )
        self.checkpointer.save_checkpoint(
            "agent_alpha", "session_B", "step_1", {"owner": "alpha_B"}
        )
        self.checkpointer.save_checkpoint(
            "agent_beta", "session_A", "step_1", {"owner": "beta_A"}
        )

        # Validate isolated, targeted queries
        state_alpha_a = self.checkpointer.get_checkpoint(
            "agent_alpha", "session_A", "step_1"
        )
        self.assertEqual(state_alpha_a["owner"], "alpha_A")

        state_alpha_b = self.checkpointer.get_checkpoint(
            "agent_alpha", "session_B", "step_1"
        )
        self.assertEqual(state_alpha_b["owner"], "alpha_B")

        state_beta_a = self.checkpointer.get_checkpoint(
            "agent_beta", "session_A", "step_1"
        )
        self.assertEqual(state_beta_a["owner"], "beta_A")


if __name__ == "__main__":
    unittest.main()
