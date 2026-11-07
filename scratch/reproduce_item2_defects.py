import unittest
import sqlite3
import tempfile
import os
from storage.schema import SchemaManager
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine

class TestCallChainDefectsReproduction(unittest.TestCase):
    def setUp(self):
        self.fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        conn = sqlite3.connect(self.db_path)
        sm = SchemaManager(conn)
        sm.apply_full_schema()
        conn.close()
        self.db_mgr = ConciergeDatabaseManager(self.db_path)
        self.engine = GraphRAGEngine(self.db_mgr)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_2a_origin_file_appears_when_start_is_symbol(self):
        # a.py::f -> a.py::h, a.py::f -> b.py::g, b.py::g -> a.py::k
        p_uuid = "proj-2a"
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES (?, ?);", (p_uuid, "p2a"))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py', 'MODULE', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::f', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::h', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'b.py', 'MODULE', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'b.py::g', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a.py::k', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        
        id_af = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'a.py::f';")[0][0]
        id_ah = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'a.py::h';")[0][0]
        id_bg = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'b.py::g';")[0][0]
        id_ak = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'a.py::k';")[0][0]

        self.db_mgr.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_af, id_ah))
        self.db_mgr.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_af, id_bg))
        self.db_mgr.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_bg, id_ak))

        chain = self.engine.get_call_chain_recursive("a.py::f", depth_limit=5)
        # In HEAD: returns ['a.py', 'b.py'] because origin file 'a.py' is not filtered out!
        self.assertNotIn("a.py", chain, f"Defect 2a reproduced: origin file 'a.py' is in result: {chain}")
        self.assertEqual(chain, ["b.py"])

    def test_2b_like_wildcard_collision(self):
        p_uuid = "proj-2b"
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES (?, ?);", (p_uuid, "p2b"))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a_b.py', 'MODULE', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'a_b.py::x', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'aXb.py', 'MODULE', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'aXb.py::y', 'FUNCTION', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'z.py', 'MODULE', 'ACTIVE');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'z.py::zz', 'FUNCTION', 'ACTIVE');", (p_uuid,))

        id_ay = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'aXb.py::y';")[0][0]
        id_zz = self.db_mgr.read_query("SELECT id FROM nodes WHERE label = 'z.py::zz';")[0][0]
        self.db_mgr.write_query("INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, 'calls');", (id_ay, id_zz))

        chain = self.engine.get_call_chain_recursive("a_b.py", depth_limit=5)
        # In HEAD: returns ['z.py'] because LIKE '_' collides with 'aXb.py'!
        self.assertEqual(chain, [], f"Defect 2b reproduced: unescaped LIKE matched aXb.py and returned {chain}")

    def test_2c_duplicate_folder_name_must_raise_error(self):
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u1', 'alpha');")
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u2', 'alpha');")
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u1', 'mod.py', 'MODULE', 'ACTIVE');")
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u2', 'mod.py', 'MODULE', 'ACTIVE');")

        # In HEAD: resolves silently to u1 without error!
        with self.assertRaises(ValueError) as ctx:
            self.engine.get_call_chain_recursive("mod.py", project_identifier="alpha")
        self.assertIn("multiple projects", str(ctx.exception).lower())

    def test_2d_ambiguity_message_does_not_contain_names_or_uuids(self):
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u-secret-1', 'folder_secret_1');")
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES ('u-secret-2', 'folder_secret_2');")
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u-secret-1', 'shared.py', 'MODULE', 'ACTIVE');")
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('u-secret-2', 'shared.py', 'MODULE', 'ACTIVE');")

        # In HEAD: leaks folder names and UUIDs in message!
        with self.assertRaises(ValueError) as ctx:
            self.engine.get_call_chain_recursive("shared.py")
        msg = str(ctx.exception)
        self.assertNotIn("folder_secret_1", msg, f"Defect 2d reproduced: leaked folder name: {msg}")
        self.assertNotIn("folder_secret_2", msg, f"Defect 2d reproduced: leaked folder name: {msg}")
        self.assertNotIn("u-secret-1", msg, f"Defect 2d reproduced: leaked uuid: {msg}")
        self.assertNotIn("u-secret-2", msg, f"Defect 2d reproduced: leaked uuid: {msg}")

    def test_2e_reject_bool_depth_limit(self):
        p_uuid = "proj-2e"
        self.db_mgr.write_query("INSERT INTO projects (uuid, folder_name) VALUES (?, 'p2e');", (p_uuid,))
        self.db_mgr.write_query("INSERT INTO nodes (project_uuid, label, node_type, status) VALUES (?, 'root.py', 'MODULE', 'ACTIVE');", (p_uuid,))

        # In HEAD: accepts depth_limit=True because isinstance(True, int) is True!
        with self.assertRaises((ValueError, TypeError)):
            self.engine.get_call_chain_recursive("root.py", depth_limit=True)

if __name__ == "__main__":
    unittest.main()
