"""
interface/mcp_server.py — Grafo Concierge v3.8.0 (Absolute Solidity)

MCP (Model Context Protocol) server exposing Grafo Concierge tools
to LLM agents via FastMCP.

v3.8 REFACTOR: Now consumes exclusively the Central Facade
(core.middleware.GrafoConcierge) instead of instantiating loose internal
dependencies. All business logic has been moved to core/.

Tools exposed (6 tools — aligned with Architecture v3.8):
    concierge_mine     → Project ingestion (crawl → parse → store)
    concierge_search   → Hybrid Search v4 with Strict Scoping
    concierge_commit   → Audited alterations registration
    concierge_wakeup   → Consciousness reactivation (Compass + Wings)
    concierge_resume   → Context Compass (concise summary)
    concierge_load     → Lazy Load of a node on demand
    concierge_status   → System health and statistics
    concierge_store_fact  → Write semantic facts (via SemanticExtractor)
    concierge_list_facts  → Read active semantic facts for a scope

    SDD-08 Extensions (Standalone module-level functions):
    agent_save_checkpoint      → Persist agent state (AgnosticCheckpointer)
    agent_get_checkpoint       → Retrieve agent state (AgnosticCheckpointer)
    agent_list_checkpoints     → Time-Travel timeline (AgnosticCheckpointer)
    concierge_get_call_chain   → Recursive call chain (GraphRAGEngine)

Architecture:
    This module is ONLY the MCP bridge ↔ Central Facade.
    No business logic resides here. All operations are delegated
    to the GrafoConcierge class (core/middleware.py).
"""

from __future__ import annotations

import logging
import os
import time
import traceback
from typing import Optional

from mcp.server.fastmcp import FastMCP

from core.middleware import GrafoConcierge
from services import JanitorService

logger = logging.getLogger("grafo-concierge.mcp")


# ---------------------------------------------------------------------------
# SDD-08: Module-level sentinels for standalone MCP tool functions.
# These are injectable by tests (setUp) or by the application bootstrap.
# ---------------------------------------------------------------------------
db_manager = None        # type: ignore[assignment]
checkpointer = None      # type: ignore[assignment]
graph_rag = None         # type: ignore[assignment]


# ---------------------------------------------------------------------------
# GrafoConciergeServer — Encapsulation of FastMCP + Central Facade
# ---------------------------------------------------------------------------

