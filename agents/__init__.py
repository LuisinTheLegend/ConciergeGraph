"""
agents/__init__.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Pacote agents/ — Guardiões de Evolução.

Exporta os agentes de IA crítica:
    - RevisorCritico → Auditor de Evolução + Reranking de Gavetas
"""

from agents.revisor_critico import RevisorCritico

__all__ = [
    "RevisorCritico",
]
