"""Teste de Integração para Indexação AST & Ferramentas MCP — Grafo Concierge v3.8.0"""
import sys
import os
import shutil
import uuid
import json

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from ingestion.orchestrator import IngestionManager
from ingestion.summarizer import LLMAdapter, ZoomSummarizer

# Configuração de caminhos temporários
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_test_ast_indexing_tmp")
os.makedirs(os.path.join(TEST_DIR, "src"), exist_ok=True)

# 1. CRIAR ARQUIVOS DE TESTE COM DEPENDÊNCIAS DE CHAMADA
py_a = """def func_a(x):
    return x + 1
"""

py_b = """from src.file_a import func_a

class MyClass:
    def method_b(self, y):
        return func_a(y) * 2

def func_b(z):
    obj = MyClass()
    return obj.method_b(z)
"""

with open(os.path.join(TEST_DIR, "src", "file_a.py"), "w", encoding="utf-8") as f:
    f.write(py_a)

with open(os.path.join(TEST_DIR, "src", "file_b.py"), "w", encoding="utf-8") as f:
    f.write(py_b)

# 2. INICIALIZAR SUBSISTEMAS (SQLite + Mock Vector/Embeddings/Summarizer)
db_path = os.path.join(TEST_DIR, "test_ast.db")
store = SqliteStore(db_path)
project_uuid = str(uuid.uuid4())
store.create_project(project_uuid, "test-ast", "dev/test")

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
        valid = [i for i in items if i.get("embedding") is not None]
        self.stored.extend(i["doc_id"] for i in valid)
        return len(valid)
    def delete(self, doc_id):
        pass
    def verify_sync(self, sqlite_ids):
        return {"orphans_removed": 0}

mock_embedder = MockEmbeddingManager()
mock_vector = MockVectorStore()

# LLM Mock simplificado para resumos
def mock_llm(prompt, max_tokens):
    return '{"summary": "Mock summary", "tags": ["mock"]}'

llm_adapter = LLMAdapter(model_name="mock", call_fn=mock_llm)
summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)

manager = IngestionManager(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    summarizer=summarizer,
)

# 3. EXECUTAR A INGESTÃO DO PROJETO COM O PARSER AST
print("=" * 60)
print("TESTE 1: Ingestão de código e parsing AST")
print("=" * 60)

result = manager.mine(project_uuid, TEST_DIR, auto_tag=True)
print(f"  Arquivos processados: {result.files_processed}")
print(f"  Nós criados: {result.nodes_created}")
print(f"  Erros: {result.errors}")

assert result.files_processed >= 2, "Deveria processar pelo menos 2 arquivos."
assert len(result.errors) == 0, f"Erros ocorridos: {result.errors}"
print("  [PASS] Ingestão concluída com sucesso.")

# 4. VERIFICAR SE NÓS E CONTEÚDOS FORAM CORRETAMENTE SALVOS NO SQLITE
print()
print("=" * 60)
print("TESTE 2: Validação de Nós, Tipos e Conteúdo (Implementation)")
print("=" * 60)

nodes = store.get_nodes_by_project(project_uuid)
print(f"  Total de nós no SQLite: {len(nodes)}")

# Categoriza nós para verificação
types_found = [n["type"] for n in nodes]
labels_found = [n["label"] for n in nodes]
print(f"  Tipos de nós encontrados: {types_found}")
print(f"  Labels encontrados: {labels_found}")

# Deve conter classes, funções, métodos e módulos
assert "class" in types_found, "Deveria ter nó do tipo class"
assert "function" in types_found, "Deveria ter nó do tipo function"
assert "method" in types_found, "Deveria ter nó do tipo method"
assert "module" in types_found, "Deveria ter nó do tipo module"

# Verifica se o código (content) está salvo
func_a_node = [n for n in nodes if "func_a" in n["label"]][0]
assert func_a_node["content"] is not None, "O nó de func_a deveria ter código armazenado."
assert "def func_a" in func_a_node["content"], "O conteúdo do nó deveria conter o código original."
print("  [PASS] Nós e conteúdos AST validados com sucesso.")

# 5. VERIFICAR DETECÇÃO DE ARESTAS DE CHAMADAS (CALL DEPENDENCIES)
print()
print("=" * 60)
print("TESTE 3: Validação de Arestas de Chamadas (calls)")
print("=" * 60)

method_b_node = [n for n in nodes if "method_b" in n["label"]][0]
func_b_node = [n for n in nodes if "func_b" in n["label"]][0]
myclass_node = [n for n in nodes if "MyClass" in n["label"] and n["type"] == "class"][0]

# method_b chama func_a
edges_from_b = store.get_edges_from(method_b_node["id"])
print(f"  Arestas saindo de method_b (ID={method_b_node['id']}): {edges_from_b}")
calls_from_b = [e for e in edges_from_b if e["relation_type"] == "calls"]
assert len(calls_from_b) >= 1, "method_b deveria ter uma aresta 'calls'"
assert calls_from_b[0]["target_id"] == func_a_node["id"], "method_b deveria chamar func_a"

# func_b chama MyClass
edges_from_func_b = store.get_edges_from(func_b_node["id"])
print(f"  Arestas saindo de func_b (ID={func_b_node['id']}): {edges_from_func_b}")
calls_from_func_b = [e for e in edges_from_func_b if e["relation_type"] == "calls"]
assert len(calls_from_func_b) >= 1, "func_b deveria chamar MyClass"
assert calls_from_func_b[0]["target_id"] == myclass_node["id"], "func_b deveria apontar para MyClass"

print("  [PASS] Arestas de dependências de chamadas AST mapeadas com sucesso.")

# 6. VERIFICAR NOVAS MÉTODOS / FERRAMENTAS MCP EXPOSTAS NA FACHADA
print()
print("=" * 60)
print("TESTE 4: Ferramentas de Navegação MCP / Fachada Central")
print("=" * 60)

gc = GrafoConcierge(
    sqlite_store=store,
    vector_store=mock_vector,
    embedding_manager=mock_embedder,
    ingestion_manager=manager,
)

# Teste 4a: search_symbols
search_results = gc.search_symbols("MyClass", project_uuid)
print(f"  search_symbols('MyClass') resultados: {search_results}")
assert len(search_results) >= 1, "Deveria encontrar o símbolo 'MyClass'"
assert search_results[0]["type"] == "class", "O símbolo encontrado deveria ser do tipo class"

# Teste 4b: get_implementations
impl = gc.get_implementations(func_a_node["id"])
print(f"  get_implementations(func_a) content: {impl.get('content')}")
assert impl["id"] == func_a_node["id"]
assert "def func_a" in impl["content"], "Deveria retornar o código de func_a"

# Teste 4c: get_callers
callers = gc.get_callers(func_a_node["id"])
print(f"  get_callers(func_a): {callers}")
assert len(callers) >= 1, "Deveria retornar pelo menos um chamador para func_a"
assert callers[0]["id"] == method_b_node["id"], "O chamador de func_a deveria ser method_b"

print("  [PASS] Ferramentas MCP search_symbols, get_implementations e get_callers validadas na Fachada.")

# 7. CLEANUP
store.close()
shutil.rmtree(TEST_DIR)

print()
print("=" * 60)
print("TODOS OS TESTES DE INDEXAÇÃO AST PASSARAM COM SUCESSO!")
print("=" * 60)
