"""archive/v4-experimental/tests/test_governor_wiring_archived.py

Testes extraidos de tests/test_governor_wiring.py durante a quarentena 4.5d:
- T3 (Lote A): acoplamento com interface.telemetry_api.mcp_governor
"""
from unittest.mock import MagicMock

from storage.store import SqliteStore
from interface.mcp_server import GrafoConciergeServer


def test_t3_governor_identity_matches_telemetry_mcp_governor(tmp_path, monkeypatch):
    """T3: Identidade — o governor do servidor É O MESMO objeto que interface.telemetry_api.mcp_governor quando ambos são importados."""
    monkeypatch.setattr("interface.mcp_server.governor", None)
    monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)

    db_file = str(tmp_path / "test_t3.db")
    store = SqliteStore(db_file)
    gc = MagicMock()
    gc._store = store
    server = GrafoConciergeServer(concierge=gc)

    from interface.telemetry_api import mcp_governor
    assert server._governor is mcp_governor, "O governor do servidor deve ser o mesmo objeto exportado por telemetry_api"
    store.close()


def test_t5_action_hooks_lazy_export_preserves_contract():
    """T5 (Lote C): from interface import ActionHooks e interface.action_hooks.ActionHooks."""
    import interface
    from interface.action_hooks import ActionHooks as DirectActionHooks
    assert hasattr(interface, "ActionHooks"), "interface deve expor ActionHooks"
    assert interface.ActionHooks is DirectActionHooks, "interface.ActionHooks deve ser idêntico a interface.action_hooks.ActionHooks"
