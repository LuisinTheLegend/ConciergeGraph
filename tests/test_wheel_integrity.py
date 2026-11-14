"""
tests/test_wheel_integrity.py — Guarda de integridade do empacotamento (wheel).

Garante offline que a construção de wheel em diretório temporário inclui todos os
módulos vivos esperados do Grafo Concierge, preserva os entrypoints console_scripts
e não vaza diretórios de testes ou quarentena.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from setuptools import build_meta


REPO_ROOT = Path(__file__).resolve().parent.parent

# Arquivos e diretórios copiados para uma cópia limpa em tmp_path, evitando
# contaminação por build/ ou *.egg-info pré-existentes na raiz do repositório.
_SOURCE_FILES = ("pyproject.toml", "main.py", "README.md", "LICENSE")
_SOURCE_DIRS = (
    "core",
    "storage",
    "ingestion",
    "services",
    "interface",
    "agent",
    "agents",
    "scripts",
    "tests",
    "archive",
)
_IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    "build",
    "dist",
    ".pytest_cache",
)

EXPECTED_LIVE_MODULES = [
    "main.py",
    "core/__init__.py",
    "core/checkpointer.py",
    "core/config.py",
    "core/database.py",
    "core/graph_rag.py",
    "core/hybrid_search.py",
    "core/mcp_governor.py",
    "core/memory_extractor.py",
    "core/middleware.py",
    "core/project_index.py",
    "core/vector_backend.py",
    "ingestion/__init__.py",
    "ingestion/crawler.py",
    "ingestion/orchestrator.py",
    "ingestion/parser.py",
    "ingestion/summarizer.py",
    "interface/__init__.py",
    "interface/cli.py",
    "interface/mcp_server.py",
    "interface/queue_writer.py",
    "services/__init__.py",
    "services/janitor.py",
    "storage/__init__.py",
    "storage/base_backend.py",
    "storage/connection.py",
    "storage/logic.py",
    "storage/schema.py",
    "storage/semantic_logic.py",
    "storage/store.py",
    "storage/vector_store.py",
]


def _copy_clean_source(dest: Path) -> None:
    """Copia apenas os fontes limpos para dest, ignorando build/ e *.egg-info."""
    dest.mkdir(parents=True, exist_ok=True)
    for filename in _SOURCE_FILES:
        src_file = REPO_ROOT / filename
        if src_file.is_file():
            shutil.copy2(src_file, dest / filename)
    for dirname in _SOURCE_DIRS:
        src_dir = REPO_ROOT / dirname
        if src_dir.is_dir():
            shutil.copytree(src_dir, dest / dirname, ignore=_IGNORE_PATTERNS)


def test_wheel_contains_all_live_modules_and_entrypoints(tmp_path, monkeypatch):
    """Constrói o wheel offline em cópia limpa e valida módulos vivos e entrypoints."""
    src_dir = tmp_path / "src"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    _copy_clean_source(src_dir)

    monkeypatch.chdir(src_dir)
    wheel_name = build_meta.build_wheel(str(dist_dir))
    wheel_path = dist_dir / wheel_name
    assert wheel_path.is_file(), f"Wheel não foi gerado em {wheel_path}"

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())
        for mod_path in EXPECTED_LIVE_MODULES:
            assert mod_path in names, f"Módulo vivo ausente no wheel: {mod_path}"

        ep_entries = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
        assert len(ep_entries) == 1, f"entry_points.txt inesperado no wheel: {ep_entries}"
        ep_text = zf.read(ep_entries[0]).decode("utf-8")
        assert "concierge = interface.cli:main" in ep_text
        assert "concierge-mcp = main:main" in ep_text

        leaked = [n for n in names if n.startswith("tests/") or n.startswith("archive/")]
        assert not leaked, f"Arquivos indevidos empacotados no wheel: {leaked}"
