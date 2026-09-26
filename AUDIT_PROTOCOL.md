# Protocolo de Auditoria — Grafo Concierge

> Este arquivo é o "estado" da auditoria. O agente lê este documento, executa o
> próximo item não concluído, atualiza este próprio arquivo, e PARA. O humano
> aprova em uma frase curta e o agente continua a partir do arquivo — nunca a
> partir de um novo prompt reescrito do zero.

---

## Regras Globais (aplicam-se a TODO item deste documento, sem exceção)

1. Você é um auditor de código cético, não um redator de relatório. Sua saída
   não vale nada se não for verificável.
2. NUNCA reporte um achado ("bug", "risco", "inconsistência") sem: (a) arquivo
   e linha exatos, (b) o mecanismo técnico explicado, (c) uma reprodução real
   que você EXECUTOU — teste pytest, script, ou traceback real. Cole a saída
   bruta do terminal como prova.
3. Se não conseguir reproduzir, classifique como `HIPÓTESE NÃO CONFIRMADA` e
   diga exatamente o que faltou para confirmar. Nunca apresente hipótese como
   fato.
4. Escopo estrito: trabalhe SOMENTE no item marcado como "▶ EM ANDAMENTO"
   abaixo. Se notar algo relevante fora do escopo, anote em
   `audits/fora-de-escopo.md` — não investigue agora.
5. Antes de ler código manualmente, rode as ferramentas estáticas relevantes
   ao escopo do item (pytest, ruff, mypy, bandit) e inclua a saída bruta no
   relatório.
6. Formato de saída obrigatório por achado, em `audits/<slug-do-item>.md`:
   tabela com colunas `arquivo | linha | severidade | mecanismo | reprodução
   | status (confirmado/hipótese)`.
7. **GATE OBRIGATÓRIO** — ao concluir um item: marque-o `[x]` neste arquivo,
   escreva o relatório em `audits/`, gere o Walkthrough/artefato de resumo, e
   **PARE completamente**. Não inicie o próximo item `[ ]` até receber um
   comentário explícito de aprovação do humano ("aprovado", "pode seguir",
   "continue" — só essas frases liberam avanço). Isso vale mesmo dentro da
   mesma missão/sessão.
8. Durante as Fases 1 e 2 (auditoria), NUNCA edite código de produção. São
   fases somente-leitura + escrita de relatórios em `audits/`.
9. Ao terminar um item, marque neste arquivo qual será o próximo com
   "▶ EM ANDAMENTO", deixando claro para a próxima rodada onde retomar.
10. Se o humano pedir uma correção pontual num achado já reportado, aplique
    a correção diretamente no arquivo de relatório correspondente antes de
    considerar o item fechado — reconhecer no chat não é suficiente, o
    arquivo é a fonte de verdade.
11. Commit obrigatório a cada gate. Imediatamente após marcar um item [x] e antes de reportar o Walkthrough como concluído, rode: git add -A && git commit -m "docs(audit): <slug-do-item> concluído". O trabalho de auditoria é feito em múltiplas máquinas (PC e notebook) — nunca deixe um item aprovado sem commit. Antes de encerrar qualquer sessão (fim de dia, troca de máquina), rode git push e confirme a saída ao humano. Ao iniciar uma sessão numa máquina diferente, rode git pull e git status ANTES de ler o item ▶ EM ANDAMENTO, e reporte o resultado — nunca assuma que o estado local está atualizado.
---

## Fase 0 — Baseline objetiva (sem interpretação)

- [ ] **fase0-baseline** — Rodar, nesta ordem, e salvar saída bruta completa
  em `audits/fase0-baseline.md`: `pytest -v --tb=short`,
  `pytest --collect-only -q`, `pytest --cov=core --cov=interface
  --cov=storage --cov-report=term-missing`, `ruff check .`, `mypy .`,
  `bandit -r .`, `pip-audit`, `npm audit` (pasta do dashboard, se existir).
  Não interpretar ainda, só organizar a saída.

