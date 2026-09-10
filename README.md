English · [Português (Brasil)](README.pt-BR.md)
---

# 🧠 Concierge Graph v4.2.0

**The Open-Source Long-Term Memory (LTM), Hierarchical Cognitive Engine & Real-Time Cockpit for AI Agents, IDEs & Developer Environments**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Next.js 16](https://img.shields.io/badge/Cockpit-Next.js%2016-black)](grafo-dashboard-web/)
[![Tests Passing](https://img.shields.io/badge/Tests-326%20Passed-brightgreen.svg)](tests/)
[![Docker Supported](https://img.shields.io/badge/Docker-Ready-blue)](docker-compose.yml)

Concierge Graph is a high-performance, local-first cognitive memory server designed to eliminate LLM "amnesia", prevent context window pollution, isolate HTTP 429 quota exhaustion, and govern multi-agent autonomy. Operating under the **Survival Engineering & Extreme Resilience Paradigm**, Concierge Graph combines relational SQLite WAL persistence with adaptive auto-batching, a Hierarchical State Machine (HSM) with Deep History Nodes ($H^*$), a Priority Rate Governor (60 RPM / 40k TPM), adaptive gating security, dual-hash delta sync (SSH + LBH Semantic Drift Guard), polyglot AST parsing (Python, TypeScript, JavaScript), and a dedicated real-time **Next.js 16 Passive Observability Cockpit**.

---

## 💡 What is Concierge Graph? (For Beginners & Senior Devs)

### 👶 Simple Explanation (The Analogy)
> Imagine hiring a brilliant senior software engineer who suffers from short-term memory loss. Every time you open a new chat window in Cursor or Claude Desktop, they forget your project structure, coding standards, past architectural decisions, and which state they were executing.
>
> **Concierge Graph is that engineer's permanent external brain and nervous system.** Connected seamlessly via the Model Context Protocol (MCP), your AI assistant automatically consults, learns from, executes within hierarchical boundaries, and updates this brain in milliseconds—without you ever copying and pasting context again!

### 🧙‍♂️ Technical Deep-Dive (For Engineers)
Concierge Graph is a local-first/VPS daemon and reactive frontend that provides:
1. **Zero-Lock Concurrency & Auto-Batching (`SerializedWriteQueue`)**: Channels all writes through a single-writer daemon on SQLite WAL. Features Adaptive Opportunistic Batching (draining up to 50 queued items in atomic `BEGIN IMMEDIATE ... COMMIT` blocks) and Single-Item Fallback to rescue healthy writes if an integrity constraint fails.
2. **Hierarchical State Machine & Deep History Nodes (`core/hsm_engine.py`)**: Models agent execution as an interactive state tree (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `ERROR`) with hierarchical lifecycle hooks (`on_enter`/`on_exit`), Deep History Nodes ($H^*$) for instant context restoration, and a 5-turn Circuit Breaker protecting against infinite repair loops.
3. **Priority Rate Governor (`core/rate_governor.py`)**: Sliding 60-second window quota regulator (60 RPM, 40,000 TPM) with a 3-tier priority queue (HIGH, MEDIUM, LOW). Reactively freezes background queues at 85% and 95% capacity to prevent HTTP 429 errors while keeping primary user interactions uninterrupted.
4. **Adaptive Gating Interceptor & Security Guard (`core/gating_interceptor.py`, `core/security_guard.py`)**: Enforces granular monorepo boundaries with configurable autonomy levels (`plan-only`, `ask`, `auto-approve`), project root confinement, path traversal sanitization, and command injection prevention.
5. **Dual-Hash Delta Sync (SSH + LBH Semantic Drift Guard)**: Combines Structural Signature Hashes (SSH) with Logical Body Hashes (LBH) using `DocstringStripper(ast.NodeTransformer)`. Catches internal logic changes (`is_dirty = 1`) while safely ignoring comments, docstrings, whitespace, and formatters, saving 100% of LLM token costs. Performs live delta audits during session resume to detect external code modifications.
6. **Next.js 16 Passive Observability Cockpit (`grafo-dashboard-web/`)**: Real-time 2x2 monitoring grid featuring a 2D Force-Directed code dependency graph with 60fps pulsating amber nodes for dirty files, live RPM/TPM circular gauges with freezing alerts, an interactive collapsible HSM state tree with 1-click resume, and a self-healing audit log feed.
7. **Structural Semantic Alias Tracking (`core/alias_tracker.py`)**: Resolves file renames and moves atomically in $< 1\text{s}$ using Structural Semantic Hashing (SSH). Cascades path updates across `ast_edges`, `files`, and `nodes` without rebuilding the graph.
8. **Polyglot AST Parser Factory (`core/parser_factory.py`)**: Extends AST code intelligence to TypeScript and JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) via Tree-sitter and high-performance lexical fallback, automatically filtering external npm packages and React hook built-ins.
9. **Frugal GraphRAG & Strict CTE Loop Guards**: Combines $O(1)$ natural directory community mapping with dynamic **Supernode Degree Outlier Filtering** (`detect_logical_communities`) to prevent graph collapse, traversing multi-hop call chains via SQLite `WITH RECURSIVE` queries protected by pipe-delimited cycle guards (`|node|` pattern matching via `instr()`).
10. **Progressive Tool Disclosure Governance (`core/mcp_governor.py`)**: Cognitive firewall enforcing two-layer tool visibility based on active HSM states. Passively filters tool discovery to eliminate prompt bloat and actively blocks unauthorized executions at runtime, raising `SecurityException`.
11. **Federated Knowledge Routing & Global Hybrid Memory Adapter**: JIT 3-tier Intent Classifier (Regex < 1ms, SQLite entities, Ollama SLM) routes queries between private `LOCAL_GRAPHRAG` (`is_private: True`) and public documentation (`is_private: False`). The `GlobalMemoryAdapter` compiles a mixed sliding window: preserving the last 3 immediate chat messages (STM) combined with a structured LTM substrate from the graph.
12. **Master 15-Endpoint Telemetry REST API (`interface/telemetry_api.py`)**: Exposes FastAPI endpoints for live dashboard observability, providing structured Pydantic v2 telemetry snapshots, persistent Server-Sent Events (`/api/telemetry/stream`), Rate Governor metrics, gating configuration, HSM state control, and time-travel rollbacks.
13. **Zero-NumPy Native Bayesian Thompson Sampling (`core/probabilistic_retriever.py`)**: Executes probabilistic memory ranking via Python's built-in `random.betavariate()` with defensive input sanitization (`max(val, 1e-5)`), saving ~30MB without sacrificing statistical precision.
14. **Smart Checkpoint Auto-Pruning (`BackgroundJanitor`)**: Prevents database bloat via a Smart LRU per Session algorithm that inviolably protects the initial `"init"` checkpoint for factory rollbacks while keeping the $N$ most recent steps.
15. **Query-Time Self-Healing & Eventual Consistency**: Intercepts vector queries and drops orphan vectors in real-time ($O(1)$ batch lookup) while a background Janitor physically purges orphans asynchronously via set-difference algorithms.

---

## 🛡️ Key Architectural Advantages (Solving Common AI Pitfalls)

| Pitfall in Traditional AI Memory | How Concierge Graph v4.2.0 Solves It |
| :--- | :--- |
| **HTTP 429 Quota Exhaustion Crashes** | **Priority Rate Governor (SDD-23)**: 60s sliding window automatically isolates traffic into HIGH/MEDIUM/LOW, freezing background tasks at 85%/95% to preserve user chat. |
| **Agent Infinite Loops & Stalls** | **HSM & 5-Turn Circuit Breaker (SDD-25/26)**: Hierarchical state tree limits turns per sub-state, tripping into `ERROR.PAUSE` before budget or context is blown. |
| **Silent Code Drift on Session Resume** | **Runtime Dual-Hash Delta Audit (SDD-27)**: Detects disk modifications made during downtime and auto-redirects agent to `EXECUTION.RE_INDEX`. |
| **Accidental Overwrites in Monorepos** | **Adaptive Gating Interceptor (SDD-24)**: Strict root confinement and gating modes (`plan-only`, `ask`, `auto-approve`) prevent out-of-scope mutations. |
| **Blindness to Agent Internal State** | **Next.js 16 Passive Cockpit (SDD-28)**: Real-time 2x2 dashboard visualizes active HSM states, quota gauges, and dirty files at 60fps via SSE. |
| **"Database is Locked" Concurrency Crashing** | **`SerializedWriteQueue` with Auto-Batching**: Single-writer daemon drains up to 50 writes per atomic transaction with Single-Item Fallback and sub-5ms concurrent reads. |
| **Silent Semantic Drift & Token Waste** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignores formatting and docstrings (zero AI token cost), detecting true logic alterations. |
| **File Renames Destroying Trajectories & Edges** | **Structural Semantic Alias Tracking**: 1-second atomic SSH buffer matches renames, migrating relations across SQLite WAL without graph rebuilds. |
| **Single-Language Blind Spots** | **Polyglot Parser Factory**: Native Python AST plus Tree-sitter and lexical parsing for TypeScript/JavaScript/React (`.ts`, `.tsx`, `.js`, `.jsx`). |
| **Graph Collapse into Monolithic Component** | **Supernode Degree Outlier Filter**: Dynamically isolates high in-degree hubs (`utils.py`) into `hub_satellite_{dir}` clusters, preserving community boundaries. |
| **Prompt Token Bloat & Premature Code Mutation** | **Progressive Tool Disclosure**: Dynamically hides mutation tools in `PLANNING` and unlocks them in `EXECUTION`, raising `SecurityException` on direct tampering. |
| **Linear Chat History Token Inflation** | **Global Memory Adapter**: Preserves only the last 3 immediate chat messages (STM) and replaces older history with a structured LTM substrate from the graph. |
| **Infinite CTE Recursion in Circular Graphs** | **Strict Delimited Loop Guard**: Pipe-delimited path accumulators (`\|node\|`) prevent loops in recursive traversals and eliminate substring collisions. |
| **Proprietary SDK Lock-in** | **Native MCP Standard (30 Tools) + FastAPI SSE**: Operates via Model Context Protocol (JSON-RPC/SSE) and FastAPI REST/SSE for full IDE and dashboard integration. |

---

## ⚙️ Advanced Engineering Highlights

* ⚡ **Unified Concurrent DX (`npm run dev:all`)**: Orchestrates both the Next.js 16 frontend (`grafo-dashboard-web`) and FastAPI/FastMCP backend concurrently with unified colored output via `concurrently`.
* 📊 **Real-Time SSE Telemetry Stream (`GET /api/telemetry/stream`)**: Pushes live state mutations (dirty files, rate governor updates, HSM transitions) to the cockpit with near-zero network overhead.
* ⚡ **Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Enables Concierge Graph to run on low-spec edge hardware or $4/mo VPS (512MB RAM) by bypassing heavy vector models and utilizing SQLite FTS5 BM25 search.
* 🔒 **Local-First Security Binding (`CONCIERGE_BIND_ADDRESS=127.0.0.1`)**: Binds to localhost by default for public Wi-Fi safety, easily configurable to `0.0.0.0` for secure Tailscale mesh networking.
* 🔍 **Hierarchical Zoom Gear (L0 ➔ L1 ➔ L2)**: Synthesizes individual code chunks (L0) into folder clusters (L1) and project-wide Context Compasses (L2) with selective amnesia thresholding.
* 🎯 **Bayesian Thompson Sampling**: Real-time feedback loop (`concierge_feedback`) that dynamically adjusts search scoring weights based on agent reinforcement signals.

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
                                    │  FastAPI REST / SSE (Port 8001)
                                    ▼
                     ┌─────────────────────────────┐
                     │ 📊 Real-Time Cockpit Next.js│
                     │  (2x2 Grid Observability)   │
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: Your IDE agent dynamically searches, recalls, and commits project memory as you write code.
* 💬 **Claude Desktop**: Grants your desktop AI assistant instant macro awareness of your repos.
* 📊 **Next.js 16 Cockpit (`grafo-dashboard-web/`)**: Receives low-latency Server-Sent Events showing real-time memory health, quota gauges, and HSM states.
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

### Option 2: Local Setup from Source & Dashboard (For Developers)

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
   Add your Gemini or OpenAI key:
   ```env
   GRAFO_LLM_API_KEY=your_gemini_api_key_here
   GRAFO_LLM_MODEL=gemini-2.0-flash
   CONCIERGE_BIND_ADDRESS=127.0.0.1
   GRAFO_RPM_LIMIT=60
   GRAFO_TPM_LIMIT=40000
   GRAFO_GATING_MODE=plan-only
   ```

3. **Start Backend & Cockpit Concurrently**:
   ```bash
   cd grafo-dashboard-web
   npm install
   npm run dev:all
   ```
   * **Cockpit UI**: `http://localhost:3000`
   * **Telemetry API**: `http://localhost:8001`
   * **FastMCP Server**: `http://localhost:8000`

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

## 🧪 Master Test Suite & Quality Assurance

Concierge Graph features an exhaustive automated test suite covering all survival modules, HSM transitions, rate quotas, gating security, and E2E integration with **100% green status (326 tests collected across 47 suites)**:

```bash
python -m pytest tests/ -v
```

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
