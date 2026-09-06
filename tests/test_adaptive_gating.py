"""
tests/test_adaptive_gating.py — SDD-SURVIVAL-24

Suíte de testes TDD para o Gating Adaptativo e Interceptador de Segurança.

Valida:
  1. Barreira física Vanguard Guard (Path Traversal fora do monorepo).
  2. Permissão de escritas dentro do monorepo.
  3. Bloqueio total de mutações no modo plan-only.
  4. Prompt CLI de aprovação no modo ask (com mock de input 'y').
  5. Rejeição CLI no modo ask (com mock de input 'n').
  6. Bloqueio de comandos CRITICAL mesmo em auto-approve.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from core.gating_interceptor import GatingInterceptor, GatingViolationException
from core.security_guard import SecurityGuard


class TestSecurityGuardBounds(unittest.TestCase):
    """Testa o Vanguard Bounds Guard de forma isolada."""

    def setUp(self):
        self.guard = SecurityGuard(project_root=".")

    def test_path_within_monorepo_is_safe(self):
        """Caminhos relativos dentro do monorepo devem ser seguros."""
        self.assertTrue(self.guard.is_safe_path("core/database.py"))
        self.assertTrue(self.guard.is_safe_path("tests/test_adaptive_gating.py"))

    def test_path_outside_monorepo_is_unsafe(self):
        """Caminhos absolutos fora do monorepo devem ser bloqueados."""
        self.assertFalse(self.guard.is_safe_path("/etc/passwd"))
        self.assertFalse(self.guard.is_safe_path("C:\\Windows\\System32\\config"))

    def test_empty_path_is_safe_noop(self):
        """Caminhos vazios ou nulos são tratados como noop seguro."""
        self.assertTrue(self.guard.is_safe_path(""))
        self.assertTrue(self.guard.is_safe_path(None))


class TestSecurityGuardCommandClassifier(unittest.TestCase):
    """Testa o classificador de comandos de terminal."""

    def setUp(self):
        self.guard = SecurityGuard(project_root=".")

    def test_critical_commands_detected(self):
        """Comandos intrinsecamente destrutivos são CRITICAL."""
        self.assertEqual(self.guard.classify_command("rm -rf /"), "CRITICAL")
        self.assertEqual(self.guard.classify_command("mkfs /dev/sda"), "CRITICAL")
        self.assertEqual(
            self.guard.classify_command("dd if=/dev/zero of=/dev/sda"), "CRITICAL"
        )

    def test_warning_commands_detected(self):
        """Comandos de infraestrutura são WARNING."""
        self.assertEqual(self.guard.classify_command("npm install express"), "WARNING")
        self.assertEqual(self.guard.classify_command("pip install flask"), "WARNING")
        self.assertEqual(self.guard.classify_command("docker build ."), "WARNING")

    def test_safe_commands_detected(self):
        """Comandos inofensivos são SAFE."""
        self.assertEqual(self.guard.classify_command("ls -la"), "SAFE")
        self.assertEqual(self.guard.classify_command("git status"), "SAFE")
        self.assertEqual(self.guard.classify_command("echo hello"), "SAFE")


class TestAdaptiveGatingInterceptor(unittest.TestCase):
    """Testa o GatingInterceptor com as três réguas de autonomia."""

    def setUp(self):
        self.guard = SecurityGuard(project_root=".")
        self.interceptor = GatingInterceptor(self.guard, default_mode="ask")
        self.mock_execute = MagicMock(return_value="executed_successfully")

    def test_should_block_out_of_bounds_path_mutation(self):
        """Valida a barreira física contra Path Traversal em escritas fora do monorepo."""

        async def run_test():
            with self.assertRaises(GatingViolationException):
                await self.interceptor.intercept_tool_call(
                    tool_name="write_file",
                    tool_category="LOCAL_MUTATION",
                    arguments={"file_path": "/etc/passwd"},
                    execute_fn=self.mock_execute,
                )

        asyncio.run(run_test())

    def test_should_allow_local_path_mutation(self):
        """Valida que escritas dentro do monorepo passam livremente pelo limite físico."""

        async def run_test():
            res = await self.interceptor.intercept_tool_call(
                tool_name="write_file",
                tool_category="LOCAL_MUTATION",
                arguments={"file_path": "core/database.py"},
                execute_fn=self.mock_execute,
            )
            self.assertEqual(res, "executed_successfully")

        asyncio.run(run_test())

    def test_should_block_mutations_in_plan_only_mode(self):
        """Valida que no modo 'plan-only' nenhuma escrita física ou comando é liberado."""
        self.interceptor.set_gating_mode("plan-only")

        async def run_test():
            # Leitura passa livremente
            read_res = await self.interceptor.intercept_tool_call(
                tool_name="get_full_topology",
                tool_category="READ_ONLY",
                arguments={},
                execute_fn=self.mock_execute,
            )
            self.assertEqual(read_res, "executed_successfully")

            # Escrita deve bater no portão de segurança
            with self.assertRaises(GatingViolationException):
                await self.interceptor.intercept_tool_call(
                    tool_name="write_file",
                    tool_category="LOCAL_MUTATION",
                    arguments={"file_path": "src/core.py"},
                    execute_fn=self.mock_execute,
                )

        asyncio.run(run_test())

    @patch("builtins.input", return_value="y")
    def test_should_allow_warning_command_in_ask_mode_with_user_approval(
        self, mock_input
    ):
        """Valida o prompt interativo de terminal liberando comandos perigosos mediante aprovação."""
        self.interceptor.set_gating_mode("ask")

        async def run_test():
            res = await self.interceptor.intercept_tool_call(
                tool_name="execute_command",
                tool_category="DANGEROUS",
                arguments={"command": "npm install"},
                execute_fn=self.mock_execute,
            )
            self.assertEqual(res, "executed_successfully")
            mock_input.assert_called_once()

        asyncio.run(run_test())

    @patch("builtins.input", return_value="n")
    def test_should_block_warning_command_in_ask_mode_when_user_rejects(
        self, mock_input
    ):
        """Valida que negar o input no console CLI aborta a tarefa com exceção."""
        self.interceptor.set_gating_mode("ask")

        async def run_test():
            with self.assertRaises(GatingViolationException):
                await self.interceptor.intercept_tool_call(
                    tool_name="execute_command",
                    tool_category="DANGEROUS",
                    arguments={"command": "pytest"},
                    execute_fn=self.mock_execute,
                )

        asyncio.run(run_test())

    def test_should_block_critical_commands_always_even_in_auto_approve(self):
        """Valida que comandos banidos (ex: rm -rf /) são abortados sumariamente em qualquer regime."""
        self.interceptor.set_gating_mode("auto-approve")

        async def run_test():
            with self.assertRaises(GatingViolationException):
                await self.interceptor.intercept_tool_call(
                    tool_name="execute_command",
                    tool_category="DANGEROUS",
                    arguments={"command": "rm -rf /"},
                    execute_fn=self.mock_execute,
                )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
