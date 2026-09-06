"""
core/nozomio_router.py — SDD-SURVIVAL-22

Federated Knowledge Router (Nozomio Style).

Routes knowledge retrieval to the correct ecosystem based on the
intent classification provided by IntentClassifier:

  - LOCAL_CODEBASE   →  Private local GraphRAG (SQLite + Qdrant)
  - EXTERNAL_GENERAL →  Federated public documentation MCP servers

Flags privacy metadata (is_private) on each result, allowing
higher layers to decide whether content can be cached externally.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class NozomioRouter:
    """Knowledge router delegating queries between local GraphRAG and external MCPs."""

    def __init__(self, db_manager, graph_rag_engine, external_mcp_client=None):
        self.db = db_manager
        self.graph_rag = graph_rag_engine
        self.external_mcp = external_mcp_client  # Mock/client for federated public MCPs

    def resolve_knowledge(self, query: str, classification: str) -> Dict[str, Any]:
        """
        Routes knowledge retrieval to the appropriate ecosystem based on classification.

        Args:
            query: The developer's textual query.
            classification: 'LOCAL_CODEBASE' or 'EXTERNAL_GENERAL' (output from IntentClassifier).

        Returns:
            Dict containing 'source', 'context', and 'is_private'.
        """
        if classification == "LOCAL_CODEBASE":
            return self._resolve_local(query)
        else:
            return self._resolve_external(query)

    def _resolve_local(self, query: str) -> Dict[str, Any]:
        """Performs search in private local GraphRAG."""
        try:
            local_context = self.graph_rag.retrieve_multihop_context(query)
        except Exception as e:
            logger.error("NozomioRouter: Local GraphRAG failure: %s", e)
            local_context = f"[GraphRAG Error] Could not retrieve local context: {e}"

        logger.debug("NozomioRouter: LOCAL resolution for '%s' (%d chars)", query[:60], len(str(local_context)))
        return {
            "source": "LOCAL_GRAPHRAG",
            "context": local_context,
            "is_private": True
        }

    def _resolve_external(self, query: str) -> Dict[str, Any]:
        """Queries external federated documentation servers in Nozomio style."""
        external_context = ""

        if self.external_mcp:
            try:
                external_context = self.external_mcp.query_docs(query)
            except Exception as e:
                logger.warning("NozomioRouter: Federated MCP connection failure: %s", e)
                external_context = "Connection error with federated documentation server."

        if not external_context:
            external_context = f"[Nozomio Fallback] External market information regarding: {query}"

        logger.debug("NozomioRouter: EXTERNAL resolution for '%s' (%d chars)", query[:60], len(external_context))
        return {
            "source": "EXTERNAL_NOZOMIO_MCP",
            "context": external_context,
            "is_private": False
        }
