"""Probe Blocos 2 e 3 da 4.5a-bis: 4 modulos alcancaveis-nao-carregados + reconciliacao de testes."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scratch" / "evidencia_4_5a_bis"
EV_45A = ROOT / "scratch" / "evidencia_4_5a"

TARGET_FOUR = [
    "agents",
    "agents.revisor_critico",
    "interface.action_hooks",
    "core.probabilistic_retriever",
]

PROD_DIRS = ("agent", "agents", "core", "ingestion", "interface", "services", "storage")


def iter_prod_py() -> list[Path]:
    files = [ROOT / "main.py"]
    for d in PROD_DIRS:
        p = ROOT / d
        if p.exists():
            files.extend(sorted(p.rglob("*.py")))
    scripts_dir = ROOT / "scripts"
    if scripts_dir.exists():
        files.extend(sorted(scripts_dir.rglob("*.py")))
    return sorted({f for f in files if f.is_file()})


def search_prod_references() -> dict:
    patterns = {
        "agents_or_revisor": re.compile(r"\bagents\b|revisor_critico|RevisorCritico"),
        "action_hooks": re.compile(r"action_hooks|ActionHooks"),
        "probabilistic_or_thompson": re.compile(
            r"probabilistic_retriever|ThompsonRetriever|enable_probabilistic|_apply_thompson_sampling"
        ),
        "env_flags_prob_or_hooks": re.compile(
            r"GRAFO_[A-Z0-9_]*(?:PROB|THOMPSON|REVISOR|HOOK|AGENT)[A-Z0-9_]*"
        ),
    }
    results: dict[str, list[dict]] = {k: [] for k in patterns}
    for path in iter_prod_py():
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, start=1):
            for key, pat in patterns.items():
                if pat.search(line):
                    results[key].append({"file": rel, "line": idx, "text": line.strip()})
    return results


def search_doc_mentions() -> dict:
    terms = {
        "revisor_or_agents": re.compile(r"revisor_critico|RevisorCritico|\bagents/", re.IGNORECASE),
        "action_hooks": re.compile(r"action_hooks|ActionHooks|action hooks", re.IGNORECASE),
        "probabilistic_or_thompson": re.compile(
            r"probabilistic_retriever|ThompsonRetriever|Thompson Sampling|enable_probabilistic",
            re.IGNORECASE,
        ),
    }
    doc_files: list[Path] = []
    for name in (
        "README.md",
        "README.pt-BR.md",
        "CHANGELOG.md",
        "AGENTS.md",
        "ACTIVE_SDD.md",
        "pyproject.toml",
    ):
        p = ROOT / name
        if p.exists():
            doc_files.append(p)
    docs_dir = ROOT / "docs-grafo-concierge"
    if docs_dir.exists():
        doc_files.extend(sorted(p for p in docs_dir.rglob("*") if p.is_file()))

    hits: dict[str, list[dict]] = {k: [] for k in terms}
    for path in doc_files:
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, start=1):
            for key, pat in terms.items():
                if pat.search(line):
                    hits[key].append({"file": rel, "line": idx, "text": line.strip()})
    return hits


def collect_pytest_once() -> tuple[str, dict[str, int]]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    counts: Counter[str] = Counter()
    summary_line = ""
    for line in proc.stdout.splitlines():
        s = line.strip()
        if "collected" in s:
            summary_line = s
        if "::" in s and s.startswith("tests/"):
            rel_file = s.split("::", 1)[0]
            counts[rel_file] += 1
    return summary_line, dict(counts)


def module_exists_in_repo(mod_name: str) -> bool:
    rel = mod_name.replace(".", "/")
    return (ROOT / f"{rel}.py").is_file() or (ROOT / rel / "__init__.py").is_file()


def get_ast_project_imports(path: Path) -> set[str]:
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if module_exists_in_repo(alias.name):
                    imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            for alias in node.names:
                cand = f"{mod}.{alias.name}"
                if module_exists_in_repo(cand):
                    imported.add(cand)
            if mod == "interface" and any(a.name == "ActionHooks" for a in node.names):
                imported.add("interface.action_hooks")
            if module_exists_in_repo(mod):
                imported.add(mod)
        elif isinstance(node, ast.Call):
            # Detect importlib.util.spec_from_file_location("mod.name", ...)
            seg = ast.get_source_segment(src, node.func) or ""
            if "spec_from_file_location" in seg and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    if module_exists_in_repo(arg0.value):
                        imported.add(arg0.value)
    return imported


def build_reconciliation(collected_counts: dict[str, int]) -> dict:
    b1 = json.loads((EV_45A / "bloco1_static_reach.json").read_text(encoding="utf-8"))
    b5 = json.loads((EV_45A / "bloco5_tests_ci.json").read_text(encoding="utf-8"))
    mixed_ev = json.loads((EV_45A / "bloco5_mixed_granular.json").read_text(encoding="utf-8"))
    mixed_map = {item["test_file"]: item for item in mixed_ev}

    unreachable_28 = sorted(
        mod for mod, info in b1["modules"].items() if info["status"] == "UNREACHABLE"
    )
    reachable_4 = sorted(TARGET_FOUR)
    type_only_1 = ["interface.queue_writer"]
    class_i_ii_iv = sorted(set(unreachable_28) | set(type_only_1) | set(reachable_4))  # 33

    test_files = sorted((ROOT / "tests").rglob("*.py"))
    rows_28 = []
    rows_28_no_watcher_ignore = []
    rows_4 = {m: [] for m in TARGET_FOUR}
    all_rows_33 = []

    for tf in test_files:
        rel = tf.relative_to(ROOT).as_posix()
        imports = get_ast_project_imports(tf)
        cnt = collected_counts.get(rel, 0)

        hits_28 = sorted(imports & set(unreachable_28))
        hits_4 = sorted(imports & set(reachable_4))
        hits_qw = sorted(imports & set(type_only_1))
        hits_33 = sorted(imports & set(class_i_ii_iv))
        live_mods = sorted(m for m in imports if m not in set(class_i_ii_iv))

        if hits_28:
            rows_28.append(
                {
                    "test_file": rel,
                    "collected": cnt,
                    "hits_28": hits_28,
                    "live_mods": live_mods,
                }
            )
            if rel != "tests/test_watcher_ignore.py":
                rows_28_no_watcher_ignore.append(
                    {"test_file": rel, "collected": cnt, "hits_28": hits_28}
                )

        for tm in hits_4:
            rows_4[tm].append({"test_file": rel, "collected": cnt, "live_mods": live_mods})

        src = tf.read_text(encoding="utf-8", errors="replace")
        for tm in TARGET_FOUR:
            if tm in src and not any(x["test_file"] == rel for x in rows_4[tm]):
                rows_4[tm].append(
                    {
                        "test_file": rel,
                        "collected": cnt,
                        "live_mods": live_mods,
                        "string_ref_only": True,
                    }
                )

        if hits_33:
            if not live_mods and (hits_28 or hits_4) and not hits_qw:
                cat = "so-dormente"
            elif not live_mods and hits_qw and not hits_28 and not hits_4:
                cat = "so-queue_writer"
            elif hits_qw and not hits_28 and not hits_4 and live_mods:
                cat = "misto_queue_writer_e_vivo"
            elif live_mods:
                cat = "misto"
            else:
                cat = "so-dormente"

            mix_info = mixed_map.get(rel)
            all_rows_33.append(
                {
                    "test_file": rel,
                    "collected": cnt,
                    "hits_28": hits_28,
                    "hits_4": hits_4,
                    "hits_qw": hits_qw,
                    "live_mods": live_mods,
                    "category": cat,
                    "mixed_fn_info": {
                        "dormant_only_tests": mix_info["dormant_only_tests"],
                        "mixed_tests": mix_info["mixed_tests"],
                        "live_only_tests": mix_info["live_only_tests"],
                        "qw_tests": mix_info["qw_tests"],
                    }
                    if mix_info
                    else None,
                }
            )

    ev45a_affected = b5["affected_files"]
    ev45a_26_names = {r["test_file"] for r in ev45a_affected}
    return {
        "unreachable_28": unreachable_28,
        "reachable_4": reachable_4,
        "ev45a_26_files_count": len(ev45a_affected),
        "ev45a_26_tests_sum": sum(r["test_count"] for r in ev45a_affected),
        "only_28_files_count": len(rows_28),
        "only_28_tests_sum": sum(r["collected"] for r in rows_28),
        "only_28_excl_watcher_ignore_count": len(rows_28_no_watcher_ignore),
        "only_28_excl_watcher_ignore_sum": sum(r["collected"] for r in rows_28_no_watcher_ignore),
        "in_ev45a_26_but_not_28": sorted(
            [
                {
                    "test_file": r["test_file"],
                    "test_count": r["test_count"],
                    "dormant_imported": r["dormant_imported"],
                }
                for r in ev45a_affected
                if r["test_file"] not in {x["test_file"] for x in rows_28}
            ],
            key=lambda x: x["test_file"],
        ),
        "rows_28": rows_28,
        "rows_4": rows_4,
        "all_rows_33": all_rows_33,
        "ev45a_26_names": sorted(ev45a_26_names),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prod_refs = search_prod_references()
    doc_mentions = search_doc_mentions()
    summary_line, collected_counts = collect_pytest_once()
    recon = build_reconciliation(collected_counts)

    out = {
        "pytest_summary": summary_line,
        "collected_counts_by_file": collected_counts,
        "prod_refs": prod_refs,
        "doc_mentions": doc_mentions,
        "reconciliation": recon,
    }
    (OUT_DIR / "bloco2_3_probe.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [f"Pytest collect: {summary_line}", "", "=== PROD REFS ==="]
    for k, items in prod_refs.items():
        lines.append(f"[{k}] ({len(items)})")
        for it in items:
            lines.append(f"  {it['file']}:{it['line']}: {it['text']}")

    lines.append("\n=== DOC MENTIONS ===")
    for k, items in doc_mentions.items():
        lines.append(f"[{k}] ({len(items)})")
        for it in items:
            lines.append(f"  {it['file']}:{it['line']}: {it['text']}")

    lines.append("\n=== FOUR REACHABLE-NOT-LOADED TEST HITS ===")
    for tm, items in recon["rows_4"].items():
        lines.append(f"[{tm}]")
        for it in items:
            lines.append(f"  {it}")

    lines.append("\n=== RECONCILIATION SUMMARY ===")
    lines.append(
        f"4.5a affected (no prob_retriever, incl 4-lazy + queue_writer? check): "
        f"{recon['ev45a_26_files_count']} files, {recon['ev45a_26_tests_sum']} tests"
    )
    lines.append(
        f"Only 28 unreachable: {recon['only_28_files_count']} files, {recon['only_28_tests_sum']} tests"
    )
    lines.append(
        f"Only 28 excl test_watcher_ignore.py: "
        f"{recon['only_28_excl_watcher_ignore_count']} files, {recon['only_28_excl_watcher_ignore_sum']} tests"
    )
    lines.append("Diff (in 4.5a 26 files but not importing any of the 28):")
    for d in recon["in_ev45a_26_but_not_28"]:
        lines.append(f"  {d}")

    lines.append("\n=== ALL AFFECTED FILES ACROSS 33 (28 + 1 + 4) ===")
    for r in recon["all_rows_33"]:
        lines.append(
            f"  {r['test_file']} | collected={r['collected']} | cat={r['category']} | "
            f"h28={r['hits_28']} | h4={r['hits_4']} | hqw={r['hits_qw']} | live={r['live_mods']}"
        )

    (OUT_DIR / "bloco2_3_probe.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
