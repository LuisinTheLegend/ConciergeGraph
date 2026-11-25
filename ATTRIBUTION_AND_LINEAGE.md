# Attribution, Technical Lineage & Architecture Patterns

> **Official Attribution and Lineage Specification for Grafo Concierge (Agnostic Domain Clean-Up)**  
> **Version:** 1.1.0  
> **Date:** 2026-11-24  
> **Status:** Active (aligned with V4 Core Quarantine — Rodada 4.5g)

---

## 1. Design Philosophy: Domain-Driven Design (DDD) & Technological Sovereignty

**Grafo Concierge** adheres to the principles of **Domain-Driven Design (DDD)** and **Hexagonal Architecture (Ports & Adapters)** across its entire codebase. Our fundamental objectives ensure:

1. **Brand & Tooling Decoupling:** No class, domain interface, business module, orchestration function, or relational database table shall depend on third-party brand names, proprietary products, commercial SaaS platforms, or ephemeral external frameworks.
2. **Code Universality & Longevity:** The codebase exclusively expresses the domain semantics of cognitive memory, hybrid retrieval, and MCP tool governance.
3. **Centralized Lineage Acknowledgement:** Rather than scattering transient vendor references throughout source files, all technical attributions, academic credits, architectural design patterns, and open-source inspirations are consolidated in this document — preserving historical lineage for both active V4 core modules and modules placed in quarantine under `archive/v4-experimental/`.

---

## 2. Lineage Matrix & Architectural Inspirations

| Subsystem / Domain Module | Component | V4 Status | Technical Lineage & Inspiration | Fundamental Architecture Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Federated Knowledge Routing** | `archive/v4-experimental/core/federated_knowledge_router.py`<br>*(formerly `core/nozomio_router.py`)* | **Quarantined** (`archive/v4-experimental/`) | Inspired by distributed telemetry and federated threat routing architectures (**Nozomi Networks**) and enterprise **Federated Search / RAG** systems. | **Content-Based Routing & Privacy-Aware Gateway:** Strict privacy segregation (`is_private`) between private local code graphs and federated public documentation. |
| **Cognitive Agent Lifecycle & HSM** | `archive/v4-experimental/agent/run_agent.py`<br>`archive/v4-experimental/core/hsm_engine.py`<br>`CognitiveAgentRunner` | **Quarantined** (`archive/v4-experimental/`) | Inspired by autonomous reasoning loops (**Nous Research / Hermes Agent**) and Anthropic's Computer-Use patterns. | **Harel Statecharts (UML 2.5 HSM) & Circuit Breaker:** Sub-state turn budget controls, deadlock recovery, and Deep History Node ($H^*$) restoration. |
| **Durable Checkpoints & Time-Travel** | `core/checkpointer.py`<br>`AgnosticCheckpointer`<br>*(note: `storage/relational_db.py` quarantined)* | **Active in V4 Core** | Inspired by **LangGraph** flow checkpointers, **Temporal.io** durable runtime, and **Git** internal state logs. | **Event Sourcing & Temporal State Isolation:** Composite primary key (`agent_id`, `session_id`, `checkpoint_id`) in `agent_checkpoints` guaranteeing deterministic state snapshots. |
| **JIT Intent Classification & SLMs** | `archive/v4-experimental/core/intent_classifier.py`<br>`IntentClassifier` | **Quarantined** (`archive/v4-experimental/`) | Inspired by local Small Language Model (SLM) inference across the **Ollama / llama.cpp / Qwen-Coder** ecosystems. | **Tiered Triage Pipeline (Chain of Responsibility):** Fast syntactic regex (<1ms) $\rightarrow$ SQLite relational entities $\rightarrow$ local asynchronous SLM inference. |
| **Tri-Signal Hybrid Search v4** | `core/hybrid_search.py`<br>`HybridSearchEngine` | **Active in V4 Core** | Inspired by dense/sparse hybrid search models from **Pinecone**, **Cohere**, and **Reciprocal Rank Fusion (RRF)**. | **Tri-Signal Scoring Composition:** Weighted blend of dense vector similarity (50%), normalized FTS5 BM25 (25%), and topological centrality/recency decay (25%). |
| **Serialized WAL Write Queue** | `interface/queue_writer.py`<br>`SerializedWriteQueue` | **Deferred (V4.1)** *(not used in live MCP path)* | Inspired by the **LMAX Disruptor** pattern and **SQLite WAL (Write-Ahead Logging)** single-writer concurrency. | **Actor Model / Single-Writer Principle:** Thread-safe serialization of disk mutations with adaptive opportunistic auto-batching. |
| **Semantic Drift Guard (Dual-Hash)** | `archive/v4-experimental/core/delta_manager.py`<br>`DeltaManager` (SSH + LBH) | **Quarantined** (`archive/v4-experimental/`) | Inspired by **Git** Directed Acyclic Graphs (DAGs) and **Locality-Based / Structural Semantic Hashing** algorithms. | **Content-Addressable Verification:** Strict separation between cosmetic edits (whitespace/comments) and functional logic drift via AST body hashing. |
| **MCP Governance & Rate/Gating Pipeline** | `core/mcp_governor.py` **(Active)**<br>`archive/v4-experimental/core/gating_interceptor.py`<br>`archive/v4-experimental/core/rate_governor.py` | **Partially Active** (`MCPToolGovernor` Active; Gating & Rate Governor Quarantined) | Inspired by enterprise API gateways (**Envoy, Kong**) and Anthropic's **Model Context Protocol (MCP)** specification. | **Progressive Tool Disclosure:** Two-layer tool filtering and runtime execution validation across `READ_ONLY`, `LOCAL_MUTATION`, and `DANGEROUS` categories. |
| **Critical Revisor & Boundary Guard** | `archive/v4-experimental/agents/revisor_critico.py`<br>`RevisorCritico` | **Quarantined** (`archive/v4-experimental/`) | Inspired by the **LLM-as-a-Judge (G-Eval / MT-Bench)** evaluation pattern and the **Bell-LaPadula** multi-level security model. | **Contamination Barrier & Auditor Pattern:** Pre-commit semantic validation and cross-tenant context leak prevention between restricted and public wings. |
| **Polyglot Resilient AST Parsing** | `archive/v4-experimental/core/parsers/`<br>`archive/v4-experimental/core/parser_factory.py`<br>*(live parser: `ingestion/parser.py`)* | **Quarantined** (`archive/v4-experimental/`; Python AST parser active in `ingestion/parser.py`) | Inspired by the **Tree-Sitter** incremental syntax analysis framework and modern compiler frontends. | **Graceful Degradation / Fallback Pattern:** Primary AST syntax analysis with resilient fallback parsing. |
| **Vector Storage Adaptability** | `storage/base_backend.py`<br>`storage/vector_store.py`<br>`core/vector_backend.py` | **Active in V4 Core** | Inspired by Robert C. Martin's **Clean Architecture** and Alistair Cockburn's **Ports & Adapters**. | **Abstract Repository & Driver Adapters:** The `BaseVectorBackend` domain port isolates core logic from physical implementations (ChromaDB default, optional Qdrant). |
| **Reactive Observability Cockpit** | `archive/v4-experimental/grafo-dashboard-web/`<br>`archive/v4-experimental/interface/telemetry_api.py` | **Quarantined** (`archive/v4-experimental/`) | Inspired by **Grafana** operational dashboards, **Prometheus** telemetry metrics, and **FastAPI SSE**. | **Reactive Event-Driven Telemetry:** Unidirectional Server-Sent Events (SSE) stream with passive rendering (Zero-Mutation UI). |

