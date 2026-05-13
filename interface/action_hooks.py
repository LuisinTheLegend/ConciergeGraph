"""
interface/action_hooks.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Gatilhos Reativos de Ciclo de Vida para Módulos Operacionais.

Este módulo expõe decoradores e funções que permitem que qualquer
Módulo Operacional (Skills no Cursor, Agentes no n8n, Automações)
se conecte ao Grafo Concierge em momentos-chave do ciclo de vida.

Triggers:
    on_planning()   → Reativa consciência + busca gavetas relevantes
    on_execution()  → Busca focada + lazy load de nós específicos
    on_done()       → Commit auditado + decaimento de trajetórias

Fluxo típico de um Módulo Operacional:
    1. Módulo recebe tarefa do usuário
    2. Chama hooks.on_planning() → recebe Bússola + contexto
    3. Executa tarefa usando hooks.on_execution() para buscar código
    4. Finaliza com hooks.on_done() → grava resultado no grafo

Integração:
    - Consome core.middleware.GrafoConcierge como única dependência
    - Consome agents.revisor_critico.RevisorCritico para auditoria
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.middleware import GrafoConcierge
from agents.revisor_critico import RevisorCritico

logger = logging.getLogger("grafo-concierge.hooks")


class ActionHooks:
    """Gatilhos reativos para Módulos Operacionais.

    Centraliza os pontos de contato entre Módulos Operacionais e
    o Grafo Concierge. Cada método corresponde a uma fase do
    ciclo de vida de uma tarefa.

    Args:
        concierge: Instância da Fachada Central.
        revisor: Instância do Revisor Crítico (opcional).
                 Se None, commits não passam por auditoria LLM.
    """

    def __init__(
        self,
        concierge: GrafoConcierge,
        revisor: Optional[RevisorCritico] = None,
    ) -> None:
        self._gc = concierge
        self._revisor = revisor or RevisorCritico()

        logger.info(
            "ActionHooks inicializado: revisor=%s",
            "LLM" if revisor and revisor._llm else "heurístico",
        )

    # ===================================================================
    # ON_PLANNING — Reativação de consciência
    # ===================================================================

    def on_planning(
        self,
        project_uuid: str,
        task: str,
        top_k: int = 5,
        node_type: Optional[str] = None,
    ) -> dict:
        """Trigger de planejamento — prepara o contexto para a tarefa.

        Fluxo:
            1. Wake-up → carrega Bússola + Reference Wings + commits
            2. Busca Híbrida → encontra gavetas relevantes para a tarefa
            3. Retorna pacote de contexto completo

        Args:
            project_uuid: UUID do projeto.
            task: Descrição da tarefa a ser executada.
            top_k: Máximo de resultados da busca.
            node_type: Filtro cirúrgico opcional.

        Returns:
            Dict com:
            {
                "wake_up": dict (Bússola + Wings + commits),
                "relevant_nodes": list[dict] (resultados da busca),
                "task": str,
            }
        """
        logger.info("on_planning: projeto=%s, task='%.50s...'", project_uuid, task)

        # 1. Wake-up
        wake_data = self._gc.wake_up(project_uuid)

        # 2. Busca Híbrida
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
            "on_planning OK: wake_up com %d commits, %d nós relevantes.",
            len(wake_data.get("recent_commits", [])),
            len(search_results),
        )
        return result

    # ===================================================================
    # ON_EXECUTION — Busca focada durante execução
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
        """Trigger de execução — busca e filtra gavetas por relevância.

        Fluxo:
            1. Busca Híbrida v4 com Strict Scoping
            2. Se rerank=True, Revisor Crítico filtra top-5
            3. Retorna gavetas relevantes para a tarefa

        Args:
            project_uuid: UUID do projeto.
            task: Descrição da tarefa atual.
            top_k: Máximo de resultados da busca inicial.
            node_type: Filtro cirúrgico (FACT, SKILL, INSIGHT, etc.).
            include_references: Incluir Reference Wings.
            rerank: Aplicar Reranking do Revisor Crítico.

        Returns:
            Lista de dicts com resultados filtrados.
        """
        logger.info("on_execution: projeto=%s, task='%.50s...'", project_uuid, task)

        # 1. Busca Híbrida
        search_results = self._gc.hybrid_search(
            query=task,
            project_uuid=project_uuid,
            top_k=top_k,
            include_references=include_references,
            node_type=node_type,
        )

        # 2. Reranking (se ativo e houver resultados)
        if rerank and search_results:
            search_results = self._revisor.rerank(
                candidates=search_results,
                task_context=task,
                max_results=5,
            )

        logger.info(
            "on_execution OK: %d resultados (rerank=%s).",
            len(search_results), rerank,
        )
        return search_results

    # ===================================================================
    # ON_DONE — Commit auditado pós-tarefa
    # ===================================================================

    def on_done(
        self,
        project_uuid: str,
        outcome: dict,
    ) -> dict:
        """Trigger de conclusão — registra resultado no grafo.

        Fluxo:
            1. Revisor Crítico audita o rascunho
            2. Se aprovado, grava commit no grafo
            3. Se houver erro/solução, registra trajetória episódica
            4. Retorna resultado da operação

        Args:
            project_uuid: UUID do projeto.
            outcome: Dict com resultado da tarefa:
                - phase (str): Fase (planning, build, done, review)
                - technical_changes (str): Mudanças técnicas
                - updated_pointers (list[str]): Ponteiros atualizados
                - node_ids (list[int], opcional): Nós afetados
                - erro_encontrado (str, opcional): Erro ocorrido
                - solucao_aplicada (str, opcional): Solução aplicada

        Returns:
            Dict com:
            {
                "commit_id": int,
                "audit": AuditResult.to_dict(),
                "trajectory_id": int (se houve erro),
            }
        """
        logger.info("on_done: projeto=%s, fase='%s'", project_uuid, outcome.get("phase", "?"))

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
