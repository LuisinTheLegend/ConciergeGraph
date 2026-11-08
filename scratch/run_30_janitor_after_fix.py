import os
import subprocess
import sys
import time

pytest_exe = os.path.abspath(".venv_clean/Scripts/pytest.exe")
env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
env["HF_HUB_OFFLINE"] = "1"

cmd = [pytest_exe, "tests/test_graph_rag_janitor.py", "tests/test_graph_rag_loops.py", "-v"]

num_cycles = 30
results = []
os.makedirs("scratch/evidencia_4_4b", exist_ok=True)
summary_file = "scratch/evidencia_4_4b/janitor_30_cycles_summary.txt"

print(f"Iniciando {num_cycles} ciclos de teste de janitor + loops...")
total_start = time.perf_counter()

with open(summary_file, "w", encoding="utf-8") as out:
    out.write(f"=== INVESTIGAÇÃO DE ESTABILIDADE: 30 CICLOS (JANITOR + LOOPS COM QUEUE_WRITER CORRIGIDO) ===\n")
    out.write(f"Comando: {' '.join(cmd)}\n\n")

    all_passed = True
    for i in range(1, num_cycles + 1):
        c_start = time.perf_counter()
        try:
            p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
            duration = time.perf_counter() - c_start
            passed = (p.returncode == 0)
            if not passed:
                all_passed = False
            status = "PASSED" if passed else f"FAILED (code {p.returncode})"
            line = f"Ciclo {i:02d}/{num_cycles:02d}: {status} em {duration:.2f}s"
            print(line)
            out.write(line + "\n")
            if not passed:
                out.write(f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}\n")
        except subprocess.TimeoutExpired as e:
            all_passed = False
            duration = time.perf_counter() - c_start
            line = f"Ciclo {i:02d}/{num_cycles:02d}: TIMEOUT (>90s)!"
            print(line)
            out.write(line + "\n")

    total_duration = time.perf_counter() - total_start
    summary_line = f"\nResumo: {num_cycles} ciclos concluídos em {total_duration:.2f}s. Sucesso: {all_passed}.\n"
    print(summary_line)
    out.write(summary_line)

if not all_passed:
    sys.exit(1)
print("30 ciclos executados com 100% de sucesso!")
