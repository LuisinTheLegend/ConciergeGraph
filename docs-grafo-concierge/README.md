# 📚 Grafo Concierge — Official Documentation Hub (v4.0.0)

Welcome to the official technical documentation for **Grafo Concierge**, the sovereign Long-Term Memory (LTM), cognitive graph server, and extreme resilience survival data engine for AI Agents and Developer IDEs.

---

## 🧭 Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**`01_ARCHITECTURE.md`**](01_ARCHITECTURE.md) | High-level system architecture, survival engine (Adaptive Auto-Batching, Semantic Drift Guard, Self-Healing, Frugal GraphRAG with Strict Loop Guard, Smart Checkpoint Pruning), `SerializedWriteQueue` concurrency, and pluggable vector backends. | Core Contributors & Architects |
| [**`02_MCP_TOOLS_REFERENCE.md`**](02_MCP_TOOLS_REFERENCE.md) | Complete, exhaustive catalog of all **30 native MCP Tools** (including Time-Travel Checkpointing & Cycle-Guarded Recursive Call Chains) with parameters, types, and JSON payloads. | AI Agents, Prompt Engineers & IDE Users |
| [**`03_COGNITIVE_MEMORY_AND_FACTS.md`**](03_COGNITIVE_MEMORY_AND_FACTS.md) | Deep dive into bi-temporal fact invalidation (`t_valid` / `t_invalid`), `SemanticExtractor` (ADD/UPDATE/DELETE/NOOP), Scoped Core Memory, and Thompson Sampling. | ML / AI Engineers |
| [**`04_INGESTION_AND_AST.md`**](04_INGESTION_AND_AST.md) | Multi-language Tree-sitter AST parsing, Early-Exit Reactive Watcher (`.conciergeignore`), Dual Hashing: SSH Structural Signature & LBH Logical Body Guard (`DocstringStripper`), and Delta Chunk Caching. | Backend Engineers & Ingestion Devs |
| [**`05_HYBRID_SEARCH_AND_ROUTING.md`**](05_HYBRID_SEARCH_AND_ROUTING.md) | Hybrid Search v4 tri-signal scoring, Query-Time Self-Healing Filter, Frugal GraphRAG (Topological mapping + SQLite CTEs with Strict Delimited Loop Guard), and Lightweight RAM mode (<35MB). | Search & Retrieval Engineers |
| [**`06_DEPLOY_AND_CONFIGURATION.md`**](06_DEPLOY_AND_CONFIGURATION.md) | Complete environment variables reference (`GRAFO_*`, `CONCIERGE_BIND_ADDRESS`), Local-First Security, Docker Compose, Tailscale remote access, and IDE integration. | DevOps, Sysadmins & Developers |
| [**`07_MIGRATION_AND_OPERATIONS.md`**](07_MIGRATION_AND_OPERATIONS.md) | CLI commands reference, Vector Reconciler Janitor, Background SLM Summarization, Smart Checkpoint Pruning (Smart LRU), Time-Travel Debugging, and Complete Master Test Audit. | Operators & Developers |

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
 │ 🧠 core/ Engine & Survival Slices (Fase 4):             │
 │ - SerializedWriteQueue (Adaptive Auto-Batching +        │
 │   Single-Item Fallback on SQLite WAL)                   │
 │ - DeltaManager (SSH Signature & LBH Semantic Drift)     │
 │ - HybridSearchEngine (Query-Time Self-Healing)          │
 │ - VectorReconciler (Background Orphan Expurging)        │
 │ - GraphRAGEngine (O(1) Communities + CTE Loop Guards)   │
 │ - BackgroundJanitor (Idle SLM Summary + Smart LRU Prune)│
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

