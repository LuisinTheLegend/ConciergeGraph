"""
interface/cli.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Interface de Terminal (CLI) para gerenciar o Grafo Concierge
via Bash/PowerShell.

Comandos:
    grafo-concierge register  → Registra novo projeto
    grafo-concierge mine      → Ingestão de diretório
    grafo-concierge search    → Busca Híbrida v4
    grafo-concierge wakeup    → Reativação de consciência
    grafo-concierge resume    → Bússola de Contexto
    grafo-concierge commit    → Registro de alterações
    grafo-concierge load      → Lazy Load de nó
    grafo-concierge status    → Saúde do sistema
    grafo-concierge projects  → Lista projetos

Uso:
    python -m interface.cli mine --path /projetos/vortex --name vortex-pro
    python -m interface.cli search --query "autenticação JWT" --project abc123
    python -m interface.cli wakeup --project abc123

Integração:
    Consome core.middleware.GrafoConcierge como única dependência.
    Bootstrap é feito automaticamente via _bootstrap_concierge().
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger("grafo-concierge.cli")


# ---------------------------------------------------------------------------
# Bootstrap — Inicializa o GrafoConcierge para uso via CLI
# ---------------------------------------------------------------------------

def _bootstrap_concierge():
    """Inicializa a Fachada Central para uso na CLI.

    Usa as mesmas variáveis de ambiente do main.py.
    Retorna uma instância de GrafoConcierge pronta para uso.
    """
    from dotenv import load_dotenv
    load_dotenv()

    from storage import SqliteStore, EmbeddingManager, EmbeddingTier, ChromaVectorStore
    from ingestion import IngestionManager, ZoomSummarizer
    from ingestion.summarizer import LLMAdapter
    from core.middleware import GrafoConcierge

    db_path = os.environ.get("GRAFO_DB_PATH", os.path.join("data", "concierge.db"))
    chroma_path = os.environ.get("GRAFO_CHROMA_PATH", os.path.join("data", "chroma"))
    chroma_collection = os.environ.get("GRAFO_CHROMA_COLLECTION", "grafo_concierge")
    llm_model = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
    llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
    llm_base_url = os.environ.get("GRAFO_LLM_BASE_URL", "")

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    os.makedirs(chroma_path, exist_ok=True)

    store = SqliteStore(db_path)
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
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
    )

    return gc, store


def _print_json(data: dict) -> None:
    """Imprime resultado formatado como JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Comandos CLI
# ---------------------------------------------------------------------------

def cmd_register(args, gc, store):
    """Registra um novo projeto."""
    uuid = gc.register_project(
        folder_name=args.name,
        wing=args.wing,
        privacy_level=args.privacy or "PUBLIC",
        summary=args.summary,
    )
    print(f"Projeto registrado: {args.name} → {uuid}")


def cmd_mine(args, gc, store):
    """Executa ingestão de um diretório."""
    uuid = gc.register_project(folder_name=args.name)
    result = gc.mine(uuid, args.path, auto_tag=not args.no_tag)
    _print_json(result)


def cmd_search(args, gc, store):
    """Busca Híbrida v4."""
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
    """Reativação de consciência."""
    result = gc.wake_up(args.project)
    _print_json(result)


def cmd_resume(args, gc, store):
    """Bússola de Contexto."""
    resume = gc.get_resume(args.project)
    print(resume)


def cmd_commit(args, gc, store):
    """Registro de commit."""
    pointers = args.pointers.split(",") if args.pointers else []
    commit_id = gc.commit_memory(
        project_uuid=args.project,
        phase=args.phase,
        technical_changes=args.changes,
        updated_pointers=pointers,
    )
    print(f"Commit registrado: id={commit_id}")


def cmd_load(args, gc, store):
    """Lazy Load de um nó."""
    result = gc.lazy_load(args.node_id)
    _print_json(result)


def cmd_status(args, gc, store):
    """Status do sistema."""
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
    """Lista todos os projetos."""
    projects = store.list_projects()
    if not projects:
        print("Nenhum projeto registrado.")
        return

    print(f"{'UUID':<38} {'Nome':<25} {'Ala':<20} {'Privacy':<12}")
    print("-" * 95)
    for p in projects:
        print(
            f"{p['uuid']:<38} {p.get('folder_name', ''):<25} "
            f"{p.get('primary_wing', 'geral'):<20} {p.get('privacy_level', 'PUBLIC'):<12}"
        )


# ---------------------------------------------------------------------------
# Parser de argumentos
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos do CLI."""

    parser = argparse.ArgumentParser(
        prog="grafo-concierge",
        description="Grafo Concierge v3.8.0 — Memória Soberana para Agentes IA",
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando disponível")

    # --- register ---
    p_register = subparsers.add_parser("register", help="Registra novo projeto")
    p_register.add_argument("--name", required=True, help="Nome do projeto")
    p_register.add_argument("--wing", default=None, help="Primary Wing")
    p_register.add_argument("--privacy", default="PUBLIC", help="Nível de privacidade")
    p_register.add_argument("--summary", default=None, help="Descrição do projeto")

    # --- mine ---
    p_mine = subparsers.add_parser("mine", help="Ingestão de diretório")
    p_mine.add_argument("--path", required=True, help="Caminho do diretório")
    p_mine.add_argument("--name", required=True, help="Nome do projeto")
    p_mine.add_argument("--no-tag", action="store_true", help="Desabilita auto-tag")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Busca Híbrida v4")
    p_search.add_argument("--query", required=True, help="Texto de busca")
    p_search.add_argument("--project", required=True, help="UUID do projeto")
    p_search.add_argument("--top-k", type=int, default=10, help="Máximo de resultados")
    p_search.add_argument("--node-type", default=None, help="Filtro de tipo de nó")
    p_search.add_argument("--refs", action="store_true", help="Incluir Reference Wings")
    p_search.add_argument("--all-wings", action="store_true", help="Buscar em todas as alas")

    # --- wakeup ---
    p_wakeup = subparsers.add_parser("wakeup", help="Reativação de consciência")
    p_wakeup.add_argument("--project", required=True, help="UUID do projeto")

    # --- resume ---
    p_resume = subparsers.add_parser("resume", help="Bússola de Contexto")
    p_resume.add_argument("--project", required=True, help="UUID do projeto")

    # --- commit ---
    p_commit = subparsers.add_parser("commit", help="Registra commit de memória")
    p_commit.add_argument("--project", required=True, help="UUID do projeto")
    p_commit.add_argument("--phase", required=True, help="Fase atual")
    p_commit.add_argument("--changes", required=True, help="Mudanças técnicas")
    p_commit.add_argument("--pointers", required=True, help="Ponteiros (separados por vírgula)")

    # --- load ---
    p_load = subparsers.add_parser("load", help="Lazy Load de um nó")
    p_load.add_argument("--node-id", type=int, required=True, help="ID do nó")

    # --- status ---
    p_status = subparsers.add_parser("status", help="Status do sistema")
    p_status.add_argument("--project", default=None, help="UUID do projeto (opcional)")

    # --- projects ---
    subparsers.add_parser("projects", help="Lista todos os projetos")

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
}


def main():
    """Ponto de entrada do CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging mínimo para CLI
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Bootstrap
    try:
        gc, store = _bootstrap_concierge()
    except Exception as e:
        print(f"Erro ao inicializar Grafo Concierge: {e}", file=sys.stderr)
        sys.exit(1)

    # Executa comando
    handler = COMMAND_MAP.get(args.command)
    if handler:
        try:
            handler(args, gc, store)
        except Exception as e:
            print(f"Erro: {e}", file=sys.stderr)
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
