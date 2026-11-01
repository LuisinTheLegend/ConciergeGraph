"""scratch/evidencia_4_2h/run_f4_017_regression.py

Passo 6B da Rodada 4.2h:
Executa o harness F4-017 (search-first e mine, n=3 por cenario, sequencial)
em venv_mcp127 e venv_mcp130_full no HEAD da 4.2h, com:
  - GRAFO_LLM_MODEL=none
  - GRAFO_LLM_API_KEY explicita com chave falsa (para nunca carregar .env)
  - HF_HUB_OFFLINE=1
  - Banco e Chroma temporarios (nunca data/)
Registra tempos, vetores criados, status (0 TRAVOU esperado) e a contagem
exata de linhas ERROR e WARNING por tipo em cada execucao.
"""

from __future__ import annotations

import asyncio
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

PY_127 = Path(r"C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe")
PY_130_FULL = Path(r"C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe")

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2e"))

import main as current_main  # noqa: E402
import mcp_e2e_v2 as v2  # noqa: E402

try:
    import psutil
except ImportError:
    psutil = None


def kill_tree(proc: Any) -> None:
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


def get_venv_versions(py_exe: Path) -> dict[str, str]:
    code = (
        "import importlib.metadata as m, json; "
        "pkgs = {'mcp': 'mcp', 'chromadb': 'chromadb', "
        "'sentence_transformers': 'sentence-transformers', "
        "'scipy': 'scipy', 'numpy': 'numpy', 'torch': 'torch'}; "
        "print(json.dumps({k: m.version(v) for k, v in pkgs.items()}))"
    )
    out = subprocess.check_output([str(py_exe), "-c", code], text=True, encoding="utf-8")
    return json.loads(out.strip())


def analyze_stderr(stderr_text: str) -> dict[str, Any]:
    safe_text = current_main.redact_log_secrets(stderr_text)
    lines = safe_text.splitlines()
    event_loop_closed = sum(1 for ln in lines if "Event loop is closed" in ln)
    task_exc = sum(1 for ln in lines if "Task exception was never retrieved" in ln)
    err_counter: collections.Counter[str] = collections.Counter()
    warn_counter: collections.Counter[str] = collections.Counter()
    for ln in lines:
        if re.search(r"\bERROR\b", ln):
            idx = ln.find("ERROR")
            body = ln[idx + 5 :].strip(" :-|") if idx >= 0 else ln.strip()
            err_counter[body[:140]] += 1
        elif re.search(r"\bWARNING\b", ln):
            idx = ln.find("WARNING")
            body = ln[idx + 7 :].strip(" :-|") if idx >= 0 else ln.strip()
            warn_counter[body[:140]] += 1
    return {
        "event_loop_closed": event_loop_closed,
        "task_exception_never_retrieved": task_exc,
        "error_total": sum(err_counter.values()),
        "warning_total": sum(warn_counter.values()),
        "error_by_type": dict(err_counter),
        "warning_by_type": dict(warn_counter),
    }


