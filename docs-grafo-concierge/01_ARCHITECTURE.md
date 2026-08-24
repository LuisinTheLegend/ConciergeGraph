# 🏛️ Grafo Concierge — System Architecture (v4.0.0)

> **The Sovereign Cognitive Memory & Long-Term Memory (LTM) Infrastructure for AI Agents, IDEs & Developer Environments**

---

## 1. Executive Summary & Survival Paradigm

**Grafo Concierge** is an open-source, high-performance Long-Term Memory (LTM) server engineered to eliminate LLM context window fragmentation, prompt bloat, codebase amnesia, and runaway cloud API billing.

Under the **Survival Engineering Paradigm (Fatias Verticais de Sobrevivência & Resiliência Extrema)**, the system is architected to guarantee local operability with Zero Technical Debt:
1. **Serialized SQLite WAL Concurrency with Auto-Batching & Single-Item Fallback (`SerializedWriteQueue` / `ConciergeDatabaseManager`)**: Completely eliminates `database is locked` errors by channeling all writes (`INSERT`, `UPDATE`, `DELETE`, `DDL`) through a dedicated single-writer daemon thread. Under heavy concurrency, drains pending writes opportunistically (up to 50 items) in atomic `BEGIN IMMEDIATE ... COMMIT` blocks without artificial latency timers. If a constraint fails, it triggers a non-blocking `ROLLBACK` and executes a **Single-Item Fallback** to rescue all healthy items.
2. **Dual-Hash Delta Sync: SSH & LBH Semantic Drift Guard (`DeltaManager` / `DocstringStripper`)**: Combines Structural Signature Hashing (SSH) for public signatures (`def`, `class`, `import`, `from`) with Logical Body Hashing (LBH). The LBH cleans AST docstrings via `DocstringStripper(ast.NodeTransformer)` and computes SHA-256 over `ast.dump()`. Internal logic changes (e.g. operators, return values) mark the file as `is_dirty = 1` for accurate graph memory, while cosmetic changes (comments, whitespace, docstrings) maintain `is_dirty = 0`, saving 100% of LLM token costs.
3. **Lazy Summarization JIT & SLM Offloading (`BackgroundJanitor`)**: Postpones AI re-summarization until context is actively queried, delegating background processing to free local Small Language Models (SLMs via Ollama) during idle cycles.
4. **Smart Checkpoint Pruning (`BackgroundJanitor.prune_session_checkpoints`)**: Implements an intelligent Smart LRU per Session algorithm that prevents database bloat in `state.db`. Inviolably protects the initial "point zero" checkpoint (`"init"` / earliest timestamp) for hard resets while retaining the last $N$ active steps (default: 10) and purging obsolete intermediate records in paginated batches via `SerializedWriteQueue`.
5. **Query-Time Self-Healing & Vector Reconciliation (`HybridSearchEngine` / `VectorReconciler`)**: Solves SQLite vs. Qdrant desynchronization without slow, blocking Two-Phase Commits (2PC). Queries automatically filter out orphan vectors in real-time ($O(1)$ lookup), while a background Janitor physically purges orphans via set-difference algorithms.
6. **Frugal GraphRAG, Supernode Outlier Filtering & Strict Delimited CTE Loop Guards (`GraphRAGEngine`)**: Eliminates RAM-heavy graph clustering algorithms by combining $O(1)$ topological directory mapping with a **Degree Outlier Filter** that isolates high in-degree supernodes (e.g., `utils.py`) into `hub_satellite_{dir}` clusters to prevent topological collapse, while multi-hop call-chains are traversed in SQLite via `WITH RECURSIVE` queries protected by strict pipe-delimited cycle guards (`|node|` matching via `instr()`).
7. **Hardware-Aware Thermal Throttling & Rate Governor (`BackgroundJanitor.check_hardware_clearance`)**: Prevents CPU exhaustion and developer distraction by inspecting host CPU utilization ($<40\%$) and active typing quiet periods before triggering background local SLM summarizations, executing at reduced OS priority (`IDLE_PRIORITY_CLASS` on Windows, `nice(15)` on Unix).
8. **Real-Time Telemetry & SSE Streaming Layer (`interface/telemetry_api.py` / `core/telemetry_schemas.py`)**: Exposes structured Pydantic v2 schemas and low-latency Server-Sent Events (`/api/telemetry/stream`) alongside REST snapshots (`/api/telemetry/snapshot`) and manual reconcile triggers, enabling real-time dashboard observability with zero polling overhead.
9. **Zero-NumPy Native Bayesian Thompson Sampling (`core/probabilistic_retriever.py`)**: Replaces the 30MB external NumPy dependency with Python's built-in `random.betavariate()` and input parameter sanitization (`max(val, 1e-5)`), delivering exact statistical equivalence and rock-solid memory ranking without footprint bloat.
10. **Agnostic State Checkpointing & Time-Travel (`AgnosticCheckpointer`)**: Provides generic, agent-agnostic persistence for arbitrary AI state dictionaries stored as JSON blobs under composite primary keys (`agent_id`, `session_id`, `checkpoint_id`), enabling hermetic isolation and chronological rollback navigation.
11. **Early-Exit Reactive Watcher (`ConciergeFileSystemHandler`)**: Filters file modification events against `.conciergeignore` / `pathspec` rules *before* hitting disk I/O, protecting the indexing pipeline from `node_modules`, `.env`, and build artifact noise.
12. **Resource Isolation & Security (`AgentDependencies`)**: Encapsulates workspace paths, database managers, and security boundaries within an immutable frozen dataclass, preventing Path Traversal vulnerabilities.

