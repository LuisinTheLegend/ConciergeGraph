# 🛠️ Operations, Janitor Maintenance & Test Audit (v3.8.3)

> **Complete Guide to Vector Reconciliation, SLM Background Summarization, Time-Travel Operations, and E2E Test Verification**

---

## 1. Background Janitor & Maintenance Operations

### 1.1 Vector Reconciliation (`core/vector_reconciler.py`)
Identifies and deletes orphaned vectors from Qdrant/Chroma that no longer exist in SQLite WAL:
* Set difference algorithm: $$\text{Orphans} = \text{Vector IDs} \setminus \text{SQLite Paths}$$.
* Batch expurge with zero impact on active search queries.

### 1.2 Idle SLM Summarization (`core/background_janitor.py`)
* Periodically inspects `communities` table for `is_dirty = 1`.
* Concatenates code files for each dirty community.
* Invokes local free SLM (e.g., Ollama `llama3.2:3b` or `qwen2.5-coder:1.5b`).
* Updates `summary_text` and resets dirty flags to `0` with zero cloud API token cost.

---

## 2. Time-Travel Debugging & State Rollback

Using `AgnosticCheckpointer`, external agents can navigate backwards in their execution timeline:
1. `agent_list_checkpoints(agent_id, session_id)`: Fetches chronological history.
2. `agent_get_checkpoint(agent_id, session_id, checkpoint_id)`: Loads previous state dictionary for variable restoration and replay.

---

## 3. Automated Test Suite & Master E2E Audit

The repository contains **23 automated tests** covering all survival slices with 100% green status and zero warnings:

```bash
python -m pytest tests/test_e2e_concierge_integration.py \
                 tests/test_mcp_server_extensions.py \
                 tests/test_agent_checkpointer.py \
                 tests/test_graph_rag_janitor.py \
                 tests/test_vector_reconciler.py \
                 tests/test_delta_sync.py \
                 tests/test_dependency_injection.py \
                 tests/test_concurrency_stress.py \
                 tests/test_watcher_ignore.py -v --noconftest
```

### Test Suite Matrix:

| Suite | Component | Scope |
| :--- | :--- | :--- |
| `test_watcher_ignore.py` | `interface/watcher.py` | Early-Exit ignore filtering (`.conciergeignore`, `pathspec`). |
| `test_concurrency_stress.py` | `interface/queue_writer.py` | Massive concurrent write stress test against SQLite WAL. |
| `test_dependency_injection.py` | `core/dependencies.py` | Immutable container and path traversal defense. |
| `test_delta_sync.py` | `core/delta_manager.py` | Structural Signature Hash (SSH) and Lazy Summarization JIT. |
| `test_vector_reconciler.py` | `core/search_engine.py` / `vector_reconciler.py` | Query-time self-healing filter and background orphan expurging. |
| `test_graph_rag_janitor.py` | `core/graph_rag.py` / `background_janitor.py` | Natural communities, CTE recursive call chains, and local SLM offloading. |
| `test_agent_checkpointer.py` | `core/checkpointer.py` | Agnostic state checkpointing, timeline ordering, and multi-agent isolation. |
| `test_mcp_server_extensions.py` | `interface/mcp_server.py` | Standalone FastMCP JSON-RPC tools for checkpoints and call chains. |
| `test_e2e_concierge_integration.py` | Master E2E Pipeline | Full lifecycle integration and cascading data verification. |
