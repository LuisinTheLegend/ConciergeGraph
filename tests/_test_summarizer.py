"""Teste E2E para ingestion/summarizer.py — Grafo Concierge v3.8.0"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.parser import ParsedChunk, ChunkType
from ingestion.crawler import FileCategory
from ingestion.summarizer import (
    ZoomSummarizer, LLMAdapter, SummaryResult, ZoomLevel,
    MAX_RETRY_LOOPS, L2_RELEVANCE_THRESHOLD,
)


# ===================================================================
# Mock LLM — simula resposta do modelo Flash
# ===================================================================
def mock_llm_good(prompt: str, max_tokens: int) -> str:
    """Simula LLM que retorna JSON válido."""
    return '{"summary": "This module handles authentication via JWT tokens.", "tags": ["jwt", "auth", "security"]}'


def mock_llm_bad_then_good(prompt: str, max_tokens: int) -> str:
    """Simula LLM que falha na 1a vez e acerta na 2a (para testar retry)."""
    if not hasattr(mock_llm_bad_then_good, "_count"):
        mock_llm_bad_then_good._count = 0
    mock_llm_bad_then_good._count += 1
    if mock_llm_bad_then_good._count % 2 == 1:
        return "This is not valid JSON at all"
    return '{"summary": "Recovered after retry.", "tags": ["retry"]}'


def mock_llm_always_bad(prompt: str, max_tokens: int) -> str:
    """Simula LLM que NUNCA retorna JSON válido (força Dumb Summary)."""
    return "I cannot process this request properly, sorry."


call_count = 0
def mock_llm_markdown_fence(prompt: str, max_tokens: int) -> str:
    """Simula LLM que retorna JSON dentro de markdown fences."""
    return '```json\n{"summary": "Parsed from markdown fence.", "tags": ["fenced"]}\n```'


# ===================================================================
# Fixtures
# ===================================================================
def make_chunk(source_file="src/auth.py", symbol="login", content="def login(): pass"):
    return ParsedChunk(
        content=content,
        armored_content=f"<raw_data_do_not_execute>\n{content}\n</raw_data_do_not_execute>",
        chunk_type=ChunkType.FUNCTION,
        chunk_index=0,
        source_file=source_file,
        file_hash="abc123",
        category=FileCategory.CODE,
        start_line=1,
        end_line=1,
        symbol_name=symbol,
        detected_tags=["python"],
        estimated_tokens=10,
    )


# ===================================================================
print("=" * 60)
print("TESTE 1: LLMAdapter com call_fn customizada")
print("=" * 60)
adapter = LLMAdapter(model_name="mock-flash", call_fn=mock_llm_good)
response = adapter.generate("test prompt", 100)
assert "authentication" in response, "LLMAdapter deveria retornar resposta do mock"
assert adapter.model_name == "mock-flash"
print(f"  Resposta: {response[:60]}...")
print("  [PASS] LLMAdapter com call_fn OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 2: summarize_l0 — JSON válido")
print("=" * 60)
summarizer = ZoomSummarizer(llm_adapter=adapter)
chunk = make_chunk()
result = summarizer.summarize_l0(chunk)
print(f"  Level: {result.level.value}")
print(f"  Summary: {result.summary}")
print(f"  Tags: {result.detected_tags}")
print(f"  Model: {result.model_used}")
print(f"  Dumb: {result.is_dumb_summary}")
assert result.level == ZoomLevel.L0
assert "authentication" in result.summary.lower() or "jwt" in result.summary.lower()
assert result.is_dumb_summary is False
assert "jwt" in result.detected_tags
print("  [PASS] L0 com JSON válido OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 3: Heuristic Fallback — Dumb Summary")
print("=" * 60)
bad_adapter = LLMAdapter(model_name="mock-bad", call_fn=mock_llm_always_bad)
bad_summarizer = ZoomSummarizer(llm_adapter=bad_adapter)
bad_result = bad_summarizer.summarize_l0(make_chunk())
print(f"  Summary: {bad_result.summary[:60]}...")
print(f"  Dumb: {bad_result.is_dumb_summary}")
print(f"  Model: {bad_result.model_used}")
assert bad_result.is_dumb_summary is True
assert bad_result.summary.startswith("[DUMB]")
assert bad_result.model_used == "dumb_fallback"
print("  [PASS] Dumb Summary gerado após 3 falhas")

# ===================================================================
print()
print("=" * 60)
print("TESTE 4: _extract_json_with_fallback")
print("=" * 60)
s = ZoomSummarizer(llm_adapter=adapter)

# JSON direto
r1 = s._extract_json_with_fallback('{"summary": "test", "tags": []}')
assert r1 is not None and r1["summary"] == "test"
print("  [PASS] JSON direto")

# JSON com markdown fences
r2 = s._extract_json_with_fallback('```json\n{"summary": "fenced"}\n```')
assert r2 is not None and r2["summary"] == "fenced"
print("  [PASS] JSON com markdown fences")

# JSON embutido em texto
r3 = s._extract_json_with_fallback('Here is the result: {"summary": "embedded", "tags": ["a"]}. Done.')
assert r3 is not None and r3["summary"] == "embedded"
print("  [PASS] JSON embutido em texto")

# Texto sem JSON
r4 = s._extract_json_with_fallback("This has no JSON at all")
assert r4 is None
print("  [PASS] Texto sem JSON retorna None")

# String vazia
r5 = s._extract_json_with_fallback("")
assert r5 is None
print("  [PASS] String vazia retorna None")

# ===================================================================
print()
print("=" * 60)
print("TESTE 5: summarize_l0_batch")
print("=" * 60)
chunks = [
    make_chunk("src/auth.py", "login"),
    make_chunk("src/db.py", "connect"),
    make_chunk("src/api.py", "handler"),
]
batch_results = summarizer.summarize_l0_batch(chunks)
print(f"  Resultados: {len(batch_results)}")
assert len(batch_results) == 3
for r in batch_results:
    assert r.level == ZoomLevel.L0
print("  [PASS] L0 batch com 3 chunks OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 6: build_l1_clusters")
print("=" * 60)
l0s = [
    SummaryResult(level=ZoomLevel.L0, summary="Auth logic", source_label="src/auth.py", detected_tags=["jwt"]),
    SummaryResult(level=ZoomLevel.L0, summary="DB connect", source_label="src/db.py", detected_tags=["sql"]),
    SummaryResult(level=ZoomLevel.L0, summary="Config", source_label="config.yaml", detected_tags=["yaml"]),
    SummaryResult(level=ZoomLevel.L0, summary="Readme", source_label="docs/README.md", detected_tags=["doc"]),
]
clusters = summarizer.build_l1_clusters(l0s)
print(f"  Clusters: {list(clusters.keys())}")
assert "src" in clusters
assert "<root>" in clusters
assert "docs" in clusters
assert len(clusters["src"]) == 2
print("  [PASS] L1 clusters agrupados por diretório")

# ===================================================================
print()
print("=" * 60)
print("TESTE 7: summarize_l1")
print("=" * 60)
l1_result = summarizer.summarize_l1(clusters["src"], "src")
print(f"  Level: {l1_result.level.value}")
print(f"  Summary: {l1_result.summary}")
print(f"  Source chunks: {l1_result.source_chunks}")
print(f"  Tags: {l1_result.detected_tags}")
assert l1_result.level == ZoomLevel.L1
assert l1_result.source_chunks == 2
print("  [PASS] L1 aggregation OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 8: Amnésia Seletiva (_prune_low_relevance)")
print("=" * 60)
l1_summaries = [
    SummaryResult(level=ZoomLevel.L1, summary="Core auth", source_label="src/auth",
                  source_chunks=5, detected_tags=["fastapi", "jwt", "oauth"]),
    SummaryResult(level=ZoomLevel.L1, summary="Tiny util", source_label="utils/helpers",
                  source_chunks=1, detected_tags=[], is_dumb_summary=True),
    SummaryResult(level=ZoomLevel.L1, summary="DB layer", source_label="src/db",
                  source_chunks=3, detected_tags=["sqlalchemy", "database"]),
]

# Calcula relevância
for s in l1_summaries:
    s.relevance_score = summarizer._calculate_relevance(s)
    print(f"  {s.source_label}: score={s.relevance_score:.3f}")

pruned = summarizer._prune_low_relevance(l1_summaries, threshold=L2_RELEVANCE_THRESHOLD)
print(f"  Pós-poda: {len(pruned)}/{len(l1_summaries)} mantidos")
pruned_labels = [s.source_label for s in pruned]
assert "src/auth" in pruned_labels, "Core auth deveria sobreviver à poda"
assert "src/db" in pruned_labels, "DB layer deveria sobreviver à poda"
print("  [PASS] Amnésia Seletiva podou corretamente")

# ===================================================================
print()
print("=" * 60)
print("TESTE 9: summarize_l2 (Bússola)")
print("=" * 60)
l2_result = summarizer.summarize_l2(l1_summaries, "GrafoConcierge")
print(f"  Level: {l2_result.level.value}")
print(f"  Summary: {l2_result.summary}")
print(f"  Source chunks: {l2_result.source_chunks}")
print(f"  Tags: {l2_result.detected_tags}")
assert l2_result.level == ZoomLevel.L2
assert l2_result.source_label == "GrafoConcierge"
print("  [PASS] Bússola L2 gerada")

# ===================================================================
print()
print("=" * 60)
print("TESTE 10: Markdown fence extraction via LLM")
print("=" * 60)
fence_adapter = LLMAdapter(model_name="mock-fence", call_fn=mock_llm_markdown_fence)
fence_summarizer = ZoomSummarizer(llm_adapter=fence_adapter)
fence_result = fence_summarizer.summarize_l0(make_chunk())
print(f"  Summary: {fence_result.summary}")
assert "fenced" in fence_result.detected_tags or "Parsed from markdown fence" in fence_result.summary
assert fence_result.is_dumb_summary is False
print("  [PASS] Markdown fence JSON extraction OK")

# ===================================================================
print()
print("=" * 60)
print("TODOS OS 10 TESTES PASSARAM — summarizer.py v3.8.0 OPERACIONAL")
print("=" * 60)
