import pytest
import os
import shutil
import sys

# Garante import do setup_workspace e bootstrap de tests/memory_stress_test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.memory_stress_test import setup_workspace, bootstrap, TEST_DIR

@pytest.fixture(scope="module")
def stress_components():
    """Inicializa os componentes reais uma única vez para o módulo de teste de stress."""
    setup_workspace()
    store, vector, embedder, manager, janitor = bootstrap()
    yield store, vector, embedder, manager, janitor
    # Cleanup após a execução do módulo
    try:
        store.close()
    except Exception:
        pass
    try:
        shutil.rmtree(TEST_DIR, ignore_errors=True)
    except Exception:
        pass

@pytest.fixture(scope="module")
def store(stress_components):
    return stress_components[0]

@pytest.fixture(scope="module")
def vector(stress_components):
    return stress_components[1]

@pytest.fixture(scope="module")
def embedder(stress_components):
    return stress_components[2]

@pytest.fixture(scope="module")
def manager(stress_components):
    return stress_components[3]

@pytest.fixture(scope="module")
def janitor(stress_components):
    return stress_components[4]


# ---------------------------------------------------------------------------
# Fixture autouse: Detecção de vazamento de variáveis globais em interface.mcp_server
# ---------------------------------------------------------------------------

_MCP_TRACKED_GLOBALS = ("db_manager", "graph_rag", "_gc", "checkpointer", "governor", "_mcp_handler")
_MISSING_SENTINEL = object()


@pytest.fixture(autouse=True)
def check_mcp_globals_leak():
    """Garante que nenhum teste vaze ou altere por identidade variáveis globais em interface.mcp_server."""
    mod = sys.modules.get("interface.mcp_server")
    before_state = {}
    if mod is not None:
        for var in _MCP_TRACKED_GLOBALS:
            before_state[var] = getattr(mod, var, _MISSING_SENTINEL)
    else:
        for var in _MCP_TRACKED_GLOBALS:
            before_state[var] = None if var in ("db_manager", "graph_rag", "checkpointer", "governor") else _MISSING_SENTINEL

    yield

    mod_after = sys.modules.get("interface.mcp_server")
    if mod_after is not None:
        for var in _MCP_TRACKED_GLOBALS:
            orig = before_state.get(var, _MISSING_SENTINEL)
            curr = getattr(mod_after, var, _MISSING_SENTINEL)
            assert curr is orig, (
                f"Global variable 'mcp_server.{var}' leaked or modified by identity during test: "
                f"expected {orig!r} (id={id(orig)}), got {curr!r} (id={id(curr)})"
            )
