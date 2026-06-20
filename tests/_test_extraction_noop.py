"""
tests/_test_extraction_noop.py — Testes unitários do motor de extração semântica (Passo 4)

Valida o pipeline de decisões semânticas (ADD, UPDATE, DELETE, NOOP) e as garantias bi-temporais.
"""

from __future__ import annotations

import sqlite3
import pytest
from typing import Any

from storage.schema import SchemaManager
from storage.semantic_logic import get_active_semantic_facts, insert_semantic_fact
from core.memory_extractor import SemanticExtractor


class MockLLMAdapter:
    """Mock do LLMAdapter para injetar respostas previsíveis nos testes."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        self.calls.append(prompt)
        if self.responses:
            return self.responses.pop(0)
        return '{"action": "NOOP", "target_id": null, "updated_statement": null}'


@pytest.fixture
def temp_db():
    """Cria banco SQLite em memória com o schema completo aplicado."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    
    manager = SchemaManager(conn)
    manager.apply_full_schema()
    
    yield conn
    conn.close()


def test_extraction_noop_optimization_on_empty_db(temp_db):
    """Garante que se a base estiver vazia, o fato é adicionado (ADD) sem chamar o LLM."""
    mock_llm = MockLLMAdapter([])
    extractor = SemanticExtractor(mock_llm)

    results = extractor.evaluate_and_store_facts(
        temp_db, "user", "uuid-john", ["João prefere café sem açúcar."]
    )

    assert len(results) == 1
    assert results[0]["action"] == "ADD"
    assert results[0]["target_id"] is None
    assert results[0]["fact_id"] is not None

    # Verifica se gravou
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 1
    assert active[0]["fact_statement"] == "João prefere café sem açúcar."
    # Garantia de que o LLM não foi consultado (otimização de banco vazio)
    assert len(mock_llm.calls) == 0


def test_extraction_add_with_existing_facts(temp_db):
    """Valida a inserção (ADD) de um fato inédito quando já existem fatos cadastrados."""
    # Primeiro fato (inserido diretamente)
    insert_semantic_fact(temp_db, "user", "uuid-john", "João prefere café sem açúcar.")

    # Mock retorna decisão de ADD para o novo fato
    mock_llm = MockLLMAdapter([
        '{"action": "ADD", "target_id": null, "updated_statement": null}'
    ])
    extractor = SemanticExtractor(mock_llm)

    results = extractor.evaluate_and_store_facts(
        temp_db, "user", "uuid-john", ["João gosta de correr pela manhã."]
    )

    assert len(results) == 1
    assert results[0]["action"] == "ADD"
    assert len(mock_llm.calls) == 1

    # Ambas devem estar ativas no banco
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 2
    statements = {f["fact_statement"] for f in active}
    assert "João prefere café sem açúcar." in statements
    assert "João gosta de correr pela manhã." in statements


def test_extraction_noop_redundancy_filter(temp_db):
    """Garante que a ação NOOP previne duplicações e não altera o banco."""
    # Fato pré-existente
    insert_semantic_fact(temp_db, "user", "uuid-john", "João prefere café sem açúcar.")

    # Novo fato idêntico/redundante
    mock_llm = MockLLMAdapter([
        '{"action": "NOOP", "target_id": null, "updated_statement": null}'
    ])
    extractor = SemanticExtractor(mock_llm)

    results = extractor.evaluate_and_store_facts(
        temp_db, "user", "uuid-john", ["João prefere café sem açúcar."]
    )

    assert len(results) == 1
    assert results[0]["action"] == "NOOP"
    assert results[0]["fact_id"] is None

    # Banco não deve ter sofrido mutações adicionais
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 1
    assert active[0]["fact_statement"] == "João prefere café sem açúcar."


def test_extraction_update_bi_temporal(temp_db):
    """Garante que UPDATE invalida o fato antigo e insere o fato atualizado (bi-temporal puro)."""
    # Fato pré-existente
    fact_id = insert_semantic_fact(temp_db, "user", "uuid-john", "João prefere café sem açúcar.")

    # Mock retorna decisão de UPDATE
    mock_llm = MockLLMAdapter([
        f'{{"action": "UPDATE", "target_id": {fact_id}, "updated_statement": "João prefere café sem açúcar e com adoçante."}}'
    ])
    extractor = SemanticExtractor(mock_llm)

    results = extractor.evaluate_and_store_facts(
        temp_db, "user", "uuid-john", ["João agora quer adoçante no café."]
    )

    assert len(results) == 1
    assert results[0]["action"] == "UPDATE"
    assert results[0]["target_id"] == fact_id

    # Apenas o fato novo deve estar ativo
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 1
    assert active[0]["fact_statement"] == "João prefere café sem açúcar e com adoçante."
    assert active[0]["t_invalid"] is None

    # O fato antigo deve existir no histórico total, mas marcado como inválido
    cursor = temp_db.execute("SELECT * FROM semantic_facts WHERE id = ?", (fact_id,))
    old_row = dict(cursor.fetchone())
    assert old_row["t_invalid"] is not None
    assert old_row["fact_statement"] == "João prefere café sem açúcar."


def test_extraction_delete_invalidation(temp_db):
    """Garante que a ação DELETE invalida temporariamente o fato correspondente."""
    # Fato pré-existente
    fact_id = insert_semantic_fact(temp_db, "user", "uuid-john", "João prefere café sem açúcar.")

    # Mock retorna decisão de DELETE
    mock_llm = MockLLMAdapter([
        f'{{"action": "DELETE", "target_id": {fact_id}, "updated_statement": null}}'
    ])
    extractor = SemanticExtractor(mock_llm)

    results = extractor.evaluate_and_store_facts(
        temp_db, "user", "uuid-john", ["João não toma mais café."]
    )

    assert len(results) == 1
    assert results[0]["action"] == "DELETE"
    assert results[0]["target_id"] == fact_id

    # Nenhum fato deve estar ativo
    active = get_active_semantic_facts(temp_db, "user", "uuid-john")
    assert len(active) == 0

    # Fato antigo ainda está no histórico mas com t_invalid
    cursor = temp_db.execute("SELECT * FROM semantic_facts WHERE id = ?", (fact_id,))
    old_row = dict(cursor.fetchone())
    assert old_row["t_invalid"] is not None
