# 🏛️ Grafo Concierge — System Architecture (v4.2.0)

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
13. **Structural Semantic Alias Tracking (`core/alias_tracker.py`)**: Resolves file renames and moves atomically in $< 1\text{s}$ using Structural Semantic Hashing (SSH). Cascades path updates across `ast_edges`, `files`, and `nodes` without rebuilding the graph, while an automated purge timer safely invokes delete callbacks on real deletions to prevent zombie records.
14. **Polyglot AST Parser Factory (`core/parser_factory.py`, `core/parsers/`)**: Extends codebase intelligence beyond Python to TypeScript and JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) via Tree-sitter and an ultra-fast lexical fallback parser, extracting classes, functions, and internal imports while filtering external npm dependencies and React built-ins.
15. **Durable FSM Checkpoints & Cognitive Time-Travel (`storage/relational_db.py`, `core/checkpointer.py`)**: Persists resilient execution snapshots in `fsm_checkpoints` under `(session_id, checkpoint_id)`. Performs recursive JSON sanitization on non-serializable objects and executes clean time-travel rollbacks that purge future checkpoints and re-flag rolled-back files as dirty.
16. **Progressive Tool Disclosure & FastMCP Security Firewall (`core/mcp_governor.py`)**: Enforces two-layer tool visibility based on agent FSM states (`PLANNING`, `DISCOVERY`, `EXECUTION`, `TDD_GREEN`, `REFACTORING`, `MAINTENANCE`). Passively filters tool discovery to reduce prompt bloat and actively blocks unauthorized executions at runtime, raising `SecurityException`.
17. **Federated Knowledge Routing & Global Hybrid Memory Adapter (`core/intent_classifier.py`, `core/federated_knowledge_router.py`, `core/global_memory_adapter.py`)**: JIT Intent Classifier in 3 layers (Regex < 1ms, SQLite relational entities, Ollama SLM fallback) routes queries between private `LOCAL_GRAPHRAG` (`is_private: True`) and public `EXTERNAL_FEDERATED_MCP` (`is_private: False`). The `GlobalMemoryAdapter` compiles a hybrid sliding window: preserving the last 3 immediate chat messages (STM) combined with a structured Long-Term Memory (LTM) substrate extracted from the graph.
18. **Hierarchical State Machine Engine (`core/hsm_engine.py`)**: Replaces flat FSM with a recursive, tree-structured HSM model. Organizes agent cognitive flow into canonical Super-States (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `STALL`, `SUCCESS`) containing domain-specialized sub-states (`DISCOVERY`, `ARCHITECTURE`, `KANBAN_GEN`, `CODE_GEN`, `TDD_GREEN`, `REFACTORING`, `RE_INDEX`, `PURGE_CACHE`, `RECONCILE`, `RESET_DB`, `AWAITING_HUMAN`, `CONTEXT_FULL`, `ERROR_PAUSE`, `IDLE_COMPLETE`). Resolves state membership via qualified paths (`PLANNING.DISCOVERY`) and assigns sensitivity categories (`READ_ONLY`, `LOCAL_MUTATION`, `DANGEROUS`).
19. **Strict Lifecycle Hooks & History Node ($H^*$) Delta Verification (`core/hsm_engine.py`)**: Dispatches `on_enter` and `on_exit` hooks in strict hierarchical order (sub-state exit $\to$ super-state exit; super-state enter $\to$ sub-state enter) with resilient try/except blocks. Records Deep History Nodes ($H^*$) storing `(state_path, checkpoint_id, timestamp)`. On `resume_from_history_node()`, verifies whether files modified since the snapshot have diverged via Dual-Hash (SSH + LBH); if drift is detected, safely redirects execution to `EXECUTION.RE_INDEX` for immediate self-healing.
20. **Cognitive Loop Runner Coupling & Circuit Breaker (`agent/run_agent.py`)**: Couples `HermesAgentRunner` with the HSM engine. Automatically initializes sessions from the latest History Node or defaults to `PLANNING.DISCOVERY`. Enforces a 5-turn **Circuit Breaker** per sub-state to prevent infinite reasoning or retry loops, tripping safely into `STALL.AWAITING_HUMAN`.
21. **Rate Governor Quotas & Multi-Tier Priority Queuing (`core/rate_governor.py`)**: Enforces high-precision 60-second sliding window quotas (60 RPM / 40,000 TPM) with a 3-tier priority request queue (`HIGH` for interactive turns, `MEDIUM` for subagents, `LOW` for background tasks). Automatically triggers 3-tier reactive freezing: `NORMAL` (<85%), `LOW_FROZEN` (≥85%, suspends low queue), `MEDIUM_FROZEN` (≥95%, suspends subagents, reserving throughput exclusively for Hermes).
22. **Real-Time Passive Observability Cockpit (`grafo-dashboard-web/`)**: Next.js 16 (App Router) + React 19 + Tailwind CSS v4 dashboard operating under a strict **100% Zero-Mutation UI** paradigm. Receives sub-second telemetry via FastAPI SSE (`/api/telemetry/stream`). Displays a 2x2 grid cockpit: (1) 2D Force-Directed Code Graph with a 60fps sinusoidal pulsating yellow aura for files marked `is_dirty = 1`, (2) SVG Semi-Circular Radial Gauges for RPM and TPM with dynamic freezing status badges, (3) HSM State Inspector with expandable tree, active state highlight, Deep History Node card, and 5-turn Circuit Breaker dots, and (4) Real-time Cyber Console Live Event Feed with auto-scroll, UTC to local time formatting (`HH:mm:ss.SSS`), and category badges (`[WAL]`, `[JANITOR]`, `[DELTA]`, `[HSM]`, `[GATING]`).

