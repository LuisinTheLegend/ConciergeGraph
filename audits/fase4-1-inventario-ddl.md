# Inventário de DDLs e Proposta de Schema Canônico (Rodada 4.1 / Passo A)

> **Documento Normativo de Auditoria e Design Técnico**  
> **Fase:** Fase 4 — Correções de Código | **Rodada:** 4.1 | **Passo:** A (Inventário e Análise)  
> **Backlog Referenciado:** [`BL-001`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L159), [`BL-002`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L166), [`BL-003`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L175), [`BL-004`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L183)  
> **Data:** 15/10/2026  
> **Regras Normativas:** Regras 2, 3, 4, 7, 10, 11 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Status:** AGUARDANDO DECISÃO HUMANA NO GATE (Nenhum código de produção ou teste foi alterado nesta rodada)

---

## 1. Contexto e Objetivo

O diagnóstico das Fases 1, 2 e 3 comprovou que o banco de dados oficial do sistema (`storage/schema.py`) define apenas 8 tabelas de negócio (`projects`, `nodes`, `edges`, `reference_wings`, `trajectories`, `commit_log`, `user_core_memory`, `semantic_facts`) e uma tabela virtual (`nodes_fts`). Cinco tabelas vitais para a operação dos motores analíticos e de sobrevivência (`files`, `communities`, `ast_edges`, `agent_checkpoints`, `fsm_checkpoints`) **não são criadas no boot de produção**.

Enquanto 12 subsistemas de produção falham em instalação limpa ([`BL-002`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L166)), 17 suítes de teste criavam suas próprias variantes dessas tabelas privadamente em seus métodos `setUp()` ([`BL-003`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L175)), mascarando os bugs e introduzindo severas discrepâncias de nomes de coluna, tipos e restrições.

Este inventário estabelece as evidências completas para a unificação definitiva do schema em `storage/schema.py` no Passo B.

---

## 2. Linha de Base de Testes (Passo 2)

Em conformidade com a Regra 2 da Fase 4, foi executada a suíte de testes completa em clone limpo antes de qualquer alteração de código.

- **Comando executado:** `python -m pytest tests/ -q`
- **Ambiente:** Python 3.14.0a4, pytest-8.3.4, pluggy-1.5.0, Windows 11
- **Arquivo de registro integral:** [`scratch/baseline_fase4_20261015.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/baseline_fase4_20261015.txt)
- **Itens coletados:** 337
- **Resultado consolidado:**
  - **Passed:** 335
  - **Failed:** 1 (`tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints`)
  - **Skipped:** 1
  - **Warnings:** 20
  - **Tempo de execução:** 183.08s (03:03)

### Detalhe da Única Falha na Linha de Base:
A falha em `test_progressive_tool_disclosure.py:90` decorre de `AssertionError: 'EXECUTION' != 'PLANNING'`, falha pré-existente documentada e catalogada no backlog sob o item [`BL-015`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L309) (Track 3 / Dessincronização do estado inicial do MCPToolGovernor).

---

## 3. Fontes Existentes de DDL (Passo 3a)

### 3a.1 Código de Produção
No código de produção sob `core/`, `interface/`, `storage/`, `ingestion/`, `agent/`, `agents/` e `services/`, **existe apenas uma única instrução DDL** para qualquer uma das 5 tabelas:

- **Arquivo:** [`storage/relational_db.py:14-23`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py#L14-L23)
```sql
CREATE TABLE IF NOT EXISTS fsm_checkpoints (
    checkpoint_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,
    state_name TEXT NOT NULL,
    shared_state_blob TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, checkpoint_id)
);
```

#### Comprovação de Ausência de Importadores (Código Órfão):
Execução literal de busca global por importadores de `storage/relational_db.py`:
```powershell
git grep -n -E "relational_db|FSM_CHECKPOINTS_TABLE_SQL|init_fsm_checkpoints_schema"
```
**Resultado da busca:**
- `storage/relational_db.py`: definição das constantes e da função `init_fsm_checkpoints_schema`.
- `audits/storage.md`: achado #4 da auditoria documentando o isolamento.
- `docs-grafo-concierge/01_ARCHITECTURE.md`: especificação teórica.
- `scratch/reproduce_storage_findings.py`: script efêmero de teste de auditoria.
- **Produção (`core/`, `interface/`, `storage/`, `ingestion/`, `services/`):** **ZERO importadores.**
- **Testes (`tests/`):** **ZERO importadores.**

Nenhum arquivo de produção ou teste importa `storage/relational_db.py`. Trata-se de código completamente órfão e desconectado da fachada oficial [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) ([`BL-019`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L349)).

### 3a.2 Omissão em `storage/schema.py`
A fachada oficial de banco de dados [`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) (`SchemaManager.apply_full_schema()`) e o dicionário `TABLES_SQL` **não contêm nenhuma instrução DDL** para:
- `files`
- `communities`
- `ast_edges`
- `agent_checkpoints`
- `fsm_checkpoints`

---

## 4. Matriz de Variantes nos Testes (Passo 3b)

Foram identificadas **17 suítes de teste** contendo declarações privadas de `CREATE TABLE IF NOT EXISTS` em seus métodos `setUp()`. Abaixo apresenta-se a matriz detalhada por tabela, evidenciando as divergências arquiteturais entre elas.

