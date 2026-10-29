"""
run_minimal_matrix.py - Executa o Passo 3: reproducao minima fora do Concierge.

Venvs:
  - mcp127: C:\\Nexus-Memory\\_venvs_4_2e\\venv_mcp127\\Scripts\\python.exe
  - mcp130: C:\\Nexus-Memory\\_venvs_4_2e\\venv_mcp130\\Scripts\\python.exe

Variantes:
  - a_sync_scipy: server_a_sync_scipy.py
  - b_sync_st:    server_b_sync_st.py
  - c_async_tot:  server_c_async_tothread.py
  - d_preimport:  server_d_preimport.py

5 repeticoes por variante e versao do mcp, timeout 180s.
Cliente stdio real usando a biblioteca mcp instalada no proprio venv sob teste.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVERS_DIR = HERE / "minimal_servers"
OUTDIR = HERE / "minimal_repro"

VENVS = {
    "mcp127": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe",
    "mcp130": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp130\Scripts\python.exe",
}

VARIANTS = {
    "a_sync_scipy": SERVERS_DIR / "server_a_sync_scipy.py",
    "b_sync_st":    SERVERS_DIR / "server_b_sync_st.py",
    "c_async_tot":  SERVERS_DIR / "server_c_async_tothread.py",
    "d_preimport":  SERVERS_DIR / "server_d_preimport.py",
}

CLIENT_RUNNER_CODE = r"""
import asyncio, json, os, sys, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_script = os.environ["MIN_SERVER_SCRIPT"]
    python_exe = sys.executable
    params = StdioServerParameters(command=python_exe, args=["-u", server_script], env=os.environ.copy())
    t0 = time.perf_counter()
    res = {"classe": "ERRO"}
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await asyncio.wait_for(session.initialize(), timeout=30)
                t_init = time.perf_counter() - t0
                res["t_init"] = round(t_init, 3)
                t_call = time.perf_counter()
                call_res = await asyncio.wait_for(session.call_tool("run_action", {}), timeout=float(os.environ.get("MIN_TIMEOUT", "180")))
                res["t_call"] = round(time.perf_counter() - t_call, 3)
                res["classe"] = "OK"
    except asyncio.TimeoutError:
        res["classe"] = "TRAVOU"
    except Exception as e:
        res["classe"] = "ERRO"
        res["error"] = f"{type(e).__name__}: {e}"
    res["total_s"] = round(time.perf_counter() - t0, 3)
    json.dump(res, open(os.environ["MIN_OUT_JSON"], "w"))
    sys.exit(0 if res["classe"] == "OK" else 3)

if __name__ == "__main__":
    asyncio.run(main())
"""

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    log_file = open(OUTDIR / "progress.log", "a", encoding="utf-8")

    def say(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    say("INICIANDO PASSO 3 — REPRODUÇÃO MÍNIMA")
    
    # Executa cada caso 5 vezes
    for rep in range(1, 6):
        for venv_name, py_exe in VENVS.items():
            for var_name, server_path in VARIANTS.items():
                out_json = OUTDIR / f"{venv_name}__{var_name}__rep{rep}.json"
                say(f"INICIO rep={rep} venv={venv_name} var={var_name}")
                env = os.environ.copy()
                env["MIN_SERVER_SCRIPT"] = str(server_path)
                env["MIN_OUT_JSON"] = str(out_json)
                env["MIN_TIMEOUT"] = "180"
                env["PYTHONUTF8"] = "1"
                t0 = time.perf_counter()
                try:
                    r = subprocess.run([py_exe, "-c", CLIENT_RUNNER_CODE], env=env, capture_output=True, text=True, timeout=240)
                    dt = time.perf_counter() - t0
                    status = "OK" if r.returncode == 0 else ("TRAVOU" if r.returncode == 3 else f"ERRO_RC_{r.returncode}")
                    say(f"FIM    rep={rep} venv={venv_name} var={var_name} status={status} em {dt:.1f}s")
                except subprocess.TimeoutExpired:
                    say(f"FIM    rep={rep} venv={venv_name} var={var_name} status=DRIVER_TIMEOUT em {time.perf_counter()-t0:.1f}s")

    say("PASSO 3 CONCLUIDO")

if __name__ == "__main__":
    main()

