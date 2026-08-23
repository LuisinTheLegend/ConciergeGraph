# 🔌 MCP Tools Reference — Complete 30 Tools Catalog (v4.0.0)

> **Official Specification for Model Context Protocol (MCP) Clients (Cursor, Windsurf, Claude Desktop, Autonomous Agents & External Multi-Agent Swarms)**

Grafo Concierge exposes **30 native tools** via the Model Context Protocol over `stdio` or `HTTP/SSE`.

---

## 📑 Tools Taxonomy

```
├── 📁 Project & Registry (7 tools)
│   ├── concierge_register
│   ├── concierge_list_projects
│   ├── concierge_status
│   ├── update_project
│   ├── delete_project
│   ├── add_reference_wing
│   └── remove_reference_wing
├── 📥 Ingestion, Context & Sessions (5 tools)
│   ├── concierge_mine
│   ├── concierge_wakeup
│   ├── concierge_resume
│   ├── concierge_load
│   └── concierge_commit
├── 🔍 Search, Discovery & Similarities (2 tools)
│   ├── concierge_search
│   └── find_similar
├── 🌳 AST Code Intelligence & Call Graphs (4 tools)
│   ├── search_symbols
│   ├── get_implementations
│   ├── get_callers
│   └── concierge_get_call_chain         [Strict CTE Cycle-Guarded]
├── 💾 Session Checkpointing & Time-Travel (3 tools)
│   ├── agent_save_checkpoint            [Smart LRU Prunable]
│   ├── agent_get_checkpoint             [Agnostic JSON Restorer]
│   └── agent_list_checkpoints           [Chronological Timeline]
├── 🧠 Bi-Temporal Cognitive Facts & Feedback (3 tools)
│   ├── concierge_store_fact
│   ├── concierge_list_facts
│   └── concierge_feedback
├── 🗄️ Scoped Core Memory (2 tools)
│   ├── concierge_set_memory
│   └── concierge_get_memory
└── ⚙️ Topology & Vector Storage Operations (4 tools)
    ├── get_full_topology
    ├── get_trajectories
    ├── count_embeddings
    └── reset_collection
```

---

## 1. Project & Registry Tools

### `concierge_register`
Registers a new project in the SQLite knowledge graph.
* **Arguments**:
  * `project_path` (`str`, required): Absolute or relative filesystem path of the project.
  * `wing` (`str`, optional): Primary Wing. Default: `geral`.
  * `privacy_level` (`str`, optional): Privacy level (`PUBLIC`, `INTERNAL`, `RESTRICTED`). Default: `PUBLIC`.
  * `summary` (`str`, optional): Descriptive project compass/summary.
* **Return**: `{"success": bool, "project_uuid": str, "folder_name": str, "primary_wing": str, "privacy_level": str}`

### `concierge_list_projects`
Lists all projects currently registered in the database.
* **Arguments**: None.
* **Return**: `{"success": bool, "projects_count": int, "projects": list[dict]}`

### `concierge_status`
Returns global or project-specific health metrics, vector count, and Janitor report.
* **Arguments**:
  * `project_uuid` (`str`, optional): Specific project UUID or name.
* **Return**: `{"success": bool, "status": dict, "vector_backend": str, "janitor_report": dict}`

### `update_project`
Updates cadastral fields of an existing project.
* **Arguments**:
  * `project_identifier` (`str`, required): Project UUID or directory name.
  * `folder_name` (`str`, optional): New directory name.
  * `primary_wing` (`str`, optional): New primary wing.
  * `privacy_level` (`str`, optional): New privacy level.
  * `summary` (`str`, optional): New descriptive summary.
* **Return**: `{"success": bool, "message": str}`

### `delete_project`
Physically removes a project and cascades deletions across nodes, edges, commits, trajectories, and vector embeddings.
* **Arguments**:
  * `project_identifier` (`str`, required): Project UUID or directory name.
* **Return**: `{"success": bool, "message": str}`

### `add_reference_wing`
Associates a recommended reference wing with a project for cross-domain search.
* **Arguments**:
  * `project_identifier` (`str`, required): Project UUID or directory name.
  * `wing_name` (`str`, required): Name of the reference wing (e.g., `finanças/quant`).
* **Return**: `{"success": bool, "message": str}`

### `remove_reference_wing`
Removes an associated reference wing from a project.
* **Arguments**:
  * `project_identifier` (`str`, required): Project UUID or directory name.
  * `wing_name` (`str`, required): Name of the reference wing to dissociate.
* **Return**: `{"success": bool, "message": str}`

---

## 2. Ingestion, Context & Sessions

