# 🔍 Hybrid Search v4, Self-Healing & Frugal GraphRAG (v4.0.0)

> **Mathematical Specification of the Tri-Signal Retrieval Model, Query-Time Self-Healing Filter, and Frugal GraphRAG with Strict Delimited Loop Guard**

---

## 1. The Tri-Signal Ranking Formula

Search in Grafo Concierge (`concierge_search` & `core/hybrid_search.py`) executes via the **Hybrid Search v4** scoring engine:

$$\boxed{\text{Score} = (0.50 \times S_{\text{vector}}) + (0.25 \times S_{\text{fts5}}) + (0.25 \times \max(S_{\text{recency}}, S_{\text{centrality}}))}$$

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

Academic GraphRAG implementations incur excessive costs and RAM consumption through heavy network partition algorithms (e.g. Leiden / Louvain). Grafo Concierge replaces this with three frugal mechanisms:

### 3.1 Natural Community Topological Mapping ($O(1)$)
`GraphRAGEngine.get_natural_community(file_path)` maps files to their immediate parent directories:
* `core/utils/delta.py` $\rightarrow$ `core/utils`
* `main.py` $\rightarrow$ `root`

### 3.2 Degree Outlier Supernode Filtering (`detect_logical_communities`)
In real-world codebases, generic utility hubs (e.g., `utils.py`, `database.py`, `types.ts`) are imported by nearly every module. Naive community clustering merges the entire graph through these hubs into a single monolithic component, destroying cluster granularity.

Under **Active-SDD #14**, `GraphRAGEngine.detect_logical_communities(in_degree_threshold=5)` implements a **Degree Outlier Filter**:
1. **Hub Detection**: Analyzes node in-degrees in `ast_edges` (`GROUP BY child_node HAVING in_degree > ?`). Nodes exceeding the threshold are tagged as **Supernodes**.
2. **Bridge Isolation**: Excludes supernode edges during topological clustering so they do not act as artificial bridges between distinct business domains.
3. **Union-Find Clustering**: Groups clean edges into disjoint connected components (`community_{root}`).
4. **Directory Fallback**: Supernodes are isolated as directory satellites (`hub_satellite_{dir}`), maintaining local relevance without collapsing global clusters.

```
       [auth.py] ──► [routes.py]           [order.py] ──► [checkout.py]
             │              │                     │               │
             ▼              ▼                     ▼               ▼
        ┌─────────────────────────────────────────────────────────────┐
        │        [utils.py]  (Supernode / In-Degree = 4)              │
        │        Isolated as `hub_satellite_src`                      │
        └─────────────────────────────────────────────────────────────┘
        Cluster A: {auth.py, routes.py}     Cluster B: {order.py, checkout.py}
```

### 3.3 Recursive Multi-Hop Dependency Resolution with Strict Loop Guard
To resolve call chains across multiple files, `get_call_chain_recursive()` executes a native `WITH RECURSIVE` query over `ast_edges`. Protected by strict pipe-delimited cycle guards:

```sql
WITH RECURSIVE call_chain(node, depth, path_visited) AS (
    -- Anchor: Select start node and initialize delimited visited tracker
    SELECT 
        ? AS node, 
        0 AS depth, 
        '|' || ? || '|' AS path_visited
    
    UNION ALL
    
    -- Recursive Member: Join with edges and check cycle guard
    SELECT 
        e.child_node AS node,
        cc.depth + 1 AS depth,
        cc.path_visited || e.child_node || '|' AS path_visited
    FROM ast_edges e
    JOIN call_chain cc ON e.parent_node = cc.node
    WHERE cc.depth < ?  -- Physical depth limit guard
      AND instr(cc.path_visited, '|' || e.child_node || '|') = 0  -- Strict Loop Block
)
SELECT DISTINCT node, depth FROM call_chain
WHERE node != ?;  -- Exclude root start node from its own dependencies
```

#### Why Strict Pipe Delimiters (`|`)?
* **Zero Substring Collisions**: Searching for `auth.js` inside `'|oauth.js|'` yields `instr('|oauth.js|', '|auth.js|') = 0`, allowing legitimate sibling files to be traversed without false-positive blocks.
* **Instant Cycle Interruption**: An indirect cycle such as $A \rightarrow B \rightarrow C \rightarrow A$ is blocked immediately when $C$ attempts to visit $A$, terminating recursive expansion without stack overflows or memory spikes.

---

## 4. Lightweight RAM-Saving Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)

When deploying on resource-constrained servers ($4/mo VPS, 512MB RAM), setting `GRAFO_LIGHTWEIGHT_MODE=true` disables neural embeddings completely and routes all discovery through SQLite FTS5 BM25, operating in $< 35\text{MB}$ RAM.
