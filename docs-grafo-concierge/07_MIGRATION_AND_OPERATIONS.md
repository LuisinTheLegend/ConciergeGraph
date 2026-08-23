# 🛠️ Operations, Janitor Maintenance & Test Audit (v4.0.0)

> **Complete Guide to Vector Reconciliation, SLM Background Summarization, Smart Checkpoint Pruning, Time-Travel Operations, and E2E Test Verification**

---

## 1. Background Janitor & Maintenance Operations

### 1.1 Vector Reconciliation (`core/vector_reconciler.py`)
Identifies and deletes orphaned vectors from Qdrant/Chroma that no longer exist in SQLite WAL:
* Set difference algorithm: $$\text{Orphans} = \text{Vector IDs} \setminus \text{SQLite Paths}$$
* Batch expurge with zero impact on active search queries.

### 1.2 Idle SLM Summarization (`core/background_janitor.py`)
* Periodically inspects `communities` table for `is_dirty = 1`.
* Concatenates code files for each dirty community.
* Invokes local free SLM (e.g., Ollama `llama3.2:3b` or `qwen2.5-coder:1.5b`).
* Updates `summary_text` and resets dirty flags to `0` with zero cloud API token cost.

### 1.3 Smart Checkpoint Pruning (`core/background_janitor.py`)
Prevents unbounded storage growth in `agent_checkpoints` (`state.db`) caused by persistent agent swarms:
* `janitor.prune_session_checkpoints(session_id=None, keep_limit=10)` executes a **Smart LRU per Session** algorithm.
* **Point-Zero Protection**: Inviolably protects the initial `"init"` checkpoint (earliest recorded timestamp) required for hard resets and factory rollbacks.
* **Recency Window**: Preserves the $N$ most recent checkpoints (`keep_limit`, default: 10).
* **Paginated Batch Elimination**: Safely purges intermediate obsolete checkpoints through `SerializedWriteQueue` with zero database lock contention on SQLite WAL.

---

## 2. Time-Travel Debugging & State Rollback

Using `AgnosticCheckpointer`, external agents can navigate backwards in their execution timeline:
1. `agent_list_checkpoints(agent_id, session_id)`: Fetches chronological history (`ORDER BY created_at ASC`).
2. `agent_get_checkpoint(agent_id, session_id, checkpoint_id)`: Loads previous state dictionary for variable restoration and replay.

---

## 3. Automated Test Suite & Master Audit

The repository contains an exhaustive test matrix covering all survival slices, cognitive memory, and advanced retrieval systems with 100% green status:

```bash
python -m pytest tests/test_checkpoint_pruning.py \
                 tests/test_queue_writer_batching.py \
                 tests/test_delta_sync_drift.py \
                 tests/test_graph_rag_loops.py \
                 tests/test_agent_checkpointer.py \
                 tests/test_delta_sync.py \
                 tests/test_graph_rag_janitor.py \
                 tests/test_vector_reconciler.py \
                 tests/test_mcp_server_extensions.py \
                 tests/test_e2e_concierge_integration.py \
                 tests/test_dependency_injection.py \
                 tests/test_concurrency_stress.py \
                 tests/test_extraction_noop.py \
                 tests/test_probabilistic_retriever.py \
                 tests/test_chunk_cache.py \
                 tests/test_conversational_db.py \
                 tests/test_ignore.py \
                 tests/test_lightweight.py \
                 tests/test_topology.py -v
```

### Complete Test Suite Matrix:

| Suite | Component | Scope & Key Verification |
| :--- | :--- | :--- |
| `test_checkpoint_pruning.py` | `core/background_janitor.py` | Smart LRU checkpoint auto-poda: protects `"init"` (point-zero) and keeps $N$ recent steps. |
| `test_queue_writer_batching.py` | `interface/queue_writer.py` | Adaptive opportunistic batching throughput & Single-Item Fallback with ROLLBACK on constraint failure. |
| `test_delta_sync_drift.py` | `core/delta_manager.py` | LBH Semantic Drift Guard & `DocstringStripper`: ignores comments/docstrings, catches logic changes. |
| `test_graph_rag_loops.py` | `core/graph_rag.py` | CTE recursion with strict pipe delimiter loop guard (`\|A\|B\|`), preventing cycles & substring collisions. |
| `test_agent_checkpointer.py` | `core/checkpointer.py` | Agnostic state checkpointing, timeline ordering, and multi-agent isolation. |
| `test_delta_sync.py` | `core/delta_manager.py` | Dual-Hash (SSH + LBH) and Lazy Summarization JIT behavior. |
| `test_graph_rag_janitor.py` | `core/graph_rag.py` / `janitor` | Natural communities, CTE recursive call chains, and local SLM offloading. |
| `test_vector_reconciler.py` | `core/search_engine.py` | Query-time self-healing filter and background orphan expurging. |
| `test_mcp_server_extensions.py`| `interface/mcp_server.py` | Standalone FastMCP JSON-RPC tools for checkpoints and call chains. |
| `test_e2e_concierge_integration.py` | Master E2E Pipeline | Full lifecycle integration, cascading data verification, and dual-hash sync. |
| `test_concurrency_stress.py` | `interface/queue_writer.py` | Massive concurrent write stress test against SQLite WAL. |
| `test_dependency_injection.py` | `core/dependencies.py` | Immutable container and path traversal defense. |
| `test_extraction_noop.py` | `core/memory_extractor.py` | SemanticExtractor NOOP/ADD/UPDATE/DELETE decision validation. |
| `test_probabilistic_retriever.py` | `core/probabilistic_retriever.py` | Thompson Sampling Beta(α,β) ranking and Bayesian feedback loop. |
| `test_chunk_cache.py` | `core/delta_manager.py` | Delta Chunk caching and invalidation across structural mutations. |
| `test_conversational_db.py` | `storage/store.py` | Conversational database operations and session persistence. |
| `test_ignore.py` | `ingestion/crawler.py` | File ignore patterns and `.conciergeignore` compliance. |
| `test_lightweight.py` | `core/hybrid_search.py` | Lightweight FTS5-only mode (`GRAFO_LIGHTWEIGHT_MODE`). |
| `test_topology.py` | `core/middleware.py` | Full topology graph export and node/edge serialization. |
| `test_watcher_ignore.py` | `interface/watcher.py` | Early-Exit ignore filtering (`.conciergeignore`, `pathspec`). |
