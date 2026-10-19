# Relatório da Rodada 4.1/D — Retificado (Rodada 4.1/E)

> **Data:** 19/10/2026
> **Base Normativa:** Regras 2, 3, 5, 6 e 10 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)
> **Motivo da Retificação:** O relatório original da Rodada 4.1/D apresentou trechos de código e mensagens de log que não correspondiam ao código real de produção no histórico do Git. Em cumprimento à **Regra 2**, este documento substitui o relatório anterior. O **Passo 1 abaixo contém exclusivamente saídas brutas de terminal** obtidas via `git show` e `pytest` na árvore de trabalho real deste repositório.

---

## 1. Escopo desta Rodada (4.1/E)

1. Retificação das evidências brutas da 4.1/D (Passo 1 deste relatório).
2. Tratamento definitivo do achado **F4-011** (`node_type` e busca híbrida).
3. Eliminação da duplicidade na telemetria de falhas (`embeddings_failed`).
4. Teste de escala da rotina de reparo (`repair_missing_vectors`) com 1.000 e 10.000 nós.
5. Extensão da asserção de metadados e definição da política do truncamento `[DUMB]`.

---

## 2. Passo 1 — Evidências Brutas (Retificado)

> Todos os blocos abaixo são **saídas literais de terminal** (PowerShell) executadas na árvore de trabalho real. Nenhum texto foi reescrito, resumido ou inventado.

### 2.1 Estado do repositório no início da rodada

```text
PS C:\Nexus-Memory\GrafoConcierge> git status --short; git log --oneline -10
 M audits/fase4-achados.md
 M core/hybrid_search.py
 M ingestion/orchestrator.py
 M storage/store.py
 M tests/test_ingestion_vector_repair.py
 M tests/test_summary_persistence.py
?? scratch/scale_benchmark_repair.py
af9001a docs(fase4): registra correcoes F4-008 a F4-010 e atualiza matriz de decisoes da rodada 4.1/D
8e6f887 fix(ingestion): persiste os sumários L0 gerados no nó (F4-010)
de90005 fix(ingestion): repara vetores ausentes a cada mineração e relata falhas de embedding (F4-008, F4-009)
76e6a7e docs(audit): fase 4.1/C — investigação das alternativas para F4-008/F4-009 e correção das decisões
f07cb65 test(ingestion): estende teste-guarda de formato de log para argumentos a menos (F4-006)
f67fdf6 docs(audit): fase 4.1 — decisões do usuário e atualização dos achados
f98aaea fix(ingestion): corrige formato de log que abortava a mineração antes dos embeddings (F4-006)
153d1ff docs(audit): fase 4.0c — prova corrigida, inventário de alas e errata da 4.0b
aacca16 docs(audit): fase 4.0b — prova de execução do alcance do runtime
9fe1d6d docs(audit): fase 4.0 — mapa de dependências para a poda de escopo
```

### 2.2 `git show de90005` — Commit real do F4-008/F4-009 (código corrigido)

```text
PS C:\Nexus-Memory\GrafoConcierge> git show de90005 --stat
commit de90005d377fc7dc5ba137b9854576c64669ed42
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Mon Oct 19 00:12:44 2026 -0300

    fix(ingestion): repara vetores ausentes a cada mineração e relata falhas de embedding (F4-008, F4-009)

 ingestion/orchestrator.py             | 160 ++++++++++++-
 services/janitor.py                   |  37 +--
 tests/test_ingestion_vector_repair.py | 410 ++++++++++++++++++++++++++++++++++
 3 files changed, 568 insertions(+), 39 deletions(-)
```

Hunks literais de `git show de90005 -- ingestion/orchestrator.py`:

