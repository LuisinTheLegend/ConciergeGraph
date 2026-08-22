# 📚 Grafo Concierge — Official Documentation Hub (v3.8.3)

Welcome to the official technical documentation for **Grafo Concierge**, the sovereign Long-Term Memory (LTM), cognitive graph server, and survival data engine for AI Agents and Developer IDEs.

---

## 🧭 Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**`01_ARCHITECTURE.md`**](01_ARCHITECTURE.md) | High-level system architecture, survival engine (Delta Sync, Self-Healing, Frugal GraphRAG), `SerializedWriteQueue` concurrency, and pluggable vector backends. | Core Contributors & Architects |
| [**`02_MCP_TOOLS_REFERENCE.md`**](02_MCP_TOOLS_REFERENCE.md) | Complete, exhaustive catalog of all **30 native MCP Tools** (including Time-Travel Checkpointing & Recursive Call Chains) with parameters, types, and JSON payloads. | AI Agents, Prompt Engineers & IDE Users |
| [**`03_COGNITIVE_MEMORY_AND_FACTS.md`**](03_COGNITIVE_MEMORY_AND_FACTS.md) | Deep dive into bi-temporal fact invalidation (`t_valid` / `t_invalid`), `SemanticExtractor` (ADD/UPDATE/DELETE/NOOP), Scoped Core Memory, and Thompson Sampling. | ML / AI Engineers |
| [**`04_INGESTION_AND_AST.md`**](04_INGESTION_AND_AST.md) | Multi-language Tree-sitter AST parsing, Early-Exit Reactive Watcher (`.conciergeignore`), SSH Structural Signature Hashing, and Delta Chunk Caching. | Backend Engineers & Ingestion Devs |
| [**`05_HYBRID_SEARCH_AND_ROUTING.md`**](05_HYBRID_SEARCH_AND_ROUTING.md) | Hybrid Search v4 tri-signal scoring, Query-Time Self-Healing Filter, Frugal GraphRAG (Topological mapping + SQLite CTEs), and Lightweight RAM mode (<35MB). | Search & Retrieval Engineers |
| [**`06_DEPLOY_AND_CONFIGURATION.md`**](06_DEPLOY_AND_CONFIGURATION.md) | Complete environment variables reference (`GRAFO_*`, `CONCIERGE_BIND_ADDRESS`), Local-First Security, Docker Compose, Tailscale remote access, and IDE integration. | DevOps, Sysadmins & Developers |
| [**`07_MIGRATION_AND_OPERATIONS.md`**](07_MIGRATION_AND_OPERATIONS.md) | CLI commands reference, Vector Reconciler Janitor, Background SLM Summarization, Time-Travel Debugging, and E2E Master Audit Suite (23 automated tests). | Operators & Developers |

---

## ⚡ Quick Architecture Overview

```
 ┌─────────────────────────────────────────────────────────┐
 │            MCP Clients (Claude Desktop / Cursor)        │
 │               External Multi-Agent Swarms               │
 └────────────────────────────┬────────────────────────────┘
                              │  FastMCP (stdio / SSE)
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🌐 interface/mcp_server.py (30 Active Cognitive Tools)  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🧠 core/ Engine & Survival Slices:                      │
 │ - SerializedWriteQueue (SQLite WAL Concurrency)         │
 │ - DeltaManager (SSH Hashing & JIT Summarization)        │
 │ - HybridSearchEngine (Query-Time Self-Healing)          │
 │ - VectorReconciler (Background Orphan Expurging)        │
 │ - GraphRAGEngine (O(1) Communities + Recursive CTEs)    │
 │ - BackgroundJanitor (Idle SLM Local Summarization)      │
 │ - AgnosticCheckpointer (State Checkpoints & Time-Travel)│
 └─────────────┬─────────────────────────────┬─────────────┘
               │                             │
               ▼                             ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐
 │ 📥 Ingestion & Watcher    │ │ 💾 Storage & Vector       │
 │ - Early-Exit File Watcher │ │ - SQLite WAL Engine       │
 │ - Tree-sitter AST Parser  │ │ - ChromaDB / Qdrant       │
 └───────────────────────────┘ └───────────────────────────┘
```
