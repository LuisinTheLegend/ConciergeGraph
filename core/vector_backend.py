"""
core/vector_backend.py — Grafo Concierge v3.8.0 (Conversational Expansion)

Backend vetorial concreto baseado no Qdrant com suporte a:
    - Separação de namespaces por escopo (scope_type, scope_id)
    - Coleção isolada de memória episódica (episodic_memory)
    - Validação rígida de payloads temporais
    - Importação defensiva (Qdrant disponível ou NO-OP)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger("grafo-concierge.qdrant-backend")

# Import defensivo do QdrantClient
try:
    import qdrant_client
    from qdrant_client.http import models as qdrant_models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.error(
        "[CRITICAL] qdrant-client não encontrado. QdrantVectorStore operando em modo NO-OP. Buscas semânticas retornarão vazias!"
    )

from storage.base_backend import BaseVectorBackend, VectorSearchResult


class QdrantVectorStore(BaseVectorBackend):
    """Backend vetorial baseado no Qdrant.

    Garante o isolamento entre a coleção de AST de código e a coleção de
    histórico episódico/conversacional.

    O payload da coleção episodic_memory exige as chaves:
        - scope_type
        - scope_id
        - timestamp
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        location: Optional[str] = None,
        memory: bool = False,
        collection_name: str = "grafo_concierge",
        embedding_dimensions: int = 384,
    ) -> None:
        self._collection_name = collection_name
        self._dimensions = embedding_dimensions
        self._last_warn_time = 0.0

        # Parâmetros guardados para reconexão
        self._url = url
        self._location = location
        self._memory = memory

        # Controle dinâmico de conexão e backoff
        self._connected = False
        self._client: Optional[qdrant_client.QdrantClient] = None
        self._backoff = 1.0
        self._max_backoff = 60.0
        self._last_connect_attempt = 0.0

        # Tenta a conexão inicial
        self._ensure_connected()

    def _ensure_connected(self) -> bool:
        """Garante a conexão dinâmica e resiliente com o Qdrant usando exponential backoff."""
        if not QDRANT_AVAILABLE:
            return False
        if self._connected and self._client:
            return True

        current_time = time.time()
        # Respeita o intervalo do backoff atual para evitar requisições frenéticas
        if current_time - self._last_connect_attempt < self._backoff:
            return False

        self._last_connect_attempt = current_time
        try:
            logger.info("Tentando estabelecer conexão com o Qdrant...")
            if self._memory:
                self._client = qdrant_client.QdrantClient(":memory:")
            elif self._location:
                self._client = qdrant_client.QdrantClient(location=self._location)
            else:
                self._client = qdrant_client.QdrantClient(url=self._url)

            # Inicializa as coleções necessárias
            self._ensure_collection(self._collection_name)
            self._ensure_collection("episodic_memory")

            self._connected = True
            self._backoff = 1.0  # reset backoff
            logger.info("Qdrant conectado e coleções inicializadas com sucesso.")
            return True
        except Exception as e:
            self._connected = False
            self._client = None
            logger.warning(
                "Falha ao conectar ou inicializar coleções do Qdrant: %s. Próxima tentativa em %.1fs",
                e,
                self._backoff
            )
            # Aumenta exponencialmente o backoff
            self._backoff = min(self._backoff * 2.0, self._max_backoff)
            return False

    def _ensure_collection(self, name: str) -> None:
        """Cria a coleção se ela não existir de forma idempotente."""
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
                logger.info("Coleção Qdrant '%s' criada com sucesso.", name)
            else:
                logger.debug("Coleção Qdrant '%s' já existe.", name)
        except Exception as e:
            logger.error("Falha ao inicializar coleção Qdrant '%s': %s", name, e)
            raise

    def _log_noop_warning(self) -> None:
        """Logs a warning when operating in NO-OP mode, throttled to once every 5 seconds."""
        current_time = time.time()
        if current_time - self._last_warn_time >= 5.0:
            logger.warning("Operação ignorada: Qdrant em modo NO-OP")
            self._last_warn_time = current_time

    def _validate_payload(self, metadata: dict) -> None:
        """Valida os campos obrigatórios dependendo da coleção alvo."""
        if self._collection_name == "episodic_memory":
            required = ["scope_type", "scope_id", "timestamp", "utility_alpha", "utility_beta"]
            for r in required:
                if r not in metadata:
                    raise ValueError(
                        f"Payload de 'episodic_memory' exige a chave '{r}' para indexação temporal."
                    )
            # O escopo deve ser um dos permitidos
            scope_type = metadata["scope_type"]
            valid_scopes = {"user", "session", "agent", "org"}
            if scope_type not in valid_scopes:
                raise ValueError(
                    f"scope_type inválido '{scope_type}'. Aceitos: {sorted(valid_scopes)}"
                )
        else:
            # Coleção padrão de código/AST exige node_id e project_uuid
            if "node_id" not in metadata:
                raise ValueError("metadata deve conter 'node_id' (int).")
            if "project_uuid" not in metadata:
                raise ValueError("metadata deve conter 'project_uuid' (str).")

    # ===================================================================
    # IMPLEMENTAÇÃO DO BaseVectorBackend CONTRACT
    # ===================================================================

    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Armazena um embedding com metadados/payload no Qdrant (com roteamento dinâmico de coleção)."""
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
        logger.debug("Embedding armazenado no Qdrant (coleção: %s): %s", collection, doc_id)

    def store_embeddings_batch(self, items: list[dict]) -> int:
        """Armazena múltiplos embeddings em lote no Qdrant (com suporte a múltiplas coleções)."""
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
                logger.warning("Item ignorado no lote Qdrant devido a payload inválido: %s", e)
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
        """Busca por similaridade coseno no Qdrant aplicando filtros."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return []

        # Constrói o filtro de busca no formato Qdrant
        qdrant_filter = self._build_filter(project_uuids, filters)

        try:
            results = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=top_k,
            )
        except Exception as e:
            logger.error("Erro na busca vetorial no Qdrant: %s", e)
            return []

        search_results: list[VectorSearchResult] = []
        for res in results:
            payload = res.payload or {}
            # Para a coleção de código, extraímos node_id e project_uuid
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
        """Deleta um vetor pelo ID."""
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
            logger.warning("Falha ao deletar vetor no Qdrant %s: %s", doc_id, e)

    def delete_batch(self, doc_ids: list[str]) -> int:
        """Deleta múltiplos vetores em lote."""
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
            logger.error("Falha ao deletar lote no Qdrant: %s", e)
            return 0

    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Detecta vetores órfãos no Qdrant."""
        if not self._ensure_connected():
            self._log_noop_warning()
            return []

        orphans: list[str] = []
        try:
            # Rola todos os pontos usando scroll API do Qdrant
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
            logger.error("Falha no verify_sync do Qdrant: %s", e)

        return orphans

    def health_check(self) -> bool:
        """Verifica se o cluster Qdrant está acessível."""
        if not self._ensure_connected():
            return False
        try:
            # Um simples ping ou consulta de coleções
            self._client.get_collections()
            return True
        except Exception as e:
            logger.error("Qdrant health check falhou: %s", e)
            return False

    def count(self, project_uuid: Optional[str] = None) -> int:
        """Conta a quantidade de vetores armazenados."""
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
            logger.error("Falha ao contar vetores no Qdrant: %s", e)
            return 0

    def _build_filter(
        self,
        project_uuids: list[str],
        extra_filters: Optional[dict] = None
    ) -> Optional[qdrant_models.Filter]:
        """Auxiliar para converter filtros em formato Qdrant Filter."""
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
        """Atualiza metadados/payload de um ponto no Qdrant."""
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
            logger.error("Falha ao atualizar metadados no Qdrant: %s", e)
