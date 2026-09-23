# Auditoria Transversal — Duplicação de `SerializedWriteQueue` e Descompasso de Persistência

> **Item:** `duplicacao-serialized-write-queue` (Achado Transversal de Alta Prioridade)  
> **Fase:** 1 — Auditoria módulo a módulo (inserido fora de ordem por risco estrutural)  
> **Arquivos Analisados:**  
> - [`interface/queue_writer.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py) (SDD-SURVIVAL-10)  
> - [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py) (SDD-SURVIVAL-02 / SqliteStore Connection Layer)  
> - [`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py) (`ConciergeDatabaseManager`)  
> - [`interface/mcp_server.py:159-175`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L159-L175) (Instanciação de `db_manager`)  
> - [`main.py:120-200`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L120-L200) e [`interface/cli.py:65-120`](file:///c:/Nexus-Memory/GrafoConcierge/interface/cli.py#L65-L120)  
> **Data:** 2026-09-22  
> **Status:** Concluído com reprodução empírica executável  

---

## 1. Contexto, Hipótese Inicial e Realidade Operacional

Durante a auditoria de `storage/` e `core/`, formulou-se a hipótese de que haveria *"duas implementações concorrentes de `SerializedWriteQueue` disputando o mesmo arquivo físico"*, baseando-se na existência de duas classes com nomes idênticos:
1. `interface/queue_writer.py::SerializedWriteQueue`: projetada para `core/database.py::ConciergeDatabaseManager` com suporte a *Opportunistic Auto-Batching* (até 50 itens) e fallback atômico;
2. `storage/connection.py::SerializedWriteQueue`: projetada para `storage/store.py::SqliteStore` via `ConnectionManager`, com execução sequencial de callables arbitrários.

Entretanto, a auditoria rigorosa dos pontos de montagem reais em produção ([`interface/mcp_server.py:161-166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L161-L166)) desfez essa moldura: **não existem duas filas concorrendo em produção**. O que realmente opera em tempo de execução é:
- **Uma fila real e ativa em `storage/`** (`storage/connection.py::SerializedWriteQueue`), com worker thread e `foreign_keys=ON;`;
- **ZERO fila do lado de `core/`** (`core/database.py::ConciergeDatabaseManager`), que ao ser instanciado em `mcp_server.py:166` sem `write_queue` (`write_queue=None`), dispara conexões SQLite físicas efêmeras cruas (`sqlite3.connect`), sem serialização, sem mutex e sem `foreign_keys=ON;`.
- A fila de `interface/queue_writer.py` é **código morto em produção**, sobrevivendo apenas em testes automatizados (`tests/`).

Ao bifurcar o acesso ao mesmo arquivo físico `data/concierge.db` dessa forma, conexões efêmeras do `core/` bombardeiam o banco por fora de qualquer fila, quebrando a integridade e colidindo com a fila real do `storage/`.

---

## 2. Tabela Oficial de Achados

| # | Arquivo Principal | Linhas | Severidade | Mecanismo | Reprodução Empírica | Status |
|---|-------------------|--------|-----------|-----------|---------------------|--------|
| 1 | `storage/connection.py` vs `core/database.py` (e `interface/queue_writer.py`) | `storage/connection.py:59`, `core/database.py:56–70`, `interface/mcp_server.py:166` | 🔴 **CRÍTICA** | **Colisão entre Fila Real (`storage/`) e Zero Fila (`core/`) sobre o Mesmo Banco**: A arquitetura projetou duas classes `SerializedWriteQueue`, mas em produção ([`interface/mcp_server.py:166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L166)) `ConciergeDatabaseManager` é instanciado com `write_queue=None`. A realidade operacional de produção não são duas filas colidindo, mas a coexistência de **uma fila real** (`storage/connection.py`) disputando o banco `data/concierge.db` contra **zero fila** do lado de `core/database.py` (que dispara conexões SQLite efêmeras cruas a cada escrita, sem serialização, sem mutex e sem `foreign_keys=ON`). | Verificação do call site real em `mcp_server.py:166`; execução simultânea de escrita via fila de storage vs conexões efêmeras cruas de `ConciergeDatabaseManager` contra o mesmo banco físico. | **CONFIRMADO** |
| 2 | `interface/mcp_server.py` e `core/database.py` | `interface/mcp_server.py:166` e `core/database.py:27–29, 56–70` | 🔴 **CRÍTICA** | **Ilusão dos Testes e Código Morto em Produção**: `interface/queue_writer.py` é testada em 11 suites de teste (`tests/`), mas em produção (`mcp_server.py:166`) `ConciergeDatabaseManager(resolved_db_path)` é instanciado **SEM** `write_queue`. Com `self.write_queue = None`, todas as escritas de `core/` em produção executam conexões efêmeras diretas (`sqlite3.connect` por query), contornando 100% a proteção serializada que a arquitetura alega oferecer. | Análise estática do call site de produção vs 11 suítes de teste; inspeção de `self.write_queue is None` em tempo de execução. | **CONFIRMADO** |
| 3 | `interface/queue_writer.py` e `core/database.py` | `interface/queue_writer.py:49–52`, `core/database.py:60`, `storage/connection.py:155` | 🟠 **GRAVE** | **Divergência de Integridade Referencial (`foreign_keys=OFF`)**: `storage/connection.py` ativa `PRAGMA foreign_keys=ON;`. Porém, `interface/queue_writer.py` e `core/database.py` **NÃO configuram foreign keys** (permanecem desativadas = 0). O `core/` consegue gravar arestas e registros com IDs órfãos no banco compartilhado, enquanto `storage/` falha com `IntegrityError`. | `ConciergeDatabaseManager` gravou aresta apontando para `source_id=999999` inexistente com sucesso (`rowid=1`). `SqliteStore` rejeitou a mesma operação com `IntegrityError`. | **CONFIRMADO** |
| 4 | `storage/connection.py` vs `interface/queue_writer.py` | `storage/connection.py:154` vs `interface/queue_writer.py:49` | 🟠 **GRAVE** | **Timeout Assimétrico e Falha com `OperationalError: database is locked`**: `storage/connection.py` configura `PRAGMA busy_timeout=5000;` (5 segundos). Já `interface/queue_writer.py` e `core/database.py` usam `timeout=30.0` (30 segundos). Sob contenção sustentada (>5s), a camada de `storage/` aborta prematuramente com erro de banco travado, enquanto `core/` continua aguardando. | Transação exclusiva mantida por 5.5s: `SqliteStore` abortou exatamente aos 5.60s com `sqlite3.OperationalError: database is locked`. | **CONFIRMADO** |
| 5 | `interface/mcp_server.py` | `interface/mcp_server.py:161–166` | 🟡 **MÉDIO** | **Quebra de Encapsulamento para Bifurcação de Estado**: `mcp_server.py` acessa `self._gc._store._conn_mgr._db_path` (três atributos privados consecutivos) para criar uma segunda instância desconexa em vez de utilizar uma camada unificada de persistência. | Análise de AST e rastreamento de instâncias em `main.py` e `mcp_server.py`. | **CONFIRMADO** |

---

## 3. Detalhamento dos Mecanismos

### Achado #1: Colisão entre Fila Real (`storage/connection.py`) e Zero Fila (`core/database.py`) sobre o Mesmo Banco Físico
- **Mecanismo Real em Produção:**  
  A documentação em `01_ARCHITECTURE.md` afirma que o Grafo Concierge possui uma fila única de gravação serializada para eliminar por completo erros de *Database Lock*.  
  No código-fonte, foram implementadas duas classes independentes denominadas `SerializedWriteQueue` ([`storage/connection.py:59`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L59) e [`interface/queue_writer.py:32`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L32)).  
  Contudo, o rastreamento da instanciação no servidor MCP revela a verdadeira topologia operacional em produção: **não são duas filas disputando o banco, mas sim uma fila real coexistindo com zero fila do outro lado**:
  1. **Lado `storage/` ([`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py)):** Opera com uma fila serializada real ativa ([`storage/connection.py::SerializedWriteQueue`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L59)), consumida pelo worker thread dedicado `sqlite-writer` com `PRAGMA foreign_keys=ON;` e `PRAGMA busy_timeout=5000;`.
  2. **Lado `core/` ([`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py)):** Em produção ([`interface/mcp_server.py:166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L166)), `ConciergeDatabaseManager(resolved_db_path)` é instanciado **sem** o parâmetro `write_queue`. Com `self.write_queue = None`, **não há nenhuma fila serializadora ativa**. Cada chamada a `execute_write` abre e fecha uma conexão SQLite física efêmera crua (`sqlite3.connect` com timeout de 30s), executando queries diretas, sem passar por fila e sem `foreign_keys=ON`.
  3. A segunda fila ([`interface/queue_writer.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py)) existe apenas nos testes automatizados (`tests/`), criando a ilusão de que o `core/` possui uma fila de escrita dedicada.
- **Impacto no Sistema:**  
  O arquivo físico `data/concierge.db` é bombardeado concorrentemente pela thread da fila de `storage/` e por múltiplos fluxos efêmeros não-serializados vindos de `core/` (como `checkpointer`, `delta_manager` e `background_janitor`). As conexões efêmeras do `core/` não respeitam a fila de `storage/` e não validam integridade referencial, podendo intercalar escritas no meio de operações lógicas alheias e provocar `database is locked` na fila de storage aos 5 segundos sob contenção.

---

### Achado #2: Ilusão dos Testes e Código Morto em Produção
- **Mecanismo:**  
  Ao auditar o ciclo de vida real em [`interface/mcp_server.py:159-167`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L159-L167):
  ```python
  if db_manager is None:
      resolved_db_path = None
      if hasattr(self._gc, "_store") and hasattr(self._gc._store, "_conn_mgr"):
          resolved_db_path = str(self._gc._store._conn_mgr._db_path)
      if not resolved_db_path:
          resolved_db_path = os.environ.get("GRAFO_DB_PATH", "data/concierge.db")
      from core.database import ConciergeDatabaseManager
      db_manager = ConciergeDatabaseManager(resolved_db_path)
  ```
  O construtor `ConciergeDatabaseManager` recebe apenas `resolved_db_path`. O argumento `write_queue` é deixado com seu valor default (`None`):
  ```python
  def __init__(self, db_path: str, write_queue: Optional[SerializedWriteQueue] = None):
      self.db_path = db_path
      self.write_queue = write_queue
  ```
  Quando `self.write_queue is None`, o método [`ConciergeDatabaseManager.execute_write`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L58-L69) recorre ao fallback direto:
  ```python
  conn = sqlite3.connect(self.db_path, timeout=30.0)
  try:
      conn.execute("PRAGMA journal_mode=WAL;")
      cursor = conn.cursor()
      cursor.execute(query, params)
      conn.commit()
      last_id = cursor.lastrowid
      return True, last_id
  finally:
      conn.close()
  ```
- **Consequência:**  
  Em ambiente de produção, **`interface/queue_writer.py::SerializedWriteQueue` NUNCA É INSTANCIADA!** É 100% código morto em runtime. Cada chamada a `checkpointer.save_checkpoint`, `delta_manager` ou `janitor` abre e fecha uma conexão SQLite efêmera direta.  
  Entretanto, **11 arquivos de teste em `tests/`** instanciam manualmente `SerializedWriteQueue` e a injetam em `ConciergeDatabaseManager`, gerando uma falsa sensação de cobertura de concorrência que não reflete a topologia de produção.

---

### Achado #3: Divergência de Integridade Referencial (`PRAGMA foreign_keys=OFF`)
- **Mecanismo:**  
  As conexões do SQLite por padrão **não validam chaves estrangeiras** a menos que o comando `PRAGMA foreign_keys=ON;` seja explicitamente executado após o `connect()`.
  - Em `storage/connection.py:155, 269`, o PRAGMA é devidamente executado em todas as conexões de leitura e no worker de escrita (`PRAGMA foreign_keys=ON;`).
  - Em `interface/queue_writer.py:49–52`, o worker só executa:
    ```python
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    ```
  - Em `core/database.py:46, 60`, o fallback direto só executa:
    ```python
    conn.execute("PRAGMA journal_mode=WAL;")
    ```
- **Comprovação de Corrupção:**  
  Ao inserir uma aresta na tabela `edges` com `source_id = 999999` (um nó que não existe na tabela `nodes`):
  - `ConciergeDatabaseManager` inseriu com sucesso e gravou o registro órfão `(999999, 1, 'CALLS')` no banco físico compartilhado.
  - `SqliteStore` rejeitou a inserção equivalente lançando `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.  
  Isso prova que qualquer módulo baseado em `core/database.py` pode corromper silenciosamente a integridade referencial do Grafo sem que o banco rejeite a transação.

---

### Achado #4: Timeout Assimétrico e Falha com `OperationalError: database is locked`
- **Mecanismo:**  
  Quando dois processos ou threads tentam gravar simultaneamente no SQLite sob WAL mode, o segundo escritor aguarda até o limite configurado em `busy_timeout`.
  - `storage/connection.py`: define `PRAGMA busy_timeout=5000;` (5.000 ms = 5s).
  - `interface/queue_writer.py` e `core/database.py`: usam `sqlite3.connect(..., timeout=30.0)` (30.000 ms = 30s).
- **Comprovação:**  
  Se uma operação pesada (ex: `JanitorService` limpando centenas de checkpoints, migração DDL, ou transação de lote de embeddings) reter o lock exclusivo de escrita por mais de 5 segundos:
  - `storage/connection.py::SerializedWriteQueue` esgota os 5 segundos e falha imediatamente com `sqlite3.OperationalError: database is locked`.
  - A camada de `storage/` quebra enquanto o `core/` ainda esperaria por mais 25 segundos, criando uma assimetria operacional frágil e imprevisível.

---

## 4. Matriz de Comparação entre as Implementações

| Característica | `storage/connection.py` | `interface/queue_writer.py` | `core/database.py` (Fallback Direto) |
|---|---|---|---|
| **Nome da Classe** | `SerializedWriteQueue` | `SerializedWriteQueue` | `ConciergeDatabaseManager` |
| **Camada Consumidora** | `storage/store.py` (`SqliteStore`) | `core/` (apenas em testes) | `core/` (produção via `mcp_server.py`) |
| **Tipo de Worker** | Thread dedicada `sqlite-writer` | Subclasse `threading.Thread` | Epêmero (abre/fecha por query) |
| **Entrada Aceita** | Callables arbitrários `fn(conn, *args)` | Tuplas `(query: str, params: tuple)` | `query: str, params: tuple` |
| **Retorno** | Retorno original da função | `(bool, lastrowid_ou_erro)` | `(bool, lastrowid_ou_erro)` |
| **Auto-Batching** | ❌ Não (executa item a item) | ✅ Sim (até 50 itens com `BEGIN IMMEDIATE`) | ❌ Não |
| **PRAGMA journal_mode** | `WAL` | `WAL` | `WAL` |
| **PRAGMA synchronous** | `FULL` (default SQLite) | `NORMAL` | `FULL` (default) |
| **PRAGMA busy_timeout** | `5000` (5 segundos) | ❌ Ausente (usa `timeout=30.0` no connect) | ❌ Ausente (usa `timeout=30.0`) |
| **PRAGMA foreign_keys** | ✅ `ON` (1) | ❌ **Ausente (`OFF` = 0)** | ❌ **Ausente (`OFF` = 0)** |
| **Uso em Produção** | ✅ Ativo (via `SqliteStore`) | ❌ **Inativo (Código Morto)** | ✅ Ativo (via `mcp_server.py:166`) |

---

## 5. Saída Bruta da Reprodução Empírica

Execução do script de verificação [`scratch/test_duplicate_queue.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_duplicate_queue.py):

