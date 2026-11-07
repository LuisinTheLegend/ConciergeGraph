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
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u1', 'alpha');")
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u2', 'alpha');")
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u1', 'mod.py', 'MODULE', 'ACTIVE');")
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u2', 'mod.py', 'MODULE', 'ACTIVE');")

    engine = GraphRAGEngine(db)
    # Today, this resolves silently to u1 without error!
    chain = engine.get_call_chain_recursive('mod.py', project_identifier='alpha')
    print('chain result with duplicate alpha:', chain)
finally:
    try:
        os.unlink(db_path)
    except OSError:
        pass

