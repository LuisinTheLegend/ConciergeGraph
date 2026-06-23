"""
main.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Ponto de entrada do sistema. Inicializa todos os componentes e
executa o servidor MCP via transport stdio.

Fluxo de inicialização:
    1. Logging configurado (console + timestamps)
    2. Storage: SqliteStore + EmbeddingManager + ChromaVectorStore
    3. Ingestão: ZoomSummarizer + IngestionManager
    4. Serviços: JanitorService (background thread)
    5. Servidor: GrafoConciergeServer (FastMCP)
    6. Shutdown gracioso: Janitor stop + DB close

Variáveis de ambiente:
    GRAFO_DB_PATH         → Caminho do SQLite (default: ./data/concierge.db)
    GRAFO_CHROMA_PATH     → Caminho do ChromaDB (default: ./data/chroma)
    GRAFO_CHROMA_COLLECTION → Nome da coleção (default: grafo_concierge)
    GRAFO_EMBEDDING_MODEL → Modelo de embedding (default: all-MiniLM-L6-v2)
    GRAFO_LLM_MODEL       → Modelo LLM para sumarização (default: gemini-2.0-flash)
    GRAFO_LLM_API_KEY     → Chave de API do LLM (opcional)
    GRAFO_JANITOR_INTERVAL → Intervalo do Janitor em segundos (default: 300)
    GRAFO_LOG_LEVEL       → Nível de log (default: INFO)
    GRAFO_TRANSPORT       → Transporte MCP: stdio ou sse (default: stdio)

Uso:
    python main.py
"""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import logging
import os
import signal
import sys

# ---------------------------------------------------------------------------
# 1. CONFIGURAÇÃO — Constantes e variáveis de ambiente
# ---------------------------------------------------------------------------

# Paths
DB_PATH = os.environ.get("GRAFO_DB_PATH", os.path.join("data", "concierge.db"))
CHROMA_PATH = os.environ.get("GRAFO_CHROMA_PATH", os.path.join("data", "chroma"))
CHROMA_COLLECTION = os.environ.get("GRAFO_CHROMA_COLLECTION", "grafo_concierge")

# Modelos
EMBEDDING_MODEL = os.environ.get("GRAFO_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_MODEL = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")

# Janitor
JANITOR_INTERVAL = int(os.environ.get("GRAFO_JANITOR_INTERVAL", "300"))
JANITOR_PROJECT_UUID = os.environ.get("GRAFO_JANITOR_PROJECT", "")

# Runtime
LOG_LEVEL = os.environ.get("GRAFO_LOG_LEVEL", "INFO").upper()
TRANSPORT = os.environ.get("GRAFO_TRANSPORT", "stdio")


# ---------------------------------------------------------------------------
# 2. LOGGING — Console com timestamps e níveis
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    """Configura logging global do Grafo Concierge."""
    numeric_level = getattr(logging, level, logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-7s │ %(name)-28s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: stderr (para não interferir com stdio do MCP)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.addHandler(handler)

    # Silencia loggers ruidosos de terceiros
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# 3. BOOTSTRAP — Inicialização de todos os componentes
# ---------------------------------------------------------------------------

logger = logging.getLogger("grafo-concierge.main")


def bootstrap():
    """Inicializa e retorna todos os componentes do sistema.

    Returns:
        Tuple com (server, janitor, store) para uso no main loop e shutdown.
    """
    # --- Garante que o diretório de dados exista ---
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    os.makedirs(CHROMA_PATH, exist_ok=True)

    # ── STORAGE ──────────────────────────────────────────────────────
    logger.info("Inicializando SqliteStore: %s", DB_PATH)
    from storage import SqliteStore
    store = SqliteStore(DB_PATH)

    logger.info("Inicializando EmbeddingManager: tier=FLASH")
    from storage import EmbeddingManager, EmbeddingTier
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)

    logger.info("Inicializando ChromaVectorStore: path=%s, collection=%s", CHROMA_PATH, CHROMA_COLLECTION)
    from storage import ChromaVectorStore
    vector_store = ChromaVectorStore(
        persist_dir=CHROMA_PATH,
        collection_name=CHROMA_COLLECTION,
        embedding_manager=embedder,
    )

    # ── INGESTÃO ─────────────────────────────────────────────────────
    logger.info("Inicializando ZoomSummarizer: model=%s", LLM_MODEL)
    from ingestion import ZoomSummarizer
    from ingestion.summarizer import LLMAdapter

    llm_adapter = LLMAdapter(
        model_name=LLM_MODEL,
        api_key=LLM_API_KEY or None,
    )
    summarizer = ZoomSummarizer(
        llm_adapter=llm_adapter,
        sqlite_store=store,
    )

    logger.info("Inicializando IngestionManager")
    from ingestion import IngestionManager
    ingestion_manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=summarizer,
    )

    # ── SERVIÇOS ─────────────────────────────────────────────────────
    logger.info("Inicializando JanitorService: interval=%ds", JANITOR_INTERVAL)
    from services import JanitorService
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector_store,
        ingestion_manager=ingestion_manager,
    )

    # ── FACHADA CENTRAL ──────────────────────────────────────────────
    logger.info("Inicializando Fachada Central GrafoConcierge")
    from core.middleware import GrafoConcierge
    concierge = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_manager,
    )

    # ── SERVIDOR MCP ─────────────────────────────────────────────────
    logger.info("Inicializando GrafoConciergeServer")
    from interface.mcp_server import GrafoConciergeServer
    server = GrafoConciergeServer(
        concierge=concierge,
        janitor=janitor,
    )

    logger.info("Bootstrap concluído — todos os componentes inicializados.")
    return server, janitor, store


# ---------------------------------------------------------------------------
# 4. MAIN — Loop principal com graceful shutdown
# ---------------------------------------------------------------------------

def main() -> None:
    """Ponto de entrada principal do Grafo Concierge."""

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

        # ── Janitor background (se há projeto configurado) ──
        if JANITOR_PROJECT_UUID:
            logger.info("Iniciando Janitor background para projeto: %s", JANITOR_PROJECT_UUID)
            janitor.start_background(JANITOR_PROJECT_UUID, interval=JANITOR_INTERVAL)
        else:
            logger.info("Janitor em modo idle (sem GRAFO_JANITOR_PROJECT definido).")

        # ── Servidor MCP ──
        logger.info("Iniciando servidor MCP (transport=%s)...", TRANSPORT)
        server.run(transport=TRANSPORT)

    except KeyboardInterrupt:
        logger.info("Interrupção recebida (Ctrl+C) — iniciando shutdown gracioso...")

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
