# 🚀 Deployment, Configuration & Local-First Security (v4.0.0)

> **Complete Operations Guide for Local IDEs, Remote VPS Hosting, Docker Containers, and Tailscale Networking**

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

In addition to FastMCP, Grafo Concierge exposes a high-performance **FastAPI Telemetry Server** for real-time observability dashboards (e.g., Next.js, Electron, or Web UIs):

### 4.1 Available Endpoints

| Endpoint | Method | Response / Content-Type | Description |
| :--- | :---: | :--- | :--- |
| **`/api/telemetry/snapshot`** | `GET` | `application/json` | Full system snapshot: dirty files, Janitor status, self-healing events, and agent checkpoints. |
| **`/api/telemetry/stream`** | `GET` | `text/event-stream` (SSE) | Persistent real-time event stream emitting system state updates every 2 seconds. |
| **`/api/janitor/reconcile`** | `POST` | `application/json` | On-demand manual trigger to execute vector reconciliation and cache cleanups. |

### 4.2 Running the Telemetry API

```bash
# Start the FastAPI telemetry server via Uvicorn
uvicorn interface.telemetry_api:create_app --factory --host 127.0.0.1 --port 8001 --reload
```

### 4.3 Next.js Dashboard Integration (SSE Client Example)

```typescript
// Example Next.js SSE hook for live Grafo Concierge telemetry
const eventSource = new EventSource("http://127.0.0.1:8001/api/telemetry/stream");

eventSource.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log("Dirty files count:", telemetry.dirty_files.length);
  console.log("Janitor active:", telemetry.janitor_status.is_running);
};
```
