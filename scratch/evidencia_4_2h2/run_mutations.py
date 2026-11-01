"""scratch/evidencia_4_2h2/run_mutations.py

Executa as 4 mutações obrigatórias da Rodada 4.2h-2:
  (i) remover o lookbehind de "sk-" em main.py -> testes negativos do item 1 falham
  (ii) aplicar a correção só no filtro, não no scanner -> teste de paridade falha
  (iii) restaurar root.handlers.clear() em main.py -> teste do item 4a falha
  (iv) descomentar GRAFO_LLM_PROVIDER em .env.example -> teste do item 2 falha
Cada mutação restaura imediatamente o arquivo original no bloco finally e salva
a saída literal em arquivo UTF-8.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


def run_and_save(out_file: Path, cmd: list[str]) -> int:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = proc.stdout + (
        ("\n" if proc.stdout and not proc.stdout.endswith("\n") else "") + proc.stderr
        if proc.stderr
        else ""
    )
    out_file.write_text(combined, encoding="utf-8")
    print(f"[{out_file.name}] rc={proc.returncode}")
    for ln in combined.splitlines()[-6:]:
        print("  ", ln)
    return proc.returncode


def main() -> int:
    main_py = REPO_ROOT / "main.py"
    scanner_py = REPO_ROOT / "scratch" / "tools" / "scan_secrets.py"
    env_example = REPO_ROOT / ".env.example"

    orig_main = main_py.read_bytes()
    orig_scanner = scanner_py.read_bytes()
    orig_env = env_example.read_bytes()

    # Mutação (i): remover o lookbehind de "sk-" em main.py
    try:
        txt = orig_main.decode("utf-8")
        mut_txt = txt.replace(
            '(_re.compile(r"(?<![A-Za-z0-9_])sk-[\\w*-]{6,}"), "[REDACTED]"),',
            '(_re.compile(r"sk-[\\w*-]{6,}"), "[REDACTED]"),',
        )
        assert mut_txt != txt, "Mutação (i) não alterou main.py"
        main_py.write_bytes(mut_txt.encode("utf-8"))
        rc1 = run_and_save(
            HERE / "mut1_remove_sk_lookbehind.txt",
            [sys.executable, "-m", "pytest", "tests/test_secret_redaction.py", "-k", "test_f4_022_negative_cases_remain_identical", "-q"],
        )
        assert rc1 != 0, "Mutação (i) deveria falhar!"
    finally:
        main_py.write_bytes(orig_main)

    # Mutação (ii): aplicar a correção só no filtro, não no scanner (remover lookbehind de sk- no scanner)
    try:
        txt = orig_scanner.decode("utf-8")
        mut_txt = txt.replace(
            '("SK_KEY_FRAGMENT", re.compile(r"(?<![A-Za-z0-9_])sk-[\\w*-]{6,}")),',
            '("SK_KEY_FRAGMENT", re.compile(r"sk-[\\w*-]{6,}")),',
        )
        assert mut_txt != txt, "Mutação (ii) não alterou scan_secrets.py"
        scanner_py.write_bytes(mut_txt.encode("utf-8"))
        rc2 = run_and_save(
            HERE / "mut2_scanner_divergence_parity.txt",
            [sys.executable, "-m", "pytest", "tests/test_secret_redaction.py", "-k", "test_f4_022_filter_and_scanner_parity", "-q"],
        )
        assert rc2 != 0, "Mutação (ii) deveria falhar!"
    finally:
        scanner_py.write_bytes(orig_scanner)

    # Mutação (iii): restaurar root.handlers.clear() em main.py
    try:
        txt = orig_main.decode("utf-8")
        target_block = (
            "    for existing_h in list(root.handlers):\r\n"
            "        if getattr(existing_h, \"_grafo_log_handler\", False):\r\n"
            "            root.removeHandler(existing_h)"
        )
        if target_block not in txt:
            target_block = target_block.replace("\r\n", "\n")
        mut_txt = txt.replace(target_block, "    root.handlers.clear()")
        assert mut_txt != txt, "Mutação (iii) não alterou main.py"
        main_py.write_bytes(mut_txt.encode("utf-8"))
        rc3 = run_and_save(
            HERE / "mut3_restore_handlers_clear.txt",
            [sys.executable, "-m", "pytest", "tests/test_secret_redaction.py", "-k", "test_item4a_setup_logging_preserves_foreign_root_handlers", "-q"],
        )
        assert rc3 != 0, "Mutação (iii) deveria falhar!"
    finally:
        main_py.write_bytes(orig_main)

    # Mutação (iv): descomentar GRAFO_LLM_PROVIDER em .env.example
    try:
        txt = orig_env.decode("utf-8")
        mut_txt = txt.replace("# GRAFO_LLM_PROVIDER=gemini", "GRAFO_LLM_PROVIDER=gemini")
        assert mut_txt != txt, "Mutação (iv) não alterou .env.example"
        env_example.write_bytes(mut_txt.encode("utf-8"))
        rc4 = run_and_save(
            HERE / "mut4_uncomment_env_example_provider.txt",
            [sys.executable, "-m", "pytest", "tests/test_env_example_provider.py", "-q"],
        )
        assert rc4 != 0, "Mutação (iv) deveria falhar!"
    finally:
        env_example.write_bytes(orig_env)

    print("ALL 4 MUTATIONS VERIFIED AND REVERTED SUCCESSFULLY.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

