"""
ingestion/summarizer.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Zoom Gear — Generation of recursive L0/L1/L2 summaries.

Responsibilities:
    - L0 (File): Generates individual summary of each file/chunk ingested.
    - L1 (Cluster): Aggregates L0 summaries into directory/topic/module summaries.
    - L2 (Compass): Generates global project summary (Context Compass).
    - Relevance Pruning (Selective Amnesia): In L2, discards nodes with
      relevance score below the threshold for giant projects.
    - Model Tiering: Uses Flash models (cheap) for L0/L1, preserving
      Elite models for execution tasks.

Heuristic Fallback & Retry Loop:
    Flash models have a higher failure rate in JSON extraction.
    The Summarizer implements:
        1. Normal attempt at JSON parsing.
        2. Regex fallback: raw extraction via \\{.*\\}.
        3. Up to 3 attempts.
        4. If all fail: "Dumb Summary" (truncated plain text).

Integration:
    - Receives ParsedChunk from parser.py.
    - Writes summaries to SqliteStore (nodes table, summary field).
    - L2 summaries feed concierge_resume / wake_up.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from storage import SqliteStore
from ingestion.parser import ParsedChunk

logger = logging.getLogger("grafo-concierge.summarizer")


# ---------------------------------------------------------------------------
# Zoom Gear Settings
# ---------------------------------------------------------------------------

MAX_RETRY_LOOPS: int = 3
MAX_L0_TOKENS: int = 1000
MAX_L1_TOKENS: int = 1500
MAX_L2_TOKENS: int = 1500
L2_RELEVANCE_THRESHOLD: float = 0.15

# Tags indicating high priority (relevance score boost)
HIGH_PRIORITY_TAGS: set[str] = {
    "fastapi", "flask", "django", "express", "react", "nextjs",
    "vue", "angular", "pytorch", "tensorflow", "graphql", "grpc",
    "auth", "jwt", "oauth", "database", "sqlalchemy", "prisma",
    "api", "security", "kubernetes", "docker",
}

# Regex to extract embedded JSON from LLM response
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


# ---------------------------------------------------------------------------
# ZoomLevel
# ---------------------------------------------------------------------------

class ZoomLevel(str, Enum):
    """Hierarchical summary levels."""
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


# ---------------------------------------------------------------------------
# SummaryResult
# ---------------------------------------------------------------------------

@dataclass
class SummaryResult:
    """Result of a summarization operation."""
    level: ZoomLevel
    summary: str
    source_label: str
    source_chunks: int = 0
    tokens_used: int = 0
    model_used: str = ""
    is_dumb_summary: bool = False
    detected_tags: list[str] = field(default_factory=list)
    relevance_score: float = 1.0


# ---------------------------------------------------------------------------
# PROMPTS — Templates for each summary level
# ---------------------------------------------------------------------------

_L0_PROMPT_TEMPLATE = """You are a code analysis assistant. Summarize the following code/document chunk.
Return ONLY a valid JSON object with these fields:
- "summary": A concise description of what this code does (max 2 sentences).
- "tags": A list of detected technologies, frameworks, or key concepts.

Source file: {source_file}
Chunk type: {chunk_type}
Symbol: {symbol_name}

Content:
{armored_content}

Respond with ONLY the JSON object, no markdown fences, no extra text."""

_L1_PROMPT_TEMPLATE = """You are a software architect. Synthesize the following file summaries into a single module/directory description.
Return ONLY a valid JSON object with these fields:
- "summary": A cohesive description of this module's purpose and responsibilities (max 3 sentences).
- "tags": Consolidated list of key technologies and concepts.

Module: {cluster_label}
File summaries:
{summaries_block}

Respond with ONLY the JSON object, no markdown fences, no extra text."""

_L2_PROMPT_TEMPLATE = """You are a senior software architect. Create a high-level project overview (Compass) from the module summaries below.
Return ONLY a valid JSON object with these fields:
- "summary": A comprehensive project overview covering architecture, purpose, and key technologies (max 4 sentences).
- "tags": The most important technologies and architectural patterns.

Project: {project_name}
Module summaries:
{summaries_block}

