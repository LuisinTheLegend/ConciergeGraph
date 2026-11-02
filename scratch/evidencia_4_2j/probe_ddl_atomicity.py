import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute('CREATE TABLE nodes (id INTEGER PRIMARY KEY, label TEXT, tags TEXT, summary TEXT, content TEXT);')
conn.execute('INSERT INTO nodes VALUES (1, "item1", "t1", "s1", "conteudo1");')
conn.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")
conn.execute("CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN INSERT INTO nodes_fts(rowid, label, tags, summary, content) VALUES (new.id, new.label, new.tags, new.summary, new.content); END;")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn.commit()

res = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'conteudo1'").fetchall()
print('Initial search:', res)

# Test 1: Using executescript (implicit commit -> NOT atomic!)
try:
    conn.execute("BEGIN IMMEDIATE;")
    conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
    conn.execute("DROP TABLE IF EXISTS nodes_fts;")
    # executescript commits immediately!
    conn.executescript("""
    CREATE VIRTUAL TABLE nodes_fts USING fts5(label, tags, summary, content);
    """)
    # crash!
    raise RuntimeError("Simulated crash after executescript!")
except RuntimeError as e:
    conn.rollback()
    print('Test 1 (executescript) rollback caught:', e)

# On Test 1, table was committed as empty table! Rebuild never ran!
res_after_executescript = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'conteudo1'").fetchall()
print('Test 1 search after rollback (SHOULD BE EMPTY/BROKEN because executescript committed):', res_after_executescript)

# Now Test 2: Using pure execute() inside transaction (all-or-nothing!)
conn2 = sqlite3.connect(':memory:')
conn2.execute('CREATE TABLE nodes (id INTEGER PRIMARY KEY, label TEXT, tags TEXT, summary TEXT, content TEXT);')
conn2.execute('INSERT INTO nodes VALUES (1, "item1", "t1", "s1", "conteudo1");')
conn2.execute("""
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
""")
conn2.execute("CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN INSERT INTO nodes_fts(rowid, label, tags, summary, content) VALUES (new.id, new.label, new.tags, new.summary, new.content); END;")
conn2.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
conn2.commit()

try:
    with conn2:
        conn2.execute("DROP TRIGGER IF EXISTS nodes_ai;")
        conn2.execute("DROP TABLE IF EXISTS nodes_fts;")
        conn2.execute("""
        CREATE VIRTUAL TABLE nodes_fts USING fts5(
            label, tags, summary, content, content='nodes', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        """)
        conn2.execute("CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN INSERT INTO nodes_fts(rowid, label, tags, summary, content) VALUES (new.id, new.label, new.tags, new.summary, new.content); END;")
        # crash before rebuild!
        raise RuntimeError("Simulated crash before rebuild!")
        conn2.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
except RuntimeError as e:
    print('Test 2 (pure execute) caught:', e)

# On Test 2, rollback should restore old table and triggers completely!
res_after_atomic = conn2.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'conteudo1'").fetchall()
print('Test 2 search after rollback (SHOULD BE INTACT):', res_after_atomic)

# Also check triggers
triggers = conn2.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
print('Test 2 triggers after rollback:', triggers)

