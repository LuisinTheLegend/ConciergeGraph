"""
core/vector_reconciler.py — SDD-SURVIVAL-05

Varredor Janitor de Consistência Eventual (Background Reconciler).

Compara os IDs existentes no banco vetorial (Qdrant) com os caminhos
registrados na tabela 'files' do SQLite WAL, identifica vetores órfãos
(presentes apenas no vetor) e os expurga em lote fisicamente.

Estratégia:
  - Coleta total dos IDs vetoriais
  - Coleta total dos paths relacionais
  - Diferença de conjuntos → órfãos
  - Deleção em lote no banco vetorial
"""

from typing import Any, List


class VectorReconciler:
    """
    Varredor de consistência que identifica e expurga vetores órfãos
    do banco vetorial que não possuem mais respaldo no SQLite WAL.
    """

    def __init__(self, db_manager: Any, vector_db: Any):
        self.db_manager = db_manager
        self.vector_db = vector_db

    def reconcile_orphans(self) -> List[str]:
        """
        Varre ambos os bancos, identifica discrepâncias órfãs e executa
        a deleção em lote física no banco vetorial.

        Retorna a lista de IDs órfãos que foram expurgados.
        """
        # Coleta todos os IDs de ambos os lados
        vector_ids = set(self.vector_db.get_all_ids())
        sqlite_paths = self._get_all_sqlite_paths()

        # Diferença de conjuntos: IDs presentes no vetor mas ausentes no relacional
        orphan_ids = sorted(vector_ids - sqlite_paths)

        if not orphan_ids:
            return []

        # Expurgo em lote físico
        self.vector_db.delete_batch(orphan_ids)
        return orphan_ids

    def _get_all_sqlite_paths(self) -> set:
        """Coleta todos os caminhos de arquivos registrados no SQLite WAL."""
        rows = self.db_manager.read_query("SELECT path FROM files;")
        return {row[0] for row in rows}
