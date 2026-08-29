"""
core/parsers/__init__.py — SDD-SURVIVAL-19

Pacote de parsers multilinguagem do Grafo Concierge.

Exporta a interface base e os parsers especializados:
    - BaseASTParser      → Interface abstrata comum
    - PythonASTParser    → Parser Python via módulo 'ast' nativo
    - TSJSASTParser      → Parser TS/JS/JSX/TSX via Tree-Sitter + Regex Fallback
"""

from core.parsers.base import BaseASTParser
from core.parsers.python_parser import PythonASTParser
from core.parsers.ts_js_parser import TSJSASTParser

__all__ = [
    "BaseASTParser",
    "PythonASTParser",
    "TSJSASTParser",
]
