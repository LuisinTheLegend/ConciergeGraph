import os

file_path = r"tests\test_call_chain_edges_nodes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix test_paths_with_wildcards_underscore_percent_and_backslash
target_wildcards = """        # Cenário com barra invertida \\
        id_win = store.create_node("proj-wildcards", label="src/win\\\\sub\\\\mod.py", node_type="MODULE")
        id_win_f = store.create_node("proj-wildcards", label="src/win\\\\sub\\\\mod.py::f", node_type="FUNCTION")
        id_win_target = store.create_node("proj-wildcards", label="src/target_win.py", node_type="MODULE")
        store.create_edge(id_win_f, id_win_target, relation_type="calls")

        chain_win = graph_rag.get_call_chain_recursive("src/win/sub/mod.py", depth_limit=5)
        assert chain_win == ["src/target_win.py"]"""

new_wildcards = """        # Cenário com barra invertida \\ (usuário busca com backslash do Windows)
        id_win = store.create_node("proj-wildcards", label="src/win/sub/mod.py", node_type="MODULE")
        id_win_f = store.create_node("proj-wildcards", label="src/win/sub/mod.py::f", node_type="FUNCTION")
        id_win_target = store.create_node("proj-wildcards", label="src/target_win.py", node_type="MODULE")
        store.create_edge(id_win_f, id_win_target, relation_type="calls")

        chain_win = graph_rag.get_call_chain_recursive(r"src\\win\\sub\\mod.py", depth_limit=5)
        assert chain_win == ["src/target_win.py"]"""

assert target_wildcards in content, "target_wildcards not found"
content = content.replace(target_wildcards, new_wildcards)

# 2. Fix test_e2e_mcp_real_server_call_chain_with_ingestion
target_e2e = """    def test_e2e_mcp_real_server_call_chain_with_ingestion(self, temp_db_env):
        \"\"\"Item 3.8: teste E2E com servidor MCP real e mineração de 3 arquivos com chamadas recursivas.\"\"\"
        import shutil
        from ingestion.orchestrator import CodebaseOrchestrator

        db_mgr: ConciergeDatabaseManager = temp_db_env["db_mgr"]
        store: SqliteStore = temp_db_env["store"]

        # Cria projeto de 3 arquivos em diretório temporário
        temp_src = tempfile.mkdtemp(prefix="e2e_src_")
        try:
            with open(os.path.join(temp_src, "alpha.py"), "w", encoding="utf-8") as f:
                f.write("import beta\\ndef fa():\\n    beta.fb()\\n")

            with open(os.path.join(temp_src, "beta.py"), "w", encoding="utf-8") as f:
                f.write("import gamma\\ndef fb():\\n    gamma.fc()\\n")

            with open(os.path.join(temp_src, "gamma.py"), "w", encoding="utf-8") as f:
                f.write("def fc():\\n    print('end')\\n")

            # Minera o projeto via CodebaseOrchestrator com GRAFO_LLM_MODEL=none
            old_llm_model = os.environ.get("GRAFO_LLM_MODEL")
            os.environ["GRAFO_LLM_MODEL"] = "none"
            try:
                orch = CodebaseOrchestrator(store, project_root=temp_src)
                p_uuid = orch.ingest_codebase(temp_src)
            finally:
                if old_llm_model is not None:
                    os.environ["GRAFO_LLM_MODEL"] = old_llm_model
                else:
                    os.environ.pop("GRAFO_LLM_MODEL", None)

            # Injeta o db_manager e graph_rag no módulo do servidor MCP
            mcp_server.db_manager = db_mgr
            mcp_server.graph_rag = GraphRAGEngine(db_mgr)

            # Executa chamada via ferramenta pública MCP concierge_get_call_chain
            result_chain = mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5)

            # Deve conter beta.py e gamma.py, sem alpha.py
            assert "beta.py" in result_chain
            assert "gamma.py" in result_chain
            assert "alpha.py" not in result_chain

            # Cria um segundo projeto que possui o mesmo arquivo 'alpha.py'
            p2_uuid = "proj-e2e-second"
            store.create_project(uuid=p2_uuid, folder_name="second_project")
            store.create_node(p2_uuid, label="alpha.py", node_type="MODULE")

            # Chamada sem project_identifier agora deve falhar por ambiguidade inter-projeto
            with pytest.raises(ValueError) as exc:
                mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5)
            assert "ambiguous" in str(exc.value).lower()

            # Chamada especificando o project_identifier do primeiro projeto deve resolver com sucesso
            resolved_p1 = mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5, project_identifier=p_uuid)
            assert "beta.py" in resolved_p1
            assert "gamma.py" in resolved_p1
        finally:
            shutil.rmtree(temp_src, ignore_errors=True)"""

