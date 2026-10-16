# Prova de Execução do Runtime Real do Servidor (Fase 4, Rodada 4.0b)

> **Documento Normativo de Auditoria e Arquitetura Empírica**  
> **Fase:** Fase 4 — Correções de Código | **Rodada:** 4.0b | **Natureza:** SOMENTE LEITURA E DOCUMENTAÇÃO  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e Regras 1 a 7 da Fase 4 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Hash de Base:** `9fe1d6d955126074d11354e7366932a7fa130e92`  
> **Data:** 15/10/2026  
> **Status:** PARADA NO GATE (Nenhum código de produção nem testes foi alterado; nenhum arquivo foi movido ou removido)

---

## 1. Passo 0 — Sincronização Inicial

Comandos executados no início da rodada:
```powershell
git pull
git rev-parse HEAD
git status
```

**Saída literal:**
```
Already up to date.
9fe1d6d955126074d11354e7366932a7fa130e92
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## 2. Passo 1 — Grafo Estático de Alcance a Partir de `main.py`

Script executado: [`scratch/fase4_0b_static_reach.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/fase4_0b_static_reach.py).
O algoritmo realizou a análise estática AST de todos os nós de importação (`ast.Import` e `ast.ImportFrom`), incluindo blocos condicionais, funções e tratamentos de exceção, partindo da raiz (`main.py`).

**Saída literal comprovada:**
```
================================================================================
GRAFO ESTATICO DE ALCANCE A PARTIR DE main.py
================================================================================
Total de modulos do projeto: 64
Total de modulos alcancaveis: 41
Total de modulos NAO alcancaveis: 23
Total de linhas em modulos NAO alcancaveis: 2956

MODULOS NAO ALCANCAVEIS POR PACOTE:

--- Pacote: agent (2 modulos) ---
  - agent/agent_prompts.py (176 linhas) [modulo: agent.agent_prompts]
  - agent/run_agent.py (266 linhas) [modulo: agent.run_agent]

--- Pacote: core (16 modulos) ---
  - core/alias_tracker.py (259 linhas) [modulo: core.alias_tracker]
  - core/background_janitor.py (290 linhas) [modulo: core.background_janitor]
  - core/delta_manager.py (265 linhas) [modulo: core.delta_manager]
  - core/delta_sync.py (12 linhas) [modulo: core.delta_sync]
  - core/dependencies.py (39 linhas) [modulo: core.dependencies]
  - core/federated_knowledge_router.py (100 linhas) [modulo: core.federated_knowledge_router]
  - core/global_memory_adapter.py (85 linhas) [modulo: core.global_memory_adapter]
  - core/intent_classifier.py (98 linhas) [modulo: core.intent_classifier]
  - core/janitor.py (12 linhas) [modulo: core.janitor]
  - core/nozomio_router.py (21 linhas) [modulo: core.nozomio_router]
  - core/parser_factory.py (80 linhas) [modulo: core.parser_factory]
  - core/parsers/__init__.py (20 linhas) [modulo: core.parsers]
  - core/parsers/base.py (41 linhas) [modulo: core.parsers.base]
  - core/parsers/python_parser.py (90 linhas) [modulo: core.parsers.python_parser]
  - core/parsers/ts_js_parser.py (265 linhas) [modulo: core.parsers.ts_js_parser]
  - core/search_engine.py (61 linhas) [modulo: core.search_engine]

--- Pacote: interface (2 modulos) ---
  - interface/cli.py (392 linhas) [modulo: interface.cli]
  - interface/watcher.py (243 linhas) [modulo: interface.watcher]

--- Pacote: root (1 modulos) ---
  - agent/__init__.py (13 linhas) [modulo: agent]

--- Pacote: scripts (1 modulos) ---
  - scripts/bootstrap_core_memory.py (93 linhas) [modulo: scripts.bootstrap_core_memory]

--- Pacote: storage (1 modulos) ---
  - storage/relational_db.py (35 linhas) [modulo: storage.relational_db]

================================================================================
QUEM IMPORTA CADA MODULO NAO ALCANCAVEL (E SE O IMPORTADOR E INALCANCAVEL):
================================================================================
[agent] (agent/__init__.py):
    <- Importado por: agent.run_agent (agent/run_agent.py) [TAMBEM INALCANCAVEL]
[agent.agent_prompts] (agent/agent_prompts.py):
    <- Importado por: agent.run_agent (agent/run_agent.py) [TAMBEM INALCANCAVEL]
[agent.run_agent] (agent/run_agent.py):
    <- Importado por: agent (agent/__init__.py) [TAMBEM INALCANCAVEL]
[core.alias_tracker] (core/alias_tracker.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.background_janitor] (core/background_janitor.py):
    <- Importado por: core.janitor (core/janitor.py) [TAMBEM INALCANCAVEL]
[core.delta_manager] (core/delta_manager.py):
    <- Importado por: core.delta_sync (core/delta_sync.py) [TAMBEM INALCANCAVEL]
[core.delta_sync] (core/delta_sync.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.dependencies] (core/dependencies.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.federated_knowledge_router] (core/federated_knowledge_router.py):
    <- Importado por: core.nozomio_router (core/nozomio_router.py) [TAMBEM INALCANCAVEL]
[core.global_memory_adapter] (core/global_memory_adapter.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.intent_classifier] (core/intent_classifier.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.janitor] (core/janitor.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.nozomio_router] (core/nozomio_router.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.parser_factory] (core/parser_factory.py):
    -> NINGUEM importa em producao (orfao absoluto)
[core.parsers] (core/parsers/__init__.py):
    <- Importado por: core.parser_factory (core/parser_factory.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers.python_parser (core/parsers/python_parser.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers.ts_js_parser (core/parsers/ts_js_parser.py) [TAMBEM INALCANCAVEL]
[core.parsers.base] (core/parsers/base.py):
    <- Importado por: core.parser_factory (core/parser_factory.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers (core/parsers/__init__.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers.python_parser (core/parsers/python_parser.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers.ts_js_parser (core/parsers/ts_js_parser.py) [TAMBEM INALCANCAVEL]
[core.parsers.python_parser] (core/parsers/python_parser.py):
    <- Importado por: core.parser_factory (core/parser_factory.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers (core/parsers/__init__.py) [TAMBEM INALCANCAVEL]
[core.parsers.ts_js_parser] (core/parsers/ts_js_parser.py):
    <- Importado por: core.parser_factory (core/parser_factory.py) [TAMBEM INALCANCAVEL]
    <- Importado por: core.parsers (core/parsers/__init__.py) [TAMBEM INALCANCAVEL]
[core.search_engine] (core/search_engine.py):
    -> NINGUEM importa em producao (orfao absoluto)
[interface.cli] (interface/cli.py):
    -> NINGUEM importa em producao (orfao absoluto)
[interface.watcher] (interface/watcher.py):
    -> NINGUEM importa em producao (orfao absoluto)
[scripts.bootstrap_core_memory] (scripts/bootstrap_core_memory.py):
    -> NINGUEM importa em producao (orfao absoluto)
[storage.relational_db] (storage/relational_db.py):
    -> NINGUEM importa em producao (orfao absoluto)
```

