"""
core/security_guard.py — SDD-SURVIVAL-24

Boundary Guard and Hazard Classifier (Vanguard Bounds Guard).

Implements two complementary security barriers:
  1. is_safe_path: Physical barrier preventing reading or writing files outside
     the normalized root directory of the monorepo.
     Prevents Path Traversal (../../etc/passwd) even under agent hallucination.
  2. classify_command: Terminal command classifier with three risk tiers
     (SAFE, WARNING, CRITICAL), feeding into GatingInterceptor.

Security Invariants:
  - Normalization via os.path.realpath() resolves symlinks and traversals.
  - Blacklist regex for inherently destructive commands (rm -rf /, mkfs, dd).
  - Zero-trust: empty or missing paths are treated as safe no-ops.
"""

import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)


class SecurityGuard:
    """
    Security boundary guard with physical path validation
    and terminal command classification.

    Parameters:
      project_root — Root directory of the monorepo. Normalized via realpath()
                     to resolve symlinks and relative path segments.
    """

    def __init__(self, project_root: str):
        # Normalize monorepo path for absolute boundary enforcement
        self.project_root = os.path.realpath(project_root)

        # Blacklisted patterns for inherently destructive commands
        self.blacklisted_patterns = re.compile(
            r"(\brm\s+-rf\s+/|\b(mkfs|dd\s+if|shutdown|reboot|systemctl|userdel|iptables)\b)",
            re.IGNORECASE,
        )

        # Terms indicating infrastructure, build, or package installation commands (WARNING)
        self.warning_terms: List[str] = [
            "npm install",
            "pip install",
            "pytest",
            "build",
            "docker",
        ]

    def is_safe_path(self, target_path: str) -> bool:
        """
        Ensures no file is read or modified outside the physical monorepo boundaries
        (Absolute Path Traversal Prevention).

        Normalizes destination path via os.path.realpath() and validates against
        project root directory. Empty paths are treated as safe no-ops
        (no target path = no hazard).

        Returns:
          True  — if path is within monorepo or is empty/null.
          False — if normalized path falls outside monorepo boundaries.
        """
        if not target_path:
            return True
        try:
            absolute_target = os.path.realpath(target_path)
            # Verify target path starts with project root + separator
            # to prevent partial string collisions (e.g. /home/user/project-evil vs /home/user/project)
            return absolute_target.startswith(
                self.project_root + os.sep
            ) or absolute_target == self.project_root
        except Exception:
            return False

    def classify_command(self, command: str) -> str:
        """
        Classifies terminal commands into three risk levels:

          CRITICAL — Inherently banned commands (rm -rf /, mkfs, dd if, etc.).
                     Blocked across ALL gating modes, including auto-approve.
          WARNING  — Infrastructure/build commands (npm install, docker, pytest, build).
                     Require human developer approval under 'ask' mode.
          SAFE     — All other safe commands (ls, cat, echo, git status, etc.).
                     Executed automatically.

        Returns: "CRITICAL", "WARNING", or "SAFE".
        """
        if self.blacklisted_patterns.search(command):
            return "CRITICAL"

        # Packaging, infrastructure, or compilation commands
        if any(term in command for term in self.warning_terms):
            return "WARNING"

        return "SAFE"
