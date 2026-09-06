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
import inspect
import uuid
import pytest

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from interface.mcp_server import GrafoConciergeServer
from interface.action_hooks import ActionHooks
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


# ---------------------------------------------------------------------------
# 1. Import smoke tests
# ---------------------------------------------------------------------------

class TestInterfaceImports:
    def test_mcp_server_importable(self):
        from interface.mcp_server import GrafoConciergeServer as _GCS  # noqa
        assert _GCS is not None

    def test_action_hooks_importable(self):
        from interface.action_hooks import ActionHooks as _AH  # noqa
        assert _AH is not None

    def test_interface_package_exports(self):
        from interface import GrafoConciergeServer as _GCS, ActionHooks as _AH  # noqa
        assert _GCS is not None
        assert _AH is not None


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
# 3. ActionHooks signature and lifecycle methods
# ---------------------------------------------------------------------------

class TestActionHooksSignature:
    def test_accepts_concierge_param(self):
        params = list(inspect.signature(ActionHooks.__init__).parameters.keys())
        assert "concierge" in params

    def test_accepts_revisor_param(self):
        params = list(inspect.signature(ActionHooks.__init__).parameters.keys())
        assert "revisor" in params

    def test_has_on_planning_method(self):
        assert hasattr(ActionHooks, "on_planning")

    def test_has_on_execution_method(self):
        assert hasattr(ActionHooks, "on_execution")

    def test_has_on_done_method(self):
        assert hasattr(ActionHooks, "on_done")


# ---------------------------------------------------------------------------
# 4. CLI parser
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
        "concierge_mine",
        "concierge_search",
        "concierge_commit",
        "concierge_wakeup",
        "concierge_resume",
        "concierge_load",
        "concierge_status",
        "concierge_list_projects",
        "concierge_register",
        "search_symbols",
        "get_implementations",
        "get_callers",
        "concierge_store_fact",
        "concierge_list_facts",
        "concierge_set_memory",
        "concierge_get_memory",
        "concierge_feedback",
    ]

    def test_all_required_tools_registered(self, server):
        registered = list(server.mcp._tool_manager._tools.keys())
        for tool in self.REQUIRED_TOOLS:
            assert tool in registered, f"Contract broken: tool '{tool}' not registered"

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
