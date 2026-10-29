# run_e3_mcp.py
# Experimento E3 da Rodada 4.2e-2:
# MCP minimo nas versoes reais venv_mcp127 (1.27.0) e venv_mcp130 (1.3.0)
# Variantes:
#   (a) a_sync_scipy: def sincrona importando scipy.special
#   (e) e_preimport_scipy: pre-import SO de scipy.special antes de run()
#   (f) f_preimport_scipy_sklearn: pre-import de scipy.special + sklearn.utils._array_api
#   (g) g_preimport_st: pre-import de sentence_transformers
# n=5 por variante e versao, timeout 180s.
# Captura faulthandler.dump_traceback_later e CPU do processo servidor a cada 5s durante 60s.

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVERS_DIR = HERE / "minimal_servers"
OUTDIR = HERE / "e3_mcp"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e3.txt"

VENVS = {
    "mcp127": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe",
    "mcp130": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp130\Scripts\python.exe",
}

VARIANTS = {
    "a_sync_scipy": SERVERS_DIR / "server_a_sync_scipy.py",
    "e_preimport_scipy": SERVERS_DIR / "server_e_preimport_scipy.py",
    "f_preimport_scipy_sklearn": SERVERS_DIR / "server_f_preimport_scipy_sklearn.py",
    "g_preimport_st": SERVERS_DIR / "server_g_preimport_st.py",
}

