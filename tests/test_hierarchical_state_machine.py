"""
tests/test_hierarchical_state_machine.py — SDD-SURVIVAL-25

Comprehensive test suite for the Hierarchical State Machine (HSM) Engine.

Covers:
    - State tree topology validation (5 super-states, 14 sub-states)
    - Node resolution for qualified paths
    - Valid transitions with checkpoint persistence
    - MCPToolGovernor synchronization on transition
    - IllegalHSMTransitionError on invalid paths
    - Deep History Node (H*) recording and session resume
    - SQLite WAL fallback resume (no in-memory history)
    - Session introspection and state tree serialization
    - Conservative fallback for unknown sessions
    - Telemetry API route integration tests
"""

import json
import os
import tempfile
import time

import pytest

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from core.hsm_engine import (
    HierarchicalStateMachine,
    HSMNode,
    IllegalHSMTransitionError,
)
from core.mcp_governor import MCPToolGovernor


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def db_path(tmp_path):
    """Provides a temporary SQLite database path."""
    return str(tmp_path / "test_hsm.db")


@pytest.fixture
def db_manager(db_path):
    """Creates a ConciergeDatabaseManager with HSM-required schema."""
    manager = ConciergeDatabaseManager(db_path)
    manager.write_query(
        "CREATE TABLE IF NOT EXISTS files ("
        "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
        ");"
    )
    manager.write_query(
        "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
        "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
        "shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "PRIMARY KEY (session_id, checkpoint_id)"
        ");"
    )
    return manager


@pytest.fixture
def checkpointer(db_manager):
    """Creates an AgnosticCheckpointer backed by the test database."""
    return AgnosticCheckpointer(db_manager)


@pytest.fixture
def mcp_governor():
    """Creates an MCPToolGovernor with PLANNING default state."""
    return MCPToolGovernor(default_state="PLANNING")


@pytest.fixture
def hsm(db_manager, checkpointer, mcp_governor):
    """Creates a fully-wired HierarchicalStateMachine."""
    return HierarchicalStateMachine(db_manager, checkpointer, mcp_governor)


@pytest.fixture
def hsm_no_governor(db_manager, checkpointer):
    """Creates an HSM without MCPToolGovernor coupling."""
    return HierarchicalStateMachine(db_manager, checkpointer, mcp_governor=None)


# ── State Tree Topology Tests ──────────────────────────────────────


class TestHSMStateTree:
    """Validates the HSM state tree topology per SDD-25 Section 3.2."""

    def test_root_has_five_super_states(self, hsm):
        """ROOT should have exactly 5 super-states."""
        assert len(hsm.root.substates) == 5
        expected = {"PLANNING", "EXECUTION", "MAINTENANCE", "STALL", "SUCCESS"}
        assert set(hsm.root.substates.keys()) == expected

    def test_planning_substates(self, hsm):
        """PLANNING should have DISCOVERY, ARCHITECTURE, KANBAN_GEN."""
        planning = hsm.root.substates["PLANNING"]
        assert set(planning.substates.keys()) == {"DISCOVERY", "ARCHITECTURE", "KANBAN_GEN"}
        assert planning.category == "READ_ONLY"

    def test_execution_substates(self, hsm):
        """EXECUTION should have CODE_GEN, TDD_GREEN, REFACTORING, RE_INDEX."""
        execution = hsm.root.substates["EXECUTION"]
        assert set(execution.substates.keys()) == {"CODE_GEN", "TDD_GREEN", "REFACTORING", "RE_INDEX"}
        assert execution.category == "LOCAL_MUTATION"

    def test_maintenance_substates(self, hsm):
        """MAINTENANCE should have PURGE_CACHE, RECONCILE, RESET_DB."""
        maintenance = hsm.root.substates["MAINTENANCE"]
        assert set(maintenance.substates.keys()) == {"PURGE_CACHE", "RECONCILE", "RESET_DB"}
        assert maintenance.category == "DANGEROUS"

    def test_stall_substates(self, hsm):
        """STALL should have AWAITING_HUMAN, CONTEXT_FULL, ERROR_PAUSE."""
        stall = hsm.root.substates["STALL"]
        assert set(stall.substates.keys()) == {"AWAITING_HUMAN", "CONTEXT_FULL", "ERROR_PAUSE"}
        assert stall.category == "READ_ONLY"

    def test_success_substates(self, hsm):
        """SUCCESS should have IDLE_COMPLETE."""
        success = hsm.root.substates["SUCCESS"]
        assert set(success.substates.keys()) == {"IDLE_COMPLETE"}
        assert success.category == "READ_ONLY"

    def test_all_leaf_substates_have_correct_categories(self, hsm):
        """Every leaf sub-state should inherit its super-state's MCP category."""
        for super_state in hsm.root.substates.values():
            for sub_state in super_state.substates.values():
                assert sub_state.category == super_state.category


