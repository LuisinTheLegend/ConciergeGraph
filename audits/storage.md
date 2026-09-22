# Relatório de Auditoria: `storage/` (Todos os Arquivos)

> **Data:** 21 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE  
> **Escopo:** Diretório [`storage/`](file:///c:/Nexus-Memory/GrafoConcierge/storage):
> - [`storage/__init__.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/__init__.py)
> - [`storage/base_backend.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py)
> - [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py)
> - [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py)
> - [`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py)
> - [`storage/logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py)
> - [`storage/semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py)
> - [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py)
> - [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py)

---

## 1. Resumo Executivo e Tabela de Achados

O diretório `storage/` atua como a camada de persistência híbrida (relacional via SQLite WAL e vetorial via ChromaDB) do Grafo Concierge. A auditoria profunda revelou **9 achados confirmados**, incluindo deadlocks de concorrência na fila serializada de escrita, vazamento contínuo de descritores e memória de conexões SQLite em threads finalizadas, bypass completo de isolamento estrito (*Strict Scoping*) na busca vetorial, corrupção silenciosa de scores de recência por incompatibilidade de tipo temporal, duplicação de nós em CTEs recursivas e incompatibilidade grave de contratos entre a fachada `SqliteStore` e o submódulo de checkpoints relacionais.

| ID | Severidade | Arquivo(s) | Resumo do Achado |
|---|---|---|---|
| **#1** | 🔴 **CRÍTICO** | [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L111-L140) | **Deadlock Inevitável em Escritas Reentrantes/Aninhadas no `SerializedWriteQueue`**: Qualquer operação executada dentro do worker da fila de escrita que tente invocar direta ou indiretamente um método de escrita submete novo job e bloqueia em `result_event.wait()`, travando permanentemente o worker thread em auto-espera. |
| **#2** | 🟠 **GRAVE** | [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L257-L273) | **Vazamento Perpétuo de Conexões SQLite de Threads Finalizadas**: `get_read_connection()` retém referências fortes de todas as conexões criadas na lista `_read_connections`. Quando threads efêmeras morrem, os objetos `sqlite3.Connection` continuam presos na lista global, vazando descritores de arquivos e memória WAL até o encerramento do processo. |
| **#3** | 🟡 **MÉDIO** | [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L75-L110) | **Falha ao Reiniciar `SerializedWriteQueue` após `stop()` (`RuntimeError`)**: O objeto `threading.Thread` é instanciado apenas uma vez no `__init__`. Se `stop()` for invocado (ou via `ConnectionManager.close()`) e posteriormente `start()` for chamado para reconexão, o Python lança `RuntimeError: threads can only be started once`, inutilizando a instância. |
| **#4** | 🟠 **GRAVE** | [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py#L27-L35) <br> [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L84-L110) | **Incompatibilidade de Contrato: `init_fsm_checkpoints_schema` Falha Silenciosamente**: A função espera um gerenciador com `execute_write` ou `write_query` (padrão `core/database.py`), mas a fachada oficial `SqliteStore` só expõe `write_callback`. O init retorna `False` sem criar a tabela `fsm_checkpoints`. Além disso, `SchemaManager.apply_full_schema` omite completamente as tabelas de checkpoints. |
| **#5** | 🟠 **GRAVE** | [`storage/logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L330-L350) | **Falha de Tipo em `_calculate_decay` com Timestamps ISO Offset-Aware (Degradação para 0.01)**: A subtração entre `datetime.utcnow()` (offset-naive) e `datetime.fromisoformat()` (offset-aware quando contendo `Z` ou `+00:00`) lança `TypeError`, que é engolido pelo bloco `except` e força o retorno de `RECENCY_MIN_SCORE` (`0.01`) para commits imediatos. |
| **#6** | 🔴 **CRÍTICO** | [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L449-L458), <br> [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L711-L740) | **Bypass de Isolamento Estrito (*Strict Scoping*) em `ChromaVectorStore.search`**: Quando `project_uuids=[]`, `_build_where_filter` não adiciona nenhum filtro de projeto, executando a busca sobre **todos os vetores de todos os projetos** da coleção e vazando dados confidenciais (*Cross-Project Leakage*). |
| **#7** | 🟡 **MÉDIO** | [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L477), <br> [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L695-L708) | **Crash com `ValueError` em `ChromaVectorStore.search` por `node_id` Vazio ou `None`**: O validador não checa o tipo de `node_id`. Se `node_id=None` for passado, `_sanitize_metadata` converte para string vazia `""`. Em `search()`, `int(meta.get("node_id", 0))` tenta executar `int("")`, explodindo a busca com `ValueError`. |
| **#8** | 🟡 **MÉDIO** | [`storage/logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L578-L593) | **Duplicação de Nós na CTE Recursiva `get_dependency_tree`**: A projeção da CTE inclui `dt.depth + 1` e utiliza `UNION ALL`. No `SELECT DISTINCT * FROM dep_tree`, como a coluna `depth` faz parte da tupla distinta, nós alcançáveis por múltiplos caminhos de profundidades distintas aparecem repetidos no resultado final. |
| **#9** | 🔵 **BAIXO** | [`storage/semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py#L1-L126) <br> [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L1-L803) | **Isolamento de `semantic_logic.py` e Violação de Encapsulamento em Módulos Externos**: A fachada `SqliteStore` não expõe métodos para manipular a tabela `semantic_facts`, forçando chamadores externos (ex.: `core/middleware.py:632`) a acessarem diretamente o atributo privado `store._conn_mgr.read()`. |

---

## 2. Matriz de Interação Interna (Entre os Arquivos de `storage/` entre si)

Esta matriz mapeia as dependências, contratos e incompatibilidades arquiteturais entre os 9 componentes internos do diretório `storage/`:

```
                    ┌──────────────┐
                    │ store.py     │◄───────────────────┐
                    └──────┬───────┘                    │
                           │ Facade unificada           │
             ┌─────────────┼─────────────┐              │
             ▼             ▼             ▼              │ Quebra de
       ┌───────────┐ ┌───────────┐ ┌───────────┐        │ encapsulamento
       │connection │ │  schema   │ │   logic   │        │
       └─────┬─────┘ └─────┬─────┘ └─────┬─────┘        │
             │             │             │              │
             │             │ DDL sem     │ Depende de   │
             │             │ FSM         │ connection   │
             ▼             ▼             ▼              │
       ┌───────────┐ ┌───────────┐ ┌──────────────┐     │
       │relational │ │semantic_  │ │vector_store  │     │
       │   _db     │ │  logic    │ │ (ChromaDB)   │     │
       └───────────┘ └─────┬─────┘ └──────┬───────┘     │
             ▲             │              │             │
             │             └──────────────┼─────────────┘
             │ Contrato incompatível      │ Implementa
             │ com store/connection       ▼
             │                     ┌──────────────┐
             │                     │base_backend  │
             │                     └──────────────┘
```

### Detalhamento dos Pares de Interação Interna:

| Arquivo Origem | Arquivo Destino | Tipo de Relação | Status / Incompatibilidade Identificada |
|---|---|---|---|
| [`store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py) | Composição direta | **Acoplamento com Risco de Deadlock**: `SqliteStore` instancia `ConnectionManager` e submete lambdas para `write_callback`. Se qualquer função interna de `SqliteStore` (ex.: `touch_node_commit`) for chamada dentro de um callback de escrita, o sistema trava em deadlock na fila serializada (**Achado #1**). |
| [`store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) | Inicialização DDL | **Omissão de Checkpoints**: `_boot_schema()` instancia `SchemaManager` e aplica o DDL. O `SchemaManager` não inclui nem valida as tabelas `fsm_checkpoints` e `agent_checkpoints` (**Achado #4**). |
| [`store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py) | Delegação | **Alinhado com Inconsistências de Tipo**: `SqliteStore` delega métodos como `compute_recency_score`, `hybrid_search_score` e `get_dependency_tree` para `GraphLogic`. Propaga os bugs de fuso horário (**Achado #5**) e duplicação de nós em CTE (**Achado #8**). |
| [`store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py) | Omissão total | **Isolamento de Domínio**: `SqliteStore` ignora completamente `semantic_logic.py`. A tabela `semantic_facts` é criada no DDL de `schema.py`, mas a fachada `store.py` não tem nenhum método de inserção ou consulta para ela (**Achado #9**). |
| [`store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) | Desacoplamento / Falta de Coordenação | **Dessincronização em Cascata**: Quando `store.delete_node(node_id)` ou `store.delete_project(uuid)` é executado no SQLite, o `ChromaVectorStore` **não é notificado**. Os vetores tornam-se órfãos imediatamente na base vetorial. |
| [`relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py) | [`connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py) | Contrato de Escrita | **Incompatibilidade de Assinatura**: `init_fsm_checkpoints_schema` busca `db_manager.execute_write` ou `db_manager.write_query`. Nem `ConnectionManager` nem `SqliteStore` possuem esses métodos (pertencem ao `core/database.py`). O init falha silenciosamente (**Achado #4**). |
| [`schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) | [`logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py) | Enums e DDL de Busca | **Alinhado**: `logic.py` importa `VALID_STATUSES` de `schema.py` e executa consultas nas tabelas `nodes_fts`, `edges`, `nodes` e `trajectories` criadas pelo `SchemaManager`. |
| [`schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) | [`semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py) | DDL / Tabelas | **Alinhado**: As colunas e restrições `CHECK(scope_type IN ('user', 'session', 'agent', 'org'))` em `schema.py` correspondem exatamente às validações em `semantic_logic.py`. |
| [`vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) | [`base_backend.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py) | Herança / Implementação | **Violação de Contrato**: `BaseVectorBackend.search` prescreve `project_uuids` como filtro de isolamento estrito. `ChromaVectorStore.search` ignora o escopo quando `project_uuids=[]` (**Achado #6**). |
| [`__init__.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/__init__.py) | Todos os módulos | Exportação Pública | **Omissão de Módulos**: Não exporta nem `semantic_logic` nem `relational_db`, forçando imports profundos ad-hoc. |

---

## 3. Matriz de Interação Transversal (Entre `storage/` e Módulos Auditados)

| Módulo Externo | Componente de `storage/` | Ponto de Contato / Contrato | Status / Impacto de Risco |
|---|---|---|---|
| [`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py) | [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py) | DDL de `fsm_checkpoints` | **Risco Alto**: `AgnosticCheckpointer` tenta persistir em `fsm_checkpoints`, mas a tabela nunca é criada pelo boot do `SqliteStore` nem pelo `SchemaManager`. |
| [`core/vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py) | [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) | `verify_sync(sqlite_node_ids)` | **Bug Cruzado**: `VectorReconciler` tentava passar caminhos de arquivo (`str`), enquanto `verify_sync` espera `set[int]`. Se corrigido no reconciler, `verify_sync` funciona, mas depende de `doc_id` seguir estritamente o padrão `node_{int}`. |
| [`core/background_janitor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py) | [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | `is_write_queue_empty()`, `execute_read_sql()` | **Estável**: Janitor utiliza os métodos de encapsulamento de `store.py` sem tocar diretamente em `_conn_mgr._write_queue._queue`. |
| [`core/rate_governor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py) | [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py) | Concorrência de I/O | **Impacto Indireto**: O rate governor controla tarefas, mas não gerencia as conexões SQLite de threads efêmeras, agravando o vazamento de conexões (**Achado #2**). |
| [`core/security_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py) | [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) | Isolamento de projetos | **Quebra de Segurança**: O Security Guard valida paths e permissões no sistema de arquivos, mas o `ChromaVectorStore` permite vazamento cross-project quando `project_uuids=[]` (**Achado #6**). |

---

## 4. Detalhamento Técnico dos Achados e Prova Empírica

### Achado #1: Deadlock Inevitável em Escritas Reentrantes/Aninhadas no `SerializedWriteQueue`
- **Severidade:** 🔴 **CRÍTICO**
- **Arquivo:** [`storage/connection.py:111-140`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L111-L140)
- **Mecanismo:**
  `SerializedWriteQueue.submit()` cria um `_WriteJob`, coloca-o na fila `self._queue` e executa `job.result_event.wait()`. A única thread que consome dessa fila é a thread `sqlite-writer`. Se uma função submetida à fila (`job.fn`) invocar direta ou indiretamente qualquer outro método de escrita (como um hook de auditoria, uma atualização secundária ou um callback reentrante), a nova submissão executa dentro do próprio worker thread `sqlite-writer`. O worker submete o job e entra em `wait()`. Como ele próprio é o único trabalhador da fila, ele nunca consumirá o novo job, entrando em um deadlock clássico e irrecuperável.
- **Evidência no Código:**
  ```python
  def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
      if not self._running:
          raise RuntimeError("SerializedWriteQueue is not running. Call start() first.")

      job = _WriteJob(fn=fn, args=args, kwargs=kwargs)
      self._queue.put(job)
      job.result_event.wait()  # <--- Bloqueia indefinidamente se chamada da própria thread trabalhadora!
  ```

---

### Achado #2: Vazamento Perpétuo de Conexões SQLite de Threads Finalizadas
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`storage/connection.py:257-273`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L257-L273)
- **Mecanismo:**
  O método `get_read_connection()` instancia uma conexão de leitura para a thread atual e a anexa à lista `self._read_connections`:
  ```python
  conn = getattr(self._local, "conn", None)
  if conn is None:
      conn = sqlite3.connect(self._db_path, check_same_thread=False)
      ...
      self._local.conn = conn
      with self._read_conns_lock:
          self._read_connections.append(conn)
  return conn
  ```
  Quando threads de trabalho (ex.: threads criadas por `ThreadPoolExecutor`, subagentes, rotinas em background) terminam sua execução, o dicionário thread-local é destruído, mas a lista `self._read_connections` retém uma **referência forte** ao objeto `sqlite3.Connection`. O garbage collector nunca consegue liberar a conexão e o descritor de arquivo aberto do SO. Com o passar do tempo e centenas de requisições, ocorre exaustão de descritores de arquivo e memory leak.

---

### Achado #3: Falha ao Reiniciar `SerializedWriteQueue` após `stop()` (`RuntimeError`)
- **Severidade:** 🟡 **MÉDIO**
- **Arquivo:** [`storage/connection.py:75, 81-89, 95-110`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L75-L110)
- **Mecanismo:**
  Em `SerializedWriteQueue.__init__`:
  ```python
  self._thread = threading.Thread(target=self._worker, daemon=True, name="sqlite-writer")
  ```
  Ao chamar `stop()`, a thread finaliza. Ao tentar chamar `start()` novamente, o código invoca `self._thread.start()`. No modelo de concorrência do Python, um objeto `threading.Thread` já finalizado não pode ser reiniciado, gerando `RuntimeError: threads can only be started once`.

---

### Achado #4: Incompatibilidade de Contrato entre `relational_db.py` e `store.py`
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`storage/relational_db.py:27-35`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py#L27-L35) e [`storage/store.py:84-110`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L84-L110)
- **Mecanismo:**
  `relational_db.py` implementa `init_fsm_checkpoints_schema`:
  ```python
  def init_fsm_checkpoints_schema(db_manager: Any) -> bool:
      write_fn = getattr(db_manager, "execute_write", getattr(db_manager, "write_query", None))
      if write_fn:
          success, _ = write_fn(FSM_CHECKPOINTS_TABLE_SQL)
          return bool(success)
      return False
  ```
  No entanto, nem `SqliteStore` nem `ConnectionManager` implementam `execute_write` ou `write_query` — eles utilizam o método `write(callable)`. Como resultado, se `init_fsm_checkpoints_schema(store)` for chamado, o método retorna `False` silenciosamente. Além disso, `SchemaManager.apply_full_schema` em `schema.py` não contém a instrução DDL de `fsm_checkpoints`, fazendo com que a tabela nunca exista no banco padrão.

---

### Achado #5: Falha de Tipo em `_calculate_decay` com Timestamps ISO Offset-Aware (Degradação para 0.01)
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`storage/logic.py:330-350`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L330-L350)
- **Mecanismo:**
  No cálculo de decaimento temporal:
  ```python
  commit_dt = datetime.fromisoformat(last_commit_at)
  now = datetime.utcnow()
  delta_days = max((now - commit_dt).total_seconds() / 86400, 0.0)
  ```
  Se o valor de `last_commit_at` contiver fuso horário (ex.: `'2026-09-22T02:12:15.176736+00:00'`, padrão de geradores ISO UTC modernos), `commit_dt` é um objeto *offset-aware*. Mas `datetime.utcnow()` retorna um objeto *offset-naive*.
  A operação `now - commit_dt` lança `TypeError: can't subtract offset-naive and offset-aware datetimes`.
  O bloco `except (ValueError, TypeError):` captura a exceção e retorna imediatamente `self.RECENCY_MIN_SCORE` (`0.01`). Assim, nós commitados segundos atrás são penalizados ao extremo, recebendo o score mínimo como se fossem obsoletos.

---

### Achado #6: Bypass de Isolamento Estrito (*Strict Scoping*) em `ChromaVectorStore.search`
- **Severidade:** 🔴 **CRÍTICO**
- **Arquivo:** [`storage/vector_store.py:449-458, 711-740`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L711-L740)
- **Mecanismo:**
  Em `ChromaVectorStore._build_where_filter`:
  ```python
  if project_uuids:
      if len(project_uuids) == 1:
          conditions.append({"project_uuid": project_uuids[0]})
      else:
          conditions.append({"project_uuid": {"$in": project_uuids}})
  ```
  Se `project_uuids` for uma lista vazia `[]` (por exemplo, quando um chamador não define escopo ou passa uma lista vazia de referências), a condição de isolamento de projeto é ignorada. A busca prossegue com `where=None` (ou apenas com filtros secundários como `node_type`), retornando vetores confidenciais de outros projetos.

---

### Achado #7: Crash com `ValueError` em `ChromaVectorStore.search` por `node_id` Vazio ou `None`
- **Severidade:** 🟡 **MÉDIO**
- **Arquivo:** [`storage/vector_store.py:477, 695-708`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L477)
- **Mecanismo:**
  O método `_sanitize_metadata` converte valores `None` para string vazia `""`:
  ```python
  elif v is None:
      safe[k] = ""
  ```
  Caso um embedding seja persistido com `metadata={"node_id": None, ...}`, o ChromaDB armazena `"node_id": ""`.
  Durante a execução de `search()`, o código faz:
  ```python
  node_id=int(meta.get("node_id", 0))
  ```
  Como a chave `"node_id"` existe no dicionário com valor `""`, o valor padrão `0` é ignorado, e a chamada `int("")` lança `ValueError: invalid literal for int() with base 10: ''`, derrubando toda a consulta de busca vetorial.

---

### Achado #8: Duplicação de Nós na CTE Recursiva `get_dependency_tree`
- **Severidade:** 🟡 **MÉDIO**
- **Arquivo:** [`storage/logic.py:578-593`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L578-L593)
- **Mecanismo:**
  A consulta CTE constrói a árvore de dependência:
  ```sql
  WITH RECURSIVE dep_tree(id, label, node_type, depth) AS (
      SELECT id, label, node_type, 0
      FROM nodes WHERE id = ?
      UNION ALL
      SELECT n.id, n.label, n.node_type, dt.depth + 1
      FROM nodes n
      JOIN edges e ON n.id = e.target_id
      JOIN dep_tree dt ON e.source_id = dt.id
      WHERE dt.depth < ?
  )
  SELECT DISTINCT * FROM dep_tree ORDER BY depth;
  ```
  A tupla gerada na CTE contém `(id, label, node_type, depth)`. Se o nó de destino for acessível por dois caminhos com profundidades diferentes (exemplo diamante: A -> B -> C e A -> C), a CTE gera `(C, 1)` e `(C, 2)`. O `SELECT DISTINCT *` falha em desduplicar porque as tuplas possuem valores de `depth` distintos.

---

### Achado #9: Isolamento de `semantic_logic.py` e Quebra de Encapsulamento
- **Severidade:** 🔵 **BAIXO**
- **Arquivo:** [`storage/semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py) e [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py)
- **Mecanismo:**
  `SqliteStore` disponibiliza 49 métodos públicos, mas nenhum para consulta ou mutação de fatos semânticos (`semantic_facts`), apesar de a tabela ser formalmente criada pelo `SchemaManager`. Para consultar fatos semânticos, módulos externos (como `core/middleware.py:632`) são forçados a quebrar o encapsulamento:
  ```python
  with self._store._conn_mgr.read() as conn:
      facts = get_active_semantic_facts(conn, scope_type, scope_id)
  ```

---

## 5. Saída Bruta Completa da Reprodução no Terminal (Regra 2)

O script [`scratch/reproduce_storage_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_storage_findings.py) foi executado no terminal PowerShell (`task-1246`). Abaixo está a transcrição integral e exata do stdout e stderr do terminal:

```text
invalid last_commit_at: '2026-09-22T02:12:15.176736+00:00'. Using minimum score.
=================================================================
EXECUCAO DO PROTOCOLO DE AUDITORIA: STORAGE/
=================================================================

--- [ACHADO 1] Deadlock em Chamadas de Escrita Reentrante / Aninhadas no SerializedWriteQueue ---
  [outer_write] Executando no worker thread: sqlite-writer
  [outer_write] Tentando submeter escrita aninhada...
  [RESULTADO] Deadlock confirmado! A thread chamadora esta bloqueada em job.result_event.wait().
  Worker thread name: sqlite-writer is_alive: True

--- [ACHADO 2] Vazamento de Conexoes SQLite de Threads Finalizadas no ConnectionManager ---
  Conexoes registradas inicialmente: 0
  Todas as 5 threads foram finalizadas (is_alive = False).
  Status is_alive das threads: [False, False, False, False, False]
  Conexoes retidas em _read_connections apos threads morrerem: 5
  Quantidade de conexoes zumbis vazadas em memoria: 5

--- [ACHADO 3] Falha Critica ao Reiniciar SerializedWriteQueue (RuntimeError) ---
  Fila iniciada pela primeira vez. is_alive: True
  Fila parada via stop(). is_alive: False
  Tentando reiniciar via start()...
  [EXCECAO CAPTURADA]: RuntimeError: threads can only be started once

--- [ACHADO 4] Incompatibilidade de Contrato: init_fsm_checkpoints_schema falha silenciosamente ---
  SqliteStore inicializado.
  Chamando init_fsm_checkpoints_schema(store)...
  Retorno de init_fsm_checkpoints_schema: False
  Tabela 'fsm_checkpoints' existe no banco? False

--- [ACHADO 5] Falha de Tipo em _calculate_decay com Timestamp ISO Aware (Degradacao para 0.01) ---
  Testando commit gerado agora ha 0 segundos: '2026-09-22T02:12:15.176736+00:00'
  Score calculado: 0.01
  Score esperado para commit de agora: ~1.0
  Score retornado e igual ao RECENCY_MIN_SCORE (0.01)? True

--- [ACHADO 6] Vazamento Cross-Project em ChromaVectorStore.search com project_uuids=[] ---
  Busca com project_uuids=[] retornou 1 resultados!
    Vazou: doc_id=node_101, project_uuid=proj_secret_999, node_id=101

--- [ACHADO 7] Crash ValueError em ChromaVectorStore.search quando node_id e None ou string vazia ---
  [EXCECAO CAPTURADA]: ValueError: invalid literal for int() with base 10: ''

--- [ACHADO 8] CTE get_dependency_tree Duplica Nos Quando Ha Multiplos Caminhos ou Ciclos ---
  Arvore de dependencia para no A:
    id=1, label=A, depth=0
    id=2, label=B, depth=1
    id=3, label=C, depth=1
    id=3, label=C, depth=2
  No C apareceu 2 vezes na saida de get_dependency_tree!

--- [ACHADO 9] Isolamento de semantic_logic.py e Quebra de Encapsulamento de SqliteStore ---
  Total de metodos publicos em SqliteStore: 49
  Funcoes de mutacao/leitura em semantic_logic.py: ['Any', 'get_active_semantic_facts', 'insert_semantic_fact', 'invalidate_semantic_fact', 'update_memory_utility']
  Funcoes de semantic_logic ausentes na fachada SqliteStore: ['Any', 'get_active_semantic_facts', 'insert_semantic_fact', 'invalidate_semantic_fact', 'update_memory_utility']
  Consequencia: middleware.py (linha 632) eh obrigado a acessar store._conn_mgr.read() diretamente para ler fatos.

=================================================================
FIM DA EXECUCAO
=================================================================
```

---

## 6. Análise Estática (Mypy) e Testes Automatizados

### Verificação de Tipagem (Mypy)
Execução do comando `python -m mypy storage/ --follow-imports=skip`:
```text
storage\semantic_logic.py:50: error: Incompatible return value type (got "int | None", expected "int")  [return-value]
storage\vector_store.py:347: error: Item "None" of "Any | None" has no attribute "upsert"  [union-attr]
storage\vector_store.py:409: error: Item "None" of "Any | None" has no attribute "upsert"  [union-attr]
storage\vector_store.py:453: error: Item "None" of "Any | None" has no attribute "query"  [union-attr]
storage\vector_store.py:496: error: Item "None" of "Any | None" has no attribute "delete"  [union-attr]
storage\vector_store.py:520: error: Item "None" of "Any | None" has no attribute "delete"  [union-attr]
storage\vector_store.py:554: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]
storage\vector_store.py:564: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]
storage\vector_store.py:603: error: Item "None" of "Any | None" has no attribute "heartbeat"  [union-attr]
storage\vector_store.py:620: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]
storage\vector_store.py:625: error: Item "None" of "Any | None" has no attribute "count"  [union-attr]
storage\vector_store.py:747: error: Item "None" of "Any | None" has no attribute "get"  [union-attr]
storage\store.py:749: error: Incompatible return value type (got "int | None", expected "int")  [return-value]
Found 13 errors in 3 files (checked 9 source files)
```

### Suite de Testes (Pytest)
Execução do comando `python -m pytest tests/test_storage_logic.py`:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 57 items

tests\test_storage_logic.py ............................................ [ 77%]
.............                                                            [100%]

============================== warnings summary ===============================
tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:341: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

====================== 57 passed, 15 warnings in 12.13s =======================
```

---

## 7. Recomendações e Plano de Remediação (Para a Fase 2)

1. **Deadlock Reentrante em `SerializedWriteQueue` (Achado #1)**:
   - Modificar `submit()` para inspecionar se a thread chamadora é a própria thread trabalhadora (`threading.current_thread() == self._thread`). Se for, executar `fn(self._conn, *args, **kwargs)` imediatamente em vez de enfileirar e bloquear em `result_event.wait()`.
2. **Vazamento de Conexões em `ConnectionManager` (Achado #2)**:
   - Substituir a lista de conexões por referências fracas (`weakref.WeakSet`) ou vincular o fechamento da conexão ao ciclo de vida da thread via `threading.local` com finalizador.
3. **Reinicialização da Fila (Achado #3)**:
   - Em `SerializedWriteQueue.start()`, instanciar uma nova `threading.Thread` se a thread anterior estiver encerrada (`self._thread is None or not self._thread.is_alive()`).
4. **Alinhamento de Contrato de Checkpoints (Achado #4)**:
   - Adicionar método compatível em `SqliteStore` ou integrar a criação de `fsm_checkpoints` e `agent_checkpoints` diretamente ao DDL de `storage/schema.py:TABLES_SQL`.
5. **Correção de Fuso Horário e Decaimento (Achado #5)**:
   - Migrar `datetime.utcnow()` para `datetime.now(timezone.utc)` e garantir normalização de `commit_dt` para UTC aware antes de calcular `delta_days`.
6. **Correção de Strict Scoping no Vetor (Achado #6)**:
   - Em `ChromaVectorStore._build_where_filter`: se `project_uuids` for vazio `[]`, forçar uma condição impossível (ex.: `{"project_uuid": "__NO_PROJECT__"}`) ou retornar lista vazia imediatamente em `search()`.
7. **Tratamento de `node_id` no Vetor (Achado #7)**:
   - Validar em `_validate_metadata` que `isinstance(metadata["node_id"], int)`.
8. **Desduplicação na CTE (Achado #8)**:
   - Modificar a projeção final da CTE para agrupar por nó: `SELECT id, label, node_type, MIN(depth) AS depth FROM dep_tree GROUP BY id, label, node_type ORDER BY depth`.
9. **Fachada Completa de Fatos Semânticos (Achado #9)**:
   - Adicionar métodos delegados em `SqliteStore` (`insert_semantic_fact`, `get_active_semantic_facts`, `invalidate_semantic_fact`, `update_memory_utility`) para encapsular o acesso a `semantic_logic.py`.
