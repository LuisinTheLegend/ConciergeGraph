"""Testes de hardening do auth_middleware HTTP/SSE (Rodada 4.7-C1)."""
from __future__ import annotations

import hmac
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from core.mcp_governor import MCPToolGovernor
import interface.mcp_server as mcp_server_mod
from interface.mcp_server import GrafoConciergeServer
from storage.store import SqliteStore


def _make_sse_client(tmp_path, monkeypatch, api_key: str) -> tuple[TestClient, SqliteStore]:
    monkeypatch.setattr(mcp_server_mod, "governor", None)
    monkeypatch.setattr(mcp_server_mod, "db_manager", None)
    monkeypatch.setattr(mcp_server_mod, "checkpointer", None)
    monkeypatch.setattr(mcp_server_mod, "graph_rag", None)
    gov = MCPToolGovernor(default_state="PLANNING")
    monkeypatch.setattr("core.mcp_governor._shared_governor", gov)
    monkeypatch.setenv("GRAFO_API_KEY", api_key)

    store = SqliteStore(str(tmp_path / "sse_auth_47.db"))
    gc_facade = MagicMock()
    gc_facade.config = None
    gc_facade._store = store

    server = GrafoConciergeServer(concierge=gc_facade)
    app = server.mcp.sse_app()
    return TestClient(app), store


def test_sse_rejects_query_param_token_with_401(tmp_path, monkeypatch):
    """Query string ?token=<key> não é aceita em nenhuma rota (GET /sse ou POST /messages/)."""
    api_key = "test-sse-api-key-query-reject-alpha"
    client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
    try:
        r_sse = client.get(f"/sse?token={api_key}")
        assert r_sse.status_code == 401

        r_msg = client.post(f"/messages/?token={api_key}", json={"jsonrpc": "2.0", "id": 1})
        assert r_msg.status_code == 401
    finally:
        store.close()


def test_sse_rejects_missing_wrong_empty_or_non_bearer_auth(tmp_path, monkeypatch):
    """Credenciais ausentes, vazias, inválidas ou não-Bearer retornam HTTP 401."""
    api_key = "test-sse-api-key-creds-alpha"
    client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
    try:
        assert client.get("/sse").status_code == 401
        assert client.post("/messages/", json={}).status_code == 401
        assert client.post(
            "/messages/", headers={"Authorization": "Bearer wrong-key-alpha"}, json={}
        ).status_code == 401
        assert client.post(
            "/messages/", headers={"Authorization": "Bearer   "}, json={}
        ).status_code == 401
        assert client.post(
            "/messages/", headers={"Authorization": "Basic dGVzdDp0ZXN0"}, json={}
        ).status_code == 401
    finally:
        store.close()


def test_sse_accepts_bearer_and_case_insensitive_scheme_using_compare_digest(tmp_path, monkeypatch):
    """Aceita Bearer / bearer case-insensitive e compara com hmac.compare_digest."""
    api_key = "test-sse-api-key-bearer-alpha"
    client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
    try:
        real_compare = hmac.compare_digest
        calls: list[tuple[bytes | str, bytes | str]] = []

        def _spy_compare(a, b):
            calls.append((a, b))
            return real_compare(a, b)

        monkeypatch.setattr(hmac, "compare_digest", _spy_compare)

        r_upper = client.post(
            "/messages/",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        )
        assert r_upper.status_code != 401

        r_lower = client.post(
            "/messages/",
            headers={"Authorization": f"bearer {api_key}"},
            json={"jsonrpc": "2.0", "id": 2, "method": "ping"},
        )
        assert r_lower.status_code != 401

        r_wrong = client.post(
            "/messages/",
            headers={"Authorization": "bearer wrong-api-key-alpha"},
            json={"jsonrpc": "2.0", "id": 3, "method": "ping"},
        )
        assert r_wrong.status_code == 401

        assert len(calls) >= 3
        expected_bytes = api_key.encode("utf-8")
        assert any(
            pair in ((expected_bytes, expected_bytes), (api_key, api_key))
            for pair in calls
        )
    finally:
        store.close()


def test_health_get_and_head_bypass_auth_with_strict_payload(tmp_path, monkeypatch):
    """GET /health e HEAD /health retornam 200 {'status': 'ok'} sem auth mesmo com GRAFO_API_KEY."""
    api_key = "test-sse-health-key-alpha"
    client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
    try:
        r_get = client.get("/health")
        assert r_get.status_code == 200
        assert r_get.json() == {"status": "ok"}

        r_get_q = client.get("/health?probe=1")
        assert r_get_q.status_code == 200
        assert r_get_q.json() == {"status": "ok"}

        r_head = client.head("/health")
        assert r_head.status_code == 200
    finally:
        store.close()


def test_health_rejects_bypass_vectors_with_401(tmp_path, monkeypatch):
    """Vetores de bypass em /health e rotas MCP seguem protegidos com HTTP 401."""
    import asyncio

    api_key = "test-sse-health-bypass-key-alpha"
    client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
    try:
        assert client.post("/health").status_code == 401
        assert client.put("/health").status_code == 401
        assert client.delete("/health").status_code == 401
        assert client.get("/health/").status_code == 401
        assert client.get("/healthz").status_code == 401
        assert client.get("/health/extra").status_code == 401
        assert client.get("/%68ealth").status_code == 401
        assert client.get("/health%2f..%2fsse").status_code == 401
        assert client.get("/sse").status_code == 401

        # Escopo ASGI cru sem normalizacao de httpx: simula socket TCP direto com dot-segment / encoding
        asgi_app = client.app

        async def _call_raw(method: str, path: str, raw_path: bytes | None) -> int:
            sent: list[dict] = []
            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "query_string": b"",
                "headers": [(b"host", b"127.0.0.1:8000")],
            }
            if raw_path is not None:
                scope["raw_path"] = raw_path

            async def _receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def _send(message):
                sent.append(message)

            await asgi_app(scope, _receive, _send)
            start_msgs = [m for m in sent if m["type"] == "http.response.start"]
            return start_msgs[0]["status"]

        assert asyncio.run(_call_raw("GET", "/health/../sse", b"/health/../sse")) == 401
        assert asyncio.run(_call_raw("GET", "/healthz", None)) == 401
        assert asyncio.run(_call_raw("GET", "/health/extra", None)) == 401
        assert asyncio.run(_call_raw("GET", "/health", b"/%68ealth")) == 401
        assert asyncio.run(_call_raw("POST", "/health", b"/health")) == 401
        assert asyncio.run(_call_raw("GET", "/health", b"/health")) == 200
        assert asyncio.run(_call_raw("HEAD", "/health", b"/health")) == 200
    finally:
        store.close()


def test_health_without_api_key_returns_200(tmp_path, monkeypatch):
    """Com GRAFO_API_KEY ausente, GET /health e HEAD /health retornam 200."""
    client, store = _make_sse_client(tmp_path, monkeypatch, "")
    try:
        monkeypatch.delenv("GRAFO_API_KEY", raising=False)
        r_get = client.get("/health")
        assert r_get.status_code == 200
        assert r_get.json() == {"status": "ok"}
        assert client.head("/health").status_code == 200
    finally:
        store.close()
