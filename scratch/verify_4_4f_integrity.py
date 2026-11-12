"""
scratch/verify_4_4f_integrity.py — Verifica scan_secrets.py (Regra 13), UTF-8 sem BOM/nulos,
ausência de diretórios residuais e escopo estrito de arquivos de produto (Rodada 4.4f).
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4f")
AUDITS_DIR = os.path.join(REPO_ROOT, "audits")


def main() -> None:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    # 1. Run scan_secrets.py
    p_sec = subprocess.run(
        [sys.executable, "scratch/tools/scan_secrets.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    sec_out = f"ReturnCode: {p_sec.returncode}\nSTDOUT:\n{p_sec.stdout}\nSTDERR:\n{p_sec.stderr}\n"
    with open(os.path.join(EVIDENCE_DIR, "scan_secrets.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sec_out)
    if p_sec.returncode != 0:
        raise RuntimeError(f"scan_secrets.py falhou:\n{sec_out}")

    # 2. Check residual directories
    res_stress = os.path.exists(os.path.join(REPO_ROOT, "tests", "_stress_test_workspace"))
    res_chroma = os.path.exists(os.path.join(REPO_ROOT, "tmp_chroma_test"))
    if res_stress or res_chroma:
        raise RuntimeError(f"Diretório residual encontrado: stress={res_stress}, chroma={res_chroma}")

    # 3. Check product scope diff (excluding storage/connection.py docstring which is checked by verify_bloco3_ast_4_4f.py)
    p_diff = subprocess.run(
        ["git", "diff", "3dccf68", "--", "core/", "ingestion/", "interface/", "services/", "main.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if p_diff.stdout.strip():
        raise RuntimeError(f"Alteração não autorizada em código de produto:\n{p_diff.stdout}")

    # 4. Check UTF-8 without BOM and without null bytes
    checked_files = []
    for folder in (EVIDENCE_DIR, AUDITS_DIR):
        for root, _, files in os.walk(folder):
            for name in sorted(files):
                if name.endswith((".txt", ".md")):
                    path = os.path.join(root, name)
                    with open(path, "rb") as bf:
                        raw = bf.read()
                    has_bom = raw.startswith(b"\xef\xbb\xbf")
                    has_null = b"\x00" in raw
                    try:
                        raw.decode("utf-8")
                        valid_utf8 = True
                    except UnicodeDecodeError:
                        valid_utf8 = False
                    rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
                    checked_files.append((rel, len(raw), valid_utf8, has_bom, has_null))
                    if not valid_utf8 or has_bom or has_null:
                        raise RuntimeError(f"Arquivo inválido {rel}: utf8={valid_utf8}, bom={has_bom}, null={has_null}")

    lines = ["=== VERIFICAÇÃO UTF-8 SEM BOM E SEM BYTES NULOS (RODADA 4.4f) ==="]
    for rel, size, valid_utf8, has_bom, has_null in checked_files:
        lines.append(f"{rel}: bytes={size}, utf8={valid_utf8}, bom={has_bom}, null={has_null}")
    lines.append(f"Total verificados: {len(checked_files)} arquivos — TODOS OK.")

    with open(os.path.join(EVIDENCE_DIR, "utf8_check.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Integridade verificada com sucesso ({len(checked_files)} arquivos UTF-8 sem BOM/nulos; 0 segredos).")


if __name__ == "__main__":
    main()

