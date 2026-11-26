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


def _norm_pkg_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _parse_req_file(path: Path) -> tuple[list[str], dict[str, Requirement]]:
    directives: list[str] = []
    reqs: dict[str, Requirement] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r", "--requirement", "-")):
            directives.append(line)
            continue
        req = Requirement(line)
        reqs[_norm_pkg_name(req.name)] = req
    return directives, reqs


def test_pyproject_spdx_metadata_build_requires_and_clean_core_deps():
    """Garante SPDX MIT, version=3.8.2, setuptools>=77, extras e core deps limpas."""
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    build_reqs = {
        _norm_pkg_name(Requirement(dep).name): Requirement(dep)
        for dep in data.get("build-system", {}).get("requires", [])
    }
    assert "setuptools" in build_reqs
    assert Version("77.0.0") in build_reqs["setuptools"].specifier
    assert Version("76.99.0") not in build_reqs["setuptools"].specifier

    project = data["project"]
    assert project["version"] == "3.8.2"
    assert project["license"] == "MIT"
    assert project.get("license-files") == ["LICENSE"]
    assert "License :: OSI Approved :: MIT License" not in project.get("classifiers", [])

    forbidden_core = {
        "fastapi",
        "watchdog",
        "pathspec",
        "psutil",
        "pytest",
        "pytest-timeout",
        "flake8",
        "mypy",
        "rich",
        "packaging",
        "setuptools",
    }
    core_names = {_norm_pkg_name(Requirement(dep).name) for dep in project["dependencies"]}
    assert not (core_names & forbidden_core), f"Deps proibidas em core: {core_names & forbidden_core}"
    assert {"chromadb", "mcp", "sentence-transformers", "python-dotenv", "starlette"} <= core_names

    extras = project.get("optional-dependencies", {})
    for expected_extra in ("gemini", "openai", "qdrant", "dev", "all"):
        assert expected_extra in extras, f"Extra ausente em pyproject.toml: {expected_extra}"

    dev_reqs = {_norm_pkg_name(Requirement(dep).name): Requirement(dep) for dep in extras["dev"]}
    assert "packaging" in dev_reqs
    assert "setuptools" in dev_reqs
    assert Version("77.0.0") in dev_reqs["setuptools"].specifier
    assert "pytest-timeout" in dev_reqs


def test_requirements_txt_is_prod_only_and_requirements_dev_exists():
    """Garante separacao entre requirements.txt (prod-only) e requirements-dev.txt."""
    req_path = REPO_ROOT / "requirements.txt"
    first_line = req_path.read_text(encoding="utf-8").splitlines()[0]
    assert "v3.8.2" not in first_line, f"Comentario de versao obsoleto em requirements.txt: {first_line}"

    _, prod_reqs = _parse_req_file(req_path)
    forbidden_prod = {
        "fastapi",
        "watchdog",
        "pathspec",
        "psutil",
        "pytest",
        "pytest-timeout",
        "flake8",
        "mypy",
        "rich",
    }
    assert not (set(prod_reqs) & forbidden_prod), (
        f"Ferramentas dev/dormentes em requirements.txt: {set(prod_reqs) & forbidden_prod}"
    )
    assert {"chromadb", "mcp", "sentence-transformers", "python-dotenv", "starlette"} <= set(prod_reqs)

    dev_path = REPO_ROOT / "requirements-dev.txt"
    assert dev_path.is_file(), "requirements-dev.txt ausente na raiz do projeto"
    directives, dev_reqs = _parse_req_file(dev_path)
    assert any(d.strip() == "-r requirements.txt" for d in directives), (
        f"requirements-dev.txt deve incluir '-r requirements.txt'; directives={directives}"
    )
    for expected_dev in ("pytest", "pytest-timeout", "flake8", "mypy", "rich", "packaging", "setuptools"):
        assert expected_dev in dev_reqs, f"{expected_dev} ausente em requirements-dev.txt"
    assert Version("77.0.0") in dev_reqs["setuptools"].specifier
