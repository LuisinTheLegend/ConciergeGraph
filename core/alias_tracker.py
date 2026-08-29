"""
core/alias_tracker.py — SDD-SURVIVAL-18 (Hardened & Resilient)

Alias Tracking por Hash Estrutural (SSH) para Preservação de Trajetórias Históricas.

Intercepta refatorações físicas de renomeação ou movimentação de arquivos na IDE,
associando deleções e criações que compartilham a mesma assinatura estrutural hash (SSH)
dentro de um buffer temporal de reconciliação, aplicando migração atômica de caminhos
sem perda de histórico, conexões topológicas ou checkpoints de agentes.

Blindagens aplicadas:
  - Rejeição estrita de payloads vazios ou boilerplates ("e3b0c4...", "", "deleted_hash")
  - Timeout assíncrono com expurgo automático: se nenhum arquivo corresponder dentro da
    janela temporal, invoca on_purge_callback para evitar registros zumbis no SQLite.
  - Sincronização segura entre threads via threading.Lock e cancelamento de timers.
"""

import time
import logging
import threading
from typing import Dict, Optional, Tuple, Any, Callable, List

logger = logging.getLogger(__name__)

EMPTY_SSH_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
INVALID_HASHES = {EMPTY_SSH_HASH, "deleted_hash", "", None}


