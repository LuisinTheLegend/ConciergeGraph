"""Computa matriz unificada e reconciliacao exata de testes para Bloco 3 da 4.5a-bis."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EV_45A = ROOT / "scratch" / "evidencia_4_5a"
OUT_DIR = ROOT / "scratch" / "evidencia_4_5a_bis"

# Conjunto Classe (i) apenas (extras suspensos D0 / inativos, excluindo (ii)/(iii) puros e (iv) e QW):
# Observacao: core.background_janitor e (i)+(ii)+(iii); inclui-se se tratarmos extras D0 + janitor/watcher.
CLASS_I_MODULES = {
    "agent",
    "agent.agent_prompts",
    "agent.run_agent",
    "core.background_janitor",
    "core.dependencies",
    "core.gating_interceptor",
    "core.hsm_engine",
    "core.janitor",
    "core.rate_governor",
    "core.security_guard",
    "core.telemetry_schemas",
    "interface.telemetry_api",
    "interface.watcher",
    "storage.relational_db",
}

CLASS_II_III_MODULES = {
    "core.alias_tracker",
    "core.delta_manager",
    "core.delta_sync",
    "core.federated_knowledge_router",
    "core.global_memory_adapter",
    "core.intent_classifier",
    "core.nozomio_router",
    "core.parser_factory",
    "core.parsers",
    "core.parsers.base",
    "core.parsers.python_parser",
    "core.parsers.ts_js_parser",
    "core.search_engine",
    "core.vector_reconciler",
}

CLASS_IV_MODULES = {
    "agents",
    "agents.revisor_critico",
    "interface.action_hooks",
    "core.probabilistic_retriever",
}

QW_MODULE = "interface.queue_writer"


def build_matrix() -> dict:
    b23 = json.loads((OUT_DIR / "bloco2_3_probe.json").read_text(encoding="utf-8"))
    b5 = json.loads((EV_45A / "bloco5_tests_ci.json").read_text(encoding="utf-8"))
    b5_gran = {x["test_file"]: x for x in json.loads((EV_45A / "bloco5_mixed_granular.json").read_text(encoding="utf-8"))}

    collected_by_file: dict[str, int] = b23["collected_counts_by_file"]
    all_rows_33 = {r["test_file"]: r for r in b23["reconciliation"]["all_rows_33"]}

    # Total test files & collected tests across tests/
    all_test_files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").rglob("*.py"))
    # Exclude __init__ or helper? Keep all .py in tests/ cleanly and note collected count
    total_tests = sum(collected_by_file.get(f, 0) for f in all_test_files)

    # Check exact pure_dormant vs misto for all 33 rows using actual AST imports verified earlier:
    # Specifically fix the 4.5a heuristic quirk on test_adaptive_gating (string 'core.py'),
    # test_multilang_parser (comments/strings), test_watcher_ignore ('import interface' just for sys.modules container)
    def get_true_file_category_33(tf: str, row: dict) -> str:
        if tf in {
            "tests/test_adaptive_gating.py",
            "tests/test_delta_sync_drift.py",
            "tests/test_dependency_injection.py",
            "tests/test_multilang_parser.py",
            "tests/test_rate_governor_priority.py",
            "tests/test_ssh_language_coverage.py",
            "tests/test_watcher_ignore.py",
        }:
            return "so-dormente"
        if tf in {
            "tests/test_agent_checkpointer.py",
            "tests/test_concurrency_stress.py",
            "tests/test_graph_rag_loops.py",
            "tests/test_mcp_server_extensions.py",
            "tests/test_queue_writer_batching.py",
            "tests/test_queue_writer_resilience.py",
        }:
            return "so-queue_writer"
        return "misto"

    def summarize_cut(target_mods: set[str], include_qw_bucket: bool = True) -> dict:
        buckets = {
            "so-dormente": {"files": [], "tests": 0},
            "misto": {"files": [], "tests": 0},
            "so-queue_writer": {"files": [], "tests": 0},
            "so-vivo": {"files": [], "tests": 0},
        }
        # Note: when include_qw_bucket=True, files touching ONLY interface.queue_writer (plus maybe live) go in so-queue_writer bucket.
        for tf in all_test_files:
            cnt = collected_by_file.get(tf, 0)
            row = all_rows_33.get(tf)
            if not row:
                buckets["so-vivo"]["files"].append(tf)
                buckets["so-vivo"]["tests"] += cnt
                continue
            mods_in_file = set(row["hits_28"]) | set(row["hits_4"])
            hits_target = mods_in_file & target_mods
            if not hits_target:
                if row["hits_qw"] and not row["hits_28"] and not row["hits_4"]:
                    buckets["so-queue_writer"]["files"].append(tf)
                    buckets["so-queue_writer"]["tests"] += cnt
                else:
                    buckets["so-vivo"]["files"].append(tf)
                    buckets["so-vivo"]["tests"] += cnt
                continue

            cat = get_true_file_category_33(tf, row)
            if cat == "so-queue_writer":
                buckets["so-queue_writer"]["files"].append(tf)
                buckets["so-queue_writer"]["tests"] += cnt
            else:
                buckets[cat]["files"].append(tf)
                buckets[cat]["tests"] += cnt

        return {
            k: {"files_count": len(v["files"]), "tests_count": v["tests"], "files": v["files"]}
            for k, v in buckets.items()
        }

    cut_i = summarize_cut(CLASS_I_MODULES)
    cut_i_ii_iii_iv = summarize_cut(CLASS_I_MODULES | CLASS_II_III_MODULES | CLASS_IV_MODULES)
    cut_unreachable_28 = summarize_cut(CLASS_I_MODULES | CLASS_II_III_MODULES)

    # Granular per-function sum inside all affected files (for Class i+ii+iii+iv + qw)
    # Note: for test_probabilistic_retriever.py (not in b5_gran), test_update_memory_utility is live-only (1), other 2 are dormant-only (2).
    gran_totals = {"dormant_only": 0, "mixed": 0, "live_only": 0, "qw": 0}
    for tf, row in all_rows_33.items():
        cnt = row["collected"]
        if tf == "tests/test_probabilistic_retriever.py":
            gran_totals["dormant_only"] += 2
            gran_totals["live_only"] += 1
        elif tf in b5_gran:
            g = b5_gran[tf]
            # Correct test_adaptive_gating (11+2 were flagged mixed due to string 'core') -> keep reported OR explain!
            gran_totals["dormant_only"] += g["dormant_only_tests"]
            gran_totals["mixed"] += g["mixed_tests"]
            gran_totals["live_only"] += g["live_only_tests"]
            gran_totals["qw"] += g["qw_tests"]

    result = {
        "total_py_files_in_tests": len(all_test_files),
        "total_collected_tests": total_tests,
        "cut_class_i": cut_i,
        "cut_unreachable_28": cut_unreachable_28,
        "cut_all_i_ii_iii_iv": cut_i_ii_iii_iv,
        "granular_4_5a_plus_prob": gran_totals,
    }
    (OUT_DIR / "bloco3_matrix.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        f"Total .py in tests/: {len(all_test_files)}, collected tests: {total_tests}",
        "\n--- CUT: CLASS (i) ONLY (14 UNREACHABLE D0 modules) ---",
    ]
    for k, v in cut_i.items():
        lines.append(f"  {k}: {v['files_count']} files, {v['tests_count']} tests")
    lines.append("\n--- CUT: 28 UNREACHABLE (CLASS i + ii/iii UNREACHABLE) ---")
    for k, v in cut_unreachable_28.items():
        lines.append(f"  {k}: {v['files_count']} files, {v['tests_count']} tests")
    lines.append("\n--- CUT: ALL (i) + (ii)/(iii) + (iv) [32 modules, excl. queue_writer] ---")
    for k, v in cut_i_ii_iii_iv.items():
        lines.append(f"  {k}: {v['files_count']} files, {v['tests_count']} tests")
    lines.append(f"\nGranular sum (affected 33 files): {gran_totals}")
    (OUT_DIR / "bloco3_matrix.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    build_matrix()
