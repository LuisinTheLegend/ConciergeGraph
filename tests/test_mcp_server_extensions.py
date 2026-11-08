"""
tests/test_mcp_server_extensions.py — SDD-SURVIVAL-08

Suíte de Testes TDD para Extensão Unificada do Servidor MCP.

Valida a integração end-to-end das 4 novas ferramentas MCP com o
SQLite WAL real, provando que as rotinas JSON-RPC se comportam
perfeitamente sem falhas de banco:
  1. agent_save_checkpoint + agent_get_checkpoint: persistência e recuperação.
  2. agent_list_checkpoints: timeline cronológica ordenada.
  3. concierge_get_call_chain: resolução recursiva de dependências.

Injeta instâncias reais de DB nos sentinels de módulo do mcp_server
para testar offline sem bootstrap completo do FastMCP.
"""

import unittest
import os
import sys
import importlib
import tempfile
import json


# ── Importação cirúrgica: carrega módulos diretamente sem acionar
#    os __init__.py dos pacotes (que puxam dependências pesadas). ──

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1) interface.queue_writer
_qw_spec = importlib.util.spec_from_file_location(
    "interface.queue_writer",
    os.path.join(_project_root, "interface", "queue_writer.py"),
)
_qw_mod = importlib.util.module_from_spec(_qw_spec)
sys.modules["interface.queue_writer"] = _qw_mod
_qw_spec.loader.exec_module(_qw_mod)
SerializedWriteQueue = _qw_mod.SerializedWriteQueue

# 2) core.database
_db_spec = importlib.util.spec_from_file_location(
    "core.database",
    os.path.join(_project_root, "core", "database.py"),
)
_db_mod = importlib.util.module_from_spec(_db_spec)
sys.modules["core.database"] = _db_mod
_db_spec.loader.exec_module(_db_mod)
ConciergeDatabaseManager = _db_mod.ConciergeDatabaseManager

# 3) core.checkpointer
_cp_spec = importlib.util.spec_from_file_location(
    "core.checkpointer",
    os.path.join(_project_root, "core", "checkpointer.py"),
)
_cp_mod = importlib.util.module_from_spec(_cp_spec)
sys.modules["core.checkpointer"] = _cp_mod
_cp_spec.loader.exec_module(_cp_mod)
AgnosticCheckpointer = _cp_mod.AgnosticCheckpointer

# 4) core.graph_rag
_gr_spec = importlib.util.spec_from_file_location(
    "core.graph_rag",
    os.path.join(_project_root, "core", "graph_rag.py"),
)
_gr_mod = importlib.util.module_from_spec(_gr_spec)
sys.modules["core.graph_rag"] = _gr_mod
_gr_spec.loader.exec_module(_gr_mod)
GraphRAGEngine = _gr_mod.GraphRAGEngine

# 5) interface.mcp_server (carrega apenas o módulo, sem bootstrap do FastMCP)
#    Precisamos mockar as dependências pesadas antes de importar
_mcp_server_path = os.path.join(_project_root, "interface", "mcp_server.py")
import types
mcp_server = None


class TestMCPServerExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global mcp_server
        cls._saved_modules = {
            mod: sys.modules.get(mod)
            for mod in [
                "mcp", "mcp.server", "mcp.server.fastmcp",
                "core.middleware", "core", "services",
                "interface", "interface.mcp_server",
            ]
        }

        if "mcp.server.fastmcp" not in sys.modules:
            _mcp_pkg = types.ModuleType("mcp")
            _mcp_server_pkg = types.ModuleType("mcp.server")
            _mcp_fastmcp = types.ModuleType("mcp.server.fastmcp")
            _mcp_fastmcp.FastMCP = type("FastMCP", (), {})
            sys.modules["mcp"] = _mcp_pkg
            sys.modules["mcp.server"] = _mcp_server_pkg
            sys.modules["mcp.server.fastmcp"] = _mcp_fastmcp

        if "core.middleware" not in sys.modules:
            _mw_mod = types.ModuleType("core.middleware")
            _mw_mod.GrafoConcierge = type("GrafoConcierge", (), {})
            sys.modules["core.middleware"] = _mw_mod

        if "core" not in sys.modules:
            _core_mod = types.ModuleType("core")
            _core_mod.__path__ = [os.path.join(_project_root, "core")]
            sys.modules["core"] = _core_mod
        elif not hasattr(sys.modules["core"], "__path__"):
            sys.modules["core"].__path__ = [os.path.join(_project_root, "core")]

        if "services" not in sys.modules:
            _svc_mod = types.ModuleType("services")
            _svc_mod.__path__ = [os.path.join(_project_root, "services")]
            _svc_mod.JanitorService = type("JanitorService", (), {})
            sys.modules["services"] = _svc_mod
        elif not hasattr(sys.modules["services"], "__path__"):
            sys.modules["services"].__path__ = [os.path.join(_project_root, "services")]

        _ms_spec = importlib.util.spec_from_file_location(
            "interface.mcp_server", _mcp_server_path,
        )
        _ms_mod = importlib.util.module_from_spec(_ms_spec)
        sys.modules["interface.mcp_server"] = _ms_mod

        if "interface" not in sys.modules:
            _iface_mod = types.ModuleType("interface")
            _iface_mod.__path__ = [os.path.join(_project_root, "interface")]
            sys.modules["interface"] = _iface_mod
        elif not hasattr(sys.modules["interface"], "__path__"):
            sys.modules["interface"].__path__ = [os.path.join(_project_root, "interface")]

        _ms_spec.loader.exec_module(_ms_mod)
        mcp_server = _ms_mod

    @classmethod
    def tearDownClass(cls):
        global mcp_server
        for mod, prev in cls._saved_modules.items():
            if prev is None:
                sys.modules.pop(mod, None)
            else:
                sys.modules[mod] = prev
        mcp_server = sys.modules.get("interface.mcp_server")
    def setUp(self):
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
        self._orig_db = getattr(mcp_server, "db_manager", None)
        self._orig_cp = getattr(mcp_server, "checkpointer", None)
        self._orig_gr = getattr(mcp_server, "graph_rag", None)
        mcp_server.db_manager = self.db_manager
        mcp_server.checkpointer = AgnosticCheckpointer(self.db_manager)
        mcp_server.graph_rag = GraphRAGEngine(self.db_manager)

    def tearDown(self):
        mcp_server.db_manager = self._orig_db
        mcp_server.checkpointer = self._orig_cp
        mcp_server.graph_rag = self._orig_gr
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                wal_path = self.db_path + ext
                if os.path.exists(wal_path):
                    os.unlink(wal_path)
        except OSError:
            pass

    def test_mcp_tool_agent_save_and_get_checkpoint(self):
        """Valida a ferramenta MCP agent_save_checkpoint e agent_get_checkpoint."""
        agent_id = "test_mcp_agent"
        session_id = "sess_mcp_42"
        checkpoint_id = "step_mcp_1"
        state_dict = {"status": "running", "step_count": 10}

        # Executa a ferramenta MCP de salvamento
        save_response_json = mcp_server.agent_save_checkpoint(
            agent_id=agent_id,
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            state_dict=state_dict,
        )

        response_data = json.loads(save_response_json)
        self.assertTrue(response_data["success"])
        self.assertIn("saved successfully", response_data["message"])

        # Executa a ferramenta MCP de recuperação
        retrieved_state = mcp_server.agent_get_checkpoint(
            agent_id=agent_id,
            session_id=session_id,
            checkpoint_id=checkpoint_id,
        )

        self.assertEqual(retrieved_state["status"], "running")
        self.assertEqual(retrieved_state["step_count"], 10)

    def test_mcp_tool_agent_list_checkpoints(self):
        """Valida a listagem cronológica através da ferramenta MCP agent_list_checkpoints."""
        agent_id = "chronos_agent"
        session_id = "sess_chronos_1"

        # Salva checkpoints sequenciais
        mcp_server.agent_save_checkpoint(agent_id, session_id, "init", {"v": 1})
        mcp_server.agent_save_checkpoint(agent_id, session_id, "run", {"v": 2})

        # Recupera a lista via ferramenta MCP
        timeline = mcp_server.agent_list_checkpoints(agent_id, session_id)

        self.assertEqual(len(timeline), 2)
        checkpoint_ids = [item["checkpoint_id"] for item in timeline]
        self.assertEqual(checkpoint_ids, ["init", "run"])

    def test_mcp_tool_concierge_get_call_chain(self):
        """Valida que a ferramenta MCP concierge_get_call_chain resolve dependências recursivas sobre nodes e edges."""
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
        self.assertNotIn("index.js", call_chain)


if __name__ == "__main__":
    unittest.main()
