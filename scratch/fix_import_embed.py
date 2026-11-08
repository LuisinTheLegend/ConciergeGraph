file_path = r"tests\test_call_chain_edges_nodes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """        from ingestion.orchestrator import IngestionManager
        from storage.vector_store import ChromaVectorStore
        from core.embeddings import EmbeddingManager"""

replacement = """        from ingestion.orchestrator import IngestionManager
        from storage.vector_store import ChromaVectorStore, EmbeddingManager"""

assert target in content, "target import not found"
content = content.replace(target, replacement)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed EmbeddingManager import in test_call_chain_edges_nodes.py")

