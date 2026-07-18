"""
storage/base_backend.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Abstract interface for pluggable vector backends.

Any vector backend (ChromaDB, Qdrant, Pinecone) MUST implement
this interface to be compatible with the Concierge Core.

Contracts:
    - store_embedding: Stores a vector + metadata. Mandatory metadata: node_id, project_uuid.
    - store_embeddings_batch: Batch insertion for massive ingestion (concierge mine).
    - search: Vector similarity search with project pre-filtering.
    - delete: Removes a vector by doc_id.
    - delete_batch: Removes multiple vectors.
    - verify_sync: Reconciliation Loop — detects orphan vectors.
    - health_check: Checks if the backend is operational.
    - count: Returns the total number of stored vectors (with optional filter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Model Tiering — controls cost vs quality of embeddings
# ---------------------------------------------------------------------------

class EmbeddingTier(str, Enum):
    """Embedding model tier for cost optimization.

    FLASH: Lightweight, fast and free model (all-MiniLM-L6-v2, 384 dims).
           Ideal for massive ingestion and local projects.

    ELITE: Premium model with higher semantic accuracy
           (text-embedding-3-small, 1536 dims).
           Ideal for critical production searches.
    """
    FLASH = "flash"
    ELITE = "elite"


# ---------------------------------------------------------------------------
# Standardized vector search result
# ---------------------------------------------------------------------------

class VectorSearchResult:
    """Individual result of a vector search.

    Attributes:
        doc_id: Document identifier in the vector backend.
        node_id: ID of the corresponding node in SQLite.
        project_uuid: UUID of the project to which the node belongs.
        score: Cosine similarity score [0.0, 1.0].
        metadata: Additional metadata stored along with the vector.
    """

    __slots__ = ("doc_id", "node_id", "project_uuid", "score", "metadata")

    def __init__(
        self,
        doc_id: str,
        node_id: int,
        project_uuid: str,
        score: float,
        metadata: Optional[dict] = None,
    ) -> None:
        self.doc_id = doc_id
        self.node_id = node_id
        self.project_uuid = project_uuid
        self.score = score
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Converts to a dict compatible with the Hybrid Search pipeline."""
        return {
            "doc_id": self.doc_id,
            "node_id": self.node_id,
            "project_uuid": self.project_uuid,
            "vector_score": self.score,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# BaseVectorBackend — Abstract interface
# ---------------------------------------------------------------------------

class BaseVectorBackend(ABC):
    """Abstract interface for pluggable vector backends.

    Concrete implementations: ChromaBackend, QdrantBackend, PineconeBackend.

    All storage methods MUST include in the metadata:
        - node_id (int): Corresponding ID in the SQLite nodes table.
        - project_uuid (str): Project UUID for Strict Scoping.
    """

    @abstractmethod
    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Stores an embedding with metadata.

        Args:
            doc_id: Unique document identifier (format: 'node_{node_id}').
            embedding: Embedding vector (384 or 1536 dimensions).
            metadata: Dict containing mandatory 'node_id' and 'project_uuid'.

        Raises:
            ValueError: If metadata does not contain mandatory fields.
        """
        ...

    @abstractmethod
    def store_embeddings_batch(
        self,
        items: list[dict],
    ) -> int:
        """Stores multiple embeddings in batch.

        Each item in the list MUST contain:
            - doc_id (str)
            - embedding (list[float])
            - metadata (dict with node_id and project_uuid)

        Args:
            items: List of dicts with doc_id, embedding and metadata.

        Returns:
            Number of successfully stored embeddings.

        Raises:
            ValueError: If any item does not contain mandatory fields.
        """
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        project_uuids: list[str],
        top_k: int = 10,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Similarity search with project pre-filtering.

        Args:
            query_embedding: Query vector (same dimension as stored vectors).
            project_uuids: List of UUIDs for Strict Scoping.
            top_k: Maximum number of results.
            filters: Additional filters (e.g. {'node_type': 'FACT'}).

        Returns:
            List of VectorSearchResult sorted by score DESC.
        """
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Removes an embedding by doc_id.

        Args:
            doc_id: Identifier of the document to remove.
        """
        ...

    @abstractmethod
    def delete_batch(self, doc_ids: list[str]) -> int:
        """Removes multiple embeddings.

        Args:
            doc_ids: List of identifiers to remove.

        Returns:
            Number of successfully removed embeddings.
        """
        ...

    @abstractmethod
    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Reconciliation Loop — detects orphan vectors in the backend.

        Compares existing IDs in the vector backend with valid IDs
        from SQLite. Returns doc_ids that exist in vector database but NOT in SQLite.

        Args:
            sqlite_node_ids: Set of valid node_ids in SQLite.

        Returns:
            List of orphan doc_ids that should be deleted.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if the backend is operational.

        Returns:
            True if the backend is accessible and responding.
        """
        ...

    @abstractmethod
    def count(self, project_uuid: Optional[str] = None) -> int:
        """Returns the total number of stored vectors.

        Args:
            project_uuid: If provided, counts only vectors from this project.

        Returns:
            Vector count.
        """
        ...

    @abstractmethod
    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Updates the metadata of an existing vector without replacing the embedding.

        Allows the Janitor to inject community_id and other attributes without
        needing to access _collection directly.

        Args:
            doc_id: Document identifier (e.g. 'node_42').
            metadata: Metadata dictionary to apply (merge or replace).
        """
        ...

    @abstractmethod
    def get_all_stored_node_ids(self) -> set[int]:
        """Returns the set of all numeric node_ids present in the vector backend.

        Returns:
            Set containing all stored numeric node_ids.
        """
        ...
