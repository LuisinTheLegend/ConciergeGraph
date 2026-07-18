"""
storage/schema.py - Grafo Concierge v3.8.0 (Absolute Solidity)

SQL Schema Definitions, CHECK constraints and FTS5 Triggers.

Responsibilities:
    - SQL constants for creation of the 6 tables of Schema v3.8:
        projects, nodes, edges, reference_wings, trajectories, commit_log.
    - CHECK constraints inline for validation at database level:
        node_type IN ('FACT','SKILL','INSIGHT','TRAJECTORY','PATCH')
        privacy_level IN ('PUBLIC','INTERNAL','RESTRICTED')
        status IN ('ACTIVE','STALE','ARCHIVED')
    - Performance indexes (10 indexes).
    - FTS5 virtual table (nodes_fts) with content sync.
    - FTS5 synchronization triggers (INSERT, DELETE, UPDATE).
    - SchemaManager: class that applies the schema idempotently
      and offers verification and migration utilities.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger("grafo-concierge.schema")


# ---------------------------------------------------------------------------
# Validation enums (mirror of SQL CHECK constraints)
# ---------------------------------------------------------------------------

VALID_NODE_TYPES: frozenset[str] = frozenset({
    "FACT", "SKILL", "INSIGHT", "TRAJECTORY", "PATCH",
    "CLASS", "FUNCTION", "METHOD", "MODULE"
})

VALID_PRIVACY_LEVELS: frozenset[str] = frozenset({
    "PUBLIC", "INTERNAL", "RESTRICTED"
})

VALID_STATUSES: frozenset[str] = frozenset({
    "ACTIVE", "STALE", "ARCHIVED"
})


# ---------------------------------------------------------------------------
# SQL Constants — Tables v3.8.0 with CHECK constraints
# ---------------------------------------------------------------------------

TABLES_SQL: str = """
CREATE TABLE IF NOT EXISTS projects (
    uuid          TEXT PRIMARY KEY,
    folder_name   TEXT NOT NULL,
    primary_wing  TEXT NOT NULL DEFAULT 'geral',
    privacy_level TEXT NOT NULL DEFAULT 'PUBLIC' 
        CHECK(privacy_level IN ('PUBLIC', 'INTERNAL', 'RESTRICTED')),
    summary       TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS nodes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    label         TEXT NOT NULL,
    summary       TEXT,
    content       TEXT,
    node_type     TEXT NOT NULL DEFAULT 'FACT' 
        CHECK(node_type IN ('FACT', 'SKILL', 'INSIGHT', 'TRAJECTORY', 'PATCH', 'CLASS', 'FUNCTION', 'METHOD', 'MODULE')),
    type          TEXT NOT NULL DEFAULT 'file',
    tags          TEXT,
    file_hash     TEXT,
    last_accessed TEXT,
    last_commit_at TEXT,
    status        TEXT NOT NULL DEFAULT 'ACTIVE' 
        CHECK(status IN ('ACTIVE', 'STALE', 'ARCHIVED')),
    valid_from_commit TEXT NULL,
    valid_to_commit   TEXT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    source_id     INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id     INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL DEFAULT 'depends_on',
    weight        REAL NOT NULL DEFAULT 1.0,
    valid_from_commit TEXT NULL,
    valid_to_commit   TEXT NULL,
    confidence_tag    TEXT NOT NULL DEFAULT 'EXTRACTED'
        CHECK(confidence_tag IN ('EXTRACTED', 'INFERRED', 'AMBIGUOUS')),
    PRIMARY KEY (source_id, target_id)
);

CREATE TABLE IF NOT EXISTS reference_wings (
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    wing_name     TEXT NOT NULL,
    PRIMARY KEY (project_uuid, wing_name)
);

CREATE TABLE IF NOT EXISTS trajectories (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid       TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    prompt_origem      TEXT NOT NULL,
    tentativa_execucao TEXT NOT NULL,
    erro_encontrado    TEXT,
    solucao_aplicada   TEXT,
    status             TEXT NOT NULL DEFAULT 'ACTIVE' 
        CHECK(status IN ('ACTIVE', 'STALE', 'ARCHIVED')),
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS commit_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid      TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    phase             TEXT NOT NULL,
    technical_changes TEXT NOT NULL,
    updated_pointers  TEXT NOT NULL,
    revisor_approved  INTEGER NOT NULL DEFAULT 0,
    partial_audit     INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_core_memory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type    TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id      TEXT NOT NULL,
    block_label   TEXT NOT NULL,
    content       TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scope_type, scope_id, block_label)
);

