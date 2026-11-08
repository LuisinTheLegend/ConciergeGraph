file_path = r"tests\test_call_chain_edges_nodes.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

if lines and lines[-1].strip() == '"""':
    lines.pop()

# Fix raw docstrings
content = "".join(lines)
content = content.replace('"""\ntests/test_call_chain_edges_nodes.py', 'r"""\ntests/test_call_chain_edges_nodes.py')
content = content.replace('"""Item 3.3 (2b): caminhos contendo curingas (_, %, \\) não colidem', 'r"""Item 3.3 (2b): caminhos contendo curingas (_, %, \\) não colidem')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Cleaned tests/test_call_chain_edges_nodes.py successfully.")

