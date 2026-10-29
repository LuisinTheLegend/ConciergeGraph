# scratch/evidencia_4_2f/run_passo4f_regress.py
"""
Passo 4f: Regressao dos commits de referencia (7db9f7d e dd92d35).
3 repeticoes cada, cenarios search-first e mine.
Salva em scratch/evidencia_4_2f/regressao_commits/ e gera tabela_passo4f.txt.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = REPO_ROOT / "scratch" / "evidencia_4_2e"
OUTDIR = REPO_ROOT / "scratch" / "evidencia_4_2f" / "regressao_commits"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = REPO_ROOT / "scratch" / "evidencia_4_2f" / "tabela_passo4f.txt"
WT_BASE = Path(r"C:\Nexus-Memory\_wt_4_2e")

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "driver.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run():
    log("Iniciando PASSO 4f: Controle de Regressão em 7db9f7d e dd92d35 (3 repetições)")
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "run_regress_matrix.py"),
        "--commits", "7db9f7d", "dd92d35",
        "--scenarios", "search-first", "mine",
        "--reps", "3",
        "--timeout", "180.0",
        "--wt-base", str(WT_BASE),
        "--outdir", str(OUTDIR),
    ]
    log(f"Comando: {' '.join(cmd)}")
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    (OUTDIR / "matrix_stdout.log").write_text(p.stdout, encoding="utf-8")
    (OUTDIR / "matrix_stderr.log").write_text(p.stderr, encoding="utf-8")
    log("Execução da matriz concluída. Gerando tabela...")

    # Tabulação dos resultados
    results = []
    for pj in sorted(OUTDIR.glob("*__*__rep*/result.json")):
        try:
            data = json.load(open(pj, encoding="utf-8"))
            parts = pj.parent.name.split("__")
            results.append({
                "commit": parts[0],
                "scenario": parts[1],
                "rep": int(parts[2].replace("rep", "")),
                "classe": data.get("classe"),
                "t_init": data.get("t_initialize_s"),
                "t_crit": data.get("t_critica_s"),
                "total": data.get("total_s"),
                "server_pid": data.get("server_pid"),
                "cpu_samples": data.get("cpu_samples", []),
            })
        except Exception as e:
            log(f"Erro lendo {pj}: {e}")

    results.sort(key=lambda x: (x["scenario"], x["commit"], x["rep"]))

    lines = []
    lines.append("=== TABELA PASSO 4f: REGRESSÃO DOS COMMITS DE REFERÊNCIA ===")
    lines.append(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("Commits: 7db9f7d (pré-4.2d) vs dd92d35 (HEAD anterior, sem desacoplamento)")
    lines.append("Repetições: n=3 por cenário, Timeout: 180s")
    lines.append("")
    lines.append(f"{'Commit':<10} | {'Cenário':<13} | {'Rep':<4} | {'Status':<8} | {'t_init(s)':<10} | {'t_crit(s)':<10} | {'Total(s)':<10} | Detalhes")
    lines.append("-" * 95)
    for r in results:
        t_init = f"{r['t_init']:.2f}" if r['t_init'] is not None else "-"
        t_crit = f"{r['t_crit']:.2f}" if r['t_crit'] is not None else "-"
        tot = f"{r['total']:.2f}" if r['total'] is not None else "-"
        cpu_m = f"{sum(r['cpu_samples'])/len(r['cpu_samples']):.1f}%" if r['cpu_samples'] else "N/A"
        det = f"TRAVOU (CPU={cpu_m})" if r['classe'] == "TRAVOU" else "OK"
        lines.append(f"{r['commit']:<10} | {r['scenario']:<13} | {r['rep']:<4} | {r['classe']:<8} | {t_init:<10} | {t_crit:<10} | {tot:<10} | {det}")
    lines.append("-" * 95)

    lines.append("\nRESUMO ESTATÍSTICO:")
    lines.append("-" * 50)
    for sc in ("search-first", "mine"):
        for c in ("7db9f7d", "dd92d35"):
            sub = [r for r in results if r["scenario"] == sc and r["commit"] == c]
            oks = sum(1 for r in sub if r["classe"] == "OK")
            travou = sum(1 for r in sub if r["classe"] == "TRAVOU")
            lines.append(f"Commit {c:<8} | Cenário {sc:<12} | OK: {oks}/3 | TRAVOU: {travou}/3")
    lines.append("=" * 95)

    out_text = "\n".join(lines) + "\n"
    TABLE_OUT.write_text(out_text, encoding="utf-8")
    print("\n" + out_text)

if __name__ == "__main__":
    run()

