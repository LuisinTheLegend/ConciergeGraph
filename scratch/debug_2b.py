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
    p_uuid = 'proj-2b'
    db.write_query("INSERT INTO projects (uuid, folder_name) VALUES (?, ?);", (p_uuid, 'p2b'))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a_b.py', 'MODULE', 'ACTIVE');", (p_uuid,))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a_b.py::x', 'FUNCTION', 'ACTIVE');", (p_uuid,))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'aXb.py', 'MODULE', 'ACTIVE');", (p_uuid,))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'aXb.py::y', 'FUNCTION', 'ACTIVE');", (p_uuid,))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'z.py', 'MODULE', 'ACTIVE');", (p_uuid,))
    db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'z.py::zz', 'FUNCTION', 'ACTIVE');", (p_uuid,))

    id_ay = db.read_query("SELECT id FROM nodes WHERE label = 'aXb.py::y';")[0][0]
    id_zz = db.read_query("SELECT id FROM nodes WHERE label = 'z.py::zz';")[0][0]
    db.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_ay, id_zz))

    engine = GraphRAGEngine(db)
    chain = engine.get_call_chain_recursive('a_b.py', depth_limit=5)
    print('chain result for a_b.py:', chain)
finally:
    try:
        os.unlink(db_path)
    except OSError:
        pass

