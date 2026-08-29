"""
core/parser_factory.py — SDD-SURVIVAL-19

Fábrica de Parsers Multilinguagem do Grafo Concierge.

Rota automaticamente o parser correto com base na extensão do arquivo:
  - .py            → PythonASTParser (módulo `ast` nativo)
  - .ts/.tsx/.js/.jsx → TSJSASTParser (Tree-Sitter + Regex Fallback)
  - Outros         → None (extensão não suportada)
"""

import os
import logging
from typing import Optional

from core.parsers.base import BaseASTParser
from core.parsers.python_parser import PythonASTParser
from core.parsers.ts_js_parser import TSJSASTParser

logger = logging.getLogger(__name__)

# Extensões suportadas por cada parser
_PYTHON_EXTENSIONS = frozenset({'.py'})
_TSJS_EXTENSIONS = frozenset({'.ts', '.tsx', '.js', '.jsx'})


class ParserFactory:
    """
    Fábrica estática que resolve o parser adequado pela extensão do arquivo.

    Uso:
        parser = ParserFactory.get_parser_for_file("app/Dashboard.tsx")
        if parser:
            result = parser.parse("app/Dashboard.tsx", code_content)
    """

    # Cache de instâncias singleton por tipo de parser
    # (evita re-instanciar o Tree-Sitter a cada arquivo)
    _python_parser: Optional[PythonASTParser] = None
    _tsjs_parser: Optional[TSJSASTParser] = None

    @staticmethod
    def get_parser_for_file(file_path: str, project_root: str = "") -> Optional[BaseASTParser]:
        """
        Retorna o parser adequado para a extensão do arquivo fornecido.

        Args:
            file_path:    caminho relativo ou absoluto do arquivo.
            project_root: raiz do projeto (passada ao TSJSASTParser).

        Returns:
            Instância de BaseASTParser ou None se a extensão não for suportada.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext in _PYTHON_EXTENSIONS:
            if ParserFactory._python_parser is None:
                ParserFactory._python_parser = PythonASTParser()
            return ParserFactory._python_parser

        if ext in _TSJS_EXTENSIONS:
            if ParserFactory._tsjs_parser is None:
                ParserFactory._tsjs_parser = TSJSASTParser(project_root=project_root)
            return ParserFactory._tsjs_parser

        return None

    @staticmethod
    def supported_extensions() -> frozenset:
        """Retorna o conjunto de extensões suportadas pelo sistema de parsers."""
        return _PYTHON_EXTENSIONS | _TSJS_EXTENSIONS

    @staticmethod
    def reset():
        """
        Reseta o cache de instâncias singleton.
        Útil para testes que precisam de instâncias limpas.
        """
        ParserFactory._python_parser = None
        ParserFactory._tsjs_parser = None
