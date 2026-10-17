import sys
import os
import sqlite3
import tempfile
import inspect
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

if "." not in sys.path:
    sys.path.insert(0, ".")

def test_call_chain_probe():
    # 1. Signatures
    from interface.mcp_server import concierge_get_call_chain
    sig = inspect.signature(concierge_get_call_chain)
    doc = concierge_get_call_chain.__doc__
    
    print("=== 1. ASSINATURA DA FERRAMENTA ===")
    print(f"concierge_get_call_chain{sig}")
    print(f"Docstring: {doc.strip()}")
    
    # 2. Current SQL in core/graph_rag.py
    from core.graph_rag import GraphRAGEngine
    get_chain_source = inspect.getsource(GraphRAGEngine.get_call_chain_recursive)
    print("\n=== 2. CÓDIGO E SQL ATUAL (core/graph_rag.py) ===")
    print(get_chain_source)
    
    # 3. Real columns of nodes and edges in SQLite
    temp_dir = tempfile.mkdtemp(prefix="call_chain_probe_")
    db_path = os.path.join(temp_dir, "test.db")
    
    from storage.schema import SchemaManager
    conn = sqlite3.connect(db_path)
    SchemaManager(conn).apply_full_schema()
    
    nodes_cols = conn.execute("PRAGMA table_info(nodes);").fetchall()
    edges_cols = conn.execute("PRAGMA table_info(edges);").fetchall()
    
    print("\n=== 3. COLUNAS REAIS DE NODES E EDGES ===")
    print("nodes:", [c[1] for c in nodes_cols])
    print("edges:", [c[1] for c in edges_cols])
    
    # 4. Populate fixture:
    # Project: proj1
    # Nodes:
    # 1: dir 'src' (directory)
    # 2: 'src/main.py' (MODULE)
    # 3: 'src/main.py::run' (FUNCTION)
    # 4: 'src/utils.py' (MODULE)
    # 5: 'src/utils.py::helper' (FUNCTION)
    # 6: 'src/db.py' (MODULE)
    # 7: 'src/db.py::connect' (FUNCTION)
    # Edges:
    # contains: 2 -> 3 (main.py contains run)
    # contains: 4 -> 5 (utils.py contains helper)
    # contains: 6 -> 7 (db.py contains connect)
    # calls: 3 -> 5 (run calls helper)
    # calls: 5 -> 7 (helper calls connect)
    
    conn.execute("INSERT INTO projects (uuid, folder_name, primary_wing) VALUES ('p1', 'src', 'geral');")
    nodes_data = [
        (1, 'p1', 'src', 'FACT', 'directory'),
        (2, 'p1', 'src/main.py::src/main.py', 'MODULE', 'module'),
        (3, 'p1', 'src/main.py::run', 'FUNCTION', 'function'),
        (4, 'p1', 'src/utils.py::src/utils.py', 'MODULE', 'module'),
        (5, 'p1', 'src/utils.py::helper', 'FUNCTION', 'function'),
        (6, 'p1', 'src/db.py::src/db.py', 'MODULE', 'module'),
        (7, 'p1', 'src/db.py::connect', 'FUNCTION', 'function'),
    ]
    conn.executemany("INSERT INTO nodes (id, project_uuid, label, node_type, type) VALUES (?, ?, ?, ?, ?);", nodes_data)
    
    edges_data = [
        (2, 3, 'contains'),
        (4, 5, 'contains'),
        (6, 7, 'contains'),
        (3, 5, 'calls'),
        (5, 7, 'calls'),
    ]
    conn.executemany("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, ?);", edges_data)
    conn.commit()
    
    print("\n=== 4. FIXTURE DE TESTE INSERIDA ===")
    for row in conn.execute("SELECT id, label, node_type, type FROM nodes").fetchall():
        print(f"  Node {row[0]}: {row[1]} ({row[2]}/{row[3]})")
    for row in conn.execute("SELECT source_id, target_id, relation_type FROM edges").fetchall():
        print(f"  Edge: {row[0]} --[{row[2]}]--> {row[1]}")
        
    # 5. Candidate Query 1: Start node by file path (e.g. 'src/main.py')
    # If start_node is a file path:
    # Step A: find all symbols contained in that file (via contains edge or label prefix),
    # or find edges traversing both contains and calls!
    # Let's test a CTE candidate for symbol start:
    print("\n=== 5A. CONSULTA CANDIDATA: START_NODE POR NOME DE SÍMBOLO ('run') ===")
    sql_symbol = """
    WITH RECURSIVE CallChain(node_id, depth, path_visited) AS (
        SELECT id, 0, '|' || id || '|'
        FROM nodes
        WHERE (label = ? OR label LIKE '%::' || ?)
        
        UNION ALL
        
        SELECT e.target_id, cc.depth + 1, cc.path_visited || e.target_id || '|'
        FROM edges e
        JOIN CallChain cc ON e.source_id = cc.node_id
        WHERE e.relation_type = 'calls'
          AND cc.depth < ?
          AND instr(cc.path_visited, '|' || e.target_id || '|') = 0
    )
    SELECT DISTINCT n.id, n.label, n.node_type, cc.depth
    FROM CallChain cc
    JOIN nodes n ON cc.node_id = n.id
    WHERE cc.depth > 0
    ORDER BY cc.depth;
    """
    rows_sym = conn.execute(sql_symbol, ('run', 'run', 5)).fetchall()
    print("Resultado para start_node='run':")
    for r in rows_sym:
        print(f"  Hop {r[3]}: id={r[0]}, label={r[1]}, type={r[2]}")
        
    # 5B. Candidate Query 2: Start node by file path ('src/main.py')
    print("\n=== 5B. CONSULTA CANDIDATA: START_NODE POR CAMINHO DE ARQUIVO ('src/main.py') ===")
    # Approach:
    # 1. Identify module node or symbols in that file:
    # A file has symbols via 'contains' edges from the module node, OR label LIKE 'file::%'
    sql_file = """
    WITH RECURSIVE 
    FileSymbols AS (
        SELECT id FROM nodes 
        WHERE label = ? OR label LIKE ? || '::%'
    ),
    CallChain(node_id, depth, path_visited) AS (
        SELECT fs.id, 0, '|' || fs.id || '|'
        FROM FileSymbols fs
        
        UNION ALL
        
        SELECT e.target_id, cc.depth + 1, cc.path_visited || e.target_id || '|'
        FROM edges e
        JOIN CallChain cc ON e.source_id = cc.node_id
        WHERE e.relation_type = 'calls'
          AND cc.depth < ?
          AND instr(cc.path_visited, '|' || e.target_id || '|') = 0
    )
    SELECT DISTINCT n.id, n.label, n.node_type, cc.depth
    FROM CallChain cc
    JOIN nodes n ON cc.node_id = n.id
    WHERE cc.depth > 0
    ORDER BY cc.depth;
    """
    rows_file = conn.execute(sql_file, ('src/main.py', 'src/main.py', 5)).fetchall()
    print("Resultado para start_node='src/main.py':")
    for r in rows_file:
        print(f"  Hop {r[3]}: id={r[0]}, label={r[1]}, type={r[2]}")

    # File paths extracted:
    target_files = sorted(list({r[1].split('::')[0] for r in rows_file if '::' in r[1]}))
    print(f"Arquivos dependentes extraídos da cadeia: {target_files}")
    
    conn.close()
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass

if __name__ == '__main__':
    test_call_chain_probe()
