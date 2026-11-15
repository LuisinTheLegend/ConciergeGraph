"""
tests/colossus_benchmark.py — Colossus Protocol
Benchmark de performance Big Data para Grafo Concierge v3.8.0.

Injecao de 20.000 nos + 20.000 vetores em 5 projetos.
100 queries hibridas com metricas P50/P99.
Comparacao 100 nos vs 20.000 nos.
Gera colossus_report.json na raiz do projeto.
"""
from __future__ import annotations
import hashlib, json, os, random, statistics, sys, time, shutil, uuid
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
TOTAL_NODES = 20_000
NUM_PROJECTS = 5
NODES_PER_PROJECT = TOTAL_NODES // NUM_PROJECTS  # 4000
VECTOR_DIM = 384
NUM_QUERIES = 100
SMALL_POOL = 100  # nos para baseline
BATCH_INSERT = 500
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "colossus_report.json")
WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_colossus_workspace")

# Vocabulario tecnico para gerar dados sinteticos
TECH_WORDS = [
    "authentication", "middleware", "database", "caching", "websocket",
    "microservice", "kubernetes", "docker", "redis", "postgresql",
    "graphql", "rest-api", "jwt-token", "oauth2", "rate-limiter",
    "load-balancer", "message-queue", "event-sourcing", "cqrs", "saga",
    "circuit-breaker", "retry-policy", "health-check", "monitoring",
    "logging", "tracing", "metrics", "deployment", "ci-cd", "terraform",
    "serverless", "lambda", "api-gateway", "service-mesh", "istio",
    "envoy-proxy", "grpc", "protobuf", "serialization", "encryption",
    "hashing", "tls-certificate", "cors-policy", "csrf-protection",
    "input-validation", "sql-injection", "xss-prevention", "rbac",
    "multi-tenancy", "sharding", "replication", "backup-strategy",
]

NODE_TYPES = ["FACT", "SKILL", "INSIGHT", "PATCH", "TRAJECTORY"]
WINGS = ["backend/api", "frontend/react", "devops/infra", "data/ml", "security/auth"]
PRIVACY = ["PUBLIC", "INTERNAL", "RESTRICTED"]


# ---------------------------------------------------------------------------
# Synthetic Mocks (zero custo LLM)
# ---------------------------------------------------------------------------

class SyntheticEmbedder:
    """Gera vetores randomicos de 384 dims instantaneamente."""
    def __init__(self):
        self.dimensions = VECTOR_DIM
        self._rng = random.Random(42)

    def embed(self, text: str) -> Optional[list[float]]:
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return [rng.gauss(0, 1) for _ in range(VECTOR_DIM)]

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        return [self.embed(t) for t in texts]


def _synthetic_summary(idx: int) -> str:
    w = TECH_WORDS
    r = random.Random(idx)
    return (
        f"Modulo {idx}: Implementacao de {r.choice(w)} com integracao "
        f"{r.choice(w)} e suporte a {r.choice(w)}. "
        f"Utiliza padrao {r.choice(w)} para garantir {r.choice(w)}."
    )


def _synthetic_label(idx: int) -> str:
    r = random.Random(idx)
    dirs = ["src", "lib", "pkg", "internal", "modules"]
    exts = [".py", ".ts", ".go", ".rs", ".java"]
    return f"{r.choice(dirs)}/{r.choice(TECH_WORDS)}{r.choice(exts)}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pXX(latencies: list[float], percentile: int) -> float:
    """Calcula percentil de uma lista de latencias."""
    if not latencies:
        return 0.0
    s = sorted(latencies)
    k = (len(s) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return s[f] + (k - f) * (s[c] - s[f])


def fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000:.2f}ms"


def progress(current: int, total: int, label: str, interval: int = 1000):
    if current % interval == 0 or current == total:
        pct = current / total * 100
        print(f"    [{label}] {current:,}/{total:,} ({pct:.0f}%)", flush=True)


# ---------------------------------------------------------------------------
# FASE 1: Injecao Massiva
# ---------------------------------------------------------------------------

