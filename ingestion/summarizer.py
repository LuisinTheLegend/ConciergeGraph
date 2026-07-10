"""
ingestion/summarizer.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Engrenagem de Zoom (Zoom Gear) — Geração de resumos recursivos L0/L1/L2.

Responsabilidades:
    - L0 (Arquivo): Gera resumo individual de cada arquivo/chunk ingerido.
    - L1 (Cluster): Agrega resumos L0 em resumos de pastas/temas/módulos.
    - L2 (Bússola): Gera resumo global do projeto (Bússola de Contexto).
    - Poda por Relevância (Amnésia Seletiva): No L2, descarta nós com
      score de relevância abaixo do threshold para projetos gigantes.
    - Model Tiering: Usa modelos Flash (baratos) para L0/L1, preservando
      modelos Elite para tarefas de execução.

Heuristic Fallback & Retry Loop:
    Modelos Flash têm maior taxa de falha na extração JSON.
    O Summarizer implementa:
        1. Tentativa normal de parsing JSON.
        2. Regex fallback: extração bruta via \\{.*\\}.
        3. Até 3 tentativas.
        4. Se tudo falhar: "Dumb Summary" (texto plano truncado).

Integração:
    - Recebe ParsedChunk do parser.py.
    - Grava resumos no SqliteStore (tabela nodes, campo summary).
    - Resumos L2 alimentam o concierge_resume / wake_up.
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
# Configurações da Engrenagem de Zoom
# ---------------------------------------------------------------------------

MAX_RETRY_LOOPS: int = 3
MAX_L0_TOKENS: int = 1000
MAX_L1_TOKENS: int = 1500
MAX_L2_TOKENS: int = 1500
L2_RELEVANCE_THRESHOLD: float = 0.15

# Tags que indicam alta prioridade (boost no score de relevância)
HIGH_PRIORITY_TAGS: set[str] = {
    "fastapi", "flask", "django", "express", "react", "nextjs",
    "vue", "angular", "pytorch", "tensorflow", "graphql", "grpc",
    "auth", "jwt", "oauth", "database", "sqlalchemy", "prisma",
    "api", "security", "kubernetes", "docker",
}

# Regex para extração de JSON embutido em resposta do LLM
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


# ---------------------------------------------------------------------------
# ZoomLevel
# ---------------------------------------------------------------------------

class ZoomLevel(str, Enum):
    """Níveis hierárquicos de resumo."""
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


# ---------------------------------------------------------------------------
# SummaryResult
# ---------------------------------------------------------------------------

@dataclass
class SummaryResult:
    """Resultado de uma operação de sumarização."""
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
# PROMPTS — Templates para cada nível de resumo
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
# LLMAdapter — interface para chamadas ao LLM (Model Tiering)
# ---------------------------------------------------------------------------

class LLMAdapter:
    """Adaptador para chamadas ao LLM com suporte a Model Tiering.

    Permite trocar o modelo sem alterar a lógica do Summarizer.
    Aceita uma call_fn customizada para testes e provedores alternativos.

    Args:
        model_name: Nome do modelo (ex: 'gemini-2.0-flash', 'claude-haiku').
        api_key: Chave da API do provedor.
        call_fn: Função de chamada customizada.
                 Assinatura: (prompt: str, max_tokens: int) -> str
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
        """Envia prompt ao LLM e retorna a resposta.

        Se call_fn foi fornecida, usa-a diretamente.
        Caso contrário, tenta usar google.generativeai (Gemini).

        Raises:
            RuntimeError: Se nenhum backend LLM estiver disponível.
        """
        # Modo customizado (para testes ou provedores alternativos)
        if self._call_fn is not None:
            return self._call_fn(prompt, max_tokens)

        # Tentativa com Google Generative AI (Gemini)
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
            logger.error("Falha ao chamar Gemini (%s): %s", self._model_name, e)
            raise RuntimeError(f"LLM call failed: {e}") from e

        # Tentativa com OpenAI / Provedor Compatível
        try:
            import openai
            
            # Auto-detecção de OpenRouter por chave se nenhuma base_url for informada
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
            logger.error("Falha ao chamar OpenAI/Provedor Compatível (%s): %s", self._model_name, e)
            raise RuntimeError(f"LLM call failed: {e}") from e

        raise RuntimeError(
            "Nenhum backend LLM disponível. Instale 'google-generativeai' ou 'openai', "
            "ou forneça uma call_fn customizada."
        )

    async def generate_async(self, prompt: str, max_tokens: int = 300) -> str:
        """Versão assíncrona de generate() para alto throughput.

        Estratégia por backend:
            - call_fn customizada / Gemini SDK: usa asyncio.to_thread (fallback seguro).
            - OpenAI / provedores compatíveis: usa openai.AsyncOpenAI nativo.
        """
        import asyncio

        # Modo customizado ou Gemini SDK — delegar para thread
        if self._call_fn is not None:
            return await asyncio.to_thread(self._call_fn, prompt, max_tokens)

        # Tentativa com OpenAI / Provedor Compatível (nativo async)
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
            logger.error("Async: Falha ao chamar OpenAI/Provedor (%s): %s", self._model_name, e)
            raise RuntimeError(f"Async LLM call failed: {e}") from e

        # Fallback: Gemini SDK via to_thread
        try:
            return await asyncio.to_thread(self.generate, prompt, max_tokens)
        except Exception as e:
            raise RuntimeError(f"Async LLM fallback failed: {e}") from e



