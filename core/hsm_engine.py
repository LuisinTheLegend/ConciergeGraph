"""
core/hsm_engine.py — SDD-SURVIVAL-25 / SDD-SURVIVAL-27

Hierarchical State Machine (HSM) Engine with History Nodes & Execution Restore.

Implements nested-state orchestration (super-states and sub-states) with deep
History Nodes (H*) that persist the agent's exact execution sub-state into the
SQLite WAL relational subsystem (`fsm_checkpoints`).

On interruption, restart, or Gating pause, the HSM restores the agent exactly
to the sub-state where it stopped — including shared context variables — with
zero token waste from re-executing prior steps.

SDD-27 Extensions:
    - Lifecycle Hooks (on_enter / on_exit): Registered callbacks per HSMNode
      fired during transitions in strict hierarchical order with atomic rollback.
    - Delta Validation on Resume: Confronts checkpoint timestamp with file mtime
      to detect stale code and redirect to EXECUTION.RE_INDEX.

Architecture:
    - HSMNode: Composite tree node representing a state or sub-state.
    - HierarchicalStateMachine: Session-aware orchestrator managing transitions,
      history node recording, MCPToolGovernor synchronization, and checkpoint
      persistence via AgnosticCheckpointer.

Integration Points:
    - core/checkpointer.py (AgnosticCheckpointer): Persistent state snapshots
    - core/mcp_governor.py (MCPToolGovernor): Progressive tool disclosure sync
    - core/database.py (ConciergeDatabaseManager): SQLite WAL read queries
"""

import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IllegalHSMTransitionError(Exception):
    """Raised when a hierarchical state transition targets an invalid or non-existent path."""
    pass


class HSMNode:
    """
    Composite tree node representing a state in the hierarchical state machine.

    Each node has:
        - name: The local state identifier (e.g. 'TDD_GREEN')
        - parent: Reference to the parent super-state node (None for ROOT)
        - category: MCP tool governance category ('READ_ONLY', 'LOCAL_MUTATION', 'DANGEROUS')
        - substates: Dict of child sub-state nodes
        - _on_enter_hooks: Lifecycle callbacks fired when entering this state (SDD-27)
        - _on_exit_hooks: Lifecycle callbacks fired when exiting this state (SDD-27)
    """

    def __init__(self, name: str, parent: Optional["HSMNode"] = None, category: str = "READ_ONLY"):
        self.name = name
        self.parent = parent
        self.category = category
        self.substates: Dict[str, "HSMNode"] = {}
        self._on_enter_hooks: List[Callable[[], None]] = []
        self._on_exit_hooks: List[Callable[[], None]] = []

    def add_substate(self, child_name: str, category: str = "READ_ONLY") -> "HSMNode":
        """Creates and registers a child sub-state node under this node."""
        child = HSMNode(child_name, parent=self, category=category)
        self.substates[child_name] = child
        return child

    def get_full_path(self) -> str:
        """Returns the fully-qualified state path (e.g. 'EXECUTION.TDD_GREEN')."""
        if self.parent and self.parent.name != "ROOT":
            return f"{self.parent.get_full_path()}.{self.name}"
        return self.name

    def is_leaf(self) -> bool:
        """Returns True if this node has no child sub-states."""
        return len(self.substates) == 0

    # ── Lifecycle Hooks (SDD-27) ─────────────────────────────────────

    def register_on_enter(self, fn: Callable[[], None]) -> None:
        """Registers a callback to be invoked when the HSM enters this state."""
        self._on_enter_hooks.append(fn)

    def register_on_exit(self, fn: Callable[[], None]) -> None:
        """Registers a callback to be invoked when the HSM exits this state."""
        self._on_exit_hooks.append(fn)

    def execute_on_enter(self) -> None:
        """
        Fires all on_enter hooks for this node.
        Raises RuntimeError if any hook fails (triggers atomic rollback in transition_to).
        """
        for hook in self._on_enter_hooks:
            try:
                hook()
            except Exception as e:
                raise RuntimeError(
                    f"on_enter hook failure in node '{self.name}': {e}"
                ) from e

    def execute_on_exit(self) -> None:
        """
        Fires all on_exit hooks for this node.
        Raises RuntimeError if any hook fails (triggers atomic rollback in transition_to).
        """
        for hook in self._on_exit_hooks:
            try:
                hook()
            except Exception as e:
                raise RuntimeError(
                    f"on_exit hook failure in node '{self.name}': {e}"
                ) from e

    def __repr__(self) -> str:
        return f"HSMNode({self.get_full_path()}, category={self.category})"


