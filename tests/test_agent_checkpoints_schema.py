# -*- coding: utf-8 -*-
"""
Testes para o Bloco 1 da Rodada 4.3:
Tabela agent_checkpoints no esquema oficial (BL-001/002/004, escopo reduzido).
"""
import gc
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import pytest

from storage.schema import SchemaManager
from core.database import ConciergeDatabaseManager
from core.checkpointer import AgnosticCheckpointer
from interface import mcp_server


@pytest.fixture
def temp_db_path():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_checkpoints.db")
    yield db_path
    gc.collect()
    for _ in range(5):
        try:
            shutil.rmtree(tmpdir)
            break
        except Exception:
            time.sleep(0.1)


def _hash_table(conn: sqlite3.Connection, table_name: str) -> str:
    cursor = conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid ASC")
    rows = cursor.fetchall()
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()


class TestAgentCheckpointsOfficialSchema:
    """Valida a inclusão de agent_checkpoints no esquema oficial e ferramentas associadas."""

    def test_schema_manager_creates_agent_checkpoints(self, temp_db_path):
        """Um banco criado unicamente pelo SchemaManager oficial deve conter agent_checkpoints."""
        conn = sqlite3.connect(temp_db_path)
        try:
            mgr = SchemaManager(conn)
            mgr.apply_full_schema()

            tables = mgr.verify_tables_exist()
            assert "agent_checkpoints" in tables, "agent_checkpoints deve constar nas tabelas obrigatórias"
            assert tables["agent_checkpoints"] is True, "agent_checkpoints deve existir após apply_full_schema"

            # Validar colunas
            cur = conn.execute("PRAGMA table_info(agent_checkpoints)")
            cols = {row[1]: row[2].upper() for row in cur.fetchall()}
            assert "agent_id" in cols
            assert "session_id" in cols
            assert "checkpoint_id" in cols
            assert "state_blob" in cols
            assert "created_at" in cols
        finally:
            conn.close()

    def test_verify_tables_exist_fails_if_agent_checkpoints_missing(self, temp_db_path):
        """Simular ausência de agent_checkpoints deve levantar erro no boot do SchemaManager/Store."""
        conn = sqlite3.connect(temp_db_path)
        try:
            mgr = SchemaManager(conn)
            mgr.apply_full_schema()
            # Drop da tabela para simular corrupção/ausência
            conn.execute("DROP TABLE IF EXISTS agent_checkpoints;")
            conn.commit()

            tables = mgr.verify_tables_exist()
            assert tables.get("agent_checkpoints") is False

            # Verificação de boot deve falhar alto com RuntimeError
            missing = [t for t, exists in tables.items() if not exists]
            assert "agent_checkpoints" in missing
        finally:
            conn.close()

    def test_migration_preserves_existing_data(self, temp_db_path):
        """Banco legado (esquema 4.2j sem agent_checkpoints) ganha a tabela sem alterar dados existentes."""
        conn = sqlite3.connect(temp_db_path)
        try:
            conn.execute("""
                CREATE TABLE projects (
                    uuid TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    privacy_level TEXT DEFAULT 'INTERNAL',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_uuid TEXT NOT NULL,
                    label TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    content TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_uuid TEXT NOT NULL,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    valid_to_commit TEXT
                );
            """)
            # Inserir dados pré-existentes
            conn.execute("INSERT INTO projects (uuid, name, root_path) VALUES ('p1', 'proj1', '/path1');")
            conn.execute("INSERT INTO nodes (project_uuid, label, node_type, content) VALUES ('p1', 'mod.py', 'MODULE', 'code');")
            conn.execute("INSERT INTO edges (project_uuid, source_id, target_id, relation_type) VALUES ('p1', 1, 1, 'contains');")
            conn.commit()

            hash_projects_before = _hash_table(conn, "projects")
            hash_nodes_before = _hash_table(conn, "nodes")
            hash_edges_before = _hash_table(conn, "edges")

            # Aplicar migração oficial
            mgr = SchemaManager(conn)
            mgr.apply_full_schema()

            # Verificar integridade dos dados existentes
            assert _hash_table(conn, "projects") == hash_projects_before
            assert _hash_table(conn, "nodes") == hash_nodes_before
            assert _hash_table(conn, "edges") == hash_edges_before

            # Verificar que a tabela agent_checkpoints agora existe
            tbls = mgr.verify_tables_exist()
            assert tbls["agent_checkpoints"] is True
        finally:
            conn.close()

    def test_e2e_checkpointer_and_mcp_tools(self, temp_db_path):
        """E2E via AgnosticCheckpointer e mcp_server com isolamento por agente e sessão."""
        # 1. Boot oficial pelo SchemaManager
        conn = sqlite3.connect(temp_db_path)
        try:
            SchemaManager(conn).apply_full_schema()
        finally:
            conn.close()

        db_mgr = ConciergeDatabaseManager(temp_db_path)
        checkpointer = AgnosticCheckpointer(db_mgr)

        # Salvar checkpoint para agente 1 na sessão A
        res1 = checkpointer.save_checkpoint("agent_alpha", "session_A", "cp_1", {"step": 1, "status": "planning"})
        assert res1 is True

        # Salvar checkpoint para agente 2 na MESMA sessão A
        res2 = checkpointer.save_checkpoint("agent_beta", "session_A", "cp_1", {"step": 99, "status": "executing"})
        assert res2 is True

        # Isolamento: get_checkpoint de agent_alpha não vê dados de agent_beta
        state_alpha = checkpointer.get_checkpoint("agent_alpha", "session_A", "cp_1")
        assert state_alpha == {"step": 1, "status": "planning"}

        state_beta = checkpointer.get_checkpoint("agent_beta", "session_A", "cp_1")
        assert state_beta == {"step": 99, "status": "executing"}

        # Inexistente deve retornar {}
        assert checkpointer.get_checkpoint("agent_gamma", "session_A", "cp_1") == {}

        # Teste via interface mcp_server
        orig_cp = mcp_server.checkpointer
        try:
            mcp_server.checkpointer = checkpointer
            resp_str = mcp_server.agent_save_checkpoint("agent_alpha", "session_A", "cp_2", {"step": 2})
            resp = json.loads(resp_str)
            assert resp["success"] is True
            assert "saved successfully" in resp["message"]

            got = mcp_server.agent_get_checkpoint("agent_alpha", "session_A", "cp_2")
            assert got == {"step": 2}

            # Listagem
            cp_list = mcp_server.agent_list_checkpoints("agent_alpha", "session_A")
            ids = [c["checkpoint_id"] for c in cp_list]
            assert ids == ["cp_1", "cp_2"]
        finally:
            mcp_server.checkpointer = orig_cp

    def test_save_checkpoint_failure_message_includes_reason(self, temp_db_path):
        """Falha no save_checkpoint deve incluir motivo sanitizado sem vazar paths ou state."""
        # Boot sem criar agent_checkpoints
        db_mgr = ConciergeDatabaseManager(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        try:
            conn.execute("DROP TABLE IF EXISTS agent_checkpoints;")
            conn.commit()
        finally:
            conn.close()

        checkpointer = AgnosticCheckpointer(db_mgr)
        orig_cp = mcp_server.checkpointer
        try:
            mcp_server.checkpointer = checkpointer
            resp_str = mcp_server.agent_save_checkpoint("agent_1", "sess_1", "cp_fail", {"secret_key": "xyz123"})
            resp = json.loads(resp_str)
            assert resp["success"] is False
            msg = resp["message"]
            assert "Failed to save checkpoint" in msg
            # Motivo incluído
            assert "no such table: agent_checkpoints" in msg or "agent_checkpoints" in msg
            # Sem vazamento de caminho de arquivo ou de conteúdo do estado
            assert "xyz123" not in msg
            assert temp_db_path not in msg
        finally:
            mcp_server.checkpointer = orig_cp

    def test_list_checkpoints_rapid_sequence_order(self, temp_db_path):
        """Checkpoints gravados em ordem não-alfabética devem preservar ordem cronológica por rowid ASC."""
        conn = sqlite3.connect(temp_db_path)
        try:
            SchemaManager(conn).apply_full_schema()
            # Drop do índice secundário para exercitar plano que expõe ausência de rowid ASC
            conn.execute("DROP INDEX IF EXISTS idx_agent_checkpoints_lookup;")
            conn.commit()
        finally:
            conn.close()

        db_mgr = ConciergeDatabaseManager(temp_db_path)
        checkpointer = AgnosticCheckpointer(db_mgr)
        ids_to_insert = [f"step_{21-i:02d}" for i in range(1, 21)]
        for cid in ids_to_insert:
            ok = checkpointer.save_checkpoint("agent_fast", "sess_seq", cid, {"data": cid})
            assert ok is True

        listing = checkpointer.list_checkpoints("agent_fast", "sess_seq")
        assert len(listing) == 20
        returned_ids = [c["checkpoint_id"] for c in listing]
        assert returned_ids == ids_to_insert, f"Ordem esperada: {ids_to_insert}, obtida: {returned_ids}"

    def test_insert_or_replace_updates_order_and_rowid(self, temp_db_path):
        """INSERT OR REPLACE sobre checkpoint existente altera rowid/created_at e move para o fim."""
        conn = sqlite3.connect(temp_db_path)
        try:
            SchemaManager(conn).apply_full_schema()
        finally:
            conn.close()

        db_mgr = ConciergeDatabaseManager(temp_db_path)
        checkpointer = AgnosticCheckpointer(db_mgr)
        checkpointer.save_checkpoint("agent_repl", "sess_repl", "cp_a", {"v": 1})
        checkpointer.save_checkpoint("agent_repl", "sess_repl", "cp_b", {"v": 2})
        checkpointer.save_checkpoint("agent_repl", "sess_repl", "cp_c", {"v": 3})

        initial_list = [c["checkpoint_id"] for c in checkpointer.list_checkpoints("agent_repl", "sess_repl")]
        assert initial_list == ["cp_a", "cp_b", "cp_c"]

        # Atualizar cp_a via INSERT OR REPLACE
        checkpointer.save_checkpoint("agent_repl", "sess_repl", "cp_a", {"v": 100})
        updated_list = [c["checkpoint_id"] for c in checkpointer.list_checkpoints("agent_repl", "sess_repl")]
        # Em SQLite, REPLACE deleta o registro antigo e reinsere com novo rowid, movendo-o para o final
        assert updated_list == ["cp_b", "cp_c", "cp_a"]
