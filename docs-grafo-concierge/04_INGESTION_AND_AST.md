# 📥 Ingestion Engine, Tree-sitter AST & Dual-Hash Delta Sync (v4.0.0)

> **Architectural Specification for Early-Exit Watchers, Code Parsing, Structural Signature Hashing (SSH), Logical Body Hashing (LBH), Call Graph Generation, and Delta Chunk Caching**

---

## 1. Overview of the Resilient Ingestion Pipeline

The Ingestion Engine is the subsystem responsible for transforming a raw codebase on disk into a rich, searchable knowledge graph while strictly containing token costs and eliminating I/O bottlenecks.

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

## 4. Multi-Language AST Parsing via Tree-sitter

Grafo Concierge parses code according to its **Abstract Syntax Tree (AST)** using Tree-sitter grammars across Python, TypeScript, JavaScript, Go, Rust, Java, C/C++, and config formats.

### Symbol Node Types:
* **`CLASS`**: Class declarations with signatures and docstrings.
* **`FUNCTION`**: Standalone top-level functions.
* **`METHOD`**: Member functions associated with a class or struct.
* **`MODULE`**: File-level imports, global variables, and package metadata.

### Call Graph Generation (`ast_edges`):
During AST parsing, function calls and external symbol references are extracted. The `ast_edges` table records `(parent_node, child_node)` pairs, enabling recursive multi-hop dependency traversals (`concierge_get_call_chain`) with strict loop cycle prevention.
