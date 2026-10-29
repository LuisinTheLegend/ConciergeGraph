"""
tabulate_regress.py - Lê os result.json da matriz do Passo 2 e gera a tabela formatada.
Salva em scratch/evidencia_4_2e/tabela_passo2.txt.
"""
import glob
import json
import os
from pathlib import Path

BASE = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e\regress")
OUT = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e\tabela_passo2.txt")

results = []
for p in sorted(BASE.glob("*__*__rep*/result.json")):
    try:
        data = json.load(open(p, encoding="utf-8"))
        parts = p.parent.name.split("__")
        commit = parts[0]
        scenario = parts[1]
        rep = parts[2].replace("rep", "")
        results.append({
            "commit": commit,
            "scenario": scenario,
            "rep": int(rep),
            "classe": data.get("classe"),
            "t_initialize_s": data.get("t_initialize_s"),
            "t_critica_s": data.get("t_critica_s"),
            "seed_s": data.get("seed_s"),
            "total_s": data.get("total_s"),
            "server_pid": data.get("server_pid"),
            "cpu_samples_count": len(data.get("cpu_samples", [])),
        })
    except Exception as e:
        print(f"Erro lendo {p}: {e}")

lines = []
lines.append("=" * 95)
lines.append("TABELA DO PASSO 2 — CONTROLE DE REGRESSÃO: 7db9f7d (pré-4.2d) vs dd92d35 (HEAD)")
lines.append("=" * 95)
lines.append(f"{'Commit':<10} | {'Cenário':<13} | {'Rep':<4} | {'Status':<8} | {'t_init (s)':<11} | {'t_crit (s)':<11} | {'Total (s)':<10} | Detalhes")
lines.append("-" * 95)

results.sort(key=lambda x: (x["scenario"], x["commit"], x["rep"]))

for r in results:
    t_init = f"{r['t_initialize_s']:.2f}" if r['t_initialize_s'] is not None else "-"
    t_crit = f"{r['t_critica_s']:.2f}" if r['t_critica_s'] is not None else "-"
    tot = f"{r['total_s']:.2f}" if r['total_s'] is not None else "-"
    det = f"PID={r['server_pid']}, CPU_samples={r['cpu_samples_count']}" if r['classe'] == "TRAVOU" else "OK"
    lines.append(f"{r['commit']:<10} | {r['scenario']:<13} | {r['rep']:<4} | {r['classe']:<8} | {t_init:<11} | {t_crit:<11} | {tot:<10} | {det}")

lines.append("=" * 95)

# Resumo agregado
lines.append("\nRESUMO ESTATÍSTICO:")
lines.append("-" * 50)
for sc in ("search-first", "mine"):
    for c in ("7db9f7d", "dd92d35"):
        subset = [r for r in results if r["scenario"] == sc and r["commit"] == c]
        oks = sum(1 for r in subset if r["classe"] == "OK")
        travou = sum(1 for r in subset if r["classe"] == "TRAVOU")
        lines.append(f"Commit {c:<8} | Cenário {sc:<12} | OK: {oks}/5 | TRAVOU: {travou}/5")
lines.append("=" * 95)

content = "\n".join(lines) + "\n"
OUT.write_text(content, encoding="utf-8")
print(content)

