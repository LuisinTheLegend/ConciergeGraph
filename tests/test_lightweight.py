import pytest
import os
import shutil
from core.config import ConciergeConfig
from storage.vector_store import EmbeddingManager, ChromaVectorStore
from core.hybrid_search import HybridSearchEngine
from core.project_index import ProjectIndex
from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR

def test_lightweight_mode_behavior(store, manager):
    """Valida o funcionamento e isolamento do Modo Lightweight.

    Verifica se:
    1. A flag GRAFO_LIGHTWEIGHT_MODE ativa corretamente o lightweight_mode na config.
    2. O EmbeddingManager não faz o carregamento do modelo e retorna None ao gerar embeds.
    3. O ChromaVectorStore entra em modo NO-OP e desativa a inicialização do PersistentClient.
    4. A busca híbrida (HybridSearchEngine) realiza o fallback gracioso para FTS5-only.
    """
    # 0. Garante que há dados no banco SQLite FTS5 antes do teste
    result = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
    assert result.files_processed > 0, "Ingestão inicial para popular banco FTS5 falhou."

    # Define a variável de ambiente para ativar o modo Lightweight
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "true"
    
    try:
        # 1. Valida detecção na configuração
        config = ConciergeConfig()
        assert config.lightweight_mode is True, "Configuração deveria ter lightweight_mode=True com env var ativa."

        # 2. Valida bypass do modelo no EmbeddingManager
        embedder = EmbeddingManager()
        # Não deve levantar erro ao inicializar, mas ao tentar embedar deve dar fallback/None silencioso
        embedding = embedder.embed("test query")
        assert embedding is None, "EmbeddingManager deveria retornar None no modo lightweight (bypass do modelo)."

        # 3. Valida bypass de inicialização no ChromaVectorStore
        tmp_dir = "./tmp_chroma_test"
        vector_store = ChromaVectorStore(persist_dir=tmp_dir)
        assert vector_store._available is False, "ChromaVectorStore deveria estar com _available=False no modo lightweight."
        assert vector_store._client is None, "ChromaVectorStore não deveria ter instanciado o PersistentClient."

        # 4. Valida busca fallback para FTS5
        project_index = ProjectIndex(store, config)
        search_engine = HybridSearchEngine(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            project_index=project_index,
            config=config,
        )

        results = search_engine.search(
            query="interest",  # Termo contido no interest_calculator.py
            project_uuid=PROJECT_UUID,
            top_k=5
        )

        # Como os vetores estão desligados, os resultados devem vir da busca FTS5/BM25
        assert len(results) > 0, "Deveria ter retornado candidatos via FTS5."
        for item in results:
            assert item["score_breakdown"]["vetorial"] == 0.0, "Score vetorial deveria ser 0.0 no modo lightweight."
            assert item["score_final"] > 0.0, "Score final deveria ser baseado no FTS5 + Recência/Centralidade."
            
    finally:
        # Restaura a variável de ambiente original
        os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
