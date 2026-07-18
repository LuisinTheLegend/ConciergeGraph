"""
main.py — Grafo Concierge v3.8.0 (Absolute Solidity)

System entry point. Initializes all components and
runs the MCP server via stdio transport.

Initialization flow:
    1. Logging configured (console + timestamps)
    2. Storage: SqliteStore + EmbeddingManager + ChromaVectorStore
    3. Ingestion: ZoomSummarizer + IngestionManager
    4. Services: JanitorService (background thread)
    5. Server: GrafoConciergeServer (FastMCP)
    6. Graceful shutdown: Janitor stop + DB close

Environment variables:
    GRAFO_DB_PATH         → SQLite path (default: ./data/concierge.db)
    GRAFO_CHROMA_PATH     → ChromaDB path (default: ./data/chroma)
    GRAFO_CHROMA_COLLECTION → Collection name (default: grafo_concierge)
    GRAFO_EMBEDDING_MODEL → Embedding model (default: all-MiniLM-L6-v2)
    GRAFO_LLM_MODEL       → LLM model for summarization (default: gemini-2.0-flash)
    GRAFO_LLM_API_KEY     → LLM API Key (optional)
    GRAFO_JANITOR_INTERVAL → Janitor interval in seconds (default: 300)
    GRAFO_LOG_LEVEL       → Log level (default: INFO)
    GRAFO_TRANSPORT       → MCP transport: stdio or sse (default: stdio)

Usage:
    python main.py
"""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import logging
import os
import signal
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. CONFIGURATION — Constants and environment variables
# ---------------------------------------------------------------------------

# Paths — anchored at the project root, never relative to the process CWD
PROJECT_ROOT = Path(__file__).parent.resolve()

def resolve_project_path(env_value: str, default_rel: str) -> str:
    val = env_value or default_rel
    path = Path(val)
    if path.is_absolute():
        return str(path)
    return str((PROJECT_ROOT / path).resolve())

DB_PATH = resolve_project_path(os.environ.get("GRAFO_DB_PATH", ""), "data/concierge.db")
CHROMA_PATH = resolve_project_path(os.environ.get("GRAFO_CHROMA_PATH", ""), "data/chroma")
CHROMA_COLLECTION = os.environ.get("GRAFO_CHROMA_COLLECTION", "grafo_concierge")

# Models
EMBEDDING_MODEL = os.environ.get("GRAFO_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_MODEL = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("GRAFO_LLM_BASE_URL", "")

# Janitor
JANITOR_INTERVAL = int(os.environ.get("GRAFO_JANITOR_INTERVAL", "300"))
JANITOR_PROJECT_UUID = os.environ.get("GRAFO_JANITOR_PROJECT", "")

# Runtime
LOG_LEVEL = os.environ.get("GRAFO_LOG_LEVEL", "INFO").upper()
TRANSPORT = os.environ.get("GRAFO_TRANSPORT", "stdio")


# ---------------------------------------------------------------------------
# 2. LOGGING — Console with timestamps and levels
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    """Configures global logging for Grafo Concierge."""
    numeric_level = getattr(logging, level, logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-7s │ %(name)-28s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: stderr (so it does not interfere with MCP stdio)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# 3. BOOTSTRAP — Initialization of all components
# ---------------------------------------------------------------------------

logger = logging.getLogger("grafo-concierge.main")


def bootstrap():
    """Initializes and returns all system components.

    Returns:
        Tuple containing (server, janitor, store) for use in the main loop and shutdown.
    """
    # --- Ensures the data directory exists ---
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    os.makedirs(CHROMA_PATH, exist_ok=True)

    # ── STORAGE ──────────────────────────────────────────────────────
    logger.info("Initializing SqliteStore: %s", DB_PATH)
    from storage import SqliteStore
    store = SqliteStore(DB_PATH)

    logger.info("Initializing EmbeddingManager: tier=FLASH")
    from storage import EmbeddingManager, EmbeddingTier
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)

    vector_backend = os.environ.get("GRAFO_VECTOR_BACKEND", "chroma").lower()
    if vector_backend == "qdrant":
        qdrant_url = os.environ.get("GRAFO_QDRANT_URL", "http://localhost:6333")
        qdrant_key = os.environ.get("GRAFO_QDRANT_API_KEY", "") or None
        logger.info("Initializing QdrantVectorStore: url=%s, collection=%s", qdrant_url, CHROMA_COLLECTION)
        from core.vector_backend import QdrantVectorStore
        vector_store = QdrantVectorStore(
            url=qdrant_url,
            api_key=qdrant_key,
            collection_name=CHROMA_COLLECTION,
            embedding_dimensions=embedder.dimensions,
        )
    else:
        logger.info("Initializing ChromaVectorStore: path=%s, collection=%s", CHROMA_PATH, CHROMA_COLLECTION)
        from storage import ChromaVectorStore
        vector_store = ChromaVectorStore(
            persist_dir=CHROMA_PATH,
            collection_name=CHROMA_COLLECTION,
            embedding_manager=embedder,
        )

    # ── INGESTION ────────────────────────────────────────────────────
    logger.info("Initializing ZoomSummarizer: model=%s", LLM_MODEL)
    from ingestion import ZoomSummarizer
    from ingestion.summarizer import LLMAdapter

    llm_adapter = LLMAdapter(
        model_name=LLM_MODEL,
        api_key=LLM_API_KEY or None,
        base_url=LLM_BASE_URL or None,
    )
    summarizer = ZoomSummarizer(
        llm_adapter=llm_adapter,
        sqlite_store=store,
    )

    logger.info("Initializing IngestionManager")
    from ingestion import IngestionManager
    ingestion_manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=summarizer,
    )

    # ── SERVICES ─────────────────────────────────────────────────────
    logger.info("Initializing JanitorService: interval=%ds", JANITOR_INTERVAL)
    from services import JanitorService
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector_store,
        ingestion_manager=ingestion_manager,
    )

    # ── CENTRAL FACADE ───────────────────────────────────────────────
    logger.info("Initializing GrafoConcierge Central Facade")
    from core.middleware import GrafoConcierge
    concierge = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_manager,
    )

    # ── MCP SERVER ───────────────────────────────────────────────────
    logger.info("Initializing GrafoConciergeServer")
    from interface.mcp_server import GrafoConciergeServer
    server = GrafoConciergeServer(
        concierge=concierge,
        janitor=janitor,
    )

    logger.info("Bootstrap complete — all components initialized.")
    return server, janitor, store


