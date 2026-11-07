"""
core/project_index.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Knowledge GPS — Wing and Scope Management with Domain Neutrality.

Responsibilities:
    1. Wing management: API to set/get Primary Wing and
       add/remove Reference Wings.
    2. List by Wing: Searches for projects in the same wing for
       find_similar_projects().
    3. Strict Scoping: Resolves UUID scopes for strict isolation
       and cross-domain reference wings.

Integration:
    - Reads and writes to the `projects` table via SqliteStore.
    - Reads and writes to the `reference_wings` table via SqliteStore.
"""

from __future__ import annotations

import logging
from typing import Optional

from storage.store import SqliteStore
from core.config import ConciergeConfig, DEFAULT_CONFIG

logger = logging.getLogger("grafo-concierge.project-index")


class ProjectIndex:
    """Knowledge GPS — manages project wings, scoping, and discovery.

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
                "Reference Wing '%s' is identical to Primary Wing — ignoring.", wing
            )
            return

        self._store.add_reference_wing(project_uuid, wing)
        logger.info("Reference Wing added: project=%s, wing='%s'", project_uuid, wing)

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
