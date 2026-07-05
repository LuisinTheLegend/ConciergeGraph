"""
ingestion/orchestrator.py — Grafo Concierge v3.8.0 (Absolute Solidity)

IngestionManager — Orquestrador do Motor de Ingestão Apex.

É o motor por trás do comando `concierge mine`.
Coordena o fluxo completo: Crawl → Parse → Summarize → Store (SQLite + Vector).

Fluxo de execução:
    1. CRAWL: ProjectCrawler escaneia o filesystem, detecta deltas (SHA256).
    2. PARSE: FileParser divide arquivos novos/modificados em chunks semânticos.
    3. SUMMARIZE: ZoomSummarizer gera resumos L0 para cada chunk.
    4. EMBED: EmbeddingManager gera vetores para cada chunk.
    5. STORE (SQLite): Cria nós (nodes), arestas estruturais (edges) e commit_log.
    6. STORE (Vector): ChromaVectorStore armazena embeddings em batch.
    7. GARBAGE COLLECTION: Remove nós e vetores de arquivos deletados.
    8. ZOOM GEAR (assíncrono/opcional): Gera resumos L1 e L2.

Retorno:
    Dict compatível com a resposta da Tool MCP concierge_mine:
    {
        "files_processed": int,
        "categories": {"code": int, "doc": int, "config": int, "conversation": int},
        "nodes_created": int,
        "embeddings_stored": int,
        "tags_applied": list[str]
    }

Integração:
    - storage.store.SqliteStore → Persistência relacional.
    - storage.vector_store.ChromaVectorStore → Persistência vetorial.
    - storage.vector_store.EmbeddingManager → Geração de embeddings.
    - ingestion.crawler.ProjectCrawler → Varredura de filesystem.
    - ingestion.parser.FileParser → Chunking semântico.
    - ingestion.summarizer.ZoomSummarizer → Engrenagem de Zoom.
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
# IngestionResult — retorno padronizado do concierge mine
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Resultado consolidado do pipeline de ingestão.

    Compatível com o retorno da Tool MCP concierge_mine (v3.8).
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
        """Converte para dict compatível com MCP response."""
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
# IngestionManager — Orquestrador do Pipeline
# ---------------------------------------------------------------------------

class IngestionManager:
    """Orquestrador do Motor de Ingestão Apex (concierge mine).

    Coordena o fluxo Crawl → Parse → Summarize → Embed → Store → GC.
    Cada etapa é isolada e resiliente (Semantic Fallback).
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
        """Executa o pipeline completo de ingestão para um projeto.

        Este é o método principal chamado pela Tool MCP concierge_mine.
        """
        t0 = time.perf_counter()
        result = IngestionResult()

        logger.info("=" * 60)
        logger.info("MINE INICIADO: projeto=%s, source=%s", project_uuid, source_path)
        logger.info("=" * 60)

        # --- Validação: projeto existe? ---
        try:
            self._store.get_project(project_uuid)
        except Exception as e:
            raise ValueError(f"Projeto não encontrado: {project_uuid}") from e

        # --- STEP 1: CRAWL ---
        logger.info("[1/7] CRAWL — Varredura do filesystem...")
        crawl_report = self._step_crawl(source_path, project_uuid)
        result.files_processed = len(crawl_report.new_files)
        result.files_skipped = len(crawl_report.unchanged_files)
        result.categories = crawl_report.categories
        logger.info(
            "[1/7] CRAWL concluído: %d novos, %d inalterados, %d deletados.",
            result.files_processed, result.files_skipped, len(crawl_report.deleted_node_ids),
        )

        # --- Short-circuit: nada novo e nada deletado ---
        if not crawl_report.new_files and not crawl_report.deleted_node_ids:
            logger.info("Nenhuma alteração detectada — pipeline encerrado.")
            elapsed = time.perf_counter() - t0
            logger.info("MINE CONCLUÍDO em %.2fs (noop).", elapsed)
            return result

        # --- STEP 2: PARSE ---
        chunks: list[ParsedChunk] = []
        if crawl_report.new_files:
            logger.info("[2/7] PARSE — Chunking semântico de %d arquivos...", len(crawl_report.new_files))
            chunks = self._step_parse(crawl_report.new_files, result)
            logger.info("[2/7] PARSE concluído: %d chunks extraídos.", len(chunks))

        # --- STEP 3: SUMMARIZE (L0) ---
        summaries: list[SummaryResult] = []
        if chunks and self._summarizer:
            logger.info("[3/7] SUMMARIZE — Geração de %d resumos L0...", len(chunks))
            summaries = self._step_summarize(chunks, result)
            result.summaries_generated = len(summaries)
            logger.info("[3/7] SUMMARIZE concluído: %d resumos L0 gerados.", len(summaries))
        else:
            logger.info("[3/7] SUMMARIZE — Ignorado (summarizer=%s, chunks=%d).",
                        "OFF" if not self._summarizer else "ON", len(chunks))

        # --- STEP 4: STORE SQLite ---
        if chunks:
            logger.info("[4/7] STORE SQLite — Persistindo %d chunks...", len(chunks))
            nodes_created = self._step_store_sqlite(chunks, summaries, project_uuid, auto_tag, result)
            result.nodes_created = nodes_created
            logger.info("[4/7] STORE SQLite concluído: %d nós criados.", nodes_created)

        # --- STEP 5: EMBED ---
        embed_items: list[dict] = []
        if chunks:
            logger.info("[5/7] EMBED — Geração de embeddings para %d chunks...", len(chunks))
            embed_items = self._step_embed(chunks, project_uuid, result)
            logger.info("[5/7] EMBED concluído: %d embeddings gerados.", len(embed_items))

        # --- STEP 6: STORE Vector ---
        if embed_items:
            logger.info("[6/7] STORE Vector — Batch insert de %d embeddings...", len(embed_items))
            stored = self._step_store_vector(embed_items, result)
            result.embeddings_stored = stored
            logger.info("[6/7] STORE Vector concluído: %d embeddings armazenados.", stored)

        # --- STEP 7: GARBAGE COLLECTION ---
        if crawl_report.deleted_node_ids:
            logger.info("[7/7] GC — Removendo %d nós órfãos...", len(crawl_report.deleted_node_ids))
            deleted = self._step_garbage_collection(crawl_report.deleted_node_ids, project_uuid, result)
            result.files_deleted = deleted
            logger.info("[7/7] GC concluído: %d nós removidos.", deleted)
        else:
            logger.info("[7/7] GC — Nenhum nó órfão detectado.")

        # --- Consolidação de tags ---
        result.tags_applied = self._consolidate_tags(chunks)

        elapsed = time.perf_counter() - t0
        logger.info("=" * 60)
        logger.info(
            "MINE CONCLUÍDO em %.2fs: %d processados, %d nós, %d embeddings, %d erros.",
            elapsed, result.files_processed, result.nodes_created,
            result.embeddings_stored, len(result.errors),
        )
        logger.info("=" * 60)

        return result

    # ===================================================================
    # ETAPAS DO PIPELINE
    # ===================================================================

    def _step_crawl(self, source_path: str, project_uuid: str) -> CrawlReport:
        """Etapa 1: Varredura do filesystem."""
        return self._crawler.crawl(source_path, project_uuid)

    def _step_parse(self, new_files: list[CrawlResult], result: IngestionResult) -> list[ParsedChunk]:
        """Etapa 2: Chunking semântico via parse_batch (Semantic Fallback nativo).

        Delega para self._parser.parse_batch() que já implementa o mesmo
        Semantic Fallback por arquivo, eliminando duplicação de loop.
        """
        try:
            return self._parser.parse_batch(new_files)
        except Exception as e:
            error_msg = f"parse_batch falhou: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return []

    def generate_community_summary(self, nodes_block: str) -> Optional[dict]:
        """Gera um resumo de comunidade via LLM se o summarizer estiver configurado.

        API pública que encapsula o acesso ao LLM, evitando que o JanitorService
        acesse self._ingestion._summarizer._llm diretamente (violação da Lei de Demeter).

        Args:
            nodes_block: Texto com os nós da comunidade para sumarizar.

        Returns:
            Dict com 'summary' (str) e 'tags' (list[str]), ou None se LLM
            não estiver configurado ou falhar.
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
            logger.warning("generate_community_summary: LLM falhou: %s", e)
        return None


    def _step_summarize(self, chunks: list[ParsedChunk], result: IngestionResult) -> list[SummaryResult]:
        """Etapa 3: Geração de resumos L0."""
        summaries: list[SummaryResult] = []
        for chunk in chunks:
            try:
                s = self._summarizer.summarize_l0(chunk)
                summaries.append(s)
            except Exception as e:
                error_msg = f"Summarize L0 falhou para {chunk.source_file}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
        return summaries


    def _step_store_sqlite(
        self,
        chunks: list[ParsedChunk],
        summaries: list[SummaryResult],
        project_uuid: str,
        auto_tag: bool,
        result: IngestionResult,
    ) -> int:
        """Etapa 4: Persistência no SQLite (nós + arestas) via Bulk Insert (WAL-friendly).

        Transaction Safety: nós e arestas de diretórios e chamadas são inseridos em lote
        dentro de transações dedicadas.
        """
        if not chunks:
            return 0

        # Coleta nós existentes no projeto para cachear diretórios e mapear símbolos globais
        try:
            existing_nodes = self._store.get_nodes_by_project(project_uuid)
        except Exception as e:
            logger.warning("Erro ao listar nós existentes para cache: %s", e)
            existing_nodes = []

        dir_node_cache = {n["label"]: n["id"] for n in existing_nodes if n.get("type") == "directory"}
        
        # 1. PREPARAR NÓS PARA CRIAÇÃO EM LOTE
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

        # Adiciona diretórios novos primeiro
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

        # Adiciona chunks de código/doc
        dir_offset = len(nodes_to_create)
        from ingestion.parser import ChunkType
        for i, chunk in enumerate(chunks):
            summary_text = None
            if i < len(summaries):
                summary_text = summaries[i].summary
            
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

        # Executa bulk insert de nós
        try:
            node_ids = self._store.create_nodes_and_edges_bulk(nodes_to_create, [])
        except Exception as e:
            error_msg = f"Bulk insert de nós falhou: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            raise RuntimeError(error_msg) from e

        # Atualiza caches com os novos IDs gerados
        for idx, d in enumerate(sorted(new_dirs)):
            dir_node_cache[d] = node_ids[idx]

        # Associa IDs aos chunks (offset pula os diretórios criados no início)
        chunk_node_ids = node_ids[dir_offset:]
        for i, chunk in enumerate(chunks):
            chunk._node_id = chunk_node_ids[i]  # type: ignore[attr-defined]

        # 2. RESOLVER MAPAS DE SÍMBOLOS PARA MAPEAMENTO DE ARESTAS
        project_symbol_map = {}
        global_symbol_map = {}

        # Mapear nós pré-existentes
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

        # Mapear novos nós inseridos
        for i, chunk in enumerate(chunks):
            nid = chunk_node_ids[i]
            sf = chunk.source_file
            sym = chunk.symbol_name
            project_symbol_map[(sf, sym)] = nid
            if sym:
                if sym not in global_symbol_map:
                    global_symbol_map[sym] = []
                global_symbol_map[sym].append(nid)

        # 3. PREPARAR ARESTAS PARA CRIAÇÃO EM LOTE
        edges_to_create = []
        file_module_map = {}

        # Mapear módulos (arquivos) de entrada do lote atual
        for i, chunk in enumerate(chunks):
            if chunk.chunk_type.value == "module":
                file_module_map[chunk.source_file] = chunk_node_ids[i]

        for i, chunk in enumerate(chunks):
            chunk_node_id = chunk_node_ids[i]

            # Arestas de estrutura: diretório -> arquivo, arquivo -> símbolo
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

            # Arestas de chamadas (calls)
            calls = getattr(chunk, "calls", [])
            for call_name in calls:
                target_node_id = None
                
                # Check 1: Lookup de símbolo no mesmo arquivo
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
                            
                # Check 3: Lookup global de símbolo no projeto
                if not target_node_id and call_name in global_symbol_map:
                    target_node_id = global_symbol_map[call_name][0]

                if target_node_id and target_node_id != chunk_node_id:
                    edges_to_create.append({
                        "source_id": chunk_node_id,
                        "target_id": target_node_id,
                        "relation_type": "calls",
                        "weight": 1.0
                    })

        # Executa bulk insert de arestas
        if edges_to_create:
            try:
                self._store.create_nodes_and_edges_bulk([], edges_to_create)
            except Exception as e:
                logger.warning("Falha ao persistir arestas em lote (não fatal): %s", e)

        return len(chunks)

    def _step_embed(self, chunks: list[ParsedChunk], project_uuid: str, result: IngestionResult) -> list[dict]:
        """Etapa 5: Geração de embeddings em batch."""
        # Coleta textos para batch embedding
        texts = [c.content for c in chunks]

        try:
            embeddings = self._embedder.embed_batch(texts)
        except Exception as e:
            error_msg = f"Embed batch falhou: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            embeddings = [None] * len(chunks)

        # Monta items para vector store
        items: list[dict] = []
        for chunk, embedding in zip(chunks, embeddings):
            node_id = getattr(chunk, "_node_id", None)
            if node_id is None:
                continue

            items.append({
                "doc_id": f"node_{node_id}",
                "embedding": embedding,  # pode ser None (Semantic Fallback)
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
        """Etapa 6: Persistência no backend vetorial (batch)."""
        try:
            stored = self._vector.store_embeddings_batch(embed_items)
            return stored
        except Exception as e:
            error_msg = f"Store Vector batch falhou: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return 0

    def _step_garbage_collection(
        self,
        deleted_node_ids: list[int],
        project_uuid: str,
        result: IngestionResult,
    ) -> int:
        """Etapa 7: Garbage Collection — remove nós e vetores orphanados."""
        removed = 0

        for node_id in deleted_node_ids:
            try:
                # Remove do SQLite
                self._store.delete_node(node_id)

                # Remove do backend vetorial
                doc_id = f"node_{node_id}"
                try:
                    self._vector.delete(doc_id)
                except Exception as ve:
                    logger.debug("GC: vetor %s não encontrado (ok): %s", doc_id, ve)

                removed += 1
            except Exception as e:
                error_msg = f"GC falhou para node_id={node_id}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Reconciliation Loop: verifica sincronização SQLite ↔ Vector
        try:
            existing_nodes = self._store.get_nodes_by_project(project_uuid)
            sqlite_ids = [f"node_{n['id']}" for n in existing_nodes if n.get("type") not in ("directory", "cluster", "project")]
            sync_report = self._vector.verify_sync(sqlite_ids)
            orphan_count = sync_report.get("orphans_removed", 0)
            if orphan_count > 0:
                logger.warning("Reconciliation: %d vetores órfãos removidos pós-GC.", orphan_count)
        except Exception as e:
            logger.debug("Reconciliation loop falhou (não fatal): %s", e)

        return removed

    # ===================================================================
    # ZOOM GEAR (L1/L2)
    # ===================================================================

    def generate_project_context(self, project_uuid: str) -> dict:
        """Gera resumos L1 e L2 para o projeto (Zoom Gear completo).

        Pode ser chamado após mine() ou pelo Background Janitor.

        Returns:
            Dict com l1_count, l2_summary, e l2_tags.
        """
        if not self._summarizer:
            logger.warning("generate_project_context: summarizer não configurado.")
            return {"l1_count": 0, "l2_summary": None, "l2_tags": []}

        logger.info("ZOOM GEAR iniciado para projeto %s...", project_uuid)

        # Busca nós com summary preenchido (L0s já gerados)
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

        # Agrupa em clusters e gera L1
        clusters = self._summarizer.build_l1_clusters(l0_summaries)
        l1_summaries: list[SummaryResult] = []

        for cluster_label, cluster_l0s in clusters.items():
            try:
                l1 = self._summarizer.summarize_l1(cluster_l0s, cluster_label)
                l1_summaries.append(l1)
                logger.debug("L1 gerado: %s (%d L0s)", cluster_label, len(cluster_l0s))
            except Exception as e:
                logger.error("L1 falhou para cluster %s: %s", cluster_label, e)

        # Gera L2 (Bússola)
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
    # UTILITÁRIOS
    # ===================================================================

    def _consolidate_tags(self, chunks: list[ParsedChunk]) -> list[str]:
        """Consolida tags únicas de todos os chunks."""
        tags: set[str] = set()
        for c in chunks:
            tags.update(c.detected_tags)
        return sorted(tags)

    def _consolidate_categories(self, chunks: list[ParsedChunk]) -> dict[str, int]:
        """Conta chunks por categoria."""
        cats: dict[str, int] = {"code": 0, "doc": 0, "config": 0, "conversation": 0}
        for c in chunks:
            key = c.category.value
            if key in cats:
                cats[key] += 1
        return cats
