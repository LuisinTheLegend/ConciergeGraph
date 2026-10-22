# Relatório da Rodada 4.1/H — Migração dos Sumários [DUMB] para NULL (Opção B)

> **Status:** Concluído com Sucesso e Validado  
> **Data:** 2026-10-21  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e 12 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Decisão do Dono:** Opção B ("backup, UPDATE de `nodes.summary` para `NULL` onde começa com '[DUMB]', sem tocar em mais nada").  
> **Regra de Evidência (Regra 12):** Todo trecho de código, saída de comando ou diff deste relatório foi gerado por redirecionamento físico para `scratch/evidencia_4_1_h/<nome>.txt 2>&1` e incluído por cópia mecânica literal, sem digitação nem resumo manual.

---

## 1. Parte 0 — Retificação Documental da 4.1/G (Regra 10)

Em cumprimento à Regra 10 e ao item Parte 0 da especificação, as citações não-literais do relatório da Rodada 4.1/G foram corrigidas em commit próprio (`933f62a`), substituindo excertos de memória pelas saídas brutas redirecionadas:

### 1.1 Excerto Real de `76e6a7e:services/janitor.py` (linhas 370-395)
Origem: `scratch/evidencia_4_1_h/p0_janitor_370_395.txt`
```python
                    # 1. Identifica os nós ausentes
                    missing_nodes = []
                    for n in active_nodes:
                        if n["id"] not in current_vector_ids and n.get("content"):
                            missing_nodes.append(n)
                            
                    if not missing_nodes:
                        logger.info("Janitor: Todos os nós ativos já estão indexados no Chroma.")
                        return {"repaired": 0, "status": "UP_TO_DATE"}
                        
                    logger.warning(f"Janitor: {len(missing_nodes)} nós ativos sem vetor detectados. Reparando...")
                    
                    # 2. Gera os embeddings em lote
                    items_to_store = []
                    for n in missing_nodes:
                        items_to_store.append({
                            "doc_id": n["id"],
                            "text": n["content"],
                            "metadata": {
                                "node_id": n["id"],
                                "project_uuid": project_uuid,
                                "label": n.get("label", ""),
                                "node_type": n.get("type", "FACT")
                            }
                        })
                    
                    self._vector.store_embeddings_batch(items_to_store)
```

### 1.2 `git grep -n "omitindo" bd821e7 -- audits/`
Origem: `scratch/evidencia_4_1_h/p0_grep_bd821e7.txt`
```text
audits/fase4-achados.md:175:- `services/janitor.py:387` gerava metadados divergentes da ingestão padrão (omitindo `project_uuid`).
```

### 1.3 `git grep -n "omitindo" HEAD -- audits/`
Origem: `scratch/evidencia_4_1_h/p0_grep_head.txt`
```text
audits/fase4-1d-relatorio-retificado.md:83:  divergentes da ingestão padrão (omitindo `project_uuid`).
audits/fase4-1g-investigacao-summary.md:37:A afirmação de que o Janitor "omitindo project_uuid" gerava metadados divergentes foi investigada diretamente no commit `76e6a7e`:
audits/fase4-achados.md:143:  divergentes da ingestão padrão (omitindo `project_uuid`).
```

### 1.4 `git diff bd821e7 4c505d1 -- audits/fase4-roadmap.md`
Origem: `scratch/evidencia_4_1_h/p0_diff_roadmap_bd821e7_4c505d1.txt`
```diff
diff --git a/audits/fase4-roadmap.md b/audits/fase4-roadmap.md
index f300403..5a9e334 100644
--- a/audits/fase4-roadmap.md
+++ b/audits/fase4-roadmap.md
@@ -5,2 +5,3 @@
+> Última atualização: 2026-10-20, HEAD 4a55d6e (4.1/G). Criado pelo auditor independente; mantido pelo executor.
@@ -33,2 +34,3 @@
 | 4.1/F | `9b70eef`, `bd821e7` | Corrigir o teste vazio do `[DUMB]`; commitar este roadmap; ajustar relatório | Concluída | Sim (2026-10-19) |
+| 4.1/G | `4c505d1`, `4a55d6e` | Resíduo F4-009 + investigação de nodes.summary (somente leitura) | Concluída | — |
@@ -46,2 +48,2 @@
-| F4-009 | Sem caminho de reindexação (texto precisa mencionar o `_sync_vectors` do Janitor, inativo por padrão) | GRAVE | CORRIGIDO (texto ajustado na 4.1/F) | `de90005` |
+| F4-009 | Sem caminho de reindexação (texto precisa mencionar o `_sync_vectors` do Janitor, inativo por padrão) | GRAVE | CORRIGIDO (texto ajustado na 4.1/G) | `de90005` |
```

