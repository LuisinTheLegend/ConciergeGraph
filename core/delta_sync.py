"""
core/delta_sync.py — SDD-SURVIVAL-11

Módulo de re-exportação para manter compatibilidade com a especificação
do Active-SDD #11 (import path: core.delta_sync).

O DeltaManager e o DocstringStripper são implementados em core/delta_manager.py.
"""

from core.delta_manager import DeltaManager, DocstringStripper

__all__ = ["DeltaManager", "DocstringStripper"]
