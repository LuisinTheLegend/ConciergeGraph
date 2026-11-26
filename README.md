English · [Português (Brasil)](README.pt-BR.md)
---

# Concierge Graph (V4 Core)

**Open-Source, Local-First Long-Term Memory (LTM), Hybrid Search & MCP Governance Server for AI Agents and IDEs**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-31-blue.svg)](docs-grafo-concierge/README.md)
[![Tests Passing](https://img.shields.io/badge/Tests-369%20Passed-brightgreen.svg)](tests/)

Concierge Graph is a local-first memory server built around the **Model Context Protocol (MCP)** that gives AI coding assistants (Cursor, Claude Desktop, and autonomous agents) persistent project memory, hybrid retrieval, recursive call-chain queries, durable agent checkpoints, and governed tool disclosure — backed by **SQLite WAL (with FTS5)** and pluggable vector storage (**ChromaDB** by default, optional **Qdrant**).

> **V4 Core Consolidation Note:** Experimental modules from earlier iterations have been moved to quarantine under [`archive/v4-experimental/`](archive/v4-experimental/) so that the active V4 core remains lean, deterministic, and audited.

---

## Core Capabilities (V4 Core)

1. **SQLite WAL + FTS5 Relational Graph (`storage/`)**: Stores projects, code nodes, call/import edges, semantic facts, memory commits, and durable agent checkpoints (`agent_checkpoints`) in a local SQLite database with WAL mode and full-text indexing.
2. **Tri-Signal Hybrid Search v4 (`core/hybrid_search.py`)**: Blends dense vector similarity (`sentence-transformers` + ChromaDB/Qdrant), SQLite FTS5 BM25 lexical scoring, and topological/recency signals with strict project/wing scoping and query-time orphan vector filtering.
3. **Python AST Ingestion & Self-Healing Vectors (`ingestion/`, `services/janitor.py`)**: Crawls repositories, extracts Python AST chunks and call edges, repairs missing embeddings during mining with honest failure reporting, and supports on-demand vector reconciliation (`concierge sync-vector`).
4. **Recursive Call-Chain GraphRAG (`core/graph_rag.py`)**: Traverses multi-hop `calls` dependencies over SQLite `edges` using `WITH RECURSIVE` CTEs protected by strict pipe-delimited cycle guards (`|node|`).
5. **Durable Agent Checkpoints with Ownership Binding (`core/checkpointer.py`)**: Persists and retrieves structured agent state dictionaries in `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint`, and `agent_list_checkpoints` with strict argument resolution, corrupt-JSON detection, and SHA-256 `owner_hash` namespace verification (`GRAFO_AGENT_TOKEN` over `stdio`, or `X-Grafo-Agent-Token` over HTTP/SSE decoupled from `Authorization: Bearer`, falling back to an ephemeral per-`ServerSession` secret).
6. **Least-Privilege MCP Governance (`core/mcp_governor.py`)**: Classifies all **31 live MCP tools** into `READ_ONLY` (17), `LOCAL_MUTATION` (12), and `DANGEROUS` (2) across a 3-state hierarchy (`PLANNING < EXECUTION < MAINTENANCE`), defaulting to `PLANNING` (`GRAFO_DEFAULT_STATE`) as a hard privilege ceiling (`max_state`). Sessions are bound server-side to the MCP transport (`WeakKeyDictionary`), undeclared tool arguments are rejected, and both `list_tools` (`ListToolsRequest`) and runtime execution enforce fail-closed governance filtering.
7. **Domain Neutrality & Free-Form Wings**: Project wings are strictly user- or agent-defined free-form strings — no hardcoded business taxonomies exist in product code, enforced by AST guard tests (`tests/test_domain_neutrality_guard.py`).
8. **Optional Lightweight Mode & Optional LLM Summaries**: Set `GRAFO_LIGHTWEIGHT_MODE=true` to operate without heavy vector models using SQLite FTS5 BM25, and `GRAFO_LLM_MODEL=none` to run fully offline without external LLM calls.

---

## Architecture Overview

```
    ┌───────────────────────────┐      ┌───────────────────────────┐
    │      Cursor / Windsurf    │      │       Claude Desktop      │
    └─────────────┬─────────────┘      └─────────────┬─────────────┘
                  │                                  │
                  │     MCP (stdio default / SSE)    │
                  └─────────────────┬────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐      ┌─────────────────────┐
                     │  Concierge Graph MCP Server │      │   concierge CLI     │
                     │  concierge-mcp (Port 8000)  │      │   (10 subcommands)  │
                     └──────────────┬──────────────┘      └──────────┬──────────┘
                                    │                                │
                                    └───────────────┬────────────────┘
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │   GrafoConcierge Facade      │
                                     │   + MCPToolGovernor (31)     │
                                     └──────────────┬───────────────┘
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  SQLite WAL/FTS5 + ChromaDB  │
                                     │  (or optional Qdrant)        │
                                     └──────────────────────────────┘
```

---

## Quick Start

### Quick Install (`v4.1.0`)

> **Release & PyPI Status:** Version `4.1.0` supersedes the legacy `v3.8.2` release on PyPI and the pre-audit `V4.0.0` GitHub tag (kept intact in repository history).

1. **Install via pip (or from source in editable mode):**
   ```bash
   # Package installation:
   pip install concierge-graph

   # Or editable source checkout:
   git clone https://github.com/LuisinTheLegend/ConciergeGraph.git
   cd ConciergeGraph
   python -m venv .venv
   # Linux / macOS: source .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -e .
   ```
   For development and running tests (or install via `pip install -r requirements-dev.txt`; `requirements.txt` contains production runtime packages only):
   ```bash
   pip install -e ".[dev]"
   ```

2. **Configure environment variables (`.env`):**
   ```bash
   cp .env.example .env
   ```
   Minimal local-first configuration (LLM disabled by default if not needed):
   ```env
   GRAFO_LLM_MODEL=none
   GRAFO_TRANSPORT=stdio
   GRAFO_DB_PATH=./data/concierge.db
   GRAFO_CHROMA_PATH=./data/chroma
   ```
   To run over HTTP/SSE instead of `stdio`:
   ```env
   GRAFO_TRANSPORT=sse
   GRAFO_HOST=127.0.0.1
   GRAFO_PORT=8000
   GRAFO_API_KEY=your_optional_bearer_token
   ```

3. **Run the MCP Server or CLI:**
   ```bash
   # Launch MCP server (uses GRAFO_TRANSPORT: stdio default, or sse on port 8000)
   concierge-mcp --help
   concierge-mcp --version
   concierge-mcp --transport sse

   # Or start via Docker Compose (non-root UID 10001, SSE + /health check)
   docker compose up -d --build

   # Use the terminal CLI (10 subcommands)
   concierge --help
   concierge register --name my-project --wing backend/core
   concierge mine --path /path/to/my-project --name my-project
   concierge search --query "authentication flow" --project <project-uuid>
   ```
   When running over HTTP/SSE, `GET /health` and `HEAD /health` return `200 {"status": "ok"}` without requiring `GRAFO_API_KEY`, while `/sse`, `/messages/`, and all other paths remain protected by pure ASGI `Authorization: Bearer` validation.

---

## MCP Tools (31 Live Tools)

| Category | Count | Tools |
| :--- | :---: | :--- |
| **`READ_ONLY`** | 17 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `agent_get_checkpoint`, `agent_list_checkpoints` |
| **`LOCAL_MUTATION`** | 12 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
| **`DANGEROUS`** | 2 | `delete_project`, `reset_collection` |

See [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) for architecture details and the full list of CLI subcommands.

---

## Testing & Verification

The active V4 core is covered by **369 passing automated tests** (verified in normal and `--reverse` order, plus CI across Linux, Windows, and real container `docker-smoke`):

```bash
python -m pytest tests/ -q
```

---

## Contributing & Lineage

- Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for architectural pillars, testing rules, and MCP governance contracts.
- Read [`ATTRIBUTION_AND_LINEAGE.md`](ATTRIBUTION_AND_LINEAGE.md) for technical credits and the active vs. quarantined status matrix.
- Read [`CHANGELOG.md`](CHANGELOG.md) for recent changes and breaking-change migration notes.

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
