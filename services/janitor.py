"""
services/janitor.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Background Janitor — Manutenção autônoma do Grafo de Memória.

Responsabilidades:
    - Decaimento de Trajetórias: Marca trajetórias episódicas stale (>30d)
      como DECAYED para evitar poluição de contexto.
    - Sincronização Atômica: Reconcilia SQLite ↔ ChromaDB via verify_sync,
      removendo vetores órfãos que ficaram após GC parcial.
    - Auto-Zoom: Detecta quando >N mudanças ocorreram desde o último L2
      e dispara automaticamente o generate_project_context (L1/L2).
    - Limpeza de Nós Inativos: Marca nós sem acesso há >60d como ARCHIVED.
    - FTS Rebuild: Reconstrói o índice Full-Text Search após manutenção pesada.

Thread Safety:
    O Janitor opera exclusivamente via SqliteStore (que já usa
    SerializedWriteQueue com thread-safe write() e contextmanager read()).
    Pode rodar em thread separada sem risco de contention.

Idle-Lock:
    O Janitor verifica se há operações de mine() em andamento antes de
    executar tarefas destrutivas (GC, decay). Se detectar atividade,
    adia a execução (backoff).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from storage import SqliteStore, ChromaVectorStore
from ingestion.orchestrator import IngestionManager

logger = logging.getLogger("grafo-concierge.janitor")


# ---------------------------------------------------------------------------
# Configurações do Background Janitor
# ---------------------------------------------------------------------------

# Decaimento de trajetórias
STALE_TRAJECTORY_DAYS: int = 30

# Auto-Zoom: número mínimo de nós novos para disparar L1/L2
AUTO_ZOOM_THRESHOLD: int = 10

# Nós inativos: dias sem acesso para marcar como ARCHIVED
INACTIVE_NODE_DAYS: int = 60

# Intervalo entre ciclos do Janitor (em segundos)
DEFAULT_INTERVAL_SECONDS: int = 300  # 5 minutos

# Idle-Lock: tempo máximo de espera (em segundos)
IDLE_LOCK_TIMEOUT: int = 30


# ---------------------------------------------------------------------------
# MaintenanceReport — relatório de uma execução do Janitor
# ---------------------------------------------------------------------------

@dataclass
class MaintenanceReport:
    """Relatório de uma rodada de manutenção."""
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
# JanitorService — Motor de Manutenção Autônoma
# ---------------------------------------------------------------------------

class JanitorService:
    """Background Janitor — manutenção autônoma do grafo.

    Thread Safety garantida pela SerializedWriteQueue do SqliteStore.
    Todas as escritas são enfileiradas atomicamente.

    Uso:
        janitor = JanitorService(store, vector_store, ingestion_manager)
        # Execução manual (single-shot):
        report = janitor.run_maintenance(project_uuid)
        # Execução contínua (background thread):
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

        # Idle-Lock: flag compartilhada para detectar mine() em andamento
        self._mine_active = threading.Event()
        self._mine_timestamp = 0.0

        # Background thread control
        self._bg_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_reports: list[MaintenanceReport] = []

        # Vector payloads em testes ou mock vector stores
        self.vector_payloads: dict[int, dict[str, Any]] = {}

        logger.info(
            "JanitorService inicializado: stale=%dd, zoom_threshold=%d, inactive=%dd, super_node_threshold=%d",
            stale_days, auto_zoom_threshold, inactive_days, super_node_threshold,
        )

    # ===================================================================
    # Idle-Lock API — chamado pelo IngestionManager
    # ===================================================================

    def signal_mine_start(self) -> None:
        """Sinaliza que mine() está em andamento (Idle-Lock ativo)."""
        self._mine_active.set()
        self._mine_timestamp = time.monotonic()
        logger.debug("Idle-Lock: mine() ativo — Janitor em espera.")

    def signal_mine_end(self) -> None:
        """Sinaliza que mine() terminou (Idle-Lock liberado)."""
        self._mine_active.clear()
        logger.debug("Idle-Lock: mine() finalizado — Janitor liberado.")

    def is_system_active(self) -> bool:
        """Retorna True se houver atividade ativa no sistema (mine ativo ou fila ocupada)."""
        if self._mine_active.is_set():
            elapsed = time.monotonic() - getattr(self, "_mine_timestamp", 0.0)
            if elapsed > 300.0:
                logger.warning(
                    "Idle-Lock: deadlock detectado! mine() ativo há %.1fs (> 300s). Forçando liberação da flag.",
                    elapsed
                )
                self._mine_active.clear()
            else:
                return True
        # Verifica a fila de escrita via API pública (sem violar encapsulamento)
        if self._store and not self._store.is_write_queue_empty():
            return True
        return False

    def _wait_for_idle(self) -> bool:
        """Espera até que mine() termine ou timeout expire.

        Returns:
            True se o sistema ficou idle, False se timeout.
        """
        if not self.is_system_active():
            return True

        logger.info("Idle-Lock: aguardando sistema ficar ocioso (timeout=%ds)...", IDLE_LOCK_TIMEOUT)
        start = time.monotonic()
        while self.is_system_active():
            if time.monotonic() - start > IDLE_LOCK_TIMEOUT:
                logger.warning("Idle-Lock: timeout — manutenção adiada.")
                return False
            time.sleep(0.5)

        return True

    # ===================================================================
    # RUN MAINTENANCE — Execução single-shot
    # ===================================================================

    def run_maintenance(self, project_uuid: str) -> MaintenanceReport:
        """Executa uma rodada completa de manutenção para um projeto.

        Fluxo:
            1. Idle-Lock check: adia se mine() ativo ou fila com tarefas.
            2. Decaimento de trajetórias stale.
            3. Sincronização SQLite ↔ ChromaDB (vetores órfãos).
            4. Arquivamento de nós inativos.
            5. Detecção de Comunidades (WITH RECURSIVE na tabela edges com FTS5).
            6. Sumarização das Comunidades e injeção vetorial.
            7. Auto-Zoom (L1/L2) se threshold atingido.
            8. FTS Rebuild se houve mudanças significativas.
        """
        t0 = time.perf_counter()
        report = MaintenanceReport(
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            project_uuid=project_uuid,
        )

        logger.info("=" * 50)
        logger.info("JANITOR: manutenção iniciada para %s", project_uuid)
        logger.info("=" * 50)

        # --- Idle-Lock ---
        if not self._wait_for_idle():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            logger.info("JANITOR: manutenção adiada (Idle-Lock).")
            return report

        # --- STEP 1: Decaimento de trajetórias ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.trajectories_decayed = self._decay_trajectories(project_uuid, report)

        # --- STEP 2: Sincronização atômica (vetores órfãos) ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.orphan_vectors_removed = self._sync_vectors(project_uuid, report)

        # --- STEP 3: Arquivamento de nós inativos ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        report.inactive_nodes_archived = self._archive_inactive_nodes(project_uuid, report)

        # --- STEP 4: Detecção de Comunidades (GraphRAG) ---
        if self.is_system_active():
            report.skipped_idle_lock = True
            report.duration_seconds = time.perf_counter() - t0
            return report
        communities = self.detect_communities(project_uuid)
        report.communities_detected = len(communities)

        # --- STEP 5: Sumarização e Injeção ---
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

        # --- STEP 7: FTS Rebuild (se houve mudanças) ---
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
            "JANITOR concluído em %.2fs: decayed=%d, orphans=%d, archived=%d, communities=%d, summaries=%d, zoom=%s",
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
    # STEP 1: Decaimento de Trajetórias
    # ===================================================================

    def _decay_trajectories(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Marca trajetórias stale como DECAYED."""
        try:
            decayed = self._store.bulk_decay_stale_trajectories(
                project_uuid, stale_threshold_days=self._stale_days,
            )
            if decayed > 0:
                logger.info(
                    "Decaimento: %d trajetórias marcadas como DECAYED (>%dd).",
                    decayed, self._stale_days,
                )
            else:
                logger.debug("Decaimento: nenhuma trajetória stale detectada.")
            return decayed
        except Exception as e:
            error_msg = f"Decaimento falhou: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 2: Sincronização Atômica (Reconciliation Loop)
    # ===================================================================

    def _sync_vectors(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Detecta e remove vetores órfãos no ChromaDB."""
        try:
            # Coleta IDs válidos do SQLite
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            valid_ids: set[int] = {n["id"] for n in nodes}

            # verify_sync retorna doc_ids órfãos
            orphans = self._vector.verify_sync(valid_ids)

            if not orphans:
                logger.debug("Sync: nenhum vetor órfão detectado.")
                return 0

            # Remove orphans em batch
            removed = self._vector.delete_batch(orphans)
            logger.info("Sync: %d vetores órfãos removidos.", removed)
            return removed

        except Exception as e:
            error_msg = f"Sync vetorial falhou: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 3: Arquivamento de Nós Inativos
    # ===================================================================

    def _archive_inactive_nodes(self, project_uuid: str, report: MaintenanceReport) -> int:
        """Marca nós sem acesso recente como ARCHIVED."""
        try:
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            threshold = datetime.utcnow() - timedelta(days=self._inactive_days)
            threshold_str = threshold.strftime("%Y-%m-%d %H:%M:%S")
            archived = 0

            for node in nodes:
                # Usa last_accessed se disponível, senão updated_at
                last_access = node.get("last_accessed") or node.get("updated_at") or node.get("created_at")
                if not last_access:
                    continue

                # Normaliza para string comparável
                if isinstance(last_access, str) and last_access < threshold_str:
                    try:
                        self._store.update_node(node["id"], status="ARCHIVED")
                        archived += 1
                    except Exception as e:
                        logger.debug("Falha ao arquivar nó %d: %s", node["id"], e)

            if archived > 0:
                logger.info(
                    "Arquivo: %d nós marcados como ARCHIVED (inativo >%dd).",
                    archived, self._inactive_days,
                )
            else:
                logger.debug("Arquivo: nenhum nó inativo detectado.")

            return archived

        except Exception as e:
            error_msg = f"Arquivamento de nós falhou: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)
            return 0

    # ===================================================================
    # STEP 4: Auto-Zoom (L1/L2 Trigger)
    # ===================================================================

    def _auto_zoom(self, project_uuid: str, report: MaintenanceReport) -> None:
        """Verifica se há mudanças suficientes para disparar Zoom Gear."""
        if not self._ingestion:
            logger.debug("Auto-Zoom: IngestionManager não configurado — ignorado.")
            return

        try:
            # Conta nós ativos — proxy para atividade recente
            nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")
            recent_count = len(nodes)

            if recent_count < self._zoom_threshold:
                logger.debug(
                    "Auto-Zoom: %d mudanças recentes < threshold %d — ignorado.",
                    recent_count, self._zoom_threshold,
                )
                return

            logger.info(
                "Auto-Zoom: %d mudanças recentes >= threshold %d — disparando Zoom Gear...",
                recent_count, self._zoom_threshold,
            )

            zoom_result = self._ingestion.generate_project_context(project_uuid)
            report.zoom_triggered = True
            report.zoom_l1_count = zoom_result.get("l1_count", 0)
            report.zoom_l2_summary = zoom_result.get("l2_summary", "")

            logger.info(
                "Auto-Zoom: %d L1 gerados, Bússola L2 = %.60s...",
                report.zoom_l1_count, report.zoom_l2_summary,
            )

        except Exception as e:
            error_msg = f"Auto-Zoom falhou: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)

    # ===================================================================
    # STEP 5: FTS Rebuild
    # ===================================================================

    def _fts_rebuild(self, report: MaintenanceReport) -> None:
        """Reconstrói o índice FTS5 após mudanças significativas."""
        try:
            self._store.fts_rebuild()
            report.fts_rebuilt = True
            logger.info("FTS Rebuild: índice reconstruído com sucesso.")
        except Exception as e:
            error_msg = f"FTS Rebuild falhou: {e}"
            logger.error(error_msg)
            report.errors.append(error_msg)

    # ===================================================================
    # STEP 4 & 5: Detecção de Comunidades e Sumarização (GraphRAG)
    # ===================================================================

    def detect_communities(self, project_uuid: str) -> dict[int, list[int]]:
        """Detecta comunidades no grafo usando WITH RECURSIVE e FTS5.
        Retorna um dicionário mapeando o ID do super-nó para a lista de IDs dos nós pertencentes à comunidade.
        """
        communities: dict[int, list[int]] = {}
        try:
            # 1. Encontra os super-nós (in_degree >= self._super_node_threshold)
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
            logger.info("Janitor detectou %d super-nós (threshold=%d) no projeto %s.",
                        len(super_node_ids), self._super_node_threshold, project_uuid)
            
            # 2. Para cada super-nó, busca recursivamente a comunidade associada
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
            logger.error("Falha na detecção de comunidades: %s", e)
            
        return communities

    def generate_and_persist_community_summaries(
        self,
        project_uuid: str,
        communities: dict[int, list[int]],
    ) -> list[dict[str, Any]]:
        """Gera resumos para as comunidades detectadas, salva como nós INSIGHT e atualiza o Qdrant."""
        from typing import Any
        import json
        
        summaries: list[dict[str, Any]] = []
        for community_id, node_ids in communities.items():
            # Proteção de Concorrência (Idle-Lock): suspende se o sistema ficar ativo
            if self.is_system_active():
                logger.warning("Janitor: suspensão de comunidade ativada devido a atividade no barramento.")
                break
                
            # Busca os detalhes dos nós na comunidade
            node_details = []
            try:
                placeholders = ",".join("?" for _ in node_ids)
                node_details = self._store.execute_read_sql(
                    f"SELECT id, label, summary, node_type, type, tags FROM nodes WHERE id IN ({placeholders})",
                    tuple(node_ids)
                )
            except Exception as e:
                logger.error("Falha ao carregar detalhes dos nós da comunidade %d: %s", community_id, e)
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
            
            # Delega ao IngestionManager que encapsula o acesso ao LLM
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

            # Salva o INSIGHT no SQLite
            try:
                insight_node_id = self._store.create_node(
                    project_uuid=project_uuid,
                    label=f"community_{community_id}_summary",
                    summary=summary_text,
                    node_type="INSIGHT",
                    type_="community_summary",
                    tags=sorted(list(set(tags))),
                )
                
                # Cria a aresta conectando o INSIGHT ao super-nó
                self._store.create_edge(
                    source_id=insight_node_id,
                    target_id=community_id,
                    relation_type="summarizes",
                    weight=1.0,
                )
                
                # Injeta os IDs de comunidade de forma direta nos metadados vetoriais
                for nid in node_ids:
                    self._update_vector_metadata(nid, project_uuid, community_id)
                    
                summaries.append({
                    "community_id": community_id,
                    "insight_node_id": insight_node_id,
                    "summary": summary_text,
                    "tags": sorted(list(set(tags))),
                })
                
            except Exception as e:
                logger.error("Falha ao salvar INSIGHT da comunidade %d no SQLite: %s", community_id, e)

        return summaries

    def _update_vector_metadata(self, node_id: int, project_uuid: str, community_id: int) -> None:
        """Atualiza a metadata no vector store injetando o community_id."""
        metadata = {
            "node_id": node_id,
            "project_uuid": project_uuid,
            "community_id": community_id,
        }

        # 1. Armazena no cache local do Janitor (útil para testes/mocks)
        self.vector_payloads[node_id] = metadata

        # 2. Atualiza via API pública (sem acessar _collection diretamente)
        if self._vector:
            doc_id = f"node_{node_id}"
            self._vector.update_metadata(doc_id, metadata)

    # ===================================================================
    # BACKGROUND THREAD — Execução contínua
    # ===================================================================

    def start_background(
        self,
        project_uuid: str,
        interval: int = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        """Inicia o Janitor em background thread.

        A thread executa run_maintenance() a cada `interval` segundos.
        Thread-safe: usa SerializedWriteQueue do SqliteStore.
        """
        if self._bg_thread and self._bg_thread.is_alive():
            logger.warning("Janitor background já está rodando.")
            return

        self._stop_event.clear()

        def _loop():
            logger.info("Janitor background iniciado (interval=%ds).", interval)
            while not self._stop_event.is_set():
                try:
                    self.run_maintenance(project_uuid)
                except Exception as e:
                    logger.error("Janitor background — erro não tratado: %s", e)

                # Sleep interruptível
                self._stop_event.wait(timeout=interval)

            logger.info("Janitor background encerrado.")

        self._bg_thread = threading.Thread(
            target=_loop,
            name="grafo-janitor",
            daemon=True,
        )
        self._bg_thread.start()
        logger.info("Janitor background thread started: name=%s", self._bg_thread.name)

    def stop_background(self, timeout: float = 10.0) -> None:
        """Para a background thread do Janitor."""
        if not self._bg_thread or not self._bg_thread.is_alive():
            logger.debug("Janitor background não está rodando.")
            return

        logger.info("Parando Janitor background...")
        self._stop_event.set()
        self._bg_thread.join(timeout=timeout)

        if self._bg_thread.is_alive():
            logger.warning("Janitor background não parou dentro do timeout de %.1fs.", timeout)
        else:
            logger.info("Janitor background parado com sucesso.")

    @property
    def is_running(self) -> bool:
        """Verifica se a background thread está ativa."""
        return self._bg_thread is not None and self._bg_thread.is_alive()

    @property
    def last_reports(self) -> list[MaintenanceReport]:
        """Histórico de relatórios de manutenção (últimos)."""
        return list(self._last_reports)

    # ===================================================================
    # FULL MAINTENANCE — todos os projetos
    # ===================================================================

    def run_all_projects(self) -> list[MaintenanceReport]:
        """Executa manutenção em TODOS os projetos registrados."""
        reports: list[MaintenanceReport] = []
        try:
            projects = self._store.list_projects()
        except Exception as e:
            logger.error("Falha ao listar projetos para manutenção global: %s", e)
            return reports

        for project in projects:
            puuid = project.get("uuid", "")
            if not puuid:
                continue
            try:
                report = self.run_maintenance(puuid)
                reports.append(report)
            except Exception as e:
                logger.error("Manutenção falhou para projeto %s: %s", puuid, e)

        logger.info("Manutenção global: %d projetos processados.", len(reports))
        return reports