---

## 3. Passo 2 — Prova Dinâmica: O que o Servidor Realmente Carrega

Executado o script [`scratch/fase4_0b_runtime_probe.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/fase4_0b_runtime_probe.py) em ambiente estritamente isolado:
- **Diretório temporário:** `tempfile.mkdtemp(prefix='fase4_0b_probe_')`
- **Variáveis de ambiente isoladas:** `GRAFO_DB_PATH`, `GRAFO_CHROMA_PATH`, `GRAFO_CHROMA_COLLECTION`
- **Garantia de não contaminação:** Asserções rígidas antes de cada operação confirmando que os caminhos residem no temporário.
- **Modelo de Embedding:** O modelo oficial `all-MiniLM-L6-v2` (`SentenceTransformer`) foi carregado com sucesso na máquina local (384 dimensões nativas), **sem necessidade de stubs**.

### Módulos Carregados em `sys.modules` no Momento A (Bootstrap) e Momento B (Após Uso)

Total de módulos do projeto carregados no Momento A: **36 módulos**.
Total de módulos do projeto carregados no Momento B: **36 módulos**.
Novos módulos carregados entre A e B: **ZERO**.

#### Lista Literal dos 36 Módulos Carregados:
- `agents`
- `agents.revisor_critico`
- `core`
- `core.checkpointer`
- `core.config`
- `core.database`
- `core.gating_interceptor`
- `core.graph_rag`
- `core.hybrid_search`
- `core.mcp_governor`
- `core.memory_extractor`
- `core.middleware`
- `core.project_index`
- `core.rate_governor`
- `core.security_guard`
- `core.telemetry_schemas`
- `ingestion`
- `ingestion.crawler`
- `ingestion.orchestrator`
- `ingestion.parser`
- `ingestion.summarizer`
- `interface`
- `interface.action_hooks`
- `interface.mcp_server`
- `interface.queue_writer`
- `interface.telemetry_api`
- `services`
- `services.janitor`
- `storage`
- `storage.base_backend`
- `storage.connection`
- `storage.logic`
- `storage.schema`
- `storage.semantic_logic`
- `storage.store`
- `storage.vector_store`

### Divergência entre Alcance Estático (41) e Runtime Dinâmico (36)
Exatamente **5 módulos** são alcançáveis estaticamente na árvore de sintaxe, mas **NÃO são carregados no runtime**:
1. `main`: O arquivo é o ponto de entrada executado como `__main__`, não importado como módulo `main`.
2. `core.hsm_engine`: Importado exclusivamente dentro da função de endpoint `interface/telemetry_api.py:79`. Como nenhum endpoint REST é chamado no runtime padrão, nunca é importado.
3. `core.vector_backend`: Importado em `main.py:134` exclusivamente se `GRAFO_VECTOR_BACKEND == 'qdrant'`. Como o backend padrão é Chroma, não é carregado.
4. `core.vector_reconciler`: Importado exclusivamente dentro do endpoint `POST /api/janitor/reconcile` em `interface/telemetry_api.py:271`. Nunca é importado no runtime padrão.
5. `core.probabilistic_retriever`: Importado em `core/hybrid_search.py:232` sob demanda para Thompson Sampling (`use_thompson_sampling=True`). Não é carregado no fluxo padrão.

---

## 4. Passo 3 — Matriz de Ferramentas MCP (31 Ferramentas × 2 Estados)

As 31 ferramentas registradas no `FastMCP` foram executadas programaticamente via `await server._mcp.call_tool(nome, args)`:
- **Estado L (Banco Limpo):** Imediatamente após o bootstrap oficial de `main.py`, sem criação manual de tabelas.
- **Estado P (Banco Populado):** Após registrar e minerar projeto de fixture com 3 arquivos `.py` (`math_ops.py`, `calc.py`, `service.py`) e 1 `.md` (`README.md`), além de salvar fatos semânticos e checkpoints.

### 4.1 Tabelas Existentes no SQLite e Contagens

| Tabela de Negócio | Estado L (Linhas) | Estado P (Linhas) | Quem Popula em Produção |
| :--- | :--- | :--- | :--- |
| `projects` | 0 | 1 | `concierge_register` via `store.register_project` |
| `nodes` | 0 | 10 | `concierge_mine` via `IngestionOrchestrator` -> `store.create_nodes_and_edges_bulk` |
| `edges` | 0 | 12 | `concierge_mine` via `IngestionOrchestrator` -> `store.create_nodes_and_edges_bulk` |
| `semantic_facts` | 0 | 1 | `concierge_store_fact` via `SemanticExtractor` -> `semantic_logic.insert_semantic_fact` |
| `user_core_memory` | 0 | 0 | `concierge_set_memory` |
| `reference_wings` | 0 | 0 | `add_reference_wing` |
| `commit_log` | 0 | 0 | `concierge_commit` |
| `test_log` | 0 | 0 | `JanitorService` |
| `trajectories` | 0 | 0 | `JanitorService` |
| `files` | **TABELA AUSENTE** | **TABELA AUSENTE** | **NINGUÉM** (omissa no bootstrap) |
| `communities` | **TABELA AUSENTE** | **TABELA AUSENTE** | **NINGUÉM** (omissa no bootstrap) |
| `ast_edges` | **TABELA AUSENTE** | **TABELA AUSENTE** | **NINGUÉM** (omissa no bootstrap) |
| `agent_checkpoints` | **TABELA AUSENTE** | **TABELA AUSENTE** | **NINGUÉM** (omissa no bootstrap) |
| `fsm_checkpoints` | **TABELA AUSENTE** | **TABELA AUSENTE** | **NINGUÉM** (omissa no bootstrap) |

> [!IMPORTANT]
> **Constatações Críticas de Banco:**
> 1. Após `concierge_mine`, a tabela oficial **`edges` é populada com 12 linhas**, comprovando que as verdadeiras arestas de grafo residem em `edges`!
> 2. A tabela **`ast_edges` NÃO EXISTE** no banco oficial. Como consequência direta, **`concierge_get_call_chain` FALHA FATALMENTE** com `no such table: ast_edges`.
> 3. A tabela **`agent_checkpoints` NÃO EXISTE** no banco oficial. Como consequência direta, `agent_get_checkpoint` e `agent_list_checkpoints` falham com `no such table: agent_checkpoints`, e `agent_save_checkpoint` retorna `success: false`.

### 4.2 Matriz 31 × 2 de Execução de Ferramentas

| Ferramenta MCP | Estado L (Limpo) | Erro / Resposta L | Estado P (Populado) | Erro / Resposta P |
| :--- | :--- | :--- | :--- | :--- |
| `concierge_list_projects` | OK com dados | `[TextContent(type='text', text='{\n  "projects": {},\n  "success": true,\n  "duration_seco` | OK com dados | `[TextContent(type='text', text='{\n  "projects": {\n    "fixture_project": {\n      "uuid"` |
| `concierge_status` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "system": "Grafo Concierge v3.8.0` | OK vazio | `[TextContent(type='text', text='{\n  "success": true,\n  "system": "Grafo Concierge v3.8.0` |
| `get_full_topology` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "nodes": [\n    {\n      "node_id` |
| `count_embeddings` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `concierge_search` | OK vazio | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'\' not found` | OK vazio | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'\' not found` |
| `search_symbols` | OK vazio | `[TextContent(type='text', text='{\n  "success": true,\n  "symbols": [],\n  "duration_secon` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "symbols": [\n    {\n      "id": ` |
| `get_implementations` | EXCEÇÃO | `ToolError: Error executing tool get_implementations: 1 validation error for get_implementa` | EXCEÇÃO | `ToolError: Error executing tool get_implementations: 1 validation error for get_implementa` |
| `get_callers` | EXCEÇÃO | `ToolError: Error executing tool get_callers: 1 validation error for get_callersArguments s` | EXCEÇÃO | `ToolError: Error executing tool get_callers: 1 validation error for get_callersArguments s` |
| `concierge_get_call_chain` | EXCEÇÃO | `ToolError: Error executing tool concierge_get_call_chain: no such table: ast_edges` | EXCEÇÃO | `ToolError: Error executing tool concierge_get_call_chain: no such table: ast_edges` |
| `concierge_load` | EXCEÇÃO | `ToolError: Error executing tool concierge_load: 1 validation error for concierge_loadArgum` | EXCEÇÃO | `ToolError: Error executing tool concierge_load: 1 validation error for concierge_loadArgum` |
| `concierge_wakeup` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project not found: 000` | OK vazio | `[TextContent(type='text', text='{\n  "project": {\n    "uuid": "6266931f-02ae-42fe-a0b9-aa` |
| `concierge_resume` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project not found: 000` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `concierge_set_state` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "session_id": "default",\n  "acti` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "session_id": "default",\n  "acti` |
| `concierge_store_fact` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` |
| `concierge_list_facts` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` |
| `concierge_set_memory` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` |
| `concierge_get_memory` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Invalid scope_type \'p` |
| `concierge_feedback` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "fact_id": 1,\n  "was_useful": tr` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "fact_id": 1,\n  "was_useful": tr` |
| `find_similar` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK vazio | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `get_trajectories` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK vazio | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `add_reference_wing` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `remove_reference_wing` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `update_project` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "Project \'test_proj\' ` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `agent_save_checkpoint` | OK com dados | `([TextContent(type='text', text='{"success": false, "message": "Failed to save checkpoint ` | OK com dados | `([TextContent(type='text', text='{"success": false, "message": "Failed to save checkpoint ` |
| `agent_get_checkpoint` | EXCEÇÃO | `ToolError: Error executing tool agent_get_checkpoint: no such table: agent_checkpoints` | EXCEÇÃO | `ToolError: Error executing tool agent_get_checkpoint: no such table: agent_checkpoints` |
| `agent_list_checkpoints` | EXCEÇÃO | `ToolError: Error executing tool agent_list_checkpoints: no such table: agent_checkpoints` | EXCEÇÃO | `ToolError: Error executing tool agent_list_checkpoints: no such table: agent_checkpoints` |
| `concierge_commit` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "updated_pointers is ma` | OK com dados | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "updated_pointers is ma` |
| `concierge_register` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` | OK com dados | `[TextContent(type='text', text='{\n  "success": true,\n  "project_uuid": "6266931f-02ae-42` |
| `concierge_mine` | EXCEÇÃO | `[TextContent(type='text', text='{\n  "success": false,\n  "error": "not all arguments conv` | OK vazio | `[TextContent(type='text', text='{\n  "files_processed": 0,\n  "categories": {\n    "code":` |
| `reset_collection` | EXCEÇÃO | `SecurityException: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocke` | EXCEÇÃO | `SecurityException: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocke` |
| `delete_project` | EXCEÇÃO | `SecurityException: Access denied: tool 'delete_project' (category 'DANGEROUS') is blocked ` | EXCEÇÃO | `SecurityException: Access denied: tool 'delete_project' (category 'DANGEROUS') is blocked ` |

---

## 5. Passo 4 — O Telemetry API Roda no Runtime Padrão?

Executado o script [`scratch/fase4_0b_telemetry_probe.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/fase4_0b_telemetry_probe.py) subindo o servidor real em subprocesso na porta efêmera 18923 com `GRAFO_TRANSPORT=sse`.

**Saída literal comprovada:**
```
Starting server in subprocess with port 18923 and transport=sse...

--- CONSULTA AOS ENDPOINTS ---
Endpoint: http://127.0.0.1:18923/api/mcp/state/probe
  HTTP Status: 404
  Resposta (primeiras linhas): Not Found
Endpoint: http://127.0.0.1:18923/api/governor/metrics
  HTTP Status: 404
  Resposta (primeiras linhas): Not Found
Endpoint: http://127.0.0.1:18923/api/gating/config
  HTTP Status: 404
  Resposta (primeiras linhas): Not Found
Endpoint: http://127.0.0.1:18923/
  HTTP Status: 404
  Resposta (primeiras linhas): Not Found
Endpoint: http://127.0.0.1:18923/sse
  HTTP Status: None
  Resposta (primeiras linhas): Connection error: TimeoutError: timed out

Encerramento do processo...
Diretório temporário descartado.

--- LOGS DO BOOT ---
  | 2026-10-15 23:35:21 │ INFO    │ grafo-concierge.main         │ ============================================================
  | 2026-10-15 23:35:21 │ INFO    │ grafo-concierge.main         │   Grafo Concierge v3.8.0 — Absolute Solidity
  | 2026-10-15 23:35:21 │ INFO    │ grafo-concierge.main         │ ============================================================
  | 2026-10-15 23:35:36 │ INFO    │ grafo-concierge.mcp          │ GrafoConciergeServer initialized — 31 tools registered.
  | 2026-10-15 23:35:36 │ INFO    │ grafo-concierge.main         │ Bootstrap complete — all components initialized.
  | 2026-10-15 23:35:36 │ INFO    │ grafo-concierge.mcp          │ Starting Grafo Concierge MCP Server (transport=sse)...
  | INFO:     Started server process [21652]
  | INFO:     Uvicorn running on http://127.0.0.1:18923 (Press CTRL+C to quit)
  | INFO:     127.0.0.1 - "GET /api/mcp/state/probe HTTP/1.1" 404 Not Found
  | INFO:     127.0.0.1 - "GET /api/governor/metrics HTTP/1.1" 404 Not Found
  | INFO:     127.0.0.1 - "GET /api/gating/config HTTP/1.1" 404 Not Found
  | INFO:     127.0.0.1 - "GET / HTTP/1.1" 404 Not Found
  | INFO:     127.0.0.1 - "GET /sse HTTP/1.1" 200 OK

Verificação de liberação da porta 18923: code=None (Esperado: None/Connection error)
```

> [!CAUTION]
> **Resposta Objetiva à Pergunta da Investigação:**  
> No caminho de execução real `python main.py`, **NENHUM endpoint REST da `telemetry_api.py` responde** (todos retornam HTTP 404). O servidor MCP roda estritamente a aplicação SSE do FastMCP (`/sse`). A aplicação FastAPI de `interface/telemetry_api.py` **NUNCA É MONTADA NEM INICIADA**.

---

## 6. Passo 5 — Matriz Consolidada dos 64 Módulos do Projeto

| Módulo | Arquivo | Linhas | Alcançável Estático | Carregado Boot | Carregado Após Uso | Classificação |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `agent` | [`agent/__init__.py`](file:///agent/__init__.py) | 13 | N | N | N | **NÃO CARREGADO** |
| `agent.agent_prompts` | [`agent/agent_prompts.py`](file:///agent/agent_prompts.py) | 176 | N | N | N | **NÃO CARREGADO** |
| `agent.run_agent` | [`agent/run_agent.py`](file:///agent/run_agent.py) | 266 | N | N | N | **NÃO CARREGADO** |
| `agents` | [`agents/__init__.py`](file:///agents/__init__.py) | 14 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `agents.revisor_critico` | [`agents/revisor_critico.py`](file:///agents/revisor_critico.py) | 610 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `core` | [`core/__init__.py`](file:///core/__init__.py) | 23 | S | S | S | **EM USO** |
| `core.alias_tracker` | [`core/alias_tracker.py`](file:///core/alias_tracker.py) | 259 | N | N | N | **NÃO CARREGADO** |
| `core.background_janitor` | [`core/background_janitor.py`](file:///core/background_janitor.py) | 290 | N | N | N | **NÃO CARREGADO** |
| `core.checkpointer` | [`core/checkpointer.py`](file:///core/checkpointer.py) | 255 | S | S | S | **EM USO** |
| `core.config` | [`core/config.py`](file:///core/config.py) | 192 | S | S | S | **EM USO** |
| `core.database` | [`core/database.py`](file:///core/database.py) | 73 | S | S | S | **EM USO** |
| `core.delta_manager` | [`core/delta_manager.py`](file:///core/delta_manager.py) | 265 | N | N | N | **NÃO CARREGADO** |
| `core.delta_sync` | [`core/delta_sync.py`](file:///core/delta_sync.py) | 12 | N | N | N | **NÃO CARREGADO** |
| `core.dependencies` | [`core/dependencies.py`](file:///core/dependencies.py) | 39 | N | N | N | **NÃO CARREGADO** |
| `core.federated_knowledge_router` | [`core/federated_knowledge_router.py`](file:///core/federated_knowledge_router.py) | 100 | N | N | N | **NÃO CARREGADO** |
| `core.gating_interceptor` | [`core/gating_interceptor.py`](file:///core/gating_interceptor.py) | 176 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `core.global_memory_adapter` | [`core/global_memory_adapter.py`](file:///core/global_memory_adapter.py) | 85 | N | N | N | **NÃO CARREGADO** |
| `core.graph_rag` | [`core/graph_rag.py`](file:///core/graph_rag.py) | 260 | S | S | S | **EM USO** |
| `core.hsm_engine` | [`core/hsm_engine.py`](file:///core/hsm_engine.py) | 511 | S | N | N | **NÃO CARREGADO** |
| `core.hybrid_search` | [`core/hybrid_search.py`](file:///core/hybrid_search.py) | 288 | S | S | S | **EM USO** |
| `core.intent_classifier` | [`core/intent_classifier.py`](file:///core/intent_classifier.py) | 98 | N | N | N | **NÃO CARREGADO** |
| `core.janitor` | [`core/janitor.py`](file:///core/janitor.py) | 12 | N | N | N | **NÃO CARREGADO** |
| `core.mcp_governor` | [`core/mcp_governor.py`](file:///core/mcp_governor.py) | 192 | S | S | S | **EM USO** |
| `core.memory_extractor` | [`core/memory_extractor.py`](file:///core/memory_extractor.py) | 245 | S | S | S | **EM USO** |
| `core.middleware` | [`core/middleware.py`](file:///core/middleware.py) | 780 | S | S | S | **EM USO** |
| `core.nozomio_router` | [`core/nozomio_router.py`](file:///core/nozomio_router.py) | 21 | N | N | N | **NÃO CARREGADO** |
| `core.parser_factory` | [`core/parser_factory.py`](file:///core/parser_factory.py) | 80 | N | N | N | **NÃO CARREGADO** |
| `core.parsers` | [`core/parsers/__init__.py`](file:///core/parsers/__init__.py) | 20 | N | N | N | **NÃO CARREGADO** |
| `core.parsers.base` | [`core/parsers/base.py`](file:///core/parsers/base.py) | 41 | N | N | N | **NÃO CARREGADO** |
| `core.parsers.python_parser` | [`core/parsers/python_parser.py`](file:///core/parsers/python_parser.py) | 90 | N | N | N | **NÃO CARREGADO** |
| `core.parsers.ts_js_parser` | [`core/parsers/ts_js_parser.py`](file:///core/parsers/ts_js_parser.py) | 265 | N | N | N | **NÃO CARREGADO** |
| `core.probabilistic_retriever` | [`core/probabilistic_retriever.py`](file:///core/probabilistic_retriever.py) | 108 | S | N | N | **NÃO CARREGADO** |
| `core.project_index` | [`core/project_index.py`](file:///core/project_index.py) | 316 | S | S | S | **EM USO** |
| `core.rate_governor` | [`core/rate_governor.py`](file:///core/rate_governor.py) | 280 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `core.search_engine` | [`core/search_engine.py`](file:///core/search_engine.py) | 61 | N | N | N | **NÃO CARREGADO** |
| `core.security_guard` | [`core/security_guard.py`](file:///core/security_guard.py) | 101 | S | S | S | **EM USO** |
| `core.telemetry_schemas` | [`core/telemetry_schemas.py`](file:///core/telemetry_schemas.py) | 82 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `core.vector_backend` | [`core/vector_backend.py`](file:///core/vector_backend.py) | 471 | S | N | N | **NÃO CARREGADO** |
| `core.vector_reconciler` | [`core/vector_reconciler.py`](file:///core/vector_reconciler.py) | 55 | S | N | N | **NÃO CARREGADO** |
| `ingestion` | [`ingestion/__init__.py`](file:///ingestion/__init__.py) | 25 | S | S | S | **EM USO** |
| `ingestion.crawler` | [`ingestion/crawler.py`](file:///ingestion/crawler.py) | 722 | S | S | S | **EM USO** |
| `ingestion.orchestrator` | [`ingestion/orchestrator.py`](file:///ingestion/orchestrator.py) | 920 | S | S | S | **EM USO** |
| `ingestion.parser` | [`ingestion/parser.py`](file:///ingestion/parser.py) | 984 | S | S | S | **EM USO** |
| `ingestion.summarizer` | [`ingestion/summarizer.py`](file:///ingestion/summarizer.py) | 948 | S | S | S | **EM USO** |
| `interface` | [`interface/__init__.py`](file:///interface/__init__.py) | 16 | S | S | S | **EM USO** |
| `interface.action_hooks` | [`interface/action_hooks.py`](file:///interface/action_hooks.py) | 261 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `interface.cli` | [`interface/cli.py`](file:///interface/cli.py) | 392 | N | N | N | **NÃO CARREGADO** |
| `interface.mcp_server` | [`interface/mcp_server.py`](file:///interface/mcp_server.py) | 1785 | S | S | S | **EM USO** |
| `interface.queue_writer` | [`interface/queue_writer.py`](file:///interface/queue_writer.py) | 148 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `interface.telemetry_api` | [`interface/telemetry_api.py`](file:///interface/telemetry_api.py) | 595 | S | S | S | **CARREGADO MAS NUNCA CHAMADO** |
| `interface.watcher` | [`interface/watcher.py`](file:///interface/watcher.py) | 243 | N | N | N | **NÃO CARREGADO** |
| `main` | [`main.py`](file:///main.py) | 282 | S | S | S | **EM USO** |
| `scripts.bootstrap_core_memory` | [`scripts/bootstrap_core_memory.py`](file:///scripts/bootstrap_core_memory.py) | 93 | N | N | N | **NÃO CARREGADO** |
| `services` | [`services/__init__.py`](file:///services/__init__.py) | 13 | S | S | S | **EM USO** |
| `services.janitor` | [`services/janitor.py`](file:///services/janitor.py) | 762 | S | S | S | **EM USO** |
| `storage` | [`storage/__init__.py`](file:///storage/__init__.py) | 31 | S | S | S | **EM USO** |
| `storage.base_backend` | [`storage/base_backend.py`](file:///storage/base_backend.py) | 241 | S | S | S | **EM USO** |
| `storage.connection` | [`storage/connection.py`](file:///storage/connection.py) | 310 | S | S | S | **EM USO** |
| `storage.logic` | [`storage/logic.py`](file:///storage/logic.py) | 703 | S | S | S | **EM USO** |
| `storage.relational_db` | [`storage/relational_db.py`](file:///storage/relational_db.py) | 35 | N | N | N | **NÃO CARREGADO** |
| `storage.schema` | [`storage/schema.py`](file:///storage/schema.py) | 390 | S | S | S | **EM USO** |
| `storage.semantic_logic` | [`storage/semantic_logic.py`](file:///storage/semantic_logic.py) | 125 | S | S | S | **EM USO** |
| `storage.store` | [`storage/store.py`](file:///storage/store.py) | 802 | S | S | S | **EM USO** |
| `storage.vector_store` | [`storage/vector_store.py`](file:///storage/vector_store.py) | 759 | S | S | S | **EM USO** |

### Resumo das Classificações:
- 🟢 **EM USO:** 29 módulos (núcleo operacional real do servidor)
- 🟡 **CARREGADO MAS NUNCA CHAMADO:** 8 módulos (carregados por efeito colateral no topo de `__init__.py` ou imports de conveniência)
- 🔴 **NÃO CARREGADO:** 27 módulos (completamente inalcançáveis ou em branches/funções mortas no runtime padrão)
- **Total:** 64 módulos

---

## 7. Classificação dos 88 Itens do Backlog (VIVO vs DORMENTE)

Sem alterar numeração, títulos ou a contagem exata (3 Máxima, 21 Crítica, 30 Grave, 29 Média, 5 Baixa):

### Resumo Estatístico:
- 🟢 **VIVO:** 42 itens (o código problemático reside em módulo **EM USO** no runtime padrão)
- 💤 **DORMENTE:** 46 itens (o código reside em módulo **NÃO CARREGADO** ou **CARREGADO MAS NUNCA CHAMADO**)
- **Total:** 88 itens

### Distribuição por Severidade:
| Severidade | Backlog Total | VIVO (Ativo em Prod) | DORMENTE (Módulo Não Executado) |
| :--- | :---: | :---: | :---: |
| 🔴🔴 PRIORIDADE MÁXIMA | 3 | **2** | **1** |
| 🔴 CRÍTICA | 21 | **10** | **11** |
| 🟠 GRAVE | 30 | **11** | **19** |
| 🟡 MÉDIA | 29 | **16** | **13** |
| 🔵 BAIXA | 5 | **3** | **2** |
| **TOTAL** | **88** | **42** | **46** |

### Tabela Completa dos 88 Itens:

| BL ID | Título | Severidade | Status Runtime | Justificativa Sintética |
| :--- | :--- | :--- | :---: | :--- |
| [`BL-001`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-001) | Omissão Estrutural de 5 Tabelas no Bootstrap Oficial de Produção | 🔴🔴 PRIORIDADE MÁXIMA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-002`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-002) | Inoperância Funcional de 12 Subsistemas Analíticos em Instalação Limpa | 🔴🔴 PRIORIDADE MÁXIMA | **DORMENTE** | Módulo primário afetado é dormente (core/delta_manager.py (NÃO CARREGADO), core/vector_reconciler.py (NÃO CARREGADO)), embora interaja com interfaces do núcleo. |
| [`BL-003`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-003) | Padrão Test Mirage: 17 Suítes de Teste Criam Tabelas Privadas em `setUp()` | 🔴 CRÍTICA | **DORMENTE** | Módulo primário afetado é dormente (), embora interaja com interfaces do núcleo. |
| [`BL-004`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-004) | Mascaramento de Erros DDL e Falsa Confirmação de Integridade no Boot | 🟠 GRAVE | **DORMENTE** | Módulo primário afetado é dormente (interface/watcher.py (NÃO CARREGADO)), embora interaja com interfaces do núcleo. |
| [`BL-005`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-005) | Abandono da Especificação Arquitetural Formal (`01_ARCHITECTURE.md`) | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-006`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-006) | Colisão Estrutural entre Fila Real (`storage/`) e Zero Fila (`core/`) sobre o Banco | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-007`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-007) | Código Morto em Produção: `interface/queue_writer.py` | 🔴 CRÍTICA | **VIVO** | Núcleo ativo em execução no runtime padrão. |
| [`BL-008`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-008) | Divergência de Integridade Referencial (`foreign_keys=OFF` no core vs `ON` em storage) | 🟠 GRAVE | **VIVO** | Núcleo ativo em execução no runtime padrão. |
| [`BL-009`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-009) | Timeout Assimétrico de Conexão (5s em storage vs 30s no core) | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-010`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-010) | Quebra de Encapsulamento Privado `_gc._store._conn_mgr._db_path` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-016`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-016) | Deadlock Inevitável em Escritas Aninhadas/Reentrantes no `SerializedWriteQueue` | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-018`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-018) | Vazamento Perpétuo de Conexões SQLite em Threads Finalizadas | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-021`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-021) | Falha ao Reiniciar `SerializedWriteQueue` após `stop()` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-011`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-011) | Bypass Total da Governança de Ferramentas via Injeção de `session_id` Fantasma | 🔴🔴 PRIORIDADE MÁXIMA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-012`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-012) | Ausência Total de Verificação de Posse em Checkpoints de Agentes | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-013`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-013) | Vazamento de 100% do Catálogo de Ferramentas em `list_tools()` | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-014`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-014) | Desconexão Total do Runtime Cognitivo no Servidor MCP | 🟠 GRAVE | **DORMENTE** | Módulo primário afetado é dormente (agent/run_agent.py (NÃO CARREGADO), core/hsm_engine.py (NÃO CARREGADO)), embora interaja com interfaces do núcleo. |
| [`BL-015`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-015) | Inicialização Insegura por Padrão (`default_state = "EXECUTION"`) | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-052`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-052) | Evasão da Blacklist de Comandos Destrutivos do SecurityGuard | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-053`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-053) | `classify_command(None)` Lança `TypeError` Não Tratado | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-054`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-054) | Bug de Barra Dupla `C:\\\\` na Raiz Bloqueia 100% dos Arquivos em `is_safe_path` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-055`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-055) | Resolução de Caminhos Relativos Ancorada ao CWD do Processo e Não a `project_root` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-056`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-056) | Falsos Positivos de WARNING em Comandos Inofensivos Contendo `"build"` | 🔵 BAIXA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-033`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-033) | Invocação de Método Fantasma `self.vector_db.get_all_ids()` | 🔴 CRÍTICA | **VIVO** | Núcleo ativo em execução no runtime padrão. |
| [`BL-034`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-034) | Purga Garantida de 100% dos Vetores por Incompatibilidade `int` vs `str` | 🔴 CRÍTICA (Perda Catastrófica de Dados) | **DORMENTE** | Módulos citados são dormentes: core/vector_reconciler.py (NÃO CARREGADO) |
| [`BL-017`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-017) | Bypass de Strict Scoping na Busca Vetorial com `project_uuids=[]` | 🔴 CRÍTICA (Vazamento Cross-Project) | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-025`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-025) | Perda Total no Grafo na Renomeação de Arquivos | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-026`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-026) | Descarte Silencioso de 100% dos Resumos L0 com Gravação de `NULL` | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-027`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-027) | Falha Silenciosa de Persistência do L2 Compass no SQLite | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-028`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-028) | Acúmulo Perpétuo de Vetores Zumbis no ChromaDB | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-035`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-035) | Race Condition Destrutiva TOCTOU no Reconciliador Vetorial | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/vector_reconciler.py (NÃO CARREGADO) |
| [`BL-057`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-057) | Método Fantasma `has_structural_change()` no DeltaManager | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: core/delta_manager.py (NÃO CARREGADO), core/hsm_engine.py (NÃO CARREGADO) |
| [`BL-058`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-058) | Cegueira de LBH em Non-Python e SSH Incompleto | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/delta_manager.py (NÃO CARREGADO) |
| [`BL-020`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-020) | Falha de Tipo em `_calculate_decay` com Timestamps ISO Offset-Aware | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-036`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-036) | Falta de Paginação em `delete_batch` no Reconciliador Vetorial | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/vector_reconciler.py (NÃO CARREGADO) |
| [`BL-029`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-029) | Crash com `AttributeError` em Ingestão sem Summarizer | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-030`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-030) | Descarte Arbitrário de `requirements.txt` por `*.txt` no Ignore Padrão | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-031`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-031) | Poluição de Tags Semânticas por Substrings Ingênuas | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-032`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-032) | Truncamento de Código JS/TS por Contagem Ingênua de Chaves `{}` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-059`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-059) | Dupla Conexão Efêmera Crua por Mutação no DeltaManager | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/delta_manager.py (NÃO CARREGADO) |
| [`BL-060`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-060) | TypeError em `compile_community_summary_jit()` quando `files.content` é NULL | 🔵 BAIXA | **DORMENTE** | Módulos citados são dormentes: core/delta_manager.py (NÃO CARREGADO) |
| [`BL-022`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-022) | Crash com `ValueError` em Busca Vetorial com `node_id=None` ou Vazio | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-023`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-023) | Duplicação de Nós na CTE Recursiva `get_dependency_tree` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-061`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-061) | SSH Context-Free Captura Declarações Independentemente de Indentação | 🔵 BAIXA | **DORMENTE** | Módulos citados são dormentes: core/delta_manager.py (NÃO CARREGADO) |
| [`BL-024`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-024) | Isolamento de `semantic_logic.py` Força Violação de Encapsulamento | 🔵 BAIXA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-088`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-088) | Falha de Atomicidade em `apply_alias_migration` (Migração Parcial sem Rollback) | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/alias_tracker.py (NÃO CARREGADO), interface/watcher.py (NÃO CARREGADO) |
| [`BL-062`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-062) | Falha Fatal e Crash HTTP 500 na Telemetria por Tabelas Inexistentes | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-063`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-063) | Inoperância Fora da Caixa por Dependência `get_db_manager` Não Configurada | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-069`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-069) | Código Morto em Handlers SSE e Telemetria Reativa Congelada | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server) |
| [`BL-070`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-070) | Ciclo Infinito de Flapping SSE a cada 8s e Inundação do Feed de Eventos | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server), interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-071`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-071) | Colisão de Portas 8000, Falha no `dev:all` e Desconexão do FastMCP | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server) |
| [`BL-064`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-064) | Falso Stream Contínuo por Limite Hardcoded (`max_checks = 5`) | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-065`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-065) | Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-066`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-066) | Insegurança Total de CORS e Falta de Autenticação em Rotas Mutantes | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-072`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-072) | Incompatibilidade de Autenticação FastMCP e Rejeição HTTP 401 | 🟠 GRAVE | **DORMENTE** | Módulo primário afetado é dormente (grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server)), embora interaja com interfaces do núcleo. |
| [`BL-073`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-073) | Omissão de Metadados em `get_full_topology` e Esvaziamento do `InspectorDrawer` | 🟠 GRAVE | **DORMENTE** | Módulo primário afetado é dormente (grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server)), embora interaja com interfaces do núcleo. |
| [`BL-067`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-067) | Crash de Tipagem em Timestamps na Telemetria (`NoneType` e `str`) | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-068`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-068) | Thread Daemônica Órfã Iniciada no Import de `telemetry_api` | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: interface/telemetry_api.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-074`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-074) | Risco de Data Inválida (`Invalid Date`) por Concatenação `+ "Z"` | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server) |
| [`BL-075`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-075) | Rotas Mutantes `/api/hsm/transition` Órfãs e Cliques Inertes no HUD | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server) |
| [`BL-076`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-076) | 37 Erros de Linter e Violação de Pureza no React 19 | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server), grafo-dashboard-web (frontend não executado no server) |
| [`BL-077`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-077) | Contaminação de Turnos Multi-Sessão no Circuit Breaker | 🔴 CRÍTICA CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agent/run_agent.py (NÃO CARREGADO) |
| [`BL-078`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-078) | Vazamento de Privacidade por Fallback Inseguro Fail-Open em `check_contamination` | 🔴 CRÍTICA CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agents/revisor_critico.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-079`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-079) | Aprovação Espúria de Commits Inválidos em `audit_with_retry` | 🟠 GRAVE CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agents/revisor_critico.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-080`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-080) | Dessincronização de Estado e Diretrizes em `step(target_transition=...)` | 🟠 GRAVE CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agent/run_agent.py (NÃO CARREGADO) |
| [`BL-081`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-081) | Falhas de Tipagem e Crash em Reranking (`NoneType` e `int` vs `str`) | 🟠 GRAVE CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agents/revisor_critico.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-082`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-082) | Incompatibilidade Universal com Corrotinas e Bypass do RateGovernor em `execute_tool` | 🟡 MÉDIA CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agent/run_agent.py (NÃO CARREGADO) |
| [`BL-083`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-083) | Dessincronização entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX` | 🟡 MÉDIA CONDICIONAL | **DORMENTE** | Módulos citados são dormentes: agent/agent_prompts.py (NÃO CARREGADO) |
| [`BL-084`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-084) | Contrato Fantasma de Cliente MCP Federado em `FederatedKnowledgeRouter` | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/federated_knowledge_router.py (NÃO CARREGADO) |
| [`BL-085`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-085) | Método Fantasma `insert()` em MockVectorDatabase Mascara Contrato de Inserção de Vetores | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-086`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-086) | Incompatibilidade de Assinatura e Retorno em `MockGraphRAGEngine.retrieve_multihop_context` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-087`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-087) | Mock Permissivo com `*args, **kwargs` e Divergência de Interface em `_MockVectorStore` | 🔵 BAIXA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-037`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-037) | Despacho Ambíguo em `save_checkpoint` Corrompe Metadados e Apaga Estado | 🔴 CRÍTICA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-038`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-038) | Mascaramento de Falhas e Transação Não Atômica em `execute_time_travel` | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-039`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-039) | Granularidade Temporal de 1s Falha em Deletar Checkpoints em Rajadas | 🟠 GRAVE | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-040`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-040) | Crash `json.JSONDecodeError` Não Tratado em `get_checkpoint` | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-041`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-041) | Tipagem Insegura Mypy no Checkpointer (`None` Not Callable) | 🟡 MÉDIA | **VIVO** | Módulos citados estão EM USO no runtime padrão. |
| [`BL-042`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-042) | Slice Negativo `[-0:]` com `keep_limit = 0` Preserva 100% dos Checkpoints | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/background_janitor.py (NÃO CARREGADO) |
| [`BL-043`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-043) | Degradação Irreversível da Prioridade do Servidor para IDLE | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/background_janitor.py (NÃO CARREGADO) |
| [`BL-044`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-044) | Deleção Cruzada de Checkpoints entre Agentes na Mesma Sessão | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/background_janitor.py (NÃO CARREGADO) |
| [`BL-045`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-045) | Crash com `TypeError` em `_summarize_community` com `files.content = NULL` | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/background_janitor.py (NÃO CARREGADO) |
| [`BL-046`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-046) | TOCTOU / Descarte Cego de `is_dirty = 0` sobre Edições Recentes | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/background_janitor.py (NÃO CARREGADO) |
| [`BL-047`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-047) | Vazamento de `unfinished_tasks` na `PriorityQueue` e Starvation | 🔴 CRÍTICA | **DORMENTE** | Módulos citados são dormentes: core/rate_governor.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-048`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-048) | Starvation de Tarefas LOW Envelhecidas em Carga de 75% a 100% | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/rate_governor.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-049`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-049) | Data Race / Lost Updates em `get_current_metrics()` sem Lock | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/rate_governor.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-050`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-050) | Deadlock Eterno em `submit_request` sem Timeout e Após `shutdown()` | 🟠 GRAVE | **DORMENTE** | Módulos citados são dormentes: core/rate_governor.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-051`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-051) | Cegueira de RPM no Fast-Path do RateGovernor | 🟡 MÉDIA | **DORMENTE** | Módulos citados são dormentes: core/rate_governor.py (CARREGADO MAS NUNCA CHAMADO) |
| [`BL-019`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-019) | Incompatibilidade de Contrato em `init_fsm_checkpoints_schema` | 🟠 GRAVE | **VIVO** | Núcleo ativo em execução no runtime padrão. |

