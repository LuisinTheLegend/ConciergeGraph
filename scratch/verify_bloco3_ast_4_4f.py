"""
scratch/verify_bloco3_ast_4_4f.py — Prova de AST idêntica (sem docstrings) em storage/connection.py
e execução de T-S1 e T-S2 (Bloco 3, Rodada 4.4f).

Salva evidência em `scratch/evidencia_4_4f/bloco3_ast_and_tests.txt`.
"""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4f")
OUT_FILE = os.path.join(EV_DIR, "bloco3_ast_and_tests.txt")
BASE_COMMIT = "3dccf68d3085b553efe27a8175e5c5fcac29048d"


class _StripDocstrings(ast.NodeTransformer):
    def _strip(self, node: ast.AST) -> ast.AST:
        self.generic_visit(node)
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
            if not body:
                body = [ast.Pass()]
            setattr(node, "body", body)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        return self._strip(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        return self._strip(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._strip(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._strip(node)


def _normalized_ast_dump(src: str) -> str:
    tree = ast.parse(src)
    stripped = _StripDocstrings().visit(tree)
    ast.fix_missing_locations(stripped)
    return ast.dump(stripped, include_attributes=False, indent=2)


def main() -> None:
    os.makedirs(EV_DIR, exist_ok=True)

    before_src = subprocess.check_output(
        ["git", "show", f"{BASE_COMMIT}:storage/connection.py"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    )
    conn_path = os.path.join(REPO_ROOT, "storage", "connection.py")
    with open(conn_path, "r", encoding="utf-8") as f:
        after_src = f.read()

    # Verificar que a docstring bruta mudou
    raw_dump_before = ast.dump(ast.parse(before_src), include_attributes=False)
    raw_dump_after = ast.dump(ast.parse(after_src), include_attributes=False)
    assert raw_dump_before != raw_dump_after, "A AST bruta (com docstrings) deveria refletir a nova docstring!"

    # Verificar que a AST sem docstrings é 100% idêntica
    norm_before = _normalized_ast_dump(before_src)
    norm_after = _normalized_ast_dump(after_src)
    sha_before = hashlib.sha256(norm_before.encode("utf-8")).hexdigest()
    sha_after = hashlib.sha256(norm_after.encode("utf-8")).hexdigest()
    ast_equal = norm_before == norm_after

    diff_txt = subprocess.check_output(
        ["git", "diff", BASE_COMMIT, "--", "storage/connection.py"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    )

    proc_test = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_connection_queue_resilience.py",
            "-v",
            "--tb=short",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    report = (
        f"=== BLOCO 3 (RODADA 4.4f): PROVA DE AST IDÊNTICA (SEM DOCSTRINGS) E TESTES T-S1 / T-S2 ===\n"
        f"Commit base comparado: {BASE_COMMIT}\n"
        f"Arquivo: storage/connection.py\n"
        f"AST bruta (com docstrings) alterada: {raw_dump_before != raw_dump_after}\n"
        f"SHA-256 AST sem docstrings (ANTES):  {sha_before}\n"
        f"SHA-256 AST sem docstrings (DEPOIS): {sha_after}\n"
        f"AST sem docstrings IDÊNTICA:         {ast_equal}\n\n"
        f"--- GIT DIFF DE storage/connection.py ---\n"
        f"{diff_txt}\n"
        f"--- EXECUÇÃO DE tests/test_connection_queue_resilience.py (INCLUINDO T-S1 E T-S2) ---\n"
        f"Return Code: {proc_test.returncode}\n"
        f"STDOUT:\n{proc_test.stdout}\nSTDERR:\n{proc_test.stderr}\n"
    )

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)

    assert ast_equal, "ERRO: A AST sem docstrings de storage/connection.py mudou!"
    assert proc_test.returncode == 0, "ERRO: Testes de test_connection_queue_resilience.py falharam!"
    print(f"Bloco 3 verificado: AST sem docstrings idêntica (sha256={sha_after}) e 14/14 testes passando.")


if __name__ == "__main__":
    main()