class AliasTracker:
    """
    Rastreador de codinomes (aliases) estruturais temporais para preservação
    de trajetórias históricas e topologia em operações de renomeação / movimentação.
    """

    def __init__(
        self,
        db_manager: Any,
        hash_generator_callback: Any,
        buffer_window_seconds: float = 1.0,
        on_purge_callback: Optional[Callable[[str], None]] = None,
    ):
        self.db = db_manager
        self.hash_gen = hash_generator_callback
        self.buffer_window = buffer_window_seconds
        self.on_purge_callback = on_purge_callback

        # Buffer de exclusões pendentes: {old_path: (structural_hash, timestamp_of_deletion)}
        self.pending_deletions: Dict[str, Tuple[str, float]] = {}
        # Timers pendentes para expurgo automático pós-timeout: {old_path: threading.Timer}
        self.pending_timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    @staticmethod
    def is_valid_hash(structural_hash: Optional[str]) -> bool:
        """Valida se o hash representa uma estrutura sintática real não trivial."""
        if not structural_hash:
            return False
        if len(structural_hash) < 5:
            return False
        if structural_hash in INVALID_HASHES:
            return False
        return True

    def register_deletion(self, path: str, structural_hash: str) -> None:
        """
        Registra uma deleção pendente no buffer temporal de alias.
        Se o hash for inválido/vazio, purga imediatamente via callback.
        Caso contrário, armazena e inicia um timer assíncrono para expurgo em caso de timeout.
        """
        if not self.is_valid_hash(structural_hash):
            logger.debug("[ALIAS-TRACKER] Hash inválido ou vazio para %s. Purgando imediatamente.", path)
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Erro no expurgo imediato de hash inválido para %s: %s", path, e)
            return

        with self._lock:
            # Cancela timer anterior se já existia para este caminho
            old_timer = self.pending_timers.pop(path, None)
            if old_timer:
                old_timer.cancel()

            self.pending_deletions[path] = (structural_hash, time.time())

            # Agenda expurgo assíncrono caso nenhuma criação ocorra na janela
            timer = threading.Timer(self.buffer_window, self._on_timeout_expire, args=[path])
            timer.daemon = True
            timer.start()
            self.pending_timers[path] = timer

    def _on_timeout_expire(self, path: str) -> None:
        """Chamado pelo timer quando a janela de espera expira sem resolução de criação."""
        with self._lock:
            self.pending_timers.pop(path, None)
            entry = self.pending_deletions.pop(path, None)

        if entry is not None and self.on_purge_callback:
            logger.info("[ALIAS-TRACKER] Timeout de alias expirado para '%s'. Purgando nó do banco.", path)
            try:
                self.on_purge_callback(path)
            except Exception as e:
                logger.error("[ALIAS-TRACKER] Erro ao invocar on_purge_callback no timeout para %s: %s", path, e)

    def check_and_resolve_creation(
        self, new_path: str, new_structural_hash: str
    ) -> Optional[str]:
        """
        Verifica se a criação de um novo arquivo corresponde a um arquivo deletado recentemente
        com a mesma assinatura estrutural hash (SSH). Retorna o caminho antigo se for um alias.
        """
        if not self.is_valid_hash(new_structural_hash):
            return None

        current_time = time.time()
        matched_old_path: Optional[str] = None
        candidates = []
        expired_paths: List[str] = []

        with self._lock:
            for old_path, (old_hash, deleted_at) in list(self.pending_deletions.items()):
                if current_time - deleted_at > self.buffer_window:
                    expired_paths.append(old_path)
                elif old_hash == new_structural_hash:
                    candidates.append(old_path)

            # Expurgar do buffer os itens expirados
            for path in expired_paths:
                timer = self.pending_timers.pop(path, None)
                if timer:
                    timer.cancel()
                self.pending_deletions.pop(path, None)

            # Se houver exatamente um candidato exclusivo, resolvemos o Alias!
            if len(candidates) == 1:
                matched_old_path = candidates[0]
                timer = self.pending_timers.pop(matched_old_path, None)
                if timer:
                    timer.cancel()
                self.pending_deletions.pop(matched_old_path, None)

        # Dispara expurgo para os itens expirados que não casaram
        for path in expired_paths:
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Erro no expurgo de caminho expirado %s: %s", path, e)

        return matched_old_path

    def purge_expired(self, current_time: Optional[float] = None) -> List[str]:
        """Purga manualmente todos os itens cujo timeout estourou."""
        if current_time is None:
            current_time = time.time()
        expired: List[str] = []
        with self._lock:
            for old_path, (_, deleted_at) in list(self.pending_deletions.items()):
                if current_time - deleted_at > self.buffer_window:
                    timer = self.pending_timers.pop(old_path, None)
                    if timer:
                        timer.cancel()
                    self.pending_deletions.pop(old_path, None)
                    expired.append(old_path)

        for path in expired:
            if self.on_purge_callback:
                try:
                    self.on_purge_callback(path)
                except Exception as e:
                    logger.error("[ALIAS-TRACKER] Erro ao purgar %s: %s", path, e)
        return expired

    def cancel_all_timers(self) -> None:
        """Cancela todos os timers pendentes (para teardown de testes e shutdown)."""
        with self._lock:
            for timer in self.pending_timers.values():
                try:
                    timer.cancel()
                except Exception:
                    pass
            self.pending_timers.clear()

    def apply_alias_migration(self, old_path: str, new_path: str) -> bool:
        """Executa a mutação atômica do caminho físico de arquivo preservando o histórico."""
        timestamp = time.time()

        # Descobre colunas de ast_edges (parent_node_id vs parent_node)
        parent_col = "parent_node_id"
        child_col = "child_node_id"
        try:
            cols = [
                r[1]
                for r in self.db.read_query("PRAGMA table_info(ast_edges);")
            ]
            if "parent_node" in cols and "parent_node_id" not in cols:
                parent_col = "parent_node"
                child_col = "child_node"
        except Exception:
            pass

        # Descobre tabelas existentes
        existing_tables = set()
        try:
            t_rows = self.db.read_query(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            existing_tables = {r[0] for r in t_rows}
        except Exception:
            pass

        queries = []
        if "files" in existing_tables:
            queries.append((
                "UPDATE files SET path = ?, last_modified = ?, is_dirty = 1 WHERE path = ?;",
                (new_path, timestamp, old_path),
            ))
        if "nodes" in existing_tables:
            queries.append((
                "UPDATE nodes SET label = ? WHERE label = ?;",
                (new_path, old_path),
            ))

        if "ast_edges" in existing_tables:
            queries.extend([
                (
                    f"UPDATE ast_edges SET {parent_col} = ? WHERE {parent_col} = ?;",
                    (new_path, old_path),
                ),
                (
                    f"UPDATE ast_edges SET {child_col} = ? WHERE {child_col} = ?;",
                    (new_path, old_path),
                ),
            ])

        if "fsm_checkpoints" in existing_tables:
            queries.append((
                "UPDATE fsm_checkpoints SET task_id = ? WHERE task_id = ?;",
                (new_path, old_path),
            ))

        try:
            for query, params in queries:
                if hasattr(self.db, "execute_write"):
                    success, res = self.db.execute_write(query, params)
                    if not success:
                        raise Exception(f"Transação falhou: {res}")
                else:
                    self.db.write_query(query, params)
            return True
        except Exception as e:
            logger.error(
                "[ALIAS-TRACKER] Falha crítica ao migrar alias %s -> %s: %s",
                old_path,
                new_path,
                e,
            )
            return False
