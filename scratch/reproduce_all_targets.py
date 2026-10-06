"""
scratch/reproduce_all_targets.py — Reprodutor Automatizado dos Alvos da Auditoria

Executa a reprodução empírica e inspeção de assinaturas para:
  - BL-060: TypeError quando files.content é NULL em compile_community_summary_jit()
  - BL-085: MockVectorDatabase.insert() fantasma vs BaseVectorBackend / ChromaVectorStore
  - BL-086: MockGraphRAGEngine.retrieve_multihop_context vs GraphRAGEngine
  - BL-087: _MockVectorStore permissivo com (*args, **kwargs) vs BaseVectorBackend.search estrito

Projetado para ser 100% resiliente:
  1. Pré-carrega `importlib.util` para contornar o bug latente em `tests/test_vector_reconciler.py:17`
     (onde `import importlib` é feito, mas `importlib.util` é referenciado sem import explícito).
  2. Fornece stubs de módulos opcionais (`mcp`, `pytest`, `chromadb`) via `unittest.mock` para
     permitir execução mesmo em ambientes sem as dependências de runtime completas instaladas.
  3. Contém fallback via AST parsing para `_MockVectorStore` caso a importação de topo de
     `tests/test_interface_contracts.py` seja bloqueada por dependências adicionais do sistema.
"""

import inspect
import sqlite3
import os
import sys
import unittest.mock

# Pré-carregar importlib.util: contorna bug latente em tests/test_vector_reconciler.py:17
import importlib
import importlib.util

# Configuração de caminhos relativos ao repositório
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Stubs transparentes para dependências externas pesadas/opcionais
for mod_name in ['mcp', 'mcp.server', 'mcp.server.fastmcp', 'pytest', 'chromadb']:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = unittest.mock.MagicMock()

from storage.base_backend import BaseVectorBackend
from storage.vector_store import ChromaVectorStore
from core.graph_rag import GraphRAGEngine
from core.delta_manager import DeltaManager

print("======================================================================")
print("REPRODUCAO BL-060: TypeError quando files.content e NULL")
print("======================================================================")
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE files (path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, body_hash TEXT, is_dirty INTEGER, community_id TEXT);")
conn.execute("CREATE TABLE communities (id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER);")
conn.execute("INSERT INTO communities (id, summary_text, is_dirty) VALUES ('c1', 'Resumo', 1);")
conn.execute("INSERT INTO files (path, content, is_dirty, community_id) VALUES ('file1.py', NULL, 1, 'c1');")

class FakeDB:
    def __init__(self, c):
        self.c = c
    def read_query(self, q, p=()):
        cur = self.c.cursor()
        cur.execute(q, p)
        return cur.fetchall()
    def write_query(self, q, p=()):
        cur = self.c.cursor()
        cur.execute(q, p)
        self.c.commit()
        return cur.rowcount

dm = DeltaManager(FakeDB(conn))
try:
    dm.compile_community_summary_jit('c1', lambda payload: "novo resumo")
    print("Sem excecao")
except TypeError as e:
    print(f"Traceback/Erro capturado com sucesso: {type(e).__name__}: {e}")

print("\n======================================================================")
print("REPRODUCAO BL-085 (mock-vs-real-audit.md #5 - MEDIA)")
print("======================================================================")
try:
    from tests.test_vector_reconciler import MockVectorDatabase
    print(f"MockVectorDatabase has 'insert': {hasattr(MockVectorDatabase, 'insert')}")
except Exception as e:
    print(f"Erro ao importar MockVectorDatabase: {e}")

print(f"BaseVectorBackend has 'insert': {hasattr(BaseVectorBackend, 'insert')}")
print(f"ChromaVectorStore has 'insert': {hasattr(ChromaVectorStore, 'insert')}")
print(f"BaseVectorBackend canonical method 'store_embedding': {hasattr(BaseVectorBackend, 'store_embedding')}")
print(f"ChromaVectorStore canonical method 'store_embedding': {hasattr(ChromaVectorStore, 'store_embedding')}")

print("\n======================================================================")
print("REPRODUCAO BL-086 (mock-vs-real-audit.md #6 - MEDIA)")
print("======================================================================")
try:
    from tests.test_cognitive_routing_memory import MockGraphRAGEngine
    print(f"MockGraphRAGEngine.retrieve_multihop_context sig: {inspect.signature(MockGraphRAGEngine.retrieve_multihop_context)}")
except Exception as e:
    print(f"Erro ao importar MockGraphRAGEngine: {e}")

print(f"GraphRAGEngine.retrieve_multihop_context sig:     {inspect.signature(GraphRAGEngine.retrieve_multihop_context)}")

print("\n======================================================================")
print("REPRODUCAO BL-087 (mock-vs-real-audit.md #7 - BAIXA)")
print("======================================================================")
_MockVectorStore = None
try:
    from tests.test_interface_contracts import _MockVectorStore
except Exception as err:
    # Fallback via AST parsing para isolamento total de dependências de importação
    import ast
    contract_test_file = os.path.join(_repo_root, "tests", "test_interface_contracts.py")
    with open(contract_test_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=contract_test_file)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_MockVectorStore":
            mod_ast = ast.Module(body=[node], type_ignores=[])
            code_obj = compile(mod_ast, filename=contract_test_file, mode="exec")
            namespace = {}
            exec(code_obj, namespace)
            _MockVectorStore = namespace.get("_MockVectorStore")
            break

if _MockVectorStore is not None:
    mock_vs = _MockVectorStore()
    print(f"_MockVectorStore has 'reset_collection': {hasattr(mock_vs, 'reset_collection')}")
    print(f"BaseVectorBackend has 'reset_collection': {hasattr(BaseVectorBackend, 'reset_collection')}")
    print(f"ChromaVectorStore has 'reset_collection': {hasattr(ChromaVectorStore, 'reset_collection')}")
    print(f"_MockVectorStore.search signature: {inspect.signature(mock_vs.search)}")
    print(f"BaseVectorBackend.search signature: {inspect.signature(BaseVectorBackend.search)}")
    
    # Chamada real comprovando permissividade excessiva
    res = mock_vs.search("qualquer_arg", ["p"], top_k=3, extra_param="invalido")
    print(f"Chamada permissiva mock_vs.search('qualquer_arg', ..., extra_param='invalido') -> Retorno: {res}")
else:
    print("Nao foi possivel carregar _MockVectorStore")

print("======================================================================")
