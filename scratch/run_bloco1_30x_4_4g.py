"""
scratch/run_bloco1_30x_4_4g.py — Bloco 1 da Rodada 4.4g:
Executa a suíte completa 30 vezes em Python 3.10 e 30 vezes em Python 3.12 na ordem normal
sobre o estado do commit 26a43e2, contabilizando qualquer chromadb InternalError (ou outra falha)
e registrando tracebacks completos, versões e contagens em scratch/evidencia_4_4g/.
"""

import os
import re
import subprocess
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
os.makedirs(EV_DIR, exist_ok=True)

PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")

RUNS_PER_VERSION = 30
SUMMARY_PATH = os.path.join(EV_DIR, "bloco1_30x_results.txt")
TRACEBACKS_PATH = os.path.join(EV_DIR, "bloco1_tracebacks.txt")


def get_versions(py_exe: str) -> str:
    code = (
        "import sys, chromadb, pytest; "
        "print(f'Python={sys.version.splitlines()[0]} | chromadb={chromadb.__version__} | pytest={pytest.__version__}')"
    )
    p = subprocess.run([py_exe, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    return p.stdout.strip()


def run_suite_once(py_exe: str) -> tuple[int, float, str, str]:
    env = os.environ.copy()
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["GRAFO_LIGHTWEIGHT_MODE"] = "false"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44g-bloco1-0000"
    env["GRAFO_LLM_MODEL"] = "none"

    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            [py_exe, "-m", "pytest", "-v", "--tb=short"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=360,
        )
        dt = time.perf_counter() - t0
        return p.returncode, dt, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        dt = time.perf_counter() - t0
        out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return -1, dt, out, f"TIMEOUT(360s): {exc}\n{err}"


def flush_reports(lines: list[str], tb_blocks: list[str]) -> None:
    with open(SUMMARY_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(TRACEBACKS_PATH, "w", encoding="utf-8", newline="\n") as f:
        if tb_blocks:
            f.write("\n".join(tb_blocks) + "\n")
        else:
            f.write("=== BLOCO 1 (RODADA 4.4g): TRACEBACKS ===\nNenhum erro/traceback observado em todas as execuções.\n")


def main() -> None:
    ver_310 = get_versions(PY310)
    ver_312 = get_versions(PY312)

    lines = [
        "=== BLOCO 1 (RODADA 4.4g): REPRODUÇÃO EM 30+30 EXECUÇÕES SEQUENCIAIS (ESTADO 26a43e2) ===",
        "Comando: <python> -m pytest -v --tb=short (ordem normal, env: TOKENIZERS_PARALLELISM=false, GRAFO_LIGHTWEIGHT_MODE=false, HF_HUB_OFFLINE=1)",
        f"Interpretador Py3.10: {ver_310}",
        f"Interpretador Py3.12: {ver_312}",
        "",
    ]
    tb_blocks: list[str] = ["=== BLOCO 1 (RODADA 4.4g): TRACEBACKS COMPLETOS DE FALHAS/InternalError ==="]
    flush_reports(lines, tb_blocks)

    summary_counts = {}

    for tag, py_exe in [("py310", PY310), ("py312", PY312)]:
        lines.append(f"--- Execuções em {tag} ({RUNS_PER_VERSION}x) ---")
        rc_nonzero = 0
        chroma_internal_errors = 0
        other_errors = 0

        for idx in range(1, RUNS_PER_VERSION + 1):
            rc, dt, out, err = run_suite_once(py_exe)
            combined = out + "\n" + err
            # Extrair última linha do resumo pytest (ex: "475 passed, 1 xfailed, ...")
            summary_line = ""
            for ln in reversed(out.splitlines()):
                if "passed" in ln or "failed" in ln or "error" in ln:
                    summary_line = ln.strip()
                    break

            has_chroma_internal = ("chromadb.errors.InternalError" in combined) or (
                "InternalError" in combined and "chromadb" in combined
            )
            if rc != 0:
                rc_nonzero += 1
                if has_chroma_internal:
                    chroma_internal_errors += 1
                else:
                    other_errors += 1
                tb_blocks.append(f"\n[{tag} Run {idx:02d}/{RUNS_PER_VERSION}] rc={rc} ({dt:.2f}s)\nSTDOUT:\n{out}\nSTDERR:\n{err}")

            status = "PASS" if rc == 0 else ("CHROMA_INTERNAL_ERROR" if has_chroma_internal else f"FAIL(rc={rc})")
            msg = f"  [{tag} {idx:02d}/{RUNS_PER_VERSION}] {status} ({dt:.2f}s) | {summary_line}"
            print(msg, flush=True)
            lines.append(msg)
            flush_reports(lines, tb_blocks)

        summary_counts[tag] = (RUNS_PER_VERSION, chroma_internal_errors, rc_nonzero, other_errors)
        lines.append(
            f"=> Resumo {tag}: total={RUNS_PER_VERSION}, chromadb_InternalError={chroma_internal_errors}, "
            f"outros_erros={other_errors}, total_falhas={rc_nonzero}\n"
        )
        flush_reports(lines, tb_blocks)

    lines.append("=== CONSOLIDADO FINAL BLOCO 1 ===")
    for tag, (tot, ci, fail, oth) in summary_counts.items():
        lines.append(f"  {tag}: {ci}/{tot} chromadb InternalError | {oth}/{tot} outros erros | {fail}/{tot} falhas totais")
    flush_reports(lines, tb_blocks)
    print("Bloco 1 (30+30 execuções) concluído.", flush=True)


if __name__ == "__main__":
    main()
