"""Testes de propriedade persistente em checkpoints (BL-012 / Rodada 4.6-C3)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext

from core.checkpointer import AgnosticCheckpointer
from core.database import ConciergeDatabaseManager
from core.mcp_governor import MCPToolGovernor, SecurityException
import interface.mcp_server as mcp_server_mod
from interface.mcp_server import GrafoConciergeServer
from main import redact_log_secrets
from storage.store import SqliteStore


class DummyTransportSession:
    """Objeto weakref-compatível para simular ServerSession MCP em testes."""

    def __init__(self, label: str) -> None:
        self.label = label


def _make_db_and_cp(db_path: Path) -> tuple[SqliteStore, ConciergeDatabaseManager, AgnosticCheckpointer]:
    store = SqliteStore(str(db_path))
    db_mgr = ConciergeDatabaseManager(str(db_path))
    cp = AgnosticCheckpointer(db_mgr)
    return store, db_mgr, cp


def _make_server(db_path: Path, monkeypatch, default_state: str = "EXECUTION", max_state: str | None = None):
    monkeypatch.setattr(mcp_server_mod, "governor", None)
    monkeypatch.setattr(mcp_server_mod, "db_manager", None)
    monkeypatch.setattr(mcp_server_mod, "checkpointer", None)
    monkeypatch.setattr(mcp_server_mod, "graph_rag", None)
    gov = MCPToolGovernor(default_state=default_state, max_state=max_state)
    monkeypatch.setattr("core.mcp_governor._shared_governor", gov)

    store = SqliteStore(str(db_path))
    gc_facade = MagicMock()
    gc_facade.config = None
    gc_facade._store = store
    server = GrafoConciergeServer(concierge=gc_facade)
    return server, store


def _call_with_req_ctx(server: GrafoConciergeServer, session, request_obj, tool_name: str, args: dict):
    """Executa call_tool com ContextVar request_ctx oficial da sessão MCP."""
    tok = request_ctx.set(
        RequestContext(
            request_id="req-bl012",
            meta=None,
            session=session,
            lifespan_context=None,
            request=request_obj,
        )
    )
    try:
        return asyncio.run(server.mcp._tool_manager.call_tool(tool_name, args))
    finally:
        request_ctx.reset(tok)


def test_direct_checkpointer_blocks_all_four_cross_owner_vectors(tmp_path):
    """Bloqueia get, list, overwrite e injeção de novo checkpoint_id em namespace alheio."""
    db_path = tmp_path / "bl012_direct.db"
    store, _, cp = _make_db_and_cp(db_path)
    try:
        victim_tok = "test-owner-token-victim-alpha"
        attacker_tok = "test-owner-token-attacker-beta"

        ok, err = cp.save_checkpoint_detailed(
            "ag-1", "sess-1", "cp-1", {"secret": "classified"}, owner_token=victim_tok
        )
        assert (ok, err) == (True, None)

        # Dono legítimo acessa normalmente
        assert cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=victim_tok) == {
            "secret": "classified"
        }
        assert len(cp.list_checkpoints("ag-1", "sess-1", owner_token=victim_tok)) == 1

        # Vetor 1: get_checkpoint por outro dono ou sem token
        with pytest.raises(PermissionError):
            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=attacker_tok)
        with pytest.raises(PermissionError):
            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token="")
        with pytest.raises(PermissionError):
            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=None)

        # Vetor 2: list_checkpoints por outro dono ou sem token
        with pytest.raises(PermissionError):
            cp.list_checkpoints("ag-1", "sess-1", owner_token=attacker_tok)
        with pytest.raises(PermissionError):
            cp.list_checkpoints("ag-1", "sess-1", owner_token="")
        with pytest.raises(PermissionError):
            cp.list_checkpoints("ag-1", "sess-1", owner_token=None)

        # Vetor 3: sobrescrever checkpoint existente no namespace alheio
        with pytest.raises(PermissionError):
            cp.save_checkpoint_detailed(
                "ag-1", "sess-1", "cp-1", {"tampered": True}, owner_token=attacker_tok
            )
        with pytest.raises(PermissionError):
            cp.save_checkpoint(
                "ag-1", "sess-1", "cp-1", {"tampered": True}, owner_token=""
            )

        # Vetor 4: injetar novo checkpoint_id dentro do namespace (ag-1, sess-1) alheio
        with pytest.raises(PermissionError):
            cp.save_checkpoint_detailed(
                "ag-1", "sess-1", "cp-injected", {"evil": 1}, owner_token=attacker_tok
            )
        with pytest.raises(PermissionError):
            cp.save_checkpoint(
                "ag-1", "sess-1", "cp-injected", {"evil": 1}, owner_token=None
            )

        # Namespace diferente pertence normalmente ao outro dono
        assert cp.save_checkpoint(
            "ag-1", "sess-other", "cp-1", {"own": True}, owner_token=attacker_tok
        ) is True

        # Conteúdo original do dono legítimo permanece intacto
        assert cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=victim_tok) == {
            "secret": "classified"
        }
        timeline = cp.list_checkpoints("ag-1", "sess-1", owner_token=victim_tok)
        assert [row["checkpoint_id"] for row in timeline] == ["cp-1"]
    finally:
        store.close()


def test_ownership_persists_across_restart_and_never_leaks_secrets(tmp_path, monkeypatch):
    """Posse sobrevive ao restart em SQLite, grava apenas SHA-256 hex e redige env var."""
    db_path = tmp_path / "bl012_restart.db"
    victim_tok = "test-owner-token-persistent-v1"
    attacker_tok = "test-owner-token-persistent-v2"
    expected_hash = hashlib.sha256(victim_tok.encode("utf-8")).hexdigest()

    store1, _, cp1 = _make_db_and_cp(db_path)
    try:
        state_before = dict(vars(cp1))
        ok, err = cp1.save_checkpoint_detailed(
            "ag-r", "sess-r", "cp-r", {"step": 10}, owner_token=victim_tok
        )
        assert (ok, err) == (True, None)
        assert vars(cp1) == state_before
    finally:
        store1.close()

    # Verificar direto no SQLite que plaintext não foi salvo e apenas o hash SHA-256 existe
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT owner_hash FROM agent_checkpoints WHERE agent_id='ag-r' AND session_id='sess-r' AND checkpoint_id='cp-r'"
        ).fetchone()
    assert row is not None
    assert row[0] == expected_hash
    assert victim_tok not in row[0]

    # Simular restart completo: novas instâncias de Store e Checkpointer
    store2, _, cp2 = _make_db_and_cp(db_path)
    try:
        assert cp2.get_checkpoint("ag-r", "sess-r", "cp-r", owner_token=victim_tok) == {"step": 10}
        with pytest.raises(PermissionError) as exc_info:
            cp2.get_checkpoint("ag-r", "sess-r", "cp-r", owner_token=attacker_tok)
        msg = str(exc_info.value)
        assert victim_tok not in msg
        assert attacker_tok not in msg
        assert expected_hash not in msg
        assert expected_hash[:12] not in msg
    finally:
        store2.close()

    # main.redact_log_secrets deve redigir GRAFO_AGENT_TOKEN
    monkeypatch.setenv("GRAFO_AGENT_TOKEN", victim_tok)
    redacted = redact_log_secrets(f"token={victim_tok} connected")
    assert victim_tok not in redacted
    assert "[REDACTED]" in redacted


def test_legacy_five_column_schema_migrates_on_store_boot_and_is_fail_closed(tmp_path):
    """Migra tabela legada de 5 colunas no boot do SqliteStore sem perder dados e sem adoção silenciosa."""
    db_path = tmp_path / "bl012_legacy.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE agent_checkpoints ("
            "agent_id TEXT NOT NULL, "
            "session_id TEXT NOT NULL, "
            "checkpoint_id TEXT NOT NULL, "
            "state_blob TEXT NOT NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
            ");"
        )
        conn.execute(
            "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob) "
            "VALUES ('legacy_ag', 'legacy_sess', 'legacy_cp', '{\"step\": 42}');"
        )
        conn.commit()

    # Boot apenas do SqliteStore (sem instanciar AgnosticCheckpointer antes)
    store1 = SqliteStore(str(db_path))
    store1.close()

    with sqlite3.connect(str(db_path)) as conn:
        cols = {row[1]: row for row in conn.execute("PRAGMA table_info(agent_checkpoints)").fetchall()}
        assert "owner_hash" in cols
        row = conn.execute(
            "SELECT state_blob, owner_hash FROM agent_checkpoints "
            "WHERE agent_id='legacy_ag' AND session_id='legacy_sess' AND checkpoint_id='legacy_cp'"
        ).fetchone()
        assert row is not None
        assert json.loads(row[0]) == {"step": 42}
        assert row[1] == ""

    # 2o boot para provar idempotência da migração
    store2, _, cp = _make_db_and_cp(db_path)
    try:
        # Chamador legado sem token continua compatível com linha legacy owner_hash == ''
        assert cp.get_checkpoint("legacy_ag", "legacy_sess", "legacy_cp") == {"step": 42}
        assert len(cp.list_checkpoints("legacy_ag", "legacy_sess")) == 1

        # Chamador autenticado NÃO adota nem lê linha legacy (hash diferente de '')
        with pytest.raises(PermissionError):
            cp.get_checkpoint(
                "legacy_ag", "legacy_sess", "legacy_cp", owner_token="test-owner-token-claimer"
            )
        with pytest.raises(PermissionError):
            cp.save_checkpoint_detailed(
                "legacy_ag", "legacy_sess", "legacy_cp2", {"step": 99}, owner_token="test-owner-token-claimer"
            )
    finally:
        store2.close()


def test_mcp_stdio_env_and_ephemeral_session_isolation(tmp_path, monkeypatch):
    """stdio usa GRAFO_AGENT_TOKEN quando definido ou segredo efêmero por ServerSession."""
    db_path = tmp_path / "bl012_mcp_stdio.db"

    # Caso 1: GRAFO_AGENT_TOKEN definido em stdio (persiste entre instâncias de servidor)
    monkeypatch.setenv("GRAFO_AGENT_TOKEN", "test-stdio-owner-token-alpha")
    srv_owner, store_owner = _make_server(db_path, monkeypatch, default_state="EXECUTION")
    try:
        sess_a = DummyTransportSession("stdio-A")
        save_res = _call_with_req_ctx(
            srv_owner,
            sess_a,
            None,
            "agent_save_checkpoint",
            {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1", "state_dict": {"ok": 1}},
        )
        payload = json.loads(save_res) if isinstance(save_res, str) else save_res
        assert payload["success"] is True

        # Tentativa de passar owner_token forjado como argumento deve ser rejeitada pelo governor
        with pytest.raises(SecurityException):
            _call_with_req_ctx(
                srv_owner,
                sess_a,
                None,
                "agent_save_checkpoint",
                {
                    "agent_id": "mcp_ag",
                    "session_id": "mcp_s1",
                    "checkpoint_id": "cp1",
                    "state_dict": {"ok": 2},
                    "owner_token": "forged",
                },
            )
    finally:
        store_owner.close()

    # Novo servidor com mesmo token (simulando restart) recupera normalmente
    srv_restart, store_restart = _make_server(db_path, monkeypatch, default_state="EXECUTION")
    try:
        assert _call_with_req_ctx(
            srv_restart,
            DummyTransportSession("stdio-A2"),
            None,
            "agent_get_checkpoint",
            {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1"},
        ) == {"ok": 1}
    finally:
        store_restart.close()

    # Novo servidor com outro GRAFO_AGENT_TOKEN deve ser bloqueado em get, list, overwrite e injeção
    monkeypatch.setenv("GRAFO_AGENT_TOKEN", "test-stdio-owner-token-beta")
    srv_attacker, store_attacker = _make_server(db_path, monkeypatch, default_state="EXECUTION")
    try:
        sess_b = DummyTransportSession("stdio-B")
        for tool_name, tool_args in (
            ("agent_get_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1"}),
            ("agent_list_checkpoints", {"agent_id": "mcp_ag", "session_id": "mcp_s1"}),
            ("agent_save_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1", "state_dict": {"hack": 1}}),
            ("agent_save_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp2", "state_dict": {"hack": 2}}),
        ):
            with pytest.raises((PermissionError, ToolError)) as exc_info:
                _call_with_req_ctx(srv_attacker, sess_b, None, tool_name, tool_args)
            if isinstance(exc_info.value, ToolError):
                assert isinstance(exc_info.value.__cause__, PermissionError)
    finally:
        store_attacker.close()

    # Caso 2: sem GRAFO_AGENT_TOKEN, cada ServerSession em stdio ganha seu segredo efêmero distinto
    monkeypatch.delenv("GRAFO_AGENT_TOKEN", raising=False)
    srv_ephem, store_ephem = _make_server(db_path, monkeypatch, default_state="EXECUTION")
    try:
        eph_s1 = DummyTransportSession("ephem-1")
        eph_s2 = DummyTransportSession("ephem-2")

        _call_with_req_ctx(
            srv_ephem,
            eph_s1,
            None,
            "agent_save_checkpoint",
            {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1", "state_dict": {"e": 1}},
        )
        assert _call_with_req_ctx(
            srv_ephem,
            eph_s1,
            None,
            "agent_get_checkpoint",
            {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1"},
        ) == {"e": 1}

        with pytest.raises((PermissionError, ToolError)) as exc_info:
            _call_with_req_ctx(
                srv_ephem,
                eph_s2,
                None,
                "agent_get_checkpoint",
                {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1"},
            )
        if isinstance(exc_info.value, ToolError):
            assert isinstance(exc_info.value.__cause__, PermissionError)
    finally:
        store_ephem.close()


def test_mcp_http_sse_decoupled_agent_token_and_ephemeral_isolation(tmp_path, monkeypatch):
    """HTTP/SSE lê exclusivamente X-Grafo-Agent-Token (sem fallback para Bearer) ou isola via segredo efêmero."""
    db_path = tmp_path / "bl012_mcp_sse.db"
    monkeypatch.delenv("GRAFO_AGENT_TOKEN", raising=False)

    server, store = _make_server(db_path, monkeypatch, default_state="EXECUTION")
    try:
        sess1 = DummyTransportSession("sse-1")
        sess2 = DummyTransportSession("sse-2")

        # 1. X-Grafo-Agent-Token identifica o dono independentemente de Authorization: Bearer
        _call_with_req_ctx(
            server,
            sess1,
            SimpleNamespace(
                headers={
                    "X-Grafo-Agent-Token": "test-sse-header-owner",
                    "Authorization": "Bearer test-sse-bearer-client-a",
                }
            ),
            "agent_save_checkpoint",
            {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1", "state_dict": {"sse": 1}},
        )

        # Reconexão em outra sessão com mesmo X-Grafo-Agent-Token (e outro Bearer) recupera normalmente
        assert _call_with_req_ctx(
            server,
            sess2,
            SimpleNamespace(
                headers={
                    "X-Grafo-Agent-Token": "test-sse-header-owner",
                    "Authorization": "Bearer test-sse-bearer-client-b",
                }
            ),
            "agent_get_checkpoint",
            {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1"},
        ) == {"sse": 1}

        # Mesmo com Bearer igual, outro X-Grafo-Agent-Token não acessa
        with pytest.raises((PermissionError, ToolError)) as exc_info:
            _call_with_req_ctx(
                server,
                sess2,
                SimpleNamespace(
                    headers={
                        "X-Grafo-Agent-Token": "test-sse-header-attacker",
                        "Authorization": "Bearer test-sse-bearer-client-a",
                    }
                ),
                "agent_get_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1"},
            )
        if isinstance(exc_info.value, ToolError):
            assert isinstance(exc_info.value.__cause__, PermissionError)

        # 2. Decisão 2A (4.7): mesmo Authorization: Bearer SEM X-Grafo-Agent-Token NÃO compartilha posse
        shared_bearer = "Bearer test-shared-sse-api-key-alpha"
        _call_with_req_ctx(
            server,
            sess1,
            SimpleNamespace(headers={"Authorization": shared_bearer}),
            "agent_save_checkpoint",
            {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1", "state_dict": {"b": 2}},
        )
        assert _call_with_req_ctx(
            server,
            sess1,
            SimpleNamespace(headers={"Authorization": shared_bearer}),
            "agent_get_checkpoint",
            {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1"},
        ) == {"b": 2}

        for tool_name, tool_args in (
            ("agent_get_checkpoint", {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1"}),
            ("agent_list_checkpoints", {"agent_id": "sse_ag", "session_id": "sse_s_bearer"}),
            ("agent_save_checkpoint", {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1", "state_dict": {"hijack": 1}}),
        ):
            with pytest.raises((PermissionError, ToolError)) as exc_info:
                _call_with_req_ctx(
                    server,
                    sess2,
                    SimpleNamespace(headers={"Authorization": shared_bearer}),
                    tool_name,
                    tool_args,
                )
            if isinstance(exc_info.value, ToolError):
                assert isinstance(exc_info.value.__cause__, PermissionError)

        # 3. Sem nenhum header de token em SSE, isola por ServerSession efêmero
        _call_with_req_ctx(
            server,
            sess1,
            SimpleNamespace(headers={}),
            "agent_save_checkpoint",
            {"agent_id": "sse_ag", "session_id": "sse_s_eph", "checkpoint_id": "cp1", "state_dict": {"e": 3}},
        )
        with pytest.raises((PermissionError, ToolError)):
            _call_with_req_ctx(
                server,
                sess2,
                SimpleNamespace(headers={}),
                "agent_get_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s_eph", "checkpoint_id": "cp1"},
            )
    finally:
        store.close()
