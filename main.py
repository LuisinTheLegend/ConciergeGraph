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
    GRAFO_LLM_MODEL       → LLM model for summarization (default: gemini-2.0-flash; use 'none' to disable)
    GRAFO_LLM_PROVIDER    → Explicit LLM provider: gemini, openai, openai-compatible, openrouter, none (optional)
    GRAFO_LLM_API_KEY     → LLM API Key (optional)
    GRAFO_JANITOR_INTERVAL → Janitor interval in seconds (default: 300)
    GRAFO_LOG_LEVEL       → Log level (default: INFO)
    GRAFO_TRANSPORT       → MCP transport: stdio or sse (default: stdio)
    GRAFO_STDIN_DECOUPLE  → Desacopla fd 0 no Windows para transporte stdio (default: 1)

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
LLM_PROVIDER = os.environ.get("GRAFO_LLM_PROVIDER", "")
LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("GRAFO_LLM_BASE_URL", "")

# Janitor
JANITOR_INTERVAL = int(os.environ.get("GRAFO_JANITOR_INTERVAL", "300"))
JANITOR_PROJECT_UUID = os.environ.get("GRAFO_JANITOR_PROJECT", "")

# Runtime
LOG_LEVEL = os.environ.get("GRAFO_LOG_LEVEL", "INFO").upper()
TRANSPORT = os.environ.get("GRAFO_TRANSPORT", "stdio")


# ---------------------------------------------------------------------------
# 2. LOGGING — Console with timestamps, levels, and secret redaction (F4-021)
# ---------------------------------------------------------------------------

import re as _re

_LOG_SECRET_PATTERNS: list[tuple[_re.Pattern[str], str]] = [
    (_re.compile(r'(Bearer\s+)[^\s"\',;)\]}]+', _re.IGNORECASE), r"\1[REDACTED]"),
    (_re.compile(r"AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"), "[REDACTED]"),
    (_re.compile(r"AIza[\w-]{10,}"), "[REDACTED]"),
    (_re.compile(r"sk-[\w*-]{6,}"), "[REDACTED]"),
    (_re.compile(r"\*{6,}\w{0,8}\."), "[REDACTED]"),
]


def redact_log_secrets(text: str) -> str:
    """Redige chaves de API e tokens Bearer em mensagens de log e tracebacks."""
    if not text or not isinstance(text, str):
        return text

    result = text
    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY"):
        secret_val = os.environ.get(env_var, "").strip()
        if len(secret_val) >= 8 and secret_val in result:
            result = result.replace(secret_val, "[REDACTED]")

    for pattern, replacement in _LOG_SECRET_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


class _SecretRedactingLogRecord(logging.LogRecord):
    """LogRecord que garante redação em getMessage() e em exceções formatadas
    para qualquer Handler (incluindo StreamHandler e RichHandler do FastMCP).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._redacted_exc_text: str | None = None
        if self.exc_info and isinstance(self.exc_info, tuple) and len(self.exc_info) == 3:
            exc_val = self.exc_info[1]
            if exc_val is not None and getattr(exc_val, "args", None):
                try:
                    exc_val.args = tuple(
                        redact_log_secrets(a) if isinstance(a, str) else a
                        for a in exc_val.args
                    )
                except Exception:
                    pass

    def getMessage(self) -> str:
        return redact_log_secrets(super().getMessage())

    @property
    def exc_text(self) -> str | None:
        return self._redacted_exc_text

    @exc_text.setter
    def exc_text(self, value: str | None) -> None:
        self._redacted_exc_text = redact_log_secrets(value) if isinstance(value, str) else value


def _secret_redacting_record_factory(*args, **kwargs) -> logging.LogRecord:
    return _SecretRedactingLogRecord(*args, **kwargs)


_secret_redacting_record_factory._grafo_secret_redacting = True  # type: ignore[attr-defined]


def setup_logging(level: str = "INFO") -> None:
    """Configures global logging for Grafo Concierge with idempotent secret redaction."""
    numeric_level = getattr(logging, level, logging.INFO)

    current_factory = logging.getLogRecordFactory()
    if not getattr(current_factory, "_grafo_secret_redacting", False):
        logging.setLogRecordFactory(_secret_redacting_record_factory)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-7s │ %(name)-28s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: stderr (so it does not interfere with MCP stdio)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(numeric_level)
    handler.setFormatter(formatter)

    # Root logger (idempotent handler setup)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
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


def decouple_stdin_from_fd0() -> bool:
    """Desacopla o fd 0 de sys.stdin no Windows para evitar travamento em imports nativos tardios.

    - PROVADO (ver scratch/evidencia_4_2e e scratch/evidencia_4_2f): com um leitor
      bloqueado em fd 0 do stdin (ex.: sys.stdin.buffer.readline()), o primeiro
      import de bibliotecas nativas (scipy.special, openblas, torch) trava no
      Windows; desacoplar o fd 0 (redirecionando fd 0 para os.devnull e envolvendo
      o descritor duplicado fd2 em sys.stdin) elimina o travamento preservando o
      canal stdio bidirecional do MCP.
    - HIPÓTESE NÃO DEMONSTRADA: o mecanismo interno do Windows (lock do CRT / loader).
    """
    if sys.platform != "win32":
        return False

    decouple_env = os.environ.get("GRAFO_STDIN_DECOUPLE", "1").strip().lower()
    if decouple_env in ("0", "false", "off"):
        return False

    nul = -1
    try:
        nul = os.open(os.devnull, os.O_RDONLY)
        fd2 = os.dup(0)
        os.dup2(nul, 0)
        os.close(nul)
        nul = -1
        sys.stdin = open(fd2, "r", encoding="utf-8", errors="replace", closefd=False)
        logger.info("Decoupled sys.stdin from fd 0 (allocated duplicate fd=%d)", fd2)
        return True
    except Exception as exc:
        if nul >= 0:
            try:
                os.close(nul)
            except OSError:
                pass
        logger.warning("Failed to decouple sys.stdin from fd 0: %s", exc)
        return False


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
        provider=LLM_PROVIDER or None,
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
        llm_adapter=llm_adapter,
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

    # ── Stdio Decouple (Windows only, avoids late import hang on fd 0) ──
    if TRANSPORT == "stdio":
        decouple_stdin_from_fd0()

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
        logger.critical("Fatal error during execution: %s", e, exc_info=True)
        sys.exit(1)

    finally:
        # ── Graceful Shutdown ──
        logger.info("Graceful shutdown initiated...")

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
