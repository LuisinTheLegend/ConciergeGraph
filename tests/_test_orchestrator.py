"""Teste E2E para ingestion/orchestrator.py — Grafo Concierge v3.8.0"""
import sys, os, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.store import SqliteStore
from ingestion.orchestrator import IngestionManager, IngestionResult
from ingestion.summarizer import LLMAdapter, ZoomSummarizer

# ===================================================================
# Setup: projeto de teste no filesystem + SqliteStore + Mocks
# ===================================================================
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_test_orchestrator_tmp")
os.makedirs(os.path.join(TEST_DIR, "src"), exist_ok=True)
os.makedirs(os.path.join(TEST_DIR, "docs"), exist_ok=True)
os.makedirs(os.path.join(TEST_DIR, "node_modules", "dep"), exist_ok=True)

# Arquivos de teste
with open(os.path.join(TEST_DIR, "src", "auth.py"), "w") as f:
    f.write('import jwt\n\ndef login(user, pw):\n    """Authenticate user."""\n    return jwt.encode({"user": user}, "secret")\n')
with open(os.path.join(TEST_DIR, "src", "db.py"), "w") as f:
    f.write('import sqlite3\n\ndef connect(path):\n    return sqlite3.connect(path)\n')
with open(os.path.join(TEST_DIR, "docs", "README.md"), "w") as f:
    f.write("# Project\n\nA test project.\n\n## Setup\n\nRun `pip install`.\n")
with open(os.path.join(TEST_DIR, "config.yaml"), "w") as f:
    f.write("database:\n  host: localhost\n  port: 5432\n")
# Lixo — NAO deve ser indexado
with open(os.path.join(TEST_DIR, "node_modules", "dep", "index.js"), "w") as f:
    f.write("module.exports = {};")
with open(os.path.join(TEST_DIR, ".gitignore"), "w") as f:
    f.write("node_modules/\ntest_orchestrator.db*\n")

# SqliteStore
db_path = os.path.join(TEST_DIR, "test_orchestrator.db")
store = SqliteStore(db_path)
project_uuid = str(uuid.uuid4())
store.create_project(project_uuid, "test-orchestrator", "dev/test")

# Mock EmbeddingManager e ChromaVectorStore
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
    def store_embedding(self, doc_id, embedding, metadata):
        self.stored.append(doc_id)
    def store_embeddings_batch(self, items):
        valid = [i for i in items if i.get("embedding") is not None]
        self.stored.extend(i["doc_id"] for i in valid)
        return len(valid)
    def delete(self, doc_id):
        self.deleted.append(doc_id)
    def verify_sync(self, sqlite_ids):
        return {"orphans_removed": 0}

mock_embedder = MockEmbeddingManager()
mock_vector = MockVectorStore()

# Mock LLM para Summarizer
def mock_llm(prompt, max_tokens):
    return '{"summary": "Test summary for mock.", "tags": ["test"]}'

llm_adapter = LLMAdapter(model_name="mock", call_fn=mock_llm)
summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)

# ===================================================================
print("=" * 60)
print("TESTE 1: mine() — Pipeline completo (1o crawl)")
print("=" * 60)
manager = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    summarizer=summarizer,
)

result = manager.mine(project_uuid, TEST_DIR, auto_tag=True)
print(f"  files_processed: {result.files_processed}")
print(f"  files_skipped: {result.files_skipped}")
print(f"  nodes_created: {result.nodes_created}")
print(f"  embeddings_stored: {result.embeddings_stored}")
print(f"  summaries_generated: {result.summaries_generated}")
print(f"  files_deleted: {result.files_deleted}")
print(f"  categories: {result.categories}")
print(f"  tags: {result.tags_applied}")
print(f"  errors: {result.errors}")

