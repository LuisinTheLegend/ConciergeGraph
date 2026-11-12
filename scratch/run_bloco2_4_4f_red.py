"""
scratch/run_bloco2_4_4f_red.py — Prova em VERMELHO no commit 3dccf68 (Bloco 2, Rodada 4.4f)

Executa 10 pares paralelos de `pytest tests/memory_stress_test.py` no Python 3.12 sobre o código
inalterado do commit 3dccf68, contabilizando quantos pares falharam e os tipos de erro observados.
Salva a evidência em `scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt`.
"""

from __future__ import annotations

import concurrent.futures
import os
import platform
import re
import shutil
import subprocess
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4f")
OUT_FILE = os.path.join(EV_DIR, "red_10_pairs_memory_stress_3dccf68.txt")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")

ERROR_PATTERNS = [
    "sqlite3.OperationalError: unable to open database file",
    "sqlite3.OperationalError: database is locked",
    "sqlite3.OperationalError: disk I/O error",
    "sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid",
    "ProjectNotFoundError",
    "ValueError: Project not found",
    "FileNotFoundError",
    "PermissionError",
    "PanicException",
    "InternalError",
]


def _run_one(cmd: list[str], timeout: int = 180) -> tuple[int, float, str, str]:
    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44f-red-0000"
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


def _extract_error_types(text: str) -> list[str]:
    found = []
    for pat in ERROR_PATTERNS:
        if pat in text:
            found.append(pat)
    for m in re.findall(r"^E\s+([A-Za-z0-9_.]+Error: [^\n]+)", text, flags=re.MULTILINE):
        short = m.strip()
        if short not in found:
            found.append(short[:120])
    return found


def main() -> None:
    os.makedirs(EV_DIR, exist_ok=True)
    cmd = [PY312, "-m", "pytest", "tests/memory_stress_test.py", "-v", "--tb=short"]

    head_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()

    lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg, flush=True)
        lines.append(msg)

    log("=== PROVA EM VERMELHO (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS DE memory_stress_test.py NO COMMIT 3dccf68 ===")
    log(f"Commit HEAD: {head_sha}")
    log(f"Sistema Operacional: {platform.system()} {platform.release()} ({platform.version()})")
    log(f"Comando por processo: {' '.join(cmd)}")
    log("-" * 80)

    pair_failures = 0
    error_type_counts: dict[str, int] = {}
    details: list[str] = []

    for i in range(1, 11):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fa = ex.submit(_run_one, cmd)
            fb = ex.submit(_run_one, cmd)
            rc_a, dt_a, out_a, err_a = fa.result()
            rc_b, dt_b, out_b, err_b = fb.result()

        failed = (rc_a != 0) or (rc_b != 0)
        if failed:
            pair_failures += 1

        errs_a = _extract_error_types(out_a + "\n" + err_a) if rc_a != 0 else []
        errs_b = _extract_error_types(out_b + "\n" + err_b) if rc_b != 0 else []
        combined_errs = sorted(set(errs_a + errs_b))
        for e in combined_errs:
            error_type_counts[e] = error_type_counts.get(e, 0) + 1

        st_a = "PASS" if rc_a == 0 else f"FAIL(rc={rc_a})"
        st_b = "PASS" if rc_b == 0 else f"FAIL(rc={rc_b})"
        log(
            f"  [Par {i:02d}/10] ProcA={st_a} ({dt_a:.2f}s) | ProcB={st_b} ({dt_b:.2f}s) "
            f"| Erros={combined_errs if combined_errs else 'nenhum'}"
        )

        if failed:
            details.append(
                f"--- Detalhe Par #{i:02d} (ProcA rc={rc_a}, ProcB rc={rc_b}) ---\n"
                f"[ProcA STDOUT]:\n{out_a}\n[ProcB STDOUT]:\n{out_b}\n"
            )

        with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

    # Limpa eventual resíduo deixado pelo código antigo antes da correção
    legacy_dir = os.path.join(REPO_ROOT, "tests", "_stress_test_workspace")
    if os.path.exists(legacy_dir):
        shutil.rmtree(legacy_dir, ignore_errors=True)

    log("-" * 80)
    log(f"RESUMO VERMELHO (commit 3dccf68): {pair_failures}/10 pares paralelos falharam.")
    log("Contagem por tipo de erro observado nos pares com falha:")
    for k, v in sorted(error_type_counts.items(), key=lambda x: (-x[1], x[0])):
        log(f"  - {k}: {v} par(es)")
    log("-" * 80)
    log("\n=== TRACEBACKS COMPLETOS DOS PARES COM FALHA ===")
    for d in details:
        log(d)

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    assert pair_failures > 0, "Esperava-se falha em vermelho nos 10 pares paralelos no commit 3dccf68!"


if __name__ == "__main__":
    main()

