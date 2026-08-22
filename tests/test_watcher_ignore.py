"""
tests/test_watcher_ignore.py — SDD-SURVIVAL-01

Suíte de testes TDD para o Monitor de Arquivos Reativo com Filtro Precoce.

Valida as três asserções críticas de sanidade:
  1. Arquivos .env são sumariamente ignorados (proteção de credenciais).
  2. Árvores node_modules/ são descartadas na borda (economia de CPU).
  3. Arquivos de código legítimos passam e disparam o callback.
"""

import unittest
import os
import sys
import importlib
import pathspec
from watchdog.events import FileSystemEvent

# Importação cirúrgica: carrega interface.watcher diretamente sem
# acionar o __init__.py do pacote (que puxa dependências pesadas como mcp).
_spec = importlib.util.spec_from_file_location(
    "interface.watcher",
    os.path.join(os.path.dirname(__file__), os.pardir, "interface", "watcher.py"),
)
_watcher_mod = importlib.util.module_from_spec(_spec)
sys.modules["interface.watcher"] = _watcher_mod
_spec.loader.exec_module(_watcher_mod)
ConciergeFileSystemHandler = _watcher_mod.ConciergeFileSystemHandler


class TestWatcherIgnore(unittest.TestCase):
    def setUp(self):
        self.project_path = "/workspace/my_project"

        # Padrões simulados do .conciergeignore
        ignore_patterns = [
            ".env",
            "node_modules/",
            "*.log",
            "dist/",
        ]
        self.ignore_spec = pathspec.PathSpec.from_lines(
            "gitignore", ignore_patterns
        )

        # Mock do callback de processamento delta
        self.called_with = []
        self.callback = lambda path: self.called_with.append(path)

        self.handler = ConciergeFileSystemHandler(
            project_path=self.project_path,
            ignore_spec=self.ignore_spec,
            on_valid_change_callback=self.callback,
        )

    def test_should_ignore_private_env_file(self):
        """Garante que salvamentos no .env não disparam callback (proteção de credenciais)."""
        event = FileSystemEvent(os.path.join(self.project_path, ".env"))
        self.handler.on_modified(event)

        self.assertEqual(
            len(self.called_with),
            0,
            "O arquivo .env deveria ter sido ignorado sumariamente.",
        )

    def test_should_ignore_node_modules_files(self):
        """Garante que alterações em pastas pesadas ignoradas sejam abortadas na borda."""
        event = FileSystemEvent(
            os.path.join(self.project_path, "node_modules/package/index.js")
        )
        self.handler.on_modified(event)

        self.assertEqual(
            len(self.called_with),
            0,
            "Arquivos de dependências node_modules devem ser descartados pelo Watchdog.",
        )

    def test_should_allow_and_process_legitimate_code_files(self):
        """Garante que arquivos legítimos passem e disparem o callback com caminho absoluto."""
        valid_file = os.path.join(self.project_path, "src/main.py")
        event = FileSystemEvent(valid_file)
        self.handler.on_modified(event)

        self.assertEqual(len(self.called_with), 1)
        self.assertEqual(
            self.called_with[0],
            os.path.abspath(valid_file),
            "Arquivos legítimos do projeto devem ser aceitos.",
        )


if __name__ == "__main__":
    unittest.main()
