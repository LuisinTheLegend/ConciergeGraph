# Contributing to Concierge Graph (GrafoConcierge)

Welcome! Thank you for your interest in contributing to **Concierge Graph** (`GrafoConcierge`), an enterprise-grade cognitive memory, frugal graph intelligence, and governance engine designed for autonomous AI agents.

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

Concierge Graph is engineered around three foundational pillars of cognitive autonomy:

1. **Pillar 1: Ingestion & Structural Topology**
   - Lexical and AST parsing (polyglot Python, TypeScript, JavaScript, React/TSX).
   - SQLite WAL (Write-Ahead Logging) storage with atomic transactions and zero-overhead indexing.
   - Vector reconciliation with Qdrant and offline orphan vector cleanup.

2. **Pillar 2: Cognitive Memory & Graph Intelligence**
   - **GraphRAG Frugal**: Multi-hop dependency traversal using recursive SQLite Common Table Expressions (CTEs) without high-RAM graph memory structures.
   - **Episodic Trajectories & Bi-Temporal Memory**: Self-healing facts with utility scoring, Thompson Sampling exploration/exploitation, and recency half-life decay ($\lambda = \ln(2) / 7$).
   - **Alias Tracking**: Resilient file rename and movement tracking via Structural Structural Hashes (SSH).

3. **Pillar 3: Governance & Security**
   - **RateGovernor**: Multi-tier priority queue (`HIGH`, `MEDIUM`, `LOW`) with dynamic freezing (85% LOW, 95% MEDIUM) under heavy traffic and zero-latency fast-path bypass under green traffic.
   - **Adaptive Gating**: Three autonomy regimes (`plan-only`, `ask`, `auto-approve`) integrated with terminal CLI approval prompts.
   - **Vanguard Bounds Guard**: Strict prevention of Path Traversal outside the monorepo root.

For detailed architecture specifications, consult [`docs-grafo-concierge/`](docs-grafo-concierge/).

---

## Environment Setup

### Prerequisites

- **Python**: Version `3.10` or higher (tested on `3.11`, `3.12`, `3.13`, and `3.14`).
- **Git**: For version control.
- **SQLite**: 3.35+ (with support for recursive CTEs and `RETURNING` clauses).
- **Optional**: Local [Ollama](https://ollama.com/) instance and [Qdrant](https://qdrant.tech/) container for live embedding testing.

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

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy sample environment configuration
   cp .env.example .env
   ```
   Inspect `.env` and verify key directories (such as `DATA_DIR`, `LOG_LEVEL`, and optional API endpoints).

---

## Development Workflow & SDD Methodology

All major features, security enhancements, and algorithmic changes follow the **Software Design Document (SDD)** standard:

1. **Specification First**: Before writing code for significant changes, an SDD entry is drafted in [`ACTIVE_SDD.md`](ACTIVE_SDD.md) covering:
   - Mission & Goal.
   - Exact file boundaries.
   - Invariant safety rules (backward compatibility, no deadlocks in SQLite WAL).
   - Test criteria and verification plans.

2. **Atomic Execution**: Refactorings and feature implementations are executed one component at a time, backed by unit tests at every step.

3. **Branching Strategy**:
   - `main`: Production-ready branch. Always green, all tests passing.
   - Feature branches: `feat/<sdd-id>-<short-description>` (e.g., `feat/sdd-24-adaptive-gating`).
   - Fix branches: `fix/<issue-id>-<short-description>`.
   - Documentation: `docs/<short-description>`.

---

## Testing Guidelines

We enforce strict test coverage across all cognitive, storage, and governance modules. **Never submit a pull request with failing tests.**

### Running the Test Suite

Run the complete test suite with `pytest`:
```bash
python -m pytest tests/ -v
```

Run specific test modules:
```bash
# Configuration & environment variable tests
python -m pytest tests/test_config.py -v

# Cognitive routing & GraphRAG recursive CTEs
python -m pytest tests/test_local_graph_rag_recursion.py tests/test_graph_rag_frugal.py -v

# RateGovernor priority traffic & Adaptive Gating
python -m pytest tests/test_rate_governor_priority.py tests/test_adaptive_gating.py -v

# Polyglot parser & Watcher ignore rules
python -m pytest tests/test_multilang_parser.py tests/test_watcher_ignore.py -v
```

### Writing New Tests

- Store all tests inside the `tests/` directory following the `test_<module_name>.py` naming convention.
- Use `pytest` fixtures for isolated temporary SQLite databases and temporary directories (`tmp_path`).
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
- **SQLite WAL**: Ensure database connections are managed safely. Never leave open uncommitted write transactions that can block read queries across threads.
- **Async & FastMCP**: Do not perform blocking I/O (such as file writes or synchronous prompts) directly inside async coroutines. Delegate blocking work using `loop.run_in_executor()`.

### Security & Path Normalization
- All file access and commands invoked by agent tools must pass through `SecurityGuard` ([`core/security_guard.py`](core/security_guard.py)).
- Prevent Path Traversal by resolving paths using `os.path.realpath()` and verifying that paths reside strictly within `project_root`.

---

## Extending MCP Tools & Governance

When adding or modifying a FastMCP tool in [`interface/mcp_server.py`](interface/mcp_server.py):

1. **Tool Classification**:
   Determine the security category of your tool:
   - `READ_ONLY`: Queries, search, topology inspection, status checks.
   - `LOCAL_MUTATION`: Code edits, file writes, checkpoints, memory writes.
   - `DANGEROUS`: Terminal command execution, external process spawning, destructive operations.

2. **Progressive Disclosure**:
   Ensure new tools are properly registered with the state governor (`MCPToolGovernor`) so they are only disclosed during relevant agent execution states (`planning`, `execution`, `maintenance`).

3. **Gating Interception**:
   Ensure mutating or dangerous actions pass through `GatingInterceptor.intercept_tool_call()` to respect active autonomy regimes (`plan-only`, `ask`, `auto-approve`).

---

## Pull Request Checklist

Before opening a pull request, please verify:

- [ ] All tests pass locally (`python -m pytest tests/ -v`).
- [ ] No regression introduced in existing test suites.
- [ ] All log messages, exceptions, and comments are in English.
- [ ] Code follows PEP 8 conventions and includes complete type hints.
- [ ] Any new feature has corresponding unit tests in `tests/`.
- [ ] If MCP tools or architecture changed, update the relevant documentation in `docs-grafo-concierge/`.
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat(governance): ...`, `fix(storage): ...`, `docs: ...`).

Thank you for helping make Concierge Graph faster, more reliable, and safer!
