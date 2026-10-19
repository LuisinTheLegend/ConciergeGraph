"""scratch/fase4_1d_e2e.py

End-to-End Probe for Phase 4, Round 4.1/D with real server and real all-MiniLM-L6-v2 model.

Scenarios tested:
1. Offline scenario: HF_HUB_OFFLINE=1 with empty cache -> 1st mine reports embeddings_failed > 0 and errors non-empty.
   Restoring model -> 2nd mine repairs vectors and count_embeddings == nodes with content;
   concierge_search returns vector_score > 0.
2. reset_collection scenario: mine -> concierge_set_state(MAINTENANCE) -> reset_collection -> mine -> vectors recomposed.
3. Summary scenario: concierge_search returns summary not null for new nodes.
4. Measurement: timing of repair_missing_vectors when nothing to repair (3rd mine).
"""

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def create_fixture(repo_path: Path):
    repo_path.mkdir(parents=True, exist_ok=True)
    f1 = repo_path / "models.py"
    f1.write_text(
        "class User:\n"
        "    \"\"\"Represents a user account.\"\"\"\n"
        "    def get_name(self):\n"
        "        return 'alice'\n\n"
        "class Profile:\n"
        "    \"\"\"Represents user profile.\"\"\"\n"
        "    def get_bio(self):\n"
        "        return 'bio'\n",
        encoding="utf-8"
    )
    f2 = repo_path / "worker.py"
    f2.write_text(
        "def run_task():\n"
        "    \"\"\"Background worker execution.\"\"\"\n"
        "    return 42\n",
        encoding="utf-8"
    )


