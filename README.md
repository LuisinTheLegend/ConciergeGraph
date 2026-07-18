# 🧠 Grafo Concierge v3.8.2
**The Long-Term Memory (LTM) Palace for AI Agents**

Grafo Concierge is a local cognitive memory infrastructure designed to solve LLM "amnesia" in complex projects. Unlike simple RAG systems, it utilizes a robust architecture combining relational persistence, vector search, hierarchical synthesis, and an autonomous maintenance system.

## 💡 The Problem We Solve (In Simple Terms)
Imagine you are building a giant software project with the help of an Artificial Intelligence. Over time, the AI starts to "forget" how files connect or the rules you defined in the past, simply because its "short-term memory" (context window) has filled up.

**Grafo Concierge** acts as an **external and permanent brain** for the AI. It tracks your entire project, understands the connections between files, and always provides the AI with exactly the information it needs to work, without forgetting the past.

## 🚀 Colossal Performance (Benchmarks)
Validated by the **Colossus Protocol**, the system demonstrated linear scalability and sub-second latency in Big Data environments.

| Metric | Result (20,000 nodes) |
| --- | --- |
| **Search Latency (P50)** | 41.69 ms |
| **Search Latency (P99)** | 112.75 ms |
| **Scalability Factor** | 0.93x (Performance preserved at high volume) |
| **Ingestion (SQLite)** | ~536 nodes/second |
| **Ingestion (ChromaDB)** | ~914 vectors/second |
| **Maintenance (Janitor)** | 20,000 orphans cleaned in ~11s |

### Understanding Terms and Metrics
- **P50 (50th Percentile / Median):** Indicates that 50% of the searches returned results in this time or faster. It is the "typical" latency experienced by the user.
- **P99 (99th Percentile):** Indicates that 99% of the searches were faster than this time. It represents the "worst-case scenario", proving the stability of the system under pressure.
- **Nodes:** The fundamental units of memory in the Graph. A node is not just text: it can represent an architectural fact, a business rule, a code file, or a decision made, all interconnected.
- **Zoom Gear (L0/L1/L2):** Our autonomous hierarchical context compression algorithm.
  - **L0 (Micro):** Detailed summary of a single file or chunk ingested.
  - **L1 (Meso):** Synthesis of multiple L0s, describing the purpose of an entire module or directory.
  - **L2 (Macro - Compass):** Global architectural summary of the project. It is used to provide the perfect initial context to AI Agents without blowing the token limit (Context Window).


## 🏛️ Architecture: Layer Division
The system is divided into modular layers to ensure that memory is organized, audited, and long-lasting:

- **`core/` (The Nervous System):** Centralizes the Hybrid Search v4 logic (Vector + FTS5 + Graph Signals) and the central facade of the system.
- **`storage/` (The Foundation):** Thread-safe atomic management of SQLite read connections and isolated serialized writes (WAL mode), plus vector persistence via ChromaDB.
- **`ingestion/` (O Motor Apex):** Code extraction pipeline, intelligent crawling, compatible multi-language AST detection, and the Zoom Gear (L0/L1/L2).
- **`agents/` (The Guardians):** AI agents dedicated to semantic Reranking and surgical auditing of commits, preventing context contamination.
- **`services/` (The Maintenance):** The Janitor, an autonomous background service that handles temporal decay and history cleanup without memory leaks.
- **`interface/` (O Portal):** Native MCP (Model Context Protocol) server extended for the complete lifecycle of projects, plus a CLI panel.

## 🛠️ Hybrid Search v4 Technology
Relevance is calculated using a weighted composition that prioritizes exact context and information recency:

1. **Vector Search (50%):** Deep semantic similarity via embeddings.
2. **FTS5 Search (25%):** Exact keyword matching (normalized BM25).
3. **Graph Signals (25%):** The higher value between temporal Recency and node Centrality (relational weight).

Recency follows an exponential decay formula, ensuring that memory "ages" gracefully and makes room for new facts over time:
$$W = W_0 \cdot e^{-\lambda t}$$

## 🔧 Installation and Usage

**Prerequisites:**
- Python 3.10+
- API Key (Google Gemini / OpenAI) for the Zoom Gear and Auditors.

**Configuration:**
1. Clone the repository.
2. Create a `.env` file in the root (securely ignored in `.gitignore`):
```env
GRAFO_LLM_API_KEY=your_key_here
GRAFO_LLM_MODEL=gemini-2.5-flash
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

**Execution:**
To start the MCP server and expose all cognitive memory and project lifecycle tools to the LLM:
```bash
python -m interface.mcp_server
```

## 🧪 Test Suite & Continuous Integration (Absolute Solidity)
The project features an exhaustive suite of integrated and unit tests with native auto-discovery configured in `pyproject.toml` and a CI pipeline via **GitHub Actions** (`ci.yml`).

To run the automated test suite:
```bash
python -m pytest
```

To run the complete health diagnostic and local memory sanitization check:
```bash
python tests/check_brain.py
```

## 📄 License
Distributed under the MIT license. See `LICENSE` for more information.