"""tests/test_fts_atomic_migration.py

Testes de unidade para F4-026 (Rodada 4.2j):
- Teste 1: Migração atômica com tudo-ou-nada: falha simulada entre DROP e rebuild
  deve reverter o banco ao estado antigo intacto (3 colunas, triggers presentes,
  busca anterior funcionando).
- Teste 2: Cenário do auditor: FTS com 4 colunas mas vazio com nodes povoado deve ser
  detectado pela verificação de consistência na inicialização e reconstruído.
- Teste 3: Idempotência da migração e preservação estrita do hash dos nós.
"""

from __future__ import annotations

import hashlib
import sqlite3
import pytest
from storage.schema import SchemaManager


class ConnectionProxy:
    """Proxy transparente para sqlite3.Connection que permite interceptar chamadas."""

    def __init__(self, target: sqlite3.Connection) -> None:
        self._target = target
        self.crash_on_pattern: str | None = None

    def execute(self, sql: str, *args, **kwargs):
        if self.crash_on_pattern and self.crash_on_pattern in sql:
            raise RuntimeError(f"CRASH_INJECTED_AT: {self.crash_on_pattern}")
        return self._target.execute(sql, *args, **kwargs)

    def executescript(self, sql: str):
        if self.crash_on_pattern and self.crash_on_pattern in sql:
            raise RuntimeError(f"CRASH_INJECTED_AT: {self.crash_on_pattern}")
        return self._target.executescript(sql)

    def commit(self):
        return self._target.commit()

    def rollback(self):
        return self._target.rollback()

    def backup(self, *args, **kwargs):
        return self._target.backup(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._target, name)


def _create_legacy_v3_database(conn: sqlite3.Connection) -> None:
    """Cria esquema pré-4.2i com nodes_fts em 3 colunas (sem coluna content)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            uuid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            root_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_uuid TEXT NOT NULL,
            label TEXT NOT NULL,
            node_type TEXT NOT NULL DEFAULT 'FACT',
            status TEXT DEFAULT 'ACTIVE',
            body TEXT,
            tags TEXT,
            summary TEXT,
            content TEXT,
            last_commit_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_uuid) REFERENCES projects(uuid)
        );

        -- Tabela FTS legada (3 colunas, sem content)
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            label, tags, summary, content='nodes', content_rowid='id'
        );

        -- Triggers legados sincronizando apenas 3 colunas
        CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
            INSERT INTO nodes_fts(rowid, label, tags, summary)
            VALUES (new.id, new.label, new.tags, new.summary);
        END;

        CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
            VALUES ('delete', old.id, old.label, old.tags, old.summary);
        END;

        CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
            VALUES ('delete', old.id, old.label, old.tags, old.summary);
            INSERT INTO nodes_fts(rowid, label, tags, summary)
            VALUES (new.id, new.label, new.tags, new.summary);
        END;

        CREATE TABLE IF NOT EXISTS schema_version (
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        );
        INSERT INTO schema_version (version) VALUES ('3.8.1');
    """)


def test_fts_migration_is_atomic_rollback_on_failure() -> None:
    """Teste 1: Falha entre DROP e rebuild deve reverter completamente ao estado anterior."""
    real_conn = sqlite3.connect(":memory:")
    _create_legacy_v3_database(real_conn)

    # Insere projeto e nós
    real_conn.execute("INSERT INTO projects (uuid, name) VALUES ('p1', 'TestProj')")
    real_conn.execute(
        "INSERT INTO nodes (id, project_uuid, label, tags, summary, content) "
        "VALUES (1, 'p1', 'modulo_antigo.py', 'tag1', 'sumario legado', 'corpo confidencial 123')"
    )
    real_conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
    real_conn.commit()

    # Confirma que busca legada funciona por label e summary
    res_label = real_conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'modulo_antigo'").fetchall()
    assert len(res_label) == 1, "Busca legada por label deve funcionar antes da migração"

    # Injeta falha forçada durante a migração no momento do rebuild
    proxy = ConnectionProxy(real_conn)
    proxy.crash_on_pattern = "rebuild"

    sm = SchemaManager(proxy)
    with pytest.raises(RuntimeError, match="CRASH_INJECTED_AT: rebuild"):
        sm.apply_full_schema()

    # Desativa a injeção para inspecionar o banco
    proxy.crash_on_pattern = None

    # Verificação pós-falha: o banco DEVE ter revertido ao estado antigo
    # 1. Tabela nodes_fts deve existir e ter o esquema legado (3 colunas, sem content)
    cur = real_conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'")
    row = cur.fetchone()
    assert row is not None, "A tabela nodes_fts deve existir após rollback da migração falha"
    fts_sql = row[0].lower()
    assert "content," not in fts_sql and "content)" not in fts_sql, (
        f"Esquema de nodes_fts deve permanecer no formato legado de 3 colunas após rollback: {fts_sql}"
    )

    # 2. Todos os 3 triggers antigos devem estar presentes
    cur_trig = real_conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    triggers = {r[0] for r in cur_trig.fetchall()}
    assert triggers == {"nodes_ai", "nodes_ad", "nodes_au"}, f"Triggers incompletos após rollback: {triggers}"

    # 3. A busca legada no nó existente DEVE continuar funcionando após o rollback
    res_after_rollback = real_conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'modulo_antigo'").fetchall()
    assert len(res_after_rollback) == 1, "Busca no nó legado deve continuar funcionando após rollback"

    # Agora executa a migração sem falha: ela DEVE completar com sucesso
    sm.apply_full_schema()

    # Verifica que migrou para 4 colunas
    cur2 = real_conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'")
    fts_sql2 = cur2.fetchone()[0].lower()
    assert "content," in fts_sql2 or "content)" in fts_sql2, "Deve ter 4 colunas após migração bem sucedida"

    # E agora o termo no corpo ('confidencial') deve ser encontrado!
    res_content = real_conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'confidencial'").fetchall()
    assert len(res_content) == 1, "Busca por conteúdo deve funcionar após migração bem sucedida"