CLIENT_RUNNER_CODE = r"""
import asyncio, json, os, sys, time, threading
import psutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_script = os.environ["MIN_SERVER_SCRIPT"]
    out_json = os.environ["MIN_OUT_JSON"]
    trace_dump = os.environ.get("TRACE_DUMP_FILE", "")
    timeout = float(os.environ.get("MIN_TIMEOUT", "180"))

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    if trace_dump:
        env["TRACE_DUMP_FILE"] = trace_dump

    params = StdioServerParameters(command=sys.executable, args=["-u", server_script], env=env)
    t0 = time.perf_counter()
    res = {
        "classe": "ERRO",
        "cpu_samples": [],
        "mean_cpu": 0.0,
        "t_init": None,
        "t_call": None,
        "total_s": None,
        "error": None
    }

    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await asyncio.wait_for(session.initialize(), timeout=30)
                res["t_init"] = round(time.perf_counter() - t0, 3)

                # Busca o processo do servidor via PID do subprocesso gerenciado pelo client se possivel
                # Ou monitora CPU periodicamente em background task
                cpu_samples = []
                stop_cpu = threading.Event()

                def monitor_cpu():
                    # Tenta encontrar processo filho com server_script
                    current_p = psutil.Process()
                    server_proc = None
                    for _ in range(20):
                        children = current_p.children(recursive=True)
                        for c in children:
                            try:
                                cmdline = " ".join(c.cmdline())
                                if os.path.basename(server_script) in cmdline:
                                    server_proc = c
                                    break
                            except Exception:
                                pass
                        if server_proc:
                            break
                        time.sleep(0.5)

                    if not server_proc:
                        return

                    while not stop_cpu.is_set():
                        try:
                            cpu = server_proc.cpu_percent(interval=1.0)
                            cpu_samples.append(cpu)
                        except Exception:
                            break
                        time.sleep(4.0)

                t_cpu = threading.Thread(target=monitor_cpu, daemon=True)
                t_cpu.start()

                t_call = time.perf_counter()
                try:
                    call_res = await asyncio.wait_for(session.call_tool("run_action", {}), timeout=timeout)
                    res["t_call"] = round(time.perf_counter() - t_call, 3)
                    res["classe"] = "OK"
                except asyncio.TimeoutError:
                    res["classe"] = "TRAVOU"
                    res["t_call"] = round(time.perf_counter() - t_call, 3)
                finally:
                    stop_cpu.set()
                    res["cpu_samples"] = cpu_samples
                    if cpu_samples:
                        res["mean_cpu"] = round(sum(cpu_samples) / len(cpu_samples), 2)

    except asyncio.TimeoutError:
        res["classe"] = "TRAVOU"
    except Exception as e:
        res["classe"] = "ERRO"
        res["error"] = f"{type(e).__name__}: {e}"

    res["total_s"] = round(time.perf_counter() - t0, 3)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    sys.exit(0 if res["classe"] == "OK" else (3 if res["classe"] == "TRAVOU" else 1))

if __name__ == "__main__":
    asyncio.run(main())
"""

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    log("INICIANDO EXPERIMENTO E3 — MCP MINIMO COM VERSOES CORRETAS")
    all_results = []

    for rep in range(1, 6):
        for venv_name, py_exe in VENVS.items():
            for var_name, server_path in VARIANTS.items():
                out_json = OUTDIR / f"{venv_name}__{var_name}__rep{rep}.json"
                trace_file = OUTDIR / f"trace__{venv_name}__{var_name}__rep{rep}.txt"
                log(f"INICIO rep={rep} venv={venv_name} var={var_name}")

                env = os.environ.copy()
                env["MIN_SERVER_SCRIPT"] = str(server_path)
                env["MIN_OUT_JSON"] = str(out_json)
                env["MIN_TIMEOUT"] = "180"
                env["TRACE_DUMP_FILE"] = str(trace_file)
                env["PYTHONUTF8"] = "1"

                t0 = time.perf_counter()
                try:
                    # Roda o client runner
                    r = subprocess.run(
                        [py_exe, "-u", "-c", CLIENT_RUNNER_CODE],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=240,
                    )
                    dt = time.perf_counter() - t0
                    if out_json.exists():
                        res_data = json.loads(out_json.read_text(encoding="utf-8"))
                        status = res_data.get("classe", "ERRO")
                        mean_cpu = res_data.get("mean_cpu", 0.0)
                    else:
                        status = "OK" if r.returncode == 0 else ("TRAVOU" if r.returncode == 3 else f"ERRO_RC_{r.returncode}")
                        mean_cpu = 0.0
                        res_data = {"classe": status, "total_s": round(dt, 2), "mean_cpu": mean_cpu}

                    log(f"FIM    rep={rep} venv={venv_name} var={var_name} status={status} em {dt:.1f}s (CPU: ~{mean_cpu}%)")
                    res_data["rep"] = rep
                    res_data["venv"] = venv_name
                    res_data["variant"] = var_name
                    all_results.append(res_data)

                except subprocess.TimeoutExpired:
                    dt = time.perf_counter() - t0
                    log(f"FIM    rep={rep} venv={venv_name} var={var_name} status=DRIVER_TIMEOUT em {dt:.1f}s")
                    all_results.append({
                        "rep": rep, "venv": venv_name, "variant": var_name,
                        "classe": "TRAVOU", "total_s": round(dt, 2), "mean_cpu": 0.0
                    })

    # Gera a tabela_e3.txt
    lines = []
    lines.append("=== TABELA EXPERIMENTO E3: MCP MINIMO COM VERSOES CORRETAS (n=5 cada) ===")
    lines.append(f"{'Venv':<10} | {'Variante':<26} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'CPU Media(%)':<14} | {'Trace Dump'}")
    lines.append("-" * 90)
    for r in all_results:
        trace_path = OUTDIR / f"trace__{r['venv']}__{r['variant']}__rep{r['rep']}.txt"
        has_trace = "SIM" if trace_path.exists() and trace_path.stat().st_size > 0 else "NAO"
        lines.append(
            f"{r['venv']:<10} | {r['variant']:<26} | {r['rep']:<4} | {r.get('classe','ERRO'):<8} | "
            f"{r.get('total_s', 0):<9.2f} | {r.get('mean_cpu', 0.0):<14.2f} | {has_trace}"
        )
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    main()
