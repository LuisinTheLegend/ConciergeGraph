import os

file_path = r"core\graph_rag.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_start = """    def get_call_chain_recursive(
        self,
        start_node: str,
        depth_limit: int = 5,
        project_identifier: Optional[str] = None,
    ) -> List[str]:"""

# We will replace from target_start up to the return of get_call_chain_recursive
idx_start = content.find(target_start)
assert idx_start != -1, "target_start not found"

target_end = """        return result_list"""
idx_end = content.find(target_end, idx_start)
assert idx_end != -1, "target_end not found"
idx_end += len(target_end)

new_func = """    def get_call_chain_recursive(
        self,
        start_node: str,
        depth_limit: int = 5,
        project_identifier: Optional[str] = None,
    ) -> List[str]:
        \"\"\"
        Executes recursive traversal across canonical 'edges' and 'nodes' tables in SQLite WAL.

        Root selection behavior:
          - File start (e.g. 'src/core.py'): root is the module node (label = path) plus all
            symbol nodes prefixed with 'path::'. Exact substring comparison avoids LIKE wildcard collisions.
          - Symbol start (e.g. 'src/core.py::my_func'): root is only the exact symbol node matching label.

        Traversal & Filtering:
          - Follows active relations: relation_type = 'calls', valid_to_commit IS NULL, status = 'ACTIVE'.
          - Scope is strictly confined to a single project (no cross-project leakage).
          - Cycle protection: tracked by visited node IDs; traversal continues through symbols of the
            origin file, but the origin file path itself is strictly excluded from returned results.
          - Deterministic order: sorted by traversal depth ASC, then alphabetically by path ASC.

        Args:
            start_node: Relative file path (e.g. 'src/core.py') or symbol ('src/core.py::my_func').
            depth_limit: Maximum traversal recursion depth (integer between 1 and 10). Rejects boolean.
            project_identifier: Optional project UUID or unique folder_name. Required if start_node exists in multiple projects.

        Returns:
            List of connected child file paths, ordered by depth ASC, then path ASC.

        Raises:
            ValueError: If depth_limit is invalid/boolean, if project_identifier is not found,
                        if start_node is not found, if folder_name is ambiguous across multiple projects,
                        or if start_node is ambiguous across projects.
        \"\"\"
        if isinstance(depth_limit, bool) or not isinstance(depth_limit, int) or depth_limit < 1 or depth_limit > 10:
            raise ValueError(f"Invalid depth_limit: {depth_limit}. Must be an integer between 1 and 10.")

        norm_start = start_node.replace(\"\\\\\", \"/\").strip()
        if not norm_start:
            raise ValueError("start_node cannot be empty.")

        is_symbol_start = \"::\" in norm_start
        origin_path = norm_start.split(\"::\")[0] if is_symbol_start else norm_start

        # 1. Resolve project_uuid if project_identifier is provided
        target_project_uuid: Optional[str] = None
        if project_identifier:
            uuid_rows = self.db.read_query(
                \"SELECT uuid FROM projects WHERE uuid = ?;\",
                (project_identifier,),
            )
            if uuid_rows:
                target_project_uuid = uuid_rows[0][0]
            else:
                folder_rows = self.db.read_query(
                    \"SELECT uuid FROM projects WHERE folder_name = ?;\",
                    (project_identifier,),
                )
                if not folder_rows:
                    raise ValueError(f\"Project '{project_identifier}' not found.\")
                if len(folder_rows) > 1:
                    raise ValueError(
                        f\"Multiple projects ({len(folder_rows)}) share folder_name '{project_identifier}'. \"
                        \"Please specify the project by its unique UUID.\"
                    )
                target_project_uuid = folder_rows[0][0]

        # 2. Locate matching active start node(s)
        if target_project_uuid:
            if is_symbol_start:
                nodes_rows = self.db.read_query(
                    \"SELECT id, project_uuid, label \"
                    \"FROM nodes \"
                    \"WHERE project_uuid = ? \"
                    \"  AND status = 'ACTIVE' \"
                    \"  AND valid_to_commit IS NULL \"
                    \"  AND label = ?;\",
                    (target_project_uuid, norm_start),
                )
            else:
                nodes_rows = self.db.read_query(
                    \"SELECT id, project_uuid, label \"
                    \"FROM nodes \"
                    \"WHERE project_uuid = ? \"
                    \"  AND status = 'ACTIVE' \"
                    \"  AND valid_to_commit IS NULL \"
                    \"  AND (label = ? OR (substr(label, 1, ?) = ?));\",
                    (target_project_uuid, norm_start, len(norm_start) + 2, f\"{norm_start}::\"),
                )
        else:
            if is_symbol_start:
                nodes_rows = self.db.read_query(
                    \"SELECT n.id, n.project_uuid, n.label \"
                    \"FROM nodes n \"
                    \"JOIN projects p ON n.project_uuid = p.uuid \"
                    \"WHERE n.status = 'ACTIVE' \"
                    \"  AND n.valid_to_commit IS NULL \"
                    \"  AND n.label = ?;\",
                    (norm_start,),
                )
            else:
                nodes_rows = self.db.read_query(
                    \"SELECT n.id, n.project_uuid, n.label \"
                    \"FROM nodes n \"
                    \"JOIN projects p ON n.project_uuid = p.uuid \"
                    \"WHERE n.status = 'ACTIVE' \"
                    \"  AND n.valid_to_commit IS NULL \"
                    \"  AND (n.label = ? OR (substr(n.label, 1, ?) = ?));\",
                    (norm_start, len(norm_start) + 2, f\"{norm_start}::\"),
                )

        if not nodes_rows:
            raise ValueError(f\"Start node '{start_node}' not found.\")

        # 3. Handle project ambiguity if project_identifier was not passed
        if not target_project_uuid:
            projects_found = set(r[1] for r in nodes_rows)
            if len(projects_found) > 1:
                raise ValueError(
                    f\"Ambiguous start_node '{start_node}' found in {len(projects_found)} projects. \"
                    \"Please specify project_identifier (use concierge_list_projects to view projects).\"
                )
            target_project_uuid = list(projects_found)[0]

        root_node_ids = [r[0] for r in nodes_rows if r[1] == target_project_uuid]

        # 4. BFS Traversal with cycle protection and active calls filter
        visited_node_ids: Set[int] = set(root_node_ids)
        depth_results: Dict[int, Set[str]] = {}
        current_level_node_ids: List[int] = list(root_node_ids)

        for current_depth in range(1, depth_limit + 1):
            if not current_level_node_ids:
                break

            placeholders = \",\".join(\"?\" for _ in current_level_node_ids)
            query = f\"\"\"
                SELECT e.target_id, n.label
                FROM edges e
                JOIN nodes n ON e.target_id = n.id
                WHERE e.source_id IN ({placeholders})
                  AND e.relation_type = 'calls'
                  AND e.valid_to_commit IS NULL
                  AND n.status = 'ACTIVE'
                  AND n.valid_to_commit IS NULL
                  AND n.project_uuid = ?;
            \"\"\"
            params = list(current_level_node_ids) + [target_project_uuid]
            edge_rows = self.db.read_query(query, tuple(params))

            next_level_node_ids = []
            for target_id, label in edge_rows:
                if target_id in visited_node_ids:
                    continue
                visited_node_ids.add(target_id)
                next_level_node_ids.append(target_id)

                path = label.split(\"::\")[0] if \"::\" in label else label
                if path != origin_path:
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
                    if p not in seen_paths and p != origin_path:
                        seen_paths.add(p)
                        result_list.append(p)

        return result_list"""

new_content = content[:idx_start] + new_func + content[idx_end:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated core/graph_rag.py successfully.")

