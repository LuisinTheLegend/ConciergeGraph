"""
ingestion/crawler.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Intelligent filesystem scanning for the Apex Ingestion Engine.

Responsibilities:
    - Recursively traverse project directories.
    - Respect ignore patterns (.gitignore + IGNORE_DIRS from config).
    - Calculate SHA256 of each file for delta detection.
    - Compare hashes with SqliteStore to skip unmodified files.
    - Classify files by type (code, doc, config, conversation).
    - Detect deleted files for Garbage Collection.

Integration:
    - SqliteStore.find_node_by_hash(project_uuid, hash) → checks if already processed.
    - SqliteStore.get_nodes_by_project(project_uuid) → lists existing nodes for GC.
    - Result is a CrawlReport consumed by the Parser/Orchestrator.

Identity Preservation (Path-Agnostic ID):
    The doc_id of each node is derived from the content (hash), not the path.
    If the file moves to another folder, the hash changes → new node is created.
    If the file is renamed without content changes → same hash → reuses the node.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import os
from storage import SqliteStore
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("grafo-concierge.crawler")


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

class FileCategory(str, Enum):
    """File categories automatically detected by the Crawler.

    Mapping per spec v3.8:
        code         → .py, .js, .ts, .go, .rs, .java, .cpp, .c, .rb
        doc          → .md, .txt, .rst, .adoc
        config       → .json, .yaml, .yml, .toml, .env, .ini, .cfg
        conversation → .log, .chat
        unknown      → unmapped extensions
    """
    CODE = "code"
    DOC = "doc"
    CONFIG = "config"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


# Extension -> category mapping (per API v3.8 table)
EXTENSION_MAP: dict[str, FileCategory] = {
    # Code
    ".py": FileCategory.CODE,
    ".js": FileCategory.CODE,
    ".ts": FileCategory.CODE,
    ".tsx": FileCategory.CODE,
    ".jsx": FileCategory.CODE,
    ".go": FileCategory.CODE,
    ".rs": FileCategory.CODE,
    ".java": FileCategory.CODE,
    ".cpp": FileCategory.CODE,
    ".c": FileCategory.CODE,
    ".h": FileCategory.CODE,
    ".hpp": FileCategory.CODE,
    ".rb": FileCategory.CODE,
    ".cs": FileCategory.CODE,
    ".swift": FileCategory.CODE,
    ".kt": FileCategory.CODE,
    ".php": FileCategory.CODE,
    ".lua": FileCategory.CODE,
    ".sh": FileCategory.CODE,
    ".bash": FileCategory.CODE,
    ".ps1": FileCategory.CODE,
    ".sql": FileCategory.CODE,
    ".r": FileCategory.CODE,
    ".scala": FileCategory.CODE,
    ".ex": FileCategory.CODE,
    ".exs": FileCategory.CODE,
    # Doc
    ".md": FileCategory.DOC,
    ".txt": FileCategory.DOC,
    ".rst": FileCategory.DOC,
    ".adoc": FileCategory.DOC,
    ".org": FileCategory.DOC,
    # Config
    ".json": FileCategory.CONFIG,
    ".yaml": FileCategory.CONFIG,
    ".yml": FileCategory.CONFIG,
    ".toml": FileCategory.CONFIG,
    ".env": FileCategory.CONFIG,
    ".ini": FileCategory.CONFIG,
    ".cfg": FileCategory.CONFIG,
    ".xml": FileCategory.CONFIG,
    ".properties": FileCategory.CONFIG,
    # Conversation
    ".log": FileCategory.CONVERSATION,
    ".chat": FileCategory.CONVERSATION,
}


# ---------------------------------------------------------------------------
# CrawlResult — individual result of a scanned file
# ---------------------------------------------------------------------------

@dataclass
class CrawlResult:
    """Result of the scan of a single file.

    Attributes:
        absolute_path: Absolute path in the filesystem.
        relative_path: Relative path to the project's source_path.
        file_hash: SHA256 of the file content.
        category: Automatic classification (code, doc, config, conversation).
        extension: File extension (e.g. '.py').
        size_bytes: Size in bytes.
        is_new: True if the hash does not exist in SqliteStore (new or modified file).
        existing_node_id: If not new, the ID of the existing node in SQLite.
    """
    absolute_path: str
    relative_path: str
    file_hash: str
    category: FileCategory
    extension: str
    size_bytes: int
    is_new: bool = True
    existing_node_id: Optional[int] = None


@dataclass
class CrawlReport:
    """Consolidated report of a crawl operation.

    Attributes:
        new_files: New or modified files (for processing).
        unchanged_files: Files whose hash has not changed (skip).
        deleted_node_ids: SQLite node IDs whose files no longer exist (GC).
        categories: Count per category.
        total_scanned: Total scanned files.
    """
    new_files: list[CrawlResult] = field(default_factory=list)
    unchanged_files: list[CrawlResult] = field(default_factory=list)
    deleted_node_ids: list[int] = field(default_factory=list)
    categories: dict[str, int] = field(default_factory=dict)
    total_scanned: int = 0


# ---------------------------------------------------------------------------
# GitignoreParser — robust parser for .gitignore
# ---------------------------------------------------------------------------

class GitignoreParser:
    """Parser for .gitignore with support for common patterns.

    Supports:
        - Comments (# ...) and blank lines.
        - Negation (! pattern → do not ignore).
        - Explicit directories (dir/ → directories only).
        - Wildcards (*, **, ?).
        - Anchored patterns (starting with /).

    Limitations:
        - Does not support nested .gitignore in subdirectories (root only).
        - Complex patterns with ranges [a-z] are treated as simple globs.
    """

    def __init__(self) -> None:
        """Initializes the parser with empty lists."""
        self._patterns: list[str] = []
        self._negations: list[str] = []
        self._dir_only_patterns: list[str] = []

    def add_patterns(self, patterns: list[str]) -> None:
        """Adds a list of ignore patterns programmatically.

        Allows loading default safety patterns (DEFAULT_IGNORE_PATTERNS)
        without depending on a file on disk. Follows the same semantics as .gitignore.

        Args:
            patterns: List of patterns in .gitignore format.
        """
        for raw in patterns:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("!"):
                negation = stripped[1:].strip()
                if negation:
                    self._negations.append(negation)
                continue
            if stripped.endswith("/"):
                self._dir_only_patterns.append(stripped.rstrip("/"))
                self._patterns.append(stripped.rstrip("/"))
                self._patterns.append(stripped.rstrip("/") + "/**")
                continue
            if stripped.startswith("/"):
                stripped = stripped[1:]
            self._patterns.append(stripped)

        logger.debug(
            "GitignoreParser.add_patterns: +%d entradas → %d padrões totais.",
            len(patterns), len(self._patterns),
        )

    def load(self, gitignore_path: str) -> None:
        """Loads and parses a .gitignore file.

        Ignores blank lines and comments.
        Negation patterns (!) are stored separately.
        Directory patterns (ending in /) are stored separately.

        Args:
            gitignore_path: Absolute path to the .gitignore.
        """
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                raw_lines = f.readlines()
        except (OSError, IOError) as e:
            logger.warning("Could not read .gitignore at %s: %s", gitignore_path, e)
            return

        for line in raw_lines:
            # Remove trailing whitespace (keeps leading for space patterns)
            stripped = line.rstrip()

            # Ignores empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Remove trailing escaped space (\\ at the end)
            if stripped.endswith("\\ "):
                stripped = stripped[:-2] + " "

            # Negation patterns
            if stripped.startswith("!"):
                negation = stripped[1:].strip()
                if negation:
                    self._negations.append(negation)
                continue

            # Directory patterns (ending in /)
            if stripped.endswith("/"):
                self._dir_only_patterns.append(stripped.rstrip("/"))
                # Also adds as normal pattern for directory contents
                self._patterns.append(stripped.rstrip("/"))
                self._patterns.append(stripped.rstrip("/") + "/**")
                continue

            # Remove leading slash (anchors to root, but we treat as relative)
            if stripped.startswith("/"):
                stripped = stripped[1:]

            self._patterns.append(stripped)

        logger.debug(
            "GitignoreParser: %d patterns loaded, %d negations, %d dir-only",
            len(self._patterns), len(self._negations), len(self._dir_only_patterns),
        )

    def should_ignore(self, relative_path: str, is_dir: bool = False) -> bool:
        """Verifies if a relative path should be ignored.

        Logic follows Git semantics:
            1. If the path matches any ignore pattern → True.
            2. If the path matches a negation pattern → False (override).
            3. Directory-only patterns only apply to directories.

        Args:
            relative_path: Relative path to the project root (forward slashes).
            is_dir: True if the path is a directory.

        Returns:
            True if it should be ignored.
        """
        # Normalize to forward slashes
        normalized = relative_path.replace("\\", "/")
        # Extract basename for simple matching (e.g. 'node_modules')
        basename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

        # Check negations first (override)
        for neg_pattern in self._negations:
            if self._matches(normalized, neg_pattern) or self._matches(basename, neg_pattern):
                return False

        # Check directory patterns
        if is_dir:
            for dir_pattern in self._dir_only_patterns:
                if self._matches(normalized, dir_pattern) or self._matches(basename, dir_pattern):
                    return True

        # Check general patterns
        for pattern in self._patterns:
            if self._matches(normalized, pattern) or self._matches(basename, pattern):
                return True

        return False

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        """Checks if a path matches a glob pattern.

        Supports:
            - fnmatch wildcards (*, ?, [seq])
            - ** (recursive glob — match of any depth)

        Args:
            path: Normalized path (forward slashes).
            pattern: Glob pattern.

        Returns:
            True if the path matches the pattern.
        """
        # ** → any subdirectory
        if "**" in pattern:
            # Transforms 'dir/**/file' into recursive match
            # Splits by '**' and checks the parts
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix = parts[0].rstrip("/")
                suffix = parts[1].lstrip("/")
                if prefix and not path.startswith(prefix):
                    return False
                if suffix and not fnmatch.fnmatch(path.rsplit("/", 1)[-1], suffix):
                    return False
                if prefix and suffix:
                    return True
                if not prefix and suffix:
                    return fnmatch.fnmatch(path.rsplit("/", 1)[-1], suffix)
                if prefix and not suffix:
                    return path.startswith(prefix)
                return True  # ** alone → ignores everything

        # Pattern contains / → match against full path
        if "/" in pattern:
            return fnmatch.fnmatch(path, pattern)

        # Simple pattern → match against each component of the path
        components = path.split("/")
        for component in components:
            if fnmatch.fnmatch(component, pattern):
                return True

        return False


# ---------------------------------------------------------------------------
# ProjectCrawler — Scanning engine
# ---------------------------------------------------------------------------

class ProjectCrawler:
    """Intelligent filesystem scanning with Delta Detection.

    Flow:
        1. Loads ignore patterns (.gitignore + IGNORE_DIRS).
        2. Recursively traverses the source_path.
        3. Calculates SHA256 of each file.
        4. Queries SqliteStore to check if the hash already exists.
        5. Classifies file by extension.
        6. Detects orphan nodes (deleted files) for Garbage Collection.

    Args:
        sqlite_store: SqliteStore instance for hash queries.
        ignore_dirs: List of extra directories to ignore (merge with DEFAULT_IGNORE_DIRS).
    """

    # Ignored directories by default (per ConciergeConfig.IGNORE_DIRS)
    DEFAULT_IGNORE_DIRS: set[str] = {
        ".git", "node_modules", ".next", "dist", "build",
        "__pycache__", ".venv", "venv", ".env", ".idea",
        ".vscode", ".mypy_cache", ".pytest_cache", "coverage",
        ".tox", "egg-info", ".eggs", ".cache", ".gradle",
        "target", "vendor", "bower_components",
    }

    # Ignored FILE patterns by default (zero-config security)
    DEFAULT_IGNORE_PATTERNS: list[str] = [
        # Security — Credentials and Keys
        ".env", ".env.*",
        "*.pem", "*.key", "*.cert", "*.der", "*.pfx", "*.p12",
        "id_rsa", "id_dsa", "id_ed25519",
        # Lock files — Pure noise
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "poetry.lock", "Cargo.lock", "composer.lock", "Gemfile.lock",
        # Logs and junk text
        "*.log", "*.txt",
        # Local databases
        "*.db", "*.sqlite", "*.sqlite3",
        # Binaries and compilation
        "*.exe", "*.dll", "*.so", "*.dylib", "*.bin", "*.o", "*.a",
        "*.pyc", "*.pyo", "*.class", "*.wasm",
        # Compressed files
        "*.zip", "*.tar", "*.tar.gz", "*.tgz", "*.rar", "*.7z", "*.bz2",
        # Media and Images
        "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.svg",
        "*.mp3", "*.mp4", "*.wav", "*.avi", "*.mov", "*.webp",
        "*.ttf", "*.woff", "*.woff2", "*.eot",
        # OS junk
        ".DS_Store", "Thumbs.db", "desktop.ini",
    ]

    # Maximum file size for ingestion (10 MB)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

    # Read block size for hash (64 KB — memory efficiency)
    _HASH_BLOCK_SIZE: int = 65536

    def __init__(
        self,
        sqlite_store: "SqliteStore",
        ignore_dirs: Optional[set[str]] = None,
    ) -> None:
        """Initializes the Crawler.

        Args:
            sqlite_store: SQLite facade for querying existing hashes.
            ignore_dirs: Extra directories to ignore (merge with DEFAULT_IGNORE_DIRS).
        """
        self._store = sqlite_store
        self._ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
        if ignore_dirs:
            self._ignore_dirs.update(ignore_dirs)

        # GitignoreParser will be loaded by crawl() if .gitignore exists
        self._gitignore: Optional[GitignoreParser] = None

        logger.info(
            "ProjectCrawler initialized: %d active ignore patterns.",
            len(self._ignore_dirs),
        )

    def crawl(
        self,
        source_path: str,
        project_uuid: str,
    ) -> CrawlReport:
        """Executes a complete scan of a project directory.

        Flow:
            1. Validates source_path.
            2. Loads .gitignore (if it exists).
            3. Traverses files recursively.
            4. For each file: hash → classify → delta check.
            5. Detects orphan nodes (Garbage Collection).
            6. Returns CrawlReport with new_files, unchanged, and deleted.

        Args:
            source_path: Root directory of the project to scan.
            project_uuid: Project UUID (for node filtering in SQLite).

        Returns:
            CrawlReport with the complete scan inventory.

        Raises:
            FileNotFoundError: If source_path does not exist.
            NotADirectoryError: If source_path is not a directory.
        """
        root = Path(source_path).resolve()

        # --- Input validation ---
        if not root.exists():
            raise FileNotFoundError(f"source_path does not exist: {source_path}")
        if not root.is_dir():
            raise NotADirectoryError(f"source_path is not a directory: {source_path}")

        logger.info("Crawl started: %s (project: %s)", root, project_uuid)

        # --- Load ignore patterns (3 layers) ---
        self._gitignore = GitignoreParser()

        # Layer 1: Default safety patterns (zero-config)
        self._gitignore.add_patterns(self.DEFAULT_IGNORE_PATTERNS)
        logger.info("Default safety patterns loaded: %d rules.", len(self.DEFAULT_IGNORE_PATTERNS))

        # Layer 2: Project .gitignore
        gitignore_file = root / ".gitignore"
        if gitignore_file.is_file():
            self._gitignore.load(str(gitignore_file))
            logger.info(".gitignore found and loaded: %s", gitignore_file)

        # Layer 3: .conciergeignore (Grafo Concierge specific extra rules)
        concierge_ignore_file = root / ".conciergeignore"
        if concierge_ignore_file.is_file():
            self._gitignore.load(str(concierge_ignore_file))
            logger.info(".conciergeignore found and loaded: %s", concierge_ignore_file)

        # --- Traverse recursively ---
        report = CrawlReport()
        current_hashes: set[str] = set()
        current_files: set[str] = set()

        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
            current_dir = Path(dirpath)
            relative_dir = current_dir.relative_to(root)

            # Filter directories IN-PLACE (os.walk topdown=True respects this)
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore_dir(d, str(relative_dir / d))
            ]

            for filename in filenames:
                filepath = current_dir / filename
                relative_filepath = str(relative_dir / filename).replace("\\", "/")

                # Skip hidden files (start with .)
                if filename.startswith("."):
                    continue

                # Check .gitignore
                if self._gitignore and self._gitignore.should_ignore(relative_filepath, is_dir=False):
                    logger.debug("Ignored (.gitignore): %s", relative_filepath)
                    continue

                # Check if it is a regular and readable file
                if not filepath.is_file():
                    continue

                # Check maximum size
                try:
                    size_bytes = filepath.stat().st_size
                except OSError as e:
                    logger.warning("Could not read stat of %s: %s", filepath, e)
                    continue

                if size_bytes > self.MAX_FILE_SIZE_BYTES:
                    logger.debug(
                        "File exceeds MAX_FILE_SIZE (%d bytes): %s",
                        size_bytes, relative_filepath,
                    )
                    continue

                # Skip empty files (0 bytes)
                if size_bytes == 0:
                    continue

                # --- Compute SHA256 ---
                file_hash = self.compute_file_hash(str(filepath))
                if file_hash is None:
                    # Reading error — skip (already logged by compute_file_hash)
                    continue

                current_hashes.add(file_hash)
                current_files.add(relative_filepath)

                # --- Classify ---
                category = self.classify_file(filename)
                extension = Path(filename).suffix.lower()

                # --- Delta Check via SqliteStore ---
                existing_node = self._store.find_node_by_hash(project_uuid, file_hash)

                result = CrawlResult(
                    absolute_path=str(filepath),
                    relative_path=relative_filepath,
                    file_hash=file_hash,
                    category=category,
                    extension=extension,
                    size_bytes=size_bytes,
                    is_new=(existing_node is None),
                    existing_node_id=existing_node["id"] if existing_node else None,
                )

                if result.is_new:
                    report.new_files.append(result)
                else:
                    report.unchanged_files.append(result)

                # Count per category
                cat_key = category.value
                report.categories[cat_key] = report.categories.get(cat_key, 0) + 1
                report.total_scanned += 1

        # --- Detect orphan nodes for Garbage Collection ---
        report.deleted_node_ids = self._detect_deleted_nodes(project_uuid, current_files)

        logger.info(
            "Crawl completed: %d scanned, %d new, %d unchanged, %d deleted (GC).",
            report.total_scanned,
            len(report.new_files),
            len(report.unchanged_files),
            len(report.deleted_node_ids),
        )

        return report

    def compute_file_hash(self, filepath: str) -> Optional[str]:
        """Calculates SHA256 of a file's content.

        Reads the file in 64KB blocks for memory efficiency.
        Returns None in case of read error (Semantic Fallback).

        Args:
            filepath: Absolute path to the file.

        Returns:
            Hexadecimal SHA256 hash (64 characters) or None if it failed.
        """
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while True:
                    block = f.read(self._HASH_BLOCK_SIZE)
                    if not block:
                        break
                    sha256.update(block)
            return sha256.hexdigest()
        except (OSError, IOError, PermissionError) as e:
            logger.warning("Failed to calculate hash of %s: %s", filepath, e)
            return None

    def classify_file(self, filename: str) -> FileCategory:
        """Classifies a file by extension.

        Args:
            filename: File name (basename, e.g. 'main.py').

        Returns:
            Corresponding FileCategory (or UNKNOWN for unmapped extensions).
        """
        ext = Path(filename).suffix.lower()
        return EXTENSION_MAP.get(ext, FileCategory.UNKNOWN)

    def _should_ignore_dir(self, dirname: str, relative_path: str) -> bool:
        """Checks if a directory should be ignored.

        Evaluates against:
            - DEFAULT_IGNORE_DIRS + customized ignore_dirs.
            - Patterns from .gitignore.
            - Hidden directories (start with . except .github, .husky).

        Args:
            dirname: Directory name (basename).
            relative_path: Relative path to root.

        Returns:
            True if it should be ignored.
        """
        # Directories from ignore list
        if dirname in self._ignore_dirs:
            return True

        # Hidden directories (except useful exceptions)
        ALLOWED_HIDDEN = {".github", ".husky", ".circleci", ".gitlab"}
        if dirname.startswith(".") and dirname not in ALLOWED_HIDDEN:
            return True

        # Check .gitignore
        if self._gitignore and self._gitignore.should_ignore(
            relative_path.replace("\\", "/"), is_dir=True
        ):
            return True

        return False

    def _detect_deleted_nodes(
        self,
        project_uuid: str,
        current_files: set[str],
    ) -> list[int]:
        """Detects nodes in SQLite whose files no longer exist on disk.

        Compares the relative paths of project nodes in SQLite with the list of files
        existing on disk. Nodes belonging to files that are no longer in current_files
        are marked for Garbage Collection.

        SECURITY: Only nodes that are not directories or projects are deleted.

        Args:
            project_uuid: UUID of the project.
            current_files: Set of relative paths of files existing on disk.

        Returns:
            List of orphan node_ids for removal.
        """
        orphan_ids: list[int] = []

        try:
            # Fetch all project nodes from SQLite
            all_nodes = self._store.get_nodes_by_project(project_uuid)
            for node in all_nodes:
                # Only nodes that are not directories or projects
                if node.get("type") in ("directory", "cluster", "project"):
                    continue

                label = node.get("label", "")
                if not label:
                    continue

                # The label is formatted as 'rel_path::symbol_name' or 'rel_path'
                rel_path = label.split("::")[0]

                # If the file no longer exists on disk → orphan node
                if rel_path not in current_files:
                    orphan_ids.append(node["id"])
                    logger.debug(
                        "Orphan node detected (GC): id=%d, label=%s, deleted file=%s",
                        node["id"], label, rel_path,
                    )

        except Exception as e:
            logger.error("Falha na detecção de nós deletados (GC): %s", e)

        if orphan_ids:
            logger.warning(
                "Garbage Collection: %d nós órfãos detectados no projeto %s.",
                len(orphan_ids), project_uuid,
            )
        else:
            logger.debug("Garbage Collection: nenhum nó órfão detectado.")

        return orphan_ids

