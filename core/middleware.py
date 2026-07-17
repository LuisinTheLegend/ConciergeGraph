"""
core/middleware.py — Grafo Concierge v3.8.0 (Absolute Solidity)

A Fachada Central — GrafoConcierge.

Esta é a classe que o mundo exterior consome. Ela encapsula TODA a
complexidade das camadas internas (storage, ingestion, services, core)
em uma API pública limpa e orientada a projetos.

Quem consome esta classe:
    - interface/mcp_server.py (Servidor MCP → Claude Desktop, Cursor)
    - interface/cli.py (Linha de Comando)
    - interface/action_hooks.py (Módulos Operacionais)
    - Testes de integração

Métodos públicos:
    - register_project()  → Registra um novo projeto no grafo
    - wake_up()           → Reativa consciência: bússola + wings + commits
    - mine()              → Ingestão de arquivos (concierge mine)
    - hybrid_search()     → Busca Híbrida v4 completa
    - commit_memory()     → Registra alterações consolidadas
    - get_resume()        → Bússola de Contexto (resumo conciso)
    - lazy_load()         → Carregamento on-demand de um nó
    - delete_project()    → Remoção com cascata
    - find_similar()      → Projetos na mesma ala
    - status()            → Estatísticas do projeto

Princípio: Nenhuma classe interna (SqliteStore, ChromaVectorStore, etc.)
é exposta ao mundo exterior. Tudo passa por esta fachada.
"""

from __future__ import annotations

import logging
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Optional

from core.config import ConciergeConfig, DEFAULT_CONFIG
from core.project_index import ProjectIndex
from core.hybrid_search import HybridSearchEngine
from core.memory_extractor import SemanticExtractor
from storage.store import SqliteStore
from storage.vector_store import ChromaVectorStore, EmbeddingManager
from ingestion.orchestrator import IngestionManager

logger = logging.getLogger("grafo-concierge.middleware")


