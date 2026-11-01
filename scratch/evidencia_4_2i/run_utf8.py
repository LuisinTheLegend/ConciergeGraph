"""scratch/evidencia_4_2i/run_utf8.py

Helper para executar comandos e gravar stdout+stderr em UTF-8 puro (sem BOM e sem UTF-16LE),
com variáveis de ambiente de segredos falsos explícitas para nunca carregar chaves reais do .env.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python run_utf8.py <out_file> <cmd...>", file=sys.stderr)
        return 2

    out_path = Path(sys.argv[1])
    cmd = sys.argv[2:]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    for k in ["GRAFO_LLM_PROVIDER", "GRAFO_LLM_BASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        env.pop(k, None)
    env.setdefault("GRAFO_LLM_API_KEY", "AQ." + "FAKEFAKEFAKE0001")
    env.setdefault("GRAFO_LLM_MODEL", "none")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    combined = proc.stdout + (
        ("\n" if proc.stdout and not proc.stdout.endswith("\n") else "") + proc.stderr
        if proc.stderr
        else ""
    )
    out_path.write_text(combined, encoding="utf-8")
    tail = "\n".join(combined.splitlines()[-10:])
    sys.stdout.buffer.write(f"[rc={proc.returncode}] saved to {out_path}:\n{tail}\n".encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

