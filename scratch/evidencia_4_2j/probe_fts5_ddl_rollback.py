import sqlite3

print("--- INVESTIGATION: SQLite Virtual Table DDL Transactionality ---")

# Experiment A: DROP TABLE of regular table vs virtual table
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t1 (id INT, val TEXT);")
conn.execute("INSERT INTO t1 VALUES (1, 'hello');")
conn.commit()

try:
    with conn:
        conn.execute("DROP TABLE t1;")
        raise RuntimeError("boom")
except RuntimeError:
    pass

res_t1 = conn.execute("SELECT * FROM t1;").fetchall()
print("Regular table DROP rollback restores table data:", res_t1)

# Experiment B: DROP TABLE of FTS5 table
conn.execute("CREATE TABLE nodes (id INT, label TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 'apple');")
conn.execute("CREATE VIRTUAL TABLE nodes_fts USING fts5(label, content, content='nodes', content_rowid='id');")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.commit()

res_before = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'apple'").fetchall()
print("FTS5 before drop:", res_before)

try:
    with conn:
        conn.execute("DROP TABLE nodes_fts;")
        raise RuntimeError("boom after drop")
except RuntimeError:
    pass

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in sqlite_master after rollback of DROP TABLE nodes_fts:", tables)
try:
    res_after = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'apple'").fetchall()
    print("FTS5 match after rollback of DROP TABLE:", res_after)
except Exception as exc:
    print("FTS5 match after rollback of DROP TABLE FAILED:", exc)