---

## 2. Layered Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │            MCP Clients (Claude Desktop / Cursor)        │
                    │            Next.js 16 Observability Cockpit (Grid 2x2)  │
                    │            Hermes Agent & Autonomous Swarms             │
                    └────────────────────────────┬────────────────────────────┘
                                                 │  JSON-RPC / FastMCP & FastAPI REST/SSE
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🌐 INTERFACE & GOVERNANCE LAYER (interface/, core/mcp_governor.py, core/rate_governor.py)   │
│ - mcp_server.py: FastMCP Server with stdio & SSE transports (30 Native Cognitive Tools)    │
│ - mcp_governor.py (MCPToolGovernor): Progressive Tool Disclosure Matrix & Active Security   │
│ - rate_governor.py (RateGovernor): 60s Sliding Quotas (60 RPM/40k TPM) & Priority Freezing  │
│ - gating_interceptor.py & security_guard.py: Adaptive Gating Interceptor (ask/auto/auton) │
│ - telemetry_api.py: 15 REST routes (/api/telemetry/*, /api/governor/*, /api/hsm/*) & SSE    │
│ - watcher.py: Early-Exit Reactive File Watcher (pathspec / .conciergeignore)                │
│ - queue_writer.py (SerializedWriteQueue): Single-Writer Daemon + Adaptive Auto-Batching     │
│ - cli.py: Management and operational CLI commands                                          │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 CORE & COGNITIVE SURVIVAL LAYER (core/ & agent/)                                         │
│ - hsm_engine.py (HierarchicalStateMachine): Recursive HSM, Super/Sub-States, Hooks & H* Node│
│ - run_agent.py (HermesAgentRunner): Cognitive Execution Loop + 5-turn Circuit Breaker       │
│ - middleware.py (GrafoConcierge): Central Facade orchestrating all subsystems                │
│ - intent_classifier.py: JIT 3-tier triage (Regex < 1ms + SQLite entities + Ollama SLM)     │
│ - federated_knowledge_router.py: Federated Router (LOCAL_GRAPHRAG vs EXTERNAL_FEDERATED_MCP)│
│ - global_memory_adapter.py: Hybrid Context Adapter (LTM substrate + Last 3 STM chat msgs)  │
│ - alias_tracker.py: Atomic File Rename & Move Detection via Structural Semantic Hash (SSH) │
│ - parser_factory.py: Polyglot parser dispatcher (.py, .ts, .tsx, .js, .jsx)                 │
│ - delta_manager.py: Dual Hash (SSH Signature + LBH Semantic Drift) & DocstringStripper      │
│ - hybrid_search.py / search_engine.py: Tri-signal score + Query-Time Self-Healing Filter    │
│ - graph_rag.py: O(1) Natural communities, Supernode Degree Outlier Filter & CTE Cycle Guard│
│ - checkpointer.py: Durable FSM & Agent Checkpoints with chronological Time-Travel           │
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

-- 13. Durable FSM Checkpoints & Time-Travel (Active-SDD #20)
CREATE TABLE IF NOT EXISTS fsm_checkpoints (
    session_id    TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    state_blob    TEXT NOT NULL, -- Sanitized JSON snapshot
    created_at    REAL NOT NULL, -- Unix timestamp (time.time())
    dirty_files   TEXT DEFAULT '[]', -- JSON array of modified file paths
    PRIMARY KEY (session_id, checkpoint_id)
);
CREATE INDEX IF NOT EXISTS idx_fsm_checkpoints_session_created
    ON fsm_checkpoints(session_id, created_at ASC);
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

### 5.8 Structural Semantic Alias Tracking (`core/alias_tracker.py`)
* Solves the **File Rename & Move Anomaly**: When developers rename files (e.g. `auth_service.py` $\rightarrow$ `authentication.py`), standard watchers trigger a `DELETE` followed by a `CREATE`, which naive systems treat as an eviction followed by a re-index. This destroys historical agent trajectories, invalidates edge relations, and causes node duplication.
* **1-Second Atomic Window**: `AliasTracker.register_deletion()` captures deletions into a temporary buffer (`pending_deletions`). When a creation event arrives, `check_and_resolve_creation()` compares the file's Structural Semantic Hash (SSH). If the SSH matches within 1 second, it resolves as an atomic **Rename / Move**.
* **Cascading Migration**: `apply_alias_migration()` updates `files`, `ast_edges`, and `nodes` path references in a single atomic SQLite transaction with zero graph rebuilds.
* **Zombie Prevention**: An asynchronous `threading.Timer` calls `on_purge_callback` upon expiration, ensuring genuine file deletions are safely processed.
* **Empty Payload Guard**: Rejects 0-byte files with an explicit `EmptyPayloadError` sentinel to avoid false-positive hash collisions on newly touched empty files.

### 5.9 Polyglot AST Parser Factory (`core/parser_factory.py` & `core/parsers/`)
* **Dynamic Resolution**: `ParserFactory.get_parser_for_file(file_path)` inspects file extensions:
  * `.py` $\rightarrow$ `PythonParser` (Native Python AST)
  * `.ts`, `.tsx`, `.js`, `.jsx` $\rightarrow$ `TsJsParser` (Tree-sitter with high-performance regex fallback)
* **TypeScript & React Intelligence**:
  * Extracts class declarations, top-level functions, arrow functions, and exported components.
  * Filters out built-in React hooks (`useState`, `useEffect`, `useMemo`, etc.) to prevent topology pollution.
  * Distinguishes local relative imports (`./components/Header`) from external npm packages (`next/navigation`, `lucide-react`, `tailwindcss`), indexing only project-internal dependencies.
  * Computes deterministic Structural Semantic Hashes (SSH) across all supported languages.

### 5.10 Durable FSM Checkpoints & Cognitive Time-Travel (`core/checkpointer.py`)
* Extends agent state preservation beyond lightweight dictionaries into durable SQLite relational persistence (`storage/relational_db.py`).
* **Non-Serializable Sanitization**: Recursively inspects state dictionaries, converting locks, threads, coroutines, and custom objects into structured string representations to guarantee 100% JSON-safe serializability.
* **Time-Travel Rollback Execution**: `execute_time_travel(session_id, target_checkpoint_id)`:
  1. Loads the target state snapshot from `fsm_checkpoints`.
  2. Identifies and purges all chronologically subsequent checkpoints (`created_at > target.created_at`) from the timeline.
  3. Re-flags any rolled-back files recorded in `dirty_files` as `is_dirty = 1` in SQLite WAL, instructing the watcher and Janitor to re-synchronize local graph state.

### 5.11 Progressive Tool Disclosure & FastMCP Firewall (`core/mcp_governor.py`)
* Acts as a dynamic cognitive firewall between the LLM and the physical runtime environment:
  * **Layer 1 — Passive Discovery Filter (`filter_tools`)**: Dynamically intercepts FastMCP tool discovery. In exploratory states (`PLANNING`, `DISCOVERY`), tools that write to disk (`LOCAL_MUTATION`) or execute commands (`DANGEROUS`) are hidden from the agent's system prompt, reducing context token overhead and preventing premature code modification.
  * **Layer 2 — Active Execution Interceptor (`validate_tool_execution`)**: Wraps `call_tool()`. If an agent attempts to invoke a restricted tool directly without transitioning its FSM state, the call is blocked immediately with a `SecurityException`.
* **State Sensitivity Matrix**:
  * `PLANNING`, `DISCOVERY`: Only `READ_ONLY` tools + `get_telemetry_snapshot`.
  * `EXECUTION`, `TDD_GREEN`, `REFACTORING`: Unlocks `LOCAL_MUTATION` tools (`write_file`, `delete_file`, `save_checkpoint`, etc.).
  * `MAINTENANCE`: Unlocks all tools including `DANGEROUS` (`execute_command`, `reset_collection`, `purge_database`).

### 5.12 Federated Knowledge Routing & Global Hybrid Memory Adapter (`core/`)
* **IntentClassifier (`core/intent_classifier.py`)**: JIT 3-tier triage pipeline:
  1. *Regex Heuristics (< 1ms)*: Matches project terminology, directory structures, and file extensions.
  2. *Relational Entity Validation*: Queries `files` in SQLite WAL to detect mentions of indexed code files.
  3. *Semantic Fallback*: Calls local Ollama SLM (`qwen2.5-coder:1.5b`) for binary classification between `LOCAL_CODEBASE` and `EXTERNAL_GENERAL`.
* **FederatedKnowledgeRouter (`core/federated_knowledge_router.py`)**: Delegates `LOCAL_CODEBASE` to local GraphRAG (`is_private: True`) and `EXTERNAL_GENERAL` to federated public documentation MCP servers (`is_private: False`).
* **GlobalMemoryAdapter (`core/global_memory_adapter.py`)**: Compiles a hybrid context payload: preserves the last 3 immediate chat messages (Short-Term Memory) for conversational continuity, while replacing older chat history with a structured Long-Term Memory (LTM) substrate extracted from the knowledge graph.

### 5.13 Hierarchical State Machine (HSM) Engine (`core/hsm_engine.py`)
* Replaces naive, flat FSMs with a recursive, tree-structured HSM model (`HierarchicalStateMachine` and `HSMNode`).
* **Canonical Hierarchy**:
  * `PLANNING`: Read-only discovery and design phase.
    * Sub-states: `DISCOVERY`, `ARCHITECTURE`, `KANBAN_GEN`.
  * `EXECUTION`: Local mutation phase.
    * Sub-states: `CODE_GEN`, `TDD_GREEN`, `REFACTORING`, `RE_INDEX`.
  * `MAINTENANCE`: Dangerous administration phase.
    * Sub-states: `PURGE_CACHE`, `RECONCILE`, `RESET_DB`.
  * `STALL`: Autonomous mitigation and human escalation.
    * Sub-states: `AWAITING_HUMAN`, `CONTEXT_FULL`, `ERROR_PAUSE`.
  * `SUCCESS`: Terminal completion.
    * Sub-states: `IDLE_COMPLETE`.
* **State Paths**: States are addressed via dot-delimited paths (e.g. `PLANNING.DISCOVERY`, `EXECUTION.TDD_GREEN`).
* **Automatic Category Inheritance**: Sub-states inherit the sensitivity category of their parent super-state unless explicitly overridden.

### 5.14 State Transition Lifecycle Hooks & History Node ($H^*$) Delta Verification
* **Hierarchical Lifecycle Hooks**: `HSMNode` supports registration of `on_enter` and `on_exit` callback handlers:
  * Exit sequence executes from innermost sub-state outwards to super-state (`sub_state.execute_on_exit()` $\to$ `super_state.execute_on_exit()`).
  * Enter sequence executes from outermost super-state inwards to sub-state (`super_state.execute_on_enter()` $\to$ `sub_state.execute_on_enter()`).
  * Each execution is guarded by try/except handlers to ensure that a failing hook logs an error but does not corrupt the state transition.
* **Deep History Node ($H^*$)**:
  * Preserves the active sub-state and associated checkpoint snapshot `(state_path, checkpoint_id, timestamp)` upon exiting a super-state or saving progress.
  * When an agent transitions back to a super-state (e.g., re-entering `EXECUTION`), the engine restores the exact sub-state where work paused instead of reverting to the initial default.
* **Resume Delta Check (`resume_from_history_node`)**:
  * Before restoring execution context, the engine executes an active audit comparing current workspace files against recorded hashes in SQLite WAL using `DeltaManager` (Dual-Hash: SSH + LBH).
  * If out-of-band file edits (stale code) are detected, it dynamically intercepts the restoration and redirects the session to `EXECUTION.RE_INDEX`, triggering graph re-synchronization before code generation resumes.

### 5.15 Cognitive Runner Coupling & Circuit Breaker (`agent/run_agent.py`)
* Couples `HermesAgentRunner` with the HSM engine as the core brain of the cognitive execution loop:
  * `initialize_session(session_id)`: Inspects SQLite for an active `history_node`. If found and code integrity passes, restores state and resumes execution; otherwise, safely boots into `PLANNING.DISCOVERY`.
* **Cognitive Circuit Breaker (Anti-Loop Guard)**:
  * Tracks consecutive turns executed within the same sub-state (`turn_count`).
  * When `turn_count >= 5` (configurable via `max_turns`), the Circuit Breaker trips:
    1. Emits a warning event to the telemetry stream.
    2. Forcefully transitions the session to `STALL.AWAITING_HUMAN` or prompts the planner to re-evaluate the strategy, preventing catastrophic token burns on stubborn test failures or hallucination cycles.

### 5.16 Rate Governor Quotas & Multi-Tier Priority Queuing (`core/rate_governor.py`)
* **60-Second Sliding Window Quotas**: Continuously measures rolling consumption:
  * **RPM (Requests per Minute)**: Default quota = 60 req/min.
  * **TPM (Tokens per Minute)**: Default quota = 40,000 tok/min.
* **Priority Request Queue (`PriorityRequestQueue`)**:
  * Channels agent API calls through three strict priority lanes:
    * `HIGH`: Interactive user turns and Hermes main cognitive steps.
    * `MEDIUM`: Autonomous sub-agents and tool execution calls.
    * `LOW`: Asynchronous background jobs (Janitor summarization, GraphRAG embeddings).
* **3-Tier Reactive Freezing**:
  * 🟢 **`NORMAL` (< 85%)**: All queues flow at full throughput.
  * 🟡 **`LOW_FROZEN` (≥ 85%)**: Suspends `LOW` priority queue to protect interactive performance.
  * 🟠 **`MEDIUM_FROZEN` (≥ 95%)**: Suspends `MEDIUM` subagents, dedicating remaining quota strictly to `HIGH` priority Hermes turns until the sliding window drains.

### 5.17 Adaptive Gating & Security Guard (`core/gating_interceptor.py`, `core/security_guard.py`)
* Intercepts tool execution requests to enforce developer-configured autonomy modes:
  * `ask`: Strict human-in-the-loop gating for all mutating operations.
  * `auto_read`: Non-mutating tools (`READ_ONLY`) execute autonomously; mutating tools require explicit confirmation.
  * `autonomous`: Full autonomy within the allowed bounds of the current HSM state.
* `SecurityGuard` performs realpath sandboxing to defend against path traversal (`../`) and forbidden workspace boundary escapes.

### 5.18 Real-Time Passive Observability Cockpit (`grafo-dashboard-web/`)
* Built with Next.js 16 (App Router), React 19, and Tailwind CSS v4 under a **100% Zero-Mutation UI** paradigm:
* **Real-time SSE Stream**: Connects to `/api/telemetry/stream` (FastAPI), hydrating state instantly on load via `/api/telemetry/snapshot`, `/api/governor/metrics`, and `/api/hsm/tree` without network polling.
* **2x2 Grid Cockpit Layout**:
  1. **Top-Left — CodeGraphViewer (`components/topology/CodeGraphViewer.tsx`)**: 2D Force-Directed Graph with directory community grouping and a 60fps sinusoidal pulsating yellow aura for files with `is_dirty = 1`.
  2. **Top-Right — QuotaGauges (`components/governor/QuotaGauges.tsx`)**: Semicircular SVG radial gauges for RPM/TPM with smooth `stroke-dashoffset` transitions and reactive freezing badges.
  3. **Bottom-Left — HSMStateInspector (`components/hsm/HSMStateInspector.tsx`)**: Visual hierarchy tree, active state highlight, Deep History Node card, and 5-turn Circuit Breaker dots.
  4. **Bottom-Right — LiveEventFeed (`components/telemetry/LiveEventFeed.tsx`)**: Cyber console with auto-scroll toggle, ISO 8601 UTC to local browser time formatting (`HH:mm:ss.SSS`), and category badges (`[WAL]`, `[JANITOR]`, `[DELTA]`, `[HSM]`, `[GATING]`).


