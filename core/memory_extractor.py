"""
core/memory_extractor.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Motor de Extração Semântica e pipeline de decisão NOOP da Camada Conversacional Híbrida.
Garante que novos fatos sejam classificados e gravados de forma bi-temporal pura (invalidação + inserção).
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
    """Motor de processamento e consolidação de fatos semânticos em escopos de memória.

    Usa um adaptador LLM para classificar novos fatos e decide se deve criá-los (ADD),
    atualizá-los sob lógica bi-temporal (UPDATE), revogá-los (DELETE) ou ignorá-los (NOOP).
    """

    def __init__(self, llm_adapter: Any) -> None:
        """Inicializa o extrator de memória.

        Args:
            llm_adapter: Objeto de adaptação do LLM (ex: LLMAdapter ou mock equivalente).
        """
        self.llm = llm_adapter

    def evaluate_and_store_facts(
        self,
        conn: sqlite3.Connection,
        scope_type: str,
        scope_id: str,
        new_facts: list[str]
    ) -> list[dict[str, Any]]:
        """Avalia novos fatos e os armazena de acordo com a lógica NOOP / bi-temporal.

        Args:
            conn: Conexão direta com o SQLite (utilizada sob uma única transação).
            scope_type: Escopo do fato ('user', 'session', 'agent', 'org').
            scope_id: ID identificador do escopo.
            new_facts: Lista de strings contendo as memórias em estado bruto a avaliar.

        Returns:
            Lista de dicionários detalhando as decisões tomadas para cada fato.
        """
        results: list[dict[str, Any]] = []

        for new_fact in new_facts:
            new_fact = new_fact.strip()
            if not new_fact:
                continue

            active_facts = get_active_semantic_facts(conn, scope_type, scope_id)
            if not active_facts:
                # Otimização: se não há fatos cadastrados, é obrigatoriamente um ADD
                fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                results.append({
                    "fact": new_fact,
                    "action": "ADD",
                    "target_id": None,
                    "fact_id": fact_id
                })
                continue

            # Monta bloco de fatos existentes para injeção no prompt
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
                    # ID inválido/inexistente nos ativos resulta em inserção pura (ADD)
                    fact_id = insert_semantic_fact(conn, scope_type, scope_id, new_fact)
                    results.append({
                        "fact": new_fact,
                        "action": "ADD",
                        "target_id": None,
                        "fact_id": fact_id
                    })
                else:
                    # Lógica Bi-temporal pura: invalida antigo e insere o novo consolidado
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
                    # Sem ID válido para invalidação, trata como NOOP
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
                # Caso de ação desconhecida ou inválida, trata como NOOP
                results.append({
                    "fact": new_fact,
                    "action": "NOOP",
                    "target_id": None,
                    "fact_id": None
                })

        return results

    def _extract_json_with_fallback(self, raw_response: str) -> Optional[dict[str, Any]]:
        """Tenta extrair o dicionário JSON da resposta do LLM com fallback progressivo."""
        if not raw_response or not raw_response.strip():
            return None
        text = raw_response.strip()

        # Remove delimitadores de markdown se presentes
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Tentativa 1: parsing direto
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # Tentativa 2: regex para capturar bloco de chaves
        matches = _JSON_BLOCK_RE.findall(text)
        for match in matches:
            try:
                return json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue

        # Tentativa 3: captura simples do primeiro e último colchetes/chaves
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

        return None
