# scratch/evidencia_4_2g/run_e2e_4_2g.py
"""
Rodada 4.2g — Item 3b, 3c, 3d:
Executa E2E real (STDIO, sem wrapper e sem aquecimento) no venv completo com mcp==1.30.0.
Grava em cada result.json:
  - versoes de mcp, chromadb, sentence_transformers, scipy, numpy, torch;
  - se server_stderr.log contem "NO-OP" ou "not installed";
  - numero de vetores na colecao Chroma temporaria apos o cenario mine (count_embeddings).
Classifica a execucao como INVALIDA se aparecer "NO-OP" ou "not installed", ou se o mine
terminar com 0 vetores.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
WT_DD92D35 = Path(r"C:\Nexus-Memory\_wt_4_2e\dd92d35")

sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2e"))
import mcp_e2e_v2 as v2  # noqa: E402

SEED_SCRIPT = r"""
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


def get_venv_versions(py_exe: str) -> dict[str, str]:
    code = (
        "import importlib.metadata as m, json; "
        "pkgs = {'mcp': 'mcp', 'chromadb': 'chromadb', "
        "'sentence_transformers': 'sentence-transformers', "
        "'scipy': 'scipy', 'numpy': 'numpy', 'torch': 'torch'}; "
        "print(json.dumps({k: m.version(v) for k, v in pkgs.items()}))"
    )
    out = subprocess.check_output([py_exe, "-c", code], text=True, encoding="utf-8")
    return json.loads(out.strip())


def kill_tree(proc):
    if proc is None:
        return
    try:
        for ch in proc.children(recursive=True):
            try:
                ch.kill()
            except Exception:
                pass
        proc.kill()
    except Exception:
        pass


def log(msg: str, logfile: Path):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with logfile.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


