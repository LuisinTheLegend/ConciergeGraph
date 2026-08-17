# 🔌 MCP Tools Reference — Complete 26 Tools Catalog (v3.8.2)

> **Official Specification for Model Context Protocol (MCP) Clients (Cursor, Windsurf, Claude Desktop, Autonomous Agents)**

Grafo Concierge exposes **26 native tools** via the Model Context Protocol over `stdio` or `HTTP/SSE`.

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
├── 🌳 AST Code Intelligence & Call Graphs (3 tools)
│   ├── search_symbols
│   ├── get_implementations
│   └── get_callers
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
  * `wing` (`str`, optional): Primary Wing. If omitted, automatically detected via keywords.
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
Executes directory ingestion: scans filesystem, performs delta-hashing, Tree-sitter AST chunking, prompt armoring, summarization, embedding, and garbage collection.
* **Arguments**:
  * `project_path` (`str`, required): Path of the directory/file to ingest.
  * `project_uuid` (`str`, optional): Project UUID or directory name.
  * `auto_tag` (`bool`, optional): Auto-detect framework and language tags. Default: `True`.
* **Return**:
  ```json
  {
    "success": true,
    "files_processed": 42,
    "categories": {"code": 30, "doc": 8, "config": 4, "conversation": 0},
    "nodes_created": 42,
    "embeddings_stored": 42,
    "tags_applied": ["python", "fastapi", "jwt"],
    "files_skipped": 12,
    "files_deleted": 0
  }
  ```

### `concierge_wakeup`
Pre-loads project context compass, reference wing summaries, and latest commits into agent context at session startup.
* **Arguments**:
  * `project_uuid` (`str`, required): Project UUID or directory name.
* **Return**: `{"success": bool, "bussola": str, "reference_wings": dict, "recent_commits": list, "total_tokens": int}`

### `concierge_resume`
Returns the L2 Context Compass of the project (200-300 tokens).
* **Arguments**:
  * `project_uuid` (`str`, required): Project UUID or directory name.
  * `max_tokens` (`int`, optional): Token ceiling. Default: `300`.
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
  * `technical_changes` (`str`, required): Summary of technical modifications and added functions/dependencies.
  * `updated_pointers` (`list[str]`, required): List of changed file paths.
* **Return**: `{"success": bool, "commit_id": int}`

---

## 3. Search & Discovery Tools

### `concierge_search`
Executes Hybrid Search v4 combining dense vectors (50%), FTS5 BM25 (25%), and Max(Recency, Centrality) (25%).
* **Arguments**:
  * `query` (`str`, required): Natural language or technical query.
  * `project_uuid` (`str`, required): Project UUID or directory name.
  * `top_k` (`int`, optional): Maximum results. Default: `10`.
  * `include_references` (`bool`, optional): Include linked reference wings. Default: `False`.
  * `all_wings` (`bool`, optional): Search across all projects globally. Default: `False`.
  * `node_type` (`str`, optional): Surgical filter (`FACT`, `SKILL`, `INSIGHT`, `TRAJECTORY`, `PATCH`, `CLASS`, `FUNCTION`, `METHOD`, `MODULE`).
  * `enable_probabilistic` (`bool`, optional): Use Thompson Sampling for reinforcement scoring. Default: `False`.
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

---

## 5. Bi-Temporal Cognitive Facts & Feedback

### `concierge_store_fact`
Evaluates and consolidates a semantic fact under bi-temporal rules (`ADD`, `UPDATE`, `DELETE`, `NOOP`).
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Scope identifier (e.g., username, project name, agent ID).
  * `fact_statement` (`str`, required): Factual statement or architectural decision.
* **Return**:
  ```json
  {
    "success": true,
    "scope_type": "user",
    "scope_id": "guial",
    "decisions": [
      {
        "fact": "Project uses SQLite WAL mode with SerializedWriteQueue",
        "action": "ADD",
        "target_id": null,
        "fact_id": 21
      }
    ]
  }
  ```

### `concierge_list_facts`
Lists all currently active semantic facts for a scope (`t_invalid IS NULL`).
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Scope identifier.
* **Return**:
  ```json
  {
    "success": true,
    "facts_count": 2,
    "facts": [
      {
        "id": 1,
        "scope_type": "user",
        "scope_id": "guial",
        "fact_statement": "Prefers FastAPI over Flask",
        "t_valid": "2026-08-16 02:20:00",
        "t_invalid": null,
        "utility_alpha": 3.0,
        "utility_beta": 1.0
      }
    ]
  }
  ```
> [!IMPORTANT]
> Always reference facts using their stable database primary key `id` (e.g., `Fact #1`). Never use list position / sequential indexing, as invalidated facts create gaps in IDs.

### `concierge_feedback`
Registers utility feedback for a semantic fact to tune Thompson Sampling weights.
* **Arguments**:
  * `fact_id` (`int`, required): Primary key of the semantic fact.
  * `was_useful` (`bool`, required): `True` increments `utility_alpha` (+1.0); `False` increments `utility_beta` (+1.0).
* **Return**: `{"success": bool, "fact_id": int, "was_useful": bool, "message": str}`

---

## 6. Scoped Core Memory

### `concierge_set_memory`
Stores or updates a labeled core memory block for a specific scope.
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Unique scope identifier.
  * `block_label` (`str`, required): Identifier label (e.g., `persona`, `tech_stack`, `rules`).
  * `content` (`str`, required): Text content to store.
* **Return**: `{"success": bool, "block_id": int, "message": str}`

### `concierge_get_memory`
Retrieves core memory blocks for a scope.
* **Arguments**:
  * `scope_type` (`str`, required): Scope category (`user`, `session`, `agent`, `org`).
  * `scope_id` (`str`, required): Unique scope identifier.
  * `block_label` (`str`, optional): If provided, returns only the specified block. If omitted, returns all blocks for the scope.
* **Return**: `{"success": bool, "blocks_count": int, "blocks": list[dict]}`

---

## 7. Topology & Low-Level Storage Operations

### `get_full_topology`
Returns the complete lean node/edge graph topology for real-time 3D web visualizations.
* **Arguments**:
  * `project_identifier` (`str`, optional): Project UUID or directory name to filter.
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
