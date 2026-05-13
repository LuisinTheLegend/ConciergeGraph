"""
core/__init__.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Pacote core/ — Cérebro do Agente.

Exporta a Fachada central (GrafoConcierge) e sub-módulos de inteligência:
    - GrafoConcierge       → Fachada unificada para operações de memória
    - ConciergeConfig      → Constantes e parâmetros centralizados
    - ProjectIndex         → GPS de Conhecimento / Categorização por Alas
    - HybridSearchEngine   → Motor de Busca Híbrida v4
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
