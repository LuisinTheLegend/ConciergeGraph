# Contributing to Concierge Graph (GrafoConcierge)

Welcome! Thank you for your interest in contributing to **Concierge Graph** (`GrafoConcierge`), an open-source, local-first long-term memory (LTM), hybrid search, and MCP governance server for AI agents.

This document outlines the architectural standards, development workflow, testing policies, and submission process for contributors.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Architectural Philosophy](#architectural-philosophy)
3. [Environment Setup](#environment-setup)
4. [Development Workflow & SDD Methodology](#development-workflow--sdd-methodology)
5. [Testing Guidelines](#testing-guidelines)
6. [Code Style & Conventions](#code-style--conventions)
7. [Extending MCP Tools & Governance](#extending-mcp-tools--governance)
8. [Pull Request Checklist](#pull-request-checklist)

---

## Code of Conduct

We are committed to providing a welcoming, constructive, and respectful environment for all contributors. Please treat fellow maintainers and contributors with professionalism, empathy, and constructive feedback.

---

## Architectural Philosophy

Concierge Graph (V4 Core) is engineered around four foundational pillars:

1. **Pillar 1: Ingestion & Structural Topology**
   - Python AST parsing and file crawling (`ingestion/crawler.py`, `ingestion/parser.py`, `ingestion/orchestrator.py`).
   - SQLite WAL (Write-Ahead Logging) storage (`storage/store.py`, `storage/schema.py`, `storage/connection.py`) with atomic transactions and FTS5 indexing.
   - Pluggable vector storage (`storage/vector_store.py`, `core/vector_backend.py`) with ChromaDB default and optional Qdrant backend, plus background maintenance via `services/janitor.py`.

2. **Pillar 2: Cognitive Memory & Hybrid Retrieval**
   - **Hybrid Search v4 (`core/hybrid_search.py`)**: Tri-signal ranking combining dense vector similarity, SQLite FTS5 BM25 lexical matching, and topological/recency signals, with strict project/wing scoping and query-time orphan filtering.
   - **Recursive Call-Chain GraphRAG (`core/graph_rag.py`)**: Multi-hop `calls` traversal over SQLite `edges` using `WITH RECURSIVE` CTEs protected by strict pipe-delimited cycle guards (`|node|`).
   - **Durable Checkpoints (`core/checkpointer.py`)**: Persistent agent state snapshots stored in `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint`, and `agent_list_checkpoints`.

3. **Pillar 3: MCP Governance & Local-First Security**
   - **Progressive Tool Disclosure (`core/mcp_governor.py`)**: Two-layer MCP firewall (`filter_tools` and `validate_tool_execution`) classifying all 31 live tools into `READ_ONLY`, `LOCAL_MUTATION`, and `DANGEROUS`, with fail-closed defaults for unclassified tools.
   - **Local-First Binding & Optional SSE Auth**: Defaults to `stdio` transport or loopback `127.0.0.1` binding for SSE (`GRAFO_TRANSPORT=sse`), with optional Bearer token authentication (`GRAFO_API_KEY`).

4. **Pillar 4: Domain Neutrality & Free-Form Wings**
   - The engine is domain-agnostic memory infrastructure for AI and AI agents.
   - **Strict Domain Neutrality Rule**: No hardcoded domain taxonomies, fixed dictionaries, or predefined business keywords may exist in product code or default configuration (`core/config.py`).
   - Project classification into wings is free-form and comes strictly from the user or the agent via explicit actions (`register_project`, `update_project`).
   - Mining operations (`GrafoConcierge.mine`) must never overwrite or mutate the project's primary wing.
   - **AST Domain Neutrality Guard (G2)**: Enforced via `tests/test_domain_neutrality_guard.py:test_g2_no_retired_domain_strings_in_product_code`. Discovers all repository Python files dynamically via `git ls-files '*.py'` (including `main.py` and `scripts/`). Scans all AST string constants (`ast.Constant`) and docstrings to prevent any substring occurrence (case-insensitive, with/without accent) of the 7 retired compound taxonomy terms (`marketing/vendas`, `finanças/quant`, `financas/quant`, `gestão/saas`, `gestao/saas`, `automação/rh`, `automacao/rh`), and exact matches for isolated domain labels (`estatística`, `estatistica`). **Known Limits of G2:** Because G2 inspects isolated `ast.Constant` string nodes in the syntax tree, it does **not** detect occurrences inside code comments (`# ...`) or strings assembled via runtime concatenation/interpolation (e.g., `"marketing" + "/vendas"`).

For documentation overview and pointers to archived experimental specs, consult [`docs-grafo-concierge/`](docs-grafo-concierge/).

---

## Environment Setup

### Prerequisites

- **Python**: Version `3.10` or higher (tested on `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`).
- **Git**: For version control.
- **SQLite**: 3.35+ (with support for recursive CTEs and FTS5).
- **Optional**: [Qdrant](https://qdrant.tech/) container if developing against the optional Qdrant vector backend (`GRAFO_VECTOR_BACKEND=qdrant`).

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LuisinTheLegend/ConciergeGraph.git
   cd ConciergeGraph
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv

   # Linux / macOS:
   source .venv/bin/activate

   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies (editable mode + dev tools):**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```
   Alternatively, install from `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy sample environment configuration
   cp .env.example .env
   ```
   Inspect `.env` and configure `GRAFO_DB_PATH`, `GRAFO_CHROMA_PATH`, `GRAFO_LOG_LEVEL`, and optional LLM credentials.

---

## Development Workflow & SDD Methodology

All major features, security enhancements, and algorithmic changes follow a specification-first workflow:

1. **Specification First**: Before writing code for significant changes, define:
   - Mission & Goal.
   - Exact file boundaries.
   - Invariant safety rules (backward compatibility, no deadlocks in SQLite WAL, domain neutrality).
   - Test criteria and verification plans.

2. **Atomic Execution**: Refactorings and feature implementations are executed in small, verifiable commits backed by unit tests (red-to-green) at every step.

3. **Branching Strategy**:
   - `main`: Production-ready branch. Always green, all tests passing.
   - Feature branches: `feat/<short-description>`.
   - Fix branches: `fix/<issue-id>-<short-description>`.
   - Documentation: `docs/<short-description>`.

---

## Testing Guidelines

We enforce strict test coverage across all memory, storage, ingestion, and governance modules. **Never submit a pull request with failing tests.**

### Running the Test Suite

Run the complete test suite with `pytest`:
```bash
python -m pytest tests/ -v
```

Run specific test modules:
```bash
# Configuration & environment variable guards
python -m pytest tests/test_config.py tests/test_env_example_provider.py -v

# MCP Governance, tool classification contracts & server wiring
python -m pytest tests/test_mcp_governor.py tests/test_governor_wiring.py tests/test_interface_contracts.py -v

# Domain neutrality guard (G1-G4) & wheel packaging integrity
python -m pytest tests/test_domain_neutrality_guard.py tests/test_wheel_integrity.py -v

# Durable checkpointer & hybrid search contracts
python -m pytest tests/test_checkpointer_live_contract.py tests/test_checkpointer_arg_resolution.py tests/test_hybrid_search_escolha_a.py -v
```

### Writing New Tests

- Store all tests inside the `tests/` directory following the `test_<module_name>.py` naming convention.
- Use `pytest` fixtures for isolated temporary SQLite databases (`SchemaManager.apply_full_schema()`) and temporary directories (`tmp_path`). Never invent ad-hoc DDL in tests.
- Do not add procedural scratch scripts (e.g. `_test_*.py`) to the repository root.
- Ensure all mocked external calls (LLMs, embeddings, network APIs) are deterministic and thread-safe.

---

## Code Style & Conventions

### Language & Localization
- **All code must be written in English**: variable names, function names, docstrings, inline comments, log messages, and user-facing exception messages must be in English.
- Avoid mixing Portuguese or other languages in code or runtime output.

### Typing & Modern Python
- Use Python standard type hints (`typing` module or PEP 585/604 built-in generics like `list[str]`, `dict[str, Any]`, `X | None`).
- Use `@dataclass(frozen=True)` for immutable configuration definitions (e.g., in [`core/config.py`](core/config.py)).

### Thread Safety & Concurrency
- **SQLite WAL**: Ensure database connections are managed safely via `storage/connection.py` and `storage/store.py`. Never leave open uncommitted write transactions that can block read queries across threads.
- **Async & FastMCP**: Do not perform blocking I/O directly inside async coroutines. Delegate blocking work safely.

### Security & Path Normalization
- Prevent Path Traversal when handling user-supplied filesystem paths by resolving paths with `Path.resolve()` / `os.path.realpath()` and validating scope boundaries.

---

## Extending MCP Tools & Governance

When adding or modifying a FastMCP tool in [`interface/mcp_server.py`](interface/mcp_server.py):

1. **Tool Classification**:
   Register every new tool in `TOOL_CLASSIFICATION` inside [`core/mcp_governor.py`](core/mcp_governor.py) under one of the three security categories:
   - `READ_ONLY`: Queries, search, topology inspection, status checks, and state inspection.
   - `LOCAL_MUTATION`: Project registration, mining, memory/fact writes, and checkpoint saves.
   - `DANGEROUS`: Destructive operations (`delete_project`, `reset_collection`).

2. **Contract Parity**:
   `tests/test_interface_contracts.py` enforces strict equality (`registered == classified`) between the tools registered in `GrafoConciergeServer` and the keys in `TOOL_CLASSIFICATION`. Every added or removed MCP tool must keep both sets in exact sync.

3. **Progressive Disclosure**:
   Ensure the tool behaves correctly under `MCPToolGovernor.filter_tools()` and `MCPToolGovernor.validate_tool_execution()` across states (`PLANNING`, `EXECUTION`, `MAINTENANCE`).

---

## Pull Request Checklist

Before opening a pull request, please verify:

- [ ] All tests pass locally (`python -m pytest tests/ -q` and `--reverse`).
- [ ] `flake8` reports zero syntax/undefined-name errors (`E9,F63,F7,F82`).
- [ ] No regression introduced in existing test suites.
- [ ] All log messages, exceptions, and comments are in English.
- [ ] Code follows PEP 8 conventions and includes complete type hints.
- [ ] Any new feature has corresponding unit tests in `tests/`.
- [ ] If MCP tools or architecture changed, update `README.md`, `README.pt-BR.md`, and `docs-grafo-concierge/README.md`.
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat(governance): ...`, `fix(storage): ...`, `docs: ...`).

Thank you for helping make Concierge Graph faster, more reliable, and safer!
