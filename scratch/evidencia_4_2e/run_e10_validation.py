# run_e10_validation.py
# Experimento E10 da Rodada 4.2e-3:
# Validacao em servidor de verdade SEM editar producao.
#
# Aplica a tecnica vencedora atraves de wrapper_main.py sobre dd92d35:
#   - Tecnica 1: "decouple_fd0" (Variante A do Experimento E7)
#   - Tecnica 2: "preimport" (Conjunto S6 do Experimento E9)
#
# Cenarios:
#   - "mine": register -> concierge_mine (1o embedding) -> concierge_search (1a busca)
#   - "search-first": seed in-process -> MCP server -> concierge_search (1a busca) -> concierge_mine (1o mine)
#
# Mede:
#   - tempo de inicializacao (t_init)
#   - tempo do 1o mine (t_mine)
#   - tempo da 1a busca (t_search)
#
# Repeticoes: n=5 por tecnica e cenario. Timeout: 180s.
# Ao final, executa boot_check.py para conferir saude e 31 ferramentas.

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
OUTDIR = HERE / "e10_validation"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e10.txt"
BOOT_CHECK_OUT = HERE / "boot_check_e10.txt"

sys.path.insert(0, str(HERE))
import mcp_e2e_v2 as v2

SEED_CODE = r"""
import json, os, sys
sys.path.insert(0, os.environ["REG_REPO"])
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
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

async def run_single_case(technique: str, scenario: str, rep: int, timeout: float = 180.0) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    case_dir = OUTDIR / f"{technique}__{scenario}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    errlog_path = case_dir / "server_stderr.log"
    res_path = case_dir / "result.json"

    tmp = Path(tempfile.mkdtemp(prefix=f"e10_{technique}_{scenario}_"))
    db = str(tmp / "test.db")
    chroma = str(tmp / "chroma")
    proj = str(tmp / "sample_proj")
    v2.create_sample_project(proj)

    env = os.environ.copy()
    env.update({
        "GRAFO_DB_PATH": db,
        "GRAFO_CHROMA_PATH": chroma,
        "GRAFO_CHROMA_COLLECTION": f"col_{technique}_{scenario}_{rep}",
        "GRAFO_TRANSPORT": "stdio",
        "GRAFO_LOG_LEVEL": "INFO",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TQDM_DISABLE": "1",
        "HF_HUB_OFFLINE": "1",
        "PYTHONPATH": str(REPO_ROOT),
        "REG_REPO": str(REPO_ROOT),
        "REG_PROJ": proj,
        "CONCIERGE_WRAPPER_TECHNIQUE": technique,
    })

    uuid = None
    if scenario == "search-first":
        seed_out = str(tmp / "seed.json")
        env_seed = dict(env, REG_SEED_OUT=seed_out)
        t0_seed = time.perf_counter()
        with open(case_dir / "seed.log", "w", encoding="utf-8") as sl:
            r = subprocess.run(
                [sys.executable, "-c", SEED_CODE],
                env=env_seed,
                cwd=str(REPO_ROOT),
                stdout=sl,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
        if r.returncode != 0 or not os.path.exists(seed_out):
            shutil.rmtree(tmp, ignore_errors=True)
            return {"technique": technique, "scenario": scenario, "rep": rep, "classe": "SEED_FALHOU"}
        uuid = json.load(open(seed_out))["uuid"]

    server_script = str(HERE / "wrapper_main.py")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", server_script],
        env=env,
        cwd=str(REPO_ROOT),
    )

    t_spawn = time.perf_counter()
    t_init = None
    t_mine = None
    t_search = None
    classe = "ERRO"
    err_msg = ""

    try:
        with open(errlog_path, "w", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as (rs, ws):
                async with ClientSession(rs, ws) as session:
                    # 1. Initialize
                    await asyncio.wait_for(session.initialize(), timeout=60)
                    t_init = time.perf_counter() - t_spawn
                    await session.list_tools()

                    if scenario == "mine":
                        # Register
                        reg_res = await session.call_tool("concierge_register", {
                            "project_path": proj,
                            "wing": "geral",
                            "privacy_level": "PUBLIC",
                            "summary": "reg",
                        })
                        reg_data = v2.parse_mcp_result(reg_res, "register")
                        uuid = reg_data["project_uuid"]

                        # 1o Mine
                        t0 = time.perf_counter()
                        mine_res = await asyncio.wait_for(
                            session.call_tool("concierge_mine", {"path": proj, "project_identifier": uuid, "auto_tag": True}),
                            timeout=timeout,
                        )
                        t_mine = time.perf_counter() - t0
                        v2.parse_mcp_result(mine_res, "concierge_mine")

                        # 1a Busca
                        t0 = time.perf_counter()
                        search_res = await asyncio.wait_for(
                            session.call_tool("concierge_search", {"query": "calculate rectangle area width height", "project_identifier": uuid, "top_k": 5}),
                            timeout=timeout,
                        )
                        t_search = time.perf_counter() - t0
                        s_data = v2.parse_mcp_result(search_res, "concierge_search")
                        if len(s_data.get("results", [])) > 0:
                            classe = "OK"

                    elif scenario == "search-first":
                        # 1a Busca (primeira chamada a usar o modelo)
                        t0 = time.perf_counter()
                        search_res = await asyncio.wait_for(
                            session.call_tool("concierge_search", {"query": "calculate rectangle area width height", "project_identifier": uuid, "top_k": 5}),
                            timeout=timeout,
                        )
                        t_search = time.perf_counter() - t0
                        s_data = v2.parse_mcp_result(search_res, "concierge_search")

                        # 1o Mine sob MCP
                        t0 = time.perf_counter()
                        mine_res = await asyncio.wait_for(
                            session.call_tool("concierge_mine", {"path": proj, "project_identifier": uuid, "auto_tag": True}),
                            timeout=timeout,
                        )
                        t_mine = time.perf_counter() - t0
                        v2.parse_mcp_result(mine_res, "concierge_mine")

                        if len(s_data.get("results", [])) > 0:
                            classe = "OK"

    except asyncio.TimeoutError:
        classe = "TRAVOU"
        err_msg = "Timeout na chamada crítica do MCP"
    except Exception as exc:
        classe = "ERRO"
        err_msg = f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    result = {
        "technique": technique,
        "scenario": scenario,
        "rep": rep,
        "classe": classe,
        "t_init_s": round(t_init, 3) if t_init is not None else None,
        "t_mine_s": round(t_mine, 3) if t_mine is not None else None,
        "t_search_s": round(t_search, 3) if t_search is not None else None,
        "total_s": round(time.perf_counter() - t_spawn, 3),
        "error": err_msg,
    }
    res_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def save_table(results: list[dict]):
    lines = []
    lines.append("=== TABELA EXPERIMENTO E10: SERVIDOR REAL COM WRAPPER (dd92d35) ===")
    lines.append(
        f"{'Tecnica':<15} | {'Cenario':<13} | {'Rep':<4} | {'Classe':<8} | {'t_init(s)':<10} | {'t_mine(s)':<10} | {'t_search(s)':<12} | {'Total(s)'}"
    )
    lines.append("-" * 95)
    for r in results:
        ti = f"{r['t_init_s']:.2f}" if r['t_init_s'] is not None else "-"
        tm = f"{r['t_mine_s']:.2f}" if r['t_mine_s'] is not None else "-"
        ts = f"{r['t_search_s']:.2f}" if r['t_search_s'] is not None else "-"
        tot = f"{r['total_s']:.2f}" if r.get('total_s') is not None else "-"
        lines.append(
            f"{r['technique']:<15} | {r['scenario']:<13} | {r['rep']:<4} | {r['classe']:<8} | "
            f"{ti:<10} | {tm:<10} | {ts:<12} | {tot}"
        )
    lines.append("-" * 95)
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def run_boot_check_validation(technique: str) -> str:
    log(f"Executando boot_check.py para validar saude e ferramentas com tecnica: {technique}")
    env = os.environ.copy()
    env["CONCIERGE_WRAPPER_TECHNIQUE"] = technique
    env["HF_HUB_OFFLINE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable, "-u", str(REPO_ROOT / "scratch" / "boot_check.py"),
        "--server-script", str(HERE / "wrapper_main.py"),
        "--timeout", "60",
    ]
    r = subprocess.run(cmd, env=env, cwd=str(REPO_ROOT), capture_output=True, text=True)
    out = f"BOOT_CHECK ({technique}) returncode={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    BOOT_CHECK_OUT.write_text(out, encoding="utf-8")
    log(f"boot_check concluido: rc={r.returncode}")
    return out

def main():
    log("INICIANDO EXPERIMENTO E10 — VALIDACAO EM SERVIDOR DE VERDADE COM WRAPPER (dd92d35)")
    techniques = ["decouple_fd0", "preimport"]
    scenarios = ["mine", "search-first"]
    reps = 5

    results = []
    for tech in techniques:
        for sc in scenarios:
            for rep in range(1, reps + 1):
                log(f"INICIO tech={tech} sc={sc} rep={rep}")
                res = asyncio.run(run_single_case(tech, sc, rep))
                ti = f"init={res['t_init_s']}s" if res['t_init_s'] else ""
                tm = f"mine={res['t_mine_s']}s" if res['t_mine_s'] else ""
                ts = f"search={res['t_search_s']}s" if res['t_search_s'] else ""
                log(f"FIM    tech={tech} sc={sc} rep={rep} -> {res['classe']} ({ti}, {tm}, {ts})")
                results.append(res)
                save_table(results)

    save_table(results)
    log(f"Tabela E10 gerada com sucesso em: {TABLE_OUT}")

    # Executa boot_check para ambas as tecnicas
    bc_decouple = run_boot_check_validation("decouple_fd0")
    bc_preimport = run_boot_check_validation("preimport")
    BOOT_CHECK_OUT.write_text(bc_decouple + "\n\n" + bc_preimport, encoding="utf-8")
    log("Validacao E10 finalizada com sucesso.")

if __name__ == "__main__":
    main()

