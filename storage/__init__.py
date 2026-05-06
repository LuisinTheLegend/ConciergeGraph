"""
storage/ — Camada de Retenção (Plugável) — Grafo Concierge v3.8.0

Módulos:
    connection.py   → SerializedWriteQueue + ConnectionManager (WAL, thread-safe)
    schema.py       → DDL, CHECK constraints, FTS5 triggers, SchemaManager
    logic.py        → GraphLogic (decaimento, centralidade, recência, FTS5, CTE)
    store.py        → SqliteStore (fachada unificada SQLite)
    base_backend.py → Interface abstrata para backends vetoriais plugáveis
    vector_store.py → ChromaVectorStore + EmbeddingManager (Flash/Elite)
"""

from storage.store import SqliteStore
from storage.connection import ConnectionManager, SerializedWriteQueue
from storage.schema import SchemaManager
from storage.logic import GraphLogic
from storage.base_backend import BaseVectorBackend, EmbeddingTier, VectorSearchResult
from storage.vector_store import ChromaVectorStore, EmbeddingManager

__all__ = [
    "SqliteStore",
    "ConnectionManager",
    "SerializedWriteQueue",
    "SchemaManager",
    "GraphLogic",
    "BaseVectorBackend",
    "EmbeddingTier",
    "VectorSearchResult",
    "ChromaVectorStore",
    "EmbeddingManager",
]
