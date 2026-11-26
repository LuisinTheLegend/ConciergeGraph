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

---

## 5. Rodada 4.5e — Remoção de Ramos SQL Dormentes em Módulos Vivos (2026-11-16)

- **Errata 4.5d (Regra 10):**
  - O relatório da Rodada `4.5d` citou indevidamente o nome `_fallback_dir_community` em `core/graph_rag.py`. Essa função não existe no repositório; as linhas `L156-157` citadas pertenciam a `GraphRAGEngine.get_natural_community` (`core/graph_rag.py:147-157`, método dormente sem chamadores em produção, removido na `4.5e`).
- **Correção da análise de cobertura (Regra 10):**
  - Os testes substitutos listados na `4.5d` só se aplicam ao código que permanece vivo (`AgnosticCheckpointer._sanitize_for_json` no ramo legado e despacho `is_sdd20`); não se escreve teste para código dormente removido (`load_checkpoint`, `execute_time_travel`, `get_natural_community`, `detect_logical_communities`).
  - O que permanecia vivo e sem cobertura foi travado antes da remoção em [`tests/test_checkpointer_live_contract.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_checkpointer_live_contract.py) (4 posicionais `dict`, kwargs legados, sanitização via ramo legado de `Lock`/`set`/`object`/aninhados, contrato invariante das 4 assinaturas `is_sdd20` e reset de `last_error`), e o novo comportamento D0 foi travado em [`tests/test_checkpointer_sdd20_removed.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_checkpointer_sdd20_removed.py).
- **Mensagem SDD-20 (`core/checkpointer.py`) — sugestão do executor, não decidida:**
  - Mantida inalterada a expressão `is_sdd20`; retorno substituído por `(False, "SDD-20 / fsm_checkpoints signature is archived in V4 (D0); use legacy agent_checkpoints (agent_id, session_id, checkpoint_id, state_dict).")` sem consulta SQL, com remoção de `load_checkpoint`, `execute_time_travel`, `time` e `logging`/`logger`.
- **Limpeza em `core/graph_rag.py`:**
  - Arquivado `tests/test_local_graph_rag_recursion.py` em `archive/v4-experimental/tests/test_local_graph_rag_recursion.py`; removidos `_get_edge_columns`, `retrieve_multihop_context`, `get_natural_community`, `detect_logical_communities` e `import os`; preservado `get_call_chain_recursive` com **0 bytes de diff**.
- **Pendências já conhecidas para a 4.5g (apontadas pelo auditor; NÃO implementadas na 4.5e):**
  1. `README.md` e `docs-grafo-concierge/01_ARCHITECTURE.md` ainda anunciam dashboard/HSM/telemetria como ativos e o `README` orienta `cd grafo-dashboard-web` (removido da raiz na `4.5d`).
  2. `Dockerfile` usa `COPY . .` e não há `.dockerignore` (`archive/` entra na imagem).
  3. Em `tests/test_governor_wiring.py`, `T1` e `T2` passam a verificar a ausência de módulos inexistentes e o cabeçalho ainda menciona o `T3` removido.
  4. Entradas fantasmas em `core/mcp_governor.py:43-126` (ex.: `retrieve_multihop_context:85`, `list_session_checkpoints:86`, `save_checkpoint:108`).
- **Propostas adicionais registradas pelo Swarm (`audits/egm/4.5e-sintese.md`) para avaliação do auditor (NÃO implementadas na 4.5e):** bug de despacho legado com `<4` posicionais + `kwargs` ignorando `args[0..2]` (`core/checkpointer.py:80-89` pós-C2), ausência de guarda `json.JSONDecodeError` / `dict` em `get_checkpoint`, limitação `NaN`/`Inf` em `_sanitize_for_json`, e casos de borda adicionais em `tests/test_call_chain_edges_nodes.py` e `agent_list_checkpoints`.

---

## 6. Rodada 4.5e-bis — Correção de 2 Bugs Legados do Checkpointer e Fechamento de Mutantes (2026-11-19)