# ---------------------------------------------------------------------------
# ZoomSummarizer — Motor da Engrenagem de Zoom
# ---------------------------------------------------------------------------

class ZoomSummarizer:
    """Motor da Engrenagem de Zoom — gera resumos recursivos L0 → L1 → L2.

    Heuristic Fallback:
        Se o LLM retornar JSON inválido, tenta regex + até 3 retries.
        Se tudo falhar, gera Dumb Summary (texto plano truncado).

    Poda por Relevância (Amnésia Seletiva):
        No L2, nós com relevance_score < L2_RELEVANCE_THRESHOLD são
        descartados da síntese para manter a Bússola concisa.
    """

    def __init__(
        self,
        llm_adapter: LLMAdapter,
        sqlite_store: Optional[SqliteStore] = None,
    ) -> None:
        self._llm = llm_adapter
        self._store = sqlite_store

    # ===================================================================
    # L0 — Resumo de chunk individual
    # ===================================================================

    def summarize_l0(self, chunk: ParsedChunk) -> SummaryResult:
        """Gera resumo L0 para um chunk/arquivo individual."""
        prompt = _L0_PROMPT_TEMPLATE.format(
            source_file=chunk.source_file,
            chunk_type=chunk.chunk_type.value,
            symbol_name=chunk.symbol_name,
            armored_content=chunk.armored_content,
        )

        # Retry loop com Heuristic Fallback
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
                    "L0 attempt %d/%d: JSON inválido para %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file,
                )

            except Exception as e:
                logger.warning(
                    "L0 attempt %d/%d falhou para %s: %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file, e,
                )

        # Dumb Summary — último recurso
        logger.error("L0: todas as tentativas falharam para %s — gerando Dumb Summary.", chunk.source_file)
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
        """Gera resumos L0 para múltiplos chunks com Semantic Fallback."""
        results: list[SummaryResult] = []
        for i, chunk in enumerate(chunks):
            try:
                result = self.summarize_l0(chunk)
                results.append(result)
                logger.debug("L0 [%d/%d] OK: %s", i + 1, len(chunks), chunk.source_file)
            except Exception as e:
                logger.error("L0 batch fallback — skip chunk %s: %s", chunk.source_file, e)
                # Gera Dumb Summary para não perder o chunk
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
        """Versão assíncrona de summarize_l0 para uso com asyncio.gather."""
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
                    "L0 async attempt %d/%d: JSON inválido para %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file,
                )

            except Exception as e:
                logger.warning(
                    "L0 async attempt %d/%d falhou para %s: %s",
                    attempt, MAX_RETRY_LOOPS, chunk.source_file, e,
                )

        # Dumb Summary — último recurso
        logger.error("L0 async: todas as tentativas falharam para %s — gerando Dumb Summary.", chunk.source_file)
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
    # L0 Grouped — Agrupamento de chunks pequenos em um único prompt
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
        """Sumariza múltiplos chunks pequenos em uma única chamada ao LLM.

        Otimização para funções getters/setters e chunks < 50 tokens,
        reduzindo o número total de chamadas HTTP ao provedor.

        Args:
            chunks: Lista de ParsedChunks pequenos a agrupar.
            indices: Índices originais de cada chunk na lista global.

        Returns:
            Lista de tuplas (índice_original, SummaryResult).
        """
        chunks_block = ""
        for idx, chunk in zip(indices, chunks):
            chunks_block += (
                f"\n--- Chunk index={idx} file={chunk.source_file} "
                f"type={chunk.chunk_type.value} symbol={chunk.symbol_name} ---\n"
                f"{chunk.armored_content}\n"
            )

        prompt = self._L0_GROUPED_PROMPT.format(chunks_block=chunks_block)

        # Estima tokens de resposta: ~200 tokens por chunk no grupo
        estimated_response_tokens = min(len(chunks) * 200, 4000)

        for attempt in range(1, MAX_RETRY_LOOPS + 1):
            try:
                raw_response = self._llm.generate(prompt, max_tokens=estimated_response_tokens)

                # Tenta parsear como array JSON
                parsed_array = None
                try:
                    parsed_array = json.loads(raw_response)
                except json.JSONDecodeError:
                    # Tenta extrair array de dentro de markdown fences
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
                        logger.info("L0 grouped: %d/%d resumos extraídos com sucesso.", len(results), len(chunks))
                        return results

                logger.warning(
                    "L0 grouped attempt %d/%d: resposta inválida (%d chunks).",
                    attempt, MAX_RETRY_LOOPS, len(chunks),
                )

            except Exception as e:
                logger.warning(
                    "L0 grouped attempt %d/%d falhou: %s",
                    attempt, MAX_RETRY_LOOPS, e,
                )

        # Fallback: retorna lista vazia, caller fará resumos individuais
        logger.error("L0 grouped: todas as tentativas falharam para %d chunks.", len(chunks))
        return []

    # ===================================================================
    # L1 — Resumo de cluster (pasta/módulo)
    # ===================================================================

    def summarize_l1(
        self,
        l0_summaries: list[SummaryResult],
        cluster_label: str,
    ) -> SummaryResult:
        """Gera resumo L1 a partir de resumos L0 agrupados."""
        # Monta bloco de resumos para o prompt
        summaries_block = "\n".join(
            f"- [{s.source_label}]: {s.summary}" for s in l0_summaries
        )

        # Consolida tags
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
                    "L1 attempt %d/%d: JSON inválido para cluster %s",
                    attempt, MAX_RETRY_LOOPS, cluster_label,
                )

            except Exception as e:
                logger.warning(
                    "L1 attempt %d/%d falhou para cluster %s: %s",
                    attempt, MAX_RETRY_LOOPS, cluster_label, e,
                )

        # Dumb Summary L1
        logger.error("L1: todas as tentativas falharam para %s — Dumb Summary.", cluster_label)
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
        """Agrupa resumos L0 por diretório pai (cluster natural)."""
        clusters: dict[str, list[SummaryResult]] = {}

        for s in l0_summaries:
            # Extrai diretório pai do source_label (relative_path)
            label = s.source_label.replace("\\", "/")
            if "/" in label:
                parent = label.rsplit("/", 1)[0]
            else:
                parent = "<root>"

            if parent not in clusters:
                clusters[parent] = []
            clusters[parent].append(s)

        logger.debug("L1 clusters construídos: %d clusters a partir de %d L0s.", len(clusters), len(l0_summaries))
        return clusters

    # ===================================================================
    # L2 — Bússola de Contexto (resumo global)
    # ===================================================================

    def summarize_l2(
        self,
        l1_summaries: list[SummaryResult],
        project_name: str,
    ) -> SummaryResult:
        """Gera Bússola de Contexto (L2) a partir de resumos L1.

        Aplica Poda por Relevância (Amnésia Seletiva) antes da síntese.
        """
        # Poda — remove módulos triviais
        pruned = self._prune_low_relevance(l1_summaries)
        pruned_count = len(l1_summaries) - len(pruned)
        if pruned_count > 0:
            logger.info(
                "Amnésia Seletiva: %d/%d módulos podados (threshold=%.2f).",
                pruned_count, len(l1_summaries), L2_RELEVANCE_THRESHOLD,
            )

        # Monta bloco de resumos
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

                    # Persiste Bússola no SqliteStore (se disponível)
                    if self._store is not None:
                        self._persist_l2(project_name, result)

                    return result

                logger.warning(
                    "L2 attempt %d/%d: JSON inválido para projeto %s",
                    attempt, MAX_RETRY_LOOPS, project_name,
                )

            except Exception as e:
                logger.warning(
                    "L2 attempt %d/%d falhou para projeto %s: %s",
                    attempt, MAX_RETRY_LOOPS, project_name, e,
                )

        # Dumb Summary L2
        logger.error("L2: todas as tentativas falharam para %s — Dumb Summary.", project_name)
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
        """Grava a Bússola L2 no campo summary do projeto no SqliteStore."""
        try:
            self._store.update_project(project_name, summary=result.summary)
            logger.info("Bússola L2 persistida para projeto %s.", project_name)
        except Exception as e:
            logger.error("Falha ao persistir Bússola L2 para %s: %s", project_name, e)

    # ===================================================================
    # HEURISTIC FALLBACK & RETRY LOOP
    # ===================================================================

    def _extract_json_with_fallback(self, raw_response: str) -> Optional[dict]:
        """Tenta extrair JSON da resposta do LLM com fallback progressivo."""
        if not raw_response or not raw_response.strip():
            return None

        text = raw_response.strip()

        # Remove markdown fences se presentes (```json ... ```)
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove primeira e última linha se são fences
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Tentativa 1: json.loads direto
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # Tentativa 2: regex para extrair JSON embutido
        matches = _JSON_BLOCK_RE.findall(text)
        for match in matches:
            try:
                return json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue

        # Tentativa 3: busca simples por { ... } mais externo
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

        logger.debug("JSON extraction falhou para resposta: %.100s...", text)
        return None

    def _generate_dumb_summary(self, content: str, max_tokens: int) -> str:
        """Gera Dumb Summary (texto plano truncado) como último recurso."""
        max_chars = max_tokens * 4
        # Remove linhas vazias em excesso
        lines = [line for line in content.splitlines() if line.strip()]
        clean = "\n".join(lines)

        if len(clean) <= max_chars:
            return f"[DUMB] {clean}"

        truncated = clean[:max_chars].rsplit(" ", 1)[0]
        return f"[DUMB] {truncated}..."

    # ===================================================================
    # PODA POR RELEVÂNCIA (Amnésia Seletiva)
    # ===================================================================

    def _calculate_relevance(self, summary: SummaryResult) -> float:
        """Calcula score de relevância para poda L2.

        Fatores (pesos normalizados para [0.0, 1.0]):
            - source_chunks: Mais chunks = módulo maior = mais relevante (40%).
            - high_priority_tags: Tags de frameworks/APIs core (40%).
            - is_dumb_summary: Penaliza resumos dumb (20%).
        """
        score = 0.0

        # Fator 1: Tamanho do módulo (normalized via log)
        chunk_score = min(1.0, summary.source_chunks / 10.0)
        score += chunk_score * 0.4

        # Fator 2: Presença de tags de alta prioridade
        if summary.detected_tags:
            high_count = sum(1 for t in summary.detected_tags if t in HIGH_PRIORITY_TAGS)
            tag_score = min(1.0, high_count / 3.0)
            score += tag_score * 0.4
        else:
            score += 0.0

        # Fator 3: Penalidade por Dumb Summary
        if summary.is_dumb_summary:
            score += 0.0  # penalidade total
        else:
            score += 0.2

        return round(min(1.0, max(0.0, score)), 3)

    def _calculate_relevance_from_parts(self, l0_summaries: list[SummaryResult]) -> float:
        """Calcula relevância de um cluster a partir de seus L0s."""
        if not l0_summaries:
            return 0.0

        # Cria um SummaryResult temporário para o cálculo
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
        """Remove resumos L1 com relevância abaixo do threshold."""
        result: list[SummaryResult] = []

        for s in summaries:
            # Calcula relevância se ainda não foi calculada
            if s.relevance_score == 1.0:
                s.relevance_score = self._calculate_relevance(s)

            if s.relevance_score >= threshold:
                result.append(s)
            else:
                logger.debug(
                    "Amnésia Seletiva: podado '%s' (score=%.3f < threshold=%.2f)",
                    s.source_label, s.relevance_score, threshold,
                )

        # Segurança: nunca poda todos — mantém pelo menos o top-1
        if not result and summaries:
            best = max(summaries, key=lambda s: s.relevance_score)
            result.append(best)
            logger.warning("Amnésia Seletiva: manteve pelo menos '%s' (score=%.3f).", best.source_label, best.relevance_score)

        return result

    # ===================================================================
    # UTILITÁRIOS
    # ===================================================================

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estima tokens: ~4 caracteres por token."""
        return max(1, len(text) // 4)
