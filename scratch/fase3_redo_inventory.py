"""
fase3_redo_inventory.py — Inventário INDEPENDENTE dos achados da Fase 1.

Refaz a Fase 3 a partir das fontes primárias (os 15 relatórios em audits/*.md),
sem ler audits/backlog-final.md. Para cada relatório, localiza a(s) tabela(s)
de achados (cabeçalho com coluna '#'/'ID' e coluna 'severidade') e extrai cada
linha com: número, severidade (normalizada), status, arquivo(s), linha(s) e
mecanismo resumido.

Saídas:
  - stdout: tabela legível + totais por severidade e por status
  - scratch/fase3_redo_inventory.json: inventário estruturado (para comparação)

Uso: python scratch/fase3_redo_inventory.py
"""
import json
import os
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDITS = os.path.join(ROOT, "audits")
EXCLUDE = {"backlog-final.md", "backlog-final-v2.md", "cruzamento-modulos.md",
           "fora-de-escopo.md", "comparacao-fase3.md"}
OUT_JSON = os.path.join(ROOT, "scratch", "fase3_redo_inventory.json")


def norm_sev(s):
    u = s.upper()
    if "MÁXIMA" in u or "MAXIMA" in u:
        return "MAXIMA"
    if "CRÍTIC" in u or "CRITIC" in u:
        return "CRITICA"
    if "GRAVE" in u or "ALTA" in u:
        return "GRAVE"
    if "MÉDI" in u or "MEDI" in u:
        return "MEDIA"
    if "BAIXA" in u or "BAIXO" in u:
        return "BAIXA"
    if "OBSERVA" in u:
        return "OBSERVACAO"
    if "FALSO" in u or "N/A" in u:
        return "N/A"
    return "?"


def norm_status(s):
    u = s.upper()
    if "FALSO POSITIVO" in u or "FALSO-POSITIVO" in u:
        return "FALSO_POSITIVO"
    if "HIPÓTESE" in u or "HIPOTESE" in u:
        return "HIPOTESE"
    if "OBSERVA" in u:
        return "OBSERVACAO"
    if "CONFIRMAD" in u:
        return "CONFIRMADO"
    return "?"


def cells(line):
    return [c.strip() for c in line.strip().split("|")[1:-1]]


def strip_md(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.replace("**", "").replace("`", "").strip()


def find_col(header, *keys):
    for i, h in enumerate(header):
        hl = h.lower()
        if any(k in hl for k in keys):
            return i
    return None


def parse_report(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    rows = []
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("|"):
            h = [strip_md(c) for c in cells(l)]
            if h and h[0] in ("#", "ID") and find_col(h, "severidade") is not None:
                c_sev = find_col(h, "severidade")
                c_status = find_col(h, "status")
                c_file = find_col(h, "arquivo", "módulos", "modulos")
                c_line = find_col(h, "linha")
                c_mech = find_col(h, "mecanismo", "resumo")
                i += 2  # pula cabeçalho e separador
                while i < len(lines) and lines[i].strip().startswith("|"):
                    c = cells(lines[i])
                    num = re.sub(r"[^\d]", "", strip_md(c[0])) if c else ""
                    if num:
                        get = lambda k: strip_md(c[k]) if k is not None and k < len(c) else ""
                        rows.append({
                            "num": int(num),
                            "sev_raw": get(c_sev),
                            "sev": norm_sev(get(c_sev)),
                            "status_raw": get(c_status),
                            "status": norm_status(get(c_status)) if c_status is not None else "?",
                            "file": get(c_file),
                            "line": get(c_line) if c_line != c_file else "",
                            "mech": get(c_mech),
                        })
                    i += 1
                continue
        i += 1
    return rows


def main():
    inventory = {}
    for name in sorted(os.listdir(AUDITS)):
        if not name.endswith(".md") or name in EXCLUDE:
            continue
        inventory[name] = parse_report(os.path.join(AUDITS, name))

    print(f"Relatórios lidos: {len(inventory)}")
    sev_c, st_c = Counter(), Counter()
    for rep, rows in inventory.items():
        print(f"\n## {rep} ({len(rows)} linhas de achado)")
        if not rows:
            print("  [AVISO] nenhuma tabela de achados reconhecida")
        seen = Counter(r["num"] for r in rows)
        for n, k in seen.items():
            if k > 1:
                print(f"  [AVISO] #{n} aparece {k} vezes")
        for r in rows:
            sev_c[r["sev"]] += 1
            st_c[r["status"]] += 1
            print(f"  #{r['num']:<2} {r['sev']:<10} {r['status']:<14} "
                  f"{r['file'][:45]:<45} | {r['mech'][:90]}")

    total = sum(len(v) for v in inventory.values())
    print("\n" + "=" * 70)
    print(f"TOTAL DE LINHAS DE ACHADO NAS FONTES PRIMÁRIAS: {total}")
    print("Por severidade:", dict(sev_c))
    print("Por status:", dict(st_c))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=1)
    print(f"Inventário salvo em {os.path.relpath(OUT_JSON, ROOT)}")


if __name__ == "__main__":
    main()
