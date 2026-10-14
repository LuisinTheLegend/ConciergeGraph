# Backlog Final — Versão 2 (refeita de forma independente)

> **Status:** reconstrução independente da Fase 3. Gerada por `scratch/fase3_redo_build_v2.py` a partir de `scratch/fase3_redo_inventory.json` (16 relatórios da Fase 1). **Não** foi derivada de `audits/backlog-final.md`, que permanece intacto como versão v1.
> **Critério de trilha:** por relatório de origem (mecânico). IDs `V2-nnn` são independentes da numeração BL.
> **Exclusões:** 2 falsos positivos (`core-delta-manager.md` #2, `mock-vs-real-audit.md` #4) e 2 duplicatas (`mock-vs-real-audit.md` #1 = `core-vector-reconciler.md` #1; `mock-vs-real-audit.md` #2 = `core-delta-manager.md` #1).

## Trilha A. Fundação: Schema e Bootstrap

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-001 | Máxima | `schema-oficial-incompleto.md` #1 | storage/schema.py, storage/store.py, core/database.py | Omissão Estrutural de 5 Tabelas Relacionais no Bootstrap Oficial: O schema oficial de produção define apenas 8 tabelas legadas + 1 FTS5. As tabelas files, co... |
| V2-002 | Máxima | `schema-oficial-incompleto.md` #2 | 12 Módulos de core/ e interface/ | Inoperância Funcional de Todos os Subsistemas Analíticos em Instalação Limpa: Em um banco oficialmente bootstrapado, operações essenciais quebram imediatamen... |
| V2-003 | Crítica | `schema-oficial-incompleto.md` #4 | Suítes de Teste (tests/) | A Ilusão dos Testes (Test Mirage): A cobertura de testes do projeto mascara a quebra estrutural porque 14 suítes de teste independentes criam privadamente as... |
| V2-004 | Grave | `schema-oficial-incompleto.md` #3 | storage/store.py, storage/schema.py, core/database.py, core/checkpoint | Mascaramento Silencioso de Erros DDL e Falsa Confirmação no Boot: core/database.py::execute_write engole exceções retornando (False, error). AgnosticCheckpoi... |
| V2-005 | Média | `schema-oficial-incompleto.md` #5 | docs-grafo-concierge/01_ARCHITECTURE.md, storage/schema.py | Abandono de Especificação Arquitetural: A documentação formal de arquitetura em 01_ARCHITECTURE.md lista com clareza as 13 tabelas necessárias, divididas ent... |

## Trilha B. Persistência, Concorrência e Estado (storage, filas, checkpoints, janitor, rate governor)

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-006 | Crítica | `core-checkpointer.md` #1 | core/checkpointer.py | Despacho ambíguo em save_checkpoint baseado em heurística de tipos (len(args) == 4 and isinstance(args[3], str)). Na chamada real em mcp_server.py:1741 (agen... |
| V2-007 | Crítica | `core-rate-governor.md` #1 | core/rate_governor.py | Vazamento cumulativo de unfinished_tasks na PriorityQueue e starvation de cabeça de fila (Head-of-Line). Quando uma tarefa de baixa/média prioridade está con... |
| V2-008 | Crítica | `duplicacao-serialized-write-queue.md` #1 | storage/connection.py vs core/database.py (e interface/queue_writer.py | Colisão entre Fila Real (storage/) e Zero Fila (core/) sobre o Mesmo Banco: A arquitetura projetou duas classes SerializedWriteQueue, mas em produção (interf... |
| V2-009 | Crítica | `duplicacao-serialized-write-queue.md` #2 | interface/mcp_server.py e core/database.py | Ilusão dos Testes e Código Morto em Produção: interface/queue_writer.py é testada em 11 suites de teste (tests/), mas em produção (mcp_server.py:166) Concier... |
| V2-010 | Crítica | `storage.md` #1 | storage/connection.py | Deadlock Inevitável em Escritas Reentrantes/Aninhadas no SerializedWriteQueue: Qualquer operação executada dentro do worker da fila de escrita que tente invo... |
| V2-011 | Crítica | `storage.md` #6 | storage/vector_store.py, ,  storage/vector_store.py | Bypass de Isolamento Estrito (*Strict Scoping*) em ChromaVectorStore.search: Quando project_uuids=[], _build_where_filter não adiciona nenhum filtro de proje... |
| V2-012 | Grave | `core-background-janitor.md` #1 | core/background_janitor.py | Falha de slice negativo em Python (remaining[-keep_limit:]) quando keep_limit = 0. Ao solicitar a retenção exclusiva do ponto-zero inicial (keep_limit=0), o ... |
| V2-013 | Grave | `core-background-janitor.md` #2 | core/background_janitor.py | Degradação irreversível da prioridade do processo inteiro do servidor (p.nice(psutil.IDLE_PRIORITY_CLASS) ou nice(15)). O método process_community_summaries_... |
| V2-014 | Grave | `core-background-janitor.md` #3 | core/background_janitor.py | Destruição de ponto-zero e deleção cruzada de checkpoints entre agentes na mesma sessão. A chave primária de agent_checkpoints é (agent_id, session_id, check... |
| V2-015 | Grave | `core-checkpointer.md` #2 | core/checkpointer.py | Falha de atomicidade e mascaramento silencioso de falhas de rollback em execute_time_travel. O método monta duas queries separadas (DELETE FROM fsm_checkpoin... |
| V2-016 | Grave | `core-checkpointer.md` #3 | core/checkpointer.py | Granularidade temporal insuficiente (1 segundo via CURRENT_TIMESTAMP) em execute_time_travel impede remoção de checkpoints em rajadas rápidas. A coluna creat... |
| V2-017 | Grave | `core-rate-governor.md` #2 | core/rate_governor.py | Starvation de tarefas LOW envelhecidas em toda a faixa de 75% a 100% de carga. O branch de envelhecimento (aging) avalia se max_pct < 75.0 para promover a ta... |
| V2-018 | Grave | `core-rate-governor.md` #3 | core/rate_governor.py | Data Race / Lost Updates em get_current_metrics(). O método lê, filtra e reatribui self.history = [item for item in self.history if item[0] >= cutoff] sem ad... |
| V2-019 | Grave | `core-rate-governor.md` #4 | core/rate_governor.py | Deadlock permanente em submit_request se o governor não estiver rodando ou após shutdown(). submit_request enfileira a tarefa e bloqueia em req.future_result... |
| V2-020 | Grave | `duplicacao-serialized-write-queue.md` #3 | interface/queue_writer.py e core/database.py | Divergência de Integridade Referencial (foreign_keys=OFF): storage/connection.py ativa PRAGMA foreign_keys=ON;. Porém, interface/queue_writer.py e core/datab... |
| V2-021 | Grave | `duplicacao-serialized-write-queue.md` #4 | storage/connection.py vs interface/queue_writer.py | Timeout Assimétrico e Falha com OperationalError: database is locked: storage/connection.py configura PRAGMA busy_timeout=5000; (5 segundos). Já interface/qu... |
| V2-022 | Grave | `storage.md` #2 | storage/connection.py | Vazamento Perpétuo de Conexões SQLite de Threads Finalizadas: get_read_connection() retém referências fortes de todas as conexões criadas na lista _read_conn... |
| V2-023 | Grave | `storage.md` #4 | storage/relational_db.py ,  storage/store.py | Incompatibilidade de Contrato: init_fsm_checkpoints_schema Falha Silenciosamente: A função espera um gerenciador com execute_write ou write_query (padrão cor... |
| V2-024 | Grave | `storage.md` #5 | storage/logic.py | Falha de Tipo em _calculate_decay com Timestamps ISO Offset-Aware (Degradação para 0.01): A subtração entre datetime.utcnow() (offset-naive) e datetime.fromi... |
| V2-025 | Média | `core-background-janitor.md` #4 | core/background_janitor.py | Crash com TypeError em _summarize_community quando files.content é NULL. Se algum arquivo da comunidade tiver conteúdo nulo no SQLite (arquivos binários, arq... |
| V2-026 | Média | `core-background-janitor.md` #5 | core/background_janitor.py | TOCTOU / Descarte cego de is_dirty = 0 sobre arquivos modificados durante a geração da SLM. A chamada ao modelo local (local_slm_callback) leva de 5 a 30 seg... |
| V2-027 | Média | `core-checkpointer.md` #4 | core/checkpointer.py | Crash com json.JSONDecodeError não tratado em get_checkpoint. Ao contrário de load_checkpoint (que protege a deserialização com try ... except), get_checkpoi... |
| V2-028 | Média | `core-checkpointer.md` #5 | core/checkpointer.py | Falha de tipagem estática do Mypy e risco de TypeError: 'NoneType' object is not callable na resolução dinâmica de write_fn. O checkpointer usa getattr(..., ... |
| V2-029 | Média | `core-rate-governor.md` #5 | core/rate_governor.py | Cegueira de RPM no Fast-Path. Requisições prioritárias (prioridade 1) sob tráfego verde (< 50%) executam inline instantaneamente sem serem inseridas na fila.... |
| V2-030 | Média | `duplicacao-serialized-write-queue.md` #5 | interface/mcp_server.py | Quebra de Encapsulamento para Bifurcação de Estado: mcp_server.py acessa self._gc._store._conn_mgr._db_path (três atributos privados consecutivos) para criar... |
| V2-031 | Média | `storage.md` #3 | storage/connection.py | Falha ao Reiniciar SerializedWriteQueue após stop() (RuntimeError): O objeto threading.Thread é instanciado apenas uma vez no __init__. Se stop() for invocad... |
| V2-032 | Média | `storage.md` #7 | storage/vector_store.py, ,  storage/vector_store.py | Crash com ValueError em ChromaVectorStore.search por node_id Vazio ou None: O validador não checa o tipo de node_id. Se node_id=None for passado, _sanitize_m... |
| V2-033 | Média | `storage.md` #8 | storage/logic.py | Duplicação de Nós na CTE Recursiva get_dependency_tree: A projeção da CTE inclui dt.depth + 1 e utiliza UNION ALL. No SELECT DISTINCT * FROM dep_tree, como a... |
| V2-034 | Baixa | `storage.md` #9 | storage/semantic_logic.py ,  storage/store.py | Isolamento de semantic_logic.py e Violação de Encapsulamento em Módulos Externos: A fachada SqliteStore não expõe métodos para manipular a tabela semantic_fa... |

## Trilha C. Segurança e Governança

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-035 | Máxima | `bypass-governanca-por-session-id.md` #1 | interface/mcp_server.py ,  core/mcp_governor.py | Bypass Total da Governança de Ferramentas via Injeção de session_id Fantasma: concierge_set_state é READ_ONLY (sempre liberada). Qualquer agente restrito em ... |
| V2-036 | Crítica | `bypass-governanca-por-session-id.md` #2 | core/checkpointer.py ,  interface/mcp_server.py | Ausência Total de Verificação de Posse em Checkpoints (Independente do Achado #1): agent_get_checkpoint (READ_ONLY) e agent_save_checkpoint (LOCAL_MUTATION) ... |
| V2-037 | Crítica | `core-security-guard.md` #1 | core/security_guard.py | Regex de blacklist \brm\s+-rf\s+/ é facilmente contornada por variações canônicas de comandos destrutivos: rm -fr / (flags invertidas), rm -r -f /, rm --recu... |
| V2-038 | Grave | `bypass-governanca-por-session-id.md` #3 | interface/mcp_server.py | Vazamento de 100% do Catálogo em list_tools() (Falha no Progressive Disclosure): governed_list_tools só filtra se session_id for fornecido. Clientes MCP ofic... |
| V2-039 | Grave | `bypass-governanca-por-session-id.md` #4 | agent/run_agent.py ,  core/hsm_engine.py ,  interface/mcp_server.py | Desconexão Total do Runtime Cognitivo (CognitiveAgentRunner e HSMEngine Órfãos): A infraestrutura de Harel Statecharts (HSM), Deep History Nodes ($H^*$) e Ci... |
| V2-040 | Grave | `core-security-guard.md` #2 | core/security_guard.py | classify_command(command) não valida se command é None antes de executar self.blacklisted_patterns.search(command). Lança TypeError: expected string or bytes... |
| V2-041 | Média | `bypass-governanca-por-session-id.md` #5 | core/mcp_governor.py | Inicialização Insegura por Padrão (default_state = "EXECUTION"): O governor não inicia em PLANNING. Ferramentas de mutação física local (LOCAL_MUTATION, ex.:... |
| V2-042 | Média | `core-security-guard.md` #3 | core/security_guard.py | Concatenação ingênua de separador self.project_root + os.sep. Se project_root for a raiz de um disco ou volume (C:\ no Windows ou / no Linux), os.path.realpa... |
| V2-043 | Média | `core-security-guard.md` #4 | core/security_guard.py | Resolução de caminhos relativos em is_safe_path via os.path.realpath(target_path) resolve contra o os.getcwd() do processo em vez de self.project_root. Se o ... |
| V2-044 | Baixa | `core-security-guard.md` #5 | core/security_guard.py | Verificação de warning_terms usa busca ingênua de substring sem limites de palavra (any(term in command)). O termo "build" causa falsos positivos automáticos... |

## Trilha D. Ingestão, Reconciliação e Delta

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-045 | Crítica | `core-delta-manager.md` #1 | delta_manager.py / hsm_engine.py | hsm_engine.py:458 chama delta_manager.has_structural_change(target_task_id). Este método não existe no DeltaManager. Os únicos métodos públicos são: calculat... |
| V2-046 | Crítica | `core-vector-reconciler.md` #1 | core/vector_reconciler.py | Invocação de método fantasma self.vector_db.get_all_ids(). Conforme já identificado no Achado #1 de audits/mock-vs-real-audit.md, o método get_all_ids() não ... |
| V2-047 | Crítica | `core-vector-reconciler.md` #2 | core/vector_reconciler.py | Incompatibilidade de TIPO (int vs str) e Domínio Semântico -> Purga Total de Vetores (Catastrophic Data Loss). O reconciliador busca vector_ids no banco veto... |
| V2-048 | Crítica | `ingestion.md` #1 | ingestion/crawler.py ,  ingestion/orchestrator.py | find_node_by_hash busca nó apenas por (project_uuid, file_hash) ignorando relative_path. Ao renomear um arquivo sem alterar conteúdo, o crawler classifica o ... |
| V2-049 | Crítica | `ingestion.md` #2 | ingestion/orchestrator.py ,  ingestion/orchestrator.py | _step_summarize chama o LLM e retorna list[SummaryResult], mas essa lista nunca é atribuída aos chunks nem repassada para _step_store_sqlite. Em _step_store_... |
| V2-050 | Grave | `core-delta-manager.md` #6 | delta_manager.py | calculate_lbh() retorna "" para todo non-Python (LBH universalmente cego). calculate_ssh() captura apenas linhas cujo strip() começa com def /class /import /... |
| V2-051 | Grave | `core-vector-reconciler.md` #3 | core/vector_reconciler.py | Ausência de sincronização atômica e race condition destrutiva com ingestão concorrente (TOCTOU). reconcile_orphans() executa em segundo plano sem qualquer lo... |
| V2-052 | Grave | `ingestion.md` #3 | ingestion/summarizer.py ,  ingestion/orchestrator.py | summarize_l2 recebe project_name (folder_name, ex: "MeuProjeto") vindo do orquestrador e chama _store.update_project(project_name, summary=...). SqliteStore.... |
| V2-053 | Grave | `ingestion.md` #4 | ingestion/orchestrator.py ,  ingestion/orchestrator.py | Ao reingerir um arquivo modificado, _store.cleanup_obsolete_nodes deleta chunks antigos apenas no SQLite. O Step 7 (_step_garbage_collection), que reconcilia... |
| V2-054 | Média | `core-alias-tracker.md` #1 | core/alias_tracker.py | apply_alias_migration não é atômico. A função aplica UPDATEs em files, nodes, ast_edges e fsm_checkpoints em loop sequencial, onde cada chamada a execute_wri... |
| V2-055 | Média | `core-delta-manager.md` #3 | delta_manager.py | Todos os métodos internos (_insert_new_file, _update_structural_change, _update_content_only, compile_community_summary_jit) executam 2 write_query separadas... |
| V2-056 | Média | `core-vector-reconciler.md` #4 | core/vector_reconciler.py | Falta de paginação em lote e ausência de tratamento de exceções em delete_batch. O método passa a lista inteira de orphan_ids de uma só vez para self.vector_... |
| V2-057 | Média | `ingestion.md` #5 | ingestion/orchestrator.py ,  ingestion/orchestrator.py | Em _step_summarize, a Fase 2 checa if small_chunks and self._summarizer:, mas a Fase 3 (regular chunks) checa apenas if regular_chunks:. Se self._summarizer ... |
| V2-058 | Média | `ingestion.md` #6 | ingestion/crawler.py ,  ingestion/crawler.py | DEFAULT_IGNORE_PATTERNS inclui indevidamente "*.txt". Na inicialização do crawler sem .gitignore de usuário, a Camada 1 injeta essa regra, fazendo com que ar... |
| V2-059 | Média | `ingestion.md` #7 | ingestion/parser.py ,  ingestion/parser.py | _detect_tags faz busca ingênua de substring keyword in content_lower sem limites de palavra (\b). Termos comuns de código Python como chamadas à builtin next... |
| V2-060 | Média | `ingestion.md` #8 | ingestion/parser.py ,  ingestion/parser.py | O parser de JS/TS usa contagem ingênua de caracteres { e } (_find_block_end_braces) sem máquina de estados léxica. Strings contendo chaves (ex.: templates HT... |
| V2-061 | Baixa | `core-delta-manager.md` #4 | delta_manager.py | compile_community_summary_jit() linha 186: payload = "\n".join(row[0] for row in files). Se files.content for NULL no banco, row[0] é None e o str.join() lan... |
| V2-062 | Observação | `core-delta-manager.md` #5 | delta_manager.py | calculate_ssh() captura todas as linhas com prefixos def , class , import , from  independentemente de indentação (usa line.strip()). Isso significa que def ... |

## Trilha E. Telemetria e Dashboard

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-063 | Crítica | `grafo-dashboard-web.md` #1 | lib/useTelemetryStream.ts | Código Morto em Handlers SSE e Telemetria Reativa Congelada: lib/useTelemetryStream.ts implementa switch (raw.event_type) para "RATE_GOVERNOR_UPDATE", "HSM_S... |
| V2-064 | Crítica | `grafo-dashboard-web.md` #2 | lib/useTelemetryStream.ts, interface/telemetry_api.py | Ciclo Infinito de Flapping SSE e Inundação do Buffer de Eventos: No backend, max_checks = 5 aborta o gerador SSE após 5s. No frontend, es.onerror captura a q... |
| V2-065 | Crítica | `grafo-dashboard-web.md` #3 | package.json, .env.local, lib/mcp/client.ts | Colisão de Portas, Inoperância do Script dev:all e Desconexão do FastMCP SSE: main.py roda FastMCP em stdio (ou porta 8000 se SSE); o FastAPI telemetry_api.p... |
| V2-066 | Crítica | `interface-telemetry-api.md` #1 | interface/telemetry_api.py | Falha Fatal em Produção por Suposição de Esquema Inexistente (OperationalError: no such table: files e agent_checkpoints): _build_telemetry_payload executa S... |
| V2-067 | Crítica | `interface-telemetry-api.md` #2 | interface/telemetry_api.py | Inoperância Fora da Caixa por Dependência Não Configurada (RuntimeError): _db_manager_instance inicia como None. get_db_manager() é exigido por quase todos o... |
| V2-068 | Grave | `grafo-dashboard-web.md` #4 | lib/mcp/client.ts, interface/mcp_server.py | Incompatibilidade de Autenticação FastMCP e Rejeição Total com HTTP 401: O backend ativa validação HTTP quando GRAFO_API_KEY existe. O frontend usa EventSour... |
| V2-069 | Grave | `grafo-dashboard-web.md` #5 | storage/store.py, app/hooks/useGraphTopology.ts, app/components/Inspec | Omissão de Metadados em get_full_topology e Esvaziamento do InspectorDrawer: store.get_lightweight_topology() projeta apenas id, label, node_type e omite del... |
| V2-070 | Grave | `interface-telemetry-api.md` #3 | interface/telemetry_api.py | Falso Stream Contínuo: SSE Aborta após 5 Segundos por Trava de Teste Codificada em Produção (max_checks = 5): O gerador assíncrono _telemetry_event_generator... |
| V2-071 | Grave | `interface-telemetry-api.md` #4 | interface/telemetry_api.py | Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico (datetime.now()): O gerador SSE promete emitir dados apenas quando o hash do payload mudar. Por... |
| V2-072 | Grave | `interface-telemetry-api.md` #5 | interface/telemetry_api.py | Insegurança Total de CORS e Ausência Completa de Autenticação em Endpoints Mutantes: Configuração de CORS com allow_origins=["*"] e allow_credentials=True co... |
| V2-073 | Média | `grafo-dashboard-web.md` #6 | app/components/CoreMemoryPanel.tsx | Risco de Crash e Corrupção de Data (Invalid Date) em CoreMemoryPanel: CoreMemoryPanel.tsx:137 concatena + "Z" cegamente em block.updated_at. Se o backend env... |
| V2-074 | Média | `grafo-dashboard-web.md` #7 | app/page.tsx, components/hsm/HSMStateInspector.tsx | Rotas Mutantes Órfãs e Callbacks Inertes no HUD: HSMStateInspector renderiza botões para cada sub-estado que disparam onSelectState(qualified). No entanto, a... |
| V2-075 | Média | `grafo-dashboard-web.md` #8 | components/telemetry/LiveEventFeed.tsx, lib/useTelemetryStream.ts | 37 Erros de Linter, Impureza em Render React 19 e Efeitos em Cascata: LiveEventFeed.tsx invoca Date.now() dentro do render em useMemo violando regras de funç... |
| V2-076 | Média | `interface-telemetry-api.md` #6 | interface/telemetry_api.py | Dessincronização de Esquema e Crash de Tipagem em Timestamps (NoneType e str): (1) _build_telemetry_payload chama datetime.fromtimestamp(ts), falhando com Ty... |
| V2-077 | Média | `interface-telemetry-api.md` #7 | interface/telemetry_api.py | Thread Daemônica Órfã e Singletons Desconectados no Import do Módulo: A mera importação de interface.telemetry_api (feita por interface/mcp_server.py:151) in... |

## Trilha F. Runtime Cognitivo e Contratos de Mock

| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |
|---|---|---|---|---|
| V2-078 | Crítica | `agent-and-agents.md` #1 | agent/run_agent.py | Contaminação de Turnos Multi-Sessão no Circuit Breaker: self.current_substate_turn_count é um inteiro único de instância da classe compartilhado entre todas ... |
| V2-079 | Crítica | `agent-and-agents.md` #2 | agents/revisor_critico.py | Vazamento de Privacidade por Fallback Inseguro e Sensibilidade a Caixa (Case-Sensitivity): check_contamination usa privacy_hierarchy.get(source_privacy, 0) s... |
| V2-080 | Grave | `agent-and-agents.md` #3 | agents/revisor_critico.py | Aprovação Espúria de Commits Inválidos e Incompatibilidade de Assinatura em audit_with_retry: O docstring prescreve Callable(task, outcome, feedback), mas o ... |
| V2-081 | Grave | `agent-and-agents.md` #4 | agent/run_agent.py | Dessincronização de Estado e Diretrizes em step(target_transition=...): step() constrói o prompt dinâmico usando o estado ANTERIOR (current_path) e só depois... |
| V2-082 | Grave | `agent-and-agents.md` #5 | agents/revisor_critico.py | Defeitos de Tipagem e Crash em Reranking (NoneType e int vs str): (1) _heuristic_rerank quebra com TypeError se algum nó contiver score_final: None; (2) _llm... |
| V2-083 | Grave | `mock-vs-real-audit.md` #3 | tests/test_cognitive_routing_memory.py / core/federated_knowledge_rout | MockExternalMCP define query_docs(self, query). O roteador FederatedKnowledgeRouter (core/federated_knowledge_router.py:73) invoca self.external_mcp.query_do... |
| V2-084 | Média | `agent-and-agents.md` #6 | agent/run_agent.py | Incompatibilidade Estrutural Universal com Corrotinas e Bypass do RateGovernor em execute_tool: Funções assíncronas (async def) nunca funcionam corretamente ... |
| V2-085 | Média | `agent-and-agents.md` #7 | agent/agent_prompts.py | Dessincronização Estrutural entre Sub-Estados do HSM e TOOL_DISCLOSURE_MATRIX: parse_state_path decompõe apenas o super-estado. As entradas de sub-estados de... |
| V2-086 | Média | `mock-vs-real-audit.md` #5 | tests/test_vector_reconciler.py / storage/base_backend.py | MockVectorDatabase define insert(vector_id, payload). insert não existe em BaseVectorBackend nem em ChromaVectorStore (o método real de produção é store_embe... |
| V2-087 | Média | `mock-vs-real-audit.md` #6 | tests/test_cognitive_routing_memory.py / core/graph_rag.py | MockGraphRAGEngine.retrieve_multihop_context(query) aceita texto puro de query e retorna str. A classe real GraphRAGEngine.retrieve_multihop_context(entry_no... |
| V2-088 | Baixa | `mock-vs-real-audit.md` #7 | tests/test_interface_contracts.py / storage/base_backend.py | _MockVectorStore.reset_collection() é testado como se fizesse parte da interface de vetor, mas reset_collection existe apenas na classe concreta ChromaVector... |

## Totais

| Severidade | Qtde |
|---|---|
| Máxima | 3 |
| Crítica | 21 |
| Grave | 30 |
| Média | 29 |
| Baixa | 4 |
| Observação | 1 |
| **Total** | **88** |

## Candidatos adicionais (itens da Fase 1 do AUDIT_PROTOCOL.md sem relatório em `audits/`)

Não numerados e fora dos totais acima: não têm relatório de origem, então não passam pela mesma exigência de rastreabilidade. Ver `audits/comparacao-fase3.md` §5 para evidências.

