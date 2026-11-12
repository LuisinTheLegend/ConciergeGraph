"""
scratch/verify_4_4g_integrity.py — Verifica scan_secrets.py (Regra 13), UTF-8 sem BOM/nulos,
ausência de alterações em código de produto e ausência de diretórios residuais (Rodada 4.4g).
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
AUDITS_DIR = os.path.join(REPO_ROOT, "audits")
BASE_SHA = "26a43e2"


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
    residual_root = [
        d for d in os.listdir(REPO_ROOT)
        if d.startswith("grafo_stress_") and os.path.exists(os.path.join(REPO_ROOT, d))
    ]
    if res_stress or res_chroma or residual_root:
        raise RuntimeError(
            f"Diretório residual encontrado: stress={res_stress}, chroma={res_chroma}, root={residual_root}"
        )

    # 3. Check product scope diff (ZERO product changes allowed in 4.4g)
    p_diff = subprocess.run(
        [
            "git",
            "diff",
            BASE_SHA,
            "--",
            "core/",
            "storage/",
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
    if p_diff.returncode != 0:
        raise RuntimeError(f"Falha ao executar git diff: {p_diff.stderr}")
    if p_diff.stdout.strip():
        raise RuntimeError(f"Alteração não autorizada em código de produto:\n{p_diff.stdout}")

    # 4. Check UTF-8 without BOM and without null bytes
    checked_files: list[tuple[str, int, bool, bool, bool]] = []
    for folder in (EVIDENCE_DIR, AUDITS_DIR):
        for root, _, files in os.walk(folder):
            for name in sorted(files):
                if name.endswith((".txt", ".md", ".json", ".log")):
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
                        raise RuntimeError(
                            f"Arquivo inválido {rel}: utf8={valid_utf8}, bom={has_bom}, null={has_null}"
                        )

    lines = [
        "=== VERIFICAÇÃO DE INTEGRIDADE, UTF-8 SEM BOM/NULOS E ZERO PRODUTO (RODADA 4.4g) ===",
        f"Diff de código de produto vs {BASE_SHA} (core/ storage/ ingestion/ interface/ services/ main.py): VAZIO (OK)",
        f"Diretórios residuais (_stress_test_workspace, tmp_chroma_test, grafo_stress_*): NENHUM (OK)",
    ]
    for rel, size, valid_utf8, has_bom, has_null in checked_files:
        lines.append(f"{rel}: bytes={size}, utf8={valid_utf8}, bom={has_bom}, null={has_null}")
    lines.append(f"Total verificados: {len(checked_files)} arquivos — TODOS OK.")

    utf8_path = os.path.join(EVIDENCE_DIR, "utf8_check.txt")
    with open(utf8_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    # Verify utf8_check.txt itself
    raw_self = open(utf8_path, "rb").read()
    assert not raw_self.startswith(b"\xef\xbb\xbf") and b"\x00" not in raw_self
    raw_self.decode("utf-8")

    print(
        f"Integridade verificada com sucesso ({len(checked_files)} arquivos UTF-8 sem BOM/nulos; "
        "0 alterações em produto; 0 segredos)."
    )


if __name__ == "__main__":
    main()

