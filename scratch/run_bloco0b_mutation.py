"""
Runner para a mutação do Bloco 0b.3 de acordo com o PEDIDO 4.4c.
Aplica a mutação em tests/test_queue_writer_resilience.py simulando a poluição
onde interface.queue_writer existe em sys.modules mas foi desvinculado do pacote pai 'interface'
(ou 'interface' foi removido de sys.modules deixando o submódulo órfão).
Executa o pytest, grava a evidência em scratch/evidencia_4_4c/mutacao_M10g.txt e restaura o arquivo.
"""

import os
import subprocess
import sys

EVIDENCIA_DIR = "scratch/evidencia_4_4c"
VENV_PYTEST_310 = ".venv_310/Scripts/pytest.exe"

os.makedirs(EVIDENCIA_DIR, exist_ok=True)

target_file = "tests/test_queue_writer_resilience.py"
target_test = "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t4_normal_path_unaltered_throughput"

replace_from = "def test_t4_normal_path_unaltered_throughput(self):"
replace_to = """def test_t4_normal_path_unaltered_throughput(self):
        # MUTAÇÃO M10g: desvincula queue_writer do pacote interface simulando poluição
        import sys as _sys
        delattr(_sys.modules["interface"], "queue_writer")"""

with open(target_file, "r", encoding="utf-8") as f:
    original_code = f.read()

assert replace_from in original_code, f"Target '{replace_from}' not found in {target_file}"

mutated_code = original_code.replace(replace_from, replace_to, 1)

evidence_path = os.path.join(EVIDENCIA_DIR, "mutacao_M10g.txt")

try:
    print("[1] Aplicando mutação M10g no código de teste...")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(mutated_code)

    print("[2] Executando pytest com mutação (esperado: FALHA pela fixture)...")
    cmd_mutated = [VENV_PYTEST_310, target_test, "-v"]
    proc_mutated = subprocess.run(cmd_mutated, capture_output=True, text=True, encoding="utf-8", errors="replace")

    print("[3] Restaurando código original...")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    print("[4] Executando pytest sem mutação (esperado: VERDE)...")
    cmd_clean = [VENV_PYTEST_310, target_test, "-v"]
    proc_clean = subprocess.run(cmd_clean, capture_output=True, text=True, encoding="utf-8", errors="replace")

    report = []
    report.append("=" * 80)
    report.append("MUTAÇÃO M10g: Poluição de pacote pai/submódulo em sys.modules")
    report.append(f"Arquivo mutado: {target_file}")
    report.append(f"Alvo: {target_test}")
    report.append("Descrição: O teste remove o atributo queue_writer de sys.modules['interface'],")
    report.append("           deixando interface.queue_writer órfão em sys.modules.")
    report.append("           A fixture de integridade em conftest.py deve capturar e falhar com AssertionError.")
    report.append("=" * 80)
    report.append("")
    report.append("--- RESULTADO COM MUTAÇÃO (esperado: FALHA/KILLED) ---")
    report.append(f"Retcode: {proc_mutated.returncode}")
    report.append(proc_mutated.stdout)
    report.append(proc_mutated.stderr)
    report.append("")
    report.append("--- RESULTADO SEM MUTAÇÃO (esperado: VERDE/PASSOU) ---")
    report.append(f"Retcode: {proc_clean.returncode}")
    report.append(proc_clean.stdout)
    report.append(proc_clean.stderr)

    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"[OK] Evidência gravada em {evidence_path}")
    print(f"Mutated retcode: {proc_mutated.returncode} (esperado != 0)")
    print(f"Clean retcode: {proc_clean.returncode} (esperado 0)")

finally:
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(original_code)
