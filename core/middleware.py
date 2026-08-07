"""
core/middleware.py - Grafo Concierge v3.8.0 (Absolute Solidity)

The Central Facade - GrafoConcierge.

This is the class that the outside world consumes. It encapsulates ALL the
complexity of the internal layers (storage, ingestion, services, core)
into a clean, project-oriented public API.

Consumers of this class:
    - interface/mcp_server.py (MCP Server → Claude Desktop, Cursor)
    - interface/cli.py (Command Line Interface)
    - interface/action_hooks.py (Operational Modules)
    - Integration tests

Public methods:
    - register_project()  → Registers a new project in the graph
    - wake_up()           → Re-activates consciousness: compass + wings + commits
    - mine()              → Ingests files (concierge mine)
    - hybrid_search()     → Complete Hybrid Search v4
    - commit_memory()     → Registers consolidated changes
    - get_resume()        → Context Compass (concise summary)
    - lazy_load()         → On-demand node loading
    - delete_project()    → Cascaded project deletion
    - find_similar()      → Projects in the same wing
    - status()            → Project statistics

Principle: No internal class (SqliteStore, ChromaVectorStore, etc.)
is exposed to the outside world. Everything flows through this facade.
"""

from __future__ import annotations

import logging
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Optional

from core.config import ConciergeConfig, DEFAULT_CONFIG
from core.project_index import ProjectIndex
from core.hybrid_search import HybridSearchEngine
from core.memory_extractor import SemanticExtractor
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager
from ingestion.orchestrator import IngestionManager

logger = logging.getLogger("grafo-concierge.middleware")


