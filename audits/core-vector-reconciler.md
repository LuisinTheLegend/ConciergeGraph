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
| 2 | `core/vector_reconciler.py` | 40–49, 54 | **CRÍTICA** | Incompatibilidade de TIPO (`int` vs `str`) e Domínio Semântico -> Purga Total de Vetores (Catastrophic Data Loss). O reconciliador busca `vector_ids` no banco vetorial e compara via `vector_ids - sqlite_paths` com `SELECT path FROM files;`. No GrafoConcierge real, `get_all_stored_node_ids()` devolve `set[int]` (IDs de nós da AST), enquanto a tabela `files` armazena caminhos de arquivos em texto (`set[str]`). Em Python, a interseção entre `int` e `str` é sempre vazia (`set()`), de modo que `vector_ids - sqlite_paths` avalia invariavelmente para `vector_ids` integralmente. **A purga total de 100% dos vetores legítimos é matematicamente garantida**, esvaziando o banco vetorial. | Executado com `set[int]` canônico e caminhos SQLite: interseção nula e 100% dos vetores enviados para expurgo físico. | **CONFIRMADO** |
| 3 | `core/vector_reconciler.py` | 31–50 | **ALTA** | Ausência de sincronização atômica e race condition destrutiva com ingestão concorrente (TOCTOU). `reconcile_orphans()` executa em segundo plano sem qualquer lock (sem `threading.Lock`) e sem coordenação transacional com o pipeline de ingestão (`IngestionOrchestrator`). Como a ingestão grava vetores no Step 6 e comita nós/arquivos no SQLite no Step 7/8, uma reconciliação que leia o banco vetorial entre esses dois passos marca os vetores recém-ingeridos como "órfãos" e os deleta fisicamente antes que o SQLite confirme a escrita. | Simulação de inserção concorrente durante leitura de IDs: vetor em trânsito de ingestão foi marcado como órfão e apagado indevidamente. | **CONFIRMADO** |
| 4 | `core/vector_reconciler.py` | 48–50 | **MÉDIA** | Falta de paginação em lote e ausência de tratamento de exceções em `delete_batch`. O método passa a lista inteira de `orphan_ids` de uma só vez para `self.vector_db.delete_batch(orphan_ids)` em desacordo com `BATCH_SIZE = 100` em `ChromaVectorStore`. Em bases grandes, listas desmedidas (ex: 500 itens) estouram limites de payload de rede ou buffer de memória, e exceções propagam sem tratamento ou recuperação. | Teste com 500 itens demonstrou despacho em lote único de 500 (`[500]`), estourando limites de payload e quebrando o reconciliador. | **CONFIRMADO** |

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

### Achado #2 — Incompatibilidade de TIPO (`int` vs `str`) e Domínio Semântico -> Purga Total de Vetores (Data Loss)

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
  A falha possui duas camadas intransponíveis:
  
  1. **Incompatibilidade de TIPO primitivo (`int` vs `str`):**
     - O método canônico real de recuperação de IDs no backend vetorial (`get_all_stored_node_ids()`, definido em `storage/base_backend.py:91` e implementado em `storage/vector_store.py:263`) retorna `set[int]` (números inteiros correspondentes às chaves primárias dos nós no SQLite).
     - A consulta `_get_all_sqlite_paths()` retorna `set[str]` contendo nomes de arquivos (`SELECT path FROM files;`).
     - Em Python, inteiros nunca são iguais a strings (`101 != "101"`). A interseção entre `set[int]` e `set[str]` é estritamente vazia (`set()`), mesmo se um arquivo se chamasse `"101"`. Logo, a operação `vector_ids - sqlite_paths` resulta em **100% de `vector_ids`**.
  
  2. **Incompatibilidade Semântica de Domínio:**
     - Os vetores indexam nós da AST gerados pelo Tree-sitter ([`ingestion/orchestrator.py:756`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L756)), com identificadores do tipo `"node_{node_id}"` e metadados de nós.
     - A tabela `files` armazena caminhos de arquivos (`"src/core/main.py"`).
     - Como nenhum nó da AST tem ID igual a um caminho de arquivo, a classificação de órfão é universal e atinge a totalidade dos registros.

- **Impacto no Sistema:**  
  **A purga de 100% da base de vetores é matematicamente garantida**, não apenas provável. Na primeira execução da rotina em produção, toda a base de embeddings é sumariamente apagada.

