import os
import subprocess
import sys
import time

out_dir = os.path.join("scratch", "evidencia_4_4")
os.makedirs(out_dir, exist_ok=True)

pytest_exe = os.path.join(".venv_clean", "Scripts", "pytest.exe")
cmd_base = [
    pytest_exe,
    "tests/test_graph_rag_janitor.py",
    "tests/test_graph_rag_loops.py",
    "-v",
    "-o", "timeout=45",
    "-o", "timeout_method=thread",
]

results = []
print(f"Starting 30 investigation runs of janitor & loops tests...")

for i in range(1, 31):
    start = time.time()
    out_file = os.path.join(out_dir, f"cycle_{i:02d}.txt")
    try:
        proc = subprocess.run(
            cmd_base,
            capture_output=True,
            text=True,
            timeout=90,  # process timeout margin above 45s pytest timeout
        )
        elapsed = time.time() - start
        combined_output = proc.stdout + ("\n--- STDERR ---\n" + proc.stderr if proc.stderr else "")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(combined_output)
        
        status = "PASSED" if proc.returncode == 0 else f"FAILED(rc={proc.returncode})"
        results.append((i, status, elapsed))
        print(f"Cycle {i:02d}: {status} in {elapsed:.2f}s")
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start
        results.append((i, "PROCESS_TIMEOUT", elapsed))
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"PROCESS_TIMEOUT after {elapsed:.2f}s\nOutput so far:\n{e.stdout}\nErrors:\n{e.stderr}")
        print(f"Cycle {i:02d}: PROCESS_TIMEOUT in {elapsed:.2f}s")

summary_file = os.path.join(out_dir, "investigation_30_summary.txt")
with open(summary_file, "w", encoding="utf-8") as f:
    for c, stat, el in results:
        f.write(f"Cycle {c:02d}: {stat} ({el:.2f}s)\n")

print("Completed 30 runs.")

