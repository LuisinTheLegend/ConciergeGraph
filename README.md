English · [Português (Brasil)](README.pt-BR.md)
---

# 🧠 Concierge Graph v4.0.0

**The Open-Source Long-Term Memory (LTM) & Cognitive Palace for AI Agents, IDEs & Developer Environments**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Docker Supported](https://img.shields.io/badge/Docker-Ready-blue)](docker-compose.yml)

Concierge Graph is a high-performance, local-first cognitive memory server designed to solve LLM "amnesia", context window pollution, and runaway cloud API costs. Unlike simple RAG (Retrieval-Augmented Generation) scripts, Concierge Graph acts as a bi-temporal, self-healing memory engine combining relational SQLite WAL persistence with adaptive auto-batching, dual-hash delta sync (SSH + LBH Semantic Drift Guard), frugal GraphRAG with strict loop guards, smart checkpoint auto-pruning, and agnostic state checkpointing with Time-Travel.

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
3. **Frugal GraphRAG & Strict Delimited CTE Loop Guards**: Replaces heavy network partition algorithms with $O(1)$ natural directory community mapping and executes multi-hop call chain traversals via SQLite `WITH RECURSIVE` queries protected by pipe-delimited cycle guards (`|node|` pattern matching via `instr()`), terminating indirect cycles ($A \rightarrow B \rightarrow C \rightarrow A$) and preventing substring collisions (`auth.js` vs `oauth.js`).
4. **Smart Checkpoint Auto-Pruning (`BackgroundJanitor`)**: Prevents database bloat via a Smart LRU per Session algorithm that inviolably protects the initial `"init"` checkpoint (point-zero) for factory rollbacks while keeping the $N$ most recent steps and pruning stale intermediate records via `SerializedWriteQueue`.
5. **Query-Time Self-Healing & Eventual Consistency**: Intercepts vector queries and drops orphan vectors in real-time ($O(1)$ batch lookup) while a background Janitor physically purges orphans asynchronously via set-difference algorithms.
6. **Agnostic State Checkpointing & Time-Travel**: Persists arbitrary AI agent state dictionaries as JSON blobs under composite primary keys `(agent_id, session_id, checkpoint_id)`, enabling hermetic multi-agent isolation and chronological state rollbacks.
7. **Bi-Temporal Fact Persistence & Thompson Sampling**: Stores semantic facts with explicit valid and transaction time tracking (`t_valid` / `t_invalid`) with Bayesian reinforcement learning over memory utility.
8. **Early-Exit Reactive Watcher**: Filters file system events against `.conciergeignore` / `pathspec` rules before opening file descriptors, eliminating I/O bottlenecks.

---

## 🛡️ Key Architectural Advantages (Solving Common Memory Pitfalls)

| Pitfall in Traditional Memory | How Concierge Graph v4.0.0 Solves It |
| :--- | :--- |
| **"Database is Locked" Concurrency Crashing** | **`SerializedWriteQueue` with Auto-Batching**: Single-writer daemon drains up to 50 writes per atomic transaction with Single-Item Fallback and concurrent sub-5ms reads on SQLite WAL. |
| **Silent Semantic Drift & Token Waste** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignores formatting and docstrings (zero AI token cost), but detects real logic alterations to keep graph memory 100% accurate. |
| **Infinite CTE Recursion in Circular Graphs** | **Strict Delimited Loop Guard**: Pipe-delimited path accumulators (`\|node\|`) prevent loops in recursive traversals and eliminate substring collision false-positives. |
| **Unbounded Checkpoint Database Bloat** | **Smart Checkpoint Pruning (Smart LRU)**: Automatically eliminates intermediate step checkpoints while protecting the `"init"` baseline and the $N$ latest steps. |
| **Stale Memory & Desynchronized Vectors** | **Query-Time Self-Healing + Janitor**: Inactive/deleted files are dropped from vector results in real-time, and background workers purge vector collections via $O(N)$ set difference. |
| **Heavy RAM Graph Partitioning** | **Frugal GraphRAG Engine**: Uses physical directory topologies ($O(1)$) as natural communities and resolves call chains through SQLite native CTEs with depth and cycle guards. |
| **Proprietary SDK Lock-in** | **Native MCP Standard (30 Tools)**: Operates via Anthropic's Model Context Protocol (JSON-RPC/SSE). Works with Cursor, Windsurf, Claude Desktop, LangChain, or custom swarms. |

---

## ⚙️ Advanced Engineering Highlights

* ⚡ **Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Enables Concierge Graph to run on low-spec edge hardware or $4/mo VPS (512MB RAM) by bypassing heavy vector models and utilizing SQLite FTS5 BM25 search.
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
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: Your IDE agent dynamically searches, recalls, and commits project memory as you write code.
* 💬 **Claude Desktop**: Grants your desktop AI assistant instant macro awareness of your repos.
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

Concierge Graph features a rigorous automated test suite covering all survival modules, Phase 4 resilience, and E2E integration with **100% passing tests**:

```bash
python -m pytest tests/test_checkpoint_pruning.py \
                 tests/test_queue_writer_batching.py \
                 tests/test_delta_sync_drift.py \
                 tests/test_graph_rag_loops.py \
                 tests/test_agent_checkpointer.py \
                 tests/test_delta_sync.py \
                 tests/test_graph_rag_janitor.py \
                 tests/test_vector_reconciler.py \
                 tests/test_mcp_server_extensions.py \
                 tests/test_e2e_concierge_integration.py \
                 tests/test_dependency_injection.py \
                 tests/test_concurrency_stress.py -v
```

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
