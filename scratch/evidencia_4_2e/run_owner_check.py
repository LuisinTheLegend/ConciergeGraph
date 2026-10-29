"""
run_owner_check.py - Script autônomo para execução manual pelo DONO no PowerShell.
Executa o teste essencial: search-first em dd92d35 (HEAD) e em 7db9f7d (pré-4.2d),
com n=3 repetições e timeout de 180s.
Escreve o resultado em scratch/evidencia_4_2e/resultado_dono.json e resultado_dono.txt.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EV_DIR = REPO_ROOT / "scratch" / "evidencia_4_2e"
WT_BASE = Path(r"C:\Nexus-Memory\_wt_4_2e")
OUT_JSON = EV_DIR / "resultado_dono.json"
OUT_TXT = EV_DIR / "resultado_dono.txt"

COMMITS = ["7db9f7d", "dd92d35"]
SCENARIO = "search-first"
REPS = 3
TIMEOUT = 180.0

def ensure_worktree(commit: str) -> Path:
    wt = WT_BASE / commit
    if not (wt / "main.py").exists():
        WT_BASE.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(wt), commit],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"Erro criando worktree para {commit}: {r.stderr}")
    return wt

def main():
    print("=" * 80)
    print("EXECUÇÃO DO DONO (SEM AGENTE) — VALIDAÇÃO DE REGRESSÃO NO TERMINAL INTERATIVO")
    print(f"Python: {sys.executable}")
    print(f"Data:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    wts = {c: ensure_worktree(c) for c in COMMITS}
    results = []

    for rep in range(1, REPS + 1):
        for c in COMMITS:
            od = EV_DIR / "owner_runs" / f"{c}__{SCENARIO}__rep{rep}"
            od.mkdir(parents=True, exist_ok=True)
            print(f"[{time.strftime('%H:%M:%S')}] Executando rep={rep} commit={c} ({SCENARIO})...", flush=True)
            cmd = [
                sys.executable,
                str(EV_DIR / "regress_rep.py"),
                "--repo", str(wts[c]),
                "--scenario", SCENARIO,
                "--timeout", str(TIMEOUT),
                "--outdir", str(od),
            ]
            t0 = time.perf_counter()
            r = subprocess.run(cmd, capture_output=True, text=True)
            dt = time.perf_counter() - t0
            res_file = od / "result.json"
            if res_file.exists():
                d = json.load(open(res_file, encoding="utf-8"))
                classe = d.get("classe")
                t_init = d.get("t_initialize_s")
                t_crit = d.get("t_critica_s")
            else:
                classe = "ERRO"
                t_init, t_crit = None, None
            
            results.append({
                "commit": c,
                "rep": rep,
                "classe": classe,
                "t_init": t_init,
                "t_crit": t_crit,
                "dt_total": round(dt, 2),
            })
            print(f"[{time.strftime('%H:%M:%S')}] Concluído: {classe} em {dt:.1f}s (t_init={t_init}s, t_crit={t_crit}s)\n", flush=True)

    # Salva JSON
    payload = {
        "executor": "DONO (terminal interativo)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Formata Tabela
    lines = []
    lines.append("=" * 80)
    lines.append("RESULTADO DA EXECUÇÃO DO DONO (POWERShell INTERATIVO)")
    lines.append("=" * 80)
    lines.append(f"{'Commit':<10} | {'Rep':<4} | {'Status':<8} | {'t_init (s)':<11} | {'t_crit (s)':<11} | {'Total (s)'}")
    lines.append("-" * 80)
    for r in results:
        ti = f"{r['t_init']:.2f}" if r['t_init'] is not None else "-"
        tc = f"{r['t_crit']:.2f}" if r['t_crit'] is not None else "-"
        lines.append(f"{r['commit']:<10} | {r['rep']:<4} | {r['classe']:<8} | {ti:<11} | {tc:<11} | {r['dt_total']:.2f}")
    lines.append("=" * 80)
    
    txt_content = "\n".join(lines) + "\n"
    OUT_TXT.write_text(txt_content, encoding="utf-8")
    print("\n" + txt_content)
    print(f"Resultados gravados em:\n  - {OUT_JSON}\n  - {OUT_TXT}")

if __name__ == "__main__":
    main()

