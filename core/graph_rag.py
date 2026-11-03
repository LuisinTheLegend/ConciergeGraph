"""
core/graph_rag.py — SDD-SURVIVAL-06 / SDD-SURVIVAL-17

Heuristic Community Detection and Multi-Hop Search (Frugal GraphRAG).

Implements two zero-computational-overhead strategies for local GraphRAG:

  1. Topological Mapping: The immediate parent directory of a file is assumed
     to be its natural community partition (zero RAM network clustering overhead).

  2. Relational Multi-Hop via Recursive CTE: Traverses the method and import call
     tree (ast_edges) directly inside SQLite WAL in sub-milliseconds,
     without loading whole graphs into process memory.
"""

import os
from typing import Any, Dict, List, Optional, Set


class GraphRAGEngine:
    """
    Frugal graph engine that partitions communities via directory topology
    and resolves dependency chains via recursive CTEs in SQLite WAL.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager
        self.db = db_manager

    def _get_edge_columns(self) -> tuple[str, str]:
        """Dynamically detects whether ast_edges uses parent_node_id or parent_node."""
        try:
            rows = self.db.read_query("PRAGMA table_info(ast_edges);")
            cols = [r[1] for r in rows]
            if "parent_node_id" in cols:
                return "parent_node_id", "child_node_id"
            if "parent_node" in cols:
                return "parent_node", "child_node"
        except Exception:
            pass
        return "parent_node_id", "child_node_id"

    # ── Recursive Multi-Hop Traversal (SDD-17) ─────────────────────

    def retrieve_multihop_context(
        self, entry_node: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Returns full structural context around a source file,
        recursively navigating AST dependencies inside SQLite WAL.
        """
        if max_depth <= 1:
            nodes_info = []
            try:
                nodes_rows = self.db.read_query(
                    "SELECT path, community_id, is_dirty FROM files WHERE path = ?;",
                    (entry_node,),
                )
                for r in nodes_rows:
                    nodes_info.append({
                        "path": r[0],
                        "community_id": r[1],
                        "is_dirty": r[2],
                    })
            except Exception:
                pass
            return {
                "entry_node": entry_node,
                "connected_nodes": nodes_info,
                "relations": [],
                "total_hops": max_depth,
            }

        parent_col, child_col = self._get_edge_columns()
        max_hops = max_depth - 1

        query = f"""
            WITH RECURSIVE CallChain AS (
                SELECT 
                    {parent_col}, 
                    {child_col}, 
                    1 as depth,
                    '|' || {parent_col} || '|' || {child_col} || '|' as path_visited
                FROM ast_edges
                WHERE {parent_col} = ?
                
                UNION ALL
                
                SELECT 
                    e.{parent_col}, 
                    e.{child_col}, 
                    c.depth + 1,
                    c.path_visited || e.{child_col} || '|' as path_visited
                FROM ast_edges e
                INNER JOIN CallChain c ON e.{parent_col} = c.{child_col}
                WHERE c.depth < ?
                  AND instr(c.path_visited, '|' || e.{child_col} || '|') = 0
            )
            SELECT DISTINCT {parent_col}, {child_col}, depth 
            FROM CallChain;
        """

        try:
            rows = self.db.read_query(query, (entry_node, max_hops))
        except Exception as e:
            # Fallback if ast_edges table does not exist or fails
            return {"entry": entry_node, "nodes": [], "edges": [], "error": str(e)}

        visited_nodes: Set[str] = {entry_node}
        edges_list: List[Dict[str, Any]] = []

        for row in rows:
            parent, child, depth = row
            visited_nodes.add(parent)
            visited_nodes.add(child)
            edges_list.append({
                "source": parent,
                "target": child,
                "depth": depth,
            })

        # Retrieve file metadata for visited nodes to assemble context payload
        nodes_info = []
        if visited_nodes:
            placeholders = ",".join(["?"] * len(visited_nodes))
            nodes_query = f"SELECT path, community_id, is_dirty FROM files WHERE path IN ({placeholders});"
            try:
                nodes_rows = self.db.read_query(nodes_query, tuple(visited_nodes))
                for r in nodes_rows:
                    nodes_info.append({
                        "path": r[0],
                        "community_id": r[1],
                        "is_dirty": r[2],
                    })
            except Exception:
                pass

        return {
            "entry_node": entry_node,
            "connected_nodes": nodes_info,
            "relations": edges_list,
            "total_hops": max_depth,
        }

    # ── Topological Mapping ────────────────────────────────────────

    def get_natural_community(self, file_path: str) -> str:
        """
        Extracts immediate parent directory of file as its natural community.

        Computational cost: O(1) string operation.
        Examples:
          - 'core/utils/delta.py' -> 'core/utils'
          - 'main.py'             -> 'root'
        """
        parent = os.path.dirname(file_path.replace("\\", "/"))
        return parent if parent else "root"

    # ── Multi-Hop via Recursive CTE ────────────────────────────────

    def get_call_chain_recursive(
        self,
        start_node: str,
        depth_limit: int = 5,
        project_identifier: Optional[str] = None,
    ) -> List[str]:
        """
        Executes recursive traversal across canonical 'edges' and 'nodes' tables in SQLite WAL.

        Follows relations where relation_type = 'calls', valid_to_commit IS NULL and status = 'ACTIVE'.
        Scope is strictly confined to a single project (no cross-project leakage).
        Cycle-safe via visited set tracking.
        Deterministic order: sorted by traversal depth ASC, then alphabetically by path ASC.
        Excludes the root start node file path from the results.

        Note: Call edges are extracted from AST parsers based on symbol names (confidence_tag='EXTRACTED'),
        not full static type checking; name collisions between functions in different files may cause false positives.

        Args:
            start_node: Relative file path (e.g. 'src/core.py') or symbol ('src/core.py::my_func').
            depth_limit: Maximum traversal recursion depth (1 to 10). Default: 5.
            project_identifier: Optional project UUID or folder_name. Required if start_node exists in multiple projects.

        Returns:
            List of connected child file paths, ordered by depth ASC, then path ASC.

        Raises:
            ValueError: If depth_limit is out of range, if project_identifier is not found,
                        if start_node is not found, or if start_node is ambiguous across projects.
        """
        if not isinstance(depth_limit, int) or depth_limit < 1 or depth_limit > 10:
            raise ValueError(f"Invalid depth_limit: {depth_limit}. Must be an integer between 1 and 10.")

        norm_start = start_node.replace("\\", "/").strip()
        if not norm_start:
            raise ValueError("start_node cannot be empty.")

        # 1. Resolve project_uuid if project_identifier is provided
        target_project_uuid: Optional[str] = None
        if project_identifier:
            p_rows = self.db.read_query(
                "SELECT uuid FROM projects WHERE uuid = ? OR folder_name = ?;",
                (project_identifier, project_identifier),
            )
            if not p_rows:
                raise ValueError(f"Project '{project_identifier}' not found.")
            target_project_uuid = p_rows[0][0]

        # 2. Locate matching active start node(s)
        if target_project_uuid:
            nodes_rows = self.db.read_query(
                "SELECT id, project_uuid, label "
                "FROM nodes "
                "WHERE project_uuid = ? "
                "  AND status = 'ACTIVE' "
                "  AND valid_to_commit IS NULL "
                "  AND (label = ? OR label LIKE ?);",
                (target_project_uuid, norm_start, f"{norm_start}::%"),
            )
        else:
            nodes_rows = self.db.read_query(
                "SELECT n.id, n.project_uuid, n.label, p.folder_name "
                "FROM nodes n "
                "JOIN projects p ON n.project_uuid = p.uuid "
                "WHERE n.status = 'ACTIVE' "
                "  AND n.valid_to_commit IS NULL "
                "  AND (n.label = ? OR n.label LIKE ?);",
                (norm_start, f"{norm_start}::%"),
            )

        if not nodes_rows:
            raise ValueError(f"Start node '{start_node}' not found.")

        # 3. Handle project ambiguity if project_identifier was not passed
        if not target_project_uuid:
            projects_found = {}
            for r in nodes_rows:
                p_uuid = r[1]
                p_folder = r[3] if len(r) > 3 else p_uuid
                projects_found[p_uuid] = p_folder

            if len(projects_found) > 1:
                candidates_str = ", ".join(f"'{folder}' ({uuid_})" for uuid_, folder in sorted(projects_found.items()))
                raise ValueError(
                    f"Ambiguous start_node '{start_node}' found in multiple projects: [{candidates_str}]. "
                    f"Please specify project_identifier."
                )
            target_project_uuid = list(projects_found.keys())[0]

        root_node_ids = [r[0] for r in nodes_rows if r[1] == target_project_uuid]
        root_paths = set()
        for r in nodes_rows:
            if r[1] == target_project_uuid:
                p = r[2].split("::")[0] if "::" in r[2] else r[2]
                root_paths.add(p)
        root_paths.add(norm_start.split("::")[0])

        # 4. BFS Traversal with cycle protection and active calls filter
        visited_node_ids: Set[int] = set(root_node_ids)
        depth_results: Dict[int, Set[str]] = {}
        current_level_node_ids: List[int] = list(root_node_ids)

        for current_depth in range(1, depth_limit + 1):
            if not current_level_node_ids:
                break

            placeholders = ",".join("?" for _ in current_level_node_ids)
            query = f"""
                SELECT e.target_id, n.label
                FROM edges e
                JOIN nodes n ON e.target_id = n.id
                WHERE e.source_id IN ({placeholders})
                  AND e.relation_type = 'calls'
                  AND e.valid_to_commit IS NULL
                  AND n.status = 'ACTIVE'
                  AND n.valid_to_commit IS NULL
                  AND n.project_uuid = ?;
            """
            params = list(current_level_node_ids) + [target_project_uuid]
            edge_rows = self.db.read_query(query, tuple(params))

            next_level_node_ids = []
            for target_id, label in edge_rows:
                if target_id in visited_node_ids:
                    continue
                visited_node_ids.add(target_id)
                next_level_node_ids.append(target_id)

                path = label.split("::")[0] if "::" in label else label
                if current_depth not in depth_results:
                    depth_results[current_depth] = set()
                depth_results[current_depth].add(path)

            current_level_node_ids = next_level_node_ids

        # 5. Deterministic ordering: depth ASC, then path ASC
        result_list: List[str] = []
        seen_paths: Set[str] = set()
        for d in range(1, depth_limit + 1):
            if d in depth_results:
                for p in sorted(depth_results[d]):
                    if p not in seen_paths:
                        seen_paths.add(p)
                        result_list.append(p)

        return result_list

    # ── Community Detection with Super-Node Filtering (SDD-14) ─────

    def detect_logical_communities(
        self, in_degree_threshold: int = 5
    ) -> dict:
        """
        Groups repository files into communities based on AST coupling
        proximity, filtering out super-nodes (global hubs).

        Algorithm:
          1. Computes in-degree for each node in ast_edges table
          2. Nodes with in-degree > in_degree_threshold are classified
             as Super-Nodes and omitted as bridge transitions
          3. Clean edges (excluding super-nodes) are grouped via Union-Find
             into independent connected components
          4. Super-nodes receive directory satellite fallback (hub_satellite_{dir})

        Returns dict: {community_key: [file_paths]}
        """
        # 1. Identify super-nodes (global hubs) by in-degree
        supernodes_rows = self.db_manager.read_query(
            "SELECT child_node, COUNT(*) as in_degree "
            "FROM ast_edges "
            "GROUP BY child_node "
            "HAVING in_degree > ?;",
            (in_degree_threshold,),
        )
        supernodes = {r[0] for r in supernodes_rows}

        # 2. Query clean edges (excluding super-nodes as bridges)
        all_edges = self.db_manager.read_query(
            "SELECT parent_node, child_node FROM ast_edges;"
        )
        filtered_edges = [
            (parent, child)
            for parent, child in all_edges
            if parent not in supernodes and child not in supernodes
        ]

        # 3. Grouping into Connected Components (Union-Find)
        parent_map: dict = {}

        def find(node: str) -> str:
            if parent_map.setdefault(node, node) != node:
                parent_map[node] = find(parent_map[node])
            return parent_map[node]

        def union(node1: str, node2: str) -> None:
            root1 = find(node1)
            root2 = find(node2)
            if root1 != root2:
                parent_map[root1] = root2

        for parent, child in filtered_edges:
            union(parent, child)

        # 4. Group files by community
        all_files = [
            r[0] for r in self.db_manager.read_query("SELECT path FROM files;")
        ]

        communities: dict = {}
        for file_path in all_files:
            if file_path in supernodes:
                # Super-node -> local directory satellite (L2/L1 fallback)
                dir_name = "/".join(file_path.replace("\\", "/").split("/")[:-1]) or "root"
                community_key = f"hub_satellite_{dir_name}"
            else:
                community_key = f"community_{find(file_path)}"

            communities.setdefault(community_key, []).append(file_path)

        return communities
