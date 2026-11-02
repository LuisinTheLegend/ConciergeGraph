import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

# Test probe verifying atomic migration + rollback + consistency check
def probe():
    conn = sqlite3.connect(":memory:")
    # Legacy DB setup
    conn.executescript("""
        CREATE TABLE nodes (id INTEGER PRIMARY KEY, label TEXT, content TEXT);
        CREATE VIRTUAL TABLE nodes_fts USING fts5(label, content='nodes', content_rowid='id');
        CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
            INSERT INTO nodes_fts(rowid, label) VALUES (new.id, new.label);
        END;
    """)
    conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 'body1')")
    conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
    conn.commit()

    # Verify atomic DDL with rollback
    conn.execute("BEGIN IMMEDIATE;")
    conn.execute("DROP TRIGGER nodes_ai;")
    conn.execute("DROP TABLE nodes_fts;")
    conn.execute("CREATE VIRTUAL TABLE nodes_fts USING fts5(label, content, content='nodes', content_rowid='id');")
    # Simulate error before rebuild
    try:
        raise RuntimeError("simulated crash before rebuild")
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        print("Rolled back successfully")

    # Check that legacy nodes_fts is intact!
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'").fetchone()
    print("Table SQL after rollback:", row[0])
    res = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'doc1'").fetchall()
    print("Search after rollback:", res)
    assert len(res) == 1

if __name__ == "__main__":
    probe()

