"""
core/nozomio_router.py — SDD-SURVIVAL-22

Roteador Federado de Conhecimento (Nozomio Style).

Direciona a recuperação de dados para o ecossistema correto com base na
classificação de intenção fornecida pelo IntentClassifier:

  - LOCAL_CODEBASE  →  GraphRAG local privado (SQLite + Qdrant)
  - EXTERNAL_GENERAL →  Servidores MCP federados de documentação pública

Sinaliza metadados de privacidade (is_private) para cada resultado, permitindo
que camadas superiores decidam se o conteúdo pode ser cacheado externamente.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class NozomioRouter:
    """Roteador de conhecimento que delega buscas entre o GraphRAG local e MCPs externos."""

    def __init__(self, db_manager, graph_rag_engine, external_mcp_client=None):
        self.db = db_manager
        self.graph_rag = graph_rag_engine
        self.external_mcp = external_mcp_client  # Mock/cliente de federação com MCPs públicos

    def resolve_knowledge(self, query: str, classification: str) -> Dict[str, Any]:
        """
        Direciona a busca para o ecossistema correto baseando-se na classificação.

        Args:
            query: A consulta textual do desenvolvedor.
            classification: 'LOCAL_CODEBASE' ou 'EXTERNAL_GENERAL' (saída do IntentClassifier).

        Returns:
            Dict com chaves 'source', 'context' e 'is_private'.
        """
        if classification == "LOCAL_CODEBASE":
            return self._resolve_local(query)
        else:
            return self._resolve_external(query)

    def _resolve_local(self, query: str) -> Dict[str, Any]:
        """Realiza a busca no GraphRAG local privado."""
        try:
            local_context = self.graph_rag.retrieve_multihop_context(query)
        except Exception as e:
            logger.error("NozomioRouter: Falha no GraphRAG local: %s", e)
            local_context = f"[GraphRAG Error] Não foi possível recuperar contexto local: {e}"

        logger.debug("NozomioRouter: Resolução LOCAL para '%s' (%d chars)", query[:60], len(str(local_context)))
        return {
            "source": "LOCAL_GRAPHRAG",
            "context": local_context,
            "is_private": True
        }

    def _resolve_external(self, query: str) -> Dict[str, Any]:
        """Consulta servidores federados externos estilo Nozomio."""
        external_context = ""

        if self.external_mcp:
            try:
                external_context = self.external_mcp.query_docs(query)
            except Exception as e:
                logger.warning("NozomioRouter: Falha na conexão MCP federado: %s", e)
                external_context = "Erro na conexão com servidor federado de documentação."

        if not external_context:
            external_context = f"[Nozomio Fallback] Informação externa de mercado sobre: {query}"

        logger.debug("NozomioRouter: Resolução EXTERNAL para '%s' (%d chars)", query[:60], len(external_context))
        return {
            "source": "EXTERNAL_NOZOMIO_MCP",
            "context": external_context,
            "is_private": False
        }
