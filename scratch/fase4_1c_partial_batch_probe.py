"""Probe to test partial batch failure during embedding step.
Tests what happens when batch 1 succeeds and batch 2 fails.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import shutil
import tempfile
from unittest.mock import MagicMock

# Safety check
def assert_no_data_touched(before_stat, after_stat):
    pass

def run_partial_batch_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_partial_batch_")
    try:
        db_path = os.path.join(temp_dir, "concierge.db")
        chroma_dir = os.path.join(temp_dir, "chroma")
        fixture_dir = os.path.join(temp_dir, "fixture_repo")
        os.makedirs(fixture_dir, exist_ok=True)

        # Create 2 files in fixture repo
        with open(os.path.join(fixture_dir, "models.py"), "w", encoding="utf-8") as f:
            f.write("class User:\n    pass\n\nclass Profile:\n    pass\n")
        with open(os.path.join(fixture_dir, "worker.py"), "w", encoding="utf-8") as f:
            f.write("def do_work():\n    pass\n\ndef clean_up():\n    pass\n")

        from storage.store import SqliteStore
        from storage.vector_store import ChromaVectorStore
        from ingestion.orchestrator import IngestionManager

        store = SqliteStore(db_path)
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="probe_partial_batch")

        # Mock embedder where batch 1 succeeds and batch 2 fails
        mock_embedder = MagicMock()
        def side_effect_embed_batch(texts):
            # Suppose texts has 5 chunks total (1 per symbol/file).
            # 1st batch of 2 succeeds with real/mock vectors, 2nd batch fails (None).
            results = []
            for idx, text in enumerate(texts):
                if idx < 2:
                    results.append([0.1] * 384)
                else:
                    results.append(None) # Failed items return None (Semantic fallback)
            return results

        mock_embedder.embed_batch.side_effect = side_effect_embed_batch

        manager = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=mock_embedder,
            summarizer=None,
        )

        import uuid
        proj_uuid = str(uuid.uuid4())
        project = store.create_project(uuid=proj_uuid, folder_name="fixture_repo")
        project_uuid = project["uuid"]

        # Run 1st mine with partial batch failure
        res1 = manager.mine(project_uuid=project_uuid, source_path=fixture_dir)
        count1 = vector_store.count(project_uuid=project_uuid)

        print("=== CASE 2: PARTIAL BATCH FAILURE ===")
        print("1st mine result:")
        print(f"  files_processed: {res1.files_processed}")
        print(f"  nodes_created: {res1.nodes_created}")
        print(f"  embeddings_stored: {res1.embeddings_stored}")
        print(f"  files_skipped: {res1.files_skipped}")
        print(f"  errors: {res1.errors}")
        print(f"  Chroma vector count: {count1}")

        # Now fix embedder (all succeed) and run 2nd mine
        mock_embedder.embed_batch.side_effect = lambda texts: [[0.1] * 384 for _ in texts]

        res2 = manager.mine(project_uuid=project_uuid, source_path=fixture_dir)
        count2 = vector_store.count(project_uuid=project_uuid)

        print("\n2nd mine result (after embedder healed):")
        print(f"  files_processed: {res2.files_processed}")
        print(f"  nodes_created: {res2.nodes_created}")
        print(f"  embeddings_stored: {res2.embeddings_stored}")
        print(f"  files_skipped: {res2.files_skipped}")
        print(f"  errors: {res2.errors}")
        print(f"  Chroma vector count: {count2}")
        print(f"\nPARTIAL FAILURE PERMANENTLY FREEZES PARTIAL VECTORS: {count1 == count2 and count2 < 5}")

        store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_partial_batch_probe()
