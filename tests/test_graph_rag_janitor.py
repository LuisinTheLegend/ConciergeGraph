"""
tests/test_graph_rag_janitor.py — SDD-SURVIVAL-06

Suíte de Testes TDD para GraphRAG Frugal e Background Janitor.

Valida os três contratos de sobrevivência:
  1. Mapeamento topológico: diretório pai como comunidade natural.
  2. Multi-hop recursivo: CTE no SQLite WAL resolve call chains em ms.
  3. Background Janitor: resume comunidades DIRTY via SLM local gratuita.

Integra com a infraestrutura real de concorrência (SDD-02).
"""

import unittest
import os
import sys
import importlib
import tempfile


# ── Importação cirúrgica: carrega módulos diretamente sem acionar
#    os __init__.py dos pacotes (que puxam dependências pesadas). ──

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1) interface.queue_writer
_qw_spec = importlib.util.spec_from_file_location(
    "interface.queue_writer",
    os.path.join(_project_root, "interface", "queue_writer.py"),
)
_qw_mod = importlib.util.module_from_spec(_qw_spec)
sys.modules["interface.queue_writer"] = _qw_mod
_qw_spec.loader.exec_module(_qw_mod)
SerializedWriteQueue = _qw_mod.SerializedWriteQueue

# 2) core.database
_db_spec = importlib.util.spec_from_file_location(
    "core.database",
    os.path.join(_project_root, "core", "database.py"),
)
_db_mod = importlib.util.module_from_spec(_db_spec)
sys.modules["core.database"] = _db_mod
_db_spec.loader.exec_module(_db_mod)
ConciergeDatabaseManager = _db_mod.ConciergeDatabaseManager

# 3) core.graph_rag
_gr_spec = importlib.util.spec_from_file_location(
    "core.graph_rag",
    os.path.join(_project_root, "core", "graph_rag.py"),
)
_gr_mod = importlib.util.module_from_spec(_gr_spec)
sys.modules["core.graph_rag"] = _gr_mod
_gr_spec.loader.exec_module(_gr_mod)
GraphRAGEngine = _gr_mod.GraphRAGEngine

# 4) core.background_janitor
_bj_spec = importlib.util.spec_from_file_location(
    "core.background_janitor",
    os.path.join(_project_root, "core", "background_janitor.py"),
)
_bj_mod = importlib.util.module_from_spec(_bj_spec)
sys.modules["core.background_janitor"] = _bj_mod
_bj_spec.loader.exec_module(_bj_mod)
BackgroundJanitor = _bj_mod.BackgroundJanitor


class TestGraphRAGAndBackgroundJanitor(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa infraestrutura de concorrência síncrona da Fase 1
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação das tabelas relacionais do SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, is_dirty INTEGER, community_id TEXT"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS communities ("
            "id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS ast_edges ("
            "parent_node TEXT, child_node TEXT, UNIQUE(parent_node, child_node)"
            ");"
        )

        # Inicializa as engines
        self.graph_rag = GraphRAGEngine(self.db_manager)
        self.janitor = BackgroundJanitor(self.db_manager)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                wal_path = self.db_path + ext
                if os.path.exists(wal_path):
                    os.unlink(wal_path)
        except OSError:
            pass

    def test_should_map_natural_community_from_file_path(self):
        """Garante a extração determinística da pasta pai como comunidade do arquivo."""
        self.assertEqual(
            self.graph_rag.get_natural_community("core/utils/delta.py"), "core/utils"
        )
        self.assertEqual(
            self.graph_rag.get_natural_community("main.py"), "root"
        )

    def test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive(self):
        """Valida que o SQLite WAL resolve conexões recursivas do grafo AST em < 10ms."""
        # Popula arestas de chamadas AST (A -> B -> C) e (D -> E)
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('core/main.py', 'core/utils.py');"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('core/utils.py', 'core/db.py');"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('interface/api.py', 'interface/auth.py');"
        )

        # Dispara a travessia recursiva iniciando em 'core/main.py'
        call_chain = self.graph_rag.get_call_chain_recursive(
            "core/main.py", depth_limit=3
        )

        # O retorno deve listar de forma recursiva os nós conectados (B e C)
        self.assertEqual(
            len(call_chain),
            2,
            "Deveria ter encontrado exatamente duas dependências recursivas.",
        )
        self.assertIn("core/utils.py", call_chain)
        self.assertIn("core/db.py", call_chain)
        self.assertNotIn(
            "interface/auth.py",
            call_chain,
            "Arestas de subgrafos isolados não podem vazar na busca.",
        )

    def test_background_janitor_should_summarize_dirty_communities_via_local_slm(self):
        """Valida que o varredor de ociosidade resume e limpa os módulos de forma frugal."""
        # Popula arquivos e comunidade marcada como DIRTY (is_dirty = 1)
        self.db_manager.write_query(
            "INSERT INTO communities (id, summary_text, is_dirty) "
            "VALUES ('core', 'Resumo antigo', 1);"
        )
        self.db_manager.write_query(
            "INSERT INTO files (path, content, is_dirty, community_id) "
            "VALUES ('core/main.py', 'print(\"main\")', 1, 'core');"
        )

        # Callback da SLM local gratuita simula geração local a custo financeiro zero
        slm_calls = 0

        def local_slm_mock(payload):
            nonlocal slm_calls
            slm_calls += 1
            return "Resumo local estruturado gerado a custo financeiro zero!"

        # Roda o processamento em background (Idle)
        logs = self.janitor.run_idle_summarization(local_slm_mock)

        # Asserções de Limpeza e Eficiência
        self.assertEqual(
            slm_calls,
            1,
            "A SLM local gratuita deveria ter sido chamada exatamente 1 vez.",
        )
        self.assertIn(
            "core",
            logs,
            "O log de execução deveria conter o ID da comunidade atualizada.",
        )

        # Garante que as flags de sujeira (DIRTY) foram resetadas no SQLite WAL
        comm_state = self.db_manager.read_query(
            "SELECT is_dirty, summary_text FROM communities WHERE id = 'core';"
        )[0]
        self.assertEqual(
            comm_state[0],
            0,
            "A comunidade deveria ter voltado para o status LIMPO (is_dirty = 0).",
        )
        self.assertEqual(
            comm_state[1],
            "Resumo local estruturado gerado a custo financeiro zero!",
        )

        file_state = self.db_manager.read_query(
            "SELECT is_dirty FROM files WHERE path = 'core/main.py';"
        )[0]
        self.assertEqual(
            file_state[0],
            0,
            "O arquivo deveria ter voltado para o status LIMPO (is_dirty = 0).",
        )


if __name__ == "__main__":
    unittest.main()
