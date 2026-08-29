# 📚 Grafo Concierge — Official Documentation Hub (v4.0.0)

Welcome to the official technical documentation for **Grafo Concierge**, the sovereign Long-Term Memory (LTM), cognitive graph server, and extreme resilience survival data engine for AI Agents and Developer IDEs.

---

## 🧭 Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**`01_ARCHITECTURE.md`**](01_ARCHITECTURE.md) | High-level system architecture, complete Pillar 2 Cognition, survival engine (`SerializedWriteQueue` Auto-Batching, Semantic Drift Guard, Self-Healing, Frugal GraphRAG, Alias Tracking, Multilang AST Parser, Durable Checkpoints & Time-Travel, Progressive Tool Disclosure, Nozomio Federated Routing, and Global Memory Adapter). | Core Contributors & Architects |
| [**`02_MCP_TOOLS_REFERENCE.md`**](02_MCP_TOOLS_REFERENCE.md) | Complete, exhaustive catalog of all **30 native MCP Tools** plus the **Progressive Tool Disclosure Security Matrix (SDD-21)** with runtime FSM gating (`READ_ONLY`, `LOCAL_MUTATION`, `DANGEROUS`). | AI Agents, Prompt Engineers & IDE Users |
| [**`03_COGNITIVE_MEMORY_AND_FACTS.md`**](03_COGNITIVE_MEMORY_AND_FACTS.md) | Deep dive into bi-temporal fact invalidation (`t_valid` / `t_invalid`), `SemanticExtractor` (ADD/UPDATE/DELETE/NOOP), Scoped Core Memory, Zero-NumPy Thompson Sampling, Durable FSM Checkpoints, and Global Hybrid Memory Adapter. | ML / AI Engineers |
| [**`04_INGESTION_AND_AST.md`**](04_INGESTION_AND_AST.md) | Multilanguage AST Parsing (`ParserFactory` for Python, TypeScript & JavaScript), Structural Semantic Alias Tracking (`core/alias_tracker.py`), Early-Exit Reactive Watcher (`.conciergeignore`), and Dual-Hash Delta Sync (SSH + LBH). | Backend Engineers & Ingestion Devs |
| [**`05_HYBRID_SEARCH_AND_ROUTING.md`**](05_HYBRID_SEARCH_AND_ROUTING.md) | Hybrid Search v4 tri-signal scoring, Query-Time Self-Healing, Local GraphRAG recursive multi-hop traversal with cycle guards, JIT Intent Classifier in 3 layers, and Nozomio Federated Knowledge Router. | Search & Retrieval Engineers |
| [**`06_DEPLOY_AND_CONFIGURATION.md`**](06_DEPLOY_AND_CONFIGURATION.md) | Environment variables reference, Unified Concurrent DX (`npm run dev:all`), FastAPI REST & SSE Telemetry API (`/api/telemetry/*`, `/api/checkpoints/*`, `/api/mcp/*`), Docker Compose, and Tailscale remote access. | DevOps, Sysadmins & Developers |
| [**`07_MIGRATION_AND_OPERATIONS.md`**](07_MIGRATION_AND_OPERATIONS.md) | Background Janitor, Vector Reconciler, Hardware-Aware SLM Summarization, Smart Checkpoint Pruning, Cognitive Time-Travel, and Master Test Audit with all **87 unit & integration tests (86 passed, 1 skipped)**. | Operators & Developers |

---

## ⚡ Quick Architecture Overview

```
 ┌─────────────────────────────────────────────────────────┐
 │            MCP Clients (Claude Desktop / Cursor)        │
 │            Next.js Dashboard & Multi-Agent Swarms       │
 └────────────────────────────┬────────────────────────────┘
                              │  FastMCP (stdio / SSE) & FastAPI REST/SSE
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🌐 INTERFACE & GOVERNANCE LAYER                         │
 │ - interface/mcp_server.py (30 Native Cognitive Tools)   │
 │ - core/mcp_governor.py (Progressive Tool Disclosure)    │
 │ - interface/telemetry_api.py (FastAPI REST + SSE Stream)│
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🧠 core/ Engine & Cognitive Slices (Pilar 2 Complete):  │
 │ - SerializedWriteQueue (Auto-Batching + Fallback WAL)   │
 │ - IntentClassifier (JIT Regex + SQLite + Ollama SLM)    │
 │ - NozomioRouter (Local GraphRAG vs Federated MCP)       │
 │ - GlobalMemoryAdapter (Hybrid Context: LTM + Last 3 STM)│
 │ - DeltaManager (SSH Signature & LBH Semantic Drift)     │
 │ - AliasTracker (Atomic File Rename via Structural Hash) │
 │ - ParserFactory (Polyglot: Python, TS, TSX, JS, JSX)   │
 │ - HybridSearchEngine (Query-Time Self-Healing)          │
 │ - VectorReconciler (Background Orphan Expurging)        │
 │ - GraphRAGEngine (Supernode Filter + CTE Cycle Guards)  │
 │ - BackgroundJanitor (Hardware-Aware SLM + Smart LRU)    │
 │ - AgnosticCheckpointer (Durable Checkpoints & TimeTravel│
 │ - ThompsonRetriever (Zero-NumPy Bayesian Sampling)      │
 └─────────────┬─────────────────────────────┬─────────────┘
               │                             │
               ▼                             ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐
 │ 📥 Ingestion & Watcher    │ │ 💾 Storage & Vector       │
 │ - Early-Exit File Watcher │ │ - SQLite WAL Engine       │
 │ - Polyglot Parser Factory │ │ - storage/relational_db.py│
 │ - Tree-sitter & Lexical   │ │ - ChromaDB / Qdrant       │
 └───────────────────────────┘ └───────────────────────────┘
```