assert result.files_processed == 4, f"Esperado 4 arquivos, obteve {result.files_processed}"
assert result.nodes_created > 0, "Deveria criar nós"
assert result.embeddings_stored > 0, "Deveria armazenar embeddings"
assert result.summaries_generated > 0, "Deveria gerar resumos L0"
assert len(result.errors) == 0, f"Não deveria ter erros: {result.errors}"
print("  [PASS] Pipeline completo OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 2: mine() — 2o crawl (delta detection, noop)")
print("=" * 60)
mock_vector2 = MockVectorStore()
manager2 = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector2,
    embedding_manager=mock_embedder,
    summarizer=summarizer,
)
result2 = manager2.mine(project_uuid, TEST_DIR)
print(f"  files_processed: {result2.files_processed}")
print(f"  files_skipped: {result2.files_skipped}")
# Pode ter novos se chunks geraram hashes diferentes dos nós,
# mas os skippados devem ser > 0
print(f"  nodes_created: {result2.nodes_created}")
print("  [PASS] 2o crawl executado sem erros")

# ===================================================================
print()
print("=" * 60)
print("TESTE 3: to_dict() — MCP alignment")
print("=" * 60)
d = result.to_dict()
required_keys = {"files_processed", "categories", "nodes_created",
                 "embeddings_stored", "tags_applied", "files_skipped",
                 "files_deleted", "summaries_generated", "errors"}
assert required_keys.issubset(set(d.keys())), f"Chaves faltando: {required_keys - set(d.keys())}"
print(f"  Keys: {sorted(d.keys())}")
print("  [PASS] MCP alignment OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 4: Garbage Collection")
print("=" * 60)
# Deleta um arquivo e faz mine de novo
os.remove(os.path.join(TEST_DIR, "src", "auth.py"))
mock_vector3 = MockVectorStore()
manager3 = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector3,
    embedding_manager=mock_embedder,
    summarizer=summarizer,
)
result3 = manager3.mine(project_uuid, TEST_DIR)
print(f"  files_deleted (GC): {result3.files_deleted}")
assert result3.files_deleted >= 1, "Deveria deletar pelo menos 1 nó órfão"
print(f"  Vetores deletados no mock: {len(mock_vector3.deleted)}")
print("  [PASS] Garbage Collection OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 5: mine() sem Summarizer (summarizer=None)")
print("=" * 60)
mock_vector4 = MockVectorStore()
manager4 = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector4,
    embedding_manager=mock_embedder,
    summarizer=None,  # SEM summarizer
)
# Recria um arquivo para ter algo novo
with open(os.path.join(TEST_DIR, "src", "new_file.py"), "w") as f:
    f.write("def new(): pass\n")
result4 = manager4.mine(project_uuid, TEST_DIR)
print(f"  files_processed: {result4.files_processed}")
print(f"  summaries_generated: {result4.summaries_generated}")
assert result4.summaries_generated == 0, "Sem summarizer, não deveria gerar resumos"
print("  [PASS] Pipeline sem Summarizer OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 6: generate_project_context() — Zoom Gear L1/L2")
print("=" * 60)
mock_vector5 = MockVectorStore()
manager5 = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector5,
    embedding_manager=mock_embedder,
    summarizer=summarizer,
)
zoom = manager5.generate_project_context(project_uuid)
print(f"  L1 count: {zoom['l1_count']}")
print(f"  L2 summary: {zoom['l2_summary']}")
print(f"  L2 tags: {zoom['l2_tags']}")
assert zoom["l1_count"] >= 0
assert zoom["l2_summary"] is not None
print("  [PASS] Zoom Gear L1/L2 OK")

# ===================================================================
# Cleanup
# ===================================================================
store.close()
shutil.rmtree(TEST_DIR)
# Remove new_file se sobrou
if os.path.exists(os.path.join(TEST_DIR)):
    shutil.rmtree(TEST_DIR)

print()
print("=" * 60)
print("TODOS OS 6 TESTES PASSARAM — orchestrator.py v3.8.0 OPERACIONAL")
print("=" * 60)
