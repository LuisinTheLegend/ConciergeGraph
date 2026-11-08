import subprocess
import sys
import os

graph_rag_file = r"core\graph_rag.py"

with open(graph_rag_file, "r", encoding="utf-8") as f:
    clean_code = f.read()

def run_mutation(mut_name, mutated_code, test_target, out_file):
    print(f"\n--- Running Mutation: {mut_name} ---")
    assert mutated_code != clean_code, f"Mutation {mut_name} did not change code!"
    with open(graph_rag_file, "w", encoding="utf-8") as f:
        f.write(mutated_code)
    try:
        cmd = [sys.executable, "-m", "pytest", "-v", test_target]
        res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(res.stdout + "\n" + res.stderr)
        print(f"Exit code: {res.returncode}")
        assert res.returncode != 0, f"Mutation {mut_name} was NOT killed!"
        print(f"Mutation {mut_name} successfully killed.")
    finally:
        with open(graph_rag_file, "w", encoding="utf-8") as f:
            f.write(clean_code)

# 1. Mutação 1: voltar a incluir o arquivo de origem
mut1 = clean_code.replace(
    "                if path != origin_path:",
    "                if True:"
).replace(
    "if p not in seen_paths and p != origin_path:",
    "if p not in seen_paths:"
)
run_mutation(
    "include_origin_file",
    mut1,
    "tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_symbol_start_excludes_origin_file_but_traverses_intrafile_callees",
    "scratch/evidencia_4_3b/b2_mutation_include_origin_file.txt"
)

# 2. Mutação 2: voltar a usar LIKE sem escape
mut2 = clean_code.replace(
    'AND (label = ? OR (substr(label, 1, ?) = ?));",\n                    (target_project_uuid, norm_start, len(norm_start) + 2, f"{norm_start}::"),',
    'AND (label = ? OR label LIKE ?);",\n                    (target_project_uuid, norm_start, f"{norm_start}::%"),'
).replace(
    'AND (n.label = ? OR (substr(n.label, 1, ?) = ?));",\n                    (norm_start, len(norm_start) + 2, f"{norm_start}::"),',
    'AND (n.label = ? OR n.label LIKE ?);",\n                    (norm_start, f"{norm_start}::%"),'
)
run_mutation(
    "unescaped_like",
    mut2,
    "tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_paths_with_wildcards_underscore_percent_and_backslash",
    "scratch/evidencia_4_3b/b2_mutation_unescaped_like.txt"
)

# 3. Mutação 3: remover a ambiguidade por folder_name
mut3 = clean_code.replace(
    '                if len(folder_rows) > 1:\n                    raise ValueError(\n                        f"Multiple projects ({len(folder_rows)}) share folder_name \'{project_identifier}\'. "\n                        "Please specify the project by its unique UUID."\n                    )\n                target_project_uuid = folder_rows[0][0]',
    '                target_project_uuid = folder_rows[0][0]'
)
run_mutation(
    "remove_folder_ambiguity",
    mut3,
    "tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_duplicate_folder_name_raises_ambiguity_error",
    "scratch/evidencia_4_3b/b2_mutation_remove_folder_ambiguity.txt"
)

# 4. Mutação 4: reintroduzir nomes/UUIDs na mensagem
mut4 = clean_code.replace(
    '                    f"Ambiguous start_node \'{start_node}\' found in {len(projects_found)} projects. "\n                    "Please specify project_identifier (use concierge_list_projects to view projects)."',
    '                    f"Ambiguous start_node \'{start_node}\' found in multiple projects: {list(projects_found)}. "\n                    "Please specify project_identifier."'
)
run_mutation(
    "leak_names_uuids",
    mut4,
    "tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_ambiguity_message_does_not_contain_names_or_uuids",
    "scratch/evidencia_4_3b/b2_mutation_leak_names_uuids.txt"
)

# 5. Mutação 5: aceitar bool em depth_limit
mut5 = clean_code.replace(
    "if isinstance(depth_limit, bool) or not isinstance(depth_limit, int) or depth_limit < 1 or depth_limit > 10:",
    "if not isinstance(depth_limit, int) or depth_limit < 1 or depth_limit > 10:"
)
run_mutation(
    "accept_bool",
    mut5,
    "tests/test_call_chain_edges_nodes.py::TestCallChainEdgesNodes::test_invalid_depth_limit_raises_clear_error",
    "scratch/evidencia_4_3b/b2_mutation_accept_bool.txt"
)

print("\nALL 5 MUTATIONS COMPLETED AND KILLED!")

