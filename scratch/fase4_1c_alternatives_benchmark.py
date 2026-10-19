"""Benchmark and prototype for Alternative A (and empirical measurements for Alternatives B, C, D).
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import shutil
import tempfile
import chromadb

def benchmark_alternative_a():
    temp_dir = tempfile.mkdtemp(prefix="grafo_bench_alt_a_")
    try:
        client = chromadb.PersistentClient(path=os.path.join(temp_dir, "chroma"))
        collection = client.create_collection("bench_alt_a")

        sizes = [100, 1000, 10000]
        results = {}

        for size in sizes:
            # Populate up to size
            current_count = collection.count()
            needed = size - current_count
            if needed > 0:
                batch_size = 1000
                for start in range(0, needed, batch_size):
                    chunk_size = min(batch_size, needed - start)
                    ids = [f"node_{current_count + start + i}" for i in range(chunk_size)]
                    embeddings = [[0.01] * 384 for _ in range(chunk_size)]
                    collection.add(ids=ids, embeddings=embeddings)

            # Test query: check existence of all IDs in collection
            test_ids = [f"node_{i}" for i in range(size)]

            # Method 1: collection.get(ids=test_ids, include=[])
            # Note: Chroma get() supports batch retrieval
            t0 = time.perf_counter()
            # In Chroma, get(ids=..., include=[]) returns {'ids': [...], ...} without data
            got = collection.get(ids=test_ids, include=[])
            found_ids = set(got["ids"])
            elapsed = time.perf_counter() - t0

            results[size] = {
                "elapsed_seconds": round(elapsed, 4),
                "ids_checked": size,
                "ids_found": len(found_ids),
                "rate_per_sec": round(size / elapsed, 1) if elapsed > 0 else 0,
            }

        print("=== BENCHMARK ALTERNATIVE A (Chroma collection.get existence check) ===")
        for s, r in results.items():
            print(f"Size {s:6d}: {r['elapsed_seconds']}s ({r['rate_per_sec']} ids/s)")

        # Test failure mode: what if Chroma is unavailable?
        # Simulate exception during collection.get
        try:
            # closed client or invalid call
            raise chromadb.errors.ChromaError("Connection refused / database locked")
        except Exception as e:
            print(f"\nChroma unavailable simulation: {type(e).__name__}: {e}")

        return results
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    benchmark_alternative_a()
