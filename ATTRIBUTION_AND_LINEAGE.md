# Attribution, Technical Lineage & Architecture Patterns

> **Official Attribution and Lineage Specification for Grafo Concierge (Agnostic Domain Clean-Up)**  
> **Version:** 1.0.0  
> **Date:** 2026-09-10  
> **Status:** Active  

---

## 1. Design Philosophy: Domain-Driven Design (DDD) & Technological Sovereignty

**Grafo Concierge** adheres to the principles of **Domain-Driven Design (DDD)** and **Hexagonal Architecture (Ports & Adapters)** across its entire codebase. Our fundamental objectives ensure:

1. **Brand & Tooling Decoupling:** No class, domain interface, business module, orchestration function, or relational database table shall depend on third-party brand names, proprietary products, commercial SaaS platforms, or ephemeral external frameworks.
2. **Code Universality & Longevity:** The codebase exclusively expresses the domain semantics of cognitive memory, hybrid retrieval, and multi-agent governance.
3. **Centralized Lineage Acknowledgement:** Rather than scattering transient vendor references throughout source files, all technical attributions, academic credits, architectural design patterns, and open-source inspirations are consolidated in this document.

---

## 2. Lineage Matrix & Architectural Inspirations

| Subsystem / Domain Module | Current / Target Component | Technical Lineage & Inspiration | Fundamental Architecture Pattern |
| :--- | :--- | :--- | :--- |
| **Federated Knowledge Routing** | `core/federated_knowledge_router.py`<br>*(formerly `core/nozomio_router.py`)* | Inspired by distributed telemetry and federated threat routing architectures (**Nozomi Networks**) and enterprise **Federated Search / RAG** systems. | **Content-Based Routing & Privacy-Aware Gateway:** Strict privacy segregation (`is_private`) between private local code graphs and federated public documentation. |
| **Cognitive Agent Lifecycle & HSM** | `agent/run_agent.py`<br>`CognitiveAgentRunner`<br>*(formerly `HermesAgentRunner`)* | Inspired by autonomous reasoning loops (**Nous Research / Hermes Agent**) and Anthropic's Computer-Use patterns. | **Harel Statecharts (UML 2.5 HSM) & Circuit Breaker:** Sub-state turn budget controls, deadlock recovery, and Deep History Node ($H^*$) restoration. |
| **Durable Checkpoints & Time-Travel** | `core/checkpointer.py`<br>`storage/relational_db.py`<br>`AgnosticCheckpointer` | Inspired by **LangGraph** flow checkpointers, **Temporal.io** durable runtime, and **Git** internal state logs. | **Event Sourcing & Temporal State Isolation:** Composite primary key (`agent_id`, `session_id`, `checkpoint_id`) guaranteeing atomic rollback and deadlock immunity. |
| **JIT Intent Classification & SLMs** | `core/intent_classifier.py`<br>`IntentClassifier` | Inspired by local Small Language Model (SLM) inference across the **Ollama / llama.cpp / Qwen-Coder** ecosystems. | **Tiered Triage Pipeline (Chain of Responsibility):** Fast syntactic regex (<1ms) $\rightarrow$ SQLite relational entities $\rightarrow$ local asynchronous SLM inference. |
| **Tri-Signal Hybrid Search v4** | `core/hybrid_search.py`<br>`HybridSearchEngine` | Inspired by dense/sparse hybrid search models from **Pinecone**, **Cohere**, and **Reciprocal Rank Fusion (RRF)**. | **Tri-Signal Scoring Composition:** Weighted blend of cosine dense vector similarity (50%), normalized BM25 (25%), and topological centrality/recency decay (25%). |
| **Serialized WAL Write Queue** | `interface/queue_writer.py`<br>`SerializedWriteQueue` | Inspired by the **LMAX Disruptor** pattern and **SQLite WAL (Write-Ahead Logging)** single-writer concurrency. | **Actor Model / Single-Writer Principle:** Thread-safe serialization of disk mutations with dynamic adaptive opportunistic auto-batching. |
| **Semantic Drift Guard (Dual-Hash)** | `core/delta_manager.py`<br>`DeltaManager` (SSH + LBH) | Inspired by **Git** Directed Acyclic Graphs (DAGs) and **Locality-Based / Structural Semantic Hashing** algorithms. | **Content-Addressable Verification:** Strict separation between cosmetic edits (whitespace/comments) and functional logic drift via AST body hashing. |
| **Triple Governance Pipeline** | `core/gating_interceptor.py`<br>`core/mcp_governor.py`<br>`core/rate_governor.py` | Inspired by enterprise API gateways (**Envoy, Kong**) and Anthropic's **Model Context Protocol (MCP)** specification. | **Adaptive Gating & Progressive Tool Disclosure:** 3 autonomy regimes (`plan-only`, `ask`, `auto-approve`), super-state tool filtering, and 3-tier Leaky Bucket queue freezing. |
| **Critical Revisor & Boundary Guard** | `agents/revisor_critico.py`<br>`RevisorCritico` | Inspired by the **LLM-as-a-Judge (G-Eval / MT-Bench)** evaluation pattern and the **Bell-LaPadula** multi-level security model. | **Contamination Barrier & Auditor Pattern:** Pre-commit semantic validation and cross-tenant context leak prevention between restricted and public wings. |
| **Polyglot Resilient AST Parsing** | `core/parsers/`<br>`core/parser_factory.py` | Inspired by the **Tree-Sitter** incremental syntax analysis framework and modern compiler frontends. | **Graceful Degradation / Fallback Pattern:** High-fidelity Tree-sitter primary parser with instant sub-millisecond lexical regex scanner fallback. |
| **Vector Storage Adaptability** | `storage/base_backend.py`<br>`storage/vector_store.py`<br>`core/vector_backend.py` | Inspired by Robert C. Martin's **Clean Architecture** and Alistair Cockburn's **Ports & Adapters**. | **Abstract Repository & Driver Adapters:** The `BaseVectorBackend` domain port isolates core logic from physical implementations (ChromaDB, Qdrant, FAISS). |
| **Reactive Observability Cockpit** | `grafo-dashboard-web/`<br>`interface/telemetry_api.py` | Inspired by **Grafana** operational dashboards, **Prometheus** telemetry metrics, and **FastAPI SSE**. | **Reactive Event-Driven Telemetry:** Unidirectional Server-Sent Events (SSE) stream with passive rendering (Zero-Mutation UI) for zero development overhead. |

