import os
import subprocess
import sys

pytest_exe = os.path.abspath(".venv_clean/Scripts/pytest.exe")
env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

def run_g2():
    cmd = [pytest_exe, "tests/test_domain_neutrality_guard.py", "-k", "test_g2_no_retired_domain_strings_in_product_code", "-v"]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res

os.makedirs("scratch/evidencia_4_4b", exist_ok=True)

# -------------------------------------------------------------
# Mutação (i): inserir 'marketing/vendas' numa docstring de core/
# -------------------------------------------------------------
core_file = os.path.abspath("core/config.py")
with open(core_file, "r", encoding="utf-8") as f:
    orig_core = f.read()

try:
    mutated_core = orig_core + '\n"""Teste de mutação G2: domínio marketing/vendas inserido em docstring."""\n'
    with open(core_file, "w", encoding="utf-8") as f:
        f.write(mutated_core)
    
    res_i = run_g2()
    assert res_i.returncode != 0, "Guarda G2 deveria falhar na mutação (i)!"
    assert "marketing/vendas" in res_i.stdout
    with open("scratch/evidencia_4_4b/m_g2_i_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (i): 'marketing/vendas' em docstring de core/ ===\n")
        f.write(f"Exit code: {res_i.returncode}\n\n")
        f.write(res_i.stdout)
    print("Mutação (i) morta com sucesso.")
finally:
    with open(core_file, "w", encoding="utf-8") as f:
        f.write(orig_core)

# -------------------------------------------------------------
# Mutação (ii): inserir em main.py
# -------------------------------------------------------------
main_file = os.path.abspath("main.py")
with open(main_file, "r", encoding="utf-8") as f:
    orig_main = f.read()

try:
    mutated_main = orig_main + '\n# Mutação G2 em main.py\n_MUT_STR = "Prefixo aleatório com finanças/quant embutido"\n'
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(mutated_main)
    
    res_ii = run_g2()
    assert res_ii.returncode != 0, "Guarda G2 deveria falhar na mutação (ii)!"
    assert "finanças/quant" in res_ii.stdout
    with open("scratch/evidencia_4_4b/m_g2_ii_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (ii): 'finanças/quant' como substring em main.py ===\n")
        f.write(f"Exit code: {res_ii.returncode}\n\n")
        f.write(res_ii.stdout)
    print("Mutação (ii) morta com sucesso.")
finally:
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(orig_main)

# -------------------------------------------------------------
# Mutação (iii): inserir em um arquivo de scripts/
# -------------------------------------------------------------
script_file = os.path.abspath("scripts/bootstrap_core_memory.py")
with open(script_file, "r", encoding="utf-8") as f:
    orig_script = f.read()

try:
    mutated_script = orig_script + '\n"""Docstring com automação/rh inserida em scripts/."""\n'
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(mutated_script)
    
    res_iii = run_g2()
    assert res_iii.returncode != 0, "Guarda G2 deveria falhar na mutação (iii)!"
    assert "automação/rh" in res_iii.stdout
    with open("scratch/evidencia_4_4b/m_g2_iii_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (iii): 'automação/rh' em scripts/ ===\n")
        f.write(f"Exit code: {res_iii.returncode}\n\n")
        f.write(res_iii.stdout)
    print("Mutação (iii) morta com sucesso.")
finally:
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(orig_script)

# -------------------------------------------------------------
# Clean run: sem mutação passa
# -------------------------------------------------------------
res_clean = run_g2()
assert res_clean.returncode == 0, "Guarda G2 deve passar limpa sem mutações!"
with open("scratch/evidencia_4_4b/m_g2_clean_passes.txt", "w", encoding="utf-8") as f:
    f.write("=== PROVA DE SUCESSO DA GUARDA G2 LIMPA ===\n")
    f.write(f"Exit code: {res_clean.returncode}\n\n")
    f.write(res_clean.stdout)
print("G2 limpa passou com sucesso.")

