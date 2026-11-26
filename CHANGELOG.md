# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [Unreleased]

- Planejado para `v4.2`: adoção opcional da arquitetura *Escolha B* (`interface/queue_writer.py`).

## [4.1.0] - 2026-11-25

> **Nota histórica:** a tag pré-auditoria `V4.0.0` permanece preservada sem alterações no histórico Git; o pacote publicado como `4.1.0` consolida todo o núcleo V4 auditado em substituição à versão legada `3.8.2` no PyPI.

### Rodada 4.9 — Preparação de Release `v4.1.0`

- **Bump e Versão Dinâmica (`pyproject.toml`, `interface/cli.py`, `interface/mcp_server.py`, `.github/workflows/ci.yml`):**
  - Elevada a versão oficial do pacote `concierge-graph` para `4.1.0` em `pyproject.toml`.
  - Substituídas as strings *hardcoded* `"v3.8.0"` por `_get_version()` dinâmico (`importlib.metadata` com *fallback* para `pyproject.toml`) em `interface/cli.py` (`cmd_status`, `build_parser`) e `interface/mcp_server.py` (`_handle_status`), adicionada opção `--version`/`-V` ao CLI `concierge` e validada dinamicamente a versão no job `Docker Smoke` do CI.
- **Empacotamento, Documentação e Higiene de Relatórios (`README.md`, `README.pt-BR.md`, `audits/`):**
  - Validados *build* limpo (`sdist` + `wheel`) e instalação isolada em ambiente virtual fora do repositório (`concierge --version` e `concierge-mcp --version` retornando `4.1.0`).
  - Reconvertido `audits/relatorio_4_8.md` para UTF-8 estrito (`0` bytes NUL) e consolidado o relatório pré-publicação `audits/relatorio_4_9.md`.

### Rodada 4.8 — Docker Real com CI Smoke, CLI `concierge-mcp`, `/health` e Empacotamento Limpo

- **CLI `concierge-mcp` (`main.py`):**
  - Adicionados `_get_package_version()` (leitura via `importlib.metadata` com fallback para `pyproject.toml`), `parse_args()` e suporte a `--help`, `--version` e `--transport {stdio,sse}` antes de `setup_logging`, `decouple_stdin_from_fd0()` e `bootstrap()`, eliminando bloqueio em `stdin` e removendo `"v3.8.0"` *hardcoded* do banner (`tests/test_cli_mcp_entrypoint.py`).
- **Rota Pública `/health` e Middleware ASGI Puro (`interface/mcp_server.py`):**
  - Exposto endpoint de *liveness* `GET` / `HEAD /health` retornando `200 {"status": "ok"}` em `custom_sse_app`.
  - Substituído `BaseHTTPMiddleware` por `_BearerAuthASGIMiddleware` ASGI puro com isenção restrita estritamente a `method in ("GET", "HEAD")`, `path == "/health"` e `raw_path in (None, b"", b"/health")`, mantendo `401` em `/sse`, `/messages/`, `/health/`, `/healthz`, `/%68ealth`, `/health/../sse` e `POST /health`, preservando `hmac.compare_digest` e eliminando *buffering* no *streaming* SSE.
- **Empacotamento PEP 639 / SPDX e Separação de Dependências (`pyproject.toml`, `requirements.txt`, `requirements-dev.txt`):**
  - Atualizado `[build-system]` para `setuptools>=77.0.0`, migrado `license = "MIT"` + `license-files = ["LICENSE"]` removendo o *classifier* legado (zero `SetuptoolsDeprecationWarning`), adicionado extra `[gemini]` e incluídos `packaging>=21.0` e `setuptools>=77.0.0` em `[dev]` (mantendo `version = "3.8.2"`).
  - Separado `requirements.txt` (produção pura) de `requirements-dev.txt` (`-r requirements.txt` + ferramentas de teste/qualidade/build) e endurecidos `tests/test_wheel_integrity.py` e `tests/test_dependency_pins.py`.
