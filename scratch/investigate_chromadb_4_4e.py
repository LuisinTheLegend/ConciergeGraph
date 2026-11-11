"""
scratch/investigate_chromadb_4_4e.py — Investigação do erro intermitente do ChromaDB (Bloco 5, Rodada 4.4e)

Executa:
1. Bateria 1: 30 execuções sequenciais isoladas de `tests/test_lightweight.py` no Python 3.10.
2. Bateria 2: 30 execuções sequenciais isoladas de `tests/memory_stress_test.py` no Python 3.12.
3. Bateria 3 (Diagnóstico de compartilhamento de estado/diretório `tests/_stress_test_workspace`):
   - 3a: 5 execuções no mesmo processo pytest (ordem normal: `tests/memory_stress_test.py tests/test_lightweight.py` no Python 3.10).
   - 3b: 5 execuções no mesmo processo pytest (ordem reversa: `tests/test_lightweight.py tests/memory_stress_test.py` no Python 3.12).
   - 3c: 10 execuções concorrentes entre processos (Python 3.10 executando `tests/test_lightweight.py` em paralelo com Python 3.12 executando `tests/memory_stress_test.py` no mesmo workspace).

Nota de ambiente:
Define `HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1` durante a execução para usar o cache local do
SentenceTransformer sem timeout de rede no sandbox, restaurando os valores originais no bloco `finally`.

Salva relatório completo e quaisquer tracebacks integrais em:
`scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt`
"""

from __future__ import annotations

import concurrent.futures
import os
import platform
import subprocess
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_FILE = os.path.join(
    REPO_ROOT, "scratch", "evidencia_4_4e", "chromadb_30_runs_investigation.txt"
)

PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")


