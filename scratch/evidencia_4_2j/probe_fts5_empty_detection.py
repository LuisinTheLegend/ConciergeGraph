import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE nodes (id INT, label TEXT, tags TEXT, summary TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 't1', 's1', 'apple');")
conn.execute("INSERT INTO nodes VALUES (2, 'doc2', 't2', 's2', 'banana');")

# Create empty virtual table WITHOUT rebuild
conn.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")
conn.commit()

# Test different ways to check if FTS is empty or desynchronized:
# 1. SELECT COUNT(*) FROM nodes_fts
cnt_fts = conn.execute("SELECT COUNT(*) FROM nodes_fts").fetchone()[0]
print("COUNT(*) FROM nodes_fts on unrebuilt table:", cnt_fts)

# 2. SELECT COUNT(*) FROM nodes_fts_docsize
try:
    cnt_docsize = conn.execute("SELECT COUNT(*) FROM nodes_fts_docsize").fetchone()[0]
    print("COUNT(*) FROM nodes_fts_docsize on unrebuilt table:", cnt_docsize)
except Exception as e:
    print("Error querying docsize:", e)

# 3. SELECT COUNT(*) FROM nodes_fts_data
try:
    cnt_data = conn.execute("SELECT COUNT(*) FROM nodes_fts_data").fetchone()[0]
    print("COUNT(*) FROM nodes_fts_data on unrebuilt table:", cnt_data)
except Exception as e:
    print("Error querying data:", e)

# Now rebuild and check again
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.commit()

cnt_fts_rebuilt = conn.execute("SELECT COUNT(*) FROM nodes_fts").fetchone()[0]
print("COUNT(*) FROM nodes_fts after rebuild:", cnt_fts_rebuilt)
cnt_docsize_rebuilt = conn.execute("SELECT COUNT(*) FROM nodes_fts_docsize").fetchone()[0]
print("COUNT(*) FROM nodes_fts_docsize after rebuild:", cnt_docsize_rebuilt)

