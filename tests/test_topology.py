"""
tests/_test_topology.py — Testes da ferramenta get_full_topology (Mapa da Galáxia)
"""

from __future__ import annotations

import os
import tempfile
import pytest

from storage.store import SqliteStore
from core.middleware import GrafoConcierge
from core.config import ConciergeConfig


@pytest.fixture
def temp_store():
    """Cria uma instância temporária do SqliteStore."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Inicializa o store
    store = SqliteStore(db_path=path)

    yield store

    # Limpeza
    store.close()
    try:
        os.remove(path)
    except OSError:
        pass


def test_get_lightweight_topology(temp_store):
    """Valida o funcionamento do método de consulta de topologia leve no SqliteStore."""
    # 1. Registra projetos
    proj_uuid1 = "11111111-1111-1111-1111-111111111111"
    proj_uuid2 = "22222222-2222-2222-2222-222222222222"
    temp_store.create_project(proj_uuid1, "p1", "geral", "PUBLIC", "Projeto 1")
    temp_store.create_project(proj_uuid2, "p2", "geral", "PUBLIC", "Projeto 2")

    # 2. Cria nós de teste
    node1_id = temp_store.create_node(
        project_uuid=proj_uuid1,
        label="src/main.py",
        summary="Função principal",
        node_type="MODULE",
        type_="file",
        file_hash="hash1"
    )
    node2_id = temp_store.create_node(
        project_uuid=proj_uuid1,
        label="src/utils.py",
        summary="Funções utilitárias",
        node_type="MODULE",
        type_="file",
        file_hash="hash2"
    )
    node3_id = temp_store.create_node(
        project_uuid=proj_uuid2,
        label="src/other.py",
        summary="Outro projeto",
        node_type="MODULE",
        type_="file",
        file_hash="hash3"
    )

    # 3. Cria arestas de teste
    temp_store.create_edge(
        source_id=node1_id,
        target_id=node2_id,
        relation_type="CALLS",
        weight=1.0
    )
    temp_store.create_edge(
        source_id=node1_id,
        target_id=node3_id,
        relation_type="DEPENDS_ON",
        weight=2.0
    )

    # 4. Busca topologia global (sem passar project_uuid)
    global_topo = temp_store.get_lightweight_topology()
    assert "nodes" in global_topo
    assert "edges" in global_topo
    
    # Nós devem conter apenas os campos especificados no contrato (sem summary)
    assert len(global_topo["nodes"]) == 3
    for node in global_topo["nodes"]:
        assert set(node.keys()) == {"node_id", "name", "node_type"}
        assert "summary" not in node

    # Arestas devem conter apenas source, target e edge_type
    assert len(global_topo["edges"]) == 2
    for edge in global_topo["edges"]:
        assert set(edge.keys()) == {"source", "target", "edge_type"}

    # 5. Busca topologia filtrada pelo Projeto 1
    p1_topo = temp_store.get_lightweight_topology(proj_uuid1)
    # Deve conter apenas nós do Projeto 1
    assert len(p1_topo["nodes"]) == 2
    p1_node_ids = {node["node_id"] for node in p1_topo["nodes"]}
    assert node1_id in p1_node_ids
    assert node2_id in p1_node_ids
    assert node3_id not in p1_node_ids

    # Arestas do Projeto 1 devem apontar apenas entre nós que pertencem ao Projeto 1 e estão ativos
    assert len(p1_topo["edges"]) == 1
    assert p1_topo["edges"][0]["source"] == node1_id
    assert p1_topo["edges"][0]["target"] == node2_id
    assert p1_topo["edges"][0]["edge_type"] == "CALLS"


def test_middleware_topology_delegation(temp_store):
    """Valida que o middleware GrafoConcierge delega corretamente a chamada."""
    # Instancia o middleware com o store existente
    config = ConciergeConfig()
    gc = GrafoConcierge(
        sqlite_store=temp_store,
        vector_store=None,
        embedding_manager=None,
        ingestion_manager=None,
        config=config
    )

    proj_uuid = "33333333-3333-3333-3333-333333333333"
    temp_store.create_project(proj_uuid, "p3", "geral", "PUBLIC")
    node_id = temp_store.create_node(
        project_uuid=proj_uuid,
        label="main.py",
        summary="x",
        node_type="MODULE",
        type_="file",
        file_hash="h"
    )

    topo = gc.get_full_topology(proj_uuid)
    assert len(topo["nodes"]) == 1
    assert topo["nodes"][0]["node_id"] == node_id
    assert topo["nodes"][0]["name"] == "main.py"
