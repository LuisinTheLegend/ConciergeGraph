"""
core/__init__.py — Grafo Concierge v3.8.0 (Absolute Solidity)

core/ package — Agent Brain.

Exports the central Facade (GrafoConcierge) and intelligence submodules:
    - GrafoConcierge       → Unified facade for memory operations
    - ConciergeConfig      → Centralized constants and parameters
    - ProjectIndex         → Knowledge GPS / Wing Categorization
    - HybridSearchEngine   → Hybrid Search Engine v4
"""

from core.config import ConciergeConfig
from core.project_index import ProjectIndex
from core.hybrid_search import HybridSearchEngine
from core.middleware import GrafoConcierge

__all__ = [
    "ConciergeConfig",
    "ProjectIndex",
    "HybridSearchEngine",
    "GrafoConcierge",
]
