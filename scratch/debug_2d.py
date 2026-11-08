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
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u-secret-1', 'folder_secret_1');")
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u-secret-2', 'folder_secret_2');")
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u-secret-1', 'shared.py', 'MODULE', 'ACTIVE');")
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u-secret-2', 'shared.py', 'MODULE', 'ACTIVE');")

    engine = GraphRAGEngine(db)
    try:
        engine.get_call_chain_recursive('shared.py')
    except ValueError as e:
        print('Ambiguity error message:', str(e))
finally:
    try:
        os.unlink(db_path)
    except OSError:
        pass