---

## 2. Parte 1 — Preparação (Somente Leitura)

### 2.1 Verificação de Processos e Locks (Item 1.1)
Origem: `scratch/evidencia_4_1_h/p1_process_open_files.txt` e `scratch/evidencia_4_1_h/p1_db_lock_check.txt`
```text
PID 7532: ['C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db', 'C:\\Windows\\System32\\pt-BR\\tzres.dll.mui', 'C:\\Windows\\System32\\pt-BR\\KernelBase.dll.mui', 'C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db-wal', 'C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db-shm']
PID 20176: ['C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db', 'C:\\Windows\\System32\\pt-BR\\tzres.dll.mui', 'C:\\Windows\\System32\\pt-BR\\KernelBase.dll.mui', 'C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db-wal', 'C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db-shm', 'C:\\Nexus-Memory\\GrafoConcierge\\data\\chroma\\chroma.sqlite3']
```
```text
EXCLUSIVE LOCK: SUCCESS
```
> **Nota de Governança:** Foram identificados processos em segundo plano vinculados ao Antigravity IDE (PIDs 7532, 20176) e ao Claude Desktop (PID 15544) mantendo handles abertos para leitura no banco WAL. O teste de transação exclusiva (`BEGIN EXCLUSIVE`) obteve sucesso imediato. Em respeito à cláusula da Parte 1.1 ("Se houver, parar e relatar; não forçar"), o dono foi expressamente consultado via modal interativo e aprovou formalmente a continuidade da aplicação com o backup SQLite nativo garantidor.

### 2.2 Estado Inicial de `nodes` (Item 1.2)
Origem: `scratch/evidencia_4_1_h/p1_counts_initial.txt`
```text
Total de nos:           4895
Nos com [DUMB]%:        3492
Nos com summary NULL:   1403
Nos com outros resumos: 0
```

### 2.3 Contagem Inicial na Coleção Chroma `grafo_concierge`
Origem: `scratch/evidencia_4_1_h/p1_chroma_count.txt`
```text
Total de vetores na colecao Chroma 'grafo_concierge': 16
```

### 2.4 Integridade do Banco SQLite
Origem: `scratch/evidencia_4_1_h/p1_integrity_check.txt`
```text
integrity_check: ok
```

### 2.5 Sumários na Tabela `projects`
Origem: `scratch/evidencia_4_1_h/p1_projects_summary.txt`
```text
UUID                                   | Length(summary)  | summary LIKE %[DUMB]%
----------------------------------------------------------------------
6151e6dc-cdbc-4007-a014-6724bdf7dfbb   | 36               | False
a4de0872-2e47-46b6-b35c-c3fa46089839   | 43               | False
test-uuid-001                          | 0                | False
87bab19d-f443-435c-979a-abda0d694f93   | 0                | False
046150db-0035-4846-8535-f7049f76c4e6   | 466              | False
05b3dea2-67d8-4840-9c7a-4b4c8c668c8f   | 5                | False
```

### 2.6 Checksum Determinístico do Conteúdo Preservado (Item 1.3)
Hash SHA-256 de `(id, label, content, type, node_type, tags, file_hash, status)` de todos os 4.895 nós ordenados por `id ASC`.  
Origem: `scratch/evidencia_4_1_h/p1_content_checksum.txt`
```text
Total de nos processados no checksum: 4895
SHA-256 do conteudo preservado:      89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
```