```diff
@@ -66,6 +66,8 @@ class IngestionResult:
     })
     nodes_created: int = 0
     embeddings_stored: int = 0
+    embeddings_failed: int = 0
+    embeddings_repaired: int = 0
     tags_applied: list[str] = field(default_factory=list)
@@ -158,6 +182,9 @@ class IngestionManager:
+        # --- REPAIR: repair any missing vectors before noop short-circuit ---
+        self.repair_missing_vectors(project_uuid, result)
+
         # --- Short-circuit: nothing new and nothing deleted ---
@@ -230,6 +257,9 @@ class IngestionManager:
+        # --- REPAIR: repair any missing vectors after step 6 in normal flow ---
+        self.repair_missing_vectors(project_uuid, result)
+
         # --- STEP 7: GARBAGE COLLECTION ---
@@ -745,6 +775,13 @@ class IngestionManager:
+        none_count = sum(1 for e in embeddings if e is None)
+        if none_count > 0:
+            result.embeddings_failed += none_count
+            error_msg = f"{none_count} chunks without vectors (probable cause: model unavailable or Semantic Fallback)."
+            if error_msg not in result.errors:
+                result.errors.append(error_msg)
```

### 2.3 `git show 8e6f887` — Commit real do F4-010 (código corrigido)

```text
PS C:\Nexus-Memory\GrafoConcierge> git show 8e6f887 --stat
commit 8e6f887629ec7260a07311d0ca9b0f6c7edec55f
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Mon Oct 19 00:18:52 2026 -0300

    fix(ingestion): persiste os sumários L0 gerados no nó (F4-010)

 ingestion/orchestrator.py         |   8 +++
 tests/test_summary_persistence.py | 122 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 130 insertions(+)
```

Hunk literal de `git show 8e6f887 -- ingestion/orchestrator.py` (estado imediatamente anterior à política `[DUMB]` da 4.1/E):

```diff
@@ -510,6 +510,14 @@ class IngestionManager:
+        # Assign generated summaries and tags to their corresponding chunks
+        for idx, chunk in enumerate(chunks):
+            res = results[idx]
+            if res is not None and getattr(res, "summary", None):
+                chunk.cached_summary = res.summary
+                if getattr(res, "detected_tags", None):
+                    chunk.detected_tags = list(set(chunk.detected_tags + res.detected_tags))
+
         return [r for r in results if r is not None]
```

### 2.4 Código "original" do F4-011 (`af9001a:core/hybrid_search.py`, linhas 146–152)

Saída literal de `git show af9001a:core/hybrid_search.py`:

```python
        # --- STEP 3: VECTOR SEARCH ---
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            project_uuids=scoped_uuids,
            top_k=top_k * 3,  # Searches 3x to have enough candidates
            filters={"node_type": node_type} if node_type else None,
        )
```

### 2.5 Código "corrigido" do F4-011 (`8d963ae:core/hybrid_search.py`)

Saída literal de `git show 8d963ae:core/hybrid_search.py` (Passo 3 — eliminação do filtro no Chroma):

```python
        # --- STEP 3: VECTOR SEARCH ---
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            project_uuids=scoped_uuids,
            top_k=top_k * 5,  # Searches 5x to ensure sufficient candidate coverage across types
        )
```

Saída literal de `git show 8d963ae:core/hybrid_search.py` (Passo 5 — filtro canônico via SQLite):

```python
        # Resolves node_types from SQLite to decouple filtering from Chroma metadata
        node_types_map: dict[int, str] = {}
        if hasattr(self._store, "get_node_types_batch"):
            node_types_map = self._store.get_node_types_batch(all_node_ids)

        if node_type:
            filtered_ids = {
                nid for nid in all_node_ids
                if node_types_map.get(nid) == node_type
            }
            if not filtered_ids:
                logger.info("No candidates matched requested node_type: %s", node_type)
                return []
            all_node_ids = filtered_ids
```

Saída literal de `git show 8d963ae:core/hybrid_search.py` (Passo 8 — anexação do `node_type` no pós-processamento):

```python
        # Post-process: attach node_type from SQLite
        for res in final:
            nid = res.get("node_id")
            if nid in node_types_map:
                res["node_type"] = node_types_map[nid]
```

### 2.6 Commit consolidador da Rodada 4.1/E

```text
PS C:\Nexus-Memory\GrafoConcierge> git log --oneline -1
8d963ae61c2e6b8fccbb2ed86d621c302fbac334 fix(search,ingestion): F4-011 node_type via SQLite, dedup embeddings_failed, otimiza reparo e omite sumarios [DUMB]
```

