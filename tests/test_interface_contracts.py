"""
tests/test_interface_contracts.py — interface/ package contracts

Migrated from:
  - _test_interface_phase4.py: import smoke tests, CLI parser validation,
    GrafoConciergeServer and ActionHooks signature checks.
  - _test_mcp_contract.py: MCP tool registration contract and status
    component assertions (no ChromaDB residue).

All tests use the fully assembled GrafoConciergeServer with minimal mocks
(no network, no disk I/O beyond a temp SQLite database).
"""
import asyncio
import inspect
import json
import uuid
import pytest

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from core.mcp_governor import SecurityException
from interface.mcp_server import GrafoConciergeServer
from interface.cli import build_parser, COMMAND_MAP


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class _MockEmbeddingManager:
    class _tier:
        value = "FLASH"
    tier = _tier()

    def embed(self, text):
        return [0.1] * 384

    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]


class _MockVectorStore:
    def __init__(self):
        self.stored = []

    def store_embeddings_batch(self, items):
        return len(items)

    def delete(self, doc_id):
        pass

    def verify_sync(self, sqlite_ids):
        return []

    def health_check(self):
        return True

    def count(self, project_uuid=None):
        return len(self.stored)

    def reset_collection(self):
        self.stored = []
        return True

    def search(self, *args, **kwargs):
        return []


class _MockIngestionManager:
    def mine(self, project_uuid, path, auto_tag=True):
        pass

    def generate_project_context(self, project_uuid):
        return {}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """GrafoConciergeServer backed by an in-memory-like temp SQLite store."""
    import core.mcp_governor as _gov_mod
    import interface.mcp_server as _mcp_mod
    orig_db = getattr(_mcp_mod, "db_manager", None)
    orig_cp = getattr(_mcp_mod, "checkpointer", None)
    orig_gr = getattr(_mcp_mod, "graph_rag", None)
    orig_gc = getattr(_mcp_mod, "_gc", None)
    orig_gov = getattr(_mcp_mod, "governor", None)
    orig_shared_gov = getattr(_gov_mod, "_shared_governor", None)

    _gov_mod._shared_governor = None

    tmp = tmp_path_factory.mktemp("interface_contracts")
    store = SqliteStore(str(tmp / "contract.db"))
    project_uuid = str(uuid.uuid4())
    store.create_project(project_uuid, "contract-project", "dev/test")

    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=_MockVectorStore(),
        embedding_manager=_MockEmbeddingManager(),
        ingestion_manager=_MockIngestionManager(),
    )
    srv = GrafoConciergeServer(concierge=gc, janitor=None)
    yield srv

    store.close()
    _mcp_mod.db_manager = orig_db
    _mcp_mod.checkpointer = orig_cp
    _mcp_mod.graph_rag = orig_gr
    _mcp_mod._gc = orig_gc
    _mcp_mod.governor = orig_gov
    _gov_mod._shared_governor = orig_shared_gov


# ---------------------------------------------------------------------------
# 1. Import smoke tests
# ---------------------------------------------------------------------------

class TestInterfaceImports:
    def test_mcp_server_importable(self):
        from interface.mcp_server import GrafoConciergeServer as _GCS  # noqa
        assert _GCS is not None

    def test_interface_package_exports(self):
        import interface
        from interface import GrafoConciergeServer as _GCS  # noqa
        assert _GCS is not None
        assert not hasattr(interface, "ActionHooks")


# ---------------------------------------------------------------------------
# 2. GrafoConciergeServer constructor signature
# ---------------------------------------------------------------------------