# ── HSMNode Tests ───────────────────────────────────────────────────


class TestHSMNode:
    """Validates HSMNode composite tree operations."""

    def test_full_path_for_root_child(self):
        """Root-level child should return its name only."""
        root = HSMNode("ROOT")
        child = root.add_substate("PLANNING")
        assert child.get_full_path() == "PLANNING"

    def test_full_path_for_nested_child(self):
        """Nested child should return SUPER.SUB path."""
        root = HSMNode("ROOT")
        parent = root.add_substate("EXECUTION")
        child = parent.add_substate("TDD_GREEN")
        assert child.get_full_path() == "EXECUTION.TDD_GREEN"

    def test_is_leaf(self):
        """Leaf nodes should return True, parent nodes should return False."""
        root = HSMNode("ROOT")
        parent = root.add_substate("PLANNING")
        leaf = parent.add_substate("DISCOVERY")
        assert leaf.is_leaf() is True
        assert parent.is_leaf() is False

    def test_parent_reference(self):
        """Child nodes should reference their parent correctly."""
        root = HSMNode("ROOT")
        parent = root.add_substate("EXECUTION")
        child = parent.add_substate("CODE_GEN")
        assert child.parent is parent
        assert parent.parent is root

    def test_repr(self):
        """HSMNode repr should show full path and category."""
        root = HSMNode("ROOT")
        parent = root.add_substate("EXECUTION", category="LOCAL_MUTATION")
        child = parent.add_substate("TDD_GREEN", category="LOCAL_MUTATION")
        assert "EXECUTION.TDD_GREEN" in repr(child)
        assert "LOCAL_MUTATION" in repr(child)


# ── Node Resolution Tests ──────────────────────────────────────────


class TestNodeResolution:
    """Validates the resolve_node path resolution algorithm."""

    def test_resolve_super_state(self, hsm):
        """Should resolve a top-level super-state by name."""
        node = hsm.resolve_node("EXECUTION")
        assert node is not None
        assert node.name == "EXECUTION"

    def test_resolve_sub_state(self, hsm):
        """Should resolve a qualified sub-state path."""
        node = hsm.resolve_node("EXECUTION.TDD_GREEN")
        assert node is not None
        assert node.name == "TDD_GREEN"
        assert node.get_full_path() == "EXECUTION.TDD_GREEN"

    def test_resolve_all_leaf_states(self, hsm):
        """Should successfully resolve every leaf sub-state in the tree."""
        all_paths = [
            "PLANNING.DISCOVERY", "PLANNING.ARCHITECTURE", "PLANNING.KANBAN_GEN",
            "EXECUTION.CODE_GEN", "EXECUTION.TDD_GREEN", "EXECUTION.REFACTORING",
            "MAINTENANCE.PURGE_CACHE", "MAINTENANCE.RECONCILE", "MAINTENANCE.RESET_DB",
            "STALL.AWAITING_HUMAN", "STALL.CONTEXT_FULL", "STALL.ERROR_PAUSE",
            "SUCCESS.IDLE_COMPLETE",
        ]
        for path in all_paths:
            node = hsm.resolve_node(path)
            assert node is not None, f"Failed to resolve: {path}"

    def test_resolve_invalid_path_returns_none(self, hsm):
        """Should return None for non-existent state paths."""
        assert hsm.resolve_node("EXECUTION.INVALID_SUBSTATE") is None
        assert hsm.resolve_node("NONEXISTENT") is None
        assert hsm.resolve_node("PLANNING.EXECUTION.TDD_GREEN") is None