### 4b.1 Tabela `files` (13 suítes, 14 declarações de DDL)

| Arquivo de Teste | Linha | Colunas Declaradas | Chave Primária | Defaults | Divergência em Relação a Produção / Arquitetura |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_agent_hsm_coupling.py` | 33 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_alias_tracker.py` | 33 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_cognitive_routing_memory.py` | 41 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_delta_sync.py` | 70 | `path TEXT, content TEXT, ssh_hash TEXT, body_hash TEXT, is_dirty INTEGER, community_id TEXT` | `path` | Nenhum | **Omite `last_modified`** |
| `tests/test_durable_checkpoints_timetravel.py` | 35 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_e2e_concierge_integration.py` | 199 | `path TEXT, content TEXT, ssh_hash TEXT, body_hash TEXT, is_dirty INTEGER, community_id TEXT` | `path` | Nenhum | **Omite `last_modified`** |
| `tests/test_graph_rag_frugal.py` | 36 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_graph_rag_janitor.py` | 78 | `path TEXT, content TEXT, is_dirty INTEGER, community_id TEXT` | `path` | Nenhum | Omite `ssh_hash`, `body_hash`, `last_modified` |
| `tests/test_hierarchical_state_machine.py` | 50 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_hsm_transition_hooks_and_delta.py` | 133 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_hsm_transition_hooks_and_delta.py` | 302 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_local_graph_rag_recursion.py` | 23 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_telemetry_api.py` | 38 | `path TEXT, community_id TEXT, is_dirty INTEGER, last_modified REAL` | `path` | Nenhum | Omite `content`, `ssh_hash`, `body_hash` |
| `tests/test_vector_reconciler.py` | 106 | `path TEXT, content TEXT, ssh_hash TEXT, is_dirty INTEGER, community_id TEXT` | `path` | Nenhum | Omite `body_hash`, `last_modified` |

**Divergência Central em `files`:**
Existem dois grupos incompatíveis de testes:
1. **Grupo Operacional/Checkpoints (10 declarações):** focado em `{path, community_id, is_dirty, last_modified}`.
2. **Grupo Ingestão/Delta (4 declarações):** focado em hashes e conteúdo `{path, content, ssh_hash, body_hash, is_dirty, community_id}`, mas ignorando `last_modified`.

---

### 4b.2 Tabela `communities` (3 suítes)

