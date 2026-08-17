# 🏛️ Grafo Concierge — System Architecture (v3.8.2)

> **The Sovereign Cognitive Memory & Long-Term Memory (LTM) Infrastructure for AI Agents, IDEs & Developer Environments**

---

## 1. Executive Summary & Vision

**Grafo Concierge** is an open-source, high-performance Long-Term Memory (LTM) server engineered to eliminate LLM context window fragmentation, prompt bloat, and codebase amnesia.

Unlike simple vector-only RAG scripts, Grafo Concierge acts as a **bi-temporal, hybrid semantic knowledge graph**. It combines:
1. **Relational SQLite Persistence (WAL Mode)** with thread-safe serialization (`SerializedWriteQueue`).
2. **Pluggable Vector Storage** (ChromaDB for zero-config local setups, Qdrant / Qdrant Cloud for enterprise scale).
3. **Multi-Language AST Parsing** via Tree-sitter for structural symbol extraction (`CLASS`, `FUNCTION`, `METHOD`) and call graph generation.
4. **Bi-Temporal Semantic Facts** with temporal validity tracking (`t_valid` / `t_invalid`) and automated LLM-based memory consolidation (`SemanticExtractor`).
5. **Probabilistic Thompson Sampling** for dynamic reinforcement learning of memory utility.
6. **Autonomous Background Maintenance** (`JanitorService`) for bidirectional vector synchronization, garbage collection, and exponential recency decay.

---

## 2. High-Level System Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │            MCP Clients (Claude Desktop / Cursor)        │
                    │               CLI / Autonomous Agent Workflows          │
                    └────────────────────────────┬────────────────────────────┘
                                                 │  JSON-RPC / SSE (FastMCP)
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🌐 INTERFACE LAYER (interface/mcp_server.py, interface/cli.py)                              │
│ - FastMCP Server with stdio & SSE transports                                                │
│ - Security Middleware: Bearer Token Auth (GRAFO_API_KEY) & CORS                             │
│ - 26 Specialized Cognitive & Management Tools                                               │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 CORE LAYER (core/middleware.py, core/hybrid_search.py, core/memory_extractor.py)         │
│ - Central Facade (GrafoConcierge): Project Indexing, Wakeup, Resume Compass                 │
│ - Hybrid Search v4: Tri-signal score (0.50 Vector + 0.25 FTS5 + 0.25 Max(Recency, InDegree)) │
│ - Cognitive Fact Engine: ADD, UPDATE (bi-temporal), DELETE, NOOP consolidation              │
│ - Probabilistic Retriever: Thompson Sampling over Beta(alpha, beta) memory utility           │
└──────────────────┬──────────────────────────────────────────┬───────────────────────────────┘
                   │                                          │
                   ▼                                          ▼
┌──────────────────────────────────────┐   ┌──────────────────────────────────────────────────┐
│ 📥 INGESTION ENGINE (ingestion/)     │   │ 🧹 MAINTENANCE LAYER (services/janitor.py)       │
│ - ProjectCrawler: Delta Hash Check   │   │ - JanitorService: Autonomous Background Daemon   │
│ - FileParser: Tree-sitter AST & Tags │   │ - Bidirectional Vector Reconciliation            │
│ - ZoomSummarizer: L0/L1/L2 Summaries │   │ - Orphan Embedding & Stale Project Pruner       │
│ - IngestionManager: Batch Pipeline   │   │ - Exponential Recency Decay & VACUUM Maintenance │
└──────────────────┬───────────────────┘   └──────────────────┬───────────────────────────────┘
                   │                                          │
                   ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 💾 STORAGE LAYER (storage/)                                                                 │
│ ┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ SQLite Engine (storage/connection.py)        │ │ Vector Store (core/vector_backend.py)   │ │
│ │ - SerializedWriteQueue (Single-Writer Thread)│ │ - ChromaVectorStore (Local Default)     │ │
│ │ - Thread-Local Read Pool (WAL Mode)          │ │ - QdrantVectorStore (Local / Cloud)     │ │
│ │ - 8 Core Tables + FTS5 Full-Text Search      │ │ - EmbeddingManager (MiniLM / Cloud)     │ │
│ └──────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Storage Layer & Concurrency Engine

