"""
storage/vector_store.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Backend vetorial concreto baseado em ChromaDB (padrão) com suporte a:
    - Model Tiering (Flash vs Elite) para otimização de custo
    - Batch Processing para ingestão massiva (concierge mine)
    - Reconciliation Loop (verify_sync) para eliminar vetores órfãos
    - Semantic Fallback (embedding falhou → log + skip, sem travar pipeline)
    - Busca vetorial com scores prontos para Hybrid Search / Reranking

Dependência: chromadb>=0.4.0 (pip install chromadb)

Arquitetura:
    EmbeddingManager  → Gera embeddings com tiering Flash/Elite + fallback
    ChromaVectorStore → Implementa BaseVectorBackend sobre ChromaDB
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("grafo-concierge.vector-store")

# ---------------------------------------------------------------------------
# Import defensivo do ChromaDB — permite importar o módulo sem a dependência
# ---------------------------------------------------------------------------

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning(
        "chromadb não instalado. Instale com: pip install chromadb>=0.4.0"
    )

# ---------------------------------------------------------------------------
# Import defensivo do SentenceTransformers (modelo Flash local)
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers não instalado. Tier FLASH indisponível. "
        "Instale com: pip install sentence-transformers"
    )

from storage.base_backend import (
    BaseVectorBackend,
    EmbeddingTier,
    VectorSearchResult,
)

# ---------------------------------------------------------------------------
# Exceções do módulo vetorial
# ---------------------------------------------------------------------------

class EmbeddingError(Exception):
    """Erro durante a geração de embedding (modelo não disponível, input inválido)."""

class VectorStoreNotAvailableError(Exception):
    """ChromaDB não está instalado ou acessível."""

# ---------------------------------------------------------------------------
# EmbeddingManager — geração de embeddings com tiering e fallback
# ---------------------------------------------------------------------------

class EmbeddingManager:
    """Gera embeddings com suporte a Model Tiering.

    Tiers:
        FLASH: all-MiniLM-L6-v2 (local, 384 dims, gratuito)
        ELITE: text-embedding-3-small (OpenAI API, 1536 dims, pago)

    Semantic Fallback:
        Se a geração falhar, retorna None + loga o erro.
        O chamador decide se pula o item ou aborta.

    Args:
        tier: EmbeddingTier.FLASH ou EmbeddingTier.ELITE.
        openai_api_key: Chave da API OpenAI (obrigatória para tier ELITE).
    """

    # Configurações por tier
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
            "EmbeddingManager inicializado: tier=%s, modelo=%s, dims=%d",
            tier.value, self._config["model_name"], self._dimensions
        )

    @property
    def dimensions(self) -> int:
        """Número de dimensões do modelo ativo."""
        return self._dimensions

    @property
    def tier(self) -> EmbeddingTier:
        """Tier atual (FLASH ou ELITE)."""
        return self._tier

    def _load_model(self) -> None:
        """Carrega o modelo de embedding (lazy loading).

        Raises:
            EmbeddingError: Se o modelo não pode ser carregado.
        """
        if self._model is not None:
            return

        if self._tier == EmbeddingTier.FLASH:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise EmbeddingError(
                    "sentence-transformers não instalado. "
                    "Instale com: pip install sentence-transformers"
                )
            try:
                self._model = SentenceTransformer(self._config["model_name"])
                logger.info("Modelo FLASH carregado: %s", self._config["model_name"])
            except Exception as e:
                raise EmbeddingError(f"Falha ao carregar modelo FLASH: {e}") from e

        elif self._tier == EmbeddingTier.ELITE:
            if not self._openai_key:
                raise EmbeddingError(
                    "openai_api_key é obrigatória para o tier ELITE."
                )
            try:
                import openai
                self._model = openai.OpenAI(api_key=self._openai_key)
                logger.info("Cliente OpenAI inicializado para tier ELITE.")
            except ImportError:
                raise EmbeddingError(
                    "openai não instalado. Instale com: pip install openai>=1.0"
                )

    def embed(self, text: str) -> Optional[list[float]]:
        """Gera embedding para um texto.

        Semantic Fallback: retorna None em caso de erro (não trava o pipeline).

        Args:
            text: Texto para gerar embedding.

        Returns:
            Lista de floats (vetor) ou None se falhou.
        """
        try:
            self._load_model()
        except EmbeddingError as e:
            logger.error("Modelo indisponível para embed(): %s", e)
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
            # SEMANTIC FALLBACK: loga o erro mas NÃO propaga
            logger.error(
                "Semantic Fallback ativado — embed falhou para texto (%.40s...): %s",
                text, e
            )
            return None

    def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Gera embeddings em lote.

        Semantic Fallback aplicado individualmente: itens que falham
        retornam None na posição correspondente.

        Args:
            texts: Lista de textos para gerar embeddings.

        Returns:
            Lista de vetores (ou None para itens que falharam).
        """
        try:
            self._load_model()
        except EmbeddingError as e:
            logger.error("Modelo indisponível para embed_batch(): %s", e)
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
            # OpenAI suporta batch nativo
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
# ChromaVectorStore — implementação concreta do BaseVectorBackend
# ---------------------------------------------------------------------------

