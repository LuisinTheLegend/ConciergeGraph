# scratch/evidencia_4_2f/run_passo4e_definitive.py
"""
Passo 4e: O teste definitivo do F4-017.
Roda mcp_e2e_v2 SEM WRAPPER e SEM AQUECIMENTO.
5 repeticoes de search-first e 5 de mine em:
  - mcp 1.27.0 (venv_mcp127)
  - mcp 1.30.0 (venv_mcp130_real)
Total: 20 execucoes sequenciais, medindo CPU a cada 5s.
Gera scratch/evidencia_4_2f/tabela_passo4e.txt.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2e"))
import mcp_e2e_v2 as v2  # noqa: E402

OUTDIR = REPO_ROOT / "scratch" / "evidencia_4_2f" / "e2e_definitive"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = REPO_ROOT / "scratch" / "evidencia_4_2f" / "tabela_passo4e.txt"

VENVS = {
    "mcp_1_27_0": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe",
    "mcp_1_30_0": r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp130_real\Scripts\python.exe",
}

SEED_SCRIPT = r"""
import json, os, sys
sys.path.insert(0, r"{repo_root}")
import main
server, janitor, store = main.bootstrap()
gc = server._gc
proj = os.environ["REG_PROJ"]
u = gc.register_project(os.path.basename(proj), "geral", "PUBLIC", "seed")
res = gc.mine(u, proj, auto_tag=True)
json.dump({"uuid": u, "res": str(res)[:400]}, open(os.environ["REG_SEED_OUT"], "w"))
store.close()
"""


def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "execution.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


async def run_single_e2e(
    py_exe: str,
    venv_name: str,
    scenario: str,
    rep: int,
    timeout: float = 180.0,
) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    case_dir = OUTDIR / f"{venv_name}__{scenario}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    errlog_path = case_dir / "server_stderr.log"
    res_path = case_dir / "result.json"

    tmp = Path(tempfile.mkdtemp(prefix=f"e2e_{venv_name}_{scenario}_"))
    db = str(tmp / "test.db")
    chroma = str(tmp / "chroma")
    proj = str(tmp / "sample_proj")
    v2.create_sample_project(proj)

    env = os.environ.copy()
    env.update({
        "GRAFO_DB_PATH": db,
        "GRAFO_CHROMA_PATH": chroma,
        "GRAFO_CHROMA_COLLECTION": f"col_{venv_name}_{scenario}_{rep}",
        "GRAFO_TRANSPORT": "stdio",
        "GRAFO_LOG_LEVEL": "INFO",
        "GRAFO_EMBED_WARMUP": "false",  # SEM AQUECIMENTO
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TQDM_DISABLE": "1",
        "HF_HUB_OFFLINE": "1",
        "PYTHONPATH": str(REPO_ROOT),
        "REG_REPO": str(REPO_ROOT),
        "REG_PROJ": proj,
    })

    uuid = None
    if scenario == "search-first":
        seed_out = str(tmp / "seed.json")
        env_seed = dict(env, REG_SEED_OUT=seed_out)
        code_seed = SEED_SCRIPT.replace("{repo_root}", str(REPO_ROOT))
        r_seed = subprocess.run(
            [py_exe, "-u", "-c", code_seed],
            capture_output=True,
            text=True,
            env=env_seed,
            cwd=str(REPO_ROOT),
        )
        (case_dir / "seed.log").write_text(r_seed.stdout + "\n" + r_seed.stderr, encoding="utf-8")
        if r_seed.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            res = {
                "venv": venv_name,
                "scenario": scenario,
                "rep": rep,
                "classe": "ERRO_SEED",
                "dur_critica": 0.0,
                "mean_cpu": 0.0,
                "max_cpu": 0.0,
                "details": "Falha no seed in-process",
            }
            res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
            return res
        try:
            uuid = json.load(open(seed_out))["uuid"]
        except Exception as e:
            shutil.rmtree(tmp, ignore_errors=True)
            res = {
                "venv": venv_name,
                "scenario": scenario,
                "rep": rep,
                "classe": "ERRO_SEED_JSON",
                "dur_critica": 0.0,
                "mean_cpu": 0.0,
                "max_cpu": 0.0,
                "details": str(e),
            }
            res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
            return res

    server_params = StdioServerParameters(
        command=py_exe,
        args=["-u", "main.py"],  # SEM WRAPPER!
        env=env,
        cwd=REPO_ROOT,
    )

    t_spawn = time.perf_counter()
    cpu_samples: list[float] = []
    stop_cpu = False

    def cpu_monitor(proc_obj):
        while not stop_cpu:
            try:
                c = proc_obj.cpu_percent(interval=None)
                cpu_samples.append(c)
            except Exception:
                pass
            time.sleep(5.0)

    try:
        with open(errlog_path, "w", encoding="utf-8") as errlog:
            async with stdio_client(server_params, errlog=errlog) as (read_stream, write_stream), \
                       ClientSession(read_stream, write_stream) as session:

                # Encontra processo do servidor para medicao de CPU
                server_proc = None
                if psutil is not None:
                    curr_p = psutil.Process()
                    children = [c for c in curr_p.children(recursive=True) if "python" in c.name().lower()]
                    if children:
                        server_proc = children[0]
                        # Dispara thread de CPU
                        import threading
                        t_mon = threading.Thread(target=cpu_monitor, args=(server_proc,), daemon=True)
                        t_mon.start()

                # 1. Initialize
                t0_init = time.perf_counter()
                await asyncio.wait_for(session.initialize(), timeout=30.0)
                t_init = time.perf_counter() - t0_init

                # 2. List tools
                await asyncio.wait_for(session.list_tools(), timeout=15.0)

                if scenario == "mine":
                    # Register
                    reg_res = await asyncio.wait_for(
                        session.call_tool("concierge_register", arguments={
                            "project_path": proj,
                            "wing": "geral",
                            "privacy_level": "PUBLIC",
                            "summary": f"E2E 4.2f {venv_name} mine {rep}",
                        }),
                        timeout=30.0,
                    )
                    reg_data = v2.parse_mcp_result(reg_res, "concierge_register")
                    u_mine = reg_data["project_uuid"]

                    # Critical call: concierge_mine (1o embedding)
                    t0_crit = time.perf_counter()
                    mine_res = await asyncio.wait_for(
                        session.call_tool("concierge_mine", arguments={
                            "path": proj,
                            "project_identifier": u_mine,
                            "auto_tag": True,
                        }),
                        timeout=timeout,
                    )
                    dur_crit = time.perf_counter() - t0_crit
                    v2.parse_mcp_result(mine_res, "concierge_mine")

                    # Secondary call: search
                    t0_sec = time.perf_counter()
                    s_res = await asyncio.wait_for(
                        session.call_tool("concierge_search", arguments={
                            "query": "rectangle area width height",
                            "project_identifier": u_mine,
                            "top_k": 3,
                        }),
                        timeout=30.0,
                    )
                    dur_sec = time.perf_counter() - t0_sec
                    v2.parse_mcp_result(s_res, "concierge_search")

                else:  # search-first
                    # Critical call: concierge_search (1o embedding na 1a chamada)
                    t0_crit = time.perf_counter()
                    s_res = await asyncio.wait_for(
                        session.call_tool("concierge_search", arguments={
                            "query": "rectangle area width height",
                            "project_identifier": uuid,
                            "top_k": 3,
                        }),
                        timeout=timeout,
                    )
                    dur_crit = time.perf_counter() - t0_crit
                    v2.parse_mcp_result(s_res, "concierge_search")

                    # Secondary call: mine
                    t0_sec = time.perf_counter()
                    mine_res = await asyncio.wait_for(
                        session.call_tool("concierge_mine", arguments={
                            "path": proj,
                            "project_identifier": uuid,
                            "auto_tag": True,
                        }),
                        timeout=timeout,
                    )
                    dur_sec = time.perf_counter() - t0_sec
                    v2.parse_mcp_result(mine_res, "concierge_mine")

                stop_cpu = True
                mean_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
                max_cpu = max(cpu_samples) if cpu_samples else 0.0

                res = {
                    "venv": venv_name,
                    "scenario": scenario,
                    "rep": rep,
                    "classe": "OK",
                    "t_init": t_init,
                    "dur_critica": dur_crit,
                    "dur_secundaria": dur_sec,
                    "cpu_samples": cpu_samples,
                    "mean_cpu": mean_cpu,
                    "max_cpu": max_cpu,
                }
                res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
                return res

    except asyncio.TimeoutError:
        stop_cpu = True
        mean_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        max_cpu = max(cpu_samples) if cpu_samples else 0.0
        res = {
            "venv": venv_name,
            "scenario": scenario,
            "rep": rep,
            "classe": "TRAVOU",
            "dur_critica": timeout,
            "cpu_samples": cpu_samples,
            "mean_cpu": mean_cpu,
            "max_cpu": max_cpu,
            "details": f"Timeout de {timeout}s atingido na chamada critica",
        }
        res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res
    except Exception as exc:
        stop_cpu = True
        dur = time.perf_counter() - t_spawn
        res = {
            "venv": venv_name,
            "scenario": scenario,
            "rep": rep,
            "classe": "ERRO",
            "dur_critica": dur,
            "cpu_samples": cpu_samples,
            "mean_cpu": 0.0,
            "max_cpu": 0.0,
            "details": f"{type(exc).__name__}: {exc}",
        }
        res_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def main_async():
    log("Iniciando PASSO 4e: Teste Definitivo do F4-017 (20 execuções sequenciais)")
    all_results = []

    for venv_name, py_exe in VENVS.items():
        log(f"=== VENV: {venv_name} ({py_exe}) ===")
        for sc in ["search-first", "mine"]:
            for rep in range(1, 6):
                log(f"-> Executando {venv_name} | {sc} | rep {rep}/5...")
                res = await run_single_e2e(py_exe, venv_name, sc, rep)
                all_results.append(res)
                log(f"   Resultado: {res['classe']} | Critica={res.get('dur_critica', 0.0):.2f}s | CPU_mean={res.get('mean_cpu', 0.0):.1f}%")

    # Gera tabela formatada
    lines = []
    lines.append("=== TABELA PASSO 4e: TESTE DEFINITIVO F4-017 (MCP REAL STDIO SEM WRAPPER) ===")
    lines.append(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("Total de execuções: 20 (2 venvs x 2 cenários x 5 repetições)")
    lines.append("")
    lines.append(f"{'Venv':<13} | {'Cenário':<13} | {'Rep':<4} | {'Classe':<7} | {'t_init(s)':<10} | {'t_critica(s)':<13} | {'t_sec(s)':<10} | {'CPU_mean(%)':<12}")
    lines.append("-" * 95)
    for r in all_results:
        t_init = f"{r.get('t_init', 0.0):.2f}" if "t_init" in r else "N/A"
        t_crit = f"{r.get('dur_critica', 0.0):.2f}"
        t_sec = f"{r.get('dur_secundaria', 0.0):.2f}" if "dur_secundaria" in r else "N/A"
        cpu = f"{r.get('mean_cpu', 0.0):.1f}"
        lines.append(f"{r['venv']:<13} | {r['scenario']:<13} | {r['rep']:<4} | {r['classe']:<7} | {t_init:<10} | {t_crit:<13} | {t_sec:<10} | {cpu:<12}")
    lines.append("-" * 95)

    n_ok = sum(1 for r in all_results if r["classe"] == "OK")
    n_travou = sum(1 for r in all_results if r["classe"] == "TRAVOU")
    n_erro = sum(1 for r in all_results if r["classe"] not in ("OK", "TRAVOU"))
    lines.append(f"Total OK: {n_ok}/20 | Total TRAVOU: {n_travou}/20 | Total ERRO: {n_erro}/20")
    lines.append(f"Status Final: {'SUCESSO ABSOLUTO (20/20 OK)' if n_ok == 20 else 'HOUVE FALHA'}")

    out_text = "\n".join(lines) + "\n"
    TABLE_OUT.write_text(out_text, encoding="utf-8")
    print("\n" + out_text)


if __name__ == "__main__":
    asyncio.run(main_async())