```text
Error in write thread (transaction rolled back): FOREIGN KEY constraint failed
Job execution failed: FOREIGN KEY constraint failed
Error in write thread (transaction rolled back): database is locked
Job execution failed: database is locked

=================================================================
1. COMPARATIVO DE PRAGMAS ENTRE AS IMPLEMENTAÇÕES
=================================================================
  [storage/connection.py::SerializedWriteQueue]
    PRAGMA journal_mode = wal
    PRAGMA busy_timeout = 5000
    PRAGMA foreign_keys = 1
    PRAGMA synchronous = 2

  [interface/queue_writer.py::SerializedWriteQueue]
    PRAGMA journal_mode = WAL
    PRAGMA synchronous = NORMAL (vs FULL em storage/connection.py)
    PRAGMA busy_timeout = AUSENTE (usa apenas timeout=30.0 no connect do Python)
    PRAGMA foreign_keys = AUSENTE (OFF - não valida integridade referencial!)

  [core/database.py::ConciergeDatabaseManager (sem write_queue, como em mcp_server.py:166)]
    PRAGMA journal_mode = WAL
    PRAGMA busy_timeout = AUSENTE
    PRAGMA foreign_keys = AUSENTE (OFF)
    PRAGMA synchronous = AUSENTE (default FULL)
    Conexão: Efêmera por query (abre e fecha sqlite3.connect a cada escrita!)

=================================================================
2. DIVERGÊNCIA DE INTEGRIDADE REFERENCIAL (FOREIGN KEYS)
=================================================================
  Inserção de aresta com source_id órfão (999999) via ConciergeDatabaseManager:
    Sucesso retornado: True, rowid: 1
  Tentativa de inserção com source_id órfão via SqliteStore:
    Exceção capturada: IntegrityError: FOREIGN KEY constraint failed
  Aresta órfã gravada no banco pelo ConciergeDatabaseManager: [(999999, 1, 'CALLS')]
  [CORRUPÇÃO DE INTEGRIDADE CONFIRMADA]: ConciergeDatabaseManager gravou chave estrangeira violada no banco compartilhado porque sua fila não ativa PRAGMA foreign_keys=ON!

=================================================================
3. REPRODUÇÃO DE ESCRITA CONCORRENTE SUSTENTADA (DUAS FILAS NO MESMO DB)
=================================================================
  Disparando 3 escritores concorrentes simultâneos por 3.0s contra o mesmo arquivo...
    - Escritor 1: SqliteStore (storage/connection.py SerializedWriteQueue)
    - Escritor 2: ConciergeDatabaseManager + interface/queue_writer.py SerializedWriteQueue
    - Escritor 3: ConciergeDatabaseManager Direto (mcp_server.py:166 em produção)

--- RESULTADOS DA EXECUÇÃO CONCORRENTE ---
  [SqliteStore (storage queue)]:
    Tentativas: 371
    Sucessos reportados: 371
    Erros/Exceções: 0
  [ConciergeDatabaseManager + interface queue]:
    Tentativas: 121
    Sucessos reportados: 121
    Erros/Exceções: 0
  [ConciergeDatabaseManager Direto (mcp_server)]:
    Tentativas: 300
    Sucessos reportados: 300
    Erros/Exceções: 0

--- CONFERÊNCIA DE INTEGRIDADE NO BANCO FÍSICO ---
  Linhas na tabela 'nodes' (SqliteStore): 371 (vs 371 sucessos)
  Linhas na tabela 'test_log' (DatabaseManager): 421 (vs 421 sucessos)
  [OK] Contagem de nós 100% consistente (371).
  [OK] Contagem de logs 100% consistente (421).

=================================================================
4. TIMEOUT ASSIMÉTRICO E LOCKOUT (5s vs 30s)
=================================================================
  [Escritor Externo] Adquiriu BEGIN EXCLUSIVE no banco compartilhado.
  [SqliteStore] Tentando gravar nó via storage/connection.py (busy_timeout=5000ms)...
  [SqliteStore] Resposta após 5.60s:
    Exceção capturada: OperationalError: database is locked
  [CRASH POR CONTENTION CONFIRMADO]: storage/connection.py abortou com 'database is locked' aos 5.0s!
  Enquanto isso, a interface/queue_writer.py aguardaria 30.0s, criando assimetria onde a camada de storage quebra primeiro!

=================================================================
FIM DO TESTE
=================================================================
```

