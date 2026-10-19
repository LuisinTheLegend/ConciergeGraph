"""scratch/scale_benchmark_repair.py

Scale and memory stress test for repair_missing_vectors with 1,000 and 10,000 nodes.
Evaluates:
- No-op check latency and memory allocation when all vectors exist.
- Repair latency and memory allocation when vectors are missing.
- Verification that data/ is never touched.
"""

import os
import sys
import time
import tracemalloc
import tempfile
from pathlib import Path

# Ensure GrafoConcierge is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore
from ingestion.orchestrator import IngestionManager
from tests.test_ingestion_vector_repair import StubDeterministicEmbedder


def run_benchmark_for_size(num_nodes: int, missing_ratio: float = 0.05):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Assert isolation
        repo_data_dir = Path("data").resolve()
        assert not str(tmp_path.resolve()).startswith(str(repo_data_dir)), "data/ directory must not be touched!"

        db_path = str(tmp_path / f"bench_{num_nodes}.db")
        chroma_dir = str(tmp_path / f"chroma_{num_nodes}")
        project_uuid = f"bench_proj_{num_nodes}"

        store = SqliteStore(db_path)
        store.create_project(project_uuid, f"Benchmark Project {num_nodes}")
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name=f"bench_coll_{num_nodes}")
        embedder = StubDeterministicEmbedder(fail_all=False)
        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
        )

        print(f"--- Populating {num_nodes} nodes in SQLite ---")
        node_ids = []
        # Batch insert for fast population
        def insert_batch(conn):
            ids = []
            for i in range(num_nodes):
                label = f"module_{i // 50}.py::func_{i}"
                content = (
                    f"def func_{i}(x, y):\n"
                    f"    \"\"\"Docstring for function {i} with some descriptive context.\"\"\"\n"
                    f"    result = (x * {i % 100}) + y\n"
                    f"    return result\n"
                )
                cur = conn.execute(
                    """INSERT INTO nodes (project_uuid, label, node_type, type, status, content)
                       VALUES (?, ?, 'FUNCTION', 'function', 'ACTIVE', ?)""",
                    (project_uuid, label, content),
                )
                ids.append(cur.lastrowid)
            return ids

        node_ids = store._conn_mgr.write(insert_batch)

        print(f"Populated {len(node_ids)} nodes.")

        # Pre-seed Chroma with all vectors initially
        print(f"Pre-seeding Chroma with {num_nodes} vectors in batches...")
        batch_size = 200
        for i in range(0, num_nodes, batch_size):
            chunk_ids = node_ids[i:i + batch_size]
            docs = [f"node_{nid}" for nid in chunk_ids]
            texts = [
                f"def func_{nid}(x, y):\n    return result\n"
                for nid in chunk_ids
            ]
            vecs = embedder.embed_batch(texts)
            metas = [
                {"node_id": nid, "project_uuid": project_uuid, "source_file": f"mod_{nid}.py"}
                for nid in chunk_ids
            ]
            vector_store._collection.upsert(ids=docs, embeddings=vecs, metadatas=metas)

        stored_count = len(vector_store.get_all_stored_node_ids())
        assert stored_count == num_nodes, f"Chroma count mismatch: {stored_count} != {num_nodes}"
        print(f"Chroma pre-seeded with {stored_count} vectors.")

        # ---------------------------------------------------------
        # Benchmark 1: NO-OP CHECK (All vectors present)
        # ---------------------------------------------------------
        tracemalloc.start()
        t0 = time.perf_counter()

        missing, repaired, failed = ingestion.repair_missing_vectors(project_uuid)

        t_noop = time.perf_counter() - t0
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert missing == 0
        assert repaired == 0
        assert failed == 0

        # ---------------------------------------------------------
        # Benchmark 2: REPAIR CHECK (missing_ratio missing)
        # ---------------------------------------------------------
        num_missing = int(num_nodes * missing_ratio)
        ids_to_delete = node_ids[:num_missing]
        print(f"Simulating {num_missing} missing vectors ({missing_ratio*100:.1f}%)...")
        for i in range(0, len(ids_to_delete), 200):
            batch_del = [f"node_{nid}" for nid in ids_to_delete[i:i+200]]
            vector_store._collection.delete(ids=batch_del)

        assert len(vector_store.get_all_stored_node_ids()) == (num_nodes - num_missing)

        tracemalloc.start()
        t0 = time.perf_counter()

        missing_r, repaired_r, failed_r = ingestion.repair_missing_vectors(project_uuid)

        t_repair = time.perf_counter() - t0
        current_mem_r, peak_mem_r = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert missing_r == num_missing
        assert repaired_r == num_missing
        assert failed_r == 0
        assert len(vector_store.get_all_stored_node_ids()) == num_nodes

        store.close()

        return {
            "num_nodes": num_nodes,
            "noop_time_ms": t_noop * 1000.0,
            "noop_peak_kb": peak_mem / 1024.0,
            "missing_count": num_missing,
            "repair_time_ms": t_repair * 1000.0,
            "repair_peak_kb": peak_mem_r / 1024.0,
        }


def main():
    print("=" * 60)
    print("BENCHMARK: repair_missing_vectors SCALE & MEMORY PROFILING")
    print("=" * 60)

    results = []
    for n in [1000, 10000]:
        res = run_benchmark_for_size(n, missing_ratio=0.05)
        results.append(res)
        print(f"\nResults for N={n}:")
        print(f"  NOOP Check:  Latency = {res['noop_time_ms']:.2f} ms | Peak Memory = {res['noop_peak_kb']:.2f} KB")
        print(f"  Repair ({res['missing_count']} items): Latency = {res['repair_time_ms']:.2f} ms | Peak Memory = {res['repair_peak_kb']:.2f} KB")

    print("\n" + "=" * 60)
    print("SUMMARY TABLE (MARKDOWN FORMAT):")
    print("=" * 60)
    print("| Carga (Nós Ativos) | Cenário | Itens Reparados | Latência (ms) | Pico de Memória (KB) | Throughput (nós/s) |")
    print("|---|---|---|---|---|---|")
    for r in results:
        n = r["num_nodes"]
        # Noop
        tp_noop = (n / (r["noop_time_ms"] / 1000.0)) if r["noop_time_ms"] > 0 else 0
        print(f"| {n:,} | No-op (100% íntegro) | 0 | {r['noop_time_ms']:.2f} ms | {r['noop_peak_kb']:.2f} KB | {tp_noop:,.0f} nós/s |")
        # Repair
        tp_rep = (r["missing_count"] / (r["repair_time_ms"] / 1000.0)) if r["repair_time_ms"] > 0 else 0
        print(f"| {n:,} | Reparo (5% ausentes) | {r['missing_count']} | {r['repair_time_ms']:.2f} ms | {r['repair_peak_kb']:.2f} KB | {tp_rep:,.0f} nós/s |")


if __name__ == "__main__":
    main()
