import sqlite3, tempfile, os
from storage.schema import SchemaManager
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine

fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(fd)
try:
    conn = sqlite3.connect(db_path)
    SchemaManager(conn).apply_full_schema()
    conn.close()
    db = ConciergeDatabaseManager(db_path)
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('p1', 'p1');")
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('p1', 'root.py', 'MODULE', 'ACTIVE');")

    engine = GraphRAGEngine(db)
    res = engine.get_call_chain_recursive('root.py', depth_limit=True)
    print('depth_limit=True accepted with return:', res)
finally:
    try:
        os.unlink(db_path)
    except OSError:
        pass