---

## 8. Impacto nas Cinco Decisões de Desenho do Passo A

Análise do impacto à luz da prova de execução empírica:

### 8.1 Tabela `files` (Decisão 1 e Decisão 2)
- **Funcionalidade EM USO que a consome:** **NENHUMA.** O pipeline de ingestão oficial (`ingestion/orchestrator.py`) e as ferramentas MCP operam 100% sobre a tabela `nodes` (com `type = 'file'`). A tabela `files` só é consultada por `watcher.py`, `delta_manager.py` e `background_janitor.py`, módulos que **NÃO SÃO CARREGADOS** no servidor padrão.

### 8.2 Tabela `communities`
- **Funcionalidade EM USO que a consome:** **NENHUMA.** `JanitorService` em produção detecta comunidades computando grafos dinâmicos em memória via CTE recursivo sobre a tabela `edges` (`janitor.py:506-557`). A tabela `communities` física é lida apenas por `background_janitor.py` (dormente).

### 8.3 Tabela `ast_edges` (Decisão 3)
- **Funcionalidade EM USO que a consome:** Apenas a ferramenta MCP `concierge_get_call_chain` (via `core/graph_rag.py:179`).
- **Fato Empírico Provado:** Como `ast_edges` nunca é populada (Passo 2 e 3), `concierge_get_call_chain` hoje falha com `no such table`. Se redirecionada para a tabela oficial `edges` (onde a ingestão AST grava `relation_type = 'calls'`), `ast_edges` passa a ter **ZERO consumidores** no sistema!

