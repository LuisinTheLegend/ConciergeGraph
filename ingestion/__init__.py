"""
ingestion/ — Motor de Ingestão Apex — Grafo Concierge v3.8.0

Módulos:
    crawler.py      → Varredura de filesystem, detecção de deltas via SHA256, .gitignore
    parser.py       → Semantic/AST Chunking com Prompt Armor (sanitização XML)
    summarizer.py   → Engrenagem de Zoom (L0/L1/L2) com Model Tiering
    orchestrator.py → IngestionManager — coordena Crawl → Parse → Summarize → Store
"""
from ingestion.crawler import ProjectCrawler, CrawlReport, CrawlResult
from ingestion.parser import FileParser, ParsedChunk
from ingestion.summarizer import ZoomSummarizer, SummaryResult
from ingestion.orchestrator import IngestionManager, IngestionResult

__all__ = [
    "ProjectCrawler",
    "CrawlReport",
    "CrawlResult",
    "FileParser",
    "ParsedChunk",
    "ZoomSummarizer",
    "SummaryResult",
    "IngestionManager",
    "IngestionResult",
]