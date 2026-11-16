# -*- coding: utf-8 -*-
"""
Contrato pos-C2 (4.5e): ramo SDD-20 retorna falha explicita D0 sem consultar/gravar SQLite.

Sem DDL proprio: esquema oficial criado exclusivamente via SchemaManager.
"""
from __future__ import annotations

import gc
import os
import shutil
import sqlite3
import tempfile
import time
from unittest.mock import MagicMock

import pytest

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from storage.schema import SchemaManager


@pytest.fixture
def official_db_checkpointer():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "sdd20_removed.db")
    conn = sqlite3.connect(db_path)
    try:
        SchemaManager(conn).apply_full_schema()
    finally:
        conn.close()

    db_mgr = ConciergeDatabaseManager(db_path)
    cp = AgnosticCheckpointer(db_mgr)
    yield cp, db_mgr, db_path

    del cp, db_mgr
    gc.collect()
    for _ in range(5):
        try:
            shutil.rmtree(tmpdir)
            break
        except Exception:
            time.sleep(0.1)


class TestCheckpointerSDD20Archived:
    def test_sdd20_returns_explicit_d0_archive_error_and_writes_nothing(self, official_db_checkpointer):
        cp, _, db_path = official_db_checkpointer

        calls = [
            (("s", "c", "a", "ESTADO"), {}),
            (("s", "c", "a", "ESTADO", {"k": 1}), {}),
            ((), {"session_id": "s", "checkpoint_id": "c", "agent_id": "a", "state_name": "ESTADO", "shared_state": {"k": 1}}),
            ((), {"session_id": "s", "checkpoint_id": "c", "agent_id": "a", "shared_state": {"k": 1}}),
        ]

        for args, kwargs in calls:
            ok, err = cp.save_checkpoint_detailed(*args, **kwargs)
            assert ok is False
            assert isinstance(err, str)
            assert "archived in V4 (D0)" in err
            assert "fsm_checkpoints" in err
            assert cp.last_error is None

            wrapped_ok = cp.save_checkpoint(*args, **kwargs)
            assert wrapped_ok is False
            assert cp.last_error == err
            cp.last_error = None

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_checkpoints").fetchone()[0]
        finally:
            conn.close()
        assert count == 0

    def test_sdd20_never_touches_database_write_methods(self):
        mock_db = MagicMock()
        cp = AgnosticCheckpointer(mock_db)

        ok, err = cp.save_checkpoint_detailed("s", "c", "a", "ESTADO", {"k": 1})
        assert ok is False
        assert err is not None and "archived in V4 (D0)" in err
        mock_db.execute_write.assert_not_called()
        mock_db.write_query.assert_not_called()
