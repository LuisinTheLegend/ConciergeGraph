"""
Runner para as mutações do Bloco 1 (Qa até Qh) de acordo com o PEDIDO 4.4c.
Aplica cada mutação em interface/queue_writer.py, executa o pytest no teste alvo,
grava a evidência em scratch/evidencia_4_4c/mutacao_<id>.txt e restaura o arquivo original.
"""

import os
import subprocess
import sys

SRC_FILE = "interface/queue_writer.py"
EVIDENCIA_DIR = "scratch/evidencia_4_4c"
VENV_PYTEST = ".venv_clean/Scripts/pytest.exe"

os.makedirs(EVIDENCIA_DIR, exist_ok=True)

MUTATIONS = [
    {
        "id": "Qa",
        "name": "Sem retry na inicialização (MAX_CONNECT_RETRIES = 1)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t2_connect_retry_and_eventual_success",
        "replaces": [
            ("MAX_CONNECT_RETRIES = 5", "MAX_CONNECT_RETRIES = 1")
        ],
    },
    {
        "id": "Qb",
        "name": "Sem checagem de vida no laço de espera (is_alive removido do poll)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast",
        "replaces": [
            (
                """                if not self.is_alive():
                    return False, RuntimeError("SerializedWriteQueue worker thread died while awaiting response.")""",
                "                pass",
            )
        ],
    },
    {
        "id": "Qc",
        "name": "Sem prazo no handshake (_ready.wait() sem timeout)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t5_unready_worker_handshake_timeout_fails_fast_without_enqueuing",
        "replaces": [
            ("if not self._ready.wait(timeout=READY_TIMEOUT_SECONDS):", "self._ready.wait()\n        if False:")
        ],
    },
    {
        "id": "Qd",
        "name": "Sem nenhuma checagem de vida (is_alive removido totalmente)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t3_worker_thread_late_death_fails_pending_and_future_fast",
        "replaces": [
            (
                """        if not self.is_alive():
            err = RuntimeError("SerializedWriteQueue worker thread is not alive.")
            return False, err""",
                "        pass",
            ),
            (
                """                if not self.is_alive():
                    return False, RuntimeError("SerializedWriteQueue worker thread died while awaiting response.")""",
                "                pass",
            ),
        ],
    },
    {
        "id": "Qe",
        "name": "Sem notificar callers ao morrer (notificação de lote e fila pendente removida)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers",
        "replaces": [
            (
                """            for b_task in batch:
                try:
                    resp_q = b_task[2]
                    resp_q.put((False, loop_error))
                except Exception:
                    pass
            self._fail_all_pending(loop_error)""",
                "            pass  # notificação de lote e pendentes removida",
            )
        ],
    },
    {
        "id": "Qf",
        "name": "Sem sinalizar prontidão na falha final (_ready.set removido na falha de startup)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t1_connect_persistent_failure_fails_fast_without_hanging",
        "replaces": [
            (
                """                    if attempt == MAX_CONNECT_RETRIES:
                        self._startup_error = e
                        self._ready.set()""",
                """                    if attempt == MAX_CONNECT_RETRIES:
                        self._startup_error = e
                        # self._ready.set() REMOVIDO""",
            )
        ],
    },
    {
        "id": "Qg",
        "name": "response_queue.get() bloqueante sem timeout",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast",
        "replaces": [
            ("success, result = response_queue.get(timeout=POLL_INTERVAL_SECONDS)", "success, result = response_queue.get()")
        ],
    },
    {
        "id": "Qh",
        "name": "Espera de regime de volta a 1,5s (REGIME_BUSY_TIMEOUT_MS = 1500)",
        "target_test": "tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t9_busy_timeout_regime_allows_lock_held_for_3s_to_succeed",
        "replaces": [
            ("REGIME_BUSY_TIMEOUT_MS = 30000", "REGIME_BUSY_TIMEOUT_MS = 1500")
        ],
    },
]


def run_test(target_test: str, timeout_sec: int = 15) -> tuple[int, str]:
    cmd = [VENV_PYTEST, target_test, "-v"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        return proc.returncode, proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired as te:
        return 999, f"TIMEOUT EXPIRED após {timeout_sec}s: {te}"


def main():
    with open(SRC_FILE, "r", encoding="utf-8") as f:
        original_content = f.read()

    results = []

    for m in MUTATIONS:
        m_id = m["id"]
        m_name = m["name"]
        target = m["target_test"]
        print(f"\n==================== Rodando Mutação {m_id}: {m_name} ====================")

        # 1. Roda teste SEM mutação (espera-se verde)
        ret_clean, out_clean = run_test(target, timeout_sec=20)
        clean_status = "PASSED" if ret_clean == 0 else f"FAILED (ret={ret_clean})"
        print(f"Sem mutação: {clean_status}")

        # 2. Aplica mutações
        mutated_content = original_content
        applied_desc = []
        skip = False
        for rep_from, rep_to in m["replaces"]:
            if rep_from not in mutated_content:
                print(f"ERRO: Alvo de substituição para {m_id} não encontrado no arquivo!")
                results.append((m_id, "ERRO_SUBSTITUICAO", False))
                skip = True
                break
            mutated_content = mutated_content.replace(rep_from, rep_to, 1)
            applied_desc.append(f"- {rep_from}\n+ {rep_to}")

        if skip:
            continue

        with open(SRC_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(mutated_content)

        # 3. Roda teste COM mutação (espera-se falha/vermelho ou timeout)
        ret_mut, out_mut = run_test(target, timeout_sec=10)
        mut_status = "KILLED (FAILED/TIMEOUT)" if ret_mut != 0 else "SURVIVED (PASSED)"
        print(f"Com mutação: {mut_status} (ret={ret_mut})")

        # 4. Restaura original
        with open(SRC_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(original_content)

        # 5. Grava arquivo de evidência
        evidencia_path = os.path.join(EVIDENCIA_DIR, f"mutacao_{m_id}.txt")
        with open(evidencia_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"MUTAÇÃO {m_id}: {m_name}\n")
            f.write(f"Alvo: {target}\n")
            f.write("Substituições:\n" + "\n".join(applied_desc) + "\n\n")
            f.write("--- RESULTADO COM MUTAÇÃO (esperado: FALHA/KILLED) ---\n")
            f.write(f"Retcode: {ret_mut}\n")
            f.write(out_mut)
            f.write("\n--- RESULTADO SEM MUTAÇÃO (esperado: PASSOU) ---\n")
            f.write(f"Retcode: {ret_clean}\n")
            f.write(out_clean)

        killed = (ret_mut != 0) and (ret_clean == 0)
        results.append((m_id, m_name, killed))

    # Restauração final por segurança
    with open(SRC_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(original_content)

    print("\n\n==================== RESUMO FINAL DAS MUTAÇÕES BLOCO 1 ====================")
    all_ok = True
    for m_id, name, killed in results:
        status_str = "MORTA (OK)" if killed else "FALHOU / SOBREVIVEU"
        if not killed:
            all_ok = False
        print(f"[{status_str}] {m_id}: {name}")

    if all_ok:
        print("\nTodas as 8 mutações (Qa a Qh) foram mortas com sucesso!")
    else:
        print("\nATENÇÃO: Nem todas as mutações foram mortas!")
        sys.exit(1)


if __name__ == "__main__":
    main()
