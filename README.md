# 🧠 Concierge Graph v3.8.2
> **🇧🇷 [Leia este README em Português (README_pt-BR.md)](file:///c:/Nexus-Memory/GrafoConcierge/README.pt-BR.md)**

**The Long-Term Memory (LTM) Palace for AI Agents & Developer Environments**

Concierge Graph is a high-performance, local cognitive memory infrastructure designed to solve LLM "amnesia" and context pollution in complex, large-scale codebases. Unlike traditional, simple RAG (Retrieval-Augmented Generation) systems, Concierge Graph utilizes a bi-temporal, hybrid database architecture combining relational SQL persistence, vector search, hierarchical context synthesis, and an autonomous self-healing maintenance system.

---

## 💡 The Core Problem We Solve

When collaborating with AI agents on massive codebases, AI models inevitably start to "forget" file relations, historical decisions, or architecture rules once their short-term memory (context window) fills up.

**Concierge Graph** acts as a **permanent external brain**. It:
1. Indexes the entire codebase structure (classes, methods, modules) and documentation.
2. Learns your habits, preferences, and architectural rules as explicit semantic facts.
3. Serves as a single source of truth that feeds relevant, highly filtered context to any AI client.

---

## 🔌 Simultaneous Multi-Client Integration via MCP

Concierge Graph is powered by the **Model Context Protocol (MCP)**. This allows you to run a single server instance and connect it **simultaneously** to multiple developer tools and environments:

* 💻 **Cursor / Windsurf**: Let your IDE agent dynamically scan, search, and recall memory graph nodes as you write code.
* 💬 **Claude Desktop**: Give your general desktop assistant full awareness of your projects and codebase topologies.
* 🤖 **Autonomous Agents / Custom Scripts**: Plug in custom orchestration scripts (e.g., n8n, LangChain, or custom LLM routines) using standard JSON-RPC 2.0 endpoints over Server-Sent Events (SSE).

---

## 🌐 Pluggable Vector Backends (Local & Qdrant Cloud)

The architecture supports pluggable database backends for vector storage, making it adaptable to any scalability requirement:

1. **ChromaDB (Default - Local)**: Zero-configuration local database storing embeddings in the local `data/` directory.
2. **Qdrant (Local & Cloud)**: Switch to Qdrant to offload embeddings processing. Supports **Qdrant Cloud** clusters for high availability, remote persistence, and multi-user configurations.

---

## 🚀 Performance Benchmarks (Colossus Protocol)

Validated under the **Colossus Protocol**, the system demonstrates sub-second latency and linear scalability even at massive data volumes.

| Metric | Result (20,000 nodes) |
| --- | --- |
| **Search Latency (P50)** | 41.69 ms |
| **Search Latency (P99)** | 112.75 ms |
| **Scalability Factor** | 0.93x (Performance preserved at high volume) |
| **Ingestion (SQLite)** | ~536 nodes/second |
| **Ingestion (ChromaDB)** | ~914 vectors/second |
| **Maintenance (Janitor)** | 20,000 orphans cleaned in ~11s |

---

## 🏛️ Layered System Architecture

Concierge Graph is built from the ground up to be modular, robust, and thread-safe:

* **`core/` (Nervous System)**: Orchestrates the **Hybrid Search Engine v4** (combining FTS5, cosine vector similarity, and graph centrality/recency signals) and the system's central facade.
* **`storage/` (Retention Layer)**: Guarantees atomic, thread-safe access to the SQLite relational database (WAL mode, serialized write queue) and vector storage.
* **`ingestion/` (Apex Ingestion Engine)**: Traverses directories (respecting `.gitignore`), parses source code files into semantic AST chunks (Python, JS/TS, Markdown), extracts metadata, and triggers the hierarchical **Zoom Gear**.
* **`agents/` (Audit & Reranking)**: AI agents designed to rerank search results using LLM-as-a-judge and audit commit statements before they write to the cognitive ledger.
* **`services/` (Autonomous Maintenance)**: Houses the **Background Janitor**, which runs in an isolated thread to handle temporal decay, reconcile SQLite ↔ Vector stores, prune orphan vectors, and rebuild search indexes.
* **`interface/` (Operational Portal)**: Exposes the MCP server and CLI utility.

---

## 🛠️ Hybrid Search v4 Formula

Relevance scores are calculated by composing three distinct signals to return only highly relevant context:

$$\text{Score} = (0.50 \times \text{Vector Similarity}) + (0.25 \times \text{Normalized FTS5 BM25}) + (0.25 \times \max(\text{Recency}, \text{Centrality}))$$

1. **Vector Similarity (50%)**: Deep semantic meaning of chunks.
2. **FTS5 BM25 (25%)**: Token matching for precise symbol signatures.
3. **Graph Signals (25%)**:
   - **Centrality**: Relative connectivity of a node (in-degree normalized).
   - **Recency**: Time-based exponential decay ensuring context ages gracefully:
     $$W = W_0 \cdot e^{-\lambda t}$$

---

## 🔌 Detailed MCP Tools & CLI Commands

### 1. Ingestion and Lifecycle
* **`concierge_register`**: Registers a new codebase workspace folder.
  * *CLI command*: `python -m interface.cli register --name <project_name> [--wing <wing>] [--privacy <level>]`
* **`concierge_mine`**: Traverses project, chunks files, generates summaries, embeds code, and stores data.
  * *CLI command*: `python -m interface.cli mine --path <absolute_path> --name <project_name>`
* **`delete_project`**: Completely purges a project and all associated relational/vector records.
  * *CLI command*: `python -m interface.cli delete --project <uuid_or_name>`
* **`update_project`**: Modifies registered details (name, wing, privacy levels, description).
* **`concierge_list_projects`**: Lists all projects inside the local database.
  * *CLI command*: `python -m interface.cli projects`

### 2. Advanced Search
* **`concierge_search`**: Runs the complete Hybrid Search v4 pipeline.
  * *CLI command*: `python -m interface.cli search --query "<query>" --project <uuid_or_name> [--top_k <k>]`
* **`search_symbols`**: Instantly searches class/function names in the FTS5 index.
* **`get_implementations`**: Returns the complete raw code block for a given symbol ID.
* **`get_callers`**: Lists all caller nodes that point to the specified symbol.
* **`find_similar`**: Finds other workspaces registered under the same wing.

### 3. Cognitive Context & Trajectories
* **`concierge_wakeup`**: Resuscitates the agent's memory for a workspace by fetching the L2 Context Compass, Reference Wings, and recent commits.
  * *CLI command*: `python -m interface.cli wakeup --project <uuid>`
* **`concierge_resume`**: Retrieves the Context Compass (recursive macro summary) of the project.
  * *CLI command*: `python -m interface.cli resume --project <uuid>`
* **`concierge_load`**: On-demand node loader (Lazy Load) returning metadata, contents, and relationships.
* **`get_trajectories`**: Retrieves the detailed bi-temporal history of navigation steps.

### 4. Facts & Preferences
* **`concierge_store_fact`**: Evaluates and records a semantic fact (preferences/rules) using bi-temporal invalidation.
* **`concierge_set_memory`**: Stores user core memory blocks (e.g. `preferred_language`, `persona`).
* **`concierge_get_memory`**: Retrieves saved core memory blocks.
* **`concierge_feedback`**: Registers search feedback to optimize search weights (Bayesian Thompson Sampling).

---

## 🔧 Installation & Configuration

### Prerequisites
* Python 3.10+
* Google Gemini or OpenAI API Key (required for LLM summarization and auditing).

### Configuration Setup
1. Clone the repository.
2. Create a `.env` file in the root directory:
```env
# LLM Provider Configuration
GRAFO_LLM_API_KEY=your_api_key_here
GRAFO_LLM_MODEL=gemini-2.5-flash

# Vector Backend (Chroma or Qdrant)
GRAFO_VECTOR_BACKEND=chroma

# (Optional) Qdrant Cloud Configuration
# GRAFO_VECTOR_BACKEND=qdrant
# QDRANT_URL=https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-1-0.aws.cloud.qdrant.io:6333
# QDRANT_API_KEY=your_qdrant_cloud_api_key
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the MCP Server
To boot the Model Context Protocol server:
```bash
python -m interface.mcp_server
```

---

## 🧪 Test Suite & Code Verification

To run the automated test suite:
```bash
python -m pytest
```

To run the complete health diagnostic checks on the memory systems:
```bash
python -m tests.check_brain
```

---

## 📄 License
Distributed under the MIT license. See `LICENSE` for more information.