## Fase 1 — Auditoria módulo a módulo (uma linha = um item = uma parada)

Itens já auditados manualmente nesta conversa — o agente deve **confirmar de
forma independente**, não aceitar de graça:

- [x] `core/alias_tracker.py` — achado: `apply_alias_migration` não é
  atômico (loop de UPDATEs sem transação envolvente) e referencia coluna
  `task_id` inexistente em `fsm_checkpoints`.
- [x] `interface/queue_writer.py` — achado: fila em memória (`queue.Queue`)
  sem persistência nem tratamento de sinal; risco de perda em SIGKILL.
- [x] `core/parser_factory.py` + `core/parsers/` — achado: só suporta
  Python e TS/JS; retorna `None` para o resto (não existe `FallbackParser`).
- [x] `core/gating_interceptor.py` — achado: `VALID_MODES` real é
  `{"plan-only","ask","auto-approve"}`; `auto_read`/`autonomous` nunca
  existiram no código, só na documentação.
- [x] `core/hsm_engine.py` — achado: `STALL`/`AWAITING_HUMAN`/
  `CONTEXT_FULL`/`ERROR_PAUSE` são reais; `ERROR` não existe no código.
  **Pendência:** ler o arquivo completo (só uma amostra foi vista).
- [x] `interface/mcp_server.py` (parcial) — achado: `concierge_feedback`
  chama `update_fact_utility` (mutação real) mas está classificado como
  `READ_ONLY`. **Pendência:** ler o arquivo completo (69KB, só uma função
  foi conferida).

Auditado nesta sessão do Antigravity, confirmado de forma independente:

- [x] `core/delta_manager.py` — 5 achados reais + 1 falso positivo resolvido (ver `audits/core-delta-manager.md`).
  Destaque: `hsm_engine.py:458` chama `delta_manager.has_structural_change()`,
  método inexistente na classe real (confirmado de forma independente) —
  mascarado por `MockDeltaManager` nos testes. Achado #2 (`_stripper` thread-safety)
  foi reavaliado e resolvido como falso positivo (objeto é stateless e AST é gerada
  em escopo thread-local; testado sob 50 threads / 10.000 chamadas sem erro).
  `calculate_lbh()` sempre retorna `""` para não-Python; `calculate_ssh()`
  documentado com 10 testes parametrizados em `tests/test_ssh_language_coverage.py`.
  Adendo pós-descoberta: Achado #3 agravado por conexões SQLite efêmeras cruas sem fila e sem `foreign_keys=ON`, executando duas conexões físicas distintas por mutação.

Tarefa extra inserida a partir do padrão encontrado acima:

- [x] **mock-vs-real-audit** — 18 classes de teste inspecionadas (ver `audits/mock-vs-real-audit.md`).
  Revelou 2º bug CRÍTICO idêntico ao `delta_manager.py`: `vector_reconciler.py:39`
  chama `vector_db.get_all_ids()`, método inexistente na classe real `ChromaVectorStore`
  (mascarado por `MockVectorDatabase` nos testes). Identificou contrato fantasma de
  `MockExternalMCP.query_docs` sem implementação real no repositório. O caso de `MockJanitor`
  foi rebaixado para Falso Positivo (em produção usa-se `JanitorService`, que satisfaz 100%
  dos métodos, restando observação de duplicidade de nomenclatura com `BackgroundJanitor`).
  `FailingIngestion` e `InMemoryConnManager` verificados como 100% conformes com as classes reais.

- [x] `core/security_guard.py` — 5 achados confirmados (ver `audits/core-security-guard.md`).
  1 CRÍTICA (evasão da blacklist de comandos via flags GNU `rm -fr /`, `rm -r -f /`,
  deleção de diretório atual `rm -rf .`, comandos nativos Windows `del /s`, `format`),
  1 ALTA (`classify_command(None)` lança `TypeError` não tratado),
  2 MÉDIA (bug de barra dupla `C:\\\\` na raiz do disco bloqueando 100% dos arquivos;
  resolução de caminhos relativos ancorada ao CWD do processo e não a `project_root`),
  1 BAIXA (falso positivo de WARNING por substring match ingênuo em `"build"`).
