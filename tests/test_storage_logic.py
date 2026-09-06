"""
tests/test_storage_logic.py — Unit tests for GraphLogic (storage/logic.py)

Covers the 7 pillars of GraphLogic:
    1. Trajectory Decay (state machine transitions)
    2. Centrality (normalized in-degree + Super-Node detection)
    3. Recency Score (exponential decay with half-life)
    4. FTS5 search (BM25 normalization)
    5. Hybrid Search (weighted scoring v4)
    6. Recursive CTE dependency trees
    7. Project statistics

Strategy:
    Uses a lightweight in-memory SQLite database with the real schema
    instead of mocking the ConnectionManager, so that SQL queries
    are actually exercised. The helper class ``InMemoryConnManager``
    implements the same ``read()`` / ``write()`` API that GraphLogic
    depends on, backed by ``:memory:``.
"""

from __future__ import annotations

import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Generator

import pytest

from storage.logic import (
    GraphLogic,
    InvalidTransitionError,
    TrajectoryNotFoundError,
)


# ---------------------------------------------------------------------------
# Lightweight in-memory ConnectionManager stub
# ---------------------------------------------------------------------------

class InMemoryConnManager:
    """Minimal drop-in replacement for ``ConnectionManager`` using ``:memory:``.

    Provides the ``read()`` context manager and ``write(fn, *args)`` method
    that GraphLogic depends on, all backed by a single in-memory connection.
    """

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._bootstrap_schema()

    # --- public API matching ConnectionManager ---

    @contextmanager
    def read(self) -> Generator[sqlite3.Connection, None, None]:
        yield self._conn

    def write(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        result = fn(self._conn, *args, **kwargs)
        self._conn.commit()
        return result

    def close(self) -> None:
        self._conn.close()

    # --- schema bootstrap (minimal subset needed by GraphLogic) ---

    def _bootstrap_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                uuid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                root_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_uuid TEXT NOT NULL,
                label TEXT NOT NULL,
                node_type TEXT NOT NULL DEFAULT 'FACT',
                body TEXT,
                last_commit_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (project_uuid) REFERENCES projects(uuid)
            );

            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation TEXT DEFAULT 'DEPENDS_ON',
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );

            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_uuid TEXT NOT NULL,
                label TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (project_uuid) REFERENCES projects(uuid)
            );

            CREATE TABLE IF NOT EXISTS commit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_uuid TEXT NOT NULL,
                sha TEXT,
                phase TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (project_uuid) REFERENCES projects(uuid)
            );

            -- FTS5 virtual table for text search
            CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                label, body, content=nodes, content_rowid=id
            );

            -- FTS5 sync triggers
            CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(rowid, label, body)
                VALUES (new.id, new.label, new.body);
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, body)
                VALUES ('delete', old.id, old.label, old.body);
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, body)
                VALUES ('delete', old.id, old.label, old.body);
                INSERT INTO nodes_fts(rowid, label, body)
                VALUES (new.id, new.label, new.body);
            END;
        """)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_UUID = "test-project-0001"


@pytest.fixture()
def conn_manager() -> InMemoryConnManager:
    """Creates a fresh in-memory database per test."""
    cm = InMemoryConnManager()
    # Seed a default project
    cm._conn.execute(
        "INSERT INTO projects (uuid, name) VALUES (?, ?)",
        (PROJECT_UUID, "TestProject"),
    )
    cm._conn.commit()
    yield cm
    cm.close()


@pytest.fixture()
def logic(conn_manager: InMemoryConnManager) -> GraphLogic:
    """GraphLogic instance wired to the in-memory database."""
    return GraphLogic(conn_manager)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_node(
    cm: InMemoryConnManager,
    label: str = "module.py",
    node_type: str = "FACT",
    body: str = "",
    last_commit_at: str | None = None,
    project_uuid: str = PROJECT_UUID,
) -> int:
    """Inserts a node and returns its ID."""
    cursor = cm._conn.execute(
        """INSERT INTO nodes (project_uuid, label, node_type, body, last_commit_at)
           VALUES (?, ?, ?, ?, ?)""",
        (project_uuid, label, node_type, body, last_commit_at),
    )
    cm._conn.commit()
    return cursor.lastrowid


def _insert_edge(
    cm: InMemoryConnManager, source_id: int, target_id: int
) -> None:
    """Inserts a directed edge source → target."""
    cm._conn.execute(
        "INSERT INTO edges (source_id, target_id) VALUES (?, ?)",
        (source_id, target_id),
    )
    cm._conn.commit()


def _insert_trajectory(
    cm: InMemoryConnManager,
    status: str = "ACTIVE",
    label: str = "traj-1",
    project_uuid: str = PROJECT_UUID,
    created_at: str | None = None,
) -> int:
    """Inserts a trajectory and returns its ID."""
    sql = """INSERT INTO trajectories (project_uuid, label, status, created_at)
             VALUES (?, ?, ?, COALESCE(?, datetime('now')))"""
    cursor = cm._conn.execute(sql, (project_uuid, label, status, created_at))
    cm._conn.commit()
    return cursor.lastrowid


# ===================================================================
# 1. TRAJECTORY DECAY — State machine tests
# ===================================================================

class TestTrajectoryDecay:
    """Tests for ``decay_trajectory`` and ``bulk_decay_stale_trajectories``."""

    def test_active_to_stale(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        tid = _insert_trajectory(conn_manager, status="ACTIVE")
        assert logic.decay_trajectory(tid, "STALE") is True

    def test_active_to_archived(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        tid = _insert_trajectory(conn_manager, status="ACTIVE")
        assert logic.decay_trajectory(tid, "ARCHIVED") is True

    def test_stale_to_active(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        """Re-activation: STALE → ACTIVE is allowed."""
        tid = _insert_trajectory(conn_manager, status="STALE")
        assert logic.decay_trajectory(tid, "ACTIVE") is True

    def test_stale_to_archived(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        tid = _insert_trajectory(conn_manager, status="STALE")
        assert logic.decay_trajectory(tid, "ARCHIVED") is True

    def test_archived_is_terminal(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        """ARCHIVED is a terminal state — no transitions allowed."""
        tid = _insert_trajectory(conn_manager, status="ARCHIVED")
        with pytest.raises(InvalidTransitionError):
            logic.decay_trajectory(tid, "ACTIVE")

    def test_archived_to_stale_blocked(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        tid = _insert_trajectory(conn_manager, status="ARCHIVED")
        with pytest.raises(InvalidTransitionError):
            logic.decay_trajectory(tid, "STALE")

    def test_invalid_status_raises_value_error(self, logic: GraphLogic, conn_manager: InMemoryConnManager) -> None:
        tid = _insert_trajectory(conn_manager, status="ACTIVE")
        with pytest.raises(ValueError, match="Invalid status"):
            logic.decay_trajectory(tid, "DELETED")

    def test_nonexistent_trajectory_raises(self, logic: GraphLogic) -> None:
        with pytest.raises(TrajectoryNotFoundError):
            logic.decay_trajectory(99999, "STALE")

    def test_bulk_decay_marks_old_trajectories_stale(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Trajectories older than threshold should be marked STALE."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        recent_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        _insert_trajectory(conn_manager, status="ACTIVE", label="old-1", created_at=old_date)
        _insert_trajectory(conn_manager, status="ACTIVE", label="old-2", created_at=old_date)
        _insert_trajectory(conn_manager, status="ACTIVE", label="recent", created_at=recent_date)

        affected = logic.bulk_decay_stale_trajectories(PROJECT_UUID, stale_threshold_days=30)
        assert affected == 2

    def test_bulk_decay_ignores_already_stale(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Already-STALE trajectories should not be affected."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        _insert_trajectory(conn_manager, status="STALE", label="already-stale", created_at=old_date)

        affected = logic.bulk_decay_stale_trajectories(PROJECT_UUID, stale_threshold_days=30)
        assert affected == 0

    def test_bulk_decay_respects_project_scope(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Only trajectories from the specified project should be affected."""
        other_uuid = "other-project-0002"
        conn_manager._conn.execute(
            "INSERT INTO projects (uuid, name) VALUES (?, ?)",
            (other_uuid, "OtherProject"),
        )
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        _insert_trajectory(conn_manager, status="ACTIVE", label="other", created_at=old_date, project_uuid=other_uuid)
        _insert_trajectory(conn_manager, status="ACTIVE", label="mine", created_at=old_date)
        conn_manager._conn.commit()

        affected = logic.bulk_decay_stale_trajectories(PROJECT_UUID, stale_threshold_days=30)
        assert affected == 1  # Only "mine", not "other"


