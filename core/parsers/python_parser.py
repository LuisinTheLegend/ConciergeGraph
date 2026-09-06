"""
core/parsers/python_parser.py — SDD-SURVIVAL-19

Native Python AST parser using stdlib `ast` module.

Extracts classes, functions (including async), and imports (import/from) from
.py files, generating a Structural Signature Hash (SSH) compatible with
the existing DeltaManager format.
"""

import ast
import hashlib
import logging
from typing import Any, Dict, List

from core.parsers.base import BaseASTParser

logger = logging.getLogger(__name__)

# Structural signature line prefixes (consistent with delta_manager.py)
_STRUCTURAL_PREFIXES = ("def ", "class ", "import ", "from ")


class PythonASTParser(BaseASTParser):
    """
    Python (.py) source parser using native stdlib `ast` module.

    Extraction strategy:
      - Classes:   ast.ClassDef
      - Functions: ast.FunctionDef + ast.AsyncFunctionDef
      - Imports:   ast.Import + ast.ImportFrom
      - SSH:       SHA-256 of lines matching structural prefixes
    """

    def parse(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Parses a Python file and returns classes, functions, imports,
        and Structural Signature Hash (SSH).
        """
        classes: List[str] = []
        functions: List[str] = []
        imports: List[str] = []

        try:
            tree = ast.parse(code_content)
        except SyntaxError:
            logger.warning(
                "[PYTHON-PARSER] SyntaxError parsing %s — returning empty extraction.",
                file_path,
            )
            return {
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "structural_signature": "",
            }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # SSH: structural signature lines (compatible with DeltaManager)
        structural_lines = [
            stripped
            for line in code_content.splitlines()
            if (stripped := line.strip()).startswith(_STRUCTURAL_PREFIXES)
        ]

        if structural_lines:
            signature = "\n".join(structural_lines)
            structural_signature = hashlib.sha256(
                signature.encode("utf-8")
            ).hexdigest()
        else:
            structural_signature = ""

        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "structural_signature": structural_signature,
        }
