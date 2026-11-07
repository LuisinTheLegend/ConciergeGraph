import os
import subprocess
import sys

env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

pytest_bin = os.path.abspath(r".venv_clean\Scripts\pytest.exe")
cmd = [pytest_bin, "tests", "-v"]

print(f"Executing: {' '.join(cmd)}")
with open(r"scratch\evidencia_4_3b\full_suite_run.txt", "w", encoding="utf-8") as out_f:
    proc = subprocess.run(
        cmd,
        stdout=out_f,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=os.path.abspath("."),
    )
print(f"Test suite finished with exit code {proc.returncode}")
sys.exit(proc.returncode)

