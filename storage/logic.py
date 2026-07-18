"""
storage/logic.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Graph Intelligence Core — Apex Algorithms.

Three pillars:
    1. Trajectories Decay (Version-Binding)
    2. Node Centrality (normalized in-degree + Super-Node detection)
    3. Weighted Hybrid Search (FTS5 BM25 + Vector + Max(Recency, Centrality))

Reference formulas (Architecture v3.8):
    - Centrality:  min(in_degree / 10, 1.0)
    - Recency:      max(e^(-λ × t), 0.01)  where λ = ln(2)/7 ≈ 0.0990
    - Final Score:   0.50×vector + 0.25×fts5 + 0.25×max(recency, centrality)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from storage.schema import VALID_STATUSES

if TYPE_CHECKING:
    from core.config import ConciergeConfig

logger = logging.getLogger("grafo-concierge.logic")


# ---------------------------------------------------------------------------
# Specific exceptions for the intelligence module
# ---------------------------------------------------------------------------

class TrajectoryNotFoundError(Exception):
    """Trajectory with the provided ID does not exist in the database."""


class InvalidTransitionError(Exception):
    """Illegal status transition (e.g. ARCHIVED → ACTIVE)."""


# ---------------------------------------------------------------------------
# GraphLogic — Grafo Concierge intelligence engine
# ---------------------------------------------------------------------------

class GraphLogic:
    """Intelligence engine over the graph persisted in SQLite.

    Depends on a ConnectionManager (connection.py) for database access.
    Reads via conn_manager.read(), writes via conn_manager.write().

    Args:
        conn_manager: Instance of ConnectionManager.
    """

    # --- Recency Constants (Exponential Decay) ---
    # Half-life of 7 days: after 7 days without commit, score drops to 0.50.
    RECENCY_HALF_LIFE_DAYS: float = 7.0
    RECENCY_LAMBDA: float = math.log(2) / 7.0  # ≈ 0.09902
    RECENCY_MIN_SCORE: float = 0.01             # Old nodes never reach zero

    # --- Centrality Constants ---
    # A node with 10+ dependents is considered a "Super-Node" (score = 1.0).
    CENTRALITY_MAX_IN_DEGREE: int = 10

    # --- Hybrid Search Weights v4 ---
    WEIGHT_VECTOR: float = 0.50
    WEIGHT_FTS5: float = 0.25
    WEIGHT_RECENCY_CENTRALITY: float = 0.25

    # --- Valid status transitions for Trajectories ---
    # Each key maps to the states it can transition to.
    _VALID_TRANSITIONS: dict[str, frozenset[str]] = {
        "ACTIVE":   frozenset({"STALE", "ARCHIVED"}),
        "STALE":    frozenset({"ACTIVE", "ARCHIVED"}),
        "ARCHIVED": frozenset(),  # Terminal state — no return
    }

    def __init__(self, conn_manager: Any, config: Optional["ConciergeConfig"] = None) -> None:
        self._conn = conn_manager

        # If config provided, overrides class constants with user values
        if config is not None:
            self.WEIGHT_VECTOR = config.weight_vector
            self.WEIGHT_FTS5 = config.weight_fts5
            self.WEIGHT_RECENCY_CENTRALITY = config.weight_recency_centrality
            self.CENTRALITY_MAX_IN_DEGREE = config.centrality_max_in_degree
            self.RECENCY_HALF_LIFE_DAYS = config.recency_half_life_days
            self.RECENCY_LAMBDA = config.recency_lambda
            self.RECENCY_MIN_SCORE = config.recency_min_score

    # ===================================================================
    # 1. TRAJECTORIES DECAY (Version-Binding)
    # ===================================================================

    def decay_trajectory(self, trajectory_id: int, new_status: str) -> bool:
        """Changes status of an episodic trajectory with transition validation.

        Transition rules (state machine):
            ACTIVE  → STALE, ARCHIVED
            STALE   → ACTIVE, ARCHIVED  (re-activation allowed)
            ARCHIVED → (terminal, no transition allowed)

        Args:
            trajectory_id: ID in trajectories table.
            new_status: Target status (ACTIVE, STALE or ARCHIVED).

        Returns:
            True if the transition was applied.

        Raises:
            ValueError: If new_status is not a valid status.
            TrajectoryNotFoundError: If trajectory_id does not exist.
            InvalidTransitionError: If the transition is illegal.
        """
        # Validation 1: is destination status recognized?
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status: '{new_status}'. "
                f"Accepted values: {sorted(VALID_STATUSES)}"
            )

        # Reading current status
        with self._conn.read() as conn:
            row = conn.execute(
                "SELECT id, status FROM trajectories WHERE id = ?",
                (trajectory_id,)
            ).fetchone()

        if row is None:
            raise TrajectoryNotFoundError(
                f"Trajectory ID={trajectory_id} not found."
            )

        current_status = row["status"]

        # Validation 2: is transition legal?
        allowed = self._VALID_TRANSITIONS.get(current_status, frozenset())
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Illegal transition: {current_status} → {new_status}. "
                f"Allowed transitions from '{current_status}': {sorted(allowed) or 'none (terminal)'}"
            )

        # Serialized write
        def _do(conn: Any, tid: int, status: str) -> bool:
            conn.execute(
                "UPDATE trajectories SET status = ? WHERE id = ?",
                (status, tid)
            )
            return True

        result = self._conn.write(_do, trajectory_id, new_status)
        logger.info(
            "Trajectory ID=%d: %s → %s", trajectory_id, current_status, new_status
        )
        return result

    def bulk_decay_stale_trajectories(
        self, project_uuid: str, stale_threshold_days: int = 30
    ) -> int:
        """Marks as STALE all ACTIVE trajectories older than the threshold.

        Used by Background Janitor in the Reconciliation Loop.

        Args:
            project_uuid: Target project UUID.
            stale_threshold_days: Days since created_at to consider stale.

        Returns:
            Number of affected trajectories.
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
                "Bulk decay: %d trajectories marked STALE in project %s (threshold=%d days)",
                affected, project_uuid, stale_threshold_days
            )
        return affected

    # ===================================================================
    # 2. CENTRALITY (normalized in-degree + Super-Nodes)
    # ===================================================================

    def compute_centrality(self, node_id: int) -> float:
        """Calculates normalized centrality of a node.

        Formula: min(in_degree / CENTRALITY_MAX_IN_DEGREE, 1.0)

        A node with in_degree >= 10 is a "Super-Node": stable core code
        that many files depend on. Receives maximum centrality (1.0),
        protecting it against low recency penalty in Hybrid Search.

        Args:
            node_id: Node ID in nodes table.

        Returns:
            Float in interval [0.0, 1.0].
        """
        with self._conn.read() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS in_deg FROM edges WHERE target_id = ?",
                (node_id,)
            ).fetchone()

        in_degree = row["in_deg"] if row else 0
        centrality = min(in_degree / self.CENTRALITY_MAX_IN_DEGREE, 1.0)

        logger.debug(
            "Centrality node ID=%d: in_degree=%d, score=%.4f%s",
            node_id, in_degree, centrality,
            " [SUPER-NODE]" if centrality >= 1.0 else ""
        )
        return centrality

    def compute_centrality_batch(self, node_ids: list[int]) -> dict[int, float]:
        """Calculates centrality for multiple nodes in a single SQL query.

        Args:
            node_ids: List of node IDs.

        Returns:
            Dict mapping node_id → normalized centrality [0.0, 1.0].
            Nodes without incoming edges return 0.0.
        """
        if not node_ids:
            return {}

        # Initializes all with 0.0 (in case they have no edges)
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
            logger.debug("Super-Nodes detected (batch): %s", super_nodes)

        return result

    # ===================================================================
    # 3. RECENCY SCORE (Exponential Decay)
    # ===================================================================

    def compute_recency_score(self, node_id: int) -> float:
        """Calculates recency score via exponential decay.

        Formula: max(e^(-λ × t), RECENCY_MIN_SCORE)
        Where:
            λ = ln(2) / 7 ≈ 0.09902
            t = days since nodes.last_commit_at

        If last_commit_at is NULL, returns RECENCY_MIN_SCORE (0.01).

        Args:
            node_id: Node ID.

        Returns:
            Float in interval [0.01, 1.0].
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
        """Calculates recency in batch for multiple nodes.

        Args:
            node_ids: List of node IDs.

        Returns:
            Dict mapping node_id → recency score [0.01, 1.0].
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

        # Ensures not found nodes return minimum score
        for nid in node_ids:
            if nid not in result:
                result[nid] = self.RECENCY_MIN_SCORE

        return result

    def _calculate_decay(self, last_commit_at: str) -> float:
        """Applies exponential decay formula.

        Args:
            last_commit_at: ISO timestamp of last commit (e.g. '2026-05-01 12:00:00').

        Returns:
            Score in interval [RECENCY_MIN_SCORE, 1.0].
        """
        try:
            commit_dt = datetime.fromisoformat(last_commit_at)
            now = datetime.utcnow()
            delta_days = max((now - commit_dt).total_seconds() / 86400, 0.0)
        except (ValueError, TypeError):
            logger.warning("invalid last_commit_at: '%s'. Using minimum score.", last_commit_at)
            return self.RECENCY_MIN_SCORE

        # e^(-λ × t) with floor at MIN_SCORE
        score = math.exp(-self.RECENCY_LAMBDA * delta_days)
        return max(score, self.RECENCY_MIN_SCORE)

    # ===================================================================
    # 4. FTS5 — Text search with normalized BM25
    # ===================================================================

    def fts_search(
        self,
        query: str,
        project_uuid: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Text search via FTS5 with BM25 normalized to [0, 1].

        SQLite returns bm25() as negative value (more negative = more relevant).
        We normalize to [0, 1] using:  1.0 - (rank / min_rank)
        where min_rank is the most negative (most relevant) value of the batch.

        Args:
            query: Search text. Special characters are escaped.
            project_uuid: Optional filter by project (Strict Scoping).
            node_type: Targeted filter (FACT, SKILL, INSIGHT, TRAJECTORY, PATCH).
            limit: Maximum results.

        Returns:
            List of dicts with node fields + normalized 'bm25_score' [0, 1].
            Sorted from most relevant to least relevant.
        """
        # Escapes quotes in query to prevent FTS5 injection
        safe_query = query.replace('"', '""')

        # Assembles the SQL query dynamically according to the filters
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

        # Normalizes BM25: the most negative rank becomes 1.0 and the least negative becomes ~0.0
        min_rank = min(r["rank"] for r in results)  # most negative value
        for r in results:
            if min_rank < 0:
                r["bm25_score"] = round(r["rank"] / min_rank, 4)
            else:
                r["bm25_score"] = 1.0
            del r["rank"]  # Removes internal SQLite field

        return results

    def fts_rebuild(self) -> None:
        """Rebuilds the complete FTS5 index.

        Use after massive ingestion (concierge mine) to optimize performance.
        """
        def _do(conn: Any) -> None:
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

        self._conn.write(_do)
        logger.info("FTS5 index rebuilt successfully.")

    # ===================================================================
    # 5. WEIGHTED HYBRID SEARCH (Hybrid Search v4)
    # ===================================================================

    def hybrid_search_score(
        self,
        node_id: int,
        vector_score: float,
        fts_score: float,
    ) -> dict:
        """Calculates final combined score for a node in Hybrid Search v4.

        Formula (Architecture v3.8):
            score = (0.50 × vector)
                  + (0.25 × normalized_fts5)
                  + (0.25 × max(recency, centrality))

        The third component uses max(recency, centrality) to protect
        stable "core code": if a node is old (low recency) but has
        high centrality (many dependents), centrality prevails.

        Args:
            node_id: Node ID.
            vector_score: Vector similarity score [0, 1] (from pluggable backend).
            fts_score: Normalized BM25 score [0, 1] (from fts_search).

        Returns:
            Dict with complete breakdown:
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
        # Calculates individual components
        recency = self.compute_recency_score(node_id)
        centrality = self.compute_centrality(node_id)

        # max(recency, centrality): protects stable Super-Nodes
        recency_centrality = max(recency, centrality)

        # Weighted final score
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
        """Calculates hybrid scores in batch and returns sorted by relevance.

        Optimized: does centrality and recency queries in batch
        instead of N individual queries.

        Args:
            candidates: List of dicts, each containing:
                - "node_id" (int)
                - "vector_score" (float) — from vector backend
                - "fts_score" (float) — from fts_search (normalized BM25)

        Returns:
            List of dicts with score_final and breakdown, sorted DESC by score.
        """
        if not candidates:
            return []

        node_ids = [c["node_id"] for c in candidates]

        # Batch queries — 2 SQL queries instead of 2N
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

        # Sorts by score_final DESC (most relevant first)
        results.sort(key=lambda x: x["score_final"], reverse=True)

        logger.debug(
            "Hybrid batch: %d candidates processed. Top score=%.4f",
            len(results), results[0]["score_final"] if results else 0.0
        )
        return results

    # ===================================================================
    # 6. RECURSIVE QUERIES (CTE) with loop protection
    # ===================================================================

    def get_dependency_tree(
        self, start_node_id: int, max_depth: int = 10
    ) -> list[dict]:
        """Dependency tree: source → target (who this node depends on).

        CTE with depth limit to prevent infinite loops.

        Args:
            start_node_id: Root node.
            max_depth: Maximum depth (default: 10).

        Returns:
            List of dicts: id, label, node_type, depth.
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
        """Reverse dependency tree: who depends ON THIS node (target → source).

        Args:
            start_node_id: Target node.
            max_depth: Maximum depth.

        Returns:
            List of dicts: id, label, node_type, depth.
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
    # 7. PROJECT STATISTICS
    # ===================================================================

    def get_project_stats(self, project_uuid: str) -> dict:
        """Complete statistics of a project via aggregated SQL.

        Returns:
            Dict with: nodes, nodes_by_type, edges, commits,
            last_commit_at, trajectories, trajectories_active.
        """
        with self._conn.read() as conn:
            # Total node count
            nodes_total = conn.execute(
                "SELECT COUNT(*) AS c FROM nodes WHERE project_uuid = ?",
                (project_uuid,)
            ).fetchone()["c"]

            # Count by node type
            type_rows = conn.execute(
                """SELECT node_type, COUNT(*) AS c FROM nodes
                   WHERE project_uuid = ? GROUP BY node_type""",
                (project_uuid,)
            ).fetchall()
            nodes_by_type = {r["node_type"]: r["c"] for r in type_rows}

            # Project edges
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

            # Trajectories
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
        """Returns the phase of the project's most recent commit.

        Returns:
            String of phase (e.g. 'build') or None if no commits.
        """
        with self._conn.read() as conn:
            row = conn.execute(
                """SELECT phase FROM commit_log
                   WHERE project_uuid = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (project_uuid,)
            ).fetchone()
        return row["phase"] if row else None
