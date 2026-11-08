import os
import subprocess
import sys
import glob

env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
env["HF_HUB_OFFLINE"] = "1"

pytest_bin = os.path.abspath(r".venv_clean\Scripts\pytest.exe")

# 1. Standard order
cmd_standard = [pytest_bin, "tests", "-v"]
print("Running full suite in STANDARD order...")
out_std = r"scratch\evidencia_4_4b\suite_standard_order.txt"
with open(out_std, "w", encoding="utf-8", newline="\n") as f:
    proc_std = subprocess.run(cmd_standard, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=os.path.abspath("."))
print(f"Standard order completed with exit code: {proc_std.returncode}")

# 2. Reverse order of test files
# Coleta exatamente a lista de arquivos de teste
test_files = sorted(glob.glob("tests/**/test_*.py", recursive=True) + glob.glob("tests/**/*_test.py", recursive=True))
# Remove duplicados preservando ordem
unique_files = []
for tf in test_files:
    if tf not in unique_files:
        unique_files.append(tf)

reversed_test_files = list(reversed(unique_files))
cmd_reverse = [pytest_bin] + reversed_test_files + ["-v"]
print(f"Running full suite in REVERSED file order ({len(reversed_test_files)} files)...")
out_rev = r"scratch\evidencia_4_4b\suite_reverse_order.txt"
with open(out_rev, "w", encoding="utf-8", newline="\n") as f:
    proc_rev = subprocess.run(cmd_reverse, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=os.path.abspath("."))
print(f"Reverse order completed with exit code: {proc_rev.returncode}")

if proc_std.returncode != 0 or proc_rev.returncode != 0:
    print(f"FAILED: Standard={proc_std.returncode}, Reverse={proc_rev.returncode}")
    sys.exit(1)
print("Both orders PASSED!")
