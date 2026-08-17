# 🛠️ Migration, Operations & CLI Reference (v3.8.2)

> **Complete Guide to CLI Commands, Vector Synchronization, Schema Upgrades, and Health Diagnostics**

---

## 1. Complete CLI Reference (`interface/cli.py`)

Grafo Concierge includes a complete terminal interface accessible via `python -m interface.cli <command>` (or `grafo-concierge <command>` if installed via package):

### 1.1 `register` — Register a Project
```bash
python -m interface.cli register --name "vortex-pro" --wing "gestão/saas" --privacy "INTERNAL" --summary "SaaS Analytics Dashboard"
```
* **Flags**:
  * `--name` (required): Folder name of the project.
  * `--wing` (optional): Primary Wing (`marketing/vendas`, `finanças/quant`, `gestão/saas`, `automação/rh`, `estatística`, `geral`).
  * `--privacy` (optional): `PUBLIC`, `INTERNAL`, or `RESTRICTED` (default: `PUBLIC`).
  * `--summary` (optional): Descriptive summary.

---

### 1.2 `mine` — Ingest a Codebase Directory
```bash
python -m interface.cli mine --path "/path/to/project" --name "vortex-pro"
```
* **Flags**:
  * `--path` (required): Filesystem path to scan and ingest.
  * `--name` (required): Project folder name or UUID.
  * `--no-tag` (optional): Disables automatic regex framework tag detection.

---

### 1.3 `search` — Hybrid Search v4 Query
```bash
python -m interface.cli search --query "JWT authentication" --project "e4b3c2a1-..." --top-k 5 --refs
```
* **Flags**:
  * `--query` (required): Natural language or technical query.
  * `--project` (required): Project UUID.
  * `--top-k` (optional): Number of results (default: 10).
  * `--node-type` (optional): Filter by node type (`CLASS`, `FUNCTION`, `FACT`, etc.).
  * `--refs` (optional): Include reference wings.
  * `--all-wings` (optional): Search across all projects globally.

---

### 1.4 `wakeup` — Re-activate Agent Session Context
```bash
python -m interface.cli wakeup --project "e4b3c2a1-..."
```
* Pre-loads the L2 Context Compass, reference wings summaries, and latest 3 commits.

---

### 1.5 `resume` — Print Project Context Compass
```bash
python -m interface.cli resume --project "e4b3c2a1-..."
```
* Prints the concise 200-300 token executive summary of the repository.

---

### 1.6 `commit` — Register Memory Changelog
```bash
python -m interface.cli commit --project "e4b3c2a1-..." --phase "build" --changes "Refactored JWT validator" --pointers "src/auth.py,src/middleware.py"
```
* **Flags**:
  * `--project` (required): Project UUID.
  * `--phase` (required): Engineering phase (`planning`, `build`, `test`, `deploy`).
  * `--changes` (required): Summary of technical modifications.
  * `--pointers` (required): Comma-separated list of modified file paths.

---

### 1.7 `load` — Inspect a Specific Node
```bash
python -m interface.cli load --node-id 42
```
* Dumps all relational attributes, code contents, and connected edges of node ID 42.

---

### 1.8 `projects` — List All Registered Projects
```bash
python -m interface.cli projects
```
* Outputs a formatted table of all registered projects with UUID, Name, Wing, and Privacy level.

---

### 1.9 `sync-vector` — Manual Batch Vector Re-sync
```bash
# Sync all projects in the database
python -m interface.cli sync-vector

# Sync a specific project
python -m interface.cli sync-vector --project "e4b3c2a1-..."
```
* Executes bidirectional vector reconciliation: prunes orphan embeddings and generates missing embeddings for all active SQLite nodes.

---

## 2. Switching Vector Backends (ChromaDB ➔ Qdrant Cloud)

When migrating from local ChromaDB to production Qdrant Cloud:

1. **Update `.env`**:
   ```env
   GRAFO_VECTOR_BACKEND=qdrant
   GRAFO_QDRANT_URL=https://your-cluster-id.qdrant.tech:6333
   GRAFO_QDRANT_API_KEY=your_qdrant_api_key
   ```
2. **Execute Full Auto-Sync**:
   ```bash
   python -m interface.cli sync-vector
   ```
3. The Janitor reconciles all SQLite nodes with the new Qdrant collection automatically, populating your cloud cluster without data loss.

---

## 3. System Diagnostics & Health Checks

### 3.1 Running the Pytest Test Suite
Grafo Concierge includes 22 rigorous unit and stress test suites covering concurrency, bi-temporal logic, Thompson sampling, and AST parsing:

```bash
python -m pytest tests/ -v
```

### 3.2 Running the Interactive Brain Check
```bash
python -m tests.check_brain
```
* Inspects database connectivity, active projects, vector store health, and executes a test hybrid search query.

---

## 4. Troubleshooting & Operational FAQ

### Q: What are the `.db-wal` and `.db-shm` files?
* **Answer**: SQLite in WAL (`Write-Ahead Logging`) mode writes transactions to temporary `.db-wal` files for performance and concurrency. Do **not** delete them manually while the server is running. They are automatically merged into `concierge.db` by SQLite checkpoints and the Janitor's `VACUUM` routine.

### Q: How do I recover from an emergency vector corruption?
* **Answer**: Call the MCP tool `reset_collection` or delete the `data/chroma/` directory, then run `python -m interface.cli sync-vector`. All vectors will be cleanly regenerated from the primary SQLite truth table.
