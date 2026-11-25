"""tests/test_governor_wiring.py

Testes de fiação e isolamento do MCPToolGovernor no GrafoConciergeServer:
- T1: import de interface.mcp_server mantém governor preguiçoso (None), não carrega
      core.mcp_governor e não arrasta módulos arquivados ou frameworks web externos
- T2: construção de GrafoConciergeServer não arrasta archive/nem frameworks web externos,
      conecta ao singleton compartilhado get_shared_governor() e expõe catálogo limpo (31 == 31)
- T4: governador usa o singleton compartilhado mesmo se telemetry_api falhar no import
- T5: governed_list_tools filtra ferramentas FastMCP reais pela sessão ativa do transporte (sem expor catálogo sem filtro)
"""
import asyncio
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

from storage.store import SqliteStore
from interface.mcp_server import GrafoConciergeServer


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks():
    """T1: Subprocesso limpo afirmando governor preguiçoso e ausência de módulos arquivados/frameworks externos no import."""
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        f"archive_dir = Path({repr(str((REPO_ROOT / 'archive').resolve()))})\n"
        "import interface.mcp_server\n"
        "assert interface.mcp_server.governor is None, 'governor deveria permanecer None no import'\n"
        "assert 'core.mcp_governor' not in sys.modules, 'core.mcp_governor nao deveria carregar no import'\n"
        "banned_names = ('agents.revisor_critico', 'agents', 'agent', 'interface.action_hooks', 'interface.telemetry_api', 'fastapi', 'flask', 'django')\n"
        "dragged = [m for m in banned_names if m in sys.modules]\n"
        "archive_mods = []\n"
        "for name, mod in list(sys.modules.items()):\n"
        "    if name == 'archive' or name.startswith('archive.'):\n"
        "        archive_mods.append(name)\n"
        "        continue\n"
        "    mod_file = getattr(mod, '__file__', None)\n"
        "    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n"
        "        archive_mods.append(f'{name}:{mod_file}')\n"
        "if dragged or archive_mods:\n"
        "    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n"
        "    sys.exit(1)\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Falha na guarda de import T1: {res.stdout.strip()} {res.stderr.strip()}"


def test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi(tmp_path):
    """T2: Subprocesso limpo construindo GrafoConciergeServer afirmando isolamento, singleton real e catálogo limpo."""
    db_file = str(tmp_path / "test_wire.db")
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from unittest.mock import MagicMock\n"
        "import core.mcp_governor\n"
        "from storage.store import SqliteStore\n"
        "import interface.mcp_server\n"
        "from interface.mcp_server import GrafoConciergeServer\n"
        f"archive_dir = Path({repr(str((REPO_ROOT / 'archive').resolve()))})\n"
        f"store = SqliteStore({repr(db_file)})\n"
        "try:\n"
        "    gc = MagicMock()\n"
        "    gc._store = store\n"
        "    server = GrafoConciergeServer(concierge=gc)\n"
        "    shared_gov = core.mcp_governor.get_shared_governor()\n"
        "    assert server._governor is shared_gov\n"
        "    assert server.governor is server._governor\n"
        "    assert interface.mcp_server.governor is server._governor\n"
        "    registered = set(server.mcp._tool_manager._tools.keys())\n"
        "    classified = set(server._governor.TOOL_CLASSIFICATION.keys())\n"
        "    assert registered == classified, f'Mismatch: reg-cls={sorted(registered-classified)} cls-reg={sorted(classified-registered)}'\n"
        "    assert len(registered) == 31\n"
        "    assert all(r['allowed_tools'] == [] for r in server._governor.TOOL_DISCLOSURE_MATRIX.values())\n"
        "finally:\n"
        "    store.close()\n"
        "banned_names = ('interface.telemetry_api', 'interface.action_hooks', 'agents', 'agent', 'fastapi', 'flask', 'django')\n"
        "dragged = [m for m in banned_names if m in sys.modules]\n"
        "archive_mods = []\n"
        "for name, mod in list(sys.modules.items()):\n"
        "    if name == 'archive' or name.startswith('archive.'):\n"
        "        archive_mods.append(name)\n"
        "        continue\n"
        "    mod_file = getattr(mod, '__file__', None)\n"
        "    if mod_file and Path(mod_file).resolve().is_relative_to(archive_dir):\n"
        "        archive_mods.append(f'{name}:{mod_file}')\n"
        "if dragged or archive_mods:\n"
        "    print('DRAGGED:', dragged, 'ARCHIVE:', archive_mods)\n"
        "    sys.exit(1)\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Falha na guarda de construção T2: {res.stdout.strip()} {res.stderr.strip()}"


