"""
tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21).

Valida o catálogo vivo das 31 ferramentas MCP sem depender de mocks fantasmas
ou módulos em quarentena, cobrindo camadas passiva (`filter_tools`) e ativa
(`validate_tool_execution`) além da garantia fail-closed.
"""

from types import SimpleNamespace
import unittest

from core.mcp_governor import MCPToolGovernor, SecurityException


class TestMCPToolGovernor(unittest.TestCase):
    def setUp(self):
        self.governor = MCPToolGovernor(default_state="PLANNING")

        # Ferramentas vivas registradas no FastMCP cobrindo todas as 3 categorias
        # (incluindo ambas as ferramentas DANGEROUS vivas)
        self.live_tools = [
            {"name": "get_full_topology", "description": "Lê topologia"},
            {"name": "concierge_search", "description": "Busca híbrida"},
            {"name": "concierge_commit", "description": "Registra commit"},
            {"name": "delete_project", "description": "Remove projeto"},
            {"name": "reset_collection", "description": "Reseta coleção vetorial"},
        ]

    def test_classification_partition_and_clean_disclosure_matrix(self):
        """Valida partição exata 18/11/2 (31 tools) e allowed_tools vazio nos 8 estados."""
        counts = {"READ_ONLY": 0, "LOCAL_MUTATION": 0, "DANGEROUS": 0}
        for tool_name, category in self.governor.TOOL_CLASSIFICATION.items():
            self.assertIn(category, counts, f"Categoria inesperada em {tool_name}: {category}")
            counts[category] += 1

        self.assertEqual(len(self.governor.TOOL_CLASSIFICATION), 31)
        self.assertEqual(counts, {"READ_ONLY": 18, "LOCAL_MUTATION": 11, "DANGEROUS": 2})

        expected_states = {
            "PLANNING",
            "DISCOVERY",
            "EXECUTION",
            "TDD_GREEN",
            "REFACTORING",
            "MAINTENANCE",
            "STALL",
            "SUCCESS",
        }
        self.assertEqual(set(self.governor.TOOL_DISCLOSURE_MATRIX.keys()), expected_states)
        for state_name, rules in self.governor.TOOL_DISCLOSURE_MATRIX.items():
            self.assertEqual(
                rules["allowed_tools"],
                [],
                f"Estado '{state_name}' deveria ter allowed_tools vazio",
            )

    def test_should_filter_tools_in_planning_state(self):
        """Valida que apenas ferramentas READ_ONLY passam em PLANNING."""
        self.governor.set_session_state("session_123", "PLANNING")

        filtered = self.governor.filter_tools("session_123", self.live_tools)
        tool_names = {t["name"] for t in filtered}

        self.assertEqual(tool_names, {"get_full_topology", "concierge_search"})
        self.assertNotIn("concierge_commit", tool_names)
        self.assertNotIn("delete_project", tool_names)
        self.assertNotIn("reset_collection", tool_names)

        # Também exercita objetos com atributo `.name` (ex.: Tool do FastMCP)
        attr_tools = [SimpleNamespace(name=t["name"]) for t in self.live_tools]
        filtered_attr = {t.name for t in self.governor.filter_tools("session_123", attr_tools)}
        self.assertEqual(filtered_attr, {"get_full_topology", "concierge_search"})

    def test_should_disclose_mutation_tools_in_execution_state(self):
        """Valida que LOCAL_MUTATION é exposta em EXECUTION, mas DANGEROUS segue oculta."""
        self.governor.set_session_state("session_123", "EXECUTION")

        filtered = self.governor.filter_tools("session_123", self.live_tools)
        tool_names = {t["name"] for t in filtered}

        self.assertEqual(tool_names, {"get_full_topology", "concierge_search", "concierge_commit"})
        self.assertNotIn("delete_project", tool_names)
        self.assertNotIn("reset_collection", tool_names)

    def test_should_disclose_all_tools_in_maintenance_state(self):
        """Valida que MAINTENANCE expõe READ_ONLY, LOCAL_MUTATION e ambas as DANGEROUS."""
        self.governor.set_session_state("session_123", "MAINTENANCE")

        filtered = self.governor.filter_tools("session_123", self.live_tools)
        tool_names = {t["name"] for t in filtered}
        self.assertEqual(
            tool_names,
            {
                "get_full_topology",
                "concierge_search",
                "concierge_commit",
                "delete_project",
                "reset_collection",
            },
        )

    def test_should_raise_security_exception_on_direct_call_attempt(self):
        """Valida barreira ativa em validate_tool_execution para PLANNING, EXECUTION e MAINTENANCE."""
        self.governor.set_session_state("session_999", "PLANNING")
        self.assertTrue(self.governor.validate_tool_execution("session_999", "get_full_topology"))
        for blocked in ("concierge_commit", "delete_project", "reset_collection"):
            with self.assertRaises(SecurityException):
                self.governor.validate_tool_execution("session_999", blocked)

        self.governor.set_session_state("session_999", "EXECUTION")
        self.assertTrue(self.governor.validate_tool_execution("session_999", "concierge_commit"))
        for dangerous in ("delete_project", "reset_collection"):
            with self.assertRaises(SecurityException):
                self.governor.validate_tool_execution("session_999", dangerous)

        self.governor.set_session_state("session_999", "MAINTENANCE")
        self.assertTrue(self.governor.validate_tool_execution("session_999", "delete_project"))
        self.assertTrue(self.governor.validate_tool_execution("session_999", "reset_collection"))

    def test_unknown_and_removed_tools_filtered_out_fail_closed(self):
        """Camada passiva (filter_tools): desconhecidas e fantasmas removidas são ocultadas em PLANNING e EXECUTION."""
        candidates = [
            {"name": "get_full_topology"},
            {"name": "concierge_commit"},
            {"name": "unclassified_unknown_tool"},
            {"name": "write_file"},
        ]

        self.governor.set_session_state("sess_fc_filter", "PLANNING")
        planning_names = {t["name"] for t in self.governor.filter_tools("sess_fc_filter", candidates)}
        self.assertEqual(planning_names, {"get_full_topology"})
        self.assertNotIn("unclassified_unknown_tool", planning_names)
        self.assertNotIn("write_file", planning_names)

        self.governor.set_session_state("sess_fc_filter", "EXECUTION")
        exec_names = {t["name"] for t in self.governor.filter_tools("sess_fc_filter", candidates)}
        self.assertEqual(exec_names, {"get_full_topology", "concierge_commit"})
        self.assertNotIn("unclassified_unknown_tool", exec_names)
        self.assertNotIn("write_file", exec_names)

    def test_unknown_and_removed_tools_blocked_in_execution_and_planning(self):
        """Camada ativa (validate_tool_execution): desconhecidas e fantasmas caem em DANGEROUS (fail-closed)."""
        for state in ("PLANNING", "EXECUTION"):
            self.governor.set_session_state("sess_fc_exec", state)
            for tool_name in ("unclassified_unknown_tool", "write_file"):
                with self.assertRaises(SecurityException) as ctx:
                    self.governor.validate_tool_execution("sess_fc_exec", tool_name)
                self.assertIn("DANGEROUS", str(ctx.exception))

    def test_session_state_normalization_invalid_preservation_and_isolation(self):
        """Valida normalização case-insensitive, rejeição segura de estado inválido e isolamento entre sessões."""
        self.governor.set_session_state("sess_a", "execution")
        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")

        # Estado desconhecido preserva estado anterior sem sobrescrever
        self.governor.set_session_state("sess_a", "INVALID_STATE")
        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")

        # Sessão B mantém seu próprio estado (e default_state sem poluição cruzada)
        self.assertEqual(self.governor.get_session_state("sess_b"), "PLANNING")
        self.governor.set_session_state("sess_b", "MAINTENANCE")
        self.assertEqual(self.governor.get_session_state("sess_a"), "EXECUTION")
        self.assertEqual(self.governor.get_session_state("sess_b"), "MAINTENANCE")


if __name__ == "__main__":
    unittest.main()
