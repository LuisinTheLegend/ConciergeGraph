"""
tests/test_mcp_security_governance.py — Testes adversariais e de regressão para BL-011 e BL-013 (Rodada 4.6-C2).

Valida:
  - BL-011: fechamento de injeção de `session_id` fantasma, remoção de `session_id` em
    `concierge_set_state`, rejeição de argumentos extras não declarados e de payload não-dict,
    vinculação da sessão ao objeto `session` do transporte MCP (WeakKeyDictionary),
    e resistência a spoofing via `_meta.client_id`.
  - BL-013: filtragem obrigatória de `list_tools()` e do handler low-level `ListToolsRequest`
    do servidor MCP em `PLANNING` (17), `EXECUTION` (29) e `MAINTENANCE` (31).
"""

from __future__ import annotations

import asyncio
import gc as py_gc
from types import SimpleNamespace
from unittest.mock import MagicMock

import mcp.types as types
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
import pytest

from core.mcp_governor import MCPToolGovernor, SecurityException
import interface.mcp_server as mcp_server_mod
from interface.mcp_server import GrafoConciergeServer
from storage.store import SqliteStore


class _DummyTransportSession:
    """Sessão MCP simulada com suporte a weakref (como mcp.server.session.ServerSession)."""


class _NonWeakrefSession:
    __slots__ = ()


def _make_server(tmp_path, monkeypatch, default_state: str = "PLANNING", max_state: str | None = None):
    monkeypatch.setattr(mcp_server_mod, "governor", None)
    monkeypatch.setattr(mcp_server_mod, "db_manager", None)
    monkeypatch.setattr(mcp_server_mod, "checkpointer", None)
    monkeypatch.setattr(mcp_server_mod, "graph_rag", None)
    gov = MCPToolGovernor(default_state=default_state, max_state=max_state)
    monkeypatch.setattr("core.mcp_governor._shared_governor", gov)

    store = SqliteStore(str(tmp_path / f"sec_{default_state}.db"))
    gc_facade = MagicMock()
    gc_facade.config = None
    gc_facade._store = store
    gc_facade.reset_collection = MagicMock(return_value=True)
    gc_facade.status = MagicMock(return_value={"status": "ok"})
    server = GrafoConciergeServer(concierge=gc_facade)
    return server, gc_facade, store


def test_bl011_ghost_session_id_injection_blocked_even_when_pre_elevated(tmp_path, monkeypatch):
    """Exploit BL-011: passar {'session_id': 'bypass_token'} a reset_collection não contorna a sessão ativa."""
    server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="MAINTENANCE")
    try:
        # Mesmo se outra sessão estivesse em MAINTENANCE no governor, a sessão ativa está em EXECUTION
        server.governor.set_session_state("bypass_token", "MAINTENANCE")

        with pytest.raises(SecurityException):
            asyncio.run(
                server.mcp._tool_manager.call_tool("reset_collection", {"session_id": "bypass_token"})
            )
        gc_facade.reset_collection.assert_not_called()

        # Mesmo em protocolo CallToolRequest real (low-level server retorna CallToolResult isError=True)
        call_handler = server.mcp._mcp_server.request_handlers[types.CallToolRequest]
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="reset_collection",
                arguments={"session_id": "bypass_token"},
            ),
        )
        sess = _DummyTransportSession()
        tok = request_ctx.set(
            RequestContext(request_id="req-1", meta=None, session=sess, lifespan_context=None)
        )
        try:
            res = asyncio.run(call_handler(req))
        finally:
            request_ctx.reset(tok)
        assert res.root.isError is True
        gc_facade.reset_collection.assert_not_called()
    finally:
        store.close()


def test_bl011_concierge_set_state_signature_ceiling_and_downgrade(tmp_path, monkeypatch):
    """concierge_set_state não aceita session_id, respeita teto max_state e permite downgrade."""
    server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
    try:
        tool = server.mcp._tool_manager.get_tool("concierge_set_state")
        assert tool is not None
        props = set((tool.parameters.get("properties") or {}).keys())
        assert props == {"state_name"}

        sess = _DummyTransportSession()
        tok = request_ctx.set(
            RequestContext(request_id="req-set", meta=None, session=sess, lifespan_context=None)
        )
        try:
            # Tentar passar session_id extra deve ser rejeitado com SecurityException
            with pytest.raises(SecurityException):
                asyncio.run(
                    server.mcp._tool_manager.call_tool(
                        "concierge_set_state",
                        {"state_name": "EXECUTION", "session_id": "other_sess"},
                    )
                )

            # Tentar escalar acima do teto EXECUTION -> MAINTENANCE bloqueado
            with pytest.raises((SecurityException, ToolError)) as exc_up:
                asyncio.run(
                    server.mcp._tool_manager.call_tool(
                        "concierge_set_state",
                        {"state_name": "MAINTENANCE"},
                    )
                )
            err_up = exc_up.value
            if isinstance(err_up, ToolError):
                assert isinstance(err_up.__cause__, SecurityException)

            # Downgrade EXECUTION -> PLANNING permitido na sessão de transporte ativa
            down = asyncio.run(
                server.mcp._tool_manager.call_tool(
                    "concierge_set_state",
                    {"state_name": "PLANNING"},
                )
            )
            assert down["success"] is True
            assert down["active_state"] == "PLANNING"
            assert down["session_id"] != "default"

            # Agora em PLANNING, concierge_set_state (LOCAL_MUTATION) está bloqueada
            with pytest.raises(SecurityException):
                asyncio.run(
                    server.mcp._tool_manager.call_tool(
                        "concierge_set_state",
                        {"state_name": "EXECUTION"},
                    )
                )
        finally:
            request_ctx.reset(tok)
    finally:
        store.close()


