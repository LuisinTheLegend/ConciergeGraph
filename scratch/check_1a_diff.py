import difflib

with open("audits/relatorio_4_3.md", "r", encoding="utf-8") as f:
    existing = f.read()

p0_head = "57ff33d36de400edc0eee03e385922f31357f664"
p0_ls_remote = "57ff33d36de400edc0eee03e385922f31357f664"

with open("scratch/build_relatorio_4_3.py", "r", encoding="utf-8") as f:
    code = f.read()

start_marker = 'doc = f"""'
end_marker = '"""\n\n    report_path'
s_idx = code.find(start_marker) + len(start_marker)
e_idx = code.find(end_marker)
doc_template = code[s_idx:e_idx]
generated = doc_template.replace("{p0_head}", p0_head).replace("{p0_ls_remote}", p0_ls_remote)

# Normalize line endings
existing_lines = [l.strip() for l in existing.splitlines() if l.strip()]
gen_lines = [l.strip() for l in generated.splitlines() if l.strip()]

diff = list(difflib.unified_diff(
    existing_lines,
    gen_lines,
    fromfile="audits/relatorio_4_3.md",
    tofile="build_relatorio_4_3.py:doc",
    lineterm=""
))

print("Diff count:", len(diff))
if not diff:
    print("EXACT MATCH! audits/relatorio_4_3.md is verbatim identical to build_relatorio_4_3.py template.")
    msg = "EXACT MATCH! audits/relatorio_4_3.md matches build_relatorio_4_3.py doc string verbatim.\n"
else:
    print("Diff found:")
    for d in diff[:20]:
        print(d)
    msg = "\n".join(diff) + "\n"

with open("scratch/evidencia_4_3c/item1a_diff_build_relatorio_4_3.txt", "w", encoding="utf-8") as f:
    f.write(msg)
