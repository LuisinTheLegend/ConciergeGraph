"""
run_passo4.py - Repete 3 vezes com OPENBLAS_NUM_THREADS=1 e OMP_NUM_THREADS=1 no caso que trava.
Caso selecionado: commit dd92d35, cenario mine, timeout 180s.
Salva em scratch/evidencia_4_2e/passo4_blas/ e gera tabela_passo4.txt.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT_DD = Path(r"C:\Nexus-Memory\_wt_4_2e\dd92d35")
OUTDIR = HERE / "passo4_blas"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_passo4.txt"

results = []
log_file = open(OUTDIR / "progress.log", "a", encoding="utf-8")

def say(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    log_file.write(line + "\n")
    log_file.flush()

say("INICIANDO PASSO 4 — TESTE COM OPENBLAS_NUM_THREADS=1 E OMP_NUM_THREADS=1")

for rep in range(1, 4):
    od = OUTDIR / f"dd92d35__mine__blas1__rep{rep}"
    cmd = [
        sys.executable,
        str(HERE / "regress_rep.py"),
        "--repo", str(WT_DD),
        "--scenario", "mine",
        "--timeout", "180",
        "--outdir", str(od),
        "--set-blas-threads",
    ]
    say(f"INICIO rep={rep} com BLAS/OMP threads=1")
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    res_json_path = od / "result.json"
    if res_json_path.exists():
        d = json.load(open(res_json_path, encoding="utf-8"))
        results.append({
            "rep": rep,
            "classe": d.get("classe"),
            "t_init": d.get("t_initialize_s"),
            "t_crit": d.get("t_critica_s"),
            "total_s": d.get("total_s"),
            "cpu_samples_count": len(d.get("cpu_samples", [])),
        })
    say(f"FIM    rep={rep} rc={r.returncode} em {dt:.1f}s | {r.stdout.strip()[-120:]}")

# Gera tabela
lines = []
lines.append("=" * 80)
lines.append("TABELA DO PASSO 4 — IMPACTO DE OPENBLAS_NUM_THREADS=1 E OMP_NUM_THREADS=1")
lines.append("Commit: dd92d35 (HEAD) | Cenário: mine | Repetições: 3 | Timeout: 180s")
lines.append("=" * 80)
lines.append(f"{'Rep':<4} | {'Status':<8} | {'t_init (s)':<11} | {'t_crit (s)':<11} | {'Total (s)':<10} | Detalhes")
lines.append("-" * 80)
for r in results:
    ti = f"{r['t_init']:.2f}" if r['t_init'] is not None else "-"
    tc = f"{r['t_crit']:.2f}" if r['t_crit'] is not None else "-"
    tot = f"{r['total_s']:.2f}" if r['total_s'] is not None else "-"
    det = f"CPU_samples={r['cpu_samples_count']}" if r['classe'] == "TRAVOU" else "OK"
    lines.append(f"{r['rep']:<4} | {r['classe']:<8} | {ti:<11} | {tc:<11} | {tot:<10} | {det}")
lines.append("=" * 80)

content = "\n".join(lines) + "\n"
TABLE_OUT.write_text(content, encoding="utf-8")
print(content)

