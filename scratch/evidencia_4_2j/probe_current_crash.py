import sys
sys.path.insert(0, ".")
import sqlite3
from tests.test_fts_atomic_migration import ConnectionProxy, _create_legacy_v3_database
from storage.schema import SchemaManager

conn = sqlite3.connect(":memory:")
_create_legacy_v3_database(conn)
conn.execute("INSERT INTO projects (uuid, name) VALUES ('p1', 'TestProj')")
conn.execute("INSERT INTO nodes (id, project_uuid, label, tags, summary, content) VALUES (1, 'p1', 'modulo_antigo.py', 'tag1', 'sumario legado', 'corpo confidencial 123')")
conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
conn.commit()

proxy = ConnectionProxy(conn)
# In current schema.py:
# Line 297: self._conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
# Line 298: self._conn.execute("DROP TRIGGER IF EXISTS nodes_ad;")
# Line 299: self._conn.execute("DROP TRIGGER IF EXISTS nodes_au;")
# Line 300: self._conn.execute("DROP TABLE IF EXISTS nodes_fts;")
# Line 303: self._conn.executescript(FTS5_TABLE_SQL)
# Line 304: self._conn.executescript(FTS5_TRIGGERS_SQL)
# Line 307: self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

# Crash during rebuild:
proxy.crash_on_pattern = "rebuild"
sm = SchemaManager(proxy)
try:
    sm.apply_full_schema()
except Exception as e:
    print('Caught exception:', e)

cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'")
row = cur.fetchone()
print('nodes_fts table row after crash during rebuild:', row[0] if row else None)

triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
print('Triggers after crash:', triggers)

# Can we search for old nodes?
try:
    res = conn.execute("SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH 'modulo_antigo'").fetchall()
    print('Search result for modulo_antigo (on current code it returned 0 because rebuild failed):', res)
except Exception as e:
    print('Search failed:', e)
