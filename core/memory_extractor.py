"""
core/memory_extractor.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Semantic Extraction Engine and NOOP decision pipeline of the Hybrid Conversational Layer.
Ensures that new facts are classified and recorded in pure bi-temporal form (invalidation + insertion).
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any, Optional

from storage.semantic_logic import insert_semantic_fact, invalidate_semantic_fact, get_active_semantic_facts

logger = logging.getLogger("grafo-concierge.memory-extractor")

_JSON_BLOCK_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)

DECISION_PROMPT_TEMPLATE = """You are an AI memory manager. Compare the NEW FACT below against the list of EXISTING FACTS for this scope, and decide which action to take: ADD, UPDATE, DELETE, or NOOP.

EXISTING FACTS:
{existing_facts_block}

NEW FACT to evaluate:
"{new_fact}"

INSTRUCTIONS:
1. Choose "NOOP" if the NEW FACT is already fully covered by or redundant with the EXISTING FACTS, without adding any new or different information.
2. Choose "ADD" if the NEW FACT is completely new, unrelated to any of the EXISTING FACTS, and doesn't contradict or update them.
3. Choose "UPDATE" if the NEW FACT updates, refines, or adds details to an EXISTING FACT. You must provide the exact ID of the existing fact to update, and the new consolidated "updated_statement" that merges both facts cleanly (e.g. keeping it concise and natural).
4. Choose "DELETE" if the NEW FACT explicitly contradicts, negates, or revokes an EXISTING FACT. You must provide the exact ID of the existing fact to delete.

You MUST respond with a single, valid JSON object and nothing else. No markdown formatting, no backticks, no comments.
JSON format:
{{
  "action": "ADD" | "UPDATE" | "DELETE" | "NOOP",
  "target_id": integer ID or null,
  "updated_statement": string or null
}}"""


class SemanticExtractor:
    """Processing and consolidation engine for semantic facts within memory scopes.

    Uses an LLM adapter to classify new facts and decides whether to create them (ADD),
    update them under bi-temporal logic (UPDATE), revoke them (DELETE), or ignore them (NOOP).
    """

    def __init__(self, llm_adapter: Any) -> None:
        """Initializes the memory extractor.

        Args:
            llm_adapter: LLM adaptation object (e.g. LLMAdapter or equivalent mock).
        """
        self.llm = llm_adapter

    def evaluate_and_store_facts(
        self,
        conn: sqlite3.Connection,
        scope_type: str,
        scope_id: str,
        new_facts: list[str]
    ) -> list[dict[str, Any]]:
        """Evaluates new facts and stores them according to NOOP / bi-temporal logic.

        Args:
            conn: Direct connection to SQLite (used under a single transaction).
            scope_type: Scope of the fact ('user', 'session', 'agent', 'org').
            scope_id: Identifying ID of the scope.
            new_facts: List of strings containing the raw memories to evaluate.

        Returns:
            List of dictionaries detailing the decisions made for each fact.
        """
        results: list[dict[str, Any]] = []

        for new_fact in new_facts:
            new_fact = new_fact.strip()
            if not new_fact:
                continue

            active_facts = get_active_semantic_facts(conn, scope_type, scope_id)
            if not active_facts:
                # Optimization: if there are no registered facts, it is obligatorily an ADD
                fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                results.append({
                    "fact": new_fact,
                    "action": "ADD",
                    "target_id": None,
                    "fact_id": fact_id
                })
                continue

            # Builds block of existing facts for injection into the prompt
            existing_facts_block = "\n".join(
                f"- ID {f['id']}: {f['fact_statement']}" for f in active_facts
            )

            prompt = DECISION_PROMPT_TEMPLATE.format(
                existing_facts_block=existing_facts_block,
                new_fact=new_fact
            )

            try:
                raw_response = self.llm.generate(prompt, max_tokens=300)
                parsed = self._extract_json_with_fallback(raw_response)
            except Exception as e:
                logger.error("Falha ao chamar LLM para avaliar o fato '%s': %s", new_fact, e)
                parsed = None

            if not parsed or "action" not in parsed:
                logger.warning("Falha ao parsear decisão estruturada para o fato '%s'. Executando ADD.", new_fact)
                fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                results.append({
                    "fact": new_fact,
                    "action": "ADD",
                    "target_id": None,
                    "fact_id": fact_id,
                    "fallback": True
                })
                continue

            action = parsed.get("action")
            target_id = parsed.get("target_id")
            updated_statement = parsed.get("updated_statement")

            try:
                t_id = int(target_id) if target_id is not None else None
            except (ValueError, TypeError):
                t_id = None

            active_ids = {f["id"] for f in active_facts}

            if action == "NOOP":
                results.append({
                    "fact": new_fact,
                    "action": "NOOP",
                    "target_id": None,
                    "fact_id": None
                })

            elif action == "ADD":
                fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                results.append({
                    "fact": new_fact,
                    "action": "ADD",
                    "target_id": None,
                    "fact_id": fact_id
                })

            elif action == "UPDATE":
                if t_id is None or t_id not in active_ids:
                    # Invalid/non-existent ID in active facts results in pure insertion (ADD)
                    fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                    results.append({
                        "fact": new_fact,
                        "action": "ADD",
                        "target_id": None,
                        "fact_id": fact_id
                    })
                else:
                    # Pure bi-temporal logic: invalidates the old one and inserts the new consolidated statement
                    invalidate_semantic_fact(conn, t_id)
                    stmt_to_insert = (updated_statement or new_fact).strip()
                    fact_id = insert_semantic_fact(conn, scope_type, scope_id, stmt_to_insert)
                    results.append({
                        "fact": new_fact,
                        "action": "UPDATE",
                        "target_id": t_id,
                        "fact_id": fact_id,
                        "updated_statement": stmt_to_insert
                    })

            elif action == "DELETE":
                if t_id is None or t_id not in active_ids:
                    # No valid ID for invalidation, treat as NOOP
                    results.append({
                        "fact": new_fact,
                        "action": "NOOP",
                        "target_id": None,
                        "fact_id": None
                    })
                else:
                    invalidate_semantic_fact(conn, t_id)
                    results.append({
                        "fact": new_fact,
                        "action": "DELETE",
                        "target_id": t_id,
                        "fact_id": None
                    })

            else:
                # In case of unknown or invalid action, treat as NOOP
                results.append({
                    "fact": new_fact,
                    "action": "NOOP",
                    "target_id": None,
                    "fact_id": None
                })

        return results

    def _extract_json_with_fallback(self, raw_response: str) -> Optional[dict[str, Any]]:
        """Attempts to extract the JSON dictionary from the LLM response with progressive fallback."""
        if not raw_response or not raw_response.strip():
            return None
        text = raw_response.strip()

        # Remove markdown delimiters if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Attempt 1: direct parsing
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # Attempt 2: regex to capture braces block
        matches = _JSON_BLOCK_RE.findall(text)
        for match in matches:
            try:
                return json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue

        # Attempt 3: simple capture of the first and last braces
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

        return None
