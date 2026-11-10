"""
scratch/run_bloco2_4_4d_mutation.py — Executor Externo da Mutação M10d em Nível de Importação de Módulo (Bloco 2 - Rodada 4.4d)

Injeta no topo de um módulo de teste (executado durante a importação na fase de coleta do pytest):
1. M10d_import_new: adição de um novo atributo global em `interface.mcp_server` no momento da importação do módulo de teste.
2. M10d_import_mutate: alteração de identidade de `interface.mcp_server.db_manager` no momento da importação do módulo de teste.

Comprova que o snapshot registrado na importação de `tests/conftest.py` e verificado em `pytest_collection_finish`
mata ambas as variantes com `returncode != 0`, e que sem a mutação o pytest passa com `returncode == 0`.
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_TEST_FILE = os.path.join(REPO_ROOT, "tests", "test_interface_contracts.py")
EVIDENCE_FILE = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d", "mutacao_M10d_import.txt")
PYTHON_EXE = os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable


def _run_pytest() -> tuple[int, str]:
    cmd = [PYTHON_EXE, "-m", "pytest", "tests/test_interface_contracts.py", "-v", "--tb=short"]
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
    with open(TARGET_TEST_FILE, "r", encoding="utf-8") as f:
        original = f.read()

    anchor = "from interface.mcp_server import GrafoConciergeServer"
    assert anchor in original, f"Anchor '{anchor}' not found in {TARGET_TEST_FILE}"

    try:
        # Variante 1: Adição de global novo em nível de importação do módulo
        mut1 = original.replace(
            anchor,
            anchor + "\nimport interface.mcp_server as _mcp_srv_mut\n_mcp_srv_mut._leaked_at_module_import_m10d = 'POLLUTED_AT_IMPORT'",
            1,
        )
        with open(TARGET_TEST_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(mut1)
        rc_mut1, out_mut1 = _run_pytest()

        # Variante 2: Mutação de global existente (db_manager) em nível de importação do módulo
        mut2 = original.replace(
            anchor,
            anchor + "\nimport interface.mcp_server as _mcp_srv_mut\n_mcp_srv_mut.db_manager = 'POLLUTED_DB_MANAGER_AT_IMPORT'",
            1,
        )
        with open(TARGET_TEST_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(mut2)
        rc_mut2, out_mut2 = _run_pytest()

        # Restaura arquivo original e executa controle limpo
        with open(TARGET_TEST_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(original)
        rc_clean, out_clean = _run_pytest()

        killed = (rc_mut1 != 0) and (rc_mut2 != 0) and (rc_clean == 0)
        status = "MORTA (OK)" if killed else "SOBREVIVEU / ERRO"

        report = (
            "=== MUTAÇÃO M10d (NÍVEL DE IMPORTAÇÃO DE MÓDULO) — BLOCO 2 (RODADA 4.4d) ===\n"
            f"Arquivo alvo mutado: tests/test_interface_contracts.py\n"
            f"Variante 1 (novo global no topo do módulo durante import): returncode={rc_mut1} (esperado != 0)\n"
            f"Variante 2 (mutação de db_manager no topo do módulo durante import): returncode={rc_mut2} (esperado != 0)\n"
            f"Controle SEM mutação: returncode={rc_clean} (esperado == 0)\n"
            f"Status Global: {status}\n\n"
            "--- [1] COM MUTAÇÃO M10d (NOVO GLOBAL NA IMPORTAÇÃO DO MÓDULO) ---\n"
            f"{out_mut1}\n"
            "--- [2] COM MUTAÇÃO M10d (MUTAÇÃO DE GLOBAL EXISTENTE NA IMPORTAÇÃO DO MÓDULO) ---\n"
            f"{out_mut2}\n"
            "--- [3] SEM MUTAÇÃO (VERDE) ---\n"
            f"{out_clean}\n"
        )
        with open(EVIDENCE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(report)
        print(f"M10d_import: mut1={rc_mut1}, mut2={rc_mut2}, clean={rc_clean} -> {status}")
        if not killed:
            raise RuntimeError("M10d_import não foi morta!")
    finally:
        with open(TARGET_TEST_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(original)


if __name__ == "__main__":
    main()

