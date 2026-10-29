"""
tabulate_minimal.py - Lê os resultados do Passo 3 e gera a tabela formatada.
Salva em scratch/evidencia_4_2e/tabela_passo3.txt.
"""
import glob
import json
from pathlib import Path

BASE = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e\minimal_repro")
OUT = Path(r"c:\Nexus-Memory\GrafoConcierge\scratch\evidencia_4_2e\tabela_passo3.txt")

results = []
for p in sorted(BASE.glob("*__*__rep*.json")):
    try:
        data = json.load(open(p, encoding="utf-8"))
        parts = p.stem.split("__")
        venv_name = parts[0]
        var_name = parts[1]
        rep = parts[2].replace("rep", "")
        classe = data.get("classe")
        if classe == "ERRO" and data.get("total_s", 0) >= 180.0:
            classe = "TRAVOU"
        results.append({
            "venv": venv_name,
            "variant": var_name,
            "rep": int(rep),
            "classe": classe,
            "t_init": data.get("t_init"),
            "t_call": data.get("t_call"),
            "total_s": data.get("total_s"),
        })
    except Exception as e:
        print(f"Erro lendo {p}: {e}")

lines = []
lines.append("=" * 85)
lines.append("TABELA DO PASSO 3 — REPRODUÇÃO MÍNIMA ISOLADA (SEM O CONCIERGE)")
lines.append("=" * 85)
lines.append(f"{'Venv (MCP)':<12} | {'Variante':<15} | {'Rep':<4} | {'Status':<8} | {'t_init (s)':<11} | {'t_call (s)':<11} | {'Total (s)'}")
lines.append("-" * 85)

results.sort(key=lambda x: (x["venv"], x["variant"], x["rep"]))

for r in results:
    ti = f"{r['t_init']:.2f}" if r['t_init'] is not None else "-"
    tc = f"{r['t_call']:.2f}" if r['t_call'] is not None else "-"
    tot = f"{r['total_s']:.2f}" if r['total_s'] is not None else "-"
    lines.append(f"{r['venv']:<12} | {r['variant']:<15} | {r['rep']:<4} | {r['classe']:<8} | {ti:<11} | {tc:<11} | {tot}")

lines.append("=" * 85)
lines.append("\nRESUMO ESTATÍSTICO:")
lines.append("-" * 65)
for v in ("mcp127", "mcp130"):
    for var in ("a_sync_scipy", "b_sync_st", "c_async_tot", "d_preimport"):
        subset = [r for r in results if r["venv"] == v and r["variant"] == var]
        oks = sum(1 for r in subset if r["classe"] == "OK")
        travou = sum(1 for r in subset if r["classe"] == "TRAVOU")
        lines.append(f"Venv {v:<7} | Variante {var:<15} | OK: {oks}/5 | TRAVOU: {travou}/5")
lines.append("=" * 85)

content = "\n".join(lines) + "\n"
OUT.write_text(content, encoding="utf-8")
print(content)
