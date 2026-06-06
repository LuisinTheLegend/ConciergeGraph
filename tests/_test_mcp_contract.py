"""Teste de Contrato para as Ferramentas MCP expostas — Grafo Concierge v3.8.0"""
import sys
import os
import shutil
import uuid

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from interface.mcp_server import GrafoConciergeServer

# Mocks e caminhos temporários
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_test_contract_tmp")
os.makedirs(os.path.join(TEST_DIR, "src"), exist_ok=True)

db_path = os.path.join(TEST_DIR, "contract_test.db")
store = SqliteStore(db_path)
project_uuid = str(uuid.uuid4())
store.create_project(project_uuid, "contract-project", "dev/test")

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
    def store_embeddings_batch(self, items):
        return len(items)
    def delete(self, doc_id):
        pass
    def verify_sync(self, sqlite_ids):
        return {"orphans_removed": 0}

class MockIngestionManager:
    def mine(self, project_uuid, path, auto_tag=True):
        pass

mock_embedder = MockEmbeddingManager()
mock_vector = MockVectorStore()
mock_ingestion = MockIngestionManager()

gc = GrafoConcierge(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    ingestion_manager=mock_ingestion,
)

server = GrafoConciergeServer(
    concierge=gc,
    janitor=None,
)

# ---------------------------------------------------------------------------
# TESTES DE CONTRATO (MCP TOOLS & STACK SANITIZATION)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TESTE DE CONTRATO MCP")
print("=" * 60)

# 1. Validar as ferramentas essenciais solicitadas pelo Nexus
registered_tools = list(server.mcp._tool_manager._tools.keys())
print(f"Ferramentas registradas: {registered_tools}")

required_tools = ["search_symbols", "get_implementations", "get_callers"]
for tool_name in required_tools:
    assert tool_name in registered_tools, f"CONTRATO QUEBRADO: Ferramenta '{tool_name}' não registrada!"
    print(f"  [PASS] Ferramenta '{tool_name}' registrada com sucesso.")

# 2. Validar que resíduos do ChromaDB não estão presentes
status = server._handle_status(project_uuid=None)
components = status.get("components", {})
print(f"Componentes reportados no status: {list(components.keys())}")

assert "chromadb" not in components, "CONTRATO QUEBRADO: ChromaDB não deveria estar nos componentes de status!"
assert "embedding" not in components, "CONTRATO QUEBRADO: Embedding não deveria estar nos componentes de status!"
print("  [PASS] Asserção negativa contra 'chromadb' e 'embedding' validada com sucesso.")

# Cleanup
store.close()
shutil.rmtree(TEST_DIR)

print()
print("=" * 60)
print("TODOS OS TESTES DE CONTRATO MCP PASSARAM COM SUCESSO!")
print("=" * 60)
