"""
fase3_redo_repro_alias.py — Reprodução do achado declarado no AUDIT_PROTOCOL.md
(Fase 1, item `core/alias_tracker.py`) que NÃO possui relatório em audits/:
"apply_alias_migration não é atômico (loop de UPDATEs sem transação envolvente)".

Usa o ConciergeDatabaseManager REAL (core/database.py), cujo execute_write faz
commit a cada chamada, sobre um banco temporário. Força a falha do 3º UPDATE
(tabela ast_edges sem as colunas esperadas) e verifica se os UPDATEs anteriores
(files, nodes) ficaram persistidos -> migração parcial = não atômica.

Uso: python scratch/fase3_redo_repro_alias.py
"""
import os
import sqlite3
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import ConciergeDatabaseManager  # noqa: E402
from core.alias_tracker import AliasTracker  # noqa: E402

tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, "repro.db")
conn = sqlite3.connect(db_path)
conn.executescript("""
CREATE TABLE files (path TEXT, last_modified REAL, is_dirty INTEGER, content TEXT);
CREATE TABLE nodes (label TEXT);
CREATE TABLE ast_edges (src TEXT, dst TEXT);  -- sem parent_node_id/child_node_id
INSERT INTO files VALUES ('old.py', 0, 0, 'x');
INSERT INTO nodes VALUES ('old.py');
""")
conn.commit()
conn.close()

db = ConciergeDatabaseManager(db_path)
tracker = AliasTracker(db, hash_generator_callback=lambda p: None)

ok = tracker.apply_alias_migration("old.py", "new.py")
print(f"apply_alias_migration retornou: {ok}")

conn = sqlite3.connect(db_path)
files = conn.execute("SELECT path FROM files").fetchall()
nodes = conn.execute("SELECT label FROM nodes").fetchall()
conn.close()
print(f"files.path após a chamada: {files}")
print(f"nodes.label após a chamada: {nodes}")
if not ok and files == [("new.py",)] and nodes == [("new.py",)]:
    print("RESULTADO: CONFIRMADO — falha no 3º UPDATE, mas files e nodes já foram "
          "migrados e commitados (migração parcial, não atômica).")
else:
    print("RESULTADO: NÃO REPRODUZIDO nesta configuração.")
