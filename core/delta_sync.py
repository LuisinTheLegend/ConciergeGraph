"""
core/delta_sync.py — SDD-SURVIVAL-11

Re-export module to maintain backward compatibility with
Active-SDD #11 specification (import path: core.delta_sync).

DeltaManager and DocstringStripper are implemented in core/delta_manager.py.
"""

from core.delta_manager import DeltaManager, DocstringStripper

__all__ = ["DeltaManager", "DocstringStripper"]