def test_fts_startup_consistency_check_rebuilds_unrebuilt_fts() -> None:
    """Teste 2: Cenário do auditor: FTS com 4 colunas mas vazio com nodes povoado deve ser reconstruído na inicialização."""
    conn = sqlite3.connect(":memory:")
    # Cria esquema já com versão 3.8.2 e 4 colunas
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (uuid TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY, project_uuid TEXT, label TEXT, node_type TEXT DEFAULT 'FACT',
            status TEXT DEFAULT 'ACTIVE', body TEXT, tags TEXT, summary TEXT, content TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            label, tags, summary, content, content='nodes', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
            INSERT INTO nodes_fts(rowid, label, tags, summary, content)
            VALUES (new.id, new.label, new.tags, new.summary, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
            VALUES ('delete', old.id, old.label, old.tags, old.summary, old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
            VALUES ('delete', old.id, old.label, old.tags, old.summary, old.content);
            INSERT INTO nodes_fts(rowid, label, tags, summary, content)
            VALUES (new.id, new.label, new.tags, new.summary, new.content);
        END;
        CREATE TABLE IF NOT EXISTS schema_version (version TEXT PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES ('3.8.2');
    """)

    # Popula nodes
    conn.execute("INSERT INTO projects VALUES ('p1', 'AuditorProj')")
    conn.execute(
        "INSERT INTO nodes (id, project_uuid, label, content) VALUES (1, 'p1', 'segredo.py', 'conteudo_oculto_auditor')"
    )
    conn.commit()

    # Simula a queda do auditor após DROP e CREATE VIRTUAL TABLE:
    # A tabela nodes_fts foi recriada vazia e o rebuild não rodou
    conn.execute("DROP TABLE nodes_fts;")
    conn.execute("""
        CREATE VIRTUAL TABLE nodes_fts USING fts5(
            label, tags, summary, content, content='nodes', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
    """)
    conn.commit()

    # Confirma que docsize está zerado e busca retorna 0 resultados
    cur_doc = conn.execute("SELECT COUNT(*) FROM nodes_fts_docsize")
    assert cur_doc.fetchone()[0] == 0, "docsize deve ser 0 antes do rebuild"
    res_before = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'conteudo_oculto_auditor'").fetchall()
    assert len(res_before) == 0, "Busca deve retornar vazio com FTS não reconstruído"

    # Inicialização pelo SchemaManager deve detectar a inconsistência e reconstruir
    sm = SchemaManager(conn)
    sm.apply_full_schema()

    # Agora docsize deve ser 1 e a busca deve retornar o nó
    cur_doc2 = conn.execute("SELECT COUNT(*) FROM nodes_fts_docsize")
    assert cur_doc2.fetchone()[0] == 1, "docsize deve ser 1 após verificação de consistência e auto-rebuild"

    res_after = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'conteudo_oculto_auditor'").fetchall()
    assert len(res_after) == 1, "Busca deve encontrar o termo após consistência na inicialização"


def test_fts_migration_idempotent_and_nodes_hash_unchanged() -> None:
    """Teste 3: Idempotência da migração e garantia de que tabela nodes permanece 100% inalterada."""
    conn = sqlite3.connect(":memory:")
    _create_legacy_v3_database(conn)

    conn.execute("INSERT INTO projects (uuid, name) VALUES ('p1', 'ProjIdem')")
    for i in range(1, 6):
        conn.execute(
            "INSERT INTO nodes (id, project_uuid, label, tags, summary, content) VALUES (?, 'p1', ?, ?, ?, ?)",
            (i, f"doc_{i}.py", f"tag_{i}", f"sumario_{i}", f"conteudo_{i}_teste"),
        )
    conn.commit()

    # Hash inicial dos dados de nodes
    rows_before = conn.execute("SELECT id, project_uuid, label, tags, summary, content FROM nodes ORDER BY id").fetchall()
    hash_before = hashlib.sha256(repr(rows_before).encode("utf-8")).hexdigest()

    # Executa migração
    sm = SchemaManager(conn)
    sm.apply_full_schema()

    # Hash após primeira migração
    rows_after1 = conn.execute("SELECT id, project_uuid, label, tags, summary, content FROM nodes ORDER BY id").fetchall()
    hash_after1 = hashlib.sha256(repr(rows_after1).encode("utf-8")).hexdigest()
    assert hash_before == hash_after1, "Os dados da tabela nodes não podem sofrer qualquer mutação"

    # Executa migração uma segunda vez (idempotência)
    sm.apply_full_schema()
    rows_after2 = conn.execute("SELECT id, project_uuid, label, tags, summary, content FROM nodes ORDER BY id").fetchall()
    hash_after2 = hashlib.sha256(repr(rows_after2).encode("utf-8")).hexdigest()
    assert hash_before == hash_after2, "Execução repetida da migração deve ser estritamente idempotente"
