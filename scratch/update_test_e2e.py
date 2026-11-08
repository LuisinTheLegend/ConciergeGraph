import os

file_path = r"tests\test_e2e_concierge_integration.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update setUp
target_setup = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # 1. Initialize SerializedWriteQueue (WAL) — Phase 1 (SDD-02)
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # 2. Initialize relational schemas in SQLite WAL
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, "
            "body_hash TEXT, is_dirty INTEGER, community_id TEXT"
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
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "agent_id TEXT, session_id TEXT, checkpoint_id TEXT, state_blob TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
            ");"
        )"""

new_setup = """    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        # 1. Guarantee official relational schema initialization for SQLite WAL
        import sqlite3
        from storage.schema import SchemaManager
        conn = sqlite3.connect(self.db_path)
        SchemaManager(conn).apply_full_schema()
        conn.close()

        # 2. Initialize SerializedWriteQueue (WAL) — Phase 1 (SDD-02)
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        self.project_uuid = "proj-e2e"
        self.db_manager.write_query(
            "INSERT INTO projects (uuid, folder_name) VALUES (?, ?);",
            (self.project_uuid, "e2e_proj"),
        )

        # Ancillary mock tables for E2E janitor/search steps
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, "
            "body_hash TEXT, is_dirty INTEGER, community_id TEXT"
            ");"
        )
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS communities ("
            "id TEXT PRIMARY KEY, summary_text TEXT, is_dirty INTEGER"
            ");"
        )"""

assert target_setup in content, "target_setup not found"
content = content.replace(target_setup, new_setup)

# And remove os.close from tearDown
target_td = """    def tearDown(self):
        # Gracefully shut down serialized write queue
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)"""

new_td = """    def tearDown(self):
        # Gracefully shut down serialized write queue
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)"""

assert target_td in content, "target_td not found"
content = content.replace(target_td, new_td)

# 2. Update Step C (edges insertion)
target_step_c = """        # Register circular AST call dependencies
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/main.py', 'core/utils.py');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/utils.py', 'core/db_driver.py');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/db_driver.py', 'core/main.py');")  # CYCLIC LOOP!

        # Recursively traverse from main.py (must safely handle cyclic loop via depth limit guard)
        call_chain = self.graph_rag.get_call_chain_recursive("core/main.py", depth_limit=4)"""

new_step_c = """        # Register circular call dependencies on canonical nodes and edges
        for mod in ["core/main.py", "core/utils.py", "core/db_driver.py"]:
            self.db_manager.write_query(
                "INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, ?, 'MODULE', 'ACTIVE');",
                (self.project_uuid, mod),
            )

        def get_id(lbl):
            return self.db_manager.read_query(
                "SELECT id FROM nodes WHERE project_uuid = ? AND label = ?;", (self.project_uuid, lbl)
            )[0][0]

        id_main = get_id("core/main.py")
        id_utils = get_id("core/utils.py")
        id_db = get_id("core/db_driver.py")

        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_main, id_utils))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_utils, id_db))
        self.db_manager.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_db, id_main))  # CYCLIC LOOP!

        # Recursively traverse from main.py (must safely handle cyclic loop via visited tracking)
        call_chain = self.graph_rag.get_call_chain_recursive("core/main.py", depth_limit=4)"""

assert target_step_c in content, "target_step_c not found"
content = content.replace(target_step_c, new_step_c)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated tests/test_e2e_concierge_integration.py successfully.")
