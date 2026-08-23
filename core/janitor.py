"""
core/janitor.py — SDD-SURVIVAL-12

Módulo de re-exportação para manter compatibilidade com a especificação
do Active-SDD #12 (import path: core.janitor).

O BackgroundJanitor é implementado em core/background_janitor.py.
"""

from core.background_janitor import BackgroundJanitor

__all__ = ["BackgroundJanitor"]
