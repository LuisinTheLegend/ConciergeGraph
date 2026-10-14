"""
fase3_redo_compare.py — Compara o refazimento independente da Fase 3 com o
backlog consolidado (audits/backlog-final.md).

Entrada:
  - scratch/fase3_redo_inventory.json (gerado por fase3_redo_inventory.py a
    partir SOMENTE dos 15 relatórios da Fase 1)
  - audits/backlog-final.md (versão consolidada, só lida aqui, nunca escrita)

Verificações:
  A. Cobertura: achados das fontes primárias x itens BL (por relatório,#)
  B. Severidade: fonte primária x BL
  C. Duplicatas entre relatórios (mesmo defeito citado em dois relatórios)
  D. Pertinência de track: heading real do BL x faixas declaradas no fluxograma
  E. Citações arquivo:linha dos BL contra o código atual (arquivo existe e
     linha <= total de linhas)
  F. Itens da Fase 1 declarados no AUDIT_PROTOCOL.md sem relatório em audits/

Uso: python scratch/fase3_redo_compare.py
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = json.load(open(os.path.join(ROOT, "scratch", "fase3_redo_inventory.json"), encoding="utf-8"))
BACKLOG = open(os.path.join(ROOT, "audits", "backlog-final.md"), encoding="utf-8").read()

# Duplicatas entre relatórios: (achado redundante) -> (achado canônico, termo que ambos citam)
DUPLICATES = {
    ("mock-vs-real-audit.md", 1): (("core-vector-reconciler.md", 1), "get_all_ids"),
    ("mock-vs-real-audit.md", 2): (("core-delta-manager.md", 1), "has_structural_change"),
}


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
    if "BAIXA" in u:
        return "BAIXA"
    return "?"


# ---------- fontes primárias ----------
src = {}
for rep, rows in INV.items():
    for r in rows:
        src[(rep, r["num"])] = r

print("=" * 70)
print("C. DUPLICATAS ENTRE RELATÓRIOS (verificação textual)")
for dup, (canon, term) in DUPLICATES.items():
    a, b = src[dup]["mech"], src[canon]["mech"]
    ok = term in a and term in b
    print(f"  {dup[0]} #{dup[1]} ≡ {canon[0]} #{canon[1]} | termo '{term}' em ambos: {ok}")

expected = {}
excluded = []
for k, r in src.items():
    if r["status"] == "FALSO_POSITIVO":
        excluded.append((k, "falso positivo"))
    elif k in DUPLICATES:
        excluded.append((k, f"duplicata de {DUPLICATES[k][0][0]} #{DUPLICATES[k][0][1]}"))
    else:
        expected[k] = r
print(f"\nLinhas de achado nas fontes: {len(src)}")
for k, why in sorted(excluded):
    print(f"  excluído: {k[0]} #{k[1]} ({why})")
obs = [k for k, r in expected.items() if r["sev"] == "OBSERVACAO"]
print(f"Esperado no backlog refeito: {len(expected)} "
      f"({len(expected) - len(obs)} achados + {len(obs)} observação: "
      f"{', '.join(f'{k[0]} #{k[1]}' for k in obs)})")
c = Counter(r["sev"] for r in expected.values())
print("Severidade esperada (fonte primária):", {s: c.get(s, 0) for s in
      ["MAXIMA", "CRITICA", "GRAVE", "MEDIA", "BAIXA", "OBSERVACAO"]})

# ---------- backlog consolidado ----------
track = None
bl = {}
for block in re.split(r"(?m)^(?=### |#### \[)", BACKLOG):
    if block.startswith("### TRACK") or block.startswith("### Componentes"):
        track = block.splitlines()[0].replace("### ", "").strip()
        continue
    if block.startswith("### "):
        track = None
        continue
    m = re.match(r"#### \[(BL-\d+)\]\s*(.*)", block)
    if not m:
        continue
    sev = re.search(r"- \*\*Severidade:\*\*\s*(.+)", block).group(1)
    files = re.search(r"- \*\*Arquivos & Linhas:\*\*\s*(.+)", block).group(1)
    orig = re.search(r"- \*\*Relatório de Origem:\*\*\s*(.+)", block).group(1)
    cm = re.search(r"\[`?(?:audits/)?([\w\-]+\.md)`?\]\([^)]*\)\s*#(\d+)", orig)
    bl[m.group(1)] = {"title": m.group(2), "sev": norm_sev(sev), "files": files,
                      "key": (cm.group(1), int(cm.group(2))), "track": track}

print("\n" + "=" * 70)
print(f"A. COBERTURA — itens BL no backlog: {len(bl)}")
by_key = defaultdict(list)
for i, d in bl.items():
    by_key[d["key"]].append(i)
missing = sorted(set(expected) - set(by_key))
extra = sorted(set(by_key) - set(expected))
dups = {k: v for k, v in by_key.items() if len(v) > 1}
print(f"  Achados esperados ausentes do backlog: {len(missing)}")
for k in missing:
    print(f"    - {k[0]} #{k[1]} [{expected[k]['sev']}] {expected[k]['mech'][:80]}")
print(f"  BL que citam achado não esperado (FP/duplicata/inexistente): {len(extra)}")
for k in extra:
    print(f"    - {by_key[k]} -> {k[0]} #{k[1]}")
print(f"  Achados citados por mais de um BL: {len(dups)}")
for k, v in dups.items():
    print(f"    - {k[0]} #{k[1]}: {v}")

print("\n" + "=" * 70)
print("B. SEVERIDADE — fonte primária x BL")
div = 0
for i, d in sorted(bl.items()):
    s = src.get(d["key"])
    if not s:
        continue
    exp = "BAIXA" if s["sev"] == "OBSERVACAO" else s["sev"]
    if exp != d["sev"]:
        div += 1
        print(f"  {i}: BL={d['sev']} vs fonte={s['sev']} ({d['key'][0]} #{d['key'][1]})")
print(f"  Divergências de severidade: {div}")
print("  Observação catalogada com severidade BAIXA no backlog:",
      [i for i, d in bl.items() if src.get(d['key'], {}).get('sev') == 'OBSERVACAO'])

print("\n" + "=" * 70)
print("D. PERTINÊNCIA DE TRACK (heading real x faixas do fluxograma da Seção 3)")
flow = re.search(r"```mermaid(.*?)```", BACKLOG, re.S).group(1)
declared = {}
for tm in re.finditer(r'T(\d)\["TRACK \d: [^<]*<br/>\(([^)]*)\)', flow):
    ids = set()
    for part in tm.group(2).split(","):
        r = re.findall(r"BL-(\d+)", part)
        if len(r) == 2:
            ids |= {f"BL-{n:03d}" for n in range(int(r[0]), int(r[1]) + 1)}
        elif len(r) == 1:
            ids.add(f"BL-{int(r[0]):03d}")
    declared[int(tm.group(1))] = ids
in_flow = set().union(*declared.values())
not_in_flow = sorted(set(bl) - in_flow)
print(f"  BL fora de qualquer faixa do fluxograma: {len(not_in_flow)}")
print(f"    {not_in_flow}")
mism = []
for i, d in sorted(bl.items()):
    real = d["track"] or "(sem track)"
    tnum = re.match(r"TRACK (\d)", real)
    decl = [t for t, s in declared.items() if i in s]
    if tnum and decl and int(tnum.group(1)) not in decl:
        mism.append((i, real[:40], decl))
print(f"  BL cujo heading real diverge da faixa declarada: {len(mism)}")
for m_ in mism:
    print(f"    {m_[0]}: heading '{m_[1]}' vs fluxograma T{m_[2]}")
by_track = defaultdict(list)
for i, d in sorted(bl.items()):
    by_track[d["track"] or "(sem track)"].append(i)
for t, ids in by_track.items():
    print(f"  [{len(ids):2d}] {t[:60]}")

print("\n" + "=" * 70)
print("E. CITAÇÕES arquivo:linha DOS BL CONTRA O CÓDIGO ATUAL")
link_re = re.compile(r"file:///c:/Nexus-Memory/GrafoConcierge/([^)#\s]+)(?:#L(\d+))?", re.I)
bad, checked = [], 0
line_cache = {}
for i, d in sorted(bl.items()):
    for path, ln in link_re.findall(d["files"]):
        full = os.path.join(ROOT, path.replace("/", os.sep))
        checked += 1
        if not os.path.exists(full):
            if path.startswith("grafo-dashboard-web/") or path.startswith("grafo-dashboard-web\\") or path == "grafo-dashboard-web":
                bad.append((i, path, ln, "não verificável (diretório ignorado pelo git)"))
            else:
                bad.append((i, path, ln, "arquivo inexistente"))
            continue
        if ln and os.path.isfile(full):
            if full not in line_cache:
                with open(full, encoding="utf-8", errors="replace") as f:
                    line_cache[full] = sum(1 for _ in f)
            if int(ln) > line_cache[full]:
                bad.append((i, path, ln, f"linha > total ({line_cache[full]})"))
print(f"  Links verificados: {checked} | problemas: {len(bad)}")
for b in bad:
    print(f"    {b[0]}: {b[1]}#L{b[2]} -> {b[3]}")

print("\n" + "=" * 70)
print("F. ITENS DA FASE 1 DECLARADOS NO AUDIT_PROTOCOL.md SEM RELATÓRIO EM audits/")
declared_items = ["core/alias_tracker.py", "interface/queue_writer.py",
                  "core/parser_factory.py", "core/gating_interceptor.py",
                  "core/hsm_engine.py", "interface/mcp_server.py"]
reports = set(INV)
for p in declared_items:
    slug = p.replace("/", "-").replace(".py", "").replace("_", "-") + ".md"
    has_report = slug in reports
    cited = [i for i, d in bl.items() if p in d["files"]]
    print(f"  {p:28s} relatório próprio: {has_report!s:5s} | citado em Arquivos&Linhas de: "
          f"{cited if cited else 'nenhum BL'}")