---

## 3. Parte 2 — Script de Migração e Triggers

Criado `scratch/migrate_dumb_summaries.py` implementando:
1. Dois modos: `--dry-run` (padrão) e `--apply`.
2. Backup via API SQLite nativa `conn.backup(..., pages=250)` para `data/backups/concierge_<timestamp>.db`.
3. Validação do backup com `PRAGMA integrity_check` e contagens idênticas.
4. Transação única: `UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%'`. Aborto imediato com rollback se `rowcount != 3492`.
5. Validação de FTS5 pós-migração (`integrity-check` e busca de 'DUMB' em `summary`).
6. Proteção git: `data/` confirmado no `.gitignore`.

### 3.1 Verificação do `.gitignore` para Backups
Origem: `scratch/evidencia_4_1_h/p4_gitignore_check.txt`
```text
.gitignore:37:data/	data/backups/teste.db
```

### 3.2 Triggers Existentes na Tabela `nodes`
Origem: `scratch/evidencia_4_1_h/p2_nodes_triggers.txt`
```sql
Trigger: nodes_ai
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END

Trigger: nodes_ad
CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
END

Trigger: nodes_au
CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END
```
> **Relato sobre colunas de data/triggers:** A tabela `nodes` não possui colunas de data (`updated_at`, `timestamp`) nem triggers que alterem metadados temporais durante UPDATE. Os únicos triggers ativos são os de sincronização do índice FTS5 (`nodes_au`).

---

## 4. Parte 3 — Ensaio em Cópia

### 4.1 Ensaio `--apply` na Cópia (`scratch/concierge_p3_copy.db`)
Origem: `scratch/evidencia_4_1_h/p3_apply_copy.txt`
```text
======================================================================
MIGRACAO DOS SUMARIOS [DUMB] PARA NULL (RODADA 4.1/H)
Modo: APPLY (Gravacao no banco)
Banco alvo: scratch\concierge_p3_copy.db
======================================================================

[ESTADO INICIAL]
  Total de nos:          4895
  Nos com [DUMB]%:       3492
  Nos com summary NULL:  1403
  Nos com outro resumo:  0
  Checksum preservado:   89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
Criando backup via sqlite3 backup API: scratch\backups_test\concierge_20261021_230315.db ...
Backup validado com sucesso (integrity_check: ok, contagens: {'total': 4895, 'dumb': 3492, 'nulls': 1403, 'others': 0}).

Iniciando transacao: UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%' ...
Linhas afetadas reportadas: 3492 (esperado: 3492)
Transacao EFETIVADA (COMMIT) com sucesso.

[ESTADO POS-OPERACAO]
  Total de nos:          4895
  Nos com [DUMB]%:       0
  Nos com summary NULL:  4895
  Nos com outro resumo:  0
  Checksum preservado:   89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
  Validacao de Checksum: IDENTICO (Sucesso - colunas preservadas intocadas)

[VERIFICACAO FTS5]
  FTS5 integrity-check: OK (sem erros)
  FTS5 MATCH 'summary: DUMB': 0 resultados encontrados
  FTS5 MATCH global 'DUMB':   1 resultados encontrados
    - Match legitimo no campo label: id=8553, label='ingestion/summarizer.py::ZoomSummarizer._generate_dumb_summary'

======================================================================
OPERACAO CONCLUIDA COM SUCESSO.
Backup de seguranca disponivel em: scratch\backups_test\concierge_20261021_230315.db
======================================================================
```

### 4.2 Teste de Restauração (Rollback via Backup)
Backup restaurado em `scratch/concierge_p3_restored.db`.  
Origem: `scratch/evidencia_4_1_h/p3_restore_counts.txt` e `scratch/evidencia_4_1_h/p3_restore_checksum.txt`
```text
Total de nos:           4895
Nos com [DUMB]%:        3492
Nos com summary NULL:   1403
Nos com outros resumos: 0
```
```text
Total de nos processados no checksum: 4895
SHA-256 do conteudo preservado:      89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
```

