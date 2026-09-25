# Auditoria Transversal — Schema Oficial Incompleto e Colapso de Produção

> **Item:** `schema-oficial-incompleto` (Achado Transversal de Severidade Máxima Arquitetural)  
> **Fase:** 1 — Auditoria módulo a módulo (investigado com PRIORIDADE MÁXIMA antes de `grafo-dashboard-web/`)  
> **Arquivos Analisados:**  
> - [`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) (`SchemaManager`, `TABLES_SQL`, `verify_tables_exist`)  
> - [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) (`SqliteStore._boot_schema`)  
> - [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py) (`FSM_CHECKPOINTS_TABLE_SQL`, `init_fsm_checkpoints_schema`)  
> - [`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py) (`ConciergeDatabaseManager._init_tables`)  
> - [`docs-grafo-concierge/01_ARCHITECTURE.md`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/01_ARCHITECTURE.md) (Especificação formal das 13 tabelas do sistema)  
> - 12 Módulos consumidores: [`core/delta_manager.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py), [`core/vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py), [`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py), [`core/background_janitor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py), [`core/graph_rag.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py), [`core/search_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/search_engine.py), [`core/intent_classifier.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/intent_classifier.py), [`core/alias_tracker.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py), [`core/hsm_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py), [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py), [`interface/watcher.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py), [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py)  
> **Data:** 2026-09-25  
> **Status:** Concluído com reprodução empírica executável  

---

## 1. Sumário Executivo

Durante a preparação para a auditoria de `grafo-dashboard-web/`, foi realizada uma varredura exaustiva de DDL (`CREATE TABLE`) em todo o repositório. O resultado revelou uma falha de severidade arquitetural absoluta, que **suplanta em gravidade todos os achados documentados até o momento**:

1. **Ausência Total de DDL em Produção**: Fora do diretório de testes (`tests/`) e de scripts temporários (`scratch/`), **nenhum arquivo `.py` de produção contém instruções `CREATE TABLE` para as tabelas `files`, `communities`, `ast_edges`, `agent_checkpoints` ou `fsm_checkpoints`**. Não existe nenhum arquivo `.sql` e nenhuma pasta de migrações (`migrations/`, `alembic/`) no projeto.
2. **Bootstrap Oficial Cria Apenas Metade do Schema**: A única fonte ativa de DDL em todo o sistema é `storage/schema.py::SchemaManager.apply_full_schema()` (invocada na inicialização de `storage/store.py:92`), que cria exclusivamente: `projects`, `nodes`, `edges`, `reference_wings`, `trajectories`, `commit_log`, `user_core_memory`, `semantic_facts` e a tabela virtual `nodes_fts`. As 5 tabelas estruturais de `core/*` **não constam no schema oficial**.
3. **Cisão Ontológica Entre Silos Incompatíveis**: O repositório abriga dois sistemas paralelos que nunca foram integrados no banco de dados:
   - **Silo 1 (Legado / Storage v3.8.0)**: Opera em torno de `nodes` (chunks/símbolos) e `edges` (grafo de conhecimento). Toda a ingestão via `orchestrator.py` e `crawler.py` escreve em `nodes`.
   - **Silo 2 (Core / "SDD-SURVIVAL")**: Os módulos de inteligência analítica (`delta_manager.py`, `vector_reconciler.py`, `background_janitor.py`, `graph_rag.py`, `checkpointer.py`, `telemetry_api.py`, etc.) ignoram a tabela `nodes` e tentam consultar tabelas relacionais dedicadas (`files`, `communities`, `ast_edges`, `agent_checkpoints`, `fsm_checkpoints`).
4. **Colapso Geral em Instalação Limpa**: Em qualquer ambiente novo (`git clone` + `python main.py`), o banco `data/concierge.db` é inicializado sem essas 5 tabelas. Ao tentar executar reconciliação de vetores, sync incremental de arquivos, sumarização em background, traversal de AST via GraphRAG, checkpoints de agentes, ou consultar a API de telemetria, **o sistema entra em colapso imediato com `sqlite3.OperationalError: no such table: ...`**.
5. **A Ilusão dos Testes (The Test Mirage)**: Esse problema permaneceu oculto porque **14 suítes de teste automatizadas** (`test_delta_sync.py`, `test_vector_reconciler.py`, `test_graph_rag_janitor.py`, `test_telemetry_api.py`, `test_checkpoint_pruning.py`, `test_e2e_concierge_integration.py`, etc.) injetam manualmente `CREATE TABLE IF NOT EXISTS files (...)`, `communities`, `ast_edges`, etc., dentro do método `setUp()`. Os testes passavam com 100% de sucesso criando tabelas fantasmas que não existem na aplicação real.

