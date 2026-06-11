"""
storage/schema.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Definições de Schema SQL, CHECK constraints e Triggers FTS5.

Responsabilidades:
    - Constantes SQL para criação das 6 tabelas do Schema v3.8:
        projects, nodes, edges, reference_wings, trajectories, commit_log.
    - CHECK constraints inline para validação no nível do banco:
        node_type IN ('FACT','SKILL','INSIGHT','TRAJECTORY','PATCH')
        privacy_level IN ('PUBLIC','INTERNAL','RESTRICTED')
        status IN ('ACTIVE','STALE','ARCHIVED')
    - Índices de performance (10 índices).
    - Tabela virtual FTS5 (nodes_fts) com content sync.
    - Triggers de sincronização FTS5 (INSERT, DELETE, UPDATE).
    - SchemaManager: classe que aplica o schema de forma idempotente
      e oferece utilitários de verificação e migração.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

logger = logging.getLogger("grafo-concierge.schema")


# ---------------------------------------------------------------------------
# Enums de validação (espelho dos CHECK constraints do SQL)
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
# Constantes SQL — Tabelas v3.8.0 com CHECK constraints
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
# SchemaManager — aplicação e verificação do schema
# ---------------------------------------------------------------------------

class SchemaManager:
    """Aplica e verifica o Schema v3.8 de forma idempotente.

    Responsabilidades:
        - Criação de tabelas (IF NOT EXISTS).
        - Aplicação de CHECK constraints no nível SQL.
        - Criação de índices.
        - Criação da tabela virtual FTS5 e seus triggers.
        - Verificação da versão do schema.
        - Rebuild do índice FTS5 para grandes cargas.

    Args:
        conn: Conexão SQLite já configurada (WAL, busy_timeout, foreign_keys).
    """

    # Versão semântica do schema para controle de migrações futuras.
    SCHEMA_VERSION: str = "3.8.0"

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def apply_full_schema(self) -> None:
        """Aplica o schema completo (tabelas + índices + FTS5 + triggers).

        Operação idempotente — seguro chamar múltiplas vezes.
        Executa dentro de uma transação única.

        Raises:
            sqlite3.OperationalError: Se houver erro irrecuperável no DDL.
        """
        logger.debug("Iniciando aplicação do Schema v%s", self.SCHEMA_VERSION)
        try:
            self._conn.executescript(TABLES_SQL)
            self._conn.executescript(INDEXES_SQL)
            self._conn.executescript(FTS5_TABLE_SQL)
            self._conn.executescript(FTS5_TRIGGERS_SQL)
            self._conn.commit()
            
            # Garantir que a coluna 'content' existe (migração retroativa para bancos legados)
            cursor = self._conn.execute("PRAGMA table_info(nodes)")
            cols = [row[1] for row in cursor.fetchall()]
            if "content" not in cols:
                self._conn.execute("ALTER TABLE nodes ADD COLUMN content TEXT;")
                self._conn.commit()
                logger.info("Migração: coluna 'content' adicionada à tabela 'nodes'.")

            # Garantir que a versão atual está salva no DB.
            current_version = self.get_schema_version()
            if not current_version or current_version != self.SCHEMA_VERSION:
                self.set_schema_version(self.SCHEMA_VERSION)
            
            logger.info("Schema v3.8 aplicado com sucesso.")
        except Exception as e:
            self._conn.rollback()
            logger.error("Falha ao aplicar schema: %s", e)
            raise

    def verify_tables_exist(self) -> dict[str, bool]:
        """Verifica quais tabelas do Schema v3.8 existem no banco.

        Returns:
            Dict mapeando nome da tabela → bool (existe ou não).
            Tabelas verificadas: projects, nodes, edges, reference_wings,
            trajectories, commit_log, nodes_fts.
        """
        required_tables = [
            "projects", "nodes", "edges", "reference_wings", 
            "trajectories", "commit_log", "nodes_fts"
        ]
        
        cursor = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' OR type='view'"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        return {table: table in existing_tables for table in required_tables}

    def verify_triggers_exist(self) -> dict[str, bool]:
        """Verifica quais triggers FTS5 existem no banco.

        Returns:
            Dict mapeando nome do trigger → bool.
            Triggers: nodes_ai, nodes_ad, nodes_au.
        """
        required_triggers = ["nodes_ai", "nodes_ad", "nodes_au"]
        
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        existing_triggers = {row[0] for row in cursor.fetchall()}
        
        return {trigger: trigger in existing_triggers for trigger in required_triggers}

    def get_schema_version(self) -> Optional[str]:
        """Retorna a versão do schema armazenada no app_id do SQLite (convertida de volta).
        No SQLite, usaremos 'user_version' que armazena int.
        
        Como queremos armazenar strings semânticas, vamos salvar numa tabela de metadados?
        Mas se não existe, usaremos um truque com PRAGMA user_version.
        3.8.0 -> 308000
        """
        cursor = self._conn.execute("PRAGMA user_version")
        val = cursor.fetchone()[0]
        if val == 0:
            return None
        
        # Converte de volta: 308000 -> 3.8.0
        major = val // 100000
        minor = (val % 100000) // 1000
        patch = val % 1000
        return f"{major}.{minor}.{patch}"

    def set_schema_version(self, version: str) -> None:
        """Grava a versão do schema no PRAGMA user_version.

        Args:
            version: Versão semântica (ex: '3.8.0').
        """
        try:
            parts = [int(p) for p in version.split(".")]
            # major * 100000 + minor * 1000 + patch
            val = parts[0] * 100000 + parts[1] * 1000 + parts[2]
            self._conn.execute(f"PRAGMA user_version = {val}")
            self._conn.commit()
            logger.debug("Schema version salva como PRAGMA user_version=%d", val)
        except Exception as e:
            logger.warning("Falha ao salvar versão de schema %s: %s", version, e)

    def rebuild_fts_index(self) -> None:
        """Reconstrói o índice FTS5 a partir da tabela nodes.

        Útil após grandes operações de ingestão (concierge mine).
        Operação potencialmente lenta para bases grandes.
        """
        logger.info("Iniciando rebuild manual do índice FTS5...")
        try:
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
            self._conn.commit()
            logger.info("Índice FTS5 reconstruído com sucesso.")
        except Exception as e:
            self._conn.rollback()
            logger.error("Falha ao reconstruir FTS5: %s", e)
            raise

    def get_table_row_counts(self) -> dict[str, int]:
        """Retorna a contagem de rows de cada tabela do schema.

        Returns:
            Dict mapeando nome da tabela → contagem de registros.
        """
        counts = {}
        tables = [
            "projects", "nodes", "edges", "reference_wings", 
            "trajectories", "commit_log"
        ]
        
        for table in tables:
            try:
                cursor = self._conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = -1  # Indica que a tabela provavelmente não existe
                
        return counts