Respond with ONLY the JSON object, no markdown fences, no extra text."""


# ---------------------------------------------------------------------------
# LLMAdapter — interface for LLM calls (Model Tiering)
# ---------------------------------------------------------------------------

class LLMAdapter:
    """Adapter for LLM calls with support for Model Tiering.

    Allows changing the model without altering the Summarizer logic.
    Accepts a custom call_fn for testing and alternative providers.

    Args:
        model_name: Model name (e.g. 'gemini-2.0-flash', 'claude-haiku').
        api_key: Provider API key.
        call_fn: Custom call function.
                 Signature: (prompt: str, max_tokens: int) -> str
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        call_fn: Optional[Callable[[str, int], str]] = None,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url
        self._call_fn = call_fn
        logger.info("LLMAdapter inicializado: model=%s, custom_fn=%s", model_name, call_fn is not None)

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        """Sends prompt to LLM and returns the response.

        If call_fn was provided, uses it directly.
        Otherwise, attempts to use google.generativeai (Gemini).

        Raises:
            RuntimeError: If no LLM backend is available.
        """
        # Custom mode (for testing or alternative providers)
        if self._call_fn is not None:
            return self._call_fn(prompt, max_tokens)

        # Attempt with Google Generative AI (Gemini)
        try:
            import google.generativeai as genai
            if self._api_key:
                genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
            )
            return response.text
        except ImportError:
            pass
        except Exception as e:
            logger.error("Failed to call Gemini (%s): %s", self._model_name, e)
            raise RuntimeError(f"LLM call failed: {e}") from e

        # Attempt with OpenAI / Compatible Provider
        try:
            import openai
            
            # Auto-detection of OpenRouter by key if no base_url is informed
            target_base_url = self._base_url
            if not target_base_url and self._api_key and self._api_key.startswith("sk-or-"):
                target_base_url = "https://openrouter.ai/api/v1"
                
            if target_base_url:
                client = openai.OpenAI(
                    api_key=self._api_key,
                    base_url=target_base_url
                )
            else:
                client = openai.OpenAI(api_key=self._api_key)
                
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except ImportError:
            pass
        except Exception as e:
            logger.error("Failed to call OpenAI/Compatible Provider (%s): %s", self._model_name, e)
            raise RuntimeError(f"LLM call failed: {e}") from e

        raise RuntimeError(
            "No LLM backend available. Install 'google-generativeai' or 'openai', "
            "or provide a custom call_fn."
        )

    async def generate_async(self, prompt: str, max_tokens: int = 300) -> str:
        """Asynchronous version of generate() for high throughput.

        Strategy by backend:
            - custom call_fn: uses asyncio.to_thread (safe fallback).
            - Native Gemini models (no custom base_url): prioritizes native Gemini SDK.
            - OpenAI / compatible providers: uses native openai.AsyncOpenAI.
        """
        import asyncio

        # Custom mode
        if self._call_fn is not None:
            return await asyncio.to_thread(self._call_fn, prompt, max_tokens)

        # If it is a native Gemini model and does not have an external custom base_url,
        # prioritize native Gemini SDK to avoid conflict with the openai library
        if self._model_name.startswith("gemini-") and not self._base_url:
            try:
                return await asyncio.to_thread(self.generate, prompt, max_tokens)
            except Exception as e:
                logger.warning("Failed initial asynchronous attempt with Gemini SDK: %s. Trying OpenAI...", e)

        # Attempt with OpenAI / Compatible Provider (native async)
        try:
            import openai

            target_base_url = self._base_url
            if not target_base_url and self._api_key and self._api_key.startswith("sk-or-"):
                target_base_url = "https://openrouter.ai/api/v1"

            if target_base_url:
                client = openai.AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=target_base_url,
                )
            else:
                client = openai.AsyncOpenAI(api_key=self._api_key)

            response = await client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except ImportError:
            pass
        except Exception as e:
            logger.error("Async: Failed to call OpenAI/Provider (%s): %s", self._model_name, e)
            raise RuntimeError(f"Async LLM call failed: {e}") from e

        # General fallback
        try:
            return await asyncio.to_thread(self.generate, prompt, max_tokens)
        except Exception as e:
            raise RuntimeError(f"Async LLM fallback failed: {e}") from e