---

## 2. Layered Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │            MCP Clients (Claude Desktop / Cursor)        │
                    │            Next.js Dashboard & Multi-Agent Swarms       │
                    └────────────────────────────┬────────────────────────────┘
                                                 │  JSON-RPC / FastMCP & FastAPI REST/SSE
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🌐 INTERFACE & TELEMETRY LAYER (interface/)                                                 │
│ - mcp_server.py: FastMCP Server with stdio & SSE transports (30 Native Cognitive Tools)    │
│ - telemetry_api.py: FastAPI REST (/api/telemetry/snapshot, /api/janitor/reconcile) & SSE    │
│ - watcher.py: Early-Exit Reactive File Watcher (pathspec / .conciergeignore)                │
│ - queue_writer.py (SerializedWriteQueue): Single-Writer Daemon + Adaptive Auto-Batching     │
│ - cli.py: Management and operational CLI commands                                          │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 CORE & SURVIVAL LAYER (core/)                                                            │
│ - middleware.py (GrafoConcierge): Central Facade orchestrating all subsystems                │
│ - telemetry_schemas.py: Pydantic v2 schemas for DirtyFiles, SelfHealing, Checkpoints & State │
│ - delta_manager.py: Dual Hash (SSH Signature + LBH Semantic Drift) & DocstringStripper      │
│ - hybrid_search.py / search_engine.py: Tri-signal score + Query-Time Self-Healing Filter    │
│ - graph_rag.py: O(1) Natural communities, Supernode Degree Outlier Filter & CTE Loop Guard  │
│ - checkpointer.py: Agent-agnostic state blobs & chronological Time-Travel timeline          │
│ - background_janitor.py: Hardware-aware Thermal Governor, Smart LRU Pruning & Local SLM    │
│ - vector_reconciler.py: Background Orphan Expurging via set differences                     │
│ - dependencies.py: Immutable frozen dataclass container with path traversal defense         │
│ - memory_extractor.py: Bi-temporal fact consolidation (ADD / UPDATE / DELETE / NOOP)        │
│ - probabilistic_retriever.py: Zero-NumPy Thompson Sampling via native random.betavariate()   │
│ - project_index.py: Project registry, node/edge CRUD & wing management                     │
│ - config.py: Centralized configuration loader (env vars, model tiers, paths)                │
└──────────────────┬──────────────────────────────────────────┬───────────────────────────────┘
                   │                                          │
                   ▼                                          ▼
┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────────────┐
│ 📥 INGESTION ENGINE (ingestion/)         │   │ 🧹 MAINTENANCE LAYER (services/janitor.py)       │
│ - ProjectCrawler: Delta Hash Check       │   │ - JanitorService: Autonomous Background Daemon   │
│ - FileParser: Tree-sitter AST & Tags     │   │ - Bidirectional Vector Reconciliation            │
│ - ZoomSummarizer: L0/L1/L2 Summaries     │   │ - Smart Checkpoint Pruner (Session-scoped LRU)   │
│ - IngestionOrchestrator: Batch Pipeline  │   │ - Exponential Recency Decay & VACUUM Maintenance │
└──────────────────┬───────────────────────┘   └──────────────────┬───────────────────────────────┘
                   │                                              │
                   ▼                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 💾 STORAGE LAYER (storage/)                                                                     │
