"""
tests/test_dependency_pins.py — Teste-guarda de limites de versao de dependencias.

Garante que pyproject.toml e requirements.txt contenham pins seguros para
dependencias criticas que sofrem quebra de API em versoes maiores (ex.: mcp 2.x).
"""

from __future__ import annotations

import sys
from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0():
    """Garante que pyproject.toml rejeite mcp 2.0.0 e aceite mcp 1.27.0."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    assert pyproject_path.is_file(), f"Arquivo nao encontrado: {pyproject_path}"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    dependencies = data.get("project", {}).get("dependencies", [])
    mcp_req = None
    for dep_str in dependencies:
        req = Requirement(dep_str)
        if req.name == "mcp":
            mcp_req = req
            break

    assert mcp_req is not None, "Dependencia 'mcp' nao encontrada em pyproject.toml"
    assert Version("2.0.0") not in mcp_req.specifier, (
        f"pyproject.toml permite indevidamente mcp 2.0.0: specifier={mcp_req.specifier}"
    )
    assert Version("1.27.0") in mcp_req.specifier, (
        f"pyproject.toml nao permite mcp 1.27.0: specifier={mcp_req.specifier}"
    )


def test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0():
    """Garante que requirements.txt rejeite mcp 2.0.0 e aceite mcp 1.27.0."""
    requirements_path = REPO_ROOT / "requirements.txt"
    assert requirements_path.is_file(), f"Arquivo nao encontrado: {requirements_path}"

    mcp_req = None
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            req = Requirement(line)
            if req.name == "mcp":
                mcp_req = req
                break

    assert mcp_req is not None, "Dependencia 'mcp' nao encontrada em requirements.txt"
    assert Version("2.0.0") not in mcp_req.specifier, (
        f"requirements.txt permite indevidamente mcp 2.0.0: specifier={mcp_req.specifier}"
    )
    assert Version("1.27.0") in mcp_req.specifier, (
        f"requirements.txt nao permite mcp 1.27.0: specifier={mcp_req.specifier}"
    )
