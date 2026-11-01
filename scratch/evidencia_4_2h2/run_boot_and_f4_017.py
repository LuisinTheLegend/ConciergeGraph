"""scratch/evidencia_4_2h2/run_boot_and_f4_017.py

Executa:
1. scratch/boot_check.py com mcp 1.27.0 (venv_mcp127) e mcp 1.30.0 (venv_mcp130_full), n=1 cada,
   com GRAFO_LLM_MODEL=none e GRAFO_LLM_API_KEY falsa explícita.
2. Harness F4-017 (search-first e mine, n=3 por cenário, sequenciais, GRAFO_LLM_MODEL=none,
   GRAFO_LLM_API_KEY falsa explícita) em venv_mcp127 e venv_mcp130_full, salvando a contagem
   literal de linhas ERROR e WARNING por tipo em cada execução.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

PY_127 = Path(r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe")
PY_130_FULL = Path(r"C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe")

sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2h"))
import run_f4_017_regression as reg_mod  # noqa: E402


def run_boot_check_for_venv(py_exe: Path, out_file: Path) -> int:
    env = os.environ.copy()
    for k in ["GRAFO_LLM_PROVIDER", "GRAFO_LLM_BASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        env.pop(k, None)
    env.update({
        "GRAFO_LLM_API_KEY": "AQ." + "FAKEFAKEFAKE0001",
        "GRAFO_LLM_MODEL": "none",
        "GRAFO_EMBED_WARMUP": "false",
        "HF_HUB_OFFLINE": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    })
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scratch" / "boot_check.py"), "--python", str(py_exe)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = proc.stdout + (
        ("\n" if proc.stdout and not proc.stdout.endswith("\n") else "") + proc.stderr
        if proc.stderr
        else ""
    )
    out_file.write_text(combined, encoding="utf-8")
    sys.stdout.buffer.write(f"[boot_check {out_file.name}] rc={proc.returncode}\n".encode("utf-8"))
    return proc.returncode


async def main_async() -> int:
    rc_127 = run_boot_check_for_venv(PY_127, HERE / "boot_check_127.txt")
    rc_130 = run_boot_check_for_venv(PY_130_FULL, HERE / "boot_check_130.txt")
    assert rc_127 == 0, f"boot_check 1.27.0 falhou com rc={rc_127}"
    assert rc_130 == 0, f"boot_check 1.30.0 falhou com rc={rc_130}"

    # Redireciona a saída de run_f4_017_regression para a pasta da 4.2h-2
    reg_mod.HERE = HERE
    rc_reg = await reg_mod.main_async()
    return rc_reg


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))

