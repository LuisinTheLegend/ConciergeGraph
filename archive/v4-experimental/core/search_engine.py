"""
core/search_engine.py — SDD-SURVIVAL-05

Hybrid Search Engine with Self-Healing Vector Validation (Query-Time Filter).

Intercepts raw results from vector database (Qdrant) and executes
a fast concurrent validation against SQLite WAL to discard orphan
vectors at runtime, guaranteeing immediate consistency for the agent
without blocking distributed transactions (Two-Phase Commit).

Flow:
  1. Raw vector search -> list of {id, score}
  2. Concurrent SELECT in SQLite -> set of existing file paths
  3. Intersection filter -> only results backed by relational records
"""

from typing import Any, Dict, List


class HybridSearchEngine:
    """
    Executes hybrid search with self-healing: cross-references vector
    results against relational SQLite WAL to discard orphan records in real time.
    """

    def __init__(self, db_manager: Any, vector_db: Any):
        self.db_manager = db_manager
        self.vector_db = vector_db

    def hybrid_search(
        self, query_text: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search with query-time self-healing filter.

        Returns only vector results whose ID actually exists
        in SQLite WAL 'files' relational table.
        """
        # 1. Raw vector search
        raw_results = self.vector_db.search(query_text, limit=limit)
        if not raw_results:
            return []

        # 2. Extract candidate IDs and validate against SQLite
        candidate_ids = [result["id"] for result in raw_results]
        valid_ids = self._validate_against_sqlite(candidate_ids)

        # 3. Filter: retain only results backed by relational records
        return [r for r in raw_results if r["id"] in valid_ids]

    def _validate_against_sqlite(self, candidate_ids: List[str]) -> set:
        """
        Executes fast concurrent SELECT in SQLite WAL to verify
        which candidate IDs still exist in relational store.
        """
        placeholders = ",".join("?" for _ in candidate_ids)
        rows = self.db_manager.read_query(
            f"SELECT path FROM files WHERE path IN ({placeholders});",
            tuple(candidate_ids),
        )
        return {row[0] for row in rows}