### `concierge_mine`
Executes directory ingestion: scans filesystem with early-exit filtering, performs dual-hash delta checks (SSH + LBH), Tree-sitter AST chunking, prompt armoring, summarization, embedding, and garbage collection.
* **Arguments**:
  * `path` (`str`, required): Path of the directory/file to ingest.
  * `project_identifier` (`str`, required): Project UUID or directory name.
  * `auto_tag` (`bool`, optional): Auto-detect framework and language tags. Default: `True`.
* **Return**: `{"success": bool, "files_processed": int, "nodes_created": int, "embeddings_stored": int, ...}`

### `concierge_wakeup`
Pre-loads project context compass, reference wing summaries, and latest commits into agent context at session startup.
* **Arguments**:
  * `project_uuid` (`str`, required): Project UUID or directory name.
* **Return**: `{"success": bool, "bussola": str, "reference_wings": dict, "recent_commits": list, "total_tokens": int}`

### `concierge_resume`
Returns the L2 Context Compass of the project (200-300 tokens).
* **Arguments**:
  * `project_uuid` (`str`, required): Project UUID or directory name.
* **Return**: `{"success": bool, "resume": str}`

### `concierge_load`
Lazy-loads full content, raw code, and relational edges of a specific node on demand.
* **Arguments**:
  * `node_id` (`int`, required): Unique integer ID of the node in SQLite.
* **Return**: `{"success": bool, "node": {"id": int, "label": str, "content": str, "summary": str, "tags": list, "edges": list}}`

### `concierge_commit`
Registers memory changelog after task completion, updating `commit_log` and refreshing recency timestamps.
* **Arguments**:
  * `project_uuid` (`str`, required): Project UUID or directory name.
  * `phase` (`str`, required): Engineering phase (`planning`, `build`, `test`, `deploy`).
  * `technical_changes` (`str`, required): Summary of technical modifications.
  * `updated_pointers` (`list[str]`, required): List of changed file paths.
  * `node_ids` (`list[int]`, optional): IDs of affected nodes.
* **Return**: `{"success": bool, "commit_id": int}`

---

## 3. Search & Discovery Tools

### `concierge_search`
Executes Hybrid Search v4 combining dense vectors (50%), FTS5 BM25 (25%), and Max(Recency, Centrality) (25%) with Query-Time Self-Healing.
* **Arguments**:
  * `query` (`str`, required): Natural language or technical query.
  * `project_identifier` (`str`, optional): Project UUID or directory name for Strict Scoping.
  * `top_k` (`int`, optional): Maximum results. Default: `10`.
  * `node_type` (`str`, optional): Surgical filter (`FACT`, `SKILL`, `INSIGHT`, `TRAJECTORY`, `PATCH`, `CLASS`, `FUNCTION`, `METHOD`, `MODULE`).
  * `include_references` (`bool`, optional): Include linked reference wings. Default: `False`.
  * `all_wings` (`bool`, optional): Search across all projects globally. Default: `False`.
* **Return**: `{"success": bool, "results_count": int, "results": list[dict]}`

### `find_similar`
Discovers other registered projects sharing the same technical wing domain.
* **Arguments**:
  * `project_identifier` (`str`, required): Anchor project UUID or name.
  * `limit` (`int`, optional): Max results. Default: `5`.
  * `include_references` (`bool`, optional): Include reference wings. Default: `False`.
  * `all_wings` (`bool`, optional): Search across all wings. Default: `False`.
* **Return**: `{"success": bool, "similar_projects": list[dict]}`

---

## 4. AST Code Intelligence & Call Graphs

### `search_symbols`
Performs fast symbol name lookup in the FTS5 index (classes, functions, methods).
* **Arguments**:
  * `query` (`str`, required): Symbol name (e.g., `authenticate_user`, `ChromaVectorStore`).
  * `project_uuid` (`str`, optional): Project UUID to restrict scope.
* **Return**: `{"success": bool, "symbols": list[dict]}`

### `get_implementations`
Returns raw implementation code block of an AST symbol node.
* **Arguments**:
  * `symbol_id` (`int`, required): Numeric ID of the symbol node.
* **Return**: `{"success": bool, "symbol_id": int, "label": str, "content": str, "summary": str}`

### `get_callers`
Inspects graph edges to find all caller nodes referencing the specified symbol.
* **Arguments**:
  * `symbol_id` (`int`, required): Numeric ID of the target symbol node.
* **Return**: `{"success": bool, "symbol_id": int, "callers_count": int, "callers": list[dict]}`

### `concierge_get_call_chain`
Executes recursive call chain discovery via `WITH RECURSIVE` queries over `ast_edges` in SQLite WAL, equipped with strict pipe-delimited cycle guards (`|node|` pattern matching via `instr()`) preventing infinite loops and substring collisions.
* **Arguments**:
  * `start_node` (`str`, required): Root file path or symbol identifier (e.g. `core/main.py`).
  * `depth_limit` (`int`, optional): Maximum traversal recursion depth. Default: `5`.