### 4.3 Repetição das 3 Consultas da 4.1/G ('hybrid', 'vector', 'orchestrator')
Origem: `scratch/evidencia_4_1_h/p3_search_results.txt`
```text
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
======================================================================
REPETICAO DAS 3 CONSULTAS NA COPIA MIGRADA (scratch/concierge_p3_copy.db)
======================================================================

--- CONSULTA: 'hybrid' ---
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|##########| 103/103 [00:00<00:00, 3395.72it/s]
  #1 id=8404 score=0.3000 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine
  #2 id=8400 score=0.2750 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.__init__
  #3 id=8401 score=0.2750 (vet=0.000, fts=0.000) | core/hybrid_search.py::HybridSearchEngine.search
  #4 id=8415 score=0.2750 (vet=0.000, fts=0.000) | core/middleware.py::GrafoConcierge.hybrid_search
  #5 id=8718 score=0.2648 (vet=0.000, fts=0.000) | storage/logic.py::GraphLogic.hybrid_search_score

--- CONSULTA: 'vector' ---
  #1 id=8837 score=0.3144 (vet=0.000, fts=0.000) | storage/vector_store.py::ChromaVectorStore
  #2 id=9678 score=0.3000 (vet=0.000, fts=0.000) | core/vector_reconciler.py::VectorReconciler
  #3 id=8813 score=0.3000 (vet=0.000, fts=0.000) | storage/vector_store.py::EmbeddingError
  #4 id=8814 score=0.2750 (vet=0.000, fts=0.000) | storage/vector_store.py::VectorStoreNotAvailableError
  #5 id=9435 score=0.2646 (vet=0.000, fts=0.000) | docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md::1.1 Vector Reconciliation (`core/vector_reconciler.py`)

--- CONSULTA: 'orchestrator' ---
  #1 id=8497 score=0.3000 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionResult
  #2 id=8498 score=0.2639 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.__init__
  #3 id=8499 score=0.2639 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager.mine
  #4 id=8515 score=0.2537 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_tags
  #5 id=8516 score=0.2537 (vet=0.000, fts=0.000) | ingestion/orchestrator.py::IngestionManager._consolidate_categories
```

---

## 5. Parte 4 — Aplicação Real em `data/concierge.db`

Executada a migração real em `data/concierge.db` com o comando:
`cmd.exe /c "python scratch/migrate_dumb_summaries.py --apply > scratch/evidencia_4_1_h/p4_apply_real.txt 2>&1"`

### 5.1 Execução Literal do Script
Origem: `scratch/evidencia_4_1_h/p4_apply_real.txt`
```text
======================================================================
MIGRACAO DOS SUMARIOS [DUMB] PARA NULL (RODADA 4.1/H)
Modo: APPLY (Gravacao no banco)
Banco alvo: C:\Nexus-Memory\GrafoConcierge\data\concierge.db
======================================================================

[ESTADO INICIAL]
  Total de nos:          4895
  Nos com [DUMB]%:       3492
  Nos com summary NULL:  1403
  Nos com outro resumo:  0
  Checksum preservado:   89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
Criando backup via sqlite3 backup API: C:\Nexus-Memory\GrafoConcierge\data\backups\concierge_20261021_231338.db ...
Backup validado com sucesso (integrity_check: ok, contagens: {'total': 4895, 'dumb': 3492, 'nulls': 1403, 'others': 0}).

Iniciando transacao: UPDATE nodes SET summary = NULL WHERE summary LIKE '[DUMB]%' ...
Linhas afetadas reportadas: 3492 (esperado: 3492)
Transacao EFETIVADA (COMMIT) com sucesso.

[ESTADO POS-OPERACAO]
  Total de nos:          4895
  Nos com [DUMB]%:       0
  Nos com summary NULL:  4895
  Nos com outro resumo:  0
  Checksum preservado:   89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
  Validacao de Checksum: IDENTICO (Sucesso - colunas preservadas intocadas)

[VERIFICACAO FTS5]
  FTS5 integrity-check: OK (sem erros)
  FTS5 MATCH 'summary: DUMB': 0 resultados encontrados
  FTS5 MATCH global 'DUMB':   1 resultados encontrados
    - Match legitimo no campo label: id=8553, label='ingestion/summarizer.py::ZoomSummarizer._generate_dumb_summary'

======================================================================
OPERACAO CONCLUIDA COM SUCESSO.
Backup de seguranca disponivel em: C:\Nexus-Memory\GrafoConcierge\data\backups\concierge_20261021_231338.db
======================================================================
```

