"""
bridge_79_87.py — Reconstrói, por script, a ponte 79 → 84 → 87 do backlog-final.

Lê `audits/backlog-final.md` diretamente do git em três versões:
  - 1535c79 (79 achados, formato tabela por seção de severidade)
  - 503aa6f (84 itens, formato '#### [BL-xxx]')
  - HEAD    (87 itens, formato '#### [BL-xxx]')

Os itens são casados por ACHADO (relatório, #número), não pelo ID BL, porque a
numeração BL mudou entre as versões. Na versão de 79, seis citações estavam
trocadas e são corrigidas antes do casamento (ver CORRECOES_79).

Uso: python scratch/bridge_79_87.py
"""
import re
import subprocess
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PATH = "audits/backlog-final.md"
SEVS = ["MAXIMA", "CRITICA", "GRAVE", "MEDIA", "BAIXA"]

# Citações corretas para os IDs da versão de 79 (commit 1535c79).
CORRECOES_79 = {
    "BL-036": ("storage.md", 4),
    "BL-063": ("storage.md", 3),
    "BL-061": ("core-delta-manager.md", 6),
    "BL-076": ("schema-oficial-incompleto.md", 5),
    "BL-018": ("interface-telemetry-api.md", 2),
    "BL-002": ("schema-oficial-incompleto.md", 4),
}

CITE_RE = re.compile(r"\[`?(?:audits/)?([\w\-]+\.md)`?\]\([^)]*\)\s*#(\d+)")


def git_show(rev):
    out = subprocess.run(
        ["git", "show", f"{rev}:{PATH}"],
        capture_output=True, check=True,
    ).stdout
    return out.decode("utf-8")


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
    return None


def parse_79(text):
    """Formato tabela: severidade vem do cabeçalho '## ' corrente."""
    items = {}
    sev = None
    for line in text.splitlines():
        if line.startswith("## "):
            sev = norm_sev(line)
            continue
        m = re.match(r"\|\s*\*\*(BL-\d+)\*\*\s*\|", line)
        if not m or sev is None:
            continue
        bl = m.group(1)
        cites = CITE_RE.findall(line)
        if bl in CORRECOES_79:
            rep, num = CORRECOES_79[bl]
            original = f"{cites[0][0]} #{cites[0][1]}" if cites else "(sem citação)"
            print(f"  [correção 79] {bl}: {original} -> {rep} #{num}")
        elif not cites:
            print(f"  [AVISO] {bl} sem citação na versão de 79")
            continue
        else:
            if len(cites) > 1:
                print(f"  [AVISO] {bl} tem {len(cites)} citações; usando a primeira")
            rep, num = cites[0][0], int(cites[0][1])
        items[bl] = ((rep, int(num)), sev)
    return items


def parse_blocks(text):
    """Formato '#### [BL-xxx] título' + '- **Severidade:**' + '- **Relatório de Origem:**'."""
    items = {}
    blocks = re.split(r"(?m)^#### \[", text)[1:]
    for b in blocks:
        m = re.match(r"(BL-\d+)\]", b)
        if not m:
            continue
        bl = m.group(1)
        ms = re.search(r"- \*\*Severidade:\*\*\s*(.+)", b)
        mr = re.search(r"- \*\*Relatório de Origem:\*\*\s*(.+)", b)
        if not ms or not mr:
            print(f"  [AVISO] {bl} sem severidade ou origem")
            continue
        cites = CITE_RE.findall(mr.group(1))
        if not cites:
            print(f"  [AVISO] {bl} origem não reconhecida: {mr.group(1)[:80]}")
            continue
        items[bl] = ((cites[0][0], int(cites[0][1])), norm_sev(ms.group(1)))
    return items


def by_achado(items, label):
    d = {}
    for bl, (key, sev) in items.items():
        if key in d:
            print(f"  [AVISO] {label}: achado {key[0]} #{key[1]} duplicado ({d[key][0]} e {bl})")
        d[key] = (bl, sev)
    return d


def totals(d):
    c = Counter(sev for _, sev in d.values())
    return [c.get(s, 0) for s in SEVS]


def fmt_tot(t):
    return " | ".join(f"{s}: {n}" for s, n in zip(SEVS, t)) + f" | TOTAL: {sum(t)}"


def stage(old, new, old_label, new_label):
    print(f"\n=== ETAPA {old_label} -> {new_label} ===")
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k][1] != new[k][1])

    print(f"Achados adicionados ({len(added)}):")
    for k in added:
        print(f"  + {k[0]} #{k[1]} [{new[k][1]}] ({new_label}: {new[k][0]})")
    print(f"Achados removidos ({len(removed)}):")
    for k in removed:
        print(f"  - {k[0]} #{k[1]} [{old[k][1]}] ({old_label}: {old[k][0]})")
    print(f"Mudanças de severidade ({len(changed)}):")
    for k in changed:
        print(f"  ~ {k[0]} #{k[1]}: {old[k][1]} -> {new[k][1]} "
              f"({old_label}: {old[k][0]}, {new_label}: {new[k][0]})")

    to, tn = totals(old), totals(new)
    print(f"Totais {old_label}: {fmt_tot(to)}")
    print(f"Totais {new_label}: {fmt_tot(tn)}")
    print("Delta por severidade (adições / mudanças de severidade / total):")
    for i, s in enumerate(SEVS):
        add = sum(1 for k in added if new[k][1] == s) - sum(1 for k in removed if old[k][1] == s)
        chg = sum(1 for k in changed if new[k][1] == s) - sum(1 for k in changed if old[k][1] == s)
        ok = "OK" if add + chg == tn[i] - to[i] else "NÃO FECHA"
        print(f"  {s:8s}: {add:+d} / {chg:+d} / {tn[i] - to[i]:+d}  [{ok}]")


def main():
    print("Lendo versões via git show...")
    print("Versão 79 (1535c79):")
    v79 = by_achado(parse_79(git_show("1535c79")), "79")
    print("Versão 84 (503aa6f):")
    v84 = by_achado(parse_blocks(git_show("503aa6f")), "84")
    print("Versão 87 (HEAD):")
    v87 = by_achado(parse_blocks(git_show("HEAD")), "87")
    print(f"Achados distintos: 79-ver={len(v79)} | 84-ver={len(v84)} | 87-ver={len(v87)}")

    print("\n=== CITAÇÕES CORRIGIDAS DA VERSÃO 79 -> ID NAS VERSÕES 84 E 87 ===")
    for bl79, key in sorted(CORRECOES_79.items()):
        a84 = v84.get(key, ("ausente", "-"))
        a87 = v87.get(key, ("ausente", "-"))
        print(f"  79:{bl79} [{v79[key][1]}] = {key[0]} #{key[1]} -> "
              f"84:{a84[0]} [{a84[1]}] -> 87:{a87[0]} [{a87[1]}]")

    stage(v79, v84, "79", "84")
    stage(v84, v87, "84", "87")
    stage(v79, v87, "79", "87")


if __name__ == "__main__":
    main()
