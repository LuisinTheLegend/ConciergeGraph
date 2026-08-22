"""
tests/test_delta_sync.py — SDD-SURVIVAL-04

Suíte de Testes TDD para Sincronização Delta e Contenção de Custos de IA.

Valida os três contratos críticos do DeltaManager:
  1. Mudanças de lógica interna NÃO marcam a comunidade como DIRTY.
  2. Mudanças estruturais (nova função/classe) MARCAM a comunidade como DIRTY.
  3. Lazy Summarization JIT só aciona a LLM sob demanda, retornando cache quando limpo.

Integra com a infraestrutura real de concorrência da Fase 1:
  - SerializedWriteQueue (SDD-02) para escrita segura no SQLite WAL
  - ConciergeDatabaseManager (SDD-02) para leitura concorrente direta
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

# 3) core.delta_manager
_dm_spec = importlib.util.spec_from_file_location(
    "core.delta_manager",
    os.path.join(_project_root, "core", "delta_manager.py"),
)
_dm_mod = importlib.util.module_from_spec(_dm_spec)
sys.modules["core.delta_manager"] = _dm_mod
_dm_spec.loader.exec_module(_dm_mod)
DeltaManager = _dm_mod.DeltaManager


class TestDeltaSyncAndLazyLoading(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa infraestrutura de concorrência da Fase 1
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Garante a criação das tabelas no SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, "
            "is_dirty INTEGER, community_id TEXT"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS communities ("
            "id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER"
            ");"
        )

        # Insere comunidade inicial de teste
        self.db_manager.write_query(
            "INSERT INTO communities (id, summary_text, is_dirty) "
            "VALUES ('core_module', 'Resumo antigo', 0);"
        )

        self.delta_manager = DeltaManager(self.db_manager)

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

    def test_should_not_trigger_dirty_flag_for_internal_logic_changes(self):
        """Garante que alterar apenas lógicas internas (como ifs) não marca o grafo como sujo."""
        file_path = "core/utils.py"
        base_code = "import os\n\ndef calculate_total(a, b):\n    return a + b\n"

        self.delta_manager.process_file_change(file_path, base_code, "core_module")

        # Simula alteração estritamente de lógica interna
        modified_code = "import os\n\ndef calculate_total(a, b):\n    return a - b  # lógica mudou, assinatura não\n"

        is_structural_change = self.delta_manager.process_file_change(
            file_path, modified_code, "core_module"
        )

        self.assertFalse(
            is_structural_change,
            "Alterações internas de lógica não deveriam sujar a estrutura.",
        )

        comm_dirty = self.db_manager.read_query(
            "SELECT is_dirty FROM communities WHERE id = 'core_module';"
        )[0][0]
        self.assertEqual(
            comm_dirty, 0, "A comunidade deveria ter permanecido limpa."
        )

    def test_should_trigger_dirty_flag_for_structural_signature_changes(self):
        """Garante que adicionar uma nova função ou assinatura suja a comunidade."""
        file_path = "core/utils.py"
        base_code = "import os\n\ndef calculate_total(a, b):\n    return a + b\n"

        self.delta_manager.process_file_change(file_path, base_code, "core_module")

        # Adiciona uma nova declaração estrutural de função
        structural_change_code = (
            "import os\n\n"
            "def calculate_total(a, b):\n    return a + b\n\n"
            "def new_helper_function():\n    pass\n"
        )

        is_structural_change = self.delta_manager.process_file_change(
            file_path, structural_change_code, "core_module"
        )
        self.assertTrue(
            is_structural_change,
            "Adicionar funções deve disparar a mutação estrutural (SSH).",
        )

        comm_dirty = self.db_manager.read_query(
            "SELECT is_dirty FROM communities WHERE id = 'core_module';"
        )[0][0]
        self.assertEqual(
            comm_dirty, 1, "A comunidade deveria ter sido marcada como DIRTY."
        )

    def test_lazy_summarization_should_return_cached_or_recompile_on_demand(self):
        """Valida que o resumo de IA só é gerado sob demanda se o arquivo estiver DIRTY."""
        file_path = "core/utils.py"
        base_code = "def calculate_total(a, b):\n    return a + b\n"
        self.delta_manager.process_file_change(file_path, base_code, "core_module")

        llm_calls = 0

        def cloud_llm_mock(payload):
            nonlocal llm_calls
            llm_calls += 1
            return "Resumo compilado de elite!"

        # Primeira chamada JIT (Deve compilar e chamar a LLM mock)
        summary_v1 = self.delta_manager.compile_community_summary_jit(
            "core_module", cloud_llm_mock
        )
        self.assertEqual(summary_v1, "Resumo compilado de elite!")
        self.assertEqual(llm_calls, 1)

        # Segunda chamada JIT (Deve buscar do cache local sem chamar a LLM mock)
        summary_v2 = self.delta_manager.compile_community_summary_jit(
            "core_module", cloud_llm_mock
        )
        self.assertEqual(summary_v2, "Resumo compilado de elite!")
        self.assertEqual(
            llm_calls,
            1,
            "A LLM não deveria ter sido chamada novamente para dados limpos.",
        )


if __name__ == "__main__":
    unittest.main()