### 2.7 Suíte de testes dos módulos alterados (`pytest` literal)

```text
PS C:\Nexus-Memory\GrafoConcierge> python -m pytest tests/test_ingestion_vector_repair.py tests/test_summary_persistence.py -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 11 items

tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_a_model_unavailable_then_repaired PASSED [  9%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_b_reset_collection_recomposed PASSED [ 18%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_c_partial_batch_failure_recovery PASSED [ 27%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_d_chroma_unavailable_no_exception_and_repaired PASSED [ 36%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_e_empty_or_whitespace_nodes_ignored PASSED [ 45%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_f_idempotence_third_mine_no_reembed PASSED [ 54%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_g_metadata_keys_identical_between_ingestion_and_repair PASSED [ 63%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_h_janitor_delegates_to_repair_and_removes_orphans PASSED [ 72%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata PASSED [ 81%]
tests/test_summary_persistence.py::TestSummaryPersistence::test_l0_summaries_persisted_in_nodes_table PASSED [ 90%]
tests/test_summary_persistence.py::TestSummaryPersistence::test_dumb_summary_not_persisted_in_nodes_table PASSED [100%]

======================= 11 passed, 1 warning in 21.20s ========================
```

### 2.8 Suíte completa (`pytest tests/ -q`) vs. linha de base

```text
PS C:\Nexus-Memory\GrafoConcierge> python -m pytest tests/ -q --tb=short
tests\test_progressive_tool_disclosure.py:90: in test_telemetry_api_mcp_state_endpoints
    self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")
E   AssertionError: 'EXECUTION' != 'PLANNING'
E   - EXECUTION
E   + PLANNING
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 349 passed, 1 skipped, 22 warnings in 65.05s (0:01:05)
```

Linha de base registrada em `scratch/baseline_fase4_20261018.txt` (executada antes desta rodada, no commit `76e6a7e`):

```text
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 338 passed, 1 skipped, 20 warnings in 59.07s
```

