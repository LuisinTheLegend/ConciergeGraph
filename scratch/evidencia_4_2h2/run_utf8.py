"""scratch/evidencia_4_2h2/run_utf8.py

Executa comando em subprocesso com stdin=DEVNULL, PYTHONUTF8=1 e
GRAFO_LLM_API_KEY falsa explicita, redirecionando stdout/stderr diretamente
para o arquivo de destino em UTF-8 (sem PIPE / capture_output, evitando
bloqueio de communicate() no Windows).
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
    out_file = Path(sys.argv[1])
    cmd = list(sys.argv[2:])
    if cmd and cmd[0] == "python":
        cmd[0] = sys.executable
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["GRAFO_LLM_API_KEY"] = "AQ." + "FAKEFAKEFAKE0001"
    env["GRAFO_LLM_MODEL"] = "none"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
        )
    text = out_file.read_text(encoding="utf-8", errors="replace")
    tail = "\n".join(text.strip().splitlines()[-5:])
    print(f"[rc={res.returncode}] saved to {out_file}:\n{tail}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