def phase1_injection(store, vector_store):
    """Injeta 20k nos no SQLite e 20k vetores no ChromaDB."""
    print("\n" + "=" * 64)
    print("  FASE 1: INJECAO MASSIVA (20.000 nos + 20.000 vetores)")
    print("=" * 64)

    embedder = SyntheticEmbedder()
    project_uuids = []

    # Registra 5 projetos
    for i in range(NUM_PROJECTS):
        puuid = str(uuid.uuid4())
        store.create_project(
            uuid=puuid,
            folder_name=f"colossus-proj-{i}",
            primary_wing=WINGS[i],
            privacy_level=PRIVACY[i % len(PRIVACY)],
            summary=f"Projeto benchmark {i} para teste Colossus",
        )
        project_uuids.append(puuid)
    print(f"  {NUM_PROJECTS} projetos registrados.")

    # --- Injecao SQLite (20k nos) ---
    print(f"\n  Injetando {TOTAL_NODES:,} nos no SQLite...")
    t0_sql = time.perf_counter()
    node_ids_by_project: dict[str, list[int]] = {p: [] for p in project_uuids}
    all_node_ids: list[int] = []

    for i in range(TOTAL_NODES):
        proj_idx = i % NUM_PROJECTS
        puuid = project_uuids[proj_idx]
        ntype = NODE_TYPES[i % len(NODE_TYPES)]
        label = _synthetic_label(i)
        summary = _synthetic_summary(i)
        tags = random.sample(TECH_WORDS, k=min(4, len(TECH_WORDS)))
        fhash = hashlib.sha256(f"node-{i}".encode()).hexdigest()

        nid = store.create_node(
            project_uuid=puuid, label=label, summary=summary,
            node_type=ntype, tags=tags, file_hash=fhash,
        )
        node_ids_by_project[puuid].append(nid)
        all_node_ids.append(nid)
        progress(i + 1, TOTAL_NODES, "SQLite", 2000)

    dt_sql = time.perf_counter() - t0_sql
    rate_sql = TOTAL_NODES / dt_sql
    print(f"  SQLite: {TOTAL_NODES:,} nos em {dt_sql:.2f}s ({rate_sql:,.0f} nos/s)")

    # --- Injecao ChromaDB (20k vetores em batches) ---
    print(f"\n  Injetando {TOTAL_NODES:,} vetores no ChromaDB...")
    t0_vec = time.perf_counter()
    vec_stored = 0

    for batch_start in range(0, TOTAL_NODES, BATCH_INSERT):
        batch_end = min(batch_start + BATCH_INSERT, TOTAL_NODES)
        items = []
        for i in range(batch_start, batch_end):
            nid = all_node_ids[i]
            puuid = project_uuids[i % NUM_PROJECTS]
            emb = embedder.embed(f"node-content-{i}")
            items.append({
                "doc_id": f"node_{nid}",
                "embedding": emb,
                "metadata": {"node_id": nid, "project_uuid": puuid},
            })
        stored = vector_store.store_embeddings_batch(items=items)
        vec_stored += stored
        progress(batch_end, TOTAL_NODES, "ChromaDB", 2000)

    dt_vec = time.perf_counter() - t0_vec
    rate_vec = vec_stored / dt_vec if dt_vec > 0 else 0
    print(f"  ChromaDB: {vec_stored:,} vetores em {dt_vec:.2f}s ({rate_vec:,.0f} vec/s)")

    return project_uuids, node_ids_by_project, all_node_ids, {
        "sqlite_nodes": TOTAL_NODES,
        "sqlite_time_s": round(dt_sql, 3),
        "sqlite_rate_per_s": round(rate_sql, 1),
        "chroma_vectors": vec_stored,
        "chroma_time_s": round(dt_vec, 3),
        "chroma_rate_per_s": round(rate_vec, 1),
    }


# ---------------------------------------------------------------------------
# FASE 2: Benchmark da Busca Hibrida v4
# ---------------------------------------------------------------------------

def phase2_hybrid_search(store, vector_store, embedder_real, project_uuids):
    """100 queries aleatorias com metricas P50/P99."""
    print("\n" + "=" * 64)
    print("  FASE 2: BENCHMARK BUSCA HIBRIDA v4 (100 queries)")
    print("=" * 64)

    from core.project_index import ProjectIndex
    from core.hybrid_search import HybridSearchEngine

    project_index = ProjectIndex(store)
    engine = HybridSearchEngine(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder_real,
        project_index=project_index,
    )

    queries = [
        f"{random.choice(TECH_WORDS)} {random.choice(TECH_WORDS)}"
        for _ in range(NUM_QUERIES)
    ]

    latencies: list[float] = []
    result_counts: list[int] = []

    for i, q in enumerate(queries):
        puuid = project_uuids[i % NUM_PROJECTS]
        t0 = time.perf_counter()
        results = engine.search(query=q, project_uuid=puuid, top_k=10)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        result_counts.append(len(results))
        if (i + 1) % 20 == 0:
            print(f"    [{i+1}/{NUM_QUERIES}] P50={fmt_ms(pXX(latencies, 50))}, P99={fmt_ms(pXX(latencies, 99))}")

    p50 = pXX(latencies, 50)
    p99 = pXX(latencies, 99)
    avg_results = statistics.mean(result_counts) if result_counts else 0

    print(f"\n  Resultados ({NUM_QUERIES} queries sobre {TOTAL_NODES:,} nos):")
    print(f"    P50: {fmt_ms(p50)}")
    print(f"    P99: {fmt_ms(p99)}")
    print(f"    Min: {fmt_ms(min(latencies))}")
    print(f"    Max: {fmt_ms(max(latencies))}")
    print(f"    Media de resultados/query: {avg_results:.1f}")

    return latencies, {
        "total_queries": NUM_QUERIES,
        "total_nodes": TOTAL_NODES,
        "p50_ms": round(p50 * 1000, 2),
        "p99_ms": round(p99 * 1000, 2),
        "min_ms": round(min(latencies) * 1000, 2),
        "max_ms": round(max(latencies) * 1000, 2),
        "avg_results_per_query": round(avg_results, 1),
    }


