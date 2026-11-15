"""
core/parser_factory.py — SDD-SURVIVAL-19

Polyglot Parser Factory for Concierge Graph.

Automatically routes to the appropriate parser based on file extension:
  - .py               -> PythonASTParser (native `ast` module)
  - .ts/.tsx/.js/.jsx -> TSJSASTParser (Tree-Sitter + Regex Fallback)
  - Others            -> None (unsupported extension)
"""

import logging
import os
from typing import Optional

from core.parsers.base import BaseASTParser
from core.parsers.python_parser import PythonASTParser
from core.parsers.ts_js_parser import TSJSASTParser

logger = logging.getLogger(__name__)

# Supported extensions by each parser engine
_PYTHON_EXTENSIONS = frozenset({'.py'})
_TSJS_EXTENSIONS = frozenset({'.ts', '.tsx', '.js', '.jsx'})


class ParserFactory:
    """
    Static factory that resolves the suitable parser based on file extension.

    Usage:
        parser = ParserFactory.get_parser_for_file("app/Dashboard.tsx")
        if parser:
            result = parser.parse("app/Dashboard.tsx", code_content)
    """

    # Singleton instance cache per parser type
    # (avoids re-initializing Tree-Sitter grammar on each file)
    _python_parser: Optional[PythonASTParser] = None
    _tsjs_parser: Optional[TSJSASTParser] = None

    @staticmethod
    def get_parser_for_file(file_path: str, project_root: str = "") -> Optional[BaseASTParser]:
        """
        Returns the appropriate parser for the given file extension.

        Args:
            file_path:    Relative or absolute path of file.
            project_root: Root directory of project (passed to TSJSASTParser).

        Returns:
            BaseASTParser instance or None if extension is not supported.
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
        """Returns the set of all supported file extensions."""
        return _PYTHON_EXTENSIONS | _TSJS_EXTENSIONS

    @staticmethod
    def reset():
        """
        Resets cached singleton instances.
        Useful for test fixtures requiring clean state.
        """
        ParserFactory._python_parser = None
        ParserFactory._tsjs_parser = None
