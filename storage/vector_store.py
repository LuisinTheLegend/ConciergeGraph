"""
storage/vector_store.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Concrete vector backend based on ChromaDB (default) with support for:
    - Model Tiering (Flash vs Elite) for cost optimization
    - Batch Processing for massive ingestion (concierge mine)
    - Reconciliation Loop (verify_sync) to eliminate orphan vectors
    - Semantic Fallback (embedding failed → log + skip, without blocking pipeline)
    - Vector search with scores ready for Hybrid Search / Reranking

Dependency: chromadb>=0.4.0 (pip install chromadb)

Architecture:
    EmbeddingManager  → Generates embeddings with Flash/Elite tiering + fallback
    ChromaVectorStore → Implements BaseVectorBackend on ChromaDB
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("grafo-concierge.vector-store")

# ---------------------------------------------------------------------------
# Defensive import of ChromaDB — allows importing the module without the dependency
# ---------------------------------------------------------------------------

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning(
        "chromadb not installed. Install with: pip install chromadb>=0.4.0"
    )

# ---------------------------------------------------------------------------
# Defensive import of SentenceTransformers (local Flash model)
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. Tier FLASH unavailable. "
        "Install with: pip install sentence-transformers"
    )

from storage.base_backend import (
    BaseVectorBackend,
    EmbeddingTier,
    VectorSearchResult,
)

# ---------------------------------------------------------------------------
# Vector module exceptions
# ---------------------------------------------------------------------------

class EmbeddingError(Exception):
    """Error during embedding generation (model not available, invalid input)."""

class VectorStoreNotAvailableError(Exception):
    """ChromaDB is not installed or accessible."""

# ---------------------------------------------------------------------------
# EmbeddingManager — embedding generation with tiering and fallback
# ---------------------------------------------------------------------------

class EmbeddingManager:
    """Generates embeddings with support for Model Tiering.

    Tiers:
        FLASH: all-MiniLM-L6-v2 (local, 384 dims, free)
        ELITE: text-embedding-3-small (OpenAI API, 1536 dims, paid)

    Semantic Fallback:
        If generation fails, returns None + logs the error.
        The caller decides whether to skip the item or abort.

    Args:
        tier: EmbeddingTier.FLASH or EmbeddingTier.ELITE.
        openai_api_key: OpenAI API key (required for tier ELITE).
    """

    # Configurations per tier
    TIER_CONFIG: dict[EmbeddingTier, dict] = {
        EmbeddingTier.FLASH: {
            "model_name": "all-MiniLM-L6-v2",
            "dimensions": 384,
            "provider": "local",
        },
        EmbeddingTier.ELITE: {
            "model_name": "text-embedding-3-small",
            "dimensions": 1536,
            "provider": "openai",
        },
    }

    def __init__(
        self,
        tier: EmbeddingTier = EmbeddingTier.FLASH,
        openai_api_key: Optional[str] = None,
    ) -> None:
        self._tier = tier
        self._config = self.TIER_CONFIG[tier]
        self._dimensions = self._config["dimensions"]
        self._model: Any = None
        self._openai_key = openai_api_key

        logger.info(
            "EmbeddingManager initialized: tier=%s, model=%s, dims=%d",
            tier.value, self._config["model_name"], self._dimensions
        )

    @property
    def dimensions(self) -> int:
        """Number of dimensions of the active model."""
        return self._dimensions

    @property
    def tier(self) -> EmbeddingTier:
        """Current tier (FLASH or ELITE)."""
        return self._tier

    def _load_model(self) -> None:
        """Loads the embedding model (lazy loading).

        Raises:
            EmbeddingError: If the model cannot be loaded.
        """
        if self._model is not None:
            return

        import os
        if os.environ.get("GRAFO_LIGHTWEIGHT_MODE", "false").lower() == "true":
            raise EmbeddingError("Lightweight mode active - local model disabled.")

        if self._tier == EmbeddingTier.FLASH:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise EmbeddingError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            try:
                self._model = SentenceTransformer(self._config["model_name"])
                logger.info("FLASH model loaded: %s", self._config["model_name"])
            except Exception as e:
                raise EmbeddingError(f"Failed to load FLASH model: {e}") from e

        elif self._tier == EmbeddingTier.ELITE:
            if not self._openai_key:
                raise EmbeddingError(
                    "openai_api_key is required for the ELITE tier."
                )
            try:
                import openai
                self._model = openai.OpenAI(api_key=self._openai_key)
                logger.info("OpenAI client initialized for ELITE tier.")
            except ImportError:
                raise EmbeddingError(
                    "openai not installed. Install with: pip install openai>=1.0"
                )

    def embed(self, text: str) -> Optional[list[float]]:
        """Generates embedding for a text.

        Semantic Fallback: returns None in case of error (does not block the pipeline).

        Args:
            text: Text to generate embedding.

        Returns:
            List of floats (vector) or None if it failed.
        """
        try:
            self._load_model()
        except EmbeddingError as e:
            logger.error("Model unavailable for embed(): %s", e)
            return None

        try:
            if self._tier == EmbeddingTier.FLASH:
                vector = self._model.encode(text).tolist()
                return vector

            elif self._tier == EmbeddingTier.ELITE:
                response = self._model.embeddings.create(
                    model=self._config["model_name"],
                    input=text,
                )
                return response.data[0].embedding

        except Exception as e:
            # SEMANTIC FALLBACK: logs the error but DOES NOT propagate
            logger.error(
                "Semantic Fallback activated — embed failed for text (%.40s...): %s",
                text, e
            )
            return None

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generates embeddings in batch.

        Semantic Fallback applied individually: failing items
        return None in the corresponding position.

        Args:
            texts: List of texts to generate embeddings.

        Returns:
            List of vectors (or None for items that failed).
        """
        try:
            self._load_model()
        except EmbeddingError as e:
            logger.error("Model unavailable for embed_batch(): %s", e)
            return [None] * len(texts)

        results: list[Optional[list[float]]] = []

        if self._tier == EmbeddingTier.FLASH:
            try:
                vectors = self._model.encode(texts)
                return [v.tolist() for v in vectors]
            except Exception as e:
                logger.error("Semantic Fallback (batch FLASH): %s", e)
                return [None] * len(texts)

        elif self._tier == EmbeddingTier.ELITE:
            # OpenAI supports native batch
            try:
                response = self._model.embeddings.create(
                    model=self._config["model_name"],
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error("Semantic Fallback (batch ELITE): %s", e)
                return [None] * len(texts)

        return results

# ---------------------------------------------------------------------------
# ChromaVectorStore — concrete implementation of BaseVectorBackend
# ---------------------------------------------------------------------------

class ChromaVectorStore(BaseVectorBackend):
    """Vector backend based on ChromaDB.

    Implements all methods of BaseVectorBackend:
        - store_embedding / store_embeddings_batch (Batch Processing)
        - search (Top-K with scores for Hybrid Search)
        - delete / delete_batch
        - verify_sync (Reconciliation Loop)
        - health_check / count

    Args:
        persist_dir: Persistence directory of ChromaDB.
        collection_name: Name of the collection (default: 'grafo_concierge').
        embedding_manager: Instance of EmbeddingManager to generate embeddings.
    """

    # Maximum size of each batch for ChromaDB (avoids OOM in massive projects)
    BATCH_SIZE: int = 100

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = "grafo_concierge",
        embedding_manager: Optional[EmbeddingManager] = None,
    ) -> None:
        if persist_dir is None:
            persist_dir = str(Path(__file__).parent.parent.resolve() / "data" / "chroma")
        self._embedding_mgr = embedding_manager or EmbeddingManager()
        self._collection_name = collection_name

        import os
        if os.environ.get("GRAFO_LIGHTWEIGHT_MODE", "false").lower() == "true":
            logger.info("ChromaVectorStore operating in NO-OP mode (Lightweight Mode active).")
            self._available = False
            self._client = None
            self._collection = None
            return

        self._available = CHROMADB_AVAILABLE

        if not CHROMADB_AVAILABLE:
            logger.warning(
                "ChromaVectorStore operating in NO-OP mode (chromadb not installed)."
            )
            self._client = None
            self._collection = None
            return

        resolved_dir = str(Path(persist_dir).expanduser().absolute())
        Path(resolved_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=resolved_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "ChromaVectorStore initialized: dir=%s, collection=%s, tier=%s",
            resolved_dir, collection_name, self._embedding_mgr.tier.value
        )

    # ===================================================================
    # STORE — individual storage
    # ===================================================================

    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Stores an embedding with metadata in ChromaDB.

        Args:
            doc_id: Unique ID (recommended format: 'node_{node_id}').
            embedding: Embedding vector.
            metadata: Dict with 'node_id' (int) and 'project_uuid' (str).

        Raises:
            ValueError: If metadata does not contain required fields.
        """
        if not self._available:
            logger.warning("store_embedding ignored: ChromaDB unavailable.")
            return

        self._validate_metadata(metadata)

        # ChromaDB requires all metadata values to be str, int or float
        safe_meta = self._sanitize_metadata(metadata)

        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[safe_meta],
        )
        logger.debug("Embedding stored: doc_id=%s, node_id=%s", doc_id, metadata.get("node_id"))

    # ===================================================================
    # STORE BATCH — batch insertion
    # ===================================================================

    def store_embeddings_batch(self, items: list[dict]) -> int:
        """Stores multiple embeddings in controlled batches.

        Processes in chunks of BATCH_SIZE to avoid OOM.
        Items with embedding=None (Semantic Fallback) are ignored silently.

        Args:
            items: List of dicts, each containing:
                - doc_id (str)
                - embedding (list[float] or None)
                - metadata (dict with node_id and project_uuid)

        Returns:
            Number of embeddings effectively stored.
        """
        if not self._available:
            logger.warning("store_embeddings_batch ignored: ChromaDB unavailable.")
            return 0

        stored = 0
        # Filters items with valid embedding
        valid_items = [
            item for item in items
            if item.get("embedding") is not None
        ]

        skipped = len(items) - len(valid_items)
        if skipped > 0:
            logger.warning(
                "Batch store: %d items ignored (Semantic Fallback — embedding None)", skipped
            )

        # Processes in chunks
        for i in range(0, len(valid_items), self.BATCH_SIZE):
            chunk = valid_items[i:i + self.BATCH_SIZE]

            ids = []
            embeddings = []
            metadatas = []

            for item in chunk:
                try:
                    self._validate_metadata(item["metadata"])
                    ids.append(item["doc_id"])
                    embeddings.append(item["embedding"])
                    metadatas.append(self._sanitize_metadata(item["metadata"]))
                except (ValueError, KeyError) as e:
                    logger.warning("Item ignored in batch (invalid metadata): %s", e)
                    continue

            if ids:
                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                stored += len(ids)
                logger.debug("Batch chunk stored: %d embeddings", len(ids))

        logger.info("Batch store finished: %d/%d embeddings stored.", stored, len(items))
        return stored

    # ===================================================================
    # SEARCH — vector search for Hybrid Search
    # ===================================================================

    def search(
        self,
        query_embedding: list[float],
        project_uuids: list[str],
        top_k: int = 10,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Search by cosine similarity with Strict Scoping per project.

        Results are returned with normalized scores [0, 1],
        ready for the Hybrid Search / Reranking pipeline.

        Args:
            query_embedding: Vector of the query.
            project_uuids: List of UUIDs to filter (Strict Scoping).
            top_k: Maximum results.
            filters: Additional filters (e.g. {'node_type': 'FACT'}).

        Returns:
            List of VectorSearchResult sorted by score DESC.
        """
        if not self._available:
            logger.warning("search ignored: ChromaDB unavailable.")
            return []

        # Builds the ChromaDB filter
        where_filter = self._build_where_filter(project_uuids, filters)

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            logger.error("Error in vector search: %s", e)
            return []

        # ChromaDB returns distances (less = more similar for cosine)
        # We convert to score (greater = more similar): score = 1 - distance
        search_results: list[VectorSearchResult] = []

        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)

            for doc_id, distance, meta in zip(ids, distances, metadatas):
                # Cosine distance -> similarity score
                score = max(1.0 - distance, 0.0)
                search_results.append(VectorSearchResult(
                    doc_id=doc_id,
                    node_id=int(meta.get("node_id", 0)),
                    project_uuid=str(meta.get("project_uuid", "")),
                    score=round(score, 4),
                    metadata=meta,
                ))

        logger.debug("Vector search returned %d results (top_k=%d)", len(search_results), top_k)
        return search_results

    # ===================================================================
    # DELETE — individual and batch deletion
    # ===================================================================

    def delete(self, doc_id: str) -> None:
        """Removes an embedding by doc_id."""
        if not self._available:
            return

        try:
            self._collection.delete(ids=[doc_id])
            logger.debug("Embedding removed: %s", doc_id)
        except Exception as e:
            logger.warning("Failed to delete embedding %s: %s", doc_id, e)

    def delete_batch(self, doc_ids: list[str]) -> int:
        """Removes multiple embeddings in batch.

        Args:
            doc_ids: List of doc_ids to remove.

        Returns:
            Number of processed IDs for removal.
        """
        if not self._available:
            return 0

        if not doc_ids:
            return 0

        deleted = 0
        for i in range(0, len(doc_ids), self.BATCH_SIZE):
            chunk = doc_ids[i:i + self.BATCH_SIZE]
            try:
                self._collection.delete(ids=chunk)
                deleted += len(chunk)
            except Exception as e:
                logger.error("Failed to delete batch of %d embeddings: %s", len(chunk), e)

        logger.info("Batch delete finished: %d/%d removed.", deleted, len(doc_ids))
        return deleted

    # ===================================================================
    # RECONCILIATION LOOP — verify_sync
    # ===================================================================

    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Detects orphan vectors by comparing with the valid SQLite IDs.

        Paged flow (OOM protection):
            1. Gets only doc_ids from ChromaDB (without heavy metadata).
            2. Iterates in batches of BATCH_SIZE, loading metadata per slice.
            3. Compares node_id of each batch with sqlite_node_ids.
            4. Accumulates doc_ids whose node_id does NOT exist in SQLite.

        Args:
            sqlite_node_ids: Set of valid node_ids in SQLite.

        Returns:
            List of orphan doc_ids (exist in vector but not in SQLite).
        """
        if not self._available:
            return []

        orphans: list[str] = []

        try:
            # Phase 1: get only IDs (without heavy metadata in RAM)
            id_data = self._collection.get(include=[])
            all_ids = id_data.get("ids", [])

            if not all_ids:
                logger.info("Reconciliation Loop: collection empty — nothing to verify.")
                return []

            # Phase 2: iterate in batches of BATCH_SIZE, loading metadata per slice
            for offset in range(0, len(all_ids), self.BATCH_SIZE):
                batch_ids = all_ids[offset:offset + self.BATCH_SIZE]
                batch_data = self._collection.get(
                    ids=batch_ids,
                    include=["metadatas"],
                )
                batch_metas = batch_data.get("metadatas", [])
                batch_doc_ids = batch_data.get("ids", batch_ids)

                for doc_id, meta in zip(batch_doc_ids, batch_metas):
                    node_id = meta.get("node_id") if meta else None
                    if node_id is None:
                        # Metadata corrupted — consider orphan
                        orphans.append(doc_id)
                        continue

                    if int(node_id) not in sqlite_node_ids:
                        orphans.append(doc_id)

        except Exception as e:
            logger.error("Failed in Reconciliation Loop (verify_sync): %s", e)

        if orphans:
            logger.warning(
                "Reconciliation Loop: %d orphan vectors detected.", len(orphans)
            )
        else:
            logger.info("Reconciliation Loop: all vectors are synchronized.")

        return orphans

    # ===================================================================
    # HEALTH CHECK + COUNT
    # ===================================================================

    def health_check(self) -> bool:
        """Verifies if ChromaDB is operational."""
        if not self._available:
            return False

        try:
            self._client.heartbeat()
            return True
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return False

    def count(self, project_uuid: Optional[str] = None) -> int:
        """Returns the total number of stored vectors.

        Args:
            project_uuid: If provided, counts only vectors of this project.
        """
        if not self._available:
            return 0

        try:
            if project_uuid:
                result = self._collection.get(
                    where={"project_uuid": project_uuid},
                    include=[],
                )
                return len(result.get("ids", []))
            return self._collection.count()
        except Exception as e:
            logger.error("Failed to count vectors: %s", e)
            return 0

    def reset_collection(self) -> bool:
        """Destroys and recreates the physical collection of vectors (emergency repair).

        WARNING: This operation deletes ALL embeddings irreversibly.
        After reset, it will be necessary to re-ingest projects to recreate vectors.

        Returns:
            True if the operation was successful, False otherwise.
        """
        if not self._available or self._client is None:
            logger.warning("reset_collection ignored: ChromaDB unavailable.")
            return False

        try:
            old_count = self._collection.count() if self._collection else 0
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "reset_collection OK: collection '%s' destroyed and recreated "
                "(%d embeddings eliminated).",
                self._collection_name, old_count,
            )
            return True
        except Exception as e:
            logger.error("reset_collection FAILED: %s", e)
            return False

    # ===================================================================
    # AUXILIARY INTERNAL METHODS
    # ===================================================================

    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Updates the metadata of an existing vector without replacing the embedding.

        Allows JanitorService to inject community_id and other attributes
        without needing to access self._collection directly.

        Args:
            doc_id: Document identifier (e.g. 'node_42').
            metadata: Metadata dictionary to apply.
        """
        if not self._available or self._collection is None:
            logger.debug("update_metadata: ChromaDB unavailable — ignored for %s.", doc_id)
            return

        try:
            safe_meta = self._sanitize_metadata(metadata)
            self._collection.update(ids=[doc_id], metadatas=[safe_meta])
            logger.debug("Vector metadata updated: doc_id=%s", doc_id)
        except Exception as e:
            logger.error("Failed to update metadata in ChromaDB for %s: %s", doc_id, e)


    @staticmethod
    def _validate_metadata(metadata: dict) -> None:
        """Validates that metadata contains required fields."""
        if "node_id" not in metadata:
            raise ValueError("metadata must contain 'node_id' (int).")
        if "project_uuid" not in metadata:
            raise ValueError("metadata must contain 'project_uuid' (str).")

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        """Ensures that all metadata values are types accepted by ChromaDB.

        ChromaDB accepts: str, int, float, bool. Lists and dicts are converted to str.
        """
        safe = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                safe[k] = v
            elif v is None:
                safe[k] = ""
            else:
                safe[k] = str(v)
        return safe

    @staticmethod
    def _build_where_filter(
        project_uuids: list[str],
        extra_filters: Optional[dict] = None,
    ) -> Optional[dict]:
        """Builds the ChromaDB 'where' filter combining project + extra filters.

        Args:
            project_uuids: List of UUIDs for Strict Scoping.
            extra_filters: Additional filters (e.g. {'node_type': 'FACT'}).

        Returns:
            Dict in ChromaDB where format, or None if no filters.
        """
        conditions: list[dict] = []

        if project_uuids:
            if len(project_uuids) == 1:
                conditions.append({"project_uuid": project_uuids[0]})
            else:
                conditions.append({"project_uuid": {"$in": project_uuids}})

        if extra_filters:
            for key, value in extra_filters.items():
                conditions.append({key: value})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def get_all_stored_node_ids(self) -> set[int]:
        """Returns all numerical node_ids present in the Chroma collection."""
        if not self._available:
            return set()
        try:
            id_data = self._collection.get(include=[])
            ids = id_data.get("ids", [])
            node_ids = set()
            for doc_id in ids:
                if doc_id.startswith("node_"):
                    try:
                        node_ids.add(int(doc_id.split("_")[1]))
                    except (IndexError, ValueError):
                        pass
            return node_ids
        except Exception as e:
            logger.error("Error obtaining stored node_ids in Chroma: %s", e)
            return set()
