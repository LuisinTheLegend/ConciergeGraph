"""scratch/b5_experiment.py

Investigação B5: Experimento em Cópia do Banco de Dados.
Executa consultas analíticas e comparações de busca híbrida em cópia isolada.
NÃO altera data/concierge.db.
"""

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import ConciergeConfig
from core.hybrid_search import HybridSearchEngine
from core.project_index import ProjectIndex
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager, EmbeddingTier

ROOT_DIR = Path("C:/Nexus-Memory/GrafoConcierge")
ORIG_DB = ROOT_DIR / "data/concierge.db"
SCRATCH_DIR = ROOT_DIR / "scratch"
COPY_ORIG_DB = SCRATCH_DIR / "concierge_b5_orig.db"
COPY_CLEAN_DB = SCRATCH_DIR / "concierge_b5_clean.db"
CHROMA_DIR = str(ROOT_DIR / "data/chroma")

def setup_copies():
    print(f"Copiando {ORIG_DB} -> {COPY_ORIG_DB}...")
    shutil.copy2(ORIG_DB, COPY_ORIG_DB)
    print(f"Copiando {ORIG_DB} -> {COPY_CLEAN_DB}...")
    shutil.copy2(ORIG_DB, COPY_CLEAN_DB)

    # Limpeza na cópia limpa
    conn = sqlite3.connect(COPY_CLEAN_DB)
    cur = conn.cursor()
    cur.execute("UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%';")
    affected = cur.rowcount
    # Rebuild do FTS5 para garantir sincronismo
    cur.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
    conn.commit()
    conn.close()
    print(f"Cópia limpa preparada: {affected} nós atualizados para NULL e FTS5 reconstruído.")

def run_counts_and_distribution():
    conn = sqlite3.connect(COPY_ORIG_DB)
    cur = conn.cursor()

    # (a) Contagens por situação
    total = cur.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
    dumb = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary LIKE '[DUMB]%';").fetchone()[0]
    nulls = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NULL;").fetchone()[0]
    others = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NOT NULL AND summary NOT LIKE '[DUMB]%';").fetchone()[0]

    print("\n" + "="*70)
    print("PARTE B5(a) — CONTAGENS POR SITUAÇÃO (CÓPIA DO data/concierge.db)")
    print("="*70)
    print(f"Total de nós no banco:                 {total:,}")
    print(f"Nós com summary iniciando por [DUMB]:  {dumb:,} ({dumb/total*100:.2f}%)")
    print(f"Nós com summary IS NULL:               {nulls:,} ({nulls/total*100:.2f}%)")
    print(f"Nós com outro summary (genuíno/outro): {others:,} ({others/total*100:.2f}%)")

    # (b) Distribuição de [DUMB] por nodes.type
    dist = cur.execute("""
        SELECT 
            type, 
            COUNT(*) as total_type,
            SUM(CASE WHEN summary LIKE '[DUMB]%' THEN 1 ELSE 0 END) as dumb_count,
            SUM(CASE WHEN summary IS NULL THEN 1 ELSE 0 END) as null_count
        FROM nodes 
        GROUP BY type 
        ORDER BY dumb_count DESC;
    """).fetchall()

    print("\n" + "="*70)
    print("PARTE B5(b) — DISTRIBUIÇÃO DE [DUMB] POR nodes.type")
    print("="*70)
    print(f"{'Tipo de Nó (nodes.type)':<25} | {'Total':<8} | {'Com [DUMB]':<12} | {'% [DUMB]':<10} | {'NULL':<8}")
    print("-" * 70)
    for row in dist:
        t_name = row[0] or "<vazio/None>"
        t_total, t_dumb, t_null = row[1], row[2], row[3]
        pct = (t_dumb / t_total * 100) if t_total else 0.0
        print(f"{t_name:<25} | {t_total:<8} | {t_dumb:<12} | {pct:>8.2f}% | {t_null:<8}")

    # (d) Tamanho total em bytes dos sumários [DUMB]
    bytes_stats = cur.execute("""
        SELECT 
            SUM(LENGTH(summary)),
            AVG(LENGTH(summary)),
            MIN(LENGTH(summary)),
            MAX(LENGTH(summary))
        FROM nodes 
        WHERE summary LIKE '[DUMB]%';
    """).fetchone()

    total_bytes = bytes_stats[0] or 0
    avg_bytes = bytes_stats[1] or 0.0
    min_bytes = bytes_stats[2] or 0
    max_bytes = bytes_stats[3] or 0

    print("\n" + "="*70)
    print("PARTE B5(d) — TAMANHO EM BYTES DOS SUMÁRIOS [DUMB]")
    print("="*70)
    print(f"Tamanho total ocupado por [DUMB]: {total_bytes:,} bytes ({total_bytes / 1024 / 1024:.2f} MB)")
    print(f"Média por sumário [DUMB]:         {avg_bytes:.1f} bytes")
    print(f"Mínimo / Máximo:                  {min_bytes} bytes / {max_bytes} bytes")

    conn.close()

