import os

test_file = r"tests\test_concurrency_stress.py"
with open(test_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the if __name__ == "__main__": line
target_idx = -1
for i, line in enumerate(lines):
    if line.strip().startswith('if __name__ == "__main__":'):
        target_idx = i
        break

if target_idx == -1:
    raise RuntimeError("Could not find __main__ line in test_concurrency_stress.py")

new_test_class = [
    "\n",
    "\n",
    "class TestCleanDatabaseManagerSchema(unittest.TestCase):\n",
    "    def test_clean_manager_does_not_leak_test_log(self):\n",
    '        """\n',
    "        Garante que ConciergeDatabaseManager não polui o banco com a tabela test_log.\n",
    "        Tabelas de produção criadas pelo SchemaManager oficial devem permanecer intactas.\n",
    '        """\n',
    "        from storage.schema import SchemaManager\n",
    "\n",
    '        fd, db_path = tempfile.mkstemp(suffix=".db")\n',
    "        os.close(fd)\n",
    "        try:\n",
    "            # 1. Aplica o schema oficial v3.8.0 + tabelas relacionais oficiais\n",
    "            sm = SchemaManager(db_path)\n",
    "            sm.apply_full_schema()\n",
    "\n",
    "            # 2. Instancia o ConciergeDatabaseManager de produção\n",
    "            db_mgr = ConciergeDatabaseManager(db_path)\n",
    "\n",
    "            # 3. Consulta tabelas em sqlite_master\n",
    '            rows = db_mgr.read_query("SELECT name FROM sqlite_master WHERE type=\'table\';")\n',
    "            table_names = [r[0] for r in rows]\n",
    "\n",
    "            # 4. Asserção principal: test_log NÃO deve existir\n",
    "            self.assertNotIn(\n",
    '                "test_log",\n',
    "                table_names,\n",
    '                "Tabela de teste \'test_log\' vazou no schema de produção!",\n',
    "            )\n",
    "\n",
    "            # 5. Asserção de integridade: tabelas legítimas continuam existindo\n",
    '            for req in ["projects", "nodes", "edges", "agent_checkpoints"]:\n',
    '                self.assertIn(req, table_names, f"Tabela legítima \'{req}\' ausente!")\n',
    "        finally:\n",
    "            try:\n",
    "                os.unlink(db_path)\n",
    '                for ext in (".wal", ".shm", "-wal", "-shm"):\n',
    "                    p = db_path + ext\n",
    "                    if os.path.exists(p):\n",
    "                        os.unlink(p)\n",
    "            except OSError:\n",
    "                pass\n",
    "\n",
]

lines = lines[:target_idx] + new_test_class + lines[target_idx:]

with open(test_file, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Appended TestCleanDatabaseManagerSchema successfully.")