- **Container Não-Root e Job `docker-smoke` (`Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`):**
  - Endurecido `Dockerfile` multi-stage com `pip install --no-cache-dir --no-deps .`, usuário não-root `concierge` (`UID/GID 10001`), `HOME=/home/concierge`, `/app/data` gravável, `GRAFO_TRANSPORT=sse`, `HEALTHCHECK` nativo em Python (`/health`) e `CMD ["concierge-mcp"]`.
  - Removido `version: '3.8'` depreciado do `docker-compose.yml`, fixados `GRAFO_TRANSPORT=sse` e caminhos `/app/data/*`, adotado volume nomeado `concierge_data:/app/data`, expostos `GRAFO_DEFAULT_STATE` e `GRAFO_AGENT_TOKEN`, e corrigido `healthcheck` em Python.
  - Adicionado job `docker-smoke` em `.github/workflows/ci.yml` (`ubuntu-latest`) validando build Docker, `UID 10001`, ausência de pacotes `dev`, CLI, `/health`, rejeição `401` e *stream* SSE autenticado — elevando o CI para **7/7 GREEN** e a suíte para **367 testes aprovados** (normal e `--reverse`).

### Rodada 4.7 — Hardening HTTP/SSE, Read-TOCTOU no Checkpointer e Higiene de DDL

- **Hardening do `auth_middleware` HTTP/SSE (`interface/mcp_server.py`):**
  - Removida completamente a autenticação por query string na URL em `custom_sse_app`; o middleware aceita exclusivamente header `Authorization: Bearer <key>` (prefixo `bearer` *case-insensitive*) com comparação em tempo constante via `hmac.compare_digest` e `BaseHTTPMiddleware` (compatível com Starlette 1.x).
- **Separação Estrita entre Transporte `GRAFO_API_KEY` e Posse `X-Grafo-Agent-Token` (`interface/mcp_server.py`):**
  - `_resolve_checkpoint_owner_token()` no ramo HTTP/SSE lê exclusivamente `X-Grafo-Agent-Token`, removendo qualquer fallback para `Authorization: Bearer`. Sem `X-Grafo-Agent-Token`, cada `ServerSession` recebe seu próprio segredo efêmero (`WeakKeyDictionary`), impedindo compartilhamento acidental de posse entre agentes autenticados pela mesma `GRAFO_API_KEY`.
- **Redação de Credenciais Qdrant (`main.py`):**
  - Adicionada `"GRAFO_QDRANT_API_KEY"` à lista de variáveis redigidas em `main.py::redact_log_secrets`.
- **Fechamento Read-TOCTOU e Higiene de DDL (`core/checkpointer.py`, `tests/test_agent_checkpointer.py`):**
  - Incluído `AND owner_hash = ?` (com `caller_hash = self._hash_owner_token(owner_token)`) nas queries de leitura de `get_checkpoint` e `list_checkpoints`.
  - Substituído o DDL manual de 5 colunas em `tests/test_agent_checkpointer.py` pela inicialização oficial via `SchemaManager(conn).apply_full_schema()`, ampliando a suíte para **353 testes aprovados** (normal e `--reverse`).

### Rodada 4.6 — Segurança de Fronteira e Governança MCP (BL-011, BL-012, BL-013, BL-014, BL-015)

- **Teto de Privilégio e Governança de 3 Estados (`core/mcp_governor.py` — BL-011, BL-014, BL-015):**
  - Alterado o estado padrão `GRAFO_DEFAULT_STATE` de `"EXECUTION"` para `"PLANNING"` (menor privilégio) e imposto o teto `max_state` (`PLANNING < EXECUTION < MAINTENANCE`) com exceção explícita `SecurityException(PermissionError)` em tentativas de escalonamento acima do teto; estados `default_state` / `max_state` inválidos falham imediatamente (`ValueError`) no `__init__`.
  - Consolidada a `TOOL_DISCLOSURE_MATRIX` de 8 para **3 estados** (`PLANNING`, `EXECUTION`, `MAINTENANCE`, todos com `"allowed_tools": []`).
  - Reclassificada `concierge_set_state` de `READ_ONLY` para `LOCAL_MUTATION` (`17 READ_ONLY / 12 LOCAL_MUTATION / 2 DANGEROUS`).
