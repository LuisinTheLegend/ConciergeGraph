import os
import sys
import tempfile
import json
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_reset_probe_")
    try:
        temp_dir_path = Path(temp_dir).resolve()
        temp_db = temp_dir_path / "concierge.db"
        temp_chroma = temp_dir_path / "chroma"
        fixture_dir = temp_dir_path / "fixture_repo"
        fixture_dir.mkdir(parents=True, exist_ok=True)

        assert not str(temp_db).startswith("data/"), f"Illegal DB path: {temp_db}"
        assert not str(temp_chroma).startswith("data/"), f"Illegal Chroma path: {temp_chroma}"

        os.environ["GRAFO_DB_PATH"] = str(temp_db)
        os.environ["GRAFO_CHROMA_PATH"] = str(temp_chroma)
        os.environ["GRAFO_CHROMA_COLLECTION"] = "probe_reset_collection"
        os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"

        # Create 2 sample files
        (fixture_dir / "service.py").write_text("def run_service():\n    return 'running'\n", encoding="utf-8")
        (fixture_dir / "utils.py").write_text("def format_str(s):\n    return s.strip()\n", encoding="utf-8")

        import main
        main.DB_PATH = str(temp_db)
        main.CHROMA_PATH = str(temp_chroma)
        main.CHROMA_COLLECTION = "probe_reset_collection"

        server, janitor, store = main.bootstrap()
        try:
            print("=== STEP 1: Register and Initial Mine ===")
            reg_res = server._handle_register(str(fixture_dir), wing="core", privacy_level="PUBLIC", summary="Test")
            project_uuid = reg_res["project_uuid"]

            mine1_res = server._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
            print("1st mine result:", {
                "files_processed": mine1_res.get("files_processed"),
                "nodes_created": mine1_res.get("nodes_created"),
                "embeddings_stored": mine1_res.get("embeddings_stored"),
                "files_skipped": mine1_res.get("files_skipped"),
            })

            count_before_reset = server._handle_count_embeddings(project_uuid)["count"]
            print(f"Vectors in Chroma before reset: {count_before_reset}")
            assert count_before_reset > 0, "Chroma should have vectors after 1st mine"

            print("\n=== STEP 2: Transition to MAINTENANCE and Reset Collection ===")
            # Use governor to transition to MAINTENANCE
            server._governor.set_session_state("default", "MAINTENANCE")
            print(f"Governor active state: {server._governor.get_session_state('default')}")

            reset_res = server._handle_reset_collection()
            print("reset_collection result:", reset_res)

            count_after_reset = server._handle_count_embeddings(project_uuid)["count"]
            print(f"Vectors in Chroma immediately after reset: {count_after_reset}")
            assert count_after_reset == 0, "Chroma collection should be 0 after reset"

            print("\n=== STEP 3: 2nd Mine (Attempting to re-populate Chroma) ===")
            server._governor.set_session_state("default", "EXECUTION")
            mine2_res = server._handle_mine(str(fixture_dir), project_uuid, auto_tag=True)
            print("2nd mine result:", {
                "files_processed": mine2_res.get("files_processed"),
                "nodes_created": mine2_res.get("nodes_created"),
                "embeddings_stored": mine2_res.get("embeddings_stored"),
                "files_skipped": mine2_res.get("files_skipped"),
            })

            count_after_2nd_mine = server._handle_count_embeddings(project_uuid)["count"]
            print(f"Vectors in Chroma after 2nd mine: {count_after_2nd_mine}")

            is_broken_state = (count_after_2nd_mine == 0 and mine2_res.get("files_skipped", 0) > 0)
            print(f"\nCONFIRMED BROKEN STATE VIA OFFICIAL TOOL: {is_broken_state}")

        finally:
            store.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_probe()
