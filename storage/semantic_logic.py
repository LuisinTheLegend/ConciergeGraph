"""
storage/semantic_logic.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Funções de mutação puras e de consulta para a tabela semantic_facts.
Todas as funções operam recebendo a conexão sqlite3.Connection por parâmetro
de forma a garantir o isolamento e evitar o Database is Locked (Single-Writer).
"""

from __future__ import annotations

import sqlite3
from typing import Any


def insert_semantic_fact(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str,
    fact_statement: str,
    utility_alpha: float = 1.0,
    utility_beta: float = 1.0
) -> int:
    """Insere um novo fato semântico ativo na tabela semantic_facts.

    Valira escopos e parâmetros rigorosamente.

    Args:
        conn: Conexão SQLite ativa.
        scope_type: Tipo de escopo (user, session, agent, org).
        scope_id: Identificador único do escopo.
        fact_statement: O texto da preferência ou fato extraído.
        utility_alpha: Sucessos históricos do fato (default: 1.0).
        utility_beta: Falhas históricas do fato (default: 1.0).

    Returns:
        O ID (rowid) do registro recém-inserido.
    """
    if scope_type not in ("user", "session", "agent", "org"):
        raise ValueError(f"scope_type inválido: '{scope_type}'. Aceitos: user, session, agent, org")
    if not scope_id or not scope_id.strip():
        raise ValueError("scope_id não pode ser vazio ou nulo")
    if not fact_statement or not fact_statement.strip():
        raise ValueError("fact_statement não pode ser vazio ou nulo")

    cursor = conn.execute(
        """INSERT INTO semantic_facts (scope_type, scope_id, fact_statement, utility_alpha, utility_beta)
           VALUES (?, ?, ?, ?, ?)""",
        (scope_type, scope_id.strip(), fact_statement.strip(), utility_alpha, utility_beta)
    )
    return cursor.lastrowid


def invalidate_semantic_fact(conn: sqlite3.Connection, fact_id: int) -> None:
    """Invalida um fato semântico definindo t_invalid para o timestamp atual.

    Representa a revogação temporal de um fato.

    Args:
        conn: Conexão SQLite ativa.
        fact_id: ID do fato semântico a ser invalidado.
    """
    if not isinstance(fact_id, int):
        raise ValueError("fact_id deve ser do tipo int")

    conn.execute(
        """UPDATE semantic_facts
           SET t_invalid = datetime('now')
           WHERE id = ?""",
        (fact_id,)
    )


def get_active_semantic_facts(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> list[dict[str, Any]]:
    """Retorna todos os fatos semânticos atualmente ativos para um escopo.

    Um fato é considerado ativo se t_invalid for NULL.

    Args:
        conn: Conexão SQLite ativa.
        scope_type: Tipo de escopo (user, session, agent, org).
        scope_id: Identificador único do escopo.

    Returns:
        Lista de dicionários contendo os dados dos fatos ativos.
    """
    if scope_type not in ("user", "session", "agent", "org"):
        raise ValueError(f"scope_type inválido: '{scope_type}'. Aceitos: user, session, agent, org")
    if not scope_id or not scope_id.strip():
        raise ValueError("scope_id não pode ser vazio ou nulo")

    cursor = conn.execute(
        """SELECT id, scope_type, scope_id, fact_statement, t_valid, t_invalid, utility_alpha, utility_beta, created_at
           FROM semantic_facts
           WHERE scope_type = ? AND scope_id = ? AND t_invalid IS NULL
           ORDER BY id ASC""",
        (scope_type, scope_id.strip())
    )
    return [dict(row) for row in cursor.fetchall()]


def update_memory_utility(conn: sqlite3.Connection, fact_id: int, was_useful: bool) -> None:
    """Atualiza a utilidade Bayesiana de um fato (incrementa alpha em sucesso ou beta em falha).

    Args:
        conn: Conexão SQLite ativa.
        fact_id: ID do fato semântico.
        was_useful: Booleano indicando se o fato foi útil (True) ou não (False).
    """
    if not isinstance(fact_id, int):
        raise ValueError("fact_id deve ser do tipo int")

    if was_useful:
        conn.execute(
            """UPDATE semantic_facts
               SET utility_alpha = utility_alpha + 1.0
               WHERE id = ?""",
            (fact_id,)
        )
    else:
        conn.execute(
            """UPDATE semantic_facts
               SET utility_beta = utility_beta + 1.0
               WHERE id = ?""",
            (fact_id,)
        )
