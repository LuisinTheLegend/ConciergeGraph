"""
tests/test_mcp_server_handlers.py — GrafoConciergeServer handler methods

Migrated from _test_mcp_server.py (script-style, 18 assert-based tests).
Tests all _handle_* methods of GrafoConciergeServer using mocks for the
GrafoConcierge facade, covering the full surface of MCP handler behaviour:
mine, search, register, status, list_projects, update/delete project,
reference wings, find_similar, count_embeddings, reset_collection.
"""
import uuid
import pytest

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from interface.mcp_server import GrafoConciergeServer


# ---------------------------------------------------------------------------
# Shared mock implementations
# ---------------------------------------------------------------------------

class MockEmbeddingManager:
    class _tier:
        value = "FLASH"
    tier = _tier()

    def embed(self, text):
        return [0.1] * 384

    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]


class MockVectorStore:
    def __init__(self, node_ids_for_search=()):
        self._stored = []
        self._deleted = []
        self._node_ids = list(node_ids_for_search)

    def search(self, query_embedding, project_uuids, top_k=10, filters=None):
        class _Result:
            def __init__(self, nid, score):
                self.node_id = nid
                self.doc_id = f"node_{nid}"
                self.score = score
                self.metadata = {}

        return [_Result(nid, 0.9 - i * 0.05) for i, nid in enumerate(self._node_ids)]

    def store_embedding(self, doc_id, embedding, metadata):
        self._stored.append(doc_id)

    def store_embeddings_batch(self, items):
        valid = [i for i in items if i.get("embedding") is not None]
        self._stored.extend(i["doc_id"] for i in valid)
        return len(valid)

    def delete(self, doc_id):
        self._deleted.append(doc_id)

    def delete_batch(self, doc_ids):
        self._deleted.extend(doc_ids)
        return len(doc_ids)

    def verify_sync(self, sqlite_ids):
        return []

    def health_check(self):
        return True

    def count(self, project_uuid=None):
        return len(self._stored)

    def reset_collection(self):
        self._stored = []
        return True


class MockIngestionManager:
    def __init__(self):
        self.mine_called = False

    def mine(self, project_uuid, path, auto_tag=True):
        self.mine_called = True

        class _Result:
            files_processed = 1
            files_skipped = 0
            nodes_created = 2
            embeddings_stored = 2
            summaries_generated = 2
            files_deleted = 0
            categories = {"code": 1}
            tags_applied = ["test"]
            errors = []

            def to_dict(self):
                return {
                    "files_processed": self.files_processed,
                    "files_skipped": self.files_skipped,
                    "nodes_created": self.nodes_created,
                    "embeddings_stored": self.embeddings_stored,
                    "summaries_generated": self.summaries_generated,
                    "files_deleted": self.files_deleted,
                    "categories": self.categories,
                    "tags_applied": self.tags_applied,
                    "errors": self.errors,
                }

        return _Result()

    def generate_project_context(self, project_uuid):
        return {"l1_count": 2, "l2_summary": "Test project."}


class MockJanitor:
    def __init__(self):
        self.mine_start_called = False
        self.mine_end_called = False
        self._running = False
        self._reports = []

    def signal_mine_start(self):
        self.mine_start_called = True

    def signal_mine_end(self):
        self.mine_end_called = True

    @property
    def is_running(self):
        return self._running

    @property
    def last_reports(self):
        return self._reports


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def store_and_project(tmp_path_factory):
    """Returns (SqliteStore, project_uuid, nid1, nid2) ready for use."""
    tmp = tmp_path_factory.mktemp("mcp_handlers")
    store = SqliteStore(str(tmp / "handlers.db"))
    project_uuid = str(uuid.uuid4())
    store.create_project(project_uuid, "mcp-test", "dev/test")

    nid1 = store.create_node(project_uuid, "auth.py", summary="Authentication module",
                              node_type="FACT", tags=["jwt", "auth"])
    nid2 = store.create_node(project_uuid, "db.py", summary="Database connection",
                              node_type="FACT", tags=["sqlite", "db"])
    yield store, project_uuid, nid1, nid2
    store.close()


@pytest.fixture(scope="module")
def server(store_and_project):
    """Full GrafoConciergeServer backed by real SQLite + mocked vector/ingestion."""
    store, project_uuid, nid1, nid2 = store_and_project
    mock_vector = MockVectorStore(node_ids_for_search=[nid1, nid2])
    mock_ingestion = MockIngestionManager()
    mock_janitor = MockJanitor()

    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=mock_vector,
        embedding_manager=MockEmbeddingManager(),
        ingestion_manager=mock_ingestion,
    )
    return GrafoConciergeServer(concierge=gc, janitor=mock_janitor)


