# Backlog Final — Auditoria do Grafo Concierge

> **Fase:** 3 — Consolidação (`backlog-final`)  
> **Data:** 2026-09-30  
> **Fonte:** 15 relatórios de `audits/*.md` (Fase 1) + [`audits/cruzamento-modulos.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/cruzamento-modulos.md) (Fase 2)  
> **Total de achados confirmados:** 79 (3 Máxima + 20 Crítica + 27 Grave + 26 Média + 3 Baixa)  
> **Status:** Concluído

---

## Como ler este documento

Cada item do backlog corresponde a **um achado confirmado com reprodução empírica** da Fase 1. Os itens estão agrupados por severidade (decrescente) e, dentro de cada severidade, ordenados por impacto sistêmico transversal (cadeias que afetam mais módulos vêm primeiro).

**Colunas:**
- **ID**: Identificador único `BL-NNN`
- **Título**: Nome resumido do achado
- **Módulo(s)**: Arquivo(s) de produção afetado(s)
- **Relatório de Origem**: Link para o `audits/*.md` onde o achado foi documentado e reproduzido
- **Cadeia Transversal**: Referência ao eixo da Fase 2, quando aplicável

---

## 🔴🔴 PRIORIDADE MÁXIMA (3 achados)

> [!CAUTION]
> Estes achados tornam o sistema **completamente inoperante ou inseguro em qualquer instalação limpa**. Devem ser resolvidos antes de qualquer outra correção.

| ID | Título | Módulo(s) | Relatório | Cadeia |
|---|---|---|---|---|
| **BL-001** | **Schema incompleto: 5 tabelas críticas ausentes do bootstrap** — `files`, `communities`, `ast_edges`, `agent_checkpoints`, `fsm_checkpoints` não possuem DDL em nenhum arquivo de produção. Crash imediato com `OperationalError: no such table` em 12+ módulos após `git clone`. | `storage/schema.py`, `storage/store.py` | [`schema-oficial-incompleto.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/schema-oficial-incompleto.md) #1 | Eixo Central §1.2 |
| **BL-002** | **Test Mirage: 14 suítes mascaram schema ausente** — Testes criam privadamente as 5 tabelas em `setUp()`, passando com 100% de sucesso enquanto produção é inoperante. Falsa confirmação de integridade no log: `Schema v3.8.0 verified - all tables and triggers OK`. | `storage/store.py:107`, 14 suítes de teste | [`schema-oficial-incompleto.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/schema-oficial-incompleto.md) #2, #3 | Eixo Central §1.2 |
| **BL-003** | **Bypass total da governança via `session_id` fantasma** — `concierge_set_state` (READ_ONLY) permite criar sessão efêmera em MAINTENANCE; agente restrito em PLANNING invoca ferramentas DANGEROUS (ex.: `reset_collection`). FastMCP descarta parâmetro extra não declarado. | `interface/mcp_server.py:249-259`, `core/mcp_governor.py:100,128-193` | [`bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md) #1 | Cadeia §6.3 |

---

## 🔴 CRÍTICA (20 achados)

> [!WARNING]
> Achados que causam **perda de dados, corrupção silenciosa, falha de segurança ou inoperância de subsistemas inteiros**.

| ID | Título | Módulo(s) | Relatório | Cadeia |
|---|---|---|---|---|
| **BL-004** | **Colisão fila real vs zero fila sobre o mesmo banco** — `ConciergeDatabaseManager` instanciado com `write_queue=None` em produção; conexões efêmeras cruas de `core/` colidem com a fila serializada de `storage/connection.py` sobre `data/concierge.db`. | `core/database.py:56-70`, `interface/mcp_server.py:166`, `storage/connection.py:59` | [`duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) #1 | Eixo Central §1.1 |
| **BL-005** | **Código morto em produção: `queue_writer.py`** — Testada em 11 suítes mas jamais instanciada no servidor MCP; falsa garantia de serialização nos testes. | `interface/queue_writer.py`, `interface/mcp_server.py:166` | [`duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) #2 | Eixo Central §1.1 |
| **BL-006** | **Ausência de verificação de posse em checkpoints** — `agent_get_checkpoint` e `agent_save_checkpoint` abertas em EXECUTION sem filtro de `agent_id`; exfiltração de segredos e envenenamento de qualquer agente. | `core/mcp_governor.py:39`, `interface/mcp_server.py:890-950` | [`bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md) #2 | Cadeia §6.3 |
| **BL-007** | **Método fantasma `get_all_ids()` no vector_reconciler** — `vector_reconciler.py:39` chama método inexistente em `BaseVectorBackend`/`ChromaVectorStore`; `AttributeError` fatal. | `core/vector_reconciler.py:39`, `storage/base_backend.py` | [`core-vector-reconciler.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-vector-reconciler.md) #1 | Cadeia §6.1 |
| **BL-008** | **Purga total de vetores por incompatibilidade `int` vs `str`** — Se BL-007 for corrigido isoladamente, `get_all_stored_node_ids()` retorna `set[int]` vs `SELECT path` retorna `set[str]`; interseção vazia → purga de 100% dos vetores legítimos. Exige correção simultânea com BL-007. | `core/vector_reconciler.py:44-52` | [`core-vector-reconciler.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-vector-reconciler.md) #2 | Cadeia §6.1 |
| **BL-009** | **Despacho ambíguo em `save_checkpoint`** — Heurística `len(args)==4 and isinstance(args[3], str)` desvia chamadas de `agent_save_checkpoint` para `fsm_checkpoints` com inversão de colunas e `shared_state="{}"`. | `core/checkpointer.py:73-117` | [`core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) #1 | — |
| **BL-010** | **Método fantasma `has_structural_change()` no delta_manager** — `hsm_engine.py:458` chama método inexistente em `DeltaManager`; mascarado por `MockDeltaManager`. | `core/delta_manager.py`, `core/hsm_engine.py:458` | [`core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) #1 | §2.2 |
| **BL-011** | **Evasão da blacklist de comandos do SecurityGuard** — `rm -fr /`, `rm -r -f /`, `rm -rf .`, `del /s`, `format`, comandos Windows contornam regex. | `core/security_guard.py` | [`core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) #1 | Cadeia §6.4 |
| **BL-012** | **Deadlock de `unfinished_tasks` + starvation no RateGovernor** — Vazamento perpétuo em `PriorityQueue`; starvation de LOW/MEDIUM durante congelamento; deadlock permanente com `join()`. | `core/rate_governor.py` | [`core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) #1 | — |
| **BL-013** | **Deadlock inevitável em escritas aninhadas no `SerializedWriteQueue`** — Reentrância no worker thread trava permanentemente. | `storage/connection.py:59-120` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #1 | — |
| **BL-014** | **Bypass de Strict Scoping com `project_uuids=[]`** — Busca vetorial retorna dados de **todos** os projetos quando lista de UUIDs está vazia. | `storage/vector_store.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #6 | §3.1 |
| **BL-015** | **Perda total no grafo na renomeação de arquivos** — `find_node_by_hash` ignora caminhos; arquivo renomeado colide no hash e GC purga o antigo. | `ingestion/crawler.py:560`, `ingestion/orchestrator.py:765` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #1 | Cadeia §6.1 |
| **BL-016** | **Descarte silencioso de 100% dos resumos L0** — `_step_summarize` descarta retorno do LLM; `nodes.summary=NULL`; esteriliza L1 e L2. | `ingestion/orchestrator.py:191,571,843` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #2 | Cadeia §6.2 |
| **BL-017** | **Crash HTTP 500 na telemetria por tabelas inexistentes** — `telemetry_api.py` consulta `files` e `agent_checkpoints` ausentes do schema. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #1 | Cadeia §6.2 |
| **BL-018** | **Inoperância fora da caixa da telemetria** — `get_db_manager` lança `RuntimeError` por dependência não configurada. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #1b | Cadeia §6.2 |
| **BL-019** | **Handlers SSE mortos no dashboard** — `event_type` ausente no backend; `QuotaGauges` e `HSMStateInspector` permanentemente congelados. | `grafo-dashboard-web/` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #1 | Cadeia §6.2 |
| **BL-020** | **Flapping SSE cíclico a cada 8s** — `max_checks=5` mantido em produção; 75 reconexões/10min inundando o feed e fazendo HUD piscar. | `grafo-dashboard-web/`, `interface/telemetry_api.py` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #2 | Cadeia §6.2 |
| **BL-021** | **Colisão de portas 8000 entre FastAPI e FastMCP** — Script `dev:all` inoperante; FastMCP SSE desconectado pela porta órfã 7077. | `grafo-dashboard-web/` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #3 | — |
| **BL-022** | **Contaminação de turnos multi-sessão no Circuit Breaker** *(CONDICIONAL: código órfão)* — Contador `current_substate_turn_count` único de instância; reset indevido afeta todos os agentes. | `agent/run_agent.py` | [`agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md) #1 | — |
| **BL-023** | **Vazamento de privacidade por fallback Fail-Open** *(CONDICIONAL)* — `check_contamination` faz `.get(source_privacy, 0)` sem `.upper()`; rótulos em minúsculas recebem nível 0 (PUBLIC). | `agents/revisor_critico.py` | [`agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md) #2 | §3.3 |

---

## 🟠 GRAVE (27 achados)

| ID | Título | Módulo(s) | Relatório | Cadeia |
|---|---|---|---|---|
| **BL-024** | **Divergência de `foreign_keys` (ON vs OFF)** — `core/` grava arestas/registros órfãos sem FKs; `storage/` rejeita com `IntegrityError`. | `core/database.py:60`, `storage/connection.py:155` | [`duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) #3 | §2.3 |
| **BL-025** | **Timeout assimétrico (5s vs 30s)** — `storage/` aborta prematuramente com `database is locked` enquanto `core/` bloqueia por 30s. | `storage/connection.py:154`, `core/database.py` | [`duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) #4 | §2.4 |
| **BL-026** | **Mascaramento silencioso em `execute_time_travel`** — Retorno de falha descartado; método reporta sucesso sem rollback real (quando tabela existe mas escrita falha). | `core/checkpointer.py:195-210` | [`core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) #2 | — |
| **BL-027** | **Granularidade de 1s em `CURRENT_TIMESTAMP`** — Checkpoints no mesmo segundo sobrevivem ao time-travel, quebrando determinismo. | `core/checkpointer.py:196` | [`core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) #3 | — |
| **BL-028** | **Slice negativo `[-0:]` preserva 100% dos checkpoints** — `keep_limit=0` no janitor nunca deleta nada. | `core/background_janitor.py` | [`core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) #1 | — |
| **BL-029** | **Degradação irreversível de prioridade para IDLE** — Processo servidor inteiro rebaixado por `psutil.Process().nice(IDLE_PRIORITY_CLASS)`. | `core/background_janitor.py` | [`core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) #2 | — |
| **BL-030** | **Deleção cruzada de checkpoints entre agentes** — `_prune_single_session` agrupa por `session_id` sem filtrar `agent_id`. | `core/background_janitor.py` | [`core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) #3 | Cadeia §6.3 |
| **BL-031** | **Race condition TOCTOU no vector_reconciler** — Ausência de locks; ingestão concorrente pode adicionar vetores entre leitura e deleção. | `core/vector_reconciler.py` | [`core-vector-reconciler.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-vector-reconciler.md) #3 | — |
| **BL-032** | **Anti-starvation aging inalcançável durante congelamento** — Incremento de prioridade nunca ultrapassa threshold do RateGovernor. | `core/rate_governor.py` | [`core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) #2 | — |
| **BL-033** | **Data race em `get_current_metrics`** — Leitura de métricas sem lock; lost updates. | `core/rate_governor.py` | [`core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) #3 | — |
| **BL-034** | **Deadlock eterno em `submit_request`** — Sem timeout e após `shutdown()`, chamadores bloqueiam para sempre. | `core/rate_governor.py` | [`core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) #4 | — |
| **BL-035** | **Vazamento de conexões SQLite zumbi** — Threads finalizadas deixam conexões abertas em `_read_connections` do `ConnectionManager`. | `storage/connection.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #2 | — |
| **BL-036** | **`init_fsm_checkpoints_schema` falha silenciosamente** — Incompatibilidade de contrato; tabela nunca criada efetivamente. | `storage/relational_db.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #3 | Eixo Central §1.2 |
| **BL-037** | **Timestamp offset-aware degrada score de recência** — `_calculate_decay` falha com `TypeError`; score cai para mínimo 0.01 sempre. | `storage/logic.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #5 | §2.1 |
| **BL-038** | **Falha de persistência do L2 Compass** — `folder_name` enviado onde `uuid` é exigido; `UPDATE` com 0 matches + falsa confirmação no log. | `ingestion/summarizer.py:789`, `ingestion/orchestrator.py:880` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #3 | Cadeia §6.2 |
| **BL-039** | **Vetores zumbis acumulam perpetuamente no ChromaDB** — Step 7 de GC pulado porque `deleted_node_ids` é vazio em modificações. | `ingestion/orchestrator.py:213,234` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #4 | Cadeia §6.1 |
| **BL-040** | **SSE aborta e desconecta clientes após 5s** — `max_checks=5` mantida em produção na telemetria. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #3 | Cadeia §6.2 |
| **BL-041** | **Hash SHA-256 invalidado perpetuamente no SSE** — `datetime.now()` dinâmico quebra filtro de broadcast. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #4 | — |
| **BL-042** | **CORS inseguro `allow_origins=['*']` com `allow_credentials=True`** — Sem autenticação em rotas mutantes; CSRF permitido. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #5 | — |
| **BL-043** | **Vazamento de 100% do catálogo de ferramentas em `list_tools()`** — Sem `session_id` no protocolo; todas as 31 ferramentas expostas. | `interface/mcp_server.py:261-270` | [`bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md) #3 | §3 |
| **BL-044** | **Desconexão total do runtime cognitivo** — `CognitiveAgentRunner` e `HSMEngine` não existem em produção no servidor MCP. | `agent/run_agent.py`, `core/hsm_engine.py` | [`bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md) #4 | §4 |
| **BL-045** | **Incompatibilidade de autenticação FastMCP no dashboard** — `EventSource` nativo não suporta headers customizados; HTTP 401 imediato. | `grafo-dashboard-web/` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #4 | — |
| **BL-046** | **InspectorDrawer vazio por metadados ausentes** — `get_full_topology` omite `summary` e `tags`; clique em nós do grafo 3D/2D não exibe nada. | `grafo-dashboard-web/`, `interface/mcp_server.py` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #5 | — |
| **BL-047** | **Aprovação espúria de commits inválidos** *(CONDICIONAL)* — `partial_audit=True` após falha em `generate_fn` em `audit_with_retry`. | `agent/run_agent.py` | [`agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md) #3 | — |
| **BL-048** | **Dessincronização prompt ↔ estado ativo** *(CONDICIONAL)* — `step(target_transition=...)` gera alucinações e bloqueios cognitivos. | `agent/run_agent.py` | [`agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md) #4 | — |
| **BL-049** | **Crash em reranking por `int` vs `str` e `NoneType`** *(CONDICIONAL)* — `_llm_rerank` faz `int(nid)` em strings e None. | `agents/revisor_critico.py` | [`agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md) #5 | §2.1 |
| **BL-050** | **Mascaramento de DDL + falsa confirmação no log de boot** — `execute_write` suprime exceções; `verify_tables_exist` valida subset restrito; log diz "all tables OK" com 5 tabelas ausentes. | `core/database.py`, `storage/store.py:107` | [`schema-oficial-incompleto.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/schema-oficial-incompleto.md) #3 | Eixo Central §1.2 |

---

## 🟡 MÉDIA (26 achados)

| ID | Título | Módulo(s) | Relatório |
|---|---|---|---|
| **BL-051** | **Quebra de encapsulamento `_gc._store._conn_mgr._db_path`** — 3 atributos privados consecutivos para criar segunda conexão. | `interface/mcp_server.py:162` | [`duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) #5 |
| **BL-052** | **Crash `json.JSONDecodeError` em `get_checkpoint`** — Blob truncado/corrompido derruba ferramenta MCP. | `core/checkpointer.py:226-234` | [`core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) #4 |
| **BL-053** | **Tipagem insegura: `None` not callable** — 4 erros Mypy em `checkpointer.py` por `getattr(..., None)` sem validação. | `core/checkpointer.py:112-113,137-138,201-206` | [`core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) #5 |
| **BL-054** | **Crash `TypeError` em `_summarize_community` com `content=NULL`** | `core/background_janitor.py` | [`core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) #4 |
| **BL-055** | **TOCTOU: descarte cego de `is_dirty=0` durante SLM** — Arquivos modificados durante sumarização são marcados como limpos. | `core/background_janitor.py` | [`core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) #5 |
| **BL-056** | **Falta de paginação e tratamento em `delete_batch`** no reconciliador vetorial. | `core/vector_reconciler.py` | [`core-vector-reconciler.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-vector-reconciler.md) #4 |
| **BL-057** | **Cegueira de RPM no Fast-Path do RateGovernor** — Sem registro em `self.history`. | `core/rate_governor.py` | [`core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) #5 |
| **BL-058** | **Bug de barra dupla `C:\\\\` bloqueia 100% dos arquivos na raiz** | `core/security_guard.py` | [`core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) #3 |
| **BL-059** | **Resolução de caminhos relativos ancorada ao CWD** — Não usa `project_root`. | `core/security_guard.py` | [`core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) #4 |
| **BL-060** | **`classify_command(None)` lança `TypeError` não tratado** | `core/security_guard.py` | [`core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) #2 |
| **BL-061** | **`calculate_lbh()` retorna `""` para não-Python** — Cobertura linguística limitada silenciosamente. | `core/delta_manager.py` | [`core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) #4 |
| **BL-062** | **Dupla conexão efêmera por mutação no delta_manager** — 2 `write_query` sem transação envolvente. | `core/delta_manager.py` | [`core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) #3 |
| **BL-063** | **`RuntimeError` ao reiniciar `SerializedWriteQueue` após `stop`** | `storage/connection.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #4 |
| **BL-064** | **Crash `ValueError` em busca vetorial com `node_id=None`/string vazia** | `storage/vector_store.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #7 |
| **BL-065** | **Duplicação de nós na CTE `get_dependency_tree`** — `depth` em `SELECT DISTINCT`. | `storage/logic.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #8 |
| **BL-066** | **Crash com `AttributeError` quando `summarizer=None`** | `ingestion/orchestrator.py:442,449` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #5 |
| **BL-067** | **Arquivos `.txt` ignorados por padrão** — `DEFAULT_IGNORE_PATTERNS` contém `*.txt`. | `ingestion/crawler.py:395,481` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #6 |
| **BL-068** | **Poluição de tags por substring ingênua** — `keyword in content_lower` adiciona tags falsas. | `ingestion/parser.py:100-111,973-975` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #7 |
| **BL-069** | **Quebra de parsing JS/TS por contador ingênuo de chaves** | `ingestion/parser.py:701-715` | [`ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md) #8 |
| **BL-070** | **Dessincronização `agent_checkpoints` vs `fsm_checkpoints`** — Crash de tipagem em timestamps. | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #6 |
| **BL-071** | **Thread daemônica iniciada desnecessariamente no import** | `interface/telemetry_api.py` | [`interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) #7 |
| **BL-072** | **Servidor inicia em `EXECUTION` em vez de `PLANNING`** | `core/mcp_governor.py:37-38` | [`bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md) #5 |
| **BL-073** | **Corrupção de data `Invalid Date` por `+ "Z"` duplicado** no dashboard. | `grafo-dashboard-web/CoreMemoryPanel` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #6 |
| **BL-074** | **Rotas mutantes `/api/hsm/transition` órfãs; cliques inertes** — `onSelectState` omitida. | `grafo-dashboard-web/` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #7 |
| **BL-075** | **37 erros de linter; violação de funções puras no React 19** | `grafo-dashboard-web/LiveEventFeed` | [`grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md) #8 |
| **BL-076** | **Abandono de especificação formal** — `01_ARCHITECTURE.md` especificava 13 tabelas; apenas 8 implementadas. | `storage/schema.py` | [`schema-oficial-incompleto.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/schema-oficial-incompleto.md) #4 |

---

## 🔵 BAIXA (3 achados)

| ID | Título | Módulo(s) | Relatório |
|---|---|---|---|
| **BL-077** | **Falso positivo de WARNING por substring match em `"build"`** | `core/security_guard.py` | [`core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) #5 |
| **BL-078** | **Isolamento total de `semantic_logic` na fachada `SqliteStore`** — Forçando quebra de encapsulamento. | `storage/store.py` | [`storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md) #9 |
| **BL-079** | **Retorno `""` silencioso de `calculate_ssh` para linguagens sem suporte** | `core/delta_manager.py` | [`core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) #5 |

---

## Resumo Executivo

```
┌─────────────────────────────────────────────────────────────────┐
│                 BACKLOG FINAL — 79 ACHADOS                      │
│                                                                 │
│  🔴🔴 MÁXIMA  ███                                    3  ( 3.8%) │
│  🔴  CRÍTICA  ████████████████████                  20  (25.3%) │
│  🟠  GRAVE    ███████████████████████████           27  (34.2%) │
│  🟡  MÉDIA    ██████████████████████████            26  (32.9%) │
│  🔵  BAIXA    ███                                    3  ( 3.8%) │
│                                                                 │
│  CRÍTICOS+GRAVES: 50 achados (63.3%)                            │
│  Módulos afetados: 13 subsistemas                               │
│  Cadeias transversais: 4 (Eixo Central + 3 cadeias)            │
│  Código morto/órfão: 6 componentes                              │
│  Test Mirage: 14 suítes mascarando bugs de produção             │
│                                                                 │
│  RECOMENDAÇÃO DE CORREÇÃO (ORDEM):                              │
│  1. BL-001/002  Schema unificado (desbloqueia 12+ módulos)      │
│  2. BL-004/005  Unificação da camada de escrita                 │
│  3. BL-003/006  Segurança e governança                          │
│  4. BL-007/010  Contratos mock→real                             │
│  5. BL-022/044  Reconexão ou expurgo do código órfão            │
│  6. BL-019-021  Frontend e telemetria                           │
└─────────────────────────────────────────────────────────────────┘
```

### Dependências Críticas de Correção

> [!IMPORTANT]
> **BL-007 e BL-008 DEVEM ser corrigidos simultaneamente.** Corrigir BL-007 (`get_all_ids` → `get_all_stored_node_ids`) isoladamente faz o sistema passar de "seguro por estar quebrado" (crash no `AttributeError`) para "roda e purga 100% dos vetores legítimos" (por incompatibilidade `int` vs `str`).

> [!IMPORTANT]
> **BL-001 desbloqueia 12+ módulos.** A maioria dos achados de `core/` e `interface/telemetry_api.py` é agravada ou ocultada pela ausência das 5 tabelas do schema. Resolvê-lo primeiro permite que os demais bugs se manifestem e sejam testáveis.

---

*Backlog gerado a partir dos 15 relatórios de auditoria da Fase 1 e da síntese transversal da Fase 2, conforme as diretrizes do AUDIT_PROTOCOL.md.*
