"""
tests/test_vector_reconciler.py — SDD-SURVIVAL-05

Suíte de Testes TDD para Consistência Eventual e Auto-Cura Vetorial.

Valida os dois mecanismos de defesa contra dessincronização:
  1. Query-Time Filter: busca híbrida descarta vetores órfãos em tempo de execução.
  2. Background Janitor: varredor identifica e expurga órfãos em lote do banco vetorial.

Integra com a infraestrutura real de concorrência (SDD-02) e utiliza um
MockVectorDatabase em memória para simular o comportamento do Qdrant.
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

# 3) core.search_engine
_se_spec = importlib.util.spec_from_file_location(
    "core.search_engine",
    os.path.join(_project_root, "core", "search_engine.py"),
)
_se_mod = importlib.util.module_from_spec(_se_spec)
sys.modules["core.search_engine"] = _se_mod
_se_spec.loader.exec_module(_se_mod)
HybridSearchEngine = _se_mod.HybridSearchEngine

# 4) core.vector_reconciler
_vr_spec = importlib.util.spec_from_file_location(
    "core.vector_reconciler",
    os.path.join(_project_root, "core", "vector_reconciler.py"),
)
_vr_mod = importlib.util.module_from_spec(_vr_spec)
sys.modules["core.vector_reconciler"] = _vr_mod
_vr_spec.loader.exec_module(_vr_mod)
VectorReconciler = _vr_mod.VectorReconciler


class MockVectorDatabase:
    """Mock em memória para simular o comportamento do Qdrant de forma isolada."""

    def __init__(self):
        self.storage = {}  # id -> payload/vector

    def insert(self, vector_id: str, payload: dict):
        self.storage[vector_id] = payload

    def search(self, query_text: str, limit: int = 5):
        # Retorna os itens simulando a estrutura de scores do Qdrant
        results = []
        for vid in list(self.storage.keys())[:limit]:
            results.append({"id": vid, "score": 0.95})
        return results

    def get_all_ids(self):
        return list(self.storage.keys())

    def delete_batch(self, ids_list):
        deleted = []
        for vid in ids_list:
            if vid in self.storage:
                del self.storage[vid]
                deleted.append(vid)
        return deleted


class TestVectorReconciliationAndSelfHealing(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa infraestrutura de concorrência síncrona da Fase 1
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação da tabela de arquivos no SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, "
            "is_dirty INTEGER, community_id TEXT"
            ");"
        )

        # Popula o SQLite com 2 arquivos legítimos
        self.db_manager.write_query(
            "INSERT INTO files (path, content) VALUES ('src/main.py', 'print(1)');"
        )
        self.db_manager.write_query(
            "INSERT INTO files (path, content) VALUES ('src/utils.py', 'print(2)');"
        )

        # Inicializa o banco vetorial Mock e insere os 2 legítimos + 1 órfão
        self.vector_db = MockVectorDatabase()
        self.vector_db.insert("src/main.py", {"text": "print(1)"})
        self.vector_db.insert("src/utils.py", {"text": "print(2)"})
        self.vector_db.insert(
            "src/deleted_file.py", {"text": "print(3)"}
        )  # ÓRFÃO! (Não existe no SQLite)

        # Inicializa os componentes de produção
        self.search_engine = HybridSearchEngine(self.db_manager, self.vector_db)
        self.reconciler = VectorReconciler(self.db_manager, self.vector_db)

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

    def test_should_filter_out_orphan_vectors_at_query_time(self):
        """Garante que a busca híbrida faz o descarte (auto-cura) do vetor órfão em tempo de execução."""
        # A busca vetorial pura trará src/main.py, src/utils.py e src/deleted_file.py (limite=3)
        raw_search_results = self.vector_db.search("any query", limit=3)
        self.assertEqual(len(raw_search_results), 3)

        # A busca híbrida filtrada por auto-cura deve descartar 'src/deleted_file.py'
        filtered_results = self.search_engine.hybrid_search("any query", limit=3)

        # Asserções de Segurança e Consistência
        self.assertEqual(
            len(filtered_results),
            2,
            "O vetor órfão deveria ter sido removido em tempo de execução.",
        )

        returned_ids = [item["id"] for item in filtered_results]
        self.assertIn("src/main.py", returned_ids)
        self.assertIn("src/utils.py", returned_ids)
        self.assertNotIn(
            "src/deleted_file.py",
            returned_ids,
            "O arquivo deletado não pode constar na resposta.",
        )

    def test_background_reconciler_should_delete_orphans_from_vector_db(self):
        """Garante que o varredor Janitor encontra e apaga os vetores órfãos na base vetorial."""
        # Verifica estado inicial
        all_vector_ids_before = self.vector_db.get_all_ids()
        self.assertIn("src/deleted_file.py", all_vector_ids_before)

        # Dispara a reconciliação do Janitor
        deleted_orphans = self.reconciler.reconcile_orphans()

        # Asserções do Varredor
        self.assertEqual(
            deleted_orphans,
            ["src/deleted_file.py"],
            "Deveria ter identificado e deletado exatamente o órfão.",
        )

        # Verifica se o vetor órfão foi fisicamente expurgado da base vetorial mock
        all_vector_ids_after = self.vector_db.get_all_ids()
        self.assertNotIn(
            "src/deleted_file.py",
            all_vector_ids_after,
            "O vetor órfão deveria ter sido apagado fisicamente.",
        )
        self.assertEqual(len(all_vector_ids_after), 2)


if __name__ == "__main__":
    unittest.main()
