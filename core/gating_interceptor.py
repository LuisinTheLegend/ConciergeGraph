"""
core/gating_interceptor.py — SDD-SURVIVAL-24

Adaptive Gating Interceptor for IDE, MCP, and Terminal.

Regulates agent autonomy (Hermes / Nexus) through three strict regimes:
  plan-only    — Read-only access. Physical mutations and terminal commands blocked.
  ask          — Local file mutations auto-approved. WARNING commands require
                 interactive human developer approval via async non-blocking CLI prompt.
  auto-approve — Full autonomy. Only inherently CRITICAL commands are banned.

Security Invariants:
  1. Vanguard Bounds Guard (impassable): Blocks any file operation outside
     the monorepo boundaries regardless of active gating mode.
  2. CRITICAL Command Blacklist: rm -rf /, mkfs, dd if, etc.
     Summarily blocked in all modes.
  3. Async CLI Prompt: Uses asyncio.run_in_executor to capture input()
     without freezing the FastMCP/FastAPI Event Loop.
"""

import asyncio
import logging
import sys
from typing import Any, Callable, Dict

from core.security_guard import SecurityGuard

logger = logging.getLogger(__name__)


class GatingViolationException(Exception):
    """Exception raised when an Adaptive Gating governance rule is violated."""

    pass


class GatingInterceptor:
    """
    Tool invocation interceptor enforcing adaptive gating rules.

    Parameters:
      security_guard — SecurityGuard instance configured with project_root.
      default_mode   — Initial gating regime ("plan-only", "ask", or "auto-approve").
    """

    VALID_MODES = {"plan-only", "ask", "auto-approve"}

    def __init__(self, security_guard: SecurityGuard, default_mode: str = "ask"):
        clean_mode = default_mode.lower()
        if clean_mode not in self.VALID_MODES:
            clean_mode = "ask"
        self.current_mode = clean_mode
        self.guard = security_guard
        # Prevents interleaved CLI prompts if multiple subagents request approval concurrently
        self._interactive_lock = asyncio.Lock()

    def set_gating_mode(self, mode: str) -> None:
        """Updates active monorepo autonomy regime."""
        clean_mode = mode.lower()
        if clean_mode in self.VALID_MODES:
            self.current_mode = clean_mode
            logger.info(
                "[GATING] Autonomy mode changed to '%s'.", clean_mode
            )

    async def intercept_tool_call(
        self,
        tool_name: str,
        tool_category: str,
        arguments: Dict[str, Any],
        execute_fn: Callable[[], Any],
    ) -> Any:
        """
        Main tool invocation interceptor.
        Applies security barrier matching the active gating regime before
        allowing physical execution.

        Verification pipeline:
          1. Physical Vanguard Guard: Path Traversal boundary check.
          2. Logical Regime Check: Active autonomy mode rules.
          3. Tool Execution: Dispatches execute_fn upon approval.

        Raises:
          GatingViolationException — if operation violates any security boundary.
        """
        # ─── 1. PHYSICAL BOUNDARY: Path Traversal Check ────────────────
        target_path = (
            arguments.get("file_path")
            or arguments.get("path")
            or arguments.get("target_path")
        )
        if target_path and not self.guard.is_safe_path(target_path):
            raise GatingViolationException(
                f"🛡️ Security Block: Operation with path '{target_path}' "
                f"is outside monorepo boundaries '{self.guard.project_root}'."
            )

        # ─── 2. LOGICAL REGIME CHECK ───────────────────────────────────

        # PLAN-ONLY Mode: Blocks any physical mutation or shell execution
        if self.current_mode == "plan-only":
            if tool_category in ("LOCAL_MUTATION", "DANGEROUS"):
                raise GatingViolationException(
                    f"🛡️ 'plan-only' mode active: Tool '{tool_name}' of category "
                    f"'{tool_category}' blocked from physical write."
                )

        # ASK Mode: Requires developer approval for dangerous commands
        elif self.current_mode == "ask":
            if tool_name == "execute_command" or tool_category == "DANGEROUS":
                command = arguments.get("command", "")
                risk = self.guard.classify_command(command)

                if risk == "CRITICAL":
                    raise GatingViolationException(
                        f"🛡️ Critical Block: Command '{command}' banned from local execution pipeline."
                    )

                if risk == "WARNING":
                    # Triggers non-blocking async CLI interactive prompt
                    approved = await self._prompt_developer_approval(
                        tool_name, arguments
                    )
                    if not approved:
                        raise GatingViolationException(
                            "Approval rejected by developer."
                        )

        # AUTO-APPROVE Mode: Autonomous run (only CRITICAL terminal commands banned)
        elif self.current_mode == "auto-approve":
            if tool_name == "execute_command":
                command = arguments.get("command", "")
                if self.guard.classify_command(command) == "CRITICAL":
                    raise GatingViolationException(
                        f"🛡️ Critical Block: Command '{command}' banned in monorepo."
                    )

        # ─── 3. TOOL EXECUTION (Passed all barriers) ───────────────────
        return execute_fn()

    async def _prompt_developer_approval(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> bool:
        """
        Displays a non-blocking interactive prompt on the console (CLI Terminal)
        to capture human approval in a thread-safe manner.

        Uses asyncio.run_in_executor to delegate input() to a worker thread,
        preventing freezing of the FastMCP/FastAPI Event Loop.

        Returns:
          True  — if developer typed 'y' or 'yes'.
          False — any other input, EOF, or error.
        """
        async with self._interactive_lock:
            print("\n" + "=" * 60, file=sys.stderr)
            print(
                "🛡️ SECURITY ALERT: Pending Execution Request",
                file=sys.stderr,
            )
            print(f"Tool: {tool_name}", file=sys.stderr)
            print(f"Arguments: {arguments}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            # Delegate input() to default executor so async event loop remains reactive
            loop = asyncio.get_running_loop()
            try:
                user_input = await loop.run_in_executor(
                    None,
                    lambda: input("\nApprove execution? [y/N]: ").strip().lower(),
                )
            except (EOFError, OSError):
                # Auto-reject in non-interactive environments (CI/CD)
                return False

            return user_input in ("y", "yes")
