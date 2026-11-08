"""
Execução de 30 ciclos de estabilidade sem instrumentação (PEDIDO 4.4c - Bloco 1.6).
Suítes: tests/test_graph_rag_janitor.py tests/test_graph_rag_loops.py
Registra duração de cada ciclo e contagem de retries de partida na SerializedWriteQueue.
"""

import os
import subprocess
import sys
import time

CYCLES = 30
OUTPUT_FILE = "scratch/evidencia_4_4c/janitor_30_cycles_stability.txt"
VENV_PYTEST = ".venv_clean/Scripts/pytest.exe"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

cycle_results = []
total_start = time.perf_counter()

print(f"Iniciando {CYCLES} ciclos de estabilidade...")

for i in range(1, CYCLES + 1):
    c_start = time.perf_counter()
    cmd = [
        VENV_PYTEST,
        "tests/test_graph_rag_janitor.py",
        "tests/test_graph_rag_loops.py",
        "-o", "log_cli=true",
        "-o", "log_cli_level=DEBUG",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - c_start
    combined_output = proc.stdout + "\n" + proc.stderr

    # Procura avisos de retry de partida no log
    retry_lines = [
        line for line in combined_output.splitlines()
        if "startup connection attempt" in line.lower()
        or ("serializedwritequeue" in line.lower() and "retrying" in line.lower())
    ]
    retry_count = len(retry_lines)

    status = "OK" if proc.returncode == 0 else f"FALHA (ret={proc.returncode})"
    cycle_results.append({
        "cycle": i,
        "status": status,
        "elapsed": elapsed,
        "retcode": proc.returncode,
        "retry_count": retry_count,
        "retry_lines": retry_lines,
    })
    print(f"Ciclo {i:02d}/{CYCLES}: {status} em {elapsed:.2f}s | retries={retry_count}")

total_elapsed = time.perf_counter() - total_start
times = [c["elapsed"] for c in cycle_results]
min_t = min(times)
max_t = max(times)
avg_t = sum(times) / len(times)
total_retries = sum(c["retry_count"] for c in cycle_results)
all_passed = all(c["retcode"] == 0 for c in cycle_results)

with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("=" * 80 + "\n")
    f.write("RELATÓRIO DE ESTABILIDADE: 30 CICLOS SEM INSTRUMENTAÇÃO (PEDIDO 4.4c - Bloco 1.6)\n")
    f.write("Suítes: tests/test_graph_rag_janitor.py tests/test_graph_rag_loops.py\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Total de ciclos executados: {CYCLES}\n")
    f.write(f"Todos os ciclos verdes: {all_passed}\n")
    f.write(f"Tempo total: {total_elapsed:.2f}s\n")
    f.write(f"Tempo médio por ciclo: {avg_t:.2f}s (min: {min_t:.2f}s, max: {max_t:.2f}s)\n")
    f.write(f"Total de retries de conexão registrados em 30 ciclos: {total_retries}\n\n")
    f.write(f"{'Ciclo':<8}{'Status':<12}{'Duração (s)':<15}{'Retries Partida':<18}\n")
    f.write("-" * 55 + "\n")
    for c in cycle_results:
        f.write(f"{c['cycle']:<8}{c['status']:<12}{c['elapsed']:<15.2f}{c['retry_count']:<18}\n")

    if total_retries > 0:
        f.write("\nLINHAS DE LOG DE RETRY DETECTADAS:\n")
        for c in cycle_results:
            if c["retry_lines"]:
                f.write(f"--- Ciclo {c['cycle']} ---\n")
                for rline in c["retry_lines"]:
                    f.write(f"  {rline}\n")
    else:
        f.write("\nNenhum aviso de retry de partida ocorreu nos 30 ciclos (todas as conexões estabelecidas na 1ª tentativa).\n")

print("\nExecução dos 30 ciclos finalizada com sucesso!")
print(f"Relatório gravado em {OUTPUT_FILE}")

