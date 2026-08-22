"""
core/search_engine.py — SDD-SURVIVAL-05

Motor de Busca Híbrida com Auto-Cura Vetorial (Query-Time Filter).

Intercepta os resultados brutos do banco vetorial (Qdrant) e executa
uma validação concorrente rápida no SQLite WAL para descartar vetores
órfãos em tempo de execução, garantindo consistência imediata para o
agente sem travas bloqueantes (Two-Phase Commit).

Fluxo:
  1. Busca vetorial bruta → lista de {id, score}
  2. SELECT concorrente no SQLite → conjunto de paths existentes
  3. Filtro de interseção → apenas resultados com respaldo relacional
"""

from typing import Any, List, Dict


class HybridSearchEngine:
    """
    Executa busca híbrida com auto-cura: cruza resultados vetoriais
    com a base relacional SQLite WAL para descartar órfãos em tempo real.
    """

    def __init__(self, db_manager: Any, vector_db: Any):
        self.db_manager = db_manager
        self.vector_db = vector_db

    def hybrid_search(
        self, query_text: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca híbrida com filtro de auto-cura (Query-Time Filter).

        Retorna apenas resultados vetoriais cujo ID existe de fato
        na tabela relacional 'files' do SQLite WAL.
        """
        # 1. Busca vetorial bruta
        raw_results = self.vector_db.search(query_text, limit=limit)
        if not raw_results:
            return []

        # 2. Extrai IDs candidatos e valida contra o SQLite
        candidate_ids = [result["id"] for result in raw_results]
        valid_ids = self._validate_against_sqlite(candidate_ids)

        # 3. Filtra: mantém apenas resultados com respaldo relacional
        return [r for r in raw_results if r["id"] in valid_ids]

    def _validate_against_sqlite(self, candidate_ids: List[str]) -> set:
        """
        Executa SELECT concorrente rápido no SQLite WAL para verificar
        quais IDs candidatos ainda existem na base relacional.
        """
        placeholders = ",".join("?" for _ in candidate_ids)
        rows = self.db_manager.read_query(
            f"SELECT path FROM files WHERE path IN ({placeholders});",
            tuple(candidate_ids),
        )
        return {row[0] for row in rows}
