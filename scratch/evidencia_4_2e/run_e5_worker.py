# run_e5_worker.py
# Experimento E5: Viabilidade de worker em processo filho
# Servidor FastMCP minimo com leitura de stdin ativa, chamando
# subprocess.run([sys.executable, "-c", "import scipy.special"], stdin=subprocess.DEVNULL, timeout=120)
# n=5, timeout 120s, registra OK/TRAVOU e tempo.

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e5_worker"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e5.txt"

SERVER_CODE = r"""
import sys, subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WorkerFeasibilityServer")

@mcp.tool()
def test_import_worker() -> str:
    res = subprocess.run(
        [sys.executable, "-c", "import scipy.special"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120
    )
    return f"worker_exit={res.returncode};stdout={res.stdout.strip()};stderr={res.stderr.strip()}"

if __name__ == "__main__":
    mcp.run()
"""

SERVER_PATH = OUTDIR / "server_worker.py"
SERVER_PATH.write_text(SERVER_CODE, encoding="utf-8")

REPS = 5
TIMEOUT = 120.0

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

async def run_one_rep(rep: int) -> dict:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(SERVER_PATH)],
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
    )

    t0 = time.perf_counter()
    classe = "ERRO"
    worker_out = ""
    timed_out = False

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                # Chama a ferramenta com timeout
                async with asyncio.timeout(TIMEOUT):
                    res = await session.call_tool("test_import_worker", {})
                    # res.content é lista de Content
                    text = "".join([c.text for c in res.content if hasattr(c, "text")])
                    worker_out = text
                    if "worker_exit=0" in text:
                        classe = "OK"
                    else:
                        classe = "ERRO"
    except TimeoutError:
        timed_out = True
        classe = "TRAVOU"
    except Exception as e:
        classe = "ERRO"
        worker_out = f"Exception: {type(e).__name__}: {e}"

    duration = time.perf_counter() - t0

    result = {
        "rep": rep,
        "classe": classe,
        "time_s": round(duration, 2),
        "worker_output": worker_out,
        "timed_out": timed_out,
    }
    (OUTDIR / f"result_rep{rep}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

async def main():
    log("INICIANDO EXPERIMENTO E5 — VIABILIDADE DE WORKER EM PROCESSO FILHO (n=5)")
    results = []
    for rep in range(1, REPS + 1):
        log(f"INICIO rep={rep} E5 (worker subprocess.DEVNULL)")
        res = await run_one_rep(rep)
        log(f"FIM    rep={rep} E5 -> {res['classe']} em {res['time_s']:.2f}s (out: {res['worker_output'][:60]})")
        results.append(res)

    lines = []
    lines.append("=== TABELA EXPERIMENTO E5: VIABILIDADE DE WORKER EM PROCESSO FILHO (n=5) ===")
    lines.append(f"{'Rep':<5} | {'Classe':<8} | {'Tempo(s)':<9} | {'Saida do Worker':<40}")
    lines.append("-" * 70)
    for r in results:
        lines.append(f"{r['rep']:<5} | {r['classe']:<8} | {r['time_s']:<9.2f} | {r['worker_output'][:40]}")
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    asyncio.run(main())
