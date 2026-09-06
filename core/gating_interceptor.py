"""
core/gating_interceptor.py — SDD-SURVIVAL-24

Interceptador de Gating Adaptativo para IDE, MCP e Terminal.

Regula a autonomia do agente Hermes/Nexus com três réguas estritas:
  plan-only   — Somente leitura. Mutações e comandos são bloqueados.
  ask         — Mutações locais auto-aprovadas. Comandos WARNING exigem
                aprovação humana interativa via prompt CLI assíncrono.
  auto-approve — Autonomia total. Apenas comandos CRITICAL são banidos.

Barreiras de Segurança:
  1. Vanguard Bounds Guard (intransponível): Bloqueia qualquer operação
     com caminho fora do monorepo, independente do modo de gating.
  2. Blacklist de Comandos CRITICAL: rm -rf /, mkfs, dd if, etc.
     Bloqueados sumariamente em todos os modos.
  3. Prompt CLI Assíncrono: Usa asyncio.run_in_executor para capturar
     input() sem bloquear o Event Loop do FastMCP/FastAPI.
"""

import asyncio
import logging
import sys
from typing import Any, Callable, Dict

from core.security_guard import SecurityGuard

logger = logging.getLogger(__name__)


class GatingViolationException(Exception):
    """Exceção disparada quando uma regra de Gating Adaptativo é violada."""

    pass


class GatingInterceptor:
    """
    Interceptador de chamadas de ferramentas com gating adaptativo.

    Parâmetros:
      security_guard — Instância do SecurityGuard com o project_root configurado.
      default_mode   — Modo inicial de gating ("plan-only", "ask" ou "auto-approve").
    """

    VALID_MODES = {"plan-only", "ask", "auto-approve"}

    def __init__(self, security_guard: SecurityGuard, default_mode: str = "ask"):
        clean_mode = default_mode.lower()
        if clean_mode not in self.VALID_MODES:
            clean_mode = "ask"
        self.current_mode = clean_mode
        self.guard = security_guard
        # Evita colisões se múltiplos subagentes pedirem aprovação juntos
        self._interactive_lock = asyncio.Lock()

    def set_gating_mode(self, mode: str) -> None:
        """Altera a régua de autonomia do monorepo."""
        clean_mode = mode.lower()
        if clean_mode in self.VALID_MODES:
            self.current_mode = clean_mode
            logger.info(
                "[GATING] Modo de autonomia alterado para '%s'.", clean_mode
            )

    async def intercept_tool_call(
        self,
        tool_name: str,
        tool_category: str,
        arguments: Dict[str, Any],
        execute_fn: Callable[[], Any],
    ) -> Any:
        """
        Interceptador principal de chamadas de ferramentas.
        Aplica a barreira correspondente ao modo de Gating antes de
        permitir a execução.

        Fluxo de verificação:
          1. Barreira Física (Vanguard Guard): Path Traversal.
          2. Régua Lógica do modo de gating ativo.
          3. Execução da ferramenta se aprovada.

        Raises:
          GatingViolationException — se a operação violar qualquer barreira.
        """
        # ─── 1. BARREIRA FÍSICA INTRANSÍVEL: Path Traversal Check ─────
        target_path = (
            arguments.get("file_path")
            or arguments.get("path")
            or arguments.get("target_path")
        )
        if target_path and not self.guard.is_safe_path(target_path):
            raise GatingViolationException(
                f"🛡️ Bloqueio de Segurança: Operação com caminho '{target_path}' "
                f"está fora do limite do monorepo '{self.guard.project_root}'."
            )

        # ─── 2. RÉGUA LÓGICA DO MODO DE GATING ATIVO ─────────────────

        # Modo PLAN-ONLY: Bloqueia qualquer mutação ou comando físico
        if self.current_mode == "plan-only":
            if tool_category in ("LOCAL_MUTATION", "DANGEROUS"):
                raise GatingViolationException(
                    f"🛡️ Modo 'plan-only' ativo: Ferramenta '{tool_name}' de categoria "
                    f"'{tool_category}' bloqueada para escrita física."
                )

        # Modo ASK: Exige aprovação para comandos perigosos
        elif self.current_mode == "ask":
            if tool_name == "execute_command" or tool_category == "DANGEROUS":
                command = arguments.get("command", "")
                risk = self.guard.classify_command(command)

                if risk == "CRITICAL":
                    raise GatingViolationException(
                        f"🛡️ Bloqueio Crítico: Comando '{command}' banido da esteira local."
                    )

                if risk == "WARNING":
                    # Dispara prompt interativo CLI assíncrono não-bloqueante
                    approved = await self._prompt_developer_approval(
                        tool_name, arguments
                    )
                    if not approved:
                        raise GatingViolationException(
                            "Aprovação recusada pelo desenvolvedor."
                        )

        # Modo AUTO-APPROVE: Roda livre (apenas CRITICAL do terminal é proibido)
        elif self.current_mode == "auto-approve":
            if tool_name == "execute_command":
                command = arguments.get("command", "")
                if self.guard.classify_command(command) == "CRITICAL":
                    raise GatingViolationException(
                        f"🛡️ Bloqueio Crítico: Comando '{command}' banido no monorepo."
                    )

        # ─── 3. EXECUÇÃO DA FERRAMENTA (passou de todas as barreiras) ─
        return execute_fn()

    async def _prompt_developer_approval(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> bool:
        """
        Exibe um prompt interativo não-bloqueante no console (Terminal CLI)
        para capturar o input humano de forma thread-safe.

        Utiliza asyncio.run_in_executor para delegar o input() a uma thread
        do pool padrão, evitando bloqueio do Event Loop do FastMCP/FastAPI.

        Retorna:
          True  — se o desenvolvedor digitou 'y' ou 'yes'.
          False — qualquer outra resposta ou erro.
        """
        async with self._interactive_lock:
            print("\n" + "=" * 60, file=sys.stderr)
            print(
                "🛡️ ALERTA DE SEGURANÇA: Solicitação de Execução Pendente",
                file=sys.stderr,
            )
            print(f"Ferramenta: {tool_name}", file=sys.stderr)
            print(f"Argumentos: {arguments}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            # Utiliza run_in_executor para não prender o Event Loop assíncrono
            loop = asyncio.get_running_loop()
            try:
                user_input = await loop.run_in_executor(
                    None,
                    lambda: input("\nAprovar execução? [y/N]: ").strip().lower(),
                )
            except (EOFError, OSError):
                # Em ambientes sem TTY (CI/CD), rejeita automaticamente
                return False

            return user_input in ("y", "yes")
