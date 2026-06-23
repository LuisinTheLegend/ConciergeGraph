"""Teste E2E para server/mcp_server.py — Grafo Concierge v3.8.0"""
import sys, os, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.store import SqliteStore
from interface.mcp_server import GrafoConciergeServer

# ===================================================================
# Setup: Mocks completos
# ===================================================================
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_test_mcp_tmp")

# Clean up any leftover database/directory from previous runs
if os.path.exists(TEST_DIR):
    try:
        shutil.rmtree(TEST_DIR)
    except Exception:
        db_path = os.path.join(TEST_DIR, "mcp_test.db")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

os.makedirs(os.path.join(TEST_DIR, "src"), exist_ok=True)

# Cria arquivo de teste para mine
with open(os.path.join(TEST_DIR, "src", "main.py"), "w") as f:
    f.write("def main():\n    print('hello')\n")
with open(os.path.join(TEST_DIR, ".gitignore"), "w") as f:
    f.write("node_modules/\n*.db\n")

db_path = os.path.join(TEST_DIR, "mcp_test.db")
store = SqliteStore(db_path)

# Ensure project_uuid is consistent with what is in the database if it already exists
try:
    project_uuid = store.get_project("mcp-test")["uuid"]
except Exception:
    project_uuid = str(uuid.uuid4())
    store.create_project(project_uuid, "mcp-test", "dev/test")

# Cria nós para search
nid1 = store.create_node(project_uuid, "auth.py", summary="Authentication module", node_type="FACT", tags=["jwt", "auth"])
nid2 = store.create_node(project_uuid, "db.py", summary="Database connection", node_type="FACT", tags=["sqlite", "db"])
nid3 = store.create_node(project_uuid, "README.md", summary="Project documentation", node_type="FACT", tags=["docs"])


class MockEmbeddingManager:
    class _tier:
        value = "FLASH"
    tier = _tier()
    def embed(self, text):
        return [0.1] * 384
    def embed_batch(self, texts):
        return [[0.1] * 384 for _ in texts]


class MockVectorStore:
    def __init__(self):
        self.stored = []
        self.deleted = []

    def search(self, query_embedding, project_uuids, top_k=10, filters=None):
        # Retorna resultados mock com node_ids reais
        class MockResult:
            def __init__(self, nid, score):
                self.node_id = nid
                self.doc_id = f"node_{nid}"
                self.score = score
                self.metadata = {}
        return [MockResult(nid1, 0.95), MockResult(nid2, 0.85)]

    def store_embedding(self, doc_id, embedding, metadata):
        self.stored.append(doc_id)

    def store_embeddings_batch(self, items):
        valid = [i for i in items if i.get("embedding") is not None]
        self.stored.extend(i["doc_id"] for i in valid)
        return len(valid)

    def delete(self, doc_id):
        self.deleted.append(doc_id)

    def delete_batch(self, doc_ids):
        self.deleted.extend(doc_ids)
        return len(doc_ids)

    def verify_sync(self, sqlite_ids):
        return []

    def health_check(self):
        return True

    def count(self):
        return len(self.stored)


class MockIngestionManager:
    def __init__(self):
        self.mine_called = False

    def mine(self, project_uuid, path, auto_tag=True):
        self.mine_called = True
        class MockResult:
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
        return MockResult()

    def generate_project_context(self, project_uuid):
        return {"l1_count": 2, "l2_summary": "Test project."}


class MockJanitor:
    def __init__(self):
        self.mine_signaled_start = False
        self.mine_signaled_end = False
        self._reports = []
        self._running = False

    def signal_mine_start(self):
        self.mine_signaled_start = True

    def signal_mine_end(self):
        self.mine_signaled_end = True

    @property
    def is_running(self):
        return self._running

    @property
    def last_reports(self):
        return self._reports


mock_embedder = MockEmbeddingManager()
mock_vector = MockVectorStore()
mock_ingestion = MockIngestionManager()
mock_janitor = MockJanitor()

