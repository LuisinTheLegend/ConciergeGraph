# Relatório Final — Rodada 4.5g (Governança, Dependências/Docker e Documentação Viva)

- **Base de partida verificada:** `884de07d52a9289a94aaaea9587813ffa0e28ffc` (`884de07`)
- **HEAD final (C3):** `dd5d7eec6a6663140db1d8dd794ef92dd9a2ab92` (`dd5d7ee`)
- **Base normativa:** `AUDIT_PROTOCOL.md` (Regras 2, 3, 4, 7, 10, 11, 12, 13, 14 e 15) + `audits/egm/4.5b-sintese.md` (D4, D7, D8) + `audits/fase4-decisoes.md`
- **Status do GATE (Regra 7):** Aguardando revisão do auditor e aprovação humana.

---

## 1. Resumo dos 4 Commits (C0–C3) e Status do CI (6/6)

| Etapa | Commit SHA | Escopo | CI (Linux 3.10/3.11/3.12 + Windows 3.10/3.12/3.14) |
| :--- | :--- | :--- | :--- |
| **C0** | `cb195f84bfa1b636a41f48281471e82655eee25f` | Relatórios EGM + Swarm pré-execução (C1/C2) | **6/6 GREEN** (`runs/44815657144`, `runs/44815657048`) |
| **C1** | `a531739e02d153719dd9352eca5b1f36194735b6` | Limpeza `core/mcp_governor.py` (41→31) + endurecimento de 3 suítes de testes | **6/6 GREEN** (`runs/44862511536`, `runs/44862511530`) |
| **C2** | `30fa1c3740b4f039b2362cedf5e9ca80b399be89` | `.dockerignore`, poda de 9 deps + `rich->dev`, URLs `ConciergeGraph`, fix `Dockerfile` | **6/6 GREEN** (`runs/45531993820`, `runs/45531993917`) |
| **C3** | `dd5d7eec6a6663140db1d8dd794ef92dd9a2ab92` | Documentação viva, `.env.example`, docstrings, `git mv` `docs-grafo-concierge/` → archive | **6/6 GREEN** (`runs/45533812538`, `runs/45533812449`) |

### 1.1 `git show --stat` dos 4 Commits (C0–C3)


```text
=== C0 (cb195f84bfa1b636a41f48281471e82655eee25f) ===
cb195f8 docs(audit): 4.5g-C0 relatórios Swarm pré-execução (governança e deps/docker)
 audits/egm/4.5g-critic.md  | 241 ++++++++++++++++++++++++++
 audits/egm/4.5g-design.md  | 401 ++++++++++++++++++++++++++++++++++++++++++++
 audits/egm/4.5g-fatos.md   | 410 +++++++++++++++++++++++++++++++++++++++++++++
 audits/egm/4.5g-sintese.md |  92 ++++++++++
 4 files changed, 1144 insertions(+)

=== C1 (a531739e02d153719dd9352eca5b1f36194735b6) ===
a531739 refactor(governor): remove 10 phantom tools and harden MCPToolGovernor contracts (4.5g-C1)
 core/mcp_governor.py              |  28 +++----
 tests/test_governor_wiring.py     | 162 ++++++++++++++++++++++++++++++--------
 tests/test_interface_contracts.py |  55 +++++++++++--
 tests/test_mcp_governor.py        | 160 +++++++++++++++++++++++++++++--------
 4 files changed, 316 insertions(+), 89 deletions(-)

=== C2 (30fa1c3740b4f039b2362cedf5e9ca80b399be89) ===
30fa1c3 build(packaging): add .dockerignore and prune quarantined dependencies (4.5g-C2)
 .dockerignore    | 59 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Dockerfile       |  8 +++++---
 pyproject.toml   | 17 ++++------------
 requirements.txt | 11 +----------
 4 files changed, 69 insertions(+), 26 deletions(-)

=== C3 (dd5d7eec6a6663140db1d8dd794ef92dd9a2ab92) ===
dd5d7ee docs(v4): align README, docs, .env.example and docstrings with live V4 core (4.5g-C3)
 .env.example                                       |  17 +-
 ATTRIBUTION_AND_LINEAGE.md                         |  59 +++---
 CHANGELOG.md                                       |  18 ++
 CONTRIBUTING.md                                    | 103 +++++-----
 README.md                                          | 222 +++++++++------------
 README.pt-BR.md                                    | 222 +++++++++------------
 .../docs-grafo-concierge}/01_ARCHITECTURE.md       |   0
 .../02_MCP_TOOLS_REFERENCE.md                      |   0
 .../03_COGNITIVE_MEMORY_AND_FACTS.md               |   0
 .../docs-grafo-concierge}/04_INGESTION_AND_AST.md  |   0
 .../05_HYBRID_SEARCH_AND_ROUTING.md                |   0
 .../06_DEPLOY_AND_CONFIGURATION.md                 |   0
 .../07_MIGRATION_AND_OPERATIONS.md                 |   0
 .../v4-experimental/docs-grafo-concierge/README.md |  69 +++++++
 audits/fase4-decisoes.md                           |  33 +++
 core/middleware.py                                 |   1 -
 docs-grafo-concierge/README.md                     | 119 ++++++-----
 interface/__init__.py                              |   7 +-
 interface/mcp_server.py                            |  31 ++-
 19 files changed, 474 insertions(+), 427 deletions(-)
```


### 1.2 Saídas Literais de Status do CI (6/6 por Commit)


#### C0
```text
Stage C0 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=44815657144 sha=cb195f84bfa1b636a41f48281471e82655eee25f status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/44815657144
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
Stage C0 CI Run (CI): id=44815657048 sha=cb195f84bfa1b636a41f48281471e82655eee25f status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/44815657048
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.10): status=completed conclusion=success
```


#### C1
```text
Stage C1 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=44862511536 sha=a531739e02d153719dd9352eca5b1f36194735b6 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/44862511536
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
Stage C1 CI Run (CI): id=44862511530 sha=a531739e02d153719dd9352eca5b1f36194735b6 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/44862511530
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.10): status=completed conclusion=success
```


#### C2
```text
Stage C2 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45531993820 sha=30fa1c3740b4f039b2362cedf5e9ca80b399be89 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45531993820
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.10): status=completed conclusion=success
Stage C2 CI Run (CI): id=45531993917 sha=30fa1c3740b4f039b2362cedf5e9ca80b399be89 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45531993917
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
Total jobs=6, all_done=True, any_failed=False
```


#### C3
```text
Stage C3 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45533812538 sha=dd5d7eec6a6663140db1d8dd794ef92dd9a2ab92 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45533812538
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
Stage C3 CI Run (CI): id=45533812449 sha=dd5d7eec6a6663140db1d8dd794ef92dd9a2ab92 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45533812449
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
Total jobs=6, all_done=True, any_failed=False
```


---

## 2. Conclusões do Swarm Pré-Execução e Propostas ao Auditor


Cópia literal de [`audits/egm/4.5g-sintese.md`](egm/4.5g-sintese.md):


# Síntese EGM + Swarm — Rodada 4.5g (Pré-Execução de C1 e C2 — Regra 15)

