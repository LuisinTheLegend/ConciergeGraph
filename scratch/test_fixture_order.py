import pytest

@pytest.fixture(autouse=True)
def my_autouse():
    import sys
    print("AUTOUSE_SETUP")
    yield
    mod = sys.modules.get("interface.mcp_server")
    print(f"AUTOUSE_TEARDOWN: db_manager={getattr(mod, 'db_manager', None)}")

def test_example(monkeypatch):
    import interface.mcp_server as mcp_server
    print(f"BEFORE MONKEYPATCH: db_manager={mcp_server.db_manager}")
    monkeypatch.setattr(mcp_server, "db_manager", "DUMMY")
    print(f"INSIDE TEST: db_manager={mcp_server.db_manager}")
