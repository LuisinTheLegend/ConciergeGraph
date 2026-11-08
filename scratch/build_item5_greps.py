import subprocess

cmds = [
    ("grep_relatorio_4_3_line23", "git grep -n \"project_id\" audits/relatorio_4_3.md"),
    ("grep_relatorio_4_3_symbol_path", "git grep -n \"symbol_or_path\" audits/relatorio_4_3.md"),
    ("grep_call_chain_signature_mcp", "git grep -n -C 5 \"def tool_concierge_get_call_chain\" interface/mcp_server.py"),
    ("grep_call_chain_signature_core", "git grep -n -C 5 \"def get_call_chain_recursive\" core/graph_rag.py"),
    ("grep_privacy_level_core", "git grep -n \"privacy_level\" core/graph_rag.py"),
    ("grep_privacy_level_all_core", "git grep -n \"privacy_level\" core/"),
    ("grep_full_suite_mention_relatorio_4_3", "git grep -n \"pytest tests\" audits/relatorio_4_3.md"),
    ("generator_script_check", "git status --short scratch/build_relatorio_4_3.py")
]

out = []
for name, cmd in cmds:
    out.append(f"=== {name} ===\n$ {cmd}\n")
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
        out.append(res.stdout + res.stderr + "\n")
    except Exception as e:
        out.append(f"ERROR: {e}\n")

with open("scratch/evidencia_4_3b/item5_errata_greps.txt", "w", encoding="utf-8") as f:
    f.write("".join(out))
print("Saved item5_errata_greps.txt successfully")

