"""
tests/test_graph_rag_frugal.py — SDD-SURVIVAL-14

Suíte de Testes TDD para o Filtro de Supernó e Throttler Térmico.

Valida isoladamente que o motor do GraphRAG detecta comunidades ignorando
supernós (hubs utilitários) e que as barreiras de hardware regulam as
execuções do BackgroundJanitor sob arquivos recém-modificados.

Testes:
    1. test_supernode_degree_filtering — Supernós são isolados como hub_satellite
    2. test_hardware_throttling_guard — Barreira de hardware bloqueia/libera
"""

import unittest
import tempfile
import os
import time
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine
from core.background_janitor import BackgroundJanitor


class TestGraphRAGFrugal(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)
        self.graph_rag = GraphRAGEngine(self.db_manager)
        self.janitor = BackgroundJanitor(self.db_manager)

        # Criação de Tabelas
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS ast_edges ("
            "parent_node TEXT, child_node TEXT, UNIQUE(parent_node, child_node)"
            ");"
        )
        time.sleep(0.1)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_supernode_degree_filtering(self):
        """Valida se supernós populares são isolados de forma que o grafo não colapse em uma única comunidade"""
        # Cadastra 5 arquivos
        for path in ["src/core.py", "src/auth.py", "src/utils.py", "src/db.py", "src/routes.py"]:
            self.db_manager.write_query(
                "INSERT INTO files (path, community_id, is_dirty, last_modified) VALUES (?, ?, ?, ?);",
                (path, None, 0, time.time())
            )

        # Monta conexões: 'src/utils.py' é o Supernó (Hub conectado a tudo)
        self.db_manager.write_query("INSERT INTO ast_edges VALUES (?, ?);", ("src/core.py", "src/utils.py"))
        self.db_manager.write_query("INSERT INTO ast_edges VALUES (?, ?);", ("src/auth.py", "src/utils.py"))
        self.db_manager.write_query("INSERT INTO ast_edges VALUES (?, ?);", ("src/db.py", "src/utils.py"))
        self.db_manager.write_query("INSERT INTO ast_edges VALUES (?, ?);", ("src/routes.py", "src/utils.py"))

        # Conexão legítima de negócio (ilha de autenticação e rotas)
        self.db_manager.write_query("INSERT INTO ast_edges VALUES (?, ?);", ("src/auth.py", "src/routes.py"))

        time.sleep(0.1)

        # Executa agrupamento definindo teto de in-degree = 2
        # (utils.py tem 4 conexões de entrada, logo será removido como ponte)
        communities = self.graph_rag.detect_logical_communities(in_degree_threshold=2)

        # 'src/utils.py' sendo supernó vira satélite hub de diretório (hub_satellite_src)
        self.assertIn("hub_satellite_src", communities)

        # As dependências menores de negócio formam suas próprias comunidades independentes
        self.assertTrue(
            any("src/auth.py" in files and "src/routes.py" in files for files in communities.values()),
            "auth.py e routes.py devem estar na mesma comunidade (conexão legítima de negócio)"
        )

    def test_hardware_throttling_guard(self):
        """Valida que a barreira de hardware impede o processamento se houver modificações recentes no código"""
        # Insere modificação super recente (0 segundos atrás) no SQLite WAL
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty, last_modified) VALUES (?, ?, ?, ?);",
            ("src/core.py", "core", 1, time.time())
        )
        time.sleep(0.1)

        # O Janitor deve recusar e pular a tarefa para poupar a CPU do host enquanto ele digita
        clearance = self.janitor.check_hardware_clearance(max_cpu_percent=99.0, quiet_period_seconds=10.0)
        self.assertFalse(clearance)

        # Altera modificação para o passado (30 segundos atrás) e valida liberação com quiet_period reduzido
        self.db_manager.write_query(
            "UPDATE files SET last_modified = ? WHERE path = ?;",
            (time.time() - 30.0, "src/core.py")
        )
        time.sleep(0.1)
        clearance = self.janitor.check_hardware_clearance(max_cpu_percent=99.0, quiet_period_seconds=10.0)
        self.assertTrue(clearance)


if __name__ == "__main__":
    unittest.main()
