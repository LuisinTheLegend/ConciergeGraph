"""
core/mcp_governor.py — SDD-SURVIVAL-21

Ocultação Progressiva de Ferramentas (Progressive Tool Disclosure) no Servidor FastMCP.

Atua como um firewall cognitivo dinâmico para os agentes de IA, interceptando
e filtrando as ferramentas listadas e executadas com base no estado atual da
sua máquina de estados finitos (FSM).

Camadas de Proteção:
  1. filter_tools: Filtro passivo na listagem (Discovery/Context Window Optimization).
  2. validate_tool_execution: Portão ativo de execução que barra injeção direta de comandos
     e levanta SecurityException em caso de violação de escopo.
"""

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    """Exceção levantada quando um agente tenta burlar a governança de ferramentas."""
    pass


class MCPToolGovernor:
    """
    Controlador de governança e divulgação progressiva de ferramentas do FastMCP.
    """

    def __init__(self, default_state: str = "PLANNING"):
        self.default_state = default_state
        # Dicionário de sessões ativas: {session_id: current_fsm_state}
        self.sessions_state: Dict[str, str] = {}

        # Definição estrita da Matriz de Visibilidade
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
        }

        # Classificação estática das ferramentas conhecidas do sistema
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
        """Define o estado ativo da máquina de estados (FSM) de uma sessão."""
        upper_state = state_name.upper()
        if upper_state in self.TOOL_DISCLOSURE_MATRIX:
            self.sessions_state[session_id] = upper_state
        else:
            logger.warning(
                "[MCP-GOVERNOR] Estado desconhecido '%s' para sessão '%s'. Mantendo estado atual.",
                state_name,
                session_id,
            )

    def get_session_state(self, session_id: str) -> str:
        """Recupera o estado atual de uma sessão (ou retorna default_state por padrão)."""
        return self.sessions_state.get(session_id, self.default_state)

    def filter_tools(
        self, session_id: str, tools_list: List[Union[Dict[str, Any], Any]]
    ) -> List[Union[Dict[str, Any], Any]]:
        """
        Primeira Camada (Passiva): Filtra a lista de ferramentas retornada para o agente
        com base nas regras do seu estado FSM corrente.

        Suporta tanto dicionários (ex: `{'name': 'write_file'}`) quanto objetos Tool.
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
        Segunda Camada (Ativa): Intercepta chamadas de execução e lança SecurityException
        caso uma ferramenta bloqueada tente ser executada.
        """
        current_state = self.get_session_state(session_id)
        rules = self.TOOL_DISCLOSURE_MATRIX.get(
            current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
        )
        category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")

        if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
            return True

        raise SecurityException(
            f"Acesso negado: ferramenta '{tool_name}' (categoria '{category}') "
            f"está bloqueada durante o estado '{current_state}' da sessão '{session_id}'."
        )