- [x] `core/rate_governor.py` — 5 achados confirmados (ver `audits/core-rate-governor.md`).
  1 CRÍTICA (vazamento de `unfinished_tasks` na `PriorityQueue` e starvation de cabeça
  de fila durante congelamento de LOW/MEDIUM; deadlock permanente com `join()`),
  3 ALTA (anti-starvation aging matematicamente inalcançável durante congelamento;
  Data Race / Lost Updates em `get_current_metrics` sem lock; deadlock eterno em
  `submit_request` sem timeout e após `shutdown()`),
  1 MÉDIA (cegueira de RPM no Fast-Path sem registro em `self.history`).
  *(Nota: 100% em memória, zero interações com `ConciergeDatabaseManager` ou SQLite).*
- [x] `core/background_janitor.py` — 5 achados confirmados (ver `audits/core-background-janitor.md`).
  3 ALTA (slice negativo `remaining[-0:]` com `keep_limit=0` preserva 100% dos checkpoints;
  degradação irreversível da prioridade do processo inteiro do servidor para IDLE;
  destruição do ponto-zero e deleção cruzada de checkpoints entre agentes por ignorar `agent_id` no DELETE),
  2 MÉDIA (crash com `TypeError` em `_summarize_community` quando `files.content` é `NULL`;
  descarte cego de `is_dirty = 0` / TOCTOU sobre arquivos modificados durante a SLM).
  Adendo pós-descoberta: Achado #5 agravado por duas conexões físicas efêmeras cruas distintas por ciclo de resumo, sem fila e sem `foreign_keys=ON`.