async def run_single_e2e(
    py_exe: str,
    venv_name: str,
    target_repo: Path,
    commit_label: str,
    outdir: Path,
    scenario: str,
    rep: int,
    versions: dict[str, str],
    timeout: float = 180.0,
) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    case_dir = outdir / f"{commit_label}__{venv_name}__{scenario}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    errlog_path = case_dir / "server_stderr.log"
    res_path = case_dir / "result.json"

    tmp = Path(tempfile.mkdtemp(prefix=f"e2e42g_{commit_label}_{scenario}_{rep}_"))
    db = str(tmp / "test.db")
    chroma = str(tmp / "chroma")
    proj = str(tmp / "sample_proj")
    v2.create_sample_project(proj)

    env = os.environ.copy()
    env.update({
        "GRAFO_DB_PATH": db,
        "GRAFO_CHROMA_PATH": chroma,
        "GRAFO_CHROMA_COLLECTION": f"col_{commit_label}_{scenario}_{rep}",
        "GRAFO_TRANSPORT": "stdio",
        "GRAFO_LOG_LEVEL": "INFO",
        "GRAFO_EMBED_WARMUP": "false",
        "GRAFO_LLM_API_KEY": "",
        "GRAFO_LLM_MODEL": "none",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TQDM_DISABLE": "1",
        "HF_HUB_OFFLINE": "1",
        "PYTHONPATH": str(target_repo),
        "REG_REPO": str(target_repo),
        "REG_PROJ": proj,
    })

    uuid = None
    seed_vectors = 0
    if scenario == "search-first":
        seed_out = str(tmp / "seed.json")
        env_seed = dict(env, REG_SEED_OUT=seed_out)
        r_seed = subprocess.run(
            [py_exe, "-u", "-c", SEED_SCRIPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env_seed,
            cwd=str(target_repo),
        )
        (case_dir / "seed.log").write_text(r_seed.stdout + "\n" + r_seed.stderr, encoding="utf-8")
        if r_seed.returncode != 0 or not os.path.exists(seed_out):
            shutil.rmtree(tmp, ignore_errors=True)
            res = {
                "commit": commit_label,
                "venv": venv_name,
                "versions": versions,
                "scenario": scenario,
                "rep": rep,
                "classe": "ERRO_SEED",
                "dur_critica": 0.0,
                "post_mine_vectors": 0,
                "stderr_contains_noop": False,
                "stderr_contains_not_installed": False,
                "mean_cpu": 0.0,
                "max_cpu": 0.0,
                "details": "Falha no seed in-process",
            }
            res_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
            return res
        seed_data = json.loads(Path(seed_out).read_text(encoding="utf-8"))
        uuid = seed_data["uuid"]
        seed_vectors = int(seed_data.get("seed_vectors", 0))

    server_params = StdioServerParameters(
        command=py_exe,
        args=["-u", "main.py"],
        env=env,
        cwd=str(target_repo),
    )

    t_spawn = time.perf_counter()
    cpu_samples: list[float] = []
    stop_cpu = False
    server_proc = None
    t_init = None
    dur_crit = None
    dur_sec = None
    post_mine_vectors = 0
    raw_classe = "ERRO"
    details = ""

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
            try:
                async with stdio_client(server_params, errlog=errlog) as (read_stream, write_stream), \
                           ClientSession(read_stream, write_stream) as session:

                    if psutil is not None:
                        curr_p = psutil.Process()
                        children = [c for c in curr_p.children(recursive=True) if "python" in c.name().lower()]
                        if children:
                            server_proc = children[-1]
                            server_proc.cpu_percent(interval=None)
                            t_mon = threading.Thread(target=cpu_monitor, args=(server_proc,), daemon=True)
                            t_mon.start()

                    # 1. Initialize
                    t0_init = time.perf_counter()
                    await asyncio.wait_for(session.initialize(), timeout=30.0)
                    t_init = time.perf_counter() - t0_init

                    # 2. List tools
                    await asyncio.wait_for(session.list_tools(), timeout=15.0)

                    if scenario == "mine":
                        reg_res = await asyncio.wait_for(
                            session.call_tool("concierge_register", arguments={
                                "project_path": proj,
                                "wing": "geral",
                                "privacy_level": "PUBLIC",
                                "summary": f"E2E 4.2g {commit_label} mine {rep}",
                            }),
                            timeout=30.0,
                        )
                        reg_data = v2.parse_mcp_result(reg_res, "concierge_register")
                        u_mine = reg_data["project_uuid"]

                        t0_crit = time.perf_counter()
                        try:
                            mine_res = await asyncio.wait_for(
                                session.call_tool("concierge_mine", arguments={
                                    "path": proj,
                                    "project_identifier": u_mine,
                                    "auto_tag": True,
                                }),
                                timeout=timeout,
                            )
                        except asyncio.TimeoutError:
                            dur_crit = time.perf_counter() - t0_crit
                            raw_classe = "TRAVOU"
                            details = f"Timeout de {timeout}s atingido em concierge_mine"
                            stop_cpu = True
                            kill_tree(server_proc)
                            raise

                        dur_crit = time.perf_counter() - t0_crit
                        v2.parse_mcp_result(mine_res, "concierge_mine")

                        # Count vectors in Chroma after mine
                        cnt_res = await asyncio.wait_for(
                            session.call_tool("count_embeddings", arguments={
                                "project_identifier": u_mine,
                            }),
                            timeout=30.0,
                        )
                        cnt_data = v2.parse_mcp_result(cnt_res, "count_embeddings")
                        post_mine_vectors = int(cnt_data.get("count", 0))

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
                        raw_classe = "OK"

                    else:  # search-first
                        t0_crit = time.perf_counter()
                        try:
                            s_res = await asyncio.wait_for(
                                session.call_tool("concierge_search", arguments={
                                    "query": "rectangle area width height",
                                    "project_identifier": uuid,
                                    "top_k": 3,
                                }),
                                timeout=timeout,
                            )
                        except asyncio.TimeoutError:
                            dur_crit = time.perf_counter() - t0_crit
                            raw_classe = "TRAVOU"
                            details = f"Timeout de {timeout}s atingido em concierge_search"
                            stop_cpu = True
                            kill_tree(server_proc)
                            raise

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

                        # Count vectors in Chroma after mine
                        cnt_res = await asyncio.wait_for(
                            session.call_tool("count_embeddings", arguments={
                                "project_identifier": uuid,
                            }),
                            timeout=30.0,
                        )
                        cnt_data = v2.parse_mcp_result(cnt_res, "count_embeddings")
                        post_mine_vectors = int(cnt_data.get("count", 0))
                        raw_classe = "OK"

                    stop_cpu = True
            except BaseException as inner_exc:
                stop_cpu = True
                if raw_classe != "TRAVOU":
                    kill_tree(server_proc)
                    raw_classe = "ERRO"
                    details = f"{type(inner_exc).__name__}: {inner_exc}"
                if dur_crit is None:
                    dur_crit = time.perf_counter() - t_spawn
    finally:
        stop_cpu = True
        kill_tree(server_proc)
        shutil.rmtree(tmp, ignore_errors=True)

    stderr_text = errlog_path.read_text(encoding="utf-8", errors="replace") if errlog_path.exists() else ""
    stderr_contains_noop = "NO-OP" in stderr_text
    stderr_contains_not_installed = "not installed" in stderr_text.lower()

    # Regra estrita do Item 3b:
    # Classifique a execucao como INVALIDA se aparecer "NO-OP" ou "not installed",
    # ou se o mine terminar com 0 vetores.
    final_classe = raw_classe
    if stderr_contains_noop or stderr_contains_not_installed:
        final_classe = "INVÁLIDA"
        details = f"INVÁLIDA: stderr_noop={stderr_contains_noop}, stderr_not_installed={stderr_contains_not_installed}"
    elif raw_classe == "OK" and post_mine_vectors <= 0:
        final_classe = "INVÁLIDA"
        details = f"INVÁLIDA: mine terminou com post_mine_vectors={post_mine_vectors}"

    mean_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
    max_cpu = max(cpu_samples) if cpu_samples else 0.0

    res = {
        "commit": commit_label,
        "venv": venv_name,
        "python": py_exe,
        "versions": versions,
        "scenario": scenario,
        "rep": rep,
        "classe": final_classe,
        "raw_classe": raw_classe,
        "t_init": round(t_init, 4) if t_init is not None else None,
        "dur_critica": round(dur_crit, 4) if dur_crit is not None else None,
        "dur_secundaria": round(dur_sec, 4) if dur_sec is not None else None,
        "seed_vectors": seed_vectors,
        "post_mine_vectors": post_mine_vectors,
        "stderr_contains_noop": stderr_contains_noop,
        "stderr_contains_not_installed": stderr_contains_not_installed,
        "cpu_samples": [round(x, 2) for x in cpu_samples],
        "mean_cpu": round(mean_cpu, 2),
        "max_cpu": round(max_cpu, 2),
        "details": details or "OK",
    }
    res_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return res


def format_table(
    title: str,
    commit_label: str,
    versions: dict[str, str],
    results: list[dict],
    reps_per_scenario: int,
) -> str:
    total_expected = reps_per_scenario * 2
    lines = []
    lines.append(f"=== {title} ===")
    lines.append(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Commit alvo: {commit_label}")
    lines.append(
        "Versões no venv: "
        + ", ".join(f"{k}={v}" for k, v in versions.items())
    )
    lines.append(f"Total de execuções sequenciais: {total_expected} (2 cenários x {reps_per_scenario} repetições)")
    lines.append("")
    header = (
        f"{'Commit':<10} | {'Cenário':<13} | {'Rep':<3} | {'Classe':<8} | "
        f"{'t_init(s)':<9} | {'t_crit(s)':<10} | {'t_sec(s)':<9} | "
        f"{'Vetores':<7} | {'NO-OP':<5} | {'not_inst':<8} | {'CPU(%)':<6}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        t_init = f"{r['t_init']:.2f}" if r.get("t_init") is not None else "N/A"
        t_crit = f"{r['dur_critica']:.2f}" if r.get("dur_critica") is not None else "N/A"
        t_sec = f"{r['dur_secundaria']:.2f}" if r.get("dur_secundaria") is not None else "N/A"
        vecs = str(r.get("post_mine_vectors", 0))
        noop = str(r.get("stderr_contains_noop", False))
        not_inst = str(r.get("stderr_contains_not_installed", False))
        cpu = f"{r.get('mean_cpu', 0.0):.1f}"
        lines.append(
            f"{r['commit']:<10} | {r['scenario']:<13} | {r['rep']:<3} | {r['classe']:<8} | "
            f"{t_init:<9} | {t_crit:<10} | {t_sec:<9} | "
            f"{vecs:<7} | {noop:<5} | {not_inst:<8} | {cpu:<6}"
        )
    lines.append("-" * len(header))
    n_ok = sum(1 for r in results if r["classe"] == "OK")
    n_travou = sum(1 for r in results if r["classe"] == "TRAVOU")
    n_invalida = sum(1 for r in results if r["classe"] == "INVÁLIDA")
    n_erro = sum(1 for r in results if r["classe"] not in ("OK", "TRAVOU", "INVÁLIDA"))
    lines.append(
        f"Resumo: OK={n_ok}/{total_expected} | TRAVOU={n_travou}/{total_expected} | "
        f"INVÁLIDA={n_invalida}/{total_expected} | ERRO={n_erro}/{total_expected}"
    )
    return "\n".join(lines) + "\n"


async def main_async():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["head", "control", "all"], default="all")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    py_exe = sys.executable
    versions = get_venv_versions(py_exe)
    venv_name = "mcp_1_30_0_full"

    if args.mode in ("head", "all"):
        head_short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            encoding="utf-8",
        ).strip()
        outdir_head = HERE / "e2e_mcp130_full"
        outdir_head.mkdir(parents=True, exist_ok=True)
        logfile_head = outdir_head / "execution.log"
        log(f"Iniciando Item 3c: E2E em HEAD ({head_short}) com {venv_name}, n=5 sequenciais", logfile_head)
        head_results = []
        for sc in ["search-first", "mine"]:
            for rep in range(1, 6):
                log(f"-> HEAD ({head_short}) | {sc} | rep {rep}/5...", logfile_head)
                res = await run_single_e2e(
                    py_exe=py_exe,
                    venv_name=venv_name,
                    target_repo=REPO_ROOT,
                    commit_label=head_short,
                    outdir=outdir_head,
                    scenario=sc,
                    rep=rep,
                    versions=versions,
                    timeout=args.timeout,
                )
                head_results.append(res)
                log(
                    f"   Resultado: {res['classe']} | t_crit={res['dur_critica']}s | "
                    f"vectors={res['post_mine_vectors']} | noop={res['stderr_contains_noop']}",
                    logfile_head,
                )
        table_head = format_table(
            title="TABELA ITEM 3c: E2E NO HEAD COM MCP 1.30.0 COMPLETO (SEM WRAPPER / SEM WARMUP)",
            commit_label=head_short,
            versions=versions,
            results=head_results,
            reps_per_scenario=5,
        )
        (HERE / "item3_tabela_head_mcp130.txt").write_text(table_head, encoding="utf-8")
        print("\n" + table_head, flush=True)

    if args.mode in ("control", "all"):
        ctrl_short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(WT_DD92D35),
            text=True,
            encoding="utf-8",
        ).strip()
        outdir_ctrl = HERE / "control_dd92d35_mcp130_full"
        outdir_ctrl.mkdir(parents=True, exist_ok=True)
        logfile_ctrl = outdir_ctrl / "execution.log"
        log(f"Iniciando Item 3d: CONTROLE em {ctrl_short} com {venv_name}, n=3 sequenciais (timeout={args.timeout}s)", logfile_ctrl)
        ctrl_results = []
        for sc in ["search-first", "mine"]:
            for rep in range(1, 4):
                log(f"-> CONTROLE ({ctrl_short}) | {sc} | rep {rep}/3...", logfile_ctrl)
                res = await run_single_e2e(
                    py_exe=py_exe,
                    venv_name=venv_name,
                    target_repo=WT_DD92D35,
                    commit_label=ctrl_short,
                    outdir=outdir_ctrl,
                    scenario=sc,
                    rep=rep,
                    versions=versions,
                    timeout=args.timeout,
                )
                ctrl_results.append(res)
                log(
                    f"   Resultado: {res['classe']} | t_crit={res['dur_critica']}s | "
                    f"vectors={res['post_mine_vectors']} | noop={res['stderr_contains_noop']}",
                    logfile_ctrl,
                )
        table_ctrl = format_table(
            title="TABELA ITEM 3d: CONTROLE NEGATIVO NO COMMIT dd92d35 COM MCP 1.30.0 COMPLETO",
            commit_label=ctrl_short,
            versions=versions,
            results=ctrl_results,
            reps_per_scenario=3,
        )
        (HERE / "item3_tabela_control_dd92d35.txt").write_text(table_ctrl, encoding="utf-8")
        print("\n" + table_ctrl, flush=True)


if __name__ == "__main__":
    asyncio.run(main_async())
