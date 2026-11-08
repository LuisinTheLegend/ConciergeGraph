import os
import subprocess
import sys

pytest_exe = os.path.abspath(".venv_clean/Scripts/pytest.exe")
qw_file = os.path.abspath("interface/queue_writer.py")

with open(qw_file, "r", encoding="utf-8") as f:
    orig_code = f.read()

env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

def run_resilience_test(test_name=None):
    cmd = [pytest_exe, "tests/test_queue_writer_resilience.py", "-v"]
    if test_name:
        cmd.extend(["-k", test_name])
    return subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")

os.makedirs("scratch/evidencia_4_4b", exist_ok=True)

# -------------------------------------------------------------
# Mutação (a): Remover o retry na inicialização (MAX_CONNECT_RETRIES = 1)
# -------------------------------------------------------------
print("Executando Mutação (a)...")
try:
    mutated_a = orig_code.replace("MAX_CONNECT_RETRIES = 5", "MAX_CONNECT_RETRIES = 1", 1)
    assert mutated_a != orig_code, "Target MAX_CONNECT_RETRIES not found"
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_a)

    res_a = run_resilience_test("test_t2_connect_retry_and_eventual_success")
    assert res_a.returncode != 0, "Mutação (a) deveria ter falhado T2!"
    with open("scratch/evidencia_4_4b/m_qw_a_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (a): RETRY REMOVIDO (MAX_CONNECT_RETRIES = 1) ===\n")
        f.write(f"Exit code: {res_a.returncode}\n\n")
        f.write(res_a.stdout)
        if res_a.stderr:
            f.write("\n=== STDERR ===\n" + res_a.stderr)
    print("Mutação (a) morta com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_code)

# -------------------------------------------------------------
# Mutação (b): Remover o Event de prontidão (self._ready)
# -------------------------------------------------------------
print("Executando Mutação (b)...")
try:
    # Remove a instanciação de self._ready no __init__
    mutated_b = orig_code.replace("self._ready = threading.Event()", "self._ready = None  # MUTAÇÃO B: Event _ready removido", 1)
    assert mutated_b != orig_code, "Target self._ready not found"
    # Também desativa chamada de self._ready.set()
    mutated_b = mutated_b.replace("self._ready.set()", "pass", 1)
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_b)

    res_b = run_resilience_test("test_t2_connect_retry_and_eventual_success")
    assert res_b.returncode != 0, f"Mutação (b) deveria ter falhado T2! Retornou: {res_b.returncode}\n{res_b.stdout}"
    with open("scratch/evidencia_4_4b/m_qw_b_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (b): EVENT DE PRONTIDÃO (self._ready) REMOVIDO ===\n")
        f.write(f"Exit code: {res_b.returncode}\n\n")
        f.write(res_b.stdout)
        if res_b.stderr:
            f.write("\n=== STDERR ===\n" + res_b.stderr)
    print("Mutação (b) morta com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_code)

# -------------------------------------------------------------
# Mutação (c): Remover checagem de thread.is_alive() no execute_write
# -------------------------------------------------------------
print("Executando Mutação (c)...")
try:
    # Remove as checagens de is_alive em execute_write simulando ausência de verificação de liveness
    mutated_c = orig_code.replace("if not self.is_alive():", "if False:  # MUTAÇÃO C: checagem is_alive removida")
    assert mutated_c != orig_code, "Target if not self.is_alive() not found"
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_c)

    res_c = run_resilience_test("test_t3_worker_thread_late_death_fails_pending_and_future_fast")
    assert res_c.returncode != 0, f"Mutação (c) deveria ter falhado T3! Retornou: {res_c.returncode}\n{res_c.stdout}"
    with open("scratch/evidencia_4_4b/m_qw_c_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (c): CHECAGEM DE thread.is_alive() REMOVIDA ===\n")
        f.write(f"Exit code: {res_c.returncode}\n\n")
        f.write(res_c.stdout)
        if res_c.stderr:
            f.write("\n=== STDERR ===\n" + res_c.stderr)
    print("Mutação (c) morta com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_code)

# -------------------------------------------------------------
# Clean test run: todos os 4 testes passam
# -------------------------------------------------------------
print("Executando suite de resiliência limpa (sem mutações)...")
res_clean = run_resilience_test()
assert res_clean.returncode == 0, f"Código limpo deve passar em todos os testes T1-T4! Retornou: {res_clean.returncode}\n{res_clean.stdout}"
with open("scratch/evidencia_4_4b/queue_writer_green.txt", "w", encoding="utf-8") as f:
    f.write("=== SUITE DE RESILIÊNCIA PASSANDO LIMPA (T1-T4) ===\n")
    f.write(f"Exit code: {res_clean.returncode}\n\n")
    f.write(res_clean.stdout)
print("Todos os testes T1-T4 passaram limpos sem mutações.")
