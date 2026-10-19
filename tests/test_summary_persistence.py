"""tests/test_summary_persistence.py

TDD tests for F4-010:
- Persistence of L0 summaries in SQLite nodes table (nodes.summary field).
- Delta cache preserves pre-existing summary for cached nodes.
- Nodes without generated summary remain NULL without error.
"""

from pathlib import Path
from typing import Optional

import pytest

from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager, IngestionResult
from ingestion.parser import ParsedChunk
from ingestion.summarizer import SummaryResult, ZoomLevel


class StubDeterministicEmbedder:
    def __init__(self):
        self.tier = EmbeddingTier.FLASH
        self.dimensions = 384

    def embed(self, text: str):
        return [0.1] * 384

    def embed_batch(self, texts: list[str]):
        return [[0.1] * 384 for _ in texts]


class StubDeterministicSummarizer:
    """Fake summarizer producing deterministic L0 summaries."""

    def __init__(self, skip_symbols: Optional[set[str]] = None):
        self.skip_symbols = skip_symbols or set()

    def summarize_l0(self, chunk: ParsedChunk) -> Optional[SummaryResult]:
        if chunk.symbol_name in self.skip_symbols:
            return None
        return SummaryResult(
            level=ZoomLevel.L0,
            summary=f"Deterministic summary for {chunk.source_file}::{chunk.symbol_name}",
            source_label=chunk.source_file,
            detected_tags=["tested_tag"],
        )

    async def summarize_l0_async(self, chunk: ParsedChunk) -> Optional[SummaryResult]:
        return self.summarize_l0(chunk)

    def summarize_l0_grouped(self, chunks: list[ParsedChunk], indices: list[int]) -> list[tuple[int, SummaryResult]]:
        res = []
        for idx, chunk in zip(indices, chunks):
            s = self.summarize_l0(chunk)
            if s is not None:
                res.append((idx, s))
        return res


def _create_sample_repo(repo_path: Path):
    repo_path.mkdir(parents=True, exist_ok=True)
    code_file = repo_path / "example.py"
    code_file.write_text(
        "def summarized_func():\n"
        "    return 'has summary'\n\n"
        "def omitted_func():\n"
        "    return 'no summary'\n",
        encoding="utf-8"
    )


class TestSummaryPersistence:
    """Tests that L0 summaries generated during ingestion are persisted in nodes.summary (F4-010)."""

    def test_l0_summaries_persisted_in_nodes_table(self, tmp_path: Path):
        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")
        repo_dir = tmp_path / "repo"
        _create_sample_repo(repo_dir)

        store = SqliteStore(db_path)
        store.create_project("test_proj", "Test Repo")
        project_uuid = "test_proj"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="summary_test")
        embedder = StubDeterministicEmbedder()
        summarizer = StubDeterministicSummarizer(skip_symbols={"omitted_func"})

        ingestion = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            summarizer=summarizer,
        )

        res1 = ingestion.mine(project_uuid, str(repo_dir))
        assert isinstance(res1, IngestionResult)

        nodes = store.get_nodes_by_project(project_uuid)
        node_map = {n["label"]: n for n in nodes}

        # 1. Nó que teve sumário gerado deve ter summary preenchido no SQLite
        summarized_node = node_map.get("example.py::summarized_func")
        assert summarized_node is not None
        assert summarized_node["summary"] is not None, "nodes.summary não deve ser nulo para nó novo com sumário"
        assert summarized_node["summary"] == "Deterministic summary for example.py::summarized_func"

        # 2. Nó sem sumário continua com summary NULL sem erro
        omitted_node = node_map.get("example.py::omitted_func")
        assert omitted_node is not None
        assert omitted_node["summary"] is None, "Nó sem sumário deve permanecer com summary NULL"

        # 3. 2ª mineração (arquivos inalterados / nós em cache): mantém o sumário existente
        res2 = ingestion.mine(project_uuid, str(repo_dir))
        nodes_after = store.get_nodes_by_project(project_uuid)
        node_map_after = {n["label"]: n for n in nodes_after}
        cached_node = node_map_after.get("example.py::summarized_func")
        assert cached_node is not None
        assert cached_node["summary"] == "Deterministic summary for example.py::summarized_func", \
            "Nó em cache deve manter seu sumário intacto"

        store.close()
