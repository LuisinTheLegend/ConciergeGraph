"""
regress_rep.py - UMA repeticao do controle de regressao (Passo 2) contra um worktree.

Cenarios:
  search-first : semeia DB/Chroma EM PROCESSO (fora do servidor MCP) e so entao sobe o servidor MCP;
                 a 1a chamada MCP que usa o modelo e concierge_search (cronometrada, timeout --timeout).
  mine         : sobe o servidor MCP, register, e concierge_mine (cronometrada, timeout --timeout).

Classificacao: OK | TRAVOU (timeout na chamada critica) | ERRO (qualquer outra falha) | SEED_FALHOU.
Em TRAVOU: CPU/threads/RSS do processo do servidor a cada 5 s por 60 s (psutil), dump de pilha via
faulthandler.dump_traceback_later (arquivo stack.txt), e o servidor e encerrado a forca.
Saida: <outdir>/result.json (+ server_stderr.log, stack.txt, seed.log).
"""
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
sys.path.insert(0, str(HERE))
import mcp_e2e_v2 as v2  # noqa: E402  (create_sample_project, parse_mcp_result)

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

SERVER_WRAPPER = r"""
import faulthandler, os, sys
sys.path.insert(0, os.environ["REG_REPO"])
_f = open(os.environ["REG_STACK_FILE"], "w", buffering=1)
faulthandler.dump_traceback_later(float(os.environ.get("REG_DUMP_AFTER", "120")), repeat=True, file=_f)
import main, storage
print("REG_PROOF main=%s storage=%s" % (main.__file__, storage.__file__), file=sys.stderr, flush=True)
main.main()
"""

SEED_CODE = r"""
import json, os, sys
sys.path.insert(0, os.environ["REG_REPO"])
import main, storage
print("REG_PROOF main=%s storage=%s" % (main.__file__, storage.__file__), flush=True)
server, janitor, store = main.bootstrap()
gc = server._gc
proj = os.environ["REG_PROJ"]
u = gc.register_project(os.path.basename(proj), "geral", "PUBLIC", "seed")
res = gc.mine(u, proj, auto_tag=True)
json.dump({"uuid": u, "res": str(res)[:400]}, open(os.environ["REG_SEED_OUT"], "w"))
store.close()
"""


def find_server_proc():
    if psutil is None:
        return None
    for ch in psutil.Process().children(recursive=True):
        try:
            if "faulthandler.dump_traceback_later" in " ".join(ch.cmdline()):
                return ch
        except Exception:
            continue
    return None


def sample_cpu(proc, seconds=60, step=5):
    """CPU% (de 1 nucleo) por intervalo, threads e RSS."""
    out = []
    if proc is None:
        return out
    try:
        prev = proc.cpu_times()
        prev_t = time.perf_counter()
        for _ in range(int(seconds / step)):
            time.sleep(step)
            cur = proc.cpu_times()
            now = time.perf_counter()
            used = (cur.user + cur.system) - (prev.user + prev.system)
            out.append({
                "t_s": round(now - prev_t, 2),
                "cpu_pct_1core": round(100.0 * used / (now - prev_t), 2),
                "threads": proc.num_threads(),
                "rss_mb": round(proc.memory_info().rss / 1048576.0, 1),
            })
            prev, prev_t = cur, now
    except Exception as e:  # noqa
        out.append({"erro": f"{type(e).__name__}: {e}"})
    return out


def kill_tree(proc):
    if proc is None:
        return
    try:
        for ch in proc.children(recursive=True):
            ch.kill()
        proc.kill()
    except Exception:
        pass


