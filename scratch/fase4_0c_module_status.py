import os
import sys

PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ast
import tempfile
import shutil
import sqlite3
import asyncio
import json
import inspect
import coverage
from collections import defaultdict
from pathlib import Path

# Step 1: Discover the 64 production python files
def discover_prod_files():
    prod_files = []
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in (
            '.git', '.agents', '.github', '.mypy_cache', '.pytest_cache', 
            '__pycache__', 'tests', 'scratch', 'audits', 'grafo-dashboard-web', 
            'data', 'docs-grafo-concierge'
        ) and not d.startswith('_test')]
        for f in files:
            if f.endswith('.py'):
                rel = os.path.relpath(os.path.join(root, f), '.').replace('\\', '/')
                prod_files.append(rel)
    prod_files.sort()
    return prod_files

def file_to_module(rel_path):
    if rel_path == 'main.py':
        return 'main'
    clean = rel_path.removesuffix('.py')
    if clean.endswith('/__init__'):
        clean = clean.removesuffix('/__init__')
    return clean.replace('/', '.')

def extract_function_body_lines(filepath):
    """
    Extracts all line numbers that belong to statements inside function/method bodies.
    Excludes module-level statements (imports, class/function definitions, top-level assignments).
    Also returns a mapping of function name -> list of lines.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
            source = fp.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return set(), {}

    func_body_lines = set()
    func_line_map = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fname = node.name
            lines = set()
            for child in node.body:
                for n in ast.walk(child):
                    if hasattr(n, 'lineno'):
                        lines.add(n.lineno)
                        func_body_lines.add(n.lineno)
            func_line_map[fname] = sorted(lines)

    return func_body_lines, func_line_map

async def main_probe():
    prod_files = discover_prod_files()
    print(f"=== FASE 4.0c: STATUS DOS MÓDULOS DERIVADO DE EXECUÇÃO (COVERAGE) ===")
    print(f"Módulos de produção descobertos: {len(prod_files)} arquivos")
    assert len(prod_files) == 64, f"Esperado 64 módulos, encontrado {len(prod_files)}"

    file_ast_info = {}
    for f in prod_files:
        body_lines, func_map = extract_function_body_lines(f)
        file_ast_info[f] = {
            "module": file_to_module(f),
            "body_lines": body_lines,
            "func_map": func_map
        }

    # Setup temporary isolated directory
    temp_dir = tempfile.mkdtemp(prefix="fase4_0c_coverage_")
    db_path = os.path.join(temp_dir, "cov_concierge.db")
    chroma_path = os.path.join(temp_dir, "cov_chroma")

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "cov_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"

    assert db_path.startswith(temp_dir)
    assert chroma_path.startswith(temp_dir)

    # Fixture project
    fixture_dir = os.path.join(temp_dir, "fixture_project")
    os.makedirs(fixture_dir, exist_ok=True)
    with open(os.path.join(fixture_dir, "math_ops.py"), "w", encoding="utf-8") as f:
        f.write("def add(a: int, b: int) -> int:\n    return a + b\n\ndef multiply(a: int, b: int) -> int:\n    return a * b\n")
    with open(os.path.join(fixture_dir, "calc.py"), "w", encoding="utf-8") as f:
        f.write("from math_ops import add, multiply\n\ndef compute_total(x: int) -> int:\n    res = add(x, 10)\n    return multiply(res, 2)\n")
    with open(os.path.join(fixture_dir, "service.py"), "w", encoding="utf-8") as f:
        f.write("from calc import compute_total\n\nclass CalculatorService:\n    def run(self, val: int) -> int:\n        return compute_total(val)\n")
    with open(os.path.join(fixture_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Fixture Project\nDocumentation for test fixture.\n")

    # Call tracker for target modules via wrapper (non-intrusive to coverage)
    call_records = defaultdict(lambda: {"callers": set(), "count": 0})

    def record_call(mod_name, func_name):
        try:
            caller_frame = inspect.currentframe().f_back.f_back
            caller_name = caller_frame.f_code.co_name
            caller_file = os.path.relpath(caller_frame.f_code.co_filename, PROJECT_ROOT).replace('\\', '/')
            caller_line = caller_frame.f_lineno
            caller_desc = f"{caller_file}:{caller_line} ({caller_name})"
        except Exception:
            caller_desc = "<unknown>"
        key = (mod_name, func_name)
        call_records[key]["callers"].add(caller_desc)
        call_records[key]["count"] += 1

    # =========================================================================
    # FASE 1 (F1): BOOTSTRAP
    # =========================================================================
    print("\n--- INICIANDO MEDIÇÃO FASE 1 (F1): BOOTSTRAP ---")
    cov_f1 = coverage.Coverage(source=["."], branch=False)
    cov_f1.start()

    import main
    server, janitor, store = main.bootstrap()

    cov_f1.stop()
    cov_f1.save()
    f1_data = cov_f1.get_data()

    f1_lines_by_file = {}
    f1_logic_by_file = {}
    for f in prod_files:
        abs_p = os.path.abspath(f)
        lines = f1_data.lines(abs_p) or []
        body_lines = file_ast_info[f]["body_lines"]
        logic_lines = set(lines) & body_lines
        f1_lines_by_file[f] = sorted(lines)
        f1_logic_by_file[f] = sorted(logic_lines)

    print(f"F1 concluído. Módulos com lógica executada em F1: {sum(1 for v in f1_logic_by_file.values() if len(v) > 0)}")

    # Check governor identity
    import interface.telemetry_api
    gov_is_tel = server._governor is interface.telemetry_api.mcp_governor
    gov_id = id(server._governor)
    tel_gov_id = id(interface.telemetry_api.mcp_governor)
    gov_mod = type(server._governor).__module__

    # Instrument methods of target modules to track callers
    # 1. core.mcp_governor.MCPToolGovernor
    from core.mcp_governor import MCPToolGovernor
    orig_val_tool = MCPToolGovernor.validate_tool_execution
    def wrapped_val_tool(self, *args, **kwargs):
        record_call("core/mcp_governor.py", "validate_tool_execution")
        return orig_val_tool(self, *args, **kwargs)
    MCPToolGovernor.validate_tool_execution = wrapped_val_tool

    orig_set_state = MCPToolGovernor.set_session_state
    def wrapped_set_state(self, *args, **kwargs):
        record_call("core/mcp_governor.py", "set_session_state")
        return orig_set_state(self, *args, **kwargs)
    MCPToolGovernor.set_session_state = wrapped_set_state

    # 2. core.checkpointer.AgnosticCheckpointer
    from core.checkpointer import AgnosticCheckpointer
    orig_save_chk = AgnosticCheckpointer.save_checkpoint
    def wrapped_save_chk(self, *args, **kwargs):
        record_call("core/checkpointer.py", "save_checkpoint")
        return orig_save_chk(self, *args, **kwargs)
    AgnosticCheckpointer.save_checkpoint = wrapped_save_chk

    orig_load_chk = AgnosticCheckpointer.load_checkpoint
    def wrapped_load_chk(self, *args, **kwargs):
        record_call("core/checkpointer.py", "load_checkpoint")
        return orig_load_chk(self, *args, **kwargs)
    AgnosticCheckpointer.load_checkpoint = wrapped_load_chk

    orig_list_chk = AgnosticCheckpointer.list_checkpoints
    def wrapped_list_chk(self, *args, **kwargs):
        record_call("core/checkpointer.py", "list_checkpoints")
        return orig_list_chk(self, *args, **kwargs)
    AgnosticCheckpointer.list_checkpoints = wrapped_list_chk

    # =========================================================================
    # PREPARAÇÃO PARA FASE 2: POPULAÇÃO
    # =========================================================================
    # Register project
    reg_res = await server._mcp.call_tool("concierge_register", {"project_path": fixture_dir, "summary": "Fixture Project"})
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT uuid FROM projects ORDER BY rowid DESC LIMIT 1")
    proj_uuid = cur.fetchone()[0]

    # Mine project
    try:
        await server._mcp.call_tool("concierge_mine", {"path": fixture_dir, "project_identifier": proj_uuid, "auto_tag": True})
    except Exception:
        pass

    # Store fact
    try:
        await server._mcp.call_tool("concierge_store_fact", {
            "scope_type": "session",
            "scope_id": "test_sess",
            "fact_statement": "CalculatorService integrates compute_total."
        })
    except Exception:
        pass

    # Query DB for node and symbol IDs
    cur.execute("SELECT id FROM nodes LIMIT 1")
    row_node = cur.fetchone()
    file_node_id = row_node[0] if row_node else 1

    cur.execute("SELECT id FROM nodes WHERE node_type IN ('FUNCTION', 'CLASS', 'SYMBOL', 'METHOD') LIMIT 1")
    row_sym = cur.fetchone()
    symbol_node_id = row_sym[0] if row_sym else 1

    cur.execute("SELECT id FROM semantic_facts ORDER BY id DESC LIMIT 1")
    row_fact = cur.fetchone()
    fact_id = row_fact[0] if row_fact else 1
    conn.close()

    print(f"IDs obtidos do banco: node_id={file_node_id}, symbol_id={symbol_node_id}, fact_id={fact_id}")

    # =========================================================================
    # FASE 2 (F2): EXECUÇÃO DAS FERRAMENTAS DO PASSO 1
    # =========================================================================
    print("\n--- INICIANDO MEDIÇÃO FASE 2 (F2): EXECUÇÃO DE TODAS AS FERRAMENTAS ---")
    cov_f2 = coverage.Coverage(source=["."], branch=False)
    cov_f2.start()

    # Run tool executions in Estado P
    tools_calls = [
        ("concierge_list_projects", {}),
        ("concierge_status", {"project_uuid": proj_uuid}),
        ("get_full_topology", {"project_identifier": proj_uuid}),
        ("count_embeddings", {"project_identifier": proj_uuid}),
        ("concierge_search", {"query": "compute_total", "project_identifier": proj_uuid}),
        ("search_symbols", {"query": "add", "project_uuid": proj_uuid}),
        ("get_implementations", {"symbol_id": symbol_node_id}),
        ("get_callers", {"symbol_id": symbol_node_id}),
        ("concierge_load", {"node_id": file_node_id}),
        ("concierge_wakeup", {"project_uuid": proj_uuid}),
        ("concierge_resume", {"project_uuid": proj_uuid}),
        ("concierge_set_state", {"state_name": "EXECUTION", "session_id": "default"}),
        ("concierge_store_fact", {"scope_type": "session", "scope_id": "test_sess", "fact_statement": "Fato adicional F2"}),
        ("concierge_list_facts", {"scope_type": "session", "scope_id": "test_sess"}),
        ("concierge_set_memory", {"scope_type": "session", "scope_id": "test_sess", "block_label": "notes", "content": "Nota F2"}),
        ("concierge_get_memory", {"scope_type": "session", "scope_id": "test_sess"}),
        ("concierge_feedback", {"fact_id": fact_id, "was_useful": True}),
        ("find_similar", {"project_identifier": proj_uuid}),
        ("get_trajectories", {"project_identifier": proj_uuid}),
        ("add_reference_wing", {"project_identifier": proj_uuid, "wing_name": "WING_TEST"}),
        ("remove_reference_wing", {"project_identifier": proj_uuid, "wing_name": "WING_TEST"}),
        ("update_project", {"project_identifier": proj_uuid, "summary": "Projeto Fixture Atualizado F2"}),
        ("agent_save_checkpoint", {"agent_id": "test_agent_1", "session_id": "sess_p", "checkpoint_id": "chk_f2", "state_dict": {"step": "f2"}}),
        ("agent_get_checkpoint", {"agent_id": "test_agent_1", "session_id": "sess_p", "checkpoint_id": "chk_p"}),
        ("agent_list_checkpoints", {"agent_id": "test_agent_1", "session_id": "sess_p"}),
        ("concierge_commit", {"project_uuid": proj_uuid, "phase": "TEST", "technical_changes": "Commit F2", "updated_pointers": ["math_ops.py"]}),
        ("concierge_register", {"project_path": fixture_dir, "summary": "Registro F2"}),
        ("concierge_mine", {"path": fixture_dir, "project_identifier": proj_uuid, "auto_tag": True}),
        ("concierge_get_call_chain", {"start_node": "calc.py", "depth_limit": 3}),
        # Dangerous tools in EXECUTION
        ("reset_collection", {}),
        ("delete_project", {"project_identifier": proj_uuid}),
    ]

    for tname, args in tools_calls:
        try:
            await server._mcp.call_tool(tname, args)
        except Exception:
            pass

    # Now change state to MAINTENANCE and call dangerous tools
    try:
        await server._mcp.call_tool("concierge_set_state", {"state_name": "MAINTENANCE", "session_id": "default"})
        await server._mcp.call_tool("reset_collection", {})
        await server._mcp.call_tool("delete_project", {"project_identifier": proj_uuid})
    except Exception:
        pass

    cov_f2.stop()
    cov_f2.save()
    f2_data = cov_f2.get_data()

    # Restore original methods
    MCPToolGovernor.validate_tool_execution = orig_val_tool
    MCPToolGovernor.set_session_state = orig_set_state
    AgnosticCheckpointer.save_checkpoint = orig_save_chk
    AgnosticCheckpointer.load_checkpoint = orig_load_chk
    AgnosticCheckpointer.list_checkpoints = orig_list_chk

    f2_lines_by_file = {}
    f2_logic_by_file = {}
    for f in prod_files:
        abs_p = os.path.abspath(f)
        lines = f2_data.lines(abs_p) or []
        body_lines = file_ast_info[f]["body_lines"]
        logic_lines = set(lines) & body_lines
        f2_lines_by_file[f] = sorted(lines)
        f2_logic_by_file[f] = sorted(logic_lines)

    print(f"F2 concluído. Módulos com lógica executada em F2: {sum(1 for v in f2_logic_by_file.values() if len(v) > 0)}")

    # =========================================================================
    # CLASSIFICAÇÃO AUTOMATIZADA DOS 64 MÓDULOS
    # =========================================================================
    # Classes:
    # EXECUTADO EM F2 (lógica rodou ao servir ferramentas)
    # EXECUTADO SÓ EM F1 (lógica rodou apenas no boot)
    # SÓ CARREGADO (nenhuma lógica rodou)
    # NÃO CARREGADO
    loaded_sys_modules = set(sys.modules.keys())

    classification = {}
    class_counts = defaultdict(int)

    for f in prod_files:
        mod_name = file_ast_info[f]["module"]
        f2_logic = len(f2_logic_by_file[f])
        f1_logic = len(f1_logic_by_file[f])
        f1_total = len(f1_lines_by_file[f])
        f2_total = len(f2_lines_by_file[f])
        is_in_sys = mod_name in loaded_sys_modules

        if f2_logic > 0:
            cls = "EXECUTADO EM F2"
        elif f1_logic > 0:
            cls = "EXECUTADO SÓ EM F1"
        elif is_in_sys or f1_total > 0 or f2_total > 0:
            cls = "SÓ CARREGADO"
        else:
            cls = "NÃO CARREGADO"

        classification[f] = {
            "module": mod_name,
            "status": cls,
            "f1_logic_lines": f1_logic,
            "f2_logic_lines": f2_logic,
            "f1_total_lines": f1_total,
            "f2_total_lines": f2_total,
            "in_sys_modules": is_in_sys,
        }
        class_counts[cls] += 1

    print("\n--- DISTRIBUIÇÃO DOS 64 MÓDULOS ---")
    for cls, cnt in sorted(class_counts.items()):
        print(f"  {cls:20s}: {cnt}")

    # =========================================================================
    # ANÁLISE DOS 4 MÓDULOS ESPECÍFICOS
    # =========================================================================
    target_rel_files = [
        "interface/telemetry_api.py",
        "core/mcp_governor.py",
        "core/checkpointer.py",
        "core/security_guard.py"
    ]
    target_analysis = {}
    for rel_f in target_rel_files:
        mod_name = file_ast_info[rel_f]["module"]
        executed_funcs_f1 = set()
        for fname, lines in file_ast_info[rel_f]["func_map"].items():
            if set(lines) & set(f1_logic_by_file[rel_f]):
                executed_funcs_f1.add(fname)
        
        executed_funcs_f2 = set()
        for fname, lines in file_ast_info[rel_f]["func_map"].items():
            if set(lines) & set(f2_logic_by_file[rel_f]):
                executed_funcs_f2.add(fname)

        calls = {}
        for (mod_key, func_key), data in call_records.items():
            if mod_key == rel_f:
                calls[func_key] = {
                    "count": data["count"],
                    "callers": sorted(list(data["callers"]))
                }

        target_analysis[rel_f] = {
            "module": mod_name,
            "status": classification[rel_f]["status"],
            "f1_logic_lines": classification[rel_f]["f1_logic_lines"],
            "f2_logic_lines": classification[rel_f]["f2_logic_lines"],
            "executed_funcs_f1": sorted(executed_funcs_f1),
            "executed_funcs_f2": sorted(executed_funcs_f2),
            "calls_recorded": calls,
        }

    governor_proof = {
        "server_governor_is_telemetry_mcp_governor": gov_is_tel,
        "server_governor_id": gov_id,
        "telemetry_mcp_governor_id": tel_gov_id,
        "governor_class_module": gov_mod,
    }

    # =========================================================================
    # DIVERGÊNCIAS EM RELAÇÃO À 4.0b
    # =========================================================================
    old_matrix_file = "scratch/modules_execution_matrix.json"
    divergences = []
    if os.path.exists(old_matrix_file):
        with open(old_matrix_file, "r", encoding="utf-8") as fp:
            old_data = json.load(fp)
        old_classes = {item.get("filepath", item.get("file")): item.get("classification", item.get("status_execucao")) for item in old_data}
        
        for f, cur in classification.items():
            old_cls = old_classes.get(f)
            if old_cls != cur["status"]:
                divergences.append({
                    "file": f,
                    "module": cur["module"],
                    "status_4_0b": old_cls,
                    "status_4_0c": cur["status"],
                    "f1_logic": cur["f1_logic_lines"],
                    "f2_logic": cur["f2_logic_lines"],
                })

    # Save output
    output = {
        "summary": dict(class_counts),
        "governor_proof": governor_proof,
        "target_analysis": target_analysis,
        "divergences_vs_4_0b": divergences,
        "modules": classification
    }

    with open("scratch/fase4_0c_module_status_results.json", "w", encoding="utf-8") as fp:
        json.dump(output, fp, indent=2, ensure_ascii=False)

    print(f"\nResultados salvos em scratch/fase4_0c_module_status_results.json")
    print(f"Total de divergências em relação à 4.0b: {len(divergences)}")
    for d in divergences:
        print(f"  - {d['file']}: 4.0b={d['status_4_0b']} -> 4.0c={d['status_4_0c']} (f1={d['f1_logic']}, f2={d['f2_logic']})")

    # Cleanup temp
    store.close()
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("Workspace temporário removido.")

if __name__ == "__main__":
    asyncio.run(main_probe())
