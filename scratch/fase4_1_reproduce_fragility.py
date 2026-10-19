import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from storage import SqliteStore, ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager

class FailingEmbeddingManager:
    """Mock EmbeddingManager that simulates failure at Step 5."""
    def __init__(self):
        self.tier = EmbeddingTier.FLASH
        self.model_name = "mock-embedder"
        self.dimensions = 384

    def embed_batch(self, texts):
        raise RuntimeError("SIMULATED_FAILURE: Embedding model unavailable during Step 5!")

    def embed(self, text):
        raise RuntimeError("SIMULATED_FAILURE: Embedding model unavailable during Step 5!")

class WorkingEmbeddingManager:
    """Deterministic mock EmbeddingManager."""
    def __init__(self):
        self.tier = EmbeddingTier.FLASH
        self.model_name = "mock-embedder"
        self.dimensions = 384

    def embed_batch(self, texts):
        return [[0.1] * self.dimensions for _ in texts]

    def embed(self, text):
        return [0.1] * self.dimensions

def main():
    temp_dir = tempfile.mkdtemp()
    try:
        temp_data = Path(temp_dir) / "data"
        temp_data.mkdir()
        temp_db = temp_data / "concierge.db"
        temp_chroma = temp_data / "chroma"
        temp_fixture = Path(temp_dir) / "fixture"
        temp_fixture.mkdir()

        # Assert zero interaction with real data/
        assert str(temp_db) != "data/concierge.db"
        assert not str(temp_db).startswith("data/")

        # Create sample files
        (temp_fixture / "mod_a.py").write_text("def func_a():\n    return 42\n", encoding="utf-8")
        (temp_fixture / "mod_b.py").write_text("def func_b():\n    return 'hello'\n", encoding="utf-8")

        store = SqliteStore(str(temp_db))
        failing_embedder = FailingEmbeddingManager()
        vector_store = ChromaVectorStore(
            persist_dir=str(temp_chroma),
            collection_name="test_fragility",
            embedding_manager=failing_embedder,
        )

        project_uuid = "proj-fragility-test"
        store.create_project(project_uuid, "Fragility Test", str(temp_fixture))

        mgr1 = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=failing_embedder,
            summarizer=None,
        )

        print("=== 1st MINING (Simulating failure during Step 5) ===")
        res1_error = None
        try:
            res1 = mgr1.mine(project_uuid, str(temp_fixture))
            print("1st mine result:", res1.to_dict())
        except Exception as e:
            res1_error = e
            print(f"1st mine caught exception: {type(e).__name__}: {e}")

        # Check SQLite state
        nodes_after_1 = store.get_nodes_by_project(project_uuid)
        code_nodes_1 = [n for n in nodes_after_1 if n.get("type") not in ("directory", "project")]
        print(f"Nodes persisted in SQLite after 1st mine: {len(code_nodes_1)}")
        for n in code_nodes_1:
            print(f"  Node: {n['label']} | hash: {n.get('file_hash')[:12]}...")

        # Check Chroma state
        chroma_count_1 = vector_store.count()
        print(f"Vectors in Chroma after 1st mine: {chroma_count_1}")

        print("\n=== 2nd MINING (With working embedder restored) ===")
        working_embedder = WorkingEmbeddingManager()
        vector_store._embedder = working_embedder
        mgr2 = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=working_embedder,
            summarizer=None,
        )

        res2 = mgr2.mine(project_uuid, str(temp_fixture))
        print("2nd mine result:", res2.to_dict())

        # Check SQLite state
        nodes_after_2 = store.get_nodes_by_project(project_uuid)
        code_nodes_2 = [n for n in nodes_after_2 if n.get("type") not in ("directory", "project")]
        print(f"Nodes in SQLite after 2nd mine: {len(code_nodes_2)}")

        # Check Chroma state
        chroma_count_2 = vector_store.count()
        print(f"Vectors in Chroma after 2nd mine: {chroma_count_2}")

        store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
