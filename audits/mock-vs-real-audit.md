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
| 6 | `MockJanitor` | [`tests/test_mcp_server_handlers.py:116`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L116) | `BackgroundJanitor` vs `JanitorService` | [`core/background_janitor.py:48`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L48) vs [`services/janitor.py:67`](file:///c:/Nexus-Memory/GrafoConcierge/services/janitor.py#L67) | ⚠️ **AMBÍGUO / ALTA:** Ausente em `core`, presente em `services` (duplicidade) |
| 7 | `MockGraphRAGEngine` | [`tests/test_cognitive_routing_memory.py:22`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_cognitive_routing_memory.py#L22) | `GraphRAGEngine` | [`core/graph_rag.py:20`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L20) | ⚠️ **MÉDIA:** Divergência de assinatura e tipo de retorno |
| 8 | `_MockVectorStore` | [`tests/test_interface_contracts.py:40`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L40) | `BaseVectorBackend` / `ChromaVectorStore` | [`storage/base_backend.py:91`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py#L91) | ⚠️ **MÉDIA:** `reset_collection` fora da interface base; `search()` sem parâmetros |
| 9 | `MockVectorStore` | [`tests/test_mcp_server_handlers.py:34`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L34) | `ChromaVectorStore` | [`storage/vector_store.py:251`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L251) | ⚠️ **BAIXA:** Alinhado ao `ChromaVectorStore`, variação de nome de parâmetro em `verify_sync` |
| 10 | `_MockIngestionManager` | [`tests/test_interface_contracts.py:67`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L67) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ⚠️ **BAIXA:** Parâmetro `path` vs `source_path` em `mine()` |
| 11 | `MockIngestionManager` | [`tests/test_mcp_server_handlers.py:79`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L79) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ⚠️ **BAIXA:** Parâmetro `path` vs `source_path` em `mine()` |
| 12 | `FailingIngestion` | [`tests/test_mcp_server_handlers.py:209`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L209) | `IngestionManager` | [`ingestion/orchestrator.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94) | ✅ **OK:** Test stub com `*args, **kwargs` simulando erro de disco |
| 13 | `DummyDatabaseManager` | [`tests/test_dependency_injection.py:34`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_dependency_injection.py#L34) | `ConciergeDatabaseManager` | [`core/database.py:21`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L21) | ✅ **OK:** Dummy sem métodos, validação de imutabilidade do container |
| 14 | `MockLLMAdapter` | [`tests/test_extraction_noop.py:18`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_extraction_noop.py#L18) | `LLMAdapter` | [`ingestion/summarizer.py:140`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py#L140) | ✅ **OK:** Método `generate(prompt, max_tokens)` estritamente alinhado |
| 15 | `_MockEmbeddingManager` | [`tests/test_interface_contracts.py:28`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L28) | `EmbeddingManager` | [`storage/vector_store.py:75`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L75) | ✅ **OK:** `embed()` e `embed_batch()` alinhados |
| 16 | `MockEmbeddingManager` | [`tests/test_mcp_server_handlers.py:22`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L22) | `EmbeddingManager` | [`storage/vector_store.py:75`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L75) | ✅ **OK:** `embed()` e `embed_batch()` alinhados |
| 17 | `InMemoryConnManager` | [`tests/test_storage_logic.py:42`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L42) | `ConnectionManager` | [`storage/connection.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L196) | ✅ **OK:** `read()`, `write()`, `close()` alinhados (`_bootstrap_schema` é helper de teste) |
| 18 | `MockDB` | [`tests/test_watcher_ignore.py:98`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_watcher_ignore.py#L98) | `ConciergeDatabaseManager` | [`core/database.py:21`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L21) | ✅ **OK:** `read_query()` alinhado |

---

## 3. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `tests/test_vector_reconciler.py` / `core/vector_reconciler.py` | test: 83; vr: 39 | **CRÍTICA** | `core/vector_reconciler.py:39` invoca `self.vector_db.get_all_ids()`. Esse método **não existe** nem na interface `BaseVectorBackend` nem na classe real `ChromaVectorStore` (o método real é `get_all_stored_node_ids()`). Em runtime, quando o `VectorReconciler` roda com a classe real, sofre `AttributeError: 'ChromaVectorStore' object has no attribute 'get_all_ids'`. Os testes em `test_vector_reconciler.py` e `test_e2e_concierge_integration.py` passam apenas porque usam `MockVectorDatabase` que inventa `get_all_ids()`. Padrão idêntico ao Achado #1 do `delta_manager.py`. | Script de reprodução executado: `hasattr(ChromaVectorStore, 'get_all_ids') == False`; invocação de `VectorReconciler(db, ChromaVectorStore(...)).reconcile_orphans()` lança `AttributeError` real. Ver saída abaixo. | **CONFIRMADO** |
| 2 | `tests/test_hsm_transition_hooks_and_delta.py` / `core/hsm_engine.py` | test: 32; hsm: 458 | **CRÍTICA** | `core/hsm_engine.py:458` chama `delta_manager.has_structural_change(target_task_id)`. O método **não existe** em `DeltaManager`. O `MockDeltaManager` implementou esse método artificialmente, mascarando o bug nos testes. | Script de reprodução executado: `hasattr(DeltaManager, 'has_structural_change') == False`; chamada direta lança `AttributeError`. | **CONFIRMADO** |
| 3 | `tests/test_cognitive_routing_memory.py` / `core/federated_knowledge_router.py` | test: 30; fkr: 73 | **ALTA** | `MockExternalMCP` define `query_docs(self, query)`. O roteador `FederatedKnowledgeRouter` (`core/federated_knowledge_router.py:73`) invoca `self.external_mcp.query_docs(query)`. Contudo, **não existe nenhuma classe de produção em todo o repositório** que implemente esse cliente MCP federado. O mock testa um contrato puramente fantasma sem correspondente real. | Busca estática global em todo o codebase por `def query_docs`: 0 classes reais encontradas. | **CONFIRMADO (AMBÍGUO / INEXISTENTE)** |
| 4 | `tests/test_mcp_server_handlers.py` / `core/background_janitor.py` | test: 116; bj: 48; js: 67 | **ALTA** | `MockJanitor` define `signal_mine_start`, `signal_mine_end`, `is_running`, `last_reports`. Se associado ao janitor do core (`core/background_janitor.py`), **todos os 4 métodos estão ausentes** (`BackgroundJanitor` só tem `run_idle_summarization`, `prune_session_checkpoints`, etc.). Esses métodos pertencem à classe `JanitorService` de `services/janitor.py`. Há duplicidade arquitetural de Janitors no repositório com contratos totalmente desconexos. | Script de reprodução executado: `hasattr(BackgroundJanitor, m)` retorna `False` para todos os 4 métodos; `JanitorService` retorna `True`. | **CONFIRMADO (AMBIGUIDADE / DUPLICIDADE)** |
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
2. **Duplicidade Arquitetural de Janitors**: Coexistem `core/background_janitor.py` (`BackgroundJanitor`) e `services/janitor.py` (`JanitorService`) com contratos totalmente distintos e sem herança compartilhada.
3. **Contrato Fantasma de Documentação**: `FederatedKnowledgeRouter` foi codificado para chamar `query_docs`, mas nenhuma classe real no projeto inteiro implementa esse cliente, apenas o `MockExternalMCP`.
