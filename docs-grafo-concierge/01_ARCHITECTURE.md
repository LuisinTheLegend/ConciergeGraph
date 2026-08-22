# 🏛️ Grafo Concierge — System Architecture (v3.8.3)

> **The Sovereign Cognitive Memory & Long-Term Memory (LTM) Infrastructure for AI Agents, IDEs & Developer Environments**

---

## 1. Executive Summary & Survival Paradigm

**Grafo Concierge** is an open-source, high-performance Long-Term Memory (LTM) server engineered to eliminate LLM context window fragmentation, prompt bloat, codebase amnesia, and runaway cloud API billing.

Under the **Survival Engineering Paradigm (Fatias Verticais de Sobrevivência)**, the system is architected to guarantee local operability with Zero Technical Debt:
1. **Serialized SQLite WAL Concurrency (`SerializedWriteQueue` / `ConciergeDatabaseManager`)**: Completely eliminates `database is locked` errors by channeling all writes (`INSERT`, `UPDATE`, `DELETE`, `DDL`) through a dedicated single-writer daemon thread while serving read queries concurrently through WAL mode.
2. **Structural Delta Sync & SSH (`DeltaManager`)**: Differentiates structural code changes (`def`, `class`, `import`, `from`) from internal logic tweaks using SHA-256 Structural Signature Hashes (SSH). Internal logic modifications update content silently without invalidating the knowledge graph or incurring LLM token costs.
3. **Lazy Summarization JIT & SLM Offloading (`BackgroundJanitor`)**: Postpones AI re-summarization until context is actively queried, delegating background processing to free local Small Language Models (SLMs via Ollama) during idle cycles.
4. **Query-Time Self-Healing & Vector Reconciliation (`HybridSearchEngine` / `VectorReconciler`)**: Solves SQLite vs. Qdrant desynchronization without slow, blocking Two-Phase Commits (2PC). Queries automatically filter out orphan vectors in real-time ($O(1)$ lookup), while a background Janitor physically purges orphans via set-difference algorithms.
5. **Frugal GraphRAG & Recursive CTEs (`GraphRAGEngine`)**: Eliminates RAM-heavy graph clustering algorithms by adopting physical directories as natural community boundaries ($O(1)$ topological mapping) and executing multi-hop call-chain traversals directly in SQLite via `WITH RECURSIVE` queries protected by cycle guards.
6. **Agnostic State Checkpointing & Time-Travel (`AgnosticCheckpointer`)**: Provides generic, agent-agnostic persistence for arbitrary AI state dictionaries stored as JSON blobs under composite primary keys (`agent_id`, `session_id`, `checkpoint_id`), enabling hermetic isolation and chronological rollback navigation.
7. **Early-Exit Reactive Watcher (`ConciergeFileSystemHandler`)**: Filters file modification events against `.conciergeignore` / `pathspec` rules *before* hitting disk I/O, protecting the indexing pipeline from `node_modules`, `.env`, and build artifact noise.
8. **Resource Isolation & Security (`AgentDependencies`)**: Encapsulates workspace paths, database managers, and security boundaries within an immutable frozen dataclass, preventing Path Traversal vulnerabilities.

---

## 2. Layered Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │            MCP Clients (Claude Desktop / Cursor)        │
                    │               External Multi-Agent Swarms               │
                    └────────────────────────────┬────────────────────────────┘
                                                 │  JSON-RPC / SSE (FastMCP)
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🌐 INTERFACE LAYER (interface/mcp_server.py, interface/watcher.py, interface/cli.py)        │
│ - FastMCP Server with stdio & SSE transports (30 Specialized Native Tools)                  │
│ - Security Middleware: Bearer Token Auth (GRAFO_API_KEY) & CORS                             │
│ - Early-Exit Reactive File Watcher (pathspec / .conciergeignore)                            │
│ - SerializedWriteQueue (Single-Writer Daemon Thread for SQLite WAL)                         │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 CORE & SURVIVAL LAYER (core/ middleware, delta_manager, search_engine, graph_rag, ...)   │
│ - DeltaManager: SHA-256 Structural Signature Hash (SSH) & Lazy Summarization JIT            │
│ - HybridSearchEngine: Tri-signal score + Query-Time Self-Healing Filter                     │
│ - GraphRAGEngine: Topological natural communities & SQLite WITH RECURSIVE call chains       │
│ - AgnosticCheckpointer: Agent-agnostic state blobs & chronological Time-Travel timeline    │
│ - VectorReconciler & BackgroundJanitor: Offline orphan expurging & SLM local offloading    │
│ - AgentDependencies: Immutable frozen dataclass container with path traversal defense       │
│ - Cognitive Fact Engine: Bi-temporal fact consolidation (ADD / UPDATE / DELETE / NOOP)      │
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
│ 💾 STORAGE LAYER (storage/ & core/database.py)                                              │
│ ┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ SQLite WAL Engine (storage/connection.py)    │ │ Vector Store (core/vector_backend.py)   │ │
│ │ - SerializedWriteQueue (Single-Writer Daemon)│ │ - ChromaVectorStore (Local Default)     │ │
│ │ - Thread-Local Read Pool (Concurrent WAL)    │ │ - QdrantVectorStore (Local / Cloud)     │ │
│ │ - Core + Survival Relational Tables + FTS5   │ │ - EmbeddingManager (MiniLM / Cloud)     │ │
│ └──────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Storage Layer & Concurrency Engine

### 3.1 `SerializedWriteQueue` (Zero Database Locks)
SQLite in high-concurrency multi-client environments can suffer from `sqlite3.OperationalError: database is locked`.

