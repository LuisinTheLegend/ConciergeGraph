import subprocess

cmds = [
    ("grep_resolve_relatorio_4_3", "git grep -n -E \"_resolve_project_identifier|ConciergeFacade\" audits/relatorio_4_3.md"),
    ("grep_concierge_facade_all", "git grep -n \"ConciergeFacade\""),
    ("grep_resolve_project_identifier_mcp", "git grep -n -C 5 \"def _resolve_project_identifier\" interface/mcp_server.py"),
    ("grep_depth_limit_code", "git grep -n -C 5 \"isinstance(depth_limit\" core/graph_rag.py")
]

out = []
for name, cmd in cmds:
    out.append(f"=== {name} ===\n$ {cmd}\n")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    out.append(res.stdout + res.stderr + "\n")

with open("scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt", "w", encoding="utf-8") as f:
    f.write("".join(out))
print("Saved item1b_resolve_project_identifier_greps.txt successfully")
