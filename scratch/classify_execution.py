import os
import sys

# Ensure current directory is on sys.path
if "." not in sys.path:
    sys.path.insert(0, ".")

import json
import sqlite3

def load_data():
    with open("scratch/probe_runtime_results.json", encoding="utf-8") as f:
        probe = json.load(f)
    with open("scratch/bl_status_map.json", encoding="utf-8") as f:
        bl_map = json.load(f)
    with open("scratch/candidate_details.json", encoding="utf-8") as f:
        cand_details = json.load(f)
    return probe, bl_map, cand_details

def count_lines(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def analyze_all():
    probe, bl_map, cand_details = load_data()
    loaded_a = set(probe["modules_moment_a"])
    loaded_b = set(probe["modules_moment_b"])
    
    # 64 modules
    from scratch.fase4_0b_static_reach import find_project_files, file_to_module, extract_imports
    files_map = find_project_files()
    mod_by_file = {p: file_to_module(p) for p in files_map}
    file_by_mod = {mod: p for p, mod in mod_by_file.items()}
    all_modules = set(mod_by_file.values())
    
    # Static reach
    from collections import deque
    imports_by_mod = {mod: extract_imports(p, p, all_modules) for p, mod in mod_by_file.items()}
    reachable = set(['main'])
    queue = deque(['main'])
    while queue:
        curr = queue.popleft()
        for nxt in imports_by_mod.get(curr, []):
            if nxt not in reachable:
                reachable.add(nxt)
                queue.append(nxt)
                
    # Classify each module:
    # EM USO:
    # modules actively executing core functions:
    # storage (connection, logic, schema, semantic_logic, store, vector_store, base_backend, __init__)
    # ingestion (crawler, orchestrator, parser, summarizer, __init__)
    # services (janitor, __init__)
    # core (config, database, graph_rag, hybrid_search, mcp_governor, memory_extractor, middleware, project_index, __init__)
    # interface (mcp_server, __init__)
    # main.py
    
    # CARREGADO MAS NUNCA CHAMADO:
    # modules that are in loaded_a/b, but were only loaded due to side-effect imports and have zero execution:
    # agents (agents/__init__.py, agents/revisor_critico.py)
    # interface (action_hooks.py, queue_writer.py, telemetry_api.py)
    # core (rate_governor.py, gating_interceptor.py, security_guard.py, telemetry_schemas.py, checkpointer.py)
    # Note: checkpointer.py is called if agent_save_checkpoint / agent_get_checkpoint are called,
    # but does it have tables? In probe, agent_save_checkpoint / agent_get_checkpoint failed with no such table.
    # What about security_guard.py? In probe, reset_collection / delete_project triggered SecurityException via mcp_governor!
    # Let's check which modules actually execute methods:
    
    in_use_modules = {
        "main",
        "storage",
        "storage.base_backend",
        "storage.connection",
        "storage.logic",
        "storage.schema",
        "storage.semantic_logic",
        "storage.store",
        "storage.vector_store",
        "ingestion",
        "ingestion.crawler",
        "ingestion.orchestrator",
        "ingestion.parser",
        "ingestion.summarizer",
        "services",
        "services.janitor",
        "core",
        "core.config",
        "core.database",
        "core.graph_rag",
        "core.hybrid_search",
        "core.mcp_governor",
        "core.memory_extractor",
        "core.middleware",
        "core.project_index",
        "core.checkpointer", # called by agent_save_checkpoint/get/list
        "core.security_guard", # called by gating_interceptor / used in mcp_server
        "interface",
        "interface.mcp_server",
    }
    
    loaded_never_called = {
        "agents",
        "agents.revisor_critico",
        "interface.action_hooks",
        "interface.queue_writer",
        "interface.telemetry_api",
        "core.rate_governor",
        "core.gating_interceptor",
        "core.telemetry_schemas",
    }
    
    module_rows = []
    for filepath in sorted(files_map.keys()):
        mod = mod_by_file[filepath]
        lines = count_lines(filepath)
        is_reachable = "S" if mod in reachable else "N"
        is_boot = "S" if mod in loaded_a or mod == "main" else "N"
        is_used = "S" if mod in loaded_b or mod == "main" else "N"
        
        if mod in in_use_modules:
            classification = "EM USO"
        elif mod in loaded_never_called or (is_boot == "S" and mod not in in_use_modules):
            classification = "CARREGADO MAS NUNCA CHAMADO"
        else:
            classification = "NÃO CARREGADO"
            
        module_rows.append({
            "filepath": filepath,
            "module": mod,
            "lines": lines,
            "reachable": is_reachable,
            "bootstrap": is_boot,
            "after_use": is_used,
            "classification": classification,
        })
        
    print(f"Total modules classified: {len(module_rows)}")
    by_class = {}
    for r in module_rows:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
    print("Classifications count:", by_class)
    
    # Save modules analysis
    with open("scratch/modules_execution_matrix.json", "w", encoding="utf-8") as f:
        json.dump(module_rows, f, indent=2, ensure_ascii=False)
        
    # Analyze 88 BL items:
    # VIVO: the code cited in 'file' is in a module classified as EM USO
    # DORMENTE: the code cited in 'file' is in a module classified as NÃO CARREGADO or CARREGADO MAS NUNCA CHAMADO
    # Wait, what if a BL cites multiple files (e.g. BL-014: agent/run_agent.py, core/hsm_engine.py, interface/mcp_server.py)?
    # If the bug is about connecting run_agent (NÃO CARREGADO) or hsm_engine (NÃO CARREGADO) to mcp_server (EM USO),
    # the failure exists only if you try to use the disconnected component. If the component is dormant, the bug is dormant in production!
    
    bl_classification = []
    # Let's inspect the files cited by each BL from backlog-final.md
    with open("audits/backlog-final.md", "r", encoding="utf-8") as f:
        backlog_text = f.read()
        
    # Let's parse each BL from backlog-final.md
    import re
    bl_blocks = re.split(r'\n#### \[(BL-\d+)\]', backlog_text)[1:]
    
    bl_items = []
    for i in range(0, len(bl_blocks), 2):
        bl_id = bl_blocks[i]
        block = bl_blocks[i+1]
        
        # extract title
        first_line = block.splitlines()[0].strip()
        title = first_line.lstrip("— -: ")
        
        # extract severity
        sev_match = re.search(r'\*\*Severidade:\*\*\s*(.+)', block)
        sev = sev_match.group(1).strip() if sev_match else "MÉDIA"
        
        # extract files cited
        files_match = re.search(r'\*\*Arquivos & Linhas:\*\*\s*(.+)', block)
        files_line = files_match.group(1).strip() if files_match else ""
        
        # determine if all cited files are dormant or in use
        # extract python files mentioned
        mentioned_files = re.findall(r'[\w/\\-]+\.(?:py|tsx|ts|js)', files_line)
        
        # Check against module_rows
        has_in_use = False
        has_dormant = False
        reasons = []
        
        for mf in mentioned_files:
            clean_mf = mf.replace('\\', '/')
            # find match in module_rows
            match_row = next((r for r in module_rows if r["filepath"] == clean_mf or r["filepath"].endswith(clean_mf)), None)
            if match_row:
                if match_row["classification"] == "EM USO":
                    has_in_use = True
                else:
                    has_dormant = True
                    reasons.append(f"{match_row['filepath']} ({match_row['classification']})")
            elif "grafo-dashboard-web" in clean_mf:
                has_dormant = True
                reasons.append("grafo-dashboard-web (frontend não executado no server)")
            elif "tests/" in clean_mf:
                pass
                
        # Classification rule:
        # If the core problem is in an EM USO module -> VIVO
        # If the primary module is CARREGADO MAS NUNCA CHAMADO or NÃO CARREGADO -> DORMENTE
        if not has_in_use and has_dormant:
            status = "DORMENTE"
            just = f"Módulos citados são dormentes: {', '.join(reasons)}"
        elif has_in_use and not has_dormant:
            status = "VIVO"
            just = "Módulos citados estão EM USO no runtime padrão."
        else:
            # Hybrid
            # Check primary target
            if "run_agent" in files_line or "telemetry_api" in files_line or "rate_governor" in files_line or "revisor_critico" in files_line or "dashboard" in files_line or "delta_manager" in files_line or "watcher" in files_line:
                status = "DORMENTE"
                just = f"Módulo primário afetado é dormente ({', '.join(reasons)}), embora interaja com interfaces do núcleo."
            else:
                status = "VIVO"
                just = "Núcleo ativo em execução no runtime padrão."
                
        bl_items.append({
            "bl_id": bl_id,
            "title": title,
            "severity": sev,
            "files": files_line,
            "status": status,
            "justification": just
        })
        
    print(f"Total BLs classified: {len(bl_items)}")
    vivos = sum(1 for b in bl_items if b["status"] == "VIVO")
    dormentes = sum(1 for b in bl_items if b["status"] == "DORMENTE")
    print(f"VIVOS: {vivos}, DORMENTES: {dormentes}")
    
    with open("scratch/bl_vivo_dormente.json", "w", encoding="utf-8") as f:
        json.dump(bl_items, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    analyze_all()
