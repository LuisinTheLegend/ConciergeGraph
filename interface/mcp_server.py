"""
interface/mcp_server.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Servidor MCP (Model Context Protocol) expondo as ferramentas do
Grafo Concierge para agentes LLM via FastMCP.

REFATORAÇÃO v3.8: Agora consome exclusivamente a Fachada Central
(core.middleware.GrafoConcierge) em vez de instanciar dependências
internas soltas. Toda lógica de negócio foi movida para core/.

Tools expostas (6 ferramentas — alinhadas com Architecture v3.8):
    concierge_mine     → Ingestão de projeto (crawl → parse → store)
    concierge_search   → Busca Híbrida v4 com Strict Scoping
    concierge_commit   → Registro de alterações auditadas
    concierge_wakeup   → Reativação de consciência (Bússola + Wings)
    concierge_resume   → Bússola de Contexto (resumo conciso)
    concierge_load     → Lazy Load de um nó sob demanda
    concierge_status   → Saúde do sistema e estatísticas

Arquitetura:
    Este módulo é APENAS a ponte MCP ↔ Fachada Central.
    Nenhuma lógica de negócio reside aqui. Toda operação é delegada
    à classe GrafoConcierge (core/middleware.py).
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
# GrafoConciergeServer — Encapsulamento do FastMCP + Fachada Central
# ---------------------------------------------------------------------------

class GrafoConciergeServer:
    """Servidor MCP do Grafo Concierge.

    Encapsula o FastMCP e registra as tools com acesso à Fachada Central.
    Cada tool é uma closure que delega à instância de GrafoConcierge.

    Args:
        concierge: Instância da Fachada Central GrafoConcierge.
        janitor: Instância do JanitorService (manutenção autônoma).
    """

    def __init__(
        self,
        concierge: GrafoConcierge,
        janitor: Optional[JanitorService] = None,
    ) -> None:
        self._gc = concierge
        self._janitor = janitor

        # Ler variáveis de ambiente para host e port (se houver)
        host = os.environ.get("GRAFO_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("GRAFO_PORT", "8000"))
        except ValueError:
            port = 8000

        # Cria o servidor FastMCP
        self._mcp = FastMCP("Grafo Concierge", host=host, port=port)

        # Registra as tools
        self._register_tools()

        tool_count = len(self._mcp._tool_manager.list_tools())
        logger.info("GrafoConciergeServer inicializado — %d tools registradas.", tool_count)

    @property
    def mcp(self) -> FastMCP:
        """Acesso direto ao FastMCP (para run/mount)."""
        return self._mcp

    # ===================================================================
    # TOOL REGISTRATION
    # ===================================================================

    def _register_tools(self) -> None:
        """Registra todas as tools MCP como closures com acesso a self."""

        server = self

        # --- concierge_register ---
        @self._mcp.tool(
            name="concierge_register",
            description=(
                "Registra um novo projeto e define Nível de Privacidade."
            ),
        )
        def concierge_register(
            project_path: str,
            wing: str = "geral",
            privacy_level: str = "PUBLIC",
            summary: Optional[str] = None,
        ) -> dict:
            """Registra um novo projeto no Grafo Concierge.

            Args:
                project_path: Caminho ou nome da pasta do projeto.
                wing: Ala principal (Primary Wing). Padrão: "geral".
                privacy_level: Nível de privacidade (PUBLIC, INTERNAL, RESTRICTED).
                summary: Descrição opcional.

            Returns:
                Dicionário com o UUID gerado e status.
            """
            return server._handle_register(project_path, wing, privacy_level, summary)

        # --- concierge_list_projects ---
        @self._mcp.tool(
            name="concierge_list_projects",
            description=(
                "Retorna a lista de todos os projetos cadastrados no Grafo Concierge, "
                "mapeando Nome do Projeto -> UUID e Data de Atualização."
            ),
        )
        def concierge_list_projects() -> dict:
            """Retorna todas as correspondências Nome -> UUID dos projetos."""
            return server._handle_list_projects()

        # --- concierge_mine ---
        @self._mcp.tool(
            name="concierge_mine",
            description=(
                "Ingere um projeto do filesystem no Grafo de Memória. "
                "Crawla o diretório, parseia arquivos (AST/Semantic), "
                "gera resumos recursivos (L0/L1/L2), armazena embeddings "
                "e sincroniza SQLite + Qdrant. Retorna relatório completo."
            ),
        )
        def concierge_mine(
            path: str,
            project_identifier: str,
            auto_tag: bool = True,
        ) -> dict:
            """Ingere um projeto no Grafo de Memória.

            Args:
                path: Caminho absoluto do diretório a ingerir.
                project_identifier: Nome legível do projeto ou seu UUID.
                auto_tag: Se True, extrai tags automaticamente dos arquivos.

            Returns:
                Dicionário com relatório de ingestão (MCP-compatible).
            """
            return server._handle_mine(path, project_identifier, auto_tag)

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
            project_identifier: str = "",
            top_k: int = 10,
            node_type: Optional[str] = None,
            include_references: bool = False,
            all_wings: bool = False,
        ) -> dict:
            """Busca híbrida no Grafo de Memória.

            Args:
                query: Texto da consulta em linguagem natural.
                project_identifier: UUID ou nome do projeto para Strict Scoping.
                                   Opcional quando all_wings=True.
                top_k: Número máximo de resultados (default: 10).
                node_type: Filtro opcional de tipo de nó (FACT, SKILL, etc.).
                include_references: Incluir Reference Wings no escopo.
                all_wings: Buscar em todas as alas (ignora Strict Scoping).

            Returns:
                Dicionário com resultados ranqueados e metadata.
            """
            return server._handle_search(
                query, project_identifier, top_k, node_type,
                include_references, all_wings,
            )

        # --- concierge_commit ---
        @self._mcp.tool(
            name="concierge_commit",
            description=(
                "Registra alterações consolidadas no Grafo de Memória. "
                "Grava na tabela commit_log, atualiza recência dos nós "
                "afetados e audita via Revisor Crítico."
            ),
        )
        def concierge_commit(
            project_uuid: str,
            phase: str,
            technical_changes: str,
            updated_pointers: list[str],
            node_ids: Optional[list[int]] = None,
        ) -> dict:
            """Registra um commit de memória auditado.

            Args:
                project_uuid: UUID do projeto.
                phase: Fase atual (planning, build, done, review).
                technical_changes: Descrição das mudanças técnicas.
                updated_pointers: Lista de ponteiros atualizados.
                node_ids: IDs dos nós afetados (atualiza recência).

            Returns:
                Dicionário com ID do commit e status.
            """
            return server._handle_commit(
                project_uuid, phase, technical_changes,
                updated_pointers, node_ids,
            )

        # --- concierge_wakeup ---
        @self._mcp.tool(
            name="concierge_wakeup",
            description=(
                "Reativa a consciência do agente para um projeto. "
                "Retorna a Bússola de Contexto, Reference Wings, "
                "últimos commits e estatísticas."
            ),
        )
        def concierge_wakeup(project_uuid: str) -> dict:
            """Reativação de consciência do agente.

            Args:
                project_uuid: UUID do projeto.

            Returns:
                Dicionário com Bússola, Wings, commits e stats.
            """
            return server._handle_wakeup(project_uuid)

        # --- concierge_resume ---
        @self._mcp.tool(
            name="concierge_resume",
            description=(
                "Retorna a Bússola de Contexto (resumo conciso) "
                "do projeto. Ideal para injeção em system prompts."
            ),
        )
        def concierge_resume(project_uuid: str) -> dict:
            """Bússola de Contexto do projeto.

            Args:
                project_uuid: UUID do projeto.

            Returns:
                Dicionário com resumo e estatísticas básicas.
            """
            return server._handle_resume(project_uuid)

        # --- concierge_load ---
        @self._mcp.tool(
            name="concierge_load",
            description=(
                "Carrega os dados completos de um nó sob demanda "
                "(Lazy Load). Retorna conteúdo, tags, arestas e "
                "metadados do nó."
            ),
        )
        def concierge_load(node_id: int) -> dict:
            """Carrega um nó completo sob demanda.

            Args:
                node_id: ID do nó a carregar.

            Returns:
                Dicionário com todos os campos e arestas do nó.
            """
            return server._handle_load(node_id)

        # --- concierge_status ---
        @self._mcp.tool(
            name="concierge_status",
            description=(
                "Retorna o status de saúde do Grafo Concierge: "
                "estatísticas do projeto, saúde do Qdrant, último "
                "relatório do Janitor e métricas do pipeline."
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

        # --- search_symbols ---
        @self._mcp.tool(
            name="search_symbols",
            description=(
                "Realiza busca rápida de assinaturas de símbolos (classes/funções) "
                "no índice FTS5 do Grafo Concierge."
            ),
        )
        def search_symbols(
            query: str,
            project_uuid: Optional[str] = None,
        ) -> dict:
            """Busca símbolos de código por nome no índice FTS5.

            Args:
                query: Texto ou nome do símbolo a buscar.
                project_uuid: UUID do projeto (opcional).

            Returns:
                Dicionário com a lista de símbolos e seus detalhes.
            """
            return server._handle_search_symbols(query, project_uuid)

        # --- get_implementations ---
        @self._mcp.tool(
            name="get_implementations",
            description=(
                "Retorna a implementação (bloco de código da AST) correspondente a um nó símbolo."
            ),
        )
        def get_implementations(symbol_id: int) -> dict:
            """Retorna a implementação de um nó símbolo.

            Args:
                symbol_id: ID numérico do nó do símbolo.

            Returns:
                Dicionário com a implementação (código) do símbolo.
            """
            return server._handle_get_implementations(symbol_id)

        # --- get_callers ---
        @self._mcp.tool(
            name="get_callers",
            description=(
                "Retorna todos os chamadores (callers) de um nó símbolo analisando as arestas do Grafo."
            ),
        )
        def get_callers(symbol_id: int) -> dict:
            """Retorna chamadores de um símbolo.

            Args:
                symbol_id: ID numérico do nó do símbolo.

            Returns:
                Dicionário com os callers e detalhes da relação.
            """
            return server._handle_get_callers(symbol_id)

        # --- concierge_store_fact ---
        @self._mcp.tool(
            name="concierge_store_fact",
            description=(
                "Grava um fato semântico no Grafo de Memória via SemanticExtractor. "
                "O extrator avalia o fato contra os existentes no escopo e decide: "
                "ADD, UPDATE, DELETE ou NOOP (bi-temporal)."
            ),
        )
        def concierge_store_fact(
            scope_type: str,
            scope_id: str,
            fact_statement: str,
        ) -> dict:
            """Grava um fato semântico no grafo.

            Args:
                scope_type: Tipo de escopo ('user', 'session', 'agent', 'org').
                scope_id: Identificador único do escopo.
                fact_statement: Texto do fato/preferência a gravar.

            Returns:
                Dicionário com as decisões tomadas pelo SemanticExtractor.
            """
            return server._handle_store_fact(scope_type, scope_id, fact_statement)

        # --- concierge_set_memory ---
        @self._mcp.tool(
            name="concierge_set_memory",
            description=(
                "Grava ou atualiza um bloco de memória core persistente (user_core_memory). "
                "Use para armazenar preferências, configurações e contexto permanente do usuário/sessão."
            ),
        )
        def concierge_set_memory(
            scope_type: str,
            scope_id: str,
            block_label: str,
            content: str,
        ) -> dict:
            """Grava um bloco de memória core persistente.

            Args:
                scope_type: Tipo de escopo ('user', 'session', 'agent', 'org').
                scope_id: Identificador único do escopo.
                block_label: Rótulo do bloco (ex: 'preferred_language', 'persona_name').
                content: Conteúdo a armazenar no bloco.

            Returns:
                Dicionário com success e memory_id do registro.
            """
            return server._handle_set_memory(scope_type, scope_id, block_label, content)

        # --- concierge_get_memory ---
        @self._mcp.tool(
            name="concierge_get_memory",
            description=(
                "Consulta blocos de memória core persistente. "
                "Se block_label for informado, retorna apenas aquele bloco. "
                "Se omitido, retorna todos os blocos do escopo."
            ),
        )
        def concierge_get_memory(
            scope_type: str,
            scope_id: str,
            block_label: Optional[str] = None,
        ) -> dict:
            """Consulta blocos de memória core.

            Args:
                scope_type: Tipo de escopo ('user', 'session', 'agent', 'org').
                scope_id: Identificador único do escopo.
                block_label: Rótulo específico (opcional). Se ausente, retorna todos.

            Returns:
                Dicionário com success e lista de blocks.
            """
            return server._handle_get_memory(scope_type, scope_id, block_label)

        # --- concierge_feedback ---
        @self._mcp.tool(
            name="concierge_feedback",
            description=(
                "Registra feedback de utilidade sobre um fato semântico (semantic_fact). "
                "Aciona o aprendizado Bayesiano: incrementa utility_alpha (sucesso) ou "
                "utility_beta (falha), alimentando o Thompson Sampling da busca híbrida."
            ),
        )
        def concierge_feedback(
            fact_id: int,
            was_useful: bool,
        ) -> dict:
            """Registra feedback de utilidade de um fato semântico.

            Args:
                fact_id: ID do semantic_fact a avaliar (campo 'id' retornado por concierge_store_fact).
                was_useful: True se o fato foi útil na resposta, False caso contrário.

            Returns:
                Dicionário com success, fact_id, was_useful e mensagem.
            """
            return server._handle_feedback(fact_id, was_useful)

    def _resolve_project_identifier(self, project_identifier: str) -> str:
        """Resolve project_identifier (UUID ou folder_name) para project_uuid.
        
        Levanta ValueError se o nome não for encontrado no banco de dados.
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
        """Handler do concierge_list_projects."""
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
            logger.error("concierge_list_projects FALHOU: %s", e)
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
        """Handler do concierge_register — delega à Fachada."""
        t0 = time.perf_counter()

        try:
            folder_name = os.path.basename(project_path.strip(r"\/")) or project_path
            
            project_uuid = self._gc.register_project(
                folder_name=folder_name,
                wing=wing,
                privacy_level=privacy_level,
                summary=summary or f"Projeto registrado via MCP: {folder_name}",
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
            logger.error("concierge_register FALHOU: %s", e)
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
        """Handler do concierge_mine — delega à Fachada."""
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
                    # Registra caso não exista
                    self._gc.register_project(
                        folder_name=project_name,
                        summary=f"Projeto ingerido de: {path}",
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

            # Sinaliza Idle-Lock para o Janitor
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
                "concierge_mine OK: %s → %d arquivos, %d nós, %.2fs",
                project_name, result.get("files_processed", 0),
                result.get("nodes_created", 0), elapsed,
            )
            return result

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_mine FALHOU: %s — %s", project_identifier, e)
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
        """Handler do concierge_search — delega à Fachada."""
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
                # Resolução transparente do project_identifier
                project_uuid = self._resolve_project_identifier(project_identifier)

            results = self._gc.hybrid_search(
                query=query,
                project_uuid=project_uuid,
                top_k=top_k,
                include_references=include_references,
                all_wings=all_wings,
                node_type=node_type,
            )

            # Enriquece com dados do nó para resposta MCP
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
                    logger.debug("Nó %d não encontrado no enriquecimento.", item.get("node_id"))

            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_search OK: query='%.40s' → %d resultados, %.3fs",
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
            logger.error("concierge_search FALHOU: %s", e)
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
        """Handler do concierge_commit — delega à Fachada."""
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
                "concierge_commit OK: id=%d, projeto=%s, fase='%s', %.3fs",
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
            logger.error("concierge_commit FALHOU: %s", e)
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
        """Handler do concierge_wakeup — delega à Fachada."""
        t0 = time.perf_counter()

        try:
            result = self._gc.wake_up(project_uuid)
            elapsed = time.perf_counter() - t0

            result["success"] = True
            result["duration_seconds"] = round(elapsed, 3)

            logger.info(
                "concierge_wakeup OK: projeto=%s, %.3fs", project_uuid, elapsed,
            )
            return result

        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_wakeup FALHOU: %s", e)
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
        """Handler do concierge_resume — delega à Fachada."""
        t0 = time.perf_counter()

        try:
            resume = self._gc.get_resume(project_uuid)
            project = self._gc.store.get_project(project_uuid)
            stats = self._gc.store.get_project_stats(project_uuid)
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_resume OK: projeto=%s, %.3fs", project_uuid, elapsed,
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
            logger.error("concierge_resume FALHOU: %s", e)
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
        """Handler do concierge_load — delega à Fachada."""
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
            logger.error("concierge_load FALHOU: %s", e)
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
        """Handler do concierge_status — delega à Fachada + componentes."""
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

            # --- Project Stats (se UUID fornecido) ---
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
    # HANDLER: search_symbols
    # ===================================================================

    def _handle_search_symbols(self, query: str, project_uuid: Optional[str] = None) -> dict:
        """Handler do search_symbols."""
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
            logger.error("search_symbols FALHOU: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_implementations
    # ===================================================================

    def _handle_get_implementations(self, symbol_id: int) -> dict:
        """Handler do get_implementations — delega à Fachada Central."""
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
            logger.error("get_implementations FALHOU: %s", e)
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # HANDLER: get_callers
    # ===================================================================

    def _handle_get_callers(self, symbol_id: int) -> dict:
        """Handler do get_callers."""
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
            logger.error("get_callers FALHOU: %s", e)
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
        """Handler do concierge_store_fact — delega à Fachada com validação fail-fast."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"scope_type inválido '{scope_type}'. Deve ser um de: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id não pode ser vazio.")
            if not fact_statement or not fact_statement.strip():
                raise ValueError("fact_statement não pode ser vazio.")

            results = self._gc.store_fact(
                scope_type=scope_type,
                scope_id=scope_id,
                fact_statement=fact_statement,
            )
            elapsed = time.perf_counter() - t0

            logger.info(
                "concierge_store_fact OK: scope=%s/%s, decisões=%d, %.3fs",
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
            logger.error("concierge_store_fact FALHOU: %s", e)
            return {
                "success": False,
                "error": str(e),
                "scope_type": scope_type,
                "scope_id": scope_id,
                "duration_seconds": round(elapsed, 3),
            }

    # ===================================================================
    # RUN — Inicialização do servidor
    # ===================================================================

    def run(self, transport: str = "stdio") -> None:
        """Inicia o servidor MCP.

        Args:
            transport: Tipo de transporte ('stdio' ou 'sse').
        """
        import asyncio
        logger.info("Iniciando Grafo Concierge MCP Server (transport=%s)...", transport)

        async def _run_server():
            if transport == "sse":
                await self._mcp.run_sse_async()
            else:
                await self._mcp.run_stdio_async()

        try:
            asyncio.run(_run_server())
        except KeyboardInterrupt:
            logger.info("Servidor parado por interrupção do usuário.")

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
        """Handler do concierge_set_memory — delega à Façada com validação fail-fast."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"scope_type inválido '{scope_type}'. Deve ser um de: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id não pode ser vazio.")
            if not block_label or not block_label.strip():
                raise ValueError("block_label não pode ser vazio.")
            if not content or not content.strip():
                raise ValueError("content não pode ser vazio.")

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
            logger.error("concierge_set_memory FALHOU: %s", e)
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
        """Handler do concierge_get_memory — delega à Façada com validação fail-fast."""
        t0 = time.perf_counter()
        try:
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(f"scope_type inválido '{scope_type}'. Deve ser um de: {valid_scopes}")
            if not scope_id or not scope_id.strip():
                raise ValueError("scope_id não pode ser vazio.")

            blocks = self._gc.get_core_memory_blocks(
                scope_type=scope_type,
                scope_id=scope_id,
                block_label=block_label,
            )
            elapsed = time.perf_counter() - t0
            logger.info(
                "concierge_get_memory OK: scope=%s/%s, label=%s, blocos=%d, %.3fs",
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
            logger.error("concierge_get_memory FALHOU: %s", e)
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
        """Handler do concierge_feedback — aciona o aprendizado Bayesiano."""
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
                "message": f"{updated_field} incrementado para o fato {fact_id}.",
                "duration_seconds": round(elapsed, 3),
            }
        except Exception as e:
            elapsed = time.perf_counter() - t0
            logger.error("concierge_feedback FALHOU: %s", e)
            return {
                "success": False,
                "fact_id": fact_id,
                "error": str(e),
                "duration_seconds": round(elapsed, 3),
            }