- **Isolamento de Sessão por Transporte e Filtragem de `list_tools` (`interface/mcp_server.py` — BL-011, BL-013):**
  - Removido o parâmetro `session_id` controlado pelo cliente em `concierge_set_state(state_name)` e vinculada a sessão de governança estritamente à instância de transporte MCP em `WeakKeyDictionary`.
  - Implementada allowlist estrita de parâmetros em `governed_call_tool` (rejeitando argumentos extras não declarados e payloads não-`dict` antes da invocação) e dupla vinculação de `governed_list_tools()` em `self._mcp.list_tools` e no handler low-level `ListToolsRequest`.
- **Propriedade Persistente em Checkpoints (`storage/schema.py`, `core/checkpointer.py`, `interface/mcp_server.py`, `main.py` — BL-012):**
  - Adicionada coluna `owner_hash TEXT NOT NULL DEFAULT ''` à tabela `agent_checkpoints` com migração idempotente `ALTER TABLE` em bancos SQLite pré-existentes sem perda de dados.
  - Aplicada verificação constante (`hmac.compare_digest` sobre SHA-256) no namespace `(agent_id, session_id)` em `save_checkpoint_detailed`, `save_checkpoint`, `get_checkpoint` e `list_checkpoints` com política *fail-closed* (`PermissionError`).
  - Resolvido o token de posse pelo servidor MCP (`X-Grafo-Agent-Token` > `Authorization: Bearer` em HTTP/SSE; `GRAFO_AGENT_TOKEN` em `stdio`; fallback efêmero por `ServerSession` em `WeakKeyDictionary`) e adicionada `GRAFO_AGENT_TOKEN` à função `main.py::redact_log_secrets`.
  - Cobertura de regressão ampliada para **347 testes aprovados** (incluindo `tests/test_mcp_security_governance.py` e `tests/test_checkpoint_ownership.py`).

### Rodada 4.5g — Governança MCP, Empacotamento/Docker e Documentação Viva

- **Governança MCP (`core/mcp_governor.py`):**
  - Removidas 10 ferramentas fantasma de `TOOL_CLASSIFICATION`, reduzindo o catálogo de 41 para exatamente as **31 ferramentas vivas** registradas em `interface/mcp_server.py` (`18 READ_ONLY`, `11 LOCAL_MUTATION`, `2 DANGEROUS`: `delete_project`, `reset_collection`).
  - Zerado `"allowed_tools": []` nos 7 estados da `TOOL_DISCLOSURE_MATRIX` que ainda listavam `"get_telemetry_snapshot"`, preservando as 8 chaves de estado, `BL-011` e `BL-015`.
  - Endurecidos os contratos em `tests/test_interface_contracts.py` (igualdade estrita `registered == classified` e isolamento do `_shared_governor`), `tests/test_mcp_governor.py` (cobertura fail-closed independente em `filter_tools` e `validate_tool_execution`) e `tests/test_governor_wiring.py` (validação de `governed_list_tools` e ausência de imports de `archive/`).
- **Dependências, `.dockerignore` e `Dockerfile`:**
  - Criado `.dockerignore` na raiz excluindo `.git/`, `.venv*/`, `archive/`, `audits/`, `scratch/`, `tests/`, `data/`, `.env`, `docs-grafo-concierge/`, `grafo-dashboard-web/` e artefatos locais, preservando `README.md`, `LICENSE`, `pyproject.toml`, `requirements.txt`, `main.py` e os 6 pacotes vivos.
  - Podadas 9 dependências dormentes ou transitivas de `[project].dependencies` em `pyproject.toml` e `# Core System & Framework` em `requirements.txt` (`fastapi`, `watchdog`, `pathspec`, `psutil`, `uvicorn`, `sse-starlette`, `httpx`, `pydantic`, `tenacity`), mantendo as 5 dependências diretas vivas (`chromadb`, `mcp>=1.27,<2`, `sentence-transformers`, `python-dotenv`, `starlette`), e movido `rich>=13.0` para `[dev]` / `# Test & Quality Tools`.
  - Atualizadas as URLs em `[project.urls]` de `GrafoConcierge` para `ConciergeGraph` (mantendo `version = "3.8.2"`).
  - Corrigida a ordem no `Dockerfile` (`COPY requirements.txt ./` → `pip install -r requirements.txt` → `COPY . .` → `pip install --no-cache-dir -e .`) para garantir que todos os 6 pacotes vivos sejam mapeados no editable install e preservar o cache de camadas.