---

## 3. Deep Dive into Technical Lineage & Credits

### 3.1. Federated Knowledge Routing
* **Conceptual Origin:** The knowledge routing pattern inspiring our federated layer originated in operational telemetry and cybersecurity architectures (**Nozomi Networks**), where localized internal telemetry operates alongside public threat intelligence feeds without exposing private data.
* **Agnostic Implementation in Grafo Concierge:** The `FederatedKnowledgeRouter` acts as an agnostic dispatcher querying `LocalGraphRAG` when user intent targets private internal code (`LOCAL_CODEBASE`, with `is_private: True`), or federated documentation servers when queries are conceptual or target public libraries (`EXTERNAL_GENERAL`, with `is_private: False`).

### 3.2. Cognitive Agent Execution Loop
* **Conceptual Origin:** The **Hermes** model family and reasoning patterns (developed by **Nous Research**) pioneered structured tool invocation, step-by-step planning, and continuous self-correction in autonomous coding agents.
* **Agnostic Implementation in Grafo Concierge:** The `CognitiveAgentRunner` class abstracts the execution loop, binding it rigidly to the Hierarchical State Machine (`HSM`). It enforces safety boundaries (5-turn maximum per sub-state), guarantees context preservation through the *Deep History Node* ($H^*$), and injects execution regime rules dynamically into prompts.

### 3.3. Hierarchical State Machines (HSM)
* **Conceptual Origin:** Formally defined by computer scientist **David Harel** in his seminal 1987 paper (*"Statecharts: A Visual Formalism for Complex Systems"*), HSMs resolve the combinatorial explosion of states in complex reactive systems.
* **Implementation in Grafo Concierge:** The `core/hsm_engine.py` module structures the agent lifecycle into super-states (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `ERROR`) and qualified sub-states (e.g., `EXECUTION.TDD_GREEN`), eliminating infinite hallucination and repair loops.

### 3.4. Progressive Tool Disclosure Governance
* **Conceptual Origin:** Anthropic's **Model Context Protocol (MCP)** specification combined with **Cloud Native Computing Foundation (CNCF)** API governance principles.
* **Implementation in Grafo Concierge:** `MCPToolGovernor` dynamically limits active tools to those permitted for the agent's current lifecycle state, drastically reducing context window token consumption and preventing unintended destructive writes during planning phases.

### 3.5. Vector & Hybrid Storage
* **Conceptual Origin:** Open-source vector database pioneers and semantic similarity search research—including the **ChromaDB**, **Qdrant**, and **Sentence Transformers** (Hugging Face / UKPLab) ecosystems.
* **Implementation in Grafo Concierge:** The system standardizes on the `BaseVectorBackend` port, enabling plug-and-play interchangeability between local vector engines without modifying ingestion, mining (`concierge_mine`), or background Janitor reconciliation workflows.

---

## 4. Ongoing Code Maintenance Guidelines

1. **New Modules and Classes:** Must always adopt functional domain terminology (`FederatedKnowledgeRouter`, `CognitiveAgentRunner`, `VectorRepositoryPort`, `DurableCheckpointer`, `SemanticFactStore`).
2. **Mandatory Documentation:** Whenever a cutting-edge technique, academic paper, or open-source framework inspires an addition to the monorepo, its attribution and architectural credits must be recorded in this `ATTRIBUTION_AND_LINEAGE.md` document.
3. **Keep Tests Domain-Agnostic:** Test suites and fixtures must use generic identifiers (`primary_agent`, `secondary_agent`, `test_session`, `federated_client`) rather than third-party or branded names.