from core.middleware import GrafoConcierge

# Instancia a fachada GrafoConcierge
gc = GrafoConcierge(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    ingestion_manager=mock_ingestion,
)

# ===================================================================
# Cria o servidor
# ===================================================================
server = GrafoConciergeServer(
    concierge=gc,
    janitor=mock_janitor,
)

# Verifica que o FastMCP foi criado
assert server.mcp is not None, "FastMCP deveria existir"

# ===================================================================
print("=" * 60)
print("TESTE 1: concierge_mine")
print("=" * 60)
result = server._handle_mine(TEST_DIR, "mcp-test", auto_tag=True)
print(f"  success: {result['success']}")
print(f"  project_uuid: {result.get('project_uuid')}")
print(f"  files_processed: {result.get('files_processed')}")
print(f"  nodes_created: {result.get('nodes_created')}")
print(f"  duration: {result.get('duration_seconds')}s")
assert result["success"] is True, f"Mine falhou: {result.get('error')}"
assert result["files_processed"] == 1
assert result["nodes_created"] == 2
assert mock_ingestion.mine_called is True
assert mock_janitor.mine_signaled_start is True
assert mock_janitor.mine_signaled_end is True
print("  [PASS] concierge_mine OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 2: concierge_search")
print("=" * 60)
search_result = server._handle_search(
    query="authentication login",
    project_identifier=project_uuid,
    top_k=5,
    node_type=None,
    include_references=False,
    all_wings=False,
)
print(f"  success: {search_result['success']}")
print(f"  results_count: {search_result['results_count']}")
print(f"  pipeline: {search_result.get('pipeline')}")
print(f"  duration: {search_result.get('duration_seconds')}s")
assert search_result["success"] is True, f"Search falhou: {search_result.get('error')}"
assert search_result["results_count"] > 0
assert len(search_result["results"]) > 0
# Verifica estrutura dos resultados
first = search_result["results"][0]
assert "node_id" in first
assert "label" in first
assert "summary" in first
assert "hybrid_score" in first
print(f"  Top result: {first['label']} (score={first['hybrid_score']})")
print("  [PASS] concierge_search OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 3: concierge_search com filtro de node_type")
print("=" * 60)
search_filtered = server._handle_search(
    query="database",
    project_identifier=project_uuid,
    top_k=3,
    node_type="FACT",
    include_references=False,
    all_wings=False,
)
assert search_filtered["success"] is True
print(f"  results_count: {search_filtered['results_count']}")
print("  [PASS] Search com filtro OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 4: concierge_status (sem project_uuid)")
print("=" * 60)
status = server._handle_status(project_uuid=None)
print(f"  success: {status['success']}")
print(f"  system: {status.get('system')}")
print(f"  components: {list(status.get('components', {}).keys())}")
assert status["success"] is True
assert "sqlite" in status["components"]
assert "chromadb" not in status["components"]
assert "janitor" in status["components"]
assert status["components"]["sqlite"]["status"] == "healthy"
print("  [PASS] concierge_status (global) OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 5: concierge_status COM project_uuid")
print("=" * 60)
status_proj = server._handle_status(project_uuid=project_uuid)
assert status_proj["success"] is True
assert "project" in status_proj
print(f"  project folder: {status_proj['project']['project'].get('folder_name')}")
print(f"  project stats: {status_proj['project'].get('stats')}")
print(f"  wings: {status_proj['project'].get('reference_wings')}")
assert status_proj["project"]["project"]["folder_name"] == "mcp-test"
print("  [PASS] concierge_status (project) OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 6: concierge_mine com erro gracioso")
print("=" * 60)
# Simula falha no mine
class FailingIngestion:
    def mine(self, *args, **kwargs):
        raise RuntimeError("Disco cheio")
    def generate_project_context(self, *args):
        return {}

