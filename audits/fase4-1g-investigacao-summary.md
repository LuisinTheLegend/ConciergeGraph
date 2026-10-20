# Relatório Técnico: Investigação Somente-Leitura de `nodes.summary` e Resíduo F4-009

> **Fase 4 — Rodada 4.1/G**  
> **Data:** 2026-10-20  
> **Status:** Somente-Leitura / Auditoria Concluída  
> **Protocolo:** AUDIT_PROTOCOL.md (Regras 2, 3, 4, 7, 10, 11)  
> **Estado de Partida:** `bd821e7`  
> **Commit da Parte A:** `4c505d1`  
> **Escopo:** Retificação documental de F4-009 + Investigação profunda de produção sobre `nodes.summary` (sem alteração de código de produção e sem alteração em `data/concierge.db`).

---

## 1. PARTE A — Retificação Documental Concluída (Commit `4c505d1`)

### 1.1 Retificação de F4-009 (`audits/fase4-achados.md`)
Foi removida a afirmação incorreta de que o Background Janitor gerava metadados divergentes da ingestão padrão "omitindo `project_uuid`".

**Prova Obrigatória por Comando (`git show 76e6a7e:services/janitor.py` linhas 388–393):**
```python
                    metadata = {
                        "project_uuid": project_uuid,
                        "node_type": n.get("type", "UNKNOWN"),  # Divergência real: tipo do chunk em vez do node_type do nó
                        "label": n.get("label", ""),
                    }
                    self._vector.add(
```
*Constatação:* O Janitor já gravava `project_uuid`. A única divergência real era o campo `node_type` (que recebia `n.get("type")` do chunk em vez de `n.get("node_type")` do nó). A menção falsa foi removida de `audits/fase4-achados.md` e de `audits/fase4-1d-relatorio-retificado.md`.

**Auditoria por Grep (`git grep -n "omitindo" -- audits/`):**
- *Antes:*
```text
audits/fase4-1d-relatorio-retificado.md:83: Janitor ao reparar vetores órfãos gerava metadados divergentes da ingestão padrão (omitindo `project_uuid` e usando `n.get("type")` no lugar de `n.get("node_type")`),
audits/fase4-achados.md:143: Janitor ao reparar vetores órfãos gerava metadados divergentes da ingestão padrão (omitindo `project_uuid` e usando `n.get("type")` no lugar de `n.get("node_type")`),
```
- *Depois:*
```text
(zero ocorrências de menção indevida)
```

### 1.2 Registro de Decisão Homologada (`audits/fase4-decisoes.md`)
Registrada a decisão oficial do dono do projeto (2026-10-19):
> *"[DUMB]: sem LLM, nodes.summary permanece NULL (não persistir o placeholder de truncamento)".*

### 1.3 Atualização do Roadmap (`audits/fase4-roadmap.md`)
- Rodada 4.1/E ajustada para "Código OK; teste do [DUMB] corrigido na 4.1/F".
- Rodada 4.1/F marcada como Concluída e verificada pelo auditor independente em 2026-10-19.
- Rodada 4.1/G registrada.
- Achados F4-009 e F4-012 atualizados na tabela resumo.
- Seção 6 item 7 atualizado como "confirmado pelo dono".

---

## 2. PARTE B — Investigação de Leitura sobre `nodes.summary`

### B1. Mapeamento de Pontos de Leitura e Escrita em Produção
Mapeamento executado via `git grep -n "summary" -- core/ ingestion/ services/ storage/ interface/`:

| Módulo:Linha | Função / Componente | Papel | O que ocorre se `summary IS NULL` | O que ocorre se `summary LIKE '[DUMB]%'` |
|---|---|---|---|---|
| `storage/schema.py:164` | `nodes_fts` (Virtual Table FTS5) | DDL / Trigger | Não gera tokens adicionais de summary no BM25; busca foca em `label` e `tags`. | Contamina o BM25 com o token `[DUMB]` e fragmentos literais de código de até 500 caracteres repetidos. |
| `storage/store.py:210,460` | `create_node`, `create_nodes_batch` | Escrita | Grava `NULL` no banco SQLite (`nodes.summary`). | Gravava a string `[DUMB]...` (comportamento legado anterior ao commit `8d963ae`). |
| `storage/store.py:314,327` | `get_lightweight_topology` | Leitura | Omitido intencionalmente na query SQL (`SELECT id, label, node_type`); sem efeito. | Omitido intencionalmente na query SQL; sem efeito. |
| `core/hybrid_search.py:163` | `HybridSearchEngine.search` | Leitura (via FTS5) | Apenas termos de `label`, `code_raw` e `tags` participam do match textual. | Consultas ganham falso match por frases ou palavras contidas no snippet truncado gravado no `summary`. |
| `core/graph_rag.py` | `GraphRAGEngine` | Leitura | **Não lê `nodes.summary`**. Opera exclusivamente sobre tabelas `files` e `ast_edges`. | Sem efeito (indiferente). |
| `core/middleware.py:182` | `GrafoConcierge.wake_up` | Leitura (`project.summary`) | Se L2 não foi gerado, usa fallback: `"Project '...' — no Context Compass defined."`. | Se L2 foi gerado sob `[DUMB]`, exibe Bússola contaminada com `[DUMB]`. |
| `core/middleware.py:381` | `GrafoConcierge.lazy_load` (`concierge_load`) | Leitura | Retorna `"summary": None` dentro do dicionário do nó carregado. | Retorna `"summary": "[DUMB] ..."` diretamente ao cliente MCP/agente consumidor. |
| `core/middleware.py:503` | `get_implementations` | Leitura | **Não lê nem retorna `summary`**. Retorna apenas `id, label, type, project_uuid, content, file_hash`. | Sem efeito (campo omitido da projeção). |
| `interface/mcp_server.py:1158` | `_handle_search` (`concierge_search`) | Leitura | Retorna `"summary": ""` no item enriquecido. | Retorna `"summary": "[DUMB] ..."` no item enriquecido para o modelo consumidor. |
| `interface/mcp_server.py:1341` | `_handle_search_symbols` (`search_symbols`) | Leitura | Retorna `"summary": ""` no símbolo retornado. | Retorna `"summary": "[DUMB] ..."` no símbolo retornado. |
| `ingestion/orchestrator.py:1013` | `generate_project_context` (Zoom L1/L2) | Leitura | Se todos os nós forem `NULL`, aborta com `"ZOOM GEAR: nenhum resumo L0 encontrado"`, retornando 0 L1s e L2 `None`. | Carrega todos os resumos `[DUMB]` como L0s e os concatena no bloco de entrada dos clusters L1. |
| `services/janitor.py:563` | `_generate_community_summaries` | Leitura | Monta prompt de comunidade com `"- [label] (type): Sem resumo"`. | Monta prompt de comunidade contendo os snippets truncados `[DUMB]` de cada nó membro. |

---

### B2. Verificação de Entrada no Índice FTS5
**Constatação Técnica:** `nodes.summary` **entra** diretamente no índice FTS5.

**Evidência Literal em `storage/schema.py:164–184`:**
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label, tags, summary, content='nodes', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;
```
*Conclusão:* Quando `summary` contém `[DUMB] <fragmento>`, o BM25 é **efetivamente contaminado**:
1. O termo `DUMB` passa a ser indexado em 3.492 linhas.
2. A repetição dos tokens do código dentro do campo `summary` altera o cálculo de `bm25(nodes_fts)`.
3. Conforme provado empiricamente em B5(c), nós contendo `[DUMB]` sofrem variação artificial de ranking.

---

### B3. Geração de Sumários Superiores (L1/L2) a partir de `nodes.summary`
**Constatação Técnica:** Os sumários de nível superior (L1 - Clusters e L2 - Bússola de Contexto) **são gerados diretamente a partir dos sumários L0 persistidos em `nodes.summary`**.

**Evidência Literal em `ingestion/orchestrator.py:1008–1035`:**
```python
        # Fetch nodes with populated summary (L0s already generated)
        all_nodes = self._store.get_nodes_by_project(project_uuid)
        l0_summaries: list[SummaryResult] = []

        for node in all_nodes:
            if node.get("type") in ("directory", "cluster", "project") or not node.get("summary"):
                continue
