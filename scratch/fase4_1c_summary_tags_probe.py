"""Probe for Passo 4.4: Investigate why summaries_generated: 7 coexisted with summary: null and tags: null in concierge_search.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import shutil
import tempfile
import json
import sqlite3

def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_summary_probe_")
    try:
        db_path = os.path.join(temp_dir, "concierge.db")
        chroma_dir = os.path.join(temp_dir, "chroma")
        fixture_dir = os.path.join(temp_dir, "fixture_repo")
        os.makedirs(fixture_dir, exist_ok=True)

        with open(os.path.join(fixture_dir, "models.py"), "w", encoding="utf-8") as f:
            f.write("class User:\n    \"\"\"Represents a user.\"\"\"\n    pass\n\nclass Profile:\n    \"\"\"Represents a profile.\"\"\"\n    pass\n")
        with open(os.path.join(fixture_dir, "worker.py"), "w", encoding="utf-8") as f:
            f.write("def do_work():\n    \"\"\"Worker task.\"\"\"\n    pass\n")

        import main
        main.SQLITE_DB_PATH = db_path
        main.CHROMA_PERSIST_DIR = chroma_dir
        main.CHROMA_COLLECTION = "probe_summary"

        server, janitor, store = main.bootstrap()

        reg_res = server._handle_register(str(fixture_dir), wing="core", privacy_level="PUBLIC", summary="Probe")
        project_uuid = reg_res["project_uuid"]

        # Mine with auto_tag=True
        mine_res = server._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
        print("=== MINE RESULT ===")
        print(f"summaries_generated: {mine_res.get('summaries_generated')}")
        print(f"files_processed: {mine_res.get('files_processed')}")
        print(f"nodes_created: {mine_res.get('nodes_created')}")

        # Check SQLite directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, type, summary, tags FROM nodes WHERE project_uuid = ?", (project_uuid,))
        sqlite_nodes = cursor.fetchall()
        print("\n=== SQLITE NODES (id, label, type, summary, tags) ===")
        for row in sqlite_nodes:
            print(f"Node id={row[0]}, label='{row[1]}', type='{row[2]}', summary={repr(row[3])}, tags={repr(row[4])}")
        conn.close()

        # Check search result
        search_res = server._handle_search(query="user", project_uuids=[project_uuid], top_k=5)
        print("\n=== SEARCH RESULTS ===")
        print(json.dumps(search_res, indent=2))

        server.store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_probe()