# ── Transition Tests ────────────────────────────────────────────────


class TestHSMTransition:
    """Validates state transitions with checkpoint persistence."""

    def test_valid_transition_returns_true(self, hsm):
        """A valid transition should succeed and return True."""
        success = hsm.transition_to(
            session_id="sess_001",
            target_path="EXECUTION.TDD_GREEN",
            agent_id="CognitiveAgent",
            shared_state={"active_test": "test_core.py"},
        )
        assert success is True

    def test_transition_updates_active_state(self, hsm):
        """Active state should reflect the last transition."""
        hsm.transition_to("sess_001", "EXECUTION.TDD_GREEN", "PrimaryAgent", {})
        assert hsm.get_current_state("sess_001") == "EXECUTION.TDD_GREEN"

    def test_transition_syncs_mcp_governor(self, hsm, mcp_governor):
        """Transition should synchronize MCPToolGovernor with the super-state."""
        hsm.transition_to("sess_001", "EXECUTION.TDD_GREEN", "PrimaryAgent", {})
        assert mcp_governor.get_session_state("sess_001") == "EXECUTION"

    def test_transition_to_maintenance_syncs_governor(self, hsm, mcp_governor):
        """Transitioning to MAINTENANCE sub-state should sync governor."""
        hsm.transition_to("sess_001", "MAINTENANCE.PURGE_CACHE", "PrimaryAgent", {})
        assert mcp_governor.get_session_state("sess_001") == "MAINTENANCE"

    def test_transition_persists_checkpoint(self, hsm, db_manager):
        """Transition should write a checkpoint row to fsm_checkpoints."""
        hsm.transition_to(
            session_id="sess_cp",
            target_path="PLANNING.DISCOVERY",
            agent_id="PrimaryAgent",
            shared_state={"step": 1},
            task_id="test.py",
        )
        rows = db_manager.read_query(
            "SELECT state_name, task_id FROM fsm_checkpoints WHERE session_id = ?;",
            ("sess_cp",),
        )
        assert len(rows) >= 1
        assert rows[0][0] == "PLANNING.DISCOVERY"
        assert rows[0][1] == "test.py"

    def test_transition_records_history_node(self, hsm):
        """Transition should record a Deep History Node (H*) for the session."""
        hsm.transition_to("sess_h", "EXECUTION.REFACTORING", "PrimaryAgent", {"step": 3})
        assert "sess_h" in hsm.history_nodes
        full_path, checkpoint_id, timestamp = hsm.history_nodes["sess_h"]
        assert full_path == "EXECUTION.REFACTORING"
        assert checkpoint_id.startswith("cp_hsm_")
        assert isinstance(timestamp, float)

    def test_invalid_transition_raises_error(self, hsm):
        """Transitioning to an invalid path should raise IllegalHSMTransitionError."""
        with pytest.raises(IllegalHSMTransitionError, match="Invalid qualified state path"):
            hsm.transition_to("sess_001", "EXECUTION.INVALID_SUBSTATE", "PrimaryAgent", {})

    def test_multiple_transitions_update_state(self, hsm):
        """Sequential transitions should update to the latest state."""
        hsm.transition_to("sess_multi", "PLANNING.DISCOVERY", "PrimaryAgent", {})
        assert hsm.get_current_state("sess_multi") == "PLANNING.DISCOVERY"

        hsm.transition_to("sess_multi", "EXECUTION.CODE_GEN", "PrimaryAgent", {})
        assert hsm.get_current_state("sess_multi") == "EXECUTION.CODE_GEN"

        hsm.transition_to("sess_multi", "EXECUTION.TDD_GREEN", "PrimaryAgent", {})
        assert hsm.get_current_state("sess_multi") == "EXECUTION.TDD_GREEN"

    def test_transition_without_governor(self, hsm_no_governor):
        """Transition should work fine without MCPToolGovernor."""
        success = hsm_no_governor.transition_to(
            "sess_ng", "STALL.AWAITING_HUMAN", "PrimaryAgent", {}
        )
        assert success is True
        assert hsm_no_governor.get_current_state("sess_ng") == "STALL.AWAITING_HUMAN"

    def test_transition_to_super_state_directly(self, hsm):
        """Transitioning to a super-state (not leaf) should also work."""
        success = hsm.transition_to("sess_super", "EXECUTION", "PrimaryAgent", {})
        assert success is True
        assert hsm.get_current_state("sess_super") == "EXECUTION"


