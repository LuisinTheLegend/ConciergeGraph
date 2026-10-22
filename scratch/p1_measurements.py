"""scratch/p1_measurements.py
Utilitário para medições da Parte 1 da Rodada 4.1/H.
Executa consultas somente-leitura em data/concierge.db e data/chroma.
"""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(ROOT_DIR / "data/concierge.db")
CHROMA_DIR = str(ROOT_DIR / "data/chroma")

def measure_counts(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
    dumb = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary LIKE '[DUMB]%';").fetchone()[0]
    nulls = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NULL;").fetchone()[0]
    others = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NOT NULL AND summary NOT LIKE '[DUMB]%';").fetchone()[0]
    conn.close()

    print(f"Total de nos:           {total}")
    print(f"Nos com [DUMB]%:        {dumb}")
    print(f"Nos com summary NULL:   {nulls}")
    print(f"Nos com outros resumos: {others}")

def measure_chroma(chroma_dir=CHROMA_DIR):
    import chromadb
    client = chromadb.PersistentClient(path=chroma_dir)
    col = client.get_collection("grafo_concierge")
    count = col.count()
    print(f"Total de vetores na colecao Chroma 'grafo_concierge': {count}")

def measure_integrity(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    result = cur.execute("PRAGMA integrity_check;").fetchall()
    conn.close()
    for row in result:
        print(f"integrity_check: {row[0]}")

def measure_projects(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT uuid, length(summary), summary LIKE '%[DUMB]%' FROM projects;").fetchall()
    conn.close()
    print(f"{'UUID':<38} | {'Length(summary)':<16} | {'summary LIKE %[DUMB]%'}")
    print("-" * 70)
    for r in rows:
        uid, l_sum, has_dumb = r[0], r[1] if r[1] is not None else 0, bool(r[2])
        print(f"{uid:<38} | {l_sum:<16} | {has_dumb}")

def inspect_triggers(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND (tbl_name='nodes' OR tbl_name='nodes_fts');").fetchall()
    conn.close()
    if not rows:
        print("Nenhum trigger encontrado.")
    for r in rows:
        print(f"Trigger: {r[0]}")
        print(f"{r[1]}\n")

def calculate_checksum(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Checksum determinístico de (id, label, content, type, node_type, tags, file_hash, status)
    # de TODOS os nós, ordenados por id
    query = """
        SELECT id, label, content, type, node_type, tags, file_hash, status
        FROM nodes
        ORDER BY id ASC;
    """
    hasher = hashlib.sha256()
    total_rows = 0
    for row in cur.execute(query):
        total_rows += 1
        # Converte para string canônica estável
        row_str = "|".join("" if v is None else str(v) for v in row)
        hasher.update(row_str.encode("utf-8"))
        hasher.update(b"\n")
    conn.close()

    digest = hasher.hexdigest()
    print(f"Total de nos processados no checksum: {total_rows}")
    print(f"SHA-256 do conteudo preservado:      {digest}")
    return digest

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "counts"
    target_db = sys.argv[2] if len(sys.argv) > 2 else DB_PATH

    if mode == "counts":
        measure_counts(target_db)
    elif mode == "chroma":
        measure_chroma()
    elif mode == "integrity":
        measure_integrity(target_db)
    elif mode == "projects":
        measure_projects(target_db)
    elif mode == "triggers":
        inspect_triggers(target_db)
    elif mode == "checksum":
        calculate_checksum(target_db)
    else:
        print(f"Modo desconhecido: {mode}")
