"""
storage/logic.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Núcleo de Inteligência do Grafo — Algoritmos Apex.

Três pilares:
    1. Decaimento de Trajetórias (Version-Binding)
    2. Centralidade de Nós (in-degree normalizado + detecção de Super-Nós)
    3. Busca Híbrida Ponderada (FTS5 BM25 + Vetorial + Max(Recência, Centralidade))

Fórmulas de referência (Architecture v3.8):
    - Centralidade:  min(in_degree / 10, 1.0)
    - Recência:      max(e^(-λ × t), 0.01)  onde λ = ln(2)/7 ≈ 0.0990
    - Score Final:   0.50×vetorial + 0.25×fts5 + 0.25×max(recência, centralidade)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from storage.schema import VALID_STATUSES

logger = logging.getLogger("grafo-concierge.logic")


# ---------------------------------------------------------------------------
# Exceções específicas do módulo de inteligência
# ---------------------------------------------------------------------------

class TrajectoryNotFoundError(Exception):
    """Trajetória com o ID fornecido não existe no banco."""


class InvalidTransitionError(Exception):
    """Transição de status ilegal (ex: ARCHIVED → ACTIVE)."""


# ---------------------------------------------------------------------------
# GraphLogic — motor de inteligência do Grafo Concierge
# ---------------------------------------------------------------------------

class GraphLogic:
    """Motor de inteligência sobre o grafo persistido no SQLite.

    Depende de um ConnectionManager (connection.py) para acesso ao banco.
    Leituras via conn_manager.read(), escritas via conn_manager.write().

    Args:
        conn_manager: Instância de ConnectionManager.
    """

    # --- Constantes de Recência (Decaimento Exponencial) ---
    # Meia-vida de 7 dias: após 7 dias sem commit, score cai para 0.50.
    RECENCY_HALF_LIFE_DAYS: float = 7.0
    RECENCY_LAMBDA: float = math.log(2) / 7.0  # ≈ 0.09902
    RECENCY_MIN_SCORE: float = 0.01             # Nós antigos nunca zeram

    # --- Constantes de Centralidade ---
    # Um nó com 10+ dependentes é considerado "Super-Nó" (score = 1.0).
    CENTRALITY_MAX_IN_DEGREE: int = 10

    # --- Pesos da Busca Híbrida v4 ---
    WEIGHT_VECTOR: float = 0.50
    WEIGHT_FTS5: float = 0.25
    WEIGHT_RECENCY_CENTRALITY: float = 0.25

    # --- Transições de status válidas para Trajetórias ---
    # Cada chave mapeia para os estados que pode transicionar.
    _VALID_TRANSITIONS: dict[str, frozenset[str]] = {
        "ACTIVE":   frozenset({"STALE", "ARCHIVED"}),
        "STALE":    frozenset({"ACTIVE", "ARCHIVED"}),
        "ARCHIVED": frozenset(),  # Estado terminal — sem retorno
    }

    def __init__(self, conn_manager: Any) -> None:
        self._conn = conn_manager

    # ===================================================================
    # 1. DECAIMENTO DE TRAJETÓRIAS (Version-Binding)
    # ===================================================================

    def decay_trajectory(self, trajectory_id: int, new_status: str) -> bool:
        """Altera o status de uma trajetória episódica com validação de transição.

        Regras de transição (máquina de estados):
            ACTIVE  → STALE, ARCHIVED
            STALE   → ACTIVE, ARCHIVED  (re-ativação permitida)
            ARCHIVED → (terminal, nenhuma transição permitida)

        Args:
            trajectory_id: ID na tabela trajectories.
            new_status: Status destino (ACTIVE, STALE ou ARCHIVED).

        Returns:
            True se a transição foi aplicada.

        Raises:
            ValueError: Se new_status não é um status válido.
            TrajectoryNotFoundError: Se trajectory_id não existe.
            InvalidTransitionError: Se a transição é ilegal.
        """
        # Validação 1: status destino é reconhecido?
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Status inválido: '{new_status}'. "
                f"Valores aceitos: {sorted(VALID_STATUSES)}"
            )

        # Leitura do status atual
        with self._conn.read() as conn:
            row = conn.execute(
                "SELECT id, status FROM trajectories WHERE id = ?",
                (trajectory_id,)
            ).fetchone()

        if row is None:
            raise TrajectoryNotFoundError(
                f"Trajetória ID={trajectory_id} não encontrada."
            )

        current_status = row["status"]

        # Validação 2: a transição é legal?
        allowed = self._VALID_TRANSITIONS.get(current_status, frozenset())
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Transição ilegal: {current_status} → {new_status}. "
                f"Transições permitidas de '{current_status}': {sorted(allowed) or 'nenhuma (terminal)'}"
            )

        # Escrita serializada
        def _do(conn: Any, tid: int, status: str) -> bool:
            conn.execute(
                "UPDATE trajectories SET status = ? WHERE id = ?",
                (status, tid)
            )
            return True

        result = self._conn.write(_do, trajectory_id, new_status)
        logger.info(
            "Trajetória ID=%d: %s → %s", trajectory_id, current_status, new_status
        )
        return result

    def bulk_decay_stale_trajectories(
        self, project_uuid: str, stale_threshold_days: int = 30
    ) -> int:
        """Marca como STALE todas as trajetórias ACTIVE mais velhas que o threshold.

        Usado pelo Background Janitor no Reconciliation Loop.

        Args:
            project_uuid: UUID do projeto alvo.
            stale_threshold_days: Dias desde created_at para considerar stale.

        Returns:
            Número de trajetórias afetadas.
        """
        def _do(conn: Any, pu: str, days: int) -> int:
            cursor = conn.execute(
                """UPDATE trajectories
                   SET status = 'STALE'
                   WHERE project_uuid = ?
                     AND status = 'ACTIVE'
                     AND julianday('now') - julianday(created_at) > ?""",
                (pu, days)
            )
            return cursor.rowcount

        affected = self._conn.write(_do, project_uuid, stale_threshold_days)
        if affected > 0:
            logger.info(
                "Bulk decay: %d trajetórias marcadas STALE no projeto %s (threshold=%d dias)",
                affected, project_uuid, stale_threshold_days
            )
        return affected

    # ===================================================================
    # 2. CENTRALIDADE (in-degree normalizado + Super-Nós)
    # ===================================================================

    def compute_centrality(self, node_id: int) -> float:
        """Calcula a centralidade normalizada de um nó.

        Fórmula: min(in_degree / CENTRALITY_MAX_IN_DEGREE, 1.0)

        Um nó com in_degree >= 10 é um "Super-Nó": código core estável
        que muitos arquivos dependem. Recebe centralidade máxima (1.0),
        protegendo-o contra penalização por recência baixa no Hybrid Search.

        Args:
            node_id: ID do nó na tabela nodes.

        Returns:
            Float no intervalo [0.0, 1.0].
        """
        with self._conn.read() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS in_deg FROM edges WHERE target_id = ?",
                (node_id,)
            ).fetchone()

        in_degree = row["in_deg"] if row else 0
        centrality = min(in_degree / self.CENTRALITY_MAX_IN_DEGREE, 1.0)

        logger.debug(
            "Centralidade nó ID=%d: in_degree=%d, score=%.4f%s",
            node_id, in_degree, centrality,
            " [SUPER-NÓ]" if centrality >= 1.0 else ""
        )
        return centrality

    def compute_centrality_batch(self, node_ids: list[int]) -> dict[int, float]:
        """Calcula centralidade para múltiplos nós em uma única query SQL.

        Args:
            node_ids: Lista de IDs de nós.

        Returns:
            Dict mapeando node_id → centralidade normalizada [0.0, 1.0].
            Nós sem arestas de entrada retornam 0.0.
        """
        if not node_ids:
            return {}

        # Inicializa todos com 0.0 (caso não tenham arestas)
        result: dict[int, float] = {nid: 0.0 for nid in node_ids}

        placeholders = ",".join("?" for _ in node_ids)
        with self._conn.read() as conn:
            rows = conn.execute(
                f"""SELECT target_id, COUNT(*) AS in_deg
                    FROM edges
                    WHERE target_id IN ({placeholders})
                    GROUP BY target_id""",
                tuple(node_ids)
            ).fetchall()

        for row in rows:
            in_deg = row["in_deg"]
            result[row["target_id"]] = min(in_deg / self.CENTRALITY_MAX_IN_DEGREE, 1.0)

        super_nodes = [nid for nid, score in result.items() if score >= 1.0]
        if super_nodes:
            logger.debug("Super-Nós detectados (batch): %s", super_nodes)

        return result

    # ===================================================================
    # 3. SCORE DE RECÊNCIA (Decaimento Exponencial)
    # ===================================================================

    def compute_recency_score(self, node_id: int) -> float:
        """Calcula o score de recência via decaimento exponencial.

        Fórmula: max(e^(-λ × t), RECENCY_MIN_SCORE)
        Onde:
            λ = ln(2) / 7 ≈ 0.09902
            t = dias desde nodes.last_commit_at

        Se last_commit_at for NULL, retorna RECENCY_MIN_SCORE (0.01).

        Args:
            node_id: ID do nó.

        Returns:
            Float no intervalo [0.01, 1.0].
        """
        with self._conn.read() as conn:
            row = conn.execute(
                "SELECT last_commit_at FROM nodes WHERE id = ?",
                (node_id,)
            ).fetchone()

        if row is None or row["last_commit_at"] is None:
            return self.RECENCY_MIN_SCORE

        return self._calculate_decay(row["last_commit_at"])

    def compute_recency_batch(self, node_ids: list[int]) -> dict[int, float]:
        """Calcula recência em batch para múltiplos nós.

        Args:
            node_ids: Lista de IDs de nós.

        Returns:
            Dict mapeando node_id → score de recência [0.01, 1.0].
        """
        if not node_ids:
            return {}

        result: dict[int, float] = {}
        placeholders = ",".join("?" for _ in node_ids)

        with self._conn.read() as conn:
            rows = conn.execute(
                f"SELECT id, last_commit_at FROM nodes WHERE id IN ({placeholders})",
                tuple(node_ids)
            ).fetchall()

        for row in rows:
            if row["last_commit_at"] is None:
                result[row["id"]] = self.RECENCY_MIN_SCORE
            else:
                result[row["id"]] = self._calculate_decay(row["last_commit_at"])

        # Garante que nós não encontrados retornem score mínimo
        for nid in node_ids:
            if nid not in result:
                result[nid] = self.RECENCY_MIN_SCORE

        return result

    def _calculate_decay(self, last_commit_at: str) -> float:
        """Aplica a fórmula de decaimento exponencial.

        Args:
            last_commit_at: Timestamp ISO do último commit (ex: '2026-05-01 12:00:00').

        Returns:
            Score no intervalo [RECENCY_MIN_SCORE, 1.0].
        """
        try:
            commit_dt = datetime.fromisoformat(last_commit_at)
            now = datetime.utcnow()
            delta_days = max((now - commit_dt).total_seconds() / 86400, 0.0)
        except (ValueError, TypeError):
            logger.warning("last_commit_at inválido: '%s'. Usando score mínimo.", last_commit_at)
            return self.RECENCY_MIN_SCORE

        # e^(-λ × t) com floor em MIN_SCORE
        score = math.exp(-self.RECENCY_LAMBDA * delta_days)
        return max(score, self.RECENCY_MIN_SCORE)

    # ===================================================================
    # 4. FTS5 — Busca textual com BM25 normalizado
    # ===================================================================

    def fts_search(
        self,
        query: str,
        project_uuid: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Busca textual via FTS5 com BM25 normalizado para [0, 1].

        O SQLite retorna bm25() como valor negativo (mais negativo = mais relevante).
        Normalizamos para [0, 1] usando:  1.0 - (rank / min_rank)
        onde min_rank é o valor mais negativo (mais relevante) do batch.

        Args:
            query: Texto de busca. Caracteres especiais são escapados.
            project_uuid: Filtro opcional por projeto (Strict Scoping).
            node_type: Filtro cirúrgico (FACT, SKILL, INSIGHT, TRAJECTORY, PATCH).
            limit: Máximo de resultados.

        Returns:
            Lista de dicts com campos do nó + 'bm25_score' normalizado [0, 1].
            Ordenada do mais relevante para o menos relevante.
        """
        # Escapa aspas no query para prevenir injection no FTS5
        safe_query = query.replace('"', '""')

        # Monta a query SQL dinamicamente conforme os filtros
        sql = """
            SELECT n.*, bm25(nodes_fts) AS rank
            FROM nodes_fts f
            JOIN nodes n ON n.id = f.rowid
            WHERE nodes_fts MATCH ?
        """
        params: list[Any] = [f'"{safe_query}"']

        if project_uuid:
            sql += " AND n.project_uuid = ?"
            params.append(project_uuid)

        if node_type:
            sql += " AND n.node_type = ?"
            params.append(node_type)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self._conn.read() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        if not rows:
            return []

        results = [dict(r) for r in rows]

        # Normaliza BM25: o rank mais negativo vira 1.0 e o menos negativo vira ~0.0
        min_rank = min(r["rank"] for r in results)  # valor mais negativo
        for r in results:
            if min_rank < 0:
                r["bm25_score"] = round(r["rank"] / min_rank, 4)
            else:
                r["bm25_score"] = 1.0
            del r["rank"]  # Remove campo interno do SQLite

        return results

    def fts_rebuild(self) -> None:
        """Reconstrói o índice FTS5 completo.

        Usar após ingestão massiva (concierge mine) para otimizar performance.
        """
        def _do(conn: Any) -> None:
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

        self._conn.write(_do)
        logger.info("Índice FTS5 reconstruído com sucesso.")

    # ===================================================================
    # 5. BUSCA HÍBRIDA PONDERADA (Hybrid Search v4)
    # ===================================================================

    def hybrid_search_score(
        self,
        node_id: int,
        vector_score: float,
        fts_score: float,
    ) -> dict:
        """Calcula o score final combinado para um nó no Hybrid Search v4.

        Fórmula (Architecture v3.8):
            score = (0.50 × vetorial)
                  + (0.25 × fts5_normalizado)
                  + (0.25 × max(recência, centralidade))

        O terceiro componente usa max(recência, centralidade) para proteger
        "código core" estável: se um nó é antigo (recência baixa) mas tem
        alta centralidade (muitos dependentes), a centralidade prevalece.

        Args:
            node_id: ID do nó.
            vector_score: Score de similaridade vetorial [0, 1] (do backend plugável).
            fts_score: Score BM25 normalizado [0, 1] (do fts_search).

        Returns:
            Dict com breakdown completo:
            {
                "node_id": int,
                "score_final": float,
                "score_breakdown": {
                    "vetorial": float,
                    "frequencia": float,
                    "recencia": float,
                    "centralidade": float
                },
                "is_super_node": bool
            }
        """
        # Calcula os componentes individuais
        recency = self.compute_recency_score(node_id)
        centrality = self.compute_centrality(node_id)

        # max(recência, centralidade): protege Super-Nós estáveis
        recency_centrality = max(recency, centrality)

        # Score final ponderado
        score_final = (
            self.WEIGHT_VECTOR * vector_score
            + self.WEIGHT_FTS5 * fts_score
            + self.WEIGHT_RECENCY_CENTRALITY * recency_centrality
        )

        return {
            "node_id": node_id,
            "score_final": round(score_final, 4),
            "score_breakdown": {
                "vetorial": round(vector_score, 4),
                "frequencia": round(fts_score, 4),
                "recencia": round(recency, 4),
                "centralidade": round(centrality, 4),
            },
            "is_super_node": centrality >= 1.0,
        }

    def hybrid_search_score_batch(
        self,
        candidates: list[dict],
    ) -> list[dict]:
        """Calcula scores híbridos em batch e retorna ordenado por relevância.

        Otimizado: faz queries de centralidade e recência em batch
        ao invés de N queries individuais.

        Args:
            candidates: Lista de dicts, cada um contendo:
                - "node_id" (int)
                - "vector_score" (float) — do backend vetorial
                - "fts_score" (float) — do fts_search (BM25 normalizado)

        Returns:
            Lista de dicts com score_final e breakdown, ordenada DESC por score.
        """
        if not candidates:
            return []

        node_ids = [c["node_id"] for c in candidates]

        # Batch queries — 2 queries SQL ao invés de 2N
        centrality_map = self.compute_centrality_batch(node_ids)
        recency_map = self.compute_recency_batch(node_ids)

        results = []
        for c in candidates:
            nid = c["node_id"]
            vector_score = c.get("vector_score", 0.0)
            fts_score = c.get("fts_score", 0.0)
            recency = recency_map.get(nid, self.RECENCY_MIN_SCORE)
            centrality = centrality_map.get(nid, 0.0)

            recency_centrality = max(recency, centrality)
            score_final = (
                self.WEIGHT_VECTOR * vector_score
                + self.WEIGHT_FTS5 * fts_score
                + self.WEIGHT_RECENCY_CENTRALITY * recency_centrality
            )

            results.append({
                "node_id": nid,
                "score_final": round(score_final, 4),
                "score_breakdown": {
                    "vetorial": round(vector_score, 4),
                    "frequencia": round(fts_score, 4),
                    "recencia": round(recency, 4),
                    "centralidade": round(centrality, 4),
                },
                "is_super_node": centrality >= 1.0,
            })

        # Ordena por score_final DESC (mais relevante primeiro)
        results.sort(key=lambda x: x["score_final"], reverse=True)

        logger.debug(
            "Hybrid batch: %d candidatos processados. Top score=%.4f",
            len(results), results[0]["score_final"] if results else 0.0
        )
        return results

    # ===================================================================
    # 6. CONSULTAS RECURSIVAS (CTE) com proteção anti-loop
    # ===================================================================

    def get_dependency_tree(
        self, start_node_id: int, max_depth: int = 10
    ) -> list[dict]:
        """Árvore de dependências: source → target (quem este nó depende).

        CTE com limite de profundidade para prevenir loops infinitos.

        Args:
            start_node_id: Nó raiz.
            max_depth: Profundidade máxima (default: 10).

        Returns:
            Lista de dicts: id, label, node_type, depth.
        """
        sql = """
            WITH RECURSIVE dep_tree(id, label, node_type, depth) AS (
                SELECT id, label, node_type, 0
                FROM nodes WHERE id = ?
                UNION ALL
                SELECT n.id, n.label, n.node_type, dt.depth + 1
                FROM nodes n
                JOIN edges e ON n.id = e.target_id
                JOIN dep_tree dt ON e.source_id = dt.id
                WHERE dt.depth < ?
            )
            SELECT DISTINCT * FROM dep_tree ORDER BY depth;
        """
        with self._conn.read() as conn:
            rows = conn.execute(sql, (start_node_id, max_depth)).fetchall()
        return [dict(r) for r in rows]

    def get_reverse_dependency_tree(
        self, start_node_id: int, max_depth: int = 10
    ) -> list[dict]:
        """Árvore reversa: quem depende DESTE nó (target → source).

        Args:
            start_node_id: Nó alvo.
            max_depth: Profundidade máxima.

        Returns:
            Lista de dicts: id, label, node_type, depth.
        """
        sql = """
            WITH RECURSIVE rev_tree(id, label, node_type, depth) AS (
                SELECT id, label, node_type, 0
                FROM nodes WHERE id = ?
                UNION ALL
                SELECT n.id, n.label, n.node_type, rt.depth + 1
                FROM nodes n
                JOIN edges e ON n.id = e.source_id
                JOIN rev_tree rt ON e.target_id = rt.id
                WHERE rt.depth < ?
            )
            SELECT DISTINCT * FROM rev_tree ORDER BY depth;
        """
        with self._conn.read() as conn:
            rows = conn.execute(sql, (start_node_id, max_depth)).fetchall()
        return [dict(r) for r in rows]

    # ===================================================================
    # 7. ESTATÍSTICAS DE PROJETO
    # ===================================================================

    def get_project_stats(self, project_uuid: str) -> dict:
        """Estatísticas completas de um projeto via SQL agregado.

        Returns:
            Dict com: nodes, nodes_by_type, edges, commits,
            last_commit_at, trajectories, trajectories_active.
        """
        with self._conn.read() as conn:
            # Contagem total de nós
            nodes_total = conn.execute(
                "SELECT COUNT(*) AS c FROM nodes WHERE project_uuid = ?",
                (project_uuid,)
            ).fetchone()["c"]

            # Contagem por tipo de nó
            type_rows = conn.execute(
                """SELECT node_type, COUNT(*) AS c FROM nodes
                   WHERE project_uuid = ? GROUP BY node_type""",
                (project_uuid,)
            ).fetchall()
            nodes_by_type = {r["node_type"]: r["c"] for r in type_rows}

            # Arestas do projeto
            edges_count = conn.execute(
                """SELECT COUNT(*) AS c FROM edges e
                   JOIN nodes n ON e.source_id = n.id
                   WHERE n.project_uuid = ?""",
                (project_uuid,)
            ).fetchone()["c"]

            # Commits
            commits_count = conn.execute(
                "SELECT COUNT(*) AS c FROM commit_log WHERE project_uuid = ?",
                (project_uuid,)
            ).fetchone()["c"]

            last_commit = conn.execute(
                "SELECT MAX(created_at) AS last_at FROM commit_log WHERE project_uuid = ?",
                (project_uuid,)
            ).fetchone()["last_at"]

            # Trajetórias
            traj_total = conn.execute(
                "SELECT COUNT(*) AS c FROM trajectories WHERE project_uuid = ?",
                (project_uuid,)
            ).fetchone()["c"]

            traj_active = conn.execute(
                "SELECT COUNT(*) AS c FROM trajectories WHERE project_uuid = ? AND status = 'ACTIVE'",
                (project_uuid,)
            ).fetchone()["c"]

        return {
            "nodes": nodes_total,
            "nodes_by_type": nodes_by_type,
            "edges": edges_count,
            "commits": commits_count,
            "last_commit_at": last_commit,
            "trajectories": traj_total,
            "trajectories_active": traj_active,
        }

    def get_last_commit_phase(self, project_uuid: str) -> Optional[str]:
        """Retorna a fase do commit mais recente do projeto.

        Returns:
            String da fase (ex: 'build') ou None se sem commits.
        """
        with self._conn.read() as conn:
            row = conn.execute(
                """SELECT phase FROM commit_log
                   WHERE project_uuid = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (project_uuid,)
            ).fetchone()
        return row["phase"] if row else None
