"""
tests/test_hsm_transition_hooks_and_delta.py -- SDD-SURVIVAL-27

Comprehensive test suite for:
    - HSMNode lifecycle hooks (on_enter / on_exit)
    - Hierarchical hook ordering during transitions
    - Atomic rollback on hook failure (parks in STALL.ERROR_PAUSE)
    - Delta validation on resume_from_history_node (stale file detection)
    - Redirection to EXECUTION.RE_INDEX when structural change detected
"""

import os
import tempfile
import time
import unittest

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from core.hsm_engine import HierarchicalStateMachine, HSMNode


# ── Mock Objects ────────────────────────────────────────────────────


class MockDeltaManager:
    """Mock that simulates structural-change detection for delta validation."""

    def __init__(self, is_structural_change: bool = True):
        self._change = is_structural_change
        self.checked_paths = []

    def has_structural_change(self, path: str) -> bool:
        self.checked_paths.append(path)
        return self._change


class MockDeltaManagerNoChange(MockDeltaManager):
    """Mock that always reports no structural change."""

    def __init__(self):
        super().__init__(is_structural_change=False)


# ── Test Suite ──────────────────────────────────────────────────────


class TestHSMNodeLifecycleHooks(unittest.TestCase):
    """Tests for the HSMNode on_enter/on_exit hook registration and execution."""

    def test_node_initializes_with_empty_hook_lists(self):
        """Validates that new HSMNodes have empty hook lists by default."""
        node = HSMNode("TEST")
        self.assertEqual(node._on_enter_hooks, [])
        self.assertEqual(node._on_exit_hooks, [])

    def test_register_on_enter_appends_callback(self):
        """Validates that register_on_enter appends to the hooks list."""
        node = HSMNode("TEST")
        fn1 = lambda: None
        fn2 = lambda: None
        node.register_on_enter(fn1)
        node.register_on_enter(fn2)
        self.assertEqual(len(node._on_enter_hooks), 2)
        self.assertIs(node._on_enter_hooks[0], fn1)
        self.assertIs(node._on_enter_hooks[1], fn2)

    def test_register_on_exit_appends_callback(self):
        """Validates that register_on_exit appends to the hooks list."""
        node = HSMNode("TEST")
        fn = lambda: None
        node.register_on_exit(fn)
        self.assertEqual(len(node._on_exit_hooks), 1)

    def test_execute_on_enter_fires_all_hooks_in_order(self):
        """Validates that all on_enter hooks fire in registration order."""
        node = HSMNode("TEST")
        results = []
        node.register_on_enter(lambda: results.append("A"))
        node.register_on_enter(lambda: results.append("B"))
        node.execute_on_enter()
        self.assertEqual(results, ["A", "B"])

    def test_execute_on_exit_fires_all_hooks_in_order(self):
        """Validates that all on_exit hooks fire in registration order."""
        node = HSMNode("TEST")
        results = []
        node.register_on_exit(lambda: results.append("X"))
        node.register_on_exit(lambda: results.append("Y"))
        node.execute_on_exit()
        self.assertEqual(results, ["X", "Y"])

    def test_execute_on_enter_raises_runtime_error_on_failure(self):
        """Validates that a failing on_enter hook raises RuntimeError."""
        node = HSMNode("BROKEN")
        node.register_on_enter(lambda: (_ for _ in ()).throw(ValueError("boom")))
        with self.assertRaises(RuntimeError) as ctx:
            node.execute_on_enter()
        self.assertIn("on_enter hook failure", str(ctx.exception))
        self.assertIn("BROKEN", str(ctx.exception))

    def test_execute_on_exit_raises_runtime_error_on_failure(self):
        """Validates that a failing on_exit hook raises RuntimeError."""
        node = HSMNode("BROKEN")
        node.register_on_exit(lambda: (_ for _ in ()).throw(ValueError("crash")))
        with self.assertRaises(RuntimeError) as ctx:
            node.execute_on_exit()
        self.assertIn("on_exit hook failure", str(ctx.exception))

    def test_execute_hooks_with_no_hooks_is_noop(self):
        """Validates that executing hooks on a node with none registered is safe."""
        node = HSMNode("EMPTY")
        # Should not raise
        node.execute_on_enter()
        node.execute_on_exit()