def test_bl011_extra_undeclared_kwargs_and_malformed_arguments_rejected(tmp_path, monkeypatch):
    """Qualquer argumento extra não declarado ou payload não-dict é rejeitado antes do handler."""
    server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING")
    try:
        with pytest.raises(SecurityException):
            asyncio.run(
                server.mcp._tool_manager.call_tool("concierge_status", {"extra_injected": "x"})
            )
        gc_facade.status.assert_not_called()

        with pytest.raises(SecurityException):
            asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", "not-a-dict"))
        gc_facade.status.assert_not_called()

        # arguments=None é normalizado para {} e funciona em READ_ONLY
        ok = asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", None))
        assert ok["success"] is True
    finally:
        store.close()


def test_transport_session_isolation_meta_spoofing_immunity_and_gc(tmp_path, monkeypatch):
    """Sessões de transporte distintas ficam isoladas, ignoram _meta.client_id e são coletadas pelo GC."""
    server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
    try:
        sess_a = _DummyTransportSession()
        sess_b = _DummyTransportSession()

        # Sessão A faz downgrade para PLANNING (ignorando _meta.client_id forjado)
        tok_a = request_ctx.set(
            RequestContext(
                request_id="ra",
                meta=SimpleNamespace(client_id="default"),
                session=sess_a,
                lifespan_context=None,
            )
        )
        try:
            res_a = asyncio.run(
                server.mcp._tool_manager.call_tool("concierge_set_state", {"state_name": "PLANNING"})
            )
            sid_a = res_a["session_id"]
        finally:
            request_ctx.reset(tok_a)

        # Sessão B continua em EXECUTION e tenta falsificar _meta.client_id = sid_a
        tok_b = request_ctx.set(
            RequestContext(
                request_id="rb",
                meta=SimpleNamespace(client_id=sid_a),
                session=sess_b,
                lifespan_context=None,
            )
        )
        try:
            tools_b = asyncio.run(server.mcp.list_tools())
            assert len(tools_b) == 29
        finally:
            request_ctx.reset(tok_b)

        assert len(server._transport_sessions) == 2
        del sess_a
        py_gc.collect()
        assert len(server._transport_sessions) == 1

        # Sessão não-weakref falha fechado
        non_weak = _NonWeakrefSession()
        tok_nw = request_ctx.set(
            RequestContext(request_id="rnw", meta=None, session=non_weak, lifespan_context=None)
        )
        try:
            with pytest.raises(SecurityException):
                asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", {}))
        finally:
            request_ctx.reset(tok_nw)
    finally:
        store.close()


def test_bl013_list_tools_and_lowlevel_handler_always_filter_by_state(tmp_path, monkeypatch):
    """BL-013: server.mcp.list_tools() e ListToolsRequest low-level filtram sempre (17 / 29 / 31)."""
    server, _, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING", max_state="MAINTENANCE")
    try:
        list_handler = server.mcp._mcp_server.request_handlers[types.ListToolsRequest]
        sess = _DummyTransportSession()

        # 1. PLANNING (default) -> 17 READ_ONLY apenas
        tools_plan = asyncio.run(server.mcp.list_tools())
        names_plan = {t.name for t in tools_plan}
        assert len(names_plan) == 17
        assert not (names_plan & {"reset_collection", "delete_project", "concierge_commit", "concierge_set_state"})

        tok = request_ctx.set(
            RequestContext(request_id="r-list", meta=None, session=sess, lifespan_context=None)
        )
        try:
            low_plan = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
            assert {t.name for t in low_plan.root.tools} == names_plan
            # Chamada interna de cache miss passa req=None
            low_none = asyncio.run(list_handler(None))
            assert len(low_none.root.tools) == 17

            # 2. EXECUTION na sessão ativa -> 29 tools (sem DANGEROUS)
            sid = server._resolve_transport_session_id()
            server.governor.set_session_state(sid, "EXECUTION")
            assert len(asyncio.run(server.mcp.list_tools())) == 29
            low_exec = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
            exec_names = {t.name for t in low_exec.root.tools}
            assert len(exec_names) == 29
            assert "concierge_commit" in exec_names
            assert "concierge_set_state" in exec_names
            assert "delete_project" not in exec_names
            assert "reset_collection" not in exec_names

            # 3. MAINTENANCE na sessão ativa -> 31 tools
            server.governor.set_session_state(sid, "MAINTENANCE")
            assert len(asyncio.run(server.mcp.list_tools())) == 31
            low_maint = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
            maint_names = {t.name for t in low_maint.root.tools}
            assert len(maint_names) == 31
            assert {"delete_project", "reset_collection"}.issubset(maint_names)
        finally:
            request_ctx.reset(tok)
    finally:
        store.close()
