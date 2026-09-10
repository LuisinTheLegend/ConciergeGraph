"""
core/mcp_governor.py — SDD-SURVIVAL-21

Progressive Tool Disclosure on FastMCP Server.

Acts as a dynamic cognitive firewall for AI agents, intercepting
and filtering disclosed and executed tools based on the current state
of their finite state machine (FSM).

Protection Layers:
  1. filter_tools: Passive listing filter (Discovery/Context Window Optimization).
  2. validate_tool_execution: Active execution barrier that blocks direct command injection
     and raises SecurityException upon scope violations.
"""

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    """Exception raised when an agent attempts to bypass tool governance rules."""
    pass


class MCPToolGovernor:
    """
    FastMCP progressive tool disclosure and governance controller.
    """

    def __init__(self, default_state: Optional[str] = None):
        import os
        if default_state is not None:
            self.default_state = default_state.upper()
        else:
            env_default = os.environ.get("GRAFO_DEFAULT_STATE", "EXECUTION")
            self.default_state = env_default.upper()
        # Active session state dict: {session_id: current_fsm_state}
        self.sessions_state: Dict[str, str] = {}

        # Strict Visibility Matrix Definition
        self.TOOL_DISCLOSURE_MATRIX: Dict[str, Dict[str, List[str]]] = {
            "PLANNING": {
                "allowed_categories": ["READ_ONLY"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "DISCOVERY": {
                "allowed_categories": ["READ_ONLY"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "EXECUTION": {
                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "TDD_GREEN": {
                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "REFACTORING": {
                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "MAINTENANCE": {
                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"],
                "allowed_tools": [],
            },
            "STALL": {
                "allowed_categories": ["READ_ONLY"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
            "SUCCESS": {
                "allowed_categories": ["READ_ONLY"],
                "allowed_tools": ["get_telemetry_snapshot"],
            },
        }

        # Static tool classification catalog
        self.TOOL_CLASSIFICATION: Dict[str, str] = {
            # READ_ONLY
            "get_full_topology": "READ_ONLY",
            "get_trajectory": "READ_ONLY",
            "get_trajectories": "READ_ONLY",
            "find_similar": "READ_ONLY",
            "retrieve_multihop_context": "READ_ONLY",
            "list_session_checkpoints": "READ_ONLY",
            "get_telemetry_snapshot": "READ_ONLY",
            "concierge_search": "READ_ONLY",
            "concierge_resume": "READ_ONLY",
            "concierge_load": "READ_ONLY",
            "concierge_status": "READ_ONLY",
            "concierge_list_facts": "READ_ONLY",
            "concierge_get_memory": "READ_ONLY",
            "concierge_list_projects": "READ_ONLY",
            "search_symbols": "READ_ONLY",
            "get_implementations": "READ_ONLY",
            "get_callers": "READ_ONLY",
            "count_embeddings": "READ_ONLY",
            "concierge_get_call_chain": "READ_ONLY",
            "concierge_set_state": "READ_ONLY",
            "agent_get_checkpoint": "READ_ONLY",
            "agent_list_checkpoints": "READ_ONLY",

            # LOCAL_MUTATION
            "write_file": "LOCAL_MUTATION",
            "delete_file": "LOCAL_MUTATION",
            "apply_alias_migration": "LOCAL_MUTATION",
            "save_checkpoint": "LOCAL_MUTATION",
            "agent_save_checkpoint": "LOCAL_MUTATION",
            "concierge_register": "LOCAL_MUTATION",
            "concierge_mine": "LOCAL_MUTATION",
            "concierge_commit": "LOCAL_MUTATION",
            "concierge_wakeup": "LOCAL_MUTATION",
            "concierge_store_fact": "LOCAL_MUTATION",
            "concierge_set_memory": "LOCAL_MUTATION",
            "concierge_feedback": "LOCAL_MUTATION",
            "add_reference_wing": "LOCAL_MUTATION",
            "remove_reference_wing": "LOCAL_MUTATION",
            "update_project": "LOCAL_MUTATION",

            # DANGEROUS
            "execute_command": "DANGEROUS",
            "reset_collection": "DANGEROUS",
            "purge_database": "DANGEROUS",
            "delete_project": "DANGEROUS",
        }

    def set_session_state(self, session_id: str, state_name: str) -> None:
        """Sets active FSM state for a session."""
        upper_state = state_name.upper()
        if upper_state in self.TOOL_DISCLOSURE_MATRIX:
            self.sessions_state[session_id] = upper_state
        else:
            logger.warning(
                "[MCP-GOVERNOR] Unknown state '%s' for session '%s'. Preserving current state.",
                state_name,
                session_id,
            )

    def get_session_state(self, session_id: str) -> str:
        """Retrieves active state of a session (or returns default_state)."""
        return self.sessions_state.get(session_id, self.default_state)

    def filter_tools(
        self, session_id: str, tools_list: List[Union[Dict[str, Any], Any]]
    ) -> List[Union[Dict[str, Any], Any]]:
        """
        Passive Layer (Discovery): Filters tool catalog disclosed to agent
        based on active FSM state rules.

        Supports both dictionaries (e.g. `{'name': 'write_file'}`) and Tool instances.
        """
        current_state = self.get_session_state(session_id)
        rules = self.TOOL_DISCLOSURE_MATRIX.get(
            current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
        )

        filtered = []
        for tool in tools_list:
            if isinstance(tool, dict):
                tool_name = tool.get("name")
            else:
                tool_name = getattr(tool, "name", None)

            if not tool_name:
                continue

            category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")

            if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
                filtered.append(tool)

        return filtered

    def validate_tool_execution(self, session_id: str, tool_name: str) -> bool:
        """
        Active Layer (Execution): Intercepts tool execution and raises SecurityException
        if a blocked tool is invoked.
        """
        current_state = self.get_session_state(session_id)
        rules = self.TOOL_DISCLOSURE_MATRIX.get(
            current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
        )
        category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")

        if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
            return True

        raise SecurityException(
            f"Access denied: tool '{tool_name}' (category '{category}') "
            f"is blocked during state '{current_state}' for session '{session_id}'."
        )
