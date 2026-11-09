"""
Execução da suíte completa de testes nas duas ordens (padrão e invertida)
para comprovação de ausência de falsos positivos na fixture de globais (M10f).
"""

import glob
import os
import subprocess
import sys
import time

EVIDENCIA_DIR = "scratch/evidencia_4_4c"
OUTPUT_FILE = os.path.join(EVIDENCIA_DIR, "mutacao_M10f.txt")
VENV_PYTEST = ".venv_clean/Scripts/pytest.exe"

test_files = sorted(glob.glob("tests/test_*.py"))
reverse_files = list(reversed(test_files))

print(f"Total de arquivos de teste identificados: {len(test_files)}")

def run_suite(file_list, order_name):
    print(f"\n--- Iniciando suíte na ordem {order_name} ({len(file_list)} arquivos) ---")
    start_t = time.perf_counter()
    cmd = [VENV_PYTEST] + file_list + ["-q"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - start_t
    print(f"Ordem {order_name}: retcode={proc.returncode} em {elapsed:.2f}s")
    return proc.returncode, elapsed, proc.stdout + "\n" + proc.stderr

# 1. Ordem padrão
ret_std, elap_std, out_std = run_suite(test_files, "PADRÃO (alfabética)")

# 2. Ordem invertida
ret_rev, elap_rev, out_rev = run_suite(reverse_files, "INVERTIDA")

with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("=" * 80 + "\n")
    f.write("EVIDÊNCIA M10f: EXECUÇÃO DA SUÍTE COMPLETA NAS DUAS ORDENS (PADRÃO E INVERTIDA)\n")
    f.write("Comprova ausência de falsos positivos e ausência de vazamento de estado.\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Total de arquivos testados: {len(test_files)}\n")
    f.write(f"Ordem padrão retcode: {ret_std} ({'PASSOU' if ret_std == 0 else 'FALHOU'}) em {elap_std:.2f}s\n")
    f.write(f"Ordem invertida retcode: {ret_rev} ({'PASSOU' if ret_rev == 0 else 'FALHOU'}) em {elap_rev:.2f}s\n\n")
    f.write("--- RESUMO ORDEM PADRÃO ---\n")
    f.write("\n".join(out_std.strip().splitlines()[-10:]) + "\n\n")
    f.write("--- RESUMO ORDEM INVERTIDA ---\n")
    f.write("\n".join(out_rev.strip().splitlines()[-10:]) + "\n\n")

print(f"\nRelatório gravado em {OUTPUT_FILE}")
if ret_std == 0 and ret_rev == 0:
    print("M10f validada com sucesso: 0 falhas em ambas as ordens!")
else:
    print(f"FALHA detectada: std={ret_std}, rev={ret_rev}")
    sys.exit(1)