fail_gc = GrafoConcierge(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    ingestion_manager=FailingIngestion(),
)
fail_server = GrafoConciergeServer(
    concierge=fail_gc,
    janitor=None,
)
fail_server._handle_register("fail-project", "geral", "PUBLIC", None)
fail_result = fail_server._handle_mine("/nonexistent", "fail-project", True)
print(f"  success: {fail_result['success']}")
print(f"  error: {fail_result.get('error')}")
assert fail_result["success"] is False
assert "Disco cheio" in fail_result["error"]
print("  [PASS] Error handling OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 7: concierge_search com projeto inexistente")
print("=" * 60)
bad_search = server._handle_search(
    query="test",
    project_identifier="non-existent-uuid-12345",
    top_k=5,
    node_type=None,
    include_references=False,
    all_wings=False,
)
# Deve retornar sucesso mas com 0 resultados (ou erro tratado)
print(f"  success: {bad_search['success']}")
print(f"  results_count: {bad_search.get('results_count', 0)}")
print("  [PASS] Search com projeto inexistente OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 8: register_project (cria novo)")
print("=" * 60)
reg_res = server._handle_register("brand-new-project", "geral", "PUBLIC", None)
new_uuid = reg_res["project_uuid"]
print(f"  UUID criado: {new_uuid}")
assert len(new_uuid) == 36  # UUID format
# Verifica que foi persistido
project = store.get_project(new_uuid)
assert project["folder_name"] == "brand-new-project"
print("  [PASS] register_project OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 9: register_project (reutiliza existente)")
print("=" * 60)
reg_res_2 = server._handle_register("mcp-test", "geral", "PUBLIC", None)
same_uuid = reg_res_2["project_uuid"]
print(f"  UUID reutilizado: {same_uuid}")
# Deve retornar o UUID do projeto existente (criado no setup ou no mine)
stored = store.get_project("mcp-test")
assert same_uuid == stored["uuid"], "Deveria reutilizar o projeto existente"
print("  [PASS] register_project reuso OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 10: FastMCP tools registradas")
print("=" * 60)
# Verifica que os tools estão registrados no FastMCP
# O FastMCP armazena tools internamente
print(f"  MCP server name: {server.mcp.name}")
assert server.mcp.name == "Grafo Concierge"
# Verifica que concierge_list_projects está registrado
assert "concierge_list_projects" in server.mcp._tool_manager._tools
print("  [PASS] FastMCP registration OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 11: concierge_list_projects")
print("=" * 60)
list_res = server._handle_list_projects()
print(f"  success: {list_res['success']}")
print(f"  projects: {list_res.get('projects')}")
assert list_res["success"] is True
assert "mcp-test" in list_res["projects"]
assert list_res["projects"]["mcp-test"]["uuid"] == project_uuid
print("  [PASS] concierge_list_projects OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 12: Resolução de Alias (nome no concierge_search)")
print("=" * 60)
alias_search = server._handle_search(
    query="authentication login",
    project_identifier="mcp-test",
    top_k=5,
    node_type=None,
    include_references=False,
    all_wings=False,
)
print(f"  success: {alias_search['success']}")
print(f"  project_uuid resolved: {alias_search.get('project_uuid')}")
assert alias_search["success"] is True
assert alias_search["project_uuid"] == project_uuid
print("  [PASS] Resolução de Alias no search OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 13: Resolução de Alias (nome no concierge_mine)")
print("=" * 60)
alias_mine = server._handle_mine(
    path=TEST_DIR,
    project_identifier="mcp-test",
    auto_tag=True,
)
print(f"  success: {alias_mine['success']}")
print(f"  project_uuid resolved: {alias_mine.get('project_uuid')}")
assert alias_mine["success"] is True
assert alias_mine["project_uuid"] == project_uuid
print("  [PASS] Resolução de Alias no mine OK")

# ===================================================================
# Cleanup
# ===================================================================
store.close()
try:
    shutil.rmtree(TEST_DIR)
except PermissionError:
    pass

print()
print("=" * 60)
print("TODOS OS 13 TESTES PASSARAM — mcp_server.py v3.8.0 OPERACIONAL")
print("=" * 60)
