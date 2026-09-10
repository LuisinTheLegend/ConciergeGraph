# 📥 Ingestion Engine, Tree-sitter AST & Dual-Hash Delta Sync (v4.2.0)

> **Architectural Specification for Early-Exit Watchers, Multi-Language Tree-sitter AST Parsing, Structural Signature Hashing (SSH), Logical Body Hashing (LBH), Alias Tracking, Deep History Delta Validation, and Reactive Observability**

---

## 1. Overview of the Resilient Ingestion Pipeline

The Ingestion Engine is the foundational subsystem responsible for transforming a raw codebase on disk into a rich, searchable knowledge graph while strictly containing token costs and eliminating I/O bottlenecks.

```
 ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
 │ 1. WATCHER   │ ─► │ 2. DELTA    │ ─► │ 3. PARSE     │ ─► │ 4. CHUNK    │
 │ Early-Exit   │    │ SSH + LBH   │    │ Tree-sitter  │    │ Delta Cache │
 └──────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
                                                                   │
 ┌──────────────┐    ┌─────────────┐    ┌──────────────┐           │
 │ 7. GC / JIT  │ ◄─ │ 6. PERSIST  │ ◄─ │ 5. EMBED     │ ◄─────────┘
 │ Self-Healing │    │ SQLite WAL  │    │ Lazy Summary │
 └──────────────┘    └─────────────┘    └──────────────┘
```

---

## 2. Early-Exit Reactive Watcher (`interface/watcher.py`)

To ensure zero latency and zero wasted I/O on large developer repositories containing thousands of transient files (`node_modules`, `.git`, `.venv`, build artifacts), the `ConciergeFileSystemHandler` implements an **Early-Exit Ignore Filter**:

* Uses the `pathspec` library to parse `.conciergeignore` (or `.gitignore`).
* Checks directory and file event paths **prior to opening file descriptors or invoking disk reads**.
* Safely discards ignored modifications in $< 0.1\text{ms}$.

---

## 3. Dual-Hash Delta Sync: SSH & LBH Semantic Drift Guard (`core/delta_manager.py`)

A major source of unexpected AI costs in market GraphRAG tools is re-indexing entire files and re-generating LLM summaries when a developer merely modifies a comment, adds a blank line, or runs an automatic code formatter. Conversely, a naive signature-only hash misses deep internal logic changes (Semantic Drift).

Grafo Concierge resolves both problems with a **Dual-Hash Architecture**:

### 3.1 Structural Signature Hashing (SSH)
`DeltaManager.calculate_ssh(file_content)` extracts public structural signature lines:
```python
# Lines matched:
# def calculate_total(a, b):
# class PaymentGateway:
# import os
# from typing import List
```
Computes the SHA-256 hash of consolidated signature lines.

### 3.2 Logical Body Hashing (LBH) via `DocstringStripper`
To detect internal logic changes without being fooled by comments or docstring edits:
1. `tree = ast.parse(file_content)` generates the AST (Python AST natively abstracts whitespace, line breaks, and comments).
2. `DocstringStripper(ast.NodeTransformer)` inspects `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, and `Module` nodes. If the first statement in the body is an `ast.Expr` containing a string literal constant (`ast.Constant`), it is stripped from the AST:
   ```python
   class DocstringStripper(ast.NodeTransformer):
       def visit_FunctionDef(self, node):
           self.generic_visit(node)
           if node.body and isinstance(node.body[0], ast.Expr):
               val = node.body[0].value
               if isinstance(val, ast.Constant) and isinstance(val.value, str):
                   node.body.pop(0)
           return node
   ```
3. `ast.dump(cleaned_tree, annotate_fields=False)` produces a deterministic structural string representation.
4. `calculate_lbh` returns the SHA-256 hash of this dump.

### 3.3 State Transition Matrix

| Change Type | SSH Changed? | LBH Changed? | Action in SQLite (`files` / `communities`) | Token Cost |
| :--- | :---: | :---: | :--- | :--- |
| **Comments / Whitespace / Formatters** | No | No | Content updated silently. `is_dirty` kept `0`. | **0 tokens (100% saved)** |
| **Docstrings Only** | No | No | Content updated silently. `is_dirty` kept `0`. | **0 tokens (100% saved)** |
| **Internal Logic Drift** (`==` $\rightarrow$ `!=`, returns) | No | **Yes** | `is_dirty = 1` set on file & community. | Lazy JIT re-summarization |
| **Signature Mutation** (new func/class/import) | **Yes** | **Yes** | `is_dirty = 1` set on file & community. | Lazy JIT re-summarization |

---

## 4. Multi-Language AST Parsing via Tree-sitter & `ParserFactory`

Under **Active-SDD #19**, Grafo Concierge introduces the **Polyglot Parser Factory** (`core/parser_factory.py`), enabling deep AST comprehension across both backend (Python) and frontend (TypeScript/JavaScript/React) modules.

### 4.1 Parser Factory Dispatch (`core/parser_factory.py`)
`ParserFactory.get_parser_for_file(file_path)` resolves the optimal parser implementation based on file extension:

```python
class ParserFactory:
    @staticmethod
    def get_parser_for_file(file_path: str) -> BaseParser:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            return PythonParser()
        elif ext in [".ts", ".tsx", ".js", ".jsx"]:
            return TsJsParser()
        else:
            return FallbackParser()