# ---------------------------------------------------------------------------
# FASE 3: Impacto do Revisor Critico
# ---------------------------------------------------------------------------

def phase3_revisor(store):
    """Mede o overhead do RevisorCritico processando Top-10 de 20k nos."""
    print("\n" + "=" * 64)
    print("  FASE 3: IMPACTO DO REVISOR CRITICO (reranking)")
    print("=" * 64)

    from agents.revisor_critico import RevisorCritico

    revisor = RevisorCritico(llm_adapter=None)

    # Simula 20 rodadas de reranking com candidatos sinteticos
    latencies: list[float] = []
    for i in range(20):
        candidates = [
            {"node_id": j, "score_final": random.uniform(0.1, 0.95)}
            for j in range(1, 51)
        ]
        t0 = time.perf_counter()
        reranked = revisor.rerank(candidates, task_context="benchmark query", max_results=10)
        dt = time.perf_counter() - t0
        latencies.append(dt)

    p50 = pXX(latencies, 50)
    p99 = pXX(latencies, 99)
    print(f"  Reranking (50 candidatos -> Top-10), 20 rodadas:")
    print(f"    P50: {fmt_ms(p50)}")
    print(f"    P99: {fmt_ms(p99)}")

    # Audit benchmark
    audit_latencies: list[float] = []
    for i in range(20):
        draft = {
            "phase": "build",
            "technical_changes": f"Refatorou modulo {random.choice(TECH_WORDS)} com padrao {random.choice(TECH_WORDS)}",
            "updated_pointers": [f"src/{random.choice(TECH_WORDS)}.py"],
            "source_wing": "backend/api",
        }
        t0 = time.perf_counter()
        result = revisor.audit(draft)
        dt = time.perf_counter() - t0
        audit_latencies.append(dt)

    p50_audit = pXX(audit_latencies, 50)
    p99_audit = pXX(audit_latencies, 99)
    print(f"\n  Audit heuristico, 20 rodadas:")
    print(f"    P50: {fmt_ms(p50_audit)}")
    print(f"    P99: {fmt_ms(p99_audit)}")

    return {
        "rerank_p50_ms": round(p50 * 1000, 4),
        "rerank_p99_ms": round(p99 * 1000, 4),
        "audit_p50_ms": round(p50_audit * 1000, 4),
        "audit_p99_ms": round(p99_audit * 1000, 4),
    }


# ---------------------------------------------------------------------------
# FASE 4: Pressao de Manutencao (JanitorService)
# ---------------------------------------------------------------------------

def phase4_janitor(store, vector_store, manager, project_uuids):
    """Mede o tempo do Janitor sobre 20k nos."""
    print("\n" + "=" * 64)
    print("  FASE 4: PRESSAO DE MANUTENCAO (JanitorService)")
    print("=" * 64)

    from services.janitor import JanitorService

    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector_store,
        ingestion_manager=manager,
        auto_zoom_threshold=999_999,  # desabilita auto-zoom no benchmark
    )

    reports = []
    for puuid in project_uuids:
        t0 = time.perf_counter()
        r = janitor.run_maintenance(puuid)
        dt = time.perf_counter() - t0
        reports.append({
            "project_uuid": puuid[:12],
            "duration_s": round(dt, 3),
            "orphans_removed": r.orphan_vectors_removed,
            "decayed": r.trajectories_decayed,
            "archived": r.inactive_nodes_archived,
            "errors": len(r.errors),
        })
        print(f"    Projeto {puuid[:12]}... -> {dt:.3f}s (orphans={r.orphan_vectors_removed})")

    total_time = sum(r["duration_s"] for r in reports)
    print(f"\n  Total manutencao ({NUM_PROJECTS} projetos): {total_time:.3f}s")

    return {
        "total_time_s": round(total_time, 3),
        "per_project": reports,
    }


