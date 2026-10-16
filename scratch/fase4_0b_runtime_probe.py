import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tempfile
import shutil
import sqlite3
import asyncio
import json
from pathlib import Path

PROJECT_PACKAGES = ("core", "interface", "ingestion", "services", "storage", "agent", "agents")

def get_loaded_project_modules():
    mods = set()
    for name in sys.modules:
        if any(name == pkg or name.startswith(pkg + ".") for pkg in PROJECT_PACKAGES):
            mods.add(name)
    return sorted(mods)

def check_db_tables(db_path):
    if not os.path.exists(db_path):
        return {"tables": [], "counts": {}}
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get business tables
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
          AND name NOT LIKE 'sqlite_%' 
          AND name NOT LIKE '%_fts%' 
          AND name NOT LIKE '%_docsize' 
          AND name NOT LIKE '%_config' 
          AND name NOT LIKE '%_idx' 
          AND name NOT LIKE '%_content' 
          AND name NOT LIKE '%_data'
        ORDER BY name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    targets = [
        "nodes", "edges", "semantic_facts", "files", 
        "communities", "ast_edges", "agent_checkpoints", "fsm_checkpoints"
    ]
    counts = {}
    for t in targets:
        if t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception as e:
                counts[t] = f"erro: {e}"
        else:
            counts[t] = "tabela ausente"
            
    conn.close()
    return {"tables": tables, "counts": counts}

