"""
core/parsers/python_parser.py — SDD-SURVIVAL-19

Parser Python nativo utilizando o módulo `ast` da stdlib.

Extrai classes, funções (incluindo async) e imports (import/from) de
arquivos .py, gerando a assinatura estrutural (SSH) compatível com o
formato do DeltaManager existente.
"""

import ast
import hashlib
import logging
from typing import Dict, Any, List

from core.parsers.base import BaseASTParser

logger = logging.getLogger(__name__)

# Prefixos de assinatura estrutural (consistente com delta_manager.py)
_STRUCTURAL_PREFIXES = ("def ", "class ", "import ", "from ")


class PythonASTParser(BaseASTParser):
    """
    Parser de arquivos Python (.py) via módulo `ast` nativo.

    Estratégia de extração:
      - Classes:   ast.ClassDef
      - Funções:   ast.FunctionDef + ast.AsyncFunctionDef
      - Imports:   ast.Import + ast.ImportFrom
      - SSH:       SHA-256 das linhas com prefixos estruturais
    """

    def parse(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Analisa um arquivo Python e retorna classes, funções, imports
        e a assinatura estrutural hash (SSH).
        """
        classes: List[str] = []
        functions: List[str] = []
        imports: List[str] = []

        try:
            tree = ast.parse(code_content)
        except SyntaxError:
            logger.warning(
                "[PYTHON-PARSER] SyntaxError ao parsear %s — retornando extração vazia.",
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

        # SSH: linhas de assinatura estrutural (compatível com DeltaManager)
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
