"""
agent/agent_prompts.py — SDD-SURVIVAL-26

Dynamic System Prompt Builder with Hierarchical State Machine (HSM) Injection.

Injects the active HSM state (super-state and sub-state) directly into the
agent's system prompt along with authorized tool categories and behavioral
guidelines governed by MCPToolGovernor.

Prevents tool misuse and State Lockout by aligning the model's self-awareness
with the strict security and cognitive phase active in the monorepo.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Standard phase guidelines mapped by super-state
SUPERSTATE_GUIDELINES: Dict[str, str] = {
    "PLANNING": (
        "Regime de Planejamento e Descoberta: Foco exclusivo em leitura, "
        "análise de topologia, exploração de código e planejamento da solução. "
        "Nenhuma mutação física em arquivos ou execução de comandos de modificação "
        "é autorizada neste estágio."
    ),
    "EXECUTION": (
        "Regime de Execução Ativa: Foco na implementação orientada a TDD, geração de código "
        "limpo e refatoração incremental. Mutações locais de arquivos do projeto "
        "estão autorizadas."
    ),
    "MAINTENANCE": (
        "Regime de Manutenção Administrativa: Foco em reconciliação de vetores, "
        "limpeza de cache, rebuild de índices e integridade estrutural. "
        "Comandos de manutenção de alta criticidade estão liberados com cautela."
    ),
    "STALL": (
        "Regime de Pausa e Espera: O agente encontra-se estagnado ou pausado "
        "devido a Circuit Breaker (limite de turnos excedido), contexto esgotado "
        "ou necessidade de intervenção do desenvolvedor humano. Nenhuma mutação permitida."
    ),
    "SUCCESS": (
        "Regime de Conclusão e Sucesso: Todas as etapas foram concluídas e "
        "validadas. O agente permanece em repouso ocioso (IDLE_COMPLETE)."
    ),
}

# Sub-state specific contextual guidelines
SUBSTATE_GUIDELINES: Dict[str, str] = {
    "DISCOVERY": "Fase DISCOVERY: Analise a estrutura dos arquivos, dependências e requisitos antes de propor qualquer mudança.",
    "ARCHITECTURE": "Fase ARCHITECTURE: Defina o design da solução, contratos de interface e impacto de segunda ordem.",
    "KANBAN_GEN": "Fase KANBAN_GEN: Estruture o plano de ação em passos atômicos e ordenados antes da codificação.",
    "CODE_GEN": "Fase CODE_GEN: Implemente a solução de código de forma atômica e modular.",
    "TDD_GREEN": "Fase TDD_GREEN: Escreva e execute a suíte de testes até que todas as asserções estejam em verde.",
    "REFACTORING": "Fase REFACTORING: Otimize a legibilidade e elimine dívidas técnicas preservando a aprovação dos testes.",
    "PURGE_CACHE": "Fase PURGE_CACHE: Esvazie caches e estados temporários corrompidos.",
    "RECONCILE": "Fase RECONCILE: Reconcilie discrepâncias entre banco relacional e vetorial.",
    "RESET_DB": "Fase RESET_DB: Reinicialização de bancos em ambiente controlado.",
    "AWAITING_HUMAN": "Fase AWAITING_HUMAN: Aguarde a entrada ou confirmação do desenvolvedor.",
    "CONTEXT_FULL": "Fase CONTEXT_FULL: Contexto saturado. Resuma o histórico ou salve checkpoint.",
    "ERROR_PAUSE": "Fase ERROR_PAUSE: Pausa preventiva por falha ou estouro do Circuit Breaker.",
    "IDLE_COMPLETE": "Fase IDLE_COMPLETE: Tarefa finalizada. Pronto para nova demanda.",
}


class DynamicPromptBuilder:
    """
    Constructs dynamic system prompts injected with the active HSM state,
    super-state behavioral rules, and MCPToolGovernor access boundaries.
    """

    def __init__(self, mcp_governor: Optional[Any] = None):
        self.mcp_governor = mcp_governor

    @staticmethod
    def parse_state_path(state_path: str) -> Tuple[str, Optional[str]]:
        """
        Splits a qualified state path like 'EXECUTION.TDD_GREEN' into
        super_state ('EXECUTION') and sub_state ('TDD_GREEN').
        """
        if not state_path:
            return "PLANNING", "DISCOVERY"
        parts = state_path.split(".", 1)
        super_state = parts[0].upper()
        sub_state = parts[1].upper() if len(parts) > 1 else None
        return super_state, sub_state

    def get_guidelines_for_state(self, state_path: str) -> str:
        """Returns aggregated guidelines for the given qualified state path."""
        super_state, sub_state = self.parse_state_path(state_path)
        guidelines = []

        super_guide = SUPERSTATE_GUIDELINES.get(
            super_state, f"Regime {super_state}: Proceda conforme as regras do sistema."
        )
        guidelines.append(super_guide)

        if sub_state and sub_state in SUBSTATE_GUIDELINES:
            guidelines.append(SUBSTATE_GUIDELINES[sub_state])

        return "\n".join(guidelines)

    def get_governance_block(self, session_id: str, state_path: str) -> str:
        """
        Builds the MCPToolGovernor disclosure directive block for the current state.
        """
        if not self.mcp_governor:
            return "[GOVERNANÇA DE FERRAMENTAS: Não configurada (Acesso padrão ativo)]"

        super_state, _ = self.parse_state_path(state_path)
        matrix = getattr(self.mcp_governor, "TOOL_DISCLOSURE_MATRIX", {})
        rules = matrix.get(super_state) or matrix.get("PLANNING", {
            "allowed_categories": ["READ_ONLY"],
            "allowed_tools": ["get_telemetry_snapshot"],
        })

        allowed_categories = rules.get("allowed_categories", [])
        allowed_tools = rules.get("allowed_tools", [])

        categories_str = ", ".join(allowed_categories) if allowed_categories else "Nenhuma"
        tools_str = ", ".join(allowed_tools) if allowed_tools else "Nenhuma específica"

        block = (
            f"[FERRAMENTAS AUTORIZADAS]\n"
            f"Categorias permitidas: [{categories_str}]\n"
            f"Ferramentas de exceção liberadas: [{tools_str}]\n"
            f"Aviso de Segurança: Invocação de ferramentas fora das categorias autorizadas "
            f"resultará em SecurityException imediata."
        )
        return block

    def build_prompt(
        self,
        session_id: str,
        current_state: str,
        base_prompt: str = "",
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Builds the full dynamic system prompt with HSM state injection.
        """
        super_state, sub_state = self.parse_state_path(current_state)
        guidelines = self.get_guidelines_for_state(current_state)
        governance = self.get_governance_block(session_id, current_state)

        sections = []

        # 1. State awareness banner
        sub_text = f" -> Sub-Estado: {sub_state}" if sub_state else ""
        sections.append(
            f"====================================================================\n"
            f"[ESTADO ATIVO: {current_state}]\n"
            f"Super-Estado: {super_state}{sub_text}\n"
            f"===================================================================="
        )

        # 2. Behavioral guidelines for this phase
        sections.append(f"[DIRETRIZES DO ESTADO]\n{guidelines}")

        # 3. Tool governance boundaries
        sections.append(governance)

        # 4. Optional extra context
        if extra_context:
            extra_lines = [f"{k}: {v}" for k, v in extra_context.items()]
            sections.append("[CONTEXTO ADICIONAL]\n" + "\n".join(extra_lines))

        # 5. Base system instructions
        if base_prompt:
            sections.append(f"[INSTRUÇÕES DE BASE]\n{base_prompt}")

        return "\n\n".join(sections)

    # Alias for build_prompt
    build_system_prompt = build_prompt
