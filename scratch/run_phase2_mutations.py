import os
import subprocess
import sys

pytest_exe = os.path.abspath(".venv_clean/Scripts/pytest.exe")
env = os.environ.copy()
env["PYTHONNOUSERSITE"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

os.makedirs("scratch/evidencia_4_4b", exist_ok=True)

qw_file = os.path.abspath("interface/queue_writer.py")
db_file = os.path.abspath("core/database.py")

with open(qw_file, "r", encoding="utf-8") as f:
    orig_qw = f.read()

with open(db_file, "r", encoding="utf-8") as f:
    orig_db = f.read()

def run_test(test_name):
    cmd = [pytest_exe, "tests/test_queue_writer_resilience.py", "-k", test_name, "-v"]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res

# -------------------------------------------------------------
# Mutação (d): Remove checagem de handshake no execute_write (T5 deve falhar)
# -------------------------------------------------------------
target_d = """        if not self._ready.is_set():
            if not self._ready.wait(timeout=READY_TIMEOUT_SECONDS):
                if self._startup_error is not None:
                    return False, self._startup_error
                return False, TimeoutError(
                    f"SerializedWriteQueue worker failed to initialize within {READY_TIMEOUT_SECONDS}s."
                )"""

assert target_d in orig_qw, "target_d não encontrado em queue_writer.py"

try:
    mutated_qw = orig_qw.replace(target_d, "        pass")
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_qw)
    
    res_d = run_test("test_t5_unready_worker_handshake_timeout_fails_fast_without_enqueuing")
    assert res_d.returncode != 0, "Mutação (d) deveria falhar o teste T5!"
    with open("scratch/evidencia_4_4b/m_phase2_d_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (d): Remoção do handshake check em execute_write ===\n")
        f.write(f"Exit code: {res_d.returncode}\n\n")
        f.write(res_d.stdout)
    print("Mutação (d) eliminada com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_qw)

# -------------------------------------------------------------
# Mutação (e): Remove notificação de batch na falha fatal (T6 deve falhar)
# -------------------------------------------------------------
target_e = """            for b_task in batch:
                try:
                    resp_q = b_task[2]
                    resp_q.put((False, loop_error))
                except Exception:
                    pass"""

assert target_e in orig_qw, "target_e não encontrado em queue_writer.py"

try:
    mutated_qw = orig_qw.replace(target_e, "            pass")
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_qw)
    
    res_e = run_test("test_t6_batch_fatal_error_notifies_all_batched_callers")
    assert res_e.returncode != 0, "Mutação (e) deveria falhar o teste T6!"
    with open("scratch/evidencia_4_4b/m_phase2_e_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (e): Remoção da notificação do batch ativo ===\n")
        f.write(f"Exit code: {res_e.returncode}\n\n")
        f.write(res_e.stdout)
    print("Mutação (e) eliminada com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_qw)

# -------------------------------------------------------------
# Mutação (f): Remove verificação de deadline expirado (T7 deve falhar)
# -------------------------------------------------------------
target_f = """        if deadline is not None and time.perf_counter() > deadline:
            response_queue.put((False, TimeoutError("Write task deadline expired before execution.")))
            return"""

assert target_f in orig_qw, "target_f não encontrado em queue_writer.py"

try:
    mutated_qw = orig_qw.replace(target_f, "        pass")
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(mutated_qw)
    
    res_f = run_test("test_t7_expired_deadline_task_skipped_without_executing")
    assert res_f.returncode != 0, "Mutação (f) deveria falhar o teste T7!"
    with open("scratch/evidencia_4_4b/m_phase2_f_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (f): Remoção da verificação de deadline expirado ===\n")
        f.write(f"Exit code: {res_f.returncode}\n\n")
        f.write(res_f.stdout)
    print("Mutação (f) eliminada com sucesso.")
finally:
    with open(qw_file, "w", encoding="utf-8") as f:
        f.write(orig_qw)

# -------------------------------------------------------------
# Mutação (g): Reintroduz PRAGMA WAL no read_query (T8 deve falhar)
# -------------------------------------------------------------
target_g = """    def read_query(self, query: str, params: tuple = ()):
        \"\"\"Fast concurrent read query directly from database (bypasses write queue).\"\"\"
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            cursor = conn.cursor()"""

replacement_g = """    def read_query(self, query: str, params: tuple = ()):
        \"\"\"Fast concurrent read query directly from database (bypasses write queue).\"\"\"
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()"""

assert target_g in orig_db, "target_g não encontrado em core/database.py"

try:
    mutated_db = orig_db.replace(target_g, replacement_g)
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(mutated_db)
    
    res_g = run_test("test_t8_reader_read_query_does_not_execute_pragma_wal")
    assert res_g.returncode != 0, "Mutação (g) deveria falhar o teste T8!"
    with open("scratch/evidencia_4_4b/m_phase2_g_fails.txt", "w", encoding="utf-8") as f:
        f.write("=== PROVA DE FALHA DA MUTAÇÃO (g): Reintrodução do PRAGMA WAL no read_query ===\n")
        f.write(f"Exit code: {res_g.returncode}\n\n")
        f.write(res_g.stdout)
    print("Mutação (g) eliminada com sucesso.")
finally:
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(orig_db)

print("Todas as 4 mutações da Fase 2 foram executadas e eliminadas com sucesso!")

