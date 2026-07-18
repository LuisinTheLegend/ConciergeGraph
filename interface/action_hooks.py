"""
interface/action_hooks.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Reactive Lifecycle Triggers for Operational Modules.

This module exposes decorators and functions that allow any
Operational Module (Cursor Skills, n8n Agents, Automations)
to connect to Grafo Concierge at key lifecycle moments.

Triggers:
    on_planning()   -> Reactivates consciousness + searches relevant drawers
    on_execution()  -> Focused search + lazy load of specific nodes
    on_done()       -> Audited commit + trajectory decay

Typical flow of an Operational Module:
    1. Module receives user task
    2. Calls hooks.on_planning() -> receives Compass + context
    3. Executes task using hooks.on_execution() to fetch code
    4. Finishes with hooks.on_done() -> writes result to graph

Integration:
    - Consumes core.middleware.GrafoConcierge as sole dependency
    - Consumes agents.revisor_critico.RevisorCritico for auditing
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.middleware import GrafoConcierge
from agents.revisor_critico import RevisorCritico

logger = logging.getLogger("grafo-concierge.hooks")


class ActionHooks:
    """Reactive triggers for Operational Modules.

    Centralizes contact points between Operational Modules and
    Grafo Concierge. Each method corresponds to a phase of
    a task's lifecycle.

    Args:
        concierge: Central Facade instance.
        revisor: Critical Reviewer instance (optional).
                 If None, commits do not go through LLM auditing.
    """

    def __init__(
        self,
        concierge: GrafoConcierge,
        revisor: Optional[RevisorCritico] = None,
    ) -> None:
        self._gc = concierge
        self._revisor = revisor or RevisorCritico()

        logger.info(
            "ActionHooks initialized: reviewer=%s",
            "LLM" if revisor and revisor._llm else "heuristic",
        )

    # ===================================================================
    # ON_PLANNING — Consciousness reactivation
    # ===================================================================

    def on_planning(
        self,
        project_uuid: str,
        task: str,
        top_k: int = 5,
        node_type: Optional[str] = None,
    ) -> dict:
        """Planning trigger — prepares the context for the task.

        Flow:
            1. Wake-up -> loads Compass + Reference Wings + commits
            2. Hybrid Search -> finds relevant drawers for the task
            3. Returns full context package

        Args:
            project_uuid: UUID of the project.
            task: Description of the task to be executed.
            top_k: Maximum number of search results.
            node_type: Optional surgical filter.

        Returns:
            Dict with:
            {
                "wake_up": dict (Compass + Wings + commits),
                "relevant_nodes": list[dict] (search results),
                "task": str,
            }
        """
        logger.info("on_planning: project=%s, task='%.50s...'", project_uuid, task)

        # 1. Wake-up
        wake_data = self._gc.wake_up(project_uuid)

        # 2. Hybrid Search
        search_results = self._gc.hybrid_search(
            query=task,
            project_uuid=project_uuid,
            top_k=top_k,
            node_type=node_type,
        )

        result = {
            "wake_up": wake_data,
            "relevant_nodes": search_results,
            "task": task,
        }

        logger.info(
            "on_planning OK: wake_up with %d commits, %d relevant nodes.",
            len(wake_data.get("recent_commits", [])),
            len(search_results),
        )
        return result

    # ===================================================================
    # ON_EXECUTION — Focused search during execution
    # ===================================================================

    def on_execution(
        self,
        project_uuid: str,
        task: str,
        top_k: int = 10,
        node_type: Optional[str] = None,
        include_references: bool = False,
        rerank: bool = True,
    ) -> list[dict]:
        """Execution trigger — searches and filters drawers by relevance.

        Flow:
            1. Hybrid Search v4 with Strict Scoping
            2. If rerank=True, Critical Reviewer filters top-5
            3. Returns relevant drawers for the task

        Args:
            project_uuid: UUID of the project.
            task: Description of the current task.
            top_k: Maximum number of initial search results.
            node_type: Surgical filter (FACT, SKILL, INSIGHT, etc.).
            include_references: Include Reference Wings.
            rerank: Apply Critical Reviewer Reranking.

        Returns:
            List of dicts with filtered results.
        """
        logger.info("on_execution: project=%s, task='%.50s...'", project_uuid, task)

        # 1. Hybrid Search
        search_results = self._gc.hybrid_search(
            query=task,
            project_uuid=project_uuid,
            top_k=top_k,
            include_references=include_references,
            node_type=node_type,
        )

        # 2. Reranking (if active and there are results)
        if rerank and search_results:
            search_results = self._revisor.rerank(
                candidates=search_results,
                task_context=task,
                max_results=5,
            )

        logger.info(
            "on_execution OK: %d results (rerank=%s).",
            len(search_results), rerank,
        )
        return search_results

    # ===================================================================
    # ON_DONE — Audited commit post-task
    # ===================================================================

    def on_done(
        self,
        project_uuid: str,
        outcome: dict,
    ) -> dict:
        """Conclusion trigger — registers result in the graph.

        Flow:
            1. Critical Reviewer audits the draft
            2. If approved, writes commit to the graph
            3. If there is an error/solution, registers episodic trajectory
            4. Returns operation result

        Args:
            project_uuid: UUID of the project.
            outcome: Dict with task outcome:
                - phase (str): Phase (planning, build, done, review)
                - technical_changes (str): Technical changes
                - updated_pointers (list[str]): Updated pointers
                - node_ids (list[int], optional): Affected nodes
                - erro_encontrado (str, optional): Error occurred
                - solucao_aplicada (str, optional): Solution applied

        Returns:
            Dict with:
            {
                "commit_id": int,
                "audit": AuditResult.to_dict(),
                "trajectory_id": int (if there was an error),
            }
        """
        logger.info("on_done: project=%s, phase='%s'", project_uuid, outcome.get("phase", "?"))

        result: dict[str, Any] = {}

        # 1. Auditoria do commit
        audit = self._revisor.audit({
            "phase": outcome.get("phase", "done"),
            "technical_changes": outcome.get("technical_changes", ""),
            "updated_pointers": outcome.get("updated_pointers", []),
            "source_wing": "primary",
        })
        result["audit"] = audit.to_dict()

        # 2. Grava commit (mesmo se partial_audit, para não perder dados)
        if audit.approved:
            commit_id = self._gc.commit_memory(
                project_uuid=project_uuid,
                phase=outcome.get("phase", "done"),
                technical_changes=audit.technical_changes,
                updated_pointers=audit.updated_pointers,
                node_ids=outcome.get("node_ids"),
            )
            result["commit_id"] = commit_id
        else:
            result["commit_id"] = None
            logger.warning("on_done: commit REJEITADO — %s", audit.reason)

        # 3. Registra trajetória episódica (se houve erro)
        if outcome.get("erro_encontrado"):
            try:
                trajectory_id = self._gc.store.create_trajectory(
                    project_uuid=project_uuid,
                    prompt_origem=outcome.get("task", ""),
                    tentativa_execucao=outcome.get("technical_changes", ""),
                    erro_encontrado=outcome.get("erro_encontrado"),
                    solucao_aplicada=outcome.get("solucao_aplicada"),
                )
                result["trajectory_id"] = trajectory_id
                logger.info(
                    "Trajetória episódica registrada: id=%d", trajectory_id,
                )
            except Exception as e:
                logger.error("Falha ao registrar trajetória: %s", e)
                result["trajectory_id"] = None

        logger.info(
            "on_done OK: commit_id=%s, audit_approved=%s, partial=%s",
            result.get("commit_id"), audit.approved, audit.partial_audit,
        )
        return result
