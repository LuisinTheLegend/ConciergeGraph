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
if "interface" not in sys.modules:
    import interface
setattr(sys.modules["interface"], "queue_writer", _qw_mod)
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

        # Aplica o SchemaManager oficial v3.8.0
        import sqlite3
        from storage.schema import SchemaManager
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        # Cria tabelas legadas do background_janitor (mantidas para compatibilidade dos testes do janitor)
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
        """Valida que a travessia recursiva resolve conexões multi-hop no grafo canônico (nodes e edges)."""
        p_uuid = "proj-janitor-multihop"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (p_uuid, "janitor_multihop"),
        )
        # Popula nós canônicos
        for mod in ["core/main.py", "core/utils.py", "core/db.py", "interface/api.py", "interface/auth.py"]:
            self.db_manager.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, ?, 'MODULE', 'ACTIVE');",
                (p_uuid, mod),
            )

        def get_id(lbl):
            return self.db_manager.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = ?;", (p_uuid, lbl)
            )[0][0]

        id_main = get_id("core/main.py")
        id_utils = get_id("core/utils.py")
        id_db = get_id("core/db.py")
        id_api = get_id("interface/api.py")
        id_auth = get_id("interface/auth.py")

        # Popula arestas canônicas com relation_type = 'calls'
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_main, id_utils))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_utils, id_db))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_api, id_auth))

        # Dispara a travessia recursiva iniciando em 'core/main.py'
        call_chain = self.graph_rag.get_call_chain_recursive(
            "core/main.py", depth_limit=3
        )

        # O retorno deve listar de forma recursiva os nós conectados (core/utils.py e core/db.py)
        # O nó raiz 'core/main.py' é excluído do resultado retornado
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