- **Fechamento dos mutantes sobreviventes S1 e S2 (Etapa C1):**
  - Testes parametrizados isolando individualmente cada um dos 4 disjuntos de `is_sdd20` (S1) e validação determinística de ordenação lexicográfica `key=str` em `set` via `{9, 10} -> [10, 9]` comprovada com `PYTHONHASHSEED=0, 1, 42` (S2) adicionados em [`tests/test_checkpointer_arg_resolution.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_checkpointer_arg_resolution.py).
- **Decisões de desenho aplicadas (ambas marcadas como "sugestão do auditor, não decidida"):**
  1. **Bug 1 — Conflito posicional × kwarg (Etapa C2):** Quando o mesmo campo legado (`agent_id`, `session_id`, `checkpoint_id`, `state_dict`) é fornecido simultaneamente por posição e por nome, `save_checkpoint_detailed` **falha alto** retornando `(False, "Duplicate argument for '<campo>': ...")` sem gravar no banco (**sugestão do auditor, não decidida**). Resolvidas combinações mistas 1+3, 2+2 e 3+1 sem alterar `is_sdd20`, o ramo SDD-20 ou o caminho MCP de 4 posicionais (`interface/mcp_server.py:1744-1748`).
  2. **Bug 2 — Blob JSON corrompido em `get_checkpoint` (Etapa C3):** Em vez de retornar `{}` (o que confundiria dado corrompido com checkpoint inexistente), `get_checkpoint` captura `json.JSONDecodeError` e **levanta `ValueError`** citando `agent_id`, `session_id` e `checkpoint_id` sem vazar o conteúdo do blob (`raise ValueError(...) from exc`) (**sugestão do auditor, não decidida**). O retorno `{}` para checkpoint inexistente permanece inalterado.
- **Escolha B (`interface/queue_writer.py` e `core/database.py`):**
  - **Reafirmada ADIADA** por decisão do Luis nesta rodada (`0 bytes` alterados em `interface/queue_writer.py` e `core/database.py`).
- **Propostas ao auditor (NÃO implementadas nesta rodada; registradas para decisão futura):**
  1. Campos legados ausentes (`agent_id`, `session_id`, `checkpoint_id`) ainda recebem default `""` no ramo legado e gravam em `agent_checkpoints` com chave vazia sem erro.
  2. `get_checkpoint` não valida que o JSON decodificado seja `dict` (ex.: se o blob válido decodificar para `list` ou `int`).
  3. Valores `float('nan')` / `float('inf')` em `json.dumps` / `_sanitize_for_json`.
  4. Casos de borda extras em `tests/test_call_chain_edges_nodes.py` e `agent_list_checkpoints` (propostos originalmente pelo Swarm na Rodada `4.5e`).

---

## 7. Rodada 4.5g — Governança, Dependências/Docker e Documentação Viva (2026-11-24)

Encerramento da série `4.5` (D4, D7, D8 de `audits/egm/4.5b-sintese.md`), executado em 4 commits atômicos com validação em CI (6/6 jobs) a cada etapa:

- **Revisão Pré-Execução EGM + Swarm — Commit C0 (`cb195f84bfa1b636a41f48281471e82655eee25f`):**
  - Produzidos `audits/egm/4.5g-{fatos,design,critic,sintese}.md` em modo 100% somente leitura cobrindo exclusivamente C1 e C2 (C3 excluído do Swarm conforme pedido).
  - **Convergência integral:** 0 bloqueios que exigissem `DECISÃO HUMANA`.
- **Governança MCP — Commit C1 (`a531739e02d153719dd9352eca5b1f36194735b6`):**
  - `core/mcp_governor.py`: removidas 10 entradas fantasma de `TOOL_CLASSIFICATION` (`41 -> 31` ferramentas vivas: `18 READ_ONLY`, `11 LOCAL_MUTATION`, `2 DANGEROUS`: `delete_project` e `reset_collection`), zerado `"allowed_tools": []` nos 7 estados de `TOOL_DISCLOSURE_MATRIX` que ainda citavam `"get_telemetry_snapshot"`, e atualizado exemplo de docstring.
  - Preservadas as 8 chaves de `TOOL_DISCLOSURE_MATRIX`, `BL-011` (`concierge_set_state` permanece `READ_ONLY`) e `BL-015` (`GRAFO_DEFAULT_STATE = "EXECUTION"`).
  - Endurecidos `tests/test_mcp_governor.py`, `tests/test_interface_contracts.py` (`registered == classified` e isolamento de `_shared_governor`) e `tests/test_governor_wiring.py` (incluindo novo `T5` para `governed_list_tools`). Todas as 6 mutações (M1–M5a/M5b) mortas; suíte ampliada de 328 para **335 testes**.
- **Dependências, `.dockerignore` e `Dockerfile` — Commit C2 (`30fa1c3740b4f039b2362cedf5e9ca80b399be89`):**
  - Criado `.dockerignore` isolando o contexto de build (12 entradas top-level incluídas, 38 excluídas, 0 arquivos Python vivos ignorados).
  - Reduzido `[project].dependencies` em `pyproject.toml` e `# Core System & Framework` em `requirements.txt` para exatamente as **5 dependências diretas vivas** (`chromadb>=1.0`, `mcp>=1.27,<2`, `sentence-transformers>=3.0`, `python-dotenv>=1.0`, `starlette>=0.36`); removidas 9 dependências dormentes/transitivas (`fastapi`, `watchdog`, `pathspec`, `psutil`, `uvicorn`, `sse-starlette`, `httpx`, `pydantic`, `tenacity`); movido `rich>=13.0` para `[dev]` / `# Test & Quality Tools`.
  - Atualizadas `[project.urls]` em `pyproject.toml` para `ConciergeGraph`, mantendo `version = "3.8.2"` inalterada (sem publicação no PyPI).
  - Ajustado `Dockerfile:10-17` (`COPY requirements.txt ./` -> `pip install -r requirements.txt` -> `COPY . .` -> `pip install --no-cache-dir -e .`), mantendo `-e .` por ancoragem de `PROJECT_ROOT` em `main.py:47` e `interface/cli.py:60`.
  - Validado por *smoke install* em venv 100% limpo fora do repositório (`fastapi`/`watchdog`/`pathspec`/`psutil` ausentes com `PackageNotFoundError`, `concierge --help` exit 0, `concierge-mcp -> main:main`, `GrafoConciergeServer` com 31 tools e `sse_app()` Starlette).
- **Documentação Viva — Commit C3:**
  - Arquivados via `git mv` os 8 arquivos legados de `docs-grafo-concierge/` em `archive/v4-experimental/docs-grafo-concierge/` e criado novo `docs-grafo-concierge/README.md`.
  - Atualizados `README.md`, `README.pt-BR.md`, `CONTRIBUTING.md`, `ATTRIBUTION_AND_LINEAGE.md`, `CHANGELOG.md`, `.env.example`, `interface/__init__.py`, `interface/mcp_server.py` (apenas docstring) e `core/middleware.py` (apenas docstring).
  - **Escolha B (`interface/queue_writer.py` e `core/database.py`):** reafirmada **ADIADA para V4.1** (`0 bytes` alterados em toda a 4.5g).
- **Propostas ao Auditor registradas na 4.5g (NÃO implementadas — Regra 15a/15b; detalhamento em `audits/egm/4.5g-sintese.md`):**
  1. Runtime Docker (`ENV GRAFO_TRANSPORT=sse`, `USER` não-root, `healthcheck` real em `docker-compose.yml` sem `curl`/`|| exit 0` e remoção de `version: '3.8'`).
  2. Separação de `requirements.txt` (produção pura) vs `requirements-dev.txt` e inclusão de `pytest-timeout>=2.2.0`.
  3. Extras opcionais em `pyproject.toml`: `[gemini]` dedicado, `packaging` em `[dev]` e `tree_sitter` (`F4-014`).
  4. Suporte a `--help` / argumentos CLI em `main.py` (`concierge-mcp`).
  5. Governança MCP além de BL-011/BL-015: `governed_list_tools(session_id=None)`, validação de `GRAFO_DEFAULT_STATE` inválido no `__init__`, e avaliação de redução de `TOOL_DISCLOSURE_MATRIX` de 8 para 3 estados.
  6. Guardas de empacotamento em `tests/test_wheel_integrity.py` e `tests/test_dependency_pins.py` (bloquear retorno de pacotes dormentes).
  7. Higiene local de diretórios órfãos com apenas `__pycache__` (`agent/`, `agents/`, `core/parsers/`).

---

## 8. Rodada 4.6 — Segurança de Fronteira e Governança MCP (2026-11-25)

Remediação integral da Track 3 (`BL-011`, `BL-012`, `BL-013`, `BL-014`, `BL-015`) e da Proposta #5 da Rodada `4.5g`, executada a partir do commit base `e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d` com CI 6/6 GREEN por etapa:

- **Decisões Arquiteturais Homologadas pelo Humano:**
  - **Decisão 1A (`BL-011` / `BL-015` — Teto de Privilégio + Sessão Vinculada ao Transporte):** `GRAFO_DEFAULT_STATE` passa de `"EXECUTION"` para `"PLANNING"` (menor privilégio). `MCPToolGovernor` impõe `max_state` (`PLANNING < EXECUTION < MAINTENANCE`) igual ao `default_state` configurado no boot, levantando `SecurityException(PermissionError)` em qualquer tentativa de elevação acima de `max_state`. `concierge_set_state(state_name)` passa para `LOCAL_MUTATION` sem parâmetro `session_id`. `governed_call_tool` nunca lê `arguments.get("session_id")` e rejeita argumentos extras não declarados no schema da ferramenta.
  - **Decisão 2A (`BL-012` — Posse Persistente em Checkpoints):** Adicionada coluna `owner_hash TEXT NOT NULL DEFAULT ''` em `agent_checkpoints` (`storage/schema.py`) com migração idempotente `ALTER TABLE`. O servidor MCP resolve `owner_token` na ordem `X-Grafo-Agent-Token` -> `Authorization: Bearer` -> segredo efêmero em `WeakKeyDictionary` (HTTP/SSE), ou `GRAFO_AGENT_TOKEN` -> segredo efêmero (stdio). `core/checkpointer.py` verifica SHA-256 com `hmac.compare_digest` no namespace `(agent_id, session_id)` em `save`, `get` e `list` (política *fail-closed* sem adoção silenciosa de linhas legadas `owner_hash == ''` por chamadores autenticados), e `main.py::redact_log_secrets` passa a redigir `GRAFO_AGENT_TOKEN`.
  - **Decisão 3A (`BL-013` — Filtragem de `list_tools`):** `governed_list_tools` filtra sempre pela sessão vinculada ao transporte e é registrada tanto em `self._mcp.list_tools` quanto em `self._mcp._mcp_server.list_tools()`.
  - **Decisão 4A (`BL-014` + Proposta #5 da `4.5g`):** `TOOL_DISCLOSURE_MATRIX` consolidada para os 3 estados (`PLANNING`, `EXECUTION`, `MAINTENANCE`, todos com `"allowed_tools": []`); estados `default_state`/`max_state` inválidos levantam `ValueError` no `__init__`.
- **Commits Executados na Rodada 4.6:**
  - **C0 (`0cf527186902dc771c07c4d0b3273146614275f7`):** Revisão pré-execução EGM + Swarm (`audits/egm/4.6-{fatos,design,critic,sintese}.md`). CI 6/6 GREEN.
  - **C1 (`279f75189d4d8e3e6b630e076577e0044b5f9ff4`):** Governança de 3 estados, teto `max_state`, `PLANNING` padrão e reclassificação de `concierge_set_state` em `core/mcp_governor.py` (`17 READ_ONLY / 12 LOCAL_MUTATION / 2 DANGEROUS`; 5/5 mutantes mortos; 337 testes). CI 6/6 GREEN.
  - **C2 (`e196005114e2f5c7d9018c642372d632a0af1bf7`):** Vínculo de sessão ao transporte (`WeakKeyDictionary`), remoção de `session_id` em `concierge_set_state`, allowlist estrita de kwargs e dupla vinculação de `list_tools` em `interface/mcp_server.py` + `tests/test_mcp_security_governance.py` (5/5 mutantes mortos; 342 testes). CI 6/6 GREEN.
  - **C3 (`79afa2cca2abd4241742eecf1fbc75018e796cd4`):** Propriedade persistente `owner_hash` em `storage/schema.py`, `core/checkpointer.py`, `interface/mcp_server.py`, `main.py` + `tests/test_checkpoint_ownership.py` (5/5 mutantes mortos; 347 testes). CI 6/6 GREEN.
  - **C4 (`04a832fa74f5c02ba72f5261a9ece5ef6ce4d605`):** Documentação viva (`.env.example`, `README.md`, `README.pt-BR.md`, `docs-grafo-concierge/README.md`, `CHANGELOG.md`, `audits/fase4-decisoes.md`) e relatório final `audits/relatorio_4_6.md`. CI 6/6 GREEN.
- **Proposta do auditor, não implementada na 4.6:**
  - Janela estreita de TOCTOU em leitura em `core/checkpointer.py` (`get_checkpoint` e `list_checkpoints` executam a segunda query sem `AND owner_hash = ?` após `_verify_namespace_ownership` ver namespace vazio).

---

## 9. Rodada 4.7 — Hardening HTTP/SSE, Read-TOCTOU no Checkpointer e Higiene de DDL (2026-11-25)

Remediação cirúrgica das Propostas #1, #2 e #4 da `audits/egm/4.6-sintese.md` e da observação read-TOCTOU da Seção 8, executada a partir do commit base `873e8146611acdd36483fbf7dcff65261d94794c` (sem fase Swarm C0 — Regra 15(f)) com CI 6/6 GREEN por etapa:

- **Decisões Arquiteturais Homologadas pelo Humano:**
  - **Decisão 1A (Hardening `auth_middleware` HTTP/SSE + Redação Qdrant):** Removida integralmente a autenticação por query string em `interface/mcp_server.py::custom_sse_app`. O middleware (`BaseHTTPMiddleware`) passa a aceitar exclusivamente `Authorization: Bearer <key>` (`bearer` *case-insensitive*), validado em tempo constante via `hmac.compare_digest`. Adicionada `"GRAFO_QDRANT_API_KEY"` em `main.py::redact_log_secrets`.
  - **Decisão 2A (Separação Estrita `GRAFO_API_KEY` vs `X-Grafo-Agent-Token`):** Em `interface/mcp_server.py::_resolve_checkpoint_owner_token`, o ramo HTTP/SSE (`request_obj is not None`) passa a ler exclusivamente `X-Grafo-Agent-Token`, eliminando o fallback para `Authorization: Bearer` e isolando cada `ServerSession` sem `X-Grafo-Agent-Token` com segredo efêmero em `WeakKeyDictionary`.
  - **Fechamento Read-TOCTOU (`core/checkpointer.py`):** `get_checkpoint` e `list_checkpoints` passam a filtrar também por `AND owner_hash = ?` (`caller_hash = self._hash_owner_token(owner_token)`) após `_verify_namespace_ownership`.
  - **Higiene de DDL (`tests/test_agent_checkpointer.py`):** Substituído o `CREATE TABLE IF NOT EXISTS agent_checkpoints` manual pela aplicação oficial via `SchemaManager(conn).apply_full_schema()`, mantendo `queue_writer` intacto (Escolha B segue ADIADA para V4.1).
- **Commits Executados na Rodada 4.7:**
  - **C1 (`2dd3be7b20b4efd738713e4939fcac4b20bb328c`):** Hardening HTTP/SSE (`BaseHTTPMiddleware` + `hmac.compare_digest`, sem query string), separação estrita `X-Grafo-Agent-Token` vs Bearer e redação `GRAFO_QDRANT_API_KEY` (`tests/test_sse_auth_hardening.py`, `tests/test_checkpoint_ownership.py`, `tests/test_secret_redaction.py`; 4/4 mutantes mortos; 351 testes). CI 6/6 GREEN.
  - **C2 (`b3b14e2879e6baef6beb74828e6461f340553e7a`):** Fechamento read-TOCTOU (`AND owner_hash = ?`) em `core/checkpointer.py::get_checkpoint` e `list_checkpoints` + migração para `SchemaManager` em `tests/test_agent_checkpointer.py` (2/2 mutantes mortos; 0 hits `CREATE TABLE`; 353 testes). CI 6/6 GREEN.
  - **C3 (`docs(security)`):** Alinhamento documental (`.env.example`, `README.md`, `README.pt-BR.md`, `docs-grafo-concierge/README.md`, `CHANGELOG.md`, `audits/fase4-decisoes.md`) e relatório final `audits/relatorio_4_7.md`.

---

## 10. Rodada 4.8 — Docker Real com CI Smoke, CLI `concierge-mcp`, `/health` e Empacotamento Limpo (2026-11-25)

Endurecimento de entrega, empacotamento PEP 639, CLI do servidor MCP e validação em container real no CI (`Propostas #1, #2, #3, #4 e #6` da `audits/egm/4.5g-sintese.md`), executado a partir do commit base `3a1c378de5e01ecad1c179e92f11d3f04f2f8a31` com fase EGM+Swarm C0 somente leitura (`audits/egm/4.8-sintese.md`), mutações e CI 6/6 GREEN (C0–C2) / 7/7 GREEN (C3–C4):

- **Decisões Arquiteturais Homologadas pelo Humano:**
  - **Decisão 1A (`GET`/`HEAD /health` Público + Docker Não-Root + CI `docker-smoke`):** Exposta rota `GET`/`HEAD /health` em `interface/mcp_server.py::custom_sse_app` retornando `200 {"status": "ok"}`, isenta do middleware ASGI puro `_BearerAuthASGIMiddleware` apenas por correspondência exata (`method in ("GET", "HEAD")`, `path == "/health"`, `raw_path in (None, b"", b"/health")`). `Dockerfile` e `docker-compose.yml` corrigidos para `USER concierge` (`UID/GID 10001`), `GRAFO_TRANSPORT=sse`, `/app/data` e `HOME=/home/concierge`, named volume `concierge_data`, remoção de `version: '3.8'` e `HEALTHCHECK` Python sem `curl` ou `|| exit 0`, com job `docker-smoke` em `.github/workflows/ci.yml`.
  - **Decisão 2A (SPDX PEP 639 + `requirements-dev.txt` + Guardas):** `pyproject.toml` atualizado para `setuptools>=77.0.0`, `license = "MIT"`, `license-files = ["LICENSE"]`, remoção do classifier MIT legado, extra `gemini`, e `packaging>=21.0` + `setuptools>=77.0.0` em `dev`. Separação entre `requirements.txt` (produção pura) e `requirements-dev.txt`, e endurecimento de `tests/test_wheel_integrity.py` e `tests/test_dependency_pins.py`.
  - **Decisão 3A (Versionamento):** `version = "3.8.2"` preservada em `pyproject.toml` na Rodada 4.8 (sem git tags e sem publicação em PyPI). Fica registrado que **o alvo de bump de versão para `v4.1.0` ocorrerá na Rodada 4.9**, após atualização/fechamento final do `CHANGELOG.md`, e que a **Escolha B (`interface/queue_writer.py`) permanece ADIADA para `v4.2`**.
  - **CLI `concierge-mcp` (`main.py`):** Adicionados `_get_package_version()`, `_resolve_cli_argv()`, `parse_args(argv=None)` (`--help`, `--version`, `--transport {stdio,sse}`) e banner sem versão hardcoded antes de `setup_logging`/`decouple_stdin_from_fd0`/`bootstrap`.
- **Commits Executados na Rodada 4.8:**
  - **C0 (`4c1f954cf8db7533c88258860f4a4da63473fb14`):** Relatórios EGM + Swarm pré-execução (`audits/egm/4.8-{fatos,design,critic,sintese}.md`). CI 6/6 GREEN.
  - **C1 (`5f4c3458f3898310aafcec0096f104216d7ab7e1`):** CLI `concierge-mcp` (`main.py`), rota `/health` e `_BearerAuthASGIMiddleware` ASGI puro (`interface/mcp_server.py`, `tests/test_cli_mcp_entrypoint.py`, `tests/test_sse_auth_hardening.py`; 4/4 mutantes mortos; 361 testes). CI 6/6 GREEN.
  - **C2 (`5c95a79ed378ff8ef4753042aaa54f9ccd3525a1`):** Migração SPDX PEP 639, extra `[gemini]`, split `requirements-dev.txt` e guardas de wheel/pins (`pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `tests/test_wheel_integrity.py`, `tests/test_dependency_pins.py`; 3/3 mutantes mortos; 0 `SetuptoolsDeprecationWarning`; 363 testes). CI 6/6 GREEN.
  - **C3 (`142b995ab4699867c1323e3e069f58f8af59e67d`):** Hardening Docker não-root (`UID 10001`, SSE, `/health`), `docker-compose.yml`, job `docker-smoke` em `.github/workflows/ci.yml` e `tests/test_docker_manifests.py` (`367 testes` normal e `--reverse`). CI **7/7 GREEN** (incluindo `Docker Smoke` em `ubuntu-latest`).
  - **C4 (`docs(audit)`):** Atualização de `CONTRIBUTING.md`, `README.md`, `README.pt-BR.md`, `CHANGELOG.md`, `audits/fase4-decisoes.md` e relatório final `audits/relatorio_4_8.md`.

---

## 11. Rodada 4.9 — Preparação do Release `v4.1.0` (2026-11-25)

Preparação final para publicação do release `v4.1.0` (sem criação de tag Git, GitHub Release ou publicação no PyPI pelo agente; ações finais exclusivas do humano), partindo do commit base `2d43180639dda65fb2aa7c6262182ff58270a342` (sem fase Swarm C0 — Regra 15(f)), mantendo a tag pré-auditoria `V4.0.0` intocada e `storage/schema.py` (`SCHEMA_VERSION = "3.8.2"`) intacto:

- **Commits Executados na Rodada 4.9:**
  - **C1 (`54d50740028211d0244532d6618f1bd53298c1e6`):** Bump de `pyproject.toml` (`3.8.2` → `4.1.0`), versão dinâmica via `_get_version()` em `interface/cli.py` (com `--version` / `-V`, `cmd_status` e descrição do parser) e `interface/mcp_server.py` (`_handle_status`), validação dinâmica da versão no job `Docker Smoke` de `.github/workflows/ci.yml` e testes (`tests/test_cli_mcp_entrypoint.py`, `tests/test_dependency_pins.py`, `tests/test_wheel_integrity.py`; 3/3 mutantes mortos; 369 testes). CI **7/7 GREEN**.
  - **C2 (`docs(release)`):** Limpeza de comentário legado em `.env.example`, promoção do `CHANGELOG.md` para `## [4.1.0] - 2026-11-25` (com nota sobre `V4.0.0` histórica e `Escolha B` / `queue_writer` planejada para `v4.2`), atualização de `README.md` / `README.pt-BR.md`, reconversão de `audits/relatorio_4_8.md` para UTF-8 puro (`0` bytes NUL), validação pré-publicação de `sdist` + `wheel` + smoke install isolado em venv limpo fora do repositório, e relatório final `audits/relatorio_4_9.md` (UTF-8 puro).
- **Ações Finais Reservadas ao Humano (após gate da 4.9):**
  1. `git tag -a v4.1.0 -m "Release v4.1.0"` e `git push origin v4.1.0`
  2. Publicação do GitHub Release `v4.1.0`
  3. Build e upload do pacote `concierge-graph==4.1.0` no PyPI





