"""
tests/test_progressive_tool_disclosure.py — SDD-SURVIVAL-21

Suíte de testes TDD para Ocultação Progressiva de Ferramentas (Progressive Tool Disclosure).

Valida isoladamente:
  1. Filtragem passiva na listagem de ferramentas no estágio PLANNING (apenas READ_ONLY).
  2. Revelação seletiva de ferramentas de escrita no estágio EXECUTION (LOCAL_MUTATION).
  3. Divulgação irrestrita no estágio MAINTENANCE (incluindo DANGEROUS).
  4. Bloqueio ativo de chamadas com lançamento de SecurityException em tentativas de injeção.
  5. Endpoints REST da Telemetry API (/api/mcp/state).
"""

import unittest
from fastapi.testclient import TestClient

from core.mcp_governor import MCPToolGovernor, SecurityException
from interface.telemetry_api import app, mcp_governor


class TestProgressiveToolDisclosure(unittest.TestCase):
    def setUp(self):
        self.governor = MCPToolGovernor(default_state="PLANNING")

        # Mock de ferramentas registradas no FastMCP
        self.mock_tools = [
            {"name": "get_full_topology", "description": "Lê topologia"},
            {"name": "write_file", "description": "Escreve arquivos"},
            {"name": "execute_command", "description": "Executa comandos"},
            {"name": "get_telemetry_snapshot", "description": "Snap de telemetria"},
        ]

        self.client = TestClient(app)

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

    def test_telemetry_api_mcp_state_endpoints(self):
        """Valida os endpoints REST /api/mcp/state (POST) e /api/mcp/state/{session_id} (GET)"""
        session_id = "sess_fsm_control"

        # 1. Consulta estado default inicial (PLANNING)
        resp_get_default = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_default.status_code, 200)
        self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")

        # 2. Atualiza estado para EXECUTION via POST
        resp_post = self.client.post(
            "/api/mcp/state",
            json={"session_id": session_id, "state_name": "EXECUTION"},
        )
        self.assertEqual(resp_post.status_code, 200)
        data = resp_post.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["active_state"], "EXECUTION")

        # 3. Consulta estado atualizado via GET
        resp_get_updated = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_updated.status_code, 200)
        self.assertEqual(resp_get_updated.json()["active_state"], "EXECUTION")


if __name__ == "__main__":
    unittest.main()