---

## 2. Tabela Oficial de Achados

| # | Módulos Afetados | Linhas Relevantes | Severidade | Mecanismo | Status |
|---|------------------|-------------------|-----------|-----------|--------|
| **1** | [`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py)<br>[`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py)<br>[`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py) | `schema.py:51–144, 285–305`<br>`store.py:91–107`<br>`database.py:32–41` | 🔴 **CRÍTICA MÁXIMA** | **Omissão Estrutural de 5 Tabelas Relacionais no Bootstrap Oficial**: O schema oficial de produção define apenas 8 tabelas legadas + 1 FTS5. As tabelas `files`, `communities`, `ast_edges`, `agent_checkpoints` e `fsm_checkpoints` não possuem DDL em nenhum arquivo de inicialização de produção. `ConciergeDatabaseManager._init_tables()` cria apenas a tabela temporária `test_log`. | **CONFIRMADO E REPRODUZIDO** |
| **2** | 12 Módulos de `core/` e `interface/` | 12 arquivos (ver lista detalhada na Seção 3) | 🔴 **CRÍTICA MÁXIMA** | **Inoperância Funcional de Todos os Subsistemas Analíticos em Instalação Limpa**: Em um banco oficialmente bootstrapado, operações essenciais quebram imediatamente: `reconcile_orphans()` (`no such table: files`), `process_file_change()` (`no such table: files`), `run_idle_summarization()` (`no such table: communities`), `detect_logical_communities()` (`no such table: ast_edges`), `get_telemetry_snapshot()` (`no such table: files`), ferramentas MCP de checkpoints (`no such table: agent_checkpoints`). | **CONFIRMADO E REPRODUZIDO** |
| **3** | [`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py)<br>[`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py)<br>[`interface/watcher.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py) | `database.py:66–67`<br>`checkpointer.py:146–149`<br>`watcher.py:93–100` | 🟠 **GRAVE** | **Mascaramento Silencioso de Erros DDL por Supressão de Exceções**: `core/database.py::execute_write` captura `Exception` e retorna `(False, error)`. `AgnosticCheckpointer.save_checkpoint` retorna `False` sem propagar erro ou registrar log crítico. `interface/watcher.py::hydrate_known_hashes` captura exceções silenciosamente com `except Exception: pass`, ocultando que a leitura de `files` falhou. | **CONFIRMADO E REPRODUZIDO** |
| **4** | Suítes de Teste (`tests/`) | 14 arquivos de teste em `tests/` | 🔴 **CRÍTICA** | **A Ilusão dos Testes (Test Mirage)**: A cobertura de testes do projeto mascara a quebra estrutural porque 14 suítes de teste independentes criam privadamente as tabelas `files`, `communities`, `ast_edges` e `agent_checkpoints` em suas rotinas de fixture `setUp()`, simulando um schema que a aplicação real em produção nunca possui. | **CONFIRMADO** |
| **5** | [`docs-grafo-concierge/01_ARCHITECTURE.md`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/01_ARCHITECTURE.md)<br>[`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) | `01_ARCHITECTURE.md:130–169` vs `schema.py:51–144` | 🟡 **MÉDIO** | **Abandono de Especificação Arquitetural**: A documentação formal de arquitetura em `01_ARCHITECTURE.md` lista com clareza as 13 tabelas necessárias, divididas entre "SURVIVAL & DELTA ENGINE TABLES" (tabelas 1 a 4) e "COGNITIVE GRAPH & FACT TABLES" (tabelas 5 a 12). No entanto, o código de `schema.py` implementou apenas as tabelas 5 a 12, abandonando as tabelas 1 a 4 sem qualquer migração ou aviso. | **CONFIRMADO** |

---

## 3. Detalhamento dos Mecanismos

### Achado #1: Omissão Estrutural de 5 Tabelas no Bootstrap Oficial

A inicialização oficial do Grafo Concierge descrita em `main.py:120-124`:
```python
logger.info("Initializing SqliteStore: %s", DB_PATH)
from storage import SqliteStore
store = SqliteStore(DB_PATH)
```
Dispara internamente `store._boot_schema(db_path)` ([`storage/store.py:84-109`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L84-L109)), que executa:
```python
mgr = SchemaManager(conn)
mgr.apply_full_schema()
```
Em [`storage/schema.py:51-144`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py#L51-L144), a constante `TABLES_SQL` define estritamente:
- `projects`
- `nodes`
- `edges`
- `reference_wings`
- `trajectories`
- `commit_log`
- `user_core_memory`
- `semantic_facts`
- `nodes_fts` (FTS5)

E em `storage/schema.py:285-300`, `verify_tables_exist()` valida apenas essas mesmas tabelas, concluindo:
`Schema v3.8.0 verified - all tables and triggers OK.`

A classe complementar de banco em `core/`, `ConciergeDatabaseManager` ([`core/database.py:32-41`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L32-L41)), possui um método `_init_tables()` que executa exclusivamente:
```python
self.write_query(
    "CREATE TABLE IF NOT EXISTS test_log ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "thread_name TEXT, "
    "val INTEGER"
    ");"
)
```

**Resultado:** Nenhuma das seguintes tabelas é criada:
1. `files` (necessária para dual-hash delta sync, dirty flags, watcher e integridade de vetores);
2. `communities` (necessária para agrupamento topológico e janitor de sumarização SLM);
3. `ast_edges` (necessária para traversals recursivos WITH RECURSIVE de chamadas AST);
4. `agent_checkpoints` (necessária para checkpoints agnósticos de agentes e time-travel);
5. `fsm_checkpoints` (necessária para histórico de transições da máquina de estados HSM).

---

### Achado #2: Ruptura de 12 Módulos Já Auditados em Produção

Ao testar as operações reais de cada subsistema sobre o banco bootstrapado oficialmente, comprovou-se que **todos os módulos de `core/` e interfaces dependentes entram em colapso**:

1. **`core/vector_reconciler.py:54`**:
   `self.db_manager.read_query("SELECT path FROM files;")`
   💥 **Colapso**: `sqlite3.OperationalError: no such table: files`. O reconciliador de vetores não consegue purgar vetores órfãos.
2. **`core/delta_manager.py:134, 183, 214, 237, 257`**:
   `SELECT ssh_hash, body_hash FROM files WHERE path = ?;`
   💥 **Colapso**: `sqlite3.OperationalError: no such table: files`. O sincronizador de deltas não consegue processar alterações em arquivos.
3. **`core/checkpointer.py:105, 139, 152, 187, 196, 227`**:
   - `save_checkpoint`: Falha silenciosa gravando em `agent_checkpoints` e `fsm_checkpoints` (retorna `False`);
   - `load_checkpoint`: `SELECT ... FROM fsm_checkpoints` 💥 `OperationalError: no such table: fsm_checkpoints`;
   - `execute_time_travel`: `DELETE FROM fsm_checkpoints` 💥 `OperationalError: no such table: fsm_checkpoints`.
4. **`core/background_janitor.py:79, 97, 143, 161, 194`**:
   - `run_idle_summarization`: `SELECT id FROM communities WHERE is_dirty = 1;` 💥 `OperationalError: no such table: communities`;
   - `prune_session_checkpoints`: `SELECT DISTINCT session_id FROM agent_checkpoints;` 💥 `OperationalError: no such table: agent_checkpoints`.
5. **`core/graph_rag.py:33, 56, 179, 219, 246`**:
   - `detect_logical_communities`: `FROM ast_edges` 💥 `OperationalError: no such table: ast_edges`;
   - `retrieve_multihop_context`: Retorna payload de erro `{'error': 'no such table: ast_edges'}`;
   - `get_call_chain_recursive`: WITH RECURSIVE sobre `ast_edges` 💥 `OperationalError: no such table: ast_edges`.
6. **`core/search_engine.py:58` (`HybridSearchEngine`)**:
   `SELECT path FROM files WHERE path IN (...);`
   💥 **Colapso**: `sqlite3.OperationalError: no such table: files`. O filtro de auto-cura da busca híbrida falha.
7. **`core/intent_classifier.py:62`**:
   `SELECT COUNT(*) FROM files WHERE ...;`
   💥 **Colapso**: O classificador heurístico de intenções do agente falha ao inspecionar arquivos indexados.
8. **`core/alias_tracker.py:216, 228, 239`**:
   Tenta atualizar `files`, `ast_edges` e `fsm_checkpoints` ao detectar renomeações de arquivos.
9. **`core/hsm_engine.py:421`**:
   `SELECT state_name, shared_state_blob FROM fsm_checkpoints ...`
   💥 **Colapso**: A máquina de estados não consegue restaurar o último estado persistido do banco.
10. **`interface/telemetry_api.py:154, 160, 183, 306`**:
    `SELECT COUNT(*) FROM files;`
    💥 **Colapso**: `GET /api/telemetry/snapshot` e `/api/telemetry/stream` falham com erro 500 (`OperationalError: no such table: files`).
11. **`interface/watcher.py:86, 95, 208`**:
    `SELECT path, structural_hash FROM files;`
    💥 Falha silenciosa no startup: `_known_hashes` inicializa vazio porque a tabela `files` não existe.
12. **`interface/mcp_server.py:887, 914` (Ferramentas FastMCP)**:
    - `concierge_get_call_chain`: 💥 `OperationalError: no such table: ast_edges`;
    - `agent_save_checkpoint`: Retorna `{"success": false, "message": "Failed to save checkpoint..."}`.

---

### Achado #3: Mascaramento Silencioso de Erros DDL

Dois mecanismos no código ocultam ativamente essa falha sistêmica:

1. **`core/database.py:66-67`**:
   ```python
   except Exception as e:
       return False, str(e)
   ```
   Quando qualquer módulo chama `execute_write` ou `write_query` tentando escrever em tabelas inexistentes, nenhuma exceção é levantada para o chamador. O método apenas retorna a tupla `(False, "no such table: ...")`.
   Em `core/checkpointer.py:146`:
   ```python
   success, _ = self.db_manager.execute_write(...)
   if not success:
       return False
   ```
   O checkpointer retorna `False` sem gerar traceback nem logar em nível `ERROR`, fazendo com que o chamador acredite que houve uma falha de validação lógica e não uma ausência estrutural da tabela.

2. **`interface/watcher.py:93-100`**:
   ```python
   try:
       rows = db_manager.read_query("SELECT path, structural_hash FROM files;")
       ...
   except Exception:
       try:
           rows = db_manager.read_query("SELECT path FROM files;")
           ...
       except Exception:
           pass
   ```
   O watcher ignora qualquer falha em bloco com `except Exception: pass`. O servidor sobe, loga que o watcher está ativo, mas o watcher não possui nenhum hash indexado em memória.

---

### Achado #4: A Ilusão dos Testes (The Test Mirage)

Por que a suíte de testes passa com 100% de sucesso?  
Porque 14 suítes de teste em `tests/` criam as tabelas localmente em suas rotinas `setUp()`:

- [`tests/test_delta_sync.py:70–77`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_delta_sync.py#L70-L77): Cria `files` e `communities`;
- [`tests/test_vector_reconciler.py:106–114`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L106-L114): Cria `files`;
- [`tests/test_graph_rag_janitor.py:78–92`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_janitor.py#L78-L92): Cria `files`, `communities` e `ast_edges`;
- [`tests/test_telemetry_api.py:38–46`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_telemetry_api.py#L38-L46): Cria `files` e `agent_checkpoints`;
- [`tests/test_mcp_server_extensions.py:134–145`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_extensions.py#L134-L145): Cria `agent_checkpoints` e `ast_edges`;
- [`tests/test_local_graph_rag_recursion.py:23–32`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_local_graph_rag_recursion.py#L23-L32): Cria `files` e `ast_edges`;
- [`tests/test_hsm_transition_hooks_and_delta.py:126–137`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py#L126-L137): Cria `fsm_checkpoints` e `files`;
- [`tests/test_graph_rag_loops.py:30–35`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_loops.py#L30-L35): Cria `ast_edges`;
- [`tests/test_hierarchical_state_machine.py:50–59`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hierarchical_state_machine.py#L50-L59): Cria `files` e `fsm_checkpoints`;
- [`tests/test_graph_rag_frugal.py:36–45`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_frugal.py#L36-L45): Cria `files` e `ast_edges`;
- [`tests/test_e2e_concierge_integration.py:199–220`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_e2e_concierge_integration.py#L199-L220): Cria `files`, `communities`, `ast_edges` e `agent_checkpoints`;
- [`tests/test_durable_checkpoints_timetravel.py:35–45`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_durable_checkpoints_timetravel.py#L35-L45): Cria `files` e `fsm_checkpoints`;
- [`tests/test_checkpoint_pruning.py:78–86`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_checkpoint_pruning.py#L78-L86): Cria `agent_checkpoints`;
- [`tests/test_alias_tracker.py:33–47`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_alias_tracker.py#L33-L47): Cria `files`, `ast_edges` e `fsm_checkpoints`.

Essa prática gerou uma **falsa sensação de integridade**: nenhum teste de ponta a ponta utilizava o caminho de bootstrap real de `main.py` e `storage/store.py` sem pré-injetar essas tabelas.

---

### Achado #5: Abandono da Especificação de Arquitetura

Na documentação do sistema ([`docs-grafo-concierge/01_ARCHITECTURE.md:130-170`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/01_ARCHITECTURE.md#L130-L170)), as 13 tabelas foram desenhadas e documentadas formalmente:

```sql
-- SURVIVAL & DELTA ENGINE TABLES (Fases 1, 2, 3 e 4)
-- 1. Files & Dual-Hash Delta Sync (SSH + LBH)
CREATE TABLE IF NOT EXISTS files (...);

-- 2. Communities & Frugal GraphRAG
CREATE TABLE IF NOT EXISTS communities (...);

-- 3. AST Call Graph Edges (Recursive CTE Table)
CREATE TABLE IF NOT EXISTS ast_edges (...);

-- 4. Agnostic State Checkpoints & Time-Travel Timeline
CREATE TABLE IF NOT EXISTS agent_checkpoints (...);
```

Porém, quando o autor escreveu `storage/schema.py`, ele copiou apenas o bloco subsequente:
`-- COGNITIVE GRAPH & FACT TABLES` (tabelas `projects`, `nodes`, `edges`, `reference_wings`, `trajectories`, `commit_log`, `user_core_memory`, `semantic_facts`).

As 4 tabelas de "SURVIVAL & DELTA ENGINE" foram ignoradas durante a consolidação do schema, e a tabela `fsm_checkpoints` foi isolada em `storage/relational_db.py` com uma função de inicialização inoperante (`init_fsm_checkpoints_schema`, documentada no Achado #4 de `audits/storage.md`).

---

## 4. Evidência Empírica Bruta de Terminal

Abaixo, a saída bruta da execução do script [`scratch/reproduce_schema_incompleto.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_schema_incompleto.py), comprovando o bootstrap em banco limpo e a falha imediata dos módulos de produção:

```text
[09/25/26 15:26:50] INFO     GrafoConciergeServer initialized mcp_server.py:233
                             - 31 tools registered.                            
                    INFO     Schema v3.8.0 verified - all tables   store.py:107
                             and triggers OK.                                  
                    INFO     SerializedWriteQueue started      connection.py:89
                             successfully (db: C:\Users\guial\AppData\Local\Temp\tmpek7j1lw8.db)                                  
                    INFO     SqliteStore initialized:               store.py:82
                             C:\Users\guial\AppData\Local\Temp\tmpek7j1lw8.db                                        
                    INFO     Requesting stop of               connection.py:105
                             SerializedWriteQueue...                           
                    INFO     SerializedWriteQueue finished.   connection.py:109
                    INFO     SqliteStore closed.                   store.py:114
================================================================================
ETAPA 1: SIMULACAO DE CLONE LIMPO E BOOTSTRAP OFICIAL
================================================================================
[1.1] Executando bootstrap oficial: SqliteStore('C:\Users\guial\AppData\Local\Temp\tmpek7j1lw8.db')...
[1.2] Tabelas criadas no banco pelo bootstrap oficial (14 encontradas):
     - commit_log
     - edges
     - nodes
     - nodes_fts
     - nodes_fts_config
     - nodes_fts_data
     - nodes_fts_docsize
     - nodes_fts_idx
     - projects
     - reference_wings
     - semantic_facts
     - sqlite_sequence
     - trajectories
     - user_core_memory

[1.3] Verificacao das 5 tabelas relacionais do subsistema core/*:
     - files               : NAO EXISTE (AUSENTE!)
     - communities         : NAO EXISTE (AUSENTE!)
     - ast_edges           : NAO EXISTE (AUSENTE!)
     - agent_checkpoints   : NAO EXISTE (AUSENTE!)
     - fsm_checkpoints     : NAO EXISTE (AUSENTE!)

     Total ausentes no bootstrap oficial: 5 de 5

[1.4] Testando conexao via ConciergeDatabaseManager(db_path)...
     Tabelas adicionadas por ConciergeDatabaseManager._init_tables(): ['test_log']
     - files               : CONTINUA AUSENTE!
     - communities         : CONTINUA AUSENTE!
     - ast_edges           : CONTINUA AUSENTE!
     - agent_checkpoints   : CONTINUA AUSENTE!
     - fsm_checkpoints     : CONTINUA AUSENTE!

================================================================================
ETAPA 2: OPERACOES REAIS DE CORE/* NO BANCO BOOTSTRAPADO
================================================================================

--- [2.1] core/vector_reconciler.py: VectorReconciler.reconcile_orphans() ---
  FALHA CONFIRMADA (OperationalError): no such table: files

--- [2.2] core/delta_manager.py: DeltaManager.process_file_change() ---
  FALHA CONFIRMADA (OperationalError): no such table: files

--- [2.3] core/checkpointer.py: AgnosticCheckpointer save / load / timetravel ---
  save_checkpoint retorno: False (Falso booleano: falha mascarada por core/database.py!)
  Escrita direta em agent_checkpoints: success=False, error='no such table: agent_checkpoints'
  load_checkpoint FALHA CONFIRMADA (OperationalError): no such table: fsm_checkpoints
  execute_time_travel FALHA CONFIRMADA (OperationalError): no such table: fsm_checkpoints

--- [2.4] core/background_janitor.py: BackgroundJanitor (Summarization & Pruning) ---
  Executando run_idle_summarization()...
  run_idle_summarization FALHA CONFIRMADA (OperationalError): no such table: communities
  Executando prune_session_checkpoints()...
  prune_session_checkpoints FALHA CONFIRMADA (OperationalError): no such table: agent_checkpoints

--- [2.5] core/graph_rag.py: GraphRAGEngine (detect_logical_communities & multihop & call chain) ---
  Executando detect_logical_communities()...
  detect_logical_communities FALHA CONFIRMADA (OperationalError): no such table: ast_edges
  Executando retrieve_multihop_context('core/example.py')...
  retrieve_multihop_context: {'entry': 'core/example.py', 'nodes': [], 'edges': [], 'error': 'no such table: ast_edges'}
  Executando get_call_chain_recursive('core/example.py')...
  get_call_chain_recursive FALHA CONFIRMADA (OperationalError): no such table: ast_edges

--- [2.6] core/search_engine.py: HybridSearchEngine.hybrid_search() ---
  hybrid_search FALHA CONFIRMADA (OperationalError): no such table: files

--- [2.7] interface/telemetry_api.py: get_telemetry_snapshot() ---
  get_telemetry_snapshot FALHA CONFIRMADA (OperationalError): no such table: files

--- [2.8] interface/watcher.py: ConciergeFileSystemHandler.hydrate_known_hashes() ---
  Chamando hydrate_known_hashes(db_manager)...
  Hashes hidratados: 0 (deveria ler 'files', mas silenciou erro!)
  Query real do watcher FALHA CONFIRMADA (OperationalError): no such table: files

--- [2.9] interface/mcp_server.py: MCP Tools (agent_save_checkpoint & concierge_get_call_chain) ---
  Executando tool agent_save_checkpoint...
  agent_save_checkpoint retorno bruto: {"success": false, "message": "Failed to save checkpoint 'chk_mcp' for agent 'test_agent'"}
  Executando tool concierge_get_call_chain...
  concierge_get_call_chain FALHA CONFIRMADA (OperationalError): no such table: ast_edges

--- [2.10] IngestionManager.mine vs DeltaManager no banco bootstrapado ---
  Projeto criado com sucesso em 'projects': {'uuid': 'test_proj', 'folder_name': 'geral', 'primary_wing': 'geral', 'privacy_level': 'PUBLIC'}
  DeltaManager FALHA CONFIRMADA (OperationalError): no such table: files

================================================================================
ETAPA 3: VARREDURA EXAUSTIVA DE DDL NO CODIGO DE PRODUCAO
================================================================================
Todas as ocorrencias de 'CREATE TABLE' em codigo de producao (10 encontradas):
  [core\database.py:35] "CREATE TABLE IF NOT EXISTS test_log ("
  [storage\relational_db.py:14] CREATE TABLE IF NOT EXISTS fsm_checkpoints (
  [storage\schema.py:52] CREATE TABLE IF NOT EXISTS projects (
  [storage\schema.py:63] CREATE TABLE IF NOT EXISTS nodes (
  [storage\schema.py:82] CREATE TABLE IF NOT EXISTS edges (
  [storage\schema.py:94] CREATE TABLE IF NOT EXISTS reference_wings (
  [storage\schema.py:100] CREATE TABLE IF NOT EXISTS trajectories (
  [storage\schema.py:112] CREATE TABLE IF NOT EXISTS commit_log (
  [storage\schema.py:123] CREATE TABLE IF NOT EXISTS user_core_memory (
  [storage\schema.py:133] CREATE TABLE IF NOT EXISTS semantic_facts (

Conclusao da varredura:
  1. storage/schema.py cria: projects, nodes, edges, reference_wings, trajectories, commit_log, user_core_memory, semantic_facts, nodes_fts.
  2. storage/relational_db.py define fsm_checkpoints, mas init_fsm_checkpoints_schema nunca e chamado.
  3. core/database.py cria apenas test_log.
  4. NENHUM arquivo de producao cria: files, communities, ast_edges, agent_checkpoints.
  5. Nao existe geracao dinamica, lazy ou via ORM.
```

