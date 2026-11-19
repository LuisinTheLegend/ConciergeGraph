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


class TestCheckpointerMixedArgsAndConflict:
    def test_mixed_2_positional_2_kwargs_exact_repro_bug1(self, official_checkpointer):
        """(a) Reproducao exata do Bug 1 deve resolver corretamente agent_id/session_id/checkpoint_id/state_dict."""
        cp, _, db_path = official_checkpointer

        res = cp.save_checkpoint_detailed("agA", "sessA", checkpoint_id="cpA", state_dict={"v": 1})
        assert res == (True, None)

        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT agent_id, session_id, checkpoint_id, state_blob FROM agent_checkpoints"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert (rows[0][0], rows[0][1], rows[0][2]) == ("agA", "sessA", "cpA")
        assert cp.get_checkpoint("agA", "sessA", "cpA") == {"v": 1}

    @pytest.mark.parametrize(
        "args,kwargs,expected_key,expected_state",
        [
            (("ag1",), {"session_id": "s1", "checkpoint_id": "c1", "state_dict": {"k": 1}}, ("ag1", "s1", "c1"), {"k": 1}),
            (("ag2", "s2"), {"checkpoint_id": "c2", "state_dict": {"k": 2}}, ("ag2", "s2", "c2"), {"k": 2}),
            (("ag3", "s3", "c3"), {"state_dict": {"k": 3}}, ("ag3", "s3", "c3"), {"k": 3}),
        ],
    )
    def test_mixed_1_to_3_positionals_with_kwargs(
        self, official_checkpointer, args, kwargs, expected_key, expected_state
    ):
        """(b) Combinacoes 1+3, 2+2 e 3+1 posicional+kwarg gravam na PK exata."""
        cp, _, db_path = official_checkpointer

        res = cp.save_checkpoint_detailed(*args, **kwargs)
        assert res == (True, None)

        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT agent_id, session_id, checkpoint_id FROM agent_checkpoints"
            ).fetchall()
        finally:
            conn.close()
        assert rows == [expected_key]
        assert cp.get_checkpoint(*expected_key) == expected_state

    def test_kwargs_only_4_positionals_and_omitted_defaults_regression(self, official_checkpointer):
        """(c) Regressao: so kwargs, 4 posicionais e campos ausentes com defaults atuais continuam funcionando."""
        cp, _, _ = official_checkpointer

        assert cp.save_checkpoint_detailed(
            agent_id="ag_kw", session_id="s_kw", checkpoint_id="c_kw", state_dict={"m": "kw"}
        ) == (True, None)
        assert cp.get_checkpoint("ag_kw", "s_kw", "c_kw") == {"m": "kw"}

        assert cp.save_checkpoint_detailed("ag_p", "s_p", "c_p", {"m": "pos"}) == (True, None)
        assert cp.get_checkpoint("ag_p", "s_p", "c_p") == {"m": "pos"}

        # Campos ausentes preservam defaults atuais ("" e {})
        assert cp.save_checkpoint_detailed("ag_def") == (True, None)
        assert cp.get_checkpoint("ag_def", "", "") == {}

    @pytest.mark.parametrize(
        "field_name,args,kwargs",
        [
            ("agent_id", ("agA",), {"agent_id": "outro", "session_id": "s", "checkpoint_id": "c", "state_dict": {}}),
            ("session_id", ("agA", "s_pos"), {"session_id": "s_kw", "checkpoint_id": "c", "state_dict": {}}),
            ("checkpoint_id", ("agA", "s", "c_pos"), {"checkpoint_id": "c_kw", "state_dict": {}}),
            ("state_dict", ("agA", "s", "c", {"a": 1}), {"state_dict": {"b": 2}}),
        ],
    )
    def test_duplicate_positional_and_kwarg_fails_loudly_without_writing(
        self, official_checkpointer, field_name, args, kwargs
    ):
        """(d) Mesmo campo por posicao e por nome falha explicitamente sem gravar em agent_checkpoints."""
        cp, _, db_path = official_checkpointer
        snapshot_before = dict(vars(cp))

        ok, err = cp.save_checkpoint_detailed(*args, **kwargs)
        assert ok is False
        assert isinstance(err, str) and field_name in err
        assert vars(cp) == snapshot_before

        wrapped_ok = cp.save_checkpoint(*args, **kwargs)
        assert wrapped_ok is False
        assert cp.last_error == err

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_checkpoints").fetchone()[0]
        finally:
            conn.close()
        assert count == 0
