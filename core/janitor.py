"""
core/janitor.py — SDD-SURVIVAL-12

Re-export module to maintain backward compatibility with
Active-SDD #12 specification (import path: core.janitor).

BackgroundJanitor is implemented in core/background_janitor.py.
"""

from core.background_janitor import BackgroundJanitor

__all__ = ["BackgroundJanitor"]
