"""
core/nozomio_router.py — DEPRECATED (Transition Shim).

This module has been renamed to `core.federated_knowledge_router`.
Please import from `core.federated_knowledge_router` directly.
"""

from core.federated_knowledge_router import (
    FederatedKnowledgeRouter,
    FederatedKnowledgeRouter as NozomioRouter,
    EXTERNAL_FEDERATED_MCP,
)

EXTERNAL_NOZOMIO_MCP = EXTERNAL_FEDERATED_MCP

__all__ = [
    "FederatedKnowledgeRouter",
    "NozomioRouter",
    "EXTERNAL_FEDERATED_MCP",
    "EXTERNAL_NOZOMIO_MCP",
]