async def run(args, res, outdir: Path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tmp = Path(tempfile.mkdtemp(prefix="reg_"))
    db, chroma, proj = str(tmp / "c.db"), str(tmp / "chroma"), str(tmp / "sample_project")
    v2.create_sample_project(proj)
    stack_path = outdir.resolve() / "stack.txt"
    stack_file = str(stack_path)

    env = os.environ.copy()
    env.update({
        "GRAFO_DB_PATH": db, "GRAFO_CHROMA_PATH": chroma, "GRAFO_CHROMA_COLLECTION": "reg_col",
        "GRAFO_TRANSPORT": "stdio", "GRAFO_LOG_LEVEL": "INFO",
        "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1", "TQDM_DISABLE": "1",
        "GRAFO_LLM_API_KEY": "", "GRAFO_LLM_MODEL": "none",
        "REG_REPO": args.repo, "REG_PROJ": proj, "REG_STACK_FILE": stack_file,
        "REG_DUMP_AFTER": "120", "PYTHONPATH": args.repo,
    })
    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
        if args.set_blas_threads:
            env[k] = "1"

    uuid = None
    if args.scenario == "search-first":
        seed_out = str(tmp / "seed.json")
        env_seed = dict(env, REG_SEED_OUT=seed_out)
        t0 = time.perf_counter()
        with open(outdir / "seed.log", "w", encoding="utf-8") as sl:
            try:
                r = subprocess.run([sys.executable, "-c", SEED_CODE], env=env_seed, cwd=args.repo,
                                   stdout=sl, stderr=subprocess.STDOUT, timeout=300)
                rc = r.returncode
            except subprocess.TimeoutExpired:
                rc = "TIMEOUT"
        res["seed_s"] = round(time.perf_counter() - t0, 2)
        res["seed_rc"] = rc
        if rc != 0 or not os.path.exists(seed_out):
            res["classe"] = "SEED_FALHOU"
            return
        uuid = json.load(open(seed_out))["uuid"]

    params = StdioServerParameters(command=sys.executable, args=["-u", "-c", SERVER_WRAPPER], env=env, cwd=args.repo)
    t_spawn = time.perf_counter()
    errlog = open(outdir / "server_stderr.log", "w", encoding="utf-8")
    async with stdio_client(params, errlog=errlog) as (rs, ws):
        async with ClientSession(rs, ws) as session:
            await asyncio.wait_for(session.initialize(), timeout=120)
            res["t_initialize_s"] = round(time.perf_counter() - t_spawn, 3)
            await session.list_tools()
            if args.scenario == "mine":
                reg = v2.parse_mcp_result(await session.call_tool("concierge_register", {
                    "project_path": proj, "wing": "geral", "privacy_level": "PUBLIC", "summary": "reg"}), "register")
                uuid = reg["project_uuid"]
                tool, targs = "concierge_mine", {"path": proj, "project_identifier": uuid, "auto_tag": True}
            else:
                tool, targs = "concierge_search", {"query": "calculate rectangle area width height",
                                                  "project_identifier": uuid, "top_k": 5}
            res["tool_critica"] = tool
            t0 = time.perf_counter()
            try:
                call = await asyncio.wait_for(session.call_tool(tool, targs), timeout=args.timeout)
            except asyncio.TimeoutError:
                res["classe"] = "TRAVOU"
                res["t_critica_s"] = round(time.perf_counter() - t0, 2)
                proc = find_server_proc()
                res["server_pid"] = proc.pid if proc else None
                res["cpu_samples"] = sample_cpu(proc, 60, 5)
                kill_tree(proc)
                return
            res["t_critica_s"] = round(time.perf_counter() - t0, 3)
            data = v2.parse_mcp_result(call, tool)
            if tool == "concierge_mine":
                ok = data.get("nodes_created", 0) > 0
                res["detalhe"] = {"nodes_created": data.get("nodes_created")}
            else:
                rl = data.get("results", [])
                ok = len(rl) >= 1
                res["detalhe"] = {"n_results": len(rl), "top_label": rl[0].get("label") if rl else None}
            res["classe"] = "OK" if ok else "ERRO"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--scenario", choices=["search-first", "mine"], required=True)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--set-blas-threads", action="store_true", help="OPENBLAS/OMP_NUM_THREADS=1 (Passo 4)")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    res = {"repo": args.repo, "scenario": args.scenario, "timeout_s": args.timeout,
           "blas_threads_1": args.set_blas_threads, "python": sys.executable,
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "classe": "ERRO"}
    t0 = time.perf_counter()
    try:
        asyncio.run(run(args, res, outdir))
    except Exception as e:  # noqa
        res["classe"] = "ERRO" if res.get("classe") in (None, "ERRO") else res["classe"]
        res["excecao"] = f"{type(e).__name__}: {e}"
    res["total_s"] = round(time.perf_counter() - t0, 2)
    (outdir / "result.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{res['classe']} {args.scenario} {Path(args.repo).name} total={res['total_s']}s", flush=True)
    sys.stdout.flush()
    os._exit(0 if res["classe"] == "OK" else 3)


if __name__ == "__main__":
    main()