class TestHSMTransitionHooksIntegration(unittest.TestCase):
    """Tests for hierarchical hook firing during HSM transitions."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
            "shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (session_id, checkpoint_id)"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )

        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.hsm = HierarchicalStateMachine(self.db_manager, self.checkpointer)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_should_trigger_on_enter_and_on_exit_hooks_in_order(self):
        """
        Validates that hooks fire in strict hierarchical order:
        EXIT_DISCOVERY -> EXIT_PLANNING -> ENTER_EXECUTION -> ENTER_CODE_GEN
        """
        events = []

        planning_node = self.hsm.resolve_node("PLANNING")
        discovery_node = self.hsm.resolve_node("PLANNING.DISCOVERY")
        execution_node = self.hsm.resolve_node("EXECUTION")
        code_gen_node = self.hsm.resolve_node("EXECUTION.CODE_GEN")

        discovery_node.register_on_exit(lambda: events.append("EXIT_DISCOVERY"))
        planning_node.register_on_exit(lambda: events.append("EXIT_PLANNING"))
        execution_node.register_on_enter(lambda: events.append("ENTER_EXECUTION"))
        code_gen_node.register_on_enter(lambda: events.append("ENTER_CODE_GEN"))

        # Initialize session at PLANNING.DISCOVERY
        self.hsm.active_session_states["sess_hooks"] = discovery_node

        # Transition to EXECUTION.CODE_GEN
        result = self.hsm.transition_to(
            session_id="sess_hooks",
            target_path="EXECUTION.CODE_GEN",
            agent_id="PrimaryAgent",
            shared_state={},
        )

        self.assertTrue(result)
        expected_order = ["EXIT_DISCOVERY", "EXIT_PLANNING", "ENTER_EXECUTION", "ENTER_CODE_GEN"]
        self.assertEqual(events, expected_order)

    def test_intra_superstate_transition_does_not_fire_superstate_hooks(self):
        """
        Validates that moving within the same super-state (e.g. CODE_GEN -> TDD_GREEN)
        does NOT fire exit/enter hooks on the shared EXECUTION super-state.
        """
        events = []

        execution_node = self.hsm.resolve_node("EXECUTION")
        code_gen_node = self.hsm.resolve_node("EXECUTION.CODE_GEN")
        tdd_green_node = self.hsm.resolve_node("EXECUTION.TDD_GREEN")

        execution_node.register_on_exit(lambda: events.append("EXIT_EXECUTION"))
        execution_node.register_on_enter(lambda: events.append("ENTER_EXECUTION"))
        code_gen_node.register_on_exit(lambda: events.append("EXIT_CODE_GEN"))
        tdd_green_node.register_on_enter(lambda: events.append("ENTER_TDD_GREEN"))

        self.hsm.active_session_states["sess_intra"] = code_gen_node

        result = self.hsm.transition_to(
            session_id="sess_intra",
            target_path="EXECUTION.TDD_GREEN",
            agent_id="PrimaryAgent",
            shared_state={},
        )

        self.assertTrue(result)
        # EXECUTION hooks should NOT fire (shared ancestor)
        self.assertNotIn("EXIT_EXECUTION", events)
        self.assertNotIn("ENTER_EXECUTION", events)
        # Only the sub-state hooks should fire
        self.assertIn("EXIT_CODE_GEN", events)
        self.assertIn("ENTER_TDD_GREEN", events)
        self.assertEqual(events, ["EXIT_CODE_GEN", "ENTER_TDD_GREEN"])

    def test_hook_failure_on_exit_triggers_rollback_to_error_pause(self):
        """
        Validates that a hook failure during on_exit rolls back and parks in STALL.ERROR_PAUSE.
        """
        discovery_node = self.hsm.resolve_node("PLANNING.DISCOVERY")

        def failing_exit():
            raise ValueError("Critical resource lock")

        discovery_node.register_on_exit(failing_exit)
        self.hsm.active_session_states["sess_fail"] = discovery_node

        result = self.hsm.transition_to(
            session_id="sess_fail",
            target_path="EXECUTION.CODE_GEN",
            agent_id="PrimaryAgent",
            shared_state={},
        )

        self.assertFalse(result)
        current = self.hsm.get_current_state("sess_fail")
        self.assertEqual(current, "STALL.ERROR_PAUSE")

    def test_hook_failure_on_enter_triggers_rollback_to_error_pause(self):
        """
        Validates that a hook failure during on_enter also parks in STALL.ERROR_PAUSE.
        """
        code_gen_node = self.hsm.resolve_node("EXECUTION.CODE_GEN")
        discovery_node = self.hsm.resolve_node("PLANNING.DISCOVERY")

        def failing_enter():
            raise RuntimeError("Init failed")

        code_gen_node.register_on_enter(failing_enter)
        self.hsm.active_session_states["sess_enter_fail"] = discovery_node

        result = self.hsm.transition_to(
            session_id="sess_enter_fail",
            target_path="EXECUTION.CODE_GEN",
            agent_id="PrimaryAgent",
            shared_state={},
        )

        self.assertFalse(result)
        current = self.hsm.get_current_state("sess_enter_fail")
        self.assertEqual(current, "STALL.ERROR_PAUSE")

    def test_transition_without_hooks_still_succeeds(self):
        """
        Validates that transitions work normally when no hooks are registered.
        """
        discovery_node = self.hsm.resolve_node("PLANNING.DISCOVERY")
        self.hsm.active_session_states["sess_clean"] = discovery_node

        result = self.hsm.transition_to(
            session_id="sess_clean",
            target_path="EXECUTION.TDD_GREEN",
            agent_id="PrimaryAgent",
            shared_state={"step": 1},
        )

        self.assertTrue(result)
        self.assertEqual(self.hsm.get_current_state("sess_clean"), "EXECUTION.TDD_GREEN")

    def test_re_index_sub_state_exists(self):
        """Validates that EXECUTION.RE_INDEX was added to the topology (SDD-27)."""
        node = self.hsm.resolve_node("EXECUTION.RE_INDEX")
        self.assertIsNotNone(node)
        self.assertEqual(node.name, "RE_INDEX")
        self.assertEqual(node.category, "LOCAL_MUTATION")
        self.assertEqual(node.parent.name, "EXECUTION")


class TestHSMDeltaValidationOnResume(unittest.TestCase):
    """Tests for delta file validation during resume_from_history_node (SDD-27)."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
            "shared_state_blob TEXT, task_id TEXT, created_at REAL, "
            "PRIMARY KEY (session_id, checkpoint_id)"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )

        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.hsm = HierarchicalStateMachine(self.db_manager, self.checkpointer)
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _create_temp_file(self, content: bytes = b"def original(): pass") -> str:
        """Creates a temp file and registers it for cleanup."""
        fd, path = tempfile.mkstemp(suffix=".py")
        os.write(fd, content)
        os.close(fd)
        self.temp_files.append(path)
        return path

    def test_should_detect_stale_file_and_redirect_to_reindex_on_resume(self):
        """
        Validates that resume with a file modified after the checkpoint
        triggers redirection to EXECUTION.RE_INDEX with stale_detected=True.
        """
        file_path = self._create_temp_file()

        old_timestamp = time.time() - 100

        # Save a checkpoint with an old created_at
        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_stale",
            checkpoint_id="cp_old",
            agent_id="PrimaryAgent",
            state_name="EXECUTION.CODE_GEN",
            shared_state={"step": 1},
            task_id=file_path,
        )

        # Backdate the checkpoint in the database
        self.db_manager.write_query(
            "UPDATE fsm_checkpoints SET created_at = ? WHERE checkpoint_id = ?",
            (old_timestamp, "cp_old"),
        )

        # Touch the file on disk (mtime is now newer than checkpoint)
        os.utime(file_path, None)

        delta_mgr = MockDeltaManager(is_structural_change=True)
        restored = self.hsm.resume_from_history_node("sess_stale", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertTrue(restored["shared_state"].get("stale_detected"))
        self.assertEqual(restored["shared_state"].get("original_state"), "EXECUTION.CODE_GEN")
        # Session should be in RE_INDEX
        self.assertEqual(self.hsm.get_current_state("sess_stale"), "EXECUTION.RE_INDEX")
        # DeltaManager was called with the file path
        self.assertIn(file_path, delta_mgr.checked_paths)

    def test_no_redirect_when_file_not_stale(self):
        """
        Validates that resume proceeds normally when the file's mtime is older
        than the checkpoint.
        """
        file_path = self._create_temp_file()

        # Set file mtime to far in the past
        os.utime(file_path, (100.0, 100.0))

        # Save checkpoint with a timestamp after the file mtime
        future_timestamp = time.time() + 100
        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_fresh",
            checkpoint_id="cp_fresh",
            agent_id="PrimaryAgent",
            state_name="EXECUTION.TDD_GREEN",
            shared_state={"step": 2},
            task_id=file_path,
        )

        # Set checkpoint created_at to future (file is older)
        self.db_manager.write_query(
            "UPDATE fsm_checkpoints SET created_at = ? WHERE checkpoint_id = ?",
            (future_timestamp, "cp_fresh"),
        )

        delta_mgr = MockDeltaManager(is_structural_change=True)
        restored = self.hsm.resume_from_history_node("sess_fresh", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertFalse(restored["shared_state"].get("stale_detected", False))
        self.assertEqual(self.hsm.get_current_state("sess_fresh"), "EXECUTION.TDD_GREEN")

    def test_no_redirect_when_delta_manager_reports_no_structural_change(self):
        """
        Validates that resume does NOT redirect to RE_INDEX when delta_manager
        reports no structural change despite file being newer.
        """
        file_path = self._create_temp_file()
        old_timestamp = time.time() - 100

        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_cosmetic",
            checkpoint_id="cp_cosmetic",
            agent_id="PrimaryAgent",
            state_name="EXECUTION.REFACTORING",
            shared_state={"step": 3},
            task_id=file_path,
        )

        self.db_manager.write_query(
            "UPDATE fsm_checkpoints SET created_at = ? WHERE checkpoint_id = ?",
            (old_timestamp, "cp_cosmetic"),
        )

        os.utime(file_path, None)

        delta_mgr = MockDeltaManagerNoChange()
        restored = self.hsm.resume_from_history_node("sess_cosmetic", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertFalse(restored["shared_state"].get("stale_detected", False))
        self.assertEqual(self.hsm.get_current_state("sess_cosmetic"), "EXECUTION.REFACTORING")

    def test_resume_without_delta_manager_works_normally(self):
        """
        Validates backwards compatibility: resume works without delta_manager.
        """
        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_compat",
            checkpoint_id="cp_compat",
            agent_id="PrimaryAgent",
            state_name="PLANNING.ARCHITECTURE",
            shared_state={"phase": "design"},
        )

        restored = self.hsm.resume_from_history_node("sess_compat")

        self.assertIsNotNone(restored)
        self.assertEqual(self.hsm.get_current_state("sess_compat"), "PLANNING.ARCHITECTURE")
        self.assertFalse(restored["shared_state"].get("stale_detected", False))

    def test_resume_with_nonexistent_task_file_skips_delta_check(self):
        """
        Validates that delta validation is skipped gracefully when the
        task file no longer exists on disk.
        """
        nonexistent_path = os.path.join(tempfile.gettempdir(), "does_not_exist_99999.py")

        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_missing",
            checkpoint_id="cp_missing",
            agent_id="PrimaryAgent",
            state_name="EXECUTION.CODE_GEN",
            shared_state={"step": 5},
            task_id=nonexistent_path,
        )

        delta_mgr = MockDeltaManager(is_structural_change=True)
        restored = self.hsm.resume_from_history_node("sess_missing", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertFalse(restored["shared_state"].get("stale_detected", False))
        # DeltaManager should NOT have been called (file doesn't exist)
        self.assertEqual(delta_mgr.checked_paths, [])

    def test_resume_via_in_memory_history_node_with_delta_validation(self):
        """
        Validates delta validation works correctly even when restoring from
        in-memory history nodes (fast path) instead of SQLite fallback.
        """
        file_path = self._create_temp_file()
        old_timestamp = time.time() - 200

        # Save checkpoint and manually set history node (simulating in-memory path)
        self.hsm.checkpointer.save_checkpoint(
            session_id="sess_mem",
            checkpoint_id="cp_mem",
            agent_id="PrimaryAgent",
            state_name="EXECUTION.TDD_GREEN",
            shared_state={"step": 7},
            task_id=file_path,
        )

        # Set in-memory history node with old timestamp
        self.hsm.history_nodes["sess_mem"] = ("EXECUTION.TDD_GREEN", "cp_mem", old_timestamp)

        # Touch file to make it newer
        os.utime(file_path, None)

        delta_mgr = MockDeltaManager(is_structural_change=True)
        restored = self.hsm.resume_from_history_node("sess_mem", delta_manager=delta_mgr)

        self.assertIsNotNone(restored)
        self.assertTrue(restored["shared_state"].get("stale_detected"))
        self.assertEqual(self.hsm.get_current_state("sess_mem"), "EXECUTION.RE_INDEX")


if __name__ == "__main__":
    unittest.main()
