"""
core/parsers/base.py — SDD-SURVIVAL-19

Common abstract interface for all Concierge Graph language parsers.

Defines the contract that each specialized parser (Python, TS/JS, etc.)
must implement to integrate with DeltaManager and BackgroundJanitor.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseASTParser(ABC):
    """
    Base interface for language parsers.

    Each concrete implementation must be capable of:
      1. Extracting classes, functions, and imports from source code.
      2. Generating a deterministic Structural Signature Hash (SSH) that ignores
         cosmetic and internal body logic modifications.
      3. Resolving relative and aliased import paths to normalized monorepo paths.
    """

    @abstractmethod
    def parse(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Parses source code content and returns a dictionary with:
          - "classes": List[str]              -> class names discovered
          - "functions": List[str]            -> function names discovered
          - "imports": List[str]              -> resolved import paths
          - "structural_signature": str       -> deterministic architectural signature

        Args:
            file_path: Relative path of file within workspace.
            code_content: Complete text content of source file.

        Returns:
            Dict containing the keys specified above.
        """
        ...
