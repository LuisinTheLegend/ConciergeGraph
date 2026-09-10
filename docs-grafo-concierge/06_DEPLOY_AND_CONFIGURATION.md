# 🚀 Deployment, Configuration & Local-First Security (v4.2.0)

> **Complete Operations Guide for Local IDEs, Remote VPS Hosting, Docker Containers, Tailscale Networking, FastAPI Telemetry Endpoints, and the Next.js Cockpit**

---

## 1. Environment Variables Reference (`.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`CONCIERGE_BIND_ADDRESS`** | `str` | `127.0.0.1` | **Local-First Security Binding**. Set to `127.0.0.1` (default, safe for public Wi-Fi) or `0.0.0.0` (for Tailscale / LAN remote access). |
| **`GRAFO_DB_PATH`** | `str` | `data/concierge.db` | Path to the relational SQLite database file. |
| **`GRAFO_CHROMA_PATH`** | `str` | `data/chroma` | Directory for local ChromaDB vector persistence. |
| **`GRAFO_CHROMA_COLLECTION`**| `str` | `grafo_concierge` | Name of the primary vector collection. |
| **`GRAFO_VECTOR_BACKEND`** | `str` | `chroma` | Vector backend selector: `chroma` or `qdrant`. |
| **`GRAFO_QDRANT_URL`** | `str` | `http://localhost:6333` | Host URL for local Qdrant container or Qdrant Cloud cluster. |
| **`GRAFO_QDRANT_API_KEY`** | `str` | `None` | API Key for authenticated Qdrant Cloud deployments. |
| **`GRAFO_LLM_PROVIDER`** | `str` | `gemini` | LLM provider: `gemini`, `openai`, `ollama`, or `custom`. |
| **`GRAFO_LLM_API_KEY`** | `str` | `None` | API key for LLM summarization and semantic fact extraction. |
| **`GRAFO_LLM_MODEL`** | `str` | `gemini-2.0-flash` | LLM model identifier. |
| **`GRAFO_LLM_BASE_URL`** | `str` | `None` | Custom base URL for Ollama or self-hosted OpenAI-compatible APIs. |
| **`GRAFO_RPM_LIMIT`** | `int` | `60` | Requests Per Minute quota for sliding window rate governance (SDD-23). |
| **`GRAFO_TPM_LIMIT`** | `int` | `40000` | Tokens Per Minute quota for sliding window rate governance (SDD-23). |
| **`GRAFO_SLIDING_WINDOW_SEC`**| `int` | `60` | Duration in seconds of Rate Governor sliding usage window. |
| **`GRAFO_GATING_MODE`** | `str` | `plan-only` | Autonomy gating mode: `plan-only`, `ask`, or `auto-approve` (SDD-24). |
| **`GRAFO_LIGHTWEIGHT_MODE`** | `bool`| `false` | When `true`, disables vector models to run in <35MB RAM via FTS5. |
| **`GRAFO_HOST`** | `str` | `127.0.0.1` | Network interface for FastMCP SSE server (`0.0.0.0` for VPS). |
| **`GRAFO_PORT`** | `int` | `8000` | HTTP / SSE port for remote MCP server. |
| **`GRAFO_API_KEY`** | `str` | `None` | Secret Bearer token required for remote VPS authentication. |
| **`GRAFO_CORS_ORIGINS`** | `str` | `*` | Comma-separated list of allowed CORS origins. |

---

## 2. Docker Deployment & Local-First Security

### `docker-compose.yml` (Secure by Default):

```yaml
version: '3.8'

services:
  concierge:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: concierge-graph
    restart: unless-stopped
    ports:
      - "${CONCIERGE_BIND_ADDRESS:-127.0.0.1}:8000:8000"
    environment:
      - GRAFO_HOST=0.0.0.0
      - GRAFO_PORT=8000
      - GRAFO_LLM_API_KEY=${GRAFO_LLM_API_KEY:-}
      - GRAFO_LLM_MODEL=${GRAFO_LLM_MODEL:-gemini-2.0-flash}
      - GRAFO_VECTOR_BACKEND=${GRAFO_VECTOR_BACKEND:-chroma}
      - GRAFO_API_KEY=${GRAFO_API_KEY:-}
      - GRAFO_CORS_ORIGINS=${GRAFO_CORS_ORIGINS:-*}
      - GRAFO_RPM_LIMIT=${GRAFO_RPM_LIMIT:-60}
      - GRAFO_TPM_LIMIT=${GRAFO_TPM_LIMIT:-40000}
      - GRAFO_GATING_MODE=${GRAFO_GATING_MODE:-plan-only}
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/ || exit 0"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional Qdrant Vector DB Service
  # qdrant:
  #   image: qdrant/qdrant:latest
  #   container_name: concierge-qdrant
  #   restart: unless-stopped
  #   ports:
  #     - "${CONCIERGE_BIND_ADDRESS:-127.0.0.1}:6333:6333"
  #     - "${CONCIERGE_BIND_ADDRESS:-127.0.0.1}:6334:6334"
  #   volumes:
  #     - ./data/qdrant_storage:/qdrant/storage
```

---

## 3. Remote Access via Tailscale

