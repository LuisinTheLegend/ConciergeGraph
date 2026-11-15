"""
core/dependencies.py — SDD-SURVIVAL-03

Strict Dependency Injection Container (AgentDependencies).

Centralizes all sensitive resources and environment configurations in an
immutable strongly-typed container (frozen dataclass), eliminating loose global
connection coupling and enabling clean mocks for offline testing.

Encapsulated Resources:
  - db_manager:     ConciergeDatabaseManager instance (SDD-SURVIVAL-02)
  - workspace_path: Absolute physical root path of user project
  - rate_governor:  Optional LLM request rate governor
  - security_guard: Optional permissions and sandboxing validator
"""

from dataclasses import dataclass
import os
from typing import Any, Optional


@dataclass(frozen=True)
class AgentDependencies:
    """
    Immutable container centralizing local infrastructure resources,
    guaranteeing connection isolation and facilitating test injection.
    """

    db_manager: Any  # ConciergeDatabaseManager instance
    workspace_path: str
    rate_governor: Optional[Any] = None
    security_guard: Optional[Any] = None

    def __post_init__(self):
        # Strict security validation during resource bootstrap
        if not os.path.exists(self.workspace_path):
            raise ValueError(
                f"Invalid or non-existent workspace path: {self.workspace_path}"
            )
