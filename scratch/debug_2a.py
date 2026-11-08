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
    p_uuid = 'proj-2a'
    print("insert proj:", db.write_query("INSERT INTO projects (uuid, folder_name) VALUES (?, ?);", (p_uuid, 'p2a')))
    print("insert a.py:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py', 'MODULE', 'ACTIVE');", (p_uuid,)))
    print("insert a.py::f:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::f', 'FUNCTION', 'ACTIVE');", (p_uuid,)))
    print("insert a.py::h:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::h', 'FUNCTION', 'ACTIVE');", (p_uuid,)))
    print("insert b.py:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'b.py', 'MODULE', 'ACTIVE');", (p_uuid,)))
    print("insert b.py::g:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'b.py::g', 'FUNCTION', 'ACTIVE');", (p_uuid,)))
    print("insert a.py::k:", db.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::k', 'FUNCTION', 'ACTIVE');", (p_uuid,)))

    id_af = db.read_query("SELECT id FROM nodes WHERE label = 'a.py::f';")[0][0]
    id_ah = db.read_query("SELECT id FROM nodes WHERE label = 'a.py::h';")[0][0]
    id_bg = db.read_query("SELECT id FROM nodes WHERE label = 'b.py::g';")[0][0]
    id_ak = db.read_query("SELECT id FROM nodes WHERE label = 'a.py::k';")[0][0]

    print("insert e1:", db.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_af, id_ah)))
    print("insert e2:", db.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_af, id_bg)))
    print("insert e3:", db.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_bg, id_ak)))

    engine = GraphRAGEngine(db)
    chain = engine.get_call_chain_recursive('a.py::f', depth_limit=5)
    print('chain result:', chain)
finally:
    try:
        os.unlink(db_path)
    except OSError:
        pass
