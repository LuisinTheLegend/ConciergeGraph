"""
server/mcp_server.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Servidor MCP (Model Context Protocol) expondo as ferramentas do
Grafo Concierge para agentes LLM via FastMCP.

Tools expostas:
    concierge_mine    → Ingestão de projeto: crawl → parse → summarize → embed → store
    concierge_search  → Busca híbrida: vetorial + FTS5 + reranking
    concierge_status  → Saúde do sistema, estatísticas e último relatório do Janitor

Arquitetura:
    Este módulo é APENAS a ponte MCP ↔ módulos internos.
    Nenhuma lógica de negócio reside aqui. Toda operação é delegada
    aos módulos já testados: IngestionManager, SqliteStore,
    ChromaVectorStore, EmbeddingManager e JanitorService.
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Optional

from mcp.server.fastmcp import FastMCP

from storage import SqliteStore, ChromaVectorStore, EmbeddingManager
from ingestion import IngestionManager
from services import JanitorService

logger = logging.getLogger("grafo-concierge.mcp")


# ---------------------------------------------------------------------------
# GrafoConciergeServer — Encapsulamento do FastMCP + dependências
# ---------------------------------------------------------------------------

class GrafoConciergeServer:
    """Servidor MCP do Grafo Concierge.

    Encapsula o FastMCP e registra as tools com acesso às dependências
    injetadas. Cada tool é uma closure que captura `self` para acessar
    os módulos internos.

    Args:
        sqlite_store:       Instância do SqliteStore (persistência relacional).
        vector_store:       Instância do ChromaVectorStore (persistência vetorial).
        embedding_manager:  Instância do EmbeddingManager (Flash/Elite).
        ingestion_manager:  Instância do IngestionManager (pipeline de ingestão).
        janitor:            Instância do JanitorService (manutenção autônoma).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        embedding_manager: EmbeddingManager,
        ingestion_manager: IngestionManager,
        janitor: Optional[JanitorService] = None,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._embedder = embedding_manager
        self._ingestion = ingestion_manager
        self._janitor = janitor

        # Cria o servidor FastMCP
        self._mcp = FastMCP("Grafo Concierge")

        # Registra as tools
        self._register_tools()

        logger.info("GrafoConciergeServer inicializado — 3 tools registradas.")

    @property
    def mcp(self) -> FastMCP:
        """Acesso direto ao FastMCP (para run/mount)."""
        return self._mcp

    # ===================================================================
    # TOOL REGISTRATION
    # ===================================================================

    def _register_tools(self) -> None:
        """Registra todas as tools MCP como closures com acesso a self."""

        # Captura self para as closures
        server = self

        # --- concierge_mine ---
        @self._mcp.tool(
            name="concierge_mine",
            description=(
                "Ingere um projeto do filesystem no Grafo de Memória. "
                "Crawla o diretório, parseia arquivos (AST/Semantic), "
                "gera resumos recursivos (L0/L1/L2), armazena embeddings "
                "e sincroniza SQLite + ChromaDB. Retorna relatório completo."
            ),
        )
        def concierge_mine(
            path: str,
            project_name: str,
            auto_tag: bool = True,
        ) -> dict:
            """Ingere um projeto no Grafo de Memória.

            Args:
                path: Caminho absoluto do diretório a ingerir.
                project_name: Nome legível do projeto (usado como folder_name).
                auto_tag: Se True, extrai tags automaticamente dos arquivos.

            Returns:
                Dicionário com relatório de ingestão (MCP-compatible).
            """
            return server._handle_mine(path, project_name, auto_tag)

        # --- concierge_search ---
        @self._mcp.tool(
            name="concierge_search",
            description=(
                "Busca híbrida no Grafo de Memória combinando similaridade "
                "vetorial (cosine), frequência (FTS5/BM25) e sinais de grafo "
                "(recência, centralidade). Retorna os chunks mais relevantes "
                "ranqueados por score híbrido."
            ),
        )
        def concierge_search(
            query: str,
            project_uuid: str,
            top_k: int = 10,
            node_type: Optional[str] = None,
        ) -> dict:
            """Busca híbrida no Grafo de Memória.

            Args:
                query: Texto da consulta em linguagem natural.
                project_uuid: UUID do projeto para Strict Scoping.
                top_k: Número máximo de resultados (default: 10).
                node_type: Filtro opcional de tipo de nó (FACT, RULE, etc.).

            Returns:
                Dicionário com resultados ranqueados e metadata.
            """
            return server._handle_search(query, project_uuid, top_k, node_type)

        # --- concierge_status ---
        @self._mcp.tool(
            name="concierge_status",
            description=(
                "Retorna o status de saúde do Grafo Concierge: "
                "estatísticas do projeto, saúde do ChromaDB, último "
                "relatório do Janitor e métricas do pipeline de ingestão."
            ),
        )
        def concierge_status(
            project_uuid: Optional[str] = None,
        ) -> dict:
            """Status de saúde do sistema.

            Args:
                project_uuid: UUID do projeto (opcional). Se omitido,
                              retorna status global.

            Returns:
                Dicionário com métricas de saúde e estatísticas.
            """
            return server._handle_status(project_uuid)

    # ===================================================================
    # HANDLER: concierge_mine
    # ===================================================================

    def _handle_mine(
        self, path: str, project_name: str, auto_tag: bool,
    ) -> dict:
        """Handler real do concierge_mine."""
        t0 = time.perf_counter()

        try:
            # Garante que o projeto existe (cria se necessário)
            project_uuid = self._ensure_project(project_name, path)

            # Sinaliza Idle-Lock para o Janitor
            if self._janitor:
                self._janitor.signal_mine_start()

            try:
                result = self._ingestion.mine(project_uuid, path, auto_tag=auto_tag)
            finally:
                if self._janitor:
                    self._janitor.signal_mine_end()

            elapsed = time.perf_counter() - t0
            response = result.to_dict()
            response["project_uuid"] = project_uuid
            response["project_name"] = project_name
            response["path"] = path
            response["duration_seconds"] = round(elapsed, 3)
            response["success"] = True

            logger.info(
                "concierge_mine OK: %s → %d arquivos, %d nós, %.2fs",
                project_name, result.files_processed, result.nodes_created, elapsed,
            )
            return response

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_mine FALHOU: %s — %s", project_name, e)
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "project_name": project_name,
                "path": path,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_search
    # ===================================================================

    def _handle_search(
        self,
        query: str,
        project_uuid: str,
        top_k: int,
        node_type: Optional[str],
    ) -> dict:
        """Handler real do concierge_search — Hybrid Search Pipeline."""
        t0 = time.perf_counter()

        try:
            # --- Fase 1: Busca Vetorial ---
            query_embedding = self._embedder.embed(query)
            vector_results = self._vector.search(
                query_embedding=query_embedding,
                project_uuids=[project_uuid],
                top_k=top_k * 2,  # Over-fetch para reranking
                filters={"node_type": node_type} if node_type else None,
            )

            # --- Fase 2: Busca FTS5 (BM25) ---
            fts_results = self._store.fts_search(
                query=query,
                project_uuid=project_uuid,
                node_type=node_type,
                limit=top_k * 2,
            )
            fts_scores: dict[int, float] = {
                r["id"]: r.get("bm25_score", 0.0) for r in fts_results
            }

            # --- Fase 3: Merge + Hybrid Scoring ---
            candidates: list[dict] = []
            seen_node_ids: set[int] = set()

            # Candidatos da busca vetorial
            for vr in vector_results:
                if vr.node_id not in seen_node_ids:
                    seen_node_ids.add(vr.node_id)
                    candidates.append({
                        "node_id": vr.node_id,
                        "vector_score": vr.score,
                        "fts_score": fts_scores.get(vr.node_id, 0.0),
                    })

            # Candidatos exclusivos do FTS (não cobertos pela vetorial)
            for fr in fts_results:
                nid = fr.get("id")
                if nid and nid not in seen_node_ids:
                    seen_node_ids.add(nid)
                    candidates.append({
                        "node_id": nid,
                        "vector_score": 0.0,
                        "fts_score": fr.get("bm25_score", 0.0),
                    })

            # --- Fase 4: Hybrid Reranking (recência + centralidade) ---
            if candidates:
                ranked = self._store.hybrid_search_score_batch(candidates)
                # hybrid_search_score_batch já retorna ordenado por score_final DESC
                ranked = ranked[:top_k]
            else:
                ranked = []

            # --- Fase 5: Enriquecimento com dados do nó ---
            enriched_results = []
            for item in ranked:
                try:
                    node = self._store.get_node(item["node_id"])
                    breakdown = item.get("score_breakdown", {})
                    enriched_results.append({
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
                    })
                except Exception:
                    # Nó pode ter sido deletado entre search e fetch
                    logger.debug("Nó %d não encontrado no enriquecimento.", item["node_id"])

            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_search OK: query='%.40s' → %d resultados, %.3fs",
                query, len(enriched_results), elapsed,
            )

            return {
                "success": True,
                "query": query,
                "project_uuid": project_uuid,
                "results_count": len(enriched_results),
                "results": enriched_results,
                "pipeline": {
                    "vector_candidates": len(vector_results),
                    "fts_candidates": len(fts_results),
                    "merged_candidates": len(candidates),
                    "final_results": len(enriched_results),
                },
                "duration_seconds": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_search FALHOU: %s", e)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "project_uuid": project_uuid,
                "results": [],
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: concierge_status
    # ===================================================================

    def _handle_status(self, project_uuid: Optional[str]) -> dict:
        """Handler real do concierge_status."""
        t0 = time.perf_counter()

        try:
            status: dict = {
                "success": True,
                "system": "Grafo Concierge v3.8.0",
                "components": {},
            }

            # --- SQLite Health ---
            try:
                projects = self._store.list_projects()
                status["components"]["sqlite"] = {
                    "status": "healthy",
                    "total_projects": len(projects),
                }
            except Exception as e:
                status["components"]["sqlite"] = {
                    "status": "degraded",
                    "error": str(e),
                }

            # --- ChromaDB Health ---
            try:
                chroma_healthy = self._vector.health_check()
                chroma_count = self._vector.count()
                status["components"]["chromadb"] = {
                    "status": "healthy" if chroma_healthy else "degraded",
                    "total_embeddings": chroma_count,
                }
            except Exception as e:
                status["components"]["chromadb"] = {
                    "status": "degraded",
                    "error": str(e),
                }

            # --- Embedding Manager ---
            status["components"]["embedding"] = {
                "tier": str(self._embedder.tier.value),
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

            # --- Project Stats (se UUID fornecido) ---
            if project_uuid:
                try:
                    project = self._store.get_project(project_uuid)
                    stats = self._store.get_project_stats(project_uuid)
                    last_phase = self._store.get_last_commit_phase(project_uuid)
                    wings = self._store.get_reference_wings(project_uuid)

                    status["project"] = {
                        "uuid": project_uuid,
                        "folder_name": project.get("folder_name", ""),
                        "privacy_level": project.get("privacy_level", ""),
                        "stats": stats,
                        "last_commit_phase": last_phase,
                        "reference_wings": wings,
                    }
                except Exception as e:
                    status["project"] = {
                        "uuid": project_uuid,
                        "error": str(e),
                    }

            elapsed = time.perf_counter() - t0
            status["duration_seconds"] = round(elapsed, 3)

            logger.info("concierge_status OK em %.3fs", elapsed)
            return status

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_status FALHOU: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # PROJECT HELPER
    # ===================================================================

    def _ensure_project(self, project_name: str, path: str) -> str:
        """Garante que o projeto existe. Cria se necessário.

        Busca por folder_name. Se não existir, cria com UUID auto-gerado.

        Returns:
            UUID do projeto.
        """
        import uuid as uuid_mod

        try:
            project = self._store.get_project(project_name)
            return project["uuid"]
        except Exception:
            # Projeto não existe — cria
            new_uuid = str(uuid_mod.uuid4())
            self._store.create_project(
                uuid=new_uuid,
                folder_name=project_name,
                primary_wing="geral",
                summary=f"Projeto ingerido de: {path}",
            )
            logger.info(
                "Projeto criado: %s → %s", project_name, new_uuid,
            )
            return new_uuid

    # ===================================================================
    # RUN — Inicialização do servidor
    # ===================================================================

    def run(self, transport: str = "stdio") -> None:
        """Inicia o servidor MCP.

        Args:
            transport: Tipo de transporte ('stdio' ou 'sse').
        """
        logger.info("Iniciando Grafo Concierge MCP Server (transport=%s)...", transport)
        self._mcp.run(transport=transport)
