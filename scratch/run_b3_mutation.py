import subprocess
import sys

db_file = r"core\database.py"

with open(db_file, "r", encoding="utf-8") as f:
    clean_code = f.read()

mutated_code = clean_code.replace(
    '    def _init_tables(self):\n        """No-op: Schema creation is managed exclusively by SchemaManager (storage/schema.py)."""\n        pass',
    '    def _init_tables(self):\n        """MUTATION: leak test_log."""\n        self.write_query(\n            "CREATE TABLE IF NOT EXISTS test_log ("\n            "id INTEGER PRIMARY KEY AUTOINCREMENT, "\n            "thread_name TEXT, "\n            "val INTEGER"\n            ");",\n        )'
)

assert mutated_code != clean_code, "Failed to apply mutation"

try:
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(mutated_code)
    
    print("Applied mutation in core/database.py. Running pytest...")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/test_concurrency_stress.py::TestCleanDatabaseManagerSchema"],
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )
    
    with open("scratch/evidencia_4_3/b3_mutation_test_log_leaks.txt", "w", encoding="utf-8") as f:
        f.write(res.stdout + "\n" + res.stderr)
        
    print("Mutation return code:", res.returncode)
    assert res.returncode != 0, "Mutation was expected to fail!"
    print("Mutation correctly killed!")
finally:
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(clean_code)
    print("Clean code restored.")

# Verify clean passes again
res_verify = subprocess.run(
    [sys.executable, "-m", "pytest", "-v", "tests/test_concurrency_stress.py::TestCleanDatabaseManagerSchema"],
    capture_output=True,
    encoding="utf-8",
    errors="replace"
)
assert res_verify.returncode == 0, "Clean code failed verification!"
print("Verified clean code passes.")