│ ┌──────────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ SQLite WAL Engine                                │ │ Vector Store                           │ │
│ │ - connection.py: SerializedWriteQueue + ConnMgr  │ │ - base_backend.py: Abstract Interface  │ │
│ │ - schema.py: DDL Schema Manager (13 tables)      │ │ - vector_store.py: Chroma & Qdrant     │ │
│ │ - logic.py: Relational Query Logic               │ │ - core/vector_backend.py: Embedding Mgr│ │
│ │ - semantic_logic.py: Semantic Facts Queries       │ │                                        │ │
│ │ - store.py: SqliteStore High-Level API           │ │                                        │ │
│ └──────────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
│ └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
```

---

## 3. Storage Layer & Concurrency Engine

### 3.1 `SerializedWriteQueue` (Adaptive Auto-Batching & Single-Item Fallback)
SQLite in high-concurrency multi-client environments can suffer from `sqlite3.OperationalError: database is locked`.

Grafo Concierge resolves this through a **Single-Writer Serialized Queue** architecture with Phase 4 resilience optimizations:
* **Single Item Immediate Execution**: If only one write is requested, it executes immediately in its own transaction without any artificial sleep, timer delay, or jitter.
* **Opportunistic Backlog Draining**: If a backlog accumulates in the queue during agent bursts, the daemon non-blockingly drains up to 50 pending write tasks via `queue.get_nowait()` and executes them in a single atomic batch transaction (`BEGIN IMMEDIATE ... COMMIT`).
* **Single-Item Fallback on Error**: If a batch fails due to an integrity constraint violation (e.g. unique constraint or invalid SQL), the queue performs a `ROLLBACK` and immediately processes each task individually. All valid writes succeed, while the failing write returns an explicit error to its caller.
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
-- SURVIVAL & DELTA ENGINE TABLES (Fases 1, 2, 3 e 4)
-- =========================================================================

-- 1. Files & Dual-Hash Delta Sync (SSH + LBH)
CREATE TABLE IF NOT EXISTS files (
    path         TEXT PRIMARY KEY,
    content      TEXT,
    ssh_hash     TEXT,             -- SHA-256 of structural signature lines
    body_hash    TEXT,             -- SHA-256 of AST body without docstrings (LBH)
    is_dirty     INTEGER DEFAULT 1,-- 1 = Needs summarization / update, 0 = Clean
    community_id TEXT,
    last_modified REAL
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

-- 4. Agnostic State Checkpoints & Time-Travel Timeline (Smart LRU Prunable)
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

### 5.1 Dual-Hash Delta Manager: SSH & LBH Semantic Drift Guard
* `DeltaManager.calculate_ssh(content)` extracts lines starting with `def `, `class `, `import `, or `from `, computing a deterministic SHA-256 signature hash.
* `DeltaManager.calculate_lbh(content)` parses the code AST, traverses it with `DocstringStripper(ast.NodeTransformer)` to strip all docstrings from functions/classes/modules, dumps the clean AST via `ast.dump(tree, annotate_fields=False)`, and computes its SHA-256.
* **Transition Logic**:
  * If SSH changes **OR** LBH changes: File is marked `is_dirty = 1` and community is marked `is_dirty = 1`.
  * If only comments, whitespace, formatting, or docstrings changed: `files.is_dirty = 0`, community remains clean, and **100% of LLM token costs are saved**.

### 5.2 Query-Time Self-Healing & Vector Reconciler
* `HybridSearchEngine.hybrid_search()` queries the vector store, intercepts candidate IDs, and runs a single parameterized batch query: `SELECT path FROM files WHERE path IN (?, ?, ...);`.
* Orphan vectors (files deleted from disk/SQLite) are dropped in real-time ($O(1)$ response-time filtering).
* `VectorReconciler.reconcile_orphans()` performs an asynchronous $O(N)$ set difference (`set(vector_ids) - set(sqlite_paths)`) and deletes orphaned vector records in batches.

### 5.3 Frugal GraphRAG: Supernode Outlier Filter & CTE Loop Guards
* **Natural Communities**: `GraphRAGEngine.get_natural_community()` maps file paths to immediate parent directories (e.g. `core/utils/delta.py` $\rightarrow$ `core/utils`), executing in $O(1)$ string operations without loading graphs into RAM.
* **Degree Outlier Supernode Filter (`detect_logical_communities`)**:
  1. Computes node in-degrees over `ast_edges` (`GROUP BY child_node HAVING in_degree > threshold`).
  2. Files exceeding the threshold (e.g., global utility hubs like `utils.py`) are classified as Supernodes and excluded as transit bridges during connected component formation.
  3. Clean edges are clustered via Union-Find into independent business communities (`community_{root}`).
  4. Supernodes receive directory-fallback clusters (`hub_satellite_{dir}`), preventing the collapse of the entire graph into a single monolithic component.
* **Strict Loop Guard Query**: `get_call_chain_recursive()` executes a `WITH RECURSIVE` CTE accumulating pipe-delimited paths (`|node1|node2|`) and testing `instr(cc.path_visited, '|' || e.child_node || '|') = 0`:
  ```sql
  WITH RECURSIVE call_chain(node, depth, path_visited) AS (
      SELECT ? AS node, 0 AS depth, '|' || ? || '|' AS path_visited
      UNION ALL
      SELECT e.child_node AS node,
             cc.depth + 1 AS depth,
             cc.path_visited || e.child_node || '|' AS path_visited
      FROM ast_edges e
      JOIN call_chain cc ON e.parent_node = cc.node
      WHERE cc.depth < ?
        AND instr(cc.path_visited, '|' || e.child_node || '|') = 0
  ) SELECT DISTINCT node, depth FROM call_chain WHERE node != ?;
  ```
  This eliminates infinite cycles ($A \rightarrow B \rightarrow C \rightarrow A$) and prevents substring collisions (`oauth.js` vs `auth.js`).

### 5.4 Agnostic Checkpointer & Smart Checkpoint Pruning
* `AgnosticCheckpointer` persists and retrieves arbitrary JSON state payloads under `(agent_id, session_id, checkpoint_id)`.
* `BackgroundJanitor.prune_session_checkpoints(session_id, keep_limit=10)` executes Smart LRU pruning: protects checkpoint `"init"` (point-zero) while keeping the $N$ most recent entries and purging stale intermediate records via `SerializedWriteQueue`.
* `list_checkpoints()` returns a chronological timeline (`ORDER BY created_at ASC`) allowing AI agents to step backwards in time.

### 5.5 Hardware-Aware Thermal Throttling & Rate Governor
* `BackgroundJanitor.check_hardware_clearance(max_cpu_percent=40.0, quiet_period_seconds=180.0)` verifies host health before launching local SLMs (Ollama):
  1. Measures host CPU usage over a 0.5s window via `psutil.cpu_percent(interval=0.5)`. Rejects execution if $\text{CPU} > 40\%$.
  2. Queries `MAX(last_modified)` from `files`. Rejects execution if files were edited within the quiet period (active typing window).
* `process_community_summaries_frugal()` automatically lowers process priority (`IDLE_PRIORITY_CLASS` on Windows, `nice(15)` on Unix) to guarantee that background summaries never degrade developer experience (DX).

### 5.6 Real-Time SSE Telemetry & Health Stream
* `interface/telemetry_api.py` provides FastAPI endpoints for dashboard integrations:
  * `GET /api/telemetry/snapshot`: Complete JSON snapshot of dirty files, Janitor status, self-healing events, and agent checkpoints using Pydantic v2 schemas.
  * `GET /api/telemetry/stream`: High-efficiency Server-Sent Events (SSE) streaming state changes every 2 seconds with automatic reconnection support.
  * `POST /api/janitor/reconcile`: Manual on-demand trigger to execute background vector reconciliation and cache cleanup.

### 5.7 Zero-NumPy Native Bayesian Thompson Sampling
* `core/probabilistic_retriever.py` uses Python's standard `random.betavariate()` instead of external NumPy packages (~30MB savings):
  ```python
  safe_alpha = max(alpha, 1e-5)
  safe_beta = max(beta, 1e-5)
  multiplier = random.betavariate(safe_alpha, safe_beta)
  ```
* Input sanitization prevents runtime `ValueError` on boundary conditions ($\le 0$), maintaining mathematical equivalence with pure Python speed.
