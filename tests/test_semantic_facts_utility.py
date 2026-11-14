"""
tests/test_semantic_facts_utility.py — Testes isolados de utilidade Bayesiana em semantic_logic.

Copiado de tests/test_probabilistic_retriever.py sem dependência de core.probabilistic_retriever.
"""

from __future__ import annotations

import sqlite3
import pytest

from storage.schema import SchemaManager
from storage.semantic_logic import (
    get_active_semantic_facts,
    insert_semantic_fact,
    update_memory_utility,
)


@pytest.fixture
def temp_db():
    """Cria banco SQLite em memória com o schema completo e migrações aplicados."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")

    manager = SchemaManager(conn)
    manager.apply_full_schema()

    yield conn
    conn.close()


def test_update_memory_utility(temp_db):
    """Valida a atualização pura do feedback Bayesiano (alpha e beta) no SQLite."""
    # Insere fato com alpha/beta padrão (1.0)
    fact_id = insert_semantic_fact(temp_db, "user", "uuid-john", "João gosta de programar em Python.")

    # Valida estado inicial
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 1
    assert active[0]["utility_alpha"] == 1.0
    assert active[0]["utility_beta"] == 1.0

    # Incrementa alpha (was_useful=True)
    update_memory_utility(temp_db, fact_id, was_useful=True)
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert active[0]["utility_alpha"] == 2.0
    assert active[0]["utility_beta"] == 1.0

    # Incrementa beta (was_useful=False)
    update_memory_utility(temp_db, fact_id, was_useful=False)
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert active[0]["utility_alpha"] == 2.0
    assert active[0]["utility_beta"] == 2.0
