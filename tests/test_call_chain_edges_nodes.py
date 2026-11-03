"""
tests/test_call_chain_edges_nodes.py — Rodada 4.3 Bloco 2

Validação da travessia de call chain sobre tabelas canônicas 'nodes' e 'edges'
com escopo estrito de projeto, ciclo-segurança, e filtragem de arestas ativas.
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

        # Registra projeto
        store.create_project(
            uuid="proj-linear-111",
            folder_name="linear-project",
            primary_wing="core",
            privacy_level="INTERNAL",
            summary="Linear chain test",
        )

        # Cria nós A, B, C
        id_a = store.create_node("proj-linear-111", label="src/a.py", node_type="FACT")
        id_b = store.create_node("proj-linear-111", label="src/b.py", node_type="FACT")
        id_c = store.create_node("proj-linear-111", label="src/c.py", node_type="FACT")

        # Cria arestas A -> B e B -> C com relation_type='calls'
        store.create_edge(id_a, id_b, relation_type="calls", weight=1.0)
        store.create_edge(id_b, id_c, relation_type="calls", weight=1.0)

        # depth_limit = 1 deve retornar apenas B
        chain_1 = graph_rag.get_call_chain_recursive("src/a.py", depth_limit=1)
        assert chain_1 == ["src/b.py"]

        # depth_limit = 2 deve retornar B, C
        chain_2 = graph_rag.get_call_chain_recursive("src/a.py", depth_limit=2)
        assert chain_2 == ["src/b.py", "src/c.py"]

        # depth_limit = 5 deve retornar B, C (fim da cadeia)
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

        id_a = store.create_node("proj-cycle-222", label="src/alpha.py", node_type="FACT")
        id_b = store.create_node("proj-cycle-222", label="src/beta.py", node_type="FACT")

        # Ciclo A -> B e B -> A
        store.create_edge(id_a, id_b, relation_type="calls")
        store.create_edge(id_b, id_a, relation_type="calls")

        # Deve visitar beta e parar sem loop infinito, excluindo a raiz alpha
        chain = graph_rag.get_call_chain_recursive("src/alpha.py", depth_limit=5)
        assert chain == ["src/beta.py"]

    def test_nonexistent_root_node_raises_clear_error(self, temp_db_env):
        """Teste 3: nó raiz não existente devolve erro claro (não lista vazia silenciosa)."""
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        with pytest.raises(ValueError) as excinfo:
            graph_rag.get_call_chain_recursive("src/ghost.py", depth_limit=5)
        assert "not found" in str(excinfo.value).lower()

    def test_ambiguous_node_across_projects_requires_identifier(self, temp_db_env):
        """Teste 4: múltiplos nós com mesmo label em projetos distintos devolve erro com candidatos;
        com project_identifier, resolve o correto."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        # Projeto 1
        store.create_project(uuid="uuid-proj-1", folder_name="repo-one", primary_wing="wing1")
        id_p1_main = store.create_node("uuid-proj-1", label="src/main.py", node_type="FACT")
        id_p1_util = store.create_node("uuid-proj-1", label="src/util_one.py", node_type="FACT")
        store.create_edge(id_p1_main, id_p1_util, relation_type="calls")

        # Projeto 2
        store.create_project(uuid="uuid-proj-2", folder_name="repo-two", primary_wing="wing2")
        id_p2_main = store.create_node("uuid-proj-2", label="src/main.py", node_type="FACT")
        id_p2_util = store.create_node("uuid-proj-2", label="src/util_two.py", node_type="FACT")
        store.create_edge(id_p2_main, id_p2_util, relation_type="calls")

        # Sem project_identifier deve recusar com erro claro listando candidatos
        with pytest.raises(ValueError) as excinfo:
            graph_rag.get_call_chain_recursive("src/main.py", depth_limit=5)
        err_msg = str(excinfo.value)
        assert "ambiguous" in err_msg.lower() or "multiple projects" in err_msg.lower()
        assert "repo-one" in err_msg or "uuid-proj-1" in err_msg
        assert "repo-two" in err_msg or "uuid-proj-2" in err_msg

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
        id_a = store.create_node("proj-hist-555", label="src/caller.py", node_type="FACT")
        id_b_old = store.create_node("proj-hist-555", label="src/old_callee.py", node_type="FACT")
        id_b_new = store.create_node("proj-hist-555", label="src/new_callee.py", node_type="FACT")

        # Aresta antiga expirada por commit (valid_to_commit não nulo)
        store.create_edge(id_a, id_b_old, relation_type="calls", valid_to_commit="deadbeef123")
        # Aresta atual ativa
        store.create_edge(id_a, id_b_new, relation_type="calls", valid_to_commit=None)

        chain = graph_rag.get_call_chain_recursive("src/caller.py", depth_limit=5)
        assert "src/new_callee.py" in chain
        assert "src/old_callee.py" not in chain

    def test_other_relation_types_are_not_followed(self, temp_db_env):
        """Teste 6: arestas de outro relation_type (ex.: depends_on, imports) NÃO são seguidas como call_chain."""
        store: SqliteStore = temp_db_env["store"]
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        store.create_project(uuid="proj-rel-666", folder_name="rel-project", primary_wing="core")
        id_src = store.create_node("proj-rel-666", label="src/service.py", node_type="FACT")
        id_dep = store.create_node("proj-rel-666", label="src/dependency.py", node_type="FACT")
        id_imp = store.create_node("proj-rel-666", label="src/imported.py", node_type="FACT")
        id_call = store.create_node("proj-rel-666", label="src/called.py", node_type="FACT")

        store.create_edge(id_src, id_dep, relation_type="depends_on")
        store.create_edge(id_src, id_imp, relation_type="imports")
        store.create_edge(id_src, id_call, relation_type="calls")

        chain = graph_rag.get_call_chain_recursive("src/service.py", depth_limit=5)
        assert chain == ["src/called.py"]
        assert "src/dependency.py" not in chain
        assert "src/imported.py" not in chain

    def test_invalid_depth_limit_raises_clear_error(self, temp_db_env):
        """Teste 7: profundidade inválida (< 1 ou > 10) devolve erro claro."""
        graph_rag: GraphRAGEngine = temp_db_env["graph_rag"]

        for invalid_depth in [0, -1, -5, 11, 20]:
            with pytest.raises(ValueError) as excinfo:
                graph_rag.get_call_chain_recursive("src/a.py", depth_limit=invalid_depth)
            assert "depth_limit" in str(excinfo.value).lower()
