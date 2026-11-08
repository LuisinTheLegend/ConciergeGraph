import os

file_path = r"tests\test_mcp_server_extensions.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_block = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Inicializa a infraestrutura de dados da nossa trilha de sobrevivência
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Aplica o SchemaManager oficial v3.8.0
        import sqlite3
        from storage.schema import SchemaManager
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        self.project_uuid = "proj-mcp-ext"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (self.project_uuid, "mcp_ext_proj"),
        )

        # Injeta os managers reais dentro do escopo do servidor MCP para rodar o teste offline
        mcp_server.db_manager = self.db_manager
        mcp_server.checkpointer = AgnosticCheckpointer(self.db_manager)
        mcp_server.graph_rag = GraphRAGEngine(self.db_manager)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)"""

new_block = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        # Aplica o SchemaManager oficial v3.8.0 antes de subir concorrência
        import sqlite3
        from storage.schema import SchemaManager
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        # Inicializa a infraestrutura de dados da nossa trilha de sobrevivência
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        self.project_uuid = "proj-mcp-ext"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (self.project_uuid, "mcp_ext_proj"),
        )

        # Injeta os managers reais dentro do escopo do servidor MCP para rodar o teste offline
        mcp_server.db_manager = self.db_manager
        mcp_server.checkpointer = AgnosticCheckpointer(self.db_manager)
        mcp_server.graph_rag = GraphRAGEngine(self.db_manager)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)"""

assert target_block in content, "target_block not found"
content = content.replace(target_block, new_block)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Reordered setUp and tearDown in test_mcp_server_extensions.py successfully.")

