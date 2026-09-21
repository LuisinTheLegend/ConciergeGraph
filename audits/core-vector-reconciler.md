# Auditoria — `core/vector_reconciler.py`

> **Item:** `core/vector_reconciler.py` (SDD-SURVIVAL-05: Eventual Consistency Janitor & Background Vector Reconciler)  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-09-20  
> **Status:** Concluído, aguardando aprovação  

---

## 1. Ferramentas Estáticas Executadas

| Ferramenta | Comando | Resultado |
|------------|---------|-----------|
| **mypy** | `python -m mypy core/vector_reconciler.py --follow-imports=skip` | `Success: no issues found in 1 source file` |
| **unittest** | `python -m unittest tests/test_vector_reconciler.py` | 2 passed em 0.046s |

---

## 2. Inventário Completo de Chamadas a Objetos Externos

Para cumprir a diretriz de auditoria além do escopo de mocks, foram catalogadas todas as interações com dependências externas em `core/vector_reconciler.py`:

| Objeto / Dependência | Método Chamado | Linha | Presente na Interface (`BaseVectorBackend`)? | Presente na Classe Real (`ChromaVectorStore`)? | Presente no Backend Qdrant (`QdrantVectorStore`)? | Status |
|----------------------|----------------|-------|----------------------------------------------|------------------------------------------------|---------------------------------------------------|--------|
| `self.vector_db` | `get_all_ids()` | 39 | ❌ **NÃO** (canônico: `get_all_stored_node_ids`) | ❌ **NÃO** (canônico: `get_all_stored_node_ids`) | ❌ **NÃO** | **FANTASMA (BUG)** |
| `self.vector_db` | `delete_batch(orphan_ids)` | 49 | ✅ **SIM** (`delete_batch(doc_ids: list[str]) -> int`) | ✅ **SIM** (`delete_batch(doc_ids: list[str]) -> int`) | ✅ **SIM** (`delete_batch(doc_ids: list[str]) -> int`) | CONFORME |
| `self.db_manager` | `read_query("SELECT path FROM files;")` | 54 | N/A (SQLite) | N/A (SQLite) | N/A (SQLite) | Incompatibilidade de Domínio (ver Achado #2) |

---

## 3. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `core/vector_reconciler.py` | 39 | **CRÍTICA** | Invocação de método fantasma `self.vector_db.get_all_ids()`. Conforme já identificado no Achado #1 de [`audits/mock-vs-real-audit.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/mock-vs-real-audit.md#L72), o método `get_all_ids()` não existe na interface abstrata `BaseVectorBackend`, nem no backend padrão de produção `ChromaVectorStore` (o método canônico é `get_all_stored_node_ids()`), nem em `QdrantVectorStore`. Em ambiente real, qualquer execução de reconciliação de vetores quebra com `AttributeError: 'ChromaVectorStore' object has no attribute 'get_all_ids'`. A suite de testes passou apenas porque `MockVectorDatabase` inventou um método inexistente. | Script executado com `ChromaVectorStore`: `AttributeError` capturado com sucesso. Nenhuma classe real implementa o método. | **CONFIRMADO** (já citado em mock-vs-real-audit) |
| 2 | `core/vector_reconciler.py` | 40–49, 54 | **CRÍTICA** | Incompatibilidade semântica de chaves e risco de purga total da base de vetores (Catastrophic Data Loss). O reconciliador busca `vector_ids` no banco vetorial e compara via `vector_ids - sqlite_paths` com `SELECT path FROM files;`. No GrafoConcierge real, os vetores indexam nós da AST com formato `node_{node_id}` (`ingestion/orchestrator.py:756`), enquanto a tabela `files` armazena caminhos de arquivos (`path` textual). Como os identificadores pertencem a espaços disjuntos, a interseção é vazia e **100% dos vetores legítimos são classificados como órfãos**, sendo sumariamente deletados em lote do banco vetorial. | Executado com vetores canônicos (`node_101`, `node_102`) e arquivos legítimos no SQLite: o reconciliador purgou 100% dos vetores legítimos, esvaziando o banco. | **CONFIRMADO** |
| 3 | `core/vector_reconciler.py` | 31–50 | **ALTA** | Ausência de sincronização atômica e race condition destrutiva com ingestão concorrente (TOCTOU). `reconcile_orphans()` executa em segundo plano sem qualquer lock (sem `threading.Lock`) e sem coordenação transacional com o pipeline de ingestão (`IngestionOrchestrator`). Como a ingestão grava vetores no Step 6 e comita nós/arquivos no SQLite no Step 7/8, uma reconciliação que leia o banco vetorial entre esses dois passos marca os vetores recém-ingeridos como "órfãos" e os deleta fisicamente antes que o SQLite confirme a escrita. | Simulação de inserção concorrente durante leitura de IDs: vetor em trânsito de ingestão foi marcado como órfão e apagado indevidamente. | **CONFIRMADO** |
| 4 | `core/vector_reconciler.py` | 48–50 | **MÉDIA** | Falta de paginação em lote e ausência de tratamento de exceções em `delete_batch`. O método passa a lista inteira de `orphan_ids` de uma só vez para `self.vector_db.delete_batch(orphan_ids)`. Em bases grandes ou após exclusão de repositórios inteiros com milhares de nós, listas desmedidas estouram limites de payload de rede (Qdrant) ou memória (Chroma). Falhas parciais não são tratadas e a exceção propaga sem retorno de diagnóstico. | Análise estática da chamada não paginada confrontada com `BATCH_SIZE = 100` presente em `ChromaVectorStore`. | **CONFIRMADO** |

---

## 4. Detalhamento de Cada Achado

### Achado #1 — Invocação de Método Fantasma `self.vector_db.get_all_ids()`

- **Citação da Fonte Prévia:**  
  Identificado previamente no Achado #1 de [`audits/mock-vs-real-audit.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/mock-vs-real-audit.md#L72). A severidade e o mecanismo permanecem estritamente consistentes com o relatório anterior.
- **Mecanismo da Falha:**  
  Em `core/vector_reconciler.py:39`:
  ```python
  vector_ids = set(self.vector_db.get_all_ids())
  ```
  O método `get_all_ids()` não existe em nenhuma classe real de armazenamento vetorial:
  - [`storage/base_backend.py:91`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py#L91) (`BaseVectorBackend`): não define `get_all_ids()`. Define `verify_sync(sqlite_node_ids)` e `get_all_stored_node_ids() -> set[int]`.
  - [`storage/vector_store.py:263`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L263) (`ChromaVectorStore`): não implementa `get_all_ids()`.
  - [`core/vector_backend.py:33`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_backend.py#L33) (`QdrantVectorStore`): não implementa `get_all_ids()`.
  Até mesmo a API de telemetria em [`interface/telemetry_api.py:274–281`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L274-L281) precisou criar um mock ad-hoc interno `_VectorDbStub` com `get_all_ids()` para não explodir ao instanciar o reconciliador.
- **Impacto no Sistema:**  
  Falha catastrófica imediata com `AttributeError` em qualquer ambiente de produção onde o `VectorReconciler` seja acionado.
- **Correção Conceitual Sugerida (Fase 3):**  
  Alinhar o reconciliador com o contrato canônico `verify_sync(sqlite_node_ids: set[int])` já implementado em `BaseVectorBackend` e `ChromaVectorStore`, ou invocar `self.vector_db.get_all_stored_node_ids()`.

---

### Achado #2 — Incompatibilidade Semântica de Chaves e Purga Total de Vetores (Data Loss)

- **Mecanismo da Falha:**  
  Em `core/vector_reconciler.py:40–55`:
  ```python
  vector_ids = set(self.vector_db.get_all_ids())
  sqlite_paths = self._get_all_sqlite_paths()

  orphan_ids = sorted(vector_ids - sqlite_paths)

  if not orphan_ids:
      return []

  self.vector_db.delete_batch(orphan_ids)
  ```
  E a consulta em `_get_all_sqlite_paths()`:
  ```python
  def _get_all_sqlite_paths(self) -> set:
      rows = self.db_manager.read_query("SELECT path FROM files;")
      return {row[0] for row in rows}
  ```
  Há uma discrepância conceitual absoluta entre o que é indexado no banco vetorial e o que é lido do SQLite:
  1. No banco vetorial de produção ([`ingestion/orchestrator.py:756`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L756)), os IDs de documentos representam nós de código: `"doc_id": f"node_{node_id}"` (ex: `"node_1"`, `"node_2"`, `"node_105"`).
  2. Na tabela `files` do SQLite, a coluna `path` armazena caminhos no sistema de arquivos: `"src/core/main.py"`, `"storage/store.py"`.
  3. Ao fazer `vector_ids - sqlite_paths`, como nenhum ID de nó (`"node_X"`) é igual a um caminho de arquivo (`"src/..."`), a operação de diferença de conjuntos avalia para `vector_ids` integralmente.
  4. O reconciliador interpreta **todos os vetores legítimos da base como órfãos** e envia a lista completa para `self.vector_db.delete_batch(orphan_ids)`.
- **Impacto no Sistema:**  
  Caso o método `get_all_ids()` fosse fornecido por um adapter superficial retornando os `doc_id`s do Chroma/Qdrant, a primeira execução da rotina de auto-cura **apagaria 100% dos embeddings de todo o projeto**, destruindo a base de busca semântica.
- **Correção Conceitual Sugerida (Fase 3):**  
  Substituir a consulta a `files.path` pela verificação dos nós da tabela `nodes`:
  ```sql
  SELECT id FROM nodes;
  ```
  E delegar a reconciliação ao método canônico `verify_sync(sqlite_node_ids)` da classe de storage, que já encapsula a lógica correta de extrair e validar `int(node_id)`.

---

### Achado #3 — Race Condition com Ingestão Concorrente (TOCTOU)

- **Mecanismo da Falha:**  
  O pipeline de ingestão ([`ingestion/orchestrator.py:769–780`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L769)) opera em etapas sequenciais:
  - Step 6: Grava os vetores no banco vetorial (`_step_store_vector`).
  - Step 7/8: Persiste as transações e relacionamentos no banco SQLite WAL.
  O `VectorReconciler` não possui lock compartilhado nem verifica se há ingestão ou reindexação em andamento (não consulta `is_indexing` nem adquire lock em `ConciergeDatabaseManager`).
  Se `reconcile_orphans()` for acionado entre o Step 6 e a persistência final no SQLite:
  1. O reconciliador lê os novos IDs no banco vetorial.
  2. O SQLite ainda não concluiu o commit das novas entidades.
  3. Os novos vetores são classificados como órfãos e deletados fisicamente antes de poderem ser utilizados.
- **Impacto no Sistema:**  
  Perda silenciosa de vetores recém-indexados sob carga ou ingestões demoradas, deixando nós do grafo sem embeddings correspondentes no banco vetorial.
- **Correção Conceitual Sugerida (Fase 3):**  
  Implementar trava de concorrência com o `IngestionOrchestrator` (ex: verificar `is_indexing` ou coordenar via lock de banco) e aplicar uma janela de tolerância temporal (quiet window / grace period), não deletando vetores criados há menos de $N$ minutos.

---

### Achado #4 — Falta de Paginação em Lote e Ausência de Tratamento de Exceções

- **Mecanismo da Falha:**  
  Em `core/vector_reconciler.py:49`:
  ```python
  self.vector_db.delete_batch(orphan_ids)
  ```
  Ao contrário da implementação em [`storage/vector_store.py:562`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L562) (que pagina em fatias de `BATCH_SIZE = 100`), o `VectorReconciler` envia toda a lista de órfãos de uma só vez.
  Se `orphan_ids` contiver dezenas de milhares de registros, requisições HTTP para backends remotos (como Qdrant ou Pinecone) falham por estouro de tamanho de requisição (HTTP 413 Payload Too Large) ou time-out de conexão. Além disso, não há bloco `try ... except` protegendo a exclusão.
- **Impacto no Sistema:**  
  Falha não recuperável de reconciliação em grandes limpezas ou migrações de projetos.
- **Correção Conceitual Sugerida (Fase 3):**  
  Fatiar a lista em lotes de 100 itens com bloco `try ... except` e registro de log por lote processado.

---

## 5. Saída Bruta da Reprodução Executada

Script executado: `scratch/reproduce_vector_reconciler_findings.py`

```text
======================================================================
PROVAS DE REPRODUCAO — core/vector_reconciler.py
======================================================================

--- TESTE ACHADO 1: Método fantasma get_all_ids() inexistente nas classes reais ---
BaseVectorBackend tem get_all_ids? False
ChromaVectorStore tem get_all_ids? False
QdrantVectorStore tem get_all_ids? False
Capturado AttributeError com sucesso: 'ChromaVectorStore' object has no attribute 'get_all_ids'
[CONFIRMADO ACHADO 1]: Nenhuma classe real implementa get_all_ids(). O VectorReconciler quebra com AttributeError em produção!

--- TESTE ACHADO 2: Incompatibilidade de Domínio e Risco de Purga Total (Data Loss) ---
Vetores existentes antes da reconciliação: ['node_101', 'node_102']
Arquivos existentes no SQLite: ['src/main.py', 'src/utils.py']
IDs purgados pelo VectorReconciler: ['node_101', 'node_102']
Vetores restantes no banco vetorial: []
[CONFIRMADO ACHADO 2]: Comparação semântica inválida (IDs de nós vs Paths de arquivos) resulta na PURGA TOTAL (100%) dos vetores legítimos!

--- TESTE ACHADO 3: Race condition com ingestão concorrente (TOCTOU) ---
Vetores apagados durante janela de ingestão: ['doc_new_incoming']
[CONFIRMADO ACHADO 3]: Vetor recém-ingerido foi expurgado como falso órfão por falta de sincronização com o pipeline de ingestão!

======================================================================
RESULTADOS: F1=True, F2=True, F3=True
======================================================================
```

---

## 6. Arquivos de Teste Relacionados

- [`tests/test_vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py):
  - Testa `HybridSearchEngine.hybrid_search` e `VectorReconciler.reconcile_orphans`.
  - Mascarou 100% dos bugs porque utilizou a classe de teste `MockVectorDatabase`, a qual inventou o método `get_all_ids()` e utilizou caminhos de arquivo como IDs no mock (`self.vector_db.insert("src/main.py", ...)`), ignorando o esquema real `node_{node_id}` de produção.
  - Resultado: 2 passed em 0.046s.
