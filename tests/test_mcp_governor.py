"""
tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21).

Copiado de tests/test_progressive_tool_disclosure.py (sem TestClient / interface.telemetry_api)
para manter a cobertura viva do governador independente dos módulos dormentes.
"""

import unittest

from core.mcp_governor import MCPToolGovernor, SecurityException


class TestMCPToolGovernor(unittest.TestCase):
    def setUp(self):
        self.governor = MCPToolGovernor(default_state="PLANNING")

        # Mock de ferramentas registradas no FastMCP (inclui mocks legados até limpeza 4.5g)
        self.mock_tools = [
            {"name": "get_full_topology", "description": "Lê topologia"},
            {"name": "write_file", "description": "Escreve arquivos"},
            {"name": "execute_command", "description": "Executa comandos"},
            {"name": "get_telemetry_snapshot", "description": "Snap de telemetria"},
        ]

    def test_should_filter_tools_in_planning_state(self):
        """Valida que apenas ferramentas de leitura e telemetria passam no estágio de planejamento"""
        self.governor.set_session_state("session_123", "PLANNING")

        filtered = self.governor.filter_tools("session_123", self.mock_tools)
        tool_names = {t["name"] for t in filtered}

        # get_full_topology (READ_ONLY) e get_telemetry_snapshot (allowed_tools) devem passar
        self.assertIn("get_full_topology", tool_names)
        self.assertIn("get_telemetry_snapshot", tool_names)

        # write_file (LOCAL_MUTATION) e execute_command (DANGEROUS) devem ser ocultadas
        self.assertNotIn("write_file", tool_names)
        self.assertNotIn("execute_command", tool_names)

    def test_should_disclose_mutation_tools_in_execution_state(self):
        """Valida que ferramentas de escrita física são expostas na transição para EXECUTION"""
        self.governor.set_session_state("session_123", "EXECUTION")

        filtered = self.governor.filter_tools("session_123", self.mock_tools)
        tool_names = {t["name"] for t in filtered}

        self.assertIn("get_full_topology", tool_names)
        self.assertIn("write_file", tool_names)  # Desbloqueado!
        self.assertIn("get_telemetry_snapshot", tool_names)

        # execute_command (DANGEROUS) continua restrito
        self.assertNotIn("execute_command", tool_names)

    def test_should_disclose_all_tools_in_maintenance_state(self):
        """Valida que no modo de manutenção total e administrativa do monorepo todos os comandos são expostos"""
        self.governor.set_session_state("session_123", "MAINTENANCE")

        filtered = self.governor.filter_tools("session_123", self.mock_tools)
        self.assertEqual(len(filtered), 4)

    def test_should_raise_security_exception_on_direct_call_attempt(self):
        """Valida que tentar injetar comandos ocultados via chamada de API direta lança erro ativo"""
        self.governor.set_session_state("session_999", "PLANNING")

        # Tentativa de chamada de leitura: OK
        allowed = self.governor.validate_tool_execution("session_999", "get_full_topology")
        self.assertTrue(allowed)

        # Tentativa de chamada de modificação: Deve estourar exceção de segurança ativa
        with self.assertRaises(SecurityException):
            self.governor.validate_tool_execution("session_999", "write_file")


if __name__ == "__main__":
    unittest.main()