class GrafoConcierge:
    """Fachada Central do Grafo Concierge — API pública unificada.

    Instanciando esta classe, todos os subsistemas são inicializados
    automaticamente e inter-conectados.

    Args:
        sqlite_store: Instância de SqliteStore.
        vector_store: Instância de ChromaVectorStore.
        embedding_manager: Instância de EmbeddingManager.
        ingestion_manager: Instância de IngestionManager.
        config: Parâmetros centralizados (default: DEFAULT_CONFIG).
    """

    def __init__(
        self,
        sqlite_store: SqliteStore,
        vector_store: ChromaVectorStore,
        embedding_manager: EmbeddingManager,
        ingestion_manager: IngestionManager,
        config: ConciergeConfig = DEFAULT_CONFIG,
        llm_adapter: Any = None,
    ) -> None:
        self._store = sqlite_store
        self._vector = vector_store
        self._embedder = embedding_manager
        self._ingestion = ingestion_manager
        self._config = config

        # Sub-módulos do core
        self._project_index = ProjectIndex(sqlite_store, config)
        self._search_engine = HybridSearchEngine(
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            embedding_manager=embedding_manager,
            project_index=self._project_index,
            config=config,
        )

        # Motor de Extração Semântica (requer LLM adapter)
        self._semantic_extractor: SemanticExtractor | None = (
            SemanticExtractor(llm_adapter) if llm_adapter else None
        )

        logger.info("GrafoConcierge (Fachada) inicializada com sucesso.")

    # ===================================================================
    # REGISTER — Registra um novo projeto
    # ===================================================================

    def register_project(
        self,
        folder_name: str,
        wing: Optional[str] = None,
        privacy_level: str = "PUBLIC",
        summary: Optional[str] = None,
    ) -> str:
        """Registra um novo projeto no grafo.

        Se o projeto já existir (por folder_name), retorna o UUID existente.
        Caso contrário, gera UUID v4 e cria o registro.

        Args:
            folder_name: Nome do diretório / identificador do projeto.
            wing: Primary Wing (se None, será categorizado automaticamente
                  após a primeira ingestão).
            privacy_level: Nível de privacidade (PUBLIC, INTERNAL, RESTRICTED).
            summary: Descrição inicial do projeto.

        Returns:
            UUID do projeto (novo ou existente).
        """
        # Verifica se já existe
        try:
            existing = self._store.get_project(folder_name)
            logger.info("Projeto já existe: '%s' → %s", folder_name, existing["uuid"])
            return existing["uuid"]
        except Exception:
            pass

        project_uuid = str(uuid_lib.uuid4())
        primary_wing = wing or self._config.default_wing

        self._store.create_project(
            uuid=project_uuid,
            folder_name=folder_name,
            primary_wing=primary_wing,
            privacy_level=privacy_level,
            summary=summary,
        )

        logger.info(
            "Projeto registrado: '%s' → %s (wing='%s', privacy='%s')",
            folder_name, project_uuid, primary_wing, privacy_level,
        )
        return project_uuid

    # ===================================================================
    # WAKE UP — Reativação de consciência
    # ===================================================================

    def wake_up(self, project_uuid: str) -> dict:
        """Reativa a consciência do agente para um projeto.

        Retorna o pacote mínimo de contexto necessário para o agente
        retomar o trabalho: Bússola, Reference Wings e últimos commits.

        Alinhado com a Tool MCP concierge_wakeup.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Dict com:
            {
                "project": dict (dados do projeto),
                "resume": str (Bússola de Contexto),
                "reference_wings": list[str],
                "recent_commits": list[dict],
                "stats": dict,
            }
        """
        project = self._store.get_project(project_uuid)
        ref_wings = self._project_index.get_reference_wings(project_uuid)
        recent_commits = self._store.get_recent_commits(project_uuid, limit=5)
        stats = self._store.get_project_stats(project_uuid)

        resume = project.get("summary", "")
        if not resume:
            resume = f"Projeto '{project.get('folder_name', 'unknown')}' — sem Bússola de Contexto definida."

        result = {
            "project": project,
            "resume": resume,
            "reference_wings": ref_wings,
            "recent_commits": recent_commits,
            "stats": stats,
        }

        logger.info(
            "Wake-up: projeto=%s, commits=%d, ref_wings=%d",
            project_uuid, len(recent_commits), len(ref_wings),
        )
        return result

    # ===================================================================
    # MINE — Ingestão de arquivos
    # ===================================================================

    def mine(
        self,
        project_uuid: str,
        source_path: str,
        auto_tag: bool = True,
        auto_categorize: bool = True,
    ) -> dict:
        """Executa o pipeline completo de ingestão (concierge mine).

        Delega ao IngestionManager e, opcionalmente, recategoriza
        a Primary Wing do projeto após a ingestão.

        Args:
            project_uuid: UUID do projeto.
            source_path: Caminho do diretório fonte.
            auto_tag: Habilitar detecção automática de tags.
            auto_categorize: Recategorizar ala após ingestão.

        Returns:
            Dict compatível com a resposta da Tool MCP concierge_mine.
        """
        result = self._ingestion.mine(project_uuid, source_path, auto_tag)
        result_dict = result.to_dict()

        # Auto-categorização pós-ingestão
        if auto_categorize and result_dict.get("nodes_created", 0) > 0:
            try:
                wing = self._project_index.auto_categorize_project(project_uuid)
                result_dict["auto_categorized_wing"] = wing
            except Exception as e:
                logger.warning("Auto-categorização falhou: %s", e)

        return result_dict

    # ===================================================================
    # SEARCH — Busca Híbrida v4
    # ===================================================================

    def hybrid_search(
        self,
        query: str,
        project_uuid: str,
        top_k: Optional[int] = None,
        include_references: bool = False,
        all_wings: bool = False,
        node_type: Optional[str] = None,
    ) -> list[dict]:
        """Busca Híbrida v4 — Pipeline completo.

        Delega ao HybridSearchEngine a orquestração tri-sinal.
        Alinhado com a Tool MCP concierge_search.

        Args:
            query: Texto de busca.
            project_uuid: UUID do projeto âncora.
            top_k: Máximo de resultados.
            include_references: Incluir Reference Wings.
            all_wings: Buscar em todas as alas.
            node_type: Filtro cirúrgico por tipo de nó.

        Returns:
            Lista de dicts com score_final e breakdown, ordenada DESC.
        """
        return self._search_engine.search(
            query=query,
            project_uuid=project_uuid,
            top_k=top_k,
            include_references=include_references,
            all_wings=all_wings,
            node_type=node_type,
        )

    # ===================================================================
    # COMMIT — Registro de alterações consolidadas
    # ===================================================================

    def commit_memory(
        self,
        project_uuid: str,
        phase: str,
        technical_changes: str,
        updated_pointers: list[str],
        node_ids: Optional[list[int]] = None,
    ) -> int:
        """Registra um commit de memória no grafo.

        Cada commit salva as alterações técnicas e ponteiros atualizados.
        Se node_ids forem fornecidos, atualiza o last_commit_at de cada nó.

        Alinhado com a Tool MCP concierge_commit.

        Args:
            project_uuid: UUID do projeto.
            phase: Fase atual (planning, build, done, review).
            technical_changes: Descrição das mudanças técnicas.
            updated_pointers: Lista de ponteiros atualizados.
            node_ids: IDs de nós afetados (para atualizar recência).

        Returns:
            ID do commit criado.
        """
        commit_id = self._store.create_commit(
            project_uuid=project_uuid,
            phase=phase,
            technical_changes=technical_changes,
            updated_pointers=updated_pointers,
        )

        # Atualiza recência dos nós afetados
        if node_ids:
            for nid in node_ids:
                try:
                    self._store.touch_node_commit(nid)
                except Exception as e:
                    logger.warning("Falha ao tocar recência do nó %d: %s", nid, e)

        logger.info(
            "Commit registrado: id=%d, projeto=%s, fase='%s', nós_afetados=%d",
            commit_id, project_uuid, phase, len(node_ids or []),
        )
        return commit_id

    # ===================================================================
    # RESUME — Bússola de Contexto
    # ===================================================================

    def get_resume(self, project_uuid: str) -> str:
        """Retorna a Bússola de Contexto (resumo conciso) do projeto.

        Alinhado com a Tool MCP concierge_resume.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            String com o resumo do projeto (max ~300 tokens).
        """
        project = self._store.get_project(project_uuid)
        resume = project.get("summary", "")

        if not resume:
            stats = self._store.get_project_stats(project_uuid)
            resume = (
                f"Projeto '{project.get('folder_name', 'unknown')}' "
                f"com {stats.get('total_nodes', 0)} nós e "
                f"{stats.get('total_edges', 0)} arestas. "
                f"Ala: {project.get('primary_wing', 'geral')}."
            )

        return resume

    # ===================================================================
    # LAZY LOAD — Carregamento on-demand de um nó
    # ===================================================================

    def lazy_load(self, node_id: int) -> dict:
        """Carrega os dados completos de um nó sob demanda.

        Atualiza o last_accessed do nó para registrar a consulta.
        Alinhado com a Tool MCP concierge_load.

        Args:
            node_id: ID do nó a carregar.

        Returns:
            Dict com todos os campos do nó + arestas de saída.
        """
        node = self._store.get_node(node_id)

        # Atualiza last_accessed (relevante para Amnésia Seletiva)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self._store.update_node(node_id, last_accessed=now)

        # Carrega arestas de saída para contexto
        edges_out = self._store.get_edges_from(node_id)

        result = {
            **node,
            "edges_out": edges_out,
        }

        logger.debug("Lazy Load: nó=%d, arestas=%d", node_id, len(edges_out))
        return result

    # ===================================================================
    # DELETE — Remoção de projeto
    # ===================================================================

    def delete_project(self, project_uuid: str) -> None:
        """Remove um projeto e todos os dados associados.

        Cascata: nós, arestas, trajetórias, commits e reference_wings.
        Também limpa vetores associados no ChromaDB.

        Args:
            project_uuid: UUID do projeto a remover.
        """
        # Remove vetores do ChromaDB antes do SQLite (precisa dos node_ids)
        try:
            nodes = self._store.get_nodes_by_project(project_uuid)
            if nodes:
                doc_ids = [f"node_{n['id']}" for n in nodes]
                self._vector.delete_batch(doc_ids)
                logger.info("Vetores removidos: %d embeddings do projeto %s", len(doc_ids), project_uuid)
        except Exception as e:
            logger.warning("Falha ao limpar vetores do projeto %s: %s", project_uuid, e)

        # Remove do SQLite (CASCADE cuida de nós, arestas, etc.)
        self._store.delete_project(project_uuid)
        logger.info("Projeto removido: %s", project_uuid)

    # ===================================================================
    # SIMILAR — Projetos da mesma ala
    # ===================================================================

    def find_similar(
        self,
        project_uuid: str,
        limit: int = 5,
        include_references: bool = False,
        all_wings: bool = False,
    ) -> list[dict]:
        """Busca projetos similares por domínio (mesma ala).

        Args:
            project_uuid: UUID do projeto âncora.
            limit: Máximo de resultados.
            include_references: Incluir Reference Wings.
            all_wings: Todas as alas.

        Returns:
            Lista de dicts com dados dos projetos similares.
        """
        return self._project_index.find_similar_projects(
            project_uuid, limit, include_references, all_wings,
        )

    # ===================================================================
    # STATUS — Estatísticas do projeto
    # ===================================================================

    def status(self, project_uuid: str) -> dict:
        """Retorna estatísticas completas de um projeto.

        Alinhado com a Tool MCP concierge_status.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Dict com contadores de nós, arestas, commits, trajetórias, etc.
        """
        project = self._store.get_project(project_uuid)
        stats = self._store.get_project_stats(project_uuid)
        ref_wings = self._project_index.get_reference_wings(project_uuid)
        last_phase = self._store.get_last_commit_phase(project_uuid)

        return {
            "project": project,
            "stats": stats,
            "reference_wings": ref_wings,
            "last_commit_phase": last_phase,
        }

    # ===================================================================
    # Acesso a sub-módulos (para uso avançado / testes)
    # ===================================================================

    @property
    def project_index(self) -> ProjectIndex:
        """Acesso ao ProjectIndex para operações avançadas de alas."""
        return self._project_index

    @property
    def search_engine(self) -> HybridSearchEngine:
        """Acesso ao HybridSearchEngine para buscas customizadas."""
        return self._search_engine

    @property
    def store(self) -> SqliteStore:
        """Acesso ao SqliteStore (para operações internas avançadas)."""
        return self._store

    def search_symbols(self, query: str, project_uuid: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Realiza busca rápida por símbolos no FTS5."""
        return self._store.search_symbols(query, project_uuid, limit)

    def get_implementations(self, symbol_id: int) -> dict:
        """Retorna o bloco de código exato da AST armazenado no nó."""
        node = self._store.get_node(symbol_id)
        return {
            "id": node["id"],
            "label": node["label"],
            "type": node["type"],
            "project_uuid": node["project_uuid"],
            "content": node.get("content"),
            "file_hash": node.get("file_hash"),
        }

    def get_callers(self, symbol_id: int) -> list[dict]:
        """Consulta as arestas para retornar todas as chamadas ao símbolo."""
        return self._store.get_callers(symbol_id)

    def get_full_topology(self, project_uuid: Optional[str] = None) -> dict[str, list[dict]]:
        """Retorna a topologia completa (nós e arestas) de forma leve."""
        return self._store.get_lightweight_topology(project_uuid)

    # ===================================================================

    # STORE FACT — Gravação de Fatos Semânticos via SemanticExtractor
    # ===================================================================

    def store_fact(
        self,
        scope_type: str,
        scope_id: str,
        fact_statement: str,
    ) -> list[dict]:
        """Grava um fato semântico no grafo via SemanticExtractor.

        O SemanticExtractor avalia o fato contra os fatos existentes
        do escopo e decide: ADD, UPDATE, DELETE ou NOOP.

        Alinhado com a Tool MCP concierge_store_fact.

        Args:
            scope_type: Tipo de escopo ('user', 'session', 'agent', 'org').
            scope_id: Identificador único do escopo.
            fact_statement: Texto do fato/preferência a gravar.

        Returns:
            Lista de dicts detalhando as decisões tomadas.

        Raises:
            RuntimeError: Se o SemanticExtractor não está configurado.
        """
        if self._semantic_extractor is None:
            raise RuntimeError(
                "SemanticExtractor não disponível: llm_adapter não foi "
                "fornecido na inicialização do GrafoConcierge."
            )

        def _do_store(conn) -> list[dict]:
            return self._semantic_extractor.evaluate_and_store_facts(
                conn=conn,
                scope_type=scope_type,
                scope_id=scope_id,
                new_facts=[fact_statement],
            )

        results = self._store.write_callback(_do_store)
        logger.info(
            "store_fact: scope=%s/%s, resultados=%d",
            scope_type, scope_id, len(results),
        )

        # Sincronização vetorial episódica se o backend for QdrantVectorStore
        try:
            from core.vector_backend import QdrantVectorStore
            if isinstance(self._vector, QdrantVectorStore) and results:
                for fact in results:
                    fact_id = fact.get("id")
                    statement = fact.get("fact_statement")
                    if fact_id is not None and statement:
                        emb = self._embedder.embed(statement)
                        if emb:
                            metadata = {
                                "scope_type": scope_type,
                                "scope_id": scope_id,
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "utility_alpha": 1.0,
                                "utility_beta": 1.0,
                                "fact_id": fact_id,
                                "fact_statement": statement
                            }
                            self._vector.store_embedding(
                                doc_id=f"fact_{fact_id}",
                                embedding=emb,
                                metadata=metadata
                            )
                            logger.info("Fato semântico %d sincronizado no Qdrant (episodic_memory).", fact_id)
        except Exception as q_err:
            logger.warning("Falha ao sincronizar fato semântico no Qdrant: %s", q_err)

        return results

    # ===================================================================
    # USER CORE MEMORY — Patch 1
    # ===================================================================

    def set_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
        content: str,
    ) -> int:
        """Grava ou atualiza um bloco de memória core do usuário/sessão.

        Args:
            scope_type: 'user', 'session', 'agent' ou 'org'.
            scope_id: Identificador único do escopo.
            block_label: Rótulo do bloco de memória.
            content: Conteúdo a armazenar.

        Returns:
            ID do registro inserido/atualizado.
        """
        return self._store.set_core_memory(scope_type, scope_id, block_label, content)

    def get_core_memory_blocks(
        self,
        scope_type: str,
        scope_id: str,
        block_label: Optional[str] = None,
    ) -> list[dict]:
        """Retorna blocos de memória core para um escopo.

        Args:
            scope_type: Tipo de escopo.
            scope_id: Identificador único do escopo.
            block_label: Se informado, retorna apenas o bloco específico
                         (lista com 0 ou 1 elemento). Se ausente, retorna todos.

        Returns:
            Lista de dicts com os registros de user_core_memory.
        """
        if block_label:
            record = self._store.get_core_memory(scope_type, scope_id, block_label)
            return [record] if record else []
        return self._store.list_core_memory_blocks(scope_type, scope_id)

    # ===================================================================
    # FEEDBACK LOOP BAYESIANO — Patch 3
    # ===================================================================

    def update_fact_utility(self, fact_id: int, was_useful: bool) -> None:
        """Atualiza a utilidade Bayesiana de um semantic_fact.

        Incrementa utility_alpha (sucesso) ou utility_beta (falha) do fato,
        alimentando o Thompson Sampling do HybridSearchEngine.

        Args:
            fact_id: ID do fato semântico (campo id de semantic_facts).
            was_useful: True se o fato foi útil, False caso contrário.
        """
        from storage.semantic_logic import update_memory_utility

        def _do_update(conn) -> None:
            update_memory_utility(conn, fact_id, was_useful)

        self._store.write_callback(_do_update)
        logger.info(
            "update_fact_utility: fact_id=%d, was_useful=%s → %s atualizado.",
            fact_id, was_useful, "utility_alpha" if was_useful else "utility_beta",
        )

    # ===================================================================
    # ARSENAL MCP — Backend-6.1: Ciclo de Vida + Telemetria + Vetorial
    # ===================================================================

    def update_project(self, project_uuid: str, **fields: Any) -> None:
        """Atualiza campos permitidos de um projeto (cadastro).

        Args:
            project_uuid: UUID do projeto.
            **fields: Campos a atualizar (folder_name, primary_wing,
                      privacy_level, summary).
        """
        self._store.update_project(project_uuid, **fields)
        logger.info("update_project: %s → campos=%s", project_uuid, list(fields.keys()))

    def add_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Associa uma Reference Wing ao projeto.

        Args:
            project_uuid: UUID do projeto.
            wing_name: Nome da ala a associar.
        """
        self._store.add_reference_wing(project_uuid, wing_name)
        logger.info("add_reference_wing: %s → wing=%s", project_uuid, wing_name)

    def remove_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Remove uma Reference Wing do projeto.

        Args:
            project_uuid: UUID do projeto.
            wing_name: Nome da ala a remover.
        """
        self._store.remove_reference_wing(project_uuid, wing_name)
        logger.info("remove_reference_wing: %s → wing=%s", project_uuid, wing_name)

    def get_trajectories(self, project_uuid: str) -> list[dict]:
        """Recupera o histórico de trajetórias cognitivas do projeto.

        Args:
            project_uuid: UUID do projeto.

        Returns:
            Lista de dicts com as trajetórias registradas.
        """
        return self._store.get_trajectories(project_uuid)

    def count_embeddings(self, project_uuid: Optional[str] = None) -> int:
        """Retorna a contagem exata de vetores no ChromaDB.

        Args:
            project_uuid: Se informado, conta apenas deste projeto.

        Returns:
            Número total de embeddings armazenados.
        """
        return self._vector.count(project_uuid)

    def reset_collection(self) -> bool:
        """Destrói e recria a coleção de vetores (reparo emergencial).

        CUIDADO: Operação destrutiva e irreversível. Exigirá re-ingestão.

        Returns:
            True se sucesso, False caso contrário.
        """
        result = self._vector.reset_collection()
        if result:
            logger.warning("reset_collection: coleção vetorial destruída e recriada.")
        return result
