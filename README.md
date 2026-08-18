English · [Português (Brasil)](README.pt-BR.md)
---

# 🧠 Concierge Graph v3.8.2

**The Open-Source Long-Term Memory (LTM) & Cognitive Palace for AI Agents, IDEs & Developer Environments**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Docker Supported](https://img.shields.io/badge/Docker-Ready-blue)](docker-compose.yml)

Concierge Graph is a high-performance, local cognitive memory server designed to solve LLM "amnesia" and context window pollution. Unlike simple RAG (Retrieval-Augmented Generation) scripts, Concierge Graph acts as a bi-temporal, self-healing memory engine combining relational SQL persistence, vector search, hierarchical context synthesis (Zoom Gear), and autonomous background maintenance (Janitor Loop).

---

## 💡 What is Concierge Graph? (For Beginners & Senior Devs)

### 👶 Simple Explanation (The Analogy)
> Imagine hiring a brilliant senior software engineer who suffers from short-term memory loss. Every time you open a new chat window in Cursor or Claude Desktop, they forget your project structure, coding standards, and past architectural decisions.
>
> **Concierge Graph is that engineer's permanent external brain.** Connected seamlessly via the Model Context Protocol (MCP), your AI assistant automatically consults, learns from, and updates this brain in milliseconds—without you ever copying and pasting context again!

### 🧙‍♂️ Technical Deep-Dive (For Engineers)
Concierge Graph is a local/VPS daemon that provides:
1. **Bi-Temporal Fact Persistence**: Stores semantic facts and code entities with explicit valid time and transaction time tracking.
2. **Hybrid Search v4 Engine**: Balances dense vector embeddings (50%), precise keyword signatures via SQLite FTS5 BM25 (25%), and graph signals (25% combining centrality and exponential recency decay $W = W_0 \cdot e^{-\lambda t}$).
3. **AST-Aware Apex Ingestion**: Parses Python, TypeScript, JS, Go, Rust, Java, C/C++ files into structural AST nodes with delta-hashing (SHA-256) to skip unmodified code.
4. **Autonomous Self-Healing (Janitor Loop)**: Operates in a background thread to reconcile relational SQLite tables with vector collections, prune orphan embeddings, and decay inactive context.

---

## 🛡️ Key Architectural Advantages (Solving Common Memory Pitfalls)

| Pitfall in Traditional Memory | How Concierge Graph v3.8.2 Solves It |
| :--- | :--- |
| **"Wrong Drawer" False Negatives** | **Dynamic Scoping with Fallback**: Search automatically falls back to Reference Wings (`all_wings=True`) if local relevance falls below threshold. No rigid lockouts. |
| **Stale Memory & Contradictions** | **Bi-Temporal Invalidation & Exponential Decay**: `concierge_store_fact` invalidates superseded facts with valid/transaction timestamps while the Janitor decays inactive nodes via $W = W_0 \cdot e^{-\lambda t}$. |
| **Dual Query I/O Latency** | **Sub-40ms Latency (Colossus Benchmark)**: Uses `SerializedWriteQueue` with SQLite WAL mode and thread-local read connections for ultra-fast P50 (41ms) response times. |
| **Proprietary SDK Lock-in** | **Native MCP Standard**: Operates via Anthropic's Model Context Protocol (JSON-RPC/SSE). Zero vendor lock-in; works with Cursor, Claude Desktop, LangChain, or custom scripts. |

---

## ⚙️ Advanced Engineering Highlights

* ⚡ **Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Enables Concierge Graph to run on low-spec edge hardware or $4/mo VPS (512MB RAM) by bypassing heavy vector models and utilizing SQLite FTS5 BM25 search.
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
* 🤖 **Autonomous Agents & Workflows**: Connect n8n, LangChain, AutoGen, or custom python scripts via SSE endpoints.

---

## ⚡ Quick Start Guide (3 Minutes)

### Option 1: Install via PyPI (Recommended for Most Users)

```bash
# Install Grafo Concierge package & CLI
pip install concierge-graph

# Uninstall anytime
pip install concierge-graph --upgrade # to update
pip uninstall concierge-graph         # to uninstall
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
   Add your Gemini or OpenAI key (and optionally Qdrant Cloud settings):
   ```env
   GRAFO_LLM_API_KEY=your_gemini_api_key_here
   GRAFO_LLM_MODEL=gemini-2.0-flash

   # Optional: Qdrant Cloud / Remote Cluster
   # GRAFO_VECTOR_BACKEND=qdrant
   # GRAFO_QDRANT_URL=https://your-cluster.qdrant.tech:6333
   # GRAFO_QDRANT_API_KEY=your_qdrant_api_key
   ```

3. **Start the MCP Server**:
   ```bash
   concierge-mcp
   # or: python main.py
   ```

---

### Option 2: VPS Deployment (Direct `pip` or `Docker`) 🌐

You can host Concierge Graph on any Linux VPS (Ubuntu/Debian) in two ways:

#### A) Direct Installation (Native `pip`)
```bash
# 1. Install directly on your VPS
pip install concierge-graph

# 2. Set your environment variables (or create a .env file)
export GRAFO_LLM_API_KEY="your_gemini_key"
export GRAFO_HOST="0.0.0.0"
export GRAFO_API_KEY="your_secure_vps_token"

# 3. Launch the server
concierge-mcp
```

#### B) Containerized Installation (Docker 🐳)
```bash
# Set your API Key for remote security in .env
echo "GRAFO_API_KEY=your_secure_vps_token" >> .env

# Boot the containerized server
docker compose up -d
```

---

## 💻 1-Click Configuration for IDEs & Claude Desktop

### For Claude Desktop (`claude_desktop_config.json`)
Add Concierge Graph to your configuration file:

```json
{
  "mcpServers": {
    "concierge-graph": {
      "command": "concierge-mcp",
      "env": {
        "GRAFO_LLM_API_KEY": "your_api_key_here"
      }
    }
  }
}
```
*(Or use `"command": "python", "args": ["-m", "interface.mcp_server"], "cwd": "/path/to/GrafoConcierge"` when running directly from cloned source).*

### For Remote VPS / SSE Connections (Cursor / Custom Scripts)
When running on a server:
```json
{
  "mcpServers": {
    "concierge-graph": {
      "url": "http://your-vps-ip:8000/sse",
      "headers": {
        "Authorization": "Bearer your_secure_remote_token"
      }
    }
  }
}
```

---

## 🚀 Performance Benchmarks (Colossus Protocol)

Tested against 20,000 code nodes under the **Colossus Protocol**:

| Metric | Result (20,000 nodes) |
| --- | --- |
| **Search Latency (P50)** | 41.69 ms |
| **Search Latency (P99)** | 112.75 ms |
| **Scalability Factor** | 0.93x (Linear performance preserved) |
| **Ingestion Throughput (SQLite)** | ~536 nodes/second |
| **Ingestion Throughput (ChromaDB)** | ~914 vectors/second |
| **Background Maintenance (Janitor)** | 20,000 orphan vectors reconciled in ~11s |

---

## 🛠️ Hybrid Search v4 Formula

Relevance scores are calculated by composing three distinct signals:

$$\text{Score} = (0.50 \times \text{Vector Similarity}) + (0.25 \times \text{Normalized FTS5 BM25}) + (0.25 \times \max(\text{Recency}, \text{Centrality}))$$

1. **Vector Similarity (50%)**: Captures deep conceptual meaning using dense embeddings.
2. **FTS5 BM25 (25%)**: Exact token signatures for function names, classes, and symbols.
3. **Graph Signals (25%)**:
   - **Centrality**: Relative connectivity of a node (in-degree normalized).
   - **Recency**: Time-based exponential decay ensuring historical context ages gracefully:
     $$W = W_0 \cdot e^{-\lambda t}$$

---

## 🔌 Core MCP Tools Reference

* **`concierge_mine`**: Ingests a directory, chunks code (AST), extracts tags, and generates L0/L1/L2 summaries.
* **`concierge_search`**: Runs the complete Hybrid Search v4 pipeline across indexed projects.
* **`concierge_wakeup`**: Reactivates agent consciousness on session start by returning the Context Compass, reference wings, and recent commits.
* **`concierge_resume`**: Retrieves macro summary of project context (ideal for system prompt injection).
* **`concierge_load`**: On-demand lazy loader for full node contents, edges, and dependencies.
* **`concierge_commit`**: Registers audited architectural changes to the cognitive ledger.
* **`concierge_store_fact`**: Records user preferences and architectural rules with bi-temporal invalidation.

---

## 🛠️ Global CLI Subcommands Reference (`concierge`)

After running `pip install concierge-graph`, two global terminal commands are installed via `pyproject.toml`:
1. **`concierge-mcp`**: Boots the FastMCP Server daemon.
2. **`concierge`**: Multifunctional CLI utility supporting the following subcommands:

```bash
# 1. Register a new workspace/project
concierge register --name my-project --wing backend --privacy PUBLIC

# 2. Mine / Ingest a codebase directory into the memory graph
concierge mine --path /path/to/codebase --name my-project

# 3. Perform Hybrid Search v4 across indexed memory
concierge search --query "authentication middleware" --project my-project

# 4. Reactivate agent consciousness (Compass + Wings + Commits)
concierge wakeup --project my-project

# 5. Retrieve Context Compass macro summary
concierge resume --project my-project

# 6. Register audited architectural commit to ledger
concierge commit --project <uuid> --phase build --technical_changes "Added Auth JWT"

# 7. Lazy load a single node on demand
concierge load --node_id 42

# 8. Display system health, counts, and database status
concierge status

# 9. List all registered projects inside the local database
concierge projects

# 10. Synchronize and reconcile vector store embeddings
concierge sync-vector

# 11. Purge a project and all associated relational & vector records
concierge delete --project my-project
```

---

## 🧪 Test Suite & Health Diagnostics

Run all unit and stress tests:
```bash
python -m pytest
```

Run full memory diagnostics:
```bash
python -m tests.check_brain
```

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.