def _get_env_versions(py_exe: str) -> str:
    code = (
        "import sys, sqlite3, pytest, chromadb; "
        "print(f'Python={sys.version.split()[0]} | pytest={pytest.__version__} | "
        "chromadb={chromadb.__version__} | sqlite3={sqlite3.sqlite_version}')"
    )
    proc = subprocess.run(
        [py_exe, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return proc.stdout.strip() if proc.returncode == 0 else f"ERRO: {proc.stderr}"


def _run_cmd(cmd: list[str], timeout: int = 180) -> tuple[int, float, str, str]:
    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44e-investigation-0000"
    env["GRAFO_LLM_MODEL"] = "none"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    dt = time.perf_counter() - t0
    return proc.returncode, dt, proc.stdout, proc.stderr


def main() -> None:
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    lines: list[str] = []

    orig_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    orig_tf_offline = os.environ.get("TRANSFORMERS_OFFLINE")

    def flush_out() -> None:
        with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

    def log(msg: str = "") -> None:
        print(msg, flush=True)
        lines.append(msg)

    try:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        log("=== INVESTIGAÇÃO DO CHROMADB INTERMITENTE (BLOCO 5 — RODADA 4.4e) ===")
        log(f"Sistema Operacional: {platform.system()} {platform.release()} ({platform.version()})")
        log(f"Ambiente Python 3.10 ({PY310}): {_get_env_versions(PY310)}")
        log(f"Ambiente Python 3.12 ({PY312}): {_get_env_versions(PY312)}")
        log(f"Estado original de HF_HUB_OFFLINE: {orig_hf_offline!r}")
        log("Nota: HF_HUB_OFFLINE=1 e TRANSFORMERS_OFFLINE=1 ativos durante as baterias (cache local do SentenceTransformer).")
        log("Nota adicional: Na tentativa anterior sem HF_HUB_OFFLINE=1, 22/22 execuções de test_lightweight.py no Python 3.10 passaram (~92s cada).")
        log()
        flush_out()

        # -----------------------------------------------------------------------
        # Bateria 1: 30 execuções sequenciais isoladas de tests/test_lightweight.py (Py 3.10)
        # -----------------------------------------------------------------------
        cmd_b1 = [PY310, "-m", "pytest", "tests/test_lightweight.py", "-v", "--tb=long"]
        log("-" * 80)
        log("1. BATERIA 1: 30 execuções sequenciais isoladas de tests/test_lightweight.py (Python 3.10)")
        log(f"Comando exato: HF_HUB_OFFLINE=1 {' '.join(cmd_b1)}")
        log("-" * 80)

        b1_failures = 0
        b1_tracebacks: list[str] = []
        t_b1_start = time.perf_counter()
        for i in range(1, 31):
            rc, dt, out, err = _run_cmd(cmd_b1)
            status = "PASS" if rc == 0 else f"FAIL(rc={rc})"
            log(f"  [B1 run {i:02d}/30] {status} ({dt:.2f}s)")
            if rc != 0:
                b1_failures += 1
                b1_tracebacks.append(
                    f"--- Traceback Bateria 1 Run #{i} (rc={rc}) ---\nSTDOUT:\n{out}\nSTDERR:\n{err}\n"
                )
        t_b1_total = time.perf_counter() - t_b1_start
        log(
            f"Resumo Bateria 1 (test_lightweight.py isolado, Python 3.10): "
            f"{b1_failures}/30 falhas em {t_b1_total:.2f}s "
            f"({'não reproduzido em 30 execuções' if b1_failures == 0 else f'reproduzido em {b1_failures}/30 execuções'})"
        )
        for tb in b1_tracebacks:
            log(tb)
        log()
        flush_out()

        # -----------------------------------------------------------------------
        # Bateria 2: 30 execuções sequenciais isoladas de tests/memory_stress_test.py (Py 3.12)
        # -----------------------------------------------------------------------
        cmd_b2 = [PY312, "-m", "pytest", "tests/memory_stress_test.py", "-v", "--tb=long"]
        log("-" * 80)
        log("2. BATERIA 2: 30 execuções sequenciais isoladas de tests/memory_stress_test.py (Python 3.12)")
        log(f"Comando exato: HF_HUB_OFFLINE=1 {' '.join(cmd_b2)}")
        log("-" * 80)

        b2_failures = 0
        b2_tracebacks: list[str] = []
        t_b2_start = time.perf_counter()
        for i in range(1, 31):
            rc, dt, out, err = _run_cmd(cmd_b2)
            status = "PASS" if rc == 0 else f"FAIL(rc={rc})"
            log(f"  [B2 run {i:02d}/30] {status} ({dt:.2f}s)")
            if rc != 0:
                b2_failures += 1
                b2_tracebacks.append(
                    f"--- Traceback Bateria 2 Run #{i} (rc={rc}) ---\nSTDOUT:\n{out}\nSTDERR:\n{err}\n"
                )
        t_b2_total = time.perf_counter() - t_b2_start
        log(
            f"Resumo Bateria 2 (memory_stress_test.py isolado, Python 3.12): "
            f"{b2_failures}/30 falhas em {t_b2_total:.2f}s "
            f"({'não reproduzido em 30 execuções' if b2_failures == 0 else f'reproduzido em {b2_failures}/30 execuções'})"
        )
        for tb in b2_tracebacks:
            log(tb)
        log()
        flush_out()

        # -----------------------------------------------------------------------
        # Bateria 3a: Mesmo processo pytest (ordem normal: memory_stress_test -> test_lightweight)
        # -----------------------------------------------------------------------
        cmd_b3a = [
            PY310,
            "-m",
            "pytest",
            "tests/memory_stress_test.py",
            "tests/test_lightweight.py",
            "-v",
            "--tb=long",
        ]
        log("-" * 80)
        log("3a. SONDA DE MESMO PROCESSO (ordem normal: memory_stress_test.py -> test_lightweight.py, Python 3.10, 5 execuções)")
        log(f"Comando exato: HF_HUB_OFFLINE=1 {' '.join(cmd_b3a)}")
        log("-" * 80)
        b3a_failures = 0
        for i in range(1, 6):
            rc, dt, out, err = _run_cmd(cmd_b3a)
            status = "PASS" if rc == 0 else f"FAIL(rc={rc})"
            log(f"  [B3a run {i:02d}/05] {status} ({dt:.2f}s)")
            if rc != 0:
                b3a_failures += 1
                log(f"--- Traceback B3a Run #{i} (rc={rc}) ---\nSTDOUT:\n{out}\nSTDERR:\n{err}\n")
        log(f"Resumo B3a: {b3a_failures}/5 falhas")
        log()
        flush_out()

        # -----------------------------------------------------------------------
        # Bateria 3b: Mesmo processo pytest (ordem reversa: test_lightweight -> memory_stress_test)
        # -----------------------------------------------------------------------
        cmd_b3b = [
            PY312,
            "-m",
            "pytest",
            "tests/test_lightweight.py",
            "tests/memory_stress_test.py",
            "-v",
            "--tb=long",
        ]
        log("-" * 80)
        log("3b. SONDA DE MESMO PROCESSO (ordem reversa: test_lightweight.py -> memory_stress_test.py, Python 3.12, 5 execuções)")
        log(f"Comando exato: HF_HUB_OFFLINE=1 {' '.join(cmd_b3b)}")
        log("-" * 80)
        b3b_failures = 0
        for i in range(1, 6):
            rc, dt, out, err = _run_cmd(cmd_b3b)
            status = "PASS" if rc == 0 else f"FAIL(rc={rc})"
            log(f"  [B3b run {i:02d}/05] {status} ({dt:.2f}s)")
            if rc != 0:
                b3b_failures += 1
                log(f"--- Traceback B3b Run #{i} (rc={rc}) ---\nSTDOUT:\n{out}\nSTDERR:\n{err}\n")
        log(f"Resumo B3b: {b3b_failures}/5 falhas")
        log()
        flush_out()

        # -----------------------------------------------------------------------
        # Bateria 3c: Execução simultânea em 2 processos compartilhando tests/_stress_test_workspace
        # -----------------------------------------------------------------------
        log("-" * 80)
        log("3c. SONDA DE CONCORRÊNCIA ENTRE PROCESSOS (10 pares simultâneos compartilhando tests/_stress_test_workspace)")
        log(f"Processo A (Py3.10): HF_HUB_OFFLINE=1 {' '.join(cmd_b1)}")
        log(f"Processo B (Py3.12): HF_HUB_OFFLINE=1 {' '.join(cmd_b2)}")
        log("-" * 80)
        b3c_pair_failures = 0
        for i in range(1, 11):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                fut_a = ex.submit(_run_cmd, cmd_b1)
                fut_b = ex.submit(_run_cmd, cmd_b2)
                rc_a, dt_a, out_a, err_a = fut_a.result()
                rc_b, dt_b, out_b, err_b = fut_b.result()
            st_a = "PASS" if rc_a == 0 else f"FAIL(rc={rc_a})"
            st_b = "PASS" if rc_b == 0 else f"FAIL(rc={rc_b})"
            log(f"  [B3c par {i:02d}/10] Py3.10(test_lightweight)={st_a} ({dt_a:.2f}s) | Py3.12(memory_stress_test)={st_b} ({dt_b:.2f}s)")
            if rc_a != 0 or rc_b != 0:
                b3c_pair_failures += 1
                if rc_a != 0:
                    log(f"--- Traceback B3c Par #{i} Processo A (Py3.10 test_lightweight, rc={rc_a}) ---\nSTDOUT:\n{out_a}\nSTDERR:\n{err_a}\n")
                if rc_b != 0:
                    log(f"--- Traceback B3c Par #{i} Processo B (Py3.12 memory_stress_test, rc={rc_b}) ---\nSTDOUT:\n{out_b}\nSTDERR:\n{err_b}\n")
        log(f"Resumo B3c (pares concorrentes compartilhando tests/_stress_test_workspace): {b3c_pair_failures}/10 pares com falha")
        log()
    finally:
        if orig_hf_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = orig_hf_offline

        if orig_tf_offline is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = orig_tf_offline

        log(
            f"Restauração de ambiente concluída: HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE')!r}, "
            f"TRANSFORMERS_OFFLINE={os.environ.get('TRANSFORMERS_OFFLINE')!r}"
        )
        flush_out()


if __name__ == "__main__":
    main()
