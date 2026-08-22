"""
tests/test_e2e_concierge_integration.py — Grande Auditoria Fim-a-Fim (E2E)

Suíte de Integração Master que orquestra as 7 fatias de sobrevivência
para comprovar que todos os subsistemas se comunicam perfeitamente sem
travas, vazamentos ou inconsistências sob um fluxo dinâmico real de
dados em cascata:

  Passo A: Ingestão de Código & Delta Sync (SDD-04)
  Passo B: Varredura Frugal do Janitor (SDD-06)
  Passo C: Navegação Topológica Recursiva com Loop Cíclico (SDD-06)
  Passo D: Busca Híbrida e Auto-Cura de Vetores (SDD-05)
  Passo E: Checkpointing de Sessão e Time-Travel (SDD-07)
  Passo F: Validação de Payload das Novas Ferramentas MCP (SDD-08)
"""

import unittest
import os
import sys
import importlib
import tempfile
import json
import types


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

# 3) core.delta_manager
_dm_spec = importlib.util.spec_from_file_location(
    "core.delta_manager",
    os.path.join(_project_root, "core", "delta_manager.py"),
)
_dm_mod = importlib.util.module_from_spec(_dm_spec)
sys.modules["core.delta_manager"] = _dm_mod
_dm_spec.loader.exec_module(_dm_mod)
DeltaManager = _dm_mod.DeltaManager

# 4) core.search_engine
_se_spec = importlib.util.spec_from_file_location(
    "core.search_engine",
    os.path.join(_project_root, "core", "search_engine.py"),
)
_se_mod = importlib.util.module_from_spec(_se_spec)
sys.modules["core.search_engine"] = _se_mod
_se_spec.loader.exec_module(_se_mod)
HybridSearchEngine = _se_mod.HybridSearchEngine

# 5) core.vector_reconciler
_vr_spec = importlib.util.spec_from_file_location(
    "core.vector_reconciler",
    os.path.join(_project_root, "core", "vector_reconciler.py"),
)
_vr_mod = importlib.util.module_from_spec(_vr_spec)
sys.modules["core.vector_reconciler"] = _vr_mod
_vr_spec.loader.exec_module(_vr_mod)
VectorReconciler = _vr_mod.VectorReconciler

# 6) core.graph_rag
_gr_spec = importlib.util.spec_from_file_location(
    "core.graph_rag",
    os.path.join(_project_root, "core", "graph_rag.py"),
)
_gr_mod = importlib.util.module_from_spec(_gr_spec)
sys.modules["core.graph_rag"] = _gr_mod
_gr_spec.loader.exec_module(_gr_mod)
GraphRAGEngine = _gr_mod.GraphRAGEngine

# 7) core.background_janitor
_bj_spec = importlib.util.spec_from_file_location(
    "core.background_janitor",
    os.path.join(_project_root, "core", "background_janitor.py"),
)
_bj_mod = importlib.util.module_from_spec(_bj_spec)
sys.modules["core.background_janitor"] = _bj_mod
_bj_spec.loader.exec_module(_bj_mod)
BackgroundJanitor = _bj_mod.BackgroundJanitor

# 8) core.checkpointer
_cp_spec = importlib.util.spec_from_file_location(
    "core.checkpointer",
    os.path.join(_project_root, "core", "checkpointer.py"),
)
_cp_mod = importlib.util.module_from_spec(_cp_spec)
sys.modules["core.checkpointer"] = _cp_mod
_cp_spec.loader.exec_module(_cp_mod)
AgnosticCheckpointer = _cp_mod.AgnosticCheckpointer

# 9) interface.mcp_server (stub das dependências pesadas)
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
    sys.modules["core"] = types.ModuleType("core")

if "services" not in sys.modules:
    _svc_mod = types.ModuleType("services")
    _svc_mod.JanitorService = type("JanitorService", (), {})
    sys.modules["services"] = _svc_mod

_ms_spec = importlib.util.spec_from_file_location(
    "interface.mcp_server",
    os.path.join(_project_root, "interface", "mcp_server.py"),
)
_ms_mod = importlib.util.module_from_spec(_ms_spec)
sys.modules["interface.mcp_server"] = _ms_mod

if "interface" not in sys.modules:
    sys.modules["interface"] = types.ModuleType("interface")

_ms_spec.loader.exec_module(_ms_mod)
mcp_server = _ms_mod


class MockVectorDatabase:
    """Mock em memória para simular o comportamento do Qdrant de forma isolada."""
    def __init__(self):
        self.storage = {}

    def insert(self, vector_id: str, payload: dict):
        self.storage[vector_id] = payload

    def search(self, query_text: str, limit: int = 5):
        results = []
        for vid in list(self.storage.keys())[:limit]:
            results.append({"id": vid, "score": 0.95})
        return results

    def get_all_ids(self):
        return list(self.storage.keys())

    def delete_batch(self, ids_list):
        deleted = []
        for vid in ids_list:
            if vid in self.storage:
                del self.storage[vid]
                deleted.append(vid)
        return deleted


