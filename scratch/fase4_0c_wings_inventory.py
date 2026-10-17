import sys
import os
import subprocess
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

if "." not in sys.path:
    sys.path.insert(0, ".")

def run_cmd(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

def main():
    print("=================================================================")
    print("PASSO 5: INVENTÁRIO DO DICIONÁRIO DE ALAS (wing_keywords)")
    print("=================================================================\n")
    
    # (a) wing_keywords e auto_categorize_project
    print("--- (a) Ocorrências de wing_keywords e auto_categorize_project ---")
    print("Comando: git grep -n \"wing_keywords\"")
    out_wk = run_cmd("git grep -n \"wing_keywords\"")
    print(out_wk)
    print("\nComando: git grep -n \"auto_categorize_project\"")
    out_ac = run_cmd("git grep -n \"auto_categorize_project\"")
    print(out_ac)
    
    # (b) Os 5 nomes de domínio e suas palavras-chave em arquivos versionados
    domains = [
        "marketing/vendas",
        "finanças/quant",
        "gestão/saas",
        "automação/rh",
        "estatística",
    ]
    print("\n--- (b) Ocorrências dos 5 nomes de domínio ---")
    for d in domains:
        print(f"\nComando: git grep -n \"{d}\"")
        out_d = run_cmd(f'git grep -n "{d}"')
        print(out_d if out_d else "  (nenhuma ocorrência encontrada)")

    # (c) max_wings, default_wing, "geral"
    print("\n--- (c) Ocorrências de max_wings, default_wing e 'geral' ---")
    print("\nComando: git grep -n \"max_wings\"")
    print(run_cmd('git grep -n "max_wings"'))
    print("\nComando: git grep -n \"default_wing\"")
    print(run_cmd('git grep -n "default_wing"'))
    print("\nComando: git grep -n \"default_wing\\|'geral'\\|\"geral\"\" (amostra representativa)")
    print(run_cmd('git grep -n "\"geral\"" -- "*.py"'))
    
    # (d) Docstrings de ferramentas MCP
    print("\n--- (d) Docstrings de ferramentas MCP que citam alas ---")
    from interface.mcp_server import GrafoConciergeServer
    import inspect
    server_source = inspect.getsource(GrafoConciergeServer._register_tools)
    
    # check tools mentioning wing
    for line in server_source.splitlines():
        if "wing" in line.lower() and ("description=" in line or "wing:" in line or "@self._mcp.tool" in line):
            print("  ", line.strip())

    # Simulation without editing code
    print("\n--- SIMULAÇÃO: ConciergeConfig(wing_keywords={}) ---")
    from core.config import ConciergeConfig
    from core.project_index import ProjectIndex
    from storage.store import SqliteStore
    
    temp_dir = tempfile.mkdtemp(prefix="wings_sim_")
    db_file = os.path.join(temp_dir, "sim.db")
    
    cfg = ConciergeConfig(wing_keywords={})
    store = SqliteStore(db_file)
    p_index = ProjectIndex(sqlite_store=store, config=cfg)
    
    # Register 2 projects:
    # 1: without specified wing (should get default_wing="geral")
    # 2: with free wing (e.g. "deep-learning")
    p1 = store.create_project(uuid="uuid_1", folder_name="proj_default", primary_wing=cfg.default_wing)
    p2 = store.create_project(uuid="uuid_2", folder_name="proj_custom", primary_wing="deep-learning")
    
    print(f"Projeto 1 criado: uuid={p1['uuid']}, folder={p1['folder_name']}, primary_wing='{p1['primary_wing']}'")
    print(f"Projeto 2 criado: uuid={p2['uuid']}, folder={p2['folder_name']}, primary_wing='{p2['primary_wing']}'")
    
    # Add nodes to proj_default to test auto_categorize_project with empty dictionary
    store.create_nodes_and_edges_bulk([
        {
            "project_uuid": p1["uuid"],
            "label": "marketing_campaign.py::run_campaign",
            "summary": "Executa campanha de marketing e funil de vendas para leads",
            "node_type": "FUNCTION",
            "type": "function",
            "tags": ["marketing", "vendas", "leads"],
            "status": "ACTIVE"
        }
    ], [])
    
    # Run auto_categorize_project:
    cat_result = p_index.auto_categorize_project(p1["uuid"])
    print(f"\nResultado de auto_categorize_project em p1 (mesmo com tags de marketing): '{cat_result}' (esperado: '{cfg.default_wing}')")
    
    # Add reference wing and test find_similar:
    p_index.add_reference_wing(p1["uuid"], "deep-learning")
    ref_wings = p_index.get_reference_wings(p1["uuid"])
    print(f"Reference wings de p1: {ref_wings}")
    
    sim_projects = p_index.find_similar_projects(p1["uuid"], include_references=True)
    print(f"Projetos similares encontrados para p1 (include_references=True): {[p['folder_name'] for p in sim_projects]}")
    
    # Scoped search test:
    # In store, filter projects by primary_wing
    p2_fetch = store.get_project("proj_custom")
    print(f"Busca por projeto com ala livre 'deep-learning': uuid={p2_fetch['uuid']}, wing='{p2_fetch['primary_wing']}'")
    
    # Affected test suites:
    print("\n--- EXECUÇÃO DOS TESTES AFETADOS COM wing_keywords={} ---")
    # Find test files mentioning wing_keywords or wings categorization
    test_files = ["tests/test_project_index.py", "tests/stress_test_v2_parte1.py"]
    
    # Run test_project_index.py with monkeypatched ConciergeConfig.wing_keywords = {}
    print("\nRodando tests/test_project_index.py com monkeypatch wing_keywords={}:")
    cmd_t1 = 'python -c "import unittest, sys; sys.path.insert(0, \'.\'); from unittest.mock import patch; from core.config import ConciergeConfig; patch.object(ConciergeConfig, \'wing_keywords\', {}).start(); suite = unittest.defaultTestLoader.discover(\'tests\', pattern=\'test_project_index.py\'); res = unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(0 if res.wasSuccessful() else 1)"'
    out_t1 = run_cmd(cmd_t1)
    print(out_t1)
    
    print("\nRodando tests/stress_test_v2_parte1.py com monkeypatch wing_keywords={}:")
    cmd_t2 = 'python -c "import sys; sys.path.insert(0, \'.\'); from unittest.mock import patch; from core.config import ConciergeConfig; patch.object(ConciergeConfig, \'wing_keywords\', {}).start(); import tests.stress_test_v2_parte1 as st; st.run_stress_test_parte1()"'
    out_t2 = run_cmd(cmd_t2)
    print(out_t2)

if __name__ == '__main__':
    main()
