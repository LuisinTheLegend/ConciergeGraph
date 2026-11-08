import os

test_file = r"tests\test_concurrency_stress.py"
with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

target = """            # 1. Aplica o schema oficial v3.8.0 + tabelas relacionais oficiais
            sm = SchemaManager(db_path)
            sm.apply_full_schema()

            # 2. Instancia o ConciergeDatabaseManager de produção
            db_mgr = ConciergeDatabaseManager(db_path)"""

replacement = """            # 1. Aplica o schema oficial v3.8.0 + tabelas relacionais oficiais
            import sqlite3
            conn = sqlite3.connect(db_path)
            try:
                sm = SchemaManager(conn)
                sm.apply_full_schema()
            finally:
                conn.close()

            # 2. Instancia o ConciergeDatabaseManager de produção
            db_mgr = ConciergeDatabaseManager(db_path)"""

assert target in content, "Target not found in test_concurrency_stress.py"
content = content.replace(target, replacement)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated test_concurrency_stress.py with sqlite3.connect.")

