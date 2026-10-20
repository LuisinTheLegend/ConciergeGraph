"""scratch/investigate_backfill.py

Investigação B4: Prova de backfill (ou ausência dele).
Verifica o que ocorre quando:
1. Arquivo minerado sem LLM (summary permanece NULL ou [DUMB]).
2. LLM passa a estar configurado, mas o arquivo NÃO mudou.
3. LLM configurado e o arquivo MUDOU.
"""

import tempfile
from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager
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

class StubNoLLMSummarizer:
    """Simula ambiente sem LLM: não gera resumos (ou gera dumb que é omitido)."""
    def __init__(self):
        self.calls = 0
    def summarize_l0(self, chunk: ParsedChunk):
        self.calls += 1
        return SummaryResult(
            level=ZoomLevel.L0,
            summary=f"[DUMB] {chunk.content[:20]}...",
            source_label=chunk.source_file,
            is_dumb_summary=True,
            detected_tags=["tested_tag"],
        )
    async def summarize_l0_async(self, chunk: ParsedChunk):
        return self.summarize_l0(chunk)
    def summarize_l0_grouped(self, chunks: list[ParsedChunk], indices: list[int]):
        return [(idx, self.summarize_l0(c)) for idx, c in zip(indices, chunks)]

class StubRealLLMSummarizer:
    """Simula ambiente com LLM ativo gerando resumos genuínos."""
    def __init__(self):
        self.calls = 0
    def summarize_l0(self, chunk: ParsedChunk):
        self.calls += 1
        return SummaryResult(
            level=ZoomLevel.L0,
            summary=f"Genuine AI Summary for {chunk.symbol_name}",
            source_label=chunk.source_file,
            is_dumb_summary=False,
            detected_tags=["ai_generated"],
        )
    async def summarize_l0_async(self, chunk: ParsedChunk):
        return self.summarize_l0(chunk)
    def summarize_l0_grouped(self, chunks: list[ParsedChunk], indices: list[int]):
        return [(idx, self.summarize_l0(c)) for idx, c in zip(indices, chunks)]

def run_experiment():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        py_file = repo_dir / "service.py"
        py_file.write_text("def process_data():\n    return 'initial'\n", encoding="utf-8")

        db_path = str(tmp_path / "test.db")
        chroma_dir = str(tmp_path / "chroma")

        store = SqliteStore(db_path)
        store.create_project("proj_backfill", "Backfill Test Repo")
        project_uuid = "proj_backfill"
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="backfill_test")
        embedder = StubDeterministicEmbedder()

        # FASE 1: Mineração sem LLM
        no_llm = StubNoLLMSummarizer()
        ingestion_no_llm = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            summarizer=no_llm,
        )
        res1 = ingestion_no_llm.mine(project_uuid, str(repo_dir))
        nodes1 = store.get_nodes_by_project(project_uuid)
        func_node1 = next(n for n in nodes1 if "process_data" in n["label"])
        print("FASE 1 (Sem LLM - 1a mineracao):")
        print(f"  files_processed={res1.files_processed}, files_skipped={res1.files_skipped}")
        print(f"  nodes.summary={repr(func_node1['summary'])}")

        # FASE 2: LLM passa a estar configurado, mas o arquivo NÃO mudou
        real_llm = StubRealLLMSummarizer()
        ingestion_real_llm = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            summarizer=real_llm,
        )
        res2 = ingestion_real_llm.mine(project_uuid, str(repo_dir))
        nodes2 = store.get_nodes_by_project(project_uuid)
        func_node2 = next(n for n in nodes2 if "process_data" in n["label"])
        print("\nFASE 2 (LLM configurado, arquivo INALTERADO):")
        print(f"  files_processed={res2.files_processed}, files_skipped={res2.files_skipped}")
        print(f"  real_llm.calls={real_llm.calls}")
        print(f"  nodes.summary={repr(func_node2['summary'])}")

        # FASE 3: LLM configurado e o arquivo MUDOU
        py_file.write_text("def process_data():\n    return 'updated content'\n", encoding="utf-8")
        res3 = ingestion_real_llm.mine(project_uuid, str(repo_dir))
        nodes3 = store.get_nodes_by_project(project_uuid)
        func_node3 = next(n for n in nodes3 if "process_data" in n["label"])
        print("\nFASE 3 (LLM configurado, arquivo MODIFICADO):")
        print(f"  files_processed={res3.files_processed}, files_skipped={res3.files_skipped}")
        print(f"  real_llm.calls={real_llm.calls}")
        print(f"  nodes.summary={repr(func_node3['summary'])}")

        store.close()

if __name__ == "__main__":
    run_experiment()