# ---------------------------------------------------------------------------
# FASE 5: Comparacao 100 nos vs 20.000 nos
# ---------------------------------------------------------------------------

def phase5_comparison(store, vector_store, embedder_real, project_uuids):
    """Compara latencia com SMALL_POOL nos vs TOTAL_NODES nos."""
    print("\n" + "=" * 64)
    print(f"  FASE 5: COMPARACAO {SMALL_POOL} nos vs {TOTAL_NODES:,} nos")
    print("=" * 64)

    from core.project_index import ProjectIndex
    from core.hybrid_search import HybridSearchEngine

    # Usa o primeiro projeto para baseline consistente
    target_uuid = project_uuids[0]
    project_index = ProjectIndex(store)
    engine = HybridSearchEngine(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder_real,
        project_index=project_index,
    )

    test_queries = [
        f"{random.choice(TECH_WORDS)} {random.choice(TECH_WORDS)}"
        for _ in range(20)
    ]

    # Busca no banco cheio (20k nos)
    lat_full: list[float] = []
    for q in test_queries:
        t0 = time.perf_counter()
        engine.search(query=q, project_uuid=target_uuid, top_k=10)
        lat_full.append(time.perf_counter() - t0)

    p50_full = pXX(lat_full, 50)
    p99_full = pXX(lat_full, 99)

    print(f"  Banco CHEIO ({TOTAL_NODES:,} nos):")
    print(f"    P50: {fmt_ms(p50_full)}")
    print(f"    P99: {fmt_ms(p99_full)}")

    ratio_text = "N/A"
    result = {
        "full_db_nodes": TOTAL_NODES,
        "full_p50_ms": round(p50_full * 1000, 2),
        "full_p99_ms": round(p99_full * 1000, 2),
        "small_db_nodes": SMALL_POOL,
        "small_p50_ms": None,
        "small_p99_ms": None,
        "degradation_factor": None,
    }

    # Cria banco pequeno isolado para comparacao justa
    small_db = os.path.join(WORKSPACE, "small_bench.db")
    small_chroma = os.path.join(WORKSPACE, "small_chroma")
    os.makedirs(small_chroma, exist_ok=True)

    try:
        from storage import SqliteStore, ChromaVectorStore
        small_store = SqliteStore(small_db)
        small_vector = ChromaVectorStore(
            persist_dir=small_chroma,
            collection_name="colossus_small",
            embedding_manager=embedder_real,
        )
        small_puuid = str(uuid.uuid4())
        small_store.create_project(uuid=small_puuid, folder_name="small-baseline", primary_wing="backend/api")

        synth_emb = SyntheticEmbedder()
        items = []
        for i in range(SMALL_POOL):
            nid = small_store.create_node(
                project_uuid=small_puuid, label=_synthetic_label(i),
                summary=_synthetic_summary(i), node_type="FACT",
                tags=random.sample(TECH_WORDS, 3),
            )
            emb = synth_emb.embed(f"small-{i}")
            items.append({
                "doc_id": f"node_{nid}",
                "embedding": emb,
                "metadata": {"node_id": nid, "project_uuid": small_puuid},
            })
        small_vector.store_embeddings_batch(items=items)

        small_pi = ProjectIndex(small_store)
        small_engine = HybridSearchEngine(
            sqlite_store=small_store, vector_store=small_vector,
            embedding_manager=embedder_real, project_index=small_pi,
        )

        lat_small: list[float] = []
        for q in test_queries:
            t0 = time.perf_counter()
            small_engine.search(query=q, project_uuid=small_puuid, top_k=10)
            lat_small.append(time.perf_counter() - t0)

        p50_small = pXX(lat_small, 50)
        p99_small = pXX(lat_small, 99)

        degradation = p50_full / p50_small if p50_small > 0 else 0
        ratio_text = f"{degradation:.2f}x"

        print(f"\n  Banco PEQUENO ({SMALL_POOL} nos):")
        print(f"    P50: {fmt_ms(p50_small)}")
        print(f"    P99: {fmt_ms(p99_small)}")
        print(f"\n  Fator de degradacao (P50): {ratio_text}")

        result["small_p50_ms"] = round(p50_small * 1000, 2)
        result["small_p99_ms"] = round(p99_small * 1000, 2)
        result["degradation_factor"] = round(degradation, 2)

        small_store.close()
    except Exception as e:
        print(f"  [WARN] Baseline pequeno falhou: {e}")

    return result


# ==================================================================
# MAIN
# ==================================================================