- **Documentação Viva e `.env.example`:**
  - Arquivados via `git mv` os 8 documentos legados de `docs-grafo-concierge/` em `archive/v4-experimental/docs-grafo-concierge/` e criado novo `docs-grafo-concierge/README.md` refletindo o núcleo vivo V4.
  - Reescritos `README.md`, `README.pt-BR.md` e `CONTRIBUTING.md` removendo referências ativas a módulos em quarentena, alinhando contagem de ferramentas (**31 MCP tools**), testes (**335 testes**), URLs (`ConciergeGraph`) e nota honesta sobre a versão `3.8.2` publicada no PyPI.
  - Adicionada coluna de status (Ativo vs Quarentena) em `ATTRIBUTION_AND_LINEAGE.md`, limpo `.env.example` (preservando `# GRAFO_LLM_PROVIDER=gemini` comentado e aviso `gemini-` / `disabled`) e corrigidas docstrings em `interface/__init__.py`, `interface/mcp_server.py` e `core/middleware.py`.

---

### Quebras de Compatibilidade (Breaking Changes) — Desacoplamento de Domínio ([F4-030])

Em conformidade com o propósito central do **Grafo Concierge** (ser uma ferramenta de memória neutra quanto a domínio, confiável e honesta sobre o que sabe e o que não sabe), a Rodada 4.4 eliminou taxonomias fixas hardcoded e heurísticas de autocategorização que alteravam arbitrariamente a categorização definida pelo usuário.

Abaixo estão detalhadas as três quebras de compatibilidade introduzidas:

---

#### 1. Parâmetro `auto_categorize` removido de `GrafoConcierge.mine`

- **O que era:**  
  A assinatura do método `GrafoConcierge.mine` continha o parâmetro booleano opcional `auto_categorize: bool = True`:
  ```python
  def mine(self, file_path: str, wing: Optional[str] = None, auto_categorize: bool = True) -> Dict[str, Any]:
  ```
  Quando mantido como `True` (o padrão), qualquer mineração bem-sucedida invocava heurísticas de autocategorização que sobrescreviam silenciosamente a ala primária (`primary_wing`) do projeto no banco de dados.

- **O que virou:**  
  O parâmetro `auto_categorize` foi completamente removido da assinatura:
  ```python
  def mine(self, file_path: str, wing: Optional[str] = None) -> Dict[str, Any]:
  ```
  A mineração agora foca estritamente em analisar e indexar o código-fonte, preservando a ala atribuída pelo usuário no momento do cadastro ou configuração de estado.

- **Exemplo de código antes:**
  ```python
  from core.middleware import GrafoConcierge

  concierge = GrafoConcierge(config=config)
  # Chamada anterior especificando explicitamente auto_categorize
  resultado = concierge.mine("services/payment.py", wing="financeiro", auto_categorize=True)
  ```

- **Exemplo de código depois:**
  ```python
  from core.middleware import GrafoConcierge

  concierge = GrafoConcierge(config=config)
  # Chamada atual sem o parâmetro auto_categorize
  resultado = concierge.mine("services/payment.py", wing="financeiro")
  ```

- **Como migrar:**  
  Remova o argumento `auto_categorize` de todas as chamadas a `concierge.mine(...)` em seu código ou scripts de integração. Se invocado posicionalmente como 3º argumento, passe apenas `file_path` e `wing`. A ala primária do projeto agora é soberana e respeita exclusivamente a atribuição explícita realizada pelo usuário ou agente via `concierge_register` ou `concierge_set_state`.