---

## 5. Recomendações para o Backlog da Fase 3

1. **Unificação Integral do Schema em `storage/schema.py`**:
   - Incorporar imediatamente no bloco `TABLES_SQL` de `storage/schema.py` as DDLs completas das 5 tabelas faltantes conforme especificadas em `01_ARCHITECTURE.md`:
     - `files` (`path PRIMARY KEY`, `content`, `ssh_hash`, `body_hash`, `is_dirty`, `community_id`, `last_modified`);
     - `communities` (`id PRIMARY KEY`, `summary_text`, `is_dirty`);
     - `ast_edges` (`parent_node`, `child_node`, `UNIQUE(parent_node, child_node)`);
     - `agent_checkpoints` (`agent_id`, `session_id`, `checkpoint_id`, `state_blob`, `created_at`, `PRIMARY KEY (agent_id, session_id, checkpoint_id)`);
     - `fsm_checkpoints` (`checkpoint_id`, `session_id`, `agent_id`, `task_id`, `state_name`, `shared_state_blob`, `created_at`, `PRIMARY KEY (session_id, checkpoint_id)`).
   - Atualizar `verify_tables_exist()` em `storage/schema.py` para incluir as 5 novas tabelas no rol obrigatório.
2. **Eliminação do Silo Duplicado de Banco**:
   - Deprecar `core/database.py::ConciergeDatabaseManager` e apontar todos os módulos de `core/` para utilizarem a fachada unificada `SqliteStore` através de sua fila de conexão serializada `storage/connection.py::SerializedWriteQueue`.
3. **Limpeza das Fixtures de Teste (`tests/`)**:
   - Remover as injeções manuais de DDL em `setUp()` das 14 suítes de teste, garantindo que os testes utilizem unicamente o `SchemaManager.apply_full_schema()` oficial.
4. **Remoção de Silenciamento de Erros**:
   - Ajustar `core/database.py` e `interface/watcher.py` para que falhas de SQL (especialmente `OperationalError`) sejam propagadas ou registradas em nível `CRITICAL` / `ERROR`, proibindo o mascaramento com `except Exception: pass`.
