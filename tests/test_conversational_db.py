"""
tests/_test_conversational_db.py — Testes da Camada Conversacional Híbrida (Passo 1)

Valida:
    - Criação de user_core_memory e semantic_facts.
    - CHECK constraints em scope_type.
    - Índices e comportamento temporal.
    - Validação de payloads em QdrantVectorStore.
"""

import sqlite3
import pytest
from unittest.mock import MagicMock

from storage.schema import SchemaManager
from core.vector_backend import QdrantVectorStore, QDRANT_AVAILABLE


@pytest.fixture
def temp_db():
    """Cria uma conexão SQLite em memória com o schema aplicado."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    
    manager = SchemaManager(conn)
    manager.apply_full_schema()
    
    yield conn
    conn.close()


def test_conversational_tables_creation(temp_db):
    """Garante que as novas tabelas de memória nascem perfeitamente no SQLite."""
    manager = SchemaManager(temp_db)
    tables = manager.verify_tables_exist()
    
    assert tables["user_core_memory"] is True
    assert tables["semantic_facts"] is True


def test_user_core_memory_scope_constraint(temp_db):
    """Valida a restrição CHECK na coluna scope_type da tabela user_core_memory."""
    # Escopos válidos: user, session, agent, org
    for valid_scope in ["user", "session", "agent", "org"]:
        cur = temp_db.execute(
            """INSERT INTO user_core_memory (scope_type, scope_id, block_label, content)
               VALUES (?, ?, ?, ?)""",
            (valid_scope, "uuid-123", "persona", "Conteúdo teste")
        )
        assert cur.lastrowid is not None

    # Escopo inválido deve estourar erro de restrição CHECK
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.execute(
            """INSERT INTO user_core_memory (scope_type, scope_id, block_label, content)
               VALUES (?, ?, ?, ?)""",
            ("project", "uuid-123", "persona", "Conteúdo inválido")
        )


def test_semantic_facts_bi_temporal(temp_db):
    """Valida o comportamento de bi-temporalidade da tabela semantic_facts."""
    # Insere um fato ativo (t_invalid é NULL)
    cur = temp_db.execute(
        """INSERT INTO semantic_facts (scope_type, scope_id, fact_statement)
           VALUES (?, ?, ?)""",
        ("user", "uuid-john", "João prefere respostas concisas.")
    )
    fact_id = cur.lastrowid
    assert fact_id is not None

    # Insere outro fato e simula inativação/substituição temporal (definindo t_invalid)
    temp_db.execute(
        """INSERT INTO semantic_facts (scope_type, scope_id, fact_statement, t_invalid)
           VALUES (?, ?, ?, datetime('now'))""",
        ("user", "uuid-john", "João usava React v17.")
    )

    # Consulta fatos semânticos atualmente ativos
    rows = temp_db.execute(
        "SELECT * FROM semantic_facts WHERE scope_id = ? AND t_invalid IS NULL",
        ("uuid-john",)
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["fact_statement"] == "João prefere respostas concisas."

    # Verifica se o fato antigo inativo é retornado na consulta histórica total
    total_rows = temp_db.execute(
        "SELECT * FROM semantic_facts WHERE scope_id = ?",
        ("uuid-john",)
    ).fetchall()
    assert len(total_rows) == 2


def test_qdrant_vector_store_payload_validation():
    """Garante que o QdrantVectorStore valida payloads sob a coleção episodic_memory."""
    # Criamos o store de forma a ignorar a conexão real
    store = QdrantVectorStore(collection_name="episodic_memory")
    
    # Se qdrant-client não estiver instalado, a validação de payload ainda funciona
    # porque a validação é puramente lógica em Python.
    
    # 1. Payload válido
    valid_payload = {
        "scope_type": "user",
        "scope_id": "user-123",
        "timestamp": "2026-06-17T18:00:00Z",
        "message": "Fato conversacional",
        "utility_alpha": 1.0,
        "utility_beta": 1.0
    }
    # Não deve subir exceção
    store._validate_payload(valid_payload)

    # 2. Falta de chaves obrigatórias
    for missing_key in ["scope_type", "scope_id", "timestamp", "utility_alpha", "utility_beta"]:
        invalid_payload = valid_payload.copy()
        invalid_payload.pop(missing_key)
        
        with pytest.raises(ValueError, match="exige a chave"):
            store._validate_payload(invalid_payload)

    # 3. escopo inválido
    invalid_scope_payload = valid_payload.copy()
    invalid_scope_payload["scope_type"] = "project" # inválido
    with pytest.raises(ValueError, match="scope_type inválido"):
        store._validate_payload(invalid_scope_payload)


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="qdrant-client não instalado")
def test_qdrant_collection_initialization_real():
    """Valida a criação de coleções reais no Qdrant quando em memória."""
    store = QdrantVectorStore(memory=True, collection_name="test_code_collection")
    assert store._client is not None
    assert store._client.collection_exists("test_code_collection") is True
    assert store._client.collection_exists("episodic_memory") is True
