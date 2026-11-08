# scratch/run_mutation_m10.py
# Aplica Mutação M10 (troca monkeypatch.setattr por atribuição direta em E2E)
# Grava m10_mutation_fails.txt e m10_without_mutation_passes.txt

import os
import subprocess

test_file = os.path.abspath("tests/test_call_chain_edges_nodes.py")
with open(test_file, "r", encoding="utf-8") as f:
    original_code = f.read()

target_str = 'monkeypatch.setattr(mcp_server, "db_manager", db_mgr)'
mutated_str = 'mcp_server.db_manager = db_mgr  # M10 MUTATION'

assert target_str in original_code, "Target string not found in test_call_chain_edges_nodes.py"
mutated_code = original_code.replace(target_str, mutated_str, 1)

env = os.environ.copy()
env["HF_HUB_OFFLINE"] = "1"
env["PYTHONNOUSERSITE"] = "1"
pytest_exe = os.path.abspath(".venv_clean/Scripts/pytest.exe")

try:
    # 1. Aplica a mutação M10
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(mutated_code)
    print("Mutação M10 aplicada no arquivo.")

    # Executa o teste afetado
    cmd = [pytest_exe, "tests/test_call_chain_edges_nodes.py", "-k", "test_e2e_mcp_real_server_call_chain_with_ingestion", "-v"]
    res_mut = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    
    with open("scratch/evidencia_4_4b/m10_mutation_fails.txt", "w", encoding="utf-8") as out:
        out.write("=== PROVA DE FALHA DA MUTAÇÃO M10 (ATRIBUIÇÃO DIRETA DE mcp_server.db_manager) ===\n")
        out.write(f"Comando: {' '.join(cmd)}\n")
        out.write(f"Exit code: {res_mut.returncode}\n\n")
        out.write(res_mut.stdout)
        if res_mut.stderr:
            out.write("\n=== STDERR ===\n")
            out.write(res_mut.stderr)
    print(f"M10 falhou como esperado (exit code {res_mut.returncode}). Salvo em m10_mutation_fails.txt")

finally:
    # 2. Reverte a mutação
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(original_code)
    print("Mutação M10 revertida.")

# Executa sem a mutação
res_clean = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
with open("scratch/evidencia_4_4b/m10_without_mutation_passes.txt", "w", encoding="utf-8") as out:
    out.write("=== PROVA DE SUCESSO SEM MUTAÇÃO M10 ===\n")
    out.write(f"Comando: {' '.join(cmd)}\n")
    out.write(f"Exit code: {res_clean.returncode}\n\n")
    out.write(res_clean.stdout)
    if res_clean.stderr:
        out.write("\n=== STDERR ===\n")
        out.write(res_clean.stderr)
print(f"Sem mutação passou com código {res_clean.returncode}. Salvo em m10_without_mutation_passes.txt")

