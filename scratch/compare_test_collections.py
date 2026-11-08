import os
import subprocess

py_exe = os.path.abspath(".venv_clean/Scripts/python.exe")
env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

# 1. Collect from ba8a6f0 worktree
wt_dir = os.path.abspath("scratch/wt_ba8a6f0")
res_ba = subprocess.run(
    [py_exe, "-m", "pytest", "--collect-only", "-q", "tests"],
    cwd=wt_dir,
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
lines_ba = [line.strip() for line in res_ba.stdout.splitlines() if line.strip() and not line.startswith("no tests") and not "collected" in line]

# 2. Collect from 1d375ad
res_1d = subprocess.run(
    [py_exe, "-m", "pytest", "--collect-only", "-q", "tests"],
    cwd=os.path.abspath("."),
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
lines_1d = [line.strip() for line in res_1d.stdout.splitlines() if line.strip() and not line.startswith("no tests") and not "collected" in line]

set_ba = set(lines_ba)
set_1d = set(lines_1d)

added = sorted(set_1d - set_ba)
removed = sorted(set_ba - set_1d)

os.makedirs("scratch/evidencia_4_4b", exist_ok=True)
out_file = "scratch/evidencia_4_4b/test_collection_reconciliation.txt"
with open(out_file, "w", encoding="utf-8", newline="\n") as f:
    f.write("=== RECONCILIAÇÃO DA COLEÇÃO DE TESTES ENTRE ba8a6f0 E 1d375ad ===\n\n")
    f.write(f"Total coletado em ba8a6f0: {len(set_ba)}\n")
    f.write(f"Total coletado em 1d375ad: {len(set_1d)}\n")
    f.write(f"Diferença líquida: {len(set_1d) - len(set_ba)}\n\n")
    
    f.write(f"--- TESTES ADICIONADOS EM 1d375ad ({len(added)}) ---\n")
    for t in added:
        f.write(f"  + {t}\n")
    f.write("\n")
    
    f.write(f"--- TESTES REMOVIDOS EM 1d375ad ({len(removed)}) ---\n")
    for t in removed:
        f.write(f"  - {t}\n")
    f.write("\n")

print(f"Reconciliation written to {out_file}")
print(f"ba8a6f0: {len(set_ba)}, 1d375ad: {len(set_1d)}, added: {len(added)}, removed: {len(removed)}")

