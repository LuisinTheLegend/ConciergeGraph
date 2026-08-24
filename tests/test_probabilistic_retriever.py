"""
tests/_test_probabilistic_retriever.py — Testes matemáticos e funcionais do ThompsonRetriever (Passo 6)

Valida a lógica de explotação e exploração baseada no Thompson Sampling (SA-CTS).
"""

from __future__ import annotations

import sqlite3
import random
import pytest

from storage.schema import SchemaManager
from storage.semantic_logic import insert_semantic_fact, get_active_semantic_facts, update_memory_utility
from core.probabilistic_retriever import ThompsonRetriever


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


def test_thompson_retriever_exploration():
    """Garante que a variância do Thompson Sampling permite a exploração de novos fatos (alpha=1, beta=1)."""
    # Cenário:
    # Fato A (Estabilizado Mediano): similarity=0.8, alpha=10, beta=10. Média Beta = 0.5. Variância baixa.
    # Fato B (Novo Frio): similarity=0.75, alpha=1, beta=1. Média Beta = 0.5. Variância alta.
    # Queremos verificar que, devido à maior variância do Fato B, ele supera o Fato A em parte das rodadas.
    
    def mock_vector_search(query: str, limit: int) -> list[dict]:
        return [
            {
                "id": 1,
                "score": 0.8,
                "metadata": {
                    "utility_alpha": 10.0,
                    "utility_beta": 10.0
                }
            },
            {
                "id": 2,
                "score": 0.75,
                "metadata": {
                    "utility_alpha": 1.0,
                    "utility_beta": 1.0
                }
            }
        ]

    retriever = ThompsonRetriever(mock_vector_search)
    
    wins_a = 0
    wins_b = 0
    
    # Fixa seed para determinismo do teste amostral
    random.seed(42)
    
    for _ in range(1000):
        results = retriever.retrieve("query", limit=5, top_k=2)
        assert len(results) == 2
        if results[0]["doc_id"] == 1:
            wins_a += 1
        elif results[0]["doc_id"] == 2:
            wins_b += 1

    # Ambos devem vencer pelo menos algumas rodadas
    assert wins_a > 0
    assert wins_b > 0
    # O Fato A (estabilizado com similaridade maior) deve ganhar a maioria das rodadas
    assert wins_a > wins_b


def test_thompson_retriever_exploitation():
    """Garante que fatos de excelente utilidade dominam fatos ruins mesmo com menor similaridade (explotação)."""
    # Cenário:
    # Fato A (Excelente): similarity=0.8, alpha=100, beta=1 (Média Beta ~ 0.99)
    # Fato B (Péssimo): similarity=0.9, alpha=1, beta=100 (Média Beta ~ 0.01)
    # Mesmo com similaridade semântica superior no Fato B, Fato A deve vencer quase 100% das vezes.
    
    def mock_vector_search(query: str, limit: int) -> list[dict]:
        return [
            {
                "id": 1,
                "score": 0.8,
                "metadata": {
                    "utility_alpha": 100.0,
                    "utility_beta": 1.0
                }
            },
            {
                "id": 2,
                "score": 0.9,
                "metadata": {
                    "utility_alpha": 1.0,
                    "utility_beta": 100.0
                }
            }
        ]

    retriever = ThompsonRetriever(mock_vector_search)
    
    wins_a = 0
    wins_b = 0
    
    random.seed(42)
    
    for _ in range(1000):
        results = retriever.retrieve("query", limit=5, top_k=2)
        if results[0]["doc_id"] == 1:
            wins_a += 1
        elif results[0]["doc_id"] == 2:
            wins_b += 1

    # Fato A deve ganhar esmagadoramente (> 99% das vezes)
    assert wins_a > 990
    assert wins_b < 10
