"""
scratch/run_bloco3_on_base_4_4g.py — Executa o teste de caracterização do Bloco 3
sobre a base 26a43e2 (ANTES do endurecimento do Bloco 2) em Python 3.10 e 3.12,
registrando que ele já passa na base (não existe teste vermelho para F4-034).
"""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")


def main() -> None:
    # Garante que tests/memory_stress_test.py ainda está no estado de 26a43e2
    diff_chk = subprocess.run(
        ["git", "diff", "26a43e2", "--", "tests/memory_stress_test.py", "tests/conftest.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert not diff_chk.stdout.strip(), "tests/memory_stress_test.py já modificado!"

    lines = ["=== BLOCO 3 (BASE 26a43e2): EXECUÇÃO DO TESTE DE CARACTERIZAÇÃO ANTES DO ENDURECIMENTO ==="]
    env = os.environ.copy()
    env["GRAFO_LIGHTWEIGHT_MODE"] = "false"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44g-bloco3-base"
    env["GRAFO_LLM_MODEL"] = "none"

    for tag, py_exe in [("py310", PY310), ("py312", PY312)]:
        p = subprocess.run(
            [py_exe, "-m", "pytest", "tests/test_stress_components_reuse.py", "-v", "--tb=short"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        lines.append(f"\n--- {tag} (base 26a43e2, sem alteração em bootstrap) | ReturnCode={p.returncode} ---")
        lines.append(p.stdout.strip())
        if p.stderr.strip():
            lines.append("STDERR:\n" + p.stderr.strip())
        assert p.returncode == 0

    lines.append(
        "\nConclusão Bloco 3 (sobre 26a43e2): O teste de caracterização do ciclo de reuso PASSA em 26a43e2 "
        "em Py3.10 e Py3.12 (RC=0). Não há teste vermelho reproduzindo o bug F4-034."
    )
    out_path = os.path.join(EV_DIR, "bloco3_base_26a43e2_check.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

