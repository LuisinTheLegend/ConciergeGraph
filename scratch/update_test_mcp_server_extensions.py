import os

file_path = r"tests\test_mcp_server_extensions.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_setup = """        # Cria as tabelas do SQLite WAL necessárias para os testes integrados do MCP
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS ast_edges ("
            "parent_node TEXT, child_node TEXT, UNIQUE(parent_node, child_node)"
            ");"
        )"""

new_setup = """        # Aplica o SchemaManager oficial v3.8.0
        import sqlite3
        from storage.schema import SchemaManager
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        self.project_uuid = "proj-mcp-ext"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (self.project_uuid, "mcp_ext_proj"),
        )"""

assert target_setup in content, "target_setup not found"
content = content.replace(target_setup, new_setup)

target_test = """    def test_mcp_tool_concierge_get_call_chain(self):
        \"\"\"Valida que a ferramenta MCP concierge_get_call_chain resolve dependências recursivas.\"\"\"
        # Insere arestas de dependências
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('index.js', 'auth.js');"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('auth.js', 'db_local.js');"
        )

        # Chama a ferramenta MCP
        call_chain = mcp_server.concierge_get_call_chain(
            start_node="index.js", depth_limit=3
        )

        self.assertEqual(len(call_chain), 2)
        self.assertIn("auth.js", call_chain)
        self.assertIn("db_local.js", call_chain)"""

new_test = """    def test_mcp_tool_concierge_get_call_chain(self):
        \"\"\"Valida que a ferramenta MCP concierge_get_call_chain resolve dependências recursivas sobre nodes e edges.\"\"\"
        for mod in ["index.js", "auth.js", "db_local.js"]:
            self.db_manager.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, ?, 'MODULE', 'ACTIVE');",
                (self.project_uuid, mod),
            )

        def get_id(lbl):
            return self.db_manager.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = ?;", (self.project_uuid, lbl)
            )[0][0]

        id_idx = get_id("index.js")
        id_auth = get_id("auth.js")
        id_db = get_id("db_local.js")

        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_idx, id_auth))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_auth, id_db))

        # Chama a ferramenta MCP
        call_chain = mcp_server.concierge_get_call_chain(
            start_node="index.js", depth_limit=3
        )

        self.assertEqual(len(call_chain), 2)
        self.assertIn("auth.js", call_chain)
        self.assertIn("db_local.js", call_chain)
        self.assertNotIn("index.js", call_chain)"""

assert target_test in content, "target_test not found"
content = content.replace(target_test, new_test)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated tests/test_mcp_server_extensions.py successfully.")

