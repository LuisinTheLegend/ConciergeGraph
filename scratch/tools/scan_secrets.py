"""scratch/tools/scan_secrets.py

Varre arquivos em scratch/ e audits/ (.txt, .md, .json, .log) listados via
git ls-files procurando padrões de chaves de API ou fragmentos mascarados.

Não imprime o conteúdo do segredo encontrado na saída (apenas arquivo, linha
e nome do padrão), evitando que o próprio relatório de varredura contenha
fragmentos de chave.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".log"}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AQ_KEY_FRAGMENT", re.compile(r"AQ\.[\w*-]{4,}")),
    ("AIZA_KEY_FRAGMENT", re.compile(r"AIza[\w-]{10,}")),
    ("SK_KEY_FRAGMENT", re.compile(r"sk-[\w*-]{6,}")),
    ("INCORRECT_API_KEY_MSG", re.compile(r"Incorrect API key provided")),
    ("MASKED_KEY_SUFFIX", re.compile(r"\*{6,}\w{0,8}\.")),
]


def list_target_files(
    repo_root: Path = REPO_ROOT,
    include_untracked: bool = True,
) -> list[Path]:
    """Lista arquivos .txt, .md, .json, .log em scratch/ e audits/ via git ls-files."""
    cmd = ["git", "ls-files", "--cached"]
    if include_untracked:
        cmd.extend(["--others", "--exclude-standard"])
    cmd.extend(["--", "scratch/", "audits/"])

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
         encoding="utf-8",
        errors="replace",
        check=True,
    )
    files: list[Path] = []
    seen: set[str] = set()
    for raw_line in proc.stdout.splitlines():
        rel = raw_line.strip()
        if not rel or rel in seen:
            continue
        seen.add(rel)
        p = repo_root / rel
        if p.suffix.lower() in ALLOWED_EXTENSIONS and p.is_file():
            files.append(p)
    return sorted(files)


def scan_files(
    repo_root: Path = REPO_ROOT,
    include_untracked: bool = True,
) -> tuple[dict[str, list[tuple[int, str, int]]], int]:
    """Varre os arquivos alvo e retorna (achados_por_arquivo, total_arquivos_varridos)."""
    target_files = list_target_files(repo_root=repo_root, include_untracked=include_untracked)
    findings: dict[str, list[tuple[int, str, int]]] = {}

    for file_path in target_files:
        rel_path = file_path.relative_to(repo_root).as_posix()
        try:
            raw_bytes = file_path.read_bytes()
        except OSError:
            continue

        # Decodifica preservando linhas
        text = None
        for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw_bytes.decode("utf-8", errors="replace")

        file_hits: list[tuple[int, str, int]] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat_name, regex in SECRET_PATTERNS:
                matches = regex.findall(line)
                if matches:
                    file_hits.append((lineno, pat_name, len(matches)))

        if file_hits:
            findings[rel_path] = file_hits

    return findings, len(target_files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scanner de segredos em scratch/ e audits/")
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Varre apenas arquivos já rastreados no índice do git (--cached).",
    )
    args = parser.parse_args(argv)

    findings, scanned_count = scan_files(
        repo_root=REPO_ROOT,
        include_untracked=not args.tracked_only,
    )

    total_hits = sum(sum(c for _, _, c in hits) for hits in findings.values())
    print(f"scanned_files={scanned_count}")
    print(f"files_with_findings={len(findings)}")
    print(f"total_pattern_hits={total_hits}")

    for rel_path, hits in sorted(findings.items()):
        by_pat: dict[str, int] = {}
        lines_set: list[int] = []
        for lineno, pat_name, count in hits:
            by_pat[pat_name] = by_pat.get(pat_name, 0) + count
            if lineno not in lines_set:
                lines_set.append(lineno)
        pat_summary = ", ".join(f"{k}:{v}" for k, v in sorted(by_pat.items()))
        line_preview = ",".join(str(x) for x in lines_set[:10])
        if len(lines_set) > 10:
            line_preview += f",...(+{len(lines_set) - 10} lines)"
        print(f"FINDING: {rel_path} | lines={line_preview} | patterns=[{pat_summary}]")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
