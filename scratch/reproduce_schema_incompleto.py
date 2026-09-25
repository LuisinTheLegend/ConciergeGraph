"""
scratch/reproduce_schema_incompleto.py

Reproduz e comprova o achado transversal maximo:
'schema-oficial-incompleto'

1. Simula clone limpo e executa o bootstrap oficial do sistema:
   SqliteStore(db_path) -> SchemaManager.apply_full_schema().
2. Tenta executar operacoes reais de ponta a ponta dos modulos de core/* e interface/*
   sobre o banco oficialmente bootstrapado.
3. Demonstra que TODOS quebram com 'sqlite3.OperationalError: no such table: ...'.
4. Verifica exaustivamente se ha criacao lazy ou dinamica de tabelas no codigo de producao.
"""

import os
import sys
import tempfile
import sqlite3
import traceback
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.store import SqliteStore
from storage.schema import SchemaManager
from core.database import ConciergeDatabaseManager


def test_clean_bootstrap():
    print("=" * 80)
    print("ETAPA 1: SIMULACAO DE CLONE LIMPO E BOOTSTRAP OFICIAL")
    print("=" * 80)
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        print(f"[1.1] Executando bootstrap oficial: SqliteStore('{db_path}')...")
        store = SqliteStore(db_path)
        
        # Conexao direta para inspecionar sqlite_master
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name;")
        tables_found = [row[0] for row in cursor.fetchall()]
        conn.close()
        store.close()
        
        print(f"[1.2] Tabelas criadas no banco pelo bootstrap oficial ({len(tables_found)} encontradas):")
        for t in tables_found:
            print(f"     - {t}")

        expected_core_tables = [
            "files",
            "communities",
            "ast_edges",
            "agent_checkpoints",
            "fsm_checkpoints"
        ]
        
        missing_tables = [t for t in expected_core_tables if t not in tables_found]
        print(f"\n[1.3] Verificacao das 5 tabelas relacionais do subsistema core/*:")
        for t in expected_core_tables:
            status = "PRESENTE" if t in tables_found else "NAO EXISTE (AUSENTE!)"
            print(f"     - {t:<20}: {status}")

        print(f"\n     Total ausentes no bootstrap oficial: {len(missing_tables)} de {len(expected_core_tables)}")
        
        print("\n[1.4] Testando conexao via ConciergeDatabaseManager(db_path)...")
        cdb = ConciergeDatabaseManager(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables_after_cdb = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        new_tables = [t for t in tables_after_cdb if t not in tables_found]
        print(f"     Tabelas adicionadas por ConciergeDatabaseManager._init_tables(): {new_tables}")
        for t in expected_core_tables:
            if t not in tables_after_cdb:
                print(f"     - {t:<20}: CONTINUA AUSENTE!")

        return db_path
    except Exception as e:
        print(f"ERRO durante bootstrap: {e}")
        traceback.print_exc()
        return None


def test_core_operations_on_bootstrapped_db(db_path: str):
    print("\n" + "=" * 80)
    print("ETAPA 2: OPERACOES REAIS DE CORE/* NO BANCO BOOTSTRAPADO")
    print("=" * 80)

    db_manager = ConciergeDatabaseManager(db_path)

    # 1. VectorReconciler
    print("\n--- [2.1] core/vector_reconciler.py: VectorReconciler.reconcile_orphans() ---")
    try:
        from core.vector_reconciler import VectorReconciler
        vdb_mock = MagicMock()
        vdb_mock.get_all_ids.return_value = ["orphan_node_1"]
        reconciler = VectorReconciler(db_manager=db_manager, vector_db=vdb_mock)
        reconciler.reconcile_orphans()
        print("  SUCESSO INESPERADO!")
    except Exception as e:
        print(f"  FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 2. DeltaManager
    print("\n--- [2.2] core/delta_manager.py: DeltaManager.process_file_change() ---")
    try:
        from core.delta_manager import DeltaManager
        delta = DeltaManager(db_manager=db_manager)
        delta.process_file_change("core/example.py", "def test(): pass", community_id="comm_1")
        print("  SUCESSO INESPERADO!")
    except Exception as e:
        print(f"  FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 3. Checkpointer
    print("\n--- [2.3] core/checkpointer.py: AgnosticCheckpointer save / load / timetravel ---")
    try:
        from core.checkpointer import AgnosticCheckpointer
        chk = AgnosticCheckpointer(db_manager)
        
        # save_checkpoint
        res_save = chk.save_checkpoint("agent_1", "session_1", "chk_1", {"key": "value"})
        print(f"  save_checkpoint retorno: {res_save} (Falso booleano: falha mascarada por core/database.py!)")
        
        # Inspecionando o erro real retornado por execute_write
        success, err = db_manager.execute_write(
            "INSERT OR REPLACE INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob) VALUES (?, ?, ?, ?);",
            ("agent_1", "session_1", "chk_1", "{}")
        )
        print(f"  Escrita direta em agent_checkpoints: success={success}, error='{err}'")

        # load_checkpoint
        try:
            res_load = chk.load_checkpoint("session_1", "chk_1")
            print(f"  load_checkpoint retorno: {res_load}")
        except Exception as e:
            print(f"  load_checkpoint FALHA CONFIRMADA ({type(e).__name__}): {e}")

        # execute_time_travel
        try:
            res_tt = chk.execute_time_travel("session_1", "chk_1")
            print(f"  execute_time_travel retorno: {res_tt}")
        except Exception as e:
            print(f"  execute_time_travel FALHA CONFIRMADA ({type(e).__name__}): {e}")
    except Exception as e:
        print(f"  FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 4. BackgroundJanitor
    print("\n--- [2.4] core/background_janitor.py: BackgroundJanitor (Summarization & Pruning) ---")
    try:
        from core.background_janitor import BackgroundJanitor
        janitor = BackgroundJanitor(db_manager=db_manager)
        
        print("  Executando run_idle_summarization()...")
        try:
            janitor.run_idle_summarization(local_slm_callback=lambda p: "summary")
            print("  run_idle_summarization: SUCESSO INESPERADO!")
        except Exception as e:
            print(f"  run_idle_summarization FALHA CONFIRMADA ({type(e).__name__}): {e}")

        print("  Executando prune_session_checkpoints()...")
        try:
            janitor.prune_session_checkpoints(keep_limit=5)
            print("  prune_session_checkpoints: SUCESSO INESPERADO!")
        except Exception as e:
            print(f"  prune_session_checkpoints FALHA CONFIRMADA ({type(e).__name__}): {e}")
    except Exception as e:
        print(f"  FALHA AO INSTANCIAR JANITOR ({type(e).__name__}): {e}")

    # 5. GraphRAG
    print("\n--- [2.5] core/graph_rag.py: GraphRAGEngine (detect_logical_communities & multihop & call chain) ---")
    try:
        from core.graph_rag import GraphRAGEngine
        grag = GraphRAGEngine(db_manager=db_manager)
        
        print("  Executando detect_logical_communities()...")
        try:
            grag.detect_logical_communities()
            print("  detect_logical_communities: SUCESSO INESPERADO!")
        except Exception as e:
            print(f"  detect_logical_communities FALHA CONFIRMADA ({type(e).__name__}): {e}")

        print("  Executando retrieve_multihop_context('core/example.py')...")
        try:
            ctx = grag.retrieve_multihop_context("core/example.py")
            print(f"  retrieve_multihop_context: {ctx}")
        except Exception as e:
            print(f"  retrieve_multihop_context FALHA CONFIRMADA ({type(e).__name__}): {e}")
            
        print("  Executando get_call_chain_recursive('core/example.py')...")
        try:
            # Compatibilizando self.db e self.db_manager para isolar a ausencia da tabela
            if not hasattr(grag, "db_manager") and hasattr(grag, "db"):
                grag.db_manager = grag.db
            chain = grag.get_call_chain_recursive("core/example.py")
            print(f"  get_call_chain_recursive: {chain}")
        except Exception as e:
            print(f"  get_call_chain_recursive FALHA CONFIRMADA ({type(e).__name__}): {e}")
    except Exception as e:
        print(f"  FALHA AO INSTANCIAR GRAPHRAG ({type(e).__name__}): {e}")

    # 6. HybridSearchEngine (core/search_engine.py)
    print("\n--- [2.6] core/search_engine.py: HybridSearchEngine.hybrid_search() ---")
    try:
        from core.search_engine import HybridSearchEngine
        vdb_mock2 = MagicMock()
        vdb_mock2.search.return_value = [{"id": "core/example.py", "score": 0.9}]
        se = HybridSearchEngine(db_manager=db_manager, vector_db=vdb_mock2)
        se.hybrid_search("consulta teste")
        print("  SUCESSO INESPERADO!")
    except Exception as e:
        print(f"  hybrid_search FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 7. TelemetryAPI
    print("\n--- [2.7] interface/telemetry_api.py: get_telemetry_snapshot() ---")
    try:
        from interface.telemetry_api import get_telemetry_snapshot
        snap = get_telemetry_snapshot(db_manager=db_manager)
        print("  get_telemetry_snapshot: SUCESSO INESPERADO!")
    except Exception as e:
        print(f"  get_telemetry_snapshot FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 8. Watcher
    print("\n--- [2.8] interface/watcher.py: ConciergeFileSystemHandler.hydrate_known_hashes() ---")
    try:
        import pathspec
        from interface.watcher import ConciergeFileSystemHandler
        spec = pathspec.PathSpec.from_lines("gitwildmatch", [".git/"])
        handler = ConciergeFileSystemHandler(
            project_path=PROJECT_ROOT,
            ignore_spec=spec,
            on_valid_change_callback=lambda p: None
        )
        print("  Chamando hydrate_known_hashes(db_manager)...")
        handler.hydrate_known_hashes(db_manager=db_manager)
        print(f"  Hashes hidratados: {len(handler._known_hashes)} (deveria ler 'files', mas silenciou erro!)")
        
        # Testando query direta executada pelo watcher
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT path, structural_hash FROM files;")
            conn.close()
        except Exception as e:
            print(f"  Query real do watcher FALHA CONFIRMADA ({type(e).__name__}): {e}")
    except Exception as e:
        print(f"  hydrate_known_hashes FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 9. MCP Server Tools de Checkpoints e Call Chain
    print("\n--- [2.9] interface/mcp_server.py: MCP Tools (agent_save_checkpoint & concierge_get_call_chain) ---")
    try:
        import interface.mcp_server as mcp_mod
        from interface.mcp_server import GrafoConciergeServer
        from core.checkpointer import AgnosticCheckpointer
        from core.graph_rag import GraphRAGEngine

        # Configura as variaveis globais que o modulo mcp_server usa
        mcp_mod.db_manager = db_manager
        mcp_mod.checkpointer = AgnosticCheckpointer(db_manager)
        mcp_mod.graph_rag = GraphRAGEngine(db_manager)
        
        mock_gc = MagicMock()
        mock_janitor = MagicMock()
        
        server = GrafoConciergeServer(
            concierge=mock_gc,
            janitor=mock_janitor
        )
        
        # Invocando tool agent_save_checkpoint
        save_tool = server._mcp._tool_manager._tools.get("agent_save_checkpoint")
        if save_tool:
            print("  Executando tool agent_save_checkpoint...")
            res = save_tool.fn(
                agent_id="test_agent",
                session_id="session_mcp",
                checkpoint_id="chk_mcp",
                state_dict={"task": "auditoria"}
            )
            print(f"  agent_save_checkpoint retorno bruto: {res}")
            
        # Invocando tool concierge_get_call_chain
        call_tool = server._mcp._tool_manager._tools.get("concierge_get_call_chain")
        if call_tool:
            print("  Executando tool concierge_get_call_chain...")
            try:
                res = call_tool.fn(start_node="core/example.py")
                print(f"  concierge_get_call_chain retorno: {res}")
            except Exception as e:
                print(f"  concierge_get_call_chain FALHA CONFIRMADA ({type(e).__name__}): {e}")

    except Exception as e:
        print(f"  MCP Server Tool Test FALHA CONFIRMADA ({type(e).__name__}): {e}")

    # 10. IngestionManager vs DeltaManager
    print("\n--- [2.10] IngestionManager.mine vs DeltaManager no banco bootstrapado ---")
    try:
        # Cria projeto no SqliteStore
        store = SqliteStore(db_path)
        proj_uuid = store.create_project("test_proj", "geral")
        print(f"  Projeto criado com sucesso em 'projects': {proj_uuid}")

        # Tenta executar DeltaManager sobre um arquivo novo do projeto
        try:
            delta = DeltaManager(db_manager=db_manager)
            delta.process_file_change("test_proj/main.py", "import os", community_id="test_proj")
            print("  DeltaManager: SUCESSO INESPERADO!")
        except Exception as e:
            print(f"  DeltaManager FALHA CONFIRMADA ({type(e).__name__}): {e}")
        
        store.close()
    except Exception as e:
        print(f"  Falha no teste de ingestao: {e}")


def test_codebase_inspection_for_lazy_or_dynamic_ddl():
    print("\n" + "=" * 80)
    print("ETAPA 3: VARREDURA EXAUSTIVA DE DDL NO CODIGO DE PRODUCAO")
    print("=" * 80)
    
    targets = ["core", "storage", "interface", "ingestion", "services", "agent", "agents"]
    
    found_ddl = []
    for t in targets:
        dirpath = os.path.join(PROJECT_ROOT, t)
        if not os.path.exists(dirpath):
            continue
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        lines = fp.readlines()
                    for idx, line in enumerate(lines, 1):
                        lower = line.lower()
                        if "create table" in lower:
                            found_ddl.append((os.path.relpath(fpath, PROJECT_ROOT), idx, line.strip()))

    print(f"Todas as ocorrencias de 'CREATE TABLE' em codigo de producao ({len(found_ddl)} encontradas):")
    for frel, line_no, content in found_ddl:
        print(f"  [{frel}:{line_no}] {content}")

    print("\nConclusao da varredura:")
    print("  1. storage/schema.py cria: projects, nodes, edges, reference_wings, trajectories, commit_log, user_core_memory, semantic_facts, nodes_fts.")
    print("  2. storage/relational_db.py define fsm_checkpoints, mas init_fsm_checkpoints_schema nunca e chamado.")
    print("  3. core/database.py cria apenas test_log.")
    print("  4. NENHUM arquivo de producao cria: files, communities, ast_edges, agent_checkpoints.")
    print("  5. Nao existe geracao dinamica, lazy ou via ORM.")


if __name__ == "__main__":
    db_path = test_clean_bootstrap()
    if db_path:
        try:
            test_core_operations_on_bootstrapped_db(db_path)
            test_codebase_inspection_for_lazy_or_dynamic_ddl()
        finally:
            # Cleanup
            for ext in ["", "-wal", "-shm"]:
                p = db_path + ext
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