- [x] `core/vector_reconciler.py` — 4 achados confirmados (ver `audits/core-vector-reconciler.md`).
  2 CRÍTICA (invocação de método fantasma `self.vector_db.get_all_ids()` inexistente em `BaseVectorBackend`/`ChromaVectorStore`/`QdrantVectorStore`, mascarado por mock nos testes; incompatibilidade de TIPO (`int` vs `str`) e de domínio semântico entre `get_all_stored_node_ids()` e `_get_all_sqlite_paths()`, causando purga matematicamente garantida de 100% dos vetores legítimos da base vetorial; dependência crítica: corrigir #1 isoladamente faz o sistema passar de 'seguro por estar quebrado' para 'roda e apaga tudo', exigindo correção simultânea),
  1 ALTA (ausência de locks e race condition destrutiva TOCTOU com ingestão concorrente em segundo plano),
  1 MÉDIA (falta de paginação em lote e ausência de tratamento de exceções em `delete_batch`).
- [x] `core/checkpointer.py` — 5 achados confirmados (ver `audits/core-checkpointer.md`).
  1 CRÍTICA (despacho ambíguo em `save_checkpoint` baseado em heurística de tipos `len(args)==4 and isinstance(args[3], str)` desviando chamadas de `agent_save_checkpoint` para `fsm_checkpoints` com inversão de colunas primárias e perda total de dados `shared_state="{}"`),
  2 ALTA (mascaramento silencioso de falhas e transação não atômica em `execute_time_travel`; granularidade de 1s de `CURRENT_TIMESTAMP` falhando em deletar checkpoints futuros em rajadas rápidas de time-travel),
  2 MÉDIA (crash com `json.JSONDecodeError` não tratado em `get_checkpoint`; tipagem insegura reportada pelo Mypy com risco de chamada em `None`).
  Adendo pós-descoberta: Achado #2 agravado por conexões físicas efêmeras cruas sem fila e sem `foreign_keys=ON`.
- [x] `storage/` (todos os arquivos) — 9 achados confirmados (ver `audits/storage.md`).
  2 CRÍTICA (deadlock inevitável em escritas aninhadas/reentrantes no `SerializedWriteQueue` travando permanentemente o worker thread; bypass completo de isolamento estrito / Strict Scoping em `ChromaVectorStore.search` quando `project_uuids=[]` vazando dados cross-project),
  3 ALTA/GRAVE (vazamento perpétuo de conexões SQLite de threads finalizadas em `ConnectionManager` acumulando zumbis em `_read_connections`; incompatibilidade de contrato em `relational_db:init_fsm_checkpoints_schema` falhando silenciosamente e ausência das tabelas de checkpoints no `SchemaManager`; falha de tipo em `GraphLogic._calculate_decay` com timestamps ISO 8601 offset-aware degradando silenciosamente o score de recência para o mínimo 0.01),
  3 MÉDIA (falha com `RuntimeError` ao reiniciar `SerializedWriteQueue` após `stop`; crash com `ValueError` em busca vetorial quando `node_id` é `None`/string vazia; duplicação de nós na CTE recursiva `get_dependency_tree` por inclusão de `depth` em `SELECT DISTINCT`),
  1 BAIXA (isolamento total de `semantic_logic` na fachada `SqliteStore` forçando quebra de encapsulamento).
- [x] **duplicacao-serialized-write-queue** — 5 achados confirmados (ver [`audits/duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md)).
  2 CRÍTICA (colisão estrutural entre uma fila real em `storage/connection.py` e zero fila do lado de `core/database.py`, onde conexões físicas efêmeras cruas disputam o mesmo banco `data/concierge.db` sem serialização, sem mutex e sem `foreign_keys=ON`; ilusão dos testes e código morto em produção onde `interface/queue_writer.py::SerializedWriteQueue` é testada em 11 suítes mas em produção `ConciergeDatabaseManager` é instanciado em `mcp_server.py:166` com `write_queue=None`),
  2 ALTA/GRAVE (divergência de integridade referencial por ausência de `PRAGMA foreign_keys=ON;` em `interface/queue_writer.py` e `core/database.py`, permitindo gravação de arestas/registros órfãos no banco compartilhado; timeout assimétrico de 5s em `storage/connection.py` vs 30s em `core/database.py` provocando `OperationalError: database is locked` prematuro na camada de storage sob contenção sustentada),
  1 MÉDIA (quebra de encapsulamento privado em `interface/mcp_server.py:162` acessando `self._gc._store._conn_mgr._db_path` para criar uma segunda conexão paralela ao invés de usar fachada unificada).
- [x] `ingestion/` (todos os arquivos) — 8 achados confirmados (ver [`audits/ingestion.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/ingestion.md)).
  2 CRÍTICA (perda total no grafo na renomeação de arquivos por colisão de hash no crawler `find_node_by_hash` ignorando caminhos + falso purge no GC; descarte silencioso de 100% dos resumos L0 com gravação de `nodes.summary = NULL` no SQLite e esterilização completa da geração subsequente de L1 e L2),
  2 ALTA/GRAVE (falha silenciosa de persistência do L2 Compass por envio de `folder_name` em vez de `uuid` para `SqliteStore.update_project`, agravada por falsa confirmação ativa de sucesso no log pois UPDATE com 0 matches não lança exceção e o `try/except` nunca captura a falha; acúmulo perpétuo de vetores zumbis no ChromaDB em modificações de arquivos por falta de coordenação no Step 7 de GC),
- [x] **bypass-governanca-por-session-id** — PRIORIDADE MÁXIMA (achado transversal de segurança; suplanta em gravidade qualquer item já concluído; ver [`audits/bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md)).
  1 CRÍTICA MÁXIMA (bypass total do `MCPToolGovernor` via injeção arbitrária de `session_id` e descarte de parâmetros extras pelo FastMCP, permitindo a agentes em `PLANNING` executarem ferramentas `DANGEROUS` como `reset_collection`),
  1 CRÍTICA (ausência total de verificação de posse em checkpoints, independente do Achado #1: `agent_get_checkpoint` [READ_ONLY] e `agent_save_checkpoint` [LOCAL_MUTATION] já estão abertas por padrão em EXECUTION, permitindo exfiltração de segredos e envenenamento de estado de qualquer agente sem necessidade de manipular estados ou burlar o governor),
  2 GRAVE (vazamento integral de 100% das 31 ferramentas em `list_tools()` para clientes MCP padrão por ausência de `session_id` no protocolo `tools/list`; desconexão total de `CognitiveAgentRunner` e `HierarchicalStateMachine` do servidor MCP em produção, onde o estado é apenas uma string manual),
  1 MÉDIA (servidor inicia por padrão no estado inseguro `EXECUTION` em vez de `PLANNING`).
- [x] `agent/` e `agents/` (todos os arquivos) — 7 achados confirmados (ver [`audits/agent-and-agents.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/agent-and-agents.md)).
  *(Nota Mandatória: Toda a severidade deste item é CONDICIONAL / CÓDIGO ÓRFÃO, pois estes arquivos estão desconectados do servidor em produção — Achado #4 de bypass-governanca).*
  2 CRÍTICA CONDICIONAL (contaminação de turnos multi-sessão e reset indevido no Circuit Breaker por contador único de instância `current_substate_turn_count`; vazamento total de privacidade por fallback inseguro para nível `0` [PUBLIC] e falta de normalização `.upper()` em `check_contamination`),
  3 GRAVE CONDICIONAL (aprovação espúria de commits inválidos com `partial_audit=True` após falha em `generate_fn` em `audit_with_retry`; dessincronização entre prompt e estado ativo em `step(target_transition=...)` gerando alucinações e bloqueios cognitivos; falha e crash em reranking por incompatibilidade de tipo `int` vs `str` e `NoneType`),
  2 MÉDIA CONDICIONAL (incompatibilidade estrutural universal com corrotinas não-awaited e bypass de `RateGovernor` em `execute_tool`; dessincronização estrutural entre sub-estados do HSM e `TOOL_DISCLOSURE_MATRIX`).
- [x] `interface/telemetry_api.py` — 7 achados confirmados (ver [`audits/interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md)).
  2 CRÍTICA (falha fatal e crash HTTP 500 em produção por suposição de tabelas inexistentes `files` e `agent_checkpoints` forjadas apenas no `setUp` dos testes; inoperância fora da caixa por dependência não configurada `get_db_manager` lançando `RuntimeError`),
  3 GRAVE (falso stream contínuo no SSE que aborta e desconecta clientes após 5 segundos devido a trava de teste `max_checks = 5` mantida em produção; invalidação perpétua do hash SHA-256 no SSE por geração dinâmica de `datetime.now()` quebrando o filtro de broadcast; insegurança total de CORS com `allow_origins=['*']` e `allow_credentials=True` sem nenhuma autenticação em rotas mutantes permitindo CSRF e alteração arbitrária de estados e regimes de segurança),
  2 MÉDIA (dessincronização interna entre `agent_checkpoints` e `fsm_checkpoints` com crash de tipagem em timestamps `NULL` e string ISO; thread consumidora daemônica iniciada desnecessariamente no import do módulo sem conexões reais no servidor FastMCP).
- [x] **schema-oficial-incompleto** — PRIORIDADE MÁXIMA (achado transversal supremo da auditoria; suplanta em severidade estrutural qualquer outro item; ver [`audits/schema-oficial-incompleto.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/schema-oficial-incompleto.md)).
  2 CRÍTICA MÁXIMA (omissão estrutural de 5 tabelas relacionais essenciais no bootstrap oficial do sistema: `files`, `communities`, `ast_edges`, `agent_checkpoints` e `fsm_checkpoints` não possuem DDL em nenhum arquivo de produção; colapso imediato com `sqlite3.OperationalError: no such table: ...` em 12 módulos já auditados de `core/` e `interface/` após clone limpo do repositório),
  1 CRÍTICA (a ilusão dos testes [Test Mirage]: 14 suítes de teste mascaram a ausência do schema criando privadamente as tabelas em seus métodos `setUp()`, fazendo a suíte passar com 100% de sucesso enquanto a instalação real de produção está completamente inoperante),
  1 ALTA/GRAVE (mascaramento silencioso de falhas de DDL por supressão de exceções em `core/database.py::execute_write` e `interface/watcher.py`; falsa confirmação enganosa no log de boot em `storage/store.py:107` logando 'Schema v3.8.0 verified - all tables and triggers OK' porque `verify_tables_exist` valida apenas seu próprio subset restrito, ocultando a ausência de 5 tabelas críticas),
  1 MÉDIA (abandono de especificação formal onde `01_ARCHITECTURE.md` especificava as 13 tabelas mas `storage/schema.py` implementou apenas metade).
- [x] `grafo-dashboard-web/` (componentes principais e chamadas à API) — 8 achados confirmados (ver [`audits/grafo-dashboard-web.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/grafo-dashboard-web.md)).
  3 CRÍTICA (código morto em handlers SSE com mostradores de cota `QuotaGauges` e estados `HSMStateInspector` permanentemente congelados por ausência do atributo `event_type` no backend; ciclo infinito de flapping SSE a cada 8s por trava `max_checks = 5` mantida em produção inundando o feed com 75 reconexões/10min e fazendo o HUD piscar sem parar; colisão de portas 8000 entre FastAPI e FastMCP com inoperância total do script `dev:all` e desconexão do FastMCP SSE por busca na porta órfã 7077),
  2 GRAVE (incompatibilidade estrutural de autenticação FastMCP com rejeição imediata HTTP 401 por ausência de suporte a headers no `EventSource` nativo e no `sendRequest`; omissão estrutural de metadados `summary` e `tags` em `get_full_topology` esvaziando permanentemente o `InspectorDrawer` ao clicar em nós do grafo 3D/2D),
  3 MÉDIA (risco de crash e corrupção de data `Invalid Date` por concatenação cega de `+ "Z"` em timestamps ISO em `CoreMemoryPanel`; rotas mutantes `/api/hsm/transition` deixadas órfãs e cliques na UI tornados inertes por omissão da prop `onSelectState`; 37 erros de linter com violação de funções puras no render de `LiveEventFeed` no React 19 e disparos de `setState` em efeitos).

▶ **PRÓXIMO PASSO (Aguardando Aprovação - FASE 1 CONCLUÍDA):** Início da Fase 2 — `cruzamento-modulos` (Todos os 18 itens da Fase 1 concluídos com relatórios e provas empíricas!)

## Fase 2 — Cruzamento transversal (só inicia com TODOS os itens da Fase 1 marcados)

- [ ] **cruzamento-modulos** — Ler todos os `audits/*.md` gerados (não
  reler o código-fonte inteiro). Apontar:
  (a) módulos que fazem suposições incompatíveis um sobre o outro;
  (b) falta de isolamento entre projetos/tenants;
  (c) funcionalidade documentada que nenhum módulo implementa de fato;
  (d) **Eixo de Colapso Sistêmico Central: `core/database.py::ConciergeDatabaseManager`** — convergência
  crítica entre `duplicacao-serialized-write-queue` e `schema-oficial-incompleto`,
  demonstrando que nem a camada de escrita (conexões efêmeras sem fila e sem FKs) nem
  a de schema (`_init_tables` só cria `test_log`) cumprem o especificado na documentação, tornando-o
  o componente mais frágil e enganoso de toda a arquitetura.

## Fase 3 — Consolidação

- [ ] **backlog-final** — Gerar um backlog único, priorizado por
  severidade, no formato do `concierge-graph-improvements-roadmap-v5.md`,
  mas exigindo que cada item cite o `audits/<arquivo>.md` de origem.

---

## Como retomar após uma parada

Responda apenas: **"aprovado, siga para o próximo item"** (ou peça correções
específicas primeiro, se o relatório do item concluído tiver problema — o
agente deve corrigir o ARQUIVO de relatório, não só reconhecer no chat, e
voltar ao mesmo gate antes de avançar).
