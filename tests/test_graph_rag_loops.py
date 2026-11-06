"""
tests/test_graph_rag_loops.py — SDD-SURVIVAL-09

Suíte TDD isolada para validar a blindagem contra loops cíclicos indiretos
e limites de travessia no GraphRAGEngine sobre o schema oficial (nodes e edges).

Cenários cobertos:
  1. Ciclo indireto complexo (A -> B -> C -> A) é interrompido sem duplicação.
  2. Substring collision: a.py não captura aa.py nem a_b.py.
  3. Limite de profundidade é respeitado estritamente.
"""

import unittest
import tempfile
import os
import sqlite3
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine
from storage.schema import SchemaManager


class TestGraphRAGLoops(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        # Inicializa o banco físico com o SchemaManager oficial
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)
        self.graph_rag = GraphRAGEngine(self.db_manager)

        self.project_uuid = "proj-test-loops"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (self.project_uuid, "test_loops"),
        )

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                p = self.db_path + ext
                if os.path.exists(p):
                    os.unlink(p)
        except OSError:
            pass

    def _insert_node(self, label: str, node_type: str = "MODULE") -> int:
        self.db_manager.write_query(
            "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, ?, ?, 'ACTIVE');",
            (self.project_uuid, label, node_type),
        )
        rows = self.db_manager.read_query(
            "SELECT id FROM nodes WHERE project_uuid = ? AND label = ?;",
            (self.project_uuid, label),
        )
        return rows[0][0]

    def _insert_call_edge(self, source_id: int, target_id: int):
        self.db_manager.write_query(
            "INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');",
            (source_id, target_id),
        )

    def test_indirect_cycle_resolution(self):
        """Valida que o ciclo indireto A -> B -> C -> A é interrompido sem loops ou duplicações."""
        id_a = self._insert_node("mod_a.py", "MODULE")
        id_b = self._insert_node("mod_b.py", "MODULE")
        id_c = self._insert_node("mod_c.py", "MODULE")

        self._insert_call_edge(id_a, id_b)
        self._insert_call_edge(id_b, id_c)
        self._insert_call_edge(id_c, id_a)

        chain = self.graph_rag.get_call_chain_recursive(start_node="mod_a.py", depth_limit=10)

        # O resultado deve conter apenas as dependências legítimas mod_b.py e mod_c.py
        # O nó raiz mod_a.py é excluído do resultado retornado
        self.assertEqual(len(chain), 2)
        self.assertIn("mod_b.py", chain)
        self.assertIn("mod_c.py", chain)
        self.assertNotIn("mod_a.py", chain)

    def test_substring_collision_prevention(self):
        """Valida que a.py não captura aa.py nem a_b.py."""
        id_a = self._insert_node("a.py", "MODULE")
        id_af = self._insert_node("a.py::f", "FUNCTION")
        id_aa = self._insert_node("aa.py", "MODULE")
        id_aag = self._insert_node("aa.py::g", "FUNCTION")
        id_ab = self._insert_node("a_b.py", "MODULE")
        id_abh = self._insert_node("a_b.py::h", "FUNCTION")

        id_target_a = self._insert_node("target_a.py", "MODULE")
        id_target_aa = self._insert_node("target_aa.py", "MODULE")
        id_target_ab = self._insert_node("target_ab.py", "MODULE")

        self._insert_call_edge(id_af, id_target_a)
        self._insert_call_edge(id_aag, id_target_aa)
        self._insert_call_edge(id_abh, id_target_ab)

        chain = self.graph_rag.get_call_chain_recursive(start_node="a.py", depth_limit=5)

        self.assertEqual(chain, ["target_a.py"])
        self.assertNotIn("target_aa.py", chain)
        self.assertNotIn("target_ab.py", chain)

    def test_depth_limit_enforcement(self):
        """Valida que a travessia obedece estritamente ao limite máximo de profundidade configurado."""
        id_a = self._insert_node("A.py", "MODULE")
        id_b = self._insert_node("B.py", "MODULE")
        id_c = self._insert_node("C.py", "MODULE")
        id_d = self._insert_node("D.py", "MODULE")
        id_e = self._insert_node("E.py", "MODULE")

        self._insert_call_edge(id_a, id_b)
        self._insert_call_edge(id_b, id_c)
        self._insert_call_edge(id_c, id_d)
        self._insert_call_edge(id_d, id_e)

        # Com profundidade máxima de 2 passos a partir de A.py: deve retornar apenas B.py e C.py
        chain = self.graph_rag.get_call_chain_recursive(start_node="A.py", depth_limit=2)

        self.assertEqual(len(chain), 2)
        self.assertIn("B.py", chain)
        self.assertIn("C.py", chain)
        self.assertNotIn("D.py", chain)
        self.assertNotIn("E.py", chain)


if __name__ == "__main__":
    unittest.main()
