"""
scratch/run_bloco1_4_4d_mutations.py — Executor Externo de Mutações Ra–Rh em storage/connection.py (Rodada 4.4d)

Aplica cada mutação externamente em storage/connection.py, roda os testes correspondentes
em tests/test_connection_queue_resilience.py, restaura o arquivo original, roda o controle
sem mutação e grava o relatório individual em scratch/evidencia_4_4d/mutacao_<ID>.txt.
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_FILE = os.path.join(REPO_ROOT, "storage", "connection.py")
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d")
PYTHON_EXE = os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

MUTATIONS = [
    {
        "id": "Ra",
        "description": "Sem retry na partida (MAX_CONNECT_RETRIES: int = 1)",
        "target": "MAX_CONNECT_RETRIES: int = 5",
        "replacement": "MAX_CONNECT_RETRIES: int = 1",
        "test": "tests/test_connection_queue_resilience.py::test_p2_startup_retries_twice_on_locked_then_succeeds",
    },
    {
        "id": "Rb",
        "description": "Sem checagem de vida no laço do submit (is_alive removido do while)",
        "target": (
            "        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):\n"
            "            if not self._thread.is_alive() and not job.result_event.is_set():\n"
            "                raise self._build_worker_dead_error()"
        ),
        "replacement": (
            "        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):\n"
            "            pass"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent",
    },
    {
        "id": "Rc",
        "description": "wait() sem prazo e sem checagem no submit (comportamento original)",
        "target": (
            "        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):\n"
            "            if not self._thread.is_alive() and not job.result_event.is_set():\n"
            "                raise self._build_worker_dead_error()"
        ),
        "replacement": "        job.result_event.wait()",
        "test": "tests/test_connection_queue_resilience.py::test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent",
    },
    {
        "id": "Rd",
        "description": "Sem propagar o erro de partida (_startup_error nao armazenado/propagado para start/submit)",
        "target": "                self._startup_error = exc\n                self._running = False",
        "replacement": "                self._startup_error = None\n                self._running = False",
        "test": "tests/test_connection_queue_resilience.py::test_p1_connect_persistent_locked_fails_fast",
    },
    {
        "id": "Re",
        "description": "Sem drenar jobs pendentes ao morrer (_drain_pending_with_error desativado no finally do _worker)",
        "target": (
            "            if self._fatal_error is not None:\n"
            "                self._drain_pending_with_error(self._fatal_error)\n"
            "            elif not self._stopped:\n"
            "                self._drain_pending_with_error(\n"
            "                    RuntimeError(\"sqlite-writer terminated unexpectedly\")\n"
            "                )"
        ),
        "replacement": "            pass  # Mutacao Re: sem drenar jobs pendentes ao morrer",
        "test": "tests/test_connection_queue_resilience.py::test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent",
    },
    {
        "id": "Rf",
        "description": "Regime de busy_timeout alterado (REGIME_BUSY_TIMEOUT_MS: int = 1500 em vez de 5000)",
        "target": "REGIME_BUSY_TIMEOUT_MS: int = 5000",
        "replacement": "REGIME_BUSY_TIMEOUT_MS: int = 1500",
        "test": "tests/test_connection_queue_resilience.py::test_p7_regime_pragmas_and_row_factory",
    },
    {
        "id": "Rg",
        "description": "Prazo total adicionado ao job em execução (levanta TimeoutError após 0.5s em submit, morta por P5)",
        "target": (
            "        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):\n"
            "            if not self._thread.is_alive() and not job.result_event.is_set():\n"
            "                raise self._build_worker_dead_error()"
        ),
        "replacement": (
            "        _t0_mut = time.monotonic()\n"
            "        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):\n"
            "            if (time.monotonic() - _t0_mut) > 0.5:\n"
            "                raise TimeoutError('Mutacao Rg: total execution timeout exceeded')\n"
            "            if not self._thread.is_alive() and not job.result_event.is_set():\n"
            "                raise self._build_worker_dead_error()"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_p5_long_running_job_2s_succeeds_without_total_timeout",
    },
    {
        "id": "Rh",
        "description": "Sem fechar a conexão na falha de partida (conn.close() removido no except OperationalError)",
        "target": (
            "            except sqlite3.OperationalError as exc:\n"
            "                if conn is not None:\n"
            "                    try:\n"
            "                        conn.close()\n"
            "                    except Exception as close_exc:\n"
            "                        logger.debug(\"Error closing failed startup connection: %s\", close_exc)\n"
            "                    conn = None"
        ),
        "replacement": (
            "            except sqlite3.OperationalError as exc:\n"
            "                conn = None  # Mutacao Rh: sem fechar conexao na falha de partida"
        ),
        "test": "tests/test_connection_queue_resilience.py::test_p3_non_lock_operational_error_fails_immediately_and_closes_conn",
    },
]


def _run_pytest(test_node: str) -> tuple[int, str]:
    cmd = [PYTHON_EXE, "-m", "pytest", test_node, "-v", "--tb=short"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=25,
        )
        return proc.returncode, f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    except subprocess.TimeoutExpired as exc:
        return 999, f"TIMEOUT EXPIRED (25s)\nSTDOUT:\n{exc.stdout}\nSTDERR:\n{exc.stderr}"


def main() -> None:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        original_content = f.read()

    summary_lines = []
    try:
        for m in MUTATIONS:
            mid = m["id"]
            assert m["target"] in original_content, f"Alvo da mutação {mid} não encontrado em storage/connection.py!"
            mutated_content = original_content.replace(m["target"], m["replacement"], 1)

            with open(TARGET_FILE, "w", encoding="utf-8", newline="\n") as f:
                f.write(mutated_content)

            mut_rc, mut_out = _run_pytest(m["test"])

            with open(TARGET_FILE, "w", encoding="utf-8", newline="\n") as f:
                f.write(original_content)

            clean_rc, clean_out = _run_pytest(m["test"])

            killed = (mut_rc != 0) and (clean_rc == 0)
            status_str = "MORTA (OK)" if killed else "SOBREVIVEU / ERRO"
            summary_lines.append(
                f"Mutação {mid}: {m['description']} -> c/ mutação ret={mut_rc}, s/ mutação ret={clean_rc} [{status_str}]"
            )
            print(summary_lines[-1], flush=True)

            report = (
                f"=== MUTAÇÃO {mid}: {m['description']} ===\n"
                f"Alvo: storage/connection.py\n"
                f"Teste: {m['test']}\n"
                f"Resultado COM mutação: returncode={mut_rc} (esperado != 0)\n"
                f"Resultado SEM mutação: returncode={clean_rc} (esperado == 0)\n"
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
                raise RuntimeError(f"Mutação {mid} não foi morta corretamente!")
    finally:
        with open(TARGET_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(original_content)

    print("\nResumo final Bloco 1 (Ra–Rh):")
    for line in summary_lines:
        print("  " + line)


if __name__ == "__main__":
    main()

