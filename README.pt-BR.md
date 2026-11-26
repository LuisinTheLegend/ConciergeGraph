[English](README.md) · Português (Brasil)
---

# Grafo Concierge (Núcleo V4)

**Servidor Open-Source e Local-First de Memória de Longo Prazo (LTM), Busca Híbrida e Governança MCP para Agentes de IA e IDEs**

[![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Ferramentas MCP](https://img.shields.io/badge/Ferramentas%20MCP-31-blue.svg)](docs-grafo-concierge/README.md)
[![Testes Aprovados](https://img.shields.io/badge/Testes-369%20Aprovados-brightgreen.svg)](tests/)

O Grafo Concierge é um servidor de memória local-first baseado no **Model Context Protocol (MCP)** que fornece a assistentes de código (Cursor, Claude Desktop e agentes autônomos) memória persistente de projetos, busca híbrida, rastreamento recursivo de chamadas, checkpoints duráveis de agentes e governança progressiva de ferramentas — apoiado em **SQLite WAL (com FTS5)** e armazenamento vetorial plugável (**ChromaDB** por padrão, **Qdrant** opcional).

> **Nota sobre a Consolidação do Núcleo V4:** Módulos experimentais de iterações anteriores foram movidos para quarentena em [`archive/v4-experimental/`](archive/v4-experimental/) para manter o núcleo ativo da V4 enxuto, determinístico e auditado.

---

## Recursos do Núcleo Ativo (V4)

1. **Grafo Relacional em SQLite WAL + FTS5 (`storage/`)**: Armazena projetos, nós de código, arestas de chamada/importação, fatos semânticos, commits de memória e checkpoints duráveis (`agent_checkpoints`) em banco SQLite local com WAL e busca textual FTS5.
2. **Busca Híbrida Tri-Sinal v4 (`core/hybrid_search.py`)**: Combina similaridade vetorial densa (`sentence-transformers` + ChromaDB/Qdrant), pontuação lexical SQLite FTS5 BM25 e sinais topológicos/de recência com escopo estrito por projeto/ala e filtragem de vetores órfãos em tempo de consulta.
3. **Ingestão AST Python e Reparo de Vetores (`ingestion/`, `services/janitor.py`)**: Percorre repositórios, extrai blocos AST Python e arestas de chamada, repara embeddings ausentes durante a mineração com relato explícito de falhas e oferece reconciliação sob demanda (`concierge sync-vector`).
4. **GraphRAG Recursivo de Cadeia de Chamadas (`core/graph_rag.py`)**: Percorre dependências multi-hop `calls` na tabela `edges` via CTEs `WITH RECURSIVE` protegidas por guarda de ciclo delimitada por pipes (`|node|`).
5. **Checkpoints Duráveis de Agentes com Posse Persistente (`core/checkpointer.py`)**: Persiste e recupera dicionários de estado de agentes em `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`, com resolução estrita de argumentos, detecção de JSON corrompido e verificação de posse por `owner_hash` SHA-256 (`GRAFO_AGENT_TOKEN` em `stdio`, ou `X-Grafo-Agent-Token` em HTTP/SSE estritamente desacoplado de `Authorization: Bearer`, com fallback efêmero por `ServerSession`).
6. **Governança MCP de Menor Privilégio (`core/mcp_governor.py`)**: Classifica todas as **31 ferramentas MCP vivas** em `READ_ONLY` (17), `LOCAL_MUTATION` (12) e `DANGEROUS` (2) em uma hierarquia de 3 estados (`PLANNING < EXECUTION < MAINTENANCE`), iniciando em `PLANNING` (`GRAFO_DEFAULT_STATE`) como teto de privilégio (`max_state`). As sessões são vinculadas ao transporte no servidor (`WeakKeyDictionary`), argumentos extras não declarados são rejeitados e tanto `list_tools` (`ListToolsRequest`) quanto a execução aplicam filtragem *fail-closed*.
7. **Neutralidade de Domínio e Alas Livres**: As alas de projetos são strings livres definidas exclusivamente pelo usuário ou agente — sem taxonomias fixas de domínio no código de produto, garantido por testes-guarda AST (`tests/test_domain_neutrality_guard.py`).
8. **Modo Lightweight e Resumos LLM Opcionais**: Defina `GRAFO_LIGHTWEIGHT_MODE=true` para operar sem modelos vetoriais pesados usando SQLite FTS5 BM25, e `GRAFO_LLM_MODEL=none` para operar 100% offline sem chamadas externas a LLMs.

---

## Visão Geral da Arquitetura

```
    ┌───────────────────────────┐      ┌───────────────────────────┐
    │      Cursor / Windsurf    │      │       Claude Desktop      │
    └─────────────┬─────────────┘      └─────────────┬─────────────┘
                  │                                  │
                  │     MCP (stdio padrão / SSE)     │
                  └─────────────────┬────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐      ┌─────────────────────┐
                     │ Servidor MCP Grafo Concierge│      │   CLI concierge     │
                     │ concierge-mcp (Porta 8000)  │      │  (10 subcomandos)   │
                     └──────────────┬──────────────┘      └──────────┬──────────┘
                                    │                                │
                                    └───────────────┬────────────────┘
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │   Fachada GrafoConcierge     │
                                     │   + MCPToolGovernor (31)     │
                                     └──────────────┬───────────────┘
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  SQLite WAL/FTS5 + ChromaDB  │
                                     │  (ou Qdrant opcional)        │
                                     └──────────────────────────────┘
```

---

## Início Rápido

### Instalação Rápida (`v4.1.0`)

> **Status de Release e PyPI:** A versão `4.1.0` substitui o lançamento legado `v3.8.2` no PyPI e a tag pré-auditoria `V4.0.0` no GitHub (preservada no histórico do repositório).

1. **Instalar via pip (ou a partir do código-fonte em modo editável):**
   ```bash
   # Instalação do pacote:
   pip install concierge-graph

   # Ou em modo editável a partir da fonte:
   git clone https://github.com/LuisinTheLegend/ConciergeGraph.git
   cd ConciergeGraph
   python -m venv .venv
   # Linux / macOS: source .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -e .
   ```
   Para desenvolvimento e execução de testes (ou via `pip install -r requirements-dev.txt`; `requirements.txt` contém apenas dependências de produção):
   ```bash
   pip install -e ".[dev]"
   ```

2. **Configurar variáveis de ambiente (`.env`):**
   ```bash
   cp .env.example .env
   ```
   Configuração mínima local-first (sem LLM externo):
   ```env
   GRAFO_LLM_MODEL=none
   GRAFO_TRANSPORT=stdio
   GRAFO_DB_PATH=./data/concierge.db
   GRAFO_CHROMA_PATH=./data/chroma
   ```
   Para executar via HTTP/SSE em vez de `stdio`:
   ```env
   GRAFO_TRANSPORT=sse
   GRAFO_HOST=127.0.0.1
   GRAFO_PORT=8000
   GRAFO_API_KEY=seu_token_bearer_opcional
   ```

3. **Executar o Servidor MCP ou a CLI:**
   ```bash
   # Iniciar o servidor MCP (usa GRAFO_TRANSPORT: stdio padrão ou sse na porta 8000)
   concierge-mcp --help
   concierge-mcp --version
   concierge-mcp --transport sse

   # Ou subir via Docker Compose (usuário não-root UID 10001, SSE + /health)
   docker compose up -d --build

   # Usar a interface de terminal (10 subcomandos)
   concierge --help
   concierge register --name meu-projeto --wing backend/core
   concierge mine --path /caminho/para/meu-projeto --name meu-projeto
   concierge search --query "fluxo de autenticacao" --project <project-uuid>
   ```
   Em HTTP/SSE, `GET /health` e `HEAD /health` respondem `200 {"status": "ok"}` sem exigir `GRAFO_API_KEY`, enquanto `/sse`, `/messages/` e qualquer outro caminho permanecem protegidos por validação ASGI pura `Authorization: Bearer`.

---

## Ferramentas MCP (31 Ferramentas Vivas)

| Categoria | Qtd. | Ferramentas |
| :--- | :---: | :--- |
| **`READ_ONLY`** | 17 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `agent_get_checkpoint`, `agent_list_checkpoints` |
| **`LOCAL_MUTATION`** | 12 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
| **`DANGEROUS`** | 2 | `delete_project`, `reset_collection` |

Consulte [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) para detalhes da arquitetura e a lista completa dos 10 subcomandos da CLI.

---

## Testes e Verificação

O núcleo ativo V4 é coberto por **369 testes automatizados aprovados** (verificados em ordem normal e `--reverse`, além de CI em Linux, Windows e `docker-smoke` em container real):

```bash
python -m pytest tests/ -q
```

---

## Contribuição e Linhagem Técnica

- Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) para os pilares arquiteturais, regras de testes e contratos de governança MCP.
- Leia [`ATTRIBUTION_AND_LINEAGE.md`](ATTRIBUTION_AND_LINEAGE.md) para créditos técnicos e matriz de status (ativo vs. quarentena).
- Leia [`CHANGELOG.md`](CHANGELOG.md) para histórico de alterações e guias de migração.

## Licença

Distribuído sob a Licença MIT. Consulte [`LICENSE`](LICENSE) para mais detalhes.