# ---------------------------------------------------------------------------
# 4. MAIN — Main loop with graceful shutdown
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point of Grafo Concierge."""

    # ── Logging ──
    setup_logging(LOG_LEVEL)

    logger.info("=" * 60)
    logger.info("  Grafo Concierge v3.8.0 — Absolute Solidity")
    logger.info("=" * 60)
    logger.info("  DB:       %s", DB_PATH)
    logger.info("  ChromaDB: %s (%s)", CHROMA_PATH, CHROMA_COLLECTION)
    logger.info("  Embedding: %s", EMBEDDING_MODEL)
    logger.info("  LLM:      %s", LLM_MODEL)
    logger.info("  Janitor:  %ds", JANITOR_INTERVAL)
    logger.info("  Transport: %s", TRANSPORT)
    logger.info("  Log Level: %s", LOG_LEVEL)
    logger.info("=" * 60)

    server = None
    janitor = None
    store = None

    try:
        # ── Bootstrap ──
        server, janitor, store = bootstrap()

        # ── Background Janitor (if project is configured) ──
        if JANITOR_PROJECT_UUID:
            logger.info("Starting background Janitor for project: %s", JANITOR_PROJECT_UUID)
            janitor.start_background(JANITOR_PROJECT_UUID, interval=JANITOR_INTERVAL)
        else:
            logger.info("Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).")

        # ── MCP Server ──
        logger.info("Starting MCP server (transport=%s)...", TRANSPORT)
        server.run(transport=TRANSPORT)

    except KeyboardInterrupt:
        logger.info("Interrupt received (Ctrl+C) — starting graceful shutdown...")

    except Exception as e:
        logger.critical("Erro fatal durante execução: %s", e, exc_info=True)
        sys.exit(1)

    finally:
        # ── Graceful Shutdown ──
        logger.info("Shutdown gracioso iniciado...")

        if janitor is not None:
            try:
                janitor.stop_background(timeout=5.0)
                logger.info("Janitor encerrado.")
            except Exception as e:
                logger.warning("Erro ao parar Janitor: %s", e)

        if store is not None:
            try:
                store.close()
                logger.info("SqliteStore encerrado.")
            except Exception as e:
                logger.warning("Erro ao fechar SqliteStore: %s", e)

        logger.info("=" * 60)
        logger.info("  Grafo Concierge encerrado com sucesso.")
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
