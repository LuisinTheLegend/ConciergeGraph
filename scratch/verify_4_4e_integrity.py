"""
scratch/verify_4_4e_integrity.py — Verifica UTF-8 sem BOM/nulos, scan_secrets.py e zero alteração em código de produto (Rodada 4.4e)
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4e")


def main() -> None:
    os.makedirs(EV_DIR, exist_ok=True)

    # 1. Executar scan_secrets.py
    proc_sec = subprocess.run(
        [sys.executable, "scratch/tools/scan_secrets.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    sec_out = (
        f"=== SCAN_SECRETS.PY (REGRA 13 — RODADA 4.4e) ===\n"
        f"Return Code: {proc_sec.returncode}\n"
        f"STDOUT:\n{proc_sec.stdout}\nSTDERR:\n{proc_sec.stderr}\n"
    )
    with open(os.path.join(EV_DIR, "scan_secrets.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sec_out)
    assert proc_sec.returncode == 0, f"scan_secrets.py falhou:\n{sec_out}"

    # 2. Verificar UTF-8 sem BOM e sem bytes nulos
    targets = sorted(
        glob.glob(os.path.join(EV_DIR, "*"))
        + [
            os.path.join(REPO_ROOT, "audits", "relatorio_4_4e.md"),
            os.path.join(REPO_ROOT, "audits", "fase4-achados.md"),
            os.path.join(REPO_ROOT, "audits", "fase4-roadmap.md"),
            os.path.join(REPO_ROOT, "audits", "design_4_4d_connection_queue.md"),
            os.path.join(REPO_ROOT, "tests", "test_connection_queue_resilience.py"),
        ]
    )
    utf8_lines = ["=== VERIFICAÇÃO UTF-8 SEM BOM E SEM BYTES NULOS (RODADA 4.4e) ==="]
    for p in targets:
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as f:
            raw = f.read()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        has_null = b"\x00" in raw
        raw.decode("utf-8")
        rel = os.path.relpath(p, REPO_ROOT).replace("\\", "/")
        utf8_lines.append(
            f"{rel}: size={len(raw)} bytes | UTF-8=OK | BOM={has_bom} | NULL_BYTES={has_null}"
        )
        assert not has_bom, f"BOM encontrado em {rel}"
        assert not has_null, f"Null byte encontrado em {rel}"

    # 3. Verificar zero alteração em código de produto
    proc_diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "a565c4e9aaebf744515820004728c8e3d635443e",
            "--",
            "storage/",
            "core/",
            "ingestion/",
            "interface/",
            "services/",
            "main.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    prod_diff = proc_diff.stdout.strip()
    utf8_lines.append(
        f"\ngit diff --name-only a565c4e -- storage/ core/ ingestion/ interface/ services/ main.py:\n"
        f"{prod_diff if prod_diff else '(vazio — zero arquivos de produto alterados)'}"
    )
    assert prod_diff == "", f"Arquivos de produto alterados indevidamente: {prod_diff}"

    with open(os.path.join(EV_DIR, "utf8_check.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(utf8_lines) + "\n")

    # Regenerar relatorio_4_4e.md após criar scan_secrets.txt e utf8_check.txt
    subprocess.run(
        [sys.executable, "scratch/generate_relatorio_4_4e.py"],
        cwd=REPO_ROOT,
        check=True,
    )
    print("Verificação de integridade 4.4e concluída com sucesso (0 segredos, UTF-8 puro, 0 arquivos de produto tocados).")


if __name__ == "__main__":
    main()