new_e2e = """    def test_e2e_mcp_real_server_call_chain_with_ingestion(self, temp_db_env):
        \"\"\"Item 3.8: teste E2E com servidor MCP real e mineração de 3 arquivos com chamadas recursivas.\"\"\"
        import shutil
        from ingestion.orchestrator import IngestionManager
        from storage.vector_store import ChromaVectorStore
        from core.embeddings import EmbeddingManager

        db_mgr: ConciergeDatabaseManager = temp_db_env["db_mgr"]
        store: SqliteStore = temp_db_env["store"]

        # Cria projeto de 3 arquivos em diretório temporário
        temp_src = tempfile.mkdtemp(prefix="e2e_src_")
        temp_chroma = tempfile.mkdtemp(prefix="e2e_chroma_")
        p_uuid = "proj-e2e-real-mcp"
        try:
            with open(os.path.join(temp_src, "alpha.py"), "w", encoding="utf-8") as f:
                f.write("def fa():\\n    fb()\\n")

            with open(os.path.join(temp_src, "beta.py"), "w", encoding="utf-8") as f:
                f.write("def fb():\\n    fc()\\n")

            with open(os.path.join(temp_src, "gamma.py"), "w", encoding="utf-8") as f:
                f.write("def fc():\\n    pass\\n")

            store.create_project(uuid=p_uuid, folder_name="e2e_real_proj")

            # Minera o projeto via IngestionManager com GRAFO_LLM_MODEL=none
            old_llm_model = os.environ.get("GRAFO_LLM_MODEL")
            os.environ["GRAFO_LLM_MODEL"] = "none"
            try:
                embedder = EmbeddingManager(sqlite_store=store)
                vector_store = ChromaVectorStore(
                    persist_dir=temp_chroma,
                    collection_name="e2e_call_chain_coll",
                    embedding_manager=embedder,
                )
                ingestion_mgr = IngestionManager(
                    sqlite_store=store,
                    vector_store=vector_store,
                    embedding_manager=embedder,
                    summarizer=None,
                )
                ingestion_res = ingestion_mgr.mine(p_uuid, temp_src)
                assert ingestion_res.files_processed == 3
            finally:
                if old_llm_model is not None:
                    os.environ["GRAFO_LLM_MODEL"] = old_llm_model
                else:
                    os.environ.pop("GRAFO_LLM_MODEL", None)

            # Injeta o db_manager e graph_rag no módulo do servidor MCP
            mcp_server.db_manager = db_mgr
            mcp_server.graph_rag = GraphRAGEngine(db_mgr)

            # Executa chamada via ferramenta pública MCP concierge_get_call_chain
            result_chain = mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5)

            # Deve conter beta.py e gamma.py, sem alpha.py
            assert "beta.py" in result_chain
            assert "gamma.py" in result_chain
            assert "alpha.py" not in result_chain

            # Cria um segundo projeto que possui o mesmo arquivo 'alpha.py'
            p2_uuid = "proj-e2e-second"
            store.create_project(uuid=p2_uuid, folder_name="second_project")
            store.create_node(p2_uuid, label="alpha.py", node_type="MODULE")

            # Chamada sem project_identifier agora deve falhar por ambiguidade inter-projeto
            with pytest.raises(ValueError) as exc:
                mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5)
            assert "ambiguous" in str(exc.value).lower()

            # Chamada especificando o project_identifier do primeiro projeto deve resolver com sucesso
            resolved_p1 = mcp_server.concierge_get_call_chain(start_node="alpha.py", depth_limit=5, project_identifier=p_uuid)
            assert "beta.py" in resolved_p1
            assert "gamma.py" in resolved_p1
        finally:
            shutil.rmtree(temp_src, ignore_errors=True)
            shutil.rmtree(temp_chroma, ignore_errors=True)"""

assert target_e2e in content, "target_e2e not found"
content = content.replace(target_e2e, new_e2e)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated tests/test_call_chain_edges_nodes.py with IngestionManager and wildcards fix.")

