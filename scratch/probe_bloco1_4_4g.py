"""
scratch/probe_bloco1_4_4g.py — Sondas observacionais locais do Bloco 1 (Rodada 4.4g):
1. Verifica em Py3.10 e Py3.12 a sonda mínima descrita no pedido (PersistentClient vivo -> rmtree -> novo PersistentClient).
2. Verifica o comportamento de shutil.rmtree(TEST_DIR, ignore_errors=True) no teardown real do projeto no Windows.
3. Verifica pyproject.toml / requirements.txt / .github/workflows/ci.yml quanto à versão de chromadb.
"""

import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")

PROBE_MIN_CODE = """
import chromadb, shutil, tempfile, os
from chromadb.config import Settings

results = []
for i in range(3):
    d = tempfile.mkdtemp(prefix=f"chroma_min_probe_{i}_")
    try:
        c1 = chromadb.PersistentClient(path=d, settings=Settings(anonymized_telemetry=False))
        col1 = c1.get_or_create_collection("probe_col")
        err_rm = None
        try:
            shutil.rmtree(d)
        except Exception as e:
            err_rm = f"{type(e).__name__}: {e}"
        shutil.rmtree(d, ignore_errors=True)
        err_c2 = None
        try:
            c2 = chromadb.PersistentClient(path=d, settings=Settings(anonymized_telemetry=False))
            col2 = c2.get_or_create_collection("probe_col")
        except Exception as e:
            err_c2 = f"{type(e).__name__}: {e}"
        results.append((i + 1, err_rm, err_c2, os.path.exists(os.path.join(d, "chroma.sqlite3"))))
    finally:
        from chromadb.api.client import SharedSystemClient
        SharedSystemClient.clear_system_cache()
        shutil.rmtree(d, ignore_errors=True)

for idx, err_rm, err_c2, db_remained in results:
    print(f"trial={idx} | rmtree_err={err_rm} | c2_err={err_c2} | sqlite_remained_after_ignore_errors={db_remained}")
"""


def main() -> None:
    lines = ["=== BLOCO 1 (PARTE 3): SONDA LOCAL DE COMPORTAMENTO WINDOWS & CONFIG CI CHROMADB ==="]

    for tag, py_exe in [("py310", PY310), ("py312", PY312)]:
        p = subprocess.run([py_exe, "-c", PROBE_MIN_CODE], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
        lines.append(f"\n--- Sonda mínima (rmtree no caminho vivo, Windows) em {tag} ---")
        lines.append(p.stdout.strip() or p.stderr.strip())

    # Verificar requisitos e CI
    lines.append("\n--- Versão de chromadb nos arquivos do projeto vs local ---")
    for rel, ln_range in [("pyproject.toml", (37, 40)), ("requirements.txt", (3, 6)), (".github/workflows/ci.yml", (30, 50))]:
        lines.append(f"[{rel}]")
        with open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as f:
            all_ln = f.readlines()
        for num in range(ln_range[0], min(ln_range[1], len(all_ln)) + 1):
            lines.append(f"  {num}: {all_ln[num - 1].rstrip()}")

    out_path = os.path.join(EV_DIR, "bloco1_sonda_and_ci_versions.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
