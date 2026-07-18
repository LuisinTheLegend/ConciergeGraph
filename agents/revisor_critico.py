"""
agents/revisor_critico.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Evolution Auditor + Drawer Reranking.

The Critical Revisor is the guardian of Grafo Concierge's quality.
It acts in two distinct moments:

Role 1 — COMMIT AUDITING:
    Validates Summarizer drafts before writing to the commit_log.
    Requires the draft to contain:
        - non-empty and readable technical_changes
        - updated_pointers with at least 1 pointer
        - No data contamination between Wings (Contamination Barrier)
    If rejected, returns feedback to the Summarizer for a retry (max 3 loops).
    After 3 rejections, approves with partial_audit=True (safe fallback).

Role 2 — DRAWER RERANKING:
    On heavy triggers (on_build, on_done), receives the top-N results
    from Hybrid Search v4 and uses the LLM as a judge to filter semantic noise.
    Criteria:
        - Technical relevance: does the node directly address the task?
        - Freshness: was the node updated recently?
        - Specificity: is the node specific (not generic)?
    Returns only the nodes that passed the criteria (1 to N items).

Role 3 — CONTAMINATION BARRIER:
    Validates that Reference Wings do not violate privacy_levels.
    A RESTRICTED project cannot have its data exposed in
    PUBLIC contexts. The revisor blocks this contamination.

Integration:
    - Reuses ingestion.summarizer.LLMAdapter for LLM calls
    - Consumes core.config.ConciergeConfig for limits and parameters
    - Is consumed by core.middleware.GrafoConcierge and interface/action_hooks
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from core.config import ConciergeConfig, DEFAULT_CONFIG
from ingestion.summarizer import LLMAdapter

logger = logging.getLogger("grafo-concierge.revisor-critico")

# Regex for extracting JSON from LLM responses
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


# ---------------------------------------------------------------------------
# Typed results
# ---------------------------------------------------------------------------

@dataclass
class AuditResult:
    """Result of a commit audit.

    Campos:
        approved: True if the draft passed validation.
        reason: Reason for approval or rejection.
        technical_changes: Validated/corrected technical changes.
        updated_pointers: List of validated pointers.
        partial_audit: True if approved by fallback (3 rejections).
        loop_count: Number of audit loops executed.
    """
    approved: bool = False
    reason: str = ""
    technical_changes: str = ""
    updated_pointers: list[str] = field(default_factory=list)
    partial_audit: bool = False
    loop_count: int = 0

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "technical_changes": self.technical_changes,
            "updated_pointers": self.updated_pointers,
            "partial_audit": self.partial_audit,
            "loop_count": self.loop_count,
        }


@dataclass
class RerankResult:
    """Result of a candidate reranking.

    Fields:
        candidates: Filtered list of approved candidates.
        filtered_count: How many candidates were removed.
        criteria_applied: Criteria used in filtering.
    """
    candidates: list[dict] = field(default_factory=list)
    filtered_count: int = 0
    criteria_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "filtered_count": self.filtered_count,
            "criteria_applied": self.criteria_applied,
        }


# ---------------------------------------------------------------------------
# Revisor Prompts
# ---------------------------------------------------------------------------

_AUDIT_PROMPT_TEMPLATE = """You are a strict code commit auditor for a memory graph system.
Review the following commit draft and validate it meets ALL criteria:

1. "technical_changes" must be non-empty and describe specific code changes (function names, modules affected).
2. "updated_pointers" must contain at least 1 file path or module reference.
3. The content must NOT contain data from restricted projects mixed with public ones.
4. The summary must be in a professional, technical tone.

Commit Draft:
- Phase: {phase}
- Technical Changes: {technical_changes}
- Updated Pointers: {updated_pointers}
- Source Wing: {source_wing}

Respond with ONLY a valid JSON object:
{{
    "approved": true/false,
    "reason": "explanation of your decision",
    "technical_changes": "cleaned/validated technical changes text",
    "updated_pointers": ["pointer1", "pointer2"]
}}"""

_RERANK_PROMPT_TEMPLATE = """You are a search result relevance judge for a code knowledge graph.
Given a task description and a list of search results, evaluate each result's relevance.

Task: {task_context}

Search Results:
{candidates_block}

For each result, score its relevance (0.0 to 1.0) based on:
1. Technical relevance: Does this directly help with the task?
2. Freshness: Is the information current and accurate?
3. Specificity: Is it specific to the problem (not generic)?

