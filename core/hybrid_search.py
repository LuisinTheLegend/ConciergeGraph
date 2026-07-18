"""
core/hybrid_search.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Hybrid Search Engine v4 — Complete orchestration of the search pipeline.

This module is the heart of memory retrieval. It orchestrates the three
relevance signals and combines them in the official weighted formula:

    score = (0.50 × vector)
          + (0.25 × normalized_fts5)
          + (0.25 × max(recency, centrality))

Pipeline flow:
    1. STRICT SCOPING — ProjectIndex resolves which project_uuids are
       in scope (Primary Wing, +References, or All Wings).
    2. EMBEDDING — EmbeddingManager generates the query vector.
    3. VECTOR SEARCH — ChromaVectorStore.search() returns candidates
       with cosine similarity scores.
    4. FTS5 SEARCH — SqliteStore.fts_search() returns candidates with
       normalized BM25 scores.
    5. MERGE — Merges both candidate sets by node_id.
    6. HYBRID SCORE — GraphLogic.hybrid_search_score_batch() calculates
       the final weighted score.
    7. SORT — Returns sorted by final_score DESC.

Usage & Integration:
    - core.project_index.ProjectIndex → Strict Scoping
    - storage.vector_store.ChromaVectorStore → Vector search
    - storage.vector_store.EmbeddingManager → Embedding generation
    - storage.store.SqliteStore → FTS5 + Hybrid Score Batch
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.config import ConciergeConfig, DEFAULT_CONFIG
from core.project_index import ProjectIndex
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager

logger = logging.getLogger("grafo-concierge.hybrid-search")


class HybridSearchEngine:
    """Hybrid Search Engine v4 — complete pipeline.

    Combines vector search, FTS5, and Max(Recency, Centrality)
    into a single optimized flow.

    Args:
        sqlite_store: SQLite facade for FTS5 and score batch.
        vector_store: Vector backend for cosine similarity.
        embedding_manager: Query embedding generator.
        project_index: Knowledge GPS for Strict Scoping.
        config: System parameters.
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        embedding_manager: EmbeddingManager,
        project_index: ProjectIndex,
        config: ConciergeConfig = DEFAULT_CONFIG,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._embedder = embedding_manager
        self._project_index = project_index
        self._config = config

    # ===================================================================
    # SEARCH — Main Entry Point
    # ===================================================================

    def search(
        self,
        query: str,
        project_uuid: str,
        top_k: Optional[int] = None,
        include_references: bool = False,
        all_wings: bool = False,
        node_type: Optional[str] = None,
        enable_probabilistic: bool = False,
    ) -> list[dict]:
        """Executes the complete Hybrid Search v4.

        This method implements the 8-step pipeline described in
        Architecture v3.8.

        Args:
            query: Search text (natural or technical language).
            project_uuid: Anchor project UUID.
            top_k: Maximum final results (default: config.search_top_k).
            include_references: Include Reference Wings in scope.
            all_wings: Search in all wings (ignores Strict Scoping).
            node_type: Surgical filter (FACT, SKILL, INSIGHT, etc.).

        Returns:
            List of dicts with final_score and complete breakdown,
            sorted by relevance (DESC).
            Each dict contains:
            {
                "node_id": int,
                "score_final": float,
                "score_breakdown": {
                    "vector": float,
                    "frequency": float,
                    "recency": float,
                    "centrality": float,
                },
                "is_super_node": bool,
            }
        """
        if top_k is None:
            top_k = self._config.search_top_k

        logger.info(
            "Hybrid Search v4: query='%.50s...', project=%s, top_k=%d, "
            "refs=%s, all_wings=%s, node_type=%s",
            query, project_uuid, top_k,
            include_references, all_wings, node_type,
        )

        # --- STEP 1: STRICT SCOPING ---
        scoped_uuids = self._project_index.resolve_scoped_uuids(
            project_uuid,
            include_references=include_references,
            all_wings=all_wings,
        )

        if not scoped_uuids:
            logger.warning("Strict Scoping returned 0 projects — empty search.")
            return []

        logger.debug("Strict Scoping: %d projects in scope.", len(scoped_uuids))

        # --- STEP 2: QUERY EMBEDDING ---
        query_embedding = self._embedder.embed(query)
        if query_embedding is None:
            logger.error("Semantic Fallback: query embedding failed. Returning FTS-only.")
            return self._fts_only_fallback(query, project_uuid, node_type, top_k)

        # --- STEP 3: VECTOR SEARCH ---
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            project_uuids=scoped_uuids,
            top_k=top_k * 3,  # Searches 3x to have enough candidates
            filters={"node_type": node_type} if node_type else None,
        )

        logger.debug("Vector search returned %d candidates.", len(vector_results))

        # Build dict of vector scores by node_id
        # GROUP BY node_id, MAX(score) — as specified in Architecture
        vector_scores: dict[int, float] = {}
        for vr in vector_results:
            if vr.node_id not in vector_scores or vr.score > vector_scores[vr.node_id]:
                vector_scores[vr.node_id] = vr.score

        # --- STEP 4: FTS5 SEARCH ---
        fts_results = self._store.fts_search(
            query=query,
            project_uuid=project_uuid,
            node_type=node_type,
            limit=self._config.fts_limit,
        )

        logger.debug("FTS5 search returned %d candidates.", len(fts_results))

        # Build dict of FTS scores by node_id
        fts_scores: dict[int, float] = {}
        for fr in fts_results:
            node_id = fr.get("id")
            if node_id is not None:
                fts_scores[node_id] = fr.get("bm25_score", 0.0)

        # --- STEP 5: MERGE — Combine candidates from both signals ---
        all_node_ids = set(vector_scores.keys()) | set(fts_scores.keys())

        if not all_node_ids:
            logger.info("No candidates found in both signals.")
            return []

        candidates: list[dict] = []
        for node_id in all_node_ids:
            candidates.append({
                "node_id": node_id,
                "vector_score": vector_scores.get(node_id, 0.0),
                "fts_score": fts_scores.get(node_id, 0.0),
            })

        logger.debug("Merge: %d unique candidates by node_id.", len(candidates))

        # --- STEP 6: HYBRID SCORE ---
        scored_results = self._store.hybrid_search_score_batch(candidates)

        # --- STEP 7: THOMPSON SAMPLING (optional) ---
        if enable_probabilistic:
            scored_results = self._apply_thompson_sampling(scored_results)

        # --- STEP 8: SORT and TRUNCATE ---
        scored_results.sort(key=lambda x: x.get("score_final", 0), reverse=True)
        final = scored_results[:top_k]

        logger.info(
            "Hybrid Search v4 complete: %d candidates → %d final results.",
            len(candidates), len(final),
        )
        return final

    # ===================================================================
    # THOMPSON SAMPLING — Probabilistic multiplier (SA-CTS)
    # ===================================================================

    def _apply_thompson_sampling(self, results: list[dict]) -> list[dict]:
        """Applies Thompson sampling probabilistic multiplier to score_final.

        For each candidate, gets utility_alpha and utility_beta from
        node metadata and samples a multiplier via Beta Distribution.
        The score_final is multiplied by this factor, balancing
        exploration (rarely accessed nodes) and exploitation (proven nodes).

        Args:
            results: List of dicts with score_final and score_breakdown.

        Returns:
            Same list with score_final adjusted by Thompson multiplier.
        """
        from core.probabilistic_retriever import ThompsonRetriever

        for item in results:
            try:
                node = self._store.get_node(item["node_id"])
                alpha = float(node.get("utility_alpha", 1.0) or 1.0)
                beta_param = float(node.get("utility_beta", 1.0) or 1.0)
            except Exception:
                alpha, beta_param = 1.0, 1.0

            multiplier = ThompsonRetriever.sample_multiplier(alpha, beta_param)
            item["score_final"] = round(item["score_final"] * multiplier, 4)
            item["score_breakdown"]["thompson_multiplier"] = round(multiplier, 4)

        return results

    # ===================================================================
    # FALLBACK — Busca apenas FTS5 quando embedding falha
    # ===================================================================

    def _fts_only_fallback(
        self,
        query: str,
        project_uuid: str,
        node_type: Optional[str],
        top_k: int,
    ) -> list[dict]:
        """Fallback: returns results from FTS5 only.

        Used when query embedding fails (Semantic Fallback).
        The results will have no vector score, only BM25 + recency/centrality.
        """
        logger.warning("FTS-only fallback active — results without vector component.")

        fts_results = self._store.fts_search(
            query=query,
            project_uuid=project_uuid,
            node_type=node_type,
            limit=top_k,
        )

        if not fts_results:
            return []

        candidates = [
            {
                "node_id": fr["id"],
                "vector_score": 0.0,  # No vector component
                "fts_score": fr.get("bm25_score", 0.0),
            }
            for fr in fts_results
            if fr.get("id") is not None
        ]

        scored = self._store.hybrid_search_score_batch(candidates)
        scored.sort(key=lambda x: x.get("score_final", 0), reverse=True)
        return scored[:top_k]
