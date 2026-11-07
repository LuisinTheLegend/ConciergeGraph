import os
import subprocess
import time

env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

pytest_bin = os.path.abspath(r".venv_clean\Scripts\pytest.exe")
test_file = r"tests\test_mcp_server_extensions.py"

log_lines = []
log_lines.append("=== ITEM 3: 10 CONSECUTIVE RUNS OF test_mcp_server_extensions.py ===")
log_lines.append(f"Pytest binary: {pytest_bin}")
log_lines.append(f"Target: {test_file}")
log_lines.append("Parameters: -v -o faulthandler_timeout=60 (timeout=120s)\n")

any_hang = False

for i in range(1, 11):
    cmd = [pytest_bin, test_file, "-v", "-o", "faulthandler_timeout=60"]
    t0 = time.perf_counter()
    print(f"Starting iteration {i}/10...")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=120,
        )
        elapsed = time.perf_counter() - t0
        status = "PASSED" if proc.returncode == 0 else f"FAILED (code {proc.returncode})"
        msg = f"Run {i:02d}/10: {status} in {elapsed:.2f}s"
        print(msg)
        log_lines.append(f"--- RUN {i:02d} ({msg}) ---")
        log_lines.append(proc.stdout)
        if proc.stderr:
            log_lines.append(proc.stderr)
        log_lines.append("\n")
    except subprocess.TimeoutExpired as te:
        elapsed = time.perf_counter() - t0
        any_hang = True
        msg = f"Run {i:02d}/10: TIMEOUT (HANG) after {elapsed:.2f}s!"
        print(msg)
        log_lines.append(f"--- RUN {i:02d} ({msg}) ---")
        if te.stdout:
            log_lines.append(te.stdout.decode("utf-8", errors="replace"))
        if te.stderr:
            log_lines.append(te.stderr.decode("utf-8", errors="replace"))
        log_lines.append("\n")

summary = f"Summary: 10 runs completed. Any hang detected: {any_hang}"
print(summary)
log_lines.append(summary)

with open(r"scratch\evidencia_4_3c\item3_10_runs_mcp_extensions.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines) + "\n")

print("Saved scratch/evidencia_4_3c/item3_10_runs_mcp_extensions.txt successfully.")

