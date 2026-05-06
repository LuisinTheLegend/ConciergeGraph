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
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._ingestion = ingestion_manager
        self._stale_days = stale_days
        self._zoom_threshold = auto_zoom_threshold
        self._inactive_days = inactive_days

        # Idle-Lock: flag compartilhada para detectar mine() em andamento
        self._mine_active = threading.Event()

        # Background thread control
        self._bg_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_reports: list[MaintenanceReport] = []

        logger.info(
            "JanitorService inicializado: stale=%dd, zoom_threshold=%d, inactive=%dd",
            stale_days, auto_zoom_threshold, inactive_days,
        )

    # ===================================================================
    # Idle-Lock API — chamado pelo IngestionManager
    # ===================================================================

    def signal_mine_start(self) -> None:
        """Sinaliza que mine() está em andamento (Idle-Lock ativo)."""
        self._mine_active.set()
        logger.debug("Idle-Lock: mine() ativo — Janitor em espera.")

    def signal_mine_end(self) -> None:
        """Sinaliza que mine() terminou (Idle-Lock liberado)."""
        self._mine_active.clear()
        logger.debug("Idle-Lock: mine() finalizado — Janitor liberado.")

    def _wait_for_idle(self) -> bool:
        """Espera até que mine() termine ou timeout expire.

        Returns:
            True se o sistema ficou idle, False se timeout.
        """
        if not self._mine_active.is_set():
            return True

        logger.info("Idle-Lock: aguardando mine() finalizar (timeout=%ds)...", IDLE_LOCK_TIMEOUT)
        # Espera o evento ser *cleared* (mine finalizado)
        start = time.monotonic()
        while self._mine_active.is_set():
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
            1. Idle-Lock check: adia se mine() ativo.
            2. Decaimento de trajetórias stale.
            3. Sincronização SQLite ↔ ChromaDB (vetores órfãos).
            4. Arquivamento de nós inativos.
            5. Auto-Zoom (L1/L2) se threshold atingido.
            6. FTS Rebuild se houve mudanças significativas.
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
        report.trajectories_decayed = self._decay_trajectories(project_uuid, report)

        # --- STEP 2: Sincronização atômica (vetores órfãos) ---
        report.orphan_vectors_removed = self._sync_vectors(project_uuid, report)

        # --- STEP 3: Arquivamento de nós inativos ---
        report.inactive_nodes_archived = self._archive_inactive_nodes(project_uuid, report)

        # --- STEP 4: Auto-Zoom ---
        self._auto_zoom(project_uuid, report)

        # --- STEP 5: FTS Rebuild (se houve mudanças) ---
        changes = (report.trajectories_decayed
                   + report.orphan_vectors_removed
                   + report.inactive_nodes_archived)
        if changes > 0:
            self._fts_rebuild(report)

        report.duration_seconds = time.perf_counter() - t0

        logger.info("=" * 50)
        logger.info(
            "JANITOR concluído em %.2fs: decayed=%d, orphans=%d, archived=%d, zoom=%s",
            report.duration_seconds,
            report.trajectories_decayed,
            report.orphan_vectors_removed,
            report.inactive_nodes_archived,
            report.zoom_triggered,
        )
        logger.info("=" * 50)

        self._last_reports.append(report)
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
