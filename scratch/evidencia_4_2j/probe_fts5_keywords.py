import sqlite3

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE nodes (id INT, label TEXT, tags TEXT, summary TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 't1', 's1', 'The file was not found on disk');")
conn.execute("INSERT INTO nodes VALUES (2, 'doc2', 't2', 's2', 'Bits AND bytes in memory');")
conn.execute("INSERT INTO nodes VALUES (3, 'doc3', 't3', 's3', 'We stood near the river bank');")
conn.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

# Test 1: "not found"
q1 = '"not" AND "found"'
r1 = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?", (q1,)).fetchall()
print('Match "not found":', r1)

# Test 2: "AND" alone
q2 = '"AND"'
r2 = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?", (q2,)).fetchall()
print('Match "AND":', r2)

# Test 3: "NEAR"
q3 = '"NEAR" AND "the" AND "river"'
r3 = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?", (q3,)).fetchall()
print('Match "NEAR the river":', r3)

# Test 4: query with operators "a AND b OR c"
q4 = '"Bits" AND "AND" AND "bytes"'
r4 = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?", (q4,)).fetchall()
print('Match "Bits AND bytes":', r4)

