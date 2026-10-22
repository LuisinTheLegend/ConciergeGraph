"""scratch/check_vectors_gap.py
Calcula a diferenca entre nos com conteudo no SQLite e vetores no Chroma
para responder a secao 5.5 do roteiro sem executar nenhuma alteracao.
"""
import sqlite3
import sys
import chromadb

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/concierge.db")
cur = conn.cursor()

# 1. Nos no banco todo
total_nodes = cur.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
nodes_with_content = cur.execute("SELECT COUNT(*) FROM nodes WHERE content IS NOT NULL AND length(trim(content)) > 0;").fetchone()[0]

# 2. Nos por projeto
projects = cur.execute("SELECT uuid, folder_name FROM projects;").fetchall()
project_stats = []
for p_uuid, p_name in projects:
    cnt = cur.execute("SELECT COUNT(*) FROM nodes WHERE project_uuid = ? AND content IS NOT NULL AND length(trim(content)) > 0;", (p_uuid,)).fetchone()[0]
    total_p = cur.execute("SELECT COUNT(*) FROM nodes WHERE project_uuid = ?;", (p_uuid,)).fetchone()[0]
    project_stats.append((p_uuid, p_name, cnt, total_p))

conn.close()

# 3. Vetores no Chroma
client = chromadb.PersistentClient("data/chroma")
col = client.get_collection("grafo_concierge")
chroma_count = col.count()

print("======================================================================")
print("INSPECAO SOMENTE-LEITURA: GAP DE VETORES (SQLITE vs. CHROMA)")
print("======================================================================")
print(f"Total de nos no SQLite (nodes):                  {total_nodes}")
print(f"Total de nos com conteudo preenchido no SQLite:  {nodes_with_content}")
print(f"Total de vetores na colecao Chroma 'grafo_concierge': {chroma_count}")
print(f"Diferenca global de nos com conteudo sem vetor: {nodes_with_content - chroma_count}")
print("\nDetalhamento por projeto (nos com conteudo / total nos):")
for p_uuid, p_name, cnt, total_p in project_stats:
    print(f"  - Projeto '{p_name}' ({p_uuid}): {cnt} nos com conteudo (de {total_p} totais)")

print("\nNota sobre o reparo da Rodada 4.1/D:")
print("O reparo da 4.1/D corrigiu o Bug F4-009 no Janitor (metadata['node_type']).")
print("Na proxima mineracao/reconciliacao, o pipeline tentara gerar embeddings para")
print(f"todos os nos pendentes que ainda nao possuem vetor na colecao.")
print("======================================================================")
