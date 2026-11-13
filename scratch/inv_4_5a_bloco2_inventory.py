"""
Bloco 2 (Inventário por módulo) - PEDIDO 4.5a
Coleta fatos objetivos para cada módulo não alcançável em tempo de carga (UNREACHABLE +
REACHABLE_ANNOTATION_ONLY_RUNTIME + REACHABLE_PEP562_LAZY):
  - LOC
  - Importadores em código de produção (arquivo:linha)
  - Arquivos de teste que importam o módulo, número exato de testes coletados, e se misturam módulos vivos
  - Menções em README.md, README.pt-BR.md, CHANGELOG.md, AGENTS.md, ACTIVE_SDD.md, docs-grafo-concierge/, pyproject.toml
    (e menções em walkthrough.md listadas separadamente apenas como referência documental)
  - Símbolos definidos no módulo dormente para subsidiar classificação (i)/(ii)/(iii).
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "scratch" / "evidencia_4_5a"


def get_tracked_py_files() -> list[Path]:
    res = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [ROOT / p.strip() for p in res.stdout.splitlines() if p.strip()]


def collect_pytest_nodes() -> dict[str, list[str]]:
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    (EVID / "pytest_collect_raw.txt").write_text(res.stdout, encoding="utf-8")
    by_file: dict[str, list[str]] = {}
    for line in res.stdout.splitlines():
        s = line.strip()
        if not s or "::" not in s or s.startswith(("=", "-")):
            continue
        fpath = s.split("::", 1)[0].replace("\\", "/")
        by_file.setdefault(fpath, []).append(s)
    return by_file


def extract_imports(py_path: Path, prod_modules: set[str]) -> list[tuple[str, int, str]]:
    """Retorna [(mod_alvo, linha, raw_stmt)] para imports AST e strings cirúrgicas (spec_from_file_location/mock)."""
    src = py_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(py_path))
    lines = src.splitlines()
    hits: list[tuple[str, int, str]] = []

    REEXPORTS = {
        "interface.ActionHooks": "interface.action_hooks",
        "agents.RevisorCritico": "agents.revisor_critico",
        "agent.CognitiveAgentRunner": "agent.run_agent",
        "agent.run_agent": "agent.run_agent",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in prod_modules:
                    hits.append((name, node.lineno, lines[node.lineno - 1].strip()))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in prod_modules:
                hits.append((mod, node.lineno, lines[node.lineno - 1].strip()))
            for alias in node.names:
                cand = f"{mod}.{alias.name}" if mod else alias.name
                if cand in REEXPORTS:
                    hits.append((REEXPORTS[cand], node.lineno, lines[node.lineno - 1].strip()))
                elif cand in prod_modules:
                    hits.append((cand, node.lineno, lines[node.lineno - 1].strip()))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            sval = node.value
            if "." in sval:
                if sval in prod_modules:
                    hits.append((sval, node.lineno, lines[node.lineno - 1].strip()))
                else:
                    for pm in prod_modules:
                        if sval.startswith(pm + "."):
                            hits.append((pm, node.lineno, lines[node.lineno - 1].strip()))
    # deduplicate preserving order
    seen = set()
    uniq = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def find_doc_mentions(target_terms: list[str], doc_files: list[Path]) -> list[dict]:
    mentions = []
    patterns = [re.compile(re.escape(t), re.IGNORECASE) for t in target_terms if len(t) >= 4]
    for df in doc_files:
        rel = df.relative_to(ROOT).as_posix()
        txt = df.read_text(encoding="utf-8", errors="replace")
        for idx, line in enumerate(txt.splitlines(), start=1):
            for pat in patterns:
                if pat.search(line):
                    mentions.append({"file": rel, "line": idx, "text": line.strip()[:140]})
                    break
    return mentions


def main() -> None:
    static_data = json.loads((EVID / "bloco1_static_reach.json").read_text(encoding="utf-8"))
    modules_info: dict = static_data["modules"]
    prod_modules = set(modules_info.keys())
    live_modules = {
        m for m, v in modules_info.items() if v["status"] in ("REACHABLE_LOAD", "REACHABLE_DEFERRED")
    }
    target_modules = sorted(
        m
        for m, v in modules_info.items()
        if v["status"]
        in ("UNREACHABLE", "REACHABLE_ANNOTATION_ONLY_RUNTIME", "REACHABLE_PEP562_LAZY")
    )

    test_nodes_by_file = collect_pytest_nodes()
    test_files = sorted(p for p in get_tracked_py_files() if p.relative_to(ROOT).as_posix().startswith("tests/"))

    test_file_imports: dict[str, list[tuple[str, int, str]]] = {}
    for tf in test_files:
        rel = tf.relative_to(ROOT).as_posix()
        test_file_imports[rel] = extract_imports(tf, prod_modules)

    doc_candidates = [
        ROOT / "README.md",
        ROOT / "README.pt-BR.md",
        ROOT / "CHANGELOG.md",
        ROOT / "AGENTS.md",
        ROOT / "ACTIVE_SDD.md",
        ROOT / "pyproject.toml",
    ]
    docs_dir = ROOT / "docs-grafo-concierge"
    if docs_dir.exists():
        doc_candidates.extend(sorted(p for p in docs_dir.rglob("*") if p.is_file()))
    doc_candidates = [p for p in doc_candidates if p.exists()]
    walkthrough_files = [ROOT / "walkthrough.md"] if (ROOT / "walkthrough.md").exists() else []

    inventory = {}
    txt_lines = []
    txt_lines.append("=== BLOCO 2: INVENTÁRIO POR MÓDULO (NÃO ALCANÇÁVEIS EM TEMPO DE CARGA) ===")
    txt_lines.append(f"Total de testes coletados (pytest): {sum(len(v) for v in test_nodes_by_file.values())}")
    txt_lines.append("")

    for mod in target_modules:
        minfo = modules_info[mod]
        mpath = ROOT / minfo["path"]
        src = mpath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
        defs = [
            n.name
            for n in tree.body
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        # Importadores de testes
        importing_tests = []
        total_tests_in_importing_files = 0
        for tf_rel, imps in test_file_imports.items():
            matched = [(l, s) for (tm, l, s) in imps if tm == mod]
            if matched:
                imported_live = sorted({tm for (tm, _, _) in imps if tm in live_modules})
                imported_dormant = sorted({tm for (tm, _, _) in imps if tm not in live_modules})
                tcount = len(test_nodes_by_file.get(tf_rel, []))
                total_tests_in_importing_files += tcount
                importing_tests.append(
                    {
                        "test_file": tf_rel,
                        "test_count": tcount,
                        "lines": matched,
                        "also_imports_live": imported_live,
                        "also_imports_dormant": imported_dormant,
                        "is_mixed": bool(imported_live),
                    }
                )

        # Termos de busca em docs: nome do arquivo/módulo e classes principais (não __init__)
        short_mod = mod.split(".")[-1]
        terms = [minfo["path"], mod]
        if short_mod != "__init__" and len(short_mod) >= 5:
            terms.append(short_mod)
        for d in defs:
            if len(d) >= 8 and not d.startswith("_"):
                terms.append(d)

        doc_hits = find_doc_mentions(terms, doc_candidates)
        walkthrough_hits = find_doc_mentions(terms, walkthrough_files)

        entry = {
            "module": mod,
            "path": minfo["path"],
            "status": minfo["status"],
            "loc": minfo["total_lines"],
            "non_empty_lines": minfo["non_empty_lines"],
            "defs": defs,
            "prod_importers": minfo["importers"],
            "importing_tests": importing_tests,
            "total_tests_in_importing_files": total_tests_in_importing_files,
            "doc_mentions": doc_hits,
            "walkthrough_mentions_count": len(walkthrough_hits),
        }
        inventory[mod] = entry

        txt_lines.append(f"[{mod}] ({minfo['path']}, {minfo['total_lines']}L / {minfo['non_empty_lines']} non-empty, status={minfo['status']})")
        txt_lines.append(f"  Símbolos top-level: {defs}")
        txt_lines.append(f"  Importadores produção: {minfo['importers']}")
        txt_lines.append(
            f"  Testes ({total_tests_in_importing_files} em {len(importing_tests)} arquivos): "
            + ", ".join(
                f"{t['test_file']}({t['test_count']}, mixed={t['is_mixed']}, live={len(t['also_imports_live'])})"
                for t in importing_tests
            )
        )
        txt_lines.append(
            f"  Menções docs ({len(doc_hits)}): "
            + ", ".join(f"{h['file']}:{h['line']}" for h in doc_hits[:12])
            + ("..." if len(doc_hits) > 12 else "")
        )
        txt_lines.append(f"  Menções walkthrough.md (apenas referência): {len(walkthrough_hits)}")
        txt_lines.append("")

    (EVID / "bloco2_inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (EVID / "bloco2_inventory.txt").write_text("\n".join(txt_lines), encoding="utf-8")
    print(f"Inventário gerado para {len(target_modules)} módulos; total pytest={sum(len(v) for v in test_nodes_by_file.values())}")


if __name__ == "__main__":
    main()
