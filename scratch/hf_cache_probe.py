"""
scratch/hf_cache_probe.py — Investiga cache local do Hugging Face e comportamento com HF_HUB_OFFLINE=1.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def probe_hf_cache() -> None:
    print("=" * 75)
    print("INVESTIGACAO DE CACHE E COMPORTAMENTO COM HF_HUB_OFFLINE=1 (C4)")
    print("=" * 75)

    # 1. Localizar cache padrao do Hugging Face
    hf_home = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface")
    hub_cache = Path(hf_home) / "hub"
    model_dir_name = "models--sentence-transformers--all-MiniLM-L6-v2"
    model_cache_path = hub_cache / model_dir_name

    print(f"HF_HOME:          {hf_home}")
    print(f"Hub Cache Dir:    {hub_cache}")
    print(f"Model Cache Dir:  {model_cache_path}")

    if model_cache_path.is_dir():
        total_size = sum(f.stat().st_size for f in model_cache_path.rglob("*") if f.is_file())
        file_count = sum(1 for f in model_cache_path.rglob("*") if f.is_file())
        print(f"Status do Modelo: PRESENTE NO CACHE LOCAL")
        print(f"Total de Arquivos:{file_count}")
        print(f"Tamanho em Disco: {total_size / (1024 * 1024):.2f} MB ({total_size:,} bytes)")
        print("\nArquivos principais no cache:")
        for f in model_cache_path.rglob("*"):
            if f.is_file() and not f.is_symlink():
                print(f"  - {f.name:30} ({f.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"Status do Modelo: NAO ENCONTRADO EM {model_cache_path}")

    print("\n" + "-" * 75)
    print("TESTE 1: main.bootstrap() com HF_HUB_OFFLINE=1")
    print("-" * 75)

    # Ativa modo offline estrito
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    tmp_dir = tempfile.mkdtemp(prefix="grafo_c4_offline_")
    db_path = os.path.join(tmp_dir, "offline_concierge.db")
    chroma_path = os.path.join(tmp_dir, "offline_chroma")

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "c4_offline_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LOG_LEVEL"] = "WARNING"

    from storage.store import SqliteStore
    from storage.vector_store import ChromaVectorStore, EmbeddingManager, EmbeddingTier
    from ingestion.summarizer import ZoomSummarizer, LLMAdapter
    from ingestion.orchestrator import IngestionManager
    from services.janitor import JanitorService
    from core.middleware import GrafoConcierge
    from interface.mcp_server import GrafoConciergeServer

    t0_boot = time.perf_counter()
    store = SqliteStore(db_path)
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    vector_store = ChromaVectorStore(
        persist_dir=chroma_path,
        collection_name="c4_offline_collection",
        embedding_manager=embedder,
    )
    llm_adapter = LLMAdapter(model_name="gemini-2.0-flash")
    summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)
    ingestion_manager = IngestionManager(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        summarizer=summarizer,
    )
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector_store,
        ingestion_manager=ingestion_manager,
    )
    concierge = GrafoConcierge(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        ingestion_manager=ingestion_manager,
        llm_adapter=llm_adapter,
    )
    server = GrafoConciergeServer(concierge=concierge, janitor=janitor)
    t_boot = time.perf_counter() - t0_boot

    print(f"[OK] bootstrap() completou em {t_boot:.4f}s com HF_HUB_OFFLINE=1.")
    print("     CONCLUSAO: O modelo all-MiniLM-L6-v2 NAO E NECESSARIO na inicializacao (bootstrap).")
    print("     O modelo so e carregado sob demanda (lazy loading) no primeiro embedding.")

    print("\n" + "-" * 75)
    print("TESTE 2: Carga de pesos e primeiro embedding com HF_HUB_OFFLINE=1")
    print("-" * 75)

    t0_load = time.perf_counter()
    embedder._load_model()
    t_load = time.perf_counter() - t0_load
    print(f"[OK] embedder._load_model() completou em {t_load:.4f}s offline usando o cache local.")

    t0_embed = time.perf_counter()
    vec = embedder.embed("frase de teste offline")
    t_embed = time.perf_counter() - t0_embed
    print(f"[OK] embed() retornou vetor com {len(vec) if vec else 0} dimensoes em {t_embed:.4f}s.")

    store.close()
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("=" * 75)


if __name__ == "__main__":
    probe_hf_cache()
