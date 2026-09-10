"""
agent/run_agent.py — SDD-SURVIVAL-26

Cognitive Loop Runner coupled with Hierarchical State Machine (HSM).

Features:
    - Deep History Node restoration on initialization (zero token loss on resume).
    - Sub-State Circuit Breaker: Prevents State Lockout and infinite token loops
      by capping maximum turns in a single sub-state (default: 5 turns).
    - Dynamic System Prompt Injection: Injects active qualified state, super-state
      behavioral rules, and MCPToolGovernor boundaries into each reasoning cycle.
    - Triple Governance Tool Pipeline:
        1. MCPToolGovernor (Scope validation)
        2. GatingInterceptor (Path traversal & autonomy regime)
        3. RateGovernor (Priority 1 execution)
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional

from agent.agent_prompts import DynamicPromptBuilder

logger = logging.getLogger(__name__)


class CognitiveAgentRunner:
    """
    Cognitive loop runner coupled to Hierarchical State Machine (HSM).
    """

    def __init__(
        self,
        hsm_engine: Any,
        gating_interceptor: Optional[Any] = None,
        rate_governor: Optional[Any] = None,
        db_manager: Optional[Any] = None,
        max_substate_turns: int = 5,
        prompt_builder: Optional[DynamicPromptBuilder] = None,
    ):
        self.hsm = hsm_engine
        self.gating = gating_interceptor
        self.governor = rate_governor
        self.db = db_manager
        self.max_substate_turns = max_substate_turns
        self.current_substate_turn_count = 0
        self.session_turn_counts: Dict[str, int] = {}

        mcp_gov = getattr(hsm_engine, "mcp_governor", None)
        self.prompt_builder = prompt_builder or DynamicPromptBuilder(mcp_governor=mcp_gov)

        logger.info(
            "[COGNITIVE-RUNNER] Initialized runner with max_substate_turns=%d",
            self.max_substate_turns,
        )

    def initialize_session(
        self, session_id: str, agent_id: str = "CognitiveAgent"
    ) -> str:
        """
        Initializes or restores an agent session.

        Restoration path:
            Queries the Deep History Node (H*). If a prior checkpoint exists,
            the agent resumes exactly at that sub-state.

        New session path:
            Transitions to 'PLANNING.DISCOVERY' as the canonical entrypoint.
        """
        restored_checkpoint = self.hsm.resume_from_history_node(session_id)
        if restored_checkpoint:
            active_path = self.hsm.get_current_state(session_id)
            print(
                f"[HSM-RESUME] Sessao {session_id} restaurada do History Node no sub-estado: {active_path}"
            )
            logger.info(
                "[COGNITIVE-RUNNER] Session '%s' restored from History Node at '%s'.",
                session_id,
                active_path,
            )
            self.current_substate_turn_count = 0
            self.session_turn_counts[session_id] = 0
            return active_path

        # New session starts in PLANNING.DISCOVERY
        initial_path = "PLANNING.DISCOVERY"
        self.hsm.transition_to(
            session_id=session_id,
            target_path=initial_path,
            agent_id=agent_id,
            shared_state={"status": "initialized"},
            task_id="init",
        )
        self.current_substate_turn_count = 0
        self.session_turn_counts[session_id] = 0
        logger.info(
            "[COGNITIVE-RUNNER] New session '%s' initialized at '%s'.",
            session_id,
            initial_path,
        )
        return initial_path

    def transition_to(
        self,
        session_id: str,
        target_path: str,
        agent_id: str = "CognitiveAgent",
        shared_state: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> bool:
        """
        Executes an HSM transition and resets the sub-state turn counter.
        """
        success = self.hsm.transition_to(
            session_id=session_id,
            target_path=target_path,
            agent_id=agent_id,
            shared_state=shared_state or {},
            task_id=task_id,
        )
        if success:
            self.current_substate_turn_count = 0
            self.session_turn_counts[session_id] = 0
            logger.info(
                "[COGNITIVE-RUNNER] State transitioned to '%s' (turn counter reset)",
                target_path,
            )
        return success

    async def step(
        self,
        session_id: str,
        user_input: str,
        agent_id: str = "CognitiveAgent",
        target_transition: Optional[str] = None,
        shared_state: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a single reasoning turn governed by the HSM.

        Step flow:
            1. Sub-State Circuit Breaker Check:
               If turns in current sub-state exceed max_substate_turns,
               transition to STALL.ERROR_PAUSE to halt token drain.
            2. Build Dynamic System Prompt with active HSM state & MCP boundaries.
            3. Apply explicit transition if requested.
            4. Return executed turn payload.
        """
        current_path = self.hsm.get_current_state(session_id)

        # Update turn counters
        self.current_substate_turn_count += 1
        self.session_turn_counts[session_id] = (
            self.session_turn_counts.get(session_id, 0) + 1
        )

        # ─── 1. Sub-State Circuit Breaker ───────────────────────────────
        if self.current_substate_turn_count > self.max_substate_turns:
            print(
                f"[CIRCUIT-BREAKER] Circuit Breaker ativado no sub-estado {current_path}. "
                f"Pausando em STALL.ERROR_PAUSE."
            )
            logger.warning(
                "[COGNITIVE-RUNNER] Circuit Breaker triggered at '%s' (turns=%d > max=%d).",
                current_path,
                self.current_substate_turn_count,
                self.max_substate_turns,
            )
            self.hsm.transition_to(
                session_id=session_id,
                target_path="STALL.ERROR_PAUSE",
                agent_id=agent_id,
                shared_state={
                    "error": "Max substate turns exceeded",
                    "previous_state": current_path,
                    "turns_at_pause": self.current_substate_turn_count,
                },
                task_id=task_id,
            )
            self.current_substate_turn_count = 0
            self.session_turn_counts[session_id] = 0
            return {
                "status": "stalled",
                "reason": "max_turns_exceeded",
                "state": "STALL.ERROR_PAUSE",
                "active_state": "STALL.ERROR_PAUSE",
            }

        # ─── 2. Build Dynamic System Prompt ─────────────────────────────
        system_prompt = self.prompt_builder.build_prompt(
            session_id=session_id,
            current_state=current_path,
            extra_context={
                "turn": self.current_substate_turn_count,
                "user_input": user_input,
            },
        )

        # ─── 3. Optional Explicit Transition ────────────────────────────
        if target_transition:
            self.transition_to(
                session_id=session_id,
                target_path=target_transition,
                agent_id=agent_id,
                shared_state=shared_state,
                task_id=task_id,
            )

        active_state = self.hsm.get_current_state(session_id)
        return {
            "status": "executed",
            "active_state": active_state,
            "turn_count": self.current_substate_turn_count,
            "prompt": system_prompt,
        }

    async def execute_tool(
        self,
        session_id: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        execute_fn: Optional[Callable[[], Any]] = None,
    ) -> Any:
        """
        Executes a tool call through the triple governance pipeline:
            1. MCPToolGovernor: State-based disclosure and access check.
            2. GatingInterceptor: Monorepo boundaries & autonomy regime.
            3. RateGovernor: Priority-based rate-limited queueing (Priority 1 = HIGH).
        """
        args = arguments or {}
        dummy_fn = execute_fn or (lambda: {"status": "success", "tool": tool_name})

        # 1. MCP Tool Governor Scope Check
        gov = getattr(self.hsm, "mcp_governor", None)
        category = "LOCAL_MUTATION"
        if gov:
            gov.validate_tool_execution(session_id, tool_name)
            category = gov.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")

        # 2. Rate Governor Queueing Helper
        def _run_with_governor():
            if self.governor:
                return self.governor.submit_request(
                    priority=1, session_id=session_id, task_fn=dummy_fn
                )
            return dummy_fn()

        # 3. Gating Interceptor Barrier
        if self.gating:
            return await self.gating.intercept_tool_call(
                tool_name=tool_name,
                tool_category=category,
                arguments=args,
                execute_fn=_run_with_governor,
            )

        # If gating is not present, dispatch directly (or via rate governor)
        if inspect.iscoroutinefunction(dummy_fn):
            return await dummy_fn()
        return _run_with_governor()


# Backward compatibility alias
HermesAgentRunner = CognitiveAgentRunner
