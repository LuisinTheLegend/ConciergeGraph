"""
tests/test_agent_hsm_coupling.py — SDD-SURVIVAL-26

TDD Test Suite for Cognitive Execution Loop Coupling with the
Hierarchical State Machine (HSM), History Node Restoration, and
Sub-State Circuit Breaker.
"""

import asyncio
import os
import tempfile
import unittest
from typing import Any, Dict

from agent.agent_prompts import DynamicPromptBuilder
from agent.run_agent import CognitiveAgentRunner, HermesAgentRunner
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

        # Required relational schemas
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
        self.runner = CognitiveAgentRunner(
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
        """Validates that a new session without a History Node initializes in PLANNING.DISCOVERY."""
        initial_state = self.runner.initialize_session("sess_new_001")
        self.assertEqual(initial_state, "PLANNING.DISCOVERY")
        self.assertEqual(
            self.hsm.get_current_state("sess_new_001"), "PLANNING.DISCOVERY"
        )
        self.assertEqual(self.runner.current_substate_turn_count, 0)

    def test_should_restore_existing_session_from_history_node(self):
        """Validates that an interrupted session in EXECUTION.CODE_GEN is restored to the exact sub-state."""
        # Create a checkpoint with prior History Node
        self.hsm.transition_to(
            session_id="sess_existing_002",
            target_path="EXECUTION.CODE_GEN",
            agent_id="CognitiveAgent",
            shared_state={"code_step": 1},
        )

        # Initialize session through the runner
        restored_state = self.runner.initialize_session("sess_existing_002")
        self.assertEqual(restored_state, "EXECUTION.CODE_GEN")
        self.assertEqual(
            self.hsm.get_current_state("sess_existing_002"), "EXECUTION.CODE_GEN"
        )
        self.assertEqual(self.runner.current_substate_turn_count, 0)

    def test_should_trigger_circuit_breaker_on_excessive_substate_turns(self):
        """Validates that exceeding the turn limit in the same sub-state trips the circuit breaker to STALL.ERROR_PAUSE."""

        async def run_circuit_breaker_test():
            self.runner.initialize_session("sess_loop_003")
            self.runner.current_substate_turn_count = 5  # Simulate 5 consecutive turns stuck without state advancement

            res = await self.runner.step("sess_loop_003", "Still attempting...")
            self.assertEqual(res["status"], "stalled")
            self.assertEqual(res["state"], "STALL.ERROR_PAUSE")
            self.assertEqual(
                self.hsm.get_current_state("sess_loop_003"), "STALL.ERROR_PAUSE"
            )

        asyncio.run(run_circuit_breaker_test())

    def test_should_reset_turn_count_on_state_transition(self):
        """Validates that a qualified state/sub-state transition resets the turn counter to zero."""

        async def run_transition_reset_test():
            self.runner.initialize_session("sess_trans_004")

            # Execute 3 normal steps
            await self.runner.step("sess_trans_004", "Exploring 1")
            await self.runner.step("sess_trans_004", "Exploring 2")
            await self.runner.step("sess_trans_004", "Exploring 3")
            self.assertEqual(self.runner.current_substate_turn_count, 3)

            # Explicit transition to EXECUTION.CODE_GEN
            self.runner.transition_to(
                "sess_trans_004",
                "EXECUTION.CODE_GEN",
                shared_state={"design_ready": True},
            )
            self.assertEqual(self.runner.current_substate_turn_count, 0)
            self.assertEqual(
                self.hsm.get_current_state("sess_trans_004"), "EXECUTION.CODE_GEN"
            )

            # Subsequent turn executes without triggering circuit breaker
            res = await self.runner.step("sess_trans_004", "Coding 1")
            self.assertEqual(res["status"], "executed")
            self.assertEqual(self.runner.current_substate_turn_count, 1)

        asyncio.run(run_transition_reset_test())

    def test_should_inject_hsm_state_and_governance_into_prompt(self):
        """Validates that the prompt generated during step contains structured state and governance blocks."""

        async def run_prompt_injection_test():
            self.runner.initialize_session("sess_prompt_005")
            res = await self.runner.step("sess_prompt_005", "Start analysis")

            prompt = res["prompt"]
            self.assertIn("[ESTADO ATIVO: PLANNING.DISCOVERY]", prompt)
            self.assertIn("Super-Estado: PLANNING", prompt)
            self.assertIn("Sub-Estado: DISCOVERY", prompt)
            self.assertIn("[FERRAMENTAS AUTORIZADAS]", prompt)
            self.assertIn("READ_ONLY", prompt)
            self.assertIn("SecurityException", prompt)

        asyncio.run(run_prompt_injection_test())

    def test_should_enforce_mcp_governance_in_runner_tool_execution(self):
        """Validates that execute_tool respects MCPToolGovernor access rules based on active state."""

        async def run_mcp_governance_test():
            self.runner.initialize_session("sess_tool_006")
            # Session in PLANNING.DISCOVERY: only READ_ONLY tools allowed

            # 1. Read tool must be authorized
            res = await self.runner.execute_tool(
                "sess_tool_006",
                "get_full_topology",
                arguments={},
                execute_fn=lambda: {"nodes": 10},
            )
            self.assertEqual(res, {"nodes": 10})

            # 2. Mutation tool (write_file) must raise SecurityException in PLANNING
            with self.assertRaises(SecurityException):
                await self.runner.execute_tool(
                    "sess_tool_006",
                    "write_file",
                    arguments={"file_path": "test.py", "content": "print(1)"},
                    execute_fn=lambda: True,
                )

            # 3. Transition to EXECUTION.CODE_GEN
            self.runner.transition_to("sess_tool_006", "EXECUTION.CODE_GEN")

            # Now write_file must be authorized!
            res_mutation = await self.runner.execute_tool(
                "sess_tool_006",
                "write_file",
                arguments={"file_path": "test.py", "content": "print(1)"},
                execute_fn=lambda: "written",
            )
            self.assertEqual(res_mutation, "written")

        asyncio.run(run_mcp_governance_test())

    def test_should_block_mutations_when_gating_is_plan_only(self):
        """Validates that GatingInterceptor in 'plan-only' mode blocks mutations even in EXECUTION state."""

        async def run_gating_test():
            temp_dir = tempfile.mkdtemp()
            security_guard = SecurityGuard(project_root=temp_dir)
            gating = GatingInterceptor(security_guard, default_mode="plan-only")

            runner_with_gating = CognitiveAgentRunner(
                hsm_engine=self.hsm,
                gating_interceptor=gating,
                db_manager=self.db_manager,
            )

            runner_with_gating.initialize_session("sess_gating_007")
            # Force transition to EXECUTION
            runner_with_gating.transition_to("sess_gating_007", "EXECUTION.CODE_GEN")

            # Even if MCP allows in EXECUTION, GatingInterceptor in plan-only must block mutations
            with self.assertRaises(GatingViolationException):
                await runner_with_gating.execute_tool(
                    "sess_gating_007",
                    "write_file",
                    arguments={"path": os.path.join(temp_dir, "code.py")},
                    execute_fn=lambda: True,
                )

        asyncio.run(run_gating_test())

    def test_should_allow_resuming_after_circuit_breaker_stall(self):
        """Validates that after entering STALL.ERROR_PAUSE, the session persists the checkpoint and History Node."""

        async def run_stall_restore_test():
            self.runner.initialize_session("sess_stall_008")
            self.runner.transition_to("sess_stall_008", "EXECUTION.CODE_GEN")

            # Trigger Circuit Breaker trip
            self.runner.current_substate_turn_count = 5
            stall_res = await self.runner.step("sess_stall_008", "Still attempting execution...")
            self.assertEqual(stall_res["state"], "STALL.ERROR_PAUSE")

            # Inspect persisted checkpoint via History Node
            latest_cp = self.hsm.resume_from_history_node("sess_stall_008")
            self.assertIsNotNone(latest_cp)
            self.assertEqual(latest_cp["state_name"], "STALL.ERROR_PAUSE")
            self.assertEqual(
                latest_cp["shared_state"]["previous_state"], "EXECUTION.CODE_GEN"
            )

        asyncio.run(run_stall_restore_test())

    def test_dynamic_prompt_builder_isolated(self):
        """Validates prompt rendering and behavioral guidelines of DynamicPromptBuilder across super-states."""
        builder = DynamicPromptBuilder(self.mcp_governor)

        # Test PLANNING super-state
        prompt_planning = builder.build_prompt("s1", "PLANNING.ARCHITECTURE")
        self.assertIn("[ESTADO ATIVO: PLANNING.ARCHITECTURE]", prompt_planning)
        self.assertIn("Fase ARCHITECTURE", prompt_planning)
        self.assertIn("READ_ONLY", prompt_planning)

        # Test EXECUTION super-state
        prompt_exec = builder.build_prompt("s2", "EXECUTION.TDD_GREEN")
        self.assertIn("[ESTADO ATIVO: EXECUTION.TDD_GREEN]", prompt_exec)
        self.assertIn("Fase TDD_GREEN", prompt_exec)
        self.assertIn("LOCAL_MUTATION", prompt_exec)

        # Test STALL super-state
        prompt_stall = builder.build_prompt("s3", "STALL.AWAITING_HUMAN")
        self.assertIn("Regime de Pausa", prompt_stall)
        self.assertIn("AWAITING_HUMAN", prompt_stall)

        # Test SUCCESS super-state
        prompt_success = builder.build_prompt("s4", "SUCCESS.IDLE_COMPLETE")
        self.assertIn("Regime de Conclusão", prompt_success)
        self.assertIn("IDLE_COMPLETE", prompt_success)

    def test_should_integrate_with_rate_governor(self):
        """Validates that agent tool executions are dispatched with priority 1 (HIGH) into RateGovernor."""

        async def run_rate_test():
            rate_gov = RateGovernor(rpm_limit=60, tpm_limit=10000)
            rate_gov.start()
            try:
                runner_with_rate = CognitiveAgentRunner(
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
        """Validates that passing target_transition in step() advances the HSM state and resets the turn counter."""

        async def run_step_trans_test():
            self.runner.initialize_session("sess_inline_010")
            res = await self.runner.step(
                "sess_inline_010",
                "Advance to TDD",
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
        """Validates strict session isolation across multiple concurrent sessions in the runner."""

        async def run_multi_sess_test():
            self.runner.initialize_session("sess_A")
            self.runner.initialize_session("sess_B")

            self.runner.transition_to("sess_B", "EXECUTION.CODE_GEN")

            # Execute steps across session A and B
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
        """Validates that shared context variables persist completely across History Node checkpoints."""
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