CREATE TABLE IF NOT EXISTS semantic_facts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type     TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id       TEXT NOT NULL,
    fact_statement TEXT NOT NULL,
    t_valid        TEXT NOT NULL DEFAULT (datetime('now')),
    t_invalid      TEXT NULL,
    utility_alpha  REAL NOT NULL DEFAULT 1.0,
    utility_beta   REAL NOT NULL DEFAULT 1.0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

INDEXES_SQL: str = """
CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project_uuid);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_refwings_project ON reference_wings(project_uuid);
CREATE INDEX IF NOT EXISTS idx_trajectories_project ON trajectories(project_uuid);
CREATE INDEX IF NOT EXISTS idx_trajectories_status ON trajectories(status);
CREATE INDEX IF NOT EXISTS idx_commitlog_project ON commit_log(project_uuid);
CREATE INDEX IF NOT EXISTS idx_commitlog_date ON commit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_user_core_memory_scope ON user_core_memory(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_scope ON semantic_facts(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_semantic_facts_temporal ON semantic_facts(t_valid, t_invalid);
"""

FTS5_TABLE_SQL: str = """
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label, tags, summary, content='nodes', content_rowid='id'
);
"""

FTS5_TRIGGERS_SQL: str = """
CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;
"""


# ---------------------------------------------------------------------------
# SchemaManager — application and verification of schema
# ---------------------------------------------------------------------------

