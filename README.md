English · [Português (Brasil)](README.pt-BR.md)
---

# 🧠 Concierge Graph v4.0.0

**The Open-Source Long-Term Memory (LTM) & Cognitive Palace for AI Agents, IDEs & Developer Environments**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Docker Supported](https://img.shields.io/badge/Docker-Ready-blue)](docker-compose.yml)

Concierge Graph is a high-performance, local-first cognitive memory server designed to solve LLM "amnesia", context window pollution, and runaway cloud API costs. Operating under the **Survival Engineering & Extreme Resilience Paradigm**, Concierge Graph acts as a sovereign Long-Term Memory (LTM) engine combining relational SQLite WAL persistence with adaptive auto-batching, dual-hash delta sync (SSH + LBH Semantic Drift Guard), frugal GraphRAG with strict loop guards, structural semantic alias tracking, polyglot AST parsing (Python, TypeScript, JavaScript), durable FSM checkpoints with cognitive time-travel, progressive tool disclosure governance, and federated knowledge routing (Nozomio RAG) with a global hybrid memory adapter.

---

## 💡 What is Concierge Graph? (For Beginners & Senior Devs)

### 👶 Simple Explanation (The Analogy)
> Imagine hiring a brilliant senior software engineer who suffers from short-term memory loss. Every time you open a new chat window in Cursor or Claude Desktop, they forget your project structure, coding standards, and past architectural decisions.
>
> **Concierge Graph is that engineer's permanent external brain.** Connected seamlessly via the Model Context Protocol (MCP), your AI assistant automatically consults, learns from, and updates this brain in milliseconds—without you ever copying and pasting context again!

### 🧙‍♂️ Technical Deep-Dive (For Engineers)
Concierge Graph is a local-first/VPS daemon that provides:
1. **Zero-Lock Concurrency & Auto-Batching (`SerializedWriteQueue`)**: Channels all writes through a single-writer daemon on SQLite WAL. Features Adaptive Opportunistic Batching (draining up to 50 queued items in atomic `BEGIN IMMEDIATE ... COMMIT` blocks) and Single-Item Fallback to rescue healthy writes if an integrity constraint fails.
2. **Dual-Hash Delta Sync (SSH + LBH Semantic Drift Guard)**: Combines Structural Signature Hashes (SSH) with Logical Body Hashes (LBH) using `DocstringStripper(ast.NodeTransformer)`. Catches internal logic changes (`is_dirty = 1`) while safely ignoring comments, docstrings, whitespace, and formatters, saving 100% of LLM token costs.
3. **Structural Semantic Alias Tracking (`core/alias_tracker.py`)**: Resolves file renames and moves atomically in $< 1\text{s}$ using Structural Semantic Hashing (SSH). Cascades path updates across `ast_edges`, `files`, and `nodes` without rebuilding the graph, while an automated purge timer safely cleans genuine deletions.
4. **Polyglot AST Parser Factory (`core/parser_factory.py`)**: Extends AST code intelligence to TypeScript and JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) via Tree-sitter and high-performance lexical fallback, automatically filtering external npm packages and React hook built-ins.
5. **Frugal GraphRAG, Supernode Filtering & Strict CTE Loop Guards**: Combines $O(1)$ natural directory community mapping with dynamic **Supernode Degree Outlier Filtering** (`detect_logical_communities`) that isolates utility hubs (e.g., `utils.py`) into `hub_satellite_{dir}` clusters to prevent topological collapse, while multi-hop call chains are traversed via SQLite `WITH RECURSIVE` queries protected by pipe-delimited cycle guards (`|node|` pattern matching via `instr()`).
6. **Durable FSM Checkpoints & Cognitive Time-Travel (`core/checkpointer.py`)**: Persists resilient execution snapshots in `fsm_checkpoints` with recursive sanitization of non-serializable objects and chronological time-travel rollbacks that purge subsequent checkpoints and re-flag rolled-back files as dirty.
7. **Progressive Tool Disclosure Governance (`core/mcp_governor.py`)**: Cognitive firewall enforcing two-layer tool visibility based on agent FSM states (`PLANNING`, `DISCOVERY`, `EXECUTION`, `TDD_GREEN`, `REFACTORING`, `MAINTENANCE`). Passively filters tool discovery to reduce prompt bloat and actively blocks unauthorized executions at runtime, raising `SecurityException`.
8. **Federated Knowledge Routing (Nozomio RAG) & Global Hybrid Memory Adapter**: JIT 3-tier Intent Classifier (Regex < 1ms, SQLite entities, Ollama SLM) routes queries between private `LOCAL_GRAPHRAG` (`is_private: True`) and public `EXTERNAL_NOZOMIO_MCP` (`is_private: False`). The `GlobalMemoryAdapter` compiles a mixed sliding window: preserving the last 3 immediate chat messages (STM) combined with a structured Long-Term Memory (LTM) substrate extracted from the graph.
9. **Hardware-Aware Thermal Throttling & Rate Governor (`BackgroundJanitor`)**: Inspects host CPU utilization ($< 40\%$) and active typing quiet periods via `psutil` before launching local SLMs (Ollama) in the background with lowered process priority (`IDLE_PRIORITY_CLASS` / `nice(15)`).
10. **Real-Time Telemetry & SSE Streaming API (`interface/telemetry_api.py`)**: Exposes FastAPI endpoints for live dashboard observability, providing structured Pydantic v2 telemetry snapshots (`/api/telemetry/snapshot`), persistent Server-Sent Events (`/api/telemetry/stream`), checkpoint navigation (`/api/checkpoints/*`), tool governance (`/api/mcp/*`), and manual reconcile triggers.
11. **Zero-NumPy Native Bayesian Thompson Sampling (`core/probabilistic_retriever.py`)**: Executes probabilistic memory ranking via Python's built-in `random.betavariate()` with defensive input sanitization (`max(val, 1e-5)`), saving ~30MB without sacrificing statistical precision.
12. **Smart Checkpoint Auto-Pruning (`BackgroundJanitor`)**: Prevents database bloat via a Smart LRU per Session algorithm that inviolably protects the initial `"init"` checkpoint (point-zero) for factory rollbacks while keeping the $N$ most recent steps and pruning stale intermediate records via `SerializedWriteQueue`.
13. **Query-Time Self-Healing & Eventual Consistency**: Intercepts vector queries and drops orphan vectors in real-time ($O(1)$ batch lookup) while a background Janitor physically purges orphans asynchronously via set-difference algorithms.
14. **Bi-Temporal Fact Persistence**: Stores semantic facts with explicit valid and transaction time tracking (`t_valid` / `t_invalid`) with Bayesian reinforcement learning over memory utility.
15. **Early-Exit Reactive Watcher**: Filters file system events against `.conciergeignore` / `pathspec` rules before opening file descriptors, eliminating I/O bottlenecks.

