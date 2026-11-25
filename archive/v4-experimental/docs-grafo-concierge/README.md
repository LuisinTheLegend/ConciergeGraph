# 📚 Grafo Concierge — Official Documentation Hub (v4.2.0)

Welcome to the official technical documentation for **Grafo Concierge**, the sovereign Long-Term Memory (LTM), cognitive graph server, and extreme resilience survival data engine for AI Agents and Developer IDEs.

---

## 🧭 Documentation Index

| Guide | Description | Target Audience |
| :--- | :--- | :--- |
| [**`01_ARCHITECTURE.md`**](01_ARCHITECTURE.md) | High-level system architecture, complete Pillars 1 to 22: Hierarchical State Machine (`core/hsm_engine.py`), Rate Governor quotas & 3-tier freezing (`core/rate_governor.py`), Adaptive Gating (`core/gating_interceptor.py`), Next.js 16 Passive Observability Cockpit, and core survival engine. | Core Contributors & Architects |
| [**`02_MCP_TOOLS_REFERENCE.md`**](02_MCP_TOOLS_REFERENCE.md) | Complete, exhaustive catalog of all **30 native MCP Tools** plus the **HSM Hierarchical State Disclosure Matrix (SDD-21 / SDD-25)** with runtime sensitivity gating (`READ_ONLY`, `LOCAL_MUTATION`, `DANGEROUS`). | AI Agents, Prompt Engineers & IDE Users |
| [**`03_COGNITIVE_MEMORY_AND_FACTS.md`**](03_COGNITIVE_MEMORY_AND_FACTS.md) | Deep dive into bi-temporal fact invalidation (`t_valid` / `t_invalid`), `SemanticExtractor` (ADD/UPDATE/DELETE/NOOP), Scoped Core Memory, Zero-NumPy Thompson Sampling, Durable FSM Checkpoints, and `HSMStateContext` Deep History Node integration. | ML / AI Engineers |
| [**`04_INGESTION_AND_AST.md`**](04_INGESTION_AND_AST.md) | Multilanguage AST Parsing (`ParserFactory` for Python, TypeScript & JavaScript), Structural Semantic Alias Tracking (`core/alias_tracker.py`), Early-Exit Reactive Watcher (`.conciergeignore`), and Dual-Hash Delta Sync (SSH + LBH) with runtime drift checks on HSM session resume. | Backend Engineers & Ingestion Devs |
| [**`05_HYBRID_SEARCH_AND_ROUTING.md`**](05_HYBRID_SEARCH_AND_ROUTING.md) | Hybrid Search v4 tri-signal scoring, Query-Time Self-Healing, Local GraphRAG recursive multi-hop traversal with cycle guards, JIT Intent Classifier in 3 layers, Federated Knowledge Router, and Rate Governor search priority triage. | Search & Retrieval Engineers |
| [**`06_DEPLOY_AND_CONFIGURATION.md`**](06_DEPLOY_AND_CONFIGURATION.md) | Environment variables reference, Unified Concurrent DX (`npm run dev:all`), all **15 FastAPI REST & SSE Telemetry Endpoints** (`/api/telemetry/*`, `/api/governor/*`, `/api/hsm/*`, `/api/gating/*`), Next.js 16 Cockpit integration, Docker Compose, and Tailscale remote access. | DevOps, Sysadmins & Developers |
| [**`07_MIGRATION_AND_OPERATIONS.md`**](07_MIGRATION_AND_OPERATIONS.md) | Background Janitor, Vector Reconciler, Hardware-Aware SLM Summarization, Smart Checkpoint Pruning, Cognitive Time-Travel, HSM Session Recovery runbooks, and Master Test Audit with all **326 unit & integration tests**. | Operators & Developers |

---

## ⚡ Quick Architecture Overview

```
 ┌─────────────────────────────────────────────────────────┐
 │            MCP Clients (Claude Desktop / Cursor)        │
 │            Next.js 16 Observability Cockpit (Grid 2x2)  │
 └────────────────────────────┬────────────────────────────┘
                              │  FastMCP (stdio / SSE) & FastAPI REST/SSE
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🌐 INTERFACE & GOVERNANCE LAYER                         │
 │ - interface/mcp_server.py (30 Native Cognitive Tools)   │
 │ - core/mcp_governor.py (Progressive Tool Disclosure)    │
 │ - core/rate_governor.py (60s Quotas: 60 RPM / 40k TPM)  │
 │ - core/gating_interceptor.py (Adaptive Gating Intercept)│
 │ - interface/telemetry_api.py (15 REST routes + SSE)     │
 │ - grafo-dashboard-web/ (Passive Cockpit 2x2: ForceGraph,│
 │   SVG Radial Gauges, HSM Inspector, Cyber Console Feed) │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 🧠 core/ Engine & Cognitive Slices (Pillars 1 to 22):   │
 │ - HierarchicalStateMachine (Super & Sub-States + H*)    │
 │ - HermesAgentRunner (Cognitive Execution Loop + HSM)    │
 │ - RateGovernor (High/Med/Low Priority Freezing Tiers)   │
 │ - SerializedWriteQueue (Auto-Batching + Fallback WAL)   │
 │ - IntentClassifier (JIT Regex + SQLite + Ollama SLM)    │
 │ - FederatedKnowledgeRouter (Local GraphRAG vs Fed MCP)  │
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
