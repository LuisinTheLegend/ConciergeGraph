import os
import sys
import tempfile
import json
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

def test_offline_trigger():
    temp_dir = tempfile.mkdtemp(prefix="grafo_offline_probe_")
    try:
        temp_dir_path = Path(temp_dir).resolve()
        temp_db = temp_dir_path / "concierge.db"
        temp_chroma = temp_dir_path / "chroma"
        temp_hf = temp_dir_path / "hf_home"
        temp_hf.mkdir(parents=True, exist_ok=True)
        fixture_dir = temp_dir_path / "fixture_repo"
        fixture_dir.mkdir(parents=True, exist_ok=True)

        assert not str(temp_db).startswith("data/"), f"Illegal DB path: {temp_db}"
        assert not str(temp_chroma).startswith("data/"), f"Illegal Chroma path: {temp_chroma}"

        # Setup offline environment
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HOME"] = str(temp_hf)
        os.environ["GRAFO_DB_PATH"] = str(temp_db)
        os.environ["GRAFO_CHROMA_PATH"] = str(temp_chroma)
        os.environ["GRAFO_CHROMA_COLLECTION"] = "probe_offline_hf"
        os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"

        (fixture_dir / "worker.py").write_text("def process_queue():\n    return 'processed'\n", encoding="utf-8")
        (fixture_dir / "models.py").write_text("class Item:\n    def __init__(self, x):\n        self.x = x\n", encoding="utf-8")

        import main
        main.DB_PATH = str(temp_db)
        main.CHROMA_PATH = str(temp_chroma)
        main.CHROMA_COLLECTION = "probe_offline_hf"

        print("=== CASE 1: 1st MINE WITH OFFLINE NETWORK (No Cached Model) ===")
        server1, janitor1, store1 = main.bootstrap()
        try:
            reg_res = server1._handle_register(str(fixture_dir), wing="offline_wing", privacy_level="PUBLIC", summary="Offline Test")
            project_uuid = reg_res["project_uuid"]

            mine1_res = server1._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
            print("1st mine result (OFFLINE):")
            print(json.dumps({
                "success": mine1_res.get("success"),
                "files_processed": mine1_res.get("files_processed"),
                "nodes_created": mine1_res.get("nodes_created"),
                "embeddings_stored": mine1_res.get("embeddings_stored"),
                "files_skipped": mine1_res.get("files_skipped"),
                "errors": mine1_res.get("errors"),
            }, indent=2))

            count1 = server1._handle_count_embeddings(project_uuid)["count"]
            print(f"Vectors in Chroma after 1st mine (offline): {count1}")

        finally:
            store1.close()

        print("\n=== CASE 1 (cont): 2nd MINE AFTER NETWORK RESTORATION ===")
        # Remove offline restrictions and allow normal HF cache
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)
        os.environ.pop("HF_HOME", None)

        # Re-bootstrap server (with real model access)
        server2, janitor2, store2 = main.bootstrap()
        try:
            mine2_res = server2._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
            print("2nd mine result (ONLINE RESTORED):")
            print(json.dumps({
                "success": mine2_res.get("success"),
                "files_processed": mine2_res.get("files_processed"),
                "nodes_created": mine2_res.get("nodes_created"),
                "embeddings_stored": mine2_res.get("embeddings_stored"),
                "files_skipped": mine2_res.get("files_skipped"),
                "errors": mine2_res.get("errors"),
            }, indent=2))

            count2 = server2._handle_count_embeddings(project_uuid)["count"]
            print(f"Vectors in Chroma after 2nd mine (restored): {count2}")

            is_permanently_empty = (count2 == 0 and mine2_res.get("files_skipped", 0) > 0)
            print(f"\nCONFIRMED OFFLINE FAILURE LEAVES CHROMA PERMANENTLY EMPTY: {is_permanently_empty}")
        finally:
            store2.close()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_offline_trigger()
