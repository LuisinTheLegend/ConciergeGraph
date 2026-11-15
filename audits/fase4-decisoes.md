# Decisões Arquiteturais e Planejamento — Fase 4

> **Status:** Registrado e Homologado pelo Usuário  
> **Data:** 18/10/2026  
> **Base Normativa:** Regras 2, 3, 4, 7, 10 e 11 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Contexto:** Rodada 4.1/B — Correção do F4-006 e Alinhamento Estratégico  

---

## 1. Decisões Oficiais do Usuário

1. **Caminho B Aprovado (Schema Reduzido & Quarentena Segura):**
   - No dilema arquitetural do schema relacional, o **Caminho B** foi oficialmente selecionado e aprovado.
   - O schema oficial de produção receberá exclusivamente a DDL da tabela `agent_checkpoints` (única das 5 tabelas ausentes do inventário que o Caminho B cria) para desbloquear as ferramentas `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`.
   - Das 5 tabelas ausentes catalogadas no inventário ([`audits/fase4-1-inventario-ddl.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-1-inventario-ddl.md)):
     - `agent_checkpoints` será criada em produção pelo Caminho B.
     - As outras 4 tabelas (`files`, `communities`, `ast_edges` e `fsm_checkpoints`), associadas aos motores Delta/Survival e HSM legado, permanecem dormentes e **não serão criadas** no schema de produção.
   - O código dormente associado será transferido para quarentena em `archive/v4-experimental` **somente após o desacoplamento seguro** de suas dependências ativas.

2. **Elevação de Severidade do F4-006 para CRÍTICA:**
   - O achado **F4-006** (crash de formatação de log em `ingestion/orchestrator.py:222`) foi elevado de 🟠 GRAVE para **🔴 CRÍTICA**, uma vez que a presença do `RichHandler` no processo real aborta o pipeline de mineração antes da geração e armazenamento de embeddings, deixando o banco vetorial vazio e a busca híbrida sem sinal semântico (`vector_score: 0.0`).

3. **Diretriz Técnica para `concierge_get_call_chain`:**
   - A ferramenta `concierge_get_call_chain` será reorientada para retornar caminhos de arquivo (*file paths*), navegando exclusivamente pelas arestas do tipo `calls` na tabela relacional `edges`.
   - A implementação e testes desta alteração ficam postergados para uma rodada futura específica.

4. **Remoção Definitiva do Dicionário de Alas (`wing_keywords`):**
   - O dicionário hardcoded de palavras-chave de domínio (`wing_keywords` em `core/config.py`) será removido em definitivo do sistema para garantir neutralidade de domínio, acompanhado de teste-guarda.
   - Esta remoção também fica agendada para uma rodada futura.

5. **Desenho Aprovado para F4-008/F4-009 (Alternativa A + Relato Honesto):**
   - Aprovada a **Alternativa A** (Reparo de vetores ausentes em `repair_missing_vectors` executado a cada mineração antes do atalho noop e após o passo 6) com **relato honesto do resultado** (`embeddings_failed`, `embeddings_repaired` e detalhamento em `errors` em caso de Semantic Fallback).
   - As alternativas B, C e D ficam oficialmente descartadas.

6. **Severidades Homologadas:**
   - **F4-008:** 🔴 **CRÍTICA**
   - **F4-009:** 🟠 **GRAVE**
   - **F4-010:** 🟠 **GRAVE**

7. **Escopo do F4-010 (Sumários L0):**
   - O F4-010 foi incluído na Rodada 4.1/D como commit separado, persistindo `chunk.cached_summary` no nó SQLite. Não há backfill de bancos existentes nesta rodada.

8. **Política para Sumários de Truncamento `[DUMB]` (Decisão do Dono — 2026-10-19):**
   - "[DUMB]: sem LLM, nodes.summary permanece NULL (não persistir o placeholder de truncamento)".
   - *Fonte:* Confirmação do dono nesta conversa (homologada nas rodadas 4.1/F e 4.1/G).
   - Sumários de truncamento gerados na ausência de LLM (`is_dumb_summary=True`) não devem ser persistidos no SQLite; em ambientes sem LLM, `nodes.summary` permanece `NULL` até que a integração com LLM esteja configurada.

9. **Migração dos Sumários `[DUMB]` Existentes e Backfill Futuro (Decisão do Dono — 2026-10-21):**
   - **Opção B Aprovada:** Execução de backup consistente via API do SQLite (`conn.backup()`) e `UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%'` em transação única atômica, preservando todas as demais colunas e tabelas e mantendo o FTS5 íntegro.
   - **Opção C (Backfill com LLM):** Registrada como funcionalidade futura, expressamente **NÃO AUTORIZADA** para execução na Fase 4.1.
   - **Efeito Conhecido Documentado:** Na ausência de sumários L0 preenchidos (permanecendo como `NULL`), o pipeline de contexto `generate_project_context` aborta com contagem nula (`l1_count: 0`, `L2: None`), até que seja implementado e autorizado um backfill oficial com LLM para gerar resumos de nós.

---

## 2. Ordem de Execução Planejada

> [!WARNING]
> **Status:** `PLANEJADO, NÃO AUTORIZADO`  
> Nenhuma das etapas 4.2 a 4.5 possui autorização de execução nesta rodada. Cada etapa depende de validação prévia e autorização humana explícita (GATE — Regra 7).

1. **Rodada 4.1/B (Concluída):**
   - Investigação de causa raiz completa do F4-006.
   - Teste de regressão e teste-guarda com RichHandler.
   - Correção pontual e cirúrgica na linha 222 de `ingestion/orchestrator.py`.
   - Prova ponta a ponta com modelo real (Chroma + SentenceTransformers) contrastada com a condição "Antes".

2. **Rodada 4.1/C (Concluída):**
   - Investigação empírica com 4 sondas (offline, falha parcial de lotes, reset_collection e sumários).
   - Elaboração e análise de 4 alternativas arquiteturais (A, B, C, D) para F4-008/F4-009.

3. **Rodada 4.1/D (Concluída):**
   - Implementação do reparo de vetores ausentes (Alternativa A) e relato honesto (F4-008, F4-009).
   - Implementação da persistência de sumários L0 nos nós SQLite (F4-010).
   - Prova ponta a ponta com modelo real `all-MiniLM-L6-v2` confrontada com baseline `76e6a7e`.

4. **Rodada 4.1/E (Retificação — Concluída):**
   - Retificação das evidências da 4.1/D em [`audits/fase4-1d-relatorio-retificado.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-1d-relatorio-retificado.md), com Passo 1 composto exclusivamente por saídas brutas de `git show` e `pytest`.
   - Tratamento definitivo do F4-011: filtro por `node_type` desacoplado do metadado do Chroma, movido para o SQLite com compatibilidade retroativa (Commit `8d963ae`).
   - Deduplicação da telemetria `embeddings_failed` no ciclo offline (Commit `8d963ae`).
   - Otimização de `repair_missing_vectors` (IDs leves antes do conteúdo completo) e medição de escala em 1.000/10.000 nós (Commit `8d963ae`).
   - **Política `[DUMB]` homologada:** sumários de truncamento gerados sem LLM (`is_dumb_summary=True`) **não são persistidos** — `nodes.summary` permanece `NULL` até a integração com LLM (Commit `8d963ae`).

5. **Rodada 4.2 (Planejado, Não Autorizado):**
   - Desacoplamento do `mcp_governor` em relação a `interface.telemetry_api`.
   - Corte definitivo da cadeia `interface/__init__` → `ActionHooks` → `RevisorCritico` / `telemetry_api`.

6. **Rodada 4.3 (Planejado, Não Autorizado):**
   - Implementação do Schema Reduzido (DDL de `agent_checkpoints`).
   - Implementação e refatoração de `concierge_get_call_chain` navegando arestas `calls` em `edges`.

7. **Rodada 4.4 (Planejado, Não Autorizado):**
   - Remoção definitiva de `wing_keywords` em `core/config.py` e adaptação do `ProjectIndex`.
   - Teste-guarda de neutralidade de domínio.

8. **Rodada 4.5 (Planejado, Não Autorizado):**
   - Movimentação do motor Delta/Survival dormente e de seus módulos associados para quarentena isolada em `archive/v4-experimental`.

---

## 3. Decisões para Quarentena e Higiene (Rodada 4.5c-bis — 2026-11-14)

Registros oficiais das decisões do Luis que orientam a `4.5c-bis` e a futura execução da `4.5d`:

- **Escolha A — `enable_probabilistic=True` após quarentena de `core/probabilistic_retriever.py` (DECIDIDA):**
  - Quando `core/probabilistic_retriever.py` for movido para quarentena na `4.5d`, qualquer chamada com `enable_probabilistic=True` deve **falhar alto com `NotImplementedError` e mensagem explícita** (idioma da mensagem — e.g. português — é apenas sugestão do executor, não decidida), **sem fallback silencioso**.
  - A implementação no código de produção ocorrerá apenas na `4.5d` junto da quarentena (nada alterado na `4.5c-bis`).

- **Escolha B — Destino de `interface/queue_writer.py` — D3 de [`audits/egm/4.5b-sintese.md:55-63, 182`](file:///c:/Nexus-Memory/GrafoConcierge/audits/egm/4.5b-sintese.md#L55-L63) (EM ABERTO):**
  - Opções em avaliação antes da `4.5d` / `4.5f`:
    1. Tentar arquivar `interface/queue_writer.py` na sub-rodada **4.5f**, **somente com portão condicional** (remover `from interface.queue_writer import SerializedWriteQueue` em [`core/database.py:18`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L18), ajustar [`L27`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L27), remover os carregamentos `importlib.util.spec_from_file_location` em nível de módulo em `tests/test_agent_checkpointer.py`, `tests/test_mcp_server_extensions.py` e `tests/test_concurrency_stress.py`, e o import em `tests/test_graph_rag_loops.py`; exigir teste concorrente vermelho→verde + mutação dedicada em `core/database.py` sem degradar `TestConcurrencyAndDelta`); **ou**
    2. **Adiar para a V4.1** (mantendo aviso textual "não usado em produção"; custo: duas classes com o mesmo nome por mais tempo).
  - Decisão do Luis: **EM ABERTO** (preferência do auditor: adiar).

> **Errata 4.5c-ter (2026-11-14 — Regra 10 / Regra 14):** Em `43ea935:audits/fase4-decisoes.md:104-109`, a versão da 4.5c-bis havia acrescentado indevidamente o qualificador "em português" como requisito decidido na **Escolha A** e descrito incorretamente as alternativas da **Escolha B** (citando destinos não propostos por D3 em [`audits/egm/4.5b-sintese.md:55-63, 182`](file:///c:/Nexus-Memory/GrafoConcierge/audits/egm/4.5b-sintese.md#L55-L63)). Texto acima corrigido para refletir estritamente a decisão registrada.

- **Exclusão de arquivos não rastreados / pré-existentes de commit (DECIDIDA):**
  - Por decisão explícita do Luis na `4.5c-bis`, permanecem fora de commit os arquivos `audits/egm/analise-completa-*.md`, `scratch/prompt_4_5b_verbatim.md` e os dois arquivos pré-existentes modificados em `scratch/` (`scratch/build_4_5a_bis_docs.py` e `scratch/inv_4_5a_bis_bloco1.py`).


---

## 4. Execução da Quarentena V4 — Rodada 4.5d (2026-11-15)

Registros da execução em 3 lotes (`4.5d-A`, `4.5d-B`, `4.5d-C`):

- **Escolha A implementada em `core/hybrid_search.py` (DECIDIDA):**
  - Guarda adicionada no início de `HybridSearchEngine.search()` levantando `NotImplementedError` imediatamente quando `enable_probabilistic` for verdadeiro (antes de consultar o grafo/banco), removendo o antigo `STEP 7` e o método `_apply_thompson_sampling` (que importava `core.probabilistic_retriever`).
  - Mensagem implementada: `"Probabilistic retrieval (Thompson Sampling / core.probabilistic_retriever) is archived in V4 (D0); pass enable_probabilistic=False."` — **sugestão do executor, não decidida** (idioma não especificado pelo Luis).
  - Coberta por `tests/test_hybrid_search_escolha_a.py` (ciclo vermelho→verde e mutação dedicada).

- **Escolha B inalterada (EM ABERTO):**
  - `interface/queue_writer.py` **não** foi movido e `core/database.py` permaneceu com 0 bytes alterados. Decisão mantida em aberto para `4.5f` ou `V4.1`.

- **Modificações e arquivos arquivados em `archive/v4-experimental/` (100 arquivos via `git mv` + 2 arquivos de testes extraídos):**
  - **Lote A (65 `git mv`):** `grafo-dashboard-web/` (40 arquivos rastreados); `core/hsm_engine.py`, `core/rate_governor.py`, `core/gating_interceptor.py`, `core/intent_classifier.py`, `core/dependencies.py`, `core/background_janitor.py`, `core/telemetry_schemas.py`, `core/security_guard.py`, `interface/telemetry_api.py`, `interface/watcher.py` (10 módulos); `tests/test_adaptive_gating.py`, `test_agent_hsm_coupling.py`, `test_dependency_injection.py`, `test_hierarchical_state_machine.py`, `test_hsm_transition_hooks_and_delta.py`, `test_rate_governor_priority.py`, `test_watcher_ignore.py`, `test_telemetry_api.py`, `test_progressive_tool_disclosure.py`, `test_checkpoint_pruning.py`, `test_graph_rag_frugal.py`, `test_graph_rag_janitor.py`, `test_e2e_concierge_integration.py`, `test_durable_checkpoints_timetravel.py`, `test_cognitive_routing_memory.py` (15 arquivos; `test_cognitive_routing_memory.py` antecipado do Lote B para o Lote A por importar `core.intent_classifier`). Criação de `archive/README.md`, ajuste em `.gitignore:69-70` e extração de `T3` de `tests/test_governor_wiring.py` para `archive/v4-experimental/tests/test_governor_wiring_archived.py`.
  - **Lote B (21 `git mv`):** `core/delta_manager.py`, `core/delta_sync.py`, `core/alias_tracker.py`, `core/vector_reconciler.py`, `core/parser_factory.py`, `core/parsers/` (4 arquivos), `core/janitor.py`, `core/search_engine.py`, `core/federated_knowledge_router.py`, `core/global_memory_adapter.py`, `core/nozomio_router.py`, `storage/relational_db.py` (15 módulos); `tests/test_delta_sync_drift.py`, `test_ssh_language_coverage.py`, `test_multilang_parser.py`, `test_alias_tracker.py`, `test_delta_sync.py`, `test_vector_reconciler.py` (6 arquivos).
  - **Lote C (14 `git mv` + extrações/higiene):** `agent/` (3 arquivos), `agents/` (2 arquivos), `core/probabilistic_retriever.py`, `interface/action_hooks.py` (7 módulos); `tests/test_revisor_critico.py`, `test_probabilistic_retriever.py`, `colossus_benchmark.py`, `stress_test_v2_setup.py`, `stress_test_v2_parte1.py`, `stress_test_v2_parte2.py`, `stress_test_v2_parte3.py` (7 arquivos). Remoção de `"agent*"` em `pyproject.toml`, remoção de `ActionHooks`/`__getattr__` em `interface/__init__.py`, extração de testes de `ActionHooks` em `tests/test_interface_contracts.py` para `archive/v4-experimental/tests/test_action_hooks_contracts.py`, extração de `T5` de `tests/test_governor_wiring.py` para `archive/v4-experimental/tests/test_governor_wiring_archived.py`, retarget da allowlist G2 em `tests/test_domain_neutrality_guard.py:84-87` e Escolha A em `core/hybrid_search.py` + `tests/test_hybrid_search_escolha_a.py`.
  - **Mantidos em `tests/`:** `tests/memory_stress_test.py` (infraestrutura importada por `tests/conftest.py:8` e 4 suítes vivas, sem imports dormentes) e `tests/check_brain.py` (diagnóstico que importa apenas camadas vivas).
