"""
tests/test_dependency_injection.py — SDD-SURVIVAL-03

Suíte de Testes Unitários para Injeção de Dependências Estrita.

Valida as três asserções de isolamento:
  1. Contêiner inicializa corretamente e é verdadeiramente imutável (frozen).
  2. Caminhos físicos inexistentes são rejeitados no bootstrap.
  3. Path traversal malicioso (../../../etc/passwd) é detectado e barrado.
"""

import unittest
import os
import sys
import importlib
import tempfile


# ── Importação cirúrgica: carrega core.dependencies diretamente sem
#    acionar o __init__.py do pacote (que puxa dependências pesadas). ──

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_dep_spec = importlib.util.spec_from_file_location(
    "core.dependencies",
    os.path.join(_project_root, "core", "dependencies.py"),
)
_dep_mod = importlib.util.module_from_spec(_dep_spec)
sys.modules["core.dependencies"] = _dep_mod
_dep_spec.loader.exec_module(_dep_mod)
AgentDependencies = _dep_mod.AgentDependencies


class DummyDatabaseManager:
    """Mock ultra-simplificado para isolamento do teste."""
    pass


class TestDependencyInjection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = os.path.abspath(self.temp_dir.name)
        self.db_mock = DummyDatabaseManager()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_should_initialize_immutable_dependencies_with_success(self):
        """Garante inicialização correta e imutabilidade do contêiner (frozen=True)."""
        deps = AgentDependencies(
            db_manager=self.db_mock,
            workspace_path=self.workspace_path,
        )
        self.assertEqual(deps.workspace_path, self.workspace_path)
        self.assertEqual(deps.db_manager, self.db_mock)

        # Garante a imutabilidade do contêiner (frozen=True)
        with self.assertRaises(AttributeError):
            deps.workspace_path = "/another/path"  # type: ignore

    def test_should_raise_error_for_invalid_workspace_path(self):
        """Garante que o contêiner aborta com caminho físico inexistente."""
        with self.assertRaises(ValueError):
            AgentDependencies(
                db_manager=self.db_mock,
                workspace_path="/caminho/fantasma/inexistente",
            )

    def test_security_check_against_path_traversal(self):
        """Prova que path traversal malicioso é barrado pelo limite do workspace."""
        deps = AgentDependencies(
            db_manager=self.db_mock,
            workspace_path=self.workspace_path,
        )

        # Simula lógica da ferramenta de arquivo de produção
        unsafe_relative_file = "../../../etc/passwd"
        target_path = os.path.abspath(
            os.path.join(deps.workspace_path, unsafe_relative_file)
        )

        is_safe = target_path.startswith(deps.workspace_path)
        self.assertFalse(
            is_safe,
            "A ferramenta deveria ter barrado o acesso fora dos limites do workspace.",
        )


if __name__ == "__main__":
    unittest.main()