def main() -> int:
    print()
    print("+" + "=" * 62 + "+")
    print("|     COLOSSUS PROTOCOL — Big Data Performance Benchmark      |")
    print("|     Grafo Concierge v3.8.0 (Absolute Solidity)              |")
    print("+" + "=" * 62 + "+")

    t_global = time.perf_counter()

    # --- Setup workspace ---
    if os.path.exists(WORKSPACE):
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    os.makedirs(WORKSPACE, exist_ok=True)

    db_path = os.path.join(WORKSPACE, "colossus.db")
    chroma_path = os.path.join(WORKSPACE, "chroma")
    os.makedirs(chroma_path, exist_ok=True)

    import logging
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s | %(name)-35s | %(message)s")

    from storage import SqliteStore, ChromaVectorStore, EmbeddingManager, EmbeddingTier
    from ingestion import IngestionManager

    store = SqliteStore(db_path)
    embedder_real = EmbeddingManager(tier=EmbeddingTier.FLASH)
    vector_store = ChromaVectorStore(
        persist_dir=chroma_path,
        collection_name="colossus_bench",
        embedding_manager=embedder_real,
    )
    manager = IngestionManager(
        sqlite_store=store, vector_store=vector_store,
        embedding_manager=embedder_real, summarizer=None,
    )

    report: dict = {
        "benchmark": "Colossus Protocol",
        "version": "Grafo Concierge v3.8.0",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "config": {
            "total_nodes": TOTAL_NODES,
            "num_projects": NUM_PROJECTS,
            "vector_dimensions": VECTOR_DIM,
            "num_queries": NUM_QUERIES,
            "small_baseline": SMALL_POOL,
        },
    }

    try:
        # FASE 1
        project_uuids, node_map, all_ids, inj_metrics = phase1_injection(store, vector_store)
        report["phase1_injection"] = inj_metrics

        # FASE 2
        _, search_metrics = phase2_hybrid_search(store, vector_store, embedder_real, project_uuids)
        report["phase2_hybrid_search"] = search_metrics

        # FASE 3
        revisor_metrics = phase3_revisor(store)
        report["phase3_revisor"] = revisor_metrics

        # FASE 4
        janitor_metrics = phase4_janitor(store, vector_store, manager, project_uuids)
        report["phase4_janitor"] = janitor_metrics

        # FASE 5
        comparison = phase5_comparison(store, vector_store, embedder_real, project_uuids)
        report["phase5_comparison"] = comparison

    except Exception as e:
        print(f"\n  [FATAL] {e}")
        import traceback; traceback.print_exc()
        report["error"] = str(e)
    finally:
        elapsed = time.perf_counter() - t_global
        report["total_time_s"] = round(elapsed, 2)

        try:
            store.close()
        except Exception:
            pass
        try:
            shutil.rmtree(WORKSPACE, ignore_errors=True)
        except Exception:
            pass

    # --- Salva relatorio JSON ---
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Relatorio salvo em: {REPORT_PATH}")

    # --- Sumario final ---
    print("\n" + "=" * 64)
    print("  SUMARIO FINAL — COLOSSUS PROTOCOL")
    print("=" * 64)
    p1 = report.get("phase1_injection", {})
    p2 = report.get("phase2_hybrid_search", {})
    p3 = report.get("phase3_revisor", {})
    p4 = report.get("phase4_janitor", {})
    p5 = report.get("phase5_comparison", {})

    print(f"  Injecao:   {p1.get('sqlite_rate_per_s', 0):,.0f} nos/s SQLite | {p1.get('chroma_rate_per_s', 0):,.0f} vec/s Chroma")
    print(f"  Busca:     P50={p2.get('p50_ms', 0):.2f}ms | P99={p2.get('p99_ms', 0):.2f}ms ({NUM_QUERIES} queries / {TOTAL_NODES:,} nos)")
    print(f"  Revisor:   Rerank P50={p3.get('rerank_p50_ms', 0):.4f}ms | Audit P50={p3.get('audit_p50_ms', 0):.4f}ms")
    print(f"  Janitor:   {p4.get('total_time_s', 0):.3f}s para {NUM_PROJECTS} projetos")

    deg = p5.get("degradation_factor")
    if deg:
        print(f"  Escala:    {SMALL_POOL} nos -> {TOTAL_NODES:,} nos = {deg:.2f}x degradacao")
    print(f"\n  Tempo total: {elapsed:.1f}s")

    print("+" + "=" * 62 + "+")
    print("|     COLOSSUS PROTOCOL COMPLETO                              |")
    print("+" + "=" * 62 + "+")
    return 0


if __name__ == "__main__":
    sys.exit(main())