class SchemaManager:
    """Applies and verifies Schema v3.8 idempotently.

    Responsibilities:
        - Creation of tables (IF NOT EXISTS).
        - Application of CHECK constraints at SQL level.
        - Creation of indexes.
        - Creation of the virtual table FTS5 and its triggers.
        - Verification of the schema version.
        - Rebuild of the FTS5 index for large loads.

    Args:
        conn: Configured SQLite connection (WAL, busy_timeout, foreign_keys).
    """

    # Semantic schema version for controlling future migrations.
    SCHEMA_VERSION: str = "3.8.0"

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def apply_full_schema(self) -> None:
        """Applies the full schema (tables + indexes + FTS5 + triggers).

        Idempotent operation — safe to call multiple times.
        Executes within a single transaction.

        Raises:
            sqlite3.OperationalError: If there is an unrecoverable DDL error.
        """
        logger.debug("Starting application of Schema v%s", self.SCHEMA_VERSION)
        try:
            self._conn.executescript(TABLES_SQL)
            self._conn.executescript(INDEXES_SQL)
            self._conn.executescript(FTS5_TABLE_SQL)
            self._conn.executescript(FTS5_TRIGGERS_SQL)
            self._conn.commit()
            
            # Ensure the column 'content' exists (retroactive migration for legacy databases)
            cursor = self._conn.execute("PRAGMA table_info(nodes)")
            cols = [row[1] for row in cursor.fetchall()]
            if "content" not in cols:
                self._conn.execute("ALTER TABLE nodes ADD COLUMN content TEXT;")
                self._conn.commit()
                logger.info("Migration: 'content' column added to table 'nodes'.")

            # Ensure 'utility_alpha' and 'utility_beta' columns exist in semantic_facts
            cursor = self._conn.execute("PRAGMA table_info(semantic_facts)")
            sem_cols = [row[1] for row in cursor.fetchall()]
            if "utility_alpha" not in sem_cols:
                self._conn.execute("ALTER TABLE semantic_facts ADD COLUMN utility_alpha REAL NOT NULL DEFAULT 1.0;")
                self._conn.commit()
                logger.info("Migration: 'utility_alpha' column added to table 'semantic_facts'.")
            if "utility_beta" not in sem_cols:
                self._conn.execute("ALTER TABLE semantic_facts ADD COLUMN utility_beta REAL NOT NULL DEFAULT 1.0;")
                self._conn.commit()
                logger.info("Migration: 'utility_beta' column added to table 'semantic_facts'.")

            # Ensure the current version is saved in DB.
            current_version = self.get_schema_version()
            if not current_version or current_version != self.SCHEMA_VERSION:
                self.set_schema_version(self.SCHEMA_VERSION)

            # Retroactive migration: UNIQUE(scope_type, scope_id, block_label) in user_core_memory.
            # Databases created before this version do not have the unique index — without it the
            # INSERT OR REPLACE does not work as upsert.
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_core_memory_scope_label'"
            )
            if cursor.fetchone() is None:
                try:
                    # Removes duplicates keeping only the most recent record
                    self._conn.execute("""
                        DELETE FROM user_core_memory
                        WHERE id NOT IN (
                            SELECT MAX(id) FROM user_core_memory
                            GROUP BY scope_type, scope_id, block_label
                        )
                    """)
                    self._conn.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_core_memory_scope_label
                        ON user_core_memory(scope_type, scope_id, block_label)
                    """)
                    self._conn.commit()
                    logger.info("Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.")
                except Exception as idx_err:
                    logger.warning("Migration UNIQUE index user_core_memory failed (may already exist): %s", idx_err)

        except Exception as e:
            self._conn.rollback()
            logger.error("Failed to apply schema: %s", e)
            raise

    def verify_tables_exist(self) -> dict[str, bool]:
        """Verifies which tables of Schema v3.8 exist in the database.

        Returns:
            Dict mapping table name → bool (exists or not).
            Verified tables: projects, nodes, edges, reference_wings,
            trajectories, commit_log, nodes_fts.
        """
        required_tables = [
            "projects", "nodes", "edges", "reference_wings", 
            "trajectories", "commit_log", "nodes_fts",
            "user_core_memory", "semantic_facts"
        ]
        
        cursor = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' OR type='view'"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        return {table: table in existing_tables for table in required_tables}

    def verify_triggers_exist(self) -> dict[str, bool]:
        """Verifies which FTS5 triggers exist in the database.

        Returns:
            Dict mapping trigger name → bool.
            Triggers: nodes_ai, nodes_ad, nodes_au.
        """
        required_triggers = ["nodes_ai", "nodes_ad", "nodes_au"]
        
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        existing_triggers = {row[0] for row in cursor.fetchall()}
        
        return {trigger: trigger in existing_triggers for trigger in required_triggers}

    def get_schema_version(self) -> Optional[str]:
        """Returns the schema version stored in user_version of SQLite (converted back).
        In SQLite, we will use 'user_version' which stores int.
        
        Since we want to store semantic strings, should we save them in a metadata table?
        But if it doesn't exist, we will use a trick with PRAGMA user_version.
        3.8.0 -> 308000
        """
        cursor = self._conn.execute("PRAGMA user_version")
        val = cursor.fetchone()[0]
        if val == 0:
            return None
        
        # Converts back: 308000 -> 3.8.0
        major = val // 100000
        minor = (val % 100000) // 1000
        patch = val % 1000
        return f"{major}.{minor}.{patch}"

    def set_schema_version(self, version: str) -> None:
        """Writes the schema version in PRAGMA user_version.

        Args:
            version: Semantic version (e.g. '3.8.0').
        """
        try:
            parts = [int(p) for p in version.split(".")]
            # major * 100000 + minor * 1000 + patch
            val = parts[0] * 100000 + parts[1] * 1000 + parts[2]
            self._conn.execute(f"PRAGMA user_version = {val}")
            self._conn.commit()
            logger.debug("Schema version saved as PRAGMA user_version=%d", val)
        except Exception as e:
            logger.warning("Failed to save schema version %s: %s", version, e)

    def rebuild_fts_index(self) -> None:
        """Rebuilds the FTS5 index from the nodes table.

        Useful after large ingestion operations (concierge mine).
        Potentially slow operation for large databases.
        """
        logger.info("Manual rebuild of FTS5 index started...")
        try:
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
            self._conn.commit()
            logger.info("FTS5 index rebuilt successfully.")
        except Exception as e:
            self._conn.rollback()
            logger.error("Failed to rebuild FTS5: %s", e)
            raise

    def get_table_row_counts(self) -> dict[str, int]:
        """Returns the row count of each table in the schema.

        Returns:
            Dict mapping table name → record count.
        """
        counts = {}
        tables = [
            "projects", "nodes", "edges", "reference_wings", 
            "trajectories", "commit_log", "user_core_memory", "semantic_facts"
        ]
        
        for table in tables:
            try:
                cursor = self._conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = -1  # Indicates that the table probably does not exist
                
        return counts
