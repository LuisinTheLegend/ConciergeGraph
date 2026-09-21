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
- [x] `core/background_janitor.py` — 5 achados confirmados (ver `audits/core-background-janitor.md`).
  3 ALTA (slice negativo `remaining[-0:]` com `keep_limit=0` preserva 100% dos checkpoints;
  degradação irreversível da prioridade do processo inteiro do servidor para IDLE;
  destruição do ponto-zero e deleção cruzada de checkpoints entre agentes por ignorar `agent_id` no DELETE),
  2 MÉDIA (crash com `TypeError` em `_summarize_community` quando `files.content` é `NULL`;
  descarte cego de `is_dirty = 0` / TOCTOU sobre arquivos modificados durante a SLM).
- [x] `core/vector_reconciler.py` — 4 achados confirmados (ver `audits/core-vector-reconciler.md`).
  2 CRÍTICA (invocação de método fantasma `self.vector_db.get_all_ids()` inexistente em `BaseVectorBackend`/`ChromaVectorStore`/`QdrantVectorStore`, mascarado por mock nos testes; incompatibilidade de TIPO (`int` vs `str`) e de domínio semântico entre `get_all_stored_node_ids()` e `_get_all_sqlite_paths()`, causando purga matematicamente garantida de 100% dos vetores legítimos da base vetorial; dependência crítica: corrigir #1 isoladamente faz o sistema passar de 'seguro por estar quebrado' para 'roda e apaga tudo', exigindo correção simultânea),
  1 ALTA (ausência de locks e race condition destrutiva TOCTOU com ingestão concorrente em segundo plano),
  1 MÉDIA (falta de paginação em lote e ausência de tratamento de exceções em `delete_batch`).
- [x] `core/checkpointer.py` — 5 achados confirmados (ver `audits/core-checkpointer.md`).
  1 CRÍTICA (despacho ambíguo em `save_checkpoint` baseado em heurística de tipos `len(args)==4 and isinstance(args[3], str)` desviando chamadas de `agent_save_checkpoint` para `fsm_checkpoints` com inversão de colunas primárias e perda total de dados `shared_state="{}"`),
  2 ALTA (mascaramento silencioso de falhas e transação não atômica em `execute_time_travel`; granularidade de 1s de `CURRENT_TIMESTAMP` falhando em deletar checkpoints futuros em rajadas rápidas de time-travel),
  2 MÉDIA (crash com `json.JSONDecodeError` não tratado em `get_checkpoint`; tipagem insegura reportada pelo Mypy com risco de chamada em `None`).
- [ ] `storage/` (todos os arquivos)
- [ ] `ingestion/` (todos os arquivos)
- [ ] `agent/` e `agents/` (todos os arquivos)
- [ ] `interface/telemetry_api.py`
- [ ] `grafo-dashboard-web/` (componentes principais e chamadas à API)

▶ **EM ANDAMENTO:** `storage/` (todos os arquivos)

## Fase 2 — Cruzamento transversal (só inicia com TODOS os itens da Fase 1 marcados)

- [ ] **cruzamento-modulos** — Ler todos os `audits/*.md` gerados (não
  reler o código-fonte inteiro). Apontar: (a) módulos que fazem suposições
  incompatíveis um sobre o outro, (b) falta de isolamento entre
  projetos/tenants, (c) funcionalidade documentada que nenhum módulo
  implementa de fato.

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