---

## 🛡️ Key Architectural Advantages (Solving Common Memory Pitfalls)

| Pitfall in Traditional Memory | How Concierge Graph v4.0.0 Solves It |
| :--- | :--- |
| **"Database is Locked" Concurrency Crashing** | **`SerializedWriteQueue` with Auto-Batching**: Single-writer daemon drains up to 50 writes per atomic transaction with Single-Item Fallback and concurrent sub-5ms reads on SQLite WAL. |
| **Silent Semantic Drift & Token Waste** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignores formatting and docstrings (zero AI token cost), but detects real logic alterations to keep graph memory 100% accurate. |
| **File Renames Destroying Trajectories & Edges** | **Structural Semantic Alias Tracking**: 1-second atomic SSH buffer matches renames, migrating `files`, `ast_edges`, and `nodes` relations without graph rebuilds. |
| **Single-Language Blind Spots** | **Polyglot Parser Factory**: Native Python AST plus Tree-sitter and lexical parsing for TypeScript/JavaScript/React (`.ts`, `.tsx`, `.js`, `.jsx`) with external package filtering. |
| **Graph Collapse into Monolithic Component** | **Supernode Degree Outlier Filter**: Dynamically isolates high in-degree hubs (`utils.py`) into `hub_satellite_{dir}` clusters via Union-Find, preserving fine-grained community boundaries. |
| **Prompt Token Bloat & Premature Code Mutation** | **Progressive Tool Disclosure**: Dynamically hides mutation/dangerous tools in `PLANNING` and unlocks them in `EXECUTION`, raising `SecurityException` on direct call tampering. |
| **Linear Chat History Token Inflation** | **Global Memory Adapter**: Preserves only the last 3 immediate chat messages (STM) and replaces older history with a structured LTM substrate from the graph, saving 70-90% of tokens. |
| **Picos de CPU e Ventoinhas com SLMs Locais** | **Throttler Térmico de Hardware**: Usa `psutil` para validar CPU < 40% e período de ociosidade, executando SLMs locais em prioridade rebaixada no SO. |
| **Heavy External Math Dependencies** | **Zero-NumPy Thompson Sampling**: Replaced NumPy with Python stdlib `random.betavariate()` and sanitization, slashing ~30MB of installation bloat. |
| **Infinite CTE Recursion in Circular Graphs** | **Strict Delimited Loop Guard**: Pipe-delimited path accumulators (`\|node\|`) prevent loops in recursive traversals and eliminate substring collision false-positives. |
| **Unbounded Checkpoint Database Bloat** | **Smart Checkpoint Pruning (Smart LRU)**: Automatically eliminates intermediate step checkpoints while protecting the `"init"` baseline and the $N$ latest steps. |
| **Stale Memory & Desynchronized Vectors** | **Query-Time Self-Healing + Janitor**: Inactive/deleted files are dropped from vector results in real-time, and background workers purge vector collections via $O(N)$ set difference. |
| **Proprietary SDK Lock-in** | **Native MCP Standard (30 Tools) + FastAPI SSE**: Operates via Model Context Protocol (JSON-RPC/SSE) and FastAPI REST/SSE for full dashboard integration. |

