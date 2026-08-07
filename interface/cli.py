"""
interface/cli.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Terminal Interface (CLI) to manage Grafo Concierge
via Bash/PowerShell.

Commands:
    grafo-concierge register  → Registers a new project
    grafo-concierge mine      → Directory ingestion
    grafo-concierge search    → Hybrid Search v4
    grafo-concierge wakeup    → Consciousness reactivation
    grafo-concierge resume    → Context Compass
    grafo-concierge commit    → Changelog registration
    grafo-concierge load      → Node Lazy Load
    grafo-concierge status    → System health status
    grafo-concierge projects  → Lists projects

Usage:
    python -m interface.cli mine --path /projects/vortex --name vortex-pro
    python -m interface.cli search --query "JWT authentication" --project abc123
    python -m interface.cli wakeup --project abc123

Integration:
    Consumes core.middleware.GrafoConcierge as sole dependency.
    Bootstrap is automatically performed via _bootstrap_concierge().
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("grafo-concierge.cli")


# ---------------------------------------------------------------------------
# Bootstrap — Initializes the GrafoConcierge for CLI use
# ---------------------------------------------------------------------------

def _bootstrap_concierge():
    """Initializes the Central Facade for CLI usage.

    Uses the same environment variables as main.py.
    Returns a ready-to-use GrafoConcierge instance.
    """
    from dotenv import load_dotenv
    load_dotenv()

    from storage import SqliteStore, EmbeddingManager, EmbeddingTier, ChromaVectorStore
    from ingestion import IngestionManager, ZoomSummarizer
    from ingestion.summarizer import LLMAdapter
    from core.middleware import GrafoConcierge

    # Dynamic anchor: interface/ → project root
    _project_root = Path(__file__).parent.parent.resolve()

    def resolve_project_path(env_value: str, default_rel: str) -> str:
        val = env_value or default_rel
        path = Path(val)
        if path.is_absolute():
            return str(path)
        return str((_project_root / path).resolve())

    db_path = resolve_project_path(os.environ.get("GRAFO_DB_PATH", ""), "data/concierge.db")
    chroma_path = resolve_project_path(os.environ.get("GRAFO_CHROMA_PATH", ""), "data/chroma")
    chroma_collection = os.environ.get("GRAFO_CHROMA_COLLECTION", "grafo_concierge")
    llm_model = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
    llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
    llm_base_url = os.environ.get("GRAFO_LLM_BASE_URL", "")

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    os.makedirs(chroma_path, exist_ok=True)

    store = SqliteStore(db_path)
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)

    vector_backend = os.environ.get("GRAFO_VECTOR_BACKEND", "chroma").lower()
    if vector_backend == "qdrant":
        qdrant_url = os.environ.get("GRAFO_QDRANT_URL", "http://localhost:6333")
        qdrant_key = os.environ.get("GRAFO_QDRANT_API_KEY", "") or None
        from core.vector_backend import QdrantVectorStore
        vector_store = QdrantVectorStore(
            url=qdrant_url,
            api_key=qdrant_key,
            collection_name=chroma_collection,
            embedding_dimensions=embedder.dimensions,
        )
    else:
        vector_store = ChromaVectorStore(
            persist_dir=chroma_path,
            collection_name=chroma_collection,
            embedding_manager=embedder,
        )

    llm_adapter = LLMAdapter(
        model_name=llm_model,
        api_key=llm_api_key or None,
        base_url=llm_base_url or None,
    )
    summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)

    ingestion_manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=summarizer,
    )

    gc = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_manager,
        llm_adapter=llm_adapter,
    )

    return gc, store


def _print_json(data: dict) -> None:
    """Prints result formatted as JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_register(args, gc, store):
    """Registers a new project."""
    uuid = gc.register_project(
        folder_name=args.name,
        wing=args.wing,
        privacy_level=args.privacy or "PUBLIC",
        summary=args.summary,
    )
    print(f"Project registered: {args.name} → {uuid}")


def cmd_mine(args, gc, store):
    """Executes directory ingestion."""
    uuid = gc.register_project(folder_name=args.name)
    result = gc.mine(uuid, args.path, auto_tag=not args.no_tag)
    _print_json(result)


def cmd_search(args, gc, store):
    """Hybrid Search v4."""
    results = gc.hybrid_search(
        query=args.query,
        project_uuid=args.project,
        top_k=args.top_k,
        node_type=args.node_type,
        include_references=args.refs,
        all_wings=args.all_wings,
    )
    _print_json({"results_count": len(results), "results": results})


def cmd_wakeup(args, gc, store):
    """Consciousness reactivation."""
    result = gc.wake_up(args.project)
    _print_json(result)


def cmd_resume(args, gc, store):
    """Context Compass."""
    resume = gc.get_resume(args.project)
    print(resume)


def cmd_commit(args, gc, store):
    """Commit registration."""
    pointers = args.pointers.split(",") if args.pointers else []
    commit_id = gc.commit_memory(
        project_uuid=args.project,
        phase=args.phase,
        technical_changes=args.changes,
        updated_pointers=pointers,
    )
    print(f"Commit registered: id={commit_id}")


def cmd_load(args, gc, store):
    """Lazy Load of a node."""
    result = gc.lazy_load(args.node_id)
    _print_json(result)


