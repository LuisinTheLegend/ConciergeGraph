"""
scratch/run_multiversion_suites_4_4f.py — Executa a suíte completa em 5 versões do CPython (3.10, 3.11, 3.12, 3.13, 3.14)
nas duas ordens (padrão e invertida com --reverse), incluindo tests/memory_stress_test.py (Rodada 4.4f).

Nota: Se o chromadb intermitente voltar a aparecer depois do isolamento, registra o traceback completo (Bloco 4).
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4f")

ENVS = [
    ("py310", os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")),
    ("py311", os.path.join(REPO_ROOT, ".venv_311", "Scripts", "python.exe")),
    ("py312", os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")),
    ("py313", os.path.join(REPO_ROOT, ".venv_313", "Scripts", "python.exe")),
    ("py314", os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")),
]


def run_one_env(tag: str, py_exe: str) -> None:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    ver_proc = subprocess.run([py_exe, "-VV"], capture_output=True, text=True, encoding="utf-8")
    ver_str = ver_proc.stdout.strip() or ver_proc.stderr.strip()

    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44f-suite-0000"
    env["GRAFO_LLM_MODEL"] = "none"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"

    cmd_std = [py_exe, "-m", "pytest", "tests/", "tests/memory_stress_test.py", "-q"]
    cmd_rev = [py_exe, "-m", "pytest", "tests/", "tests/memory_stress_test.py", "--reverse", "-q"]

    print(f"[{tag}] Running standard order ({ver_str})...", flush=True)
    p_std = subprocess.run(cmd_std, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    print(f"[{tag}] Standard RC={p_std.returncode}", flush=True)

    print(f"[{tag}] Running reverse order ({ver_str})...", flush=True)
    p_rev = subprocess.run(cmd_rev, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    print(f"[{tag}] Reverse RC={p_rev.returncode}", flush=True)

    report = (
        f"=== SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===\n"
        f"Tag: {tag}\n"
        f"Interpretador: {py_exe}\n"
        f"Versão do Python: {ver_str}\n"
        f"Ordem Padrão ReturnCode: {p_std.returncode}\n"
        f"Ordem Invertida (--reverse) ReturnCode: {p_rev.returncode}\n\n"
        f"--- [1] ORDEM PADRÃO (pytest tests/ tests/memory_stress_test.py -q) ---\n"
        f"STDOUT:\n{p_std.stdout}\n"
        f"STDERR:\n{p_std.stderr}\n\n"
        f"--- [2] ORDEM INVERTIDA (pytest tests/ tests/memory_stress_test.py --reverse -q) ---\n"
        f"STDOUT:\n{p_rev.stdout}\n"
        f"STDERR:\n{p_rev.stderr}\n"
    )
    out_file = os.path.join(EVIDENCE_DIR, f"suite_{tag}.txt")
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)

    if p_std.returncode != 0 or p_rev.returncode != 0:
        raise RuntimeError(f"Falha na suíte {tag}: std={p_std.returncode}, rev={p_rev.returncode}")


def main() -> None:
    target_tags = sys.argv[1:] if len(sys.argv) > 1 else [t for t, _ in ENVS]
    for tag, py_exe in ENVS:
        if tag in target_tags:
            run_one_env(tag, py_exe)


if __name__ == "__main__":
    main()

