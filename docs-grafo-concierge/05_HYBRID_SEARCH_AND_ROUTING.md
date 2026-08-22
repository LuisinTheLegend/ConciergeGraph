# 🔍 Hybrid Search v4, Self-Healing & Frugal GraphRAG (v3.8.3)

> **Mathematical Specification of the Tri-Signal Retrieval Model, Query-Time Self-Healing Filter, and Frugal GraphRAG Multi-Hop Navigation**

---

## 1. The Tri-Signal Ranking Formula

Search in Grafo Concierge (`concierge_search` & `core/hybrid_search.py`) executes via the **Hybrid Search v4** scoring engine:

$$oxed{    ext{Score} = (0.50     imes S_{    ext{vector}}) + (0.25     imes S_{    ext{fts5}}) + (0.25     imes \max(S_{    ext{recency}}, S_{    ext{centrality}}))}$$

---

## 2. Query-Time Self-Healing Filter (`core/search_engine.py`)

Distributed databases often face desynchronization when files are deleted on disk while their vectors linger in the vector database. Instead of complex Two-Phase Commits (2PC) that block the IDE, Grafo Concierge implements **Eventual Consistency with Query-Time Self-Healing**:

1. **Query Interception**: The `HybridSearchEngine` receives candidate IDs (file paths) from the vector database search.
2. **Concealed Relational Validation**: Executes a single concurrent batch query on SQLite WAL:
   ```sql
   SELECT path FROM files WHERE path IN (?, ?, ?, ...);
   ```
3. **Instant Orphan Descarte**: Drops any vector result whose file path no longer exists in SQLite WAL.
4. **Result**: The AI agent receives a 100% consistent response in $< 5\text{ms}$ with zero zombie files.

---

## 3. Frugal GraphRAG Engine (`core/graph_rag.py`)

Academic GraphRAG implementations incur excessive costs and RAM consumption through heavy network partition algorithms (e.g. Leiden / Louvain). Grafo Concierge replaces this with two frugal mechanisms:

### 3.1 Natural Community Topological Mapping ($O(1)$)
`GraphRAGEngine.get_natural_community(file_path)` maps files to their immediate parent directories:
* `core/utils/delta.py` $
ightarrow$ `core/utils`
* `main.py` $
ightarrow$ `root`

### 3.2 Recursive Multi-Hop Dependency Resolution (SQLite CTE)
To resolve call chains across multiple files, `get_call_chain_recursive()` executes a native `WITH RECURSIVE` query over `ast_edges` with a depth limit and cycle guard:

```sql
WITH RECURSIVE call_chain(node, depth) AS (
    SELECT child_node, 1 FROM ast_edges WHERE parent_node = ?
    UNION
    SELECT e.child_node, cc.depth + 1
    FROM ast_edges e
    JOIN call_chain cc ON e.parent_node = cc.node
    WHERE cc.depth < ?
)
SELECT DISTINCT node FROM call_chain WHERE node != ?;
```

---

## 4. Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)

When deploying on resource-constrained servers ($4/mo VPS, 512MB RAM), setting `GRAFO_LIGHTWEIGHT_MODE=true` disables neural embeddings completely and routes all discovery through SQLite FTS5 BM25, operating in $< 35\text{MB}$ RAM.
