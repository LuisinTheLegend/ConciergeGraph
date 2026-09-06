"""
core/delta_manager.py — SDD-SURVIVAL-04 / SDD-SURVIVAL-11

Cost Containment Gateway — Delta Synchronization.

Discriminates file modifications between:
  - Cosmetic changes (comments, whitespaces, docstrings) -> completely ignored
  - Internal logic changes (ifs, returns, variables) -> marked as DIRTY (SDD-11)
  - Structural changes (def, class, import) -> marks community as DIRTY

Re-summarization via LLM occurs exclusively on-demand (Lazy Summarization JIT),
preventing unexpected cloud API bills during trivial code modifications.

Key Concepts:
  - SSH (Structural Signature Hash): SHA-256 of public signature lines
    (def, class, import, from), ignoring implementation bodies.
  - LBH (Logical Body Hash): SHA-256 of structural AST dump after removing
    docstrings via DocstringStripper, detecting semantic drift even without signature alterations. (SDD-11)
  - Dirty Flag Propagation: DIRTY file -> DIRTY community.
  - Community Reconciliation: when all files in a community are clean,
    the community is reconciled back to CLEAN.
"""

import ast
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Prefixes defining public structural signature lines
_STRUCTURAL_PREFIXES = ("def ", "class ", "import ", "from ")


class DocstringStripper(ast.NodeTransformer):
    """
    AST transformer that strips docstrings from functions and classes,
    allowing the logical body hash to ignore documentation changes.
    """

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node

    def visit_AsyncFunctionDef(self, node):
        # Treat async functions identically to standard functions
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node


class DeltaManager:
    """
    Manages delta synchronization between physical file modifications
    and the structural state of the community graph in SQLite WAL.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Structural Signatures ──────────────────────────────────────

    _stripper = DocstringStripper()

    def calculate_ssh(self, file_content: str) -> str:
        """
        Extracts structural signature lines (def, class, import, from),
        ignoring internal implementation, comments, and whitespace.
        Returns a deterministic SHA-256 hash of consolidated signature.
        """
        structural_lines = [
            stripped
            for line in file_content.splitlines()
            if (stripped := line.strip()).startswith(_STRUCTURAL_PREFIXES)
        ]
        if not structural_lines:
            return ""
        signature = "\n".join(structural_lines)
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()

    def calculate_lbh(self, file_content: str) -> str:
        """
        Calculates the Logical Body Hash (LBH) of Python code:
        parses AST, strips docstrings via DocstringStripper,
        generates structural ast.dump, and returns SHA-256.

        Ignores comments, whitespace, and docstrings.
        Detects any internal logic modification (ifs, returns, operators).

        Returns empty string for non-Python files or parse syntax errors.
        """
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return ""
        cleaned = self._stripper.visit(tree)
        dump = ast.dump(cleaned, annotate_fields=False)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    # ── Change Processing ──────────────────────────────────────────

    def process_file_change(
        self, file_path: str, new_content: str, community_id: str
    ) -> bool:
        """
        Compares structural signature (SSH) and logical body hash (LBH)
        of new content against stored database records.

        Returns True if structural or semantic change occurred (DIRTY),
        False if only cosmetic comments, whitespaces, or docstrings were modified.
        """
        new_ssh = self.calculate_ssh(new_content)
        new_lbh = self.calculate_lbh(new_content)

        existing = self.db_manager.read_query(
            "SELECT ssh_hash, body_hash FROM files WHERE path = ?;", (file_path,)
        )

        if not existing:
            # New file: structural addition to graph
            return self._insert_new_file(
                file_path, new_content, new_ssh, new_lbh, community_id
            )

        old_ssh = existing[0][0]
        old_lbh = existing[0][1]

        ssh_changed = new_ssh != old_ssh
        lbh_changed = new_lbh != old_lbh

        if not ssh_changed and not lbh_changed:
            # Strictly cosmetic modification (comments, whitespace, docstrings)
            return self._update_content_only(file_path, new_content, community_id)

        # Structural and/or semantic change detected
        return self._update_structural_change(
            file_path, new_content, new_ssh, new_lbh, community_id
        )

    # ── Lazy Summarization JIT ─────────────────────────────────────

    def compile_community_summary_jit(
        self, community_id: str, cloud_llm_mock_callback
    ) -> str:
        """
        Returns cached summary if community is clean.
        If DIRTY, consolidates file contents, triggers LLM callback,
        saves result, and reconciles dirty flags.
        """
        community = self.db_manager.read_query(
            "SELECT is_dirty, summary_text FROM communities WHERE id = ?;",
            (community_id,),
        )
        if not community:
            raise ValueError(f"Community not found: {community_id}")

        is_dirty, summary_text = community[0]

        # Cache hit: clean community with existing summary
        if is_dirty == 0 and summary_text:
            return summary_text

        # Cache miss: on-demand recompilation
        files = self.db_manager.read_query(
            "SELECT content FROM files WHERE community_id = ?;",
            (community_id,),
        )
        payload = "\n".join(row[0] for row in files)

        new_summary = cloud_llm_mock_callback(payload)

        # Persist new summary and reconcile flags
        self.db_manager.write_query(
            "UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;",
            (new_summary, community_id),
        )
        self.db_manager.write_query(
            "UPDATE files SET is_dirty = 0 WHERE community_id = ?;",
            (community_id,),
        )

        return new_summary

    # ── Internal Database Operations ───────────────────────────────

    def _insert_new_file(
        self,
        file_path: str,
        content: str,
        ssh_hash: str,
        body_hash: str,
        community_id: str,
    ) -> bool:
        """Records new file into graph and propagates DIRTY flag to community."""
        self.db_manager.write_query(
            "INSERT INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) "
            "VALUES (?, ?, ?, ?, 1, ?);",
            (file_path, content, ssh_hash, body_hash, community_id),
        )
        self.db_manager.write_query(
            "UPDATE communities SET is_dirty = 1 WHERE id = ?;",
            (community_id,),
        )
        return True

    def _update_content_only(
        self, file_path: str, content: str, community_id: str
    ) -> bool:
        """
        Updates content only (internal logic/cosmetic change).
        Clears dirty flag for file and reconciles community if all its files are clean.
        """
        self.db_manager.write_query(
            "UPDATE files SET content = ?, is_dirty = 0 WHERE path = ?;",
            (content, file_path),
        )
        # Community reconciliation: clears dirty flag if no remaining file is DIRTY
        dirty_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM files WHERE community_id = ? AND is_dirty = 1;",
            (community_id,),
        )[0][0]
        if dirty_count == 0:
            self.db_manager.write_query(
                "UPDATE communities SET is_dirty = 0 WHERE id = ?;",
                (community_id,),
            )
        return False

    def _update_structural_change(
        self,
        file_path: str,
        content: str,
        ssh_hash: str,
        body_hash: str,
        community_id: str,
    ) -> bool:
        """Updates file with new signature/body and propagates DIRTY to community."""
        self.db_manager.write_query(
            "UPDATE files SET content = ?, ssh_hash = ?, body_hash = ?, is_dirty = 1 "
            "WHERE path = ?;",
            (content, ssh_hash, body_hash, file_path),
        )
        self.db_manager.write_query(
            "UPDATE communities SET is_dirty = 1 WHERE id = ?;",
            (community_id,),
        )
        return True
