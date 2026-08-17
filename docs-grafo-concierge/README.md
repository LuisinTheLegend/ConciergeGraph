# 📚 Grafo Concierge — Official Documentation Hub (v3.8.2)

Welcome to the official technical documentation for **Grafo Concierge**, the open-source Long-Term Memory (LTM) and cognitive graph server for AI Agents and Developer IDEs.

---

## 🧭 Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**`01_ARCHITECTURE.md`**](01_ARCHITECTURE.md) | High-level system architecture, layered design, 8 SQLite relational tables, `SerializedWriteQueue` concurrency, and pluggable vector backends. | Core Contributors & Architects |
| [**`02_MCP_TOOLS_REFERENCE.md`**](02_MCP_TOOLS_REFERENCE.md) | Complete, exhaustive catalog of all **26 native MCP Tools** with parameters, types, descriptions, and JSON payload examples. | AI Agents, Prompt Engineers & IDE Users |
| [**`03_COGNITIVE_MEMORY_AND_FACTS.md`**](03_COGNITIVE_MEMORY_AND_FACTS.md) | Deep dive into bi-temporal fact invalidation (`t_valid` / `t_invalid`), `SemanticExtractor` (ADD/UPDATE/DELETE/NOOP), Scoped Core Memory, and Thompson Sampling. | ML / AI Engineers |
| [**`04_INGESTION_AND_AST.md`**](04_INGESTION_AND_AST.md) | Multi-language Tree-sitter AST parsing, symbol extraction (`CLASS`, `FUNCTION`, `METHOD`), call graph edges, chunk delta caching, and Prompt Armor XML sanitization. | Backend Engineers & Ingestion Devs |
| [**`05_HYBRID_SEARCH_AND_ROUTING.md`**](05_HYBRID_SEARCH_AND_ROUTING.md) | Hybrid Search v4 tri-signal scoring formula (Vector + FTS5 + Max(Recency, Centrality)), Wing taxonomy, and edge-friendly Lightweight RAM mode (<35MB). | Search & Retrieval Engineers |
| [**`06_DEPLOY_AND_CONFIGURATION.md`**](06_DEPLOY_AND_CONFIGURATION.md) | Complete environment variables reference (`GRAFO_*`), Docker / Compose setup, remote FastMCP VPS hosting, token authentication, and 1-click IDE integration. | DevOps, Sysadmins & Developers |
| [**`07_MIGRATION_AND_OPERATIONS.md`**](07_MIGRATION_AND_OPERATIONS.md) | CLI commands reference (`register`, `mine`, `search`, `sync-vector`), switching to Qdrant Cloud, system diagnostics, and operational troubleshooting. | Operators & Developers |

---

## ⚡ Quick Architecture Overview

```
 ┌─────────────────────────────────────────────────────────┐
 │            MCP Clients (Claude Desktop / Cursor)        │
 └────────────────────────────┬────────────────────────────┘
                              │  FastMCP (stdio / SSE)
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🌐 interface/mcp_server.py (26 Active Cognitive Tools)  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🧠 core/middleware.py (Central Facade & Hybrid Search)  │
 └─────────────┬─────────────────────────────┬─────────────┘
               │                             │
               ▼                             ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐
 │ 📥 Ingestion & Tree-sitter│ │ 🧹 Autonomous Janitor     │
 └─────────────┬─────────────┘ └─────────────┬─────────────┘
               │                             │
               ▼                             ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 💾 SQLite Engine (8 Tables) + Vector (Chroma / Qdrant)  │
 └─────────────────────────────────────────────────────────┘
```