class ChromaVectorStore(BaseVectorBackend):
    """Backend vetorial baseado em ChromaDB.

    Implementa todos os métodos do BaseVectorBackend:
        - store_embedding / store_embeddings_batch (Batch Processing)
        - search (Top-K com scores para Hybrid Search)
        - delete / delete_batch
        - verify_sync (Reconciliation Loop)
        - health_check / count

    Args:
        persist_dir: Diretório de persistência do ChromaDB.
        collection_name: Nome da coleção (default: 'grafo_concierge').
        embedding_manager: Instância de EmbeddingManager para gerar embeddings.
    """

    # Tamanho máximo de cada batch para ChromaDB (evita OOM em projetos gigantes)
    BATCH_SIZE: int = 100

    def __init__(
        self,
        persist_dir: str = "~/.grafo-concierge/chroma",
        collection_name: str = "grafo_concierge",
        embedding_manager: Optional[EmbeddingManager] = None,
    ) -> None:
        self._available = CHROMADB_AVAILABLE
        self._embedding_mgr = embedding_manager or EmbeddingManager()
        self._collection_name = collection_name

        if not CHROMADB_AVAILABLE:
            logger.warning(
                "ChromaVectorStore operando em modo NO-OP (chromadb não instalado)."
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
            "ChromaVectorStore inicializado: dir=%s, collection=%s, tier=%s",
            resolved_dir, collection_name, self._embedding_mgr.tier.value
        )

    # ===================================================================
    # STORE — armazenamento individual
    # ===================================================================

    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Armazena um embedding com metadados no ChromaDB.

        Args:
            doc_id: ID único (formato recomendado: 'node_{node_id}').
            embedding: Vetor de embedding.
            metadata: Dict com 'node_id' (int) e 'project_uuid' (str).

        Raises:
            ValueError: Se metadata não contém campos obrigatórios.
        """
        if not self._available:
            logger.warning("store_embedding ignorado: ChromaDB indisponível.")
            return

        self._validate_metadata(metadata)

        # ChromaDB requer que todos os valores de metadata sejam str, int ou float
        safe_meta = self._sanitize_metadata(metadata)

        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[safe_meta],
        )
        logger.debug("Embedding armazenado: doc_id=%s, node_id=%s", doc_id, metadata.get("node_id"))

    # ===================================================================
    # STORE BATCH — inserção em lote para concierge mine
    # ===================================================================

    def store_embeddings_batch(self, items: list[dict]) -> int:
        """Armazena múltiplos embeddings em lotes controlados.

        Processa em chunks de BATCH_SIZE para evitar OOM.
        Itens com embedding=None (Semantic Fallback) são ignorados silenciosamente.

        Args:
            items: Lista de dicts, cada um contendo:
                - doc_id (str)
                - embedding (list[float] ou None)
                - metadata (dict com node_id e project_uuid)

        Returns:
            Número de embeddings efetivamente armazenados.
        """
        if not self._available:
            logger.warning("store_embeddings_batch ignorado: ChromaDB indisponível.")
            return 0

        stored = 0
        # Filtra itens com embedding válido
        valid_items = [
            item for item in items
            if item.get("embedding") is not None
        ]

        skipped = len(items) - len(valid_items)
        if skipped > 0:
            logger.warning(
                "Batch store: %d itens ignorados (Semantic Fallback — embedding None)", skipped
            )

        # Processa em chunks
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
                    logger.warning("Item ignorado no batch (metadata inválida): %s", e)
                    continue

            if ids:
                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                stored += len(ids)
                logger.debug("Batch chunk armazenado: %d embeddings", len(ids))

        logger.info("Batch store finalizado: %d/%d embeddings armazenados.", stored, len(items))
        return stored

    # ===================================================================
    # SEARCH — busca vetorial para Hybrid Search
    # ===================================================================

    def search(
        self,
        query_embedding: list[float],
        project_uuids: list[str],
        top_k: int = 10,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Busca por similaridade coseno com Strict Scoping por projeto.

        Os resultados são retornados com scores normalizados [0, 1],
        prontos para o pipeline de Hybrid Search / Reranking.

        Args:
            query_embedding: Vetor da query.
            project_uuids: Lista de UUIDs para filtrar (Strict Scoping).
            top_k: Máximo de resultados.
            filters: Filtros adicionais (ex: {'node_type': 'FACT'}).

        Returns:
            Lista de VectorSearchResult ordenada por score DESC.
        """
        if not self._available:
            logger.warning("search ignorada: ChromaDB indisponível.")
            return []

        # Monta o filtro do ChromaDB
        where_filter = self._build_where_filter(project_uuids, filters)

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            logger.error("Erro na busca vetorial: %s", e)
            return []

        # ChromaDB retorna distances (menor = mais similar para cosine)
        # Convertemos para score (maior = mais similar): score = 1 - distance
        search_results: list[VectorSearchResult] = []

        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)

            for doc_id, distance, meta in zip(ids, distances, metadatas):
                # Cosine distance → similarity score
                score = max(1.0 - distance, 0.0)
                search_results.append(VectorSearchResult(
                    doc_id=doc_id,
                    node_id=int(meta.get("node_id", 0)),
                    project_uuid=str(meta.get("project_uuid", "")),
                    score=round(score, 4),
                    metadata=meta,
                ))

        logger.debug("Busca vetorial retornou %d resultados (top_k=%d)", len(search_results), top_k)
        return search_results

    # ===================================================================
    # DELETE — remoção individual e batch
    # ===================================================================

    def delete(self, doc_id: str) -> None:
        """Remove um embedding pelo doc_id."""
        if not self._available:
            return

        try:
            self._collection.delete(ids=[doc_id])
            logger.debug("Embedding removido: %s", doc_id)
        except Exception as e:
            logger.warning("Falha ao deletar embedding %s: %s", doc_id, e)

    def delete_batch(self, doc_ids: list[str]) -> int:
        """Remove múltiplos embeddings em lote.

        Args:
            doc_ids: Lista de doc_ids a remover.

        Returns:
            Número de IDs processados para remoção.
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
                logger.error("Falha ao deletar batch de %d embeddings: %s", len(chunk), e)

        logger.info("Batch delete finalizado: %d/%d removidos.", deleted, len(doc_ids))
        return deleted

    # ===================================================================
    # RECONCILIATION LOOP — verify_sync
    # ===================================================================

    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Detecta vetores órfãos comparando com os IDs válidos do SQLite.

        Fluxo paginado (proteção OOM):
            1. Obtém apenas os doc_ids do ChromaDB (sem metadados pesados).
            2. Itera em lotes de BATCH_SIZE, carregando metadados por fatia.
            3. Compara node_id de cada lote com sqlite_node_ids.
            4. Acumula doc_ids cujo node_id NÃO existe no SQLite.

        Args:
            sqlite_node_ids: Conjunto de node_ids válidos no SQLite.

        Returns:
            Lista de doc_ids órfãos (existem no vetor mas não no SQLite).
        """
        if not self._available:
            return []

        orphans: list[str] = []

        try:
            # Fase 1: obtém apenas IDs (sem metadados pesados na RAM)
            id_data = self._collection.get(include=[])
            all_ids = id_data.get("ids", [])

            if not all_ids:
                logger.info("Reconciliation Loop: coleção vazia — nada a verificar.")
                return []

            # Fase 2: itera em lotes de BATCH_SIZE, carregando metadados por fatia
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
                        # Metadata corrompida — considerar órfão
                        orphans.append(doc_id)
                        continue

                    if int(node_id) not in sqlite_node_ids:
                        orphans.append(doc_id)

        except Exception as e:
            logger.error("Falha no Reconciliation Loop (verify_sync): %s", e)

        if orphans:
            logger.warning(
                "Reconciliation Loop: %d vetores órfãos detectados.", len(orphans)
            )
        else:
            logger.info("Reconciliation Loop: todos os vetores estão sincronizados.")

        return orphans

    # ===================================================================
    # HEALTH CHECK + COUNT
    # ===================================================================

    def health_check(self) -> bool:
        """Verifica se o ChromaDB está operacional."""
        if not self._available:
            return False

        try:
            self._client.heartbeat()
            return True
        except Exception as e:
            logger.error("Health check falhou: %s", e)
            return False

    def count(self, project_uuid: Optional[str] = None) -> int:
        """Retorna o total de vetores armazenados.

        Args:
            project_uuid: Se informado, conta apenas vetores deste projeto.
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
            logger.error("Falha ao contar vetores: %s", e)
            return 0

    # ===================================================================
    # MÉTODOS AUXILIARES INTERNOS
    # ===================================================================

    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Atualiza os metadados de um vetor existente sem substituir o embedding.

        Permite que o JanitorService injete community_id e outros atributos
        sem precisar acessar self._collection diretamente.

        Args:
            doc_id: Identificador do documento (ex: 'node_42').
            metadata: Dicionário de metadados a aplicar.
        """
        if not self._available or self._collection is None:
            logger.debug("update_metadata: ChromaDB indisponível — ignorado para %s.", doc_id)
            return

        try:
            safe_meta = self._sanitize_metadata(metadata)
            self._collection.update(ids=[doc_id], metadatas=[safe_meta])
            logger.debug("Metadata vetorial atualizada: doc_id=%s", doc_id)
        except Exception as e:
            logger.error("Falha ao atualizar metadados no ChromaDB para %s: %s", doc_id, e)


    @staticmethod
    def _validate_metadata(metadata: dict) -> None:
        """Valida que metadata contém campos obrigatórios."""
        if "node_id" not in metadata:
            raise ValueError("metadata deve conter 'node_id' (int).")
        if "project_uuid" not in metadata:
            raise ValueError("metadata deve conter 'project_uuid' (str).")

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        """Garante que todos os valores de metadata sejam tipos aceitos pelo ChromaDB.

        ChromaDB aceita: str, int, float, bool. Listas e dicts são convertidos para str.
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
        """Monta o filtro 'where' do ChromaDB combinando projeto + filtros extras.

        Args:
            project_uuids: Lista de UUIDs para Strict Scoping.
            extra_filters: Filtros adicionais (ex: {'node_type': 'FACT'}).

        Returns:
            Dict no formato ChromaDB where, ou None se sem filtros.
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
