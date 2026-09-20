# Auditoria — `mock-vs-real-audit`

> **Item:** Comparação Sistemática de Mocks em `tests/` vs Classes Reais de Produção  
> **Fase:** 1 — Auditoria módulo a módulo (Tarefa Transversal de Mocks)  
> **Data:** 2026-09-19  
> **Status:** Concluído  

---

## 1. Contexto e Objetivo

No Achado #1 da auditoria do `core/delta_manager.py`, identificou-se que `hsm_engine.py:458` invocava `delta_manager.has_structural_change()`, um método inexistente na classe real de produção. Esse bug crítico passava despercebido nos testes automatizados porque `tests/test_hsm_transition_hooks_and_delta.py` definia um `MockDeltaManager` que implementava artificialmente esse método.

Esta auditoria inspecionou **todas as 18 classes de Mock / Test Double** presentes no diretório `tests/`, mapeou cada uma à sua respectiva classe de produção e identificou:
1. Métodos presentes no mock mas ausentes na classe real (padrão de mascaramento de bug).
2. Divergências de assinatura e de contrato de tipos entre mocks e produção.
3. Mocks ambíguos ou com classes reais inexistentes.

---

## 2. Inventário Completo de Mocks em `tests/` (18 classes)

| # | Mock Class | Arquivo:Linha (Mock) | Classe Real | Arquivo:Linha (Real) | Status de Alinhamento |
|---|------------|----------------------|-------------|----------------------|-----------------------|
| 1 | `MockDeltaManager` | [`tests/test_hsm_transition_hooks_and_delta.py:25`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py#L25) | `DeltaManager` | [`core/delta_manager.py:70`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L70) | ❌ **CRÍTICA:** Mock define `has_structural_change`, ausente no real |
| 2 | `MockDeltaManagerNoChange` | [`tests/test_hsm_transition_hooks_and_delta.py:37`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py#L37) | `DeltaManager` | [`core/delta_manager.py:70`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L70) | ❌ **CRÍTICA:** Herda método fantasma `has_structural_change` |
| 3 | `MockVectorDatabase` | [`tests/test_vector_reconciler.py:67`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L67) | `BaseVectorBackend` / `ChromaVectorStore` | [`storage/base_backend.py:91`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py#L91) / [`storage/vector_store.py:251`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L251) | ❌ **CRÍTICA:** Mock define `get_all_ids` e `insert`, ausentes no real |
| 4 | `MockVectorDatabase` | [`tests/test_e2e_concierge_integration.py:157`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_e2e_concierge_integration.py#L157) | `BaseVectorBackend` / `ChromaVectorStore` | [`storage/base_backend.py:91`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py#L91) / [`storage/vector_store.py:251`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L251) | ❌ **CRÍTICA:** Idêntico ao acima (`get_all_ids`, `insert` fantasmas) |
| 5 | `MockExternalMCP` | [`tests/test_cognitive_routing_memory.py:28`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_cognitive_routing_memory.py#L28) | *Nenhuma (Inexistente)* | *Nenhum* | ⚠️ **AMBÍGUO:** `query_docs` não é implementado por nenhuma classe real |
| 6 | `MockJanitor` | [`tests/test_mcp_server_handlers.py:116`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L116) | `JanitorService` (produção) vs `BackgroundJanitor` (core) | [`services/janitor.py:107`](file:///c:/Nexus-Memory/GrafoConcierge/services/janitor.py#L107) vs [`core/background_janitor.py:48`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L48) | ℹ️ **FALSO POSITIVO (OBSERVAÇÃO):** `JanitorService` (classe real injetada no servidor MCP) satisfaz 100% dos métodos do mock. Mantida apenas a observação de duplicidade de nomenclatura com `BackgroundJanitor`. |
| 7 | `MockGraphRAGEngine` | [`tests/test_cognitive_routing_memory.py:22`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_cognitive_routing_memory.py#L22) | `GraphRAGEngine` | [`core/graph_rag.py:20`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L20) | ⚠️ **MÉDIA:** Divergência de assinatura e tipo de retorno |
| 8 | `_MockVectorStore` | [`tests/test_interface_contracts.py:40`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L40) | `BaseVectorBackend` / `ChromaVectorStore` | [`storage/base_backend.py:91`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py#L91) | ⚠️ **MÉDIA:** `reset_collection` fora da interface base; `search()` sem parâmetros |
| 9 | `MockVectorStore` | [`tests/test_mcp_server_handlers.py:34`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L34) | `ChromaVectorStore` | [`storage/vector_store.py:251`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L251) | ⚠️ **BAIXA:** Alinhado ao `ChromaVectorStore`, variação de nome de parâmetro em `verify_sync` |
| 10 | `_MockIngestionManager` | [`tests/test_interface_contracts.py:67`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L67) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ⚠️ **BAIXA:** Parâmetro `path` vs `source_path` em `mine()` |
| 11 | `MockIngestionManager` | [`tests/test_mcp_server_handlers.py:79`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L79) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ⚠️ **BAIXA:** Parâmetro `path` vs `source_path` em `mine()` |
| 12 | `FailingIngestion` | [`tests/test_mcp_server_handlers.py:209`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L209) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ✅ **CONFORME:** `mine` e `generate_project_context` presentes no real; test stub para erro |
| 13 | `DummyDatabaseManager` | [`tests/test_dependency_injection.py:34`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_dependency_injection.py#L34) | `ConciergeDatabaseManager` | [`core/database.py:21`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L21) | ✅ **OK:** Dummy sem métodos, validação de imutabilidade do container |
| 14 | `MockLLMAdapter` | [`tests/test_extraction_noop.py:18`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_extraction_noop.py#L18) | `LLMAdapter` | [`ingestion/summarizer.py:140`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py#L140) | ✅ **OK:** Método `generate(prompt, max_tokens)` estritamente alinhado |
| 15 | `_MockEmbeddingManager` | [`tests/test_interface_contracts.py:28`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L28) | `EmbeddingManager` | [`storage/vector_store.py:75`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L75) | ✅ **OK:** `embed()` e `embed_batch()` alinhados |
| 16 | `MockEmbeddingManager` | [`tests/test_mcp_server_handlers.py:22`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L22) | `EmbeddingManager` | [`storage/vector_store.py:75`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L75) | ✅ **OK:** `embed()` e `embed_batch()` alinhados |
| 17 | `InMemoryConnManager` | [`tests/test_storage_logic.py:42`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L42) | `ConnectionManager` | [`storage/connection.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L196) | ✅ **CONFORME:** API pública (`read`, `write`, `close`) 100% coincidente com a classe real |
| 18 | `MockDB` | [`tests/test_watcher_ignore.py:98`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_watcher_ignore.py#L98) | `ConciergeDatabaseManager` | [`core/database.py:21`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L21) | ✅ **OK:** `read_query()` alinhado |

### 2.1 Comparação Detalhada de Test Doubles Especiais

#### `FailingIngestion` vs `IngestionManager`
- **Arquivo do Teste:** [`tests/test_mcp_server_handlers.py:209`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L209)
- **Arquivo de Produção:** [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94)
- **Métodos no stub:**
  1. `mine(self, *args, **kwargs)` — Presente na classe real [`IngestionManager.mine(self, project_uuid, source_path, auto_tag=True)`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L127). O stub aceita `*args, **kwargs` para injetar `RuntimeError("Disk full")`.
  2. `generate_project_context(self, *args)` — Presente na classe real [`IngestionManager.generate_project_context(self, project_uuid)`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L824).
- **Métodos presentes no mock mas ausentes no real:** **Nenhum (0)**.
- **Resultado:** **CONFORME**. O stub cobre estritamente os métodos chamados pelo fluxo de teste de resiliência a falhas de disco.

#### `InMemoryConnManager` vs `ConnectionManager`
- **Arquivo do Teste:** [`tests/test_storage_logic.py:42`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L42)
- **Arquivo de Produção:** [`storage/connection.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L196)
- **Métodos no fake:**
  1. `read(self)` — Context manager idêntico a [`ConnectionManager.read(self)`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L276).
  2. `write(self, fn: Callable, *args: Any, **kwargs: Any) -> Any` — Idêntico a [`ConnectionManager.write(self, fn, *args, **kwargs)`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L284).
  3. `close(self) -> None` — Idêntico a [`ConnectionManager.close(self)`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L242).
  4. `_bootstrap_schema(self) -> None` — Helper privado exclusivo de teste para inicializar tabelas em `:memory:`.
- **Métodos públicos presentes no mock mas ausentes no real:** **Nenhum (0)**.
- **Resultado:** **CONFORME**. O fake in-memory atende perfeitamente ao contrato de `ConnectionManager`.

---

## 3. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `tests/test_vector_reconciler.py` / `core/vector_reconciler.py` | test: 83; vr: 39 | **CRÍTICA** | `core/vector_reconciler.py:39` invoca `self.vector_db.get_all_ids()`. Esse método **não existe** nem na interface `BaseVectorBackend` nem na classe real `ChromaVectorStore` (o método real é `get_all_stored_node_ids()`). Em runtime, quando o `VectorReconciler` roda com a classe real, sofre `AttributeError: 'ChromaVectorStore' object has no attribute 'get_all_ids'`. Os testes em `test_vector_reconciler.py` e `test_e2e_concierge_integration.py` passam apenas porque usam `MockVectorDatabase` que inventa `get_all_ids()`. Padrão idêntico ao Achado #1 do `delta_manager.py`. | Script de reprodução executado: `hasattr(ChromaVectorStore, 'get_all_ids') == False`; invocação de `VectorReconciler(db, ChromaVectorStore(...)).reconcile_orphans()` lança `AttributeError` real. Ver saída abaixo. | **CONFIRMADO** |
| 2 | `tests/test_hsm_transition_hooks_and_delta.py` / `core/hsm_engine.py` | test: 32; hsm: 458 | **CRÍTICA** | `core/hsm_engine.py:458` chama `delta_manager.has_structural_change(target_task_id)`. O método **não existe** em `DeltaManager`. O `MockDeltaManager` implementou esse método artificialmente, mascarando o bug nos testes. | Script de reprodução executado: `hasattr(DeltaManager, 'has_structural_change') == False`; chamada direta lança `AttributeError`. | **CONFIRMADO** |
| 3 | `tests/test_cognitive_routing_memory.py` / `core/federated_knowledge_router.py` | test: 30; fkr: 73 | **ALTA** | `MockExternalMCP` define `query_docs(self, query)`. O roteador `FederatedKnowledgeRouter` (`core/federated_knowledge_router.py:73`) invoca `self.external_mcp.query_docs(query)`. Contudo, **não existe nenhuma classe de produção em todo o repositório** que implemente esse cliente MCP federado. O mock testa um contrato puramente fantasma sem correspondente real. | Busca estática global em todo o codebase por `def query_docs`: 0 classes reais encontradas. | **CONFIRMADO (AMBÍGUO / INEXISTENTE)** |
| 4 | `tests/test_mcp_server_handlers.py` / `interface/mcp_server.py` | test: 116; mcp: 135; js: 107 | **FALSO POSITIVO (OBSERVAÇÃO)** | `MockJanitor` define `signal_mine_start`, `signal_mine_end`, `is_running`, `last_reports`. A classe real usada pelo servidor MCP (`interface/mcp_server.py:135`) é `JanitorService` de `services/janitor.py`, a qual **implementa 100% desses 4 métodos**. Em runtime de produção, o servidor funciona perfeitamente com a classe real. A aparente divergência ocorreria apenas se o mock substituísse `core/background_janitor.py` (`BackgroundJanitor`). Não há quebra em runtime (falso positivo de defeito). Resta apenas uma **observação arquitetural** de duplicidade conceitual de nomenclatura entre `core/background_janitor.py` e `services/janitor.py`. | Verificado em `interface/mcp_server.py:50, 135`: tipo anotado e utilizado é `JanitorService`. `hasattr(JanitorService, m) == True` para todos os métodos. | **FALSO POSITIVO (RESOLVIDO / OBSERVADO)** |
| 5 | `tests/test_vector_reconciler.py` / `storage/base_backend.py` | test: 73; bb: 91 | **MÉDIA** | `MockVectorDatabase` define `insert(vector_id, payload)`. `insert` não existe em `BaseVectorBackend` nem em `ChromaVectorStore` (o método real de produção é `store_embedding(doc_id, embedding, metadata)`). Embora `VectorReconciler` não chame `insert`, o mock esconde que a inserção de vetores real requer metadados obrigatórios (`project_uuid`, `node_id`) e vetor float validado. | Script de reprodução: `hasattr(BaseVectorBackend, 'insert') == False`; `hasattr(ChromaVectorStore, 'insert') == False`. | **CONFIRMADO** |
| 6 | `tests/test_cognitive_routing_memory.py` / `core/graph_rag.py` | test: 24; gr: 45 | **MÉDIA** | `MockGraphRAGEngine.retrieve_multihop_context(query)` aceita texto puro de query e retorna `str`. A classe real `GraphRAGEngine.retrieve_multihop_context(entry_node, max_depth=3)` espera o caminho de um arquivo (`entry_node`) e retorna um `Dict[str, Any]`. Ao plugar a classe real no `FederatedKnowledgeRouter._resolve_local()`, passar uma query em linguagem natural falhará na busca relacional de `files.path` e retornará um dicionário em vez de texto, quebrando as expectativas de contexto das camadas superiores. | Inspeção de assinatura: mock `(self, query: str) -> str` vs real `(self, entry_node: str, max_depth: int = 3) -> Dict[str, Any]`. | **CONFIRMADO** |
| 7 | `tests/test_interface_contracts.py` / `storage/base_backend.py` | test: 62, 65; bb: 91 | **BAIXA** | `_MockVectorStore.reset_collection()` é testado como se fizesse parte da interface de vetor, mas `reset_collection` existe apenas na classe concreta `ChromaVectorStore`, não na interface abstrata `BaseVectorBackend`. Além disso, `_MockVectorStore.search(self)` não aceita parâmetros (`def search(self): return []`), enquanto a interface real exige `query_embedding` e `project_uuids`. | Inspeção de métodos de `BaseVectorBackend` vs `_MockVectorStore`. | **CONFIRMADO** |

---

## 4. Saída Bruta da Reprodução Executada

```
======================================================================
REPRODUCAO: MOCK VS REAL AUDIT
======================================================================

--- CASO 1: MockDeltaManager vs DeltaManager ---
MockDeltaManager has 'has_structural_change': True
DeltaManager has 'has_structural_change': False
>>> RUNTIME TRACEBACK CONFIRMADO: AttributeError - 'DeltaManager' object has no attribute 'has_structural_change'

--- CASO 2: MockVectorDatabase vs ChromaVectorStore (VectorReconciler crash) ---
MockVectorDatabase has 'get_all_ids': True
BaseVectorBackend has 'get_all_ids': False
ChromaVectorStore has 'get_all_ids': False
BaseVectorBackend has canonical 'get_all_stored_node_ids': True
ChromaVectorStore has canonical 'get_all_stored_node_ids': True
>>> RUNTIME TRACEBACK CONFIRMADO: AttributeError - 'ChromaVectorStore' object has no attribute 'get_all_ids'

--- CASO 3: MockVectorDatabase.insert vs BaseVectorBackend ---
MockVectorDatabase has 'insert': True
BaseVectorBackend has 'insert': False
ChromaVectorStore has 'insert': False
Canonical method is 'store_embedding': True

--- CASO 4: MockJanitor vs BackgroundJanitor vs JanitorService ---
Method 'signal_mine_start': MockJanitor=True | BackgroundJanitor=False | JanitorService=True
Method 'signal_mine_end': MockJanitor=True | BackgroundJanitor=False | JanitorService=True
Method 'is_running': MockJanitor=True | BackgroundJanitor=False | JanitorService=True
Method 'last_reports': MockJanitor=True | BackgroundJanitor=False | JanitorService=True

--- CASO 5: MockExternalMCP vs Classes de Producao ---
MockExternalMCP has 'query_docs': True
Production classes with 'query_docs': NONE (CLASSE REAL INEXISTENTE / AMBIGUO)

--- CASO 6: MockGraphRAGEngine vs GraphRAGEngine ---
MockGraphRAGEngine.retrieve_multihop_context sig: (self, query: str) -> str
GraphRAGEngine.retrieve_multihop_context sig:     (self, entry_node: str, max_depth: int = 3) -> Dict[str, Any]

======================================================================
FIM DA REPRODUCAO
======================================================================
```

---

## 5. Síntese e Descoberta Mais Importante

A auditoria sistemática confirmou com sucesso que o padrão do Achado #1 do `delta_manager.py` **não era um caso isolado**:

1. **Segundo Bug Crítico Idêntico Encontrado**: O `VectorReconciler` (`core/vector_reconciler.py:39`) chama `self.vector_db.get_all_ids()`, mas nem `ChromaVectorStore` nem `BaseVectorBackend` implementam esse método (implementam `get_all_stored_node_ids()`). Em produção, a reconciliação de vetores quebra com `AttributeError`. O teste passa 100% porque `MockVectorDatabase` inventou o método `get_all_ids()`.
2. **Duplicidade Arquitetural de Nomenclatura (Janitors — Falso Positivo de Defeito em Produção)**: Coexistem `core/background_janitor.py` (`BackgroundJanitor`) e `services/janitor.py` (`JanitorService`) com contratos totalmente distintos. O servidor MCP em produção utiliza explicitamente `JanitorService` (`interface/mcp_server.py:135`), o qual satisfaz 100% dos métodos testados pelo `MockJanitor`. Não há quebra em runtime (falso positivo de bug), restando apenas a observação arquitetural de ambiguidade/duplicidade do termo Janitor no codebase.
3. **Contrato Fantasma de Documentação**: `FederatedKnowledgeRouter` foi codificado para chamar `query_docs`, mas nenhuma classe real no projeto inteiro implementa esse cliente, apenas o `MockExternalMCP`.
4. **Conformidade dos Test Doubles Especiais**: `FailingIngestion` (stub de erro para `IngestionManager`) e `InMemoryConnManager` (fake in-memory para `ConnectionManager`) possuem zero (0) métodos ausentes nas classes reais de produção, atendendo estritamente aos contratos públicos chamados.
