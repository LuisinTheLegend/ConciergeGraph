"""
core/probabilistic_retriever.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Motor de Recuperação Probabilística (SA-CTS - Padrão U-Mem) com Amostragem de Thompson.
Equilibra exploração e explotação com base nas métricas de utilidade (utility_alpha, utility_beta).
"""

from __future__ import annotations

import logging
from typing import Any, Callable
import numpy as np

logger = logging.getLogger("grafo-concierge.probabilistic-retriever")


class ThompsonRetriever:
    """Implementa a recuperação probabilística baseada em Thompson Sampling (SA-CTS).

    Combina similaridade vetorial com a utilidade histórica (parâmetros Beta)
    armazenados nos metadados do vetor no Qdrant para balancear exploração/explotação.
    """

    def __init__(self, vector_search_fn: Callable[[str, int], list[Any]]) -> None:
        """Inicializa o ThompsonRetriever.

        Args:
            vector_search_fn: Função de busca vetorial que retorna uma lista de candidatos
                              (VectorSearchResult ou dicionários equivalentes), cada um com
                              metadados contendo utility_alpha e utility_beta.
        """
        self.vector_search_fn = vector_search_fn

    @staticmethod
    def sample_multiplier(alpha: float, beta: float) -> float:
        """Sorteia um multiplicador probabilístico usando a Distribuição Beta do numpy."""
        return float(np.random.beta(alpha, beta))

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        top_k: int = 3
    ) -> list[dict[str, Any]]:
        """Recupera fatos semânticos aplicando Thompson Sampling.

        Etapas:
            1. Executa a busca vetorial padrão (similaridade semântica).
            2. Para cada candidato retornado, extrai utility_alpha e utility_beta do metadado.
            3. Sorteia multiplicador probabilístico usando a Distribuição Beta:
               thompson_multiplier = ThompsonRetriever.sample_multiplier(alpha, beta)
            4. O score final do candidato será: similaridade_vetorial * thompson_multiplier.
            5. Retorna as top_k memórias baseadas no score final.
        """
        candidates = self.vector_search_fn(query, limit)
        if not candidates:
            return []

        results = []
        for cand in candidates:
            # Identificação do formato do candidato (VectorSearchResult ou dict)
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

            # Obtém alpha e beta diretamente dos metadados (default 1.0)
            alpha = float(metadata.get("utility_alpha", 1.0))
            beta = float(metadata.get("utility_beta", 1.0))

            # Realiza sorteio com a Distribuição Beta do numpy
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

        # Ordena desc pelo score final e seleciona top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
