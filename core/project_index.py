"""
core/project_index.py — Grafo Concierge v3.8.0 (Absolute Solidity)

GPS de Conhecimento — Categorização automática de projetos em Alas (Wings).

Responsabilidades:
    1. Categorização automática: Infere a Primary Wing de um projeto
       analisando nomes de arquivos, tags e descrições contra o
       dicionário WING_KEYWORDS de ConciergeConfig.
    2. Gerenciamento de Wings: API para set/get Primary Wing e
       adicionar/remover Reference Wings.
    3. Listagem por Ala: Busca projetos da mesma ala para
       find_similar_projects().

Integração:
    - Lê e escreve na tabela `projects` via SqliteStore.
    - Lê e escreve na tabela `reference_wings` via SqliteStore.
    - Consulta ConciergeConfig.wing_keywords para classificação.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

from storage.store import SqliteStore
from core.config import ConciergeConfig, DEFAULT_CONFIG

logger = logging.getLogger("grafo-concierge.project-index")


class ProjectIndex:
    """GPS de Conhecimento — gerencia categorização e descoberta de projetos.

    Args:
        sqlite_store: Instância de SqliteStore para persistência.
        config: Configurações do sistema (default: DEFAULT_CONFIG).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        config: ConciergeConfig = DEFAULT_CONFIG,
    ) -> None:
        self._store = sqlite_store
        self._config = config

    # ===================================================================
    # CATEGORIZAÇÃO AUTOMÁTICA
    # ===================================================================

    def categorize_project(
        self,
        labels: list[str],
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Infere a Primary Wing mais adequada para um projeto.

        Analisa labels de nós (nomes de arquivos), tags detectadas e
        uma descrição opcional contra o dicionário de WING_KEYWORDS.

        Algoritmo:
            1. Concatena labels + tags + descrição em um corpus.
            2. Para cada ala, conta quantas palavras-chave aparecem.
            3. A ala com mais matches vence.
            4. Empate: retorna a primeira ala em ordem alfabética.
            5. Zero matches: retorna config.default_wing ("geral").

        Args:
            labels: Nomes de arquivos / nós do projeto.
            tags: Tags detectadas durante a ingestão.
            description: Descrição textual do projeto (opcional).

        Returns:
            Nome da ala (ex: "gestão/saas", "finanças/quant", "geral").
        """
        # Monta corpus normalizado
        corpus_parts: list[str] = []
        corpus_parts.extend(labels)
        if tags:
            corpus_parts.extend(tags)
        if description:
            corpus_parts.append(description)

        corpus = " ".join(corpus_parts).lower()

        # Conta matches por ala
        scores: Counter[str] = Counter()
        for wing, keywords in self._config.wing_keywords.items():
            for kw in keywords:
                if kw.lower() in corpus:
                    scores[wing] += 1

        if not scores:
            logger.debug("Nenhuma keyword detectada — ala padrão '%s'.", self._config.default_wing)
            return self._config.default_wing

        # Ala com mais matches (em caso de empate, ordem alfabética)
        best_wing = max(sorted(scores.keys()), key=lambda w: scores[w])
        logger.info(
            "Categorização automática: '%s' (score=%d, total_candidatas=%d)",
            best_wing, scores[best_wing], len(scores),
        )
        return best_wing

    # ===================================================================
    # PRIMARY WING — Gerenciamento
    # ===================================================================

    def get_primary_wing(self, project_uuid: str) -> str:
        """Retorna a Primary Wing de um projeto.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Nome da Primary Wing.

        Raises:
            ProjectNotFoundError: Se o projeto não existe.
        """
        project = self._store.get_project(project_uuid)
        return project.get("primary_wing", self._config.default_wing)

    def set_primary_wing(self, project_uuid: str, wing: str) -> None:
        """Define a Primary Wing de um projeto (override manual).

        Args:
            project_uuid: UUID do projeto.
            wing: Nome da ala a atribuir.

        Raises:
            ProjectNotFoundError: Se o projeto não existe.
        """
        # Valida que o projeto existe
        self._store.get_project(project_uuid)
        self._store.update_project(project_uuid, primary_wing=wing)
        logger.info("Primary Wing definida: projeto=%s, wing='%s'", project_uuid, wing)

    def auto_categorize_project(self, project_uuid: str) -> str:
        """Categoriza automaticamente um projeto baseado nos nós existentes.

        Fluxo:
            1. Busca todos os nós ACTIVE do projeto.
            2. Extrai labels e tags.
            3. Chama categorize_project().
            4. Atualiza a Primary Wing no banco.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Nome da ala atribuída.
        """
        nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")

        labels = [n["label"] for n in nodes]
        all_tags: list[str] = []
        for n in nodes:
            if isinstance(n.get("tags"), list):
                all_tags.extend(n["tags"])

        # Usa o summary do projeto como descrição, se disponível
        project = self._store.get_project(project_uuid)
        description = project.get("summary")

        wing = self.categorize_project(labels, all_tags, description)
        self.set_primary_wing(project_uuid, wing)

        return wing

    # ===================================================================
    # REFERENCE WINGS — Gerenciamento
    # ===================================================================

    def get_reference_wings(self, project_uuid: str) -> list[str]:
        """Lista as Reference Wings de um projeto.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Lista de nomes de alas referenciadas.
        """
        return self._store.get_reference_wings(project_uuid)

    def add_reference_wing(self, project_uuid: str, wing: str) -> None:
        """Adiciona uma Reference Wing ao projeto.

        Reference Wings permitem buscas interdisciplinares,
        expondo apenas resumos (não dados brutos) da ala referenciada.

        Args:
            project_uuid: UUID do projeto.
            wing: Nome da ala a referenciar.
        """
        primary = self.get_primary_wing(project_uuid)
        if wing == primary:
            logger.warning(
                "Reference Wing '%s' é idêntica à Primary Wing — ignorando.", wing
            )
            return

        self._store.add_reference_wing(project_uuid, wing)
        logger.info("Reference Wing adicionada: projeto=%s, wing='%s'", project_uuid, wing)

    def remove_reference_wing(self, project_uuid: str, wing: str) -> None:
        """Remove uma Reference Wing do projeto.

        Args:
            project_uuid: UUID do projeto.
            wing: Nome da ala a remover.
        """
        self._store.remove_reference_wing(project_uuid, wing)
        logger.info("Reference Wing removida: projeto=%s, wing='%s'", project_uuid, wing)

    # ===================================================================
    # STRICT SCOPING — Resolução de UUIDs para busca
    # ===================================================================

    def resolve_scoped_uuids(
        self,
        project_uuid: str,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[str]:
        """Resolve a lista de project_uuids para Strict Scoping.

        Modos:
            - Padrão: Apenas projetos da mesma Primary Wing.
            - include_references=True: Primary + Reference Wings.
            - all_wings=True: Todos os projetos do sistema.

        Args:
            project_uuid: UUID do projeto âncora.
            include_references: Incluir Reference Wings.
            all_wings: Incluir todas as alas (ignora scoping).

        Returns:
            Lista de UUIDs de projetos no escopo da busca.
        """
        all_projects = self._store.list_projects()

        if all_wings:
            return [p["uuid"] for p in all_projects]

        # Monta o conjunto de alas no escopo
        primary = self.get_primary_wing(project_uuid)
        target_wings = {primary}

        if include_references:
            ref_wings = self.get_reference_wings(project_uuid)
            target_wings.update(ref_wings)

        # Filtra projetos que pertencem às alas do escopo
        scoped = [
            p["uuid"] for p in all_projects
            if p.get("primary_wing", self._config.default_wing) in target_wings
        ]

        logger.debug(
            "Strict Scoping: projeto=%s, wings=%s, projetos_no_escopo=%d",
            project_uuid, target_wings, len(scoped),
        )
        return scoped

    # ===================================================================
    # DESCOBERTA — Projetos similares
    # ===================================================================

    def find_similar_projects(
        self,
        project_uuid: str,
        limit: int = 5,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[dict]:
        """Busca projetos da mesma ala (ou alas expandidas).

        A similaridade é baseada na ala: projetos da mesma Primary Wing
        são considerados similares por domínio.

        Args:
            project_uuid: UUID do projeto âncora.
            limit: Máximo de projetos a retornar.
            include_references: Incluir Reference Wings.
            all_wings: Incluir todas as alas.

        Returns:
            Lista de dicts com dados de projetos (excluindo o próprio).
        """
        scoped_uuids = self.resolve_scoped_uuids(
            project_uuid,
            include_references=include_references,
            all_wings=all_wings,
        )

        # Remove o projeto âncora da lista
        scoped_uuids = [u for u in scoped_uuids if u != project_uuid]

        # Busca dados completos dos projetos no escopo
        results: list[dict] = []
        for uuid in scoped_uuids[:limit]:
            try:
                project = self._store.get_project(uuid)
                results.append(project)
            except Exception:
                continue

        logger.info(
            "find_similar_projects: projeto=%s, encontrados=%d (limit=%d)",
            project_uuid, len(results), limit,
        )
        return results