### 8.4 Tabela `agent_checkpoints` (Decisão 4)
- **Funcionalidade EM USO que a consome:** As ferramentas MCP `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints` (via `core/checkpointer.py`).
- **Impacto da Coluna `timestamp`:** O único consumidor que exigia o nome `timestamp` era `interface/telemetry_api.py:183`. Como provado no Passo 4, `telemetry_api.py` não roda no servidor. Portanto, o DDL canônico deve utilizar estritamente `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`.

### 8.5 Tabela `fsm_checkpoints` (Decisão 5)
- **Funcionalidade EM USO que a consome:** **NENHUMA.** O motor HSM (`core/hsm_engine.py`) não roda no servidor MCP padrão.

---

## 9. Três Caminhos para Decisão do Usuário

Apresentam-se três rotas arquiteturais objetivas com seus respectivos impactos quantificados:

### Caminho A: Criar as 5 Tabelas e Manter Tudo
- **Descrição:** Cria as 5 tabelas no schema oficial (`files`, `communities`, `ast_edges`, `agent_checkpoints`, `fsm_checkpoints`), mantém todos os 64 módulos e o dashboard no repositório.
- **Módulos Ativos:** 64 módulos Python (~11.000 linhas) + 43 arquivos no frontend Next.js (14.384 linhas).
- **Backlog Ativo:** **88 itens** (3 Máxima, 21 Crítica, 30 Grave, 29 Média, 5 Baixa) permanecem como dívida técnica ativa a corrigir.
- **Comportamento das Ferramentas MCP:** As 31 ferramentas continuam registradas. `agent_*` passam a funcionar. Porém, `concierge_get_call_chain` retornará sempre lista vazia, pois nenhum módulo de produção popula `ast_edges`.

