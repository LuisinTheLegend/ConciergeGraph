"""scratch/verify_p4_after.py
Verifica contagens, integridade, checksum e FTS em data/concierge.db apos a migracao.
"""
import hashlib
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/concierge.db")
cur = conn.cursor()

def print_counts():
    total = cur.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
    dumb = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary LIKE '[DUMB]%';").fetchone()[0]
    nulls = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NULL;").fetchone()[0]
    others = cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NOT NULL AND summary NOT LIKE '[DUMB]%';").fetchone()[0]
    print(f"total={total}")
    print(f"dumb={dumb}")
    print(f"nulls={nulls}")
    print(f"others={others}")

def print_integrity():
    res = cur.execute("PRAGMA integrity_check;").fetchall()
    for row in res:
        print(f"integrity_check={row[0]}")

def print_checksum():
    hasher = hashlib.sha256()
    query = "SELECT id, label, content, type, node_type, tags, file_hash, status FROM nodes ORDER BY id ASC;"
    for row in cur.execute(query):
        row_str = "|".join("" if v is None else str(v) for v in row)
        hasher.update(row_str.encode("utf-8"))
        hasher.update(b"\n")
    print(f"content_checksum={hasher.hexdigest()}")

def print_fts():
    cur.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
    print("fts_integrity_check=ok")
    summary_matches = cur.execute("SELECT COUNT(*) FROM nodes_fts WHERE nodes_fts MATCH 'summary: DUMB';").fetchone()[0]
    global_matches = cur.execute("SELECT COUNT(*) FROM nodes_fts WHERE nodes_fts MATCH 'DUMB';").fetchone()[0]
    print(f"fts_summary_dumb_matches={summary_matches}")
    print(f"fts_global_dumb_matches={global_matches}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "counts"
    if mode == "counts":
        print_counts()
    elif mode == "integrity":
        print_integrity()
    elif mode == "checksum":
        print_checksum()
    elif mode == "fts":
        print_fts()
    conn.close()