To connect multiple machines (e.g. laptop querying desktop PC running Grafo Concierge):
1. In `.env`, change `CONCIERGE_BIND_ADDRESS=0.0.0.0`.
2. Access the server over your secure Tailscale IP (e.g. `http://100.x.y.z:8000/sse`).

---

## 4. Real-Time Telemetry & REST API (`interface/telemetry_api.py`)

In addition to FastMCP, Grafo Concierge exposes a high-performance **FastAPI Telemetry Server** for real-time observability dashboards (e.g., Next.js 16 Cockpit, Electron, or terminal observers):

### 4.1 Master Endpoints Matrix (15 Total Endpoints)

| Category | Method | Path | Description |
| :--- | :---: | :--- | :--- |
| **System Telemetry** | `GET` | `/api/telemetry/snapshot` | Consolidated snapshot of system state: dirty files, Janitor status, self-healing events, checkpoints. |
| **System Telemetry** | `GET` | `/api/telemetry/stream` | Persistent Server-Sent Events (SSE) stream emitting updates whenever volatile DB hash changes. |
| **Janitor** | `POST` | `/api/janitor/reconcile` | Triggers background reconciliation of orphan vectors against SQLite WAL via FastAPI BackgroundTasks. |
| **Rate Governor** | `GET` | `/api/governor/metrics` | Real-time moving window quota occupancy (RPM/TPM), queue backlog, and freezing flags. |
| **Rate Governor** | `POST` | `/api/governor/report` | Allows subagent executors to report actual tokens used post-LLM call to update sliding window metrics. |
| **Adaptive Gating** | `GET` | `/api/gating/config` | Returns active security configuration, autonomy mode (`plan-only`/`ask`/`auto-approve`), and project root. |
| **Adaptive Gating** | `POST` | `/api/gating/config` | Dynamically updates monorepo autonomy mode with runtime boundary validation. |
| **HSM Engine** | `GET` | `/api/hsm/state/{session_id}` | Queries the active hierarchical qualified state (`PLANNING.SCOPING`) and History Node for a session. |
| **HSM Engine** | `POST` | `/api/hsm/transition` | Executes a sub-state transition, fires lifecycle hooks (`on_exit`/`on_enter`), and persists checkpoint. |
| **HSM Engine** | `POST` | `/api/hsm/resume/{session_id}` | Restores session from Deep History Node ($H^*$) with runtime dual-hash code drift validation. |
| **HSM Engine** | `GET` | `/api/hsm/tree` | Returns the complete hierarchical state tree topology as a serializable dictionary. |
| **Cognitive Memory** | `GET` | `/api/checkpoints/{session_id}` | Lists chronological timeline of active checkpoints for an agent session. |
| **Cognitive Memory** | `POST` | `/api/checkpoints/time-travel` | Triggers cognitive-relational time-travel rollback: restores state, purges future steps, marks dirty files. |
| **Tool Governance** | `POST` | `/api/mcp/state` | Updates session mental state to trigger progressive tool disclosure re-scoping. |
| **Tool Governance** | `GET` | `/api/mcp/state/{session_id}` | Queries current registered mental state and active tool disclosure profile for a session. |

### 4.2 Running the Telemetry API

```bash
# Start the FastAPI telemetry server via Uvicorn
uvicorn interface.telemetry_api:app --host 127.0.0.1 --port 8001 --reload
```

---

## 5. Next.js 16 Passive Observability Cockpit (`grafo-dashboard-web/`)

Under **Active-SDD #28**, Grafo Concierge features a dedicated **Next.js 16 (App Router)** cockpit designed for real-time passive monitoring:

### 5.1 Architecture & 2x2 Grid Layout
* **Top-Left (`CodeGraphViewer.tsx`)**: Interactive 2D Force-Directed Graph of files and AST dependency edges. Files with `is_dirty = 1` are highlighted with a 60fps pulsating amber glow.
* **Top-Right (`QuotaGauges.tsx`)**: High-precision circular gauges for RPM (60 limit) and TPM (40,000 limit) featuring dynamic color gradients (Cyan $\rightarrow$ Amber $\rightarrow$ Crimson) and freezing indicators (`LOW_FROZEN`, `MEDIUM_FROZEN`).
* **Bottom-Left (`HSMStateTree.tsx`)**: Interactive collapsible tree of the Hierarchical State Machine showing active super-states, sub-states, Deep History Nodes ($H^*$), and a 1-click **"Resume Session"** trigger.
* **Bottom-Right (`HealingFeed.tsx`)**: Real-time chronological audit terminal streaming Janitor reconciliation events, WAL transactions, and circuit breaker trip notifications.

### 5.2 Unified Concurrent DX (`npm run dev:all`)
The Next.js dashboard project includes `concurrently` orchestration:

```json
{
  "scripts": {
    "dev": "next dev",
    "dev:backend": "cd ../GrafoConcierge && python -m uvicorn interface.telemetry_api:app --host 127.0.0.1 --port 8001 --reload",
    "dev:all": "concurrently -n \"WEB,API\" -c \"cyan,magenta\" \"npm run dev\" \"npm run dev:backend\""
  }
}
```

Simply run `npm run dev:all` to launch both the Next.js visual cockpit (`http://localhost:3000`) and the FastAPI telemetry server (`http://localhost:8001`) with synchronized terminal outputs.