---

## 3. Deep Dive into Technical Lineage & Credits

### 3.1. Federated Knowledge Routing
* **Status:** Quarantined (`archive/v4-experimental/`)
* **Conceptual Origin:** The knowledge routing pattern inspiring our federated layer originated in operational telemetry and cybersecurity architectures (**Nozomi Networks**), where localized internal telemetry operates alongside public threat intelligence feeds without exposing private data.
* **Historical Implementation:** `FederatedKnowledgeRouter` acted as a dispatcher querying local graph memory when intent targeted private code (`LOCAL_CODEBASE`, `is_private: True`), or external documentation servers when queries targeted public libraries (`EXTERNAL_GENERAL`, `is_private: False`).

### 3.2. Cognitive Agent Execution Loop
* **Status:** Quarantined (`archive/v4-experimental/`)
* **Conceptual Origin:** The **Hermes** model family and reasoning patterns (developed by **Nous Research**) pioneered structured tool invocation, step-by-step planning, and continuous self-correction in autonomous coding agents.
* **Historical Implementation:** `CognitiveAgentRunner` abstracted the autonomous reasoning loop bound to the Hierarchical State Machine (`HSM`), enforcing per-sub-state turn budgets and *Deep History Node* ($H^*$) restoration.

### 3.3. Hierarchical State Machines (HSM)
* **Status:** Quarantined (`archive/v4-experimental/`)
* **Conceptual Origin:** Formally defined by computer scientist **David Harel** in his seminal 1987 paper (*"Statecharts: A Visual Formalism for Complex Systems"*), HSMs resolve the combinatorial explosion of states in complex reactive systems.
* **Historical Implementation:** `core/hsm_engine.py` modeled agent lifecycle states (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `ERROR`) and qualified sub-states; it now resides in `archive/v4-experimental/`.

### 3.4. Progressive Tool Disclosure Governance
* **Status:** Active in V4 Core (`core/mcp_governor.py`)
* **Conceptual Origin:** Anthropic's **Model Context Protocol (MCP)** specification combined with **Cloud Native Computing Foundation (CNCF)** API governance principles.
* **Implementation in Grafo Concierge:** `MCPToolGovernor` classifies all 31 registered MCP tools (`READ_ONLY`, `LOCAL_MUTATION`, `DANGEROUS`) and limits tool visibility and execution according to session state, defaulting fail-closed (`DANGEROUS`) for any unclassified tool.

### 3.5. Vector & Hybrid Storage
* **Status:** Active in V4 Core (`storage/base_backend.py`, `storage/vector_store.py`, `core/vector_backend.py`)
* **Conceptual Origin:** Open-source vector database pioneers and semantic similarity search research—including the **ChromaDB**, **Qdrant**, and **Sentence Transformers** (Hugging Face / UKPLab) ecosystems.
* **Implementation in Grafo Concierge:** The system standardizes on the `BaseVectorBackend` port, enabling plug-and-play interchangeability between ChromaDB (default) and Qdrant without modifying ingestion (`concierge_mine`), hybrid search (`core/hybrid_search.py`), or background Janitor reconciliation (`services/janitor.py`).

---

## 4. Ongoing Code Maintenance Guidelines

1. **New Modules and Classes:** Must always adopt functional, domain-neutral terminology (`VectorRepositoryPort`, `AgnosticCheckpointer`, `SemanticExtractor`, `MCPToolGovernor`).
2. **Mandatory Documentation:** Whenever a cutting-edge technique, academic paper, or open-source framework inspires an addition to the repository, its attribution, architectural credits, and lifecycle status must be recorded in this `ATTRIBUTION_AND_LINEAGE.md` document.
3. **Keep Tests Domain-Agnostic:** Test suites and fixtures must use generic identifiers (`primary_agent`, `secondary_agent`, `test_session`) rather than third-party or branded names.
