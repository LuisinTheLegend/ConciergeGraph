import os
import sys

PROJECT_ROOT = os.path.abspath(".")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tempfile
import shutil
import sqlite3
import asyncio
import json
import inspect
from pathlib import Path

# Ensure isolation
def check_db_tables(db_path):
    if not os.path.exists(db_path):
        return {"tables": [], "counts": {}}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
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
        "communities", "ast_edges", "agent_checkpoints", "fsm_checkpoints",
        "projects", "commit_log", "user_core_memory"
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

async def run_tool_matrix():
    temp_dir = tempfile.mkdtemp(prefix="fase4_0c_matrix_")
    print(f"=== FASE 4.0c: MATRIZ DE FERRAMENTAS 31x2 REFEITA ===")
    print(f"Workspace temporario: {temp_dir}")

    db_path = os.path.join(temp_dir, "probe_concierge.db")
    chroma_path = os.path.join(temp_dir, "probe_chroma")

    os.environ["GRAFO_DB_PATH"] = db_path
    os.environ["GRAFO_CHROMA_PATH"] = chroma_path
    os.environ["GRAFO_CHROMA_COLLECTION"] = "fase4_0c_collection"
    os.environ["GRAFO_TRANSPORT"] = "stdio"
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"

    assert db_path.startswith(temp_dir), f"DB fora do temp_dir: {db_path}"
    assert chroma_path.startswith(temp_dir), f"Chroma fora do temp_dir: {chroma_path}"

    # Fixture
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

    # Bootstrap
    import main
    server, janitor, store = main.bootstrap()

    tools_list = server._mcp._tool_manager.list_tools()
    tool_names = [t.name for t in tools_list]
    print(f"Ferramentas registradas ({len(tool_names)}): {tool_names}")
    assert len(tool_names) == 31, f"Esperado 31 ferramentas, encontrado {len(tool_names)}"

    # Check governor identity
    import interface.telemetry_api
    gov_from_telemetry = server._governor is interface.telemetry_api.mcp_governor
    print(f"Governor origin check: server._governor is telemetry_api.mcp_governor -> {gov_from_telemetry}")
    print(f"server._governor id: {id(server._governor)}, telemetry_api.mcp_governor id: {id(interface.telemetry_api.mcp_governor)}")

    # Ordered tools for execution
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

    def parse_mcp_response(res_raw):
        """Extract parsed JSON object from MCP response, or return dict."""
        while isinstance(res_raw, (list, tuple)) and len(res_raw) > 0:
            res_raw = res_raw[0]
        if hasattr(res_raw, "text"):
            try:
                return json.loads(res_raw.text)
            except Exception:
                return {"raw_text": res_raw.text}
        if isinstance(res_raw, str):
            try:
                return json.loads(res_raw)
            except Exception:
                return {"raw_str": res_raw}
        if isinstance(res_raw, dict):
            return res_raw
        return {"raw": str(res_raw)}

    def classify_response(res_raw, exc=None):
        """
        Five discrete classes:
        1. SUCESSO COM DADOS
        2. SUCESSO VAZIO
        3. ERRO DE NEGÓCIO (success:false, com a mensagem)
        4. EXCEÇÃO (com o tipo)
        5. NEGADO PELO GOVERNOR
        """
        if exc is not None:
            err_str = str(exc)
            exc_type = type(exc).__name__
            if "SecurityException" in exc_type or "Access denied" in err_str or "blocked during state" in err_str:
                return "NEGADO PELO GOVERNOR", err_str
            return "EXCEÇÃO", f"{exc_type}: {err_str}"

        parsed = parse_mcp_response(res_raw)
        
        # Check if governor denied returned as dict
        if isinstance(parsed, dict):
            if parsed.get("success") is False:
                msg = parsed.get("error") or parsed.get("message") or str(parsed)
                if "Access denied" in msg or "blocked during state" in msg:
                    return "NEGADO PELO GOVERNOR", msg
                return "ERRO DE NEGÓCIO", msg
            
            if "error" in parsed and not parsed.get("success", True):
                return "ERRO DE NEGÓCIO", parsed.get("error")

            # Check emptiness
            if parsed == {} or parsed == []:
                return "SUCESSO VAZIO", str(parsed)
            
            # Check specific tools payload emptiness
            if "projects" in parsed and not parsed["projects"]:
                return "SUCESSO VAZIO", str(parsed)
            if "symbols" in parsed and len(parsed["symbols"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "nodes" in parsed and len(parsed["nodes"]) == 0 and len(parsed.get("edges", [])) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "facts" in parsed and len(parsed["facts"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "blocks" in parsed and len(parsed["blocks"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "callers" in parsed and len(parsed["callers"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "implementation" in parsed and not parsed["implementation"]:
                return "SUCESSO VAZIO", str(parsed)
            if "trajectories" in parsed and len(parsed["trajectories"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "similar" in parsed and len(parsed["similar"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "results" in parsed and len(parsed["results"]) == 0:
                return "SUCESSO VAZIO", str(parsed)
            if parsed.get("count") == 0 or parsed.get("total") == 0:
                return "SUCESSO VAZIO", str(parsed)
            if "files_processed" in parsed and parsed.get("files_processed") == 0 and parsed.get("nodes_created") == 0:
                return "SUCESSO VAZIO", str(parsed)

            return "SUCESSO COM DADOS", str(parsed)
        
        return "SUCESSO COM DADOS", str(parsed)

    async def execute_tool(tname, args):
        assert db_path.startswith(temp_dir), f"Segurança: DB {db_path} fora de {temp_dir}"
        assert chroma_path.startswith(temp_dir), f"Segurança: Chroma {chroma_path} fora de {temp_dir}"
        try:
            res = await server._mcp.call_tool(tname, args)
            cls, detail = classify_response(res)
            return cls, detail, parse_mcp_response(res)
        except Exception as e:
            cls, detail = classify_response(None, exc=e)
            return cls, detail, {"exception": str(e), "type": type(e).__name__}

    # Inspect tool signatures
    tool_signatures = {}
    for t in tools_list:
        tool_signatures[t.name] = {
            "parameters": t.parameters,
            "description": t.description
        }

    # =========================================================================
    # ESTADO L: BANCO LIMPO
    # =========================================================================
    print("\n--- EXECUTANDO ESTADO L (BANCO LIMPO) ---")
    db_state_l = check_db_tables(db_path)
    print("Tabelas no Estado L:", db_state_l["tables"])

    args_used_l = {
        "concierge_list_projects": {},
        "concierge_status": {"project_uuid": "00000000-0000-0000-0000-000000000000"},
        "get_full_topology": {},
        "count_embeddings": {},
        "concierge_search": {"query": "compute_total", "all_wings": True},
        "search_symbols": {"query": "add"},
        "get_implementations": {"symbol_id": 1},
        "get_callers": {"symbol_id": 1},
        "concierge_get_call_chain": {"start_node": "calc.py", "depth_limit": 3},
        "concierge_load": {"node_id": 1},
        "concierge_wakeup": {"project_uuid": "00000000-0000-0000-0000-000000000000"},
        "concierge_resume": {"project_uuid": "00000000-0000-0000-0000-000000000000"},
        "concierge_set_state": {"state_name": "EXECUTION", "session_id": "default"},
        "concierge_store_fact": {"scope_type": "session", "scope_id": "test_sess", "fact_statement": "Fato inicial em L"},
        "concierge_list_facts": {"scope_type": "session", "scope_id": "test_sess"},
        "concierge_set_memory": {"scope_type": "session", "scope_id": "test_sess", "block_label": "notes", "content": "Nota em L"},
        "concierge_get_memory": {"scope_type": "session", "scope_id": "test_sess"},
        "concierge_feedback": {"fact_id": 1, "was_useful": True},
        "find_similar": {"project_identifier": "00000000-0000-0000-0000-000000000000"},
        "get_trajectories": {"project_identifier": "00000000-0000-0000-0000-000000000000"},
        "add_reference_wing": {"project_identifier": "00000000-0000-0000-0000-000000000000", "wing_name": "WING_TEST"},
        "remove_reference_wing": {"project_identifier": "00000000-0000-0000-0000-000000000000", "wing_name": "WING_TEST"},
        "update_project": {"project_identifier": "00000000-0000-0000-0000-000000000000", "summary": "Atualizacao em L"},
        "agent_save_checkpoint": {"agent_id": "test_agent_1", "session_id": "sess_l", "checkpoint_id": "chk_l", "state_dict": {"init": True}},
        "agent_get_checkpoint": {"agent_id": "test_agent_1", "session_id": "sess_l", "checkpoint_id": "chk_l"},
        "agent_list_checkpoints": {"agent_id": "test_agent_1", "session_id": "sess_l"},
        "concierge_commit": {
            "project_uuid": "00000000-0000-0000-0000-000000000000",
            "phase": "TEST",
            "technical_changes": "Commit em L",
            "updated_pointers": ["file1.py"]
        },
        "concierge_register": {"project_path": fixture_dir, "summary": "Projeto Fixture L"},
        "concierge_mine": {"path": fixture_dir, "project_identifier": "00000000-0000-0000-0000-000000000000", "auto_tag": True},
        "reset_collection": {},
        "delete_project": {"project_identifier": "00000000-0000-0000-0000-000000000000"},
    }

    results_l = {}
    for tname in ordered_tools:
        args = args_used_l[tname]
        cls, detail, parsed = await execute_tool(tname, args)
        results_l[tname] = {"class": cls, "detail": detail[:150], "parsed": parsed, "args": args}
        print(f"  [L] {tname:28s} -> {cls:22s} | {detail[:80]}")

    # =========================================================================
    # POPULAÇÃO PARA ESTADO P
    # =========================================================================
    print("\n--- POPULANDO BANCO PARA ESTADO P ---")
    
    # 1. Register project
    reg_res = await server._mcp.call_tool("concierge_register", {"project_path": fixture_dir, "summary": "Fixture Project Populated"})
    reg_parsed = parse_mcp_response(reg_res)
    proj_uuid = reg_parsed.get("project_uuid") or reg_parsed.get("uuid")
    print(f"Projeto registrado: UUID={proj_uuid}")

    # 2. Mine project (1ª Execução)
    print("Executando concierge_mine pela 1ª vez...")
    mine_1_res = await server._mcp.call_tool("concierge_mine", {"path": fixture_dir, "project_identifier": proj_uuid, "auto_tag": True})
    mine_1_parsed = parse_mcp_response(mine_1_res)
    print(f"Retorno mine (1ª vez): files_processed={mine_1_parsed.get('files_processed')}, nodes_created={mine_1_parsed.get('nodes_created')}, files_skipped={mine_1_parsed.get('files_skipped')}")

    # 3. Mine project (2ª Execução - Idempotência)
    print("Executando concierge_mine pela 2ª vez (teste de idempotencia)...")
    mine_2_res = await server._mcp.call_tool("concierge_mine", {"path": fixture_dir, "project_identifier": proj_uuid, "auto_tag": True})
    mine_2_parsed = parse_mcp_response(mine_2_res)
    print(f"Retorno mine (2ª vez): files_processed={mine_2_parsed.get('files_processed')}, nodes_created={mine_2_parsed.get('nodes_created')}, files_skipped={mine_2_parsed.get('files_skipped')}")

    # 4. Store Fact
    fact_res = await server._mcp.call_tool("concierge_store_fact", {
        "scope_type": "session",
        "scope_id": "test_sess",
        "fact_statement": "CalculatorService integrates compute_total and math operations."
    })
    fact_parsed = parse_mcp_response(fact_res)
    print(f"Fato gravado: success={fact_parsed.get('success')}")

    # 5. Save Checkpoint (expected failure due to missing table)
    chk_res = await server._mcp.call_tool("agent_save_checkpoint", {
        "agent_id": "test_agent_1",
        "session_id": "sess_p",
        "checkpoint_id": "chk_p",
        "state_dict": {"step": "populated", "status": "active"}
    })
    chk_parsed = parse_mcp_response(chk_res)
    print(f"Checkpoint gravado: success={chk_parsed.get('success')}, msg={chk_parsed.get('message')}")

    # Query DB for real IDs
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, node_type, label FROM nodes WHERE node_type='FILE' LIMIT 1")
    file_node = cur.fetchone()
    file_node_id = file_node[0] if file_node else 1

    cur.execute("SELECT id, node_type, label FROM nodes WHERE node_type IN ('FUNCTION', 'CLASS', 'SYMBOL') LIMIT 1")
    symbol_node = cur.fetchone()
    symbol_node_id = symbol_node[0] if symbol_node else 2

    cur.execute("SELECT id, fact_statement FROM semantic_facts ORDER BY id DESC LIMIT 1")
    fact_row = cur.fetchone()
    real_fact_id = fact_row[0] if fact_row else 1
    conn.close()

    print(f"IDs obtidos do banco temporario: file_node_id={file_node_id} ({file_node}), symbol_node_id={symbol_node_id} ({symbol_node}), real_fact_id={real_fact_id}")

    # Check DB tables and counts in State P
    db_state_p = check_db_tables(db_path)
    print("\n--- ESTADO P: TABELAS E CONTAGENS ---")
    print("Tabelas existentes:", db_state_p["tables"])
    for t, cnt in db_state_p["counts"].items():
        print(f"  - {t}: {cnt}")

    # =========================================================================
    # ESTADO P: MATRIZ DE FERRAMENTAS COM ARGUMENTOS VÁLIDOS
    # =========================================================================
    print("\n--- EXECUTANDO ESTADO P (COM ARGUMENTOS VÁLIDOS) ---")

    args_used_p = {
        "concierge_list_projects": {},
        "concierge_status": {"project_uuid": proj_uuid},
        "get_full_topology": {"project_identifier": proj_uuid},
        "count_embeddings": {"project_identifier": proj_uuid},
        "concierge_search": {"query": "compute_total", "project_identifier": proj_uuid},
        "search_symbols": {"query": "add", "project_uuid": proj_uuid},
        "get_implementations": {"symbol_id": symbol_node_id},
        "get_callers": {"symbol_id": symbol_node_id},
        "concierge_get_call_chain": {"start_node": "calc.py", "depth_limit": 3},
        "concierge_load": {"node_id": file_node_id},
        "concierge_wakeup": {"project_uuid": proj_uuid},
        "concierge_resume": {"project_uuid": proj_uuid},
        "concierge_set_state": {"state_name": "EXECUTION", "session_id": "default"},
        "concierge_store_fact": {"scope_type": "session", "scope_id": "test_sess", "fact_statement": "Fato adicional no estado P"},
        "concierge_list_facts": {"scope_type": "session", "scope_id": "test_sess"},
        "concierge_set_memory": {"scope_type": "session", "scope_id": "test_sess", "block_label": "notes", "content": "Nota persistida no estado P"},
        "concierge_get_memory": {"scope_type": "session", "scope_id": "test_sess"},
        "concierge_feedback": {"fact_id": real_fact_id, "was_useful": True},
        "find_similar": {"project_identifier": proj_uuid},
        "get_trajectories": {"project_identifier": proj_uuid},
        "add_reference_wing": {"project_identifier": proj_uuid, "wing_name": "WING_TEST"},
        "remove_reference_wing": {"project_identifier": proj_uuid, "wing_name": "WING_TEST"},
        "update_project": {"project_identifier": proj_uuid, "summary": "Projeto Fixture Atualizado"},
        "agent_save_checkpoint": {"agent_id": "test_agent_1", "session_id": "sess_p", "checkpoint_id": "chk_p2", "state_dict": {"step": "p2"}},
        "agent_get_checkpoint": {"agent_id": "test_agent_1", "session_id": "sess_p", "checkpoint_id": "chk_p"},
        "agent_list_checkpoints": {"agent_id": "test_agent_1", "session_id": "sess_p"},
        "concierge_commit": {
            "project_uuid": proj_uuid,
            "phase": "TEST",
            "technical_changes": "Commit consolidado em P",
            "updated_pointers": ["math_ops.py", "calc.py"]
        },
        "concierge_register": {"project_path": fixture_dir, "summary": "Novo registro em P"},
        "concierge_mine": {"path": fixture_dir, "project_identifier": proj_uuid, "auto_tag": True},
        "reset_collection": {},
        "delete_project": {"project_identifier": proj_uuid},
    }

    results_p = {}
    for tname in ordered_tools:
        args = args_used_p[tname]
        cls, detail, parsed = await execute_tool(tname, args)
        results_p[tname] = {"class": cls, "detail": detail[:150], "parsed": parsed, "args": args}
        print(f"  [P] {tname:28s} -> {cls:22s} | {detail[:80]}")

    # =========================================================================
    # TESTES ESPECIAIS SOLICITADOS
    # =========================================================================
    print("\n--- TESTES ESPECIAIS ---")

    # 1. concierge_feedback com fact_id inexistente (99999)
    print("Testando concierge_feedback com fact_id inexistente (99999)...")
    fb_nonexist_cls, fb_nonexist_detail, fb_nonexist_parsed = await execute_tool("concierge_feedback", {"fact_id": 99999, "was_useful": True})
    print(f"  Resultado fact_id=99999: class={fb_nonexist_cls}, parsed={fb_nonexist_parsed}")

    # 2. reset_collection e delete_project no estado MAINTENANCE
    print("\nTestando reset_collection e delete_project em MAINTENANCE...")
    # Verificar bloqueio literal em EXECUTION
    print(f"  Bloqueio reset_collection em EXECUTION: {results_p['reset_collection']['detail']}")
    print(f"  Bloqueio delete_project em EXECUTION: {results_p['delete_project']['detail']}")

    # Mudar estado para MAINTENANCE
    set_maint_res = await server._mcp.call_tool("concierge_set_state", {"state_name": "MAINTENANCE", "session_id": "default"})
    print(f"  Transicao de estado: {parse_mcp_response(set_maint_res)}")

    # Executar reset_collection em MAINTENANCE
    reset_maint_cls, reset_maint_detail, reset_maint_parsed = await execute_tool("reset_collection", {})
    print(f"  reset_collection em MAINTENANCE -> {reset_maint_cls} | {reset_maint_detail}")

    # Executar delete_project em MAINTENANCE
    delete_maint_cls, delete_maint_detail, delete_maint_parsed = await execute_tool("delete_project", {"project_identifier": proj_uuid})
    print(f"  delete_project em MAINTENANCE -> {delete_maint_cls} | {delete_maint_detail}")

    # Restaurar estado
    await server._mcp.call_tool("concierge_set_state", {"state_name": "EXECUTION", "session_id": "default"})

    # Salvar resultados completos em JSON
    matrix_output = {
        "db_state_l": db_state_l,
        "db_state_p": db_state_p,
        "proj_uuid": proj_uuid,
        "file_node_id": file_node_id,
        "symbol_node_id": symbol_node_id,
        "real_fact_id": real_fact_id,
        "args_used_l": args_used_l,
        "args_used_p": args_used_p,
        "results_l": results_l,
        "results_p": results_p,
        "mine_1_retorno": mine_1_parsed,
        "mine_2_retorno": mine_2_parsed,
        "feedback_nonexistent": {
            "class": fb_nonexist_cls,
            "detail": fb_nonexist_detail,
            "parsed": fb_nonexist_parsed
        },
        "governor_maintenance_test": {
            "reset_collection_execution": results_p["reset_collection"],
            "delete_project_execution": results_p["delete_project"],
            "reset_collection_maintenance": {
                "class": reset_maint_cls,
                "detail": reset_maint_detail,
                "parsed": reset_maint_parsed
            },
            "delete_project_maintenance": {
                "class": delete_maint_cls,
                "detail": delete_maint_detail,
                "parsed": delete_maint_parsed
            }
        }
    }

    with open("scratch/fase4_0c_matrix_results.json", "w", encoding="utf-8") as f:
        json.dump(matrix_output, f, indent=2, ensure_ascii=False)
    print("\nResultados salvos em scratch/fase4_0c_matrix_results.json")

    # Cleanup temp
    store.close()
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("Workspace temporario removido com sucesso.")

if __name__ == "__main__":
    asyncio.run(run_tool_matrix())
