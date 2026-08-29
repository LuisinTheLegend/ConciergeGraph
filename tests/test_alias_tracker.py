"""
tests/test_alias_tracker.py — SDD-SURVIVAL-18 (Hardened)

Suíte de testes TDD para o AliasTracker (rastreamento de codinomes por hash estrutural).
Valida deterministicamente que renomeações e movimentações físicas são resolvidas
com segurança temporal e preservação completa de relacionamentos topológicos e checkpoints,
além de blindar contra arquivos zumbis (timeout purge) e colisões de hash vazio.
"""

import unittest
import tempfile
import os
import time
import hashlib
from core.database import ConciergeDatabaseManager
from core.alias_tracker import AliasTracker, EMPTY_SSH_HASH


class TestAliasTracker(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)
        self.purged_paths = []
        self.tracker = AliasTracker(
            db_manager=self.db_manager,
            hash_generator_callback=lambda p: "structural_hash_mock_123",
            buffer_window_seconds=0.5,
            on_purge_callback=lambda p: self._handle_purge(p),
        )

        # Criação simplificada de schemas de teste
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
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT PRIMARY KEY, task_id TEXT, state_name TEXT"
            ");"
        )

    def _handle_purge(self, rel_path: str):
        """Simula a deleção real do nó do banco quando o timeout de alias expira."""
        self.purged_paths.append(rel_path)
        self.db_manager.write_query("DELETE FROM files WHERE path = ?;", (rel_path,))

    def tearDown(self):
        self.tracker.cancel_all_timers()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_should_track_and_apply_renaming_alias(self):
        """Testa se a renomeação é capturada pelo hash e as FKs herdam as alterações"""
        # Inserir arquivo antigo e referências
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty) VALUES ('src/old_name.py', 'core', 0);"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges (parent_node_id, child_node_id) VALUES ('src/old_name.py', 'utils.py');"
        )
        self.db_manager.write_query(
            "INSERT INTO fsm_checkpoints (checkpoint_id, task_id, state_name) VALUES ('cp_1', 'src/old_name.py', 'PLANNING');"
        )

        # 1. Simula Deleção do Arquivo Antigo
        self.tracker.register_deletion("src/old_name.py", "hash_structural_python_code")

        # 2. Simula Criação do Arquivo Novo em < 500ms
        matched_old = self.tracker.check_and_resolve_creation(
            "src/utils/new_name.py", "hash_structural_python_code"
        )
        self.assertEqual(matched_old, "src/old_name.py")

        # 3. Executa a migração física atômica
        success = self.tracker.apply_alias_migration(
            "src/old_name.py", "src/utils/new_name.py"
        )
        self.assertTrue(success)

        # 4. Asserções de consistência e cascata
        files_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM files WHERE path = 'src/old_name.py';"
        )[0][0]
        self.assertEqual(files_count, 0)

        new_file_exists = self.db_manager.read_query(
            "SELECT COUNT(*) FROM files WHERE path = 'src/utils/new_name.py';"
        )[0][0]
        self.assertEqual(new_file_exists, 1)

        # As arestas AST devem apontar para o novo caminho
        edges_parent = self.db_manager.read_query(
            "SELECT parent_node_id FROM ast_edges;"
        )[0][0]
        self.assertEqual(edges_parent, "src/utils/new_name.py")

        # Os checkpoints FSM de depuração também devem ser preservados
        checkpoint_task = self.db_manager.read_query(
            "SELECT task_id FROM fsm_checkpoints;"
        )[0][0]
        self.assertEqual(checkpoint_task, "src/utils/new_name.py")

    def test_should_ignore_aliasing_if_buffer_window_expires(self):
        """Testa se o alias tracker ignora a colagem de histórico se estourar a janela de tempo"""
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id) VALUES ('src/old.py', 'core');"
        )

        # Registra deleção
        self.tracker.register_deletion("src/old.py", "hash_structural_python_code")

        # Aguarda estourar a janela de buffer de 0.5s
        time.sleep(0.6)

        # Tenta resolver a criação: deve falhar
        matched_old = self.tracker.check_and_resolve_creation(
            "src/new.py", "hash_structural_python_code"
        )
        self.assertIsNone(matched_old)

    def test_should_purge_zombie_node_when_buffer_timeout_expires(self):
        """BUG 1: Valida que deleções legítimas disparam o on_purge_callback para evitar nós zumbis."""
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id) VALUES ('src/zombie_file.py', 'core');"
        )

        # Registra deleção de arquivo real
        self.tracker.register_deletion("src/zombie_file.py", "hash_valid_complex_ast_456")

        # Verifica que ainda está no banco durante a janela de buffer
        self.assertEqual(
            self.db_manager.read_query(
                "SELECT COUNT(*) FROM files WHERE path = 'src/zombie_file.py';"
            )[0][0],
            1,
        )

        # Aguarda o timer assíncrono de 0.5s disparar o expurgo
        time.sleep(0.65)

        # Confirma que o callback foi executado e o nó foi purgado do banco
        self.assertIn("src/zombie_file.py", self.purged_paths)
        self.assertEqual(
            self.db_manager.read_query(
                "SELECT COUNT(*) FROM files WHERE path = 'src/zombie_file.py';"
            )[0][0],
            0,
            "O arquivo excluído definitivamente deveria ter sido purgado do banco pelo timer.",
        )

    def test_should_reject_empty_payload_hash_and_purge_immediately(self):
        """BUG 2: Valida que payloads vazios ('e3b0c4...') são rejeitados e purgados imediatamente."""
        empty_hash = hashlib.sha256(b"").hexdigest()
        self.assertEqual(empty_hash, EMPTY_SSH_HASH)

        self.db_manager.write_query(
            "INSERT INTO files (path, community_id) VALUES ('empty_init.py', 'core');"
        )

        # 1. Deleção de arquivo sem assinatura sintática: deve purgar imediatamente sem enfileirar
        self.tracker.register_deletion("empty_init.py", empty_hash)
        self.assertIn("empty_init.py", self.purged_paths)
        self.assertNotIn("empty_init.py", self.tracker.pending_deletions)

        # 2. Criação de arquivo com hash vazio: deve ser rejeitado sumariamente
        matched = self.tracker.check_and_resolve_creation("another_empty.py", empty_hash)
        self.assertIsNone(matched, "Hashes de payload vazio não podem casar como alias.")


if __name__ == "__main__":
    unittest.main()
