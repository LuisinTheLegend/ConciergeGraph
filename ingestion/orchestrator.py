"""
ingestion/orchestrator.py - Grafo Concierge v3.8.0 (Absolute Solidity)

IngestionManager — Orchestrator of the Apex Ingestion Engine.

This is the engine behind the `concierge mine` command.
Coordinates the complete flow: Crawl → Parse → Summarize → Store (SQLite + Vector).

Execution Flow:
    1. CRAWL: ProjectCrawler scans the filesystem, detects deltas (SHA256).
    2. PARSE: FileParser splits new/modified files into semantic chunks.
    3. SUMMARIZE: ZoomSummarizer generates L0 summaries for each chunk.
    4. EMBED: EmbeddingManager generates vectors for each chunk.
    5. STORE (SQLite): Creates nodes, structural edges, and commit_log.
    6. STORE (Vector): QdrantVectorStore/ChromaVectorStore stores embeddings in batch.
    7. GARBAGE COLLECTION: Removes nodes and vectors of deleted files.
    8. ZOOM GEAR (async/optional): Generates L1 and L2 summaries.

Return:
    Dict compatible with the concierge_mine MCP tool response:
    {
        "files_processed": int,
        "categories": {"code": int, "doc": int, "config": int, "conversation": int},
        "nodes_created": int,
        "embeddings_stored": int,
        "tags_applied": list[str]
    }

Integration:
    - storage.store.SqliteStore → Relational persistence.
    - storage.vector_store.ChromaVectorStore/QdrantVectorStore → Vector persistence.
    - storage.vector_store.EmbeddingManager → Embedding generation.
    - ingestion.crawler.ProjectCrawler → Filesystem scanning.
    - ingestion.parser.FileParser → Semantic chunking.
    - ingestion.summarizer.ZoomSummarizer → Zoom Gear.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from storage import SqliteStore, ChromaVectorStore, EmbeddingManager
from ingestion.crawler import ProjectCrawler, CrawlReport, CrawlResult, FileCategory
from ingestion.parser import FileParser, ParsedChunk
from ingestion.summarizer import ZoomSummarizer, SummaryResult, ZoomLevel

logger = logging.getLogger("grafo-concierge.orchestrator")


# ---------------------------------------------------------------------------
# IngestionResult — standardized return of concierge mine
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Consolidated result of the ingestion pipeline.

    Compatible with the response of the concierge_mine MCP Tool (v3.8).
    """
    files_processed: int = 0
    categories: dict[str, int] = field(default_factory=lambda: {
        "code": 0, "doc": 0, "config": 0, "conversation": 0
    })
    nodes_created: int = 0
    embeddings_stored: int = 0
    tags_applied: list[str] = field(default_factory=list)
    files_skipped: int = 0
    files_deleted: int = 0
    summaries_generated: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Converts to dict compatible with MCP response."""
        return {
            "files_processed": self.files_processed,
            "categories": self.categories,
            "nodes_created": self.nodes_created,
            "embeddings_stored": self.embeddings_stored,
            "tags_applied": self.tags_applied,
            "files_skipped": self.files_skipped,
            "files_deleted": self.files_deleted,
            "summaries_generated": self.summaries_generated,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# IngestionManager — Pipeline Orchestrator
# ---------------------------------------------------------------------------

class IngestionManager:
    """Orchestrator of the Apex Ingestion Engine (concierge mine).

    Coordinates the flow Crawl → Parse → Summarize → Embed → Store → GC.
    Each step is isolated and resilient (Semantic Fallback).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        embedding_manager: EmbeddingManager,
        summarizer: Optional[ZoomSummarizer] = None,
        crawler: Optional[ProjectCrawler] = None,
        parser: Optional[FileParser] = None,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._embedder = embedding_manager
        self._summarizer = summarizer
        self._crawler = crawler or ProjectCrawler(sqlite_store)
        self._parser = parser or FileParser()

        logger.info(
            "IngestionManager inicializado: summarizer=%s, embedder_tier=%s",
            "ON" if summarizer else "OFF",
            embedding_manager.tier.value if hasattr(embedding_manager, 'tier') else "unknown",
        )

    # ===================================================================
    # MINE — Entry Point (concierge mine)
    # ===================================================================

    def mine(
        self,
        project_uuid: str,
        source_path: str,
        auto_tag: bool = True,
    ) -> IngestionResult:
        """Executes the complete ingestion pipeline for a project.

        This is the main method called by the concierge_mine MCP Tool.
        """
        t0 = time.perf_counter()
        result = IngestionResult()

        logger.info("=" * 60)
        logger.info("MINE STARTED: project=%s, source=%s", project_uuid, source_path)
        logger.info("=" * 60)

        # --- Validation: project exists? ---
        try:
            self._store.get_project(project_uuid)
        except Exception as e:
            raise ValueError(f"Project not found: {project_uuid}") from e

        # --- STEP 1: CRAWL ---
        logger.info("[1/7] CRAWL — Filesystem scanning...")
        crawl_report = self._step_crawl(source_path, project_uuid)
        result.files_processed = len(crawl_report.new_files)
        result.files_skipped = len(crawl_report.unchanged_files)
        result.categories = crawl_report.categories
        logger.info(
            "[1/7] CRAWL completed: %d new, %d unchanged, %d deleted.",
            result.files_processed, result.files_skipped, len(crawl_report.deleted_node_ids),
        )

        # --- Short-circuit: nothing new and nothing deleted ---
        if not crawl_report.new_files and not crawl_report.deleted_node_ids:
            logger.info("No change detected — ending pipeline.")
            elapsed = time.perf_counter() - t0
            logger.info("MINE COMPLETED in %.2fs (noop).", elapsed)
            return result

        # --- STEP 2: PARSE ---
        chunks: list[ParsedChunk] = []
        if crawl_report.new_files:
            logger.info("[2/8] PARSE — Semantic chunking of %d files...", len(crawl_report.new_files))
            chunks = self._step_parse(crawl_report.new_files, result)
            logger.info("[2/8] PARSE completed: %d chunks extracted.", len(chunks))

        # --- STEP 2.5: DELTA CACHE ---
        cached_count = 0
        if chunks:
            logger.info("[2.5/8] DELTA CACHE — Checking unchanged chunks...")
            cached_count = self._detect_cached_chunks(chunks, project_uuid)
            logger.info(
                "[2.5/8] DELTA CACHE completed: %d cached, %d new for LLM.",
                cached_count, len(chunks) - cached_count,
            )

        # --- STEP 3: SUMMARIZE (L0) ---
        uncached_chunks = [c for c in chunks if not c.cached]
        summaries: list[SummaryResult] = []
        if uncached_chunks and self._summarizer:
            logger.info("[3/8] SUMMARIZE — Generating %d L0 summaries (skipping %d cached)...",
                        len(uncached_chunks), cached_count)
            summaries = self._step_summarize(uncached_chunks, result)
            result.summaries_generated = len(summaries)
            logger.info("[3/8] SUMMARIZE completed: %d L0 summaries generated.", len(summaries))
        else:
            logger.info("[3/8] SUMMARIZE — Ignored (summarizer=%s, new=%d).",
                        "OFF" if not self._summarizer else "ON", len(uncached_chunks))

        # --- STEP 4: STORE SQLite ---
        if chunks:
            logger.info("[4/8] STORE SQLite — Persisting %d chunks...", len(chunks))
            nodes_created = self._step_store_sqlite(chunks, project_uuid, auto_tag, result)
            result.nodes_created = nodes_created
            logger.info("[4/8] STORE SQLite completed: %d nodes created.", nodes_created)

        # Update file_hash of cached nodes to avoid Garbage Collection
        if cached_count > 0:
            self._apply_cache_updates(chunks, project_uuid)

        # Remove obsolete nodes of files that were modified
        if crawl_report.new_files:
            for f in crawl_report.new_files:
                try:
                    self._store.cleanup_obsolete_nodes(project_uuid, f.relative_path, f.file_hash)
                    logger.debug("Cleanup post-ingestion: obsolete nodes of %s removed.", f.relative_path)
                except Exception as e:
                    logger.warning("Failed post-ingestion cleanup for %s: %s", f.relative_path, e)


        # --- STEP 5: EMBED ---
        embed_items: list[dict] = []
        if chunks:
            logger.info("[5/8] EMBED — Generating embeddings...", len(chunks))
            embed_items = self._step_embed(chunks, project_uuid, result)
            logger.info("[5/8] EMBED completed: %d embeddings generated.", len(embed_items))

        # --- STEP 6: STORE Vector ---
        if embed_items:
            logger.info("[6/8] STORE Vector — Batch insert of %d embeddings...", len(embed_items))
            stored = self._step_store_vector(embed_items, result)
            result.embeddings_stored = stored
            logger.info("[6/8] STORE Vector completed: %d embeddings stored.", stored)

        # --- STEP 7: GARBAGE COLLECTION ---
        if crawl_report.deleted_node_ids:
            logger.info("[7/8] GC — Removing %d orphan nodes...", len(crawl_report.deleted_node_ids))
            deleted = self._step_garbage_collection(crawl_report.deleted_node_ids, project_uuid, result)
            result.files_deleted = deleted
            logger.info("[7/8] GC completed: %d nodes removed.", deleted)
        else:
            logger.info("[7/8] GC — No orphan nodes detected.")

        # --- Tag consolidation ---
        result.tags_applied = self._consolidate_tags(chunks)

        elapsed = time.perf_counter() - t0
        logger.info("=" * 60)
        logger.info(
            "MINE COMPLETED in %.2fs: %d processed, %d nodes, %d embeddings, %d errors.",
            elapsed, result.files_processed, result.nodes_created,
            result.embeddings_stored, len(result.errors),
        )
        logger.info("=" * 60)

        return result

    # ===================================================================
    # ETAPAS DO PIPELINE
    # ===================================================================

    def _step_crawl(self, source_path: str, project_uuid: str) -> CrawlReport:
        """Step 1: Filesystem scan."""
        return self._crawler.crawl(source_path, project_uuid)

    def _step_parse(self, new_files: list[CrawlResult], result: IngestionResult) -> list[ParsedChunk]:
        """Step 2: Semantic Chunking via parse_batch (native Semantic Fallback).

        Delegates to self._parser.parse_batch() which already implements the same
        Semantic Fallback per file, eliminating loop duplication.
        """
        try:
            return self._parser.parse_batch(new_files)
        except Exception as e:
            error_msg = f"parse_batch failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return []

    def _detect_cached_chunks(self, chunks: list[ParsedChunk], project_uuid: str) -> int:
        """Step 2.5: Delta Cache — detects chunks whose content has not changed.

        Compares each parsed chunk with existing nodes in SQLite by label
        (source_file::symbol_name). If the textual content is identical,
        marks the chunk as cached and copies existing summary/tags.

        Returns:
            Number of chunks marked as cached.
        """
        try:
            existing_nodes = self._store.get_nodes_by_project(project_uuid)
        except Exception as e:
            logger.warning("Delta Cache: failed to fetch existing nodes: %s", e)
            return 0

        if not existing_nodes:
            return 0

        # Builds map: label → {content, summary, tags, id, file_hash}
        import json as _json
        node_map: dict[str, dict] = {}
        for node in existing_nodes:
            if node.get("type") in ("directory", "cluster", "project"):
                continue
            label = node.get("label", "")
            if not label:
                continue

            tags = node.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = _json.loads(tags)
                except Exception:
                    tags = []

            node_map[label] = {
                "content": node.get("content", ""),
                "summary": node.get("summary", ""),
                "tags": tags if isinstance(tags, list) else [],
                "id": node["id"],
                "file_hash": node.get("file_hash", ""),
            }

        cached_count = 0
        for chunk in chunks:
            label = f"{chunk.source_file}::{chunk.symbol_name}"
            existing = node_map.get(label)

            if existing and existing["content"] and existing["content"] == chunk.content:
                # Content identical — reuse summary and tags
                chunk.cached = True
                chunk.node_id = existing["id"]
                chunk.cached_summary = existing["summary"]
                chunk.cached_tags = existing["tags"]
                cached_count += 1
                logger.debug("Delta Cache HIT: %s (node_id=%d)", label, existing["id"])

        return cached_count

    def _apply_cache_updates(self, chunks: list[ParsedChunk], project_uuid: str) -> None:
        """Updates file_hash of cached nodes to the new file hash.

        When a file changes hash (file content changed) but a specific chunk
        remained identical, we need to update the file_hash of this node
        to the new hash, otherwise the Garbage Collector will consider it orphan.
        """
        updates: list[tuple[int, str]] = []
        for chunk in chunks:
            if chunk.cached and chunk.node_id is not None:
                updates.append((chunk.node_id, chunk.file_hash))

        if updates:
            try:
                updated = self._store.update_nodes_file_hash_bulk(updates)
                logger.info("Delta Cache: %d nodes with updated file_hash.", updated)
            except Exception as e:
                logger.error("Delta Cache: failed to update file_hash: %s", e)


    def generate_community_summary(self, nodes_block: str) -> Optional[dict]:
        """Generates a community summary via LLM if the summarizer is configured.

        Public API that encapsulates LLM access, preventing JanitorService
        from accessing self._ingestion._summarizer._llm directly (violation of Law of Demeter).

        Args:
            nodes_block: Text with the community nodes to summarize.

        Returns:
            Dict with 'summary' (str) and 'tags' (list[str]), or None if LLM
            is not configured or fails.
        """
        if not self._summarizer or not hasattr(self._summarizer, "_llm") or not self._summarizer._llm:
            return None
        try:
            prompt = (
                "You are a software architect. Synthesize the following node descriptions belonging "
                "to a logical community in the project graph into a single cohesive community summary.\n"
                "Return ONLY a valid JSON object with these fields:\n"
                '- "summary": A cohesive description of this community\'s purpose (max 3 sentences).\n'
                '- "tags": Consolidated list of key technologies and concepts.\n\n'
                f"Nodes in community:\n{nodes_block}\n\n"
                "Respond with ONLY the JSON object, no markdown fences, no extra text."
            )
            raw = self._summarizer._llm.generate(prompt, max_tokens=300)
            parsed = self._summarizer._extract_json_with_fallback(raw)
            if parsed and "summary" in parsed:
                return {
                    "summary": parsed["summary"],
                    "tags": parsed.get("tags", []) if isinstance(parsed.get("tags"), list) else [],
                }
        except Exception as e:
            logger.warning("generate_community_summary: LLM failed: %s", e)
        return None


    def _step_summarize(self, chunks: list[ParsedChunk], result: IngestionResult) -> list[SummaryResult]:
        """Step 3: L0 summaries generation — async + grouping + fallback.

        Optimization pipeline:
            1. Groups small chunks (< 50 tokens) into batched prompts.
            2. Sends remaining chunks via asyncio.gather with Semaphore.
            3. Fallback to ThreadPoolExecutor if asyncio fails.
        """
        import asyncio

        SMALL_CHUNK_THRESHOLD = 50  # tokens
        GROUP_SIZE = 5  # chunks per grouped prompt
        MAX_CONCURRENCY = 20  # semaphore limit

        # --- Phase 1: Separate small chunks for grouping ---
        small_chunks: list[tuple[int, ParsedChunk]] = []
        regular_chunks: list[tuple[int, ParsedChunk]] = []

        for idx, chunk in enumerate(chunks):
            if chunk.estimated_tokens < SMALL_CHUNK_THRESHOLD and chunk.estimated_tokens > 0:
                small_chunks.append((idx, chunk))
            else:
                regular_chunks.append((idx, chunk))

        results = [None] * len(chunks)

        # --- Phase 2: Process small groups (batching in prompt) ---
        if small_chunks and self._summarizer:
            logger.info("Grouping: %d small chunks into groups of %d.", len(small_chunks), GROUP_SIZE)
            for batch_start in range(0, len(small_chunks), GROUP_SIZE):
                batch = small_chunks[batch_start:batch_start + GROUP_SIZE]
                batch_indices = [idx for idx, _ in batch]
                batch_chunks = [chunk for _, chunk in batch]

                try:
                    grouped_results = self._summarizer.summarize_l0_grouped(batch_chunks, batch_indices)
                    for orig_idx, summary in grouped_results:
                        results[orig_idx] = summary
                except Exception as e:
                    logger.warning("Grouped summarization failed, individual fallback: %s", e)

                # Chunks not resolved by the group → move to regular
                for idx, chunk in batch:
                    if results[idx] is None:
                        regular_chunks.append((idx, chunk))

        # --- Phase 3: Process regular chunks via asyncio ---
        if regular_chunks:
            async def _run_async_summaries():
                sem = asyncio.Semaphore(MAX_CONCURRENCY)

                async def _bounded_summarize(idx: int, chunk: ParsedChunk):
                    async with sem:
                        try:
                            s = await self._summarizer.summarize_l0_async(chunk)
                            return idx, s, None
                        except Exception as e:
                            return idx, None, f"Async L0 failed for {chunk.source_file}: {e}"

                tasks = [_bounded_summarize(idx, chunk) for idx, chunk in regular_chunks]
                return await asyncio.gather(*tasks)

            try:
                # Tenta usar loop existente ou criar novo
                try:
                    loop = asyncio.get_running_loop()
                    # Already inside a loop — use to_thread for the whole block
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        async_results = pool.submit(
                            lambda: asyncio.run(_run_async_summaries())
                        ).result()
                except RuntimeError:
                    # No loop running — create a new one
                    async_results = asyncio.run(_run_async_summaries())

                for idx, summary, error_msg in async_results:
                    if error_msg:
                        logger.error(error_msg)
                        result.errors.append(error_msg)
                    if summary:
                        results[idx] = summary

            except Exception as e:
                logger.warning("Async summarization failed, ThreadPool fallback: %s", e)
                # Fallback to ThreadPoolExecutor
                self._step_summarize_threaded(regular_chunks, results, result)

        return [r for r in results if r is not None]

    def _step_summarize_threaded(
        self,
        indexed_chunks: list[tuple[int, ParsedChunk]],
        results: list,
        result: IngestionResult,
    ) -> None:
        """Fallback: summarization via ThreadPoolExecutor (if asyncio fails)."""
        from concurrent.futures import ThreadPoolExecutor

        def process_chunk(index: int, chunk: ParsedChunk):
            try:
                s = self._summarizer.summarize_l0(chunk)
                return index, s, None
            except Exception as e:
                return index, None, f"Summarize L0 failed for {chunk.source_file}: {e}"

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(process_chunk, idx, chunk) for idx, chunk in indexed_chunks]
            for future in futures:
                idx, summary, error_msg = future.result()
                if error_msg:
                    logger.error(error_msg)
                    result.errors.append(error_msg)
                if summary:
                    results[idx] = summary


    def _step_store_sqlite(
        self,
        chunks: list[ParsedChunk],
        project_uuid: str,
        auto_tag: bool,
        result: IngestionResult,
    ) -> int:
        """Step 4: Persistence in SQLite (nodes + edges) via Bulk Insert (WAL-friendly).

        Separates already cached nodes (keeping their IDs) from new nodes, inserting
        only the new ones in SQLite, while mapping and creating structural and call edges
        for ALL chunks (new and cached).
        """
        if not chunks:
            return 0

        # Coleta nós existentes no projeto para cachear diretórios e mapear símbolos globais
        try:
            existing_nodes = self._store.get_nodes_by_project(project_uuid)
        except Exception as e:
            logger.warning("Error fetching existing nodes for cache: %s", e)
            existing_nodes = []

        dir_node_cache = {n["label"]: n["id"] for n in existing_nodes if n.get("type") == "directory"}
        
        # 1. PREPARE NODES FOR BULK CREATION
        nodes_to_create = []
        new_dirs = set()

        for chunk in chunks:
            parent_dir = chunk.source_file.replace("\\", "/")
            if "/" in parent_dir:
                parent_dir = parent_dir.rsplit("/", 1)[0]
            else:
                parent_dir = "<root>"
                
            if parent_dir not in dir_node_cache:
                new_dirs.add(parent_dir)

        # Adds new directories first
        for d in sorted(new_dirs):
            nodes_to_create.append({
                "project_uuid": project_uuid,
                "label": d,
                "summary": None,
                "content": None,
                "node_type": "FACT",
                "type": "directory",
                "tags": None,
                "file_hash": None,
                "status": "ACTIVE"
            })

        # Adds only new (not cached) code/doc chunks
        new_chunks = [c for c in chunks if not c.cached]
        dir_offset = len(nodes_to_create)
        from ingestion.parser import ChunkType
        
        for chunk in new_chunks:
            summary_text = chunk.cached_summary
            
            ntype = "FACT"
            if chunk.chunk_type in (ChunkType.CLASS, ChunkType.FUNCTION, ChunkType.METHOD, ChunkType.MODULE):
                ntype = chunk.chunk_type.value.upper()
            
            tags = chunk.detected_tags if auto_tag else None
            nodes_to_create.append({
                "project_uuid": project_uuid,
                "label": f"{chunk.source_file}::{chunk.symbol_name}",
                "summary": summary_text,
                "content": chunk.content,
                "node_type": ntype,
                "type": chunk.chunk_type.value,
                "tags": tags,
                "file_hash": chunk.file_hash,
                "status": "ACTIVE"
            })

        # Executes bulk insert of nodes (new directories + new chunks)
        node_ids = []
        if nodes_to_create:
            try:
                node_ids = self._store.create_nodes_and_edges_bulk(nodes_to_create, [])
            except Exception as e:
                error_msg = f"Bulk insert of nodes failed: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                raise RuntimeError(error_msg) from e

        # Updates directory caches with the new generated IDs
        for idx, d in enumerate(sorted(new_dirs)):
            if idx < len(node_ids):
                dir_node_cache[d] = node_ids[idx]

        # Associates new IDs to the created chunks
        chunk_node_ids = node_ids[dir_offset:]
        for i, chunk in enumerate(new_chunks):
            if i < len(chunk_node_ids):
                chunk.node_id = chunk_node_ids[i]

        # 2. RESOLVE SYMBOL MAPS FOR EDGE MAPPING (new + cached)
        project_symbol_map = {}
        global_symbol_map = {}

        # Maps pre-existing nodes in the database
        for n in existing_nodes:
            label = n["label"]
            nid = n["id"]
            sf = label
            sym = ""
            if "::" in label:
                sf, sym = label.split("::", 1)
            project_symbol_map[(sf, sym)] = nid
            if sym:
                if sym not in global_symbol_map:
                    global_symbol_map[sym] = []
                global_symbol_map[sym].append(nid)

        # Maps all chunks (new and cached) of the current batch
        for chunk in chunks:
            nid = chunk.node_id
            if nid is None:
                continue
            sf = chunk.source_file
            sym = chunk.symbol_name
            project_symbol_map[(sf, sym)] = nid
            if sym:
                if sym not in global_symbol_map:
                    global_symbol_map[sym] = []
                global_symbol_map[sym].append(nid)

        # 3. PREPARE EDGES FOR BULK CREATION (new + cached)
        edges_to_create = []
        file_module_map = {}

        # Maps modules (files) of the current batch
        for chunk in chunks:
            if chunk.chunk_type.value == "module" and chunk.node_id is not None:
                file_module_map[chunk.source_file] = chunk.node_id

        for chunk in chunks:
            chunk_node_id = chunk.node_id
            if chunk_node_id is None:
                continue

            # Structural edges: directory -> file, file -> symbol
            parent_dir = chunk.source_file.replace("\\", "/")
            if "/" in parent_dir:
                parent_dir = parent_dir.rsplit("/", 1)[0]
            else:
                parent_dir = "<root>"
                
            dir_id = dir_node_cache.get(parent_dir, -1)

            if chunk.chunk_type.value == "module":
                if dir_id > 0:
                    edges_to_create.append({
                        "source_id": dir_id,
                        "target_id": chunk_node_id,
                        "relation_type": "contains",
                        "weight": 1.0
                    })
            else:
                module_id = file_module_map.get(chunk.source_file)
                if module_id:
                    edges_to_create.append({
                        "source_id": module_id,
                        "target_id": chunk_node_id,
                        "relation_type": "contains",
                        "weight": 1.0
                    })
                elif dir_id > 0:
                    edges_to_create.append({
                        "source_id": dir_id,
                        "target_id": chunk_node_id,
                        "relation_type": "contains",
                        "weight": 1.0
                    })

            # Call edges (calls)
            calls = getattr(chunk, "calls", [])
            for call_name in calls:
                target_node_id = None
                
                # Check 1: Symbol lookup in the same file
                if (chunk.source_file, call_name) in project_symbol_map:
                    target_node_id = project_symbol_map[(chunk.source_file, call_name)]
                
                # Check 2: Dotted path (ex: Class.method)
                if not target_node_id and "." in call_name:
                    parts = call_name.split(".")
                    if (chunk.source_file, call_name) in project_symbol_map:
                        target_node_id = project_symbol_map[(chunk.source_file, call_name)]
                    else:
                        last_part = parts[-1]
                        if (chunk.source_file, last_part) in project_symbol_map:
                            target_node_id = project_symbol_map[(chunk.source_file, last_part)]
                            
                # Check 3: Global symbol lookup in the project
                if not target_node_id and call_name in global_symbol_map:
                    target_node_id = global_symbol_map[call_name][0]

                if target_node_id and target_node_id != chunk_node_id:
                    edges_to_create.append({
                        "source_id": chunk_node_id,
                        "target_id": target_node_id,
                        "relation_type": "calls",
                        "weight": 1.0
                    })

        # Executes bulk insert of edges
        if edges_to_create:
            try:
                self._store.create_nodes_and_edges_bulk([], edges_to_create)
            except Exception as e:
                logger.warning("Failed to persist edges in bulk (non-fatal): %s", e)

        return len(new_chunks)

    def _step_embed(self, chunks: list[ParsedChunk], project_uuid: str, result: IngestionResult) -> list[dict]:
        """Step 5: Batch embedding generation (only for new chunks)."""
        new_chunks = [c for c in chunks if not c.cached]
        if not new_chunks:
            return []

        # Collects texts for batch embedding
        texts = [c.content for c in new_chunks]

        try:
            embeddings = self._embedder.embed_batch(texts)
        except Exception as e:
            error_msg = f"Embed batch failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            embeddings = [None] * len(new_chunks)

        # Assemble items for vector store
        items: list[dict] = []
        for chunk, embedding in zip(new_chunks, embeddings):
            node_id = chunk.node_id
            if node_id is None:
                continue

            items.append({
                "doc_id": f"node_{node_id}",
                "embedding": embedding,  # can be None (Semantic Fallback)
                "metadata": {
                    "node_id": node_id,
                    "project_uuid": project_uuid,
                    "source_file": chunk.source_file,
                    "chunk_type": chunk.chunk_type.value,
                    "symbol_name": chunk.symbol_name,
                },
            })

        return items

    def _step_store_vector(self, embed_items: list[dict], result: IngestionResult) -> int:
        """Step 6: Persistence in the vector backend (batch)."""
        try:
            stored = self._vector.store_embeddings_batch(embed_items)
            return stored
        except Exception as e:
            error_msg = f"Store Vector batch failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return 0

    def _step_garbage_collection(
        self,
        deleted_node_ids: list[int],
        project_uuid: str,
        result: IngestionResult,
    ) -> int:
        """Step 7: Garbage Collection — removes orphaned nodes and vectors."""
        removed = 0

        for node_id in deleted_node_ids:
            try:
                # Remove from SQLite
                self._store.delete_node(node_id)

                # Remove from vector backend
                doc_id = f"node_{node_id}"
                try:
                    self._vector.delete(doc_id)
                except Exception as ve:
                    logger.debug("GC: vector %s not found (ok): %s", doc_id, ve)

                removed += 1
            except Exception as e:
                error_msg = f"GC failed for node_id={node_id}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Reconciliation Loop: verifies SQLite ↔ Vector synchronization
        try:
            existing_nodes = self._store.get_nodes_by_project(project_uuid)
            sqlite_ids = [f"node_{n['id']}" for n in existing_nodes if n.get("type") not in ("directory", "cluster", "project")]
            sync_report = self._vector.verify_sync(sqlite_ids)
            orphan_count = sync_report.get("orphans_removed", 0)
            if orphan_count > 0:
                logger.warning("Reconciliation: %d orphan vectors removed post-GC.", orphan_count)
        except Exception as e:
            logger.debug("Reconciliation loop failed (non-fatal): %s", e)

        return removed

    # ===================================================================
    # ZOOM GEAR (L1/L2)
    # ===================================================================

    def generate_project_context(self, project_uuid: str) -> dict:
        """Generates L1 and L2 summaries for the project (complete Zoom Gear).

        Can be called after mine() or by the Background Janitor.

        Returns:
            Dict with l1_count, l2_summary, and l2_tags.
        """
        if not self._summarizer:
            logger.warning("generate_project_context: summarizer not configured.")
            return {"l1_count": 0, "l2_summary": None, "l2_tags": []}

        logger.info("ZOOM GEAR started for project %s...", project_uuid)

        # Fetch nodes with populated summary (L0s already generated)
        all_nodes = self._store.get_nodes_by_project(project_uuid)
        l0_summaries: list[SummaryResult] = []

        for node in all_nodes:
            if node.get("type") in ("directory", "cluster", "project") or not node.get("summary"):
                continue

            tags = node.get("tags", [])
            if isinstance(tags, str):
                import json
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = []

            l0_summaries.append(SummaryResult(
                level=ZoomLevel.L0,
                summary=node["summary"],
                source_label=node.get("label", "unknown"),
                source_chunks=1,
                detected_tags=tags if isinstance(tags, list) else [],
            ))

        if not l0_summaries:
            logger.warning("ZOOM GEAR: nenhum resumo L0 encontrado para %s.", project_uuid)
            return {"l1_count": 0, "l2_summary": None, "l2_tags": []}

        # Group into clusters and generate L1
        clusters = self._summarizer.build_l1_clusters(l0_summaries)
        l1_summaries: list[SummaryResult] = []

        for cluster_label, cluster_l0s in clusters.items():
            try:
                l1 = self._summarizer.summarize_l1(cluster_l0s, cluster_label)
                l1_summaries.append(l1)
                logger.debug("L1 gerado: %s (%d L0s)", cluster_label, len(cluster_l0s))
            except Exception as e:
                logger.error("L1 falhou para cluster %s: %s", cluster_label, e)

        # Generate L2 (Compass)
        project = self._store.get_project(project_uuid)
        project_name = project.get("folder_name", project_uuid)

        try:
            l2 = self._summarizer.summarize_l2(l1_summaries, project_name)
            logger.info("Bússola L2 gerada: %s", l2.summary[:80])
        except Exception as e:
            logger.error("L2 (Bússola) falhou para %s: %s", project_name, e)
            l2 = SummaryResult(level=ZoomLevel.L2, summary="", source_label=project_name)

        result = {
            "l1_count": len(l1_summaries),
            "l2_summary": l2.summary,
            "l2_tags": l2.detected_tags,
        }

        logger.info(
            "ZOOM GEAR concluído: %d L1 gerados, Bússola L2 = %.60s...",
            len(l1_summaries), l2.summary,
        )

        return result

    # ===================================================================
    # UTILITIES
    # ===================================================================

    def _consolidate_tags(self, chunks: list[ParsedChunk]) -> list[str]:
        """Consolidates unique tags from all chunks."""
        tags: set[str] = set()
        for c in chunks:
            tags.update(c.detected_tags)
        return sorted(tags)

    def _consolidate_categories(self, chunks: list[ParsedChunk]) -> dict[str, int]:
        """Counts chunks by category."""
        cats: dict[str, int] = {"code": 0, "doc": 0, "config": 0, "conversation": 0}
        for c in chunks:
            key = c.category.value
            if key in cats:
                cats[key] += 1
        return cats