Grafo Concierge resolves this through a **Single-Writer Serialized Queue** architecture:
* **Write Operations**: All write mutations (`INSERT`, `UPDATE`, `DELETE`, `DDL`) are submitted to a thread-safe `queue.Queue`. A single dedicated daemon thread (`sqlite-writer`) executes them sequentially inside atomic transactions.
* **Read Operations**: Read queries execute concurrently through `ConciergeDatabaseManager.read_query()` using `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.

### 3.2 Pluggable Vector Backends
* **ChromaDB (`ChromaVectorStore`)**: Default local backend. Persists vectors to disk under `data/chroma/`. Zero external dependencies.
* **Qdrant (`QdrantVectorStore`)**: Recommended for multi-user, multi-agent, or cloud production deployments. Supports local Docker instances or managed **Qdrant Cloud** clusters via `GRAFO_QDRANT_URL` and `GRAFO_QDRANT_API_KEY`.
* **Lightweight Mode (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Disables vector generation and dense embeddings completely, routing all retrieval through SQLite FTS5 BM25. Enables Grafo Concierge to operate on edge devices or low-spec VPS ($4/mo, 512MB RAM).

---

## 4. Complete Database Schema (SQLite WAL)

The relational engine maintains normalized tables for both long-term cognitive graph memory and survival sync operations:

```sql
-- =========================================================================
-- SURVIVAL & DELTA ENGINE TABLES (Fases 1, 2 e 3)
-- =========================================================================

-- 1. Files & Structural Delta Sync
CREATE TABLE IF NOT EXISTS files (
    path         TEXT PRIMARY KEY,
    content      TEXT,
    ssh_hash     TEXT,             -- SHA-256 of structural signature lines
    is_dirty     INTEGER DEFAULT 1,-- 1 = Needs summarization / update, 0 = Clean
    community_id TEXT
);

-- 2. Communities & Frugal GraphRAG
CREATE TABLE IF NOT EXISTS communities (
    id           TEXT PRIMARY KEY, -- Natural directory path or custom cluster
    summary_text TEXT,
    is_dirty     INTEGER DEFAULT 1 -- 1 = Stale summary, 0 = Up-to-date
);

-- 3. AST Call Graph Edges (Recursive CTE Table)
CREATE TABLE IF NOT EXISTS ast_edges (
    parent_node TEXT,
    child_node  TEXT,
    UNIQUE(parent_node, child_node)
);

-- 4. Agnostic State Checkpoints & Time-Travel Timeline
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    agent_id      TEXT,
    session_id    TEXT,
    checkpoint_id TEXT,
    state_blob    TEXT,            -- JSON-serialized arbitrary state dictionary
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, session_id, checkpoint_id)
);

-- =========================================================================
-- COGNITIVE GRAPH & FACT TABLES
-- =========================================================================

-- 5. Projects Registry
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

-- 6. Structural & Semantic Code Nodes
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

-- 7. Graph Relational Edges
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

-- 8. Reference Wings (Cross-Domain Semantic Links)
CREATE TABLE IF NOT EXISTS reference_wings (
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    wing_name     TEXT NOT NULL,
    PRIMARY KEY (project_uuid, wing_name)
);

-- 9. Episodic Trajectories (Agent Cognitive History)
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

-- 10. Memory Commit Log
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

-- 11. Scoped Core Memory Blocks
CREATE TABLE IF NOT EXISTS user_core_memory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type    TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id      TEXT NOT NULL,
    block_label   TEXT NOT NULL,
    content       TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scope_type, scope_id, block_label)
);

-- 12. Bi-Temporal Semantic Facts & Bayesian Utility
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

## 5. Survival Subsystems Breakdown

### 5.1 Delta Manager & Structural Signature Hashing (SSH)
* `DeltaManager.calculate_ssh(content)` extracts lines starting with `def `, `class `, `import `, or `from `, computing a deterministic SHA-256 hash.
* If a file's body/internal logic changes without altering its SSH, `process_file_change()` updates `content` in SQLite, clears `files.is_dirty = 0`, and reconciles the community to `0` if all files are clean.
* If the signature changes, it marks both the file and its community as `is_dirty = 1`.

### 5.2 Query-Time Self-Healing & Vector Reconciler
* `HybridSearchEngine.hybrid_search()` queries the vector store, intercepts candidate IDs, and runs a single parameterized batch query: `SELECT path FROM files WHERE path IN (?, ?, ...);`.
* Orphan vectors (files deleted from disk/SQLite) are dropped in real-time ($O(1)$ response-time filtering).
* `VectorReconciler.reconcile_orphans()` performs an asynchronous $O(N)$ set difference (`set(vector_ids) - set(sqlite_paths)`) and deletes orphaned vector records in batches.

### 5.3 Frugal GraphRAG Engine
* **Natural Communities**: `GraphRAGEngine.get_natural_community()` maps file paths to immediate parent directories (e.g. `core/utils/delta.py` $ightarrow$ `core/utils`), executing in $O(1)$ string operations without loading graphs into RAM.
* **Recursive Call Chains**: `get_call_chain_recursive()` executes a native `WITH RECURSIVE` query over `ast_edges` with a depth limit parameter and cycle protection (`WHERE node != ?`).

### 5.4 Agnostic Checkpointer & Time-Travel Debugging
* `AgnosticCheckpointer` persists and retrieves arbitrary JSON state payloads under `(agent_id, session_id, checkpoint_id)`.
* Idempotent upsert via `INSERT OR REPLACE`.
* `list_checkpoints()` returns a chronological timeline (`ORDER BY created_at ASC`) allowing AI agents to step backwards in time.
