import ast
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


class DocstringStripper(ast.NodeTransformer):
    def _strip_docstring(self, node):
        self.generic_visit(node)
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:] or [ast.Pass()]
        return node

    def visit_Module(self, node):
        return self._strip_docstring(node)

    def visit_FunctionDef(self, node):
        return self._strip_docstring(node)

    def visit_AsyncFunctionDef(self, node):
        return self._strip_docstring(node)

    def visit_ClassDef(self, node):
        return self._strip_docstring(node)


def dump_without_docstrings(source: str) -> str:
    tree = ast.parse(source)
    tree = DocstringStripper().visit(tree)
    return ast.dump(tree, include_attributes=False, indent=2)


def main():
    head_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
    ).strip()
    old_src = subprocess.check_output(
        ["git", "show", "21610d8:main.py"],
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
    )
    new_src = subprocess.check_output(
        ["git", "show", f"{head_hash}:main.py"],
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
    )

    old_dump = dump_without_docstrings(old_src)
    new_dump = dump_without_docstrings(new_src)

    diff_out = subprocess.check_output(
        ["git", "diff", "--no-color", "21610d8", head_hash, "--", "main.py"],
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
    )

    lines = []
    lines.append("=== PROVA DE AST IDENTICO EM main.py (ITEM 2) ===")
    lines.append(f"Comparacao: ast.dump(include_attributes=False) sem docstrings entre 21610d8:main.py e {head_hash}:main.py")
    if old_dump == new_dump:
        lines.append("Resultado: AST IDÊNTICO (zero linhas de código executável alteradas)")
        lines.append(f"Tamanho do ast.dump (caracteres): {len(new_dump)}")
    else:
        lines.append("Resultado: AST DIFERENTE")
    lines.append("")
    lines.append(f"=== GIT DIFF LITERAL DE main.py (21610d8..{head_hash}) ===")
    lines.append(diff_out.strip())

    out_path = HERE / "item2_ast_proof.txt"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_path.read_text(encoding="utf-8"), flush=True)


if __name__ == "__main__":
    main()