- **Motivo:**  
  Desacoplamento de domínio e garantia da honestidade e neutralidade. O comportamento anterior violava o princípio de menor surpresa ao alterar metadados de projeto sem consentimento ou intenção explícita do usuário.

---

#### 2. Chave `auto_categorized_wing` removida do retorno de `GrafoConcierge.mine`

- **O que era:**  
  O dicionário retornado por `concierge.mine(...)` incluía a chave `"auto_categorized_wing": Optional[str]`, contendo a ala atribuída pela heurística de palavras-chave caso uma reclassificação tivesse ocorrido.

- **O que virou:**  
  A chave `"auto_categorized_wing"` foi eliminada do dicionário de retorno de `mine`. O payload retornado foca estritamente nas métricas e no status do processo de ingestão:
  ```python
  {
      "status": "success",
      "file_path": file_path,
      "nodes_created": count_nodes,
      "edges_created": count_edges,
      "ast_edges_created": count_ast,
      ...
  }
  ```

- **Exemplo de código antes:**
  ```python
  res = concierge.mine("models/customer.py")
  nova_ala = res.get("auto_categorized_wing")
  if nova_ala:
      print(f"Projeto reclassificado para: {nova_ala}")
  ```

- **Exemplo de código depois:**
  ```python
  res = concierge.mine("models/customer.py")
  # A chave auto_categorized_wing não existe mais
  print(f"Status: {res['status']}, Nós criados: {res['nodes_created']}")
  # Para verificar a ala do projeto, consulte concierge_status ou list_projects
  status = concierge.get_status(project_identifier)
  print(f"Ala atual do projeto: {status['primary_wing']}")
  ```

- **Como migrar:**  
  Remova acessos diretos à chave `res["auto_categorized_wing"]` ou `res.get("auto_categorized_wing")`. Se sua aplicação precisa verificar ou consultar a ala primária do projeto, consulte os métodos oficiais de inspeção de estado (`get_status`, `list_projects` ou ferramentas MCP equivalentes).

- **Motivo:**  
  Desacoplamento de domínio. Com o fim da autocategorização embutida na mineração, a presença dessa chave era enganosa e propagava acoplamento a heurísticas legadas.

---

#### 3. Campo `wing_keywords` removido de `ConciergeConfig`

- **O que era:**  
  A classe `ConciergeConfig` (`core/config.py`) possuía o campo `wing_keywords: Dict[str, List[str]]`, pré-populado com um mapa de palavras-chave arbitrário (ex: `"marketing/vendas"`, `"finanças/quant"`, `"gestão/saas"`, `"automação/rh"`, etc.).

- **O que virou:**  
  O campo `wing_keywords` foi completamente removido de `ConciergeConfig`. A classe de configuração não carrega mais nenhum dicionário de taxonomia pré-fixado.

- **Exemplo de código antes:**
  ```python
  from core.config import ConciergeConfig

  config = ConciergeConfig(
      db_path="concierge.db",
      wing_keywords={
          "custom_wing": ["token1", "token2"]
      }
  )
  ```

- **Exemplo de código depois:**
  ```python
  from core.config import ConciergeConfig

  config = ConciergeConfig(
      db_path="concierge.db"
  )
  ```

- **Como migrar:**  
  Remova o argumento `wing_keywords` de chamadas de instanciação de `ConciergeConfig` e quaisquer acessos a `config.wing_keywords`. Se a sua arquitetura necessita de classificação taxonômica personalizada, realize essa gestão na camada externa do agente ou passe a ala desejada diretamente via `concierge_register(..., wing="sua-ala")` ou `add_reference_wing`.

- **Motivo:**  
  Desacoplamento de domínio. A memória do Grafo Concierge deve ser agnóstica em relação ao domínio da aplicação. Taxonomias de negócios pertencem à camada de aplicação ou aos prompts dos agentes, nunca ao núcleo do motor de grafos.
