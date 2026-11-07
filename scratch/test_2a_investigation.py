import os
import shutil
import tempfile
import sqlite3
from storage.schema import SchemaManager
from storage.store import SqliteStore
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine
from ingestion.orchestrator import IngestionManager
from storage.vector_store import EmbeddingManager

# Test real mining of 2 files with util() and 1 file calling util()
tmpdir = tempfile.mkdtemp()
src_dir = os.path.join(tmpdir, "src")
os.makedirs(os.path.join(src_dir, "pkg_a"), exist_ok=True)
os.makedirs(os.path.join(src_dir, "pkg_b"), exist_ok=True)
os.makedirs(os.path.join(src_dir, "app"), exist_ok=True)

with open(os.path.join(src_dir, "pkg_a", "tools.py"), "w", encoding="utf-8") as f:
    f.write("def util():\n    return 1\n")

with open(os.path.join(src_dir, "pkg_b", "tools.py"), "w", encoding="utf-8") as f:
    f.write("def util():\n    return 2\n")

with open(os.path.join(src_dir, "app", "main.py"), "w", encoding="utf-8") as f:
    f.write("def run():\n    return util()\n")

db_path = os.path.join(tmpdir, "test.db")
conn = sqlite3.connect(db_path)
SchemaManager(conn).apply_full_schema()
conn.close()

db_mgr = ConciergeDatabaseManager(db_path)
store = SqliteStore(db_path)
graph_rag = GraphRAGEngine(db_mgr)

os.environ["GRAFO_LLM_MODEL"] = "none"
ingest_mgr = IngestionManager(
    sqlite_store=store,
    embedding_manager=EmbeddingManager(),
    vector_store=None,
)

p_uuid = store.create_project(uuid="test-uuid", folder_name="src")
res = ingest_mgr.mine("test-uuid", src_dir)
print("Mine result files_processed:", res.files_processed)

# Inspect nodes for util
util_nodes = db_mgr.read_query("SELECT id, label FROM nodes WHERE label LIKE '%::util' ORDER BY id ASC")
print("util_nodes in DB:", util_nodes)

# Inspect edge created for run -> util
edges = db_mgr.read_query("""
    SELECT e.source_id, n1.label, e.target_id, n2.label, e.relation_type
    FROM edges e
    JOIN nodes n1 ON e.source_id = n1.id
    JOIN nodes n2 ON e.target_id = n2.id
    WHERE e.relation_type = 'calls'
""")
print("Call edges in DB:", edges)

chain = graph_rag.get_call_chain_recursive("app/main.py", depth_limit=5)
print("Call chain for app/main.py:", chain)

shutil.rmtree(tmpdir, ignore_errors=True)
