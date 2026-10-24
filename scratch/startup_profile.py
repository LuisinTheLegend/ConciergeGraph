"""
scratch/startup_profile.py — Instrumentacao detalhada do tempo de inicializacao do Grafo Concierge.

Mede com time.perf_counter():
  1. Tempo de import de cada componente e dependencias pesadas.
  2. Tempo de instanciacao de cada classe do bootstrap() (main.py).
  3. Tempo de carga do modelo de embedding local vs inferencia do 1o embedding.
Usa DB e ChromaDB temporarios isolados (NUNCA toca em data/).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_profile() -> dict[str, float]:
    measurements: dict[str, float] = {}

    tmp_dir = tempfile.mkdtemp(prefix="grafo_profile_")
    db_path = os.path.join(tmp_dir, "profile_concierge.db")
    chroma_path = os.path.join(tmp_dir, "profile_chroma")

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "profile_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LOG_LEVEL"] = "WARNING"

    print("=" * 75)
    print("GRAFO CONCIERGE — STARTUP PROFILE (main.bootstrap)")
    print("=" * 75)
    print(f"Python:       {sys.version}")
    print(f"Temp DB:      {db_path}")
    print(f"Temp Chroma:  {chroma_path}")
    print("=" * 75)

    total_start = time.perf_counter()

    # -------------------------------------------------------------
    # 1. IMPORTS INDIVIDUAIS
    # -------------------------------------------------------------
    def _measure_import(name: str, import_fn) -> None:
        t0 = time.perf_counter()
        import_fn()
        t1 = time.perf_counter()
        measurements[f"import: {name}"] = t1 - t0

    # Medir imports de baixo nivel que suspeitamos serem pesados
    _measure_import("chromadb (top-level)", lambda: __import__("chromadb"))
    _measure_import("torch (top-level)", lambda: __import__("torch"))
    _measure_import("sentence_transformers", lambda: __import__("sentence_transformers"))

    # Imports dos modulos do projeto
    _measure_import("storage.store", lambda: __import__("storage.store"))
    _measure_import("storage.vector_store", lambda: __import__("storage.vector_store"))
    _measure_import("storage (package)", lambda: __import__("storage"))
    _measure_import("ingestion.summarizer", lambda: __import__("ingestion.summarizer"))
    _measure_import("ingestion.orchestrator", lambda: __import__("ingestion.orchestrator"))
    _measure_import("services.janitor", lambda: __import__("services.janitor"))
    _measure_import("core.middleware", lambda: __import__("core.middleware"))
    _measure_import("interface.mcp_server", lambda: __import__("interface.mcp_server"))

    # -------------------------------------------------------------
    # 2. INSTANCIACAO DOS COMPONENTES (main.bootstrap)
    # -------------------------------------------------------------
    from storage.store import SqliteStore
    from storage.vector_store import ChromaVectorStore, EmbeddingManager, EmbeddingTier
    from ingestion.summarizer import ZoomSummarizer, LLMAdapter
    from ingestion.orchestrator import IngestionManager
    from services.janitor import JanitorService
    from core.middleware import GrafoConcierge
    from interface.mcp_server import GrafoConciergeServer

    # 2.1 SqliteStore
    t0 = time.perf_counter()
    store = SqliteStore(db_path)
    t1 = time.perf_counter()
    measurements["instantiate: SqliteStore"] = t1 - t0

    # 2.2 EmbeddingManager
    t0 = time.perf_counter()
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    t1 = time.perf_counter()
    measurements["instantiate: EmbeddingManager(FLASH)"] = t1 - t0

    # 2.3 ChromaVectorStore
    t0 = time.perf_counter()
    vector_store = ChromaVectorStore(
        persist_dir=chroma_path,
        collection_name="profile_collection",
        embedding_manager=embedder,
    )
    t1 = time.perf_counter()
    measurements["instantiate: ChromaVectorStore"] = t1 - t0

    # 2.4 ZoomSummarizer
    t0 = time.perf_counter()
    llm_adapter = LLMAdapter(model_name="gemini-2.0-flash")
    summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)
    t1 = time.perf_counter()
    measurements["instantiate: ZoomSummarizer"] = t1 - t0

    # 2.5 IngestionManager
    t0 = time.perf_counter()
    ingestion_manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=summarizer,
    )
    t1 = time.perf_counter()
    measurements["instantiate: IngestionManager"] = t1 - t0

    # 2.6 JanitorService
    t0 = time.perf_counter()
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector_store,
        ingestion_manager=ingestion_manager,
    )
    t1 = time.perf_counter()
    measurements["instantiate: JanitorService"] = t1 - t0

    # 2.7 GrafoConcierge (Facade)
    t0 = time.perf_counter()
    concierge = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_manager,
        llm_adapter=llm_adapter,
    )
    t1 = time.perf_counter()
    measurements["instantiate: GrafoConcierge (Facade)"] = t1 - t0

    # 2.8 GrafoConciergeServer + 31 ferramentas
    t0 = time.perf_counter()
    server = GrafoConciergeServer(
        concierge=concierge,
        janitor=janitor,
    )
    t1 = time.perf_counter()
    measurements["instantiate: GrafoConciergeServer (31 tools)"] = t1 - t0

    bootstrap_total = time.perf_counter() - total_start
    measurements["TOTAL: bootstrap() completo"] = bootstrap_total

    # -------------------------------------------------------------
    # 3. PRIMEIRO EMBEDDING (CARGA DO MODELO VS INFERENCIA)
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    embedder._load_model()
    t1 = time.perf_counter()
    measurements["embedding: _load_model() (carga de pesos)"] = t1 - t0

    t0 = time.perf_counter()
    first_vec = embedder.embed("teste de inicializacao de embedding")
    t1 = time.perf_counter()
    measurements["embedding: 1a inferencia (embed_query)"] = t1 - t0

    # Fechar recursos
    store.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # TABELA FORMATADA
    # -------------------------------------------------------------
    print(f"{'Etapa / Operacao':<48} | {'Tempo (s)':>10} | {'% Total':>8}")
    print("-" * 75)
    for step, duration in measurements.items():
        pct = (duration / bootstrap_total) * 100 if bootstrap_total > 0 else 0
        if step.startswith("TOTAL"):
            print("-" * 75)
            print(f"{step:<48} | {duration:>10.4f}s | {pct:>7.1f}%")
            print("-" * 75)
        elif step.startswith("embedding"):
            print(f"{step:<48} | {duration:>10.4f}s | {'(pos)':>8}")
        else:
            print(f"{step:<48} | {duration:>10.4f}s | {pct:>7.1f}%")
    print("=" * 75)

    return measurements


if __name__ == "__main__":
    run_profile()
