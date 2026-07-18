"""
core/vector_backend.py — Grafo Concierge v3.8.0 (Conversational Expansion)

Concrete vector backend based on Qdrant with support for:
    - Namespace separation by scope (scope_type, scope_id)
    - Isolated collection for episodic memory (episodic_memory)
    - Strict validation of temporal payloads
    - Defensive import (Qdrant available or NO-OP)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger("grafo-concierge.qdrant-backend")

# Defensive import of QdrantClient
try:
    import qdrant_client
    from qdrant_client.http import models as qdrant_models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.error(
        "[CRITICAL] qdrant-client not found. QdrantVectorStore operating in NO-OP mode. Semantic searches will return empty!"
    )

from storage.base_backend import BaseVectorBackend, VectorSearchResult


class QdrantVectorStore(BaseVectorBackend):
    """Vector backend based on Qdrant.

    Ensures isolation between the code AST collection and the
    episodic/conversational history collection.

    The episodic_memory collection payload requires keys:
        - scope_type
        - scope_id
        - timestamp
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        location: Optional[str] = None,
        memory: bool = False,
        collection_name: str = "grafo_concierge",
        embedding_dimensions: int = 384,
    ) -> None:
        self._collection_name = collection_name
        self._dimensions = embedding_dimensions
        self._last_warn_time = 0.0

        # Saved parameters for reconnection
        self._url = url
        self._api_key = api_key
        self._location = location
        self._memory = memory

        # Dynamic connection control and backoff
        self._connected = False
        self._client: Optional[qdrant_client.QdrantClient] = None
        self._backoff = 1.0
        self._max_backoff = 60.0
        self._last_connect_attempt = 0.0

        import os
        if os.environ.get("GRAFO_LIGHTWEIGHT_MODE", "false").lower() == "true":
            logger.info("QdrantVectorStore operating in NO-OP mode (Lightweight Mode active).")
            return

        # Tries initial connection
        self._ensure_connected()

    def _ensure_connected(self) -> bool:
        """Ensures a dynamic and resilient connection to Qdrant using exponential backoff."""
        if not QDRANT_AVAILABLE:
            return False
        if self._connected and self._client:
            return True

        current_time = time.time()
        # Respects the current backoff interval to avoid frantic requests
        if current_time - self._last_connect_attempt < self._backoff:
            return False

        self._last_connect_attempt = current_time
        try:
            logger.info("Attempting to establish connection to Qdrant...")
            if self._memory:
                self._client = qdrant_client.QdrantClient(":memory:")
            elif self._location:
                self._client = qdrant_client.QdrantClient(location=self._location, api_key=self._api_key)
            else:
                self._client = qdrant_client.QdrantClient(url=self._url, api_key=self._api_key)

            # Initializes necessary collections
            self._ensure_collection(self._collection_name)
            self._ensure_collection("episodic_memory")

            self._connected = True
            self._backoff = 1.0  # reset backoff
            logger.info("Qdrant connected and collections initialized successfully.")
            return True
        except Exception as e:
            self._connected = False
            self._client = None
            logger.warning(
                "Failed to connect or initialize Qdrant collections: %s. Next attempt in %.1fs",
                e,
                self._backoff
            )
            # Exponentially increases backoff
            self._backoff = min(self._backoff * 2.0, self._max_backoff)
            return False

    def _ensure_collection(self, name: str) -> None:
        """Creates the collection if it does not exist in an idempotent way."""
        if not self._client:
            return
        try:
            exists = self._client.collection_exists(collection_name=name)
            if not exists:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self._dimensions,
                        distance=qdrant_models.Distance.COSINE
                    )
                )
                logger.info("Qdrant collection '%s' created successfully.", name)
            else:
                logger.debug("Qdrant collection '%s' already exists.", name)
        except Exception as e:
            logger.error("Failed to initialize Qdrant collection '%s': %s", name, e)
            raise

    def _log_noop_warning(self) -> None:
        """Logs a warning when operating in NO-OP mode, throttled to once every 5 seconds."""
        current_time = time.time()
        if current_time - self._last_warn_time >= 5.0:
            logger.warning("Operation ignored: Qdrant in NO-OP mode")
            self._last_warn_time = current_time

    def _validate_payload(self, metadata: dict) -> None:
        """Validates the mandatory fields depending on the target collection."""
        if self._collection_name == "episodic_memory":
            required = ["scope_type", "scope_id", "timestamp", "utility_alpha", "utility_beta"]
            for r in required:
                if r not in metadata:
                    raise ValueError(
                        f"Payload de 'episodic_memory' exige a chave '{r}' para indexação temporal."
                    )
            # Scope type must be one of the permitted scopes
            scope_type = metadata["scope_type"]
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(
                    f"scope_type inválido '{scope_type}'. Aceitos: {sorted(valid_scopes)}"
                )
        else:
            # Default code/AST collection requires node_id and project_uuid
            if "node_id" not in metadata:
                raise ValueError("metadata deve conter 'node_id' (int).")
            if "project_uuid" not in metadata:
                raise ValueError("metadata deve conter 'project_uuid' (str).")

    # ===================================================================
    # IMPLEMENTATION OF BaseVectorBackend CONTRACT
    # ===================================================================

    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Stores an embedding with metadata/payload in Qdrant (with dynamic collection routing)."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return

        self._validate_payload(metadata)

        collection = "episodic_memory" if "timestamp" in metadata else self._collection_name

        self._client.upsert(
            collection_name=collection,
            points=[
                qdrant_models.PointStruct(
                    id=doc_id if isinstance(doc_id, (int, str)) else hash(doc_id),
                    vector=embedding,
                    payload=metadata
                )
            ]
        )
        logger.debug("Embedding stored in Qdrant (collection: %s): %s", collection, doc_id)

    def store_embeddings_batch(self, items: list[dict]) -> int:
        """Stores multiple embeddings in batch in Qdrant (with multiple collections support)."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return 0
        if not items:
            return 0

        points_by_collection: dict[str, list] = {}
        for item in items:
            doc_id = item["doc_id"]
            embedding = item["embedding"]
            metadata = item["metadata"]

            if embedding is None:
                continue

            try:
                self._validate_payload(metadata)
                collection = "episodic_memory" if "timestamp" in metadata else self._collection_name
                if collection not in points_by_collection:
                    points_by_collection[collection] = []

                points_by_collection[collection].append(
                    qdrant_models.PointStruct(
                        id=doc_id if isinstance(doc_id, (int, str)) else hash(doc_id),
                        vector=embedding,
                        payload=metadata
                    )
                )
            except (ValueError, KeyError) as e:
                logger.warning("Item ignored in Qdrant batch due to invalid payload: %s", e)
                continue

        total_upserted = 0
        for collection, points in points_by_collection.items():
            if points:
                self._client.upsert(
                    collection_name=collection,
                    points=points
                )
                total_upserted += len(points)
        return total_upserted

    def search(
        self,
        query_embedding: list[float],
        project_uuids: list[str],
        top_k: int = 10,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Searches by cosine similarity in Qdrant applying filters."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return []

        # Builds the search filter in Qdrant format
        qdrant_filter = self._build_filter(project_uuids, filters)

        try:
            results = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=top_k,
            )
        except Exception as e:
            logger.error("Error in Qdrant vector search: %s", e)
            return []

        search_results: list[VectorSearchResult] = []
        for res in results:
            payload = res.payload or {}
            # For the code collection, we extract node_id and project_uuid
            node_id = int(payload.get("node_id", 0))
            project_uuid = str(payload.get("project_uuid", ""))

            search_results.append(
                VectorSearchResult(
                    doc_id=str(res.id),
                    node_id=node_id,
                    project_uuid=project_uuid,
                    score=float(res.score),
                    metadata=payload,
                )
            )
        return search_results

    def delete(self, doc_id: str) -> None:
        """Deletes a vector by ID."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return

        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[doc_id]
                )
            )
        except Exception as e:
            logger.warning("Failed to delete vector in Qdrant %s: %s", doc_id, e)

    def delete_batch(self, doc_ids: list[str]) -> int:
        """Deletes multiple vectors in batch."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return 0
        if not doc_ids:
            return 0

        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=doc_ids
                )
            )
            return len(doc_ids)
        except Exception as e:
            logger.error("Failed to delete batch in Qdrant: %s", e)
            return 0

    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Detects orphan vectors in Qdrant."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return []

        orphans: list[str] = []
        try:
            # Scroll all points using Qdrant scroll API
            offset = None
            while True:
                res, next_offset = self._client.scroll(
                    collection_name=self._collection_name,
                    limit=100,
                    with_payload=True,
                    offset=offset
                )
                for point in res:
                    payload = point.payload or {}
                    node_id = payload.get("node_id")
                    if node_id is None or int(node_id) not in sqlite_node_ids:
                        orphans.append(str(point.id))
                if not next_offset:
                    break
                offset = next_offset
        except Exception as e:
            logger.error("Failed in Qdrant verify_sync: %s", e)

        return orphans

    def health_check(self) -> bool:
        """Verifies if the Qdrant cluster is accessible."""
        if not self._ensure_connected():
            return False
        try:
            # A simple ping or collection query
            self._client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant health check failed: %s", e)
            return False

    def count(self, project_uuid: Optional[str] = None) -> int:
        """Counts the quantity of stored vectors."""
        if not self._ensure_connected():
            return 0
        try:
            if project_uuid:
                q_filter = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="project_uuid",
                            match=qdrant_models.MatchValue(value=project_uuid)
                        )
                    ]
                )
                res = self._client.count(
                    collection_name=self._collection_name,
                    count_filter=q_filter
                )
            else:
                res = self._client.count(collection_name=self._collection_name)
            return res.count
        except Exception as e:
            logger.error("Failed to count vectors in Qdrant: %s", e)
            return 0

    def _build_filter(
        self,
        project_uuids: list[str],
        extra_filters: Optional[dict] = None
    ) -> Optional[qdrant_models.Filter]:
        """Helper to convert filters to Qdrant Filter format."""
        must_conditions: list[Any] = []

        if project_uuids:
            if len(project_uuids) == 1:
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key="project_uuid",
                        match=qdrant_models.MatchValue(value=project_uuids[0])
                    )
                )
            else:
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key="project_uuid",
                        match=qdrant_models.MatchAny(any=project_uuids)
                    )
                )

        if extra_filters:
            for k, v in extra_filters.items():
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key=k,
                        match=qdrant_models.MatchValue(value=v)
                    )
                )

        if not must_conditions:
            return None
        return qdrant_models.Filter(must=must_conditions)

    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Updates metadata/payload of a point in Qdrant."""
        if not self._ensure_connected() or not self._client:
            self._log_noop_warning()
            return

        try:
            self._client.set_payload(
                collection_name=self._collection_name,
                payload=metadata,
                points=[doc_id if isinstance(doc_id, (int, str)) else hash(doc_id)]
            )
        except Exception as e:
            logger.error("Failed to update metadata in Qdrant: %s", e)

    def get_all_stored_node_ids(self) -> set[int]:
        """Returns all numeric node_ids present in the Qdrant collection."""
        if not self._ensure_connected() or not self._client:
            return set()
        node_ids = set()
        try:
            offset = None
            while True:
                res, next_offset = self._client.scroll(
                    collection_name=self._collection_name,
                    limit=100,
                    with_payload=True,
                    offset=offset
                )
                for point in res:
                    payload = point.payload or {}
                    n_id = payload.get("node_id")
                    if n_id is not None:
                        node_ids.add(int(n_id))
                if not next_offset:
                    break
                offset = next_offset
            return node_ids
        except Exception as e:
            logger.error("Error obtaining saved node_ids in Qdrant: %s", e)
            return set()
