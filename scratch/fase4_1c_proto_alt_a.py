"""Prototype of Alternative A on a broken state database.
Demonstrates that checking vector IDs in Chroma correctly flags files whose vectors are missing.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import shutil
import tempfile
import sqlite3
import chromadb

def run_prototype():
    temp_dir = tempfile.mkdtemp(prefix="grafo_proto_alt_a_")
    try:
        db_path = os.path.join(temp_dir, "concierge.db")
        chroma_dir = os.path.join(temp_dir, "chroma")
        
        # 1. Setup SQLite with nodes (simulating a completed mine where embeddings failed)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE nodes (id INTEGER PRIMARY KEY, project_uuid TEXT, label TEXT, file_hash TEXT)")
        conn.execute("INSERT INTO nodes VALUES (1, 'proj1', 'models.py::User', 'hash123')")
        conn.execute("INSERT INTO nodes VALUES (2, 'proj1', 'models.py::Profile', 'hash123')")
        conn.execute("INSERT INTO nodes VALUES (3, 'proj1', 'worker.py::do_work', 'hash456')")
        conn.commit()
        conn.close()

        # 2. Setup Chroma (simulating partial failure: only node_1 was stored; node_2 and node_3 missing)
        client = chromadb.PersistentClient(path=chroma_dir)
        collection = client.create_collection("proto_col")
        collection.add(ids=["node_1"], embeddings=[[0.1]*384])

        # 3. Prototype check: Given a file and its nodes in SQLite, are all vectors present in Chroma?
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Suppose crawler sees models.py with hash 'hash123'
        cur.execute("SELECT id FROM nodes WHERE project_uuid = 'proj1' AND file_hash = 'hash123'")
        model_node_ids = [r[0] for r in cur.fetchall()]
        
        # Query Chroma for these IDs
        expected_doc_ids = [f"node_{nid}" for nid in model_node_ids]
        chroma_res = collection.get(ids=expected_doc_ids, include=[])
        found_doc_ids = set(chroma_res["ids"])
        
        models_complete = all(doc_id in found_doc_ids for doc_id in expected_doc_ids)
        print(f"File models.py nodes in SQLite: {model_node_ids}")
        print(f"Vectors found in Chroma: {found_doc_ids}")
        print(f"Should models.py be skipped? {models_complete} (False means it needs reindexing!)")
        
        # For worker.py (hash456)
        cur.execute("SELECT id FROM nodes WHERE project_uuid = 'proj1' AND file_hash = 'hash456'")
        worker_node_ids = [r[0] for r in cur.fetchall()]
        worker_expected = [f"node_{nid}" for nid in worker_node_ids]
        worker_found = set(collection.get(ids=worker_expected, include=[])["ids"])
        worker_complete = all(doc_id in worker_found for doc_id in worker_expected)
        print(f"\nFile worker.py nodes in SQLite: {worker_node_ids}")
        print(f"Vectors found in Chroma: {worker_found}")
        print(f"Should worker.py be skipped? {worker_complete} (False means it needs reindexing!)")

        conn.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_prototype()