def cmd_status(args, gc, store):
    """System status."""
    if args.project:
        result = gc.status(args.project)
    else:
        projects = store.list_projects()
        result = {
            "system": "Grafo Concierge v3.8.0",
            "total_projects": len(projects),
            "projects": [
                {"uuid": p["uuid"], "name": p.get("folder_name", ""), "wing": p.get("primary_wing", "geral")}
                for p in projects
            ],
        }
    _print_json(result)


def cmd_projects(args, gc, store):
    """Lists all projects."""
    projects = store.list_projects()
    if not projects:
        print("No projects registered.")
        return

    print(f"{'UUID':<38} {'Name':<25} {'Wing':<20} {'Privacy':<12}")
    print("-" * 95)
    for p in projects:
        print(
            f"{p['uuid']:<38} {p.get('folder_name', ''):<25} "
            f"{p.get('primary_wing', 'general'):<20} {p.get('privacy_level', 'PUBLIC'):<12}"
        )


def cmd_sync_vector(args, gc, store):
    """Synchronizes and reconciles missing embeddings in the active vector store manually."""
    from services.janitor import JanitorService, MaintenanceReport
    
    # Initializes local JanitorService
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=gc._vector,
        ingestion_manager=gc._ingestion,
    )
    
    projects_to_sync = []
    if args.project:
        projects_to_sync.append(args.project)
    else:
        all_projects = store.list_projects()
        projects_to_sync = [p["uuid"] for p in all_projects]
        
    if not projects_to_sync:
        print("No registered projects found to synchronize.")
        return
        
    print(f"Starting manual batch vector reconciliation for {len(projects_to_sync)} projects...")
    for p_uuid in projects_to_sync:
        p_name = next((p["folder_name"] for p in store.list_projects() if p["uuid"] == p_uuid), p_uuid)
        print(f"-> Synchronizing project: {p_name} ({p_uuid})...")
        report = MaintenanceReport()
        # Executes bidirectional reconciliation (deletes orphans and generates missing)
        janitor._sync_vectors(p_uuid, report)
        if report.errors:
            print(f"   [ERROR] {report.errors[0]}")
        else:
            print(f"   [OK] Vector reconciliation completed successfully.")
    print("Reconciliation and synchronization finished!")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="grafo-concierge",
        description="Grafo Concierge v3.8.0 — Sovereign Memory for AI Agents",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available command")

    # --- register ---
    p_register = subparsers.add_parser("register", help="Registers a new project")
    p_register.add_argument("--name", required=True, help="Project name")
    p_register.add_argument("--wing", default=None, help="Primary Wing")
    p_register.add_argument("--privacy", default="PUBLIC", help="Privacy level")
    p_register.add_argument("--summary", default=None, help="Project description")

    # --- mine ---
    p_mine = subparsers.add_parser("mine", help="Directory ingestion")
    p_mine.add_argument("--path", required=True, help="Directory path")
    p_mine.add_argument("--name", required=True, help="Project name")
    p_mine.add_argument("--no-tag", action="store_true", help="Disables auto-tag")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Hybrid Search v4")
    p_search.add_argument("--query", required=True, help="Search text")
    p_search.add_argument("--project", required=True, help="Project UUID")
    p_search.add_argument("--top-k", type=int, default=10, help="Maximum results")
    p_search.add_argument("--node-type", default=None, help="Node type filter")
    p_search.add_argument("--refs", action="store_true", help="Include Reference Wings")
    p_search.add_argument("--all-wings", action="store_true", help="Search in all wings")

    # --- wakeup ---
    p_wakeup = subparsers.add_parser("wakeup", help="Consciousness reactivation")
    p_wakeup.add_argument("--project", required=True, help="Project UUID")

    # --- resume ---
    p_resume = subparsers.add_parser("resume", help="Context Compass")
    p_resume.add_argument("--project", required=True, help="Project UUID")

    # --- commit ---
    p_commit = subparsers.add_parser("commit", help="Registers a memory commit")
    p_commit.add_argument("--project", required=True, help="Project UUID")
    p_commit.add_argument("--phase", required=True, help="Current phase")
    p_commit.add_argument("--changes", required=True, help="Technical changes")
    p_commit.add_argument("--pointers", required=True, help="Pointers (comma-separated)")

    # --- load ---
    p_load = subparsers.add_parser("load", help="Lazy Load of a node")
    p_load.add_argument("--node-id", type=int, required=True, help="Node ID")

    # --- status ---
    p_status = subparsers.add_parser("status", help="System status")
    p_status.add_argument("--project", default=None, help="Project UUID (optional)")

    # --- projects ---
    subparsers.add_parser("projects", help="Lists all projects")

    # --- sync-vector ---
    p_sync_vector = subparsers.add_parser("sync-vector", help="Synchronizes and reconciles missing embeddings in the active vector store manually")
    p_sync_vector.add_argument("--project", default=None, help="UUID of a specific project to synchronize (optional)")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "register": cmd_register,
    "mine": cmd_mine,
    "search": cmd_search,
    "wakeup": cmd_wakeup,
    "resume": cmd_resume,
    "commit": cmd_commit,
    "load": cmd_load,
    "status": cmd_status,
    "projects": cmd_projects,
    "sync-vector": cmd_sync_vector,
}


def main():
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup minimal logging for CLI
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Bootstrap
    try:
        gc, store = _bootstrap_concierge()
    except Exception as e:
        print(f"Error initializing Grafo Concierge: {e}", file=sys.stderr)
        sys.exit(1)

    # Executes command
    handler = COMMAND_MAP.get(args.command)
    if handler:
        try:
            handler(args, gc, store)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            try:
                store.close()
            except Exception:
                pass
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