def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path, monkeypatch):
    """T4: Com sys.modules['interface.telemetry_api'] = None (import quebrado), o servidor usa o MESMO singleton compartilhado."""
    # Zera sentinelas globais para garantir isolamento estrito e independencia de ordem
    monkeypatch.setattr("interface.mcp_server.governor", None)
    monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
    monkeypatch.setattr("core.mcp_governor._shared_governor", None)

    import core.mcp_governor
    assert hasattr(core.mcp_governor, "get_shared_governor"), "core.mcp_governor deve expor get_shared_governor()"
    shared_gov = core.mcp_governor.get_shared_governor()

    # Simula falha total ao importar interface.telemetry_api
    monkeypatch.setitem(sys.modules, "interface.telemetry_api", None)

    db_file = str(tmp_path / "test_t4.db")
    store = SqliteStore(db_file)
    try:
        gc = MagicMock()
        gc._store = store
        server = GrafoConciergeServer(concierge=gc)

        assert server._governor is shared_gov, "Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar"
    finally:
        store.close()


def test_t5_governed_list_tools_filters_by_transport_session_state(tmp_path, monkeypatch):
    """T5: governed_list_tools sempre filtra Tool reais do FastMCP pelo estado da sessão de transporte."""
    monkeypatch.delenv("GRAFO_DEFAULT_STATE", raising=False)
    monkeypatch.setattr("interface.mcp_server.governor", None)
    monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
    monkeypatch.setattr("core.mcp_governor._shared_governor", None)

    db_file = str(tmp_path / "test_t5_list.db")
    store = SqliteStore(db_file)
    try:
        gc = MagicMock()
        gc._store = store
        server = GrafoConciergeServer(concierge=gc)

        # Sem request_ctx ativo -> sessão "default" em PLANNING (17 ferramentas READ_ONLY)
        unscoped = asyncio.run(server.mcp.list_tools())
        assert len(unscoped) == 17
        assert "default" not in server.governor.sessions_state

        # Em request_ctx com sessão de transporte dedicada -> "default" segue intocado
        from mcp.server.lowlevel.server import request_ctx
        from mcp.shared.context import RequestContext

        class _Sess:
            pass

        sess = _Sess()
        monkeypatch.setattr(server.governor, "max_state", "MAINTENANCE")
        tok = request_ctx.set(
            RequestContext(request_id="t5", meta=None, session=sess, lifespan_context=None)
        )
        try:
            sid = server._resolve_transport_session_id()
            assert sid != "default"

            server.governor.set_session_state(sid, "PLANNING")
            planning_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
            assert len(planning_names) == 17
            assert "get_full_topology" in planning_names
            assert "concierge_set_state" not in planning_names
            assert "concierge_commit" not in planning_names
            assert "delete_project" not in planning_names
            assert "reset_collection" not in planning_names

            server.governor.set_session_state(sid, "EXECUTION")
            exec_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
            assert len(exec_names) == 29
            assert "concierge_set_state" in exec_names
            assert "concierge_commit" in exec_names
            assert "delete_project" not in exec_names
            assert "reset_collection" not in exec_names

            server.governor.set_session_state(sid, "MAINTENANCE")
            maint_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
            assert len(maint_names) == 31
            assert {"delete_project", "reset_collection"}.issubset(maint_names)
            assert "default" not in server.governor.sessions_state
        finally:
            request_ctx.reset(tok)
    finally:
        store.close()
