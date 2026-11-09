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


import types
from typing import Any

# ---------------------------------------------------------------------------
# Fixtures autouse: Detecção dinâmica de vazamento de variáveis globais em interface.mcp_server
# Atua nos três níveis: função, classe e módulo (Pedido 4.4c - Bloco 2)
# ---------------------------------------------------------------------------

_MCP_GLOBALS_ALLOWLIST = {
    # Allowlist documentada: nenhuma variável global de interface.mcp_server possui autorização
    # para vazar mutações permanentes entre testes, classes ou módulos.
}


def _is_mutable_candidate(name: str, val: Any) -> bool:
    """Filtra o que for mutável (não-módulo, não-função pura, não-classe pura, não-built-in)."""
    if name.startswith("__") and name.endswith("__"):
        return False
    if isinstance(val, types.ModuleType):
        return False
    if isinstance(val, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        return False
    if isinstance(val, type):
        return False
    if getattr(type(val), "__module__", "") == "typing":
        return False
    if type(val).__name__ == "_Feature":
        return False
    return True


def _get_mcp_module():
    if "interface.mcp_server" not in sys.modules:
        try:
            import interface.mcp_server  # noqa: F401
        except Exception:
            return None
    return sys.modules.get("interface.mcp_server")


def _capture_mcp_snapshot() -> dict:
    mod = _get_mcp_module()
    if mod is None:
        return {}
    snapshot = {}
    for k, v in vars(mod).items():
        if _is_mutable_candidate(k, v) and k not in _MCP_GLOBALS_ALLOWLIST:
            snapshot[k] = (id(v), repr(v))
    return snapshot


def _verify_mcp_globals(before_snapshot: dict, scope_level: str):
    mod = _get_mcp_module()
    if mod is None:
        return
    current_vars = vars(mod)
    current_mutable_keys = {
        k for k, v in current_vars.items()
        if _is_mutable_candidate(k, v) and k not in _MCP_GLOBALS_ALLOWLIST
    }

    # 1. Checa variáveis removidas (M10e)
    for k in before_snapshot:
        if k not in current_vars:
            prev_id, prev_repr = before_snapshot[k]
            assert False, (
                f"[{scope_level}] Global variable 'mcp_server.{k}' was deleted during test execution: "
                f"was {prev_repr} (id={prev_id})"
            )

    # 2. Checa variáveis adicionadas (M10d)
    for k in current_mutable_keys:
        if k not in before_snapshot:
            curr_val = current_vars[k]
            assert False, (
                f"[{scope_level}] New global variable 'mcp_server.{k}' was added during test execution: "
                f"value {curr_val!r} (id={id(curr_val)})"
            )

    # 3. Checa mutação de identidade / vazamento (M10a, M10b, M10c)
    for k, (orig_id, orig_repr) in before_snapshot.items():
        curr_val = current_vars[k]
        curr_id = id(curr_val)
        assert curr_id == orig_id, (
            f"[{scope_level}] Global variable 'mcp_server.{k}' leaked or modified by identity during test: "
            f"expected {orig_repr} (id={orig_id}), got {curr_val!r} (id={curr_id})"
        )


@pytest.fixture(autouse=True, scope="function")
def check_mcp_globals_leak_function():
    """Garante que nenhum teste de função vaze ou altere por identidade globais em mcp_server."""
    before = _capture_mcp_snapshot()
    yield
    _verify_mcp_globals(before, "function")


@pytest.fixture(autouse=True, scope="class")
def check_mcp_globals_leak_class():
    """Garante que nenhuma classe de teste vaze ou altere por identidade globais em mcp_server."""
    before = _capture_mcp_snapshot()
    yield
    _verify_mcp_globals(before, "class")


@pytest.fixture(autouse=True, scope="module")
def check_mcp_globals_leak_module():
    """Garante que nenhum módulo de teste vaze ou altere por identidade globais em mcp_server."""
    before = _capture_mcp_snapshot()
    yield
    _verify_mcp_globals(before, "module")
