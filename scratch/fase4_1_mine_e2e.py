import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_e2e_")
    try:
        temp_dir_path = Path(temp_dir).resolve()
        temp_db = temp_dir_path / "concierge.db"
        temp_chroma = temp_dir_path / "chroma"
        fixture_dir = temp_dir_path / "fixture_repo"
        fixture_dir.mkdir(parents=True, exist_ok=True)

        # STRICT ASSERT: Nothing touches real data/
        assert not str(temp_db).startswith("data/"), f"Illegal DB path: {temp_db}"
        assert not str(temp_chroma).startswith("data/"), f"Illegal Chroma path: {temp_chroma}"
        assert "data\\concierge.db" not in str(temp_db).lower() or "temp" in str(temp_db).lower()

        # Set environment variables for bootstrap
        os.environ["GRAFO_DB_PATH"] = str(temp_db)
        os.environ["GRAFO_CHROMA_PATH"] = str(temp_chroma)
        os.environ["GRAFO_CHROMA_COLLECTION"] = "e2e_fase4_1"
        os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"

        # Create fixture files
        (fixture_dir / "math_ops.py").write_text(
            "def calculate_fibonacci(n: int) -> int:\n"
            "    \"\"\"Calculates the nth Fibonacci number recursively.\"\"\"\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)\n",
            encoding="utf-8"
        )
        (fixture_dir / "data_handler.py").write_text(
            "class MemoryRepository:\n"
            "    \"\"\"Repository for handling in-memory datasets.\"\"\"\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n\n"
            "    def retrieve_records(self):\n"
            "        return [1, 2, 3]\n",
            encoding="utf-8"
        )
        (fixture_dir / "README.md").write_text(
            "# Project Fixture E2E\n"
            "Demonstration fixture for end to end mining and hybrid search validation.\n",
            encoding="utf-8"
        )

        import main
        main.DB_PATH = str(temp_db)
        main.CHROMA_PATH = str(temp_chroma)
        main.CHROMA_COLLECTION = "e2e_fase4_1"

        print("=== BOOTSTRAP REAL SERVER ===")
        server, janitor, store = main.bootstrap()

        try:
            print("\n=== STEP 1: concierge_register ===")
            reg_res = server._handle_register(
                project_path=str(fixture_dir),
                wing="e2e_wing",
                privacy_level="PUBLIC",
                summary="E2E Validation Project"
            )
            print("Register result:")
            print(json.dumps(reg_res, indent=2))
            project_uuid = reg_res["project_uuid"]

            print("\n=== STEP 2: 1st concierge_mine ===")
            mine1_res = server._handle_mine(
                path=str(fixture_dir),
                project_identifier=project_uuid,
                auto_tag=True
            )
            print("1st mine result:")
            print(json.dumps(mine1_res, indent=2))

            print("\n=== STEP 3: 2nd concierge_mine ===")
            mine2_res = server._handle_mine(
                path=str(fixture_dir),
                project_identifier=project_uuid,
                auto_tag=True
            )
            print("2nd mine result:")
            print(json.dumps(mine2_res, indent=2))

            print("\n=== STEP 4: count_embeddings ===")
            count_res = server._handle_count_embeddings(project_identifier=project_uuid)
            print("count_embeddings result:")
            print(json.dumps(count_res, indent=2))

            print("\n=== STEP 5: concierge_search for 'calculate_fibonacci' ===")
            search_res = server._handle_search(
                query="calculate_fibonacci",
                project_identifier=project_uuid,
                top_k=5,
                node_type=None,
                include_references=False,
                all_wings=False
            )
            print("concierge_search result:")
            print(json.dumps(search_res, indent=2))

            # Verificações dos resultados esperados
            print("\n=== AUDIT CHECKS ===")
            print(f"Check 1: 1st mine embeddings_stored > 0: {mine1_res.get('embeddings_stored', 0)} -> {mine1_res.get('embeddings_stored', 0) > 0}")
            print(f"Check 2: 2nd mine files_skipped > 0: {mine2_res.get('files_skipped', 0)} -> {mine2_res.get('files_skipped', 0) > 0}")
            print(f"Check 3: count_embeddings count > 0: {count_res.get('count', 0)} -> {count_res.get('count', 0) > 0}")
            
            first_vector_score = 0.0
            if search_res.get("results"):
                first_vector_score = search_res["results"][0].get("vector_score", 0.0)
            print(f"Check 4: search top result vector_score > 0: {first_vector_score} -> {first_vector_score > 0}")

        finally:
            store.close()
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_probe()
