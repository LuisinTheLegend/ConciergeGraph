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


def _capture_package_integrity_snapshot() -> dict:
    """Captura o estado de integridade de sys.modules e atributos de pacotes raiz conhecidos (ex: interface)."""
    snapshot = {}
    pkg = sys.modules.get("interface")
    snapshot["interface_in_sys_modules"] = (pkg is not None)
    if pkg is not None:
        snapshot["interface_id"] = id(pkg)
        sub_attrs = {}
        for attr_name, attr_val in vars(pkg).items():
            if isinstance(attr_val, types.ModuleType):
                sub_attrs[attr_name] = id(attr_val)
        snapshot["sub_attrs"] = sub_attrs
    return snapshot


def _verify_package_integrity(before_snapshot: dict, scope_level: str):
    """Verifica se sys.modules e os atributos de pacote pai/filho permanecem íntegros."""
    # 1. Integridade de submódulos interface.* em sys.modules
    for mod_name, mod_obj in list(sys.modules.items()):
        if mod_name.startswith("interface.") and mod_obj is not None:
            sub_name = mod_name.split(".", 1)[1]
            pkg = sys.modules.get("interface")
            assert pkg is not None, (
                f"[{scope_level}] Package leak: sys.modules contains {mod_name!r} "
                f"but parent package 'interface' is missing from sys.modules."
            )
            pkg_dict = vars(pkg)
            assert sub_name in pkg_dict, (
                f"[{scope_level}] Package attribute leak: parent package 'interface' has no attribute {sub_name!r} in __dict__ "
                f"while {mod_name!r} exists in sys.modules."
            )
            pkg_attr = pkg_dict[sub_name]
            assert pkg_attr is mod_obj, (
                f"[{scope_level}] Package attribute mismatch: interface.{sub_name} (id={id(pkg_attr)}) "
                f"does not match sys.modules[{mod_name!r}] (id={id(mod_obj)})."
            )

    # 2. Integridade contra deleção de submódulos que existiam antes
    if before_snapshot.get("interface_in_sys_modules"):
        pkg = sys.modules.get("interface")
        assert pkg is not None, (
            f"[{scope_level}] Package leak: 'interface' was removed from sys.modules during test."
        )
        before_sub_attrs = before_snapshot.get("sub_attrs", {})
        pkg_dict = vars(pkg)
        for attr_name, prev_mod_id in before_sub_attrs.items():
            if f"interface.{attr_name}" in sys.modules:
                assert attr_name in pkg_dict, (
                    f"[{scope_level}] Package attribute leak: attribute interface.{attr_name} was deleted "
                    f"during test execution."
                )


@pytest.fixture(autouse=True, scope="function")
def check_mcp_globals_leak_function():
    """Garante que nenhum teste de função vaze ou altere por identidade globais em mcp_server ou desvincule pacotes."""
    before_mcp = _capture_mcp_snapshot()
    before_pkg = _capture_package_integrity_snapshot()
    yield
    _verify_package_integrity(before_pkg, "function")
    _verify_mcp_globals(before_mcp, "function")


@pytest.fixture(autouse=True, scope="class")
def check_mcp_globals_leak_class():
    """Garante que nenhuma classe de teste vaze ou altere por identidade globais em mcp_server ou desvincule pacotes."""
    before_mcp = _capture_mcp_snapshot()
    before_pkg = _capture_package_integrity_snapshot()
    yield
    _verify_package_integrity(before_pkg, "class")
    _verify_mcp_globals(before_mcp, "class")


@pytest.fixture(autouse=True, scope="module")
def check_mcp_globals_leak_module():
    """Garante que nenhum módulo de teste vaze ou altere por identidade globais em mcp_server ou desvincule pacotes."""
    before_mcp = _capture_mcp_snapshot()
    before_pkg = _capture_package_integrity_snapshot()
    yield
    _verify_package_integrity(before_pkg, "module")
    _verify_mcp_globals(before_mcp, "module")
