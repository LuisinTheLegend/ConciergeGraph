import os

file_path = r"tests\test_mcp_server_extensions.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_setup = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Aplica o SchemaManager oficial v3.8.0"""

new_setup = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        # Aplica o SchemaManager oficial v3.8.0"""

assert target_setup in content, "target_setup not found"
content = content.replace(target_setup, new_setup)

target_teardown = """    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)"""

new_teardown = """    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)"""

assert target_teardown in content, "target_teardown not found"
content = content.replace(target_teardown, new_teardown)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated setUp/tearDown in test_mcp_server_extensions.py")

