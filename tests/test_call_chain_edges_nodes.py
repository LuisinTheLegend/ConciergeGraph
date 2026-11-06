r"""
tests/test_call_chain_edges_nodes.py — Rodada 4.3b

Validação da travessia de call chain sobre tabelas canônicas 'nodes' e 'edges'
com escopo estrito de projeto, ciclo-segurança, e filtragem de arestas ativas.
Inclui todos os cenários normativos do Pedido 4.3b:
  - Nó STALE ou ARCHIVED ignorado (raiz e destino)
  - Início por símbolo exclui raiz e atravessa callees
  - Escape de curingas LIKE (_, %, \)
  - Ambiguidade por folder_name duplicado
  - Mensagem de ambiguidade sem nomes nem UUIDs
  - project_identifier inexistente
  - Símbolo duplicado
  - E2E real via MCP tool e mineração de 3 arquivos
"""

import os
import sqlite3
import tempfile
import pytest

from storage.schema import SchemaManager
from storage.store import SqliteStore
from core.database import ConciergeDatabaseManager
from core.graph_rag import GraphRAGEngine
from interface import mcp_server


@pytest.fixture
def temp_db_env():
    """Cria banco físico temporário populado estritamente via SchemaManager oficial."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    try:
        SchemaManager(conn).apply_full_schema()
    finally:
        conn.close()

    db_mgr = ConciergeDatabaseManager(path)
    store = SqliteStore(path)
    graph_rag = GraphRAGEngine(db_mgr)

    yield {
        "path": path,
        "db_mgr": db_mgr,
        "store": store,
        "graph_rag": graph_rag,
    }

    try:
        store.close()
    except Exception:
        pass
    for ext in ("", "-wal", "-shm"):
        p = path + ext
        if os.path.exists(p):
            try:
                os.unlink(p)
            except OSError:
                pass


class TestCallChainEdgesNodes:
    def test_linear_chain_depth_limits(self, temp_db_env):
        """Teste 1: cadeia linear A -> B -> C com depth_limit=1, 2, 5."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(
            uuid="proj-linear-111",
            folder_name="linear-project",
            primary_wing="core",
            privacy_level="INTERNAL",
            summary="Linear chain test",
        )

        id_a = store.create_node("proj-linear-111", label="src/a.py", node_type="MODULE")
        id_b = store.create_node("proj-linear-111", label="src/b.py", node_type="MODULE")
        id_c = store.create_node("proj-linear-111", label="src/c.py", node_type="MODULE")

        store.create_edge(id_a, id_b, relation_type="calls", weight=1.0)
        store.create_edge(id_b, id_c, relation_type="calls", weight=1.0)

        chain_1 = graph_rag.get_call_chain_recursive("src/a.py", depth_limit=1)
        assert chain_1 == ["src/b.py"]

        chain_2 = graph_rag.get_call_chain_recursive("src/a.py", depth_limit=2)
        assert chain_2 == ["src/b.py", "src/c.py"]

        chain_5 = graph_rag.get_call_chain_recursive("src/a.py", depth_limit=5)
        assert chain_5 == ["src/b.py", "src/c.py"]

    def test_cycle_protection_prevents_infinite_loop(self, temp_db_env):
        """Teste 2: ciclo A -> B -> A não entra em loop infinito."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(
            uuid="proj-cycle-222",
            folder_name="cycle-project",
            primary_wing="core",
        )

        id_a = store.create_node("proj-cycle-222", label="src/alpha.py", node_type="MODULE")
        id_b = store.create_node("proj-cycle-222", label="src/beta.py", node_type="MODULE")

        store.create_edge(id_a, id_b, relation_type="calls")
        store.create_edge(id_b, id_a, relation_type="calls")

        chain = graph_rag.get_call_chain_recursive("src/alpha.py", depth_limit=5)
        assert chain == ["src/beta.py"]

    def test_nonexistent_root_node_raises_clear_error(self, temp_db_env):
        """Teste 3: nó raiz não existente devolve erro claro (não lista vazia silenciosa)."""
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        with pytest.raises(ValueError) as excinfo:
            graph_rag.get_call_chain_recursive("src/ghost.py", depth_limit=5)
        assert "not found" in str(excinfo.value).lower()

    def test_ambiguous_node_across_projects_requires_identifier(self, temp_db_env):
        """Teste 4: múltiplos nós com mesmo label em projetos distintos exige project_identifier;
        mensagem de erro não contém nomes de pastas nem UUIDs dos projetos candidatos."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        # Projeto 1
        store.create_project(uuid="uuid-proj-1", folder_name="repo-one", primary_wing="wing1")
        id_p1_main = store.create_node("uuid-proj-1", label="src/main.py", node_type="MODULE")
        id_p1_util = store.create_node("uuid-proj-1", label="src/util_one.py", node_type="MODULE")
        store.create_edge(id_p1_main, id_p1_util, relation_type="calls")

        # Projeto 2
        store.create_project(uuid="uuid-proj-2", folder_name="repo-two", primary_wing="wing2")
        id_p2_main = store.create_node("uuid-proj-2", label="src/main.py", node_type="MODULE")
        id_p2_util = store.create_node("uuid-proj-2", label="src/util_two.py", node_type="MODULE")
        store.create_edge(id_p2_main, id_p2_util, relation_type="calls")

        # Sem project_identifier deve recusar com erro claro informando quantidade
        with pytest.raises(ValueError) as excinfo:
            graph_rag.get_call_chain_recursive("src/main.py", depth_limit=5)
        err_msg = str(excinfo.value)
        assert "ambiguous" in err_msg.lower() or "multiple projects" in err_msg.lower()
        # Item 2d: mensagem não deve conter folder_name nem UUID
        assert "repo-one" not in err_msg
        assert "repo-two" not in err_msg
        assert "uuid-proj-1" not in err_msg
        assert "uuid-proj-2" not in err_msg

        # Com project_identifier = "repo-one" resolve projeto 1
        res_p1 = graph_rag.get_call_chain_recursive("src/main.py", depth_limit=5, project_identifier="repo-one")
        assert res_p1 == ["src/util_one.py"]

        # Com project_identifier = "uuid-proj-2" resolve projeto 2
        res_p2 = graph_rag.get_call_chain_recursive("src/main.py", depth_limit=5, project_identifier="uuid-proj-2")
        assert res_p2 == ["src/util_two.py"]

    def test_historical_valid_to_commit_edges_are_ignored(self, temp_db_env):
        """Teste 5: arestas com valid_to_commit preenchido (históricas/apagadas) são ignoradas."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-hist-555", folder_name="hist-project", primary_wing="core")
        id_a = store.create_node("proj-hist-555", label="src/caller.py", node_type="MODULE")
        id_b_old = store.create_node("proj-hist-555", label="src/old_callee.py", node_type="MODULE")
        id_b_new = store.create_node("proj-hist-555", label="src/new_callee.py", node_type="MODULE")

        store.create_edge(id_a, id_b_old, relation_type="calls", valid_to_commit="deadbeef123")
        store.create_edge(id_a, id_b_new, relation_type="calls", valid_to_commit=None)

        chain = graph_rag.get_call_chain_recursive("src/caller.py", depth_limit=5)
        assert "src/new_callee.py" in chain
        assert "src/old_callee.py" not in chain

    def test_other_relation_types_are_not_followed(self, temp_db_env):
        """Teste 6: arestas de outro relation_type (ex.: depends_on, imports) NÃO são seguidas como call_chain."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-rel-666", folder_name="rel-project", primary_wing="core")
        id_src = store.create_node("proj-rel-666", label="src/service.py", node_type="MODULE")
        id_dep = store.create_node("proj-rel-666", label="src/dependency.py", node_type="MODULE")
        id_imp = store.create_node("proj-rel-666", label="src/imported.py", node_type="MODULE")
        id_call = store.create_node("proj-rel-666", label="src/called.py", node_type="MODULE")

        store.create_edge(id_src, id_dep, relation_type="depends_on")
        store.create_edge(id_src, id_imp, relation_type="imports")
        store.create_edge(id_src, id_call, relation_type="calls")

        chain = graph_rag.get_call_chain_recursive("src/service.py", depth_limit=5)
        assert chain == ["src/called.py"]
        assert "src/dependency.py" not in chain
        assert "src/imported.py" not in chain

    def test_invalid_depth_limit_raises_clear_error(self, temp_db_env):
        """Teste 7: profundidade inválida (< 1 ou > 10, ou booleano) devolve erro claro."""
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        for invalid_depth in [0, -1, -5, 11, 20, True, False]:
            with pytest.raises(ValueError) as excinfo:
                graph_rag.get_call_chain_recursive("src/a.py", depth_limit=invalid_depth)
            assert "depth_limit" in str(excinfo.value).lower()

    # ── Novos Testes Normativos do Pedido 4.3b ──────────────────────

    def test_stale_or_archived_nodes_are_ignored(self, temp_db_env):
        """Item 3.1: nós com status STALE ou ARCHIVED são ignorados como raiz e como destino."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-status-test", folder_name="status-project")

        id_active_root = store.create_node("proj-status-test", label="src/active_root.py", node_type="MODULE", status="ACTIVE")
        id_stale_root = store.create_node("proj-status-test", label="src/stale_root.py", node_type="MODULE", status="STALE")
        id_arch_root = store.create_node("proj-status-test", label="src/arch_root.py", node_type="MODULE", status="ARCHIVED")

        id_active_child = store.create_node("proj-status-test", label="src/active_child.py", node_type="MODULE", status="ACTIVE")
        id_stale_child = store.create_node("proj-status-test", label="src/stale_child.py", node_type="MODULE", status="STALE")
        id_arch_child = store.create_node("proj-status-test", label="src/arch_child.py", node_type="MODULE", status="ARCHIVED")

        # Conecta raiz ativa aos 3 destinos
        store.create_edge(id_active_root, id_active_child, relation_type="calls")
        store.create_edge(id_active_root, id_stale_child, relation_type="calls")
        store.create_edge(id_active_root, id_arch_child, relation_type="calls")

        # Destinos STALE e ARCHIVED devem ser ignorados
        chain = graph_rag.get_call_chain_recursive("src/active_root.py", depth_limit=5)
        assert chain == ["src/active_child.py"]

        # Raiz STALE deve levantar not found
        with pytest.raises(ValueError) as exc_stale:
            graph_rag.get_call_chain_recursive("src/stale_root.py", depth_limit=5)
        assert "not found" in str(exc_stale.value).lower()

        # Raiz ARCHIVED deve levantar not found
        with pytest.raises(ValueError) as exc_arch:
            graph_rag.get_call_chain_recursive("src/arch_root.py", depth_limit=5)
        assert "not found" in str(exc_arch.value).lower()

    def test_symbol_start_excludes_origin_file_but_traverses_intrafile_callees(self, temp_db_env):
        """Item 3.2 (2a): início por símbolo exclui o arquivo de origem do resultado, mas atravessa símbolos do mesmo arquivo."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-symbol-2a", folder_name="symbol-2a")

        id_a = store.create_node("proj-symbol-2a", label="a.py", node_type="MODULE")
        id_af = store.create_node("proj-symbol-2a", label="a.py::f", node_type="FUNCTION")
        id_ah = store.create_node("proj-symbol-2a", label="a.py::h", node_type="FUNCTION")
        id_b = store.create_node("proj-symbol-2a", label="b.py", node_type="MODULE")
        id_bg = store.create_node("proj-symbol-2a", label="b.py::g", node_type="FUNCTION")
        id_ak = store.create_node("proj-symbol-2a", label="a.py::k", node_type="FUNCTION")

        # a.py::f -> a.py::h (intra-arquivo)
        # a.py::f -> b.py::g (inter-arquivo)
        # b.py::g -> a.py::k (volta para a.py)
        store.create_edge(id_af, id_ah, relation_type="calls")
        store.create_edge(id_af, id_bg, relation_type="calls")
        store.create_edge(id_bg, id_ak, relation_type="calls")

        chain = graph_rag.get_call_chain_recursive("a.py::f", depth_limit=5)
        # O arquivo de origem 'a.py' NÃO pode estar no resultado
        assert "a.py" not in chain
        assert chain == ["b.py"]

    def test_paths_with_wildcards_underscore_percent_and_backslash(self, temp_db_env):
        r"""Item 3.3 (2b): caminhos contendo curingas (_, %, \) não colidem e são tratados como literais exatos."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-wildcards", folder_name="wildcards")

        # Cenário com underscore
        id_ab = store.create_node("proj-wildcards", label="src/a_b.py", node_type="MODULE")
        id_ab_x = store.create_node("proj-wildcards", label="src/a_b.py::x", node_type="FUNCTION")
        id_axb = store.create_node("proj-wildcards", label="src/aXb.py", node_type="MODULE")
        id_axb_y = store.create_node("proj-wildcards", label="src/aXb.py::y", node_type="FUNCTION")
        id_target_z = store.create_node("proj-wildcards", label="src/z.py", node_type="MODULE")
        id_target_zz = store.create_node("proj-wildcards", label="src/z.py::zz", node_type="FUNCTION")

        store.create_edge(id_axb_y, id_target_zz, relation_type="calls")

        # Início por a_b.py não pode colidir com aXb.py
        chain_ab = graph_rag.get_call_chain_recursive("src/a_b.py", depth_limit=5)
        assert chain_ab == []

        # Cenário com percentual %
        id_pct = store.create_node("proj-wildcards", label="src/dir%special/main.py", node_type="MODULE")
        id_pct_f = store.create_node("proj-wildcards", label="src/dir%special/main.py::f", node_type="FUNCTION")
        id_pct_target = store.create_node("proj-wildcards", label="src/target_pct.py", node_type="MODULE")
        store.create_edge(id_pct_f, id_pct_target, relation_type="calls")

        chain_pct = graph_rag.get_call_chain_recursive("src/dir%special/main.py", depth_limit=5)
        assert chain_pct == ["src/target_pct.py"]

        # Cenário com barra invertida \ (usuário busca com backslash do Windows)
        id_win = store.create_node("proj-wildcards", label="src/win/sub/mod.py", node_type="MODULE")
        id_win_f = store.create_node("proj-wildcards", label="src/win/sub/mod.py::f", node_type="FUNCTION")
        id_win_target = store.create_node("proj-wildcards", label="src/target_win.py", node_type="MODULE")
        store.create_edge(id_win_f, id_win_target, relation_type="calls")

        chain_win = graph_rag.get_call_chain_recursive(r"src\win\sub\mod.py", depth_limit=5)
        assert chain_win == ["src/target_win.py"]

    def test_duplicate_folder_name_raises_ambiguity_error(self, temp_db_env):
        """Item 3.4 (2c): se múltiplos projetos compartilham folder_name, project_identifier por nome levanta ValueError."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="uuid-dupl-1", folder_name="common_name")
        store.create_project(uuid="uuid-dupl-2", folder_name="common_name")

        store.create_node("uuid-dupl-1", label="src/mod.py", node_type="MODULE")
        store.create_node("uuid-dupl-2", label="src/mod.py", node_type="MODULE")

        with pytest.raises(ValueError) as exc:
            graph_rag.get_call_chain_recursive("src/mod.py", project_identifier="common_name")
        err_msg = str(exc.value).lower()
        assert "multiple projects" in err_msg or "share folder_name" in err_msg

        # Mas se passar o UUID exato, deve resolver sem erro
        res = graph_rag.get_call_chain_recursive("src/mod.py", project_identifier="uuid-dupl-1")
        assert res == []

    def test_ambiguity_message_does_not_contain_names_or_uuids(self, temp_db_env):
        """Item 3.5 (2d): mensagem de erro de ambiguidade não lista nomes de pasta nem UUIDs."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="u-priv-1", folder_name="restricted_folder_alpha")
        store.create_project(uuid="u-priv-2", folder_name="restricted_folder_beta")

        store.create_node("u-priv-1", label="shared.py", node_type="MODULE")
        store.create_node("u-priv-2", label="shared.py", node_type="MODULE")

        with pytest.raises(ValueError) as exc:
            graph_rag.get_call_chain_recursive("shared.py")
        msg = str(exc.value)

        assert "restricted_folder_alpha" not in msg
        assert "restricted_folder_beta" not in msg
        assert "u-priv-1" not in msg
        assert "u-priv-2" not in msg

    def test_nonexistent_project_identifier_raises_clear_error(self, temp_db_env):
        """Item 3.6: passar project_identifier inexistente levanta erro claro."""
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        with pytest.raises(ValueError) as exc:
            graph_rag.get_call_chain_recursive("src/a.py", project_identifier="non_existent_project")
        assert "not found" in str(exc.value).lower()

    def test_repeated_symbol_name_orchestrator_behavior(self, temp_db_env):
        """Item 3.7 (2f): documenta o comportamento do orquestrador ao ligar chamadas para símbolos globais repetidos."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-repeat-symbol", folder_name="repeat_symbol")

        # Duas funções util em módulos diferentes
        id_mod1 = store.create_node("proj-repeat-symbol", label="pkg_a/tools.py", node_type="MODULE")
        id_util1 = store.create_node("proj-repeat-symbol", label="pkg_a/tools.py::util", node_type="FUNCTION")

        id_mod2 = store.create_node("proj-repeat-symbol", label="pkg_b/tools.py", node_type="MODULE")
        id_util2 = store.create_node("proj-repeat-symbol", label="pkg_b/tools.py::util", node_type="FUNCTION")

        id_caller = store.create_node("proj-repeat-symbol", label="app/main.py", node_type="MODULE")
        id_caller_run = store.create_node("proj-repeat-symbol", label="app/main.py::run", node_type="FUNCTION")

        # Conforme orchestrator.py:768, global_symbol_map[call_name][0] é selecionado (primeiro registrado)
        # Fixamos a aresta para util1
        store.create_edge(id_caller_run, id_util1, relation_type="calls")

        chain = graph_rag.get_call_chain_recursive("app/main.py", depth_limit=5)
        assert chain == ["pkg_a/tools.py"]
        assert "pkg_b/tools.py" not in chain

    def test_e2e_mcp_real_server_call_chain_with_ingestion(self, temp_db_env):
        """Item 3.8: teste E2E com servidor MCP real e mineração de 3 arquivos com chamadas recursivas."""
        import shutil
        from ingestion.orchestrator import IngestionManager
        from storage.vector_store import ChromaVectorStore, EmbeddingManager

        db_mgr: ConciergeDatabaseManager = temp_db_env["db_mgr"]
        store: SqliteStore = temp_db_env["store"]

        # Cria projeto de 3 arquivos em diretório temporário
        temp_src = tempfile.mkdtemp(prefix="e2e_src_")
        temp_chroma = tempfile.mkdtemp(prefix="e2e_chroma_")
        p_uuid = "proj-e2e-real-mcp"
        try:
            with open(os.path.join(temp_src, "alpha.py"), "w", encoding="utf-8") as f:
                f.write("def fa():\n    fb()\n")

            with open(os.path.join(temp_src, "beta.py"), "w", encoding="utf-8") as f:
                f.write("def fb():\n    fc()\n")

            with open(os.path.join(temp_src, "gamma.py"), "w", encoding="utf-8") as f:
                f.write("def fc():\n    pass\n")

            store.create_project(uuid=p_uuid, folder_name="e2e_real_proj")

            # Minera o projeto via IngestionManager com GRAFO_LLM_MODEL=none
            old_llm_model = os.environ.get("GRAFO_LLM_MODEL")
            os.environ["GRAFO_LLM_MODEL"] = "none"
            try:
                embedder = EmbeddingManager()
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
            shutil.rmtree(temp_chroma, ignore_errors=True)