### 3.1 `SerializedWriteQueue` (Zero Database Locks)
SQLite in high-concurrency multi-client environments (e.g., Cursor IDE calling MCP tools while the Janitor daemon runs in the background) can suffer from `sqlite3.OperationalError: database is locked`.

Grafo Concierge resolves this through a **Single-Writer Serialized Queue** architecture:
* **Write Operations**: All write mutations (`INSERT`, `UPDATE`, `DELETE`) are wrapped in `_WriteJob` objects and submitted to a thread-safe `queue.Queue`. A single dedicated daemon thread (`sqlite-writer`) executes them sequentially inside atomic transactions.
* **Read Operations**: Read queries execute concurrently using **Thread-Local Connections** (`threading.local`) configured with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.

### 3.2 Pluggable Vector Backends
* **ChromaDB (`ChromaVectorStore`)**: Default local backend. Persists vectors to disk under `data/chroma/`. Zero external dependencies.
* **Qdrant (`QdrantVectorStore`)**: Recommended for multi-user, multi-agent, or cloud production deployments. Supports local Docker instances or managed **Qdrant Cloud** clusters via `GRAFO_QDRANT_URL` and `GRAFO_QDRANT_API_KEY`.
* **Lightweight Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Disables vector generation and dense embeddings completely, routing all retrieval through SQLite FTS5 BM25. Enables Grafo Concierge to operate on edge devices or low-spec VPS ($4/mo, 512MB RAM).

---

## 4. Official Database Schema (SQLite)

The SQLite database consists of **8 normalized relational tables** with inline `CHECK` constraints, foreign keys, performance indexes, and virtual FTS5 tables:

```sql
-- 1. Projects Registry
CREATE TABLE IF NOT EXISTS projects (
    uuid          TEXT PRIMARY KEY,
    folder_name   TEXT NOT NULL,
    primary_wing  TEXT NOT NULL DEFAULT 'geral',
    privacy_level TEXT NOT NULL DEFAULT 'PUBLIC' 
        CHECK(privacy_level IN ('PUBLIC', 'INTERNAL', 'RESTRICTED')),
    summary       TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. Structural & Semantic Code Nodes
CREATE TABLE IF NOT EXISTS nodes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid      TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    label             TEXT NOT NULL,
    summary           TEXT,
    content           TEXT,
    node_type         TEXT NOT NULL DEFAULT 'FACT' 
        CHECK(node_type IN ('FACT', 'SKILL', 'INSIGHT', 'TRAJECTORY', 'PATCH', 'CLASS', 'FUNCTION', 'METHOD', 'MODULE')),
    type              TEXT NOT NULL DEFAULT 'file',
    tags              TEXT,          -- JSON Array: ["python", "fastapi", "auth"]
    file_hash         TEXT,          -- SHA-256 for delta chunk caching
    last_accessed     TEXT,
    last_commit_at    TEXT,
    status            TEXT NOT NULL DEFAULT 'ACTIVE' 
        CHECK(status IN ('ACTIVE', 'STALE', 'ARCHIVED')),
    valid_from_commit TEXT NULL,
    valid_to_commit   TEXT NULL
);

-- 3. Dependency & Structural Graph Edges
CREATE TABLE IF NOT EXISTS edges (
    source_id         INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id         INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation_type     TEXT NOT NULL DEFAULT 'depends_on',
    weight            REAL NOT NULL DEFAULT 1.0,
    valid_from_commit TEXT NULL,
    valid_to_commit   TEXT NULL,
    confidence_tag    TEXT NOT NULL DEFAULT 'EXTRACTED'
        CHECK(confidence_tag IN ('EXTRACTED', 'INFERRED', 'AMBIGUOUS')),
    PRIMARY KEY (source_id, target_id)
);

-- 4. Reference Wings (Cross-Domain Semantic Links)
CREATE TABLE IF NOT EXISTS reference_wings (
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    wing_name     TEXT NOT NULL,
    PRIMARY KEY (project_uuid, wing_name)
);

-- 5. Episodic Trajectories (Agent Cognitive History & Error Biographies)
CREATE TABLE IF NOT EXISTS trajectories (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid       TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    prompt_origem      TEXT NOT NULL,
    tentativa_execucao TEXT NOT NULL,
    erro_encontrado    TEXT,
    solucao_aplicada   TEXT,
    status             TEXT NOT NULL DEFAULT 'ACTIVE' 
        CHECK(status IN ('ACTIVE', 'STALE', 'ARCHIVED')),
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 6. Memory Commit Log (Changelogs & Architectural Changes)
CREATE TABLE IF NOT EXISTS commit_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid      TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    phase             TEXT NOT NULL,
    technical_changes TEXT NOT NULL,
    updated_pointers  TEXT NOT NULL, -- JSON Array of modified file paths
    revisor_approved  INTEGER NOT NULL DEFAULT 0,
    partial_audit     INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7. Scoped Core Memory Blocks
CREATE TABLE IF NOT EXISTS user_core_memory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type    TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id      TEXT NOT NULL,
    block_label   TEXT NOT NULL,
    content       TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scope_type, scope_id, block_label)
);

-- 8. Bi-Temporal Semantic Facts & Bayesian Utility
CREATE TABLE IF NOT EXISTS semantic_facts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type     TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id       TEXT NOT NULL,
    fact_statement TEXT NOT NULL,
    t_valid        TEXT NOT NULL DEFAULT (datetime('now')),
    t_invalid      TEXT NULL,     -- Populated on revocation/update
    utility_alpha  REAL NOT NULL DEFAULT 1.0, -- Bayesian Successes
    utility_beta   REAL NOT NULL DEFAULT 1.0, -- Bayesian Failures
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Virtual Table: Full-Text Search (FTS5 BM25)
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label, tags, summary,
    content='nodes',
    content_rowid='id'
);
```

