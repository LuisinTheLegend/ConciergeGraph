"""
storage/store.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Unified Facade that composes:
    - ConnectionManager (connection.py) -> WAL, busy_timeout, serialized queue
    - SchemaManager (schema.py)        -> DDL, CHECK constraints, FTS5 triggers
    - GraphLogic (logic.py)            -> decay, centrality, recency, FTS5

API consistent with MCP v3.8 Tools:
    concierge_resume   -> get_project / get_project_stats
    concierge_commit   -> create_commit + touch_node_commit
    concierge_search   -> fts_search / hybrid_search_score_batch
    concierge_mine     -> create_node / find_node_by_hash
    concierge_register -> create_project
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

from storage.connection import ConnectionManager

if TYPE_CHECKING:
    from core.config import ConciergeConfig
from storage.schema import SchemaManager, VALID_NODE_TYPES, VALID_PRIVACY_LEVELS, VALID_STATUSES
from storage.logic import GraphLogic, TrajectoryNotFoundError, InvalidTransitionError

logger = logging.getLogger("grafo-concierge.store")


# ---------------------------------------------------------------------------
# Facade exceptions
# ---------------------------------------------------------------------------

class ProjectNotFoundError(Exception):
    """Project not found by UUID or folder_name."""

class NodeNotFoundError(Exception):
    """Node not found by the provided ID."""

class CommitValidationError(Exception):
    """Required fields missing in the commit."""


# ---------------------------------------------------------------------------
# SqliteStore — Unified Facade
# ---------------------------------------------------------------------------

class SqliteStore:
    """SQLite persistence facade for Grafo Concierge v3.8.

    In __init__, the schema is verified and applied automatically.
    The end user only interacts with this class.

    Args:
        db_path: Path to the .db (default: <project_root>/data/concierge.db).
    """

    def __init__(self, db_path: str | None = None, config: Optional["ConciergeConfig"] = None) -> None:
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.resolve() / "data" / "concierge.db")
        resolved = str(Path(db_path).expanduser().absolute())
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)

        # 1. Schema FIRST (applies DDL + FTS5 + triggers before any persistent connection)
        #    The temporary connection is opened and closed here, without competing with the queue.
        self._boot_schema(resolved)

        # 2. Connections (WAL + busy_timeout + serialized queue) - starts AFTER schema is ready
        self._conn_mgr = ConnectionManager(resolved)
        self._conn_mgr.start()

        # 3. Intelligence (centrality, recency, decay, FTS5, CTE)
        #    Now passes ConciergeConfig so that weights obey user config
        self._logic = GraphLogic(self._conn_mgr, config=config)

        logger.info("SqliteStore initialized: %s", resolved)

    def _boot_schema(self, db_path: str) -> None:
        """Opens temporary connection to apply the schema idempotently."""
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            mgr = SchemaManager(conn)
            mgr.apply_full_schema()

            # Verification log
            tables = mgr.verify_tables_exist()
            missing = [t for t, exists in tables.items() if not exists]
            if missing:
                logger.error("Missing tables after boot: %s", missing)
                raise RuntimeError(f"Incomplete schema: {missing}")

            triggers = mgr.verify_triggers_exist()
            missing_t = [t for t, exists in triggers.items() if not exists]
            if missing_t:
                logger.error("Missing FTS5 triggers: %s", missing_t)
                raise RuntimeError(f"Missing triggers: {missing_t}")

            logger.info("Schema v%s verified - all tables and triggers OK.", SchemaManager.SCHEMA_VERSION)
        finally:
            conn.close()

    def close(self) -> None:
        """Shuts down the write queue and read connections."""
        self._conn_mgr.close()
        logger.info("SqliteStore closed.")

    def write_callback(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Delegates a write operation to the ConnectionManager's serialized queue.

        This method protects the encapsulation of the ConnectionManager and its
        internal write queue.
        """
        return self._conn_mgr.write(fn, *args, **kwargs)

    # ===================================================================
    # PROJECTS
    # ===================================================================

    def create_project(
        self, uuid: str, folder_name: str, primary_wing: str = "geral",
        privacy_level: str = "PUBLIC", summary: Optional[str] = None,
    ) -> dict:
        """Registers a new project (aligned with concierge_register)."""
        if privacy_level not in VALID_PRIVACY_LEVELS:
            raise ValueError(f"Invalid privacy_level: '{privacy_level}'. Accepted: {sorted(VALID_PRIVACY_LEVELS)}")

        def _do(conn, u, fn, pw, pl, s):
            conn.execute(
                "INSERT INTO projects (uuid, folder_name, primary_wing, privacy_level, summary) VALUES (?,?,?,?,?)",
                (u, fn, pw, pl, s))
            return {"uuid": u, "folder_name": fn, "primary_wing": pw, "privacy_level": pl}

        return self._conn_mgr.write(_do, uuid, folder_name, primary_wing, privacy_level, summary)

    def get_project(self, project_id: str) -> dict:
        """Retrieves a project by UUID or folder_name."""
        with self._conn_mgr.read() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE uuid = ? OR folder_name = ?",
                (project_id, project_id)).fetchone()
        if not row:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return dict(row)

    def update_project(self, uuid: str, **fields: Any) -> None:
        """Updates allowed fields of a project."""
        allowed = {"folder_name", "primary_wing", "privacy_level", "summary"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "privacy_level" in updates and updates["privacy_level"] not in VALID_PRIVACY_LEVELS:
            raise ValueError(f"Invalid privacy_level: {updates['privacy_level']}")
        updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [uuid]

        def _do(conn, sc, v):
            conn.execute(f"UPDATE projects SET {sc} WHERE uuid = ?", v)
        self._conn_mgr.write(_do, set_clause, vals)

    def delete_project(self, uuid: str) -> None:
        """Removes a project and all cascaded data."""
        def _do(conn, u):
            conn.execute("DELETE FROM projects WHERE uuid = ?", (u,))
        self._conn_mgr.write(_do, uuid)

    def list_projects(self) -> list[dict]:
        """Lists all projects sorted by updated_at DESC."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    # ===================================================================
    # NODES
    # ===================================================================

    def create_node(
        self, project_uuid: str, label: str, summary: Optional[str] = None,
        node_type: str = "FACT", type_: str = "file",
        tags: Optional[list[str]] = None, file_hash: Optional[str] = None,
        status: str = "ACTIVE", content: Optional[str] = None,
        valid_from_commit: Optional[str] = None,
        valid_to_commit: Optional[str] = None,
    ) -> int:
        """Creates a node in the graph (aligned with concierge_mine).

        Args:
            valid_from_commit: SHA of the commit where the node becomes valid (optional).
            valid_to_commit: SHA of the commit where the node ceases to be valid (optional).
        """
        if node_type not in VALID_NODE_TYPES:
            raise ValueError(f"Invalid node_type: '{node_type}'. Accepted: {sorted(VALID_NODE_TYPES)}")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: '{status}'. Accepted: {sorted(VALID_STATUSES)}")
        
        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        def _do(conn, pu, lb, sm, nt, tp, tg, fh, st, ct, vfc, vtc):
            cur = conn.execute(
                """INSERT INTO nodes
                   (project_uuid, label, summary, node_type, type, tags, file_hash, status, content,
                    valid_from_commit, valid_to_commit)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pu, lb, sm, nt, tp, tg, fh, st, ct, vfc, vtc))
            return cur.lastrowid
        return self._conn_mgr.write(
            _do, project_uuid, label, summary, node_type, type_, tags_json,
            file_hash, status, content, valid_from_commit, valid_to_commit,
        )

    def get_node(self, node_id: int) -> dict:
        """Returns a node by ID."""
        with self._conn_mgr.read() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if not row:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        result = dict(row)
        if result.get("tags"):
            try:
                result["tags"] = json.loads(result["tags"])
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def get_nodes_by_project(
        self, project_uuid: str, node_type: Optional[str] = None, status: Optional[str] = None,
    ) -> list[dict]:
        """Lists nodes of a project with optional filters."""
        sql = "SELECT * FROM nodes WHERE project_uuid = ?"
        params: list[Any] = [project_uuid]
        if node_type:
            sql += " AND node_type = ?"
            params.append(node_type)
        if status:
            sql += " AND status = ?"
            params.append(status)
        with self._conn_mgr.read() as conn:
            rows = conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("tags"):
                try:
                    d["tags"] = json.loads(d["tags"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results

    def get_lightweight_topology(self, project_uuid: Optional[str] = None) -> dict[str, list[dict]]:
        """Returns the complete and lightweight topology (nodes and edges) from the database.

        Avoids loading text summaries (summary) or embeddings for bandwidth optimization.

        Args:
            project_uuid: Optional UUID to filter the nodes and edges of that project.

        Returns:
            Dict with structure:
            {
                "nodes": [{"node_id": int, "name": str, "node_type": str}],
                "edges": [{"source": int, "target": int, "edge_type": str}]
            }
        """
        if project_uuid:
            nodes_sql = "SELECT id AS node_id, label AS name, node_type FROM nodes WHERE project_uuid = ? AND status = 'ACTIVE'"
            nodes_params = [project_uuid]

            edges_sql = """
                SELECT e.source_id AS source, e.target_id AS target, e.relation_type AS edge_type
                FROM edges e
                JOIN nodes n1 ON e.source_id = n1.id
                JOIN nodes n2 ON e.target_id = n2.id
                WHERE n1.project_uuid = ? AND n2.project_uuid = ?
                  AND n1.status = 'ACTIVE' AND n2.status = 'ACTIVE'
            """
            edges_params = [project_uuid, project_uuid]
        else:
            nodes_sql = "SELECT id AS node_id, label AS name, node_type FROM nodes WHERE status = 'ACTIVE'"
            nodes_params = []

            edges_sql = "SELECT source_id AS source, target_id AS target, relation_type AS edge_type FROM edges"
            edges_params = []

        with self._conn_mgr.read() as conn:
            node_rows = conn.execute(nodes_sql, nodes_params).fetchall()
            edge_rows = conn.execute(edges_sql, edges_params).fetchall()

        return {
            "nodes": [dict(r) for r in node_rows],
            "edges": [dict(r) for r in edge_rows]
        }


    def update_node(self, node_id: int, **fields: Any) -> None:
        """Updates allowed fields of a node (includes temporal fields)."""
        allowed = {"label", "summary", "node_type", "type", "tags", "file_hash",
                    "last_accessed", "last_commit_at", "status",
                    "valid_from_commit", "valid_to_commit"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "node_type" in updates and updates["node_type"] not in VALID_NODE_TYPES:
            raise ValueError(f"Invalid node_type: {updates['node_type']}")
        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {updates['status']}")
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [node_id]

        def _do(conn, sc, v):
            conn.execute(f"UPDATE nodes SET {sc} WHERE id = ?", v)
        self._conn_mgr.write(_do, set_clause, vals)

    def delete_node(self, node_id: int) -> None:
        """Removes a node and its edges (CASCADE)."""
        def _do(conn, nid):
            conn.execute("DELETE FROM nodes WHERE id = ?", (nid,))
        self._conn_mgr.write(_do, node_id)

    def find_node_by_hash(self, project_uuid: str, file_hash: str) -> Optional[dict]:
        """Searches node by SHA256 hash (delta update check in concierge_mine)."""
        with self._conn_mgr.read() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE project_uuid = ? AND file_hash = ?",
                (project_uuid, file_hash)).fetchone()
        return dict(row) if row else None

    def touch_node_commit(self, node_id: int) -> None:
        """Updates last_commit_at to now (used in commit_memory)."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.update_node(node_id, last_commit_at=now)

    def update_nodes_file_hash_bulk(self, updates: list[tuple[int, str]]) -> int:
        """Updates file_hash of multiple nodes in a single transaction.

        Used by Delta Cache to bind cached nodes to the new file hash,
        preventing Garbage Collection from marking them as orphans.

        Args:
            updates: List of tuples (node_id, new_file_hash).

        Returns:
            Number of successfully updated nodes.
        """
        if not updates:
            return 0

        def _do(conn, upd):
            for node_id, new_hash in upd:
                conn.execute(
                    "UPDATE nodes SET file_hash = ? WHERE id = ?",
                    (new_hash, node_id),
                )
        self._conn_mgr.write(_do, updates)
        return len(updates)

    def cleanup_obsolete_nodes(self, project_uuid: str, relative_path: str, current_file_hash: str) -> None:
        """Removes orphan nodes from a modified file (chunks that ceased to exist).

        When modifying a file, unchanged chunks are cached and new ones are
        inserted (both with the new file_hash). Old chunks of the same file
        that were not reused keep the old hash and are removed here.
        """
        def _do(conn):
            prefix = f"{relative_path}::"
            conn.execute(
                "DELETE FROM nodes WHERE project_uuid = ? AND (label = ? OR label LIKE ?) AND (file_hash IS NULL OR file_hash != ?)",
                (project_uuid, relative_path, prefix + "%", current_file_hash)
            )
        self._conn_mgr.write(_do)


    def create_nodes_and_edges_bulk(
        self,
        nodes_to_create: list[dict],
        edges_to_create: list[dict]
    ) -> list[int]:
        """Creates multiple nodes and edges in a single SQLite transaction (WAL-friendly).

        Supports temporal fields and confidence_tag in each node/edge dict.
        """
        def _do(conn) -> list[int]:
            node_ids = []
            # Insert nodes
            for n in nodes_to_create:
                if n.get("node_type", "FACT") not in VALID_NODE_TYPES:
                    raise ValueError(f"Invalid node_type in bulk: {n.get('node_type')}")
                if n.get("status", "ACTIVE") not in VALID_STATUSES:
                    raise ValueError(f"Invalid status in bulk: {n.get('status')}")
                    
                tags_json = json.dumps(n.get("tags"), ensure_ascii=False) if n.get("tags") else None
                cur = conn.execute(
                    """INSERT INTO nodes
                       (project_uuid, label, summary, content, node_type, type, tags, file_hash, status,
                        valid_from_commit, valid_to_commit)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (n["project_uuid"], n["label"], n.get("summary"), n.get("content"),
                     n.get("node_type", "FACT"), n.get("type", "file"), tags_json,
                     n.get("file_hash"), n.get("status", "ACTIVE"),
                     n.get("valid_from_commit"), n.get("valid_to_commit"))
                )
                node_ids.append(cur.lastrowid)
                
            # Insert edges
            for e in edges_to_create:
                src_id = e["source_id"]
                tgt_id = e["target_id"]
                
                # Resolution of index references if passed as idx_0, idx_1 etc.
                if isinstance(src_id, str) and src_id.startswith("idx_"):
                    idx = int(src_id.split("_")[1])
                    src_id = node_ids[idx]
                if isinstance(tgt_id, str) and tgt_id.startswith("idx_"):
                    idx = int(tgt_id.split("_")[1])
                    tgt_id = node_ids[idx]
                    
                conn.execute(
                    """INSERT OR REPLACE INTO edges
                       (source_id, target_id, relation_type, weight,
                        valid_from_commit, valid_to_commit, confidence_tag)
                       VALUES (?,?,?,?,?,?,?)""",
                    (src_id, tgt_id, e.get("relation_type", "depends_on"), e.get("weight", 1.0),
                     e.get("valid_from_commit"), e.get("valid_to_commit"),
                     e.get("confidence_tag", "EXTRACTED"))
                )
            return node_ids
            
        return self._conn_mgr.write(_do)

    # ===================================================================
    # EDGES
    # ===================================================================

    def create_edge(
        self, source_id: int, target_id: int,
        relation_type: str = "depends_on", weight: float = 1.0,
        valid_from_commit: Optional[str] = None,
        valid_to_commit: Optional[str] = None,
        confidence_tag: str = "EXTRACTED",
    ) -> None:
        """Creates or updates an edge between two nodes.

        Args:
            valid_from_commit: Commit SHA in which the edge becomes valid.
            valid_to_commit: Commit SHA in which the edge ceases to be valid.
            confidence_tag: Confidence degree of the relation ('EXTRACTED'|'INFERRED'|'AMBIGUOUS').
        """
        def _do(conn, s, t, r, w, vfc, vtc, ct):
            conn.execute(
                """INSERT OR REPLACE INTO edges
                   (source_id, target_id, relation_type, weight,
                    valid_from_commit, valid_to_commit, confidence_tag)
                   VALUES (?,?,?,?,?,?,?)""",
                (s, t, r, w, vfc, vtc, ct))
        self._conn_mgr.write(
            _do, source_id, target_id, relation_type, weight,
            valid_from_commit, valid_to_commit, confidence_tag,
        )

    def get_edges_from(self, node_id: int) -> list[dict]:
        """Edges coming out of a node (source → targets)."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM edges WHERE source_id = ?", (node_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_edges_to(self, node_id: int) -> list[dict]:
        """Edges arriving at a node (sources → target)."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM edges WHERE target_id = ?", (node_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_in_degree(self, node_id: int) -> int:
        """Counts incoming edges (in-degree) of a node."""
        with self._conn_mgr.read() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM edges WHERE target_id = ?", (node_id,)).fetchone()
        return row["c"] if row else 0

    def delete_edge(self, source_id: int, target_id: int) -> None:
        """Removes an edge."""
        def _do(conn, s, t):
            conn.execute("DELETE FROM edges WHERE source_id = ? AND target_id = ?", (s, t))
        self._conn_mgr.write(_do, source_id, target_id)

    # ===================================================================
    # TRAJECTORIES
    # ===================================================================

    def create_trajectory(
        self, project_uuid: str, prompt_origem: str, tentativa_execucao: str,
        erro_encontrado: Optional[str] = None, solucao_aplicada: Optional[str] = None,
        status: str = "ACTIVE",
    ) -> int:
        """Registers an episodic trajectory (Learning Loop)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: '{status}'")

        def _do(conn, pu, po, te, ee, sa, st):
            cur = conn.execute(
                """INSERT INTO trajectories
                   (project_uuid, prompt_origem, tentativa_execucao, erro_encontrado, solucao_aplicada, status)
                   VALUES (?,?,?,?,?,?)""",
                (pu, po, te, ee, sa, st))
            return cur.lastrowid
        return self._conn_mgr.write(_do, project_uuid, prompt_origem, tentativa_execucao,
                                     erro_encontrado, solucao_aplicada, status)

    def get_trajectories(self, project_uuid: str, status: Optional[str] = None) -> list[dict]:
        """Lists trajectories of a project with optional status filter."""
        sql = "SELECT * FROM trajectories WHERE project_uuid = ?"
        params: list[Any] = [project_uuid]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC"
        with self._conn_mgr.read() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def decay_trajectory(self, trajectory_id: int, new_status: str) -> bool:
        """Delegates to GraphLogic (state machine with validation)."""
        return self._logic.decay_trajectory(trajectory_id, new_status)

    # ===================================================================
    # COMMIT LOG (aligned with concierge_commit)
    # ===================================================================

    def create_commit(
        self, project_uuid: str, phase: str, technical_changes: str,
        updated_pointers: list[str], revisor_approved: bool = False,
        partial_audit: bool = False,
    ) -> int:
        """Registers an audited memory commit.

        Mandatory validation: technical_changes and updated_pointers cannot be empty.
        """
        if not technical_changes:
            raise CommitValidationError("technical_changes is mandatory and cannot be empty.")
        if not updated_pointers:
            raise CommitValidationError("updated_pointers is mandatory and cannot be empty.")
        pointers_json = json.dumps(updated_pointers, ensure_ascii=False)

        def _do(conn, pu, ph, tc, up, ra, pa):
            cur = conn.execute(
                """INSERT INTO commit_log
                   (project_uuid, phase, technical_changes, updated_pointers, revisor_approved, partial_audit)
                   VALUES (?,?,?,?,?,?)""",
                (pu, ph, tc, up, int(ra), int(pa)))
            return cur.lastrowid
        return self._conn_mgr.write(_do, project_uuid, phase, technical_changes,
                                     pointers_json, revisor_approved, partial_audit)

    def get_recent_commits(self, project_uuid: str, limit: int = 5) -> list[dict]:
        """Returns the N most recent commits of a project."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute(
                "SELECT * FROM commit_log WHERE project_uuid = ? ORDER BY created_at DESC LIMIT ?",
                (project_uuid, limit)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("updated_pointers"):
                try:
                    d["updated_pointers"] = json.loads(d["updated_pointers"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results

    # ===================================================================
    # REFERENCE WINGS
    # ===================================================================

    def add_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Adds a Reference Wing to the project."""
        def _do(conn, pu, wn):
            conn.execute("INSERT OR IGNORE INTO reference_wings (project_uuid, wing_name) VALUES (?,?)", (pu, wn))
        self._conn_mgr.write(_do, project_uuid, wing_name)

    def get_reference_wings(self, project_uuid: str) -> list[str]:
        """Lists Reference Wings of a project."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT wing_name FROM reference_wings WHERE project_uuid = ?", (project_uuid,)).fetchall()
        return [r["wing_name"] for r in rows]

    def remove_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Removes a Reference Wing."""
        def _do(conn, pu, wn):
            conn.execute("DELETE FROM reference_wings WHERE project_uuid = ? AND wing_name = ?", (pu, wn))
        self._conn_mgr.write(_do, project_uuid, wing_name)

    # ===================================================================
    # INTELLIGENCE (delegated to GraphLogic)
    # ===================================================================

    def compute_centrality(self, node_id: int) -> float:
        """Normalized centrality: min(in_degree/10, 1.0)."""
        return self._logic.compute_centrality(node_id)

    def compute_recency_score(self, node_id: int) -> float:
        """Recency score: max(e^(-λ×t), 0.01)."""
        return self._logic.compute_recency_score(node_id)

    def fts_search(self, query: str, project_uuid: Optional[str] = None,
                   node_type: Optional[str] = None, limit: int = 20) -> list[dict]:
        """FTS5 search with normalized BM25 (concierge_search - frequency component)."""
        return self._logic.fts_search(query, project_uuid, node_type, limit)

    def hybrid_search_score(self, node_id: int, vector_score: float, fts_score: float) -> dict:
        """Individual hybrid score: 0.50×vet + 0.25×fts + 0.25×max(rec,cent)."""
        return self._logic.hybrid_search_score(node_id, vector_score, fts_score)

    def hybrid_search_score_batch(self, candidates: list[dict]) -> list[dict]:
        """Hybrid score in batch — used by concierge_search."""
        return self._logic.hybrid_search_score_batch(candidates)

    def fts_rebuild(self) -> None:
        """Rebuilds the FTS5 index (post massive concierge_mine)."""
        self._logic.fts_rebuild()

    def get_dependency_tree(self, start_node_id: int, max_depth: int = 10) -> list[dict]:
        """CTE: dependency tree with anti-loop protection."""
        return self._logic.get_dependency_tree(start_node_id, max_depth)

    def get_reverse_dependency_tree(self, start_node_id: int, max_depth: int = 10) -> list[dict]:
        """Reverse CTE: who depends on this node."""
        return self._logic.get_reverse_dependency_tree(start_node_id, max_depth)

    def get_project_stats(self, project_uuid: str) -> dict:
        """Complete statistics of a project."""
        return self._logic.get_project_stats(project_uuid)

    def get_last_commit_phase(self, project_uuid: str) -> Optional[str]:
        """Phase of the most recent commit."""
        return self._logic.get_last_commit_phase(project_uuid)

    def bulk_decay_stale_trajectories(self, project_uuid: str, stale_threshold_days: int = 30) -> int:
        """Mass decay for the Background Janitor."""
        return self._logic.bulk_decay_stale_trajectories(project_uuid, stale_threshold_days)

    def search_symbols(self, query: str, project_uuid: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Searches for indexed classes, methods, and functions using FTS5."""
        safe_query = query.replace('"', '""')
        sql = """
            SELECT n.id, n.label, n.type, n.project_uuid, n.file_hash
            FROM nodes_fts f
            JOIN nodes n ON n.id = f.rowid
            WHERE nodes_fts MATCH ? AND n.type IN ('class', 'function', 'method')
            ORDER BY CASE n.type WHEN 'class' THEN 1 WHEN 'function' THEN 2 WHEN 'method' THEN 3 ELSE 4 END, n.id
        """
        params: list[Any] = [f'"{safe_query}"']
        if project_uuid:
            sql += " AND n.project_uuid = ?"
            params.append(project_uuid)
        sql += " LIMIT ?"
        params.append(limit)
        return self._conn_mgr.execute_raw_read(sql, tuple(params))

    def get_callers(self, symbol_id: int) -> list[dict]:
        """Returns all nodes that call the specified symbol."""
        sql = """
            SELECT n.id, n.label, n.type, n.project_uuid
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ? AND e.relation_type = 'calls'
        """
        return self._conn_mgr.execute_raw_read(sql, (symbol_id,))


    # ===================================================================
    # ENCAPSULATION — Public API for JanitorService (Patch 2)
    # ===================================================================

    def is_write_queue_empty(self) -> bool:
        """Returns True if the write queue (SerializedWriteQueue) has no pending jobs.

        Replaces direct access to _conn_mgr._write_queue._queue.empty() in Janitor.
        """
        return self._conn_mgr.is_write_queue_empty()

    def execute_read_sql(self, sql: str, params: tuple = ()) -> list[dict]:
        """Executes arbitrary read SQL and returns a list of dicts.

        Allows JanitorService to make complex queries (WITH RECURSIVE,
        JOIN with FTS5, etc.) without needing to access self._conn_mgr directly.

        Args:
            sql: SQL query for reading (SELECT / WITH RECURSIVE).
            params: Positional parameters for the query.

        Returns:
            List of dictionaries with the results.
        """
        return self._conn_mgr.execute_raw_read(sql, params)

    # ===================================================================
    # USER CORE MEMORY — Complete CRUD (Patch 1)
    # ===================================================================

    _VALID_SCOPE_TYPES: frozenset[str] = frozenset({"user", "session", "agent", "org"})

    def set_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
        content: str,
    ) -> int:
        """Writes or updates a block of user/session core memory.

        Uses INSERT OR REPLACE to ensure block_label is unique per scope.

        Args:
            scope_type: Scope type — 'user', 'session', 'agent' or 'org'.
            scope_id: Scope identifier (e.g. user UUID, session UUID).
            block_label: Label of the memory block (e.g. 'preferred_language').
            content: Content of the memory block.

        Returns:
            The id of the inserted or replaced record.

        Raises:
            ValueError: If scope_type is invalid or required fields are empty.
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"Invalid scope_type: '{scope_type}'. Accepted: {sorted(self._VALID_SCOPE_TYPES)}")
        if not scope_id or not scope_id.strip():
            raise ValueError("scope_id cannot be empty.")
        if not block_label or not block_label.strip():
            raise ValueError("block_label cannot be empty.")

        def _write(conn: "sqlite3.Connection") -> int:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO user_core_memory
                   (scope_type, scope_id, block_label, content, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (scope_type, scope_id.strip(), block_label.strip(), content),
            )
            return cursor.lastrowid

        return self._conn_mgr.write(_write)

    def get_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
    ) -> Optional[dict]:
        """Returns a specific core memory block, or None if it doesn't exist.

        Args:
            scope_type: Scope type.
            scope_id: Scope identifier.
            block_label: Label of the memory block.

        Returns:
            Dict with the record columns, or None.
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"Invalid scope_type: '{scope_type}'.")
        rows = self._conn_mgr.execute_raw_read(
            """SELECT id, scope_type, scope_id, block_label, content, updated_at
               FROM user_core_memory
               WHERE scope_type = ? AND scope_id = ? AND block_label = ?
               LIMIT 1""",
            (scope_type, scope_id.strip(), block_label.strip()),
        )
        return rows[0] if rows else None

    def list_core_memory_blocks(
        self,
        scope_type: str,
        scope_id: str,
    ) -> list[dict]:
        """Returns all core memory blocks for a scope.

        Args:
            scope_type: Scope type.
            scope_id: Scope identifier.

        Returns:
            List of dicts (can be empty).
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"Invalid scope_type: '{scope_type}'.")
        return self._conn_mgr.execute_raw_read(
            """SELECT id, scope_type, scope_id, block_label, content, updated_at
               FROM user_core_memory
               WHERE scope_type = ? AND scope_id = ?
               ORDER BY block_label ASC""",
            (scope_type, scope_id.strip()),
        )
