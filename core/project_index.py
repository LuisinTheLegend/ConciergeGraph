"""
core/project_index.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Knowledge GPS — Automatic categorization of projects into Wings.

Responsibilities:
    1. Automatic categorization: Infers a project's Primary Wing by
       analyzing file names, tags, and descriptions against the
       WING_KEYWORDS dictionary of ConciergeConfig.
    2. Wing management: API to set/get Primary Wing and
       add/remove Reference Wings.
    3. List by Wing: Searches for projects in the same wing for
       find_similar_projects().

Integration:
    - Reads and writes to the `projects` table via SqliteStore.
    - Reads and writes to the `reference_wings` table via SqliteStore.
    - Queries ConciergeConfig.wing_keywords for classification.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

from storage.store import SqliteStore
from core.config import ConciergeConfig, DEFAULT_CONFIG

logger = logging.getLogger("grafo-concierge.project-index")


class ProjectIndex:
    """Knowledge GPS — manages project categorization and discovery.

    Args:
        sqlite_store: SqliteStore instance for persistence.
        config: System configurations (default: DEFAULT_CONFIG).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        config: ConciergeConfig = DEFAULT_CONFIG,
    ) -> None:
        self._store = sqlite_store
        self._config = config

    # ===================================================================
    # AUTOMATIC CATEGORIZATION
    # ===================================================================

    def categorize_project(
        self,
        labels: list[str],
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Infers the most suitable Primary Wing for a project.

        Analyzes node labels (file names), detected tags, and
        an optional description against the WING_KEYWORDS dictionary.

        Algorithm:
            1. Concatenates labels + tags + description into a corpus.
            2. For each wing, counts how many keywords appear.
            3. The wing with the most matches wins.
            4. Tie: returns the first wing in alphabetical order.
            5. Zero matches: returns config.default_wing ("geral").

        Args:
            labels: File / node names of the project.
            tags: Tags detected during ingestion.
            description: Textual description of the project (optional).

        Returns:
            Wing name (e.g. "gestão/saas", "finanças/quant", "geral").
        """
        # Build normalized corpus
        corpus_parts: list[str] = []
        corpus_parts.extend(labels)
        if tags:
            corpus_parts.extend(tags)
        if description:
            corpus_parts.append(description)

        corpus = " ".join(corpus_parts).lower()

        # Count matches per wing
        scores: Counter[str] = Counter()
        for wing, keywords in self._config.wing_keywords.items():
            for kw in keywords:
                if kw.lower() in corpus:
                    scores[wing] += 1

        if not scores:
            logger.debug("No keyword detected — using default wing '%s'.", self._config.default_wing)
            return self._config.default_wing

        # Wing with most matches (in case of tie, alphabetical order)
        best_wing = max(sorted(scores.keys()), key=lambda w: scores[w])
        logger.info(
            "Automatic categorization: '%s' (score=%d, total_candidates=%d)",
            best_wing, scores[best_wing], len(scores),
        )
        return best_wing

    # ===================================================================
    # PRIMARY WING — Management
    # ===================================================================

    def get_primary_wing(self, project_uuid: str) -> str:
        """Returns the Primary Wing of a project.

        Args:
            project_uuid: Project UUID.

        Returns:
            Name of the Primary Wing.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        project = self._store.get_project(project_uuid)
        return project.get("primary_wing", self._config.default_wing)

    def set_primary_wing(self, project_uuid: str, wing: str) -> None:
        """Sets the Primary Wing of a project (manual override).

        Args:
            project_uuid: Project UUID.
            wing: Wing name to assign.

        Raises:
            ProjectNotFoundError: If the project does not exist.
        """
        # Validate that the project exists
        self._store.get_project(project_uuid)
        self._store.update_project(project_uuid, primary_wing=wing)
        logger.info("Primary Wing definida: projeto=%s, wing='%s'", project_uuid, wing)

    def auto_categorize_project(self, project_uuid: str) -> str:
        """Automatically categorizes a project based on existing nodes.

        Flow:
            1. Fetches all ACTIVE nodes of the project.
            2. Extracts labels and tags.
            3. Calls categorize_project().
            4. Updates the Primary Wing in the database.

        Args:
            project_uuid: Project UUID.

        Returns:
            Name of the assigned wing.
        """
        nodes = self._store.get_nodes_by_project(project_uuid, status="ACTIVE")

        labels = [n["label"] for n in nodes]
        all_tags: list[str] = []
        for n in nodes:
            if isinstance(n.get("tags"), list):
                all_tags.extend(n["tags"])

        # Use the project summary as description, if available
        project = self._store.get_project(project_uuid)
        description = project.get("summary")

        wing = self.categorize_project(labels, all_tags, description)
        self.set_primary_wing(project_uuid, wing)

        return wing

    # ===================================================================
    # REFERENCE WINGS — Management
    # ===================================================================

    def get_reference_wings(self, project_uuid: str) -> list[str]:
        """Lists the Reference Wings of a project.

        Args:
            project_uuid: Project UUID.

        Returns:
            List of referenced wing names.
        """
        return self._store.get_reference_wings(project_uuid)

    def add_reference_wing(self, project_uuid: str, wing: str) -> None:
        """Adds a Reference Wing to the project.

        Reference Wings allow cross-disciplinary searches,
        exposing only summaries (not raw data) of the referenced wing.

        Args:
            project_uuid: Project UUID.
            wing: Wing name to reference.
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
        """Removes a Reference Wing from the project.

        Args:
            project_uuid: Project UUID.
            wing: Wing name to remove.
        """
        self._store.remove_reference_wing(project_uuid, wing)
        logger.info("Reference Wing removida: projeto=%s, wing='%s'", project_uuid, wing)

    # ===================================================================
    # STRICT SCOPING — UUID Resolution for search
    # ===================================================================

    def resolve_scoped_uuids(
        self,
        project_uuid: str,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[str]:
        """Resolves the list of project_uuids for Strict Scoping.

        Modes:
            - Default: Only projects of the same Primary Wing.
            - include_references=True: Primary + Reference Wings.
            - all_wings=True: All projects in the system.

        Args:
            project_uuid: Anchor project UUID.
            include_references: Include Reference Wings.
            all_wings: Include all wings (ignores scoping).

        Returns:
            List of project UUIDs in the scope of the search.
        """
        all_projects = self._store.list_projects()

        if all_wings:
            return [p["uuid"] for p in all_projects]

        # Assemble the set of wings in scope
        primary = self.get_primary_wing(project_uuid)
        target_wings = {primary}

        if include_references:
            ref_wings = self.get_reference_wings(project_uuid)
            target_wings.update(ref_wings)

        # Filter projects that belong to the wings in scope
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
    # DISCOVERY — Similar Projects
    # ===================================================================

    def find_similar_projects(
        self,
        project_uuid: str,
        limit: int = 5,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[dict]:
        """Searches projects of the same wing (or expanded wings).

        Similarity is based on the wing: projects of the same Primary Wing
        are considered similar by domain.

        Args:
            project_uuid: Anchor project UUID.
            limit: Maximum projects to return.
            include_references: Include Reference Wings.
            all_wings: Include all wings.

        Returns:
            List of dicts with project data (excluding itself).
        """
        scoped_uuids = self.resolve_scoped_uuids(
            project_uuid,
            include_references=include_references,
            all_wings=all_wings,
        )

        # Remove the anchor project from the list
        scoped_uuids = [u for u in scoped_uuids if u != project_uuid]

        # Retrieve complete data of projects in scope
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
