# Concierge Graph — Documentation (V4 Core)

This directory documents the active **V4 Core** of **Concierge Graph** (`GrafoConcierge`), a local-first Long-Term Memory (LTM), Hybrid Search, and MCP Governance server for AI agents.

> **Historical experimental specifications:** Earlier architecture drafts covering experimental modules moved to quarantine are preserved unmodified in [`archive/v4-experimental/docs-grafo-concierge/`](../archive/v4-experimental/docs-grafo-concierge/).

---

## 1. Active V4 Core Architecture

Concierge Graph is organized around six live Python packages plus the root entrypoint (`main.py`):

| Layer | Modules | Responsibility |
| :--- | :--- | :--- |
| **Entrypoint** | `main.py` (`concierge-mcp`) | Loads environment variables, initializes SQLite/Vector/Ingestion/Facade, and starts the MCP server (`stdio` default, or `sse` on port `8000`). |
| **Core Facade & Logic** | `core/middleware.py`, `core/hybrid_search.py`, `core/graph_rag.py`, `core/checkpointer.py`, `core/mcp_governor.py`, `core/memory_extractor.py`, `core/project_index.py`, `core/vector_backend.py`, `core/config.py`, `core/database.py` | Central `GrafoConcierge` facade, tri-signal Hybrid Search v4, recursive `calls` traversal via SQLite CTEs, durable agent checkpoints (`agent_checkpoints`), progressive MCP tool governance (`MCPToolGovernor`), semantic fact extraction, and optional Qdrant adapter. |
| **Storage** | `storage/schema.py`, `storage/store.py`, `storage/connection.py`, `storage/logic.py`, `storage/semantic_logic.py`, `storage/vector_store.py`, `storage/base_backend.py` | SQLite WAL persistence, FTS5 full-text index, schema management, embedding manager (`sentence-transformers`), and ChromaDB default vector store. |
| **Ingestion** | `ingestion/crawler.py`, `ingestion/parser.py`, `ingestion/orchestrator.py`, `ingestion/summarizer.py` | Directory crawling, Python AST chunking, vector reconciliation/repair during mining, and optional L0/L1/L2 LLM summarization. |
| **Services** | `services/janitor.py` | Background and on-demand orphan vector cleanup and reconciliation (`JanitorService`). |
| **Interface** | `interface/mcp_server.py`, `interface/cli.py` | FastMCP server exposing **31 governed MCP tools** and the `concierge` CLI with **10 subcommands**. |
| **Scripts** | `scripts/bootstrap_core_memory.py` | Utility bootstrap script for initial memory seeding. |

---

## 2. MCP Tools Reference (31 Live Tools)

All **31 MCP tools** registered in `interface/mcp_server.py` are classified in `core/mcp_governor.py` (`TOOL_CLASSIFICATION`) and governed by `MCPToolGovernor` across a 3-state privilege hierarchy (`PLANNING < EXECUTION < MAINTENANCE`) with fail-closed defaults for unclassified names:

### `READ_ONLY` (17 tools)
- **Retrieval & Context:** `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`
- **Graph & Code Symbols:** `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`
- **Checkpoints:** `agent_get_checkpoint`, `agent_list_checkpoints`

### `LOCAL_MUTATION` (12 tools)
- **Project & Ingestion:** `concierge_register`, `concierge_mine`, `update_project`, `add_reference_wing`, `remove_reference_wing`
- **Memory & Governance:** `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`
- **Checkpoints:** `agent_save_checkpoint`

### `DANGEROUS` (2 tools)
- **Destructive Operations:** `delete_project`, `reset_collection`

### Governance & Checkpoint Security Model
- **Default state & ceiling:** `GRAFO_DEFAULT_STATE` defaults to `PLANNING` (least privilege: 17 `READ_ONLY` tools) and sets `max_state`. `concierge_set_state(state_name)` no longer accepts client `session_id`, operates strictly on the transport-bound session (`WeakKeyDictionary`), and cannot escalate above `max_state`.
- **Discovery & parameter enforcement:** Both `FastMCP.list_tools` and low-level `ListToolsRequest` filter exposed tools by the active session state, while `governed_call_tool` rejects undeclared extra arguments before execution.
- **Persistent checkpoint ownership:** `agent_checkpoints` stores SHA-256 `owner_hash` verified via `hmac.compare_digest` over `(agent_id, session_id)` on save, get, and list (plus SQL `AND owner_hash = ?` read-TOCTOU closure). MCP resolves the owner token strictly from `X-Grafo-Agent-Token` (HTTP/SSE, decoupled from `Authorization: Bearer` transport auth) or `GRAFO_AGENT_TOKEN` (`stdio`), falling back to an ephemeral per-`ServerSession` secret when unset.
- **SSE transport auth:** When `GRAFO_API_KEY` is configured, `custom_sse_app` enforces constant-time `hmac.compare_digest` validation exclusively on `Authorization: Bearer <key>`.

---

## 3. CLI Reference (`concierge` — 10 Subcommands)

Installed via `pyproject.toml` (`concierge = "interface.cli:main"`), or run with `python -m interface.cli <command>`:

| Subcommand | Description |
| :--- | :--- |
| `register` | Registers a new project with free-form primary wing and privacy level |
| `mine` | Ingests a project directory (crawl, Python AST parse, SQLite + vector indexing) |
| `search` | Runs Hybrid Search v4 against a project or wing scope |
| `wakeup` | Reactivates project context (Context Compass, reference wings, recent commits) |
| `resume` | Returns concise macro summary of project context |
| `commit` | Records an audited memory commit in the project ledger |
| `load` | Lazy-loads full details and edges for a specific node ID |
| `status` | Prints system and project health statistics |
| `projects` | Lists all registered projects |
| `sync-vector` | Reconciles missing or orphan embeddings in the active vector backend |

---

## 4. Configuration & Storage Notes

- **Environment variables:** Copy `.env.example` to `.env`. LLM summarization is optional (`GRAFO_LLM_MODEL=none` disables it; non-`gemini-*` models require an explicit `GRAFO_LLM_PROVIDER` or LLM remains disabled for safety).
- **Domain neutrality:** Wings are strictly free-form user/agent strings (`tests/test_domain_neutrality_guard.py`). Mining never mutates `primary_wing`.
- **Probabilistic retrieval:** `enable_probabilistic=True` in `HybridSearchEngine.search()` raises `NotImplementedError` explicitly (archived under `archive/v4-experimental/`).
- **Packaging & Docker:** Core runtime depends on 5 direct packages (`chromadb`, `mcp>=1.27,<2`, `sentence-transformers`, `python-dotenv`, `starlette`). `.dockerignore` excludes archives, audits, tests, local databases, and secrets from container build contexts.
