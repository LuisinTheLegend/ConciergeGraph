"""
ingestion/ - Apex Ingestion Engine - Grafo Concierge v3.8.0

Modules:
    crawler.py      → Filesystem scanning, delta detection via SHA256, .gitignore
    parser.py       → Semantic/AST Chunking with Prompt Armor (XML sanitization)
    summarizer.py   → Zoom Gear (L0/L1/L2) with Model Tiering
    orchestrator.py → IngestionManager — coordinates Crawl → Parse → Summarize → Store
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