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
from typing import Any, Dict, List, Set


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
        self, start_node: str, depth_limit: int = 5
    ) -> List[str]:
        """
        Executes recursive traversal across ast_edges table in SQLite WAL
        using WITH RECURSIVE, returning all child nodes connected to root
        up to specified depth limit.

        Excludes the root node from response — returns only transitive dependencies.
        Disconnected subgraphs are automatically ignored.
        """
        rows = self.db_manager.read_query(
            "WITH RECURSIVE call_chain(node, depth, path_visited) AS ("
            "  SELECT ? AS node, 0 AS depth, '|' || ? || '|' AS path_visited"
            "  UNION ALL"
            "  SELECT e.child_node AS node,"
            "         cc.depth + 1 AS depth,"
            "         cc.path_visited || e.child_node || '|' AS path_visited"
            "  FROM ast_edges e"
            "  JOIN call_chain cc ON e.parent_node = cc.node"
            "  WHERE cc.depth < ?"
            "    AND instr(cc.path_visited, '|' || e.child_node || '|') = 0"
            ") SELECT DISTINCT node, depth FROM call_chain WHERE node != ?;",
            (start_node, start_node, depth_limit, start_node),
        )
        return [row[0] for row in rows]

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
