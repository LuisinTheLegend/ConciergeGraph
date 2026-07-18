"""
core/probabilistic_retriever.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Probabilistic Retrieval Engine (SA-CTS - U-Mem Pattern) with Thompson Sampling.
Balances exploration and exploitation based on utility metrics (utility_alpha, utility_beta).
"""

from __future__ import annotations

import logging
from typing import Any, Callable
import numpy as np

logger = logging.getLogger("grafo-concierge.probabilistic-retriever")


class ThompsonRetriever:
    """Implements probabilistic retrieval based on Thompson Sampling (SA-CTS).

    Combines vector similarity with historical utility (Beta parameters)
    stored in the vector metadata in Qdrant to balance exploration/exploitation.
    """

    def __init__(self, vector_search_fn: Callable[[str, int], list[Any]]) -> None:
        """Initializes the ThompsonRetriever.

        Args:
            vector_search_fn: Vector search function that returns a list of candidates
                              (VectorSearchResult or equivalent dictionaries), each with
                              metadata containing utility_alpha and utility_beta.
        """
        self.vector_search_fn = vector_search_fn

    @staticmethod
    def sample_multiplier(alpha: float, beta: float) -> float:
        """Samples a probabilistic multiplier using numpy's Beta Distribution."""
        return float(np.random.beta(alpha, beta))

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """Retrieves semantic facts applying Thompson Sampling.

        Steps:
            1. Runs default vector search (semantic similarity).
            2. For each returned candidate, extracts utility_alpha and utility_beta from metadata.
            3. Samples probabilistic multiplier using Beta Distribution:
               thompson_multiplier = ThompsonRetriever.sample_multiplier(alpha, beta)
            4. The candidate's final score will be: vector_similarity * thompson_multiplier.
            5. Returns top_k memories based on final score.
        """
        candidates = self.vector_search_fn(query, limit)
        if not candidates:
            return []

        results = []
        for cand in candidates:
            # Candidate format identification (VectorSearchResult or dict)
            if hasattr(cand, "metadata"):
                metadata = cand.metadata or {}
                similarity = cand.score
                doc_id = cand.doc_id
                node_id = cand.node_id
            elif isinstance(cand, dict):
                metadata = cand.get("metadata") or {}
                similarity = cand.get("vector_score") or cand.get("score") or 0.0
                doc_id = cand.get("doc_id") or cand.get("id")
                node_id = cand.get("node_id")
            else:
                metadata = {}
                similarity = 0.0
                doc_id = None
                node_id = None

            # Get alpha and beta directly from metadata (default 1.0)
            alpha = float(metadata.get("utility_alpha", 1.0))
            beta = float(metadata.get("utility_beta", 1.0))

            # Perform sampling with numpy Beta Distribution
            thompson_multiplier = ThompsonRetriever.sample_multiplier(alpha, beta)
            final_score = similarity * thompson_multiplier

            results.append({
                "doc_id": doc_id,
                "node_id": node_id,
                "score": final_score,
                "raw_score": similarity,
                "utility_alpha": alpha,
                "utility_beta": beta,
                "thompson_multiplier": thompson_multiplier,
                "metadata": metadata
            })

        # Sort descending by final score and select top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
