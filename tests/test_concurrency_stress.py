"""
tests/test_concurrency_stress.py — SDD-SURVIVAL-02

Suíte de Testes de Estresse Transacional Massivo.

Simula cenário real de múltiplos subagentes escrevendo simultaneamente
logs de trajetória no SQLite WAL via SerializedWriteQueue.

Asserções validadas:
  1. Zero erros ou travamentos de banco ("database is locked")
  2. SQLite WAL permaneceu livre de locks em 100% das escritas
  3. Contagem final de registros = 500 (integridade física total)
"""

import unittest
import os
import sys
import importlib
import tempfile
import threading


# ── Importação cirúrgica: carrega os módulos diretamente sem acionar
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

# 2) core.database (depende de interface.queue_writer já registrado acima)
_db_spec = importlib.util.spec_from_file_location(
    "core.database",
    os.path.join(_project_root, "core", "database.py"),
)
_db_mod = importlib.util.module_from_spec(_db_spec)
sys.modules["core.database"] = _db_mod
_db_spec.loader.exec_module(_db_mod)
ConciergeDatabaseManager = _db_mod.ConciergeDatabaseManager


class TestConcurrencyAndDelta(unittest.TestCase):
    def setUp(self):
        # Cria banco físico temporário (WAL necessita de arquivo real)
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa e inicia a thread única de gravação
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()

        # Conecta o gerenciador do banco à fila
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

    def tearDown(self):
        # Envia sinal de encerramento para a thread da fila
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)

        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
            # Limpa arquivos auxiliares WAL/SHM que o SQLite pode criar
            for ext in ("-wal", "-shm"):
                wal_path = self.db_path + ext
                if os.path.exists(wal_path):
                    os.unlink(wal_path)
        except OSError:
            pass

    def test_massive_concurrent_writes_should_never_lock_db(self):
        """
        Garante que sob estresse de dezenas de threads de agentes gravando logs,
        o SQLite WAL nunca trave por contenção (database is locked).

        10 threads × 50 escritas = 500 inserções concorrentes.
        """
        num_threads = 10
        writes_per_thread = 50
        errors = []

        def worker(thread_idx):
            for i in range(writes_per_thread):
                success, result = self.db_manager.write_query(
                    "INSERT INTO test_log (thread_name, val) VALUES (?, ?);",
                    (f"Thread-{thread_idx}", i),
                )
                if not success:
                    errors.append(result)

        # Dispara 10 threads (subagentes) executando inserções paralelas em massa
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Asserção 1: Zero erros de concorrência
        self.assertEqual(
            len(errors),
            0,
            f"Ocorreram erros de concorrência ou travas de banco: {errors}",
        )

        # Asserção 2: Integridade transacional — todas as 500 linhas gravadas
        rows = self.db_manager.read_query("SELECT COUNT(*) FROM test_log;")
        self.assertEqual(
            rows[0][0],
            num_threads * writes_per_thread,
            "Nem todas as inserções concorrentes foram salvas.",
        )


if __name__ == "__main__":
    unittest.main()
