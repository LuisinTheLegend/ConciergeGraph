import sqlite3

print("--- INVESTIGATION 2: Explicit BEGIN with DDL in SQLite ---")

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE t1 (id INT, val TEXT);")
conn.execute("INSERT INTO t1 VALUES (1, 'hello');")
conn.commit()

# Test explicit BEGIN TRANSACTION with regular table DROP
conn.execute("BEGIN IMMEDIATE;")
conn.execute("DROP TABLE t1;")
conn.rollback()

res_t1 = conn.execute("SELECT * FROM t1;").fetchall()
print("With explicit BEGIN, regular table DROP rollback restores table data:", res_t1)

# Now test with FTS5 virtual table
conn.execute("CREATE TABLE nodes (id INT, label TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 'apple');")
conn.execute("CREATE VIRTUAL TABLE nodes_fts USING fts5(label, content, content='nodes', content_rowid='id');")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.commit()

res_before = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'apple'").fetchall()
print("FTS5 before drop:", res_before)

# Test explicit BEGIN with FTS5 DROP
conn.execute("BEGIN IMMEDIATE;")
conn.execute("DROP TABLE nodes_fts;")
conn.rollback()

tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in sqlite_master after rollback of DROP TABLE nodes_fts:", tables)
try:
    res_after = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'apple'").fetchall()
    print("FTS5 match after rollback of DROP TABLE nodes_fts:", res_after)
except Exception as exc:
    print("FTS5 match after rollback of DROP TABLE FAILED:", exc)