class TestGrafoConciergeServerSignature:
    def test_accepts_concierge_param(self):
        params = list(inspect.signature(GrafoConciergeServer.__init__).parameters.keys())
        assert "concierge" in params

    def test_accepts_janitor_param(self):
        params = list(inspect.signature(GrafoConciergeServer.__init__).parameters.keys())
        assert "janitor" in params

    def test_no_legacy_sqlite_store_param(self):
        params = list(inspect.signature(GrafoConciergeServer.__init__).parameters.keys())
        assert "sqlite_store" not in params, "Legacy param still present!"

    def test_no_legacy_vector_store_param(self):
        params = list(inspect.signature(GrafoConciergeServer.__init__).parameters.keys())
        assert "vector_store" not in params, "Legacy param still present!"

    def test_no_legacy_embedding_manager_param(self):
        params = list(inspect.signature(GrafoConciergeServer.__init__).parameters.keys())
        assert "embedding_manager" not in params, "Legacy param still present!"


# ---------------------------------------------------------------------------
# 3. CLI parser
# ---------------------------------------------------------------------------

class TestCLIParser:
    CLI_COMMANDS = [
        "register", "mine", "search", "wakeup",
        "resume", "commit", "load", "status", "projects", "sync-vector",
    ]

    def test_all_subcommands_present(self):
        for cmd in self.CLI_COMMANDS:
            assert cmd in COMMAND_MAP, f"Missing CLI command: {cmd}"

    def test_command_count(self):
        assert len(COMMAND_MAP) == 10, (
            f"Expected 10 CLI commands, got {len(COMMAND_MAP)}"
        )

    def test_search_args_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["search", "--query", "test", "--project", "abc123"])
        assert args.command == "search"
        assert args.query == "test"
        assert args.project == "abc123"

    def test_mine_args_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["mine", "--path", "/tmp/proj", "--name", "my-project"])
        assert args.command == "mine"
        assert args.path == "/tmp/proj"
        assert args.name == "my-project"


# ---------------------------------------------------------------------------
# 5. MCP tool registration contract
# ---------------------------------------------------------------------------

