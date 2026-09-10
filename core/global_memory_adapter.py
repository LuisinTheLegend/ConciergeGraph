"""
core/global_memory_adapter.py — SDD-SURVIVAL-22

Hierarchical Global Memory Adapter (LTM + STM).

Replaces inefficient linear chat history passing with a structured semantic composite:

  - STM (Short-Term Memory): Sliding window of the latest 3 raw chat messages,
    preserving conversational pronouns and immediate flow.
  - LTM (Long-Term Memory): Structured substrate of entities, facts, and community
    summaries extracted from Concierge Graph SQLite/Qdrant backends.

Policy: Hybrid Sliding Window Context Injection.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Number of recent chat messages preserved intact in short-term window
STM_WINDOW_SIZE = 3


class GlobalMemoryAdapter:
    """Dynamic context injector with hybrid LTM + STM sliding window."""

    def __init__(self, db_manager):
        self.db = db_manager

    def compile_hybrid_context(
        self,
        chat_history: List[Dict[str, str]],
        retrieved_knowledge: Dict[str, Any],
    ) -> str:
        """
        Compiles final context payload for the agent.

        Retains the latest STM_WINDOW_SIZE raw chat messages and replaces
        older conversation history with structured graph summaries.

        Args:
            chat_history: List of dicts with 'role' ('user'|'assistant') and 'content'.
            retrieved_knowledge: Dict with 'source' and 'context' (output from FederatedKnowledgeRouter).

        Returns:
            Compiled string ready for injection into system/context prompt.
        """
        # 1. Retrieve latest conversational turns (STM)
        if len(chat_history) > STM_WINDOW_SIZE:
            recent_chat_history = chat_history[-STM_WINDOW_SIZE:]
        else:
            recent_chat_history = chat_history

        # 2. Prepare Structured Long-Term Memory block (LTM)
        source = retrieved_knowledge.get("source", "UNKNOWN")
        context = retrieved_knowledge.get("context", "")
        ltm_block = (
            f"=== LONG-TERM MEMORY SUBSTRATE (Sourced from: {source}) ===\n"
            f"Retrieved Context:\n{context}\n"
        )

        # 3. Assemble grounding instruction
        system_injection = (
            "You are the executing agent with access to consolidated Long-Term Memory (LTM) "
            "and short-term conversation history. Use the LTM below as your primary technical "
            "source of truth regarding the project.\n\n"
            f"{ltm_block}\n"
            "=== SHORT-TERM CONVERSATION HISTORY ===\n"
        )

        # 4. Format and append recent chat turns
        chat_str = ""
        for msg in recent_chat_history:
            role = "Developer" if msg.get("role") == "user" else "Agent"
            chat_str += f"{role}: {msg.get('content', '')}\n"

        compiled = system_injection + chat_str

        logger.debug(
            "GlobalMemoryAdapter: Compiled hybrid context — LTM source=%s, STM msgs=%d, total chars=%d",
            source, len(recent_chat_history), len(compiled)
        )

        return compiled