* **Return**: `list[str]` (Flat list of connected child file paths, excluding the root start node).

---

## 5. Session Checkpointing & Time-Travel

### `agent_save_checkpoint`
Persists arbitrary agent state dictionaries as JSON blobs in SQLite WAL under a composite primary key `(agent_id, session_id, checkpoint_id)` via `AgnosticCheckpointer`. Checkpoints are automatically prunable by `BackgroundJanitor`'s Smart LRU algorithm while protecting the `"init"` checkpoint.
* **Arguments**:
  * `agent_id` (`str`, required): Identifier of the agent (e.g. `nexus_agent`, `hermes`).
  * `session_id` (`str`, required): Unique session run identifier.
  * `checkpoint_id` (`str`, required): Identifier of the step/checkpoint (e.g. `init`, `step_1`, `pre_refactor`).
  * `state_dict` (`dict`, required): Arbitrary Python dictionary containing agent variables, memory, and kanban state.
* **Return**: `str` (JSON string: `{"success": true, "message": "Checkpoint 'step_1' saved successfully for agent 'nexus_agent'"}`).

### `agent_get_checkpoint`
Retrieves and decodes the persisted state dictionary for a specific step.
* **Arguments**:
  * `agent_id` (`str`, required): Identifier of the agent.
  * `session_id` (`str`, required): Session run identifier.
  * `checkpoint_id` (`str`, required): Step identifier.
* **Return**: `dict` (Decoded state dictionary, or `{}` if non-existent).

### `agent_list_checkpoints`
Lists the complete chronological history of checkpoints recorded for an agent session, enabling Time-Travel navigation and rollback capabilities.
* **Arguments**:
  * `agent_id` (`str`, required): Identifier of the agent.
  * `session_id` (`str`, required): Session run identifier.
* **Return**: `list[dict]` (List of `{"checkpoint_id": str, "created_at": str}` ordered ascending by creation timestamp).

---

## 6. Bi-Temporal Cognitive Facts & Feedback

### `concierge_store_fact`
Evaluates and consolidates a semantic fact under bi-temporal rules (`ADD`, `UPDATE`, `DELETE`, `NOOP`).
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Scope identifier.
  * `fact_statement` (`str`, required): Factual statement or architectural decision.
* **Return**: `{"success": bool, "scope_type": str, "scope_id": str, "decisions": list[dict]}`

### `concierge_list_facts`
Lists all currently active semantic facts for a scope (`t_invalid IS NULL`).
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Scope identifier.
* **Return**: `{"success": bool, "facts_count": int, "facts": list[dict]}`

### `concierge_feedback`
Registers utility feedback for a semantic fact to tune Thompson Sampling weights.
* **Arguments**:
  * `fact_id` (`int`, required): Primary key of the semantic fact.
  * `was_useful` (`bool`, required): `True` increments `utility_alpha`; `False` increments `utility_beta`.
* **Return**: `{"success": bool, "fact_id": int, "was_useful": bool, "message": str}`

---

## 7. Scoped Core Memory

### `concierge_set_memory`
Stores or updates a labeled core memory block for a specific scope.
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Unique scope identifier.
  * `block_label` (`str`, required): Identifier label (e.g. `persona`, `tech_stack`).
  * `content` (`str`, required): Text content to store.
* **Return**: `{"success": bool, "block_id": int, "message": str}`

### `concierge_get_memory`
Retrieves core memory blocks for a scope.
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Unique scope identifier.
  * `block_label` (`str`, optional): If provided, returns only that block. If omitted, returns all.
* **Return**: `{"success": bool, "blocks_count": int, "blocks": list[dict]}`

---

## 8. Topology & Low-Level Storage Operations

### `get_full_topology`
Returns the complete lean node/edge graph topology for real-time 3D web visualizations.
* **Arguments**:
  * `project_identifier` (`str`, optional): Project UUID or directory name.
* **Return**: `{"success": bool, "nodes": list[dict], "edges": list[dict]}`

### `get_trajectories`
Retrieves historical execution paths, errors, and applied fixes.
* **Arguments**:
  * `project_identifier` (`str`, required): Project UUID or directory name.
* **Return**: `{"success": bool, "trajectories": list[dict]}`

### `count_embeddings`
Returns exact vector counts in the active vector collection.
* **Arguments**:
  * `project_identifier` (`str`, optional): Filter count by project UUID.
* **Return**: `{"success": bool, "count": int}`

### `reset_collection`
Emergency repair tool that destroys and recreates the physical vector collection.
* **Arguments**: None.
* **Return**: `{"success": bool, "message": str}`