Respond with ONLY a valid JSON object:
{{
    "evaluations": [
        {{"node_id": <id>, "relevance": <0.0-1.0>, "reason": "brief explanation"}},
        ...
    ]
}}"""


# ---------------------------------------------------------------------------
# RevisorCritico — Guardian of Evolution
# ---------------------------------------------------------------------------

class RevisorCritico:
    """Evolution Auditor + Drawer Reranking.

    Two modes of operation:
        1. audit(draft) → Validates commit before recording
        2. rerank(candidates, task_context) → Filters search results

    Args:
        llm_adapter: LLM adapter for AI calls.
                     If None, operates in heuristic mode (no LLM).
        config: Centralized configurations.
    """

    # Relevance threshold for reranking (0.0 - 1.0)
    RERANK_RELEVANCE_THRESHOLD: float = 0.5

    def __init__(
        self,
        llm_adapter: Optional[LLMAdapter] = None,
        config: ConciergeConfig = DEFAULT_CONFIG,
    ) -> None:
        self._llm = llm_adapter
        self._config = config
        self._max_loops = config.max_revisor_loops

        mode = "LLM" if llm_adapter else "heuristic"
        logger.info("RevisorCritico initialized: mode=%s, max_loops=%d", mode, self._max_loops)

    # ===================================================================
    # ROLE 1 — COMMIT AUDITING
    # ===================================================================

    def audit(self, draft: dict) -> AuditResult:
        """Audits a commit draft.

        First applies heuristic validation (strict rules).
        If the LLM is available, performs additional semantic validation.

        Args:
            draft: Dict with draft fields:
                - phase (str): Current phase
                - technical_changes (str): Description of changes
                - updated_pointers (list[str]): Updated pointers
                - source_wing (str, optional): Source wing

        Returns:
            AuditResult with approval and feedback.
        """
        result = AuditResult(loop_count=1)

        # --- Heuristic validation (strict rules, without LLM) ---
        heuristic_ok, heuristic_reason = self._heuristic_audit(draft)

        if not heuristic_ok:
            result.approved = False
            result.reason = heuristic_reason
            result.technical_changes = draft.get("technical_changes", "")
            result.updated_pointers = draft.get("updated_pointers", [])
            logger.info("Heuristic audit REJECTED: %s", heuristic_reason)
            return result

        # --- Semantic validation with LLM (if available) ---
        if self._llm is not None:
            return self._llm_audit(draft)

        # Without LLM -> heuristic approval
        result.approved = True
        result.reason = "Aprovado por validação heurística (sem LLM disponível)."
        result.technical_changes = draft.get("technical_changes", "")
        result.updated_pointers = draft.get("updated_pointers", [])
        logger.info("Heuristic audit APPROVED (no LLM mode).")
        return result

    def _heuristic_audit(self, draft: dict) -> tuple[bool, str]:
        """Strict rule-based validation (without LLM).

        Returns:
            Tuple (passed: bool, reason: str).
        """
        tc = draft.get("technical_changes", "")
        up = draft.get("updated_pointers", [])

        # Rule 1: technical_changes cannot be empty
        if not tc or not tc.strip():
            return False, "technical_changes is empty or contains only spaces."

        # Rule 2: technical_changes too short (< 10 characters)
        if len(tc.strip()) < 10:
            return False, (
                f"technical_changes too short ({len(tc.strip())} characters). "
                "Describe the changes with more detail."
            )

        # Rule 3: updated_pointers must have at least 1 item
        if not up or (isinstance(up, list) and len(up) == 0):
            return False, "updated_pointers is empty. Include at least 1 pointer."

        # Rule 4: each pointer must be a non-empty string
        if isinstance(up, list):
            empty_ptrs = [p for p in up if not isinstance(p, str) or not p.strip()]
            if empty_ptrs:
                return False, (
                    f"{len(empty_ptrs)} invalid pointer(s) in updated_pointers. "
                    "Each pointer must be a non-empty string."
                )

        return True, "OK"

    def _llm_audit(self, draft: dict) -> AuditResult:
        """Semantic validation via LLM (when available).

        Returns:
            AuditResult with LLM decision.
        """
        prompt = _AUDIT_PROMPT_TEMPLATE.format(
            phase=draft.get("phase", "unknown"),
            technical_changes=draft.get("technical_changes", ""),
            updated_pointers=draft.get("updated_pointers", []),
            source_wing=draft.get("source_wing", "geral"),
        )

        result = AuditResult(loop_count=1)

        try:
            raw_response = self._llm.generate(prompt, max_tokens=300)
            parsed = self._extract_json(raw_response)

            if parsed and "approved" in parsed:
                result.approved = bool(parsed["approved"])
                result.reason = parsed.get("reason", "")
                result.technical_changes = parsed.get(
                    "technical_changes",
                    draft.get("technical_changes", ""),
                )
                result.updated_pointers = parsed.get(
                    "updated_pointers",
                    draft.get("updated_pointers", []),
                )

                status = "APPROVED" if result.approved else "REJECTED"
                logger.info("LLM audit %s: %s", status, result.reason[:100])
                return result

            logger.warning("LLM audit returned invalid JSON — heuristic fallback.")

        except Exception as e:
            logger.error("LLM audit failed: %s — heuristic fallback.", e)

        # Fallback: heuristic approval
        result.approved = True
        result.reason = "Approved by fallback (LLM unavailable or invalid response)."
        result.technical_changes = draft.get("technical_changes", "")
        result.updated_pointers = draft.get("updated_pointers", [])
        result.partial_audit = True
        return result

    def audit_with_retry(
        self,
        draft: dict,
        generate_fn: Optional[Any] = None,
    ) -> AuditResult:
        """Executes the complete audit loop (max N attempts).

        If the revisor rejects, calls generate_fn to generate a new draft
        with the rejection feedback. After max_loops rejections, approves with
        partial_audit=True.

        Args:
            draft: Initial draft.
            generate_fn: Callable(task, outcome, feedback) -> dict
                         Function to regenerate the draft.
                         If None, returns the result of the first attempt.

        Returns:
            AuditResult final (approved or partial_audit).
        """
        current_draft = draft

        for attempt in range(1, self._max_loops + 1):
            result = self.audit(current_draft)
            result.loop_count = attempt

            if result.approved:
                logger.info(
                    "Commit approved on attempt %d/%d.",
                    attempt, self._max_loops,
                )
                return result

            logger.warning(
                "Commit rejected (%d/%d): %s",
                attempt, self._max_loops, result.reason,
            )

            # If no regeneration function is provided, return rejection
            if generate_fn is None:
                return result

            # Regenerate with feedback
            try:
                current_draft = generate_fn(result.reason)
            except Exception as e:
                logger.error("Failed to regenerate draft: %s", e)
                break

        # Fallback after max_loops
        logger.error(
            "Commit not approved after %d attempts — partial_audit=True.",
            self._max_loops,
        )

        final = AuditResult(
            approved=True,
            reason=f"Approved by partial_audit after {self._max_loops} rejections.",
            technical_changes=current_draft.get("technical_changes", ""),
            updated_pointers=current_draft.get("updated_pointers", []),
            partial_audit=True,
            loop_count=self._max_loops,
        )
        return final

    # ===================================================================
    # ROLE 2 — DRAWER RERANKING
    # ===================================================================

    def rerank(
        self,
        candidates: list[dict],
        task_context: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Filters search results by technical relevance.

        If LLM is available: uses LLM as a semantic judge.
        If not: applies heuristics based on score_final.

        Args:
            candidates: Top-N results of Hybrid Search v4.
                        Each dict must have: node_id, score_final, score_breakdown.
            task_context: Description of the current task.
            max_results: Maximum results to return.

        Returns:
            Filtered list of approved candidates (1 to max_results items).
        """
        if not candidates:
            return []

        # Limits to max_results before reranking
        top_candidates = candidates[:max_results]

        if self._llm is not None:
            reranked = self._llm_rerank(top_candidates, task_context)
        else:
            reranked = self._heuristic_rerank(top_candidates)

        logger.info(
            "Reranking: %d candidates → %d approved (task='%.50s...')",
            len(top_candidates), len(reranked), task_context,
        )
        return reranked

    def _heuristic_rerank(self, candidates: list[dict]) -> list[dict]:
        """Heuristic reranking (without LLM).

        Filters candidates with score_final below 30% of the best score.
        Guarantees at least 1 result.
        """
        if not candidates:
            return []

        max_score = max(c.get("score_final", 0) for c in candidates)
        threshold = max_score * 0.30

        filtered = [
            c for c in candidates
            if c.get("score_final", 0) >= threshold
        ]

        # Guarantees at least 1 result
        if not filtered and candidates:
            filtered = [candidates[0]]

        logger.debug(
            "Heuristic reranking: threshold=%.4f, filtered=%d/%d",
            threshold, len(filtered), len(candidates),
        )
        return filtered

    def _llm_rerank(self, candidates: list[dict], task_context: str) -> list[dict]:
        """Semantic reranking via LLM.

        The LLM evaluates each candidate and assigns a relevance score.
        Candidates below the RERANK_RELEVANCE_THRESHOLD are filtered.
        """
        # Builds candidates block for prompt
        lines: list[str] = []
        for i, c in enumerate(candidates, 1):
            breakdown = c.get("score_breakdown", {})
            lines.append(
                f"[{i}] node_id={c.get('node_id', '?')}, "
                f"score_final={c.get('score_final', 0):.4f}, "
                f"vetorial={breakdown.get('vetorial', 0):.4f}, "
                f"fts5={breakdown.get('frequencia', 0):.4f}, "
                f"recencia={breakdown.get('recencia', 0):.4f}, "
                f"centralidade={breakdown.get('centralidade', 0):.4f}, "
                f"is_super_node={c.get('is_super_node', False)}"
            )

        candidates_block = "\n".join(lines)

        prompt = _RERANK_PROMPT_TEMPLATE.format(
            task_context=task_context,
            candidates_block=candidates_block,
        )

        try:
            raw_response = self._llm.generate(prompt, max_tokens=400)
            parsed = self._extract_json(raw_response)

            if parsed and "evaluations" in parsed:
                evaluations = parsed["evaluations"]

                # Builds node_id → relevance map
                relevance_map: dict[int, float] = {}
                for ev in evaluations:
                    nid = ev.get("node_id")
                    rel = ev.get("relevance", 0.0)
                    if nid is not None:
                        relevance_map[int(nid)] = float(rel)

                # Filters approved candidates
                approved: list[dict] = []
                for c in candidates:
                    nid = c.get("node_id")
                    relevance = relevance_map.get(nid, 0.0)
                    if relevance >= self.RERANK_RELEVANCE_THRESHOLD:
                        c_copy = dict(c)
                        c_copy["rerank_relevance"] = relevance
                        approved.append(c_copy)

                # Guarantees at least 1 result
                if not approved and candidates:
                    best_nid = max(relevance_map, key=relevance_map.get, default=None)
                    if best_nid is not None:
                        for c in candidates:
                            if c.get("node_id") == best_nid:
                                c_copy = dict(c)
                                c_copy["rerank_relevance"] = relevance_map[best_nid]
                                approved = [c_copy]
                                break

                # Sorts by reranking relevance
                approved.sort(
                    key=lambda x: x.get("rerank_relevance", 0),
                    reverse=True,
                )

                logger.info(
                    "LLM Reranking: %d/%d approved (threshold=%.2f)",
                    len(approved), len(candidates), self.RERANK_RELEVANCE_THRESHOLD,
                )
                return approved

            logger.warning("LLM reranking returned invalid JSON — heuristic fallback.")

        except Exception as e:
            logger.error("LLM reranking failed: %s — heuristic fallback.", e)

        # Heuristic fallback
        return self._heuristic_rerank(candidates)

    # ===================================================================
    # ROLE 3 — CONTAMINATION BARRIER
    # ===================================================================

    def check_contamination(
        self,
        source_project: dict,
        target_project: dict,
    ) -> tuple[bool, str]:
        """Checks for risk of contamination between projects.

        Rule: data from RESTRICTED projects cannot flow to
        PUBLIC or INTERNAL contexts.

        Args:
            source_project: Source project of the data.
            target_project: Target project that will receive/expose the data.

        Returns:
            Tuple (is_safe: bool, reason: str).
        """
        source_privacy = source_project.get("privacy_level", "PUBLIC")
        target_privacy = target_project.get("privacy_level", "PUBLIC")

        # Hierarchy: RESTRICTED > INTERNAL > PUBLIC
        privacy_hierarchy = {"PUBLIC": 0, "INTERNAL": 1, "RESTRICTED": 2}
        source_level = privacy_hierarchy.get(source_privacy, 0)
        target_level = privacy_hierarchy.get(target_privacy, 0)

        if source_level > target_level:
            reason = (
                f"CONTAMINAÇÃO BLOQUEADA: dados de projeto {source_privacy} "
                f"não podem fluir para contexto {target_privacy}. "
                f"Projeto fonte: '{source_project.get('folder_name', '?')}', "
                f"projeto destino: '{target_project.get('folder_name', '?')}'."
            )
            logger.warning(reason)
            return False, reason

        return True, "OK — sem risco de contaminação."

    # ===================================================================
    # UTILITIES
    # ===================================================================

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extracts JSON from an LLM response (with regex fallback).

        Attempts:
            1. Direct json.loads()
            2. Regex to find embedded JSON block
        """
        if not text:
            return None

        # Attempt 1: direct parse
        clean = text.strip()
        if clean.startswith("```"):
            # Removes markdown fences
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines).strip()

        try:
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            pass

        # Attempt 2: regex
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group())
            except (json.JSONDecodeError, TypeError):
                pass

        return None