```

### 4.2 Hybrid TypeScript / JavaScript Parser (`core/parsers/ts_js_parser.py`)
To index React components, Next.js page routers, and UI components without requiring heavy external node runtime processes, `TsJsParser` operates in a resilient dual mode:
1. **Tree-sitter TS/TSX Grammar**: Native AST traversal when Tree-sitter bindings are present.
2. **Lexical Regex Fallback**: Ultra-fast regex scanner that matches functions, classes, and exported constants with $< 1\text{ms}$ latency.

#### Intelligence Filters:
* **React Hook Built-in Filter**: Automatically excludes React internal primitives (`useState`, `useEffect`, `useCallback`, `useMemo`, `useRef`, `useContext`) so they do not pollute the call graph as standalone project functions.
* **External npm Package Filter**: Distinguishes local relative imports (`./components/Header`, `../lib/api`) from third-party vendor packages (`react`, `next/navigation`, `lucide-react`, `tailwindcss`), indexing only project-internal dependencies.
* **Structural Semantic Hashing (SSH)**: Extracts public function signatures, classes, and local imports, hashing them deterministically for delta sync and alias tracking.

### 4.3 Symbol Node Types
* **`CLASS`**: Class declarations with signatures and docstrings.
* **`FUNCTION`**: Standalone top-level functions and exported arrow components.
* **`METHOD`**: Member functions associated with a class or object.
* **`MODULE`**: File-level imports, global constants, and package exports.

---

## 5. Structural Semantic Alias Tracking (`core/alias_tracker.py`)

Under **Active-SDD #18**, Grafo Concierge solves the **File Rename & Move Anomaly**:

### 5.1 The Problem
When a developer renames a file (e.g. `core/auth.py` $\rightarrow$ `core/authentication.py`):
1. Standard OS file watchers emit a `DELETE` event for `auth.py` followed by a `CREATE` event for `authentication.py`.
2. Naive indexing systems evict `auth.py`, deleting all its historical trajectory logs, commit audits, and relational edges.
3. Then they index `authentication.py` as an entirely new entity, breaking dependency graphs and causing node duplication.

### 5.2 The 1-Second Atomic Buffer
`AliasTracker` maintains a thread-safe `pending_deletions` buffer:

```
[File Deleted: auth.py]
         │
         ▼
Calculate SSH Hash & Store in Buffer with timestamp
         │
         ├─── Within 1.0s: [File Created: authentication.py]
         │          │
         │          ▼
         │    Calculate SSH of new file
         │    Match Found! (auth.py SSH == authentication.py SSH)
         │          │
         │          ▼
         │    Execute `apply_alias_migration(auth.py -> authentication.py)`
         │    (Atomic cascade across `files`, `ast_edges`, `nodes`)
         │
         └─── Timeout Exceeded (> 1.0s, no matching creation):
                    │
                    ▼
              Genuine Deletion Confirmed!
              `threading.Timer` invokes `on_purge_callback`
              (Permanently cleans up SQLite WAL and vector embeddings)
```

### 5.3 Cascading Relational Migration
`apply_alias_migration(old_path, new_path)` executes within a single atomic SQLite transaction:
```sql
UPDATE files SET path = ? WHERE path = ?;
UPDATE ast_edges SET parent_node = ? WHERE parent_node = ?;
UPDATE ast_edges SET child_node = ? WHERE child_node = ?;
UPDATE nodes SET label = ? WHERE label = ?;
```
Zero graph re-indexes. 100% preservation of historical agent trajectories.

### 5.4 Empty Payload Collision Guard
Newly created files during IDE saves are often momentarily 0 bytes. `AliasTracker` explicitly detects empty payloads and skips hash matching with an `EmptyPayloadError` sentinel, preventing unrelated blank files from falsely matching as aliases.

---

## 6. Runtime Delta Validation during Deep History Resume (`core/hsm_engine.py`)

Under **Active-SDD #27**, the Dual-Hash mechanism is directly wired into session recovery through the **Deep History Node ($H^*$)**:

### 6.1 The Stale File Inconsistency Problem
When an agent session is interrupted and later resumed via `HierarchicalStateMachine.resume_from_history_node(session_id, delta_manager)`:
1. If the operator or another external tool modified the underlying source file on disk while the agent was halted, the checkpoint memory would reflect an obsolete state of code.
2. Proceeding blindly in `CODE_GEN` or `TESTING` on stale code causes hallucinations, broken diff patches, and build failures.

### 6.2 The Runtime Delta Audit Workflow

```
[Operator Invokes resume_from_history_node]
                     │
                     ▼
        Resolve Checkpoint from WAL / Cache
                     │
                     ▼
       File mtime > checkpoint.created_at?
           ├─── NO ──► Restore Target Sub-state directly
           │
           └─── YES ──► delta_manager.has_structural_change(file)?
                          ├─── NO (formatting/comments) ──► Restore normally
                          │
                          └─── YES (Structural Code Drift detected!)
                                 │
                                 ├── Set restored.shared_state["stale_detected"] = True
                                 ├── Set restored.shared_state["original_state"] = target
                                 └── Auto-Redirect State ──► EXECUTION.RE_INDEX
```

When redirected to `EXECUTION.RE_INDEX`, the ingestion engine triggers an immediate re-parse of the modified AST, re-syncs SQLite WAL edges, and clears the stale flag before resuming development.

---

## 7. Reactive Observability Integration: Cockpit 60fps Pulsing (`is_dirty = 1`)

Under **Active-SDD #28**, ingestion state changes are broadcast in real time to the Next.js Cockpit (`grafo-dashboard-web/`):

1. Whenever `DeltaManager` or the File Watcher detects structural changes, the file is marked with `is_dirty = 1` in SQLite.
2. The SSE telemetry channel (`/api/telemetry/stream`) emits a `DELTA_DETECTED` event containing the affected node identifier and timestamp.
3. In `CodeGraphViewer.tsx`, the 2D Force-Directed Graph dynamically renders any node with `is_dirty = 1` with a **glowing amber/yellow pulsating aura at 60fps**.
4. Once JIT re-indexing completes and the community summary is refreshed, `is_dirty` resets to `0` and the node returns to its steady-state color.