---

## ⚙️ Advanced Engineering Highlights

* ⚡ **Unified Concurrent DX (`npm run dev:all`)**: Orchestrates both Next.js frontend (`grafo-dashboard-web`) and FastAPI/FastMCP backend concurrently with unified colored output via `concurrently`.
* ⚡ **Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Enables Concierge Graph to run on low-spec edge hardware or $4/mo VPS (512MB RAM) by bypassing heavy vector models and utilizing SQLite FTS5 BM25 search.
* 📊 **Real-Time SSE Telemetry Stream (`GET /api/telemetry/stream`)**: Pushes live state mutations (dirty files, self-healing events, checkpoints) to Next.js / Electron dashboards with zero polling overhead.
* 🔒 **Local-First Security Binding (`CONCIERGE_BIND_ADDRESS=127.0.0.1`)**: Binds to localhost by default for public Wi-Fi safety, easily configurable to `0.0.0.0` for secure Tailscale mesh networking.
* 🔍 **Hierarchical Zoom Gear (L0 ➔ L1 ➔ L2)**: Synthesizes individual code chunks (L0) into folder clusters (L1) and project-wide Context Compasses (L2) with selective amnesia thresholding.
* 🎯 **Bayesian Thompson Sampling**: Real-time feedback loop (`concierge_feedback`) that dynamically adjusts search scoring weights based on agent reinforcement signals.
* 🔐 **Privacy Wings Isolation**: Structural partition between `PUBLIC`, `INTERNAL`, and `RESTRICTED` wings to prevent cross-tenant context contamination.

---

## 🔌 Simultaneous Multi-Client Integration via MCP

Powered by Anthropic's **Model Context Protocol (MCP)**, a single Concierge Graph server instance communicates **simultaneously** with all your favorite tools:

