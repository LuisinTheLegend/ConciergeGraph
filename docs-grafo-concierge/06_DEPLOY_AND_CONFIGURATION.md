# 🚀 Deployment, Configuration & Client Integration (v3.8.2)

> **Complete Operations Guide for Local IDEs, Remote VPS Deployments, Docker Containers, and Qdrant Cloud**

---

## 1. Environment Variables Reference (`.env`)

All runtime options are configured via environment variables prefixed with `GRAFO_`:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`GRAFO_DB_PATH`** | `str` | `data/concierge.db` | Relative or absolute path to the relational SQLite database file. |
| **`GRAFO_CHROMA_PATH`** | `str` | `data/chroma` | Directory for local ChromaDB vector persistence. |
| **`GRAFO_CHROMA_COLLECTION`**| `str` | `grafo_concierge` | Name of the primary vector collection. |
| **`GRAFO_VECTOR_BACKEND`** | `str` | `chroma` | Vector backend selector: `chroma` or `qdrant`. |
| **`GRAFO_QDRANT_URL`** | `str` | `http://localhost:6333` | Host URL for local Qdrant container or Qdrant Cloud cluster. |
| **`GRAFO_QDRANT_API_KEY`** | `str` | `None` | API Key for authenticated Qdrant Cloud deployments. |
| **`GRAFO_LLM_PROVIDER`** | `str` | `gemini` | LLM provider: `gemini`, `openai`, `ollama`, or `custom`. |
| **`GRAFO_LLM_API_KEY`** | `str` | `None` | API key for the LLM summarization and semantic fact extraction. |
| **`GRAFO_LLM_MODEL`** | `str` | `gemini-2.0-flash` | LLM model identifier (recommended: fast/flash tier models). |
| **`GRAFO_LLM_BASE_URL`** | `str` | `None` | Custom base URL for Ollama or self-hosted OpenAI-compatible APIs. |
| **`GRAFO_LIGHTWEIGHT_MODE`** | `bool`| `false` | When `true`, disables vector models to run in <35MB RAM via FTS5. |
| **`GRAFO_HOST`** | `str` | `127.0.0.1` | Network interface for FastMCP SSE server (`0.0.0.0` for VPS). |
| **`GRAFO_PORT`** | `int` | `8000` | HTTP / SSE port for remote MCP server. |
| **`GRAFO_API_KEY`** | `str` | `None` | Secret Bearer token required for remote VPS authentication. |
| **`GRAFO_CORS_ORIGINS`** | `str` | `*` | Comma-separated list of allowed CORS origins. |

---

## 2. Deployment Strategies

### Option A: Local Stdio (Default Developer Setup)
Ideal for individual developers running Cursor or Claude Desktop locally.

```bash
# 1. Clone and install in editable mode
git clone https://github.com/LuisinTheLegend/GrafoConcierge.git
cd GrafoConcierge
pip install -e .

# 2. Configure .env
cp .env.example .env

# 3. Launch FastMCP server over stdio
concierge-mcp
```

---

### Option B: Remote VPS Hosting (FastMCP HTTP / SSE)
Run Grafo Concierge as a centralized, continuous daemon on a Linux VPS (Ubuntu/Debian) to serve multiple machines or automated agents.

```bash
# 1. Set environment on VPS
export GRAFO_HOST="0.0.0.0"
export GRAFO_PORT="8000"
export GRAFO_API_KEY="your_super_secret_vps_token"
export GRAFO_LLM_API_KEY="your_gemini_or_openai_key"

# 2. Start server in SSE mode
concierge-mcp --transport sse
```

---

### Option C: Containerized Deployment (Docker & Compose)
Run fully isolated instances with volume persistence for SQLite and ChromaDB.

`docker-compose.yml`:
```yaml
services:
  grafo-concierge:
    build: .
    container_name: grafo-concierge
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - GRAFO_HOST=0.0.0.0
      - GRAFO_PORT=8000
      - GRAFO_API_KEY=your_secure_token_here
      - GRAFO_LLM_API_KEY=your_gemini_api_key_here
      - GRAFO_LLM_MODEL=gemini-2.0-flash
      - GRAFO_VECTOR_BACKEND=chroma
    volumes:
      - ./data:/app/data
```

Launch with:
```bash
docker compose up -d
```

---

## 3. Client Configuration (1-Click Integration)

### 3.1 Claude Desktop (`claude_desktop_config.json`)

* **Local stdio connection (via `concierge-graph` package)**:
  ```json
  {
    "mcpServers": {
      "concierge-graph": {
        "command": "concierge-mcp",
        "env": {
          "GRAFO_LLM_API_KEY": "your_api_key_here"
        }
      }
    }
  }
  ```
  *(Or use `"command": "python", "args": ["-m", "interface.mcp_server"]` when executing from local source).*

* **Remote VPS SSE connection**:
  ```json
  {
    "mcpServers": {
      "concierge-graph": {
        "url": "http://your-vps-ip:8000/sse",
        "headers": {
          "Authorization": "Bearer your_super_secret_vps_token"
        }
      }
    }
  }
  ```

---

### 3.2 Cursor IDE (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "concierge-graph": {
      "command": "concierge-mcp",
      "env": {
        "GRAFO_DB_PATH": "C:/Nexus-Memory/GrafoConcierge/data/concierge.db"
      }
    }
  }
}
```

---

### 3.3 Windsurf IDE (`mcp_config.json`)

```json
{
  "mcpServers": {
    "concierge-graph": {
      "command": "concierge-mcp",
      "env": {
        "GRAFO_LLM_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

---

### 3.4 Programmatic Python / LangChain Integration

```python
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

# Connect to Grafo Concierge programmatically in Python agent loops
async with stdio_client(["python", "-m", "interface.mcp_server"]) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        results = await session.call_tool("concierge_search", {
            "query": "database connection pool",
            "project_uuid": "e4b3c2a1-..."
        })
        print(results)
```
