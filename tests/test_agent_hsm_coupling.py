"""
tests/test_agent_hsm_coupling.py — SDD-SURVIVAL-26

Suíte de testes TDD para o Acoplamento do Loop Cognitivo Hermes com a
Máquina de Estados Hierárquica (HSM), Restauração de History Nodes e
Circuit Breaker de Sub-Estado.
"""

import asyncio
import os
import tempfile
import unittest
from typing import Any, Dict

from agent.agent_prompts import DynamicPromptBuilder
from agent.run_agent import HermesAgentRunner
from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from core.gating_interceptor import GatingInterceptor, GatingViolationException
from core.hsm_engine import HierarchicalStateMachine
from core.mcp_governor import MCPToolGovernor, SecurityException
from core.rate_governor import RateGovernor
from core.security_guard import SecurityGuard


class TestAgentHSMCoupling(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        # Schemas necessários
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS fsm_checkpoints ("
            "checkpoint_id TEXT, session_id TEXT, agent_id TEXT, state_name TEXT, "
            "shared_state_blob TEXT, task_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (session_id, checkpoint_id)"
            ");"
        )

        self.checkpointer = AgnosticCheckpointer(self.db_manager)
        self.mcp_governor = MCPToolGovernor(default_state="PLANNING")
        self.hsm = HierarchicalStateMachine(
            self.db_manager, self.checkpointer, self.mcp_governor
        )
        self.runner = HermesAgentRunner(
            hsm_engine=self.hsm,
            gating_interceptor=None,
            rate_governor=None,
            db_manager=self.db_manager,
            max_substate_turns=5,
        )

    def tearDown(self):
        try:
            os.close(self.db_fd)
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_should_initialize_new_session_in_planning_discovery(self):
        """Valida que uma nova sessão sem History Node inicia em PLANNING.DISCOVERY"""
        initial_state = self.runner.initialize_session("sess_new_001")
        self.assertEqual(initial_state, "PLANNING.DISCOVERY")
        self.assertEqual(
            self.hsm.get_current_state("sess_new_001"), "PLANNING.DISCOVERY"
        )
        self.assertEqual(self.runner.current_substate_turn_count, 0)

    def test_should_restore_existing_session_from_history_node(self):
        """Valida que uma sessão interrompida em EXECUTION.CODE_GEN é restaurada no mesmo sub-estado"""
        # Cria um checkpoint com History Node prévio
        self.hsm.transition_to(
            session_id="sess_existing_002",
            target_path="EXECUTION.CODE_GEN",
            agent_id="HermesAgent",
            shared_state={"code_step": 1},
        )

        # Inicializa via runner
        restored_state = self.runner.initialize_session("sess_existing_002")
        self.assertEqual(restored_state, "EXECUTION.CODE_GEN")
        self.assertEqual(
            self.hsm.get_current_state("sess_existing_002"), "EXECUTION.CODE_GEN"
        )
        self.assertEqual(self.runner.current_substate_turn_count, 0)

    def test_should_trigger_circuit_breaker_on_excessive_substate_turns(self):
        """Valida que exceder o limite de turnos no mesmo sub-estado força transição para STALL.ERROR_PAUSE"""

        async def run_circuit_breaker_test():
            self.runner.initialize_session("sess_loop_003")
            self.runner.current_substate_turn_count = 5  # Simula 5 turnos presos sem avançar

            res = await self.runner.step("sess_loop_003", "Ainda tentando...")
            self.assertEqual(res["status"], "stalled")
            self.assertEqual(res["state"], "STALL.ERROR_PAUSE")
            self.assertEqual(
                self.hsm.get_current_state("sess_loop_003"), "STALL.ERROR_PAUSE"
            )

        asyncio.run(run_circuit_breaker_test())

    def test_should_reset_turn_count_on_state_transition(self):
        """Valida que a transição de estado/sub-estado reseta o contador de turnos"""

        async def run_transition_reset_test():
            self.runner.initialize_session("sess_trans_004")

            # Executa 3 turnos normais
            await self.runner.step("sess_trans_004", "Explorando 1")
            await self.runner.step("sess_trans_004", "Explorando 2")
            await self.runner.step("sess_trans_004", "Explorando 3")
            self.assertEqual(self.runner.current_substate_turn_count, 3)

            # Transição explícita para EXECUTION.CODE_GEN
            self.runner.transition_to(
                "sess_trans_004",
                "EXECUTION.CODE_GEN",
                shared_state={"design_ready": True},
            )
            self.assertEqual(self.runner.current_substate_turn_count, 0)
            self.assertEqual(
                self.hsm.get_current_state("sess_trans_004"), "EXECUTION.CODE_GEN"
            )

            # Próximo turno executa sem disparar circuit breaker
            res = await self.runner.step("sess_trans_004", "Codificando 1")
            self.assertEqual(res["status"], "executed")
            self.assertEqual(self.runner.current_substate_turn_count, 1)

        asyncio.run(run_transition_reset_test())

    def test_should_inject_hsm_state_and_governance_into_prompt(self):
        """Valida que o prompt gerado no step contém os blocos estruturados de estado e governança"""

        async def run_prompt_injection_test():
            self.runner.initialize_session("sess_prompt_005")
            res = await self.runner.step("sess_prompt_005", "Iniciar análise")

            prompt = res["prompt"]
            self.assertIn("[ESTADO ATIVO: PLANNING.DISCOVERY]", prompt)
            self.assertIn("Super-Estado: PLANNING", prompt)
            self.assertIn("Sub-Estado: DISCOVERY", prompt)
            self.assertIn("[FERRAMENTAS AUTORIZADAS]", prompt)
            self.assertIn("READ_ONLY", prompt)
            self.assertIn("SecurityException", prompt)

        asyncio.run(run_prompt_injection_test())

    def test_should_enforce_mcp_governance_in_runner_tool_execution(self):
        """Valida que execute_tool respeita o bloqueio da MCPToolGovernor conforme o estado ativo"""

        async def run_mcp_governance_test():
            self.runner.initialize_session("sess_tool_006")
            # Sessão em PLANNING.DISCOVERY: apenas READ_ONLY permitida

            # 1. Ferramenta de leitura deve ser autorizada
            res = await self.runner.execute_tool(
                "sess_tool_006",
                "get_full_topology",
                arguments={},
                execute_fn=lambda: {"nodes": 10},
            )
            self.assertEqual(res, {"nodes": 10})

            # 2. Ferramenta de mutação (write_file) deve levantar SecurityException
            with self.assertRaises(SecurityException):
                await self.runner.execute_tool(
                    "sess_tool_006",
                    "write_file",
                    arguments={"file_path": "test.py", "content": "print(1)"},
                    execute_fn=lambda: True,
                )

            # 3. Transita para EXECUTION.CODE_GEN
            self.runner.transition_to("sess_tool_006", "EXECUTION.CODE_GEN")

            # Agora write_file deve ser permitida!
            res_mutation = await self.runner.execute_tool(
                "sess_tool_006",
                "write_file",
                arguments={"file_path": "test.py", "content": "print(1)"},
                execute_fn=lambda: "written",
            )
            self.assertEqual(res_mutation, "written")

        asyncio.run(run_mcp_governance_test())

    def test_should_block_mutations_when_gating_is_plan_only(self):
        """Valida que o GatingInterceptor em regime 'plan-only' barra mutações mesmo em EXECUTION"""

        async def run_gating_test():
            temp_dir = tempfile.mkdtemp()
            security_guard = SecurityGuard(project_root=temp_dir)
            gating = GatingInterceptor(security_guard, default_mode="plan-only")

            runner_with_gating = HermesAgentRunner(
                hsm_engine=self.hsm,
                gating_interceptor=gating,
                db_manager=self.db_manager,
            )

            runner_with_gating.initialize_session("sess_gating_007")
            # Força transição para EXECUTION
            runner_with_gating.transition_to("sess_gating_007", "EXECUTION.CODE_GEN")

            # Mesmo que a MCP permita em EXECUTION, o GatingInterceptor em plan-only deve barrar
            with self.assertRaises(GatingViolationException):
                await runner_with_gating.execute_tool(
                    "sess_gating_007",
                    "write_file",
                    arguments={"path": os.path.join(temp_dir, "code.py")},
                    execute_fn=lambda: True,
                )

        asyncio.run(run_gating_test())

    def test_should_allow_resuming_after_circuit_breaker_stall(self):
        """Valida que após entrar em STALL.ERROR_PAUSE, a sessão persiste o checkpoint e o History Node armazena o estado"""

        async def run_stall_restore_test():
            self.runner.initialize_session("sess_stall_008")
            self.runner.transition_to("sess_stall_008", "EXECUTION.CODE_GEN")

            # Provoca o estouro do Circuit Breaker
            self.runner.current_substate_turn_count = 5
            stall_res = await self.runner.step("sess_stall_008", "Ainda tentando rodar...")
            self.assertEqual(stall_res["state"], "STALL.ERROR_PAUSE")

            # Consulta o checkpoint gerado
            latest_cp = self.hsm.resume_from_history_node("sess_stall_008")
            self.assertIsNotNone(latest_cp)
            self.assertEqual(latest_cp["state_name"], "STALL.ERROR_PAUSE")
            self.assertEqual(
                latest_cp["shared_state"]["previous_state"], "EXECUTION.CODE_GEN"
            )

        asyncio.run(run_stall_restore_test())

    def test_dynamic_prompt_builder_isolated(self):
        """Valida a renderização e diretrizes do DynamicPromptBuilder em vários super-estados"""
        builder = DynamicPromptBuilder(self.mcp_governor)

        # Teste PLANNING
        prompt_planning = builder.build_prompt("s1", "PLANNING.ARCHITECTURE")
        self.assertIn("[ESTADO ATIVO: PLANNING.ARCHITECTURE]", prompt_planning)
        self.assertIn("Fase ARCHITECTURE", prompt_planning)
        self.assertIn("READ_ONLY", prompt_planning)

        # Teste EXECUTION
        prompt_exec = builder.build_prompt("s2", "EXECUTION.TDD_GREEN")
        self.assertIn("[ESTADO ATIVO: EXECUTION.TDD_GREEN]", prompt_exec)
        self.assertIn("Fase TDD_GREEN", prompt_exec)
        self.assertIn("LOCAL_MUTATION", prompt_exec)

        # Teste STALL
        prompt_stall = builder.build_prompt("s3", "STALL.AWAITING_HUMAN")
        self.assertIn("Regime de Pausa", prompt_stall)
        self.assertIn("AWAITING_HUMAN", prompt_stall)

        # Teste SUCCESS
        prompt_success = builder.build_prompt("s4", "SUCCESS.IDLE_COMPLETE")
        self.assertIn("Regime de Conclusão", prompt_success)
        self.assertIn("IDLE_COMPLETE", prompt_success)

    def test_should_integrate_with_rate_governor(self):
        """Valida que chamadas de ferramenta pelo Hermes são despachadas com prioridade 1 no RateGovernor"""

        async def run_rate_test():
            rate_gov = RateGovernor(rpm_limit=60, tpm_limit=10000)
            rate_gov.start()
            try:
                runner_with_rate = HermesAgentRunner(
                    hsm_engine=self.hsm,
                    rate_governor=rate_gov,
                    db_manager=self.db_manager,
                )
                runner_with_rate.initialize_session("sess_rate_009")

                res = await runner_with_rate.execute_tool(
                    "sess_rate_009",
                    "get_full_topology",
                    arguments={},
                    execute_fn=lambda: {"priority_test": True},
                )
                self.assertEqual(res, {"priority_test": True})
            finally:
                rate_gov.shutdown()

        asyncio.run(run_rate_test())

    def test_should_support_inline_transition_during_step(self):
        """Valida que passar target_transition no step avança a HSM e reseta turn count"""

        async def run_step_trans_test():
            self.runner.initialize_session("sess_inline_010")
            res = await self.runner.step(
                "sess_inline_010",
                "Avançar para TDD",
                target_transition="EXECUTION.TDD_GREEN",
                shared_state={"tests_written": 5},
            )
            self.assertEqual(res["status"], "executed")
            self.assertEqual(res["active_state"], "EXECUTION.TDD_GREEN")
            self.assertEqual(
                self.hsm.get_current_state("sess_inline_010"), "EXECUTION.TDD_GREEN"
            )
            self.assertEqual(self.runner.current_substate_turn_count, 0)

        asyncio.run(run_step_trans_test())

    def test_should_isolate_multiple_sessions(self):
        """Valida isolamento estrito entre múltiplas sessões concorrentes no runner"""

        async def run_multi_sess_test():
            self.runner.initialize_session("sess_A")
            self.runner.initialize_session("sess_B")

            self.runner.transition_to("sess_B", "EXECUTION.CODE_GEN")

            # Executa steps em A e B
            await self.runner.step("sess_A", "Input A1")
            await self.runner.step("sess_A", "Input A2")
            await self.runner.step("sess_B", "Input B1")

            self.assertEqual(
                self.hsm.get_current_state("sess_A"), "PLANNING.DISCOVERY"
            )
            self.assertEqual(
                self.hsm.get_current_state("sess_B"), "EXECUTION.CODE_GEN"
            )

        asyncio.run(run_multi_sess_test())

    def test_should_preserve_shared_context_across_history_nodes(self):
        """Valida que o contexto de variáveis compartilhadas persiste integralmente no History Node"""
        self.runner.initialize_session("sess_ctx_012")
        self.runner.transition_to(
            "sess_ctx_012",
            "EXECUTION.CODE_GEN",
            shared_state={"tokens_used": 1500, "files_created": ["main.py"]},
            task_id="task_ctx",
        )

        restored_checkpoint = self.hsm.resume_from_history_node("sess_ctx_012")
        self.assertIsNotNone(restored_checkpoint)
        self.assertEqual(restored_checkpoint["shared_state"]["tokens_used"], 1500)
        self.assertEqual(
            restored_checkpoint["shared_state"]["files_created"], ["main.py"]
        )


if __name__ == "__main__":
    unittest.main()