# ── History Node Resume Tests ───────────────────────────────────────


class TestHistoryNodeResume:
    """Validates session restoration from Deep History Nodes (H*)."""

    def test_resume_from_in_memory_history(self, hsm):
        """Should restore session from in-memory history node."""
        hsm.transition_to(
            session_id="sess_resume",
            target_path="EXECUTION.REFACTORING",
            agent_id="CognitiveAgent",
            shared_state={"refactor_step": 3},
            task_id="core/hsm_engine.py",
        )

        # Simulate restart: clear active states
        hsm.active_session_states.clear()

        restored = hsm.resume_from_history_node("sess_resume")
        assert restored is not None
        assert restored["state_name"] == "EXECUTION.REFACTORING"
        assert restored["shared_state"]["refactor_step"] == 3
        assert hsm.get_current_state("sess_resume") == "EXECUTION.REFACTORING"

    def test_resume_from_sqlite_wal_fallback(self, hsm):
        """Should restore from SQLite WAL when in-memory history is missing."""
        hsm.transition_to(
            session_id="sess_wal",
            target_path="PLANNING.ARCHITECTURE",
            agent_id="PrimaryAgent",
            shared_state={"arch_doc": "v2"},
        )

        # Simulate full restart: clear both active states and history
        hsm.active_session_states.clear()
        hsm.history_nodes.clear()

        restored = hsm.resume_from_history_node("sess_wal")
        assert restored is not None
        assert restored["state_name"] == "PLANNING.ARCHITECTURE"
        assert restored["shared_state"]["arch_doc"] == "v2"

    def test_resume_nonexistent_session_returns_none(self, hsm):
        """Should return None for a session with no history."""
        result = hsm.resume_from_history_node("nonexistent_session")
        assert result is None

    def test_resume_syncs_mcp_governor(self, hsm, mcp_governor):
        """Resume should re-synchronize MCPToolGovernor with the restored super-state."""
        hsm.transition_to("sess_gov_resume", "MAINTENANCE.RECONCILE", "PrimaryAgent", {})
        hsm.active_session_states.clear()

        hsm.resume_from_history_node("sess_gov_resume")
        assert mcp_governor.get_session_state("sess_gov_resume") == "MAINTENANCE"


# ── Session Introspection Tests ─────────────────────────────────────


class TestSessionIntrospection:
    """Validates session query and state tree serialization."""

    def test_get_current_state_unknown_session_returns_fallback(self, hsm):
        """Unknown session should return conservative fallback PLANNING.DISCOVERY."""
        assert hsm.get_current_state("unknown") == "PLANNING.DISCOVERY"

    def test_get_super_state(self, hsm):
        """get_super_state should return the parent super-state name."""
        hsm.transition_to("sess_sp", "EXECUTION.TDD_GREEN", "PrimaryAgent", {})
        assert hsm.get_super_state("sess_sp") == "EXECUTION"

    def test_get_super_state_unknown_returns_planning(self, hsm):
        """Unknown session should return PLANNING as super-state."""
        assert hsm.get_super_state("unknown") == "PLANNING"

    def test_get_all_sessions(self, hsm):
        """get_all_sessions should return a summary of all active sessions."""
        hsm.transition_to("s1", "PLANNING.DISCOVERY", "H", {})
        hsm.transition_to("s2", "EXECUTION.TDD_GREEN", "H", {})

        sessions = hsm.get_all_sessions()
        assert "s1" in sessions
        assert "s2" in sessions
        assert sessions["s1"]["current_state"] == "PLANNING.DISCOVERY"
        assert sessions["s2"]["super_state"] == "EXECUTION"
        assert sessions["s2"]["has_history_node"] is True

    def test_get_state_tree_structure(self, hsm):
        """get_state_tree should return a serializable dict of the full topology."""
        tree = hsm.get_state_tree()
        assert "PLANNING" in tree
        assert "EXECUTION" in tree
        assert "MAINTENANCE" in tree
        assert "STALL" in tree
        assert "SUCCESS" in tree

        # Validate nesting
        assert "substates" in tree["EXECUTION"]
        assert "TDD_GREEN" in tree["EXECUTION"]["substates"]
        assert tree["EXECUTION"]["category"] == "LOCAL_MUTATION"

    def test_state_tree_is_json_serializable(self, hsm):
        """State tree should be fully JSON-serializable."""
        tree = hsm.get_state_tree()
        serialized = json.dumps(tree)
        assert isinstance(serialized, str)
        assert len(serialized) > 100


