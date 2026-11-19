# -*- coding: utf-8 -*-
"""
Testes de fechamento de mutantes (S1/S2) e resolucao de argumentos / JSON corrompido
em AgnosticCheckpointer (Rodada 4.5e-bis).

Sem DDL proprio: todo banco fisico e inicializado exclusivamente via SchemaManager oficial.
"""
from __future__ import annotations

import gc
import json
import os
import shutil
import sqlite3
import tempfile
import time

import pytest

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from interface import mcp_server
from storage.schema import SchemaManager


@pytest.fixture
def official_checkpointer():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "arg_resolution.db")
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


class TestCheckpointerArgAndSanitizerClosing:
    @pytest.mark.parametrize(
        "case_name,args,kwargs",
        [
            (
                "only_state_name_kwarg",
                (),
                {
                    "agent_id": "a",
                    "session_id": "s",
                    "checkpoint_id": "c",
                    "state_dict": {"k": 1},
                    "state_name": "PLANNING",
                },
            ),
            (
                "only_shared_state_kwarg",
                (),
                {
                    "agent_id": "a",
                    "session_id": "s",
                    "checkpoint_id": "c",
                    "shared_state": {"k": 1},
                },
            ),
            (
                "exactly_5_positionals",
                ("s", "c", "a", {"not_str": 1}, {"k": 1}),
                {},
            ),
            (
                "four_positionals_4th_str",
                ("s", "c", "a", "ESTADO"),
                {},
            ),
        ],
    )
    def test_sdd20_each_disjunct_isolated(self, official_checkpointer, case_name, args, kwargs):
        """(S1) Cada disjunto de is_sdd20 e testado isoladamente como unico verdadeiro."""
        cp, _, db_path = official_checkpointer

        res = cp.save_checkpoint_detailed(*args, **kwargs)
        assert isinstance(res, tuple) and len(res) == 2, f"{case_name}: esperado tuple(2)"
        assert res[0] is False, f"{case_name}: SDD-20 deve retornar False"
        assert isinstance(res[1], str) and bool(res[1].strip()), f"{case_name}: mensagem vazia"
        assert cp.last_error is None

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_checkpoints").fetchone()[0]
        finally:
            conn.close()
        assert count == 0, f"{case_name}: nenhuma linha pode ser gravada em agent_checkpoints"

    def test_sanitize_for_json_set_deterministic_str_order(self, official_checkpointer):
        """
        (S2) Em CPython, list({9, 10}) e sorted([9, 10]) produzem [9, 10] porque 9 < 10
        numericamente e seus hashes inteiros preservam ordem crescente na tabela de dispersao.
        Ja sorted(list({9, 10}), key=str) ordena lexicograficamente ('10' < '9'), produzindo [10, 9].
        Isso diferencia deterministicamente key=str tanto de list(obj) quanto de sorted(list(obj)).
        """
        cp, _, _ = official_checkpointer

        sanitized = AgnosticCheckpointer._sanitize_for_json(
            {"nums": {9, 10}, "labels": {"z", "a", "10", "9"}}
        )
        assert sanitized == {
            "nums": [10, 9],
            "labels": ["10", "9", "a", "z"],
        }

        # Tambem pelo fluxo completo via save_checkpoint_detailed -> get_checkpoint
        sentinel = object()
        ok, err = cp.save_checkpoint_detailed(
            "ag-s2",
            "sess-s2",
            "cp-s2",
            {"nums": {9, 10}, "labels": {"z", "a", "10", "9"}, "sentinel": sentinel},
        )
        assert (ok, err) == (True, None)
        loaded = cp.get_checkpoint("ag-s2", "sess-s2", "cp-s2")
        assert loaded["nums"] == [10, 9]
        assert loaded["labels"] == ["10", "9", "a", "z"]
        assert loaded["sentinel"] == str(sentinel)

    def test_mcp_path_4_positionals_contract(self, official_checkpointer, monkeypatch):
        """Regressao do caminho MCP oficial com 4 posicionais."""
        cp, _, _ = official_checkpointer
        monkeypatch.setattr(mcp_server, "checkpointer", cp)

        save_raw = mcp_server.agent_save_checkpoint("mcp_ag", "mcp_sess", "mcp_cp", {"k": "v"})
        assert json.loads(save_raw) == {
            "success": True,
            "message": "Checkpoint 'mcp_cp' saved successfully for agent 'mcp_ag'",
        }
        assert mcp_server.agent_get_checkpoint("mcp_ag", "mcp_sess", "mcp_cp") == {"k": "v"}
