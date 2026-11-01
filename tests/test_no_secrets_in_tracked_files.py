"""tests/test_no_secrets_in_tracked_files.py

Teste de guarda para F4-021 (Rodada 4.2h - Passo 4c):
Falha se scratch/tools/scan_secrets.py encontrar qualquer padrão de segredo
ou fragmento de chave em arquivos de scratch/ ou audits/.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_scanner():
    repo_root = Path(__file__).resolve().parent.parent
    scanner_path = repo_root / "scratch" / "tools" / "scan_secrets.py"
    spec = importlib.util.spec_from_file_location("scan_secrets", scanner_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, repo_root


def test_no_secrets_in_scratch_or_audits() -> None:
    """Garante zero achados de segredos ou fragmentos de chaves em scratch/ e audits/."""
    scanner, repo_root = _load_scanner()
    findings, scanned_count = scanner.scan_files(repo_root=repo_root, include_untracked=True)
    assert scanned_count > 0, "O scanner deveria ter varrido pelo menos 1 arquivo em scratch/ ou audits/."

    if findings:
        summary_lines = []
        for rel_path, hits in sorted(findings.items()):
            pats = sorted({pat_name for _, pat_name, _ in hits})
            lines = sorted({lineno for lineno, _, _ in hits})
            summary_lines.append(
                f"{rel_path}: {len(hits)} hit(s) on line(s) {lines[:10]} patterns={pats}"
            )
        raise AssertionError(
            f"Encontrados padrões de segredo em {len(findings)} arquivo(s):\n"
            + "\n".join(summary_lines)
        )

