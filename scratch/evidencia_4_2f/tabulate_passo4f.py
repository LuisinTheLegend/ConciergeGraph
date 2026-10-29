# scratch/evidencia_4_2f/tabulate_passo4f.py
import json
from pathlib import Path

OUTDIR = Path("scratch/evidencia_4_2f/regressao_commits")
TABLE_OUT = Path("scratch/evidencia_4_2f/tabela_passo4f.txt")

results = []
for pj in sorted(OUTDIR.glob("*__*__rep*/result.json")):
    try:
        data = json.load(open(pj, encoding="utf-8"))
        parts = pj.parent.name.split("__")
        raw_cpu = data.get("cpu_samples", [])
        cpu_vals = [s.get("cpu_pct_1core", 0.0) if isinstance(s, dict) else float(s) for s in raw_cpu]
        results.append({
            "commit": parts[0],
            "scenario": parts[1],
            "rep": int(parts[2].replace("rep", "")),
            "classe": data.get("classe"),
            "t_init": data.get("t_initialize_s"),
            "t_crit": data.get("t_critica_s"),
            "total": data.get("total_s"),
            "server_pid": data.get("server_pid"),
            "cpu_vals": cpu_vals,
        })
    except Exception as e:
        print("Erro:", e)

results.sort(key=lambda x: (x["scenario"], x["commit"], x["rep"]))

lines = []
lines.append("=== TABELA PASSO 4f: REGRESSAO DOS COMMITS DE REFERENCIA ===")
lines.append("Commits: 7db9f7d (pre-4.2d) vs dd92d35 (HEAD anterior, sem desacoplamento)")
lines.append("Repeticoes: n=3 por cenario, Timeout: 180s")
lines.append("")
lines.append(f"{'Commit':<10} | {'Cenario':<13} | {'Rep':<4} | {'Status':<8} | {'t_init(s)':<10} | {'t_crit(s)':<10} | {'Total(s)':<10} | Detalhes")
lines.append("-" * 95)
for r in results:
    t_init = f"{r['t_init']:.2f}" if r['t_init'] is not None else "-"
    t_crit = f"{r['t_crit']:.2f}" if r['t_crit'] is not None else "-"
    tot = f"{r['total']:.2f}" if r['total'] is not None else "-"
    cpu_m = f"{sum(r['cpu_vals'])/len(r['cpu_vals']):.1f}%" if r['cpu_vals'] else "N/A"
    det = f"TRAVOU (CPU={cpu_m})" if r['classe'] == "TRAVOU" else "OK"
    lines.append(f"{r['commit']:<10} | {r['scenario']:<13} | {r['rep']:<4} | {r['classe']:<8} | {t_init:<10} | {t_crit:<10} | {tot:<10} | {det}")
lines.append("-" * 95)

lines.append("\nRESUMO ESTATISTICO:")
lines.append("-" * 50)
for sc in ("search-first", "mine"):
    for c in ("7db9f7d", "dd92d35"):
        sub = [r for r in results if r["scenario"] == sc and r["commit"] == c]
        oks = sum(1 for r in sub if r["classe"] == "OK")
        travou = sum(1 for r in sub if r["classe"] == "TRAVOU")
        lines.append(f"Commit {c:<8} | Cenario {sc:<12} | OK: {oks}/3 | TRAVOU: {travou}/3")
lines.append("=" * 95)

out_text = "\n".join(lines) + "\n"
TABLE_OUT.write_text(out_text, encoding="utf-8")
print(out_text)
