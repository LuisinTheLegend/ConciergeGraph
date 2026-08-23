"""
tests/test_graph_rag_loops.py — SDD-SURVIVAL-09

Suíte TDD isolada para validar a blindagem contra loops cíclicos indiretos
no CTE recursivo do GraphRAGEngine.

Cenários cobertos:
  1. Ciclo indireto complexo (A → B → C → A) é interrompido sem duplicação.
  2. Nomes de arquivo parcialmente similares (auth.js vs oauth.js) não colidem.
  3. Limite de profundidade é respeitado estritamente.
"""

import unittest
import tempfile
import os
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine


class TestGraphRAGLoops(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação da tabela de arestas para os testes
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS ast_edges ("
            "parent_node TEXT, child_node TEXT, UNIQUE(parent_node, child_node)"
            ");"
        )
        self.graph_rag = GraphRAGEngine(self.db_manager)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_indirect_cycle_resolution(self):
        """Valida que o ciclo indireto A -> B -> C -> A é interrompido sem loops ou duplicações"""
        # Insere o ciclo A -> B -> C -> A
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('A', 'B');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('B', 'C');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('C', 'A');")

        # Roda a travessia a partir do nó raiz 'A' com limite de profundidade amplo (10)
        chain = self.graph_rag.get_call_chain_recursive(start_node="A", depth_limit=10)

        # O resultado deve conter apenas as dependências legítimas 'B' e 'C'
        # O nó raiz 'A' não pode reaparecer devido ao filtro final 'node != start_node'
        # O ciclo de recursão deve ser abortado no momento em que 'C' tenta chamar 'A' novamente
        self.assertEqual(len(chain), 2)
        self.assertIn("B", chain)
        self.assertIn("C", chain)
        self.assertNotIn("A", chain)

    def test_substring_collision_prevention(self):
        """Valida que nomes parciais parecidos (ex: auth.js vs oauth.js) não colidem na busca visitada"""
        # Configura o fluxo linear: index.js -> oauth.js -> auth.js -> db.js
        # Se houver busca de substring falha, 'auth.js' será bloqueado achando que já visitou 'oauth.js'
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('index.js', 'oauth.js');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('oauth.js', 'auth.js');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('auth.js', 'db.js');")

        chain = self.graph_rag.get_call_chain_recursive(start_node="index.js", depth_limit=5)

        # Deve mapear toda a cadeia linear até o fim com sucesso
        self.assertEqual(len(chain), 3)
        self.assertIn("oauth.js", chain)
        self.assertIn("auth.js", chain)
        self.assertIn("db.js", chain)

    def test_depth_limit_enforcement(self):
        """Valida que a travessia obedece estritamente ao limite máximo de profundidade configurado"""
        # Cadeia linear: A -> B -> C -> D -> E
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('A', 'B');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('B', 'C');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('C', 'D');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('D', 'E');")

        # Com profundidade máxima de 2 passos a partir de A: deve retornar apenas B e C
        chain = self.graph_rag.get_call_chain_recursive(start_node="A", depth_limit=2)

        self.assertEqual(len(chain), 2)
        self.assertIn("B", chain)
        self.assertIn("C", chain)
        self.assertNotIn("D", chain)
        self.assertNotIn("E", chain)
