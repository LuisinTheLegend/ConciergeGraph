"""
storage/semantic_logic.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Pure mutation and query functions for the semantic_facts table.
All functions operate by receiving the sqlite3.Connection as a parameter
in order to ensure isolation and prevent Database is Locked (Single-Writer).
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
    """Inserts a new active semantic fact into the semantic_facts table.

    Strictly validates scopes and parameters.

    Args:
        conn: Active SQLite connection.
        scope_type: Scope type (user, session, agent, org).
        scope_id: Unique identifier of the scope.
        fact_statement: The text of the preference or extracted fact.
        utility_alpha: Historical successes of the fact (default: 1.0).
        utility_beta: Historical failures of the fact (default: 1.0).

    Returns:
        The ID (rowid) of the newly inserted record.
    """
    if scope_type not in ("user", "session", "agent", "org"):
        raise ValueError(f"Invalid scope_type: '{scope_type}'. Accepted: user, session, agent, org")
    if not scope_id or not scope_id.strip():
        raise ValueError("scope_id cannot be empty or null")
    if not fact_statement or not fact_statement.strip():
        raise ValueError("fact_statement cannot be empty or null")

    cursor = conn.execute(
        """INSERT INTO semantic_facts (scope_type, scope_id, fact_statement, utility_alpha, utility_beta)
           VALUES (?, ?, ?, ?, ?)""",
        (scope_type, scope_id.strip(), fact_statement.strip(), utility_alpha, utility_beta)
    )
    return cursor.lastrowid


def invalidate_semantic_fact(conn: sqlite3.Connection, fact_id: int) -> None:
    """Invalidates a semantic fact by setting t_invalid to the current timestamp.

    Represents the temporal revocation of a fact.

    Args:
        conn: Active SQLite connection.
        fact_id: ID of the semantic fact to be invalidated.
    """
    if not isinstance(fact_id, int):
        raise ValueError("fact_id must be of type int")

    conn.execute(
        """UPDATE semantic_facts
           SET t_invalid = datetime('now')
           WHERE id = ?""",
        (fact_id,)
    )


def get_active_semantic_facts(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> list[dict[str, Any]]:
    """Returns all currently active semantic facts for a scope.

    A fact is considered active if t_invalid is NULL.

    Args:
        conn: Active SQLite connection.
        scope_type: Scope type (user, session, agent, org).
        scope_id: Unique identifier of the scope.

    Returns:
        List of dictionaries containing active facts data.
    """
    if scope_type not in ("user", "session", "agent", "org"):
        raise ValueError(f"Invalid scope_type: '{scope_type}'. Accepted: user, session, agent, org")
    if not scope_id or not scope_id.strip():
        raise ValueError("scope_id cannot be empty or null")

    cursor = conn.execute(
        """SELECT id, scope_type, scope_id, fact_statement, t_valid, t_invalid, utility_alpha, utility_beta, created_at
           FROM semantic_facts
           WHERE scope_type = ? AND scope_id = ? AND t_invalid IS NULL
           ORDER BY id ASC""",
        (scope_type, scope_id.strip())
    )
    return [dict(row) for row in cursor.fetchall()]


def update_memory_utility(conn: sqlite3.Connection, fact_id: int, was_useful: bool) -> None:
    """Updates the Bayesian utility of a fact (increments alpha on success or beta on failure).

    Args:
        conn: Active SQLite connection.
        fact_id: ID of the semantic fact.
        was_useful: Boolean indicating if the fact was useful (True) or not (False).
    """
    if not isinstance(fact_id, int):
        raise ValueError("fact_id must be of type int")

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