def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="grafo_e2e_fase4_1d_")
    print(f"=== E2E PROBE STARTED in {temp_dir} ===")

    # Isolation assertions: ensure data/ in repo is NEVER touched
    data_repo_dir = REPO_ROOT / "data"
    data_before_mtime = data_repo_dir.stat().st_mtime if data_repo_dir.exists() else None

    # Redirect environment to temp directory
    os.environ["GRAFO_DATA_DIR"] = temp_dir
    os.environ["GRAFO_CHROMA_DIR"] = os.path.join(temp_dir, "chroma")
    os.environ["GRAFO_DB_PATH"] = os.path.join(temp_dir, "grafo.db")
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"

    repo_path = Path(temp_dir) / "fixture_repo"
    create_fixture(repo_path)

    # Save original HF env
    orig_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    orig_hf_home = os.environ.get("HF_HOME")

    try:
        # =====================================================================
        # SCENARIO 1: OFFLINE MODEL (HF_HUB_OFFLINE=1 with empty cache)
        # =====================================================================
        print("\n--- [1] OFFLINE SCENARIO (HF_HUB_OFFLINE=1 com cache vazio) ---")
        empty_hf_home = Path(temp_dir) / "empty_hf_home"
        empty_hf_home.mkdir(parents=True, exist_ok=True)

        import huggingface_hub.constants as hf_constants
        hf_constants.HF_HUB_OFFLINE = True
        hf_constants.HF_HOME = str(empty_hf_home)
        hf_constants.HF_HUB_CACHE = str(empty_hf_home / "hub")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HOME"] = str(empty_hf_home)

        from main import bootstrap
        server, janitor, store = bootstrap()

        # Register project
        proj_uuid = server._gc.register_project("fixture_repo", "Fixture Project")
        print(f"Project registered: {proj_uuid}")

        # 1st mine with offline model
        res1 = server._handle_mine(str(repo_path), proj_uuid, False)
        print("1st mine result (offline):")
        print(f"  nodes_created: {res1.get('nodes_created')}")
        print(f"  embeddings_stored: {res1.get('embeddings_stored')}")
        print(f"  embeddings_failed: {res1.get('embeddings_failed')}")
        print(f"  errors: {res1.get('errors')}")

        count1 = server._handle_count_embeddings(proj_uuid)["count"]
        print(f"  count_embeddings after 1st mine: {count1}")

        # Restore model
        import huggingface_hub.constants as hf_constants
        hf_constants.HF_HUB_OFFLINE = False
        if orig_hf_home is not None:
            hf_constants.HF_HOME = orig_hf_home
            hf_constants.HF_HUB_CACHE = os.path.join(orig_hf_home, "hub")
            os.environ["HF_HOME"] = orig_hf_home
        else:
            os.environ.pop("HF_HOME", None)
            # Default HF cache
            default_home = os.path.expanduser("~/.cache/huggingface")
            hf_constants.HF_HOME = default_home
            hf_constants.HF_HUB_CACHE = os.path.join(default_home, "hub")

        if orig_hf_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = orig_hf_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)

        # Reset embedder model inside server so it re-initializes with the real model
        server._gc._ingestion._embedder._model = None
        server._gc._search_engine._embedder._model = None

        # 2nd mine (unchanged files) -> must repair missing vectors
        print("\n--- [1.b] RESTORE MODEL AND 2nd MINE (REPAIR) ---")
        res2 = server._handle_mine(str(repo_path), proj_uuid, False)
        print("2nd mine result:")
        print(f"  files_skipped: {res2.get('files_skipped')}")
        print(f"  embeddings_stored: {res2.get('embeddings_stored')}")
        print(f"  embeddings_repaired: {res2.get('embeddings_repaired')}")
        print(f"  embeddings_failed: {res2.get('embeddings_failed')}")

        nodes = store.get_nodes_by_project(proj_uuid, status="ACTIVE")
        nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]
        count2 = server._handle_count_embeddings(proj_uuid)["count"]
        print(f"  nodes with content in SQLite: {len(nodes_with_content)}")
        print(f"  count_embeddings after 2nd mine: {count2}")

        # Hybrid Search: must return vector_score > 0
        search_dict = server._handle_search(
            query="user account",
            project_identifier=proj_uuid,
            top_k=3,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        search_res = search_dict.get("results", [])
        print(f"  search results count: {len(search_res)}")
        for r in search_res:
            print(f"    - node_id={r['node_id']} label='{r['label']}' vector_score={r['vector_score']} hybrid_score={r['hybrid_score']}")

        # =====================================================================
        # SCENARIO 2: RESET_COLLECTION SCENARIO
        # =====================================================================
        print("\n--- [2] RESET_COLLECTION SCENARIO ---")
        # Transition state to MAINTENANCE via governor
        server._governor.set_session_state("default", "MAINTENANCE")
        print(f"Session state transitioned to: {server._governor.get_session_state('default')}")

        # Call reset_collection
        reset_res = server._handle_reset_collection()
        print(f"reset_collection result: {reset_res}")

        count_after_reset = server._handle_count_embeddings(proj_uuid)["count"]
        print(f"count_embeddings after reset: {count_after_reset}")

        # Mine again to recompose vectors
        res_recompose = server._handle_mine(str(repo_path), proj_uuid, False)
        print("Mine after reset_collection:")
        print(f"  embeddings_repaired: {res_recompose.get('embeddings_repaired')}")
        count_recomposed = server._handle_count_embeddings(proj_uuid)["count"]
        print(f"count_embeddings after recomposition: {count_recomposed}")

        # Transition back to PLANNING
        server._governor.set_session_state("default", "PLANNING")

        # =====================================================================
        # SCENARIO 3: SUMMARY SCENARIO
        # =====================================================================
        print("\n--- [3] SUMMARY SCENARIO ---")
        # Ingest a new file with unique content
        f3 = repo_path / "service.py"
        f3.write_text("def auth_service():\n    return 'auth'\n", encoding="utf-8")
        res_summary = server._handle_mine(str(repo_path), proj_uuid, False)
        print(f"Mine new file: nodes_created={res_summary.get('nodes_created')}, summaries_generated={res_summary.get('summaries_generated')}")

        search_summary_dict = server._handle_search(
            query="auth service",
            project_identifier=proj_uuid,
            top_k=3,
            node_type=None,
            include_references=False,
            all_wings=False,
        )
        search_summary = search_summary_dict.get("results", [])
        for r in search_summary:
            print(f"  Search result: label='{r['label']}', summary={repr(r['summary'])}, summary non-empty={bool(r['summary'])}")

        # =====================================================================
        # SCENARIO 4: TIMING OF REPAIR ROUTINE (3rd mine / no missing)
        # =====================================================================
        print("\n--- [4] TIMING MEASUREMENT (NADA A REPARAR) ---")
        repair_fn = getattr(server._gc._ingestion, "repair_missing_vectors", None)
        if repair_fn is not None:
            t_start = time.perf_counter()
            found_missing, repaired, failed = repair_fn(proj_uuid)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000
            print(f"repair_missing_vectors when nothing to repair: found={found_missing}, repaired={repaired}, failed={failed}")
            print(f"Time elapsed: {t_elapsed_ms:.4f} ms")
        else:
            print("repair_missing_vectors NÃO EXISTE em IngestionManager (código legado 76e6a7e)")

        # Isolation check: data/ must not have been modified
        if data_repo_dir.exists() and data_before_mtime is not None:
            assert data_repo_dir.stat().st_mtime == data_before_mtime, "CRITICAL: data/ was touched during probe!"
        print("\n=== ISOLATION CONFIRMED: data/ in repository was NOT touched! ===")

        store.close()
    finally:
        try:
            import huggingface_hub.constants as hf_constants
            hf_constants.HF_HUB_OFFLINE = bool(orig_hf_offline) if orig_hf_offline else False
            if orig_hf_home:
                hf_constants.HF_HOME = orig_hf_home
                hf_constants.HF_HUB_CACHE = os.path.join(orig_hf_home, "hub")
            else:
                default_home = os.path.expanduser("~/.cache/huggingface")
                hf_constants.HF_HOME = default_home
                hf_constants.HF_HUB_CACHE = os.path.join(default_home, "hub")
        except Exception:
            pass

        if orig_hf_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = orig_hf_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)

        if orig_hf_home is not None:
            os.environ["HF_HOME"] = orig_hf_home
        else:
            os.environ.pop("HF_HOME", None)

        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Temp directory {temp_dir} cleaned up.")


if __name__ == "__main__":
    run_probe()
