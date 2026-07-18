"""
storage/base_backend.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Interface abstrata para backends vetoriais plugáveis.

Qualquer backend vetorial (ChromaDB, Qdrant, Pinecone) DEVE implementar
esta interface para ser compatível com o Concierge Core.

Contratos:
    - store_embedding: Armazena um vetor + metadados. Metadata obrigatória: node_id, project_uuid.
    - store_embeddings_batch: Inserção em lote para ingestão massiva (concierge mine).
    - search: Busca por similaridade vetorial com pré-filtro por projeto.
    - delete: Remove um vetor pelo doc_id.
    - delete_batch: Remove múltiplos vetores.
    - verify_sync: Reconciliation Loop — detecta vetores órfãos.
    - health_check: Verifica se o backend está operacional.
    - count: Retorna o total de vetores armazenados (com filtro opcional).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Model Tiering — controla custo vs qualidade dos embeddings
# ---------------------------------------------------------------------------

class EmbeddingTier(str, Enum):
    """Tier de modelo de embedding para otimização de custo.

    FLASH: Modelo leve, rápido e gratuito (all-MiniLM-L6-v2, 384 dims).
           Ideal para ingestão massiva e projetos locais.

    ELITE: Modelo premium com maior precisão semântica
           (text-embedding-3-small, 1536 dims).
           Ideal para buscas críticas em produção.
    """
    FLASH = "flash"
    ELITE = "elite"


# ---------------------------------------------------------------------------
# Resultado padronizado de busca vetorial
# ---------------------------------------------------------------------------

class VectorSearchResult:
    """Resultado individual de uma busca vetorial.

    Attributes:
        doc_id: Identificador do documento no backend vetorial.
        node_id: ID do nó correspondente no SQLite.
        project_uuid: UUID do projeto ao qual o nó pertence.
        score: Score de similaridade coseno [0.0, 1.0].
        metadata: Metadados adicionais armazenados junto ao vetor.
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
        """Converte para dict compatível com o Hybrid Search pipeline."""
        return {
            "doc_id": self.doc_id,
            "node_id": self.node_id,
            "project_uuid": self.project_uuid,
            "vector_score": self.score,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# BaseVectorBackend — Interface abstrata
# ---------------------------------------------------------------------------

class BaseVectorBackend(ABC):
    """Interface abstrata para backends vetoriais plugáveis.

    Implementações concretas: ChromaBackend, QdrantBackend, PineconeBackend.

    Todos os métodos de armazenamento DEVEM incluir nos metadados:
        - node_id (int): ID correspondente na tabela nodes do SQLite.
        - project_uuid (str): UUID do projeto para Strict Scoping.
    """

    @abstractmethod
    def store_embedding(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Armazena um embedding com metadados.

        Args:
            doc_id: Identificador único do documento (formato: 'node_{node_id}').
            embedding: Vetor de embedding (384 ou 1536 dimensões).
            metadata: Dict contendo obrigatoriamente 'node_id' e 'project_uuid'.

        Raises:
            ValueError: Se metadata não contém campos obrigatórios.
        """
        ...

    @abstractmethod
    def store_embeddings_batch(
        self,
        items: list[dict],
    ) -> int:
        """Armazena múltiplos embeddings em lote.

        Cada item da lista DEVE conter:
            - doc_id (str)
            - embedding (list[float])
            - metadata (dict com node_id e project_uuid)

        Args:
            items: Lista de dicts com doc_id, embedding e metadata.

        Returns:
            Número de embeddings armazenados com sucesso.

        Raises:
            ValueError: Se algum item não contém campos obrigatórios.
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
        """Busca por similaridade vetorial com pré-filtro por projeto.

        Args:
            query_embedding: Vetor da query (mesma dimensão dos vetores armazenados).
            project_uuids: Lista de UUIDs para Strict Scoping.
            top_k: Número máximo de resultados.
            filters: Filtros adicionais (ex: {'node_type': 'FACT'}).

        Returns:
            Lista de VectorSearchResult ordenada por score DESC.
        """
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove um embedding pelo doc_id.

        Args:
            doc_id: Identificador do documento a remover.
        """
        ...

    @abstractmethod
    def delete_batch(self, doc_ids: list[str]) -> int:
        """Remove múltiplos embeddings.

        Args:
            doc_ids: Lista de identificadores a remover.

        Returns:
            Número de embeddings removidos com sucesso.
        """
        ...

    @abstractmethod
    def verify_sync(self, sqlite_node_ids: set[int]) -> list[str]:
        """Reconciliation Loop — detecta vetores órfãos no backend.

        Compara os IDs existentes no backend vetorial com os IDs válidos
        do SQLite. Retorna doc_ids que existem no vetor mas NÃO no SQLite.

        Args:
            sqlite_node_ids: Conjunto de node_ids válidos no SQLite.

        Returns:
            Lista de doc_ids órfãos que devem ser deletados.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica se o backend está operacional.

        Returns:
            True se o backend está acessível e respondendo.
        """
        ...

    @abstractmethod
    def count(self, project_uuid: Optional[str] = None) -> int:
        """Retorna o total de vetores armazenados.

        Args:
            project_uuid: Se informado, conta apenas vetores deste projeto.

        Returns:
            Contagem de vetores.
        """
        ...

    @abstractmethod
    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        """Atualiza os metadados de um vetor existente sem substituir o embedding.

        Permite que o Janitor injete community_id e outros atributos sem
        precisar acessar _collection diretamente.

        Args:
            doc_id: Identificador do documento (ex: 'node_42').
            metadata: Dicionário de metadados a aplicar (merge ou replace).
        """
        ...

    @abstractmethod
    def get_all_stored_node_ids(self) -> set[int]:
        """Retorna o conjunto de todos os node_ids numéricos presentes no backend vetorial.

        Returns:
            Conjunto contendo todos os node_ids numéricos armazenados.
        """
        ...
