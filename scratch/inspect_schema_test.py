import sys, os
sys.path.insert(0, os.path.abspath('.'))

import sqlite3
from storage.schema import SchemaManager

conn = sqlite3.connect(':memory:')
sm = SchemaManager(conn)
sm.apply_full_schema()

cursor = conn.cursor()
cursor.execute("SELECT type, name FROM sqlite_master WHERE type='table' ORDER BY name;")
rows = cursor.fetchall()
print(f"Total de tabelas em sqlite_master: {len(rows)}")
for r in rows:
    print(f"  {r[0]:6s}: {r[1]}")