- **DEPENDÊNCIA CRÍTICA ENTRE ACHADO #1 E ACHADO #2:**  
  > [!CAUTION]
  > **Risco Extremo de Regressão Destrutiva em Correção Isolada:**  
  > Atualmente, o sistema está **"seguro por estar quebrado"**: a rotina aborta imediatamente na linha 39 com `AttributeError` devido ao Achado #1 (`get_all_ids()` inexistente), impedindo que a execução atinja as linhas 43–49.  
  > Se um desenvolvedor corrigir apenas o Achado #1 isoladamente (por exemplo, criando um método `get_all_ids()` que aponte para `get_all_stored_node_ids()`), o sistema passará do estado quebrado para o estado **"roda e apaga todo o banco vetorial"** devido ao Achado #2.  
  > **Conclusão mandatória:** Os Achados #1 e #2 **DEVEM ser corrigidos estritamente no mesmo commit / mini-plano**, nunca de forma incremental ou separada!

- **Correção Conceitual Sugerida (Fase 3):**  
  Substituir a consulta a `files.path` pela verificação dos nós da tabela `nodes`:
  ```sql
  SELECT id FROM nodes;
  ```
  E delegar a reconciliação ao método canônico `verify_sync(sqlite_node_ids: set[int])` de `ChromaVectorStore`, que já opera com tipos `int` e validação bidirecional correta.

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

Script executado: `python scratch/reproduce_vector_reconciler_findings.py`

```text
[CRITICAL] qdrant-client not found. QdrantVectorStore operating in NO-OP mode. Semantic searches will return empty!
======================================================================
PROVAS DE REPRODUÇÃO EXECUTÁVEIS — core/vector_reconciler.py
======================================================================

======================================================================
TESTE ACHADO 1: Método fantasma get_all_ids() inexistente nas classes reais
======================================================================
BaseVectorBackend tem get_all_ids? False
ChromaVectorStore tem get_all_ids? False
QdrantVectorStore tem get_all_ids? False
BaseVectorBackend tem get_all_stored_node_ids? True
ChromaVectorStore tem get_all_stored_node_ids? True
Capturado AttributeError em runtime: 'ChromaVectorStore' object has no attribute 'get_all_ids'
[CONFIRMADO ACHADO 1]: get_all_ids() é método fantasma. Em produção, VectorReconciler quebra imediatamente com AttributeError.

======================================================================
TESTE ACHADO 2: Incompatibilidade de TIPO (int vs str) e Domínio -> Purga Total Garantida
======================================================================
Tipo retornado por get_all_stored_node_ids(): <class 'int'> -> {101, 102, 103}
Tipo retornado por _get_all_sqlite_paths():   <class 'str'> -> {'101', 'src/main.py', 'src/utils.py'}
Diferença de conjuntos (vector_ids - sqlite_paths): {101, 102, 103}
Interseção entre set[int] e set[str]: set()
Taxa de purga resultante: 100.0%
Vetores existentes antes da reconciliação: [101, 102]
Arquivos válidos registrados no SQLite: ['src/main.py', 'src/utils.py']
IDs expurgados pelo VectorReconciler: [101, 102]
Vetores restantes no banco vetorial: []
[CONFIRMADO ACHADO 2]: Pelo descasamento de TIPO (int vs str) e domínio semântico, 100% dos vetores legítimos são purgados (Data Loss Catastrófico garantido)!

======================================================================
TESTE ACHADO 3: Ausência de Locks e Race Condition TOCTOU com Ingestão Concorrente
======================================================================
Vetores apagados durante a janela de ingestão concorrente: ['new_ingested_node_in_transit']
[CONFIRMADO ACHADO 3]: Vetor legítimo em trânsito de ingestão foi destruído por falta de sincronização atômica entre vector store e SQLite!

======================================================================
TESTE ACHADO 4: Ausência de Paginação em Lote e Exceções Não Tratadas em delete_batch
======================================================================
Tamanho do lote canônico configurado em ChromaVectorStore: BATCH_SIZE = 100
Total de órfãos a deletar: 500
Chamadas realizadas a delete_batch: [500] (lote único de 500 itens)
Exceção não tratada propagada pelo VectorReconciler: Payload too large: batch size exceeds maximum allowed limit of 250 items
[CONFIRMADO ACHADO 4]: delete_batch despacha a lista completa de uma só vez sem paginação (BATCH_SIZE), propagando falhas não tratadas!

======================================================================
RESULTADOS FINAIS: F1=True | F2=True | F3=True | F4=True
======================================================================
```

---

## 6. Arquivos de Teste Relacionados

- [`tests/test_vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py):
  - Testa `HybridSearchEngine.hybrid_search` e `VectorReconciler.reconcile_orphans`.
  - Mascarou 100% dos bugs porque utilizou a classe de teste `MockVectorDatabase`, a qual inventou o método `get_all_ids()` e utilizou caminhos de arquivo como IDs no mock (`self.vector_db.insert("src/main.py", ...)`), ignorando o esquema real `node_{node_id}` de produção.
  - Resultado: 2 passed em 0.046s.
