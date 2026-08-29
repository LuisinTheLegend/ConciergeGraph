"""
core/global_memory_adapter.py — SDD-SURVIVAL-22

Adaptador de Memória Global Hierárquica (LTM + STM).

Substitui a passagem ineficiente do histórico linear bruto de mensagens
(chat history) na janela de contexto por um compilado semântico estruturado:

  - STM (Short-Term Memory): Janela deslizante das últimas 3 mensagens brutas
    do chat, preservando referências de pronomes e fluxo conversacional imediato.
  - LTM (Long-Term Memory): Substrato estruturado de entidades e resumos
    extraídos das tabelas de relacionamento e comunidades do Grafo Concierge.

Política: Janela Deslizante de Contexto Misto (Hybrid Sliding Window).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Número de mensagens recentes do chat a preservar intactas na janela de curto prazo
STM_WINDOW_SIZE = 3


class GlobalMemoryAdapter:
    """Injetor de contexto dinâmico com janela deslizante mista LTM + STM."""

    def __init__(self, db_manager):
        self.db = db_manager

    def compile_hybrid_context(
        self,
        chat_history: List[Dict[str, str]],
        retrieved_knowledge: Dict[str, Any],
    ) -> str:
        """
        Compila o payload final de contexto para o agente.

        Conserva as últimas STM_WINDOW_SIZE mensagens brutas do chat e substitui
        o histórico antigo por resumos estruturados extraídos do Grafo.

        Args:
            chat_history: Lista de dicts com 'role' ('user'|'assistant') e 'content'.
            retrieved_knowledge: Dict com 'source' e 'context' (saída do NozomioRouter).

        Returns:
            String compilada pronta para injeção como system/context no prompt do agente.
        """
        # 1. Recupera as últimas N interações conversacionais (STM)
        if len(chat_history) > STM_WINDOW_SIZE:
            recent_chat_history = chat_history[-STM_WINDOW_SIZE:]
        else:
            recent_chat_history = chat_history

        # 2. Prepara o Bloco de Memória de Longo Prazo Estruturada (LTM)
        source = retrieved_knowledge.get("source", "UNKNOWN")
        context = retrieved_knowledge.get("context", "")
        ltm_block = (
            f"=== SUBSTRATO DE MEMÓRIA DE LONGO PRAZO (Sourced from: {source}) ===\n"
            f"Contexto Recuperado:\n{context}\n"
        )

        # 3. Monta a instrução de ancoragem de contexto
        system_injection = (
            "Você é o agente executor e tem acesso à sua Memória de Longo Prazo (LTM) consolidada e "
            "ao histórico de conversação de curto prazo. Utilize o LTM abaixo como sua única e estrita "
            "fonte de verdade técnica sobre o projeto, ignorando especulações.\n\n"
            f"{ltm_block}\n"
            "=== HISTÓRICO CONVERSACIONAL DE CURTO PRAZO ===\n"
        )

        # 4. Concatena o histórico recente formatado
        chat_str = ""
        for msg in recent_chat_history:
            role = "Desenvolvedor" if msg.get("role") == "user" else "Agente"
            chat_str += f"{role}: {msg.get('content', '')}\n"

        compiled = system_injection + chat_str

        logger.debug(
            "GlobalMemoryAdapter: Compilado contexto híbrido — LTM source=%s, STM msgs=%d, total chars=%d",
            source, len(recent_chat_history), len(compiled)
        )

        return compiled
