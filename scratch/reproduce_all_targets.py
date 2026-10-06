import inspect
import sqlite3
import os
import sys

# Configuração de caminhos relativos ao diretório do script
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

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
from tests.test_vector_reconciler import MockVectorDatabase
print(f"MockVectorDatabase has 'insert': {hasattr(MockVectorDatabase, 'insert')}")
print(f"BaseVectorBackend has 'insert': {hasattr(BaseVectorBackend, 'insert')}")
print(f"ChromaVectorStore has 'insert': {hasattr(ChromaVectorStore, 'insert')}")
print(f"BaseVectorBackend canonical method 'store_embedding': {hasattr(BaseVectorBackend, 'store_embedding')}")
print(f"ChromaVectorStore canonical method 'store_embedding': {hasattr(ChromaVectorStore, 'store_embedding')}")

print("\n======================================================================")
print("REPRODUCAO BL-086 (mock-vs-real-audit.md #6 - MEDIA)")
print("======================================================================")
from tests.test_cognitive_routing_memory import MockGraphRAGEngine
print(f"MockGraphRAGEngine.retrieve_multihop_context sig: {inspect.signature(MockGraphRAGEngine.retrieve_multihop_context)}")
print(f"GraphRAGEngine.retrieve_multihop_context sig:     {inspect.signature(GraphRAGEngine.retrieve_multihop_context)}")

print("\n======================================================================")
print("REPRODUCAO BL-087 (mock-vs-real-audit.md #7 - BAIXA)")
print("======================================================================")
from tests.test_interface_contracts import _MockVectorStore
mock_vs = _MockVectorStore()
print(f"_MockVectorStore has 'reset_collection': {hasattr(mock_vs, 'reset_collection')}")
print(f"BaseVectorBackend has 'reset_collection': {hasattr(BaseVectorBackend, 'reset_collection')}")
print(f"ChromaVectorStore has 'reset_collection': {hasattr(ChromaVectorStore, 'reset_collection')}")
print(f"_MockVectorStore.search signature: {inspect.signature(mock_vs.search)}")
print(f"BaseVectorBackend.search signature: {inspect.signature(BaseVectorBackend.search)}")
print("======================================================================")
