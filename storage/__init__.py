"""
storage/ - Retention Layer (Pluggable) - Grafo Concierge v3.8.0

Modules:
    connection.py   → SerializedWriteQueue + ConnectionManager (WAL, thread-safe)
    schema.py       → DDL, CHECK constraints, FTS5 triggers, SchemaManager
    logic.py        → GraphLogic (decay, centrality, recency, FTS5, CTE)
    store.py        → SqliteStore (unified SQLite facade)
    base_backend.py → Abstract interface for pluggable vector backends
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
