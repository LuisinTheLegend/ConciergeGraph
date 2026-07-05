"""
core/hybrid_search.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Motor de Busca Híbrida v4 — Orquestração completa do pipeline de busca.

Este módulo é o coração da recuperação de memória. Ele orquestra os três
sinais de relevância e combina-os na fórmula ponderada oficial:

    score = (0.50 × vetorial)
          + (0.25 × fts5_normalizado)
          + (0.25 × max(recência, centralidade))

Fluxo do pipeline:
    1. STRICT SCOPING — ProjectIndex resolve quais project_uuids estão
       no escopo (Primary Wing, +References, ou All Wings).
    2. EMBEDDING — EmbeddingManager gera o vetor da query.
    3. BUSCA VETORIAL — ChromaVectorStore.search() retorna candidatos
       com scores de similaridade coseno.
    4. BUSCA FTS5 — SqliteStore.fts_search() retorna candidatos com
       scores BM25 normalizados.
    5. MERGE — Une os dois conjuntos de candidatos por node_id.
    6. SCORE HÍBRIDO — GraphLogic.hybrid_search_score_batch() calcula
       o score final ponderado.
    7. SORT — Retorna ordenado por score_final DESC.

Integração:
    - core.project_index.ProjectIndex → Strict Scoping
    - storage.vector_store.ChromaVectorStore → Busca vetorial
    - storage.vector_store.EmbeddingManager → Geração de embeddings
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
    """Motor de Busca Híbrida v4 — pipeline completo.

    Combina busca vetorial, FTS5 e Max(Recência, Centralidade)
    em um único fluxo otimizado.

    Args:
        sqlite_store: Fachada SQLite para FTS5 e score batch.
        vector_store: Backend vetorial para similaridade coseno.
        embedding_manager: Gerador de embeddings da query.
        project_index: GPS de Conhecimento para Strict Scoping.
        config: Parâmetros do sistema.
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
    # SEARCH — Entry Point principal
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
        """Executa a Busca Híbrida v4 completa.

        Este método implementa o pipeline de 7 etapas descrito na
        Architecture v3.8.

        Args:
            query: Texto de busca (linguagem natural ou técnica).
            project_uuid: UUID do projeto âncora.
            top_k: Máximo de resultados finais (default: config.search_top_k).
            include_references: Incluir Reference Wings no escopo.
            all_wings: Buscar em todas as alas (ignora Strict Scoping).
            node_type: Filtro cirúrgico (FACT, SKILL, INSIGHT, etc.).

        Returns:
            Lista de dicts com score_final e breakdown completo,
            ordenada por relevância (DESC).
            Cada dict contém:
            {
                "node_id": int,
                "score_final": float,
                "score_breakdown": {
                    "vetorial": float,
                    "frequencia": float,
                    "recencia": float,
                    "centralidade": float,
                },
                "is_super_node": bool,
            }
        """
        if top_k is None:
            top_k = self._config.search_top_k

        logger.info(
            "Hybrid Search v4: query='%.50s...', projeto=%s, top_k=%d, "
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
            logger.warning("Strict Scoping retornou 0 projetos — busca vazia.")
            return []

        logger.debug("Strict Scoping: %d projetos no escopo.", len(scoped_uuids))

        # --- STEP 2: EMBEDDING da query ---
        query_embedding = self._embedder.embed(query)
        if query_embedding is None:
            logger.error("Semantic Fallback: embedding da query falhou. Retornando FTS-only.")
            return self._fts_only_fallback(query, project_uuid, node_type, top_k)

        # --- STEP 3: BUSCA VETORIAL ---
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            project_uuids=scoped_uuids,
            top_k=top_k * 3,  # Busca 3x para ter candidatos suficientes
            filters={"node_type": node_type} if node_type else None,
        )

        logger.debug("Busca vetorial retornou %d candidatos.", len(vector_results))

        # Monta dict de scores vetoriais por node_id
        # GROUP BY node_id, MAX(score) — como especificado na Architecture
        vector_scores: dict[int, float] = {}
        for vr in vector_results:
            if vr.node_id not in vector_scores or vr.score > vector_scores[vr.node_id]:
                vector_scores[vr.node_id] = vr.score

        # --- STEP 4: BUSCA FTS5 ---
        fts_results = self._store.fts_search(
            query=query,
            project_uuid=project_uuid,
            node_type=node_type,
            limit=self._config.fts_limit,
        )

        logger.debug("Busca FTS5 retornou %d candidatos.", len(fts_results))

        # Monta dict de scores FTS por node_id
        fts_scores: dict[int, float] = {}
        for fr in fts_results:
            node_id = fr.get("id")
            if node_id is not None:
                fts_scores[node_id] = fr.get("bm25_score", 0.0)

        # --- STEP 5: MERGE — Une candidatos dos dois sinais ---
        all_node_ids = set(vector_scores.keys()) | set(fts_scores.keys())

        if not all_node_ids:
            logger.info("Nenhum candidato encontrado nos dois sinais.")
            return []

        candidates: list[dict] = []
        for node_id in all_node_ids:
            candidates.append({
                "node_id": node_id,
                "vector_score": vector_scores.get(node_id, 0.0),
                "fts_score": fts_scores.get(node_id, 0.0),
            })

        logger.debug("Merge: %d candidatos únicos por node_id.", len(candidates))

        # --- STEP 6: SCORE HÍBRIDO ---
        scored_results = self._store.hybrid_search_score_batch(candidates)

        # --- STEP 7: THOMPSON SAMPLING (opcional) ---
        if enable_probabilistic:
            scored_results = self._apply_thompson_sampling(scored_results)

        # --- STEP 8: SORT e TRUNCATE ---
        scored_results.sort(key=lambda x: x.get("score_final", 0), reverse=True)
        final = scored_results[:top_k]

        logger.info(
            "Hybrid Search v4 concluída: %d candidatos → %d resultados finais.",
            len(candidates), len(final),
        )
        return final

    # ===================================================================
    # THOMPSON SAMPLING — Multiplicador probabilístico (SA-CTS)
    # ===================================================================

    def _apply_thompson_sampling(self, results: list[dict]) -> list[dict]:
        """Aplica multiplicador probabilístico Thompson ao score_final.

        Para cada candidato, obtém utility_alpha e utility_beta dos
        metadados do nó e sorteia um multiplicador via Distribuição Beta.
        O score_final é multiplicado por esse fator, balanceando
        exploração (nós pouco acessados) e explotação (nós comprovados).

        Args:
            results: Lista de dicts com score_final e score_breakdown.

        Returns:
            Mesma lista com score_final ajustado pelo Thompson multiplier.
        """
        import numpy as np

        for item in results:
            try:
                node = self._store.get_node(item["node_id"])
                alpha = float(node.get("utility_alpha", 1.0) or 1.0)
                beta_param = float(node.get("utility_beta", 1.0) or 1.0)
            except Exception:
                alpha, beta_param = 1.0, 1.0

            multiplier = float(np.random.beta(alpha, beta_param))
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
        """Fallback: retorna resultados apenas do FTS5.

        Usado quando o embedding da query falha (Semantic Fallback).
        Os resultados não terão score vetorial, apenas BM25 + recência/centralidade.
        """
        logger.warning("FTS-only fallback ativado — resultados sem componente vetorial.")

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
                "vector_score": 0.0,  # Sem componente vetorial
                "fts_score": fr.get("bm25_score", 0.0),
            }
            for fr in fts_results
            if fr.get("id") is not None
        ]

        scored = self._store.hybrid_search_score_batch(candidates)
        scored.sort(key=lambda x: x.get("score_final", 0), reverse=True)
        return scored[:top_k]
