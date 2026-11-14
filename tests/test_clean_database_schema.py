"""
tests/test_clean_database_schema.py — Integridade do schema de produção do ConciergeDatabaseManager.

Movido de tests/test_concurrency_stress.py para isolar a cobertura viva de
ConciergeDatabaseManager do teste legado com write_queue.
"""

import os
import sqlite3
import tempfile
import unittest

from core.database import ConciergeDatabaseManager
from storage.schema import SchemaManager


class TestCleanDatabaseManagerSchema(unittest.TestCase):
    def test_clean_manager_does_not_leak_test_log(self):
        """
        Garante que ConciergeDatabaseManager não polui o banco com a tabela test_log.
        Tabelas de produção criadas pelo SchemaManager oficial devem permanecer intactas.
        """
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            # 1. Aplica o schema oficial v3.8.0 + tabelas relacionais oficiais
            conn = sqlite3.connect(db_path)
            try:
                sm = SchemaManager(conn)
                sm.apply_full_schema()
            finally:
                conn.close()

            # 2. Instancia o ConciergeDatabaseManager de produção
            db_mgr = ConciergeDatabaseManager(db_path)

            # 3. Consulta tabelas em sqlite_master
            rows = db_mgr.read_query("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [r[0] for r in rows]

            # 4. Asserção principal: test_log NÃO deve existir
            self.assertNotIn(
                "test_log",
                table_names,
                "Tabela de teste 'test_log' vazou no schema de produção!",
            )

            # 5. Asserção de integridade: tabelas legítimas continuam existindo
            for req in ["projects", "nodes", "edges", "agent_checkpoints"]:
                self.assertIn(req, table_names, f"Tabela legítima '{req}' ausente!")
        finally:
            try:
                os.unlink(db_path)
                for ext in (".wal", ".shm", "-wal", "-shm"):
                    p = db_path + ext
                    if os.path.exists(p):
                        os.unlink(p)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