class TestMCPToolRegistration:
    REQUIRED_TOOLS = [
        "concierge_register",
        "concierge_list_projects",
        "concierge_mine",
        "concierge_search",
        "concierge_commit",
        "concierge_set_state",
        "concierge_wakeup",
        "concierge_resume",
        "concierge_load",
        "concierge_status",
        "search_symbols",
        "get_implementations",
        "get_callers",
        "concierge_store_fact",
        "concierge_list_facts",
        "concierge_set_memory",
        "concierge_get_memory",
        "concierge_feedback",
        "get_full_topology",
        "delete_project",
        "update_project",
        "add_reference_wing",
        "remove_reference_wing",
        "find_similar",
        "get_trajectories",
        "count_embeddings",
        "reset_collection",
        "concierge_get_call_chain",
        "agent_save_checkpoint",
        "agent_get_checkpoint",
        "agent_list_checkpoints",
    ]

    def test_all_required_tools_registered(self, server):
        registered = list(server.mcp._tool_manager._tools.keys())
        for tool in self.REQUIRED_TOOLS:
            assert tool in registered, f"Contract broken: tool '{tool}' not registered"
        assert len(self.REQUIRED_TOOLS) == 31
        assert set(registered) == set(self.REQUIRED_TOOLS)

    def test_all_registered_tools_classified_in_governor(self, server):
        registered = set(server.mcp._tool_manager._tools.keys())
        classified = set(server.governor.TOOL_CLASSIFICATION.keys())
        unclassified = sorted(registered - classified)
        phantom = sorted(classified - registered)
        assert not unclassified, f"Registered tools missing from TOOL_CLASSIFICATION: {unclassified}"
        assert not phantom, f"Phantom tools in TOOL_CLASSIFICATION not registered on server: {phantom}"
        assert classified == registered

    def test_governor_disclosure_matrix_clean_and_valid(self, server):
        expected_states = {
            "PLANNING",
            "EXECUTION",
            "MAINTENANCE",
        }
        assert set(server.governor.TOOL_DISCLOSURE_MATRIX.keys()) == expected_states
        assert server.governor.TOOL_CLASSIFICATION["concierge_set_state"] == "LOCAL_MUTATION"
        classified = set(server.governor.TOOL_CLASSIFICATION.keys())
        valid_categories = {"READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"}
        for state_name, rules in server.governor.TOOL_DISCLOSURE_MATRIX.items():
            assert "allowed_tools" in rules, f"State '{state_name}' missing allowed_tools"
            allowed_tools = rules["allowed_tools"]
            assert allowed_tools == [], (
                f"State '{state_name}' has unexpected allowed_tools override: {allowed_tools}"
            )
            assert set(allowed_tools).issubset(classified), (
                f"State '{state_name}' references unclassified tools: {sorted(set(allowed_tools) - classified)}"
            )
            assert set(rules["allowed_categories"]).issubset(valid_categories)

    def test_governor_destructive_tools_classified_as_dangerous(self, server):
        assert server.governor.TOOL_CLASSIFICATION["delete_project"] == "DANGEROUS"
        assert server.governor.TOOL_CLASSIFICATION["reset_collection"] == "DANGEROUS"
        dangerous = {
            name
            for name, cat in server.governor.TOOL_CLASSIFICATION.items()
            if cat == "DANGEROUS"
        }
        assert dangerous == {"delete_project", "reset_collection"}

    def test_governed_call_tool_executes_and_enforces_state(self, server, monkeypatch):
        import interface.mcp_server as _mcp_mod
        from core.checkpointer import AgnosticCheckpointer
        from core.database import ConciergeDatabaseManager
        from core.graph_rag import GraphRAGEngine

        db_mgr = ConciergeDatabaseManager(str(server._gc._store._conn_mgr._db_path))
        monkeypatch.setattr(_mcp_mod, "db_manager", db_mgr)
        monkeypatch.setattr(_mcp_mod, "checkpointer", AgnosticCheckpointer(db_mgr))
        monkeypatch.setattr(_mcp_mod, "graph_rag", GraphRAGEngine(db_mgr))

        def call_governed(name: str, arguments: dict):
            return asyncio.run(server.mcp._tool_manager.call_tool(name, arguments))

        # 1. Governance enforcement: PLANNING blocks LOCAL_MUTATION tools via governed_call_tool
        # Note: governed_call_tool checks default session when session_id is not a tool param,
        # so restore sessions_state["default"] without leaking an injected key.
        had_default = "default" in server.governor.sessions_state
        orig_default = server.governor.sessions_state.get("default")
        orig_max_state = server.governor.max_state
        try:
            server.governor.set_session_state("default", "PLANNING")
            with pytest.raises(SecurityException):
                call_governed(
                    "concierge_set_memory",
                    {
                        "scope_type": "user",
                        "scope_id": "contract-user",
                        "block_label": "blocked_key",
                        "content": "should_not_write",
                    },
                )

            # 2. Transition session state to MAINTENANCE and exercise lightweight-safe tools
            server.governor.max_state = "MAINTENANCE"
            server.governor.set_session_state("default", "MAINTENANCE")
            server.governor.set_session_state("sess_contract_maint", "MAINTENANCE")
            assert server.governor.get_session_state("default") == "MAINTENANCE"

            status_res = call_governed("concierge_status", {})
            assert status_res["success"] is True

            projects_res = call_governed("concierge_list_projects", {})
            assert projects_res["success"] is True

            store_res = call_governed(
                "concierge_store_fact",
                {
                    "scope_type": "user",
                    "scope_id": "contract-user",
                    "fact_statement": "Contract test fact via governed_call_tool.",
                },
            )
            assert store_res["success"] is True

            facts_res = call_governed(
                "concierge_list_facts",
                {"scope_type": "user", "scope_id": "contract-user"},
            )
            assert facts_res["success"] is True
            assert facts_res["facts_count"] >= 1
            fact_id = facts_res["facts"][0]["id"]

            fb_res = call_governed(
                "concierge_feedback",
                {"fact_id": fact_id, "was_useful": True},
            )
            assert fb_res["success"] is True

            set_mem_res = call_governed(
                "concierge_set_memory",
                {
                    "scope_type": "user",
                    "scope_id": "contract-user",
                    "block_label": "contract_block",
                    "content": "contract_value",
                },
            )
            assert set_mem_res["success"] is True

            get_mem_res = call_governed(
                "concierge_get_memory",
                {
                    "scope_type": "user",
                    "scope_id": "contract-user",
                    "block_label": "contract_block",
                },
            )
            assert get_mem_res["success"] is True
            assert len(get_mem_res["blocks"]) == 1

            topo_res = call_governed(
                "get_full_topology",
                {"project_identifier": "contract-project"},
            )
            assert topo_res["success"] is True

            count_res = call_governed(
                "count_embeddings",
                {"project_identifier": "contract-project"},
            )
            assert count_res["success"] is True

            contract_uuid = db_mgr.read_query(
                "SELECT uuid FROM projects WHERE folder_name = 'contract-project';"
            )[0][0]
            db_mgr.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'contract_entry.py', 'MODULE', 'ACTIVE');",
                (contract_uuid,),
            )
            db_mgr.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'contract_helper.py', 'MODULE', 'ACTIVE');",
                (contract_uuid,),
            )
            entry_id = db_mgr.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = 'contract_entry.py';",
                (contract_uuid,),
            )[0][0]
            helper_id = db_mgr.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = 'contract_helper.py';",
                (contract_uuid,),
            )[0][0]
            db_mgr.write_query(
                "INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');",
                (entry_id, helper_id),
            )

            chain_res = call_governed(
                "concierge_get_call_chain",
                {
                    "start_node": "contract_entry.py",
                    "depth_limit": 2,
                    "project_identifier": "contract-project",
                },
            )
            assert isinstance(chain_res, list)
            assert chain_res == ["contract_helper.py"]

            save_cp_raw = call_governed(
                "agent_save_checkpoint",
                {
                    "agent_id": "contract_agent",
                    "session_id": "sess_contract_maint",
                    "checkpoint_id": "cp_1",
                    "state_dict": {"step": 1},
                },
            )
            save_cp_res = json.loads(save_cp_raw) if isinstance(save_cp_raw, str) else save_cp_raw
            assert save_cp_res["success"] is True

            get_cp_res = call_governed(
                "agent_get_checkpoint",
                {
                    "agent_id": "contract_agent",
                    "session_id": "sess_contract_maint",
                    "checkpoint_id": "cp_1",
                },
            )
            assert get_cp_res == {"step": 1}

            list_cp_res = call_governed(
                "agent_list_checkpoints",
                {
                    "agent_id": "contract_agent",
                    "session_id": "sess_contract_maint",
                },
            )
            assert isinstance(list_cp_res, list)
            assert len(list_cp_res) >= 1
        finally:
            server.governor.max_state = orig_max_state
            server.governor.sessions_state.pop("sess_contract_maint", None)
            if had_default:
                server.governor.sessions_state["default"] = orig_default
            else:
                server.governor.sessions_state.pop("default", None)

    def test_server_name_is_grafo_concierge(self, server):
        assert server.mcp.name == "Grafo Concierge"

    def test_status_has_no_chromadb_component(self, server):
        status = server._handle_status(project_uuid=None)
        components = status.get("components", {})
        assert "chromadb" not in components, "ChromaDB residue in status components!"

    def test_status_has_no_embedding_component(self, server):
        status = server._handle_status(project_uuid=None)
        components = status.get("components", {})
        assert "embedding" not in components, "Embedding residue in status components!"

    def test_status_has_sqlite_component(self, server):
        status = server._handle_status(project_uuid=None)
        assert "sqlite" in status.get("components", {})
        assert status["components"]["sqlite"]["status"] == "healthy"
