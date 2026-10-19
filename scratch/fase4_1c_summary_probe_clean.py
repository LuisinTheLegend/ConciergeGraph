"""Probe for Passo 4.4: Verify why summaries_generated > 0 has summary: null and tags: null.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import shutil
import tempfile
import json
import sqlite3
from unittest.mock import MagicMock

def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_summary_probe_")
    try:
        db_path = os.path.join(temp_dir, "concierge.db")
        chroma_dir = os.path.join(temp_dir, "chroma")
        fixture_dir = os.path.join(temp_dir, "fixture_repo")
        os.makedirs(fixture_dir, exist_ok=True)

        with open(os.path.join(fixture_dir, "models.py"), "w", encoding="utf-8") as f:
            f.write("class User:\n    \"\"\"Represents a user.\"\"\"\n    pass\n\nclass Profile:\n    \"\"\"Represents a profile.\"\"\"\n    pass\n")

        from storage.store import SqliteStore
        from storage.vector_store import ChromaVectorStore
        from ingestion.orchestrator import IngestionManager
        from ingestion.summarizer import SummaryResult, ZoomLevel

        store = SqliteStore(db_path)
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="probe_summary")

        # Mock summarizer that returns real SummaryResult objects
        mock_summarizer = MagicMock()
        def mock_summarize_l0_async(chunk):
            async def _coro():
                return SummaryResult(
                    level=ZoomLevel.L0,
                    summary=f"Summary for {chunk.symbol_name}",
                    source_label=chunk.symbol_name,
                    detected_tags=["mock_tag"]
                )
            return _coro()
        mock_summarizer.summarize_l0_async.side_effect = mock_summarize_l0_async

        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.embed_batch.side_effect = lambda texts: [[0.1] * 384 for _ in texts]

        manager = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=mock_embedder,
            summarizer=mock_summarizer,
        )

        import uuid
        proj_uuid = str(uuid.uuid4())
        store.create_project(uuid=proj_uuid, folder_name="fixture_repo")

        # Mine with auto_tag=True
        mine_res = manager.mine(project_uuid=proj_uuid, source_path=fixture_dir, auto_tag=True)
        print("=== MINE RESULT ===")
        print(f"summaries_generated: {mine_res.summaries_generated}")
        print(f"files_processed: {mine_res.files_processed}")
        print(f"nodes_created: {mine_res.nodes_created}")

        # Query SQLite directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, type, summary, tags FROM nodes WHERE project_uuid = ?", (proj_uuid,))
        rows = cursor.fetchall()
        print("\n=== SQLITE NODES (id, label, type, summary, tags) ===")
        for r in rows:
            print(f"Node id={r[0]}, label='{r[1]}', type='{r[2]}', summary={repr(r[3])}, tags={repr(r[4])}")
        conn.close()

        store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_probe()
