"""
run_regress_matrix.py - driver da matriz commit x cenario x repeticao (Passo 2 / Passo 5).

Cria git worktrees (detached) FORA da arvore principal, em --wt-base, e executa regress_rep.py
alternando commits dentro de cada repeticao (reduz vies de deriva temporal).
Escreve <outdir>/<commit>__<cenario>__rep<N>/result.json e um progress.log.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_REPO = HERE.parent.parent


def ensure_worktree(base: Path, commit: str) -> Path:
    wt = base / commit
    if (wt / "main.py").exists():
        return wt
    base.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "-C", str(MAIN_REPO), "worktree", "add", "--detach", str(wt), commit],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git worktree add falhou para {commit}: {r.stderr}")
    return wt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commits", nargs="+", required=True)
    ap.add_argument("--scenarios", nargs="+", default=["search-first", "mine"])
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--wt-base", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--set-blas-threads", action="store_true")
    a = ap.parse_args()

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    wts = {c: ensure_worktree(Path(a.wt_base), c) for c in a.commits}
    log = open(outdir / "progress.log", "a", encoding="utf-8")

    def say(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    say(f"worktrees: { {c: str(p) for c, p in wts.items()} }")
    for rep in range(1, a.reps + 1):
        for sc in a.scenarios:
            for c in a.commits:
                od = outdir / f"{c}__{sc}__rep{rep}"
                cmd = [sys.executable, str(HERE / "regress_rep.py"), "--repo", str(wts[c]), "--scenario", sc,
                       "--timeout", str(a.timeout), "--outdir", str(od)]
                if a.set_blas_threads:
                    cmd.append("--set-blas-threads")
                say(f"INICIO commit={c} cenario={sc} rep={rep}")
                t0 = time.perf_counter()
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout + 600)
                    say(f"FIM    commit={c} cenario={sc} rep={rep} rc={r.returncode} {time.perf_counter()-t0:.0f}s | {r.stdout.strip()[-160:]}")
                except subprocess.TimeoutExpired:
                    say(f"FIM    commit={c} cenario={sc} rep={rep} DRIVER_TIMEOUT {time.perf_counter()-t0:.0f}s")
    say("MATRIZ COMPLETA")


if __name__ == "__main__":
    main()

