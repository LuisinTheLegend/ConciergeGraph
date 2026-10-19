"""scratch/compare_repair_query_old_vs_new.py

Micro-benchmark comparing the OLD repair pre-check query (full row load via
get_nodes_by_project) against the NEW ids-only query (get_active_node_ids_with_content)
at 1,000 and 10,000 active nodes. Measures latency and tracemalloc peak memory.
"""

import sys
import time
import tracemalloc
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.store import SqliteStore


def populate(store: SqliteStore, project_uuid: str, num_nodes: int) -> None:
    def insert_batch(conn):
        for i in range(num_nodes):
            label = f"module_{i // 50}.py::func_{i}"
            content = (
                f"def func_{i}(x, y):\n"
                f'    """Docstring for function {i} with some descriptive context."""\n'
                f"    result = (x * {i % 100}) + y\n"
                f"    return result\n"
            )
            conn.execute(
                """INSERT INTO nodes (project_uuid, label, node_type, type, status, content)
                   VALUES (?, ?, 'FUNCTION', 'function', 'ACTIVE', ?)""",
                (project_uuid, label, content),
            )

    store._conn_mgr.write(insert_batch)


def bench(fn, repeats: int = 3):
    best_t = float("inf")
    peak = 0
    for _ in range(repeats):
        tracemalloc.start()
        t0 = time.perf_counter()
        out = fn()
        elapsed = time.perf_counter() - t0
        _, p = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        best_t = min(best_t, elapsed)
        peak = max(peak, p)
    return best_t * 1000.0, peak / 1024.0, out


def main():
    print("=" * 72)
    print("OLD vs NEW repair pre-check query (latency / peak memory, best of 3)")
    print("=" * 72)
    for n in (1000, 10000):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store = SqliteStore(str(Path(tmp) / "cmp.db"))
            uuid = f"cmp_{n}"
            store.create_project(uuid, f"cmp {n}")
            populate(store, uuid, n)

            # OLD path: full row load + python-side content filter (pre-fix behavior)
            def old_path():
                nodes = store.get_nodes_by_project(uuid, status="ACTIVE")
                return {x["id"] for x in nodes if x.get("content") and x["content"].strip()}

            # NEW path: ids-only SQL (current behavior)
            def new_path():
                return store.get_active_node_ids_with_content(uuid)

            old_ms, old_kb, old_ids = bench(old_path)
            new_ms, new_kb, new_ids = bench(new_path)
            assert old_ids == new_ids, "ID sets must match between old and new paths"

            print(f"N={n:,}: OLD {old_ms:8.2f} ms / {old_kb:9.2f} KB  |  "
                  f"NEW {new_ms:8.2f} ms / {new_kb:9.2f} KB  |  "
                  f"speedup {old_ms / new_ms:5.1f}x  |  mem {old_kb / max(new_kb, 0.01):5.1f}x  |  ids equal: OK")
            store.close()


if __name__ == "__main__":
    main()
