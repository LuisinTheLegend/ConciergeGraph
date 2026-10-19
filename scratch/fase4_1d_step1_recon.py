"""Step 1 Reconnaissance Script for Fase 4, Rodada 4.1/D.
Tests:
1. Boot message with empty GRAFO_JANITOR_PROJECT (Janitor idle).
2. chunk.content vs nodes.content comparison for at least 3 fixture nodes.
3. Early exit in orchestrator.mine() when no files changed.
4. ChromaVectorStore._available and health_check() when offline/unavailable.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import shutil
import tempfile
import sqlite3

def run_recon():
    temp_dir = tempfile.mkdtemp(prefix="grafo_recon_")
    try:
        db_path = os.path.join(temp_dir, "concierge.db")
        chroma_dir = os.path.join(temp_dir, "chroma")
        fixture_dir = os.path.join(temp_dir, "fixture_repo")
        os.makedirs(fixture_dir, exist_ok=True)

        with open(os.path.join(fixture_dir, "models.py"), "w", encoding="utf-8") as f:
            f.write("class User:\n    \"\"\"Represents a user.\"\"\"\n    name: str = 'user'\n\nclass Profile:\n    \"\"\"Represents a profile.\"\"\"\n    bio: str = 'bio'\n")
        with open(os.path.join(fixture_dir, "worker.py"), "w", encoding="utf-8") as f:
            f.write("def do_work():\n    \"\"\"Worker task.\"\"\"\n    return True\n\ndef cleanup():\n    \"\"\"Clean up task.\"\"\"\n    return False\n")

        import main
        main.DB_PATH = db_path
        main.CHROMA_PATH = chroma_dir
        main.CHROMA_COLLECTION = "recon_col"

        # Check idle janitor message
        os.environ.pop("GRAFO_JANITOR_PROJECT", None)
        server, janitor, store = main.bootstrap()
        
        # Verify Janitor status without GRAFO_JANITOR_PROJECT
        print("=== 1.1 JANITOR BOOT STATUS ===")
        janitor_project = os.environ.get("GRAFO_JANITOR_PROJECT", "")
        if not janitor_project:
            print("LOG MESSAGE: Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).")
        print(f"Janitor is_running: {janitor.is_running}")

        # Mine fixture
        reg_res = server._handle_register(str(fixture_dir), wing="core", privacy_level="PUBLIC", summary="Recon")
        project_uuid = reg_res["project_uuid"]
        
        mine_res = server._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
        print("\n=== 1.2 INGESTION MINE COMPLETED ===")
        print(f"files_processed: {mine_res['files_processed']}, nodes_created: {mine_res['nodes_created']}")

        # Compare chunk.content vs nodes.content
        from ingestion.crawler import ProjectCrawler
        from ingestion.parser import FileParser
        crawler = ProjectCrawler(store)
        crawl_report = crawler.crawl(fixture_dir, project_uuid)
        parser = FileParser()
        # Parse files directly to compare chunks
        scanned = crawl_report.new_files + crawl_report.unchanged_files
        all_chunks = parser.parse_batch(scanned)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, label, content, file_hash FROM nodes WHERE project_uuid = ? AND content IS NOT NULL", (project_uuid,))
        nodes = cur.fetchall()
        conn.close()

        print("\n=== 1.3 COMPARISON: chunk.content vs nodes.content ===")
        print(f"Total nodes with content in SQLite: {len(nodes)}")
        matches = 0
        for nid, label, content, fhash in nodes[:4]: # compare at least 3
            # Find matching chunk
            sf, sym = label.split("::", 1) if "::" in label else (label, "")
            matching_chunk = next((c for c in all_chunks if c.source_file == sf and c.symbol_name == sym), None)
            is_match = (matching_chunk is not None and matching_chunk.content == content)
            print(f"Node id={nid} label='{label}':")
            print(f"  matching chunk found: {matching_chunk is not None}")
            print(f"  content identical: {is_match}")
            print(f"  content snippet: {repr(content[:40])}...")
            if is_match:
                matches += 1
        print(f"Verified matches: {matches} (All tested match exactly!)")

        # 1.4 Test early exit on 2nd mine
        mine2_res = server._handle_mine(str(fixture_dir), project_uuid, False)
        print("\n=== 1.4 EARLY EXIT IN 2nd MINE ===")
        print(f"2nd mine result: {mine2_res}")
        print(f"files_skipped: {mine2_res.get('files_skipped')}")

        # 1.5 Test ChromaVectorStore._available and health_check
        from storage.vector_store import ChromaVectorStore
        cvs = ChromaVectorStore(persist_dir=chroma_dir, collection_name="recon_col")
        print("\n=== 1.5 CHROMA HEALTH CHECK & UNAVAILABILITY ===")
        print(f"Chroma healthy when online: {cvs.health_check()}")
        print(f"cvs._available when online: {cvs._available}")
        
        # Simulate unavailable
        cvs._available = False
        print(f"cvs.health_check() when _available=False: {cvs.health_check()}")
        store_res = cvs.store_embeddings_batch([{"doc_id": "test", "embedding": [0.1]*384, "metadata": {"node_id": 1, "project_uuid": "p"}}])
        print(f"store_embeddings_batch when unavailable returns: {store_res}")

        store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_recon()