class GrafoConciergeServer:
    """MCP Server of Grafo Concierge.

    Encapsulates FastMCP and registers tools with access to the Central Facade.
    Each tool is a closure that delegates to the GrafoConcierge instance.

    Args:
        concierge: Instance of the GrafoConcierge Central Facade.
        janitor: Instance of JanitorService (autonomous maintenance).
    """

    def __init__(
        self,
        concierge: GrafoConcierge,
        janitor: Optional[JanitorService] = None,
    ) -> None:
        self._gc = concierge
        self._janitor = janitor

        # Read environment variables for host and port (if any)
        host = os.environ.get("GRAFO_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("GRAFO_PORT", "8000"))
        except ValueError:
            port = 8000

        # Creates the FastMCP server
        self._mcp = FastMCP("Grafo Concierge", host=host, port=port)

        # Enables CORS and optional API Key Authentication on Starlette sse_app
        original_sse_app = self._mcp.sse_app
        def custom_sse_app(*args, **kwargs):
            app = original_sse_app(*args, **kwargs)
            from starlette.middleware.cors import CORSMiddleware
            from starlette.responses import JSONResponse
            
            cfg = getattr(self._gc, "config", None)
            api_key = (getattr(cfg, "api_key", None) if cfg else None) or os.environ.get("GRAFO_API_KEY")
            cors_origins_env = os.environ.get("GRAFO_CORS_ORIGINS")
            if cors_origins_env:
                origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
            elif cfg and hasattr(cfg, "cors_origins"):
                origins = list(cfg.cors_origins)
            else:
                origins = ["*"]

            # 1. API Key Authentication Middleware (if configured)
            if api_key:
                @app.middleware("http")
                async def auth_middleware(request, call_next):
                    # Check Authorization header (Bearer token) or query param ?token=
                    auth_header = request.headers.get("Authorization", "")
                    token_param = request.query_params.get("token", "")
                    
                    is_valid = False
                    if auth_header.startswith("Bearer "):
                        is_valid = (auth_header[7:].strip() == api_key)
                    elif token_param:
                        is_valid = (token_param.strip() == api_key)

                    if not is_valid:
                        return JSONResponse({"error": "Unauthorized access to Grafo Concierge MCP"}, status_code=401)
                    return await call_next(request)

            # 2. CORS Middleware
            allow_creds = True if origins != ["*"] else False
            app.add_middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=allow_creds,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            return app
        self._mcp.sse_app = custom_sse_app

        # Registers the tools
        self._register_tools()


        tool_count = len(self._mcp._tool_manager.list_tools())
        logger.info("GrafoConciergeServer initialized — %d tools registered.", tool_count)

    @property
    def mcp(self) -> FastMCP:
        """Direct access to FastMCP (for run/mount)."""
        return self._mcp

    # ===================================================================
    # TOOL REGISTRATION
    # ===================================================================

    def _register_tools(self) -> None:
        """Registers all MCP tools as closures with access to self."""

        server = self

        # --- concierge_register ---
        @self._mcp.tool(
            name="concierge_register",
            description=(
                "Registers a new project and defines Privacy Level."
            ),
        )
        def concierge_register(
            project_path: str,
            wing: str = "geral",
            privacy_level: str = "PUBLIC",
            summary: Optional[str] = None,
        ) -> dict:
            """Registers a new project in Grafo Concierge.

            Args:
                project_path: Path or directory name of the project.
                wing: Main wing (Primary Wing). Default: "geral".
                privacy_level: Privacy level (PUBLIC, INTERNAL, RESTRICTED).
                summary: Optional description.

            Returns:
                Dictionary with the generated UUID and status.
            """
            return server._handle_register(project_path, wing, privacy_level, summary)

        # --- concierge_list_projects ---
        @self._mcp.tool(
            name="concierge_list_projects",
            description=(
                "Returns the list of all registered projects in Grafo Concierge, "
                "mapping Project Name -> UUID and Update Date."
            ),
        )
        def concierge_list_projects() -> dict:
            """Returns all Name -> UUID matches of the projects."""
            return server._handle_list_projects()

        # --- concierge_mine ---
        @self._mcp.tool(
            name="concierge_mine",
            description=(
                "Ingests a project from the filesystem into the Memory Graph. "
                "Crawls the directory, parses files (AST/Semantic), "
                "generates recursive summaries (L0/L1/L2), stores embeddings "
                "and synchronizes SQLite + Qdrant. Returns complete report."
            ),
        )
        def concierge_mine(
            path: str,
            project_identifier: str,
            auto_tag: bool = True,
        ) -> dict:
            """Ingests a project in the Memory Graph.

            Args:
                path: Absolute path of the directory to ingest.
                project_identifier: Readable name of the project or its UUID.
                auto_tag: If True, extracts tags automatically from files.

            Returns:
                Dictionary with ingestion report (MCP-compatible).
            """
            return server._handle_mine(path, project_identifier, auto_tag)

        # --- concierge_search ---
        @self._mcp.tool(
            name="concierge_search",
            description=(
                "Hybrid search in the Memory Graph combining vector similarity "
                "(cosine), frequency (FTS5/BM25) and graph signals "
                "(recency, centrality). Returns the most relevant chunks "
                "ranked by hybrid score."
            ),
        )
        def concierge_search(
            query: str,
            project_identifier: str = "",
            top_k: int = 10,
            node_type: Optional[str] = None,
            include_references: bool = False,
            all_wings: bool = False,
        ) -> dict:
            """Hybrid search in the Memory Graph.

            Args:
                query: Natural language query text.
                project_identifier: UUID or name of the project for Strict Scoping.
                                   Optional when all_wings=True.
                top_k: Maximum number of results (default: 10).
                node_type: Optional filter for node type (FACT, SKILL, etc.).
                include_references: Include Reference Wings in scope.
                all_wings: Search in all wings (ignores Strict Scoping).

            Returns:
                Dictionary with ranked results and metadata.
            """
            return server._handle_search(
                query, project_identifier, top_k, node_type,
                include_references, all_wings,
            )

        # --- concierge_commit ---
        @self._mcp.tool(
            name="concierge_commit",
            description=(
                "Registers consolidated changes in the Memory Graph. "
                "Writes to the commit_log table, updates recency of affected "
                "nodes, and audits via Critical Reviewer."
            ),
        )
        def concierge_commit(
            project_uuid: str,
            phase: str,
            technical_changes: str,
            updated_pointers: list[str],
            node_ids: Optional[list[int]] = None,
        ) -> dict:
            """Registers an audited memory commit.

            Args:
                project_uuid: UUID of the project.
                phase: Current phase (planning, build, done, review).
                technical_changes: Description of the technical changes.
                updated_pointers: List of updated pointers.
                node_ids: IDs of the affected nodes (updates recency).

            Returns:
                Dictionary with commit ID and status.
            """
            return server._handle_commit(
                project_uuid, phase, technical_changes,
                updated_pointers, node_ids,
            )

        # --- concierge_wakeup ---
        @self._mcp.tool(
            name="concierge_wakeup",
            description=(
                "Reactivates agent consciousness for a project. "
                "Returns the Context Compass, Reference Wings, "
                "latest commits and statistics."
            ),
        )
        def concierge_wakeup(project_uuid: str) -> dict:
            """Agent consciousness reactivation.

            Args:
                project_uuid: UUID of the project.

            Returns:
                Dictionary with Compass, Wings, commits and stats.
            """
            return server._handle_wakeup(project_uuid)

        # --- concierge_resume ---
        @self._mcp.tool(
            name="concierge_resume",
            description=(
                "Returns the Context Compass (concise summary) "
                "of the project. Ideal for system prompt injection."
            ),
        )
        def concierge_resume(project_uuid: str) -> dict:
            """Context Compass of the project.

            Args:
                project_uuid: UUID of the project.

            Returns:
                Dictionary with summary and basic statistics.
            """
            return server._handle_resume(project_uuid)

        # --- concierge_load ---
        @self._mcp.tool(
            name="concierge_load",
            description=(
                "Loads complete node data on demand (Lazy Load). "
                "Returns content, tags, edges and node metadata."
            ),
        )
        def concierge_load(node_id: int) -> dict:
            """Loads a complete node on demand.

            Args:
                node_id: ID of the node to load.

            Returns:
                Dictionary with all fields and edges of the node.
            """
            return server._handle_load(node_id)

        # --- concierge_status ---
        @self._mcp.tool(
            name="concierge_status",
            description=(
                "Returns health status of Grafo Concierge: "
                "project statistics, Qdrant health, latest Janitor "
                "report and pipeline metrics."
            ),
        )
        def concierge_status(
            project_uuid: Optional[str] = None,
        ) -> dict:
            """System health status.

            Args:
                project_uuid: UUID of the project (optional). If omitted,
                              returns global status.

            Returns:
                Dictionary with health metrics and statistics.
            """
            return server._handle_status(project_uuid)

        # --- search_symbols ---
        @self._mcp.tool(
            name="search_symbols",
            description=(
                "Performs fast search of symbol signatures (classes/functions) "
                "in the FTS5 index of Grafo Concierge."
            ),
        )
        def search_symbols(
            query: str,
            project_uuid: Optional[str] = None,
        ) -> dict:
            """Searches code symbols by name in the FTS5 index.

            Args:
                query: Text or symbol name to search.
                project_uuid: UUID of the project (optional).

            Returns:
                Dictionary with list of symbols and details.
            """
            return server._handle_search_symbols(query, project_uuid)

        # --- get_implementations ---
        @self._mcp.tool(
            name="get_implementations",
            description=(
                "Returns implementation (AST code block) corresponding to a symbol node."
            ),
        )
        def get_implementations(symbol_id: int) -> dict:
            """Returns the implementation of a symbol node.

            Args:
                symbol_id: Numeric ID of the symbol node.

            Returns:
                Dictionary with the symbol implementation (code).
            """
            return server._handle_get_implementations(symbol_id)

        # --- get_callers ---
        @self._mcp.tool(
            name="get_callers",
            description=(
                "Returns all callers of a symbol node by analyzing the Graph edges."
            ),
        )
        def get_callers(symbol_id: int) -> dict:
            """Returns callers of a symbol.

            Args:
                symbol_id: Numeric ID of the symbol node.

            Returns:
                Dictionary with callers and relationship details.
            """
            return server._handle_get_callers(symbol_id)

        # --- concierge_store_fact ---
        @self._mcp.tool(
            name="concierge_store_fact",
            description=(
                "Writes a semantic fact to the Memory Graph via SemanticExtractor. "
                "Extractor evaluates fact against existing scope and decides: "
                "ADD, UPDATE, DELETE or NOOP (bi-temporal)."
            ),
        )
        def concierge_store_fact(
            scope_type: str,
            scope_id: str,
            fact_statement: str,
        ) -> dict:
            """Writes a semantic fact to the graph.

            Args:
                scope_type: Scope type ('user', 'session', 'agent', 'org').
                scope_id: Unique identifier of scope.
                fact_statement: Fact/preference text to write.

            Returns:
                Dictionary with decisions made by SemanticExtractor.
            """
            return server._handle_store_fact(scope_type, scope_id, fact_statement)

        # --- concierge_list_facts ---
        @self._mcp.tool(
            name="concierge_list_facts",
            description=(
                "Lists all active semantic facts for a given scope. "
                "Returns facts stored via concierge_store_fact that are still valid "
                "(not invalidated). Use to review stored preferences, decisions, and context. "
                "IMPORTANT: Each fact object contains a stable 'id' field (the database primary key). "
                "Always reference facts by this 'id' (e.g., 'Fact #<id>'). "
                "Never use list position or sequential counting — IDs may have gaps due to "
                "bi-temporal invalidation of superseded facts."
            ),
        )
        def concierge_list_facts(
            scope_type: str,
            scope_id: str,
        ) -> dict:
            """Lists active semantic facts for a scope.

            Args:
                scope_type: Scope type ('user', 'session', 'agent', 'org').
                scope_id: Unique identifier of scope.

            Returns:
                Dictionary with success, facts list, and count.
            """
            return server._handle_list_facts(scope_type, scope_id)

        # --- concierge_set_memory ---
        @self._mcp.tool(
            name="concierge_set_memory",
            description=(
                "Writes or updates a persistent core memory block (user_core_memory). "
                "Use to store preferences, settings, and permanent context of the user/session."
            ),
        )
        def concierge_set_memory(
            scope_type: str,
            scope_id: str,
            block_label: str,
            content: str,
        ) -> dict:
            """Writes a persistent core memory block.

            Args:
                scope_type: Scope type ('user', 'session', 'agent', 'org').
                scope_id: Unique identifier of scope.
                block_label: Block label (e.g. 'preferred_language', 'persona_name').
                content: Content to store in the block.

            Returns:
                Dictionary with success and memory_id of the record.
            """
            return server._handle_set_memory(scope_type, scope_id, block_label, content)

        # --- concierge_get_memory ---
        @self._mcp.tool(
            name="concierge_get_memory",
            description=(
                "Queries persistent core memory blocks. "
                "If block_label is provided, returns only that block. "
                "If omitted, returns all blocks of the scope."
            ),
        )
        def concierge_get_memory(
            scope_type: str,
            scope_id: str,
            block_label: Optional[str] = None,
        ) -> dict:
            """Queries core memory blocks.

            Args:
                scope_type: Scope type ('user', 'session', 'agent', 'org').
                scope_id: Unique identifier of scope.
                block_label: Specific label (optional). If absent, returns all.

            Returns:
                Dictionary with success and list of blocks.
            """
            return server._handle_get_memory(scope_type, scope_id, block_label)

        # --- concierge_feedback ---
        @self._mcp.tool(
            name="concierge_feedback",
            description=(
                "Registers utility feedback on a semantic fact (semantic_fact). "
                "Triggers Bayesian learning: increments utility_alpha (success) or "
                "utility_beta (failure), feeding Thompson Sampling of hybrid search."
            ),
        )
        def concierge_feedback(
            fact_id: int,
            was_useful: bool,
        ) -> dict:
            """Registers utility feedback of a semantic fact.

            Args:
                fact_id: ID of the semantic_fact to evaluate (id field returned by concierge_store_fact).
                was_useful: True if the fact was useful in the response, False otherwise.

            Returns:
                Dictionary with success, fact_id, was_useful and message.
            """
            return server._handle_feedback(fact_id, was_useful)

        # --- get_full_topology ---
        @self._mcp.tool(
            name="get_full_topology",
            description=(
                "Returns the complete topology of nodes and edges (call graph, "
                "symbols, files and dependencies) in an ultra-lean way. "
                "Used by the Web Dashboard for real-time 3D visualizations. "
                "Does not include text summaries or embeddings."
            ),
        )
        def get_full_topology(
            project_identifier: Optional[str] = None,
        ) -> dict:
            """Returns the complete topology of nodes and edges in the database.

            Args:
                project_identifier: Optional project UUID or name to filter the data.

            Returns:
                Dictionary containing success, list of nodes and list of edges.
            """
            return server._handle_get_full_topology(project_identifier)

        # --- delete_project ---
        @self._mcp.tool(
            name="delete_project",
            description=(
                "Physically removes a project and all linked records, "
                "including nodes, edges, commits, trajectories and associated embeddings."
            ),
        )
        def delete_project(project_identifier: str) -> dict:
            """Removes a project and all its cascading data.

            Args:
                project_identifier: UUID or directory name of the project.
            """
            return server._handle_delete_project(project_identifier)

        # --- update_project ---
        @self._mcp.tool(
            name="update_project",
            description=(
                "Updates permitted cadastral fields of a project "
                "(folder_name, primary_wing, privacy_level, summary)."
            ),
        )
        def update_project(
            project_identifier: str,
            folder_name: Optional[str] = None,
            primary_wing: Optional[str] = None,
            privacy_level: Optional[str] = None,
            summary: Optional[str] = None,
        ) -> dict:
            """Updates a project registration.

            Args:
                project_identifier: UUID or directory name of the project.
                folder_name: New directory name (optional).
                primary_wing: New primary wing of the project (optional).
                privacy_level: Privacy level (PUBLIC, INTERNAL, RESTRICTED) (optional).
                summary: New descriptive summary of the project (optional).
            """
            return server._handle_update_project(
                project_identifier, folder_name, primary_wing, privacy_level, summary
            )

        # --- add_reference_wing ---
        @self._mcp.tool(
            name="add_reference_wing",
            description="Associates a recommended reference wing (Reference Wing) with a project.",
        )
        def add_reference_wing(project_identifier: str, wing_name: str) -> dict:
            """Associates a recommended wing with the project.

            Args:
                project_identifier: UUID or directory name of the project.
                wing_name: Name of the wing to associate.
            """
            return server._handle_add_reference_wing(project_identifier, wing_name)

        # --- remove_reference_wing ---
        @self._mcp.tool(
            name="remove_reference_wing",
            description="Removes an associated reference wing (Reference Wing) from a project.",
        )
        def remove_reference_wing(project_identifier: str, wing_name: str) -> dict:
            """Removes an associated wing from the project.

            Args:
                project_identifier: UUID or directory name of the project.
                wing_name: Name of the wing to remove.
            """
            return server._handle_remove_reference_wing(project_identifier, wing_name)

        # --- find_similar ---
        @self._mcp.tool(
            name="find_similar",
            description="Searches other registered projects that share the same domain of technical expertise.",
        )
        def find_similar(
            project_identifier: str,
            limit: int = 5,
            include_references: bool = False,
            all_wings: bool = False,
        ) -> dict:
            """Searches similar projects in the same technical wing.

            Args:
                project_identifier: UUID or directory name of the anchor project.
                limit: Maximum limit of projects returned (default: 5).
                include_references: If True, includes reference wings in search.
                all_wings: If True, searches in all wings indistinctly.
            """
            return server._handle_find_similar(project_identifier, limit, include_references, all_wings)

        # --- get_trajectories ---
        @self._mcp.tool(
            name="get_trajectories",
            description="Retrieves the detailed history of cognitive trajectories and previous navigation steps of the project.",
        )
        def get_trajectories(project_identifier: str) -> dict:
            """Retrieves history of cognitive trajectories.

            Args:
                project_identifier: UUID or directory name of the project.
            """
            return server._handle_get_trajectories(project_identifier)

        # --- count_embeddings ---
        @self._mcp.tool(
            name="count_embeddings",
            description="Returns the exact count of vectors (embeddings) stored in the vector collection.",
        )
        def count_embeddings(project_identifier: Optional[str] = None) -> dict:
            """Counts collection vectors.

            Args:
                project_identifier: If provided, filters and counts only vectors of this project.
            """
            return server._handle_count_embeddings(project_identifier)

        # --- reset_collection ---
        @self._mcp.tool(
            name="reset_collection",
            description=(
                "Destroys and recreates the physical vector collection (emergency repair). "
                "WARNING: Irreversible operation that deletes ALL vectors!"
            ),
        )
        def reset_collection() -> dict:
            """Destroys and recreates the collection of vectors."""
            return server._handle_reset_collection()

    def _resolve_project_identifier(self, project_identifier: str) -> str:
        """Resolves project_identifier (UUID or folder_name) to project_uuid.
        
        Raises ValueError if the name is not found in the database.
        """
        import uuid
        try:
            uuid.UUID(project_identifier)
            return project_identifier
        except ValueError:
            pass

        try:
            project = self._gc.store.get_project(project_identifier)
            return project["uuid"]
        except Exception:
            raise ValueError(
                f"Project '{project_identifier}' not found. "
                "Please list available projects using concierge_list_projects."
            )

    # ===================================================================
    # HANDLER: concierge_list_projects
    # ===================================================================

    def _handle_list_projects(self) -> dict:
        """Handler for concierge_list_projects."""
        t0 = time.perf_counter()
        try:
            projects = self._gc.store.list_projects()
            formatted = {}
            for p in projects:
                name = p["folder_name"]
                updated = p["updated_at"][:10] if p["updated_at"] else ""
                formatted[name] = {"uuid": p["uuid"], "updated_at": updated}
            
            elapsed = time.perf_counter() - t0
            return {
                "success": True,
                "projects": formatted,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_list_projects FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "projects": {},
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_register
    # ===================================================================

    def _handle_register(
        self, project_path: str, wing: str, privacy_level: str, summary: Optional[str]
    ) -> dict:
        """Handler for concierge_register — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            folder_name = os.path.basename(project_path.strip(r"\/")) or project_path
            
            project_uuid = self._gc.register_project(
                folder_name=folder_name,
                wing=wing,
                privacy_level=privacy_level,
                summary=summary or f"Project registered via MCP: {folder_name}",
            )

            elapsed = time.perf_counter() - t0
            logger.info(
                "concierge_register OK: %s → %s (wing=%s, privacy=%s), %.3fs",
                folder_name, project_uuid, wing, privacy_level, elapsed,
            )

            return {
                "success": True,
                "project_uuid": project_uuid,
                "folder_name": folder_name,
                "wing": wing,
                "privacy_level": privacy_level,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_register FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_mine
    # ===================================================================

    def _handle_mine(
        self, path: str, project_identifier: str, auto_tag: bool,
    ) -> dict:
        """Handler for concierge_mine — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            import uuid
            is_uuid = False
            try:
                uuid.UUID(project_identifier)
                is_uuid = True
            except ValueError:
                pass

            if is_uuid:
                project_uuid = project_identifier
                try:
                    project = self._gc.store.get_project(project_uuid)
                    project_name = project["folder_name"]
                except Exception:
                    project_name = os.path.basename(path.rstrip(r"\/")) or project_uuid
                    # Registers if it does not exist
                    self._gc.register_project(
                        folder_name=project_name,
                        summary=f"Project ingested from: {path}",
                    )
            else:
                try:
                    project = self._gc.store.get_project(project_identifier)
                    project_uuid = project["uuid"]
                    project_name = project["folder_name"]
                except Exception:
                    raise ValueError(
                        f"Project '{project_identifier}' not found. "
                        "Please list available projects using concierge_list_projects."
                    )

            # Signals Idle-Lock for the Janitor
            if self._janitor:
                self._janitor.signal_mine_start()

            try:
                result = self._gc.mine(project_uuid, path, auto_tag=auto_tag)
            finally:
                if self._janitor:
                    self._janitor.signal_mine_end()

            elapsed = time.perf_counter() - t0
            result["project_uuid"] = project_uuid
            result["project_name"] = project_name
            result["path"] = path
            result["duration_seconds"] = round(elapsed, 3)
            result["success"] = True

            logger.info(
                "concierge_mine OK: %s → %d files, %d nodes, %.2fs",
                project_name, result.get("files_processed", 0),
                result.get("nodes_created", 0), elapsed,
            )
            return result

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_mine FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "project_name": project_identifier,
                "path": path,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_search
    # ===================================================================

    def _handle_search(
        self,
        query: str,
        project_identifier: str,
        top_k: int,
        node_type: Optional[str],
        include_references: bool,
        all_wings: bool,
    ) -> dict:
        """Handler for concierge_search — delegates to Facade."""
        t0 = time.perf_counter()

        logger.info(
            "[concierge_search] query='%.60s' project_identifier=%r "
            "top_k=%d all_wings=%s",
            query, project_identifier, top_k, all_wings,
        )

        try:
            # When all_wings=True and no project_identifier is given, skip
            # UUID resolution — the search spans every wing anyway.
            if all_wings and not project_identifier:
                project_uuid = ""
            else:
                # Transparent resolution of project_identifier
                project_uuid = self._resolve_project_identifier(project_identifier)

            results = self._gc.hybrid_search(
                query=query,
                project_uuid=project_uuid,
                top_k=top_k,
                include_references=include_references,
                all_wings=all_wings,
                node_type=node_type,
            )

            # Enriches with node data for MCP response
            enriched = []
            for item in results:
                try:
                    node = self._gc.store.get_node(item["node_id"])
                    breakdown = item.get("score_breakdown", {})
                    enriched.append({
                        "node_id": item["node_id"],
                        "label": node.get("label", ""),
                        "summary": node.get("summary", ""),
                        "node_type": node.get("node_type", ""),
                        "tags": node.get("tags", []),
                        "hybrid_score": round(item.get("score_final", 0), 4),
                        "vector_score": round(breakdown.get("vetorial", 0), 4),
                        "fts_score": round(breakdown.get("frequencia", 0), 4),
                        "recency_score": round(breakdown.get("recencia", 0), 4),
                        "centrality_score": round(breakdown.get("centralidade", 0), 4),
                        "is_super_node": item.get("is_super_node", False),
                    })
                except Exception:
                    logger.debug("Node %d not found in enrichment.", item.get("node_id"))

            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_search OK: query='%.40s' → %d results, %.3fs",
                query, len(enriched), elapsed,
            )

            return {
                "success": True,
                "query": query,
                "project_uuid": project_uuid,
                "results_count": len(enriched),
                "results": enriched,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_search FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "project_uuid": project_identifier,
                "results": [],
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_commit
    # ===================================================================

    def _handle_commit(
        self,
        project_uuid: str,
        phase: str,
        technical_changes: str,
        updated_pointers: list[str],
        node_ids: Optional[list[int]],
    ) -> dict:
        """Handler for concierge_commit — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            commit_id = self._gc.commit_memory(
                project_uuid=project_uuid,
                phase=phase,
                technical_changes=technical_changes,
                updated_pointers=updated_pointers,
                node_ids=node_ids,
            )

            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_commit OK: id=%d, project=%s, phase='%s', %.3fs",
                commit_id, project_uuid, phase, elapsed,
            )

            return {
                "success": True,
                "commit_id": commit_id,
                "project_uuid": project_uuid,
                "phase": phase,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_commit FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "project_uuid": project_uuid,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_wakeup
    # ===================================================================

    def _handle_wakeup(self, project_uuid: str) -> dict:
        """Handler for concierge_wakeup — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            result = self._gc.wake_up(project_uuid)
            elapsed = time.perf_counter() - t0

            result["success"] = True
            result["duration_seconds"] = round(elapsed, 3)

            logger.info(
                "concierge_wakeup OK: project=%s, %.3fs", project_uuid, elapsed,
            )
            return result

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_wakeup FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "project_uuid": project_uuid,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_resume
    # ===================================================================

    def _handle_resume(self, project_uuid: str) -> dict:
        """Handler for concierge_resume — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            resume = self._gc.get_resume(project_uuid)
            project = self._gc.store.get_project(project_uuid)
            stats = self._gc.store.get_project_stats(project_uuid)
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_resume OK: project=%s, %.3fs", project_uuid, elapsed,
            )

            return {
                "success": True,
                "project_uuid": project_uuid,
                "folder_name": project.get("folder_name", ""),
                "primary_wing": project.get("primary_wing", "geral"),
                "resume": resume,
                "stats": stats,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_resume FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "project_uuid": project_uuid,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_load
    # ===================================================================

    def _handle_load(self, node_id: int) -> dict:
        """Handler for concierge_load — delegates to Facade."""
        t0 = time.perf_counter()

        try:
            result = self._gc.lazy_load(node_id)
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_load OK: node_id=%d, %.3fs", node_id, elapsed,
            )

            return {
                "success": True,
                "node": result,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_load FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "node_id": node_id,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_status
    # ===================================================================

    def _handle_status(self, project_uuid: Optional[str]) -> dict:
        """Handler for concierge_status — delegates to Facade + components."""
        t0 = time.perf_counter()

        try:
            status: dict = {
                "success": True,
                "system": "Grafo Concierge v3.8.0",
                "components": {},
            }

            # --- SQLite Health ---
            try:
                projects = self._gc.store.list_projects()
                status["components"]["sqlite"] = {
                    "status": "healthy",
                    "total_projects": len(projects),
                }
            except Exception as e:
                status["components"]["sqlite"] = {
                    "status": "degraded",
                    "error": str(e),
                }

            # --- Janitor ---
            if self._janitor:
                last = self._janitor.last_reports
                janitor_status = {
                    "status": "active" if self._janitor.is_running else "idle",
                    "total_runs": len(last),
                }
                if last:
                    janitor_status["last_report"] = last[-1].to_dict()
                status["components"]["janitor"] = janitor_status
            else:
                status["components"]["janitor"] = {"status": "not_configured"}

            # --- Project Stats (if UUID provided) ---
            if project_uuid:
                try:
                    project_status = self._gc.status(project_uuid)
                    status["project"] = project_status
                except Exception as e:
                    status["project"] = {
                        "uuid": project_uuid,
                        "error": str(e),
                    }

            elapsed = time.perf_counter() - t0
            status["duration_seconds"] = round(elapsed, 3)

            logger.info("concierge_status OK in %.3fs", elapsed)
            return status

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_status FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: search_symbols
    # ===================================================================

    def _handle_search_symbols(self, query: str, project_uuid: Optional[str] = None) -> dict:
        """Handler for search_symbols."""
        t0 = time.perf_counter()
        try:
            results = self._gc.store.fts_search(query, project_uuid=project_uuid)
            formatted = []
            for r in results:
                formatted.append({
                    "id": r["id"],
                    "label": r["label"],
                    "node_type": r["node_type"],
                    "file_path": r.get("label", ""),
                    "summary": r.get("summary", ""),
                })
            elapsed = time.perf_counter() - t0
            return {
                "success": True,
                "symbols": formatted,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("search_symbols FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_implementations
    # ===================================================================

    def _handle_get_implementations(self, symbol_id: int) -> dict:
        """Handler for get_implementations — delegates to Central Facade."""
        t0 = time.perf_counter()
        try:
            impl = self._gc.get_implementations(symbol_id)
            elapsed = time.perf_counter() - t0
            return {
                "success": True,
                "symbol_id": symbol_id,
                "label": impl.get("label", ""),
                "type": impl.get("type", ""),
                "implementation": impl.get("content", ""),
                "project_uuid": impl.get("project_uuid", ""),
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("get_implementations FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_callers
    # ===================================================================

    def _handle_get_callers(self, symbol_id: int) -> dict:
        """Handler for get_callers."""
        t0 = time.perf_counter()
        try:
            edges = self._gc.store.get_edges_to(symbol_id)
            callers = []
            for edge in edges:
                try:
                    source_node = self._gc.store.get_node(edge["source_id"])
                    callers.append({
                        "id": source_node["id"],
                        "label": source_node["label"],
                        "node_type": source_node["node_type"],
                        "relation_type": edge["relation_type"],
                    })
                except Exception:
                    pass
            elapsed = time.perf_counter() - t0
            return {
                "success": True,
                "symbol_id": symbol_id,
                "callers": callers,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("get_callers FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_store_fact
    # ===================================================================

    def _handle_store_fact(
        self, scope_type: str, scope_id: str, fact_statement: str,
    ) -> dict:
        """Handler for concierge_store_fact — delegates to Facade with fail-fast validation."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"Invalid scope_type '{scope_type}'. Must be one of: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id cannot be empty.")
            if not fact_statement or not fact_statement.strip():
                raise ValueError("fact_statement cannot be empty.")

            results = self._gc.store_fact(
                scope_type=scope_type,
                scope_id=scope_id,
                fact_statement=fact_statement,
            )
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_store_fact OK: scope=%s/%s, decisions=%d, %.3fs",
                scope_type, scope_id, len(results), elapsed,
            )

            return {
                "success": True,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "decisions": results,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_store_fact FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "scope_type": scope_type,
                "scope_id": scope_id,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_list_facts
    # ===================================================================

    def _handle_list_facts(
        self, scope_type: str, scope_id: str,
    ) -> dict:
        """Handler for concierge_list_facts — delegates to Facade."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"Invalid scope_type '{scope_type}'. Must be one of: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id cannot be empty.")

            facts = self._gc.list_facts(
                scope_type=scope_type,
                scope_id=scope_id,
            )
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_list_facts OK: scope=%s/%s, count=%d, %.3fs",
                scope_type, scope_id, len(facts), elapsed,
            )

            return {
                "success": True,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "facts_count": len(facts),
                "facts": facts,
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_list_facts FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "scope_type": scope_type,
                "scope_id": scope_id,
                "facts": [],
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # RUN — Server initialization
    # ===================================================================

    def run(self, transport: str = "stdio") -> None:
        """Starts the MCP server.

        Args:
            transport: Transport type ('stdio' or 'sse').
        """
        import asyncio
        logger.info("Starting Grafo Concierge MCP Server (transport=%s)...", transport)

        async def _run_server():
            if transport == "sse":
                await self._mcp.run_sse_async()
            else:
                await self._mcp.run_stdio_async()

        try:
            asyncio.run(_run_server())
        except KeyboardInterrupt:
            logger.info("Server stopped by user interrupt.")

    # ===================================================================
    # HANDLER: concierge_set_memory
    # ===================================================================

    def _handle_set_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
        content: str,
    ) -> dict:
        """Handler for concierge_set_memory — delegates to Facade with fail-fast validation."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"Invalid scope_type '{scope_type}'. Must be one of: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id cannot be empty.")
            if not block_label or not block_label.strip():
                raise ValueError("block_label cannot be empty.")
            if not content or not content.strip():
                raise ValueError("content cannot be empty.")

            memory_id = self._gc.set_core_memory(
                scope_type=scope_type,
                scope_id=scope_id,
                block_label=block_label,
                content=content,
            )
            elapsed = time.perf_counter() - t0
            logger.info(
                "concierge_set_memory OK: scope=%s/%s, label=%s, id=%s, %.3fs",
                scope_type, scope_id, block_label, memory_id, elapsed,
            )
            return {
                "success": True,
                "memory_id": memory_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "block_label": block_label,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_set_memory FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "scope_type": scope_type,
                "scope_id": scope_id,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_get_memory
    # ===================================================================

    def _handle_get_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: Optional[str],
    ) -> dict:
        """Handler for concierge_get_memory — delegates to Facade with fail-fast validation."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"Invalid scope_type '{scope_type}'. Must be one of: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id cannot be empty.")

            blocks = self._gc.get_core_memory_blocks(
                scope_type=scope_type,
                scope_id=scope_id,
                block_label=block_label,
            )
            elapsed = time.perf_counter() - t0
            logger.info(
                "concierge_get_memory OK: scope=%s/%s, label=%s, blocks=%d, %.3fs",
                scope_type, scope_id, block_label or '*', len(blocks), elapsed,
            )
            return {
                "success": True,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "block_label": block_label,
                "blocks": blocks,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_get_memory FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "scope_type": scope_type,
                "scope_id": scope_id,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_feedback
    # ===================================================================

    def _handle_feedback(self, fact_id: int, was_useful: bool) -> dict:
        """Handler for concierge_feedback — triggers Bayesian learning."""
        t0 = time.perf_counter()
        try:
            self._gc.update_fact_utility(fact_id=fact_id, was_useful=was_useful)
            elapsed = time.perf_counter() - t0
            updated_field = "utility_alpha" if was_useful else "utility_beta"
            logger.info(
                "concierge_feedback OK: fact_id=%d, was_useful=%s, %s+1, %.3fs",
                fact_id, was_useful, updated_field, elapsed,
            )
            return {
                "success": True,
                "fact_id": fact_id,
                "was_useful": was_useful,
                "updated_field": updated_field,
                "message": f"{updated_field} incremented for fact {fact_id}.",
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_feedback FAILED: %s", e)
            return {
                "success": False,
                "fact_id": fact_id,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_full_topology
    # ===================================================================

    def _handle_get_full_topology(self, project_identifier: Optional[str] = None) -> dict:
        """Handler for get_full_topology."""
        t0 = time.perf_counter()
        try:
            project_uuid = None
            if project_identifier:
                project_uuid = self._resolve_project_identifier(project_identifier)

            topology = self._gc.get_full_topology(project_uuid)
            elapsed = time.perf_counter() - t0
            logger.info(
                "get_full_topology OK: project=%s, nodes=%d, edges=%d, %.3fs",
                project_identifier or "ALL",
                len(topology.get("nodes", [])),
                len(topology.get("edges", [])),
                elapsed,
            )
            return {
                "success": True,
                "nodes": topology.get("nodes", []),
                "edges": topology.get("edges", []),
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("get_full_topology FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "nodes": [],
                "edges": [],
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: delete_project
    # ===================================================================

    def _handle_delete_project(self, project_identifier: str) -> dict:
        """Handler for delete_project."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            self._gc.delete_project(project_uuid)
            elapsed = time.perf_counter() - t0
            logger.info("delete_project OK: %s in %.3fs", project_uuid, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("delete_project FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: update_project
    # ===================================================================

    def _handle_update_project(
        self,
        project_identifier: str,
        folder_name: Optional[str] = None,
        primary_wing: Optional[str] = None,
        privacy_level: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> dict:
        """Handler for update_project."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            fields = {}
            if folder_name is not None:
                fields["folder_name"] = folder_name
            if primary_wing is not None:
                fields["primary_wing"] = primary_wing
            if privacy_level is not None:
                fields["privacy_level"] = privacy_level
            if summary is not None:
                fields["summary"] = summary

            self._gc.update_project(project_uuid, **fields)
            elapsed = time.perf_counter() - t0
            logger.info("update_project OK: %s with fields=%s in %.3fs", project_uuid, list(fields.keys()), elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "updated_fields": list(fields.keys()),
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("update_project FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: add_reference_wing
    # ===================================================================

    def _handle_add_reference_wing(self, project_identifier: str, wing_name: str) -> dict:
        """Handler for add_reference_wing."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            self._gc.add_reference_wing(project_uuid, wing_name)
            elapsed = time.perf_counter() - t0
            logger.info("add_reference_wing OK: %s -> %s in %.3fs", project_uuid, wing_name, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "wing_name": wing_name,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("add_reference_wing FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: remove_reference_wing
    # ===================================================================

    def _handle_remove_reference_wing(self, project_identifier: str, wing_name: str) -> dict:
        """Handler for remove_reference_wing."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            self._gc.remove_reference_wing(project_uuid, wing_name)
            elapsed = time.perf_counter() - t0
            logger.info("remove_reference_wing OK: %s -> %s in %.3fs", project_uuid, wing_name, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "wing_name": wing_name,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("remove_reference_wing FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: find_similar
    # ===================================================================

    def _handle_find_similar(
        self,
        project_identifier: str,
        limit: int = 5,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> dict:
        """Handler for find_similar."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            similar = self._gc.find_similar(
                project_uuid=project_uuid,
                limit=limit,
                include_references=include_references,
                all_wings=all_wings,
            )
            elapsed = time.perf_counter() - t0
            logger.info("find_similar OK: %s (limit=%d) in %.3fs", project_uuid, limit, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "similar_projects": similar,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("find_similar FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_trajectories
    # ===================================================================

    def _handle_get_trajectories(self, project_identifier: str) -> dict:
        """Handler for get_trajectories."""
        t0 = time.perf_counter()
        try:
            project_uuid = self._resolve_project_identifier(project_identifier)
            trajectories = self._gc.get_trajectories(project_uuid)
            elapsed = time.perf_counter() - t0
            logger.info("get_trajectories OK: %s in %.3fs", project_uuid, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "trajectories": trajectories,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("get_trajectories FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: count_embeddings
    # ===================================================================

    def _handle_count_embeddings(self, project_identifier: Optional[str] = None) -> dict:
        """Handler for count_embeddings."""
        t0 = time.perf_counter()
        try:
            project_uuid = None
            if project_identifier:
                project_uuid = self._resolve_project_identifier(project_identifier)

            count = self._gc.count_embeddings(project_uuid)
            elapsed = time.perf_counter() - t0
            logger.info("count_embeddings OK: project=%s, count=%d in %.3fs", project_uuid or "ALL", count, elapsed)
            return {
                "success": True,
                "project_uuid": project_uuid,
                "count": count,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("count_embeddings FAILED: %s — %s", project_identifier, e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: reset_collection
    # ===================================================================

    def _handle_reset_collection(self) -> dict:
        """Handler for reset_collection."""
        t0 = time.perf_counter()
        try:
            success = self._gc.reset_collection()
            elapsed = time.perf_counter() - t0
            logger.info("reset_collection OK: %s in %.3fs", success, elapsed)
            return {
                "success": success,
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("reset_collection FAILED: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }


# ===================================================================
# SDD-08: STANDALONE MODULE-LEVEL MCP TOOL FUNCTIONS
# ===================================================================
# These functions are callable directly as module-level functions
# (e.g., mcp_server.agent_save_checkpoint(...)) and delegate to the
# module-level sentinel instances (checkpointer, graph_rag).
# They serve as JSON-RPC bridge functions for external agent integration.
# ===================================================================

import json as _json


def agent_save_checkpoint(
    agent_id: str,
    session_id: str,
    checkpoint_id: str,
    state_dict: dict,
) -> str:
    """MCP Tool: Persists agent state in SQLite WAL via AgnosticCheckpointer.

    Returns a JSON string with 'success' (bool) and 'message' (str).
    """
    success = checkpointer.save_checkpoint(
        agent_id, session_id, checkpoint_id, state_dict
    )
    return _json.dumps({
        "success": success,
        "message": (
            f"Checkpoint '{checkpoint_id}' saved successfully for agent '{agent_id}'"
            if success
            else f"Failed to save checkpoint '{checkpoint_id}' for agent '{agent_id}'"
        ),
    })


def agent_get_checkpoint(
    agent_id: str,
    session_id: str,
    checkpoint_id: str,
) -> dict:
    """MCP Tool: Retrieves agent state from SQLite WAL via AgnosticCheckpointer.

    Returns the decoded state dictionary, or {} if not found.
    """
    return checkpointer.get_checkpoint(agent_id, session_id, checkpoint_id)


def agent_list_checkpoints(
    agent_id: str,
    session_id: str,
) -> list:
    """MCP Tool: Returns the chronological timeline of checkpoints for Time-Travel.

    Returns a list of dicts with 'checkpoint_id' and 'created_at', ordered ASC.
    """
    return checkpointer.list_checkpoints(agent_id, session_id)


def concierge_get_call_chain(
    start_node: str,
    depth_limit: int = 5,
) -> list:
    """MCP Tool: Resolves recursive call chain dependencies via GraphRAGEngine.

    Returns a flat list of file paths connected to the start node.
    """
    return graph_rag.get_call_chain_recursive(start_node, depth_limit)
