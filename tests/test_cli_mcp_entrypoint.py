"""tests/test_cli_mcp_entrypoint.py

Testes do entrypoint CLI do servidor MCP (main.py / concierge-mcp, Rodada 4.8-C1).
Cobre _get_package_version(), parse_args(), main(argv), --help, --version e --transport.
"""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _clean_cli_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = str(tmp_path / "cli_test.db")
    env["GRAFO_CHROMA_PATH"] = str(tmp_path / "cli_chroma")
    env["GRAFO_LIGHTWEIGHT_MODE"] = "true"
    env.pop("GRAFO_TRANSPORT", None)
    return env


def test_cli_help_exits_zero_without_blocking_stdin(tmp_path):
    """python main.py --help retorna exit 0 imediatamente sem bloquear stdin ou bootstrap."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "main.py"), "--help"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_clean_cli_env(tmp_path),
        timeout=15,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "--transport" in result.stdout
    assert "--version" in result.stdout
    assert "stdio" in result.stdout
    assert "sse" in result.stdout
    assert "SqliteStore" not in result.stderr


def test_cli_version_exits_zero_with_real_package_version(tmp_path):
    """python main.py --version retorna exit 0 com versao do pacote (sem v3.8.0 hardcoded)."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "main.py"), "--version"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_clean_cli_env(tmp_path),
        timeout=15,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    combined = (result.stdout + result.stderr).strip()
    assert "3.8.2" in combined
    assert "3.8.0" not in combined


def test_parse_args_supports_transport_defaults_and_rejects_invalid():
    """parse_args aceita --transport stdio/sse, default None e rejeita flag invalida."""
    import main

    ns_empty = main.parse_args([])
    assert ns_empty.transport is None

    ns_sse = main.parse_args(["--transport", "sse"])
    assert ns_sse.transport == "sse"

    ns_stdio = main.parse_args(["--transport", "stdio"])
    assert ns_stdio.transport == "stdio"

    with pytest.raises(SystemExit) as exc_info:
        main.parse_args(["--flag-inexistente"])
    assert exc_info.value.code == 2


def test_get_package_version_fallbacks(monkeypatch, tmp_path):
    """_get_package_version faz fallback de importlib.metadata -> pyproject.toml -> 'unknown'."""
    import main

    # 1. Pacote ausente nos metadados -> le pyproject.toml
    def _raise_not_found(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(_name)

    monkeypatch.setattr(importlib.metadata, "version", _raise_not_found)
    assert main._get_package_version() == "3.8.2"

    # 2. pyproject.toml ausente -> fallback 'unknown'
    monkeypatch.setattr(main, "PROJECT_ROOT", tmp_path)
    assert main._get_package_version() == "unknown"


def test_main_transport_cli_overrides_global_and_preserves_zero_arg_wiring(monkeypatch):
    """main(['--transport', ...]) sobrescreve main.TRANSPORT; main([]) preserva monkeypatch."""
    import main

    decouple_calls: list[bool] = []
    run_transports: list[str] = []

    def _mock_decouple() -> bool:
        decouple_calls.append(True)
        return True

    def _mock_bootstrap():
        srv = SimpleNamespace(run=lambda transport: run_transports.append(transport))
        return srv, None, None

    monkeypatch.setattr(main, "decouple_stdin_from_fd0", _mock_decouple)
    monkeypatch.setattr(main, "bootstrap", _mock_bootstrap)

    # Override sse quando TRANSPORT esta stdio
    monkeypatch.setattr(main, "TRANSPORT", "stdio")
    decouple_calls.clear()
    run_transports.clear()
    main.main(["--transport", "sse"])
    assert decouple_calls == []
    assert run_transports == ["sse"]

    # Override stdio quando TRANSPORT esta sse
    monkeypatch.setattr(main, "TRANSPORT", "sse")
    decouple_calls.clear()
    run_transports.clear()
    main.main(["--transport", "stdio"])
    assert decouple_calls == [True]
    assert run_transports == ["stdio"]

    # main([]) e main() sem argumentos preservam TRANSPORT configurado/monkeypatched
    monkeypatch.setattr(main, "TRANSPORT", "sse")
    decouple_calls.clear()
    run_transports.clear()
    main.main([])
    assert decouple_calls == []
    assert run_transports == ["sse"]
