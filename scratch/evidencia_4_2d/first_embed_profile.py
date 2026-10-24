"""scratch/evidencia_4_2d/first_embed_profile.py

Mede em processo isolado:
  1. Tempo de bootstrap completo.
  2. Tempo da PRIMEIRA chamada a embed() (inclui import tardio + carga de pesos do modelo).
  3. Tempo da SEGUNDA chamada a embed() (apenas inferencia com modelo aquecido).
Usa diretorios temporarios isolados (nunca toca em data/).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="grafo_first_embed_")
    db_path = os.path.join(tmp_dir, "test_concierge.db")
    chroma_path = os.path.join(tmp_dir, "test_chroma")

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "test_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LOG_LEVEL"] = "WARNING"

    print("=" * 70)
    print("GRAFO CONCIERGE — FIRST EMBED PROFILE")
    print("=" * 70)
    print(f"Python:       {sys.version.split()[0]}")
    print(f"Temp DB:      {db_path}")
    print(f"Temp Chroma:  {chroma_path}")
    print("-" * 70)

    # 1. BOOTSTRAP
    t0 = time.perf_counter()
    import main as main_module
    server, janitor, store = main_module.bootstrap()
    t_boot = time.perf_counter() - t0

    embedder = server._gc._embedder
    print(f"Bootstrap time (server, janitor, store)  : {t_boot:8.4f} s")
    print(f"Embedder tier                             : {embedder.tier.value}")
    print(f"Embedder model loaded before embed?       : {embedder._model is not None}")

    # 2. PRIMEIRA CHAMADA DE EMBED
    query_1 = "Como funciona o sistema de memorias e grafos?"
    t1_start = time.perf_counter()
    vec1 = embedder.embed(query_1)
    t_embed_1 = time.perf_counter() - t1_start

    len1 = len(vec1) if vec1 else 0
    print(f"1st embed call (import + model load)      : {t_embed_1:8.4f} s (dims={len1})")
    print(f"Embedder model loaded after 1st embed?    : {embedder._model is not None}")

    # 3. SEGUNDA CHAMADA DE EMBED
    query_2 = "Segunda busca para medicao de inferencia pura."
    t2_start = time.perf_counter()
    vec2 = embedder.embed(query_2)
    t_embed_2 = time.perf_counter() - t2_start

    len2 = len(vec2) if vec2 else 0
    print(f"2nd embed call (warm inference)           : {t_embed_2:8.4f} s (dims={len2})")
    print("=" * 70)

    # Cleanup
    try:
        store.close()
    except Exception:
        pass
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
