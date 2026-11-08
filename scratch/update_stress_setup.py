test_file = r"tests\test_concurrency_stress.py"
with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

target = """        # Conecta o gerenciador do banco à fila
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)"""

replacement = """        # Conecta o gerenciador do banco à fila
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Cria explicitamente a tabela test_log necessária exclusivamente para este teste de estresse
        success, err = self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS test_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "thread_name TEXT, "
            "val INTEGER"
            ");"
        )
        self.assertTrue(success, f"Falha ao criar test_log para o teste de estresse: {err}")"""

assert target in content, "Target not found in test_concurrency_stress.py"
content = content.replace(target, replacement)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated setUp in test_concurrency_stress.py successfully.")

