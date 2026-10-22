"""scratch/p3_search_comparison.py
Executa as 3 consultas solicitadas ('hybrid', 'vector', 'orchestrator')
na copia migrada (scratch/concierge_p3_copy.db) e exibe os rankings top-5.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.config import ConciergeConfig
from core.hybrid_search import HybridSearchEngine
from core.project_index import ProjectIndex
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager, EmbeddingTier

def run_searches():
    db_path = str(ROOT_DIR / "scratch/concierge_p3_copy.db")
    chroma_dir = str(ROOT_DIR / "data/chroma")
    project_uuid = "6151e6dc-cdbc-4007-a014-6724bdf7dfbb"  # GrafoConcierge

    config = ConciergeConfig()
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="grafo_concierge")
    store = SqliteStore(db_path)
    p_index = ProjectIndex(store, config)

    engine = HybridSearchEngine(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        project_index=p_index,
        config=config,
    )

    queries = ["hybrid", "vector", "orchestrator"]

    print("=" * 70)
    print("REPETICAO DAS 3 CONSULTAS NA COPIA MIGRADA (scratch/concierge_p3_copy.db)")
    print("=" * 70)

    for q in queries:
        print(f"\n--- CONSULTA: '{q}' ---")
        results = engine.search(query=q, project_uuid=project_uuid, top_k=5)
        for idx, r in enumerate(results, 1):
            n = store.get_node(r["node_id"])
            lbl = n.get("label", "unknown") if n else "unknown"
            bd = r.get("score_breakdown", {})
            print(f"  #{idx} id={r['node_id']} score={r['score_final']:.4f} (vet={bd.get('vector',0):.3f}, fts={bd.get('frequency',0):.3f}) | {lbl}")

    store.close()

if __name__ == "__main__":
    run_searches()
