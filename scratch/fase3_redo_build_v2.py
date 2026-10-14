"""
fase3_redo_build_v2.py — Gera audits/backlog-final-v2.md a partir SOMENTE do
inventário independente (scratch/fase3_redo_inventory.json). Não lê nem altera
audits/backlog-final.md. Agrupamento em trilhas por RELATÓRIO DE ORIGEM (critério
mecânico, diferente do v1, que dividiu relatórios entre trilhas manualmente).

Exclui: falsos positivos e duplicatas entre relatórios (ver DUPLICATES).
Uso: python scratch/fase3_redo_build_v2.py
"""
import json
import os
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = json.load(open(os.path.join(ROOT, "scratch", "fase3_redo_inventory.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "audits", "backlog-final-v2.md")

DUPLICATES = {("mock-vs-real-audit.md", 1), ("mock-vs-real-audit.md", 2)}
TRACKS = [
    ("A. Fundação: Schema e Bootstrap", ["schema-oficial-incompleto.md"]),
    ("B. Persistência, Concorrência e Estado (storage, filas, checkpoints, janitor, rate governor)",
     ["duplicacao-serialized-write-queue.md", "storage.md", "core-checkpointer.md",
      "core-background-janitor.md", "core-rate-governor.md"]),
    ("C. Segurança e Governança", ["bypass-governanca-por-session-id.md", "core-security-guard.md"]),
    ("D. Ingestão, Reconciliação e Delta", ["ingestion.md", "core-vector-reconciler.md",
                                            "core-delta-manager.md", "core-alias-tracker.md"]),
    ("E. Telemetria e Dashboard", ["interface-telemetry-api.md", "grafo-dashboard-web.md"]),
    ("F. Runtime Cognitivo e Contratos de Mock", ["agent-and-agents.md", "mock-vs-real-audit.md"]),
]
ORDER = ["MAXIMA", "CRITICA", "GRAVE", "MEDIA", "BAIXA", "OBSERVACAO"]
LABEL = {"MAXIMA": "Máxima", "CRITICA": "Crítica", "GRAVE": "Grave",
         "MEDIA": "Média", "BAIXA": "Baixa", "OBSERVACAO": "Observação"}

out = ["# Backlog Final — Versão 2 (refeita de forma independente)", "",
       "> **Status:** reconstrução independente da Fase 3. Gerada por "
       "`scratch/fase3_redo_build_v2.py` a partir de `scratch/fase3_redo_inventory.json` "
       "(16 relatórios da Fase 1). **Não** foi derivada de `audits/backlog-final.md`, que "
       "permanece intacto como versão v1.",
       "> **Critério de trilha:** por relatório de origem (mecânico). IDs `V2-nnn` são "
       "independentes da numeração BL.",
       "> **Exclusões:** 2 falsos positivos (`core-delta-manager.md` #2, `mock-vs-real-audit.md` "
       "#4) e 2 duplicatas (`mock-vs-real-audit.md` #1 = `core-vector-reconciler.md` #1; "
       "`mock-vs-real-audit.md` #2 = `core-delta-manager.md` #1).", ""]

n = 0
sev_total = Counter()
rows_all = []
for title, reps in TRACKS:
    rows = []
    for rep in reps:
        for r in INV[rep]:
            k = (rep, r["num"])
            if r["status"] == "FALSO_POSITIVO" or k in DUPLICATES:
                continue
            rows.append((rep, r))
    rows.sort(key=lambda x: (ORDER.index(x[1]["sev"]), x[0], x[1]["num"]))
    out += [f"## Trilha {title}", "", "| ID | Severidade | Origem | Arquivo(s) | Mecanismo (resumo) |",
            "|---|---|---|---|---|"]
    for rep, r in rows:
        n += 1
        sev_total[r["sev"]] += 1
        mech = r["mech"].replace("|", "/")
        mech = mech if len(mech) <= 160 else mech[:157] + "..."
        files = r["file"].replace("<br>", ", ").replace("|", "/")[:70]
        out.append(f"| V2-{n:03d} | {LABEL[r['sev']]} | `{rep}` #{r['num']} | {files} | {mech} |")
        rows_all.append(rep)
    out.append("")

out += ["## Totais", "", "| Severidade | Qtde |", "|---|---|"]
for s in ORDER:
    out.append(f"| {LABEL[s]} | {sev_total.get(s, 0)} |")
out.append(f"| **Total** | **{n}** |")
out += ["", "## Candidatos adicionais (itens da Fase 1 do AUDIT_PROTOCOL.md sem relatório em `audits/`)", "",
        "Não numerados e fora dos totais acima: não têm relatório de origem, então não passam pela "
        "mesma exigência de rastreabilidade. Ver `audits/comparacao-fase3.md` §5 para evidências.", ""]
open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"Gerado {os.path.relpath(OUT, ROOT)}: {n} itens")
print({LABEL[s]: sev_total.get(s, 0) for s in ORDER})
