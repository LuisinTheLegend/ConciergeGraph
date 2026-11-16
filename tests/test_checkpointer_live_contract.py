# -*- coding: utf-8 -*-
"""
Contratos vivos de AgnosticCheckpointer antes e depois da remocao do ramo SDD-20 (4.5e).

Sem DDL proprio: todo banco fisico e inicializado estritamente via SchemaManager oficial.
"""
from __future__ import annotations

import gc
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from storage.schema import SchemaManager


class _OpaqueMarker:
    def __str__(self) -> str:
        return "<OpaqueMarker:ok>"


@pytest.fixture
def official_checkpointer():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "live_contract.db")
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


class TestCheckpointerLiveContract:
    def test_legacy_positional_4_args_dict_roundtrip_and_isolation(self, official_checkpointer):
        """(a) 4 posicionais com 4o dict grava em agent_checkpoints preservando (agent_id, session_id, checkpoint_id)."""
        cp, _, _ = official_checkpointer

        ok = cp.save_checkpoint("agent-alpha", "sess-100", "cp-001", {"step": 1, "ok": True})
        assert ok is True
        assert cp.last_error is None

        # Ordem correta recupera o estado; inversao agent_id <-> session_id nao encontra nada
        assert cp.get_checkpoint("agent-alpha", "sess-100", "cp-001") == {"step": 1, "ok": True}
        assert cp.get_checkpoint("sess-100", "agent-alpha", "cp-001") == {}

        listing = cp.list_checkpoints("agent-alpha", "sess-100")
        assert [row["checkpoint_id"] for row in listing] == ["cp-001"]
        assert cp.list_checkpoints("sess-100", "agent-alpha") == []
        assert cp.list_checkpoints("agent-alpha", "sess-inexistente") == []

    def test_legacy_kwargs_roundtrip(self, official_checkpointer):
        """(b) Forma por kwargs legada grava em agent_checkpoints e preserva vars(cp)."""
        cp, _, _ = official_checkpointer

        snapshot_before = dict(vars(cp))
        ok, err = cp.save_checkpoint_detailed(
            agent_id="agent-kw",
            session_id="sess-kw",
            checkpoint_id="cp-kw",
            state_dict={"mode": "kwargs", "count": 42},
        )
        assert (ok, err) == (True, None)
        assert vars(cp) == snapshot_before
        assert cp.get_checkpoint("agent-kw", "sess-kw", "cp-kw") == {"mode": "kwargs", "count": 42}

    def test_legacy_non_serializable_sanitization_lock_set_object_and_nested(self, official_checkpointer):
        """(c) Objetos nao serializaveis (Lock, set, object, tuple/set aninhados) sao sanitizados no ramo legado."""
        cp, _, _ = official_checkpointer
        lock = threading.Lock()
        marker = _OpaqueMarker()

        payload: dict[Any, Any] = {
            "lock": lock,
            "marker": marker,
            "tags": {"beta", "alpha"},
            "nested": {
                "seq": (1, {"x", lock}, marker),
                ("k1", "k2"): {"inner_set": {3, 1}, "lock": lock},
            },
        }

        ok, err = cp.save_checkpoint_detailed("agent-san", "sess-san", "cp-san", payload)
        assert ok is True
        assert err is None

        loaded = cp.get_checkpoint("agent-san", "sess-san", "cp-san")
        assert loaded["lock"] == str(lock)
        assert loaded["marker"] == "<OpaqueMarker:ok>"
        assert loaded["tags"] == ["alpha", "beta"]
        assert loaded["nested"]["seq"][0] == 1
        assert sorted(loaded["nested"]["seq"][1], key=str) == sorted(["x", str(lock)], key=str)
        assert loaded["nested"]["seq"][2] == "<OpaqueMarker:ok>"
        assert loaded["nested"][str(("k1", "k2"))] == {"inner_set": [1, 3], "lock": str(lock)}

        # Cobertura direta dos ramos de _sanitize_for_json
        sanitized = AgnosticCheckpointer._sanitize_for_json(
            {"tuple": (lock, marker, None, True, 7, 2.5), "set": {2, 1}}
        )
        assert sanitized == {
            "tuple": [str(lock), "<OpaqueMarker:ok>", None, True, 7, 2.5],
            "set": [1, 2],
        }

    def test_sdd20_signatures_fail_without_writing_agent_checkpoints(self, official_checkpointer):
        """(d) Todas as assinaturas SDD-20 falham sem gravar em agent_checkpoints."""
        cp, _, db_path = official_checkpointer

        sdd20_calls = [
            (("s", "c", "a", "ESTADO"), {}),
            (("s", "c", "a", "ESTADO", {"k": 1}), {}),
            ((), {"session_id": "s", "checkpoint_id": "c", "agent_id": "a", "state_name": "ESTADO", "shared_state": {"k": 1}}),
            ((), {"session_id": "s", "checkpoint_id": "c", "agent_id": "a", "shared_state": {"k": 1}}),
        ]

        for args, kwargs in sdd20_calls:
            res = cp.save_checkpoint_detailed(*args, **kwargs)
            assert isinstance(res, tuple) and len(res) == 2
            assert res[0] is False
            assert isinstance(res[1], str) and bool(res[1].strip())
            assert cp.last_error is None

            ok = cp.save_checkpoint(*args, **kwargs)
            assert ok is False
            assert isinstance(cp.last_error, str) and bool(cp.last_error.strip())
            cp.last_error = None

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_checkpoints").fetchone()[0]
        finally:
            conn.close()
        assert count == 0

    def test_write_failure_unknown_error_and_last_error_reset(self, official_checkpointer):
        """Falha com motivo None gera 'Unknown write error'; sucesso posterior limpa last_error."""
        cp, _, _ = official_checkpointer

        failing_db = MagicMock()
        failing_db.write_query.return_value = (False, None)
        failing_cp = AgnosticCheckpointer(failing_db)

        snapshot = dict(vars(failing_cp))
        ok_d, err_d = failing_cp.save_checkpoint_detailed("a", "s", "c", {"v": 1})
        assert (ok_d, err_d) == (False, "Unknown write error")
        assert vars(failing_cp) == snapshot

        assert failing_cp.save_checkpoint("a", "s", "c", {"v": 1}) is False
        assert failing_cp.last_error == "Unknown write error"

        # Sucesso subsequente no banco real deve limpar last_error
        cp.last_error = "stale error"
        assert cp.save_checkpoint("a", "s", "c", {"v": 2}) is True
        assert cp.last_error is None
        assert cp.get_checkpoint("a", "s", "c") == {"v": 2}