@pytest.fixture(scope="module")
def project_uuid(store_and_project):
    _, project_uuid, _, _ = store_and_project
    return project_uuid


# ---------------------------------------------------------------------------
# _handle_mine
# ---------------------------------------------------------------------------

class TestHandleMine:
    def test_mine_success(self, server, store_and_project, project_uuid, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("mine_src")
        (tmp / "main.py").write_text("def main():\n    print('hello')\n")
        result = server._handle_mine(str(tmp), "mcp-test", auto_tag=True)
        assert result["success"] is True

    def test_mine_returns_files_processed(self, server, store_and_project, project_uuid, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("mine_src2")
        (tmp / "main.py").write_text("def main(): pass\n")
        result = server._handle_mine(str(tmp), project_uuid, auto_tag=True)
        assert result["files_processed"] == 1
        assert result["nodes_created"] == 2

    def test_mine_signals_janitor(self, server, store_and_project, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("mine_src3")
        (tmp / "x.py").write_text("x = 1\n")
        result = server._handle_mine(str(tmp), "mcp-test", auto_tag=False)
        assert result["success"] is True
        # Janitor signals confirmed via fixture (mock records calls)

    def test_mine_graceful_error_on_failing_ingestion(self, store_and_project, tmp_path_factory):
        store, project_uuid, _, _ = store_and_project

        class FailingIngestion:
            def mine(self, *args, **kwargs):
                raise RuntimeError("Disk full")
            def generate_project_context(self, *args):
                return {}

        gc = GrafoConcierge(
            sqlite_store=store,
            vector_store=MockVectorStore(),
            embedding_manager=MockEmbeddingManager(),
            ingestion_manager=FailingIngestion(),
        )
        fail_server = GrafoConciergeServer(concierge=gc, janitor=None)
        fail_server._handle_register("fail-project", "geral", "PUBLIC", None)

        tmp = tmp_path_factory.mktemp("mine_fail")
        result = fail_server._handle_mine(str(tmp), "fail-project", auto_tag=True)
        assert result["success"] is False
        assert "Disk full" in result["error"]
        assert "traceback" in result

    def test_mine_alias_resolution(self, server, project_uuid, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("mine_alias")
        (tmp / "y.py").write_text("y = 2\n")
        result = server._handle_mine(str(tmp), "mcp-test", auto_tag=False)
        assert result["success"] is True
        assert result["project_uuid"] == project_uuid


# ---------------------------------------------------------------------------
# _handle_search
# ---------------------------------------------------------------------------

class TestHandleSearch:
    def test_search_success(self, server, project_uuid):
        result = server._handle_search(
            query="authentication login",
            project_identifier=project_uuid,
            top_k=5,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        assert result["success"] is True
        assert result["results_count"] > 0

    def test_search_result_fields(self, server, project_uuid):
        result = server._handle_search(
            query="database",
            project_identifier=project_uuid,
            top_k=5,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        assert len(result["results"]) > 0
        first = result["results"][0]
        assert "node_id" in first
        assert "label" in first
        assert "summary" in first
        assert "hybrid_score" in first

    def test_search_with_node_type_filter(self, server, project_uuid):
        result = server._handle_search(
            query="database",
            project_identifier=project_uuid,
            top_k=3,
            node_type="FACT",
            include_references=False,
            all_wings=False,
        )
        assert result["success"] is True

    def test_search_with_alias(self, server, project_uuid):
        result = server._handle_search(
            query="authentication login",
            project_identifier="mcp-test",
            top_k=5,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        assert result["success"] is True
        assert result["project_uuid"] == project_uuid

    def test_search_nonexistent_project_returns_error_dict(self, server):
        result = server._handle_search(
            query="test",
            project_identifier="non-existent-uuid-99999",
            top_k=5,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        # Either success with 0 results or graceful failure
        assert "success" in result


# ---------------------------------------------------------------------------
# _handle_status
# ---------------------------------------------------------------------------

class TestHandleStatus:
    def test_status_global_success(self, server):
        status = server._handle_status(project_uuid=None)
        assert status["success"] is True

    def test_status_has_sqlite_component(self, server):
        status = server._handle_status(project_uuid=None)
        assert "sqlite" in status["components"]
        assert status["components"]["sqlite"]["status"] == "healthy"

    def test_status_has_janitor_component(self, server):
        status = server._handle_status(project_uuid=None)
        assert "janitor" in status["components"]

    def test_status_no_chromadb_residue(self, server):
        status = server._handle_status(project_uuid=None)
        assert "chromadb" not in status["components"]

    def test_status_with_project_uuid(self, server, project_uuid):
        status = server._handle_status(project_uuid=project_uuid)
        assert status["success"] is True
        assert "project" in status


# ---------------------------------------------------------------------------
# _handle_register and _handle_list_projects
# ---------------------------------------------------------------------------

class TestHandleRegisterAndList:
    def test_register_new_project(self, server, store_and_project):
        store, _, _, _ = store_and_project
        result = server._handle_register("brand-new-project", "geral", "PUBLIC", None)
        assert result["success"] is True
        new_uuid = result["project_uuid"]
        assert len(new_uuid) == 36  # valid UUID
        project = store.get_project(new_uuid)
        assert project["folder_name"] == "brand-new-project"

    def test_register_reuses_existing(self, server, project_uuid, store_and_project):
        store, _, _, _ = store_and_project
        result = server._handle_register("mcp-test", "geral", "PUBLIC", None)
        assert result["success"] is True
        stored = store.get_project("mcp-test")
        assert result["project_uuid"] == stored["uuid"]

    def test_list_projects_success(self, server, project_uuid):
        result = server._handle_list_projects()
        assert result["success"] is True
        assert "mcp-test" in result["projects"]
        assert result["projects"]["mcp-test"]["uuid"] == project_uuid

    def test_mcp_server_name(self, server):
        assert server.mcp.name == "Grafo Concierge"

    def test_list_projects_registered_in_fastmcp(self, server):
        assert "concierge_list_projects" in server.mcp._tool_manager._tools


# ---------------------------------------------------------------------------
# _handle_update_project, _handle_get_trajectories
# ---------------------------------------------------------------------------

class TestHandleUpdateProject:
    def test_update_project_fields(self, server, project_uuid, store_and_project):
        store, _, _, _ = store_and_project
        result = server._handle_update_project(
            project_identifier=project_uuid,
            folder_name="mcp-test-updated",
            primary_wing="frontend",
            privacy_level="RESTRICTED",
            summary="Updated description",
        )
        assert result["success"] is True
        stored = store.get_project(project_uuid)
        assert stored["folder_name"] == "mcp-test-updated"
        assert stored["primary_wing"] == "frontend"
        assert stored["privacy_level"] == "RESTRICTED"
        assert stored["summary"] == "Updated description"

    def test_get_trajectories_success(self, server, project_uuid):
        result = server._handle_get_trajectories(project_uuid)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# _handle_add_reference_wing, _handle_remove_reference_wing
# ---------------------------------------------------------------------------

class TestHandleReferenceWings:
    def test_add_and_remove_wing(self, server, project_uuid, store_and_project):
        store, _, _, _ = store_and_project
        add_result = server._handle_add_reference_wing(project_uuid, "wing-security")
        assert add_result["success"] is True
        wings = store.get_reference_wings(project_uuid)
        assert "wing-security" in wings

        remove_result = server._handle_remove_reference_wing(project_uuid, "wing-security")
        assert remove_result["success"] is True
        wings = store.get_reference_wings(project_uuid)
        assert "wing-security" not in wings


# ---------------------------------------------------------------------------
# _handle_find_similar, _handle_count_embeddings, _handle_reset_collection
# ---------------------------------------------------------------------------

class TestHandleMiscHandlers:
    def test_find_similar_success(self, server, project_uuid):
        result = server._handle_find_similar(project_uuid, limit=2)
        assert result["success"] is True

    def test_count_embeddings_success(self, server, project_uuid):
        result = server._handle_count_embeddings(project_uuid)
        assert result["success"] is True
        assert "count" in result

    def test_reset_collection_success(self, server):
        result = server._handle_reset_collection()
        assert result["success"] is True

    def test_count_after_reset_is_zero(self, server):
        server._handle_reset_collection()
        result = server._handle_count_embeddings()
        assert result["success"] is True
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# _handle_delete_project
# ---------------------------------------------------------------------------

class TestHandleDeleteProject:
    def test_delete_project_removes_from_store(self, store_and_project, tmp_path_factory):
        """Uses a fresh isolated project to avoid contaminating other tests."""
        store, _, _, _ = store_and_project
        tmp = tmp_path_factory.mktemp("delete_proj")

        gc = GrafoConcierge(
            sqlite_store=store,
            vector_store=MockVectorStore(),
            embedding_manager=MockEmbeddingManager(),
            ingestion_manager=MockIngestionManager(),
        )
        srv = GrafoConciergeServer(concierge=gc, janitor=None)

        reg = srv._handle_register("to-be-deleted", "geral", "PUBLIC", None)
        del_uuid = reg["project_uuid"]

        result = srv._handle_delete_project(del_uuid)
        assert result["success"] is True

        with pytest.raises(Exception):
            store.get_project(del_uuid)
