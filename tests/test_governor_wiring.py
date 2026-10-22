"""tests/test_governor_wiring.py

Testes da Rodada 4.2: Desacoplamento do MCPToolGovernor da telemetria e corte da cadeia de imports.
Verifica:
- T1: import interface.mcp_server nao arrasta agents nem action_hooks
- T2: construcao de GrafoConciergeServer nao arrasta telemetry_api nem fastapi
- T3: governor do servidor e identico ao exportado por telemetry_api (regressao)
- T4: governor usa o singleton compartilhado mesmo se telemetry_api falhar no import
- T5: interface.ActionHooks continua acessivel via export lazy (PEP 562)
"""
import os
import subprocess
import sys
from unittest.mock import MagicMock
import pytest

from storage.store import SqliteStore
from interface.mcp_server import GrafoConciergeServer


def test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks():
    """T1: Subprocesso limpo afirmando que 'agents.revisor_critico', 'agents' e 'interface.action_hooks' NÃO estão em sys.modules."""
    code = (
        "import sys\n"
        "import interface.mcp_server\n"
        "dragged = [m for m in ('agents.revisor_critico', 'agents', 'interface.action_hooks') if m in sys.modules]\n"
        "if dragged:\n"
        "    print('DRAGGED:', dragged)\n"
        "    sys.exit(1)\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, f"Módulos arrastados indevidamente no import de interface.mcp_server: {res.stdout.strip()} {res.stderr.strip()}"


def test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi(tmp_path):
    """T2: Subprocesso limpo construindo GrafoConciergeServer afirmando que 'interface.telemetry_api' e 'fastapi' NÃO estão em sys.modules."""
    db_file = str(tmp_path / "test_wire.db")
    code = (
        "import sys\n"
        "from unittest.mock import MagicMock\n"
        "from storage.store import SqliteStore\n"
        "from interface.mcp_server import GrafoConciergeServer\n"
        f"store = SqliteStore(r'{db_file}')\n"
        "gc = MagicMock()\n"
        "gc._store = store\n"
        "server = GrafoConciergeServer(concierge=gc)\n"
        "store.close()\n"
        "dragged = [m for m in ('interface.telemetry_api', 'fastapi') if m in sys.modules]\n"
        "if dragged:\n"
        "    print('DRAGGED:', dragged)\n"
        "    sys.exit(1)\n"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0, f"Módulos arrastados na construção de GrafoConciergeServer: {res.stdout.strip()} {res.stderr.strip()}"


def test_t3_governor_identity_matches_telemetry_mcp_governor(tmp_path):
    """T3: Identidade — o governor do servidor É O MESMO objeto que interface.telemetry_api.mcp_governor quando ambos são importados."""
    db_file = str(tmp_path / "test_t3.db")
    store = SqliteStore(db_file)
    gc = MagicMock()
    gc._store = store
    server = GrafoConciergeServer(concierge=gc)

    from interface.telemetry_api import mcp_governor
    assert server._governor is mcp_governor, "O governor do servidor deve ser o mesmo objeto exportado por telemetry_api"
    store.close()


def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path, monkeypatch):
    """T4: Com sys.modules['interface.telemetry_api'] = None (import quebrado), o servidor usa o MESMO singleton compartilhado."""
    import core.mcp_governor
    assert hasattr(core.mcp_governor, "get_shared_governor"), "core.mcp_governor deve expor get_shared_governor()"
    shared_gov = core.mcp_governor.get_shared_governor()

    # Simula falha total ao importar interface.telemetry_api
    monkeypatch.setitem(sys.modules, "interface.telemetry_api", None)

    db_file = str(tmp_path / "test_t4.db")
    store = SqliteStore(db_file)
    gc = MagicMock()
    gc._store = store
    server = GrafoConciergeServer(concierge=gc)

    assert server._governor is shared_gov, "Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar"
    store.close()


def test_t5_action_hooks_lazy_export_preserves_contract():
    """T5: from interface import ActionHooks continua funcionando (lazy) e interface.ActionHooks is interface.action_hooks.ActionHooks."""
    import interface
    from interface.action_hooks import ActionHooks as DirectActionHooks
    assert hasattr(interface, "ActionHooks"), "interface deve expor ActionHooks"
    assert interface.ActionHooks is DirectActionHooks, "interface.ActionHooks deve ser idêntico a interface.action_hooks.ActionHooks"
