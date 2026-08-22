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
            "WITH RECURSIVE call_chain(node, depth) AS ("
            "  SELECT child_node, 1 FROM ast_edges WHERE parent_node = ?"
            "  UNION"
            "  SELECT e.child_node, cc.depth + 1"
            "  FROM ast_edges e"
            "  JOIN call_chain cc ON e.parent_node = cc.node"
            "  WHERE cc.depth < ?"
            ") SELECT DISTINCT node FROM call_chain WHERE node != ?;",
            (start_node, depth_limit, start_node),
        )
        return [row[0] for row in rows]