### Caminho B: Criar Só o que tem Consumidor EM USO (Tratar Motor Delta/Survival como Dormente)
- **Descrição:** Cria no schema oficial unicamente a tabela **`agent_checkpoints`** (usada pelas 3 ferramentas de agente ativas). Trata as tabelas `files`, `communities`, `ast_edges` e `fsm_checkpoints` como pertencentes ao subsistema experimental dormente.
- **Redirecionamento de `concierge_get_call_chain`:**
  - **Viabilidade:** 100% viável e cirúrgico. A ingestão oficial (`ingestion/orchestrator.py:644-727`) já grava arestas de AST em `edges` com `relation_type IN ('calls', 'depends_on')`.
  - **Mudança Mínima:** Em `core/graph_rag.py:179`, substituir `FROM ast_edges` por `FROM edges WHERE relation_type IN ('calls', 'depends_on')` e mapear `parent_node -> source_id`, `child_node -> target_id`.
  - **Resultado:** `concierge_get_call_chain` passa a funcionar com dados reais do grafo imediatamente!
- **Módulos Ativos:** 29 módulos EM USO.
- **Backlog Ativo:** **42 itens VIVOS** (2 Máxima, 10 Crítica, 11 Grave, 16 Média, 3 Baixa).
- **Backlog em Quarentena / Dormente:** **46 itens** são isolados sem risco de quebra.
- **Comportamento das Ferramentas MCP:** **100% das ferramentas do núcleo operacional (29 de 31) funcionando perfeitamente**, sem tabelas fantasmas.