class GrafoConcierge:
    """Central Facade of Grafo Concierge - unified public API.

    By instantiating this class, all subsystems are initialized
    automatically and interconnected.

    Args:
        sqlite_store: SqliteStore instance.
        vector_store: ChromaVectorStore instance.
        embedding_manager: EmbeddingManager instance.
        ingestion_manager: IngestionManager instance.
        config: Centralized parameters (default: DEFAULT_CONFIG).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        embedding_manager: EmbeddingManager,
        ingestion_manager: IngestionManager,
        config: ConciergeConfig = DEFAULT_CONFIG,
        llm_adapter: Any = None,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._embedder = embedding_manager
        self._ingestion = ingestion_manager
        self._config = config

        # Core submodules
        self._project_index = ProjectIndex(sqlite_store, config)
        self._search_engine = HybridSearchEngine(
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            embedding_manager=embedding_manager,
            project_index=self._project_index,
            config=config,
        )

        # Semantic Extraction Engine (requires LLM adapter)
        self._semantic_extractor: SemanticExtractor | None = (
            SemanticExtractor(llm_adapter) if llm_adapter else None
        )

        logger.info("GrafoConcierge (Fachada) inicializada com sucesso.")

    # ===================================================================
    # REGISTER — Registers a new project
    # ===================================================================

    def register_project(
        self,
        folder_name: str,
        wing: Optional[str] = None,
        privacy_level: str = "PUBLIC",
        summary: Optional[str] = None,
    ) -> str:
        """Registers a new project in the graph.

        If the project already exists (by folder_name), returns the existing UUID.
        Otherwise, generates a v4 UUID and creates the record.

        Args:
            folder_name: Source directory / project identifier.
            wing: Primary Wing (if None, it will be automatically categorized
                  after the first ingestion).
            privacy_level: Privacy level (PUBLIC, INTERNAL, RESTRICTED).
            summary: Initial description of the project.

        Returns:
            UUID of the project (new or existing).
        """
        # Checks if already exists
        try:
            existing = self._store.get_project(folder_name)
            logger.info("Projeto já existe: '%s' → %s", folder_name, existing["uuid"])
            return existing["uuid"]
        except Exception:
            pass

        project_uuid = str(uuid_lib.uuid4())
        primary_wing = wing or self._config.default_wing

        self._store.create_project(
            uuid=project_uuid,
            folder_name=folder_name,
            primary_wing=primary_wing,
            privacy_level=privacy_level,
            summary=summary,
        )

        logger.info(
            "Projeto registrado: '%s' → %s (wing='%s', privacy='%s')",
            folder_name, project_uuid, primary_wing, privacy_level,
        )
        return project_uuid

    # ===================================================================
    # WAKE UP — Re-activation of consciousness
    # ===================================================================

    def wake_up(self, project_uuid: str) -> dict:
        """Re-activates the agent's consciousness for a project.

        Returns the minimum context package necessary for the agent
        to resume work: Compass, Reference Wings, and last commits.

        Aligned with the MCP Tool concierge_wakeup.

        Args:
            project_uuid: Project UUID.

        Returns:
            Dict containing:
            {
                "project": dict (project data),
                "resume": str (Context Compass),
                "reference_wings": list[str],
                "recent_commits": list[dict],
                "stats": dict,
            }
        """
        project = self._store.get_project(project_uuid)
        ref_wings = self._project_index.get_reference_wings(project_uuid)
        recent_commits = self._store.get_recent_commits(project_uuid, limit=5)
        stats = self._store.get_project_stats(project_uuid)

        resume = project.get("summary", "")
        if not resume:
            resume = f"Projeto '{project.get('folder_name', 'unknown')}' — sem Bússola de Contexto definida."

        result = {
            "project": project,
            "resume": resume,
            "reference_wings": ref_wings,
            "recent_commits": recent_commits,
            "stats": stats,
        }

        logger.info(
            "Wake-up: projeto=%s, commits=%d, ref_wings=%d",
            project_uuid, len(recent_commits), len(ref_wings),
        )
        return result

    # ===================================================================
    # MINE — Ingestion of files
    # ===================================================================

    def mine(
        self,
        project_uuid: str,
        source_path: str,
        auto_tag: bool = True,
        auto_categorize: bool = True,
    ) -> dict:
        """Runs the complete ingestion pipeline (concierge mine).

        Delegates to IngestionManager and optionally re-categorizes
        the project's Primary Wing after ingestion.

        Args:
            project_uuid: Project UUID.
            source_path: Path to the source directory.
            auto_tag: Enable automatic tag detection.
            auto_categorize: Re-categorize wing after ingestion.

        Returns:
            Dict compatible with the MCP Tool concierge_mine response.
        """
        result = self._ingestion.mine(project_uuid, source_path, auto_tag)
        result_dict = result.to_dict()

        # Auto-categorization post-ingestion
        if auto_categorize and result_dict.get("nodes_created", 0) > 0:
            try:
                wing = self._project_index.auto_categorize_project(project_uuid)
                result_dict["auto_categorized_wing"] = wing
            except Exception as e:
                logger.warning("Auto-categorização falhou: %s", e)

        return result_dict

    # ===================================================================
    # SEARCH — Hybrid Search v4
    # ===================================================================

    def hybrid_search(
        self,
        query: str,
        project_uuid: str,
        top_k: Optional[int] = None,
        include_references: bool = False,
        all_wings: bool = False,
        node_type: Optional[str] = None,
    ) -> list[dict]:
        """Hybrid Search v4 — Complete Pipeline.

        Delegates tri-signal orchestration to HybridSearchEngine.
        Aligned with the MCP Tool concierge_search.

        Args:
            query: Search query.
            project_uuid: Anchor project UUID.
            top_k: Maximum results.
            include_references: Include Reference Wings.
            all_wings: Search in all wings.
            node_type: Surgical filter by node type.

        Returns:
            List of dicts with final_score and breakdown, sorted DESC.
        """
        return self._search_engine.search(
            query=query,
            project_uuid=project_uuid,
            top_k=top_k,
            include_references=include_references,
            all_wings=all_wings,
            node_type=node_type,
        )

    # ===================================================================
    # COMMIT — Consolidated changes registration
    # ===================================================================

    def commit_memory(
        self,
        project_uuid: str,
        phase: str,
        technical_changes: str,
        updated_pointers: list[str],
        node_ids: Optional[list[int]] = None,
    ) -> int:
        """Registers a memory commit in the graph.

        Each commit saves technical changes and updated pointers.
        If node_ids are provided, updates the last_commit_at of each node.

        Aligned with the MCP Tool concierge_commit.

        Args:
            project_uuid: Project UUID.
            phase: Current phase (planning, build, done, review).
            technical_changes: Description of technical changes.
            updated_pointers: List of updated pointers.
            node_ids: IDs of affected nodes (to update recency).

        Returns:
            ID of the created commit.
        """
        commit_id = self._store.create_commit(
            project_uuid=project_uuid,
            phase=phase,
            technical_changes=technical_changes,
            updated_pointers=updated_pointers,
        )

        # Update recency of affected nodes
        if node_ids:
            for nid in node_ids:
                try:
                    self._store.touch_node_commit(nid)
                except Exception as e:
                    logger.warning("Falha ao tocar recência do nó %d: %s", nid, e)

        logger.info(
            "Commit registrado: id=%d, projeto=%s, fase='%s', nós_afetados=%d",
            commit_id, project_uuid, phase, len(node_ids or []),
        )
        return commit_id

    # ===================================================================
    # RESUME — Context Compass
    # ===================================================================

    def get_resume(self, project_uuid: str) -> str:
        """Returns the Context Compass (concise summary) of the project.

        Aligned with the MCP Tool concierge_resume.

        Args:
            project_uuid: Project UUID.

        Returns:
            String with the project summary (max ~300 tokens).
        """
        project = self._store.get_project(project_uuid)
        resume = project.get("summary", "")

        if not resume:
            stats = self._store.get_project_stats(project_uuid)
            resume = (
                f"Projeto '{project.get('folder_name', 'unknown')}' "
                f"com {stats.get('total_nodes', 0)} nós e "
                f"{stats.get('total_edges', 0)} arestas. "
                f"Ala: {project.get('primary_wing', 'geral')}."
            )

        return resume

    # ===================================================================
    # LAZY LOAD — On-demand node loading
    # ===================================================================

    def lazy_load(self, node_id: int) -> dict:
        """Loads complete node data under demand.

        Updates the node's last_accessed to record the query.
        Aligned with the MCP Tool concierge_load.

        Args:
            node_id: ID of the node to load.

        Returns:
            Dict with all node fields + outgoing edges.
        """
        node = self._store.get_node(node_id)

        # Update last_accessed (relevant for Selective Amnesia)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self._store.update_node(node_id, last_accessed=now)

        # Load outgoing edges for context
        edges_out = self._store.get_edges_from(node_id)

        result = {
            **node,
            "edges_out": edges_out,
        }

        logger.debug("Lazy Load: nó=%d, arestas=%d", node_id, len(edges_out))
        return result

    # ===================================================================
    # DELETE — Project removal
    # ===================================================================

    def delete_project(self, project_uuid: str) -> None:
        """Removes a project and all associated data.

        Cascade: nodes, edges, trajectories, commits, and reference_wings.
        Also clears associated vectors in ChromaDB.

        Args:
            project_uuid: UUID of the project to remove.
        """
        # Remove vectors from ChromaDB before SQLite (needs node_ids)
        try:
            nodes = self._store.get_nodes_by_project(project_uuid)
            if nodes:
                doc_ids = [f"node_{n['id']}" for n in nodes]
                self._vector.delete_batch(doc_ids)
                logger.info("Vetores removidos: %d embeddings do projeto %s", len(doc_ids), project_uuid)
        except Exception as e:
            logger.warning("Falha ao limpar vetores do projeto %s: %s", project_uuid, e)

        # Remove from SQLite (CASCADE handles nodes, edges, etc.)
        self._store.delete_project(project_uuid)
        logger.info("Projeto removido: %s", project_uuid)

    # ===================================================================
    # SIMILAR — Projects in the same wing
    # ===================================================================

    def find_similar(
        self,
        project_uuid: str,
        limit: int = 5,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[dict]:
        """Searches similar projects by domain (same wing).

        Args:
            project_uuid: Anchor project UUID.
            limit: Maximum results.
            include_references: Include Reference Wings.
            all_wings: All wings.

        Returns:
            List of dicts with data of similar projects.
        """
        return self._project_index.find_similar_projects(
            project_uuid, limit, include_references, all_wings,
        )

    # ===================================================================
    # STATUS — Project statistics
    # ===================================================================

    def status(self, project_uuid: str) -> dict:
        """Returns complete project statistics.

        Aligned with the MCP Tool concierge_status.

        Args:
            project_uuid: Project UUID.

        Returns:
            Dict with counters for nodes, edges, commits, trajectories, etc.
        """
        project = self._store.get_project(project_uuid)
        stats = self._store.get_project_stats(project_uuid)
        ref_wings = self._project_index.get_reference_wings(project_uuid)
        last_phase = self._store.get_last_commit_phase(project_uuid)

        return {
            "project": project,
            "stats": stats,
            "reference_wings": ref_wings,
            "last_commit_phase": last_phase,
        }

    # ===================================================================
    # Submodule access (for advanced use / testing)
    # ===================================================================

    @property
    def project_index(self) -> ProjectIndex:
        """Access to ProjectIndex for advanced wing operations."""
        return self._project_index

    @property
    def search_engine(self) -> HybridSearchEngine:
        """Access to HybridSearchEngine for customized searches."""
        return self._search_engine

    @property
    def store(self) -> SqliteStore:
        """Access to SqliteStore (for advanced internal operations)."""
        return self._store

    def search_symbols(self, query: str, project_uuid: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Performs quick symbol search on FTS5."""
        return self._store.search_symbols(query, project_uuid, limit)

    def get_implementations(self, symbol_id: int) -> dict:
        """Returns the exact AST code block stored in the node."""
        node = self._store.get_node(symbol_id)
        return {
            "id": node["id"],
            "label": node["label"],
            "type": node["type"],
            "project_uuid": node["project_uuid"],
            "content": node.get("content"),
            "file_hash": node.get("file_hash"),
        }

    def get_callers(self, symbol_id: int) -> list[dict]:
        """Queries edges to return all calls to the symbol."""
        return self._store.get_callers(symbol_id)

    def get_full_topology(self, project_uuid: Optional[str] = None) -> dict[str, list[dict]]:
        """Returns the complete topology (nodes and edges) in a lightweight format."""
        return self._store.get_lightweight_topology(project_uuid)

    # ===================================================================
    # STORE FACT — Storing Semantic Facts via SemanticExtractor
    # ===================================================================

    def store_fact(
        self,
        scope_type: str,
        scope_id: str,
        fact_statement: str,
    ) -> list[dict]:
        """Stores a semantic fact in the graph via SemanticExtractor.

        The SemanticExtractor evaluates the fact against existing facts
        of the scope and decides: ADD, UPDATE, DELETE, or NOOP.

        Aligned with the MCP Tool concierge_store_fact.

        Args:
            scope_type: Scope type ('user', 'session', 'agent', 'org').
            scope_id: Unique identifier of the scope.
            fact_statement: Text of the fact/preference to store.

        Returns:
            List of dicts detailing the decisions made.

        Raises:
            RuntimeError: If SemanticExtractor is not configured.
        """
        if self._semantic_extractor is None:
            def _do_direct_store(conn) -> list[dict]:
                from storage.semantic_logic import insert_semantic_fact
                fact_id = insert_semantic_fact(conn, scope_type, scope_id, fact_statement.strip())
                return [{
                    "fact": fact_statement.strip(),
                    "action": "ADD",
                    "target_id": None,
                    "fact_id": fact_id
                }]
            results = self._store.write_callback(_do_direct_store)
            logger.info("store_fact (direct fallback): scope=%s/%s, fact_id=%s", scope_type, scope_id, results[0].get("fact_id"))
            return results

        def _do_store(conn) -> list[dict]:
            return self._semantic_extractor.evaluate_and_store_facts(
                conn=conn,
                scope_type=scope_type,
                scope_id=scope_id,
                new_facts=[fact_statement],
            )

        results = self._store.write_callback(_do_store)
        logger.info(
            "store_fact: scope=%s/%s, results=%d",
            scope_type, scope_id, len(results),
        )

        # Episodic vector synchronization if vector backend is QdrantVectorStore
        try:
            from core.vector_backend import QdrantVectorStore
            if isinstance(self._vector, QdrantVectorStore) and results:
                for fact in results:
                    fact_id = fact.get("id")
                    statement = fact.get("fact_statement")
                    if fact_id is not None and statement:
                        emb = self._embedder.embed(statement)
                        if emb:
                            metadata = {
                                "scope_type": scope_type,
                                "scope_id": scope_id,
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "utility_alpha": 1.0,
                                "utility_beta": 1.0,
                                "fact_id": fact_id,
                                "fact_statement": statement
                            }
                            self._vector.store_embedding(
                                doc_id=f"fact_{fact_id}",
                                embedding=emb,
                                metadata=metadata
                            )
                            logger.info("Semantic fact %d synchronized in Qdrant (episodic_memory).", fact_id)
        except Exception as q_err:
            logger.warning("Failed to synchronize semantic fact in Qdrant: %s", q_err)

        return results

    # ===================================================================
    # USER CORE MEMORY — Patch 1
    # ===================================================================

    def set_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
        content: str,
    ) -> int:
        """Stores or updates a core memory block of the user/session.

        Args:
            scope_type: 'user', 'session', 'agent', or 'org'.
            scope_id: Unique identifier of the scope.
            block_label: Label of the memory block.
            content: Content to store.

        Returns:
            ID of the inserted/updated record.
        """
        return self._store.set_core_memory(scope_type, scope_id, block_label, content)

    def get_core_memory_blocks(
        self,
        scope_type: str,
        scope_id: str,
        block_label: Optional[str] = None,
    ) -> list[dict]:
        """Returns core memory blocks for a scope.

        Args:
            scope_type: Scope type.
            scope_id: Unique identifier of the scope.
            block_label: If provided, returns only the specific block
                         (list with 0 or 1 element). If absent, returns all.

        Returns:
            List of dicts with the user_core_memory records.
        """
        if block_label:
            record = self._store.get_core_memory(scope_type, scope_id, block_label)
            return [record] if record else []
        return self._store.list_core_memory_blocks(scope_type, scope_id)

    # ===================================================================
    # BAYESIAN FEEDBACK LOOP — Patch 3
    # ===================================================================

    def update_fact_utility(self, fact_id: int, was_useful: bool) -> None:
        """Updates the Bayesian utility of a semantic_fact.

        Increments utility_alpha (success) or utility_beta (failure) of the fact,
        feeding Thompson Sampling in HybridSearchEngine.

        Args:
            fact_id: ID of the semantic fact.
            was_useful: True if the fact was useful, False otherwise.
        """
        from storage.semantic_logic import update_memory_utility

        def _do_update(conn) -> None:
            update_memory_utility(conn, fact_id, was_useful)

        self._store.write_callback(_do_update)
        logger.info(
            "update_fact_utility: fact_id=%d, was_useful=%s → %s atualizado.",
            fact_id, was_useful, "utility_alpha" if was_useful else "utility_beta",
        )

    # ===================================================================
    # MCP ARSENAL — Backend-6.1: Life Cycle + Telemetry + Vector
    # ===================================================================

    def update_project(self, project_uuid: str, **fields: Any) -> None:
        """Updates allowed fields of a project (registry).

        Args:
            project_uuid: Project UUID.
            **fields: Fields to update (folder_name, primary_wing,
                      privacy_level, summary).
        """
        self._store.update_project(project_uuid, **fields)
        logger.info("update_project: %s → campos=%s", project_uuid, list(fields.keys()))

    def add_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Associates a Reference Wing to the project.

        Args:
            project_uuid: Project UUID.
            wing_name: Wing name to associate.
        """
        self._store.add_reference_wing(project_uuid, wing_name)
        logger.info("add_reference_wing: %s → wing=%s", project_uuid, wing_name)

    def remove_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Removes a Reference Wing from the project.

        Args:
            project_uuid: Project UUID.
            wing_name: Wing name to remove.
        """
        self._store.remove_reference_wing(project_uuid, wing_name)
        logger.info("remove_reference_wing: %s → wing=%s", project_uuid, wing_name)

    def get_trajectories(self, project_uuid: str) -> list[dict]:
        """Retrieves the history of cognitive trajectories of the project.

        Args:
            project_uuid: Project UUID.

        Returns:
            List of dicts with the registered trajectories.
        """
        return self._store.get_trajectories(project_uuid)

    def count_embeddings(self, project_uuid: Optional[str] = None) -> int:
        """Returns the exact count of vectors in ChromaDB.

        Args:
            project_uuid: If provided, counts only for this project.

        Returns:
            Total number of stored embeddings.
        """
        return self._vector.count(project_uuid)

    def reset_collection(self) -> bool:
        """Destroys and recreates the vector collection (emergency repair).

        CAUTION: Destructive and irreversible operation. Will require re-ingestion.

        Returns:
            True if successful, False otherwise.
        """
        result = self._vector.reset_collection()
        if result:
            logger.warning("reset_collection: coleção vetorial destruída e recriada.")
        return result
