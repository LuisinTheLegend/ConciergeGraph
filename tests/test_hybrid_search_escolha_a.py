"""
tests/test_hybrid_search_escolha_a.py — Escolha A (Rodada 4.5d)

Garante que chamar HybridSearchEngine.search com enable_probabilistic=True
falhe imediatamente com NotImplementedError e mensagem explícita
(sem fallback silencioso nem acesso ao retriever arquivado), e que
enable_probabilistic=False preserve o comportamento normal.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.config import ConciergeConfig
from core.hybrid_search import HybridSearchEngine


def _make_engine() -> tuple[HybridSearchEngine, MagicMock]:
    store = MagicMock()
    vector_store = MagicMock()
    embedder = MagicMock()
    project_index = MagicMock()
    project_index.resolve_scoped_uuids.return_value = []
    engine = HybridSearchEngine(
        sqlite_store=store,
        vector_store=vector_store,
        embedding_manager=embedder,
        project_index=project_index,
        config=ConciergeConfig(),
    )
    return engine, project_index


def test_enable_probabilistic_true_raises_not_implemented_immediately():
    """Escolha A: enable_probabilistic=True deve falhar alto no início de search()."""
    engine, project_index = _make_engine()

    with pytest.raises(NotImplementedError, match="enable_probabilistic"):
        engine.search("consulta qualquer", "proj-uuid-1", enable_probabilistic=True)

    project_index.resolve_scoped_uuids.assert_not_called()


def test_enable_probabilistic_false_runs_normally():
    """enable_probabilistic=False (padrão) segue o fluxo normal sem erro."""
    engine, project_index = _make_engine()

    result = engine.search("consulta qualquer", "proj-uuid-1", enable_probabilistic=False)

    assert result == []
    project_index.resolve_scoped_uuids.assert_called_once()
