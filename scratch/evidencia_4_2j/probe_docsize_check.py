import sqlite3

def check_fts_consistency(conn: sqlite3.Connection) -> bool:
    """Returns True if consistent, False if rebuild is needed."""
    try:
        cur_nodes = conn.execute("SELECT COUNT(*) FROM nodes")
        node_count = cur_nodes.fetchone()[0]
    except sqlite3.OperationalError:
        return True # nodes table doesn't exist

    if node_count == 0:
        return True

    # Check FTS5 docsize shadow table
    try:
        cur_docsize = conn.execute("SELECT COUNT(*) FROM nodes_fts_docsize")
        docsize_count = cur_docsize.fetchone()[0]
    except sqlite3.OperationalError:
        # nodes_fts or nodes_fts_docsize doesn't exist
        return False

    return node_count == docsize_count

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE nodes (id INT, label TEXT, tags TEXT, summary TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 't1', 's1', 'apple');")
conn.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")

print("Consistent before rebuild?", check_fts_consistency(conn))

conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
print("Consistent after rebuild?", check_fts_consistency(conn))

