"""
services/janitor.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Background Janitor — Autonomous maintenance of the Memory Graph.

Responsibilities:
    - Trajectories Decay: Marks stale episodic trajectories (>30d)
      as DECAYED to prevent context pollution.
    - Atomic Sync: Reconciles SQLite ↔ ChromaDB via verify_sync,
      removing orphan vectors left behind after partial GC.
    - Auto-Zoom: Detects when >N changes occurred since the last L2
      and automatically triggers generate_project_context (L1/L2).
    - Inactive Nodes Cleanup: Marks nodes with no access for >60d as ARCHIVED.
    - FTS Rebuild: Rebuilds Full-Text Search index after heavy maintenance.

Thread Safety:
    The Janitor operates exclusively via SqliteStore (which already uses
    SerializedWriteQueue with thread-safe write() and contextmanager read()).
    It can run in a separate thread without contention risk.

Idle-Lock:
    The Janitor checks if there are mine() operations in progress before
    executing destructive tasks (GC, decay). If it detects activity,
    it postpones the execution (backoff).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from storage import SqliteStore, ChromaVectorStore
from ingestion.orchestrator import IngestionManager

logger = logging.getLogger("grafo-concierge.janitor")


# ---------------------------------------------------------------------------
# Background Janitor Settings
# ---------------------------------------------------------------------------

# Trajectories decay
STALE_TRAJECTORY_DAYS: int = 30

# Auto-Zoom: minimum number of new nodes to trigger L1/L2
AUTO_ZOOM_THRESHOLD: int = 10

# Inactive nodes: days without access to mark as ARCHIVED
INACTIVE_NODE_DAYS: int = 60

# Interval between Janitor cycles (in seconds)
DEFAULT_INTERVAL_SECONDS: int = 300  # 5 minutes

# Idle-Lock: maximum waiting time (in seconds)
IDLE_LOCK_TIMEOUT: int = 30


# ---------------------------------------------------------------------------
# MaintenanceReport — report of a Janitor execution
# ---------------------------------------------------------------------------

@dataclass
class MaintenanceReport:
    """Report of a maintenance round."""
    timestamp: str = ""
    project_uuid: str = ""
    trajectories_decayed: int = 0
    orphan_vectors_removed: int = 0
    inactive_nodes_archived: int = 0
    communities_detected: int = 0
    summaries_generated: int = 0
    zoom_triggered: bool = False
    zoom_l1_count: int = 0
    zoom_l2_summary: str = ""
    fts_rebuilt: bool = False
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    skipped_idle_lock: bool = False

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "project_uuid": self.project_uuid,
            "trajectories_decayed": self.trajectories_decayed,
            "orphan_vectors_removed": self.orphan_vectors_removed,
            "inactive_nodes_archived": self.inactive_nodes_archived,
            "communities_detected": self.communities_detected,
            "summaries_generated": self.summaries_generated,
            "zoom_triggered": self.zoom_triggered,
            "zoom_l1_count": self.zoom_l1_count,
            "zoom_l2_summary": self.zoom_l2_summary,
            "fts_rebuilt": self.fts_rebuilt,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 3),
            "skipped_idle_lock": self.skipped_idle_lock,
        }


# ---------------------------------------------------------------------------
# JanitorService — Autonomous Maintenance Engine
# ---------------------------------------------------------------------------

class JanitorService:
    """Background Janitor — autonomous maintenance of the graph.

    Thread Safety guaranteed by SerializedWriteQueue of SqliteStore.
    All writes are queued atomically.

    Usage:
        janitor = JanitorService(store, vector_store, ingestion_manager)
        # Manual execution (single-shot):
        report = janitor.run_maintenance(project_uuid)
        # Continuous execution (background thread):
        janitor.start_background(project_uuid, interval=300)
        janitor.stop_background()
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        ingestion_manager: Optional[IngestionManager] = None,
        stale_days: int = STALE_TRAJECTORY_DAYS,
        auto_zoom_threshold: int = AUTO_ZOOM_THRESHOLD,
        inactive_days: int = INACTIVE_NODE_DAYS,
        super_node_threshold: int = 10,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._ingestion = ingestion_manager
        self._stale_days = stale_days
        self._zoom_threshold = auto_zoom_threshold
        self._inactive_days = inactive_days
        self._super_node_threshold = super_node_threshold

        # Idle-Lock: shared flag to detect mine() in progress
        self._mine_active = threading.Event()
        self._mine_timestamp = 0.0

        # Background thread control
        self._bg_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_reports: list[MaintenanceReport] = []

        # Vector payloads in tests or mock vector stores
        self.vector_payloads: dict[int, dict[str, Any]] = {}

        logger.info(
            "JanitorService initialized: stale=%dd, zoom_threshold=%d, inactive=%dd, super_node_threshold=%d",
            stale_days, auto_zoom_threshold, inactive_days, super_node_threshold,
        )

    # ===================================================================
    # Idle-Lock API — called by IngestionManager
    # ===================================================================

    def signal_mine_start(self) -> None:
        """Signals that mine() is in progress (Idle-Lock active)."""
        self._mine_active.set()
        self._mine_timestamp = time.monotonic()
        logger.debug("Idle-Lock: mine() active — Janitor waiting.")

    def signal_mine_end(self) -> None:
        """Signals that mine() has finished (Idle-Lock released)."""
        self._mine_active.clear()
        logger.debug("Idle-Lock: mine() finished — Janitor released.")

    def is_system_active(self) -> bool:
        """Returns True if there is active activity in the system (mine active or queue busy)."""
        if self._mine_active.is_set():
            elapsed = time.monotonic() - getattr(self, "_mine_timestamp", 0.0)
            if elapsed > 300.0:
                logger.warning(
                    "Idle-Lock: deadlock detected! mine() active for %.1fs (> 300s). Forcing flag release.",
                    elapsed
                )
                self._mine_active.clear()
            else:
                return True
        # Verifies write queue via public API (without violating encapsulation)
        if self._store and not self._store.is_write_queue_empty():
            return True
        return False

    def _wait_for_idle(self) -> bool:
        """Waits until mine() finishes or timeout expires.

        Returns:
            True if system became idle, False if timeout.
        """
        if not self.is_system_active():
            return True

        logger.info("Idle-Lock: waiting for system to become idle (timeout=%ds)...", IDLE_LOCK_TIMEOUT)
        start = time.monotonic()
        while self.is_system_active():
            if time.monotonic() - start > IDLE_LOCK_TIMEOUT:
                logger.warning("Idle-Lock: timeout — maintenance postponed.")
                return False
            time.sleep(0.5)

        return True

    # ===================================================================
    # RUN MAINTENANCE — Single-shot execution
    # ===================================================================

    def run_maintenance(self, project_uuid: str) -> MaintenanceReport:
        """Executes a full maintenance round for a project.

        Flow:
            1. Idle-Lock check: postpones if mine() active or queue has tasks.
            2. Decay of stale trajectories.
            3. SQLite ↔ ChromaDB sync (orphan vectors).
            4. Archiving of inactive nodes.
            5. Community Detection (WITH RECURSIVE on edges table with FTS5).
            6. Synthesis/summarization of Communities and vector injection.
            7. Auto-Zoom (L1/L2) if threshold reached.
            8. FTS Rebuild if significant changes occurred.
        """
        t0 = time.perf_counter()
        report = MaintenanceReport(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            project_uuid=project_uuid,
        )

        logger.info("=" * 50)
        logger.info("JANITOR: maintenance started for %s", project_uuid)
        logger.info("=" * 50)

        # --- Idle-Lock ---
        if not self._wait_for_idle():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            logger.info("JANITOR: maintenance postponed (Idle-Lock).")
            return report

        # --- STEP 1: Trajectory decay ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.trajectories_decayed = self._decay_trajectories(project_uuid, report)

        # --- STEP 2: Atomic sync (orphan vectors) ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.orphan_vectors_removed = self._sync_vectors(project_uuid, report)

        # --- STEP 3: Inactive nodes archiving ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.inactive_nodes_archived = self._archive_inactive_nodes(project_uuid, report)

        # --- STEP 4: Community Detection (GraphRAG) ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        communities = self.detect_communities(project_uuid)
        report.communities_detected = len(communities)

        # --- STEP 5: Summarization and Injection ---
        if communities:
            if self.is_system_active():
                report.skipped_idle_lock = True
                report.duration_seconds = time.perf_counter() - t0
                return report
            summaries = self.generate_and_persist_community_summaries(project_uuid, communities)
            report.summaries_generated = len(summaries)

        # --- STEP 6: Auto-Zoom ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        self._auto_zoom(project_uuid, report)

        # --- STEP 7: FTS Rebuild (if changes occurred) ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        changes = (report.trajectories_decayed
                   + report.orphan_vectors_removed
                   + report.inactive_nodes_archived
                   + report.summaries_generated)
        if changes > 0:
            self._fts_rebuild(report)

        report.duration_seconds = time.perf_counter() - t0

        logger.info("=" * 50)
        logger.info(
            "JANITOR completed in %.2fs: decayed=%d, orphans=%d, archived=%d, communities=%d, summaries=%d, zoom=%s",
            report.duration_seconds,
            report.trajectories_decayed,
            report.orphan_vectors_removed,
            report.inactive_nodes_archived,
            report.communities_detected,
            report.summaries_generated,
            report.zoom_triggered,
        )
        logger.info("=" * 50)

        self._last_reports.append(report)
        if len(self._last_reports) > 100:
            self._last_reports.pop(0)
        return report

    # ===================================================================
    # STEP 1: Trajectory Decay
    # ===================================================================

    def _decay_trajectories(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Marks stale trajectories as DECAYED."""
        try:
            decayed = self._store.bulk_decay_stale_trajectories(
                project_uuid, stale_threshold_days=self._stale_days,
            )
            if decayed > 0:
                logger.info(
                    "Decay: %d trajectories marked as DECAYED (>%dd).",
                    decayed, self._stale_days,
                )
            else:
                logger.debug("Decay: no stale trajectory detected.")
            return decayed
        except Exception as e:
            error_msg = f"Decay failed: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 2: Atomic Sync (Reconciliation Loop)
    # ===================================================================

    def _sync_vectors(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Detects/removes orphan vectors and auto-generates missing vectors on the active backend."""
        try:
            # Collect active nodes with content from SQLite
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            nodes_with_content = [n for n in nodes if n.get("content")]
            valid_ids: set[int] = {n["id"] for n in nodes}

            # 1. Remove orphan vectors
            orphans = self._vector.verify_sync(valid_ids)
            removed = 0
            if orphans:
                removed = self._vector.delete_batch(orphans)
                logger.info("Sync: %d orphan vectors removed.", removed)

            # 2. Auto-generates and syncs missing embeddings (e.g. Chroma ↔ Qdrant migration)
            if hasattr(self._vector, "get_all_stored_node_ids") and self._ingestion and hasattr(self._ingestion, "_embedder"):
                sqlite_ids = {n["id"] for n in nodes_with_content}
                stored_ids = self._vector.get_all_stored_node_ids()
                
                missing_ids = sqlite_ids - stored_ids
                if missing_ids:
                    logger.info("Sync: %d SQLite nodes without match in active vector database. Auto-generating embeddings...", len(missing_ids))
                    
                    items_to_store = []
                    embedder = self._ingestion._embedder
                    
                    for n in nodes_with_content:
                        if n["id"] in missing_ids:
                            try:
                                emb = embedder.embed(n["content"])
                                items_to_store.append({
                                    "doc_id": f"node_{n['id']}",
                                    "embedding": emb,
                                    "metadata": {
                                        "node_id": n["id"],
                                        "project_uuid": project_uuid,
                                        "label": n.get("label", ""),
                                        "node_type": n.get("type", "FACT")
                                    }
                                })
                            except Exception as embed_err:
                                logger.error("Failed to generate embedding for node %d in auto-sync: %s", n["id"], embed_err)
                    
                    if items_to_store:
                        stored_count = self._vector.store_embeddings_batch(items_to_store)
                        logger.info("Sync: %d missing vectors auto-generated and synchronized successfully.", stored_count)

            return removed

        except Exception as e:
            error_msg = f"Vector sync failed: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 3: Inactive Nodes Archiving
    # ===================================================================

    def _archive_inactive_nodes(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Marks nodes without recent access as ARCHIVED."""
        try:
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            threshold = datetime.now(timezone.utc) - timedelta(days=self._inactive_days)
            threshold_str = threshold.strftime("%Y-%m-%d %H:%M:%S")
            archived = 0

            for node in nodes:
                # Uses last_accessed if available, otherwise updated_at
                last_access = node.get("last_accessed") or node.get("updated_at") or node.get("created_at")
                if not last_access:
                    continue

                # Normalizes to comparable string
                if isinstance(last_access, str) and last_access < threshold_str:
                    try:
                        self._store.update_node(node["id"], status="ARCHIVED")
                        archived += 1
                    except Exception as e:
                        logger.debug("Failed to archive node %d: %s", node["id"], e)

            if archived > 0:
                logger.info(
                    "Archive: %d nodes marked as ARCHIVED (inactive >%dd).",
                    archived, self._inactive_days,
                )
            else:
                logger.debug("Archive: no inactive node detected.")

            return archived

        except Exception as e:
            error_msg = f"Archiving of nodes failed: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 4: Auto-Zoom (L1/L2 Trigger)
    # ===================================================================

    def _auto_zoom(self, project_uuid: str, report: MaintenanceReport) -> None:
        """Checks if there are enough changes to trigger Zoom Gear."""
        if not self._ingestion:
            logger.debug("Auto-Zoom: IngestionManager not configured — ignored.")
            return

        try:
            # Count active nodes — proxy for recent activity
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            recent_count = len(nodes)

            if recent_count < self._zoom_threshold:
                logger.debug(
                    "Auto-Zoom: %d recent changes < threshold %d — ignored.",
                    recent_count, self._zoom_threshold,
                )
                return

            logger.info(
                "Auto-Zoom: %d recent changes >= threshold %d — triggering Zoom Gear...",
                recent_count, self._zoom_threshold,
            )

            zoom_result = self._ingestion.generate_project_context(project_uuid)
            report.zoom_triggered = True
            report.zoom_l1_count = zoom_result.get("l1_count", 0)
            report.zoom_l2_summary = zoom_result.get("l2_summary", "")

            logger.info(
                "Auto-Zoom: %d L1s generated, L2 Compass = %.60s...",
                report.zoom_l1_count, report.zoom_l2_summary,
            )

        except Exception as e:
            error_msg = f"Auto-Zoom failed: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)

    # ===================================================================
    # STEP 5: FTS Rebuild
    # ===================================================================

    def _fts_rebuild(self, report: MaintenanceReport) -> None:
        """Rebuilds the FTS5 index after significant changes."""
        try:
            self._store.fts_rebuild()
            report.fts_rebuilt = True
            logger.info("FTS Rebuild: index rebuilt successfully.")
        except Exception as e:
            error_msg = f"FTS Rebuild failed: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)

    # ===================================================================
    # STEP 4 & 5: Community Detection and Summarization (GraphRAG)
    # ===================================================================

    def detect_communities(self, project_uuid: str) -> dict[int, list[int]]:
        """Detects communities in the graph using WITH RECURSIVE and FTS5.
        Returns a dictionary mapping the super-node ID to the list of node IDs belonging to the community.
        """
        communities: dict[int, list[int]] = {}
        try:
            # 1. Finds super-nodes (in_degree >= self._super_node_threshold)
            super_nodes_rows = self._store.execute_read_sql(
                """
                SELECT n.id
                FROM nodes n
                LEFT JOIN edges e ON n.id = e.target_id
                WHERE n.project_uuid = ? AND n.status = 'ACTIVE'
                GROUP BY n.id
                HAVING COUNT(e.source_id) >= ?
                """,
                (project_uuid, self._super_node_threshold)
            )
            
            super_node_ids = [row["id"] for row in super_nodes_rows]
            logger.info("Janitor detected %d super-nodes (threshold=%d) in project %s.",
                        len(super_node_ids), self._super_node_threshold, project_uuid)
            
            # 2. For each super-node, recursively searches the associated community
            for sn_id in super_node_ids:
                community_rows = self._store.execute_read_sql(
                    """
                    WITH RECURSIVE community(id, depth) AS (
                        SELECT ? AS id, 0 AS depth
                        UNION
                        SELECT e.source_id, c.depth + 1
                        FROM edges e
                        JOIN community c ON e.target_id = c.id
                        JOIN nodes n ON e.source_id = n.id
                        WHERE c.depth < 5 AND n.project_uuid = ? AND n.status = 'ACTIVE'
                        UNION
                        SELECT e.target_id, c.depth + 1
                        FROM edges e
                        JOIN community c ON e.source_id = c.id
                        JOIN nodes n ON e.target_id = n.id
                        WHERE c.depth < 5 AND n.project_uuid = ? AND n.status = 'ACTIVE'
                    )
                    SELECT DISTINCT id FROM community
                    """,
                    (sn_id, project_uuid, project_uuid)
                )
                communities[sn_id] = [row["id"] for row in community_rows]
                    
        except Exception as e:
            logger.error("Failed community detection: %s", e)
            
        return communities

    def generate_and_persist_community_summaries(
        self,
        project_uuid: str,
        communities: dict[int, list[int]],
    ) -> list[dict[str, Any]]:
        """Generates summaries for the detected communities, saves as INSIGHT nodes and updates Qdrant."""
        import json
        
        summaries: list[dict[str, Any]] = []
        for community_id, node_ids in communities.items():
            # Concurrency Protection (Idle-Lock): suspends if the system becomes active
            if self.is_system_active():
                logger.warning("Janitor: community suspension activated due to bus activity.")
                break
                
            # Fetches node details in the community
            node_details = []
            try:
                placeholders = ",".join("?" for _ in node_ids)
                node_details = self._store.execute_read_sql(
                    f"SELECT id, label, summary, node_type, type, tags FROM nodes WHERE id IN ({placeholders})",
                    tuple(node_ids)
                )
            except Exception as e:
                logger.error("Failed to load details of community nodes %d: %s", community_id, e)
                continue

            if not node_details:
                continue

            nodes_block = "\n".join(
                f"- [{n['label']}] ({n['node_type']}/{n['type']}): {n['summary'] or 'Sem resumo'}"
                for n in node_details
            )

            summary_text = None
            tags: list[str] = []
            for n in node_details:
                if n.get("tags"):
                    try:
                        t_list = json.loads(n["tags"]) if isinstance(n["tags"], str) else n["tags"]
                        if isinstance(t_list, list):
                            tags.extend(t_list)
                    except Exception:
                        pass
            
            # Delegates to IngestionManager which encapsulates access to LLM
            if self._ingestion:
                result = self._ingestion.generate_community_summary(nodes_block)
                if result:
                    summary_text = result.get("summary")
                    extra_tags = result.get("tags", [])
                    if isinstance(extra_tags, list):
                        tags.extend(extra_tags)

            if not summary_text:
                # Heuristic / Dumb fallback
                labels_str = ", ".join(n["label"] for n in node_details[:5])
                if len(node_details) > 5:
                    labels_str += f" and {len(node_details) - 5} more"
                summary_text = f"Logical community anchored by super-node {community_id}, containing nodes: {labels_str}."

            # Saves the INSIGHT to SQLite
            try:
                insight_node_id = self._store.create_node(
                    project_uuid=project_uuid,
                    label=f"community_{community_id}_summary",
                    summary=summary_text,
                    node_type="INSIGHT",
                    type_="community_summary",
                    tags=sorted(list(set(tags))),
                )
                
                # Creates the edge connecting the INSIGHT to the super-node
                self._store.create_edge(
                    source_id=insight_node_id,
                    target_id=community_id,
                    relation_type="summarizes",
                    weight=1.0,
                )
                
                # Injects community IDs directly into vector metadata
                for nid in node_ids:
                    self._update_vector_metadata(nid, project_uuid, community_id)
                    
                summaries.append({
                    "community_id": community_id,
                    "insight_node_id": insight_node_id,
                    "summary": summary_text,
                    "tags": sorted(list(set(tags))),
                })
                
            except Exception as e:
                logger.error("Failed to save community INSIGHT %d in SQLite: %s", community_id, e)

        return summaries

    def _update_vector_metadata(self, node_id: int, project_uuid: str, community_id: int) -> None:
        """Updates metadata in the vector store injecting the community_id."""
        metadata = {
            "node_id": node_id,
            "project_uuid": project_uuid,
            "community_id": community_id,
        }

        # 1. Stores in Janitor's local cache (useful for tests/mocks)
        self.vector_payloads[node_id] = metadata

        # 2. Updates via public API (without accessing _collection directly)
        if self._vector:
            doc_id = f"node_{node_id}"
            self._vector.update_metadata(doc_id, metadata)

    # ===================================================================
    # BACKGROUND THREAD — Continuous execution
    # ===================================================================

    def start_background(
        self,
        project_uuid: str,
        interval: int = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        """Starts Janitor in background thread.

        The thread runs run_maintenance() every `interval` seconds.
        Thread-safe: uses SerializedWriteQueue of SqliteStore.
        """
        if self._bg_thread and self._bg_thread.is_alive():
            logger.warning("Janitor background is already running.")
            return

        self._stop_event.clear()

        def _loop():
            logger.info("Janitor background started (interval=%ds).", interval)
            while not self._stop_event.is_set():
                try:
                    self.run_maintenance(project_uuid)
                except Exception as e:
                    logger.error("Janitor background — unhandled error: %s", e)

                # Interruptible sleep
                self._stop_event.wait(timeout=interval)

            logger.info("Janitor background stopped.")

        self._bg_thread = threading.Thread(
            target=_loop,
            name="grafo-janitor",
            daemon=True,
        )
        self._bg_thread.start()
        logger.info("Janitor background thread started: name=%s", self._bg_thread.name)

    def stop_background(self, timeout: float = 10.0) -> None:
        """Stops the Janitor background thread."""
        if not self._bg_thread or not self._bg_thread.is_alive():
            logger.debug("Janitor background is not running.")
            return

        logger.info("Stopping Janitor background...")
        self._stop_event.set()
        self._bg_thread.join(timeout=timeout)

        if self._bg_thread.is_alive():
            logger.warning("Janitor background did not stop within timeout of %.1fs.", timeout)
        else:
            logger.info("Janitor background stopped successfully.")

    @property
    def is_running(self) -> bool:
        """Checks if the background thread is active."""
        return self._bg_thread is not None and self._bg_thread.is_alive()

    @property
    def last_reports(self) -> list[MaintenanceReport]:
        """Maintenance reports history (latest)."""
        return list(self._last_reports)

    # ===================================================================
    # FULL MAINTENANCE — all projects
    # ===================================================================

    def run_all_projects(self) -> list[MaintenanceReport]:
        """Executes maintenance on ALL registered projects."""
        reports: list[MaintenanceReport] = []
        try:
            projects = self._store.list_projects()
        except Exception as e:
            logger.error("Failed to list projects for global maintenance: %s", e)
            return reports

        for project in projects:
            puuid = project.get("uuid", "")
            if not puuid:
                continue
            try:
                report = self.run_maintenance(puuid)
                reports.append(report)
            except Exception as e:
                logger.error("Maintenance failed for project %s: %s", puuid, e)

        logger.info("Global maintenance: %d projects processed.", len(reports))
        return reports