class TestConciergeSovereignE2EAudit(unittest.TestCase):
    """
    Suíte de Teste de Integração Fim-a-Fim (E2E) e Auditoria de Concorrencia.
    Esta classe orquestra as 7 fatias de sobrevivência para garantir que todos
    os subsistemas se comuniquem perfeitamente sem travas, vazamentos ou inconsistências.
    """
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # 1. Inicializa Fila de Escrita Serializada (WAL) — Fase 1 (SDD-02)
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # 2. Inicializa as Tabelas Relacionais do SQLite WAL (DDR e DDL concorrentes)
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, content TEXT, ssh_hash TEXT, is_dirty INTEGER, community_id TEXT"
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
        )

        # 3. Instancia os Managers e Engines Reais
        self.delta_manager = DeltaManager(self.db_manager)
        self.graph_rag = GraphRAGEngine(self.db_manager)
        self.janitor = BackgroundJanitor(self.db_manager)
        self.checkpointer = AgnosticCheckpointer(self.db_manager)

        # 4. Instancia Banco Vetorial Mock e Motores de Busca
        self.vector_db = MockVectorDatabase()
        self.search_engine = HybridSearchEngine(self.db_manager, self.vector_db)
        self.reconciler = VectorReconciler(self.db_manager, self.vector_db)

        # 5. Injeta instâncias ativas no escopo de módulo do Servidor MCP para Auditoria de Ferramentas
        mcp_server.db_manager = self.db_manager
        mcp_server.checkpointer = self.checkpointer
        mcp_server.graph_rag = self.graph_rag

    def tearDown(self):
        # Desliga a fila de escritas serializadas de forma graciosa
        self.write_queue.queue.put(None)
        self.write_queue.join(timeout=10)
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
            for ext in ("-wal", "-shm"):
                wal_path = self.db_path + ext
                if os.path.exists(wal_path):
                    os.unlink(wal_path)
        except OSError:
            pass

    def test_e2e_flow_full_lifecycle_and_communication(self):
        """
        AUDITORIA FIM-A-FIM: Executa o fluxo de dados em cascata provando que
        as comunicações entre Delta Manager, GraphRAG, Checkpointer, Busca Vetorial
        e as pontes públicas do Servidor MCP operam em sintonia perfeita.
        """
        # ==========================================
        # PASSO A: Ingestão de Código & Delta Sync (Fase 2 / SDD-04)
        # ==========================================
        community_id = "core_system"
        file_path_1 = "core/main.py"
        file_path_2 = "core/utils.py"

        # Cria registros iniciais das comunidades
        self.db_manager.write_query(
            "INSERT INTO communities (id, summary_text, is_dirty) VALUES (?, 'Old Summary', 1);",
            (community_id,)
        )

        code_1 = "import sys\n\ndef run():\n    return 'OK'\n"
        code_2 = "def calculate_hash(data):\n    return hash(data)\n"

        # Processa alterações de arquivos via DeltaManager (SSH hashes gerados)
        struct_change_1 = self.delta_manager.process_file_change(file_path_1, code_1, community_id)
        struct_change_2 = self.delta_manager.process_file_change(file_path_2, code_2, community_id)

        self.assertTrue(struct_change_1, "Arquivo inédito deve registrar mudança estrutural.")
        self.assertTrue(struct_change_2, "Arquivo inédito deve registrar mudança estrutural.")

        # Verifica se o banco de dados WAL capturou as flags de sujeira (DIRTY = 1)
        comm_dirty = self.db_manager.read_query("SELECT is_dirty FROM communities WHERE id = ?;", (community_id,))
        self.assertEqual(comm_dirty[0][0], 1, "A comunidade deve estar marcada como DIRTY.")

        # Simula alteração estrita de lógica interna no arquivo 1 (não altera assinatura/estruturas)
        code_1_logic_only = "import sys\n\ndef run():\n    return 'Logic Changed'  # logic change inside def\n"
        struct_change_logic = self.delta_manager.process_file_change(file_path_1, code_1_logic_only, community_id)

        self.assertFalse(struct_change_logic, "Mudança de lógica interna não deveria invalidar o grafo (SSH idêntico).")

        # ==========================================
        # PASSO B: Varredura Frugal do Janitor (Fase 2 / SDD-06)
        # ==========================================
        # Com a comunidade marcada como DIRTY, o background janitor deve rodar de forma preguiçosa (Lazy Summarization)
        slm_calls = 0
        def local_slm_mock(payload):
            nonlocal slm_calls
            slm_calls += 1
            return f"Summary of {len(payload.splitlines())} lines of code structure."

        logs = self.janitor.run_idle_summarization(local_slm_mock)

        self.assertEqual(slm_calls, 1, "A SLM local deve ser executada para compilar a comunidade suja.")
        self.assertIn(community_id, logs, "O log de auditoria do Janitor deve registrar o processamento da comunidade.")

        # Garante que as flags de sujeira foram devidamente resetadas após a compilação
        comm_state = self.db_manager.read_query("SELECT is_dirty, summary_text FROM communities WHERE id = ?;", (community_id,))
        self.assertEqual(comm_state[0][0], 0, "A flag is_dirty da comunidade deve retornar para 0.")
        self.assertTrue(comm_state[0][1].startswith("Summary of"), "O resumo conceitual deve ser salvo no banco local.")

        # ==========================================
        # PASSO C: Navegação Topológica Recursiva (Fase 2 / SDD-06)
        # ==========================================
        # Registra dependências de chamadas AST de forma cruzada
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/main.py', 'core/utils.py');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/utils.py', 'core/db_driver.py');")
        self.db_manager.write_query("INSERT INTO ast_edges VALUES ('core/db_driver.py', 'core/main.py');")  # LOOP CÍCLICO!

        # Varre recursivamente a partir do main.py (deve ignorar o loop cíclico graças ao guard de depth)
        call_chain = self.graph_rag.get_call_chain_recursive("core/main.py", depth_limit=4)

        self.assertEqual(len(call_chain), 2, "A busca do GraphRAG deve mapear exatamente os 2 nós filhos interconectados.")
        self.assertIn("core/utils.py", call_chain)
        self.assertIn("core/db_driver.py", call_chain)

        # ==========================================
        # PASSO D: Busca Híbrida e Auto-Cura de Vetores (Fase 2 / SDD-05)
        # ==========================================
        # Insere dados legítimos e órfãos no banco vetorial
        self.vector_db.insert("core/main.py", {"text": "main"})
        self.vector_db.insert("core/utils.py", {"text": "utils"})
        self.vector_db.insert("core/deleted_file.py", {"text": "orphan"})  # ÓRFÃO!

        # Busca híbrida com auto-cura em tempo de execução
        search_results = self.search_engine.hybrid_search("find functions", limit=5)

        returned_ids = [r["id"] for r in search_results]
        self.assertEqual(len(search_results), 2, "O Query-Time Filter deve remover o vetor órfão em tempo de execução.")
        self.assertIn("core/main.py", returned_ids)
        self.assertNotIn("core/deleted_file.py", returned_ids, "O arquivo inexistente no SQLite WAL foi limpo JIT.")

        # Limpeza física de background
        deleted_orphans = self.reconciler.reconcile_orphans()
        self.assertEqual(deleted_orphans, ["core/deleted_file.py"], "O Janitor físico deve identificar e expurgar o órfão.")
        self.assertNotIn("core/deleted_file.py", self.vector_db.get_all_ids(), "O vetor órfão deve ser extinto do Qdrant.")

        # ==========================================
        # PASSO E: Checkpointing de Sessão e Time-Travel (Fase 3 / SDD-07)
        # ==========================================
        agent_id = "hermes_core"
        session_id = "audit_session_2026"

        state_1 = {"node": "DRAFTING", "code_blocks": 5}
        state_2 = {"node": "REFACTORING", "code_blocks": 8}

        # Grava estados sequenciais
        self.checkpointer.save_checkpoint(agent_id, session_id, "checkpoint_1", state_1)
        self.checkpointer.save_checkpoint(agent_id, session_id, "checkpoint_2", state_2)

        # Lista linha do tempo cronológica
        timeline = self.checkpointer.list_checkpoints(agent_id, session_id)
        self.assertEqual(len(timeline), 2, "Deveria listar a história exata com 2 checkpoints.")
        self.assertEqual(timeline[0]["checkpoint_id"], "checkpoint_1")
        self.assertEqual(timeline[1]["checkpoint_id"], "checkpoint_2")

        # Simula o Time-Travel carregando o estado antigo para rollback de variáveis
        restored_state = self.checkpointer.get_checkpoint(agent_id, session_id, "checkpoint_1")
        self.assertEqual(restored_state["node"], "DRAFTING", "O Time-Travel deve restaurar fielmente o dicionário do agente.")

        # ==========================================
        # PASSO F: Validação de Payload das Novas Ferramentas MCP (Fase 3 / SDD-08)
        # ==========================================
        # Testa a ponte JSON-RPC pública de Checkpoint
        save_response_json = mcp_server.agent_save_checkpoint(
            agent_id=agent_id,
            session_id=session_id,
            checkpoint_id="mcp_step",
            state_dict={"api_call": True}
        )

        parsed_response = json.loads(save_response_json)
        self.assertTrue(parsed_response["success"])
        self.assertIn("saved successfully", parsed_response["message"])

        # Testa a ponte JSON-RPC pública de busca recursiva
        mcp_call_chain = mcp_server.concierge_get_call_chain(start_node="core/main.py", depth_limit=3)
        self.assertIn("core/utils.py", mcp_call_chain, "A ponte do MCP de dependências deve responder identicamente.")
        self.assertIn("core/db_driver.py", mcp_call_chain, "A ponte do MCP de dependências deve responder identicamente.")
        self.assertEqual(len(mcp_call_chain), 2)


if __name__ == "__main__":
    unittest.main()