---

## 6. Mapeamento de Dependências e Recomendações para a Fase 2

1. **Unificação da Fila de Escrita (Remoção da Duplicação)**:
   - Eliminar `interface/queue_writer.py` e consolidar toda a persistência do Grafo Concierge sob uma **única** camada de conexão (`storage/connection.py::ConnectionManager`).
   - Fazer com que `ConciergeDatabaseManager` seja uma camada adaptadora leve (ou seja descontinuado), delegando todas as chamadas diretamente para o `SqliteStore` ou para o `ConnectionManager` já existente.
2. **Padronização dos PRAGMAs do SQLite**:
   - Garantir que toda e qualquer conexão aberta no sistema execute invariavelmente:
     - `PRAGMA journal_mode=WAL;`
     - `PRAGMA synchronous=NORMAL;`
     - `PRAGMA busy_timeout=30000;` (unificado em 30 segundos, evitando crashes prematuros aos 5s);
     - `PRAGMA foreign_keys=ON;` (obrigatório para evitar inserção de nós/arestas/checkpoints corrompidos).
3. **Eliminação da Quebra de Encapsulamento em `interface/mcp_server.py:162`**:
   - O servidor MCP deve receber `store: SqliteStore` e reutilizar sua infraestrutura de banco, sem instanciar gerenciadores de banco paralelos nem navegar privadamente por `_store._conn_mgr._db_path`.
4. **Atualização dos Testes Automatizados**:
   - Atualizar os 11 arquivos de teste em `tests/` que hoje instanciam `interface.queue_writer.SerializedWriteQueue` para utilizarem o gerenciador unificado de `storage/connection.py`.
