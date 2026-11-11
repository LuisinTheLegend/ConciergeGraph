"""
scratch/run_bloco1_4_4e_mutations.py — Executor Externo de Testes A1–A3, T-S1–T-S2 e Mutações Sm e Sn (Rodada 4.4e)

1. Executa A1, A2, A3, T-S1 e T-S2 contra storage/connection.py inalterado (verde) -> a1_a3_ts1_ts2_green.txt.
2. Aplica externamente Mutação Sm (remove self._conn.commit() no worker), comprova falha em vermelho de A1,
   restaura storage/connection.py, comprova verde sem mutação -> mutacao_Sm.txt.
3. Aplica externamente Mutação Sn (remove self._conn.rollback() no worker), comprova falha em vermelho de A2,
   restaura storage/connection.py, comprova verde sem mutação -> mutacao_Sn.txt.
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_FILE = os.path.join(REPO_ROOT, "storage", "connection.py")
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4e")
PYTHON_EXE = os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

MUTATIONS = [
    {
        "id": "Sm",
        "description": "Remover self._conn.commit() no _worker (storage/connection.py:324); A1 deve falhar",
        "target": (
            "                    job.result = job.fn(self._conn, *job.args, **job.kwargs)\n"
            "                    self._conn.commit()"
        ),
        "replacement": (
            "                    job.result = job.fn(self._conn, *job.args, **job.kwargs)\n"
            "                    pass  # Mutacao Sm: commit removido"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_a1_commit_visible_to_external_connection",
    },
    {
        "id": "Sn",
        "description": "Remover self._conn.rollback() no _worker (storage/connection.py:329); A2 deve falhar",
        "target": (
            "                except Exception as exc:\n"
            "                    try:\n"
            "                        self._conn.rollback()"
        ),
        "replacement": (
            "                except Exception as exc:\n"
            "                    try:\n"
            "                        pass  # Mutacao Sn: rollback removido"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_a2_rollback_on_error_prevents_partial_write_leak",
    },
    {
        "id": "So",
        "description": "Interromper laço do worker após falha de um job (storage/connection.py:338); A3 deve falhar",
        "target": (
            "                    job.error = exc\n"
            "                    logger.error(\"Error in write thread (transaction rolled back): %s\", exc)\n"
            "                    job.result_event.set()"
        ),
        "replacement": (
            "                    job.error = exc\n"
            "                    logger.error(\"Error in write thread (transaction rolled back): %s\", exc)\n"
            "                    job.result_event.set()\n"
            "                    break  # Mutacao So: interrompe worker apos falha de job"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_a3_failed_job_does_not_block_subsequent_jobs",
    },
    {
        "id": "Sp",
        "description": "Não marcar self._stopped = True em stop() (storage/connection.py:157); T-S1 deve falhar",
        "target": (
            "        logger.info(\"Requesting stop of SerializedWriteQueue...\")\n"
            "        self._stopped = True"
        ),
        "replacement": (
            "        logger.info(\"Requesting stop of SerializedWriteQueue...\")\n"
            "        self._stopped = False  # Mutacao Sp: nao marca _stopped em stop()"
        ),
        "test": "tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running",
    },
    {
        "id": "Sq",
        "description": "Manter while True no _worker em vez de while self._running (storage/connection.py:311); T-S2 deve falhar",
        "target": (
            "        try:\n"
            "            while self._running:"
        ),
        "replacement": (
            "        try:\n"
            "            while True:  # Mutacao Sq: consome jobs antes do sentinela em vez de sair por self._running"
        ),
        "test": "tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died",
    },
]


def _run_pytest(args: list[str]) -> tuple[int, str]:
    cmd = [PYTHON_EXE, "-m", "pytest", *args, "-v", "--tb=short"]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return proc.returncode, f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"


def main() -> None:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(TARGET_FILE, "rb") as f:
        original_bytes = f.read()
    original_content = original_bytes.decode("utf-8").replace("\r\n", "\n")

    # 1. Execução verde dos novos testes (A1, A2, A3, T-S1, T-S2) e da suíte completa do arquivo
    rc_all, out_all = _run_pytest(["tests/test_connection_queue_resilience.py"])
    green_path = os.path.join(EVIDENCE_DIR, "a1_a3_ts1_ts2_green.txt")
    with open(green_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            f"=== EXECUÇÃO VERDE DOS TESTES P1–P9, A1–A3 E T-S1–T-S2 (RODADA 4.4e) ===\n"
            f"Return Code: {rc_all}\n\n{out_all}"
        )
    assert rc_all == 0, f"Suíte test_connection_queue_resilience.py falhou sem mutação! rc={rc_all}\n{out_all}"

    # 2. Execução das mutações Sm e Sn
    try:
        for m in MUTATIONS:
            mid = m["id"]
            assert m["target"] in original_content, f"Alvo da mutação {mid} não encontrado!"
            mutated_content = original_content.replace(m["target"], m["replacement"], 1)

            with open(TARGET_FILE, "w", encoding="utf-8", newline="\n") as f:
                f.write(mutated_content)

            mut_rc, mut_out = _run_pytest([m["test"]])

            with open(TARGET_FILE, "wb") as f:
                f.write(original_bytes)

            clean_rc, clean_out = _run_pytest([m["test"]])

            killed = (mut_rc != 0) and (clean_rc == 0)
            status_str = "MORTA (OK)" if killed else "SOBREVIVEU / ERRO"
            print(f"Mutação {mid}: mut_rc={mut_rc}, clean_rc={clean_rc} -> {status_str}")

            report = (
                f"=== MUTAÇÃO {mid}: {m['description']} ===\n"
                f"Alvo: storage/connection.py\n"
                f"Teste: {m['test']}\n"
                f"Resultado COM mutação (VERMELHO): returncode={mut_rc} (esperado != 0)\n"
                f"Resultado SEM mutação (VERDE): returncode={clean_rc} (esperado == 0)\n"
                f"Status: {status_str}\n\n"
                f"--- [1] EXECUÇÃO COM MUTAÇÃO {mid} (VERMELHO) ---\n"
                f"{mut_out}\n"
                f"--- [2] EXECUÇÃO SEM MUTAÇÃO {mid} (VERDE) ---\n"
                f"{clean_out}\n"
            )
            out_path = os.path.join(EVIDENCE_DIR, f"mutacao_{mid}.txt")
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)

            if not killed:
                raise RuntimeError(f"Mutação {mid} não foi morta!")
    finally:
        with open(TARGET_FILE, "wb") as f:
            f.write(original_bytes)


if __name__ == "__main__":
    main()
