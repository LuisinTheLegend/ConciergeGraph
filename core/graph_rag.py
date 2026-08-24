"""
core/graph_rag.py — SDD-SURVIVAL-06

Detecção de Comunidades Heurística e Busca Multi-Hop (GraphRAG Frugal).

Implementa duas estratégias de custo computacional zero para o GraphRAG local:

  1. Mapeamento Topológico: O diretório pai imediato do arquivo é assumido
     como a partição de comunidade natural (sem algoritmos de rede em RAM).

  2. Multi-Hop Relacional via CTE Recursivo: Varre a árvore de chamadas
     de métodos (ast_edges) diretamente no SQLite WAL em milissegundos,
     sem carregar grafos inteiros na memória.
"""

import os
from typing import Any, List


class GraphRAGEngine:
    """
    Motor de grafos frugal que mapeia comunidades por topologia de diretórios
    e resolve cadeias de dependência via CTEs recursivos no SQLite WAL.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Mapeamento Topológico ─────────────────────────────────────

    def get_natural_community(self, file_path: str) -> str:
        """
        Extrai o diretório pai imediato do arquivo como comunidade natural.

        Custo computacional: O(1) — simples operação de string.
        Exemplos:
          - 'core/utils/delta.py' → 'core/utils'
          - 'main.py'             → 'root'
        """
        parent = os.path.dirname(file_path.replace("\\", "/"))
        return parent if parent else "root"

    # ── Multi-Hop via CTE Recursivo ───────────────────────────────

    def get_call_chain_recursive(
        self, start_node: str, depth_limit: int = 5
    ) -> List[str]:
        """
        Executa travessia recursiva sobre a tabela ast_edges no SQLite WAL
        usando WITH RECURSIVE, retornando todos os nós filhos conectados
        ao nó raiz até o limite de profundidade especificado.

        Não inclui o nó raiz na resposta — apenas dependências transitivas.
        Nós de subgrafos desconectados são automaticamente excluídos.
        """
        rows = self.db_manager.read_query(
            "WITH RECURSIVE call_chain(node, depth, path_visited) AS ("
            "  SELECT ? AS node, 0 AS depth, '|' || ? || '|' AS path_visited"
            "  UNION ALL"
            "  SELECT e.child_node AS node,"
            "         cc.depth + 1 AS depth,"
            "         cc.path_visited || e.child_node || '|' AS path_visited"
            "  FROM ast_edges e"
            "  JOIN call_chain cc ON e.parent_node = cc.node"
            "  WHERE cc.depth < ?"
            "    AND instr(cc.path_visited, '|' || e.child_node || '|') = 0"
            ") SELECT DISTINCT node, depth FROM call_chain WHERE node != ?;",
            (start_node, start_node, depth_limit, start_node),
        )
        return [row[0] for row in rows]

    # ── Detecção de Comunidades com Filtro de Supernó (SDD-14) ────

    def detect_logical_communities(
        self, in_degree_threshold: int = 5
    ) -> dict:
        """
        Agrupa os arquivos do repositório em comunidades baseadas na
        proximidade de acoplamento AST, filtrando supernós (hubs globais).

        Algoritmo:
          1. Calcula in-degree de cada nó na tabela ast_edges
          2. Nós com in-degree > in_degree_threshold são classificados
             como Supernós e omitidos como pontes de transição
          3. Arestas limpas (sem supernós) são agrupadas via Union-Find
             em componentes conectados independentes
          4. Supernós recebem fallback de diretório (hub_satellite_{dir})

        Retorna dict: {community_key: [file_paths]}
        """
        # 1. Identificar supernós (hubs globais) por in-degree
        supernodes_rows = self.db_manager.read_query(
            "SELECT child_node, COUNT(*) as in_degree "
            "FROM ast_edges "
            "GROUP BY child_node "
            "HAVING in_degree > ?;",
            (in_degree_threshold,),
        )
        supernodes = {r[0] for r in supernodes_rows}

        # 2. Buscar arestas limpas (excluindo supernós como pontes)
        all_edges = self.db_manager.read_query(
            "SELECT parent_node, child_node FROM ast_edges;"
        )
        filtered_edges = [
            (parent, child)
            for parent, child in all_edges
            if parent not in supernodes and child not in supernodes
        ]

        # 3. Agrupamento em Componentes Conectados (Union-Find)
        parent_map: dict = {}

        def find(node: str) -> str:
            if parent_map.setdefault(node, node) != node:
                parent_map[node] = find(parent_map[node])
            return parent_map[node]

        def union(node1: str, node2: str) -> None:
            root1 = find(node1)
            root2 = find(node2)
            if root1 != root2:
                parent_map[root1] = root2

        for parent, child in filtered_edges:
            union(parent, child)

        # 4. Agrupa arquivos por comunidade
        all_files = [
            r[0] for r in self.db_manager.read_query("SELECT path FROM files;")
        ]

        communities: dict = {}
        for file_path in all_files:
            if file_path in supernodes:
                # Supernó → satélite do diretório local (Fallback L2/L1)
                dir_name = "/".join(file_path.replace("\\", "/").split("/")[:-1]) or "root"
                community_key = f"hub_satellite_{dir_name}"
            else:
                community_key = f"community_{find(file_path)}"

            communities.setdefault(community_key, []).append(file_path)

        return communities