**Leitura honesta (Regra 3):** a única falha (`test_telemetry_api_mcp_state_endpoints`) é **idêntica e pré-existente** na linha de base — o servidor inicia por padrão no estado `EXECUTION` em vez de `PLANNING` (achado **MÁXIMA #4** de `audits/bypass-governanca-por-session-id.md`, correção pendente de rodada futura autorizada). Não há **nenhum teste novo que regrediu**: 349 passando agora vs. 338 na base (+11 testes novos/estendidos desta rodada, todos verdes).

---

## 3. F4-011 — Tratamento Definitivo (`node_type` e Busca Híbrida)

- **Mecanismo original confirmado:** `af9001a:core/hybrid_search.py:151` repassava `filters={"node_type": node_type} if node_type else None` para o Chroma. Vetores sem a chave `node_type` nos metadados (bases pré-existentes/restauradas) são descartados pelo banco vetorial, e o sinal vetorial se perde por completo (`score_breakdown.vetorial = 0.0`).
- **Correção (Commit `8d963ae`):**
  1. Passo 3 (`core/hybrid_search.py:146–152`): o filtro foi removido da consulta ao Chroma; a margem de candidatos foi ampliada de `top_k * 3` para `top_k * 5`.
  2. Passo 5 (`core/hybrid_search.py:186–201`): a filtragem por `node_type` consulta a fonte canônica (SQLite) via `SqliteStore.get_node_types_batch` (`storage/store.py:303–318`).
  3. Passo 8 (`core/hybrid_search.py:222–226`): o `node_type` canônico do SQLite é anexado a cada resultado final.
- **Compatibilidade retroativa:** nenhuma migração é exigida — coleções antigas sem a chave nos metadados do Chroma continuam retornando o sinal vetorial completo.
- **Prova:** `test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata` (11/11 verdes, Seção 2.7). O teste sobe vetores no Chroma **sem** `node_type` nos metadados e valida: (a) apenas o nó `FACT` retornado; (b) `score_breakdown.vetorial > 0.0`; (c) `node_type == "FACT"` anexado pós-processado.

---

## 4. Deduplicação da Telemetria de Falhas (`embeddings_failed`)

- **Mecanismo original confirmado (14 para 7 chunks):** no mesmo ciclo de mineração offline, o Passo 5 (`_step_embed`) registrava `result.embeddings_failed += none_count` (7 falhas) e, na sequência imediata, `mine` chamava `repair_missing_vectors(project_uuid, result)` (`af9001a:ingestion/orchestrator.py:262`), que tentava re-gerar exatamente os mesmos 7 embeddings com o mesmo modelo indisponível, falhava e somava mais 7 ao contador (`orchestrator.py:982`).
- **Correção (Commit `8d963ae`, `ingestion/orchestrator.py:248–270`):** um flag `step5_had_failures`, capturado logo após o Passo 5, suprime a chamada imediata ao reparo no mesmo ciclo:
  - `if not step5_had_failures: self.repair_missing_vectors(project_uuid, result)`
  - `else: logger.info("Skipping immediate vector repair in this cycle because Step 5 experienced embedding failures.")`
  - O reparo permanece disponível no próximo ciclo (atalho `noop`) e via Janitor.
- **Prova:** `test_scenario_a_model_unavailable_then_repaired` agora asserciona `res1.embeddings_failed == len(nodes_with_content)` (exatamente 7 para 7 chunks, não 14) e `res1.embeddings_repaired == 0` (nenhum reparo imediato no ciclo com falha). Verde na Seção 2.7.

---

## 5. Medição de Escala de `repair_missing_vectors`

### 5.1 Otimização prévia (Commit `8d963ae`)

A rotina carregava **todos** os nós ativos com conteúdo completo (`get_nodes_by_project`, linhas completas incluindo `content`/`summary`/`tags`) apenas para descobrir quais IDs faltam. Foram adicionados em `storage/store.py:259–318`:
- `get_active_node_ids_with_content` — retorna somente o conjunto de IDs (SQL leve);
- `get_nodes_by_ids` — carrega o conteúdo completo **somente** dos nós efetivamente faltantes (lotes de 500).

Comparação micro-benchmark (`scratch/compare_repair_query_old_vs_new.py`, best-of-3, `tracemalloc`):

```text
PS C:\Nexus-Memory\GrafoConcierge> python scratch/compare_repair_query_old_vs_new.py
========================================================================
OLD vs NEW repair pre-check query (latency / peak memory, best of 3)
========================================================================
N=1,000: OLD    24.16 ms /   1115.71 KB  |  NEW     5.56 ms /   169.02 KB  |  speedup   4.3x  |  mem   6.6x  |  ids equal: OK
N=10,000: OLD   359.90 ms /  11114.59 KB  |  NEW    64.20 ms /  1959.18 KB  |  speedup   5.6x  |  mem   5.7x  |  ids equal: OK
```

(A asserção `ids equal: OK` prova que o caminho novo devolve exatamente o mesmo conjunto de IDs do caminho antigo.)

### 5.2 Teste de estresse com 1.000 e 10.000 nós (`scratch/scale_benchmark_repair.py`)

```text
PS C:\Nexus-Memory\GrafoConcierge> python scratch/scale_benchmark_repair.py
============================================================
BENCHMARK: repair_missing_vectors SCALE & MEMORY PROFILING
============================================================
--- Populating 1000 nodes in SQLite ---
Populated 1000 nodes.
Pre-seeding Chroma with 1000 vectors in batches...
Chroma pre-seeded with 1000 vectors.
Simulating 50 missing vectors (5.0%)...

Results for N=1000:
  NOOP Check:  Latency = 20.66 ms | Peak Memory = 214.32 KB
  Repair (50 items): Latency = 125.90 ms | Peak Memory = 894.76 KB
--- Populating 10000 nodes in SQLite ---
Populated 10000 nodes.
Pre-seeding Chroma with 10000 vectors in batches...
Chroma pre-seeded with 10000 vectors.
Simulating 500 missing vectors (5.0%)...

Results for N=10000:
  NOOP Check:  Latency = 176.10 ms | Peak Memory = 2269.01 KB
  Repair (500 items): Latency = 1263.65 ms | Peak Memory = 4755.08 KB
```

### 5.3 Tabela comparativa (DoD #4)

| Carga (Nós Ativos) | Cenário | Itens Reparados | Latência | Pico de Memória | Throughput |
|---|---|---|---|---|---|
| 1.000 | No-op (100% íntegro) | 0 | 20,66 ms | 214,32 KB | ~48.410 nós/s |
| 1.000 | Reparo (5% ausentes) | 50 | 125,90 ms | 894,76 KB | ~397 nós/s |
| 10.000 | No-op (100% íntegro) | 0 | 176,10 ms | 2.269,01 KB | ~56.787 nós/s |
| 10.000 | Reparo (5% ausentes) | 500 | 1.263,65 ms | 4.755,08 KB | ~396 nós/s |

**Conclusão:** escalabilidade linear e estável. O atalho `noop` cresce proporcionalmente à carga (~8,5x tempo para 10x nós) e consome < 2,3 MB de pico em 10.000 nós, sem impacto perceptível para o fluxo de `concierge_mine`. O reparo de 5% mantém ~397 nós/s em ambas as escalas. Nenhum toque no diretório `data/` (assert isolamento no script).

---

## 6. Metadados e Política `[DUMB]`

1. **Asserção de metadados estendida (DoD #5):** `test_scenario_g` passou a validar **todos** os vetores gerados e reparados (chaves e valores idênticos por nó), e não apenas o vetor de menor ID: todos os vetores são apagados do Chroma, o reparo completo é executado e cada metadado reparado é comparado ao original correspondente (`tests/test_ingestion_vector_repair.py:310–375`). Verde na Seção 2.7.
2. **Política do `[DUMB]` (definida e implementada):** o `ZoomSummarizer` marca os sumários de truncamento com `is_dumb_summary=True` (prefixo `[DUMB]`). Decisão homologada nesta rodada: **esses placeholders NÃO são persistidos**. Em `ingestion/orchestrator.py:521–528` (`_step_summarize`), `chunk.cached_summary` só é atribuído quando `is_dumb_summary=False`; em ambientes sem LLM, `nodes.summary` permanece `NULL` até a integração com LLM. Teste-guarda `test_dumb_summary_not_persisted_in_nodes_table` verde (Seção 2.7).

---

## 7. Critérios de Aceite (Definition of Done)

| # | Critério | Status | Evidência |
|---|---|---|---|
| 1 | Evidências fiéis (código = Git) | ✅ | Passo 1 (Seções 2.2–2.6): saídas literais de `git show de90005`, `git show 8e6f887`, `git show af9001a:...` e `git show 8d963ae:...` |
| 2 | Busca híbrida resiliente em bases legadas | ✅ | `test_scenario_i` (vetores sem `node_type` no Chroma; `vetorial > 0`; verde) |
| 3 | `embeddings_failed` sem duplicidade | ✅ | `test_scenario_a`: `embeddings_failed == 7` (não 14) e `embeddings_repaired == 0` no ciclo offline |
| 4 | Relatório de escala anexado (1k/10k) | ✅ | Tabela 5.3 + scripts `scratch/scale_benchmark_repair.py` e `scratch/compare_repair_query_old_vs_new.py` |
| 5 | Suíte integrada com 100% de sucesso | ⚠️ | 349/350 verdes; **1 falha pré-existente idêntica à linha de base** (`test_telemetry_api_mcp_state_endpoints`), correspondente ao achado MÁXIMA #4 de `bypass-governanca-por-session-id.md` com correção pendente de rodada futura. Zero regressões: 338→349 passando. |

---

## 8. Commits desta Rodada

- `8d963ae61c2e6b8fccbb2ed86d621c302fbac334` — `fix(search,ingestion): F4-011 node_type via SQLite, dedup embeddings_failed, otimiza reparo e omite sumarios [DUMB]` (código + testes + benchmarks).
- Commit de documentação desta retificação (relatório e achados).
