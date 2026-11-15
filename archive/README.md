# Archive — Código Experimental da V4 (Suspenso por D0)

Este diretório (`archive/v4-experimental/`) guarda os módulos, testes e o painel web experimentais da V4 suspensos pela decisão **D0 = cenário A** (núcleo de memória reduzido na Rodada 4.5d).

## Estatuto deste código

- **Suspenso / quarentena:** preservado via `git mv` (histórico mantido), **não** apagado.
- **Não empacotado:** excluído do wheel (`pyproject.toml` / `tests/test_wheel_integrity.py`).
- **Não testado no CI:** excluído de `tests/` e das execuções do GitHub Actions.
- **Não importável em produção:** nenhum módulo vivo em `core/`, `storage/`, `ingestion/`, `interface/`, `services/` ou `main.py` importa arquivos daqui.
- **Publicação proibida neste HEAD:** nunca publicar pacotes no PyPI a partir deste HEAD (no PyPI existe apenas `3.8.2`).

---

## Dívidas técnicas conhecidas (telemetria / dashboard)

Antes de qualquer eventual reativação na V5+, estas 3 dívidas estruturais já existiam no código arquivado e precisam de correção dedicada:

1. **Coluna `timestamp` inexistente em `agent_checkpoints`:**
   - `archive/v4-experimental/interface/telemetry_api.py:182-183` executa `SELECT agent_id, session_id, checkpoint_id, timestamp FROM agent_checkpoints ORDER BY timestamp ASC;`.
   - Porém, `storage/schema.py:146-153` define a coluna como `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (linha `151`) e o índice `idx_agent_checkpoints_lookup` em `storage/schema.py:170` também usa `created_at`.

2. **Tabela `files` ausente no schema de produção:**
   - `archive/v4-experimental/interface/telemetry_api.py:154` (`SELECT COUNT(*) FROM files;`) e `archive/v4-experimental/interface/telemetry_api.py:160` (`SELECT path, community_id, last_modified FROM files WHERE is_dirty = 1;`) consultam a tabela `files`, que não existe em `storage/schema.py` (assim como `fsm_checkpoints` consultada em `archive/v4-experimental/interface/telemetry_api.py:306` só aparece em `archive/v4-experimental/storage/relational_db.py:14`).

3. **Colisão de porta `8000` e desconexão entre dashboard e backend MCP:**
   - O frontend configura fallback da API FastAPI para `http://127.0.0.1:8000` (`archive/v4-experimental/grafo-dashboard-web/.env.example:9-10`, `archive/v4-experimental/grafo-dashboard-web/lib/useTelemetryStream.ts:29`, `archive/v4-experimental/grafo-dashboard-web/app/components/SelfHealingConsole.tsx:23`, `archive/v4-experimental/grafo-dashboard-web/app/page.tsx:7`).
   - Essa porta `8000` colide com a porta padrão do servidor FastMCP (`interface/mcp_server.py:144` via `GRAFO_PORT`, e `Dockerfile:29,32` com `ENV GRAFO_PORT=8000` / `EXPOSE 8000`). Além disso, `archive/v4-experimental/grafo-dashboard-web/package.json:10` (`dev:backend`) sobe `python main.py`, que é o servidor MCP sem rotas `/api/*`.