# ---------------------------------------------------------------------------
# ZoomSummarizer — Zoom Gear Engine
# ---------------------------------------------------------------------------

class ZoomSummarizer:
    """Zoom Gear Engine — generates recursive summaries L0 → L1 → L2.

    Heuristic Fallback:
        If LLM returns invalid JSON, attempts regex + up to 3 retries.
        If all fails, generates Dumb Summary (truncated plain text).

    Relevance Pruning (Selective Amnesia):
        In L2, nodes with relevance_score < L2_RELEVANCE_THRESHOLD are
        discarded from synthesis to keep the Compass concise.
    """

    def __init__(
        self,
        llm_adapter: LLMAdapter,
        sqlite_store: Optional[SqliteStore] = None,
    ) -> None:
        self._llm = llm_adapter
        self._store = sqlite_store

    # ===================================================================
    # L0 — Summary of individual chunk
    # ===================================================================

    def summarize_l0(self, chunk: ParsedChunk) -> SummaryResult:
        """Generates L0 summary for an individual chunk/file."""
        prompt = _L0_PROMPT_TEMPLATE.format(
            source_file=chunk.source_file,
            chunk_type=chunk.chunk_type.value,
            symbol_name=chunk.symbol_name,
            armored_content=chunk.armored_content,
        )

        # Retry loop with Heuristic Fallback
        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = self._llm.generate(prompt, max_tokens=MAX_L0_TOKENS)
                parsed = self._extract_json_with_fallback(raw_response)

                if parsed and "summary" in parsed:
                    summary_text = parsed["summary"]
                    tags = parsed.get("tags", [])
                    if isinstance(tags, list):
                        tags = [str(t).lower() for t in tags]
                    else:
                        tags = []

                    return SummaryResult(
                        level=ZoomLevel.L0,
                        summary=summary_text,
                        source_label=chunk.source_file,
                        source_chunks=1,
                        tokens_used=self._estimate_tokens(summary_text),
                        model_used=self._llm.model_name,
                        is_dumb_summary=False,
                        detected_tags=sorted(set(chunk.detected_tags + tags)),
                        relevance_score=1.0,
                    )

                logger.warning(
                    "L0 attempt %d/%d: invalid JSON for %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file,
                )

            except Exception as e:
                logger.warning(
                    "L0 attempt %d/%d failed for %s: %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file, e,
                )

        # Dumb Summary — last resort
        logger.error("L0: all attempts failed for %s — generating Dumb Summary.", chunk.source_file)
        dumb = self._generate_dumb_summary(chunk.content, MAX_L0_TOKENS)
        return SummaryResult(
            level=ZoomLevel.L0,
            summary=dumb,
            source_label=chunk.source_file,
            source_chunks=1,
            tokens_used=self._estimate_tokens(dumb),
            model_used="dumb_fallback",
            is_dumb_summary=True,
            detected_tags=chunk.detected_tags,
            relevance_score=0.5,
        )

    def summarize_l0_batch(self, chunks: list[ParsedChunk]) -> list[SummaryResult]:
        """Generates L0 summaries for multiple chunks with Semantic Fallback."""
        results: list[SummaryResult] = []
        for i, chunk in enumerate(chunks):
            try:
                result = self.summarize_l0(chunk)
                results.append(result)
                logger.debug("L0 [%d/%d] OK: %s", i + 1, len(chunks), chunk.source_file)
            except Exception as e:
                logger.error("L0 batch fallback — skip chunk %s: %s", chunk.source_file, e)
                # Generates Dumb Summary to not lose the chunk
                dumb = self._generate_dumb_summary(chunk.content, MAX_L0_TOKENS)
                results.append(SummaryResult(
                    level=ZoomLevel.L0,
                    summary=dumb,
                    source_label=chunk.source_file,
                    source_chunks=1,
                    tokens_used=self._estimate_tokens(dumb),
                    model_used="dumb_fallback",
                    is_dumb_summary=True,
                    detected_tags=chunk.detected_tags,
                    relevance_score=0.5,
                ))
        return results

    async def summarize_l0_async(self, chunk: ParsedChunk) -> SummaryResult:
        """Asynchronous version of summarize_l0 for use with asyncio.gather."""
        prompt = _L0_PROMPT_TEMPLATE.format(
            source_file=chunk.source_file,
            chunk_type=chunk.chunk_type.value,
            symbol_name=chunk.symbol_name,
            armored_content=chunk.armored_content,
        )

        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = await self._llm.generate_async(prompt, max_tokens=MAX_L0_TOKENS)
                parsed = self._extract_json_with_fallback(raw_response)

                if parsed and "summary" in parsed:
                    summary_text = parsed["summary"]
                    tags = parsed.get("tags", [])
                    if isinstance(tags, list):
                        tags = [str(t).lower() for t in tags]
                    else:
                        tags = []

                    return SummaryResult(
                        level=ZoomLevel.L0,
                        summary=summary_text,
                        source_label=chunk.source_file,
                        source_chunks=1,
                        tokens_used=self._estimate_tokens(summary_text),
                        model_used=self._llm.model_name,
                        is_dumb_summary=False,
                        detected_tags=sorted(set(chunk.detected_tags + tags)),
                        relevance_score=1.0,
                    )

                logger.warning(
                    "L0 async attempt %d/%d: invalid JSON for %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file,
                )

            except Exception as e:
                logger.warning(
                    "L0 async attempt %d/%d failed for %s: %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file, e,
                )

        # Dumb Summary — last resort
        logger.error("L0 async: all attempts failed for %s — generating Dumb Summary.", chunk.source_file)
        dumb = self._generate_dumb_summary(chunk.content, MAX_L0_TOKENS)
        return SummaryResult(
            level=ZoomLevel.L0,
            summary=dumb,
            source_label=chunk.source_file,
            source_chunks=1,
            tokens_used=self._estimate_tokens(dumb),
            model_used="dumb_fallback",
            is_dumb_summary=True,
            detected_tags=chunk.detected_tags,
            relevance_score=0.5,
        )

    # ===================================================================
    # L0 Grouped — Grouping of small chunks in a single prompt
    # ===================================================================

    _L0_GROUPED_PROMPT = """You are a code analysis assistant. Summarize each of the following code chunks individually.
Return ONLY a valid JSON array of objects. Each object must have:
- "index": The chunk index number (integer, starting from the values given).
- "summary": A concise description of what this code does (max 2 sentences).
- "tags": A list of detected technologies, frameworks, or key concepts.

Chunks:
{chunks_block}

Respond with ONLY the JSON array, no markdown fences, no extra text."""

    def summarize_l0_grouped(
        self,
        chunks: list[ParsedChunk],
        indices: list[int],
    ) -> list[tuple[int, SummaryResult]]:
        """Summarizes multiple small chunks in a single LLM call.

        Optimization for getter/setter functions and chunks < 50 tokens,
        reducing the total number of HTTP calls to the provider.

        Args:
            chunks: List of small ParsedChunks to group.
            indices: Original indices of each chunk in the global list.

        Returns:
            List of tuples (original_index, SummaryResult).
        """
        chunks_block = ""
        for idx, chunk in zip(indices, chunks):
            chunks_block += (
                f"\n--- Chunk index={idx} file={chunk.source_file} "
                f"type={chunk.chunk_type.value} symbol={chunk.symbol_name} ---\n"
                f"{chunk.armored_content}\n"
            )

        prompt = self._L0_GROUPED_PROMPT.format(chunks_block=chunks_block)

        # Estimates response tokens: ~200 tokens per chunk in the group
        estimated_response_tokens = min(len(chunks) * 200, 4000)

        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = self._llm.generate(prompt, max_tokens=estimated_response_tokens)

                # Tries to parse as JSON array
                parsed_array = None
                try:
                    parsed_array = json.loads(raw_response)
                except json.JSONDecodeError:
                    # Tries to extract array from within markdown fences
                    import re
                    array_match = re.search(r'\[.*\]', raw_response, re.DOTALL)
                    if array_match:
                        try:
                            parsed_array = json.loads(array_match.group())
                        except json.JSONDecodeError:
                            pass

                if isinstance(parsed_array, list) and len(parsed_array) > 0:
                    results: list[tuple[int, SummaryResult]] = []
                    for item in parsed_array:
                        if not isinstance(item, dict) or "summary" not in item:
                            continue
                        item_idx = item.get("index", -1)
                        if item_idx not in indices:
                            continue

                        chunk_pos = indices.index(item_idx)
                        chunk = chunks[chunk_pos]
                        tags = item.get("tags", [])
                        if isinstance(tags, list):
                            tags = [str(t).lower() for t in tags]
                        else:
                            tags = []

                        results.append((item_idx, SummaryResult(
                            level=ZoomLevel.L0,
                            summary=item["summary"],
                            source_label=chunk.source_file,
                            source_chunks=1,
                            tokens_used=self._estimate_tokens(item["summary"]),
                            model_used=self._llm.model_name,
                            is_dumb_summary=False,
                            detected_tags=sorted(set(chunk.detected_tags + tags)),
                            relevance_score=1.0,
                        )))

                    if results:
                        logger.info("L0 grouped: %d/%d summaries extracted successfully.", len(results), len(chunks))
                        return results

                logger.warning(
                    "L0 grouped attempt %d/%d: invalid response (%d chunks).",
                    attempt, MAX_RETRY_LOOPS, len(chunks),
                )

            except Exception as e:
                logger.warning(
                    "L0 grouped attempt %d/%d failed: %s",
                    attempt, MAX_RETRY_LOOPS, e,
                )

        # Fallback: returns empty list, caller will perform individual summaries
        logger.error("L0 grouped: all attempts failed for %d chunks.", len(chunks))
        return []

    # ===================================================================
    # L1 — Summary of cluster (folder/module)
    # ===================================================================

    def summarize_l1(
        self,
        l0_summaries: list[SummaryResult],
        cluster_label: str,
    ) -> SummaryResult:
        """Generates L1 summary from grouped L0 summaries."""
        # Assemble block of summaries for the prompt
        summaries_block = "\n".join(
            f"- [{s.source_label}]: {s.summary}" for s in l0_summaries
        )

        # Consolidate tags
        all_tags: set[str] = set()
        for s in l0_summaries:
            all_tags.update(s.detected_tags)

        prompt = _L1_PROMPT_TEMPLATE.format(
            cluster_label=cluster_label,
            summaries_block=summaries_block,
        )

        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = self._llm.generate(prompt, max_tokens=MAX_L1_TOKENS)
                parsed = self._extract_json_with_fallback(raw_response)

                if parsed and "summary" in parsed:
                    summary_text = parsed["summary"]
                    tags = parsed.get("tags", [])
                    if isinstance(tags, list):
                        all_tags.update(str(t).lower() for t in tags)

                    return SummaryResult(
                        level=ZoomLevel.L1,
                        summary=summary_text,
                        source_label=cluster_label,
                        source_chunks=len(l0_summaries),
                        tokens_used=self._estimate_tokens(summary_text),
                        model_used=self._llm.model_name,
                        is_dumb_summary=False,
                        detected_tags=sorted(all_tags),
                        relevance_score=self._calculate_relevance_from_parts(l0_summaries),
                    )

                logger.warning(
                    "L1 attempt %d/%d: invalid JSON for cluster %s",
                    attempt, MAX_RETRY_LOOPS, cluster_label,
                )

            except Exception as e:
                logger.warning(
                    "L1 attempt %d/%d failed for cluster %s: %s",
                    attempt, MAX_RETRY_LOOPS, cluster_label, e,
                )

        # Dumb Summary L1
        logger.error("L1: all attempts failed for %s — Dumb Summary.", cluster_label)
        dumb = self._generate_dumb_summary(summaries_block, MAX_L1_TOKENS)
        return SummaryResult(
            level=ZoomLevel.L1,
            summary=dumb,
            source_label=cluster_label,
            source_chunks=len(l0_summaries),
            tokens_used=self._estimate_tokens(dumb),
            model_used="dumb_fallback",
            is_dumb_summary=True,
            detected_tags=sorted(all_tags),
            relevance_score=self._calculate_relevance_from_parts(l0_summaries),
        )

    def build_l1_clusters(
        self,
        l0_summaries: list[SummaryResult],
    ) -> dict[str, list[SummaryResult]]:
        """Groups L0 summaries by parent directory (natural cluster)."""
        clusters: dict[str, list[SummaryResult]] = {}

        for s in l0_summaries:
            # Extract parent directory from source_label (relative_path)
            label = s.source_label.replace("\\", "/")
            if "/" in label:
                parent = label.rsplit("/", 1)[0]
            else:
                parent = "<root>"

            if parent not in clusters:
                clusters[parent] = []
            clusters[parent].append(s)

        logger.debug("L1 clusters built: %d clusters from %d L0s.", len(clusters), len(l0_summaries))
        return clusters

    # ===================================================================
    # L2 — Context Compass (global summary)
    # ===================================================================

    def summarize_l2(
        self,
        l1_summaries: list[SummaryResult],
        project_name: str,
    ) -> SummaryResult:
        """Generates Context Compass (L2) from L1 summaries.

        Applies Relevance Pruning (Selective Amnesia) before synthesis.
        """
        # Pruning — remove trivial modules
        pruned = self._prune_low_relevance(l1_summaries)
        pruned_count = len(l1_summaries) - len(pruned)
        if pruned_count > 0:
            logger.info(
                "Selective Amnesia: %d/%d modules pruned (threshold=%.2f).",
                pruned_count, len(l1_summaries), L2_RELEVANCE_THRESHOLD,
            )

        # Assemble block of summaries
        summaries_block = "\n".join(
            f"- [{s.source_label}] (relevance={s.relevance_score:.2f}): {s.summary}"
            for s in pruned
        )

        all_tags: set[str] = set()
        for s in pruned:
            all_tags.update(s.detected_tags)

        prompt = _L2_PROMPT_TEMPLATE.format(
            project_name=project_name,
            summaries_block=summaries_block,
        )

        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = self._llm.generate(prompt, max_tokens=MAX_L2_TOKENS)
                parsed = self._extract_json_with_fallback(raw_response)

                if parsed and "summary" in parsed:
                    summary_text = parsed["summary"]
                    tags = parsed.get("tags", [])
                    if isinstance(tags, list):
                        all_tags.update(str(t).lower() for t in tags)

                    result = SummaryResult(
                        level=ZoomLevel.L2,
                        summary=summary_text,
                        source_label=project_name,
                        source_chunks=len(pruned),
                        tokens_used=self._estimate_tokens(summary_text),
                        model_used=self._llm.model_name,
                        is_dumb_summary=False,
                        detected_tags=sorted(all_tags),
                        relevance_score=1.0,
                    )

                    # Persists Compass in SqliteStore (if available)
                    if self._store is not None:
                        self._persist_l2(project_name, result)

                    return result

                logger.warning(
                    "L2 attempt %d/%d: invalid JSON for project %s",
                    attempt, MAX_RETRY_LOOPS, project_name,
                )

            except Exception as e:
                logger.warning(
                    "L2 attempt %d/%d failed for project %s: %s",
                    attempt, MAX_RETRY_LOOPS, project_name, e,
                )

        # Dumb Summary L2
        logger.error("L2: all attempts failed for %s — Dumb Summary.", project_name)
        dumb = self._generate_dumb_summary(summaries_block, MAX_L2_TOKENS)
        result = SummaryResult(
            level=ZoomLevel.L2,
            summary=dumb,
            source_label=project_name,
            source_chunks=len(pruned),
            tokens_used=self._estimate_tokens(dumb),
            model_used="dumb_fallback",
            is_dumb_summary=True,
            detected_tags=sorted(all_tags),
            relevance_score=1.0,
        )
        if self._store is not None:
            self._persist_l2(project_name, result)
        return result

    def _persist_l2(self, project_name: str, result: SummaryResult) -> None:
        """Writes the L2 Compass in the summary field of the project in SqliteStore."""
        try:
            self._store.update_project(project_name, summary=result.summary)
            logger.info("L2 Compass persisted for project %s.", project_name)
        except Exception as e:
            logger.error("Failed to persist L2 Compass for %s: %s", project_name, e)

    # ===================================================================
    # HEURISTIC FALLBACK & RETRY LOOP
    # ===================================================================

    def _extract_json_with_fallback(self, raw_response: str) -> Optional[dict]:
        """Attempts to extract JSON from LLM response with progressive fallback."""
        if not raw_response or not raw_response.strip():
            return None

        text = raw_response.strip()

        # Removes markdown fences if present (```json ... ```)
        if text.startswith("```"):
            lines = text.splitlines()
            # Removes first and last line if they are fences
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Attempt 1: direct json.loads
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # Attempt 2: regex to extract embedded JSON
        matches = _JSON_BLOCK_RE.findall(text)
        for match in matches:
            try:
                return json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue

        # Attempt 3: simple search for outermost { ... }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

        logger.debug("JSON extraction failed for response: %.100s...", text)
        return None

    def _generate_dumb_summary(self, content: str, max_tokens: int) -> str:
        """Generates a Dumb Summary (truncated plain text) as a last resort."""
        max_chars = max_tokens * 4
        # Remove excess empty lines
        lines = [line for line in content.splitlines() if line.strip()]
        clean = "\n".join(lines)

        if len(clean) <= max_chars:
            return f"[DUMB] {clean}"

        truncated = clean[:max_chars].rsplit(" ", 1)[0]
        return f"[DUMB] {truncated}..."

    # ===================================================================
    # RELEVANCE PRUNING (Selective Amnesia)
    # ===================================================================

    def _calculate_relevance(self, summary: SummaryResult) -> float:
        """Calculates relevance score for L2 pruning.

        Factors (normalized weights to [0.0, 1.0]):
            - source_chunks: More chunks = larger module = more relevant (40%).
            - high_priority_tags: Core frameworks/APIs tags (40%).
            - is_dumb_summary: Penalizes dumb summaries (20%).
        """
        score = 0.0

        # Factor 1: Module size (normalized via log-ish mapping)
        chunk_score = min(1.0, summary.source_chunks / 10.0)
        score += chunk_score * 0.4

        # Factor 2: Presence of high priority tags
        if summary.detected_tags:
            high_count = sum(1 for t in summary.detected_tags if t in HIGH_PRIORITY_TAGS)
            tag_score = min(1.0, high_count / 3.0)
            score += tag_score * 0.4
        else:
            score += 0.0

        # Factor 3: Penalty for Dumb Summary
        if summary.is_dumb_summary:
            score += 0.0  # total penalty
        else:
            score += 0.2

        return round(min(1.0, max(0.0, score)), 3)

    def _calculate_relevance_from_parts(self, l0_summaries: list[SummaryResult]) -> float:
        """Calculates relevance of a cluster from its L0s."""
        if not l0_summaries:
            return 0.0

        # Creates a temporary SummaryResult for the calculation
        all_tags: set[str] = set()
        has_dumb = False
        for s in l0_summaries:
            all_tags.update(s.detected_tags)
            if s.is_dumb_summary:
                has_dumb = True

        temp = SummaryResult(
            level=ZoomLevel.L1,
            summary="",
            source_label="",
            source_chunks=len(l0_summaries),
            detected_tags=sorted(all_tags),
            is_dumb_summary=has_dumb,
        )
        return self._calculate_relevance(temp)

    def _prune_low_relevance(
        self,
        summaries: list[SummaryResult],
        threshold: float = L2_RELEVANCE_THRESHOLD,
    ) -> list[SummaryResult]:
        """Removes L1 summaries with relevance below the threshold."""
        result: list[SummaryResult] = []

        for s in summaries:
            # Calculates relevance if not yet calculated
            if s.relevance_score == 1.0:
                s.relevance_score = self._calculate_relevance(s)

            if s.relevance_score >= threshold:
                result.append(s)
            else:
                logger.debug(
                    "Selective Amnesia: pruned '%s' (score=%.3f < threshold=%.2f)",
                    s.source_label, s.relevance_score, threshold,
                )

        # Safety: never prunes all — keeps at least the top-1
        if not result and summaries:
            best = max(summaries, key=lambda s: s.relevance_score)
            result.append(best)
            logger.warning("Selective Amnesia: kept at least '%s' (score=%.3f).", best.source_label, best.relevance_score)

        return result

    # ===================================================================
    # UTILITIES
    # ===================================================================

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimates tokens: ~4 characters per token."""
        return max(1, len(text) // 4)