async def run_probe():
    temp_dir = tempfile.mkdtemp(prefix="fase4_0b_probe_")
    print(f"Temporary workspace: {temp_dir}")
    
    db_path = os.path.join(temp_dir, "probe_concierge.db")
    chroma_path = os.path.join(temp_dir, "probe_chroma")
    
    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "probe_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
    
    # Assert isolation
    assert db_path.startswith(temp_dir), f"DB path {db_path} outside temp_dir!"
    assert chroma_path.startswith(temp_dir), f"Chroma path {chroma_path} outside temp_dir!"
    
    # Create fixture project
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
        
    print("Fixture project created with 3 .py files and 1 .md file.")
    
    # Bootstrap
    import main
    server, janitor, store = main.bootstrap()
    
    # Verify tools registered
    tools_list = server._mcp._tool_manager.list_tools()
    tool_names = [t.name for t in tools_list]
    print(f"Registered tools ({len(tool_names)}): {tool_names}")
    assert len(tool_names) == 31, f"Expected 31 tools, found {len(tool_names)}"
    
    # Moment A: Modules after bootstrap
    modules_moment_a = get_loaded_project_modules()
    
    # Inspect DB after bootstrap (State L)
    db_state_l = check_db_tables(db_path)
    print("\n--- Estado L: Tabelas e Contagens ---")
    print("Tabelas existentes:", db_state_l["tables"])
    for t, cnt in db_state_l["counts"].items():
        print(f"  - {t}: {cnt}")
        
    # Order of tools execution
    # We call non-destructive first, and delete_project / reset_collection LAST
    ordered_tools = [
        "concierge_list_projects",
        "concierge_status",
        "get_full_topology",
        "count_embeddings",
        "concierge_search",
        "search_symbols",
        "get_implementations",
        "get_callers",
        "concierge_get_call_chain",
        "concierge_load",
        "concierge_wakeup",
        "concierge_resume",
        "concierge_set_state",
        "concierge_store_fact",
        "concierge_list_facts",
        "concierge_set_memory",
        "concierge_get_memory",
        "concierge_feedback",
        "find_similar",
        "get_trajectories",
        "add_reference_wing",
        "remove_reference_wing",
        "update_project",
        "agent_save_checkpoint",
        "agent_get_checkpoint",
        "agent_list_checkpoints",
        "concierge_commit",
        "concierge_register",
        "concierge_mine",
        "reset_collection",
        "delete_project",
    ]
    
    def get_args_for_tool(tname, state, registered_uuid=None):
        if tname == "concierge_list_projects":
            return {}
        elif tname == "concierge_status":
            return {"project_uuid": registered_uuid or "00000000-0000-0000-0000-000000000000"}
        elif tname == "get_full_topology":
            return {"project_identifier": registered_uuid or "test_proj"}
        elif tname == "count_embeddings":
            return {"project_identifier": registered_uuid or "test_proj"}
        elif tname == "concierge_search":
            return {"query": "compute_total"}
        elif tname == "search_symbols":
            return {"query": "add", "project_uuid": registered_uuid or "00000000-0000-0000-0000-000000000000"}
        elif tname == "get_implementations":
            return {"symbol_id": "compute_total"}
        elif tname == "get_callers":
            return {"symbol_id": "add"}
        elif tname == "concierge_get_call_chain":
            return {"start_node": "calc.py", "depth_limit": 3}
        elif tname == "concierge_load":
            return {"node_id": "math_ops.py"}
        elif tname == "concierge_wakeup":
            return {"project_uuid": registered_uuid or "00000000-0000-0000-0000-000000000000"}
        elif tname == "concierge_resume":
            return {"project_uuid": registered_uuid or "00000000-0000-0000-0000-000000000000"}
        elif tname == "concierge_set_state":
            return {"state_name": "ANALYSIS", "session_id": "default"}
        elif tname == "concierge_store_fact":
            return {"scope_type": "project", "scope_id": registered_uuid or "test_proj", "fact_statement": "Fixture uses add"}
        elif tname == "concierge_list_facts":
            return {"scope_type": "project", "scope_id": registered_uuid or "test_proj"}
        elif tname == "concierge_set_memory":
            return {"scope_type": "project", "scope_id": registered_uuid or "test_proj", "block_label": "notes", "content": "Sample note"}
        elif tname == "concierge_get_memory":
            return {"scope_type": "project", "scope_id": registered_uuid or "test_proj"}
        elif tname == "concierge_feedback":
            return {"fact_id": 1, "was_useful": True}
        elif tname == "find_similar":
            return {"project_identifier": registered_uuid or "test_proj"}
        elif tname == "get_trajectories":
            return {"project_identifier": registered_uuid or "test_proj"}
        elif tname == "add_reference_wing":
            return {"project_identifier": registered_uuid or "test_proj", "wing_name": "WING_TEST"}
        elif tname == "remove_reference_wing":
            return {"project_identifier": registered_uuid or "test_proj", "wing_name": "WING_TEST"}
        elif tname == "update_project":
            return {"project_identifier": registered_uuid or "test_proj", "summary": "Updated summary"}
        elif tname == "agent_save_checkpoint":
            return {"agent_id": "probe_agent", "session_id": "probe_sess", "checkpoint_id": "chk_1", "state_dict": {"k": "v"}}
        elif tname == "agent_get_checkpoint":
            return {"agent_id": "probe_agent", "session_id": "probe_sess", "checkpoint_id": "chk_1"}
        elif tname == "agent_list_checkpoints":
            return {"agent_id": "probe_agent", "session_id": "probe_sess"}
        elif tname == "concierge_commit":
            return {
                "project_uuid": registered_uuid or "00000000-0000-0000-0000-000000000000",
                "phase": "TEST",
                "technical_changes": "Initial test commit",
                "updated_pointers": []
            }
        elif tname == "concierge_register":
            return {"project_path": fixture_dir, "wing": "DEFAULT", "privacy_level": "INTERNAL", "summary": "Fixture project"}
        elif tname == "concierge_mine":
            return {"path": fixture_dir, "project_identifier": registered_uuid or fixture_dir, "auto_tag": True}
        elif tname == "reset_collection":
            return {}
        elif tname == "delete_project":
            return {"project_identifier": registered_uuid or "nonexistent_proj"}
        return {}

    async def execute_tool(tname, args):
        try:
            res = await server._mcp.call_tool(tname, args)
            # res can be ContentBlock or dict or list
            # parse response
            res_str = str(res)
            # check if governor denied
            if "Tool denied" in res_str or "denied by governor" in res_str.lower():
                return "NEGADO pelo governor", res_str[:200], False
            # check if contains error text
            if "no such table" in res_str.lower():
                return "EXCEÇÃO", res_str[:200], True
            if "error" in res_str.lower() and ("failed" in res_str.lower() or "traceback" in res_str.lower() or "exception" in res_str.lower()):
                return "EXCEÇÃO", res_str[:200], False
            # check empty vs com dados
            is_empty = False
            if res == [] or res == {} or res == "" or res_str == "[]" or res_str == "{}" or res_str == "[TextContent(type='text', text='[]')]" or res_str == "[TextContent(type='text', text='{}')]":
                is_empty = True
            elif "[]" in res_str or "total': 0" in res_str or "results': []" in res_str or "count': 0" in res_str:
                is_empty = True
                
            status = "OK vazio" if is_empty else "OK com dados"
            return status, res_str[:200], False
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            has_no_such = "no such table" in err.lower()
            return "EXCEÇÃO", err[:200], has_no_such

    # 1. ESTADO L
    print("\nExecutando 31 ferramentas no Estado L...")
    results_l = {}
    for tname in ordered_tools:
        args = get_args_for_tool(tname, "L")
        st, msg, no_such = await execute_tool(tname, args)
        results_l[tname] = {"status": st, "msg": msg, "no_such_table": no_such, "args": args}
        print(f"  [L] {tname:28s} -> {st} (no_such_table={no_such}) | {msg[:100]}")

    # 2. ESTADO P (População)
    print("\nPopulando banco para Estado P...")
    # Register fixture project
    reg_res = await server._mcp.call_tool("concierge_register", {"project_path": fixture_dir, "summary": "Fixture Project"})
    print("Register result:", reg_res)
    # extract project uuid
    reg_str = str(reg_res)
    proj_uuid = None
    try:
        # try to parse json from text if present
        if hasattr(reg_res, '__iter__') and len(reg_res) > 0 and hasattr(reg_res[0], 'text'):
            data = json.loads(reg_res[0].text)
            proj_uuid = data.get("uuid") or data.get("project_uuid")
    except Exception:
        pass
    if not proj_uuid:
        # lookup in projects table
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT uuid FROM projects ORDER BY rowid DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            proj_uuid = row[0]
        conn.close()
    print(f"Registered project UUID: {proj_uuid}")

    # Mine project
    print("Mining fixture project...")
    mine_res = await server._mcp.call_tool("concierge_mine", {"path": fixture_dir, "project_identifier": proj_uuid or fixture_dir})
    print("Mine result:", str(mine_res)[:200])

    # Store fact & Save checkpoint
    await server._mcp.call_tool("concierge_store_fact", {
        "scope_type": "project",
        "scope_id": proj_uuid or "test_proj",
        "fact_statement": "CalculatorService integrates compute_total and math operations."
    })
    await server._mcp.call_tool("agent_save_checkpoint", {
        "agent_id": "test_agent_1",
        "session_id": "sess_p",
        "checkpoint_id": "chk_init",
        "state_dict": {"step": "ingestion_complete", "status": "active"}
    })

    # Check DB tables and counts in State P before queries
    db_state_p = check_db_tables(db_path)
    print("\n--- Estado P: Tabelas e Contagens ---")
    print("Tabelas existentes:", db_state_p["tables"])
    for t, cnt in db_state_p["counts"].items():
        print(f"  - {t}: {cnt}")

    # Execute all tools in Estado P
    print("\nExecutando 31 ferramentas no Estado P...")
    results_p = {}
    for tname in ordered_tools:
        args = get_args_for_tool(tname, "P", registered_uuid=proj_uuid)
        st, msg, no_such = await execute_tool(tname, args)
        results_p[tname] = {"status": st, "msg": msg, "no_such_table": no_such, "args": args}
        print(f"  [P] {tname:28s} -> {st} (no_such_table={no_such}) | {msg[:100]}")

    # Moment B: Modules after calling all tools
    modules_moment_b = get_loaded_project_modules()

    # Save full probe results to scratch
    output_data = {
        "modules_moment_a": modules_moment_a,
        "modules_moment_b": modules_moment_b,
        "new_modules_after_tools": sorted(list(set(modules_moment_b) - set(modules_moment_a))),
        "db_state_l": db_state_l,
        "db_state_p": db_state_p,
        "results_l": results_l,
        "results_p": results_p,
    }
    
    with open("scratch/probe_runtime_results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nProbe execution finished. Data saved to scratch/probe_runtime_results.json")
    print(f"Modules in A: {len(modules_moment_a)}, Modules in B: {len(modules_moment_b)}")
    print(f"New modules loaded between A and B: {output_data['new_modules_after_tools']}")

    # Clean up temp
    store.close()
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("Temporary directory cleaned up.")

if __name__ == "__main__":
    asyncio.run(run_probe())