# ===================================================================
# 2. CENTRALITY — Normalized in-degree + Super-Node detection
# ===================================================================

class TestCentrality:
    """Tests for ``compute_centrality`` and ``compute_centrality_batch``."""

    def test_zero_edges_gives_zero_centrality(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        nid = _insert_node(conn_manager, label="isolated.py")
        assert logic.compute_centrality(nid) == 0.0

    def test_one_edge_gives_0_1(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        target = _insert_node(conn_manager, label="target.py")
        source = _insert_node(conn_manager, label="source.py")
        _insert_edge(conn_manager, source, target)
        assert logic.compute_centrality(target) == pytest.approx(0.1)

    def test_five_edges_gives_0_5(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        target = _insert_node(conn_manager, label="target.py")
        for i in range(5):
            src = _insert_node(conn_manager, label=f"dep_{i}.py")
            _insert_edge(conn_manager, src, target)
        assert logic.compute_centrality(target) == pytest.approx(0.5)

    def test_super_node_at_10_edges(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A node with 10+ incoming edges is a Super-Node (centrality = 1.0)."""
        target = _insert_node(conn_manager, label="core_lib.py")
        for i in range(10):
            src = _insert_node(conn_manager, label=f"client_{i}.py")
            _insert_edge(conn_manager, src, target)
        assert logic.compute_centrality(target) == 1.0

    def test_super_node_capped_at_1_0(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Centrality must never exceed 1.0 even with 20+ edges."""
        target = _insert_node(conn_manager, label="mega_core.py")
        for i in range(20):
            src = _insert_node(conn_manager, label=f"user_{i}.py")
            _insert_edge(conn_manager, src, target)
        assert logic.compute_centrality(target) == 1.0

    def test_batch_centrality_empty_list(self, logic: GraphLogic) -> None:
        assert logic.compute_centrality_batch([]) == {}

    def test_batch_centrality_mixed(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Batch should return correct centrality for nodes with varying in-degree."""
        isolated = _insert_node(conn_manager, label="iso.py")
        popular = _insert_node(conn_manager, label="popular.py")
        for i in range(5):
            src = _insert_node(conn_manager, label=f"b_dep_{i}.py")
            _insert_edge(conn_manager, src, popular)

        result = logic.compute_centrality_batch([isolated, popular])
        assert result[isolated] == pytest.approx(0.0)
        assert result[popular] == pytest.approx(0.5)


# ===================================================================
# 3. RECENCY SCORE — Exponential decay
# ===================================================================

class TestRecencyScore:
    """Tests for ``compute_recency_score``, ``compute_recency_batch``, ``_calculate_decay``."""

    def test_node_with_no_commit_returns_min(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Nodes without last_commit_at should return RECENCY_MIN_SCORE (0.01)."""
        nid = _insert_node(conn_manager, label="no_commit.py", last_commit_at=None)
        assert logic.compute_recency_score(nid) == pytest.approx(0.01)

    def test_node_committed_now_returns_near_1(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A node committed just now should have recency very close to 1.0."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="fresh.py", last_commit_at=now)
        score = logic.compute_recency_score(nid)
        assert score > 0.99

    def test_half_life_at_7_days(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """After exactly 7 days, recency should be ≈ 0.50."""
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="week_old.py", last_commit_at=seven_days_ago)
        score = logic.compute_recency_score(nid)
        assert score == pytest.approx(0.5, abs=0.02)

    def test_14_days_gives_quarter(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """After 14 days (2 half-lives), recency should be ≈ 0.25."""
        two_weeks_ago = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="old.py", last_commit_at=two_weeks_ago)
        score = logic.compute_recency_score(nid)
        assert score == pytest.approx(0.25, abs=0.02)

    def test_very_old_node_has_min_score(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A node 365 days old should be at the floor RECENCY_MIN_SCORE."""
        ancient = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="ancient.py", last_commit_at=ancient)
        score = logic.compute_recency_score(nid)
        assert score == pytest.approx(0.01, abs=0.001)

    def test_nonexistent_node_returns_min(
        self, logic: GraphLogic
    ) -> None:
        """Querying a non-existent node should return RECENCY_MIN_SCORE."""
        score = logic.compute_recency_score(99999)
        assert score == pytest.approx(0.01)

    def test_calculate_decay_invalid_timestamp(self, logic: GraphLogic) -> None:
        """Invalid timestamp strings should fall back to RECENCY_MIN_SCORE."""
        assert logic._calculate_decay("not-a-date") == pytest.approx(0.01)

    def test_batch_recency_empty(self, logic: GraphLogic) -> None:
        assert logic.compute_recency_batch([]) == {}

    def test_batch_recency_mixed(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        old = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        fresh_id = _insert_node(conn_manager, label="fresh_b.py", last_commit_at=now)
        old_id = _insert_node(conn_manager, label="old_b.py", last_commit_at=old)
        none_id = _insert_node(conn_manager, label="none_b.py", last_commit_at=None)

        result = logic.compute_recency_batch([fresh_id, old_id, none_id])
        assert result[fresh_id] > 0.99
        assert result[old_id] < 0.15
        assert result[none_id] == pytest.approx(0.01)

    def test_batch_recency_missing_nodes(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Node IDs not found in the DB should receive RECENCY_MIN_SCORE."""
        real_id = _insert_node(conn_manager, label="real.py",
                               last_commit_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        result = logic.compute_recency_batch([real_id, 88888])
        assert 88888 in result
        assert result[88888] == pytest.approx(0.01)


# ===================================================================
# 4. FTS5 SEARCH — BM25 normalization
# ===================================================================

class TestFTS5Search:
    """Tests for ``fts_search`` and ``fts_rebuild``."""

    def test_fts_basic_match(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        _insert_node(conn_manager, label="auth_handler", body="handles authentication tokens")
        _insert_node(conn_manager, label="payment_gateway", body="processes credit card payments")

        results = logic.fts_search("authentication")
        assert len(results) >= 1
        assert any("auth" in r["label"] for r in results)

    def test_fts_no_results(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        _insert_node(conn_manager, label="util", body="helper functions")
        results = logic.fts_search("zyxwvutsrqp")  # nonsense query
        assert results == []

    def test_fts_bm25_normalization(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """All returned bm25_score values must be in [0, 1]."""
        for i in range(5):
            _insert_node(conn_manager, label=f"module_{i}", body=f"database query optimizer {i}")

        results = logic.fts_search("database")
        assert len(results) > 0
        for r in results:
            assert 0.0 <= r["bm25_score"] <= 1.0
            assert "rank" not in r  # internal field should be removed

    def test_fts_project_scope_filter(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Results should respect project_uuid filter."""
        other_uuid = "other-project-fts"
        conn_manager._conn.execute(
            "INSERT INTO projects (uuid, name) VALUES (?, ?)",
            (other_uuid, "OtherFTS"),
        )
        _insert_node(conn_manager, label="shared_lib", body="shared library code", project_uuid=PROJECT_UUID)
        _insert_node(conn_manager, label="other_lib", body="shared library other", project_uuid=other_uuid)

        results = logic.fts_search("shared", project_uuid=PROJECT_UUID)
        for r in results:
            assert r["project_uuid"] == PROJECT_UUID

    def test_fts_node_type_filter(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        _insert_node(conn_manager, label="skill_node", body="machine learning skill", node_type="SKILL")
        _insert_node(conn_manager, label="fact_node", body="machine learning fact", node_type="FACT")

        results = logic.fts_search("machine learning", node_type="SKILL")
        assert all(r["node_type"] == "SKILL" for r in results)

    def test_fts_rebuild_does_not_raise(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        _insert_node(conn_manager, label="rebuild_test", body="content for rebuild")
        logic.fts_rebuild()  # Should not raise

    def test_fts_quote_injection_safe(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Queries containing double quotes should not cause SQL/FTS5 injection."""
        _insert_node(conn_manager, label="safe_node", body="safe content")
        # Should not raise, even with quotes in the query
        results = logic.fts_search('test "injection" attempt')
        assert isinstance(results, list)


# ===================================================================
# 5. HYBRID SEARCH — Weighted scoring v4
# ===================================================================

class TestHybridSearch:
    """Tests for ``hybrid_search_score`` and ``hybrid_search_score_batch``."""

    def test_perfect_vector_score(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Node with vector=1.0, fts=0.0, no edges, recent commit → dominated by vector weight."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="perfect_vec.py", last_commit_at=now)

        result = logic.hybrid_search_score(nid, vector_score=1.0, fts_score=0.0)
        # 0.50×1.0 + 0.25×0.0 + 0.25×max(~1.0, 0.0) ≈ 0.75
        assert result["score_final"] == pytest.approx(0.75, abs=0.02)
        assert result["is_super_node"] is False

    def test_super_node_protection(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A Super-Node with old commit should still score high via centrality."""
        ancient = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        target = _insert_node(conn_manager, label="core_super.py", last_commit_at=ancient)
        for i in range(12):
            src = _insert_node(conn_manager, label=f"dep_super_{i}.py")
            _insert_edge(conn_manager, src, target)

        result = logic.hybrid_search_score(target, vector_score=0.8, fts_score=0.5)
        # 0.50×0.8 + 0.25×0.5 + 0.25×max(0.01, 1.0) = 0.40 + 0.125 + 0.25 = 0.775
        assert result["score_final"] == pytest.approx(0.775, abs=0.02)
        assert result["is_super_node"] is True

    def test_score_breakdown_keys(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        nid = _insert_node(conn_manager, label="keys.py")
        result = logic.hybrid_search_score(nid, vector_score=0.5, fts_score=0.5)

        assert "node_id" in result
        assert "score_final" in result
        assert "score_breakdown" in result
        assert "is_super_node" in result

        breakdown = result["score_breakdown"]
        assert "vetorial" in breakdown
        assert "frequencia" in breakdown
        assert "recencia" in breakdown
        assert "centralidade" in breakdown

    def test_all_zeros(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """All zero inputs still get a non-zero score from recency floor."""
        nid = _insert_node(conn_manager, label="zero.py")
        result = logic.hybrid_search_score(nid, vector_score=0.0, fts_score=0.0)
        # 0.25 × max(0.01, 0.0) = 0.0025 minimum
        assert result["score_final"] >= 0.0025

    def test_batch_empty(self, logic: GraphLogic) -> None:
        assert logic.hybrid_search_score_batch([]) == []

    def test_batch_sorted_descending(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Batch results must be sorted by score_final descending."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        high_id = _insert_node(conn_manager, label="high.py", last_commit_at=now)
        low_id = _insert_node(conn_manager, label="low.py", last_commit_at=now)

        candidates = [
            {"node_id": low_id, "vector_score": 0.1, "fts_score": 0.1},
            {"node_id": high_id, "vector_score": 0.9, "fts_score": 0.9},
        ]
        results = logic.hybrid_search_score_batch(candidates)

        assert len(results) == 2
        assert results[0]["score_final"] >= results[1]["score_final"]
        assert results[0]["node_id"] == high_id

    def test_batch_uses_batch_queries(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Batch method should produce same scores as individual method."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="batch_vs_single.py", last_commit_at=now)

        individual = logic.hybrid_search_score(nid, vector_score=0.7, fts_score=0.3)
        batch = logic.hybrid_search_score_batch([
            {"node_id": nid, "vector_score": 0.7, "fts_score": 0.3}
        ])

        assert batch[0]["score_final"] == pytest.approx(individual["score_final"], abs=0.001)


# ===================================================================
# 6. DEPENDENCY TREES — Recursive CTE
# ===================================================================

class TestDependencyTrees:
    """Tests for ``get_dependency_tree`` and ``get_reverse_dependency_tree``."""

    def test_single_node_tree(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A node with no edges returns only itself at depth 0."""
        nid = _insert_node(conn_manager, label="lone.py")
        tree = logic.get_dependency_tree(nid)
        assert len(tree) == 1
        assert tree[0]["id"] == nid
        assert tree[0]["depth"] == 0

    def test_linear_chain(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """A → B → C should produce tree with depth 0, 1, 2."""
        a = _insert_node(conn_manager, label="a.py")
        b = _insert_node(conn_manager, label="b.py")
        c = _insert_node(conn_manager, label="c.py")
        _insert_edge(conn_manager, a, b)
        _insert_edge(conn_manager, b, c)

        tree = logic.get_dependency_tree(a)
        depths = {r["label"]: r["depth"] for r in tree}
        assert depths["a.py"] == 0
        assert depths["b.py"] == 1
        assert depths["c.py"] == 2

    def test_max_depth_limit(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Depth limit should prevent infinite traversal."""
        nodes = []
        for i in range(15):
            nodes.append(_insert_node(conn_manager, label=f"chain_{i}.py"))
        for i in range(14):
            _insert_edge(conn_manager, nodes[i], nodes[i + 1])

        tree = logic.get_dependency_tree(nodes[0], max_depth=3)
        max_depth = max(r["depth"] for r in tree)
        assert max_depth <= 3

    def test_reverse_dependency_tree(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        """Reverse tree: who depends on this node."""
        core = _insert_node(conn_manager, label="core.py")
        client1 = _insert_node(conn_manager, label="client1.py")
        client2 = _insert_node(conn_manager, label="client2.py")
        _insert_edge(conn_manager, client1, core)
        _insert_edge(conn_manager, client2, core)

        rev_tree = logic.get_reverse_dependency_tree(core)
        labels = {r["label"] for r in rev_tree}
        assert "core.py" in labels
        assert "client1.py" in labels
        assert "client2.py" in labels


# ===================================================================
# 7. PROJECT STATISTICS
# ===================================================================

class TestProjectStats:
    """Tests for ``get_project_stats`` and ``get_last_commit_phase``."""

    def test_empty_project_stats(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        stats = logic.get_project_stats(PROJECT_UUID)
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["commits"] == 0
        assert stats["trajectories"] == 0
        assert stats["trajectories_active"] == 0

    def test_populated_project_stats(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        n1 = _insert_node(conn_manager, label="a.py", node_type="FACT")
        n2 = _insert_node(conn_manager, label="b.py", node_type="SKILL")
        n3 = _insert_node(conn_manager, label="c.py", node_type="FACT")
        _insert_edge(conn_manager, n1, n2)
        _insert_trajectory(conn_manager, status="ACTIVE")
        _insert_trajectory(conn_manager, status="ARCHIVED")

        conn_manager._conn.execute(
            "INSERT INTO commit_log (project_uuid, sha, phase) VALUES (?, ?, ?)",
            (PROJECT_UUID, "abc123", "build"),
        )
        conn_manager._conn.commit()

        stats = logic.get_project_stats(PROJECT_UUID)
        assert stats["nodes"] == 3
        assert stats["nodes_by_type"]["FACT"] == 2
        assert stats["nodes_by_type"]["SKILL"] == 1
        assert stats["edges"] == 1
        assert stats["commits"] == 1
        assert stats["trajectories"] == 2
        assert stats["trajectories_active"] == 1

    def test_last_commit_phase_returns_latest(
        self, logic: GraphLogic, conn_manager: InMemoryConnManager
    ) -> None:
        conn_manager._conn.execute(
            "INSERT INTO commit_log (project_uuid, sha, phase, created_at) VALUES (?, ?, ?, ?)",
            (PROJECT_UUID, "sha1", "analyze", "2026-01-01 00:00:00"),
        )
        conn_manager._conn.execute(
            "INSERT INTO commit_log (project_uuid, sha, phase, created_at) VALUES (?, ?, ?, ?)",
            (PROJECT_UUID, "sha2", "build", "2026-06-01 00:00:00"),
        )
        conn_manager._conn.commit()

        phase = logic.get_last_commit_phase(PROJECT_UUID)
        assert phase == "build"

    def test_last_commit_phase_no_commits(
        self, logic: GraphLogic
    ) -> None:
        phase = logic.get_last_commit_phase("nonexistent-project")
        assert phase is None


# ===================================================================
# 8. CONFIG OVERRIDE — Custom weights
# ===================================================================

class TestConfigOverride:
    """Tests that GraphLogic respects ConciergeConfig overrides."""

    def test_custom_weights_affect_hybrid_score(
        self, conn_manager: InMemoryConnManager
    ) -> None:
        """Custom weights should change the final score calculation."""
        from unittest.mock import MagicMock

        config = MagicMock()
        config.weight_vector = 0.80
        config.weight_fts5 = 0.10
        config.weight_recency_centrality = 0.10
        config.centrality_max_in_degree = 10
        config.recency_half_life_days = 7.0
        config.recency_lambda = math.log(2) / 7.0
        config.recency_min_score = 0.01

        logic = GraphLogic(conn_manager, config=config)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        nid = _insert_node(conn_manager, label="cfg_test.py", last_commit_at=now)

        result = logic.hybrid_search_score(nid, vector_score=1.0, fts_score=0.0)
        # 0.80×1.0 + 0.10×0.0 + 0.10×max(~1.0, 0.0) ≈ 0.90
        assert result["score_final"] == pytest.approx(0.90, abs=0.02)

    def test_custom_centrality_max(
        self, conn_manager: InMemoryConnManager
    ) -> None:
        """Custom centrality_max_in_degree=5 should make 5 edges = Super-Node."""
        from unittest.mock import MagicMock

        config = MagicMock()
        config.weight_vector = 0.50
        config.weight_fts5 = 0.25
        config.weight_recency_centrality = 0.25
        config.centrality_max_in_degree = 5
        config.recency_half_life_days = 7.0
        config.recency_lambda = math.log(2) / 7.0
        config.recency_min_score = 0.01

        logic = GraphLogic(conn_manager, config=config)
        target = _insert_node(conn_manager, label="custom_super.py")
        for i in range(5):
            src = _insert_node(conn_manager, label=f"c_dep_{i}.py")
            _insert_edge(conn_manager, src, target)

        assert logic.compute_centrality(target) == 1.0


# ===================================================================
# 9. MATHEMATICAL PROPERTIES
# ===================================================================

class TestMathematicalProperties:
    """Validates core mathematical invariants of the scoring formulas."""

    def test_recency_lambda_matches_half_life(self) -> None:
        """λ = ln(2) / half_life should produce exactly 0.5 at t = half_life."""
        half_life = 7.0
        lam = math.log(2) / half_life
        score_at_half_life = math.exp(-lam * half_life)
        assert score_at_half_life == pytest.approx(0.5, abs=1e-10)

    def test_recency_is_monotonically_decreasing(self) -> None:
        """Recency score must decrease as days increase."""
        lam = math.log(2) / 7.0
        previous = 1.0
        for days in range(1, 100):
            score = math.exp(-lam * days)
            assert score < previous
            previous = score

    def test_centrality_is_linear_up_to_max(self) -> None:
        """Centrality must be linear: centrality(n) = n/10 for n <= 10."""
        max_degree = 10
        for n in range(0, max_degree + 1):
            expected = n / max_degree
            actual = min(n / max_degree, 1.0)
            assert actual == pytest.approx(expected)

    def test_hybrid_weights_sum_to_1(self) -> None:
        """The three hybrid search weights must sum to 1.0."""
        total = GraphLogic.WEIGHT_VECTOR + GraphLogic.WEIGHT_FTS5 + GraphLogic.WEIGHT_RECENCY_CENTRALITY
        assert total == pytest.approx(1.0)

    def test_hybrid_score_bounded_0_to_1(self) -> None:
        """If all inputs are in [0,1], the final score must also be in [0,1]."""
        for v in [0.0, 0.5, 1.0]:
            for f in [0.0, 0.5, 1.0]:
                for rc in [0.0, 0.5, 1.0]:
                    score = (
                        GraphLogic.WEIGHT_VECTOR * v
                        + GraphLogic.WEIGHT_FTS5 * f
                        + GraphLogic.WEIGHT_RECENCY_CENTRALITY * rc
                    )
                    assert 0.0 <= score <= 1.0, f"Out of bounds: v={v}, f={f}, rc={rc} → {score}"
