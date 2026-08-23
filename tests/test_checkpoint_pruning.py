"""
tests/test_checkpoint_pruning.py — SDD-SURVIVAL-12

Suíte TDD para validar a Auto-Poda Inteligente de Checkpoints
(Smart LRU per Session) no BackgroundJanitor.

Cenários cobertos:
  1. O checkpoint inicial ("init") é preservado incondicionalmente.
  2. Os N checkpoints mais recentes (keep_limit) são mantidos intactos.
  3. Checkpoints intermediários obsoletos são fisicamente eliminados do banco.
"""

import unittest
import os
import sys
import importlib
import tempfile
import time
import sqlite3


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

# 3) core.checkpointer
_cp_spec = importlib.util.spec_from_file_location(
    "core.checkpointer",
    os.path.join(_project_root, "core", "checkpointer.py"),
)
_cp_mod = importlib.util.module_from_spec(_cp_spec)
sys.modules["core.checkpointer"] = _cp_mod
_cp_spec.loader.exec_module(_cp_mod)
AgnosticCheckpointer = _cp_mod.AgnosticCheckpointer

# 4) core.background_janitor
_bj_spec = importlib.util.spec_from_file_location(
    "core.background_janitor",
    os.path.join(_project_root, "core", "background_janitor.py"),
)
_bj_mod = importlib.util.module_from_spec(_bj_spec)
sys.modules["core.background_janitor"] = _bj_mod
_bj_spec.loader.exec_module(_bj_mod)
BackgroundJanitor = _bj_mod.BackgroundJanitor


class TestCheckpointPruning(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação física da tabela de checkpoints com o schema real
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "agent_id TEXT, "
            "session_id TEXT, "
            "checkpoint_id TEXT, "
            "state_blob TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
            ");"
        )
        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.janitor = BackgroundJanitor(self.db_manager)
        time.sleep(0.1)

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

    def test_smart_lru_pruning_preserves_init_and_recents(self):
        """Valida que a auto-poda remove checkpoints intermediários, mas protege o init e os mais recentes"""
        session_id = "test_session_99"
        agent_id = "test_agent_01"

        # 1. Grava o checkpoint inicial crítico (ID "init") que nunca deve ser apagado
        self.checkpointer.save_checkpoint(
            agent_id, session_id, "init", {"step": 0}
        )
        time.sleep(0.05)

        # 2. Grava 15 checkpoints intermediários em sequência cronológica
        for i in range(1, 16):
            self.checkpointer.save_checkpoint(
                agent_id, session_id, f"step_{i}", {"step": i}
            )
            time.sleep(0.05)

        # 3. Dispara a limpeza do Janitor pedindo para manter no máximo os últimos 5 checkpoints por sessão
        self.janitor.prune_session_checkpoints(session_id=session_id, keep_limit=5)
        time.sleep(0.3)  # Pausa para o processamento assíncrono na fila de escrita

        # 4. Verifica o estado atual do banco físico
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT checkpoint_id FROM agent_checkpoints "
            "WHERE session_id = ? ORDER BY created_at ASC;",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        saved_checkpoint_ids = [r[0] for r in rows]

        # ASSERÇÃO 1: O checkpoint inicial "init" DEVE estar preservado intacto!
        self.assertIn("init", saved_checkpoint_ids)

        # ASSERÇÃO 2: Os 5 checkpoints mais recentes (step_11 a step_15) DEVEM estar preservados intactos!
        for i in range(11, 16):
            self.assertIn(f"step_{i}", saved_checkpoint_ids)

        # ASSERÇÃO 3: Checkpoints antigos intermediários (ex: step_1, step_2, step_10) DEVEM ter sido eliminados
        self.assertNotIn("step_1", saved_checkpoint_ids)
        self.assertNotIn("step_5", saved_checkpoint_ids)
        self.assertNotIn("step_10", saved_checkpoint_ids)

        # ASSERÇÃO 4: Placar final de registros mantidos no banco deve ser exatamente 6 (1 init + 5 recentes)
        self.assertEqual(len(saved_checkpoint_ids), 6)


if __name__ == "__main__":
    unittest.main()