| Arquivo de Teste | Linha | Colunas Declaradas | Chave Primária | Defaults | Divergência |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_delta_sync.py` | 76 | `id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER` | `id` | Nenhum | Nenhuma (100% de convergência) |
| `tests/test_e2e_concierge_integration.py` | 205 | `id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER` | `id` | Nenhum | Nenhuma (100% de convergência) |
| `tests/test_graph_rag_janitor.py` | 83 | `id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER` | `id` | Nenhum | Nenhuma (100% de convergência) |

**Conclusão sobre `communities`:** Convergência unânime em testes e produção quanto a `(id, summary_text, is_dirty)`.

---

### 4b.3 Tabela `ast_edges` (7 suítes)

| Arquivo de Teste | Linha | Colunas Declaradas | Chave Primária / Constraint | Divergência |
| :--- | :--- | :--- | :--- | :--- |
| `tests/test_alias_tracker.py` | 38 | `parent_node_id TEXT, child_node_id TEXT` | Nenhuma constraint | Usa sufixo `_id`, sem `UNIQUE` |
| `tests/test_e2e_concierge_integration.py` | 210 | `parent_node TEXT, child_node TEXT` | `UNIQUE(parent_node, child_node)` | Nomes canônicos `parent_node`, `child_node` |
| `tests/test_graph_rag_frugal.py` | 41 | `parent_node TEXT, child_node TEXT` | `UNIQUE(parent_node, child_node)` | Nomes canônicos `parent_node`, `child_node` |
| `tests/test_graph_rag_janitor.py` | 88 | `parent_node TEXT, child_node TEXT` | `UNIQUE(parent_node, child_node)` | Nomes canônicos `parent_node`, `child_node` |
| `tests/test_graph_rag_loops.py` | 30 | `parent_node TEXT, child_node TEXT` | `UNIQUE(parent_node, child_node)` | Nomes canônicos `parent_node`, `child_node` |
| `tests/test_local_graph_rag_recursion.py` | 28 | `parent_node_id TEXT, child_node_id TEXT` | Nenhuma constraint | Usa sufixo `_id`, sem `UNIQUE` |
| `tests/test_mcp_server_extensions.py` | 141 | `parent_node TEXT, child_node TEXT` | `UNIQUE(parent_node, child_node)` | Nomes canônicos `parent_node`, `child_node` |

**Divergência Central em `ast_edges`:**
- 5 suítes adotam `parent_node` e `child_node` com `UNIQUE(parent_node, child_node)`.
- 2 suítes (`test_alias_tracker.py` e `test_local_graph_rag_recursion.py`) adotam `parent_node_id` e `child_node_id` sem constraint de unicidade.

---

### 4b.4 Tabela `agent_checkpoints` (5 suítes)

| Arquivo de Teste | Linha | Colunas Declaradas | Chave Primária | Defaults | Divergência |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_agent_checkpointer.py` | 69 | `agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, created_at TIMESTAMP` | `(agent_id, session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Formato padrão de produção |
| `tests/test_checkpoint_pruning.py` | 78 | `agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, created_at TIMESTAMP` | `(agent_id, session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Formato padrão de produção |
| `tests/test_e2e_concierge_integration.py` | 215 | `agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, created_at TIMESTAMP` | `(agent_id, session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Formato padrão de produção |
| `tests/test_mcp_server_extensions.py` | 134 | `agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, created_at TIMESTAMP` | `(agent_id, session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Formato padrão de produção |
| `tests/test_telemetry_api.py` | 43 | `id INTEGER, agent_id TEXT, session_id TEXT, checkpoint_id TEXT, timestamp REAL` | `id AUTOINCREMENT` | Nenhum | **Grave anomalia: usa PK autoincrement, omite `state_blob` e renomeia `created_at` para `timestamp REAL`** |

**Divergência Central em `agent_checkpoints`:**
`test_telemetry_api.py` diverge totalmente da arquitetura do `AgnosticCheckpointer`, substituindo a chave primária composta de negócio por uma surrogate key e alterando o nome e o tipo do campo temporal de `created_at TIMESTAMP` para `timestamp REAL`.

---

### 4b.5 Tabela `fsm_checkpoints` (6 suítes)

| Arquivo de Teste | Linha | Colunas Declaradas | Chave Primária | Defaults | Divergência |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_agent_hsm_coupling.py` | 38 | `checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP` | `(session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Idêntico a `storage/relational_db.py` |
| `tests/test_alias_tracker.py` | 43 | `checkpoint_id TEXT, task_id TEXT, state_name TEXT` | `checkpoint_id` | Nenhum | Stub minimalista, omite colunas NOT NULL |
| `tests/test_durable_checkpoints_timetravel.py` | 40 | `checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP` | `(session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Idêntico a `storage/relational_db.py` |
| `tests/test_hierarchical_state_machine.py` | 55 | `checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP` | `(session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Idêntico a `storage/relational_db.py` |
| `tests/test_hsm_transition_hooks_and_delta.py` | 126 | `checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP` | `(session_id, checkpoint_id)` | `CURRENT_TIMESTAMP` | Idêntico a `storage/relational_db.py` |
| `tests/test_hsm_transition_hooks_and_delta.py` | 295 | `checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, shared_state_blob TEXT, task_id TEXT, created_at REAL` | `(session_id, checkpoint_id)` | Nenhum | **Declara `created_at REAL` (timestamp numérico)** |

**Divergência Central em `fsm_checkpoints`:**
A divergência crítica reside no tipo de dado de `created_at`:
- `storage/relational_db.py` e 4 testes usam `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (string ISO).
- `test_hsm_transition_hooks_and_delta.py:295` usa `REAL` (segundos epoch float).
- `core/hsm_engine.py:457` faz `if file_mtime > float(created_at):`, exigindo que `created_at` seja conversível para float.

---

## 5. Colunas Realmente Usadas em Produção (Passo 3c)

Mapeamento exato de todos os comandos SQL executados pelos módulos de produção em `core/`, `interface/`, `storage/`, `ingestion/`, `agent/`, `agents/` e `services/`:

### 5c.1 Tabela `files`
- [`core/alias_tracker.py:216`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L216): `UPDATE files SET path = ?, last_modified = ?, is_dirty = 1 WHERE path = ?;`  
  *(Colunas: `path`, `last_modified`, `is_dirty`)*
- [`core/background_janitor.py:97`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L97): `SELECT content FROM files WHERE community_id = ?;`  
  *(Colunas: `content`, `community_id`)*
- [`core/background_janitor.py:111`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L111): `UPDATE files SET is_dirty = 0 WHERE community_id = ?;`  
  *(Colunas: `is_dirty`, `community_id`)*
- [`core/background_janitor.py:240`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L240): `SELECT MAX(last_modified) FROM files;`  
  *(Colunas: `last_modified`)*
- [`core/checkpointer.py:201`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L201): `UPDATE files SET is_dirty = 1, last_modified = ? WHERE path = ?;`  
  *(Colunas: `is_dirty`, `last_modified`, `path`)*
- [`core/delta_manager.py:134`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L134): `SELECT ssh_hash, body_hash FROM files WHERE path = ?;`  
  *(Colunas: `ssh_hash`, `body_hash`, `path`)*
- [`core/delta_manager.py:183`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L183): `SELECT content FROM files WHERE community_id = ?;`  
  *(Colunas: `content`, `community_id`)*
- [`core/delta_manager.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L196): `UPDATE files SET is_dirty = 0 WHERE community_id = ?;`  
  *(Colunas: `is_dirty`, `community_id`)*
- [`core/delta_manager.py:214`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L214): `INSERT INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) VALUES (?, ?, ?, ?, 1, ?);`  
  *(Colunas: `path`, `content`, `ssh_hash`, `body_hash`, `is_dirty`, `community_id` — **Nota: omite `last_modified`**)*
- [`core/delta_manager.py:232`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L232): `UPDATE files SET content = ?, is_dirty = 0 WHERE path = ?;`  
  *(Colunas: `content`, `is_dirty`, `path`)*
- [`core/delta_manager.py:237`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L237): `SELECT COUNT(*) FROM files WHERE community_id = ? AND is_dirty = 1;`  
  *(Colunas: `community_id`, `is_dirty`)*
- [`core/delta_manager.py:257`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L257): `UPDATE files SET content = ?, ssh_hash = ?, body_hash = ?, is_dirty = 1 WHERE path = ?;`  
  *(Colunas: `content`, `ssh_hash`, `body_hash`, `is_dirty`, `path`)*
- [`core/graph_rag.py:56`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L56): `SELECT path, community_id, is_dirty FROM files WHERE path = ?;`  
  *(Colunas: `path`, `community_id`, `is_dirty`)*
- [`core/graph_rag.py:126`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L126): `SELECT path, community_id, is_dirty FROM files WHERE path IN (...);`  
  *(Colunas: `path`, `community_id`, `is_dirty`)*
- [`core/graph_rag.py:246`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L246): `SELECT path FROM files;`  
  *(Colunas: `path`)*
- [`core/intent_classifier.py:62`](file:///c:/Nexus-Memory/GrafoConcierge/core/intent_classifier.py#L62): `SELECT COUNT(*) FROM files WHERE ...;`  
  *(Colunas: `path`)*
- [`core/search_engine.py:58`](file:///c:/Nexus-Memory/GrafoConcierge/core/search_engine.py#L58): `SELECT path FROM files WHERE path IN (...);`  
  *(Colunas: `path`)*
- [`core/vector_reconciler.py:54`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py#L54): `SELECT path FROM files;`  
  *(Colunas: `path`)*
- [`interface/telemetry_api.py:154`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L154): `SELECT COUNT(*) FROM files;`  
- [`interface/telemetry_api.py:160`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L160): `SELECT path, community_id, last_modified FROM files WHERE is_dirty = 1;`  
  *(Colunas: `path`, `community_id`, `last_modified`, `is_dirty`)*
- [`interface/watcher.py:86`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L86): `SELECT path, structural_hash FROM files;`  
  *(Colunas: `path`, `structural_hash`)*
- [`interface/watcher.py:95`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L95): `SELECT path FROM files;`  
- [`interface/watcher.py:208`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L208): `SELECT structural_hash FROM files WHERE path = ? LIMIT 1;`  
  *(Colunas: `structural_hash`, `path`)*

> [!WARNING]
> **DESTAQUE DE COLUNA NÃO EXISTENTE NOS TESTES (`structural_hash`):**  
> A coluna `structural_hash` é consultada em duas rotinas críticas de detecção de deltas em [`interface/watcher.py:86`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L86) e [`interface/watcher.py:208`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L208), mas **NÃO EXISTE em nenhuma das 14 declarações de DDL nos testes** e **NUNCA é inserida por `delta_manager.py`** (que persiste `ssh_hash` e `body_hash`). Se `structural_hash` for consultada num banco canônico sem ela, o `watcher.py` falhará com `sqlite3.OperationalError: no such column: structural_hash`. Esta discrepância é submetida abaixo como **DECISÃO HUMANA 1**.

---

### 5c.2 Tabela `communities`
- [`core/background_janitor.py:79`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L79): `SELECT id FROM communities WHERE is_dirty = 1;`  
  *(Colunas: `id`, `is_dirty`)*
- [`core/background_janitor.py:107`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L107): `UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;`  
  *(Colunas: `summary_text`, `is_dirty`, `id`)*
- [`core/delta_manager.py:169`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L169): `SELECT is_dirty, summary_text FROM communities WHERE id = ?;`  
  *(Colunas: `is_dirty`, `summary_text`, `id`)*
- [`core/delta_manager.py:192`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L192): `UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;`  
  *(Colunas: `summary_text`, `is_dirty`, `id`)*
- [`core/delta_manager.py:219`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L219): `UPDATE communities SET is_dirty = 1 WHERE id = ?;`  
  *(Colunas: `is_dirty`, `id`)*
- [`core/delta_manager.py:242`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L242): `UPDATE communities SET is_dirty = 0 WHERE id = ?;`  
  *(Colunas: `is_dirty`, `id`)*
- [`core/delta_manager.py:262`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L262): `UPDATE communities SET is_dirty = 1 WHERE id = ?;`  
  *(Colunas: `is_dirty`, `id`)*

**Conclusão sobre `communities`:** 100% das referências utilizam exatamente as colunas `(id, summary_text, is_dirty)`.

---

### 5c.3 Tabela `ast_edges`
- [`core/alias_tracker.py:228, 232`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L228): `UPDATE ast_edges SET {parent_col} = ? WHERE {parent_col} = ?;` / `UPDATE ast_edges SET {child_col} = ? WHERE {child_col} = ?;`  
  *(Detecta dinamicamente via PRAGMA se as colunas são `parent_node` ou `parent_node_id`)*
- [`core/graph_rag.py:84, 94`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L84): Query recursiva em `retrieve_multihop_context`: usa `{parent_col}` e `{child_col}` resolvidos dinamicamente por `_get_edge_columns()`.
- [`core/graph_rag.py:179, 180`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L179): `WITH RECURSIVE call_chain ... FROM ast_edges e JOIN call_chain cc ON e.parent_node = cc.node ... SELECT e.child_node AS node`  
  *(**HARDCODED** para `parent_node` e `child_node`)*
- [`core/graph_rag.py:209, 210`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L209): `SELECT child_node, COUNT(*) as in_degree FROM ast_edges GROUP BY child_node HAVING in_degree > ?;`  
  *(**HARDCODED** para `child_node`)*
- [`core/graph_rag.py:219`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L219): `SELECT parent_node, child_node FROM ast_edges;`  
  *(**HARDCODED** para `parent_node` e `child_node`)*

> [!IMPORTANT]
> **EVIDÊNCIA TÉCNICA CRÍTICA EM `ast_edges`:**  
> Embora `alias_tracker.py` e `retrieve_multihop_context()` tentem inspecionar o schema dinamicamente, os métodos [`detect_logical_communities()`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L209) e [`get_call_chain()`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L179) possuem consultas SQL com `parent_node` e `child_node` **estritamente hardcoded**. A utilização dos nomes `parent_node_id` / `child_node_id` causa crash imediato em `detect_logical_communities()`.

---

### 5c.4 Tabela `agent_checkpoints`
- [`core/background_janitor.py:143`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L143): `SELECT DISTINCT session_id FROM agent_checkpoints;`  
  *(Colunas: `session_id`)*
- [`core/background_janitor.py:161`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L161): `SELECT checkpoint_id FROM agent_checkpoints WHERE session_id = ? ORDER BY created_at ASC;`  
  *(Colunas: `checkpoint_id`, `session_id`, `created_at`)*
- [`core/background_janitor.py:194`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L194): `DELETE FROM agent_checkpoints WHERE session_id = ? AND checkpoint_id IN (...);`  
  *(Colunas: `session_id`, `checkpoint_id`)*
- [`core/checkpointer.py:139`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L139): `INSERT OR REPLACE INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob) VALUES (?, ?, ?, ?);`  
  *(Colunas: `agent_id`, `session_id`, `checkpoint_id`, `state_blob` — exige chave primária composta `(agent_id, session_id, checkpoint_id)` para semântica de substituição idempotente)*
- [`core/checkpointer.py:227`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L227): `SELECT state_blob FROM agent_checkpoints WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ?;`  
  *(Colunas: `state_blob`, `agent_id`, `session_id`, `checkpoint_id`)*
- [`core/checkpointer.py:247`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L247): `SELECT checkpoint_id, created_at FROM agent_checkpoints WHERE agent_id = ? AND session_id = ? ORDER BY created_at ASC;`  
  *(Colunas: `checkpoint_id`, `created_at`, `agent_id`, `session_id`)*
- [`interface/telemetry_api.py:183`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L183): `SELECT agent_id, session_id, checkpoint_id, timestamp FROM agent_checkpoints ORDER BY timestamp ASC;`  
  *(**Colisão de nome de coluna**: consulta `timestamp` em vez de `created_at`)*

---

### 5c.5 Tabela `fsm_checkpoints`
- [`core/alias_tracker.py:239`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L239): `UPDATE fsm_checkpoints SET task_id = ? WHERE task_id = ?;`  
  *(Colunas: `task_id`)*
- [`core/checkpointer.py:105`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L105): `INSERT INTO fsm_checkpoints (checkpoint_id, session_id, agent_id, state_name, shared_state_blob, task_id) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(session_id, checkpoint_id) DO UPDATE SET state_name = excluded.state_name, shared_state_blob = excluded.shared_state_blob, task_id = excluded.task_id;`  
  *(Colunas: `checkpoint_id`, `session_id`, `agent_id`, `state_name`, `shared_state_blob`, `task_id`)*
- [`core/checkpointer.py:152`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L152): `SELECT state_name, shared_state_blob, agent_id, task_id FROM fsm_checkpoints WHERE session_id = ? AND checkpoint_id = ?;`  
  *(Colunas: `state_name`, `shared_state_blob`, `agent_id`, `task_id`, `session_id`, `checkpoint_id`)*
- [`core/checkpointer.py:187`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L187): `SELECT created_at, task_id FROM fsm_checkpoints WHERE session_id = ? AND checkpoint_id = ?;`  
  *(Colunas: `created_at`, `task_id`, `session_id`, `checkpoint_id`)*
- [`core/checkpointer.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L196): `DELETE FROM fsm_checkpoints WHERE session_id = ? AND created_at > ?;`  
  *(Colunas: `session_id`, `created_at`)*
- [`core/hsm_engine.py:421`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L421): `SELECT checkpoint_id, state_name, created_at, task_id FROM fsm_checkpoints WHERE session_id = ? ORDER BY created_at DESC LIMIT 1;`  
  *(Colunas: `checkpoint_id`, `state_name`, `created_at`, `task_id`, `session_id`)*
- [`core/hsm_engine.py:457`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L457): `if file_mtime > float(created_at):`  
  *(Exige valor conversível para float, gerando exceção se contiver string ISO padrão `YYYY-MM-DD HH:MM:SS`)*
- [`interface/telemetry_api.py:306`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L306): `SELECT checkpoint_id, state_name, task_id, created_at FROM fsm_checkpoints WHERE session_id = ? ORDER BY created_at ASC;`  
  *(Colunas: `checkpoint_id`, `state_name`, `task_id`, `created_at`, `session_id`)*

---

## 6. Proposta de DDL Canônico e Decisões Humanas no Gate (Passo 3d)

Com base nas evidências levantadas e nas diretrizes consolidadas pelo [`01_ARCHITECTURE.md`](file:///c:/Nexus-Memory/GrafoConcierge/docs-grafo-concierge/01_ARCHITECTURE.md), formula-se a proposta canônica para as 5 tabelas a serem integradas em `storage/schema.py:TABLES_SQL`:

### 6.1 Tabela `files` (Proposta Base)
```sql
CREATE TABLE IF NOT EXISTS files (
    path            TEXT PRIMARY KEY,
    content         TEXT,
    ssh_hash        TEXT,
    body_hash       TEXT,
    is_dirty        INTEGER NOT NULL DEFAULT 1,
    community_id    TEXT,
    last_modified   REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_community_id ON files(community_id);
```
- **Justificativa:** Unifica o conjunto de colunas exigido por `DeltaManager` (`content`, `ssh_hash`, `body_hash`), `BackgroundJanitor` (`content`, `community_id`), `GraphRAG` (`path`, `community_id`, `is_dirty`) e `TelemetryAPI` (`last_modified`). O índice `idx_files_community_id` atende expressamente à diretriz do BL-001.

> [!CAUTION]
> #### DECISÃO HUMANA 1: Coluna `structural_hash` em `files`
> - **Situação:** `interface/watcher.py:86, 208` executa `SELECT path, structural_hash FROM files;` e `SELECT structural_hash FROM files WHERE path = ? LIMIT 1;`. Porém, nem `delta_manager.py` nem nenhuma suíte de teste usa `structural_hash` (usam `ssh_hash` e `body_hash`).
> - **Alternativa A (Recomendada):** Adicionar `structural_hash TEXT` na tabela `files` no DDL canônico.
>   - *Prós:* Evita erro de schema (`no such column: structural_hash`) imediatamente no `watcher.py` sem exigir edição de código de produção na Track 1. Na Track 4, `watcher.py` pode ser alinhado a `ssh_hash`.
>   - *Contras:* Mantém temporariamente uma coluna redundante no schema até o refatoramento do watcher.
> - **Alternativa B:** Não incluir `structural_hash` no DDL e registrar no backlog que `interface/watcher.py` precisa ser alterado para consultar `ssh_hash`.
>   - *Prós:* Schema canônico 100% puro alinhado com `01_ARCHITECTURE.md`.
>   - *Contras:* `watcher.py` falhará caso seja executado antes da Track 4.

> [!CAUTION]
> #### DECISÃO HUMANA 2: Default e Tipo de `last_modified` em `files`
> - **Situação:** `delta_manager.py:214` faz `INSERT INTO files` omitindo `last_modified`. Se inserido como `NULL`, `telemetry_api.py:160` gera exceção de tipo (`datetime.fromtimestamp(None)`).
> - **Alternativa A (Recomendada):** `last_modified REAL DEFAULT (strftime('%s', 'now'))` ou `REAL DEFAULT 0.0`.
>   - *Prós:* Garante que novos arquivos inseridos pelo `delta_manager` tenham um valor numérico válido, blindando a telemetria contra crashes por `NoneType`.
>   - *Contras:* Sobrescreve um mtime não informado com o timestamp da inserção.
> - **Alternativa B:** `last_modified REAL DEFAULT NULL` e corrigir `telemetry_api.py` para tratar `None` (já previsto no BL-067).
>   - *Prós:* Não mascara a ausência do mtime real do arquivo no disco.
>   - *Contras:* Depende da correção de código em outra Track para não falhar a telemetria.

---

### 6.2 Tabela `communities` (Proposta Base)
```sql
CREATE TABLE IF NOT EXISTS communities (
    id              TEXT PRIMARY KEY,
    summary_text    TEXT,
    is_dirty        INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_communities_id ON communities(id);
```
- **Justificativa:** 100% convergente entre as 3 suítes de teste, `DeltaManager`, `BackgroundJanitor` e especificação arquitetural `01_ARCHITECTURE.md:147`.
- **Nota sobre BL-001 ("índice para communities.community_id"):** Na tabela `communities`, o identificador primário é `id`. A referência a `community_id` no BL-001 diz respeito à chave estrangeira/associação presente em `files(community_id)`, que é contemplada pelo índice `idx_files_community_id` proposto na Seção 6.1. O índice explícito `idx_communities_id` (ou a própria PK) cobre as buscas primárias.

---

### 6.3 Tabela `ast_edges` (Proposta Base)
```sql
CREATE TABLE IF NOT EXISTS ast_edges (
    parent_node     TEXT NOT NULL,
    child_node      TEXT NOT NULL,
    UNIQUE(parent_node, child_node)
);

CREATE INDEX IF NOT EXISTS idx_ast_edges_parent ON ast_edges(parent_node);
CREATE INDEX IF NOT EXISTS idx_ast_edges_child ON ast_edges(child_node);
```
- **Justificativa:** Suportada pela especificação arquitetural `01_ARCHITECTURE.md:154`, por 5 suítes de teste e exigida impreterivelmente pelas queries hardcoded em [`core/graph_rag.py:179, 209, 219`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L209).

> [!CAUTION]
> #### DECISÃO HUMANA 3: Nomenclatura das Colunas de `ast_edges`
> - **Situação:** 5 suítes e o núcleo analítico de `GraphRAG` usam `parent_node, child_node`. No entanto, 2 suítes (`test_alias_tracker.py` e `test_local_graph_rag_recursion.py`) usam `parent_node_id, child_node_id`.
> - **Alternativa A (Recomendada):** Consolidar `(parent_node, child_node)`.
>   - *Prós:* Garante que `core/graph_rag.py:detect_logical_communities()` e `get_call_chain()` funcionem sem crash. As 2 suítes divergentes serão ajustadas na Fase 4 (Track 1) ao remover seus DDLs privados.
>   - *Contras:* Exige ajuste nas 2 suítes que fazem `INSERT INTO ast_edges (parent_node_id, child_node_id)`.
> - **Alternativa B:** Adicionar colunas geradas ou criar uma VIEW / aliases no SQLite (ou 4 colunas).
>   - *Prós:* Compatibilidade temporária dupla.
>   - *Contras:* Complexidade desnecessária e poluição arquitetural do schema relacional.

---

### 6.4 Tabela `agent_checkpoints` (Proposta Base)
```sql
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    agent_id        TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    checkpoint_id   TEXT NOT NULL,
    state_blob      TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timestamp       REAL DEFAULT 0.0,
    PRIMARY KEY (agent_id, session_id, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_session ON agent_checkpoints(session_id);
```
- **Justificativa:** A chave primária composta `(agent_id, session_id, checkpoint_id)` é estritamente mandatória para o funcionamento de [`core/checkpointer.py:139`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L139) (`INSERT OR REPLACE INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob)`). Sem essa PK composta, o `REPLACE` não substitui o checkpoint do agente na sessão e corrompe o histórico.

> [!CAUTION]
> #### DECISÃO HUMANA 4: Nomenclatura Temporal em `agent_checkpoints` (`created_at` vs `timestamp`)
> - **Situação:** `core/checkpointer.py:247` e `core/background_janitor.py:161` ordenam por `created_at`. No entanto, `interface/telemetry_api.py:183` executa `SELECT agent_id, session_id, checkpoint_id, timestamp FROM agent_checkpoints ORDER BY timestamp ASC;`.
> - **Alternativa A (Recomendada):** Incluir ambas as colunas no schema canônico (`created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` e `timestamp REAL DEFAULT (strftime('%s', 'now'))`).
>   - *Prós:* Garante compatibilidade imediata com o checkpointer, o janitor e a telemetria, prevenindo falhas de `no such column` antes do refatoramento da Track 5.
>   - *Contras:* Duplicidade de informação temporal na mesma tabela até a Track 5 alinhar a telemetria.
> - **Alternativa B:** Definir apenas `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` e registrar a alteração de `telemetry_api.py:183` no BL-067 (Track 5).
>   - *Prós:* Mantém o schema canônico elegante e normalizado.
>   - *Contras:* A rota `/api/telemetry/snapshot` falhará até que o BL-067 seja corrigido.

---

### 6.5 Tabela `fsm_checkpoints` (Proposta Base)
```sql
CREATE TABLE IF NOT EXISTS fsm_checkpoints (
    checkpoint_id       TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    agent_id            TEXT NOT NULL,
    task_id             TEXT,
    state_name          TEXT NOT NULL,
    shared_state_blob   TEXT NOT NULL,
    created_at          REAL NOT NULL DEFAULT (strftime('%s', 'now')),
    PRIMARY KEY (session_id, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_fsm_checkpoints_session_id ON fsm_checkpoints(session_id);
```
- **Justificativa:** Adota a chave primária composta `(session_id, checkpoint_id)` de `storage/relational_db.py` e `01_ARCHITECTURE.md:283`. Cria expressamente o índice `idx_fsm_checkpoints_session_id` estipulado pelo critério de validação do BL-001.

> [!CAUTION]
> #### DECISÃO HUMANA 5: Tipo de Dado de `created_at` em `fsm_checkpoints` (`REAL` vs `TIMESTAMP`)
> - **Situação:** `storage/relational_db.py:21` definiu `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (string ISO `'YYYY-MM-DD HH:MM:SS'`). Todavia, a especificação formal `01_ARCHITECTURE.md:287` define `created_at REAL NOT NULL, -- Unix timestamp (time.time())`, e o motor de execução [`core/hsm_engine.py:457`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L457) executa `if file_mtime > float(created_at):`. Se `created_at` for uma string ISO, `float(created_at)` gera `ValueError` e desabilita a detecção de stale files no resume.
> - **Alternativa A (Recomendada):** Definir `created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))`.
>   - *Prós:* Compatível diretamente com `float(created_at)` em `hsm_engine.py` e com `time.time()` usado em `test_hsm_transition_hooks_and_delta.py:295` e `01_ARCHITECTURE.md`.
>   - *Contras:* Diverge da instrução textual legada em `storage/relational_db.py:21`.
> - **Alternativa B:** Manter `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` e alterar `core/hsm_engine.py:457` na Track 6 para fazer parse de data ISO.
>   - *Prós:* Mantém fidelidade estrita à string SQL que existia em `storage/relational_db.py`.
>   - *Contras:* Quebra `hsm_engine.py` até que seja corrigido, forçando conversões de formato e afetando comparações numéricas com `os.path.getmtime`.

---

## 7. Impacto nos Testes ao Unificar DDL (Passo 3e)

Quando a resolução do [`BL-003`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L175) purgar os `CREATE TABLE` locais das 17 suítes de teste e passar a inicializar o banco via `SqliteStore` ou `SchemaManager`, os seguintes impactos ocorrerão em cada arquivo:

1. **`tests/test_agent_checkpointer.py`**:
   - *Impacto:* Nenhum impacto negativo. As colunas declaradas no teste eram exatamente as canônicas. Passará a herdar o schema oficial sem precisar de fixture própria.
2. **`tests/test_agent_hsm_coupling.py`**:
   - *Impacto:* As tabelas `files` e `fsm_checkpoints` receberão todas as colunas canônicas completas. Nenhum teste quebra.
3. **`tests/test_alias_tracker.py`**:
   - *Impacto:* 
     - Na tabela `ast_edges`: o teste faz `INSERT INTO ast_edges (parent_node_id, child_node_id)`. Se a proposta canônica consolidar `parent_node, child_node`, este insert específico precisará atualizar a tupla de colunas.
     - Na tabela `fsm_checkpoints`: o teste faz `INSERT INTO fsm_checkpoints (checkpoint_id, task_id, state_name)`. O schema canônico possui constraints `NOT NULL` em `session_id`, `agent_id` e `shared_state_blob`. Os inserts de teste precisarão fornecer valores padrão (ex: `session_id='s1', agent_id='a1', shared_state_blob='{}'`).
4. **`tests/test_checkpoint_pruning.py`**:
   - *Impacto:* Nenhum impacto negativo. O teste já utilizava a assinatura canônica de `agent_checkpoints`.
5. **`tests/test_cognitive_routing_memory.py`**:
   - *Impacto:* `files` receberá colunas adicionais de hash (`ssh_hash`, `body_hash`). O teste não será impactado.
6. **`tests/test_delta_sync.py`**:
   - *Impacto:* `files` passará a ter `last_modified REAL DEFAULT 0.0`. O teste insere `path, content, ssh_hash, body_hash, is_dirty, community_id`, o que continuará perfeitamente válido.
7. **`tests/test_durable_checkpoints_timetravel.py`**:
   - *Impacto:* Nenhum impacto negativo. As operações de time-travel e rollback passarão a ter suporte canônico das tabelas `files` e `fsm_checkpoints`.
8. **`tests/test_e2e_concierge_integration.py`**:
   - *Impacto:* O teste cria as 4 tabelas (`files`, `communities`, `ast_edges`, `agent_checkpoints`). O teste faz `INSERT INTO ast_edges VALUES (?, ?)`, que é compatível por posição. `files` receberá `last_modified`. Nenhum impacto negativo.
9. **`tests/test_graph_rag_frugal.py`**:
   - *Impacto:* `files` receberá colunas de hash; `ast_edges` já usava `parent_node, child_node`. Nenhum impacto negativo.
10. **`tests/test_graph_rag_janitor.py`**:
    - *Impacto:* O teste omitia hashes em `files`. Passará a contar com eles. Nenhum impacto negativo.
11. **`tests/test_graph_rag_loops.py`**:
    - *Impacto:* `ast_edges` já usava `parent_node, child_node`. Nenhum impacto negativo.
12. **`tests/test_hierarchical_state_machine.py`**:
    - *Impacto:* Nenhum impacto negativo. As tabelas `files` e `fsm_checkpoints` estarão disponíveis globalmente.
13. **`tests/test_hsm_transition_hooks_and_delta.py`**:
    - *Impacto:* O teste possuía duas classes com `setUp()` criando tabelas, uma delas usando `created_at REAL`. Ao adotar `created_at REAL` canônico, ambas as classes passarão sem conflito.
14. **`tests/test_local_graph_rag_recursion.py`**:
    - *Impacto:* O teste insere explicitamente em `(parent_node_id, child_node_id)`. Ao migrar para o schema canônico, a fixture de teste precisará ajustar os nomes das colunas para `(parent_node, child_node)`.
15. **`tests/test_mcp_server_extensions.py`**:
    - *Impacto:* Cria `agent_checkpoints` e `ast_edges`. Já utiliza a nomenclatura canônica. Nenhum impacto negativo.
16. **`tests/test_telemetry_api.py`**:
    - *Impacto:* O teste insere em `agent_checkpoints (agent_id, session_id, checkpoint_id, timestamp)`. Com a Decisão Humana 4 (incluindo a coluna `timestamp REAL` no schema canônico), o teste continuará passando sem nenhuma alteração imediata.
17. **`tests/test_vector_reconciler.py`**:
    - *Impacto:* `files` passará a contar com `body_hash` e `last_modified`. O teste insere `(path, content)`, o que continuará válido graças aos defaults das demais colunas.

---

## 8. Conclusão e Ponto de Parada (Gate)

O inventário comprova de forma incontestável que:
1. `storage/relational_db.py` é código órfão sem nenhum importador no projeto.
2. O schema de produção em `storage/schema.py` precisa absorver formalmente as 5 tabelas no Passo B.
3. As propostas de DDL canônico foram desenhadas para harmonizar os requisitos de produção com a compatibilidade retroativa dos testes.
4. Foram isoladas **5 DECISÕES HUMANAS** essenciais para a governança do Passo B.

Em estrito cumprimento à **Regra 7 (Gates)** e às regras da **Fase 4**, a execução é interrompida neste ponto, aguardando as deliberações do usuário.