...
            l0_summaries.append(SummaryResult(
                level=ZoomLevel.L0,
                summary=node["summary"],
                source_label=node.get("label", "unknown"),
                source_chunks=1,
                detected_tags=tags if isinstance(tags, list) else [],
            ))

        if not l0_summaries:
            logger.warning("ZOOM GEAR: nenhum resumo L0 encontrado para %s.", project_uuid)
            return {"l1_count": 0, "l2_summary": None, "l2_tags": []}
```
**Efeito de `[DUMB]`:**
1. Em `ingestion/summarizer.py:607`, o bloco de texto enviado para a síntese L1 é montado com:
   `f"- [{s.source_label}]: {s.summary}"`.
2. Se `s.summary` for `[DUMB] ...`, o sintetizador (LLM ou truncador fallback) recebe lixo repetitivo como entrada.
3. No fallback sem LLM, o L1 e o L2 também viram `[DUMB]` truncados e o L2 grava esse texto na coluna `projects.summary` (lida no `concierge_wakeup`/`resume`).
4. Se `nodes.summary` for `NULL`, a geração de L1/L2 é suspensa de forma limpa e segura (retornando `l1_count: 0, l2_summary: None`), sem produzir alucinações.

---

### B4. Caminho de Backfill e Comportamento com Arquivos Inalterados vs Modificados
**Constatação Técnica:** **NÃO existe caminho de backfill automático para arquivos inalterados.**

**Prova Empírica em Banco Temporário (`scratch/investigate_backfill.py`):**
Executado teste com banco SQLite e coleção Chroma criados em `tempfile.TemporaryDirectory`.

**Saída Literal do Comando:**
```text
FASE 1 (Sem LLM - 1a mineracao):
  files_processed=1, files_skipped=0
  nodes.summary=None

FASE 2 (LLM configurado, arquivo INALTERADO):
  files_processed=0, files_skipped=1
  real_llm.calls=0
  nodes.summary=None

FASE 3 (LLM configurado, arquivo MODIFICADO):
  files_processed=1, files_skipped=0
  real_llm.calls=2
  nodes.summary='Genuine AI Summary for process_data'
