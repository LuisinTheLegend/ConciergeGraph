import sqlite3

print("--- INVESTIGATION 3: Full FTS5 Upgrade Sequence Transactionality ---")

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE nodes (id INT, label TEXT, tags TEXT, summary TEXT, content TEXT);")
conn.execute("INSERT INTO nodes VALUES (1, 'doc1', 't1', 's1', 'apple');")
# Old 3-column table
conn.execute("CREATE VIRTUAL TABLE nodes_fts USING fts5(label, tags, summary, content='nodes', content_rowid='id');")
conn.execute("CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN INSERT INTO nodes_fts(rowid, label, tags, summary) VALUES (new.id, new.label, new.tags, new.summary); END;")
conn.execute("CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary) VALUES('delete', old.id, old.label, old.tags, old.summary); END;")
conn.execute("CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary) VALUES('delete', old.id, old.label, old.tags, old.summary); INSERT INTO nodes_fts(rowid, label, tags, summary) VALUES (new.id, new.label, new.tags, new.summary); END;")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.commit()

# Old search by label works
res_old = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'doc1'").fetchall()
print("Old search before migration:", res_old)

# Now simulate failed migration inside BEGIN IMMEDIATE
try:
    conn.execute("BEGIN IMMEDIATE;")
    conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
    conn.execute("DROP TRIGGER IF EXISTS nodes_ad;")
    conn.execute("DROP TRIGGER IF EXISTS nodes_au;")
    conn.execute("DROP TABLE IF EXISTS nodes_fts;")
    conn.execute("""
    CREATE VIRTUAL TABLE nodes_fts USING fts5(
        label, tags, summary, content, content='nodes', content_rowid='id',
        tokenize='unicode61 remove_diacritics 2'
    );
    """)
    conn.execute("""
    CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
      INSERT INTO nodes_fts(rowid, label, tags, summary, content)
      VALUES (new.id, new.label, new.tags, new.summary, new.content);
    END;
    """)
    # Simulated failure before rebuild!
    raise RuntimeError("Power outage or process killed before rebuild!")
    conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
    conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
    conn.execute("COMMIT;")
except Exception as exc:
    conn.execute("ROLLBACK;")
    print("Caught migration failure:", exc)

# Now check state after rollback!
# 1. Did the old nodes_fts table restore?
schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'").fetchone()[0]
print("Schema of nodes_fts after rollback (should have 3 columns):", "content," not in schema)

# 2. Did the 3 triggers restore?
triggers = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()]
print("Triggers after rollback (should be 3):", triggers)

# 3. Does old search work?
res_after_rollback = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'doc1'").fetchall()
print("Search after rollback (should match doc1):", res_after_rollback)

# 4. Now run migration cleanly to completion
conn.execute("BEGIN IMMEDIATE;")
conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
conn.execute("DROP TRIGGER IF EXISTS nodes_ad;")
conn.execute("DROP TRIGGER IF EXISTS nodes_au;")
conn.execute("DROP TABLE IF EXISTS nodes_fts;")
conn.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")
conn.execute("""
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary, content)
  VALUES (new.id, new.label, new.tags, new.summary, new.content);
END;
""")
conn.execute("""
CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
  VALUES('delete', old.id, old.label, old.tags, old.summary, old.content);
END;
""")
conn.execute("""
CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
  VALUES('delete', old.id, old.label, old.tags, old.summary, old.content);
  INSERT INTO nodes_fts(rowid, label, tags, summary, content)
  VALUES (new.id, new.label, new.tags, new.summary, new.content);
END;
""")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
conn.execute("COMMIT;")

# Verify search on content now works!
res_content = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'apple'").fetchall()
print("Search on content after successful migration:", res_content)

