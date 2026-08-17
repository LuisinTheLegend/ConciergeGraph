# 🔍 Hybrid Search v4, Dynamic Routing & Lightweight Mode (v3.8.2)

> **Mathematical Specification of the Tri-Signal Retrieval Model, Wing Scoping, and Edge-Optimized Lightweight Search**

---

## 1. The Tri-Signal Ranking Formula

Search in Grafo Concierge (`concierge_search` & `core/hybrid_search.py`) executes via the **Hybrid Search v4** scoring engine. It unifies semantic embeddings, exact keyword matching, and topological graph signals into a single normalized score between `0.0` and `1.0`:

$$\boxed{\text{Score} = (0.50 \times S_{\text{vector}}) + (0.25 \times S_{\text{fts5}}) + (0.25 \times \max(S_{\text{recency}}, S_{\text{centrality}}))}$$

```
                ┌───────────────────────────────────────────────────────────┐
                │               HYBRID SEARCH v4 SIGNALS                     │
                ├─────────────────────────────┬─────────────────────────────┤
                │ Dense Vector Similarity     │ 50% Weight (Cosine CosSim)  │
                │ SQLite FTS5 BM25            │ 25% Weight (Keyword Match)  │
                │ Max(Recency, Centrality)    │ 25% Weight (Graph Dynamics) │
                └─────────────────────────────┴─────────────────────────────┘
```

---

## 2. Signal Breakdown & Mathematical Derivation

### 2.1 Dense Vector Similarity ($S_{\text{vector}}$)
* Evaluates cosine similarity between the query embedding and stored node/chunk vectors in ChromaDB or Qdrant.
* Captures semantic intent, conceptual synonyms, and high-level conceptual questions (e.g. `"how is user session handled?"`).

### 2.2 Full-Text Keyword Match ($S_{\text{fts5}}$)
* Executes over SQLite's native **FTS5 Virtual Table** (`nodes_fts`) with Okapi BM25 ranking parameters:
  * $k_1 = 1.5$
  * $b = 0.75$
  * Indexed fields: `label` (file path / symbol name), `tags`, and `summary`.
* Guarantees exact matches for precise symbols, function names, error codes, and library imports (e.g. `SerializedWriteQueue`, `jwt.decode`).

### 2.3 Exponential Recency Decay ($S_{\text{recency}}$)
Recent code modifications and commits reflect current developer focus. Older, untouched code decays in relevance over time according to a 7-day half-life:

$$S_{\text{recency}} = \max\left(e^{-\lambda \cdot t},\, 0.01\right)$$

Where:
* $t$: Time elapsed in days since `last_commit_at` or `created_at`.
* $\lambda$: Decay constant defined as $\lambda = \frac{\ln(2)}{7} \approx 0.09902$.

```
     Recency Score
     1.0 ──┐
           │\
     0.5 ──┼─\  (Half-life: 7 days)
           │  \
     0.25 ─┼───\ (14 days)
           │    └───► Floor: 0.01
     0.0 ──┴─────────────────────────► Time (days)
           0   7   14   21   28
```

### 2.4 In-Degree Centrality ($S_{\text{centrality}}$)
Nodes that are frequently imported or referenced by multiple other modules are critical architectural hubs ("Super-Nodes"):

$$S_{\text{centrality}} = \min\left(\frac{\text{In-Degree}}{10},\, 1.0\right)$$

* A node with **10 or more incoming dependency edges** achieves the maximum centrality score of `1.0`.
* By taking $\max(S_{\text{recency}}, S_{\text{centrality}})$, core foundational modules (like `config.py` or database connection pools) maintain high retrieval priority even if they haven't been committed to recently.

---

## 3. Wing Taxonomy & Strict Scoping

To avoid mixing unrelated domain context across multiple client projects, Grafo Concierge organizes repositories into **Wings (Alas)**.

### 3.1 Standard Wing Categories
* **`marketing/vendas`**: Marketing funnels, landing pages, conversion scripts.
* **`finanças/quant`**: Trading bots, quantitative finance, crypto, risk algorithms.
* **`gestão/saas`**: Dashboards, ERPs, SaaS platforms, multi-tenant billing.
* **`automação/rh`**: Workflow automation, spreadsheets, HR integrations, n8n/Zapier.
* **`estatística`**: Data science, analytics, machine learning datasets.
* **`geral`**: General-purpose utilities and unclassified software.

### 3.2 Scoping Modes

| Search Mode | Flag | Target Scope |
| :--- | :--- | :--- |
| **Strict Scoping (Default)** | `include_references=False, all_wings=False` | Searches exclusively within the project's `primary_wing`. |
| **Interdisciplinary Search** | `include_references=True` | Expands search to include linked `reference_wings`. |
| **Global Discovery** | `all_wings=True` | Searches across all registered projects in the database. |

### 3.3 Dynamic Fallback Routing
If Strict Scoping in the primary wing yields zero high-confidence results (e.g. best score $< 0.35$), the hybrid engine dynamically triggers a fallback query across `reference_wings` to prevent false negatives.

---

## 4. Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)

When deploying on resource-constrained servers (e.g. $4/month VPS, Docker containers with 512MB RAM, Raspberry Pi), loading large Transformer embedding models (like `all-MiniLM-L6-v2` or `sentence-transformers`) can cause Out-Of-Memory (OOM) crashes.

### 4.1 How Lightweight Mode Operates
Setting `GRAFO_LIGHTWEIGHT_MODE=true` in `.env`:
1. **Completely skips initializing neural embedding models** and vector databases (zero RAM overhead from PyTorch/ONNX).
2. **Routes 100% of retrieval through SQLite FTS5 BM25** and graph centrality/recency signals.
3. System idle memory drops from ~450MB down to **< 35MB RAM**.

```
                ┌────────────────────────────────────────────────────────┐
                │          LIGHTWEIGHT MODE RETRIEVAL FLOW               │
                ├────────────────────────────────────────────────────────┤
                │ Client Query ──► FTS5 BM25 Tokenizer (SQLite)          │
                │              ──► BM25 Score + Max(Recency, Centrality) │
                │              ──► Top Results in < 5ms                  │
                └────────────────────────────────────────────────────────┘
```
