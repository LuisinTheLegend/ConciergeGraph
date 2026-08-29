"""
interface/watcher.py — SDD-SURVIVAL-01 (Hardened & Resilient)

Monitor de Arquivos Reativo com Filtro Precoce de Ignorados (Early Exit) e
Rastreamento Atômico de Codinomes (Alias Tracking).

Captura eventos de gravação no sistema de arquivos local e aplica
regras de descarte precoce baseadas nos padrões do .conciergeignore,
utilizando pathspec (Git Wildmatch) para correspondência ultra-rápida.

Blindagens aplicadas:
  - Proteção de Zumbis: se um arquivo deletado não casar no AliasTracker,
    o expurgo por timeout dispara automaticamente on_delete_callback.
  - Proteção de Startup e Offline Deletions: hydrate_known_hashes detecta arquivos
    removidos enquanto o servidor estava offline e os limpa via deleção fria.
  - Tratamento robusto contra FileNotFoundError em eventos concorrentes.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import pathspec
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class ConciergeFileSystemHandler(FileSystemEventHandler):
    """
    Captura eventos de gravação no sistema de arquivos local e aplica
    regras de descarte precoce (Early Exit) baseadas no arquivo de ignore,
    além de integrar com o AliasTracker para reconciliação de movimentações (SDD-18).
    """

    def __init__(
        self,
        project_path: str,
        ignore_spec: pathspec.PathSpec,
        on_valid_change_callback,
        alias_tracker=None,
        hash_calculator=None,
        on_delete_callback=None,
    ):
        super().__init__()
        self.project_path = os.path.abspath(project_path)
        self.ignore_spec = ignore_spec
        self.on_valid_change_callback = on_valid_change_callback
        self.alias_tracker = alias_tracker
        self.hash_calculator = hash_calculator
        self.on_delete_callback = on_delete_callback
        self._known_hashes: Dict[str, str] = {}

        if self.alias_tracker and self.on_delete_callback:
            self._connect_alias_purge_callback()

    def _connect_alias_purge_callback(self) -> None:
        """Conecta o expurgo de timeout do AliasTracker ao on_delete_callback."""
        def _purge_alias_wrapper(purged_rel_path: str):
            p_abs = os.path.join(self.project_path, purged_rel_path)
            if self.on_delete_callback:
                try:
                    logger.info("[WATCHER] Expurgo de alias acionando deleção real de: %s", p_abs)
                    self.on_delete_callback(p_abs)
                except Exception as e:
                    logger.error("[WATCHER] Falha no expurgo assíncrono de %s: %s", p_abs, e)
        self.alias_tracker.on_purge_callback = _purge_alias_wrapper

    def set_alias_tracker(self, alias_tracker) -> None:
        """Permite injeção ou atualização do AliasTracker com reconexão de callback."""
        self.alias_tracker = alias_tracker
        if self.alias_tracker and self.on_delete_callback:
            self._connect_alias_purge_callback()

    def hydrate_known_hashes(self, db_manager: Any = None, initial_paths: Optional[List[str]] = None) -> None:
        """
        Hidrata o cache _known_hashes a partir do banco relacional ou lista de arquivos.
        Se um arquivo listado no banco não existir fisicamente no disco (deleção offline),
        captura o FileNotFoundError e aciona a deleção fria (on_delete_callback) para limpar
        registros órfãos, ou utiliza o hash do banco como backup seguro.
        """
        paths_to_check = set()
        db_hashes = {}

        if db_manager is not None:
            try:
                rows = db_manager.read_query("SELECT path, structural_hash FROM files;")
                for r in rows:
                    if r and r[0]:
                        p_rel = r[0]
                        paths_to_check.add(p_rel)
                        if len(r) > 1 and r[1]:
                            db_hashes[p_rel] = r[1]
            except Exception:
                try:
                    rows = db_manager.read_query("SELECT path FROM files;")
                    for r in rows:
                        if r and r[0]:
                            paths_to_check.add(r[0])
                except Exception:
                    pass

        if initial_paths:
            paths_to_check.update(initial_paths)

        for rel_path in paths_to_check:
            abs_path = os.path.abspath(os.path.join(self.project_path, rel_path))
            try:
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"Arquivo ausente no disco: {abs_path}")

                if self.hash_calculator:
                    computed = self.hash_calculator(abs_path)
                    if computed:
                        self._known_hashes[rel_path] = computed
                elif rel_path in db_hashes:
                    self._known_hashes[rel_path] = db_hashes[rel_path]
            except (FileNotFoundError, OSError):
                # Deleção offline detectada na inicialização
                logger.info("[WATCHER] Arquivo ausente detectado no startup (deleção offline): %s", abs_path)
                if self.on_delete_callback:
                    try:
                        self.on_delete_callback(abs_path)
                    except Exception as e:
                        logger.error("[WATCHER] Erro ao limpar arquivo deletado offline %s: %s", abs_path, e)
            except Exception as e:
                logger.debug("[WATCHER] Erro não fatal ao hidratar hash de %s: %s", abs_path, e)
                if rel_path in db_hashes:
                    self._known_hashes[rel_path] = db_hashes[rel_path]

    def on_modified(self, event):
        if event.is_directory:
            return

        abs_path = os.path.abspath(event.src_path)
        rel_path = os.path.relpath(abs_path, self.project_path)

        # 🛡️ Portão de Segurança / Descarte Precoce (Early Exit)
        if self.ignore_spec.match_file(rel_path):
            return

        if self.hash_calculator:
            try:
                self._known_hashes[rel_path] = self.hash_calculator(abs_path)
            except (FileNotFoundError, OSError):
                # Arquivo removido no meio da escrita concorrente
                if self.on_delete_callback:
                    self.on_delete_callback(abs_path)
                return
            except Exception:
                pass

        # Passou pelo portão: executa o callback de processamento delta
        self.on_valid_change_callback(abs_path)

    def on_created(self, event):
        if event.is_directory:
            return

        abs_path = os.path.abspath(event.src_path)
        rel_path = os.path.relpath(abs_path, self.project_path)

        if self.ignore_spec.match_file(rel_path):
            return

        if self.alias_tracker and self.hash_calculator:
            try:
                new_hash = self.hash_calculator(abs_path)
            except (FileNotFoundError, OSError):
                new_hash = ""
            except Exception:
                new_hash = ""

            if new_hash and getattr(self.alias_tracker, "is_valid_hash", lambda h: True)(new_hash):
                self._known_hashes[rel_path] = new_hash
                matched_old = self.alias_tracker.check_and_resolve_creation(
                    rel_path, new_hash
                )
                if matched_old:
                    self.alias_tracker.apply_alias_migration(matched_old, rel_path)
                    return

        self.on_valid_change_callback(abs_path)

    def on_deleted(self, event):
        if event.is_directory:
            return

        abs_path = os.path.abspath(event.src_path)
        rel_path = os.path.relpath(abs_path, self.project_path)

        if self.ignore_spec.match_file(rel_path):
            return

        structural_hash = self._known_hashes.pop(rel_path, None)

        if not structural_hash and self.hash_calculator:
            try:
                structural_hash = self.hash_calculator(abs_path)
            except (FileNotFoundError, OSError):
                structural_hash = None
            except Exception:
                pass

        # Fallback: busca último hash persistido no banco
        if not structural_hash and self.alias_tracker and hasattr(self.alias_tracker, "db") and self.alias_tracker.db:
            try:
                rows = self.alias_tracker.db.read_query(
                    "SELECT structural_hash FROM files WHERE path = ? LIMIT 1;",
                    (rel_path,),
                )
                if rows and rows[0][0]:
                    structural_hash = rows[0][0]
            except Exception:
                pass

        # Verifica se o hash é válido para tentativa de reconciliação de alias
        is_eligible = (
            structural_hash
            and getattr(self.alias_tracker, "is_valid_hash", lambda h: True)(structural_hash)
        )

        if self.alias_tracker and is_eligible:
            self.alias_tracker.register_deletion(rel_path, structural_hash)
        elif self.on_delete_callback:
            self.on_delete_callback(abs_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        src_abs = os.path.abspath(event.src_path)
        dest_abs = os.path.abspath(event.dest_path)
        src_rel = os.path.relpath(src_abs, self.project_path)
        dest_rel = os.path.relpath(dest_abs, self.project_path)

        if self.ignore_spec.match_file(src_rel) and self.ignore_spec.match_file(dest_rel):
            return

        if self.alias_tracker:
            self.alias_tracker.apply_alias_migration(src_rel, dest_rel)
            return

        self.on_valid_change_callback(dest_abs)
