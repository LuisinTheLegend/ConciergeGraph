"""
interface/watcher.py — SDD-SURVIVAL-01 (Hardened & Resilient)

Reactive File Watcher with Early Ignore Filtering (Early Exit) and
Atomic Alias Tracking.

Captures write events on the local file system and applies
early discard rules based on .conciergeignore patterns,
using pathspec (Git Wildmatch) for ultra-fast matching.

Hardening protections applied:
  - Zombie Protection: if a deleted file does not match in AliasTracker,
    timeout purge automatically triggers on_delete_callback.
  - Startup and Offline Deletion Protection: hydrate_known_hashes detects files
    removed while the server was offline and purges them via cold deletion.
  - Robust handling against FileNotFoundError in concurrent events.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import pathspec
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class ConciergeFileSystemHandler(FileSystemEventHandler):
    """
    Captures write events on the local filesystem and applies early exit
    rules based on the ignore spec, integrating with AliasTracker
    for move/rename reconciliation (SDD-18).
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
        """Connects AliasTracker timeout purge to on_delete_callback."""
        def _purge_alias_wrapper(purged_rel_path: str):
            p_abs = os.path.join(self.project_path, purged_rel_path)
            if self.on_delete_callback:
                try:
                    logger.info("[WATCHER] Alias purge triggering physical deletion of: %s", p_abs)
                    self.on_delete_callback(p_abs)
                except Exception as e:
                    logger.error("[WATCHER] Async purge failed for %s: %s", p_abs, e)
        self.alias_tracker.on_purge_callback = _purge_alias_wrapper

    def set_alias_tracker(self, alias_tracker) -> None:
        """Allows injection or update of AliasTracker with callback reconnection."""
        self.alias_tracker = alias_tracker
        if self.alias_tracker and self.on_delete_callback:
            self._connect_alias_purge_callback()

    def hydrate_known_hashes(self, db_manager: Any = None, initial_paths: Optional[List[str]] = None) -> None:
        """
        Hydrates _known_hashes cache from relational database or file list.
        If a file listed in the database does not physically exist on disk (offline deletion),
        catches FileNotFoundError and triggers cold deletion (on_delete_callback) to clean
        orphan records, or uses the database hash as safe backup.
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
                # Offline deletion detected at startup
                logger.info("[WATCHER] Missing file detected at startup (offline deletion): %s", abs_path)
                if self.on_delete_callback:
                    try:
                        self.on_delete_callback(abs_path)
                    except Exception as e:
                        logger.error("[WATCHER] Error cleaning offline deleted file %s: %s", abs_path, e)
            except Exception as e:
                logger.debug("[WATCHER] Non-fatal error hydrating hash for %s: %s", abs_path, e)
                if rel_path in db_hashes:
                    self._known_hashes[rel_path] = db_hashes[rel_path]

    def on_modified(self, event):
        if event.is_directory:
            return

        abs_path = os.path.abspath(event.src_path)
        rel_path = os.path.relpath(abs_path, self.project_path)

        # 🛡️ Security Gate / Early Exit Discard
        if self.ignore_spec.match_file(rel_path):
            return

        if self.hash_calculator:
            try:
                self._known_hashes[rel_path] = self.hash_calculator(abs_path)
            except (FileNotFoundError, OSError):
                # File removed during concurrent write
                if self.on_delete_callback:
                    self.on_delete_callback(abs_path)
                return
            except Exception:
                pass

        # Passed security gate: trigger valid delta processing callback
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

        # Fallback: retrieve last persisted hash from database
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

        # Verify whether the hash is valid for alias reconciliation attempt
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
