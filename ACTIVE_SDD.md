# 🏛️ ACTIVE_SDD: Grafo Concierge System Design Specification (v3.8.2)

---

## 1. Executive Summary & Vision

**Grafo Concierge** is an Open Source, high-performance Long-Term Memory (LTM) infrastructure for AI Agents, Developer IDEs (Cursor, Windsurf, Claude Desktop), and automated workflows.

It solves LLM context fragmentation and codebase amnesia by building a bi-temporal, hybrid semantic graph combining relational SQLite persistence, vector search, hierarchical context synthesis (Zoom Gear), and autonomous background maintenance (Janitor Service).

---

## 2. System Architecture & Components

```
                  ┌────────────────────────────────────────┐
                  │   MCP Clients (Cursor/Claude/Agents)   │
                  └───────────────────┬────────────────────┘
                                      │  JSON-RPC / SSE
                                      ▼
                  ┌────────────────────────────────────────┐
                  │    interface/mcp_server.py (FastMCP)   │
                  │   - Token Auth & CORS Middleware       │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │     core/middleware.py (Facade)        │
                  └──────┬─────────────────┬───────────────┘
                         │                 │
            ┌────────────▼─────┐     ┌─────▼──────────────┐
            │   ingestion/     │     │   services/janitor │
            │ (Crawler/Parser) │     │ (Background Loop)  │
            └────────────┬─────┘     └─────┬──────────────┘
                         │                 │
                         ▼                 ▼
                  ┌────────────────────────────────────────┐
                  │           storage/ (Retention)         │
                  │ - SerializedWriteQueue (SQLite WAL)    │
                  │ - Vector Store (ChromaDB / Qdrant)    │
                  └────────────────────────────────────────┘
```

### Key Modules:
- **`core/middleware.py`**: Central Facade coordinating memory mining, hybrid search, committing trajectories, and project wakeups.
- **`core/hybrid_search.py`**: Hybrid Search v4 tri-signal ranking score:
  $$\text{Score} = (0.50 \times \text{Vector Similarity}) + (0.25 \times \text{FTS5 BM25}) + (0.25 \times \max(\text{Recency}, \text{Centrality}))$$
- **`storage/connection.py`**: `SerializedWriteQueue` thread enforcing single-writer transactions on SQLite WAL mode to eliminate database locks.
- **`services/janitor.py`**: Autonomous background service executing vector reconciliation, orphan pruning, and recency decay.
- **`interface/mcp_server.py`**: Model Context Protocol bridge with optional `GRAFO_API_KEY` authentication for VPS deployments.

---

## 3. Verification & Compliance Matrix

- **Unit & Integration Tests**: 22 pytest suites (`python -m pytest`).
- **Memory Diagnostics**: System check via `python -m tests.check_brain`.
- **Deployment**: Local CLI, FastMCP Server, Docker (`docker compose up`).
- **OS Support**: Windows, Linux, and macOS (Intel & Apple Silicon M1/M2/M3/M4).
