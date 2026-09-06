"""
core/vector_reconciler.py — SDD-SURVIVAL-05

Eventual Consistency Janitor (Background Vector Reconciler).

Compares IDs present in vector database (Qdrant) with file paths
registered in SQLite WAL 'files' table, identifies orphan vectors
(present in vector DB but missing in relational storage), and physically
purges them in batch.

Strategy:
  - Collect all vector IDs
  - Collect all relational file paths
  - Set difference -> orphan vectors
  - Batch deletion in vector database
"""

from typing import Any, List


class VectorReconciler:
    """
    Consistency reconciler that identifies and purges orphan vectors
    from the vector database when no relational SQLite backing exists.
    """

    def __init__(self, db_manager: Any, vector_db: Any):
        self.db_manager = db_manager
        self.vector_db = vector_db

    def reconcile_orphans(self) -> List[str]:
        """
        Scans both datastores, detects orphan discrepancies, and executes
        physical batch deletion in the vector database.

        Returns list of purged orphan IDs.
        """
        # Collect all IDs from both stores
        vector_ids = set(self.vector_db.get_all_ids())
        sqlite_paths = self._get_all_sqlite_paths()

        # Set difference: IDs present in vector DB but absent in relational DB
        orphan_ids = sorted(vector_ids - sqlite_paths)

        if not orphan_ids:
            return []

        # Physical batch purge
        self.vector_db.delete_batch(orphan_ids)
        return orphan_ids

    def _get_all_sqlite_paths(self) -> set:
        """Collects all file paths registered in SQLite WAL."""
        rows = self.db_manager.read_query("SELECT path FROM files;")
        return {row[0] for row in rows}
