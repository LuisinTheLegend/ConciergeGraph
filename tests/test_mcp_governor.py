"""
tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21 / BL-014 / BL-015).

Valida o catálogo vivo das 31 ferramentas MCP sem depender de mocks fantasmas
ou módulos em quarentena, cobrindo matriz de 3 estados, default seguro PLANNING,
teto de privilégio (max_state), classificação de concierge_set_state como
LOCAL_MUTATION, validação fail-fast e garantia fail-closed.
"""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.mcp_governor import MCPToolGovernor, SecurityException


class TestMCPToolGovernor(unittest.TestCase):
    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
        self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")

        # Ferramentas vivas registradas no FastMCP cobrindo todas as 3 categorias
        # (incluindo concierge_set_state em LOCAL_MUTATION e ambas DANGEROUS vivas)
        self.live_tools = [
            {"name": "get_full_topology", "description": "Lê topologia"},
            {"name": "concierge_search", "description": "Busca híbrida"},
            {"name": "concierge_set_state", "description": "Transiciona estado"},
            {"name": "concierge_commit", "description": "Registra commit"},
            {"name": "delete_project", "description": "Remove projeto"},
            {"name": "reset_collection", "description": "Reseta coleção vetorial"},
        ]

    def test_classification_partition_and_three_state_disclosure_matrix(self):
        """Valida partição exata 17/12/2 (31 tools), concierge_set_state=LOCAL_MUTATION e matriz de 3 estados."""
        counts = {"READ_ONLY": 0, "LOCAL_MUTATION": 0, "DANGEROUS": 0}
        for tool_name, category in self.governor.TOOL_CLASSIFICATION.items():
            self.assertIn(category, counts, f"Categoria inesperada em {tool_name}: {category}")
            counts[category] += 1

        self.assertEqual(len(self.governor.TOOL_CLASSIFICATION), 31)
        self.assertEqual(self.governor.TOOL_CLASSIFICATION["concierge_set_state"], "LOCAL_MUTATION")
        self.assertEqual(counts, {"READ_ONLY": 17, "LOCAL_MUTATION": 12, "DANGEROUS": 2})

        expected_states = {"PLANNING", "EXECUTION", "MAINTENANCE"}
        self.assertEqual(set(self.governor.TOOL_DISCLOSURE_MATRIX.keys()), expected_states)
        for state_name, rules in self.governor.TOOL_DISCLOSURE_MATRIX.items():
            self.assertEqual(
                rules["allowed_tools"],
                [],
                f"Estado '{state_name}' deveria ter allowed_tools vazio",
            )

    def test_default_state_is_planning_and_fail_fast_validation(self):
        """BL-015 / Decisão 4A: default sem env é PLANNING; estados inválidos ou max < default levantam ValueError."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GRAFO_DEFAULT_STATE", None)
            gov = MCPToolGovernor()
            self.assertEqual(gov.default_state, "PLANNING")
            self.assertEqual(gov.max_state, "PLANNING")
            self.assertEqual(gov.get_session_state("new_sess"), "PLANNING")

        with self.assertRaises(ValueError):
            MCPToolGovernor(default_state="INVALID")

        with self.assertRaises(ValueError):
            MCPToolGovernor(default_state="INVALID", max_state="PLANNING")

        with patch.dict(os.environ, {"GRAFO_DEFAULT_STATE": "INVALID"}, clear=False):
            with self.assertRaises(ValueError):
                MCPToolGovernor()

        with self.assertRaises(ValueError):
            MCPToolGovernor(default_state="PLANNING", max_state="DISCOVERY")

        with self.assertRaises(ValueError):
            MCPToolGovernor(default_state="MAINTENANCE", max_state="EXECUTION")

    def test_privilege_ceiling_blocks_escalation_and_allows_downgrade(self):
        """Decisão 1A: set_session_state bloqueia elevação acima de max_state com SecurityException(PermissionError)."""
        gov_plan = MCPToolGovernor(default_state="PLANNING")
        for forbidden in ("EXECUTION", "MAINTENANCE"):
            with self.assertRaises(SecurityException) as ctx:
                gov_plan.set_session_state("sess_plan", forbidden)
            self.assertIsInstance(ctx.exception, PermissionError)
            self.assertEqual(gov_plan.get_session_state("sess_plan"), "PLANNING")
        gov_plan.set_session_state("sess_plan", "planning")
        self.assertEqual(gov_plan.get_session_state("sess_plan"), "PLANNING")

        gov_exec = MCPToolGovernor(default_state="EXECUTION")
        self.assertEqual(gov_exec.max_state, "EXECUTION")
        gov_exec.set_session_state("sess_exec", "PLANNING")
        self.assertEqual(gov_exec.get_session_state("sess_exec"), "PLANNING")
        gov_exec.set_session_state("sess_exec", "EXECUTION")
        self.assertEqual(gov_exec.get_session_state("sess_exec"), "EXECUTION")
        with self.assertRaises(SecurityException) as ctx_up:
            gov_exec.set_session_state("sess_exec", "MAINTENANCE")
        self.assertIsInstance(ctx_up.exception, PermissionError)
        self.assertEqual(gov_exec.get_session_state("sess_exec"), "EXECUTION")

        # concierge_set_state (LOCAL_MUTATION) bloqueada em PLANNING
        with self.assertRaises(SecurityException) as ctx_set:
            gov_plan.validate_tool_execution("sess_plan", "concierge_set_state")
        self.assertIsInstance(ctx_set.exception, PermissionError)

    def test_should_filter_tools_in_planning_state(self):
        """Valida que apenas ferramentas READ_ONLY passam em PLANNING (excluindo concierge_set_state)."""
        self.governor.set_session_state("session_123", "PLANNING")

        filtered = self.governor.filter_tools("session_123", self.live_tools)
        tool_names = {t["name"] for t in filtered}

        self.assertEqual(tool_names, {"get_full_topology", "concierge_search"})
        self.assertNotIn("concierge_set_state", tool_names)
        self.assertNotIn("concierge_commit", tool_names)
        self.assertNotIn("delete_project", tool_names)
        self.assertNotIn("reset_collection", tool_names)

        # Também exercita objetos com atributo `.name` (ex.: Tool do FastMCP)
        attr_tools = [SimpleNamespace(name=t["name"]) for t in self.live_tools]
        filtered_attr = {t.name for t in self.governor.filter_tools("session_123", attr_tools)}
        self.assertEqual(filtered_attr, {"get_full_topology", "concierge_search"})

    def test_should_disclose_mutation_tools_in_execution_state(self):
        """Valida que LOCAL_MUTATION (incluindo concierge_set_state) é exposta em EXECUTION, mas DANGEROUS segue oculta."""
        self.governor.set_session_state("session_123", "EXECUTION")

        filtered = self.governor.filter_tools("session_123", self.live_tools)
        tool_names = {t["name"] for t in filtered}

        self.assertEqual(
            tool_names,
            {"get_full_topology", "concierge_search", "concierge_set_state", "concierge_commit"},
        )
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
                "concierge_set_state",
                "concierge_commit",
                "delete_project",
                "reset_collection",
            },
        )

    def test_should_raise_security_exception_on_direct_call_attempt(self):
        """Valida barreira ativa em validate_tool_execution para PLANNING, EXECUTION e MAINTENANCE."""
        self.governor.set_session_state("session_999", "PLANNING")
        self.assertTrue(self.governor.validate_tool_execution("session_999", "get_full_topology"))
        for blocked in ("concierge_set_state", "concierge_commit", "delete_project", "reset_collection"):
            with self.assertRaises(SecurityException):
                self.governor.validate_tool_execution("session_999", blocked)

        self.governor.set_session_state("session_999", "EXECUTION")
        self.assertTrue(self.governor.validate_tool_execution("session_999", "concierge_set_state"))
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