```

**Mecanismo Identificado:**
- Quando o arquivo não é alterado, o crawler/orquestrador calcula o SHA-256 e encontra o registro correspondente no banco SQLite (`find_node_by_hash`).
- O arquivo é pulado (`files_skipped = 1`). A etapa de `_step_summarize` **não é executada** e o objeto LLM sequer é acionado (`real_llm.calls = 0`).
- Portanto, se um arquivo foi minerado sem LLM (deixando `summary = NULL` ou com o legado `[DUMB]`), configurar o LLM posteriormente **NÃO atualizará os sumários**, a menos que o arquivo seja fisicamente editado no disco ou que uma rotina explícita de backfill seja desenvolvida.

---

### B5. Experimento em Cópia Isolada de `data/concierge.db`
Executado via `scratch/b5_experiment.py` sobre cópias físicas `scratch/concierge_b5_orig.db` e `scratch/concierge_b5_clean.db` (nenhuma consulta tocou no arquivo original).

#### (a) Contagens por Situação
- **Total de nós no banco:** `4.895`
- **Nós com `summary LIKE '[DUMB]%'`:** `3.492` (**71,34%**)
- **Nós com `summary IS NULL`:** `1.403` (**28,66%**)
- **Nós com outro sumário (genuíno/outro):** `0` (**0,00%**)

#### (b) Distribuição de `[DUMB]` por `nodes.type`
| Tipo de Nó (`nodes.type`) | Total | Com `[DUMB]` | % `[DUMB]` | `NULL` |
|---|---|---|---|---|
| `raw` | 1.761 | 1.753 | 99,55% | 8 |
| `section` | 1.226 | 954 | 77,81% | 272 |
| `config` | 281 | 275 | 97,86% | 6 |
| `method` | 814 | 268 | 32,92% | 546 |
| `class` | 250 | 160 | 64,00% | 90 |
| `function` | 165 | 72 | 43,64% | 93 |
| `module` | 93 | 10 | 10,75% | 83 |
| `directory` | 305 | 0 | 0,00% | 305 |

#### (d) Tamanho em Bytes dos Sumários `[DUMB]`
- **Tamanho total ocupado por `[DUMB]`:** `1.584.087 bytes` (**1,51 MB**)
- **Média por sumário `[DUMB]`:** `453,6 bytes`
- **Mínimo / Máximo:** `12 bytes` / `609 bytes`

#### (c) Comparação Real de Top-5 na Busca Híbrida: Cópia Original vs Cópia Limpa (`SET summary = NULL`)
Foram testadas 8 consultas representativas sobre o projeto `6151e6dc-cdbc-4007-a014-6724bdf7dfbb` (GrafoConcierge).
*Nota de Ambiente:* A coleção Chroma local possui apenas 16 vetores gravados (devido ao achado histórico F4-006 pré-correção), logo o sinal da busca híbrida para este projeto opera no motor FTS5 puro com rerank e cálculo de centralidade/recência.

**Resultados Literais do Experimento:**

```text
--- CONSULTA: 'SqliteStore' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=8811 score=0.3500 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore
    #2 id=8769 score=0.2718 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #3 id=8771 score=0.2718 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #4 id=8773 score=0.2718 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #5 id=8778 score=0.2718 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
  [CÓPIA LIMPA - Com NULL]:
    #1 id=8811 score=0.3500 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore
    #2 id=8769 score=0.2639 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #3 id=8771 score=0.2639 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #4 id=8773 score=0.2639 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
    #5 id=8778 score=0.2639 (vet=0.000, fts=0.000) | storage/store.py::SqliteStore._do
  --> IDs idênticos: True | Scores idênticos: False

--- CONSULTA: 'hybrid' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=8404 score=0.2846 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine
    #2 id=9396 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/05_HYBRID_SEARCH_AND_ROUTING.md::🔍 Hybrid Search v4, Self-Healing & Frugal GraphRAG (v4.0.0)
    #3 id=8400 score=0.2596 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.__init__
    #4 id=8401 score=0.2596 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.search
    #5 id=8415 score=0.2596 (vet=0.000, fts=0.000) | core/middleware.py::GrafoConcierge.hybrid_search
  [CÓPIA LIMPA - Com NULL]:
    #1 id=8404 score=0.3000 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine
    #2 id=8400 score=0.2750 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.__init__
    #3 id=8401 score=0.2750 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.search
    #4 id=8415 score=0.2750 (vet=0.000, fts=0.000) | core/middleware.py::GrafoConcierge.hybrid_search
    #5 id=8718 score=0.2648 (vet=0.000, fts=0.000) | storage/logic.py::GraphLogic.hybrid_search_score
  --> IDs idênticos: False | Scores idênticos: False

--- CONSULTA: 'concierge' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=9308 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_register`
    #2 id=9310 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_status`
    #3 id=9316 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_mine`
    #4 id=9317 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_wakeup`
    #5 id=9318 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_resume`
  [CÓPIA LIMPA - Com NULL]:
    #1 id=9308 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_register`
    #2 id=9310 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_status`
    #3 id=9316 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_mine`
    #4 id=9317 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_wakeup`
    #5 id=9318 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/02_MCP_TOOLS_REFERENCE.md::`concierge_resume`
  --> IDs idênticos: True | Scores idênticos: True

--- CONSULTA: 'orchestrator' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=8497 score=0.3000 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionResult
    #2 id=8498 score=0.2718 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.__init__
    #3 id=8499 score=0.2718 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.mine
    #4 id=8515 score=0.2686 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_tags
    #5 id=8516 score=0.2686 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_categories
  [CÓPIA LIMPA - Com NULL]:
    #1 id=8497 score=0.3000 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionResult
    #2 id=8498 score=0.2639 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.__init__
    #3 id=8499 score=0.2639 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.mine
    #4 id=8515 score=0.2537 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_tags
    #5 id=8516 score=0.2537 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_categories
  --> IDs idênticos: True | Scores idênticos: False