---

## 5. Core Subsystems

### 5.1 Hybrid Search v4 Engine
Retrieval executes through a tri-signal mathematical scoring model:

$$\text{Final Score} = (0.50 \times \text{Vector Similarity}) + (0.25 \times \text{Normalized FTS5}) + (0.25 \times \max(\text{Recency}, \text{Centrality}))$$

* **Recency Score**: Computed via exponential half-life decay: $\text{Recency} = \max(e^{-\lambda \cdot t}, 0.01)$ where $\lambda = \frac{\ln(2)}{7\text{ days}}$.
* **Centrality Score**: Graph in-degree normalized: $\text{Centrality} = \min\left(\frac{\text{In-Degree}}{10}, 1.0\right)$.
* **Strict Scoping**: By default, search is physically constrained to the project's `primary_wing`. Setting `include_references=True` expands the scope to `reference_wings`, and `all_wings=True` performs global multi-project discovery.

### 5.2 Bi-Temporal Facts & `SemanticExtractor`
* When storing facts via `concierge_store_fact`, the `SemanticExtractor` prompts an LLM to evaluate the new statement against all currently active facts (`t_invalid IS NULL`) for that scope.
* Possible actions:
  * **`ADD`**: Completely new fact.
  * **`UPDATE`**: Invalidates old fact (`t_invalid = now()`) and inserts consolidated statement.
  * **`DELETE`**: Revokes superseded/negated fact (`t_invalid = now()`).
  * **`NOOP`**: Redundant information discarded with zero storage bloat.

### 5.3 Thompson Sampling (Probabilistic Retriever)
* Balances cognitive **exploration** and **exploitation** using Beta distribution sampling: $\text{Multiplier} \sim \text{Beta}(\alpha, \beta)$.
* High-utility facts ($\alpha \gg \beta$) are prioritized, while under-explored facts maintain a probabilistic chance of being recalled to verify their ongoing relevance.

### 5.4 Autonomous Janitor Daemon
Running as a background worker thread (`services/janitor.py`), the Janitor performs:
1. **Bidirectional Vector Sync**: Reconciles SQLite nodes with vector collections, generating missing embeddings and deleting orphan vectors.
2. **Stale Project Pruning**: Decays inactive projects older than threshold days.
3. **Database Compaction**: Executes `PRAGMA optimize` and `VACUUM` during idle periods.
4. **Memory Leak Protection**: Limits in-memory maintenance history with strict FIFO rotation.
