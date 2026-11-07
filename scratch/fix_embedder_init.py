file_path = r"tests\test_call_chain_edges_nodes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = "embedder = EmbeddingManager(sqlite_store=store)"
replacement = "embedder = EmbeddingManager()"

assert target in content, "target not found"
content = content.replace(target, replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated embedder call.")

