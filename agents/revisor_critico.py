"""
agents/revisor_critico.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Auditor de Evolução + Reranking de Gavetas.

O Revisor Crítico é o guardião da qualidade do Grafo Concierge.
Ele atua em dois momentos distintos:

Papel 1 — AUDITORIA DE COMMIT:
    Valida rascunhos do Sumarizador antes de gravar no commit_log.
    Exige que o rascunho contenha:
        - technical_changes não vazio e legível
        - updated_pointers com pelo menos 1 ponteiro
        - Sem contaminação de dados entre Wings (Barreira de Contaminação)
    Se rejeitar, devolve feedback ao Sumarizador para retry (máx 3 loops).
    Após 3 rejeições, aprova com partial_audit=True (fallback seguro).

Papel 2 — RERANKING DE GAVETAS:
    Em triggers pesados (on_build, on_done), recebe os top-N resultados
    da Busca Híbrida v4 e usa LLM como juiz para filtrar ruído semântico.
    Critérios:
        - Relevância técnica: o nó trata diretamente da tarefa?
        - Frescor: o nó foi atualizado recentemente?
        - Especificidade: o nó é específico (não genérico)?
    Retorna apenas os nós que passaram nos critérios (1 a N itens).

Papel 3 — BARREIRA DE CONTAMINAÇÃO:
    Valida que Reference Wings não violam privacy_levels.
    Um projeto RESTRICTED não pode ter seus dados expostos em
    contextos PUBLIC. O revisor bloqueia essa contaminação.

Integração:
    - Reutiliza ingestion.summarizer.LLMAdapter para chamadas LLM
    - Consome core.config.ConciergeConfig para limites e parâmetros
    - É consumido por core.middleware.GrafoConcierge e interface/action_hooks
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

# Regex para extração de JSON de respostas LLM
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


# ---------------------------------------------------------------------------
# Resultados tipados
# ---------------------------------------------------------------------------

@dataclass
class AuditResult:
    """Resultado de uma auditoria de commit.

    Campos:
        approved: True se o rascunho passou na validação.
        reason: Motivo da aprovação ou rejeição.
        technical_changes: Mudanças técnicas validadas/corrigidas.
        updated_pointers: Lista de ponteiros validados.
        partial_audit: True se aprovado por fallback (3 rejeições).
        loop_count: Número de loops de auditoria executados.
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
    """Resultado de um reranking de candidatos.

    Campos:
        candidates: Lista filtrada de candidatos aprovados.
        filtered_count: Quantos candidatos foram removidos.
        criteria_applied: Critérios usados na filtragem.
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
# Prompts do Revisor
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
# RevisorCritico — Guardião de Evolução
# ---------------------------------------------------------------------------

class RevisorCritico:
    """Auditor de Evolução + Reranking de Gavetas.

    Dois modos de operação:
        1. audit(draft) → Valida commit antes de gravar
        2. rerank(candidates, task_context) → Filtra resultados de busca

    Args:
        llm_adapter: Adaptador LLM para chamadas de IA.
                     Se None, opera em modo heurístico (sem LLM).
        config: Configurações centralizadas.
    """

    # Limiar de relevância para reranking (0.0 - 1.0)
    RERANK_RELEVANCE_THRESHOLD: float = 0.5

    def __init__(
        self,
        llm_adapter: Optional[LLMAdapter] = None,
        config: ConciergeConfig = DEFAULT_CONFIG,
    ) -> None:
        self._llm = llm_adapter
        self._config = config
        self._max_loops = config.max_revisor_loops

        mode = "LLM" if llm_adapter else "heurístico"
        logger.info("RevisorCritico inicializado: modo=%s, max_loops=%d", mode, self._max_loops)

    # ===================================================================
    # PAPEL 1 — AUDITORIA DE COMMIT
    # ===================================================================

    def audit(self, draft: dict) -> AuditResult:
        """Audita um rascunho de commit.

        Primeiro aplica validação heurística (regras rígidas).
        Se o LLM estiver disponível, faz validação semântica adicional.

        Args:
            draft: Dict com campos do rascunho:
                - phase (str): Fase atual
                - technical_changes (str): Descrição das mudanças
                - updated_pointers (list[str]): Ponteiros atualizados
                - source_wing (str, opcional): Ala de origem

        Returns:
            AuditResult com aprovação e feedback.
        """
        result = AuditResult(loop_count=1)

        # --- Validação heurística (regras rígidas, sem LLM) ---
        heuristic_ok, heuristic_reason = self._heuristic_audit(draft)

        if not heuristic_ok:
            result.approved = False
            result.reason = heuristic_reason
            result.technical_changes = draft.get("technical_changes", "")
            result.updated_pointers = draft.get("updated_pointers", [])
            logger.info("Auditoria heurística REJEITOU: %s", heuristic_reason)
            return result

        # --- Validação semântica com LLM (se disponível) ---
        if self._llm is not None:
            return self._llm_audit(draft)

        # Sem LLM → aprovação heurística
        result.approved = True
        result.reason = "Aprovado por validação heurística (sem LLM disponível)."
        result.technical_changes = draft.get("technical_changes", "")
        result.updated_pointers = draft.get("updated_pointers", [])
        logger.info("Auditoria heurística APROVOU (modo sem LLM).")
        return result

    def _heuristic_audit(self, draft: dict) -> tuple[bool, str]:
        """Validação rígida baseada em regras (sem LLM).

        Returns:
            Tuple (passed: bool, reason: str).
        """
        tc = draft.get("technical_changes", "")
        up = draft.get("updated_pointers", [])

        # Regra 1: technical_changes não pode estar vazio
        if not tc or not tc.strip():
            return False, "technical_changes está vazio ou contém apenas espaços."

        # Regra 2: technical_changes muito curto (< 10 caracteres)
        if len(tc.strip()) < 10:
            return False, (
                f"technical_changes muito curto ({len(tc.strip())} caracteres). "
                "Descreva as mudanças com mais detalhes."
            )

        # Regra 3: updated_pointers deve ter pelo menos 1 item
        if not up or (isinstance(up, list) and len(up) == 0):
            return False, "updated_pointers está vazio. Inclua ao menos 1 ponteiro."

        # Regra 4: cada ponteiro deve ser uma string não vazia
        if isinstance(up, list):
            empty_ptrs = [p for p in up if not isinstance(p, str) or not p.strip()]
            if empty_ptrs:
                return False, (
                    f"{len(empty_ptrs)} ponteiro(s) inválido(s) em updated_pointers. "
                    "Cada ponteiro deve ser uma string não vazia."
                )

        return True, "OK"

    def _llm_audit(self, draft: dict) -> AuditResult:
        """Validação semântica via LLM (quando disponível).

        Returns:
            AuditResult com decisão do LLM.
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

                status = "APROVOU" if result.approved else "REJEITOU"
                logger.info("Auditoria LLM %s: %s", status, result.reason[:100])
                return result

            logger.warning("Auditoria LLM retornou JSON inválido — fallback heurístico.")

        except Exception as e:
            logger.error("Auditoria LLM falhou: %s — fallback heurístico.", e)

        # Fallback: aprovação heurística
        result.approved = True
        result.reason = "Aprovado por fallback (LLM indisponível ou resposta inválida)."
        result.technical_changes = draft.get("technical_changes", "")
        result.updated_pointers = draft.get("updated_pointers", [])
        result.partial_audit = True
        return result

    def audit_with_retry(
        self,
        draft: dict,
        generate_fn: Optional[Any] = None,
    ) -> AuditResult:
        """Executa o loop de auditoria completo (máx N tentativas).

        Se o revisor rejeitar, chama generate_fn para gerar um novo rascunho
        com o feedback da rejeição. Após max_loops rejeições, aprova com
        partial_audit=True.

        Args:
            draft: Rascunho inicial.
            generate_fn: Callable(task, outcome, feedback) -> dict
                         Função para regenerar o rascunho.
                         Se None, retorna o resultado da primeira tentativa.

        Returns:
            AuditResult final (aprovado ou partial_audit).
        """
        current_draft = draft

        for attempt in range(1, self._max_loops + 1):
            result = self.audit(current_draft)
            result.loop_count = attempt

            if result.approved:
                logger.info(
                    "Commit aprovado na tentativa %d/%d.",
                    attempt, self._max_loops,
                )
                return result

            logger.warning(
                "Commit rejeitado (%d/%d): %s",
                attempt, self._max_loops, result.reason,
            )

            # Se não tem função de regeneração, retorna rejeição
            if generate_fn is None:
                return result

            # Regenera com feedback
            try:
                current_draft = generate_fn(result.reason)
            except Exception as e:
                logger.error("Falha ao regenerar rascunho: %s", e)
                break

        # Fallback após max_loops
        logger.error(
            "Commit não aprovado após %d tentativas — partial_audit=True.",
            self._max_loops,
        )

        final = AuditResult(
            approved=True,
            reason=f"Aprovado por partial_audit após {self._max_loops} rejeições.",
            technical_changes=current_draft.get("technical_changes", ""),
            updated_pointers=current_draft.get("updated_pointers", []),
            partial_audit=True,
            loop_count=self._max_loops,
        )
        return final

    # ===================================================================
    # PAPEL 2 — RERANKING DE GAVETAS
    # ===================================================================

    def rerank(
        self,
        candidates: list[dict],
        task_context: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Filtra resultados de busca por relevância técnica.

        Se LLM disponível: usa LLM como juiz semântico.
        Se não: aplica heurísticas baseadas em score_final.

        Args:
            candidates: Top-N resultados da Busca Híbrida v4.
                        Cada dict deve ter: node_id, score_final, score_breakdown.
            task_context: Descrição da tarefa atual.
            max_results: Máximo de resultados a retornar.

        Returns:
            Lista filtrada de candidatos aprovados (1 a max_results itens).
        """
        if not candidates:
            return []

        # Limita a max_results antes do reranking
        top_candidates = candidates[:max_results]

        if self._llm is not None:
            reranked = self._llm_rerank(top_candidates, task_context)
        else:
            reranked = self._heuristic_rerank(top_candidates)

        logger.info(
            "Reranking: %d candidatos → %d aprovados (task='%.50s...')",
            len(top_candidates), len(reranked), task_context,
        )
        return reranked

    def _heuristic_rerank(self, candidates: list[dict]) -> list[dict]:
        """Reranking heurístico (sem LLM).

        Filtra candidatos com score_final abaixo de 30% do melhor score.
        Garante pelo menos 1 resultado.
        """
        if not candidates:
            return []

        max_score = max(c.get("score_final", 0) for c in candidates)
        threshold = max_score * 0.30

        filtered = [
            c for c in candidates
            if c.get("score_final", 0) >= threshold
        ]

        # Garante pelo menos 1 resultado
        if not filtered and candidates:
            filtered = [candidates[0]]

        logger.debug(
            "Reranking heurístico: threshold=%.4f, filtrados=%d/%d",
            threshold, len(filtered), len(candidates),
        )
        return filtered

    def _llm_rerank(self, candidates: list[dict], task_context: str) -> list[dict]:
        """Reranking semântico via LLM.

        O LLM avalia cada candidato e atribui um score de relevância.
        Candidatos abaixo do RERANK_RELEVANCE_THRESHOLD são filtrados.
        """
        # Monta bloco de candidatos para o prompt
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

                # Monta mapa node_id → relevância
                relevance_map: dict[int, float] = {}
                for ev in evaluations:
                    nid = ev.get("node_id")
                    rel = ev.get("relevance", 0.0)
                    if nid is not None:
                        relevance_map[int(nid)] = float(rel)

                # Filtra candidatos aprovados
                approved: list[dict] = []
                for c in candidates:
                    nid = c.get("node_id")
                    relevance = relevance_map.get(nid, 0.0)
                    if relevance >= self.RERANK_RELEVANCE_THRESHOLD:
                        c_copy = dict(c)
                        c_copy["rerank_relevance"] = relevance
                        approved.append(c_copy)

                # Garante pelo menos 1 resultado
                if not approved and candidates:
                    best_nid = max(relevance_map, key=relevance_map.get, default=None)
                    if best_nid is not None:
                        for c in candidates:
                            if c.get("node_id") == best_nid:
                                c_copy = dict(c)
                                c_copy["rerank_relevance"] = relevance_map[best_nid]
                                approved = [c_copy]
                                break

                # Ordena por relevância do reranking
                approved.sort(
                    key=lambda x: x.get("rerank_relevance", 0),
                    reverse=True,
                )

                logger.info(
                    "Reranking LLM: %d/%d aprovados (threshold=%.2f)",
                    len(approved), len(candidates), self.RERANK_RELEVANCE_THRESHOLD,
                )
                return approved

            logger.warning("Reranking LLM retornou JSON inválido — fallback heurístico.")

        except Exception as e:
            logger.error("Reranking LLM falhou: %s — fallback heurístico.", e)

        # Fallback heurístico
        return self._heuristic_rerank(candidates)

    # ===================================================================
    # PAPEL 3 — BARREIRA DE CONTAMINAÇÃO
    # ===================================================================

    def check_contamination(
        self,
        source_project: dict,
        target_project: dict,
    ) -> tuple[bool, str]:
        """Verifica se há risco de contaminação entre projetos.

        Regra: dados de projetos RESTRICTED não podem fluir para
        contextos PUBLIC ou INTERNAL.

        Args:
            source_project: Projeto de origem dos dados.
            target_project: Projeto que receberá/exporá os dados.

        Returns:
            Tuple (is_safe: bool, reason: str).
        """
        source_privacy = source_project.get("privacy_level", "PUBLIC")
        target_privacy = target_project.get("privacy_level", "PUBLIC")

        # Hierarquia: RESTRICTED > INTERNAL > PUBLIC
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
    # UTILITÁRIOS
    # ===================================================================

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extrai JSON de uma resposta LLM (com fallback regex).

        Tenta:
            1. json.loads() direto
            2. Regex para encontrar bloco JSON embutido
        """
        if not text:
            return None

        # Tentativa 1: parse direto
        clean = text.strip()
        if clean.startswith("```"):
            # Remove fences de markdown
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines).strip()

        try:
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            pass

        # Tentativa 2: regex
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group())
            except (json.JSONDecodeError, TypeError):
                pass

        return None