class HierarchicalStateMachine:
    """
    Session-aware Hierarchical State Machine with History Nodes (H*).

    Manages:
        - State tree construction (super-states and sub-states per SDD-25 topology)
        - Validated transitions with IllegalHSMTransitionError on invalid paths
        - Deep History Node (H*) recording per session
        - Checkpoint persistence via AgnosticCheckpointer into fsm_checkpoints
        - MCPToolGovernor synchronization on every transition
        - Session resume from History Node or SQLite WAL fallback
    """

    def __init__(self, db_manager: Any, checkpointer: Any, mcp_governor: Any = None):
        self.db = db_manager
        self.checkpointer = checkpointer
        self.mcp_governor = mcp_governor

        # Build the hierarchical state tree
        self.root = HSMNode("ROOT")
        self._build_state_tree()

        # Deep History Node per session: {session_id: (full_state_path, checkpoint_id, timestamp)}
        self.history_nodes: Dict[str, Tuple[str, str, float]] = {}
        # Active state per session: {session_id: HSMNode}
        self.active_session_states: Dict[str, HSMNode] = {}

        logger.info("[HSM] Hierarchical State Machine initialized with %d super-states.",
                    len(self.root.substates))

    # ── State Tree Construction ─────────────────────────────────────

    def _build_state_tree(self) -> None:
        """
        Constructs the full HSM topology as defined in SDD-25 Section 3.2.

        Super-States: PLANNING, EXECUTION, MAINTENANCE, STALL, SUCCESS
        Each with their respective sub-states and MCP governance categories.
        """
        # Super-State: PLANNING (READ_ONLY)
        planning = self.root.add_substate("PLANNING", category="READ_ONLY")
        planning.add_substate("DISCOVERY", category="READ_ONLY")
        planning.add_substate("ARCHITECTURE", category="READ_ONLY")
        planning.add_substate("KANBAN_GEN", category="READ_ONLY")

        # Super-State: EXECUTION (LOCAL_MUTATION)
        execution = self.root.add_substate("EXECUTION", category="LOCAL_MUTATION")
        execution.add_substate("CODE_GEN", category="LOCAL_MUTATION")
        execution.add_substate("TDD_GREEN", category="LOCAL_MUTATION")
        execution.add_substate("REFACTORING", category="LOCAL_MUTATION")
        execution.add_substate("RE_INDEX", category="LOCAL_MUTATION")  # SDD-27: Stale file re-analysis

        # Super-State: MAINTENANCE (DANGEROUS)
        maint = self.root.add_substate("MAINTENANCE", category="DANGEROUS")
        maint.add_substate("PURGE_CACHE", category="DANGEROUS")
        maint.add_substate("RECONCILE", category="DANGEROUS")
        maint.add_substate("RESET_DB", category="DANGEROUS")

        # Super-State: STALL (READ_ONLY) — Agent pause states
        stall = self.root.add_substate("STALL", category="READ_ONLY")
        stall.add_substate("AWAITING_HUMAN", category="READ_ONLY")
        stall.add_substate("CONTEXT_FULL", category="READ_ONLY")
        stall.add_substate("ERROR_PAUSE", category="READ_ONLY")

        # Super-State: SUCCESS (READ_ONLY) — Terminal success
        success = self.root.add_substate("SUCCESS", category="READ_ONLY")
        success.add_substate("IDLE_COMPLETE", category="READ_ONLY")

    # ── Node Resolution ─────────────────────────────────────────────

    def resolve_node(self, full_path: str) -> Optional[HSMNode]:
        """
        Resolves a fully-qualified state path to its HSMNode.

        Supports paths like:
            - 'EXECUTION'           → super-state node
            - 'EXECUTION.TDD_GREEN' → sub-state node
            - 'PLANNING.DISCOVERY'  → sub-state node

        Returns None if the path cannot be resolved.
        """
        parts = full_path.split(".")
        current = self.root
        for part in parts:
            if part in current.substates:
                current = current.substates[part]
            elif current.name == part:
                continue
            else:
                return None
        return current

    # ── State Queries ───────────────────────────────────────────────

    def get_current_state(self, session_id: str) -> str:
        """Returns the fully-qualified active state path for a session."""
        node = self.active_session_states.get(session_id)
        if node:
            return node.get_full_path()
        return "PLANNING.DISCOVERY"  # Conservative safe fallback

    def get_super_state(self, session_id: str) -> str:
        """Returns only the super-state name for a session (e.g. 'EXECUTION')."""
        node = self.active_session_states.get(session_id)
        if node:
            if node.parent and node.parent.name != "ROOT":
                return node.parent.name
            return node.name
        return "PLANNING"

    def get_state_tree(self) -> Dict[str, Any]:
        """Returns the full state tree as a serializable dictionary."""
        def _node_to_dict(node: HSMNode) -> Dict[str, Any]:
            result: Dict[str, Any] = {
                "name": node.name,
                "category": node.category,
                "full_path": node.get_full_path(),
            }
            if node.substates:
                result["substates"] = {
                    name: _node_to_dict(child)
                    for name, child in node.substates.items()
                }
            return result

        return {
            name: _node_to_dict(child)
            for name, child in self.root.substates.items()
        }

    # ── Transition Engine ───────────────────────────────────────────

    def _get_ancestor_chain(self, node: Optional[HSMNode]) -> List[HSMNode]:
        """
        Returns the list [sub-state, super-state, ...] from node up to (excluding) ROOT.
        Used to compute hierarchical hook chains during transitions.
        """
        chain: List[HSMNode] = []
        current = node
        while current and current.name != "ROOT":
            chain.append(current)
            current = current.parent
        return chain

    def transition_to(
        self,
        session_id: str,
        target_path: str,
        agent_id: str,
        shared_state: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> bool:
        """
        Executes a hierarchical state transition with full persistence.

        Steps:
            1. Resolves and validates the target state path
            2. Fires on_exit hooks (sub-state first, then super-state) — SDD-27
            3. Fires on_enter hooks (super-state first, then sub-state) — SDD-27
            4. Updates the session's active state
            5. Synchronizes MCPToolGovernor with the super-state
            6. Persists a checkpoint in SQLite WAL via AgnosticCheckpointer
            7. Records the Deep History Node (H*) for the session

        If any lifecycle hook raises an exception, the transition is atomically
        rolled back: the previous state is restored and the HSM transitions to
        STALL.ERROR_PAUSE for safe governance logging.

        Args:
            session_id: Unique session identifier
            target_path: Fully-qualified target state (e.g. 'EXECUTION.TDD_GREEN')
            agent_id: Agent performing the transition
            shared_state: Context variables to persist with the checkpoint
            task_id: Optional task file identifier for dirty-marking on restore

        Returns:
            True if transition and checkpoint succeeded, False otherwise.

        Raises:
            IllegalHSMTransitionError: If target_path cannot be resolved.
        """
        target_node = self.resolve_node(target_path)
        if not target_node:
            raise IllegalHSMTransitionError(
                f"Invalid qualified state path: '{target_path}'"
            )

        # Record previous state for logging and rollback
        previous_node = self.active_session_states.get(session_id)
        previous_path = self.get_current_state(session_id)

        # ── SDD-27: Lifecycle Hook Firing ───────────────────────────────
        # Compute exit chain (old sub -> old super) and enter chain (new super -> new sub)
        old_chain = self._get_ancestor_chain(previous_node)  # [sub, super, ...]
        new_chain = self._get_ancestor_chain(target_node)     # [sub, super, ...]

        # Determine shared ancestor to avoid firing hooks on unchanged ancestors
        old_set = set(id(n) for n in old_chain)
        new_set = set(id(n) for n in new_chain)

        exit_nodes = [n for n in old_chain if id(n) not in new_set]   # sub-first
        enter_nodes = [n for n in new_chain if id(n) not in old_set]  # sub-first
        enter_nodes.reverse()  # super-first for entry

        try:
            # Fire on_exit hooks: sub-state first, then super-state (ascending)
            for node in exit_nodes:
                node.execute_on_exit()
            # Fire on_enter hooks: super-state first, then sub-state (descending)
            for node in enter_nodes:
                node.execute_on_enter()
        except RuntimeError as hook_err:
            # Atomic Rollback: Restore previous state and park in STALL.ERROR_PAUSE
            logger.error(
                "[HSM] Hook failure during transition %s -> %s: %s. Rolling back.",
                previous_path, target_path, hook_err,
            )
            if previous_node:
                self.active_session_states[session_id] = previous_node
            error_node = self.resolve_node("STALL.ERROR_PAUSE")
            if error_node:
                self.active_session_states[session_id] = error_node
            return False

        # Update active session state
        self.active_session_states[session_id] = target_node
        full_path = target_node.get_full_path()

        # Derive super-state for MCPToolGovernor
        super_state = target_node.parent.name if (target_node.parent and target_node.parent.name != "ROOT") else target_node.name

        # Synchronize MCPToolGovernor if coupled
        if self.mcp_governor:
            self.mcp_governor.set_session_state(session_id, super_state)

        # Generate deterministic checkpoint_id based on timestamp
        checkpoint_id = f"cp_hsm_{int(time.time() * 1000)}"

        # Persist full checkpoint to SQLite WAL via AgnosticCheckpointer
        saved = self.checkpointer.save_checkpoint(
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            agent_id=agent_id,
            state_name=full_path,
            shared_state=shared_state,
            task_id=task_id,
        )

        if saved:
            # Record Deep History Node (H*) for the session
            self.history_nodes[session_id] = (full_path, checkpoint_id, time.time())
            logger.info(
                "[HSM] Transition %s -> %s (session=%s, checkpoint=%s)",
                previous_path, full_path, session_id, checkpoint_id,
            )
            return True

        logger.error(
            "[HSM] Checkpoint persistence failed for transition to '%s' (session=%s)",
            full_path, session_id,
        )
        return False

    # ── History Node Resume ─────────────────────────────────────────

    def resume_from_history_node(
        self, session_id: str, delta_manager: Any = None
    ) -> Optional[Dict[str, Any]]:
        """
        Restores a session to its exact sub-state using the Deep History Node (H*).

        Resolution order:
            1. In-memory history_nodes dict (fast path)
            2. SQLite WAL fallback: queries fsm_checkpoints for latest checkpoint

        SDD-27 Delta Validation:
            If delta_manager is provided and the checkpoint's task_id references a
            file whose mtime is newer than the checkpoint's created_at, the delta
            manager is asked whether the change is structural. If so, the session
            is redirected to EXECUTION.RE_INDEX (or EXECUTION.CODE_GEN fallback)
            with stale_detected=True in shared_state.

        On successful restore:
            - Active session state is set to the restored node
            - MCPToolGovernor is synchronized with the restored super-state

        Returns:
            Restored checkpoint dict with state_name, shared_state, etc.
            None if no history could be found.
        """
        history = self.history_nodes.get(session_id)
        created_at = None
        task_id_from_db = None

        if not history:
            # Fallback: query SQLite WAL for latest checkpoint
            query = """
                SELECT checkpoint_id, state_name, created_at, task_id
                FROM fsm_checkpoints
                WHERE session_id = ?
                ORDER BY created_at DESC LIMIT 1;
            """
            rows = self.db.read_query(query, (session_id,))
            if not rows:
                logger.warning(
                    "[HSM] No History Node found for session '%s'.", session_id
                )
                return None
            checkpoint_id, state_name = rows[0][0], rows[0][1]
            created_at = rows[0][2] if len(rows[0]) > 2 else None
            task_id_from_db = rows[0][3] if len(rows[0]) > 3 else None
            full_path = state_name
        else:
            full_path, checkpoint_id, timestamp = history
            created_at = timestamp

        # Restore mental state through AgnosticCheckpointer
        restored = self.checkpointer.load_checkpoint(session_id, checkpoint_id)
        if not restored:
            logger.error(
                "[HSM] Checkpoint load failed for session '%s' (checkpoint=%s)",
                session_id, checkpoint_id,
            )
            return None

        # ── SDD-27: Delta Validation on Resume ─────────────────────────
        target_task_id = task_id_from_db or restored.get("task_id")
        is_stale = False

        if delta_manager and target_task_id and created_at is not None:
            try:
                if os.path.exists(target_task_id):
                    file_mtime = os.path.getmtime(target_task_id)
                    # Checkpoint is older than file on disk
                    if file_mtime > float(created_at):
                        if delta_manager.has_structural_change(target_task_id):
                            is_stale = True
                            logger.warning(
                                "[HSM] Stale file detected for session '%s': "
                                "file '%s' mtime (%.2f) > checkpoint created_at (%.2f).",
                                session_id, target_task_id, file_mtime, float(created_at),
                            )
            except (OSError, ValueError) as e:
                logger.error("[HSM] Delta validation error: %s", e)

        if is_stale:
            # Redirect to RE_INDEX sub-state for AST re-analysis
            reindex_node = self.resolve_node("EXECUTION.RE_INDEX")
            target_node = reindex_node or self.resolve_node("EXECUTION.CODE_GEN")
            restored["shared_state"]["stale_detected"] = True
            restored["shared_state"]["original_state"] = full_path
            logger.info(
                "[HSM] Session '%s' redirected to '%s' due to stale file delta.",
                session_id, target_node.get_full_path() if target_node else "UNKNOWN",
            )
        else:
            target_node = self.resolve_node(full_path)

        if target_node:
            self.active_session_states[session_id] = target_node
            # Synchronize MCPToolGovernor with restored super-state
            super_name = None
            if target_node.parent and target_node.parent.name != "ROOT":
                super_name = target_node.parent.name
            if self.mcp_governor and super_name:
                self.mcp_governor.set_session_state(session_id, super_name)
            logger.info(
                "[HSM] Session '%s' restored to '%s' from History Node.",
                session_id, target_node.get_full_path(),
            )

        return restored

    # ── Session Introspection ───────────────────────────────────────

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Returns a summary of all active sessions and their states."""
        result = {}
        for session_id, node in self.active_session_states.items():
            history = self.history_nodes.get(session_id)
            result[session_id] = {
                "current_state": node.get_full_path(),
                "super_state": node.parent.name if (node.parent and node.parent.name != "ROOT") else node.name,
                "category": node.category,
                "has_history_node": history is not None,
                "history_checkpoint_id": history[1] if history else None,
                "history_timestamp": history[2] if history else None,
            }
        return result