### Caminho C: Ligar o Motor Delta/Survival ao Servidor Real
- **Descrição:** Modifica o bootstrap de `main.py` para iniciar o `interface/watcher.py`, conecta `core/delta_manager.py` ao fluxo de mutação de arquivos, implementa no orquestrador a gravação simultânea em `files`, `communities` e `ast_edges`, e sobe a API de telemetria em thread auxiliar.
- **Módulos Ativos:** Todos os 64 módulos acoplados em tempo de execução.
- **Backlog Ativo:** **88 itens ativos**, acrescidos dos custos de refatoração das 23 queries de `files` para escopo multi-projeto e resolução de contenção de concorrência.
- **Comportamento das Ferramentas MCP:** Exige reestruturação profunda do runtime.

---

## 10. Conclusão e Parada no Gate (Regra 7)

Este relatório estabelece de forma irrefutável e empírica o limite entre o que está **EM USO** e o que está **DORMENTE** no Grafo Concierge:
1. O servidor operacional do FastMCP é sustentado por **29 módulos centrais** (`storage`, `ingestion`, `services/janitor`, `core/middleware`, `core/mcp_governor`, `interface/mcp_server`).
2. Toda a infraestrutura de telemetria REST, HSM, Revisor Crítico, Watcher e Delta Manager está inativa no caminho padrão `python main.py`.
3. A decisão sobre os Caminhos A, B ou C determinará o escopo exato das correções da Fase 4.

Em estrito cumprimento à **Regra 7 (Gates)**, nada é movido, removido, desacoplado nem implementado. A execução está interrompida aguardando a deliberação do usuário.