async def run_f4_017_case(
    py_exe: Path,
    venv_label: str,
    versions: dict[str, str],
    commit_label: str,
    scenario: str,
    rep: int,
    timeout: float = 120.0,
) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tmp = Path(tempfile.mkdtemp(prefix=f"f4017_42h_{venv_label}_{scenario}_{rep}_"))
    db = str(tmp / "test.db")
    chroma = str(tmp / "chroma")
    proj = str(tmp / "sample_proj")
    errlog_path = tmp / "server_stderr.log"
    v2.create_sample_project(proj)

    fake_key = "AQ." + "FAKEFAKEFAKE0001"
    env = os.environ.copy()
    for k in ["GRAFO_LLM_PROVIDER", "GRAFO_LLM_BASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        env.pop(k, None)

    env.update({
        "GRAFO_DB_PATH": db,
        "GRAFO_CHROMA_PATH": chroma,
        "GRAFO_CHROMA_COLLECTION": f"col_{venv_label}_{scenario}_{rep}",
        "GRAFO_TRANSPORT": "stdio",
        "GRAFO_LOG_LEVEL": "INFO",
        "GRAFO_EMBED_WARMUP": "false",
        "GRAFO_LLM_API_KEY": fake_key,
        "GRAFO_LLM_MODEL": "none",
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
        r_seed = subprocess.run(
            [str(py_exe), "-u", "-c", SEED_SCRIPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env_seed,
            cwd=str(REPO_ROOT),
        )
        if r_seed.returncode != 0 or not os.path.exists(seed_out):
            shutil.rmtree(tmp, ignore_errors=True)
            return {
                "commit": commit_label,
                "venv": venv_label,
                "mcp_version": versions.get("mcp", "?"),
                "scenario": scenario,
                "rep": rep,
                "classe": "ERRO_SEED",
                "t_init": None,
                "dur_critica": None,
                "dur_secundaria": None,
                "post_mine_vectors": 0,
                "stderr_contains_noop": False,
                "stderr_contains_not_installed": False,
                "stderr_stats": {},
            }
        seed_data = json.loads(Path(seed_out).read_text(encoding="utf-8"))
        uuid = seed_data["uuid"]

    server_params = StdioServerParameters(
        command=str(py_exe),
        args=["-u", "main.py"],
        env=env,
        cwd=str(REPO_ROOT),
    )

    t_init = None
    dur_crit = None
    dur_sec = None
    post_mine_vectors = 0
    raw_classe = "ERRO"
    server_proc = None

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

                    t0_init = time.perf_counter()
                    await asyncio.wait_for(session.initialize(), timeout=30.0)
                    t_init = round(time.perf_counter() - t0_init, 2)

                    await asyncio.wait_for(session.list_tools(), timeout=15.0)

                    if scenario == "mine":
                        reg_res = await asyncio.wait_for(
                            session.call_tool("concierge_register", arguments={
                                "project_path": proj,
                                "wing": "geral",
                                "privacy_level": "PUBLIC",
                                "summary": f"F4-017 4.2h {venv_label} mine {rep}",
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
                            dur_crit = round(time.perf_counter() - t0_crit, 2)
                            raw_classe = "TRAVOU"
                            raise

                        dur_crit = round(time.perf_counter() - t0_crit, 2)
                        v2.parse_mcp_result(mine_res, "concierge_mine")

                        cnt_res = await asyncio.wait_for(
                            session.call_tool("count_embeddings", arguments={
                                "project_identifier": u_mine,
                            }),
                            timeout=30.0,
                        )
                        cnt_data = v2.parse_mcp_result(cnt_res, "count_embeddings")
                        post_mine_vectors = int(cnt_data.get("count", 0))

                        t0_sec = time.perf_counter()
                        s_res = await asyncio.wait_for(
                            session.call_tool("concierge_search", arguments={
                                "query": "rectangle area width height",
                                "project_identifier": u_mine,
                                "top_k": 3,
                            }),
                            timeout=30.0,
                        )
                        dur_sec = round(time.perf_counter() - t0_sec, 2)
                        v2.parse_mcp_result(s_res, "concierge_search")
                        raw_classe = "OK"
                    else:
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
                            dur_crit = round(time.perf_counter() - t0_crit, 2)
                            raw_classe = "TRAVOU"
                            raise

                        dur_crit = round(time.perf_counter() - t0_crit, 2)
                        v2.parse_mcp_result(s_res, "concierge_search")

                        t0_sec = time.perf_counter()
                        mine_res = await asyncio.wait_for(
                            session.call_tool("concierge_mine", arguments={
                                "path": proj,
                                "project_identifier": uuid,
                                "auto_tag": True,
                            }),
                            timeout=timeout,
                        )
                        dur_sec = round(time.perf_counter() - t0_sec, 2)
                        v2.parse_mcp_result(mine_res, "concierge_mine")

                        cnt_res = await asyncio.wait_for(
                            session.call_tool("count_embeddings", arguments={
                                "project_identifier": uuid,
                            }),
                            timeout=30.0,
                        )
                        cnt_data = v2.parse_mcp_result(cnt_res, "count_embeddings")
                        post_mine_vectors = int(cnt_data.get("count", 0))
                        raw_classe = "OK"
            except BaseException:
                kill_tree(server_proc)
                if raw_classe != "TRAVOU":
                    raw_classe = "ERRO"
        await asyncio.sleep(0.2)
        stderr_text = errlog_path.read_text(encoding="utf-8", errors="replace") if errlog_path.exists() else ""
    finally:
        kill_tree(server_proc)
        shutil.rmtree(tmp, ignore_errors=True)

    stderr_noop = "NO-OP" in stderr_text
    stderr_not_inst = "not installed" in stderr_text.lower()
    final_classe = raw_classe
    if stderr_noop or stderr_not_inst or (raw_classe == "OK" and post_mine_vectors <= 0):
        final_classe = "INVÁLIDA"

    st_stats = analyze_stderr(stderr_text)
    return {
        "commit": commit_label,
        "venv": venv_label,
        "mcp_version": versions.get("mcp", "?"),
        "scenario": scenario,
        "rep": rep,
        "classe": final_classe,
        "t_init": t_init,
        "dur_critica": dur_crit,
        "dur_secundaria": dur_sec,
        "post_mine_vectors": post_mine_vectors,
        "stderr_contains_noop": stderr_noop,
        "stderr_contains_not_installed": stderr_not_inst,
        "stderr_stats": st_stats,
    }


async def main_async() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    head_short = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO_ROOT), text=True
    ).strip()

    venvs = [
        ("venv_mcp127", PY_127),
        ("venv_mcp130_full", PY_130_FULL),
    ]
    all_rows: list[dict[str, Any]] = []
    for venv_label, py_exe in venvs:
        versions = get_venv_versions(py_exe)
        for scenario in ["search-first", "mine"]:
            for rep in range(1, 4):
                print(f"[F4-017 4.2h] {venv_label} | {scenario} | rep {rep}/3 ...", flush=True)
                row = await run_f4_017_case(
                    py_exe=py_exe,
                    venv_label=venv_label,
                    versions=versions,
                    commit_label=head_short,
                    scenario=scenario,
                    rep=rep,
                )
                all_rows.append(row)
                print(
                    f"  -> classe={row['classe']} t_crit={row['dur_critica']}s "
                    f"vecs={row['post_mine_vectors']} err={row['stderr_stats']['error_total']} "
                    f"warn={row['stderr_stats']['warning_total']}",
                    flush=True,
                )

    (HERE / "p6_f4_017_regression.json").write_text(
        json.dumps(all_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines: list[str] = []
    lines.append("=== PASSO 6B: HARNESS F4-017 EM venv_mcp127 E venv_mcp130_full (GRAFO_LLM_MODEL=none) ===")
    lines.append(f"Commit: {head_short}")
    lines.append("")
    hdr = (
        f"{'Venv':<16} | {'MCP':<6} | {'Cenário':<12} | {'Rep':<3} | {'Classe':<8} | "
        f"{'t_init':<6} | {'t_crit':<6} | {'t_sec':<5} | {'Vecs':<4} | {'NO-OP':<5} | "
        f"{'LoopCl':<6} | {'TaskEx':<6} | {'ERR':<3} | {'WARN':<4}"
    )
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for r in all_rows:
        st = r["stderr_stats"]
        lines.append(
            f"{r['venv']:<16} | {r['mcp_version']:<6} | {r['scenario']:<12} | {r['rep']:<3} | "
            f"{r['classe']:<8} | {str(r['t_init']):<6} | {str(r['dur_critica']):<6} | "
            f"{str(r['dur_secundaria']):<5} | {r['post_mine_vectors']:<4} | "
            f"{str(r['stderr_contains_noop']):<5} | {st['event_loop_closed']:<6} | "
            f"{st['task_exception_never_retrieved']:<6} | {st['error_total']:<3} | {st['warning_total']:<4}"
        )
    lines.append("-" * len(hdr))
    n_ok = sum(1 for r in all_rows if r["classe"] == "OK")
    n_travou = sum(1 for r in all_rows if r["classe"] == "TRAVOU")
    lines.append(f"Resumo Geral: OK={n_ok}/{len(all_rows)} | TRAVOU={n_travou}/{len(all_rows)}")
    lines.append("")
    lines.append("=== DETALHAMENTO DE ERROR / WARNING POR EXECUÇÃO ===")
    for r in all_rows:
        st = r["stderr_stats"]
        lines.append(
            f"[{r['venv']} | {r['scenario']} | rep={r['rep']}] "
            f"ERROR({st['error_total']})={json.dumps(st['error_by_type'], ensure_ascii=False)} | "
            f"WARNING({st['warning_total']})={json.dumps(st['warning_by_type'], ensure_ascii=False)}"
        )

    out_txt = "\n".join(lines) + "\n"
    (HERE / "p6_f4_017_regression.txt").write_text(out_txt, encoding="utf-8")
    print("\n" + out_txt, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))

