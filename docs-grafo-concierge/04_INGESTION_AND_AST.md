# 📥 Ingestion Engine, Tree-sitter AST & Survival Delta Sync (v3.8.3)

> **Architectural Specification for Early-Exit Watchers, Code Parsing, Structural Signature Hashing (SSH), Call Graph Generation, and Delta Chunk Caching**

---

## 1. Overview of the Resilient Ingestion Pipeline

The Ingestion Engine is the subsystem responsible for transforming a raw codebase on disk into a rich, searchable knowledge graph while strictly containing token costs and eliminating I/O bottlenecks.

```
 ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
 │ 1. WATCHER   │ ─► │ 2. DELTA    │ ─► │ 3. PARSE     │ ─► │ 4. CHUNK    │
 │ Early-Exit   │    │ SSH Check   │    │ Tree-sitter  │    │ Delta Cache │
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

## 3. Structural Signature Hashing (SSH) & Delta Sync (`core/delta_manager.py`)

A major source of unexpected AI costs in market GraphRAG tools is re-indexing entire files and re-generating LLM summaries when a developer simply modifies an internal `if` condition, changes a variable name, or adds a comment.

Grafo Concierge uses **Structural Signature Hashing (SSH)**:
1. `DeltaManager.calculate_ssh(file_content)` strips all function bodies and comments, extracting only public structural signature lines:
   ```python
   # Lines matched:
   # def calculate_total(a, b):
   # class PaymentGateway:
   # import os
   # from typing import List
   ```
2. Computes the SHA-256 hash of consolidated signature lines.
3. When a file modification event occurs:
   * **Internal Logic Change (SSH unchanged)**: Content is updated silently in `files.content`. The file's dirty flag is cleared (`is_dirty = 0`). If all files in the community are clean, `communities.is_dirty` is reconciled to `0`. **Zero LLM tokens are spent**.
   * **Structural Mutation (SSH changed)**: Marks `files.is_dirty = 1` and sets `communities.is_dirty = 1`. AI re-summarization is scheduled lazily (JIT).

---

## 4. Multi-Language AST Parsing via Tree-sitter

Grafo Concierge parses code according to its **Abstract Syntax Tree (AST)** using Tree-sitter grammars across Python, TypeScript, JavaScript, Go, Rust, Java, C/C++, and config formats.

### Symbol Node Types:
* **`CLASS`**: Class declarations with signatures and docstrings.
* **`FUNCTION`**: Standalone top-level functions.
* **`METHOD`**: Member functions associated with a class or struct.
* **`MODULE`**: File-level imports, global variables, and package metadata.

### Call Graph Generation (`ast_edges`):
During AST parsing, function calls and external symbol references are extracted. The `ast_edges` table records `(parent_node, child_node)` pairs, enabling recursive multi-hop dependency traversals (`concierge_get_call_chain`).