--- CONSULTA: 'FastEmbed' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
  [CÓPIA LIMPA - Com NULL]:
  --> IDs idênticos: True | Scores idênticos: True

--- CONSULTA: 'Janitor' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=8646 score=0.3250 (vet=0.000, fts=0.000) | services/janitor.py::MaintenanceReport
    #2 id=9108 score=0.3218 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService
    #3 id=9606 score=0.2718 (vet=0.000, fts=0.000) | core/janitor.py::<module>
    #4 id=8647 score=0.2718 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService.__init__
    #5 id=8661 score=0.2718 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService._loop
  [CÓPIA LIMPA - Com NULL]:
    #1 id=8646 score=0.3250 (vet=0.000, fts=0.000) | services/janitor.py::MaintenanceReport
    #2 id=9108 score=0.3139 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService
    #3 id=9606 score=0.2639 (vet=0.000, fts=0.000) | core/janitor.py::<module>
    #4 id=8647 score=0.2639 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService.__init__
    #5 id=8661 score=0.2639 (vet=0.000, fts=0.000) | services/janitor.py::JanitorService._loop
  --> IDs idênticos: True | Scores idênticos: False

--- CONSULTA: 'RateGovernor' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=9655 score=0.3000 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor
    #2 id=9648 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.__init__
    #3 id=9653 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.run
    #4 id=9654 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.shutdown
    #5 id=9649 score=0.2719 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.report_usage
  [CÓPIA LIMPA - Com NULL]:
    #1 id=9655 score=0.3000 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor
    #2 id=9648 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.__init__
    #3 id=9653 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.run
    #4 id=9654 score=0.2750 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.shutdown
    #5 id=9649 score=0.2648 (vet=0.000, fts=0.000) | core/rate_governor.py::RateGovernor.report_usage
  --> IDs idênticos: True | Scores idênticos: False

--- CONSULTA: 'vector' ---
  [CÓPIA ORIGINAL - Com [DUMB]]:
    #1 id=8837 score=0.3048 (vet=0.000, fts=0.000) | storage/vector_store.py::ChromaVectorStore
    #2 id=9678 score=0.2827 (vet=0.000, fts=0.000) | core/vector_reconciler.py::VectorReconciler
    #3 id=8813 score=0.2827 (vet=0.000, fts=0.000) | storage/vector_store.py::EmbeddingError
    #4 id=9435 score=0.2750 (vet=0.000, fts=0.000) | docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md::1.1 Vector Reconciliation (`core/vector_reconciler.py`)
    #5 id=8814 score=0.2577 (vet=0.000, fts=0.000) | storage/vector_store.py::VectorStoreNotAvailableError
  [CÓPIA LIMPA - Com NULL]:
    #1 id=8837 score=0.3144 (vet=0.000, fts=0.000) | storage/vector_store.py::ChromaVectorStore
    #2 id=9678 score=0.3000 (vet=0.000, fts=0.000) | core/vector_reconciler.py::VectorReconciler
    #3 id=8813 score=0.3000 (vet=0.000, fts=0.000) | storage/vector_store.py::EmbeddingError
    #4 id=8814 score=0.2750 (vet=0.000, fts=0.000) | storage/vector_store.py::VectorStoreNotAvailableError
    #5 id=9435 score=0.2646 (vet=0.000, fts=0.000) | docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md::1.1 Vector Reconciliation (`core/vector_reconciler.py`)
  --> IDs idênticos: False | Scores idênticos: False
