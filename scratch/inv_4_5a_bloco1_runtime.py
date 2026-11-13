"""
Bloco 1 (Runtime Trace) - PEDIDO 4.5a
Sobe main.bootstrap() em diretório temporário isolado com chaves FAKE,
sem tocar em .env ou data/, exercita todas as ferramentas MCP registradas,
também exercita interface.cli em subprocesso isolado, e registra o diff de sys.modules.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_TXT = ROOT / "scratch" / "evidencia_4_5a" / "bloco1_runtime_trace.txt"
OUT_JSON = ROOT / "scratch" / "evidencia_4_5a" / "bloco1_runtime_trace.json"


def project_modules_snapshot() -> set[str]:
    roots = {"main", "core", "storage", "ingestion", "interface", "services", "agent", "agents"}
    loaded = set()
    for name in list(sys.modules.keys()):
        top = name.split(".")[0]
        if top in roots:
            mod = sys.modules[name]
            if mod is not None:
                loaded.add(name)
    return loaded


def main_trace() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    with tempfile.TemporaryDirectory(prefix="grafo_45a_runtime_") as tmp:
        tmp_path = Path(tmp)
        sample_proj = tmp_path / "sample_proj"
        sample_proj.mkdir()
        (sample_proj / "app.py").write_text(
            '"""Sample app."""\n\n'
            "def helper(x: int) -> int:\n"
            "    return x + 1\n\n"
            "def run_flow(val: int) -> int:\n"
            "    return helper(val)\n",
            encoding="utf-8",
        )
        (sample_proj / "utils.ts").write_text(
            "export function greet(name: string): string {\n"
            "  return 'hi ' + name;\n"
            "}\n",
            encoding="utf-8",
        )
        sample_proj2 = tmp_path / "ref_proj"
        sample_proj2.mkdir()
        (sample_proj2 / "lib.py").write_text("def ref_fn():\n    return 42\n", encoding="utf-8")

        db_path = tmp_path / "concierge.db"
        chroma_path = tmp_path / "chroma"

        # Blindagem total contra .env e data/ reais:
        os.environ["GRAFO_DB_PATH"] = str(db_path)
        os.environ["GRAFO_CHROMA_PATH"] = str(chroma_path)
        os.environ["GRAFO_CHROMA_COLLECTION"] = "grafo_45a_test"
        os.environ["GRAFO_LLM_MODEL"] = "none"
        os.environ["GRAFO_LLM_PROVIDER"] = "none"
        os.environ["GRAFO_LLM_API_KEY"] = "sk-fake-45a-00000000"
        os.environ["GRAFO_API_KEY"] = "fake-api-key-45a"
        os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "true"
        os.environ["GRAFO_VECTOR_BACKEND"] = "chroma"
        os.environ["GRAFO_DEFAULT_STATE"] = "MAINTENANCE"
        os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"
        os.environ["GRAFO_TRANSPORT"] = "stdio"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        import dotenv
        dotenv.load_dotenv = lambda *a, **kw: False  # impede leitura de .env

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            snap_before = project_modules_snapshot()

            import main as app_main
            snap_after_import = project_modules_snapshot()

            server, janitor, store = app_main.bootstrap()
            snap_after_bootstrap = project_modules_snapshot()

            tools = server.mcp._tool_manager.list_tools()
            tool_names = [t.name for t in tools]
            tool_map = {t.name: t for t in tools}
            print(f"[TRACE] listed {len(tool_names)} tools", file=sys.stderr, flush=True)

            results: dict[str, dict] = {}

            def call_sync(name: str, args: dict):
                print(f"[TRACE] calling {name}...", file=sys.stderr, flush=True)
                try:
                    session_id = args.get("session_id", "default") if isinstance(args, dict) else "default"
                    server.governor.validate_tool_execution(session_id, name)
                    tool_obj = tool_map[name]
                    res = tool_obj.fn(**args)
                    txt = str(res)
                    print(f"[TRACE] done {name}", file=sys.stderr, flush=True)
                    return {"ok": True, "result_preview": txt[:300]}
                except Exception as exc:
                    print(f"[TRACE] err {name}: {exc}", file=sys.stderr, flush=True)
                    return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

            def run_all_sync():
                # 1. concierge_set_state -> MAINTENANCE (garante permissão para DANGEROUS)
                results["concierge_set_state"] = call_sync(
                    "concierge_set_state", {"state_name": "MAINTENANCE", "session_id": "default"}
                )
                # 2. registrar 2 projetos
                results["concierge_register"] = call_sync(
                    "concierge_register",
                    {"project_path": str(sample_proj), "wing": "core", "privacy_level": "PUBLIC", "summary": "Sample"},
                )
                call_sync(
                    "concierge_register",
                    {"project_path": str(sample_proj2), "wing": "ref", "privacy_level": "PUBLIC", "summary": "Ref"},
                )
                proj_id = "sample_proj"
                ref_id = "ref_proj"
                results["concierge_list_projects"] = call_sync("concierge_list_projects", {})
                try:
                    prows = store.list_projects()
                    for r in prows:
                        if "sample_proj" in str(r.get("name", "")) or "sample_proj" in str(r.get("root_path", "")):
                            proj_id = r["uuid"]
                        if "ref_proj" in str(r.get("name", "")) or "ref_proj" in str(r.get("root_path", "")):
                            ref_id = r["uuid"]
                except Exception:
                    pass

                ordered = [
                    ("concierge_mine", {"path": str(sample_proj), "project_identifier": proj_id, "auto_tag": True}),
                    ("concierge_status", {"project_identifier": proj_id}),
                    ("concierge_wakeup", {"project_identifier": proj_id}),
                    ("concierge_resume", {"project_identifier": proj_id}),
                    ("concierge_search", {"query": "helper", "project_identifier": proj_id, "top_k": 5}),
                    ("find_similar", {"query": "helper function", "project_identifier": proj_id, "top_k": 5}),
                    ("concierge_load", {"node_id": "2"}),
                    ("concierge_commit", {"project_uuid": proj_id, "phase": "4.5a", "technical_changes": "Runtime trace test"}),
                    ("get_trajectories", {"project_identifier": proj_id, "limit": 5}),
                    ("concierge_store_fact", {"scope_type": "session", "scope_id": "s45a", "fact_statement": "Runtime uses SQLite WAL"}),
                    ("concierge_list_facts", {"scope_type": "session", "scope_id": "s45a"}),
                    ("concierge_set_memory", {"scope_type": "session", "scope_id": "s45a", "block_label": "notes", "content": "block-v1"}),
                    ("concierge_get_memory", {"scope_type": "session", "scope_id": "s45a", "block_label": "notes"}),
                    ("concierge_feedback", {"fact_id": 1, "was_useful": True}),
                    ("search_symbols", {"query": "helper", "project_identifier": proj_id}),
                    ("get_implementations", {"symbol_id": "2"}),
                    ("get_callers", {"symbol_id": "2"}),
                    ("concierge_get_call_chain", {"start_node": "app.py::run_flow", "depth_limit": 2, "project_identifier": proj_id}),
                    ("get_full_topology", {"project_identifier": proj_id}),
                    ("count_embeddings", {"project_identifier": proj_id}),
                    ("update_project", {"project_identifier": proj_id, "summary": "Updated"}),
                    ("add_reference_wing", {"project_identifier": proj_id, "reference_wing": "ref"}),
                    ("remove_reference_wing", {"project_identifier": proj_id, "reference_wing": "ref"}),
                    ("agent_save_checkpoint", {"agent_id": "agent-45a", "checkpoint_id": "ckpt-1", "state": {"ok": True}}),
                    ("agent_get_checkpoint", {"agent_id": "agent-45a", "checkpoint_id": "ckpt-1"}),
                    ("agent_list_checkpoints", {"agent_id": "agent-45a"}),
                    ("reset_collection", {}),
                    ("delete_project", {"project_identifier": ref_id, "confirm": True}),
                ]

                for tname, default_args in ordered:
                    if tname in tool_map and tname not in results:
                        props = (tool_map[tname].parameters or {}).get("properties", {})
                        if props:
                            filtered = {k: v for k, v in default_args.items() if k in props}
                            req = (tool_map[tname].parameters or {}).get("required", [])
                            for rk in req:
                                if rk not in filtered:
                                    if "project" in rk:
                                        filtered[rk] = proj_id
                                    elif "session" in rk:
                                        filtered[rk] = "s45a"
                                    elif "confirm" in rk:
                                        filtered[rk] = True
                                    else:
                                        filtered[rk] = "test"
                            results[tname] = call_sync(tname, filtered)
                        else:
                            results[tname] = call_sync(tname, default_args)

                for t in tools:
                    if t.name not in results:
                        req = (t.parameters or {}).get("required", [])
                        args = {}
                        for rk in req:
                            if "project" in rk:
                                args[rk] = proj_id
                            elif "confirm" in rk:
                                args[rk] = True
                            else:
                                args[rk] = "test"
                        results[t.name] = call_sync(t.name, args)

            run_all_sync()
            snap_after_tools = project_modules_snapshot()

            # Fechar store/janitor
            try:
                janitor.stop()
            except Exception:
                pass
            try:
                store.close()
            except Exception:
                pass
        finally:
            os.chdir(old_cwd)

        # Também testar a segunda raiz (interface.cli) em subprocesso isolado para capturar sys.modules ao rodar CLI status
        cli_probe = (
            "import sys, os, dotenv; dotenv.load_dotenv = lambda *a, **kw: False; "
            "import interface.cli as c; "
            "roots = {'main','core','storage','ingestion','interface','services','agent','agents'}; "
            "print('\\n'.join(sorted(m for m,v in sys.modules.items() if m.split('.')[0] in roots and v is not None)))"
        )
        cli_env = os.environ.copy()
        cli_env["PYTHONPATH"] = str(ROOT)
        cli_proc = subprocess.run(
            [sys.executable, "-c", cli_probe],
            cwd=str(tmp_path),
            env=cli_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        cli_import_mods = [ln.strip() for ln in cli_proc.stdout.splitlines() if ln.strip()]

        # Subprocesso CLI executando status (sem tocar em .env/data real)
        cli_status_probe = "\n".join([
            "import sys, os, dotenv",
            "dotenv.load_dotenv = lambda *a, **kw: False",
            "sys.argv = ['concierge', 'status']",
            "import interface.cli as c",
            "try:",
            "    c.main()",
            "except SystemExit:",
            "    pass",
            "roots = {'main','core','storage','ingestion','interface','services','agent','agents'}",
            "print('__MODS__')",
            "print('\\n'.join(sorted(m for m,v in sys.modules.items() if m.split('.')[0] in roots and v is not None)))",
        ])
        cli_status_proc = subprocess.run(
            [sys.executable, "-c", cli_status_probe],
            cwd=str(tmp_path),
            env=cli_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        cli_exec_mods = []
        if "__MODS__" in cli_status_proc.stdout:
            after_marker = cli_status_proc.stdout.split("__MODS__", 1)[1]
            cli_exec_mods = [ln.strip() for ln in after_marker.splitlines() if ln.strip()]

    # Carregar saída estática do Bloco 1 para comparação
    static_json = ROOT / "scratch" / "evidencia_4_5a" / "bloco1_static_reach.json"
    static_data = json.loads(static_json.read_text(encoding="utf-8"))
    static_all = set(static_data["modules"].keys())
    static_load = {m for m, v in static_data["modules"].items() if v["status"] == "REACHABLE_LOAD"}
    static_deferred = {m for m, v in static_data["modules"].items() if v["status"] == "REACHABLE_DEFERRED"}
    static_ann = {m for m, v in static_data["modules"].items() if v["status"] == "REACHABLE_ANNOTATION_ONLY_RUNTIME"}
    static_pep562 = {m for m, v in static_data["modules"].items() if v["status"] == "REACHABLE_PEP562_LAZY"}
    static_unreach = {m for m, v in static_data["modules"].items() if v["status"] == "UNREACHABLE"}

    runtime_all = snap_after_tools | set(cli_exec_mods)
    union_static_reachable = static_load | static_deferred | static_ann | static_pep562

    in_static_reach_not_runtime = sorted(union_static_reachable - runtime_all)
    in_runtime_not_static_load_def = sorted(runtime_all - (static_load | static_deferred))
    runtime_vs_static_unreach = sorted(runtime_all & static_unreach)

    payload = {
        "tools_registered_count": len(tool_names),
        "tools_registered": tool_names,
        "tools_results": results,
        "snap_before": sorted(snap_before),
        "snap_after_import_main": sorted(snap_after_import - snap_before),
        "snap_after_bootstrap": sorted(snap_after_bootstrap - snap_before),
        "snap_after_tools": sorted(snap_after_tools - snap_before),
        "cli_import_mods": cli_import_mods,
        "cli_exec_mods": cli_exec_mods,
        "runtime_union": sorted(runtime_all - snap_before),
        "comparison": {
            "in_static_reachable_not_in_runtime": in_static_reach_not_runtime,
            "in_runtime_not_in_static_load_or_deferred": in_runtime_not_static_load_def,
            "static_unreachable_loaded_at_runtime": runtime_vs_static_unreach,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("=== BLOCO 1 (RUNTIME TRACE): DIFF DE sys.modules ===")
    lines.append(f"Ferramentas MCP registradas: {len(tool_names)}")
    lines.append(f"Módulos após import main: {len(payload['snap_after_import_main'])} -> {payload['snap_after_import_main']}")
    lines.append(f"Módulos após main.bootstrap(): {len(payload['snap_after_bootstrap'])} -> {payload['snap_after_bootstrap']}")
    lines.append(f"Módulos após exercitar ferramentas MCP: {len(payload['snap_after_tools'])} -> {payload['snap_after_tools']}")
    lines.append(f"Módulos após import interface.cli: {len(cli_import_mods)} -> {cli_import_mods}")
    lines.append(f"Módulos após CLI `status`: {len(cli_exec_mods)} -> {cli_exec_mods}")
    lines.append(f"União runtime (MCP + CLI): {len(payload['runtime_union'])} módulos")
    lines.append("")
    lines.append("--- RESULTADOS DAS FERRAMENTAS MCP ---")
    for tname in tool_names:
        r = results.get(tname, {"ok": False, "error": "not called"})
        lines.append(f"  - {tname}: ok={r.get('ok')} | {r.get('result_preview') or r.get('error')}")
    lines.append("")
    lines.append("--- COMPARAÇÃO RUNTIME vs GRAFO ESTÁTICO ---")
    lines.append(f"Alcançáveis no grafo estático MAS NÃO carregados no runtime ({len(in_static_reach_not_runtime)}): {in_static_reach_not_runtime}")
    lines.append(f"Carregados no runtime fora de LOAD+DEFERRED ({len(in_runtime_not_static_load_def)}): {in_runtime_not_static_load_def}")
    lines.append(f"Não alcançáveis estáticos carregados no runtime ({len(runtime_vs_static_unreach)}): {runtime_vs_static_unreach}")
    lines.append("")
    lines.append("Nota CLI returncode: " + f"import={cli_proc.returncode}, status={cli_status_proc.returncode}")
    if cli_status_proc.returncode != 0 or cli_status_proc.stderr:
        lines.append("CLI status stderr (preview): " + cli_status_proc.stderr[:400].replace("\n", " "))

    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Registered tools: {len(tool_names)}")
    print(f"Runtime union count: {len(payload['runtime_union'])}")
    print(f"Static reachable NOT loaded at runtime: {in_static_reach_not_runtime}")
    print(f"Static unreachable loaded at runtime: {runtime_vs_static_unreach}")


if __name__ == "__main__":
    main_trace()