def run_search_comparison():
    print("\n" + "="*70)
    print("PARTE B5(c) — COMPARAÇÃO DE BUSCA HÍBRIDA (ORIGINAL COM [DUMB] vs CÓPIA LIMPA COM NULL)")
    print("="*70)

    config = ConciergeConfig()
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    vector_store = ChromaVectorStore(persist_dir=CHROMA_DIR, collection_name="grafo_concierge")

    store_orig = SqliteStore(str(COPY_ORIG_DB))
    p_index_orig = ProjectIndex(store_orig, config)
    engine_orig = HybridSearchEngine(
        sqlite_store=store_orig,
        vector_store=vector_store,
        embedding_manager=embedder,
        project_index=p_index_orig,
        config=config,
    )

    store_clean = SqliteStore(str(COPY_CLEAN_DB))
    p_index_clean = ProjectIndex(store_clean, config)
    engine_clean = HybridSearchEngine(
        sqlite_store=store_clean,
        vector_store=vector_store,
        embedding_manager=embedder,
        project_index=p_index_clean,
        config=config,
    )

    project_uuid = "6151e6dc-cdbc-4007-a014-6724bdf7dfbb"  # GrafoConcierge
    queries = [
        "SqliteStore",
        "hybrid",
        "concierge",
        "orchestrator",
        "FastEmbed",
        "Janitor",
        "RateGovernor",
        "vector",
    ]

    for q in queries:
        print(f"\n--- CONSULTA: '{q}' ---")
        res_orig = engine_orig.search(query=q, project_uuid=project_uuid, top_k=5)
        res_clean = engine_clean.search(query=q, project_uuid=project_uuid, top_k=5)

        # Carregar labels dos nós
        print("  [CÓPIA ORIGINAL - Com [DUMB]]:")
        for idx, r in enumerate(res_orig, 1):
            n = store_orig.get_node(r["node_id"])
            lbl = n.get("label", "unknown") if n else "unknown"
            bd = r.get("score_breakdown", {})
            print(f"    #{idx} id={r['node_id']} score={r['score_final']:.4f} (vet={bd.get('vector',0):.3f}, fts={bd.get('frequency',0):.3f}) | {lbl}")

        print("  [CÓPIA LIMPA - Com NULL]:")
        for idx, r in enumerate(res_clean, 1):
            n = store_clean.get_node(r["node_id"])
            lbl = n.get("label", "unknown") if n else "unknown"
            bd = r.get("score_breakdown", {})
            print(f"    #{idx} id={r['node_id']} score={r['score_final']:.4f} (vet={bd.get('vector',0):.3f}, fts={bd.get('frequency',0):.3f}) | {lbl}")

        # Comparação objetiva
        orig_ids = [r["node_id"] for r in res_orig]
        clean_ids = [r["node_id"] for r in res_clean]
        orig_scores = [round(r["score_final"], 4) for r in res_orig]
        clean_scores = [round(r["score_final"], 4) for r in res_clean]

        same_ids = (orig_ids == clean_ids)
        same_scores = (orig_scores == clean_scores)
        print(f"  --> IDs idênticos: {same_ids} | Scores idênticos: {same_scores}")

    store_orig.close()
    store_clean.close()

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    setup_copies()
    run_counts_and_distribution()
    run_search_comparison()