```

**Análise do Impacto Medido:**
1. **Distorção Comprovada de Ranking e Resultados:**
   - Na consulta `'hybrid'`, o nó `9396` (uma seção de documentação markdown) aparecia em **#2** na cópia original devido ao match textual artificial no seu sumário `[DUMB]`. Na cópia limpa com `NULL`, o ranking recuperou sua pureza semântica: `9396` saiu do top-5 e o método central `storage/logic.py::GraphLogic.hybrid_search_score` (#5, id=8718) assumiu sua posição legítima.
   - Na consulta `'vector'`, a inversão foi direta: a classe de erro `VectorStoreNotAvailableError` (#4 na limpa) estava rebaixada para #5 na cópia original, enquanto a seção markdown de migração estava inflada em #4.
2. **Impacto em Scores:** Em 6 das 8 consultas, os scores sofreram variações diretas (entre 0.008 e 0.020 pontos) devido ao recálculo da estatística de densidade de frequência BM25 do FTS5 (`nodes_fts`).

---

### B6. Análise de Opções e Recomendação

| Opção | Descrição | Risco | Esforço | Efeito Medido |
|---|---|---|---|---|
| **Opção A: Deixar como está** | Manter os 3.492 sumários `[DUMB]` gravados no `data/concierge.db`. Nenhuma alteração no banco pré-existente. | Baixo para integridade física; **Médio/Alto para precisão semântica**: contamina o FTS5, distorce o BM25 da busca híbrida e expõe strings de truncamento nas ferramentas MCP (`concierge_search`, `concierge_load`, `search_symbols`). | Zero | 1,51 MB de ruído no SQLite mantidos. Ranking de busca híbrida com desvios comprovados em 25% das consultas reais. |
| **Opção B: UPDATE para NULL com backup físico e simulação prévia** | Executar rotina controlada (ex.: script em rodada futura) que cria backup com timestamp de `data/concierge.db`, executa `UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%';` e reconstrói o índice FTS5 com `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');`. | **Muito Baixo**. O código atual já trata `summary = NULL` de forma universalmente segura (usando `.get("summary", "")`). Alinha o banco legado ao comportamento padrão do código de produção desde o commit `8d963ae`. | Muito Baixo (~30 linhas de script idempotente). | Elimina 1,51 MB de lixo imediatamente. Restaura a pureza do BM25 e despolui as respostas das ferramentas MCP. |
| **Opção C: Regenerar sumários com LLM ativo + caminho de backfill dedicado** | Implementar rotina de backfill (`concierge_backfill_summaries` ou flag no Janitor) que lê nós com `summary IS NULL` ou `[DUMB]`, chama o LLM em lotes controlados com `RateGovernor` e persiste resumos genuínos L0, L1 e L2. | **Médio**. Requer chave de LLM operacional em produção, consome aproximadamente 1,5 milhão de tokens de prompt/geração (3.492 nós) e introduz risco de rate-limit externo e latência de rede. | Médio/Alto (desenvolvimento de rotina com batching, controle de cota, retry e testes de carga). | Substitui 100% do ruído por sumários semânticos de alta fidelidade L0/L1/L2, ativando a Bússola de Contexto em sua capacidade máxima. |

#### Recomendação do Executor:
> **Recomendação Técnica do Executor:**  
> 1. Adotar a **Opção B** em uma rodada futura específica de manutenção (ex.: Rodada 4.1/H): realizar o backup com timestamp de `data/concierge.db`, executar o `UPDATE ... SET summary = NULL WHERE summary LIKE '[DUMB]%'` e reconstruir o `nodes_fts`. Essa medida é cirúrgica, de risco praticamente nulo, sem custo financeiro de API e alinha imediatamente a base de dados legada à política homologada de código (`8d963ae`).  
> 2. Planejar a **Opção C** como um épico/funcionalidade separada para quando o ambiente de produção tiver uma chave de LLM estável e com cotas dimensionadas, implementando um comando administrativo dedicado de backfill progressivo.

---

## 3. DECISÃO HUMANA (Ponto de Parada — Regra 7)

Conforme a Regra 7 do `AUDIT_PROTOCOL.md`, o executor **NÃO** toma a decisão de alteração dos dados existentes nem inicia implementações das rodadas subsequentes.

Aguardando a decisão do Dono do Projeto entre:
- **(A)** Deixar o banco legado `data/concierge.db` inalterado (manter `[DUMB]`);
- **(B)** Autorizar migração cirúrgica para `NULL` com backup prévio (Opção B);
- **(C)** Desenvolver rotina de backfill com LLM (Opção C);
- **(D)** Outra orientação específica.