- **Base verificada:** HEAD `884de07d52a9289a94aaaea9587813ffa0e28ffc` (`= origin/main`)
- **Escopo estrito desta síntese:** **exclusivamente C1 (Governança)** e **C2 (Dependências & Docker)**. C3 (Documentação) foi intencionalmente excluído desta revisão conforme determinação do pedido 4.5g.
- **Natureza e governança (Regra 15a/15c/15e/15f):** Os 3 subagentes EGM isolados da Fase 1 (`fatos`, `design`, `critic`) e as 2 rodadas de crítica cruzada do Swarm da Fase 2 (`fatos-45g`, `design-45g`, `critic-45g`) operaram 100% em modo **somente leitura** e foram encerrados com `swarm(action="kill")` antes de qualquer edição em código. O Swarm **propõe** e **não decide**, não edita código e não substitui a verificação independente do auditor.
- **Relatórios individuais (fontes primárias):**
  - [`4.5g-fatos.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/egm/4.5g-fatos.md) (Fase 1 + Swarm `seq #24` e `#30`)
  - [`4.5g-design.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/egm/4.5g-design.md) (Fase 1 + Swarm `seq #25` e `#29`)
  - [`4.5g-critic.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/egm/4.5g-critic.md) (Fase 1 + Swarm `seq #26` e `#28`)

---

## 1. Status de `DECISÃO HUMANA` e Trava de Parada

- **Bloqueios / conflitos que exijam `DECISÃO HUMANA`: ZERO (0).**
- Todas as divergências iniciais entre `fatos`, `design` e `critic` na Fase 1 convergiram integralmente na Rodada 2 do Swarm dentro das invariantes já definidas no pedido (manter os 8 estados em `TOOL_DISCLOSURE_MATRIX`, não mexer em `BL-011`/`BL-015`, manter `version = "3.8.2"`, não alterar `tests/test_wheel_integrity.py` nem `main.py`, e limitar edições em `Dockerfile` ao ajuste mínimo objetivo).

---

## 2. Consenso Técnico para C1 — Governança (`core/mcp_governor.py` e Testes)

1. **Catálogo exato em `core/mcp_governor.py`:**
   - Verificado por `fatos-45g` e `critic-45g`: `TOOL_CLASSIFICATION` (`L79-126`) possui **41 entradas** = **31 ferramentas vivas** registradas em `interface/mcp_server.py:278-963` (`18 READ_ONLY`, `11 LOCAL_MUTATION`, `2 DANGEROUS`: `delete_project` e `reset_collection`) + **10 ferramentas fantasma** (`apply_alias_migration`, `delete_file`, `execute_command`, `get_telemetry_snapshot`, `get_trajectory`, `list_session_checkpoints`, `purge_database`, `retrieve_multihop_context`, `save_checkpoint`, `write_file`).
   - Em `TOOL_DISCLOSURE_MATRIX` (`L43-76`), **7 de 8 estados** (`PLANNING`, `DISCOVERY`, `EXECUTION`, `TDD_GREEN`, `REFACTORING`, `STALL`, `SUCCESS`) ainda listam `"get_telemetry_snapshot"` em `"allowed_tools"`.
   - **Limpeza aprovada:** remover as 10 fantasmas de `TOOL_CLASSIFICATION`, zerar `"allowed_tools": []` nos 7 estados mantendo as 8 chaves de estado e suas `allowed_categories`, e atualizar o exemplo de docstring em `filter_tools` (`L151`, de `'write_file'` para `'concierge_commit'`). `BL-011` (`concierge_set_state` como `READ_ONLY`) e `BL-015` (`GRAFO_DEFAULT_STATE = "EXECUTION"`) permanecem intactos.
2. **Endurecimento de `tests/test_interface_contracts.py` (RED -> GREEN):**
   - Trocar `registered <= classified` (`L231-237`) por igualdade estrita `registered == classified` (`31 == 31`).
   - Verificar os 8 estados preservados e exigir `rules["allowed_tools"] == []` e `set(rules["allowed_tools"]) <= classified` em todos os 8 estados de `TOOL_DISCLOSURE_MATRIX` (fechando a brecha em que `allowed_tools <= classified` deixava sobreviver uma ferramenta viva movida indevidamente para `allowed_tools`).
   - Exigir que `TOOL_CLASSIFICATION["delete_project"] == "DANGEROUS"` e `TOOL_CLASSIFICATION["reset_collection"] == "DANGEROUS"` (únicas 2 `DANGEROUS` vivas).
   - **Fechamento do vazamento C1-F4 (`L77-107, 256, 413`):** comprovado por `fatos-45g` que `test_governed_call_tool_executes_and_enforces_state` grava `"default": "EXECUTION"` permanentemente em `_shared_governor.sessions_state`, sem detecção por `tests/conftest.py`. Corrigir com `had_default` + `pop("default", None)` no `finally:` e salvar/restaurar `core.mcp_governor._shared_governor` na fixture `server`.
3. **Endurecimento de `tests/test_mcp_governor.py` (RED -> GREEN):**
   - Substituir os 3 mocks fantasma (`write_file`, `execute_command`, `get_telemetry_snapshot`) por ferramentas vivas das 3 categorias, testando **ambas** as `DANGEROUS` (`delete_project` e `reset_collection`), `dict` e objeto com `.name` (`SimpleNamespace`, cobrindo `core/mcp_governor.py:163`), partição exata `18/11/2` e `allowed_tools == []` nos 8 estados.
   - **Fechamento de M5 (C1-F2):** testar ferramenta desconhecida (`"unclassified_unknown_tool"`) e fantasma removida (`"write_file"`) **separadamente** em `filter_tools` (`L168`) **e** em `validate_tool_execution` (`L184`), **ambos em `PLANNING` e em `EXECUTION`**, matando mutações `"DANGEROUS" -> "READ_ONLY"` e `"DANGEROUS" -> "LOCAL_MUTATION"` em qualquer uma das duas linhas isoladamente.
   - Cobrir `set_session_state` inválido preservando estado atual (`L131-138`), normalização case-insensitive (`L130`) e isolamento entre sessões.
4. **Refatoração de `tests/test_governor_wiring.py` (RED -> GREEN):**
   - Remover menções obsoletas a `T3`/`T5` na docstring e imports não utilizados (`os`, `pytest`).
   - **`T1` (subprocesso limpo):** validar `import interface.mcp_server` -> `governor is None`, `'core.mcp_governor' not in sys.modules`, zero `archive`/`archive.*` (por nome ou `__file__`) e zero `('agents.revisor_critico', 'agents', 'agent', 'interface.action_hooks', 'interface.telemetry_api', 'fastapi', 'flask', 'django')` — **não** banir `starlette`, pois `mcp/server/fastmcp/server.py:23` a importa no top-level (C1-F5).
   - **`T2` (subprocesso limpo):** construir `GrafoConciergeServer` com `try/finally: store.close()`, validar zero `archive` e frameworks banidos, identidade `server._governor is server.governor is interface.mcp_server.governor is get_shared_governor()`, `registered == classified` e `allowed_tools == []`.
   - **`T4`:** manter intacto, adicionando `monkeypatch.setattr(core.mcp_governor, "_shared_governor", None)` e `try/finally: store.close()`.
   - **`T5` (novo — C1-F5):** testar `governed_list_tools` (`interface/mcp_server.py:258-266`) usando **`session_id` explícito não-`"default"`** (com `"default"` intocado no padrão) e `monkeypatch` das 4 sentinelas + `_shared_governor`, asserindo contagens e filtros concretos sobre objetos `Tool` reais: sem `session_id` -> 31, `PLANNING` -> 18, `EXECUTION` -> 29, `MAINTENANCE` -> 31.

---

## 3. Consenso Técnico para C2 — Dependências, `.dockerignore` e `Dockerfile`

1. **Auditoria das 15 dependências de `pyproject.toml::dependencies`:**
   - **Manter exatamente 5 diretas vivas:** `chromadb>=1.0` (`storage/vector_store.py:32-33,317`), `mcp>=1.27,<2` (`interface/mcp_server.py:47`), `sentence-transformers>=3.0` (`storage/vector_store.py:49,158`), `python-dotenv>=1.0` (`main.py:33-34`, `interface/cli.py:51-52`, `scripts/bootstrap_core_memory.py:12,18`), `starlette>=0.36` (`interface/mcp_server.py:180-181`).
   - **Mover para `[project.optional-dependencies].dev`:** `rich>=13.0` (0 imports em produção; import direto obrigatório em `tests/test_ingestion_embed_regression.py:17,103`; em `mcp` é apenas `extra == 'rich'`, hoje chegava só via `chromadb`).
   - **Remover 9 pacotes de `[project].dependencies`:** 4 dormentes não-transitivas (`fastapi`, `watchdog`, `pathspec`, `psutil`) + 5 transitivas sem nenhum import direto no código ou testes vivos e cobertas incondicionalmente por `mcp` e/ou `chromadb` (`uvicorn`, `sse-starlette`, `httpx`, `pydantic`, `tenacity`). `fatos-45g` verificou que `sse-starlette>=2.0` vs `>=1.6.1` do `mcp` não possui exigência técnica no código vivo (único consumidor é o próprio `mcp`).
   - **URLs em `pyproject.toml:74-76`:** alinhar `GrafoConcierge` -> `ConciergeGraph` (conforme `git remote -v`). Manter `version = "3.8.2"`.
2. **Sincronização de `requirements.txt`:**
   - Reduzir `# Core System & Framework` para as mesmas **5** dependências vivas em PEP 508 puro (sem `-e .` ou flags, respeitando `tests/test_dependency_pins.py:57-65`).
   - Preservar `# LLM Providers` (`google-genai`, `openai`) e `# Optional Vector Backends` (`qdrant-client`) consumidos pelo fluxo `Dockerfile:15` / `docker-compose.yml:16-17`, além de `CONTRIBUTING.md:89`.
   - Mover `rich>=13.0.0` para `# Test & Quality Tools`.
3. **`.dockerignore` (entregável obrigatório de C2):**
   - Blacklist explícita cobrindo `.git/`, `.github/`, `.gitignore`, `.gitattributes`, `.venv*/`, `venv/`, `env/`, `.uv/`, `__pycache__/`, `**/__pycache__/`, `**/*.py[cod]`, `**/*$py.class`, `.pytest_cache/`, `.mypy_cache/`, `.coverage`, `htmlcov/`, `build/`, `dist/`, `*.egg-info/`, `archive/`, `audits/`, `scratch/`, `tests/`, `docs-grafo-concierge/`, `grafo-dashboard-web/`, `node_modules/`, `agent/`, `agents/`, `core/parsers/`, `_stress_test_*`, `_colossus_workspace/`, `_test_*_tmp/`, `data/`, `chroma/`, `chroma_db/`, `.qdrant/`, `**/*.db*`, `**/*.sqlite*`, `*.log`, `logs/`, `.env`, `.env.*`, `.conciergeignore*`, `*.pem`, `*.key`, `*.cert`, `*.crt`, `*.md` seguido de `!README.md`, `*.txt` seguido de `!requirements.txt`, `.vscode/`, `.idea/`, `.agents/`, `.reversa/`, `_reversa_sdd/`, `.claude/`, `docker-compose.yml`, `.dockerignore` (omitindo `Dockerfile` para máxima portabilidade entre builders).
   - Verificado que nenhum arquivo vivo nos 6 pacotes (`core/`, `storage/`, `ingestion/`, `services/`, `interface/`, `scripts/`) tem extensão ignorada (`.md`, `.txt`, `.db*`, `.py[cod]`), preservando 100% do código vivo, `README.md`, `LICENSE`, `pyproject.toml`, `requirements.txt` e `main.py`.
4. **Defeito objetivo comprovado em `Dockerfile:10-17` e ajuste mínimo:**
   - **Prova estática e empírica (`fatos-45g` em `setuptools 84.2.1`):** a ausência de `README.md`/`LICENSE` no `builder` emitia warnings em `expand.py:126-138`, mas o defeito real e objetivo é que `pip install -e .` antes de `COPY . .` gera `_TopLevelFinder` em `editable_wheel.py:381-390,521-544` com `MAPPING = {'main': '/app/main'}` e **0/6 pacotes vivos mapeados** (quebrando `concierge` e `concierge-mcp` fora de `/app`, além de gerar `METADATA` sem `README`/`LICENSE`).
   - **Retificação unânime (`design-45g` + `critic-45g`):** **manter `pip install -e .`** (não trocar por instalação não-editável `.`), pois `main.py:47` (`PROJECT_ROOT`) e `interface/cli.py:60` ancoram `data/` a `__file__`; sem `-e .`, `concierge` e `concierge-mcp` gravariam em `site-packages/data/` em vez do volume `/app/data`.
   - **Ajuste mínimo aprovado em `Dockerfile:10-17`:** trocar `COPY pyproject.toml requirements.txt ./` -> `COPY requirements.txt ./` antes de `pip install -r requirements.txt` (preservando cache de ~2 GB de camadas PyTorch/ChromaDB contra edições em `pyproject.toml`), e mover `COPY . .` para imediatamente antes de `RUN pip install --no-cache-dir -e .`.
5. **Smoke install em venv 100% limpo fora do repo:**
   - `main.py` (caminho proibido) não possui parser `--help` (`concierge-mcp --help` iniciaria `stdio` e bloquearia `stdin`).
   - Portanto o smoke valida: `<venv>\Scripts\concierge --help` (exit 0), existência do executável `concierge-mcp` + `entry_points(group="console_scripts")` mapeando `concierge-mcp -> main:main` (`callable(ep.load()) is True`), `PackageNotFoundError` para `fastapi`/`watchdog`/`pathspec`/`psutil`, import dos 6 pacotes/módulos vivos (`scripts.bootstrap_core_memory` como namespace PEP 420), instanciação de `GrafoConciergeServer` com **`gc.config = None`** listando **31 ferramentas**, e `server.mcp.sse_app()` retornando aplicação Starlette íntegra.

---

## 4. Propostas ao Auditor (Fora do Escopo Aprovado da 4.5g — NÃO Implementadas, Regra 15a/15b)

Os achados concretos abaixo foram confirmados pelo Swarm, mas **extrapolam o escopo estrito de C1/C2/C3** e ficam registrados exclusivamente para decisão futura do auditor e do humano:

1. **Runtime e Healthcheck no Docker (`Dockerfile:19-34`, `docker-compose.yml:1,9-26`):**
   - Nem `Dockerfile` nem `docker-compose.yml` definem `ENV GRAFO_TRANSPORT=sse`, embora exponham porta `8000`; sem isso, `main.py:73` sobe em `stdio`, lê EOF e encerra em loop de restart (`unless-stopped`).
   - `docker-compose.yml:23` executa `curl -f http://localhost:8000/ || exit 0` — `curl` não vem em `python:3.12-slim` e `|| exit 0` mascara qualquer erro tornando o container eternamente `healthy` (e `/sse` responde `401` se `GRAFO_API_KEY` estiver definida).
   - Processo no container roda como `root` (sem `USER`) e `docker-compose.yml:1` usa `version: '3.8'` depreciado no Compose v2.
2. **Separação de `requirements.txt` (produção pura vs dev) e ausência de `pytest-timeout` (`requirements.txt:27-30` vs `pyproject.toml:60,118-119`):**
   - `Dockerfile:15` ainda instala `pytest`, `flake8`, `mypy` e `rich` na imagem Docker por ler `requirements.txt`. E `pytest-timeout>=2.2.0` (usado por 14 testes em `tests/test_connection_queue_resilience.py`) falta em `requirements.txt`. Avaliar `requirements.txt` prod-only + `requirements-dev.txt` em rodada futura.
3. **Metadados de extras opcionais e de testes em `pyproject.toml`:**
   - Ausência de extra opcional `[gemini]` dedicado (`google-genai>=0.1.0` consta apenas em `[dev]` e `[all]`), assimétrico em relação a `[openai]` e `[qdrant]`.
   - `tests/test_dependency_pins.py:12-13` importa `packaging` diretamente sem declaração explícita em `[project.optional-dependencies].dev`.
   - `F4-014` (`ingestion/parser.py:180-235`): `tree_sitter` e gramáticas continuam ausentes das dependências opcionais.
4. **Suporte a `--help` / argumentos CLI em `main.py` (`concierge-mcp`):**
   - `main.py` é caminho proibido na 4.5g; adicionar `argparse` (`--help`, `--version`, `--transport`) em `concierge-mcp` para evitar bloqueio acidental em `stdin`.
5. **Governança MCP em produção além de BL-011 e BL-015:**
   - `interface/mcp_server.py:260-264`: `governed_list_tools(session_id=None)` retorna todas as 31 ferramentas sem filtro quando clientes MCP padrão não enviam `session_id` em `tools/list`, e 27 das 31 ferramentas em `governed_call_tool` (`:246-254`) não declaram `session_id`, caindo em `"default"`.
   - `core/mcp_governor.py:37-38,154-156,181-183`: `GRAFO_DEFAULT_STATE` inválido fora de `TOOL_DISCLOSURE_MATRIX` não é validado no `__init__` e gera `KeyError` em tempo de execução.
   - Avaliar futuramente reduzir `TOOL_DISCLOSURE_MATRIX` dos 8 estados HSM legados para os 3 estados documentados em `concierge_set_state` (`PLANNING`, `EXECUTION`, `MAINTENANCE`) ao tratar BL-011/BL-015.
6. **Guardas de empacotamento e resíduos locais em `tests/` (fora da lista de arquivos autorizados de C1/C2):**
   - `tests/test_wheel_integrity.py:28-29,115` e `tests/test_ingestion_embed_regression.py:205` ainda citam `"agent"` / `"agents"`, e `leaked` no wheel ainda não bloqueia `agent/` e `agents/` nem inspeciona `Requires-Dist` em `METADATA`.
   - Estender `tests/test_dependency_pins.py` futuramente com guarda anti-regressão bloqueando retorno de `fastapi`, `watchdog`, `pathspec`, `psutil` a `[project].dependencies`.
7. **Higiene local do ambiente:**
   - Existem pastas não rastreadas apenas com `__pycache__/*.pyc` órfãos em `agent/`, `agents/` e `core/parsers/`, além do editable install local em `.venv_313` apontando para o estado pré-4.5d (`.venv_313/.../__editable___concierge_graph_3_8_2_finder.py`).


> **Observação menor descoberta durante C3 (fora de escopo — NÃO editada):** durante a varredura estendida de docstrings, foi identificada a menção residual `"feeding Thompson Sampling in HybridSearchEngine."` na docstring de `GrafoConcierge.update_fact_utility` em `core/middleware.py:681`. Por disciplina de escopo (em `core/middleware.py`, apenas a linha 13 constava no escopo autorizado da 4.5g), `L681` foi mantida intocada e registrada aqui para eventual higienização futura.

---

## 3. Evidências de C1 — Governança (`core/mcp_governor.py` e Testes)

### 3.1 Fase RED (`c1_red.txt`)


```text
$ C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe -m pytest tests/test_interface_contracts.py tests/test_mcp_governor.py tests/test_governor_wiring.py -v --tb=short
exit_code=1

============================= test session starts =============================
platform win32 -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
timeout: 300.0s
timeout method: thread
timeout func_only: False
collecting ... collected 32 items

tests/test_interface_contracts.py::TestInterfaceImports::test_mcp_server_importable PASSED [  3%]
tests/test_interface_contracts.py::TestInterfaceImports::test_interface_package_exports PASSED [  6%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_accepts_concierge_param PASSED [  9%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_accepts_janitor_param PASSED [ 12%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_sqlite_store_param PASSED [ 15%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_vector_store_param PASSED [ 18%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_embedding_manager_param PASSED [ 21%]
tests/test_interface_contracts.py::TestCLIParser::test_all_subcommands_present PASSED [ 25%]
tests/test_interface_contracts.py::TestCLIParser::test_command_count PASSED [ 28%]
tests/test_interface_contracts.py::TestCLIParser::test_search_args_parsed PASSED [ 31%]
tests/test_interface_contracts.py::TestCLIParser::test_mine_args_parsed PASSED [ 34%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_all_required_tools_registered PASSED [ 37%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_all_registered_tools_classified_in_governor FAILED [ 40%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_disclosure_matrix_clean_and_valid FAILED [ 43%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_destructive_tools_classified_as_dangerous FAILED [ 46%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_governed_call_tool_executes_and_enforces_state PASSED [ 50%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_server_name_is_grafo_concierge PASSED [ 53%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_no_chromadb_component PASSED [ 56%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_no_embedding_component PASSED [ 59%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_sqlite_component PASSED [ 62%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_clean_disclosure_matrix FAILED [ 65%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_session_state_normalization_invalid_preservation_and_isolation PASSED [ 68%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_all_tools_in_maintenance_state PASSED [ 71%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_mutation_tools_in_execution_state PASSED [ 75%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_filter_tools_in_planning_state PASSED [ 78%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_raise_security_exception_on_direct_call_attempt PASSED [ 81%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_blocked_in_execution_and_planning FAILED [ 84%]
tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_filtered_out_fail_closed FAILED [ 87%]
tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 90%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi FAILED [ 93%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails PASSED [ 96%]
tests/test_governor_wiring.py::test_t5_governed_list_tools_filters_by_explicit_session_id PASSED [100%]

================================== FAILURES ===================================
__ TestMCPToolRegistration.test_all_registered_tools_classified_in_governor ___
tests\test_interface_contracts.py:242: in test_all_registered_tools_classified_in_governor
    assert not phantom, f"Phantom tools in TOOL_CLASSIFICATION not registered on server: {phantom}"
E   AssertionError: Phantom tools in TOOL_CLASSIFICATION not registered on server: ['apply_alias_migration', 'delete_file', 'execute_command', 'get_telemetry_snapshot', 'get_trajectory', 'list_session_checkpoints', 'purge_database', 'retrieve_multihop_context', 'save_checkpoint', 'write_file']
E   assert not ['apply_alias_migration', 'delete_file', 'execute_command', 'get_telemetry_snapshot', 'get_trajectory', 'list_session_checkpoints', ...]
___ TestMCPToolRegistration.test_governor_disclosure_matrix_clean_and_valid ___
tests\test_interface_contracts.py:262: in test_governor_disclosure_matrix_clean_and_valid
    assert allowed_tools == [], (
E   AssertionError: State 'PLANNING' has unexpected allowed_tools override: ['get_telemetry_snapshot']
E   assert ['get_telemetry_snapshot'] == []
E     
E     Left contains one more item: 'get_telemetry_snapshot'
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E     - []
E     + [
E     +     'get_telemetry_snapshot',
E     + ]
_ TestMCPToolRegistration.test_governor_destructive_tools_classified_as_dangerous _
tests\test_interface_contracts.py:278: in test_governor_destructive_tools_classified_as_dangerous
    assert dangerous == {"delete_project", "reset_collection"}
E   AssertionError: assert {'delete_proj...t_collection'} == {'delete_proj...t_collection'}
E     
E     Extra items in the left set:
E     'purge_database'
E     'execute_command'
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       {...
E     
E     ...Full output truncated, use '-vv' to show
_ TestMCPToolGovernor.test_classification_partition_and_clean_disclosure_matrix _
tests\test_mcp_governor.py:36: in test_classification_partition_and_clean_disclosure_matrix
    self.assertEqual(len(self.governor.TOOL_CLASSIFICATION), 31)
E   AssertionError: 41 != 31
_ TestMCPToolGovernor.test_unknown_and_removed_tools_blocked_in_execution_and_planning _
tests\test_mcp_governor.py:148: in test_unknown_and_removed_tools_blocked_in_execution_and_planning
    self.assertIn("DANGEROUS", str(ctx.exception))
E   AssertionError: 'DANGEROUS' not found in "Access denied: tool 'write_file' (category 'LOCAL_MUTATION') is blocked during state 'PLANNING' for session 'sess_fc_exec'."
_ TestMCPToolGovernor.test_unknown_and_removed_tools_filtered_out_fail_closed _
tests\test_mcp_governor.py:137: in test_unknown_and_removed_tools_filtered_out_fail_closed
    self.assertEqual(exec_names, {"get_full_topology", "concierge_commit"})
E   AssertionError: Items in the first set but not the second:
E   'write_file'
_____ test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi ______
tests\test_governor_wiring.py:104: in test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi
    assert res.returncode == 0, f"Falha na guarda de construção T2: {res.stdout.strip()} {res.stderr.strip()}"
E   AssertionError: Falha na guarda de construção T2:  [11/20/26 18:01:58] INFO     GrafoConciergeServer initialized mcp_server.py:230
E                                  — 31 tools registered.                            
E                         INFO     Requesting stop of               connection.py:164
E                                  SerializedWriteQueue...                           
E                         INFO     SerializedWriteQueue finished.   connection.py:170
E                         INFO     SqliteStore closed.                   store.py:114
E     Traceback (most recent call last):
E       File "<string>", line 20, in <module>
E         assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'
E                ^^^^^^^^^^^^^^^^^^^^^^^^
E     AssertionError: Mismatch: reg-cls=[] cls-reg=['apply_alias_migration', 'delete_file', 'execute_command', 'get_telemetry_snapshot', 'get_trajectory', 'list_session_checkpoints', 'purge_database', 'retrieve_multihop_context', 'save_checkpoint', 'write_file']
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=['C:\\Nexus-Memory\\GrafoConcierge\\.venv_313\\Scripts\\python.exe', '-c', "import sys\nfrom pathlib import Path\nfrom unittest.mock import MagicMock\nimport core.mcp_governor\nfrom storage.store import SqliteStore\nimport interface.mcp_server\nfrom interface.mcp_server import GrafoConciergeServer\narchive_dir = Path('C:\\\\Nexus-Memory\\\\GrafoConcierge\\\\archive')\nstore = SqliteStore('C:\\\\Users\\\\guial\\\\AppData\\\\Local\\\\Temp\\\\pytest-of-guial\\\\pytest-485\\\\test_t2_mcp_server_constructio0\\\\test_wire.db')\ntry:\n    gc = MagicMock()\n    gc._store = store\n    server = GrafoConciergeServer(concierge=gc)\n    shared_gov = core.mcp_governor.get_shared_governor()\n    assert server._governor is shared_gov\n    assert server.governor is server._governor\n    assert interface.mcp_server.governor is server._governor\n    registered = set(server.mcp._tool_manager._tools.keys())\n    classified = set(server._governor.TOOL_CLASSIFICATION.keys())\n    assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'\n    assert len(registered) == 31\n    assert all(r['allowed_tools'] == [] for...  archive_mods.append(f'{name}:{mod_file}')\nif dragged or archive_mods:\n    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n    sys.exit(1)\n"], returncode=1, stdout='', stderr='[11/20/26 18:01:58] INFO     GrafoConciergeServer initialized mcp_server.py:230\n                             — 31 tools registered.                            \n                    INFO     Requesting stop of               connection.py:164\n                             SerializedWriteQueue...                           \n                    INFO     SerializedWriteQueue finished.   connection.py:170\n                    INFO     SqliteStore closed.                   store.py:114\nTraceback (most recent call last):\n  File "<string>", line 20, in <module>\n    assert registered == classified, f\'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}\'\n           ^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Mismatch: reg-cls=[] cls-reg=[\'apply_alias_migration\', \'delete_file\', \'execute_command\', \'get_telemetry_snapshot\', \'get_trajectory\', \'list_session_checkpoints\', \'purge_database\', \'retrieve_multihop_context\', \'save_checkpoint\', \'write_file\']\n').returncode
=========================== short test summary info ===========================
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_all_registered_tools_classified_in_governor
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_disclosure_matrix_clean_and_valid
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_destructive_tools_classified_as_dangerous
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_clean_disclosure_matrix
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_blocked_in_execution_and_planning
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_filtered_out_fail_closed
FAILED tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi
======================== 7 failed, 25 passed in 10.83s ========================
```


### 3.2 Testes de Mutação M1–M5a/M5b (`c1_mutations.txt`)


```text
=== MUTACOES DELIBERADAS C1 (core/mcp_governor.py) ===
Pre-check GREEN: 32 passed in 10.46s

## M1 (delete_project DANGEROUS -> READ_ONLY)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -112,7 +112,7 @@
 
             # DANGEROUS
             "reset_collection": "DANGEROUS",
-            "delete_project": "DANGEROUS",
+            "delete_project": "READ_ONLY",
         }
 
     def set_session_state(self, session_id: str, state_name: str) -> None:
--- resumo da falha pytest ---
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_destructive_tools_classified_as_dangerous
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_clean_disclosure_matrix
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_mutation_tools_in_execution_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_filter_tools_in_planning_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_raise_security_exception_on_direct_call_attempt
======================== 5 failed, 23 passed in 1.70s =========================

## M2 (reset_collection DANGEROUS -> READ_ONLY)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -111,7 +111,7 @@
             "update_project": "LOCAL_MUTATION",
 
             # DANGEROUS
-            "reset_collection": "DANGEROUS",
+            "reset_collection": "READ_ONLY",
             "delete_project": "DANGEROUS",
         }
--- resumo da falha pytest ---
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_destructive_tools_classified_as_dangerous
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_clean_disclosure_matrix
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_mutation_tools_in_execution_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_filter_tools_in_planning_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_raise_security_exception_on_direct_call_attempt
======================== 5 failed, 23 passed in 1.53s =========================

## M3 (reinserir write_file em TOOL_CLASSIFICATION)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -98,6 +98,7 @@
             "agent_list_checkpoints": "READ_ONLY",
 
             # LOCAL_MUTATION
+            "write_file": "LOCAL_MUTATION",
             "agent_save_checkpoint": "LOCAL_MUTATION",
             "concierge_register": "LOCAL_MUTATION",
             "concierge_mine": "LOCAL_MUTATION",
--- resumo da falha pytest ---
E     AssertionError: Mismatch: reg-cls=[] cls-reg=['write_file']
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=['C:\\Nexus-Memory\\GrafoConcierge\\.venv_313\\Scripts\\python.exe', '-c', "import sys\nfrom pathlib import Path\nfrom unittest.mock import MagicMock\nimport core.mcp_governor\nfrom storage.store import SqliteStore\nimport interface.mcp_server\nfrom interface.mcp_server import GrafoConciergeServer\narchive_dir = Path('C:\\\\Nexus-Memory\\\\GrafoConcierge\\\\archive')\nstore = SqliteStore('C:\\\\Users\\\\guial\\\\AppData\\\\Local\\\\Temp\\\\pytest-of-guial\\\\pytest-489\\\\test_t2_mcp_server_constructio0\\\\test_wire.db')\ntry:\n    gc = MagicMock()\n    gc._store = store\n    server = GrafoConciergeServer(concierge=gc)\n    shared_gov = core.mcp_governor.get_shared_governor()\n    assert server._governor is shared_gov\n    assert server.governor is server._governor\n    assert interface.mcp_server.governor is server._governor\n    registered = set(server.mcp._tool_manager._tools.keys())\n    classified = set(server._governor.TOOL_CLASSIFICATION.keys())\n    assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'\n    assert len(registered) == 31\n    assert all(r['allowed_tools'] == [] for... or name.startswith('archive.'):\n        archive_mods.append(name)\n        continue\n    mod_file = getattr(mod, '__file__', None)\n    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n        archive_mods.append(f'{name}:{mod_file}')\nif dragged or archive_mods:\n    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n    sys.exit(1)\n"], returncode=1, stdout='', stderr='[11/20/26 18:03:36] INFO     GrafoConciergeServer initialized mcp_server.py:230\n                             — 31 tools registered.                            \n                    INFO     Requesting stop of               connection.py:164\n                             SerializedWriteQueue...                           \n                    INFO     SerializedWriteQueue finished.   connection.py:170\n                    INFO     SqliteStore closed.                   store.py:114\nTraceback (most recent call last):\n  File "<string>", line 20, in <module>\n    assert registered == classified, f\'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}\'\n           ^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Mismatch: reg-cls=[] cls-reg=[\'write_file\']\n').returncode
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_all_registered_tools_classified_in_governor
FAILED tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi
======================== 2 failed, 22 passed in 9.20s =========================

## M4 (reinserir get_telemetry_snapshot em PLANNING allowed_tools)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -43,7 +43,7 @@
         self.TOOL_DISCLOSURE_MATRIX: Dict[str, Dict[str, List[str]]] = {
             "PLANNING": {
                 "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": [],
+                "allowed_tools": ["get_telemetry_snapshot"],
             },
             "DISCOVERY": {
                 "allowed_categories": ["READ_ONLY"],
--- resumo da falha pytest ---
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=['C:\\Nexus-Memory\\GrafoConcierge\\.venv_313\\Scripts\\python.exe', '-c', "import sys\nfrom pathlib import Path\nfrom unittest.mock import MagicMock\nimport core.mcp_governor\nfrom storage.store import SqliteStore\nimport interface.mcp_server\nfrom interface.mcp_server import GrafoConciergeServer\narchive_dir = Path('C:\\\\Nexus-Memory\\\\GrafoConcierge\\\\archive')\nstore = SqliteStore('C:\\\\Users\\\\guial\\\\AppData\\\\Local\\\\Temp\\\\pytest-of-guial\\\\pytest-490\\\\test_t2_mcp_server_constructio0\\\\test_wire.db')\ntry:\n    gc = MagicMock()\n    gc._store = store\n    server = GrafoConciergeServer(concierge=gc)\n    shared_gov = core.mcp_governor.get_shared_governor()\n    assert server._governor is shared_gov\n    assert server.governor is server._governor\n    assert interface.mcp_server.governor is server._governor\n    registered = set(server.mcp._tool_manager._tools.keys())\n    classified = set(server._governor.TOOL_CLASSIFICATION.keys())\n    assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'\n    assert len(registered) == 31\n    assert all(r['allowed_tools'] == [] for...me == 'archive' or name.startswith('archive.'):\n        archive_mods.append(name)\n        continue\n    mod_file = getattr(mod, '__file__', None)\n    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n        archive_mods.append(f'{name}:{mod_file}')\nif dragged or archive_mods:\n    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n    sys.exit(1)\n"], returncode=1, stdout='', stderr='[11/20/26 18:03:49] INFO     GrafoConciergeServer initialized mcp_server.py:230\n                             — 31 tools registered.                            \n                    INFO     Requesting stop of               connection.py:164\n                             SerializedWriteQueue...                           \n                    INFO     SerializedWriteQueue finished.   connection.py:170\n                    INFO     SqliteStore closed.                   store.py:114\nTraceback (most recent call last):\n  File "<string>", line 22, in <module>\n    assert all(r[\'allowed_tools\'] == [] for r in server._governor.TOOL_DISCLOSURE_MATRIX.values())\n           ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError\n').returncode
FAILED tests/test_interface_contracts.py::TestMCPToolRegistration::test_governor_disclosure_matrix_clean_and_valid
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_clean_disclosure_matrix
FAILED tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi
======================== 3 failed, 29 passed in 9.53s =========================

## M5a (fallback filter_tools DANGEROUS -> READ_ONLY isolado)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -155,7 +155,7 @@
             if not tool_name:
                 continue
 
-            category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")
+            category = self.TOOL_CLASSIFICATION.get(tool_name, "READ_ONLY")
 
             if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
                 filtered.append(tool)
--- resumo da falha pytest ---
tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_filtered_out_fail_closed FAILED [100%]
E   AssertionError: Items in the first set but not the second:
E   'write_file'
E   'unclassified_unknown_tool'
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_filtered_out_fail_closed
========================= 1 failed, 7 passed in 1.00s =========================

## M5b (fallback validate_tool_execution DANGEROUS -> READ_ONLY isolado)
exit_code=1 (KILLED) | reverted_exact=True
--- diff da mutacao ---
--- core/mcp_governor.py (C1 green)
+++ core/mcp_governor.py (mutated)
@@ -171,7 +171,7 @@
         rules = self.TOOL_DISCLOSURE_MATRIX.get(
             current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
         )
-        category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")
+        category = self.TOOL_CLASSIFICATION.get(tool_name, "READ_ONLY")
 
         if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
             return True
--- resumo da falha pytest ---
tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_blocked_in_execution_and_planning FAILED [ 87%]
E   AssertionError: SecurityException not raised
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_blocked_in_execution_and_planning
========================= 1 failed, 7 passed in 1.09s =========================

Final core/mcp_governor.py == C1 green baseline: True
git diff core/mcp_governor.py (linhas vs HEAD 884de07): 91
```


### 3.3 `git diff` Integral de C1 (`c1_diff.txt`)


```diff
diff --git a/core/mcp_governor.py b/core/mcp_governor.py
index 2843a77..48179ca 100644
--- a/core/mcp_governor.py
+++ b/core/mcp_governor.py
@@ -43,23 +43,23 @@ class MCPToolGovernor:
         self.TOOL_DISCLOSURE_MATRIX: Dict[str, Dict[str, List[str]]] = {
             "PLANNING": {
                 "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "DISCOVERY": {
                 "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "EXECUTION": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "TDD_GREEN": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "REFACTORING": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "MAINTENANCE": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"],
@@ -67,24 +67,20 @@ class MCPToolGovernor:
             },
             "STALL": {
                 "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
             "SUCCESS": {
                 "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": ["get_telemetry_snapshot"],
+                "allowed_tools": [],
             },
         }
 
-        # Static tool classification catalog
+        # Static tool classification catalog (31 live MCP tools)
         self.TOOL_CLASSIFICATION: Dict[str, str] = {
             # READ_ONLY
             "get_full_topology": "READ_ONLY",
-            "get_trajectory": "READ_ONLY",
             "get_trajectories": "READ_ONLY",
             "find_similar": "READ_ONLY",
-            "retrieve_multihop_context": "READ_ONLY",
-            "list_session_checkpoints": "READ_ONLY",
-            "get_telemetry_snapshot": "READ_ONLY",
             "concierge_search": "READ_ONLY",
             "concierge_resume": "READ_ONLY",
             "concierge_load": "READ_ONLY",
@@ -102,10 +98,6 @@ class MCPToolGovernor:
             "agent_list_checkpoints": "READ_ONLY",
 
             # LOCAL_MUTATION
-            "write_file": "LOCAL_MUTATION",
-            "delete_file": "LOCAL_MUTATION",
-            "apply_alias_migration": "LOCAL_MUTATION",
-            "save_checkpoint": "LOCAL_MUTATION",
             "agent_save_checkpoint": "LOCAL_MUTATION",
             "concierge_register": "LOCAL_MUTATION",
             "concierge_mine": "LOCAL_MUTATION",
@@ -119,9 +111,7 @@ class MCPToolGovernor:
             "update_project": "LOCAL_MUTATION",
 
             # DANGEROUS
-            "execute_command": "DANGEROUS",
             "reset_collection": "DANGEROUS",
-            "purge_database": "DANGEROUS",
             "delete_project": "DANGEROUS",
         }
 
@@ -148,7 +138,7 @@ class MCPToolGovernor:
         Passive Layer (Discovery): Filters tool catalog disclosed to agent
         based on active FSM state rules.
 
-        Supports both dictionaries (e.g. `{'name': 'write_file'}`) and Tool instances.
+        Supports both dictionaries (e.g. `{'name': 'concierge_commit'}`) and Tool instances.
         """
         current_state = self.get_session_state(session_id)
         rules = self.TOOL_DISCLOSURE_MATRIX.get(
diff --git a/tests/test_governor_wiring.py b/tests/test_governor_wiring.py
index 0f336ff..82b7d89 100644
--- a/tests/test_governor_wiring.py
+++ b/tests/test_governor_wiring.py
@@ -1,57 +1,107 @@
 """tests/test_governor_wiring.py
 
-Testes da Rodada 4.2: Desacoplamento do MCPToolGovernor da telemetria e corte da cadeia de imports.
-Verifica:
-- T1: import interface.mcp_server nao arrasta agents nem action_hooks
-- T2: construcao de GrafoConciergeServer nao arrasta telemetry_api nem fastapi
-- T3: governor do servidor e identico ao exportado por telemetry_api (regressao)
-- T4: governor usa o singleton compartilhado mesmo se telemetry_api falhar no import
-- T5: interface.ActionHooks continua acessivel via export lazy (PEP 562)
+Testes de fiação e isolamento do MCPToolGovernor no GrafoConciergeServer:
+- T1: import de interface.mcp_server mantém governor preguiçoso (None), não carrega
+      core.mcp_governor e não arrasta módulos arquivados ou frameworks web externos
+- T2: construção de GrafoConciergeServer não arrasta archive/nem frameworks web externos,
+      conecta ao singleton compartilhado get_shared_governor() e expõe catálogo limpo (31 == 31)
+- T4: governador usa o singleton compartilhado mesmo se telemetry_api falhar no import
+- T5: governed_list_tools filtra ferramentas FastMCP reais por session_id explícito não-"default"
 """
-import os
+import asyncio
+from pathlib import Path
 import subprocess
 import sys
 from unittest.mock import MagicMock
-import pytest
 
 from storage.store import SqliteStore
 from interface.mcp_server import GrafoConciergeServer
 
 
+REPO_ROOT = Path(__file__).resolve().parent.parent
+
+
 def test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks():
-    """T1: Subprocesso limpo afirmando que 'agents.revisor_critico', 'agents' e 'interface.action_hooks' NÃO estão em sys.modules."""
+    """T1: Subprocesso limpo afirmando governor preguiçoso e ausência de módulos arquivados/frameworks externos no import."""
     code = (
         "import sys\n"
+        "from pathlib import Path\n"
+        f"archive_dir = Path({repr(str((REPO_ROOT / 'archive').resolve()))})\n"
         "import interface.mcp_server\n"
-        "dragged = [m for m in ('agents.revisor_critico', 'agents', 'interface.action_hooks') if m in sys.modules]\n"
-        "if dragged:\n"
-        "    print('DRAGGED:', dragged)\n"
+        "assert interface.mcp_server.governor is None, 'governor deveria permanecer None no import'\n"
+        "assert 'core.mcp_governor' not in sys.modules, 'core.mcp_governor nao deveria carregar no import'\n"
+        "banned_names = ('agents.revisor_critico', 'agents', 'agent', 'interface.action_hooks', 'interface.telemetry_api', 'fastapi', 'flask', 'django')\n"
+        "dragged = [m for m in banned_names if m in sys.modules]\n"
+        "archive_mods = []\n"
+        "for name, mod in list(sys.modules.items()):\n"
+        "    if name == 'archive' or name.startswith('archive.'):\n"
+        "        archive_mods.append(name)\n"
+        "        continue\n"
+        "    mod_file = getattr(mod, '__file__', None)\n"
+        "    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n"
+        "        archive_mods.append(f'{name}:{mod_file}')\n"
+        "if dragged or archive_mods:\n"
+        "    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n"
         "    sys.exit(1)\n"
     )
-    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
-    assert res.returncode == 0, f"Módulos arrastados indevidamente no import de interface.mcp_server: {res.stdout.strip()} {res.stderr.strip()}"
+    res = subprocess.run(
+        [sys.executable, "-c", code],
+        cwd=str(REPO_ROOT),
+        capture_output=True,
+        text=True,
+    )
+    assert res.returncode == 0, f"Falha na guarda de import T1: {res.stdout.strip()} {res.stderr.strip()}"
 
 
 def test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi(tmp_path):
-    """T2: Subprocesso limpo construindo GrafoConciergeServer afirmando que 'interface.telemetry_api' e 'fastapi' NÃO estão em sys.modules."""
+    """T2: Subprocesso limpo construindo GrafoConciergeServer afirmando isolamento, singleton real e catálogo limpo."""
     db_file = str(tmp_path / "test_wire.db")
     code = (
         "import sys\n"
+        "from pathlib import Path\n"
         "from unittest.mock import MagicMock\n"
+        "import core.mcp_governor\n"
         "from storage.store import SqliteStore\n"
+        "import interface.mcp_server\n"
         "from interface.mcp_server import GrafoConciergeServer\n"
-        f"store = SqliteStore(r'{db_file}')\n"
-        "gc = MagicMock()\n"
-        "gc._store = store\n"
-        "server = GrafoConciergeServer(concierge=gc)\n"
-        "store.close()\n"
-        "dragged = [m for m in ('interface.telemetry_api', 'fastapi') if m in sys.modules]\n"
-        "if dragged:\n"
-        "    print('DRAGGED:', dragged)\n"
+        f"archive_dir = Path({repr(str((REPO_ROOT / 'archive').resolve()))})\n"
+        f"store = SqliteStore({repr(db_file)})\n"
+        "try:\n"
+        "    gc = MagicMock()\n"
+        "    gc._store = store\n"
+        "    server = GrafoConciergeServer(concierge=gc)\n"
+        "    shared_gov = core.mcp_governor.get_shared_governor()\n"
+        "    assert server._governor is shared_gov\n"
+        "    assert server.governor is server._governor\n"
+        "    assert interface.mcp_server.governor is server._governor\n"
+        "    registered = set(server.mcp._tool_manager._tools.keys())\n"
+        "    classified = set(server._governor.TOOL_CLASSIFICATION.keys())\n"
+        "    assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'\n"
+        "    assert len(registered) == 31\n"
+        "    assert all(r['allowed_tools'] == [] for r in server._governor.TOOL_DISCLOSURE_MATRIX.values())\n"
+        "finally:\n"
+        "    store.close()\n"
+        "banned_names = ('interface.telemetry_api', 'interface.action_hooks', 'agents', 'agent', 'fastapi', 'flask', 'django')\n"
+        "dragged = [m for m in banned_names if m in sys.modules]\n"
+        "archive_mods = []\n"
+        "for name, mod in list(sys.modules.items()):\n"
+        "    if name == 'archive' or name.startswith('archive.'):\n"
+        "        archive_mods.append(name)\n"
+        "        continue\n"
+        "    mod_file = getattr(mod, '__file__', None)\n"
+        "    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n"
+        "        archive_mods.append(f'{name}:{mod_file}')\n"
+        "if dragged or archive_mods:\n"
+        "    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n"
         "    sys.exit(1)\n"
     )
-    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
-    assert res.returncode == 0, f"Módulos arrastados na construção de GrafoConciergeServer: {res.stdout.strip()} {res.stderr.strip()}"
+    res = subprocess.run(
+        [sys.executable, "-c", code],
+        cwd=str(REPO_ROOT),
+        capture_output=True,
+        text=True,
+    )
+    assert res.returncode == 0, f"Falha na guarda de construção T2: {res.stdout.strip()} {res.stderr.strip()}"
 
 
 def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path, monkeypatch):
@@ -61,6 +111,7 @@ def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path,
     monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
     monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
     monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
+    monkeypatch.setattr("core.mcp_governor._shared_governor", None)
 
     import core.mcp_governor
     assert hasattr(core.mcp_governor, "get_shared_governor"), "core.mcp_governor deve expor get_shared_governor()"
@@ -71,9 +122,58 @@ def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path,
 
     db_file = str(tmp_path / "test_t4.db")
     store = SqliteStore(db_file)
-    gc = MagicMock()
-    gc._store = store
-    server = GrafoConciergeServer(concierge=gc)
+    try:
+        gc = MagicMock()
+        gc._store = store
+        server = GrafoConciergeServer(concierge=gc)
+
+        assert server._governor is shared_gov, "Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar"
+    finally:
+        store.close()
+
+
+def test_t5_governed_list_tools_filters_by_explicit_session_id(tmp_path, monkeypatch):
+    """T5: governed_list_tools aplica filter_tools sobre Tool reais do FastMCP por session_id explícito."""
+    monkeypatch.setattr("interface.mcp_server.governor", None)
+    monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
+    monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
+    monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
+    monkeypatch.setattr("core.mcp_governor._shared_governor", None)
+
+    db_file = str(tmp_path / "test_t5_list.db")
+    store = SqliteStore(db_file)
+    try:
+        gc = MagicMock()
+        gc._store = store
+        server = GrafoConciergeServer(concierge=gc)
+
+        # Sem session_id explícito -> todas as 31 ferramentas registradas
+        unscoped = asyncio.run(server.mcp.list_tools())
+        assert len(unscoped) == 31
+
+        # Sessão explícita não-"default" mantendo "default" intocado
+        sid = "sess_wiring_list"
+        assert "default" not in server.governor.sessions_state
+
+        server.governor.set_session_state(sid, "PLANNING")
+        planning_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
+        assert len(planning_names) == 18
+        assert "get_full_topology" in planning_names
+        assert "concierge_commit" not in planning_names
+        assert "delete_project" not in planning_names
+        assert "reset_collection" not in planning_names
+
+        server.governor.set_session_state(sid, "EXECUTION")
+        exec_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
+        assert len(exec_names) == 29
+        assert "concierge_commit" in exec_names
+        assert "delete_project" not in exec_names
+        assert "reset_collection" not in exec_names
 
-    assert server._governor is shared_gov, "Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar"
-    store.close()
+        server.governor.set_session_state(sid, "MAINTENANCE")
+        maint_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
+        assert len(maint_names) == 31
+        assert {"delete_project", "reset_collection"}.issubset(maint_names)
+        assert "default" not in server.governor.sessions_state
+    finally:
+        store.close()
diff --git a/tests/test_interface_contracts.py b/tests/test_interface_contracts.py
index 7201034..775168a 100644
--- a/tests/test_interface_contracts.py
+++ b/tests/test_interface_contracts.py
@@ -77,12 +77,16 @@ class _MockIngestionManager:
 @pytest.fixture(scope="module")
 def server(tmp_path_factory):
     """GrafoConciergeServer backed by an in-memory-like temp SQLite store."""
+    import core.mcp_governor as _gov_mod
     import interface.mcp_server as _mcp_mod
     orig_db = getattr(_mcp_mod, "db_manager", None)
     orig_cp = getattr(_mcp_mod, "checkpointer", None)
     orig_gr = getattr(_mcp_mod, "graph_rag", None)
     orig_gc = getattr(_mcp_mod, "_gc", None)
     orig_gov = getattr(_mcp_mod, "governor", None)
+    orig_shared_gov = getattr(_gov_mod, "_shared_governor", None)
+
+    _gov_mod._shared_governor = None
 
     tmp = tmp_path_factory.mktemp("interface_contracts")
     store = SqliteStore(str(tmp / "contract.db"))
@@ -104,6 +108,7 @@ def server(tmp_path_factory):
     _mcp_mod.graph_rag = orig_gr
     _mcp_mod._gc = orig_gc
     _mcp_mod.governor = orig_gov
+    _gov_mod._shared_governor = orig_shared_gov
 
 
 # ---------------------------------------------------------------------------
@@ -230,11 +235,47 @@ class TestMCPToolRegistration:
 
     def test_all_registered_tools_classified_in_governor(self, server):
         registered = set(server.mcp._tool_manager._tools.keys())
-        # Note: TOOL_CLASSIFICATION still holds 10 legacy/phantom entries until 4.5g cleanup,
-        # so 4.5c asserts registered ⊆ TOOL_CLASSIFICATION.
         classified = set(server.governor.TOOL_CLASSIFICATION.keys())
         unclassified = sorted(registered - classified)
+        phantom = sorted(classified - registered)
         assert not unclassified, f"Registered tools missing from TOOL_CLASSIFICATION: {unclassified}"
+        assert not phantom, f"Phantom tools in TOOL_CLASSIFICATION not registered on server: {phantom}"
+        assert classified == registered
+
+    def test_governor_disclosure_matrix_clean_and_valid(self, server):
+        expected_states = {
+            "PLANNING",
+            "DISCOVERY",
+            "EXECUTION",
+            "TDD_GREEN",
+            "REFACTORING",
+            "MAINTENANCE",
+            "STALL",
+            "SUCCESS",
+        }
+        assert set(server.governor.TOOL_DISCLOSURE_MATRIX.keys()) == expected_states
+        classified = set(server.governor.TOOL_CLASSIFICATION.keys())
+        valid_categories = {"READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"}
+        for state_name, rules in server.governor.TOOL_DISCLOSURE_MATRIX.items():
+            assert "allowed_tools" in rules, f"State '{state_name}' missing allowed_tools"
+            allowed_tools = rules["allowed_tools"]
+            assert allowed_tools == [], (
+                f"State '{state_name}' has unexpected allowed_tools override: {allowed_tools}"
+            )
+            assert set(allowed_tools).issubset(classified), (
+                f"State '{state_name}' references unclassified tools: {sorted(set(allowed_tools) - classified)}"
+            )
+            assert set(rules["allowed_categories"]).issubset(valid_categories)
+
+    def test_governor_destructive_tools_classified_as_dangerous(self, server):
+        assert server.governor.TOOL_CLASSIFICATION["delete_project"] == "DANGEROUS"
+        assert server.governor.TOOL_CLASSIFICATION["reset_collection"] == "DANGEROUS"
+        dangerous = {
+            name
+            for name, cat in server.governor.TOOL_CLASSIFICATION.items()
+            if cat == "DANGEROUS"
+        }
+        assert dangerous == {"delete_project", "reset_collection"}
 
     def test_governed_call_tool_executes_and_enforces_state(self, server, monkeypatch):
         import interface.mcp_server as _mcp_mod
@@ -252,8 +293,9 @@ class TestMCPToolRegistration:
 
         # 1. Governance enforcement: PLANNING blocks LOCAL_MUTATION tools via governed_call_tool
         # Note: governed_call_tool checks default session when session_id is not a tool param,
-        # so set PLANNING on "default" to verify real call_tool interception cleanly.
-        orig_default = server.governor.get_session_state("default")
+        # so restore sessions_state["default"] without leaking an injected key.
+        had_default = "default" in server.governor.sessions_state
+        orig_default = server.governor.sessions_state.get("default")
         try:
             server.governor.set_session_state("default", "PLANNING")
             with pytest.raises(SecurityException):
@@ -410,7 +452,10 @@ class TestMCPToolRegistration:
             assert isinstance(list_cp_res, list)
             assert len(list_cp_res) >= 1
         finally:
-            server.governor.set_session_state("default", orig_default)
+            if had_default:
+                server.governor.sessions_state["default"] = orig_default
+            else:
+                server.governor.sessions_state.pop("default", None)
 
     def test_server_name_is_grafo_concierge(self, server):
         assert server.mcp.name == "Grafo Concierge"
diff --git a/tests/test_mcp_governor.py b/tests/test_mcp_governor.py
index a00c8b9..d428347 100644
--- a/tests/test_mcp_governor.py
+++ b/tests/test_mcp_governor.py
@@ -1,10 +1,12 @@
 """
 tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21).
 
-Copiado de tests/test_progressive_tool_disclosure.py (sem TestClient / interface.telemetry_api)
-para manter a cobertura viva do governador independente dos módulos dormentes.
+Valida o catálogo vivo das 31 ferramentas MCP sem depender de mocks fantasmas
+ou módulos em quarentena, cobrindo camadas passiva (`filter_tools`) e ativa
+(`validate_tool_execution`) além da garantia fail-closed.
 """
 
+from types import SimpleNamespace
 import unittest
 
 from core.mcp_governor import MCPToolGovernor, SecurityException
@@ -14,61 +16,151 @@ class TestMCPToolGovernor(unittest.TestCase):
     def setUp(self):
         self.governor = MCPToolGovernor(default_state="PLANNING")
 
-        # Mock de ferramentas registradas no FastMCP (inclui mocks legados até limpeza 4.5g)
-        self.mock_tools = [
+        # Ferramentas vivas registradas no FastMCP cobrindo todas as 3 categorias
+        # (incluindo ambas as ferramentas DANGEROUS vivas)
+        self.live_tools = [
             {"name": "get_full_topology", "description": "Lê topologia"},
-            {"name": "write_file", "description": "Escreve arquivos"},
-            {"name": "execute_command", "description": "Executa comandos"},
-            {"name": "get_telemetry_snapshot", "description": "Snap de telemetria"},
+            {"name": "concierge_search", "description": "Busca híbrida"},
+            {"name": "concierge_commit", "description": "Registra commit"},
+            {"name": "delete_project", "description": "Remove projeto"},
+            {"name": "reset_collection", "description": "Reseta coleção vetorial"},
         ]
 
+    def test_classification_partition_and_clean_disclosure_matrix(self):
+        """Valida partição exata 18/11/2 (31 tools) e allowed_tools vazio nos 8 estados."""
+        counts = {"READ_ONLY": 0, "LOCAL_MUTATION": 0, "DANGEROUS": 0}
+        for tool_name, category in self.governor.TOOL_CLASSIFICATION.items():
+            self.assertIn(category, counts, f"Categoria inesperada em {tool_name}: {category}")
+            counts[category] += 1
+
+        self.assertEqual(len(self.governor.TOOL_CLASSIFICATION), 31)
+        self.assertEqual(counts, {"READ_ONLY": 18, "LOCAL_MUTATION": 11, "DANGEROUS": 2})
+
+        expected_states = {
+            "PLANNING",
+            "DISCOVERY",
+            "EXECUTION",
+            "TDD_GREEN",
+            "REFACTORING",
+            "MAINTENANCE",
+            "STALL",
+            "SUCCESS",
+        }
+        self.assertEqual(set(self.governor.TOOL_DISCLOSURE_MATRIX.keys()), expected_states)
+        for state_name, rules in self.governor.TOOL_DISCLOSURE_MATRIX.items():
+            self.assertEqual(
+                rules["allowed_tools"],
+                [],
+                f"Estado '{state_name}' deveria ter allowed_tools vazio",
+            )
+
     def test_should_filter_tools_in_planning_state(self):
-        """Valida que apenas ferramentas de leitura e telemetria passam no estágio de planejamento"""
+        """Valida que apenas ferramentas READ_ONLY passam em PLANNING."""
         self.governor.set_session_state("session_123", "PLANNING")
 
-        filtered = self.governor.filter_tools("session_123", self.mock_tools)
+        filtered = self.governor.filter_tools("session_123", self.live_tools)
         tool_names = {t["name"] for t in filtered}
 
-        # get_full_topology (READ_ONLY) e get_telemetry_snapshot (allowed_tools) devem passar
-        self.assertIn("get_full_topology", tool_names)
-        self.assertIn("get_telemetry_snapshot", tool_names)
+        self.assertEqual(tool_names, {"get_full_topology", "concierge_search"})
+        self.assertNotIn("concierge_commit", tool_names)
+        self.assertNotIn("delete_project", tool_names)
+        self.assertNotIn("reset_collection", tool_names)
 
-        # write_file (LOCAL_MUTATION) e execute_command (DANGEROUS) devem ser ocultadas
-        self.assertNotIn("write_file", tool_names)
-        self.assertNotIn("execute_command", tool_names)
+        # Também exercita objetos com atributo `.name` (ex.: Tool do FastMCP)
+        attr_tools = [SimpleNamespace(name=t["name"]) for t in self.live_tools]
+        filtered_attr = {t.name for t in self.governor.filter_tools("session_123", attr_tools)}
+        self.assertEqual(filtered_attr, {"get_full_topology", "concierge_search"})
 
     def test_should_disclose_mutation_tools_in_execution_state(self):
-        """Valida que ferramentas de escrita física são expostas na transição para EXECUTION"""
+        """Valida que LOCAL_MUTATION é exposta em EXECUTION, mas DANGEROUS segue oculta."""
         self.governor.set_session_state("session_123", "EXECUTION")
 
-        filtered = self.governor.filter_tools("session_123", self.mock_tools)
+        filtered = self.governor.filter_tools("session_123", self.live_tools)
         tool_names = {t["name"] for t in filtered}
 
-        self.assertIn("get_full_topology", tool_names)
-        self.assertIn("write_file", tool_names)  # Desbloqueado!
-        self.assertIn("get_telemetry_snapshot", tool_names)
-
-        # execute_command (DANGEROUS) continua restrito
-        self.assertNotIn("execute_command", tool_names)
+        self.assertEqual(tool_names, {"get_full_topology", "concierge_search", "concierge_commit"})
+        self.assertNotIn("delete_project", tool_names)
+        self.assertNotIn("reset_collection", tool_names)
 
     def test_should_disclose_all_tools_in_maintenance_state(self):
-        """Valida que no modo de manutenção total e administrativa do monorepo todos os comandos são expostos"""
+        """Valida que MAINTENANCE expõe READ_ONLY, LOCAL_MUTATION e ambas as DANGEROUS."""
         self.governor.set_session_state("session_123", "MAINTENANCE")
 
-        filtered = self.governor.filter_tools("session_123", self.mock_tools)
-        self.assertEqual(len(filtered), 4)
+        filtered = self.governor.filter_tools("session_123", self.live_tools)
+        tool_names = {t["name"] for t in filtered}
+        self.assertEqual(
+            tool_names,
+            {
+                "get_full_topology",
+                "concierge_search",
+                "concierge_commit",
+                "delete_project",
+                "reset_collection",
+            },
+        )
 
     def test_should_raise_security_exception_on_direct_call_attempt(self):
-        """Valida que tentar injetar comandos ocultados via chamada de API direta lança erro ativo"""
+        """Valida barreira ativa em validate_tool_execution para PLANNING, EXECUTION e MAINTENANCE."""
         self.governor.set_session_state("session_999", "PLANNING")
+        self.assertTrue(self.governor.validate_tool_execution("session_999", "get_full_topology"))
+        for blocked in ("concierge_commit", "delete_project", "reset_collection"):
+            with self.assertRaises(SecurityException):
+                self.governor.validate_tool_execution("session_999", blocked)
+
+        self.governor.set_session_state("session_999", "EXECUTION")
+        self.assertTrue(self.governor.validate_tool_execution("session_999", "concierge_commit"))
+        for dangerous in ("delete_project", "reset_collection"):
+            with self.assertRaises(SecurityException):
+                self.governor.validate_tool_execution("session_999", dangerous)
+
+        self.governor.set_session_state("session_999", "MAINTENANCE")
+        self.assertTrue(self.governor.validate_tool_execution("session_999", "delete_project"))
+        self.assertTrue(self.governor.validate_tool_execution("session_999", "reset_collection"))
+
+    def test_unknown_and_removed_tools_filtered_out_fail_closed(self):
+        """Camada passiva (filter_tools): desconhecidas e fantasmas removidas são ocultadas em PLANNING e EXECUTION."""
+        candidates = [
+            {"name": "get_full_topology"},
+            {"name": "concierge_commit"},
+            {"name": "unclassified_unknown_tool"},
+            {"name": "write_file"},
+        ]
 
-        # Tentativa de chamada de leitura: OK
-        allowed = self.governor.validate_tool_execution("session_999", "get_full_topology")
-        self.assertTrue(allowed)
-
-        # Tentativa de chamada de modificação: Deve estourar exceção de segurança ativa
-        with self.assertRaises(SecurityException):
-            self.governor.validate_tool_execution("session_999", "write_file")
+        self.governor.set_session_state("sess_fc_filter", "PLANNING")
+        planning_names = {t["name"] for t in self.governor.filter_tools("sess_fc_filter", candidates)}
+        self.assertEqual(planning_names, {"get_full_topology"})
+        self.assertNotIn("unclassified_unknown_tool", planning_names)
+        self.assertNotIn("write_file", planning_names)
+
+        self.governor.set_session_state("sess_fc_filter", "EXECUTION")
+        exec_names = {t["name"] for t in self.governor.filter_tools("sess_fc_filter", candidates)}
+        self.assertEqual(exec_names, {"get_full_topology", "concierge_commit"})
+        self.assertNotIn("unclassified_unknown_tool", exec_names)
+        self.assertNotIn("write_file", exec_names)
+
+    def test_unknown_and_removed_tools_blocked_in_execution_and_planning(self):
+        """Camada ativa (validate_tool_execution): desconhecidas e fantasmas caem em DANGEROUS (fail-closed)."""
+        for state in ("PLANNING", "EXECUTION"):
+            self.governor.set_session_state("sess_fc_exec", state)
+            for tool_name in ("unclassified_unknown_tool", "write_file"):
+                with self.assertRaises(SecurityException) as ctx:
+                    self.governor.validate_tool_execution("sess_fc_exec", tool_name)
+                self.assertIn("DANGEROUS", str(ctx.exception))
+
+    def test_session_state_normalization_invalid_preservation_and_isolation(self):
+        """Valida normalização case-insensitive, rejeição segura de estado inválido e isolamento entre sessões."""
+        self.governor.set_session_state("sess_a", "execution")
+        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")
+
+        # Estado desconhecido preserva estado anterior sem sobrescrever
+        self.governor.set_session_state("sess_a", "INVALID_STATE")
+        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")
+
+        # Sessão B mantém seu próprio estado (e default_state sem poluição cruzada)
+        self.assertEqual(self.governor.get_session_state("sess_b"), "PLANNING")
+        self.governor.set_session_state("sess_b", "MAINTENANCE")
+        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")
+        self.assertEqual(self.governor.get_session_state("sess_b"), "MAINTENANCE")
 
 
 if __name__ == "__main__":
```


---

## 4. Evidências de C2 — Dependências, `.dockerignore` e `Dockerfile`


### 4.1 Auditoria de Imports em Módulos Vivos (`c2_deps_audit.txt`)


```text
================================================================
C2 DEPENDENCY AUDIT — 32 arquivos Python vivos inspecionados
================================================================

OK: NENHUM modulo vivo importa os 9 pacotes candidatos a remocao.

Pacotes removidos de [project].dependencies:
  - fastapi (import: fastapi): livre (0 imports)
  - watchdog (import: watchdog): livre (0 imports)
  - pathspec (import: pathspec): livre (0 imports)
  - psutil (import: psutil): livre (0 imports)
  - uvicorn (import: uvicorn): livre (0 imports)
  - sse-starlette (import: sse_starlette): livre (0 imports)
  - httpx (import: httpx): livre (0 imports)
  - pydantic (import: pydantic): livre (0 imports)
  - tenacity (import: tenacity): livre (0 imports)

Pacotes movidos para [project.optional-dependencies].dev:
  - rich (import: rich): 0 imports -> []
```


### 4.2 Verificação de `.dockerignore` (`c2_dockerignore_check.txt`)


```text
================================================================
C2 .dockerignore CHECK
================================================================

[1] Verificacao MUST_INCLUDE:
  README.md                                     -> OK
  LICENSE                                       -> OK
  pyproject.toml                                -> OK
  requirements.txt                              -> OK
  main.py                                       -> OK
  Dockerfile                                    -> OK
  core/__init__.py                              -> OK
  core/mcp_governor.py                          -> OK
  core/database.py                              -> OK
  storage/schema.py                             -> OK
  storage/store.py                              -> OK
  ingestion/orchestrator.py                     -> OK
  services/janitor.py                           -> OK
  interface/mcp_server.py                       -> OK
  interface/cli.py                              -> OK
  scripts/bootstrap_core_memory.py              -> OK

[2] Verificacao MUST_EXCLUDE:
  .git/HEAD                                     -> OK (excluded)
  .github/workflows/ci.yml                      -> OK (excluded)
  .venv_313/Scripts/python.exe                  -> OK (excluded)
  archive/README.md                             -> OK (excluded)
  archive/v4-experimental/core/rate_governor.py -> OK (excluded)
  audits/fase4-decisoes.md                      -> OK (excluded)
  scratch/c2_deps_audit.py                      -> OK (excluded)
  tests/test_mcp_governor.py                    -> OK (excluded)
  docs-grafo-concierge/README.md                -> OK (excluded)
  grafo-dashboard-web/package.json              -> OK (excluded)
  agent/__pycache__/foo.pyc                     -> OK (excluded)
  agents/__pycache__/foo.pyc                    -> OK (excluded)
  core/parsers/__pycache__/foo.pyc              -> OK (excluded)
  data/grafo.db                                 -> OK (excluded)
  sub/test.sqlite3                              -> OK (excluded)
  .env                                          -> OK (excluded)
  .env.example                                  -> OK (excluded)
  CHANGELOG.md                                  -> OK (excluded)
  CONTRIBUTING.md                               -> OK (excluded)
  docker-compose.yml                            -> OK (excluded)
  .dockerignore                                 -> OK (excluded)
  core/__pycache__/mcp_governor.cpython-313.pyc -> OK (excluded)
  core/foo.pyc                                  -> OK (excluded)

[3] Varredura real dos 6 pacotes vivos (nenhum .py vivo ignorado):
  Total .py vivos nos 6 pacotes: 31
  Ignorados indevidamente: 0 -> []

[4] Simulacao de contexto real no disco (contagem de entradas top-level):
  Top-level INCLUIDOS (12): ['Dockerfile', 'LICENSE', 'README.md', 'core', 'ingestion', 'interface', 'main.py', 'pyproject.toml', 'requirements.txt', 'scripts', 'services', 'storage']
  Top-level EXCLUIDOS (38): ['.agents', '.conciergeignore', '.conciergeignore.example', '.coverage', '.dockerignore', '.env', '.env.example', '.git', '.gitattributes', '.github', '.gitignore', '.mypy_cache', '.pytest_cache', '.venv_310', '.venv_311', '.venv_312', '.venv_313', '.venv_clean', 'ACTIVE_SDD.md', 'AGENTS.md', 'ATTRIBUTION_AND_LINEAGE.md', 'AUDIT_PROTOCOL.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'README.pt-BR.md', '__pycache__', '_stress_test_v2_workspace', 'agent', 'agents', 'archive', 'audits', 'data', 'docker-compose.yml', 'docs-grafo-concierge', 'grafo-dashboard-web', 'scratch', 'tests', 'walkthrough.md']

RESULTADO: OK (0 erros)
```


### 4.3 Smoke Install em Venv 100% Limpo Fora do Repositório (`c2_smoke_install.txt`)


```text
================================================================
C2 SMOKE INSTALL (VENV LIMPO FORA DO REPO)
================================================================
Repo: C:\Nexus-Memory\GrafoConcierge
Temp dir: C:\Users\guial\AppData\Local\Temp\gc_c2_smoke_7g2qi6xm
Base Python: C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\python.exe
uv executable: None
[1] python -m venv criado com sucesso.
[2] pip install . (sem [dev]) concluido com sucesso.
[3] concierge --help exit=0
    head: usage: grafo-concierge [-h]
[4] concierge-mcp.exe exists=True (C:\Users\guial\AppData\Local\Temp\gc_c2_smoke_7g2qi6xm\venv\Scripts\concierge-mcp.exe)
[5] Probe Python exit=0
  [5a] entry_points OK: concierge -> interface.cli:main, concierge-mcp -> main:main
  [5b] fastapi: PackageNotFoundError (OK)
  [5b] watchdog: PackageNotFoundError (OK)
  [5b] pathspec: PackageNotFoundError (OK)
  [5b] psutil: PackageNotFoundError (OK)
  [5c] chromadb==1.5.9 (OK)
  [5c] mcp==1.30.0 (OK)
  [5c] sentence-transformers==6.3.0 (OK)
  [5c] python-dotenv==1.2.4 (OK)
  [5c] starlette==1.10.0 (OK)
  [5d] imports vivos + scripts.bootstrap_core_memory (PEP 420) OK
  [5e] GrafoConciergeServer tools count=31
  [5f] server.mcp.sse_app() -> Starlette OK
STDERR: [11/24/26 23:15:47] INFO     GrafoConciergeServer initialized mcp_server.py:230
                             — 31 tools registered.

RESULTADO SMOKE INSTALL: OK
```


### 4.4 `git diff` Integral de C2 (`c2_diff.txt`)


```diff
diff --git a/.dockerignore b/.dockerignore
new file mode 100644
index 0000000..e8483e6
--- /dev/null
+++ b/.dockerignore
@@ -0,0 +1,59 @@
+.git/
+.github/
+.gitignore
+.gitattributes
+.venv*/
+venv/
+env/
+.uv/
+__pycache__/
+**/__pycache__/
+**/*.py[cod]
+**/*$py.class
+.pytest_cache/
+.mypy_cache/
+.coverage
+htmlcov/
+build/
+dist/
+*.egg-info/
+archive/
+audits/
+scratch/
+tests/
+docs-grafo-concierge/
+grafo-dashboard-web/
+node_modules/
+agent/
+agents/
+core/parsers/
+_stress_test_*
+_colossus_workspace/
+_test_*_tmp/
+data/
+chroma/
+chroma_db/
+.qdrant/
+**/*.db*
+**/*.sqlite*
+*.log
+logs/
+.env
+.env.*
+.conciergeignore*
+*.pem
+*.key
+*.cert
+*.crt
+*.md
+!README.md
+*.txt
+!requirements.txt
+.vscode/
+.idea/
+.agents/
+.reversa/
+_reversa_sdd/
+.claude/
+docker-compose.yml
+.dockerignore
diff --git a/Dockerfile b/Dockerfile
index e27656f..45e857a 100644
--- a/Dockerfile
+++ b/Dockerfile
@@ -7,13 +7,15 @@ RUN apt-get update && apt-get install -y --no-install-recommends \
     build-essential \
     && rm -rf /var/lib/apt/lists/*
 
-COPY pyproject.toml requirements.txt ./
+COPY requirements.txt ./
 
 RUN python -m venv /opt/venv
 ENV PATH="/opt/venv/bin:$PATH"
 RUN pip install --no-cache-dir --upgrade pip && \
-    pip install --no-cache-dir -r requirements.txt && \
-    pip install --no-cache-dir -e .
+    pip install --no-cache-dir -r requirements.txt
+
+COPY . .
+RUN pip install --no-cache-dir -e .
 
 # Final runtime image
 FROM python:3.12-slim
diff --git a/pyproject.toml b/pyproject.toml
index 435f1e7..70b7ca0 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -40,16 +40,6 @@ dependencies = [
     "sentence-transformers>=3.0",
     "python-dotenv>=1.0",
     "starlette>=0.36",
-    "sse-starlette>=2.0",
-    "uvicorn>=0.25",
-    "fastapi>=0.100.0",
-    "httpx>=0.25",
-    "pydantic>=2.0",
-    "rich>=13.0",
-    "tenacity>=8.0",
-    "pathspec>=0.11",
-    "watchdog>=4.0",
-    "psutil>=5.9.0",
 ]
 
 [project.optional-dependencies]
@@ -60,6 +50,7 @@ dev = [
     "pytest-timeout>=2.2.0",
     "flake8>=6.0",
     "mypy>=1.0",
+    "rich>=13.0",
     "qdrant-client>=1.7",
     "google-genai>=0.1.0",
     "openai>=1.0",
@@ -71,9 +62,9 @@ all = [
 ]
 
 [project.urls]
-Homepage = "https://github.com/LuisinTheLegend/GrafoConcierge"
-Repository = "https://github.com/LuisinTheLegend/GrafoConcierge"
-Issues = "https://github.com/LuisinTheLegend/GrafoConcierge/issues"
+Homepage = "https://github.com/LuisinTheLegend/ConciergeGraph"
+Repository = "https://github.com/LuisinTheLegend/ConciergeGraph"
+Issues = "https://github.com/LuisinTheLegend/ConciergeGraph/issues"
 
 # ──────────────────────────────────────────────────────────────
 # CLI Entry Points — Global Terminal Commands
diff --git a/requirements.txt b/requirements.txt
index 51d0eea..34f5381 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -6,16 +6,6 @@ mcp>=1.27,<2
 sentence-transformers>=3.0.0
 python-dotenv>=1.0.0
 starlette>=0.36.0
-sse-starlette>=2.0.0
-uvicorn>=0.25.0
-fastapi>=0.100.0
-httpx>=0.25.0
-pydantic>=2.0.0
-rich>=13.0.0
-tenacity>=8.0.0
-pathspec>=0.11.0
-watchdog>=4.0.0
-psutil>=5.9.0
 
 # LLM Providers (Google GenAI & OpenAI)
 google-genai>=0.1.0
@@ -28,3 +18,4 @@ qdrant-client>=1.7.0
 pytest>=7.0.0
 flake8>=6.0.0
 mypy>=1.0.0
+rich>=13.0.0
```


---

## 5. Evidências de C3 — Documentação Viva, Suíte Final e Caminhos Proibidos


### 5.1 Varredura de Termos Quarentenados nos Documentos Vivos (`c3_doc_scan.txt`)


```text
====================================================================
C3 DOC SCAN — Varredura de termos quarentenados e metadados obsoletos
====================================================================
  README.md                           -> 0 hits
  README.pt-BR.md                     -> 0 hits
  CONTRIBUTING.md                     -> 0 hits
  docs-grafo-concierge/README.md      -> 0 hits
  pyproject.toml                      -> 0 hits
  .env.example                        -> 0 hits

RESULTADO: OK (0 hits em 6 arquivos, 51 padroes verificados)
```


### 5.2 Suíte Completa Final — Normal e `--reverse` (`c3_suite.txt`)


```text
=== PYTEST NORMAL (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
...............................................                          [100%]
============================== warnings summary ===============================
tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-311
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-313
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-330
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated
  !!
  
          ********************************************************************************
          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).
  
          By 2027-Feb-18, you need to update your project and remove deprecated calls
          or your builds will no longer be supported.
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    corresp(dist, value, root_dir)

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.
  !!
  
          ********************************************************************************
          Please consider removing the following classifiers in favor of a SPDX license expression:
  
          License :: OSI Approved :: MIT License
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    dist._finalize_license_expression()

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.
  !!
  
          ********************************************************************************
          Please consider removing the following classifiers in favor of a SPDX license expression:
  
          License :: OSI Approved :: MIT License
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    self._finalize_license_expression()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
335 passed, 24 warnings in 125.36s (0:02:05)

=== PYTEST REVERSE (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
...............................................                          [100%]
============================== warnings summary ===============================
tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated
  !!
  
          ********************************************************************************
          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).
  
          By 2027-Feb-18, you need to update your project and remove deprecated calls
          or your builds will no longer be supported.
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    corresp(dist, value, root_dir)

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.
  !!
  
          ********************************************************************************
          Please consider removing the following classifiers in favor of a SPDX license expression:
  
          License :: OSI Approved :: MIT License
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    dist._finalize_license_expression()

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.
  !!
  
          ********************************************************************************
          Please consider removing the following classifiers in favor of a SPDX license expression:
  
          License :: OSI Approved :: MIT License
  
          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
          ********************************************************************************
  
  !!
    self._finalize_license_expression()

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-102
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-116
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-121
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_conversational_db.py::test_semantic_facts_bi_temporal
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
335 passed, 24 warnings in 119.63s (0:01:59)
```


### 5.3 Verificação de Diff Zero em Caminhos Proibidos (`c3_prohibited_diff.txt`)


```text
(saída vazia — 0 bytes alterados entre 884de07 e dd5d7ee em todos os caminhos proibidos)
```


### 5.4 Varredura Final de Segredos (`scan_secrets.py`)


```text
scanned_files=1530
files_with_findings=0
total_pattern_hits=0
```


### 5.5 `git status` Final (`final_git_status.txt`)


Confirma que nenhum arquivo excluído pela decisão da `4.5c-bis`, nenhum arquivo de `scratch/` e nenhum diretório não autorizado foi commitado:


```text
## main...origin/main
 M scratch/build_4_5a_bis_docs.py
 M scratch/inv_4_5a_bis_bloco1.py
?? audits/egm/analise-completa-codebase-details.md
?? audits/egm/analise-completa-comprehension.md
?? audits/egm/analise-completa-design.md
?? audits/egm/analise-completa-inventive-catalyst.md
?? audits/egm/analise-completa-sintese.md
?? audits/egm/analise-completa-zoom-out.md
?? grafo-dashboard-web/
?? scratch/c2_deps_audit.py
?? scratch/c2_dockerignore_check.py
?? scratch/c2_smoke.py
?? scratch/c3_doc_scan.py
?? scratch/caracterizacao_sdd20_4_5e.py
?? scratch/chamadores_4_5e.py
?? scratch/chamadores_4_5e_bis.py
?? scratch/check_ci_4_5d.py
?? scratch/check_ci_4_5e.py
?? scratch/check_ci_4_5e_bis.py
?? scratch/check_ci_4_5g.py
?? scratch/coverage_mistos_4_5d.py
?? scratch/evidencia_4_5d/
?? scratch/evidencia_4_5e/
?? scratch/evidencia_4_5e_bis/
?? scratch/evidencia_4_5g/
?? scratch/gate_4_5e.py
?? scratch/gate_4_5e_bis.py
?? scratch/gate_lote_4_5d.py
?? scratch/grafo_importadores_4_5d.py
?? scratch/move_lote_4_5d.py
?? scratch/mutacao_escolha_a_4_5d.py
?? scratch/mutacoes_c1_4_5e.py
?? scratch/mutacoes_c1_4_5e_bis.py
?? scratch/mutacoes_c1_4_5g.py
?? scratch/mutacoes_c2_4_5e.py
?? scratch/mutacoes_c2_4_5e_bis.py
?? scratch/mutacoes_c3_4_5e.py
?? scratch/mutacoes_c3_4_5e_bis.py
?? scratch/preflight_4_5d.py
?? scratch/preflight_4_5e.py
?? scratch/preflight_4_5e_bis.py
?? scratch/preflight_4_5g.py
?? scratch/prompt_4_5b_verbatim.md
?? scratch/repro_4_5e_bis.py
?? scratch/save_swarm_4_5e.py
?? scratch/save_swarm_4_5g.py
?? scratch/trace_funcs_45e.py
?? scratch/trace_funcs_45e_bis.py
?? scratch/verificacoes_finais_4_5d.py
```