# ── Telemetry API Integration Tests ─────────────────────────────────


class TestHSMTelemetryAPI:
    """Integration tests for the HSM REST endpoints in telemetry_api.py."""

    @pytest.fixture
    def api_client(self, db_manager):
        """Creates a FastAPI TestClient with injected db_manager."""
        from fastapi.testclient import TestClient
        from interface.telemetry_api import app, set_db_manager, get_db_manager

        # Reset HSM singleton for test isolation
        import interface.telemetry_api as api_module
        api_module._hsm_service_instance = None

        set_db_manager(db_manager)
        client = TestClient(app)
        yield client
        # Cleanup
        api_module._hsm_service_instance = None

    def test_get_hsm_state_unknown_session(self, api_client):
        """GET /api/hsm/state/{id} should return fallback for unknown session."""
        response = api_client.get("/api/hsm/state/unknown_sess")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "unknown_sess"
        assert data["current_full_path"] == "PLANNING.DISCOVERY"
        assert data["history_node"] is None

    def test_post_hsm_transition_success(self, api_client):
        """POST /api/hsm/transition should execute a valid transition."""
        payload = {
            "session_id": "api_sess",
            "target_path": "EXECUTION.CODE_GEN",
            "agent_id": "TestAgent",
            "shared_state": {"file": "main.py"},
        }
        response = api_client.post("/api/hsm/transition", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["saved"] is True
        assert data["new_state"] == "EXECUTION.CODE_GEN"

    def test_post_hsm_transition_invalid_path(self, api_client):
        """POST /api/hsm/transition with invalid path should return 400."""
        payload = {
            "session_id": "api_sess",
            "target_path": "INVALID.PATH",
            "agent_id": "TestAgent",
            "shared_state": {},
        }
        response = api_client.post("/api/hsm/transition", json=payload)
        assert response.status_code == 400

    def test_post_resume_after_transition(self, api_client):
        """POST /api/hsm/resume/{id} should restore a session with history."""
        # First, create a transition to establish a History Node
        api_client.post("/api/hsm/transition", json={
            "session_id": "resume_sess",
            "target_path": "EXECUTION.TDD_GREEN",
            "agent_id": "PrimaryAgent",
            "shared_state": {"test": "unit"},
        })

        response = api_client.post("/api/hsm/resume/resume_sess")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["restored_state"]["state_name"] == "EXECUTION.TDD_GREEN"

    def test_post_resume_nonexistent_returns_404(self, api_client):
        """POST /api/hsm/resume/{id} for nonexistent session should return 404."""
        response = api_client.post("/api/hsm/resume/ghost_session")
        assert response.status_code == 404

    def test_get_hsm_tree(self, api_client):
        """GET /api/hsm/tree should return the full state tree."""
        response = api_client.get("/api/hsm/tree")
        assert response.status_code == 200
        data = response.json()
        assert "state_tree" in data
        assert "PLANNING" in data["state_tree"]
        assert "EXECUTION" in data["state_tree"]

    def test_transition_then_query_state(self, api_client):
        """State query should reflect the latest transition."""
        api_client.post("/api/hsm/transition", json={
            "session_id": "query_sess",
            "target_path": "MAINTENANCE.RECONCILE",
            "agent_id": "PrimaryAgent",
            "shared_state": {},
        })

        response = api_client.get("/api/hsm/state/query_sess")
        assert response.status_code == 200
        data = response.json()
        assert data["current_full_path"] == "MAINTENANCE.RECONCILE"
        assert data["super_state"] == "MAINTENANCE"
        assert data["history_node"] is not None
