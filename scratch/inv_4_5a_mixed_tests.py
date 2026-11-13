"""
Analisa granularmente cada teste individual nos arquivos mistos do Bloco 5,
distinguindo testes que exercitam apenas dormentes vs apenas vivos vs ambos.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "scratch" / "evidencia_4_5a"


def main() -> None:
    b5 = json.loads((EVID / "bloco5_tests_ci.json").read_text(encoding="utf-8"))
    inv = json.loads((EVID / "bloco2_inventory.json").read_text(encoding="utf-8"))
    pytest_raw = (EVID / "pytest_collect_raw.txt").read_text(encoding="utf-8").splitlines()

    # Map dormant module -> exported symbols
    dorm_symbols_by_mod = {m: set(e["defs"]) for m, e in inv.items() if m != "interface.queue_writer"}

    # Extra known dormant symbol tokens (module names, endpoint routes, etc.)
    DORMANT_TOKENS_MAP = {
        "core.hsm_engine": {"HierarchicalStateMachine", "HSMNode", "IllegalHSMTransitionError", "hsm", "/api/hsm/"},
        "core.rate_governor": {"RateGovernor", "PriorityRequest", "rate_governor", "governor_metrics", "/api/governor/"},
        "core.gating_interceptor": {"GatingInterceptor", "GatingViolationException", "gating", "/api/gating/"},
        "core.security_guard": {"SecurityGuard"},
        "core.telemetry_schemas": {"TelemetryPayloadSchema", "DirtyFileSchema", "AgentSessionSchema", "CheckpointSchema", "JanitorStatusSchema"},
        "interface.telemetry_api": {"telemetry_api", "TestClient", "/api/telemetry/", "/api/janitor/", "/api/checkpoints/", "/api/mcp/state", "/api/governor/", "/api/gating/", "/api/hsm/"},
        "interface.watcher": {"ConciergeFileSystemHandler", "watcher"},
        "interface.action_hooks": {"ActionHooks", "on_planning", "on_execution", "on_done"},
        "agents.revisor_critico": {"RevisorCritico", "AuditResult", "RerankResult"},
        "agent.run_agent": {"CognitiveAgentRunner", "HermesAgentRunner"},
        "agent.agent_prompts": {"DynamicPromptBuilder"},
        "core.background_janitor": {"BackgroundJanitor", "run_idle_summarization", "prune_checkpoints"},
        "core.dependencies": {"AgentDependencies"},
        "core.federated_knowledge_router": {"FederatedKnowledgeRouter", "NozomioRouter"},
        "core.global_memory_adapter": {"GlobalMemoryAdapter"},
        "core.intent_classifier": {"IntentClassifier"},
        "core.alias_tracker": {"AliasTracker"},
        "core.delta_manager": {"DeltaManager", "DocstringStripper", "calculate_ssh", "calculate_lbh"},
        "core.delta_sync": {"delta_sync", "DeltaManager", "DocstringStripper"},
        "core.parser_factory": {"ParserFactory"},
        "core.parsers.python_parser": {"PythonASTParser"},
        "core.parsers.ts_js_parser": {"TSJSASTParser"},
        "core.search_engine": {"HybridSearchEngine"},
        "core.vector_reconciler": {"VectorReconciler"},
        "storage.relational_db": {"init_fsm_checkpoints_schema", "FSM_CHECKPOINTS_TABLE_SQL"},
    }
    LIVE_TOKENS = {
        "SqliteStore", "GrafoConcierge", "GrafoConciergeServer", "MCPToolGovernor", "AgnosticCheckpointer",
        "GraphRAGEngine", "ConciergeDatabaseManager", "SchemaManager", "IngestionManager", "ZoomSummarizer",
        "JanitorService", "HybridSearch", "ChromaVectorStore", "QdrantVectorStore", "cli_main", "concierge_",
        "agent_save_checkpoint", "agent_get_checkpoint", "agent_list_checkpoints", "get_full_topology",
        "mcp_server", "concierge_search", "concierge_mine", "decouple_stdin", "EmbeddingManager",
    }

    lines = ["=== BLOCO 5 (GRANULAR): INSPEÇÃO POR TESTE INDIVIDUAL EM ARQUIVOS MISTOS ==="]
    granular_summary = []

    for af in b5["affected_files"]:
        tf = af["test_file"]
        nids = [l.strip() for l in pytest_raw if l.strip().startswith(tf + "::")]
        if af["test_count"] == 0:
            continue
        src = (ROOT / tf).read_text(encoding="utf-8", errors="replace")
        src_lines = src.splitlines()
        tree = ast.parse(src)

        dorm_mods = set(af["dormant_imported"])
        dorm_toks = set()
        for dm in dorm_mods:
            dorm_toks |= DORMANT_TOKENS_MAP.get(dm, set())
            dorm_toks |= dorm_symbols_by_mod.get(dm, set())

        # Collect top-level functions and class methods named test_*
        test_bodies: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                seg = "\n".join(src_lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
                test_bodies[node.name] = seg
            elif isinstance(node, ast.ClassDef):
                cls_header = "\n".join(src_lines[node.lineno - 1 : min(len(src_lines), node.lineno + 30)])
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                        seg = "\n".join(src_lines[item.lineno - 1 : getattr(item, "end_lineno", item.lineno)])
                        test_bodies[f"{node.name}::{item.name}"] = cls_header + "\n" + seg

        dormant_only_cnt = 0
        mixed_cnt = 0
        live_only_cnt = 0
        qw_only_cnt = 0
        per_test_rows = []
        for nid in nids:
            short = nid.split("::", 1)[1]
            # strip parametrize suffix [...]
            base_short = short.split("[", 1)[0]
            body = test_bodies.get(base_short, src)
            has_d = any(tok in body for tok in dorm_toks)
            has_qw = ("SerializedWriteQueue" in body or "write_queue" in body or "queue_writer" in body)
            has_l = any(tok in body for tok in LIVE_TOKENS)
            if set(dorm_mods) == {"interface.queue_writer"}:
                tag = "QW_HARNESS_OR_SUITE"
                qw_only_cnt += 1
            elif has_d and has_l:
                tag = "MIXED_TEST"
                mixed_cnt += 1
            elif has_d and not has_l:
                tag = "DORMANT_ONLY_TEST"
                dormant_only_cnt += 1
            elif not has_d and has_l:
                tag = "LIVE_ONLY_TEST_IN_MIXED_FILE"
                live_only_cnt += 1
            else:
                # Fallback: check class / setUp in whole file
                if af["pure_dormant_only"]:
                    tag = "DORMANT_ONLY_TEST"
                    dormant_only_cnt += 1
                else:
                    tag = "NEEDS_SETUP_CHECK"
                    mixed_cnt += 1
            per_test_rows.append((nid, tag))

        rec = {
            "test_file": tf,
            "collected": len(nids),
            "dormant_imported": sorted(dorm_mods),
            "live_imported": af["live_imported"],
            "dormant_only_tests": dormant_only_cnt,
            "mixed_tests": mixed_cnt,
            "live_only_tests": live_only_cnt,
            "qw_tests": qw_only_cnt,
        }
        granular_summary.append(rec)
        lines.append(
            f"[{tf}] ({len(nids)} testes) -> dormant_only={dormant_only_cnt}, mixed={mixed_cnt}, "
            f"live_only={live_only_cnt}, qw={qw_only_cnt} | dorm={sorted(dorm_mods)} | live={af['live_imported']}"
        )
        if live_only_cnt > 0:
            for nid, tag in per_test_rows:
                if tag == "LIVE_ONLY_TEST_IN_MIXED_FILE":
                    lines.append(f"    (PRESERVAR - só vivo) {nid}")

    (EVID / "bloco5_mixed_granular.json").write_text(json.dumps(granular_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (EVID / "bloco5_mixed_granular.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Arquivos analisados:", len(granular_summary))
    print("Live-only tests em arquivos mistos:", sum(r["live_only_tests"] for r in granular_summary))


if __name__ == "__main__":
    main()
