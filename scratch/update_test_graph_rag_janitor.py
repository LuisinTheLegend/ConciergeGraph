import os

file_path = r"tests\test_graph_rag_janitor.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target_setup = """        # Garante a criação das tabelas relacionais do SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, is_dirty INTEGER, community_id TEXT"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS communities ("
            "id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER"
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

        # Cria tabelas legadas do background_janitor (mantidas para compatibilidade dos testes do janitor)
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, is_dirty INTEGER, community_id TEXT"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS communities ("
            "id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER"
            ");"
        )"""

assert target_setup in content, "target_setup not found"
content = content.replace(target_setup, new_setup)

target_test = """    def test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive(self):
        \"\"\"Valida que o SQLite WAL resolve conexões recursivas do grafo AST em < 10ms.\"\"\"
        # Popula arestas de chamadas AST (A -> B -> C) e (D -> E)
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('core/main.py', 'core/utils.py');"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('core/utils.py', 'core/db.py');"
        )
        self.db_manager.write_query(
            "INSERT INTO ast_edges VALUES ('interface/api.py', 'interface/auth.py');"
        )

        # Dispara a travessia recursiva iniciando em 'core/main.py'
        call_chain = self.graph_rag.get_call_chain_recursive(
            "core/main.py", depth_limit=3
        )

        # O retorno deve listar de forma recursiva os nós conectados (B e C)
        self.assertEqual(
            len(call_chain),
            2,
            "Deveria ter encontrado exatamente duas dependências recursivas.",
        )
        self.assertIn("core/utils.py", call_chain)
        self.assertIn("core/db.py", call_chain)
        self.assertNotIn(
            "interface/auth.py",
            call_chain,
            "Arestas de subgrafos isolados não podem vazar na busca.",
        )"""

new_test = """    def test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive(self):
        \"\"\"Valida que a travessia recursiva resolve conexões multi-hop no grafo canônico (nodes e edges).\"\"\"
        p_uuid = "proj-janitor-multihop"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (p_uuid, "janitor_multihop"),
        )
        # Popula nós canônicos
        for mod in ["core/main.py", "core/utils.py", "core/db.py", "interface/api.py", "interface/auth.py"]:
            self.db_manager.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, ?, 'MODULE', 'ACTIVE');",
                (p_uuid, mod),
            )

        def get_id(lbl):
            return self.db_manager.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = ?;", (p_uuid, lbl)
            )[0][0]

        id_main = get_id("core/main.py")
        id_utils = get_id("core/utils.py")
        id_db = get_id("core/db.py")
        id_api = get_id("interface/api.py")
        id_auth = get_id("interface/auth.py")

        # Popula arestas canônicas com relation_type = 'calls'
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_main, id_utils))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_utils, id_db))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_api, id_auth))

        # Dispara a travessia recursiva iniciando em 'core/main.py'
        call_chain = self.graph_rag.get_call_chain_recursive(
            "core/main.py", depth_limit=3
        )

        # O retorno deve listar de forma recursiva os nós conectados (core/utils.py e core/db.py)
        # O nó raiz 'core/main.py' é excluído do resultado retornado
        self.assertEqual(
            len(call_chain),
            2,
            "Deveria ter encontrado exatamente duas dependências recursivas.",
        )
        self.assertIn("core/utils.py", call_chain)
        self.assertIn("core/db.py", call_chain)
        self.assertNotIn(
            "interface/auth.py",
            call_chain,
            "Arestas de subgrafos isolados não podem vazar na busca.",
        )"""

assert target_test in content, "target_test not found"
content = content.replace(target_test, new_test)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated tests/test_graph_rag_janitor.py successfully.")

