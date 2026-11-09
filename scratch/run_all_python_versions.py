"""
Executa a suíte de testes nas ordens padrão e invertida nos ambientes Python 3.10, 3.11, 3.12 e 3.14.
Grava as evidências individuais em scratch/evidencia_4_4c/suite_py<versao>.txt
em formato UTF-8 sem BOM e sem bytes nulos.
"""

import os
import subprocess
import sys
import time

VENVS = [
    ("310", ".venv_310/Scripts/python.exe", ".venv_310/Scripts/pytest.exe"),
    ("311", ".venv_311/Scripts/python.exe", ".venv_311/Scripts/pytest.exe"),
    ("312", ".venv_312/Scripts/python.exe", ".venv_312/Scripts/pytest.exe"),
    ("314", ".venv_clean/Scripts/python.exe", ".venv_clean/Scripts/pytest.exe"),
]

EVIDENCIA_DIR = "scratch/evidencia_4_4c"
os.makedirs(EVIDENCIA_DIR, exist_ok=True)

def run_environment(tag: str, py_bin: str, pytest_bin: str):
    print(f"\n{'='*70}\nINICIANDO BATERIA PARA PYTHON {tag} ({py_bin})\n{'='*70}")
    
    # Obtém a versão detalhada do Python
    ver_proc = subprocess.run([py_bin, "-c", "import sys; print(sys.version)"], capture_output=True, text=True, encoding="utf-8")
    py_version_str = ver_proc.stdout.strip()
    print(f"Versao: {py_version_str}")

    # 1. Ordem Padrao
    print(f"[{tag}] Executando suite completa - Ordem Padrao...")
    t0 = time.time()
    cmd_standard = [pytest_bin, "tests/", "-q"]
    proc_standard = subprocess.run(cmd_standard, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dur_standard = time.time() - t0
    print(f"[{tag}] Ordem Padrao concluida em {dur_standard:.2f}s (retcode={proc_standard.returncode})")

    # 2. Ordem Invertida
    print(f"[{tag}] Executando suite completa - Ordem Invertida (--reverse)...")
    t0 = time.time()
    cmd_reverse = [pytest_bin, "tests/", "--reverse", "-q"]
    proc_reverse = subprocess.run(cmd_reverse, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dur_reverse = time.time() - t0
    print(f"[{tag}] Ordem Invertida concluida em {dur_reverse:.2f}s (retcode={proc_reverse.returncode})")

    # Monta relatorio de evidencia
    out_lines = []
    out_lines.append("=" * 80)
    out_lines.append(f"EVIDENCIA SUITE COMPLETA - PYTHON {tag}")
    out_lines.append(f"Interpretador: {py_bin}")
    out_lines.append(f"Versao detalhada: {py_version_str}")
    out_lines.append("=" * 80)
    out_lines.append("")
    out_lines.append(f"--- 1. ORDEM PADRAO ---")
    out_lines.append(f"Comando: {' '.join(cmd_standard)}")
    out_lines.append(f"Retcode: {proc_standard.returncode} ({'PASSOU' if proc_standard.returncode == 0 else 'FALHOU'})")
    out_lines.append(f"Duracao: {dur_standard:.2f}s")
    out_lines.append("--- SAIDA (stdout) ---")
    out_lines.append(proc_standard.stdout)
    if proc_standard.stderr.strip():
        out_lines.append("--- ERROS (stderr) ---")
        out_lines.append(proc_standard.stderr)
    out_lines.append("")
    out_lines.append(f"--- 2. ORDEM INVERTIDA (--reverse) ---")
    out_lines.append(f"Comando: {' '.join(cmd_reverse)}")
    out_lines.append(f"Retcode: {proc_reverse.returncode} ({'PASSOU' if proc_reverse.returncode == 0 else 'FALHOU'})")
    out_lines.append(f"Duracao: {dur_reverse:.2f}s")
    out_lines.append("--- SAIDA (stdout) ---")
    out_lines.append(proc_reverse.stdout)
    if proc_reverse.stderr.strip():
        out_lines.append("--- ERROS (stderr) ---")
        out_lines.append(proc_reverse.stderr)
    out_lines.append("")

    out_file = os.path.join(EVIDENCIA_DIR, f"suite_py{tag}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print(f"[{tag}] Evidencia gravada em {out_file}")

if __name__ == "__main__":
    target_tag = sys.argv[1] if len(sys.argv) > 1 else None
    for tag, py_bin, pytest_bin in VENVS:
        if target_tag and tag != target_tag:
            continue
        run_environment(tag, py_bin, pytest_bin)