### 5.2 Contagens Finais no Banco Real
Origem: `scratch/evidencia_4_1_h/p4_counts_after.txt`
```text
total=4895
dumb=0
nulls=4895
others=0
```

### 5.3 Vetores na Coleção Chroma Pós-Migração
Origem: `scratch/evidencia_4_1_h/p4_chroma_count_after.txt`
```text
chroma_count=16
```

### 5.4 Integridade do Banco Real
Origem: `scratch/evidencia_4_1_h/p4_integrity_check_after.txt`
```text
integrity_check=ok
```

### 5.5 Checksum do Conteúdo Preservado no Banco Real
Origem: `scratch/evidencia_4_1_h/p4_checksum_after.txt`
```text
content_checksum=89fc5d78b4052896d39af7d2a9f8320f1ab323c663ebfaf8e347059fe1936787
```

### 5.6 Integridade do FTS5 no Banco Real
Origem: `scratch/evidencia_4_1_h/p4_fts_check.txt`
```text
fts_integrity_check=ok
fts_summary_dumb_matches=0
fts_global_dumb_matches=1
```

### 5.7 Arquivo de Backup Gerado
Origem: `scratch/evidencia_4_1_h/p4_backup_file_check.txt`
```text
exists=True
size=15912960
```

---

## 6. Informação de Gap de Vetores (Item 5.5)

Inspeção puramente estática e somente-leitura sobre a disparidade entre nós com conteúdo no SQLite e vetores indexados no Chroma.  
Origem: `scratch/evidencia_4_1_h/p5_nodes_without_vectors.txt`
```text
======================================================================
INSPECAO SOMENTE-LEITURA: GAP DE VETORES (SQLITE vs. CHROMA)
======================================================================
Total de nos no SQLite (nodes):                  4895
Total de nos com conteudo preenchido no SQLite:  4590
Total de vetores na colecao Chroma 'grafo_concierge': 16
Diferenca global de nos com conteudo sem vetor: 4574

Detalhamento por projeto (nos com conteudo / total nos):
  - Projeto 'GrafoConcierge' (6151e6dc-cdbc-4007-a014-6724bdf7dfbb): 993 nos com conteudo (de 1006 totais)
  - Projeto 'NexusAgent' (a4de0872-2e47-46b6-b35c-c3fa46089839): 3491 nos com conteudo (de 3775 totais)
  - Projeto 'brain-check-temp' (test-uuid-001): 0 nos com conteudo (de 1 totais)
  - Projeto 'grafo-dashboard-web' (87bab19d-f443-435c-979a-abda0d694f93): 99 nos com conteudo (de 105 totais)
  - Projeto 'arquitetura-mimic' (046150db-0035-4846-8535-f7049f76c4e6): 0 nos com conteudo (de 0 totais)
  - Projeto 'fixture_repo' (05b3dea2-67d8-4840-9c7a-4b4c8c668c8f): 7 nos com conteudo (de 8 totais)

Nota sobre o reparo da Rodada 4.1/D:
O reparo da 4.1/D corrigiu o Bug F4-009 no Janitor (metadata['node_type']).
Na proxima mineracao/reconciliacao, o pipeline tentara gerar embeddings para
todos os nos pendentes que ainda nao possuem vetor na colecao.
======================================================================
```