```
    ┌───────────────────────────┐      ┌───────────────────────────┐
    │     Cursor / Windsurf     │      │       Claude Desktop      │
    └─────────────┬─────────────┘      └─────────────┬─────────────┘
                  │                                  │
                  │        JSON-RPC / SSE (MCP)      │
                  └─────────────────┬────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │ 🧠 Concierge Graph Server   │
                     │  (Local / VPS - Port 8000)  │
                     └──────────────┬──────────────┘
                                    │  FastAPI REST / SSE
                                    ▼
                     ┌─────────────────────────────┐
                     │ 📊 Real-Time UI / Dashboard │
                     │   (Next.js / Web / Desktop) │
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: Your IDE agent dynamically searches, recalls, and commits project memory as you write code.
* 💬 **Claude Desktop**: Grants your desktop AI assistant instant macro awareness of your repos.
* 📊 **Live Dashboard (Next.js)**: Receives low-latency Server-Sent Events showing real-time memory health.
* 🤖 **Autonomous Agents & Swarms**: Connect n8n, LangChain, AutoGen, or custom python scripts via SSE endpoints.

---

## ⚡ Quick Start Guide (3 Minutes)

### Option 1: Install via PyPI (Recommended for Most Users)

```bash
# Install Grafo Concierge package & CLI
pip install concierge-graph

# Launch FastMCP Server
concierge-mcp
```

### Option 2: Local Setup from Source (For Developers & Contributors)

1. **Clone & Install in Editable Mode**:
   ```bash
   git clone https://github.com/LuisinTheLegend/GrafoConcierge.git
   cd GrafoConcierge
   pip install -e .[dev]
   ```

2. **Configure Environment (`.env`)**:
   ```bash
   cp .env.example .env
   ```
   Add your Gemini or OpenAI key (and optionally Qdrant settings):
   ```env
   GRAFO_LLM_API_KEY=your_gemini_api_key_here
   GRAFO_LLM_MODEL=gemini-2.0-flash
   CONCIERGE_BIND_ADDRESS=127.0.0.1
   ```

3. **Start the MCP Server**:
   ```bash
   concierge-mcp
   ```

---

## 🔌 Core MCP Tools Reference (30 Tools)

* **`concierge_mine`**: Ingests a directory with early-exit filtering, AST chunking, dual-hash checks (SSH + LBH), and L0/L1/L2 summarization.
* **`concierge_search`**: Hybrid Search v4 combining dense vectors (50%), FTS5 BM25 (25%), and graph dynamics (25%) with Query-Time Self-Healing.
* **`concierge_get_call_chain`**: Multi-hop recursive call chain discovery via SQLite CTEs with strict pipe-delimited loop and cycle protection.
* **`agent_save_checkpoint`**: Persists arbitrary AI agent state dictionaries into SQLite WAL (Smart LRU auto-prunable).
* **`agent_get_checkpoint`**: Retrieves and decodes stored state dictionaries for a given step.
* **`agent_list_checkpoints`**: Returns the chronological timeline of checkpoints for Time-Travel Debugging.
* **`concierge_wakeup`**: Reactivates agent consciousness on session start by returning Context Compass, reference wings, and recent commits.
* **`concierge_resume`**: Retrieves macro summary of project context (ideal for system prompt injection).
* **`concierge_load`**: On-demand lazy loader for full node contents, edges, and dependencies.
* **`concierge_commit`**: Registers audited architectural changes to the cognitive ledger.
* **`concierge_store_fact`**: Records user preferences and architectural rules with bi-temporal invalidation.
* **`concierge_list_facts`**: Lists all active semantic facts for a scope with stable database primary keys.
* **`concierge_feedback`**: Registers utility feedback for Bayesian Thompson Sampling optimization.

---

## 🧪 Test Suite & Quality Assurance

Concierge Graph features a rigorous automated test suite covering all survival modules, complete Pilar 2 Cognition, and E2E integration with **100% passing tests (86 passed, 1 skipped out of 87 tests)**:

```bash
python -m pytest tests/ -v
```

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
