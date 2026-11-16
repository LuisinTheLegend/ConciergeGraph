"""
tests/test_local_graph_rag_recursion.py — SDD-SURVIVAL-17

Suíte TDD para validar o algoritmo de Travessia Recursiva Multi-Hop e
Detecção de Comunidades no SQLite WAL com resiliência a ciclos e profundidade controlada.
"""

import unittest
import tempfile
import os
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine


class TestLocalGraphRAGRecursion(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)
        self.graph_rag = GraphRAGEngine(self.db_manager)

        # Criação de Tabelas
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS ast_edges ("
            "parent_node_id TEXT, child_node_id TEXT"
            ");"
        )

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_recursive_multihop_traversal(self):
        """Valida que a travessia alcança corretamente nós em profundidade (multi-hop)"""
        # Monta um caminho linear de dependências: A -> B -> C -> D
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('A.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('B.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('C.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('D.py', 'c2');")

        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('A.py', 'B.py');")
        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('B.py', 'C.py');")
        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('C.py', 'D.py');")

        # Executa travessia a partir de A.py com profundidade 3 (deve capturar B e C)
        context = self.graph_rag.retrieve_multihop_context("A.py", max_depth=3)
        connected_paths = {n["path"] for n in context["connected_nodes"]}

        self.assertIn("A.py", connected_paths)
        self.assertIn("B.py", connected_paths)
        self.assertIn("C.py", connected_paths)
        # D.py não deve ser incluído pois exigiria profundidade 4 (ou seja, 3 saltos a partir do root)
        self.assertNotIn("D.py", connected_paths)

    def test_circular_dependency_resilience(self):
        """Valida que dependências cíclicas (loops infinitos) não causam travamento de pilha"""
        # Monta um ciclo: A -> B -> A
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('A.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('B.py', 'c1');")

        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('A.py', 'B.py');")
        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('B.py', 'A.py');")

        try:
            # Tenta executar a busca recursiva
            context = self.graph_rag.retrieve_multihop_context("A.py", max_depth=4)
            self.assertEqual(len(context["connected_nodes"]), 2)
            self.assertIn("A.py", {n["path"] for n in context["connected_nodes"]})
            self.assertIn("B.py", {n["path"] for n in context["connected_nodes"]})
        except Exception as e:
            self.fail(f"O motor de travessia falhou e causou exceção em dependência cíclica: {str(e)}")

    def test_cycle_guard_prevents_duplicate_relations_in_cross_imports(self):
        """BUG 3: Garante que o path_visited na CTE poda a re-exploração cíclica na ramificação."""
        # Monta ciclo triangular: A -> B -> C -> A
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('X.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('Y.py', 'c1');")
        self.db_manager.write_query("INSERT INTO files (path, community_id) VALUES ('Z.py', 'c1');")

        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('X.py', 'Y.py');")
        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('Y.py', 'Z.py');")
        self.db_manager.write_query("INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('Z.py', 'X.py');")

        # Com max_depth = 5, sem cycle guard ele faria X->Y, Y->Z, Z->X, X->Y...
        # Com path_visited, ao tentar ir de Z para X, X já está no path_visited (|X|Y|Z|), abortando a aresta redundante
        context = self.graph_rag.retrieve_multihop_context("X.py", max_depth=5)
        relations = context["relations"]
        # As arestas devem ser X->Y (depth 1) e Y->Z (depth 2), sem re-entrar em X
        sources_and_targets = [(r["source"], r["target"]) for r in relations]
        self.assertIn(("X.py", "Y.py"), sources_and_targets)
        self.assertIn(("Y.py", "Z.py"), sources_and_targets)
        # Z.py -> X.py não deve ser explorado porque fecharia o ciclo no nó raiz X
        self.assertNotIn(("Z.py", "X.py"), sources_and_targets)


if __name__ == "__main__":
    unittest.main()
