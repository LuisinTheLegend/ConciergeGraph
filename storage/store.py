"""
storage/store.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Fachada (Facade) unificada que compõe:
    - ConnectionManager (connection.py) → WAL, busy_timeout, fila serializada
    - SchemaManager (schema.py)        → DDL, CHECK constraints, FTS5 triggers
    - GraphLogic (logic.py)            → decaimento, centralidade, recência, FTS5

API consistente com as Tools MCP v3.8:
    concierge_resume   → get_project / get_project_stats
    concierge_commit   → create_commit + touch_node_commit
    concierge_search   → fts_search / hybrid_search_score_batch
    concierge_mine     → create_node / find_node_by_hash
    concierge_register → create_project
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from storage.connection import ConnectionManager

if TYPE_CHECKING:
    from core.config import ConciergeConfig
from storage.schema import SchemaManager, VALID_NODE_TYPES, VALID_PRIVACY_LEVELS, VALID_STATUSES
from storage.logic import GraphLogic, TrajectoryNotFoundError, InvalidTransitionError

logger = logging.getLogger("grafo-concierge.store")


# ---------------------------------------------------------------------------
# Exceções da fachada
# ---------------------------------------------------------------------------

class ProjectNotFoundError(Exception):
    """Projeto não encontrado por UUID nem folder_name."""

class NodeNotFoundError(Exception):
    """Nó não encontrado pelo ID fornecido."""

class CommitValidationError(Exception):
    """Campos obrigatórios ausentes no commit."""


# ---------------------------------------------------------------------------
# SqliteStore — Fachada Unificada
# ---------------------------------------------------------------------------

class SqliteStore:
    """Fachada de persistência SQLite para o Grafo Concierge v3.8.

    No __init__, o schema é verificado e aplicado automaticamente.
    O usuário final só interage com esta classe.

    Args:
        db_path: Caminho para o .db (default: ~/.grafo-concierge/concierge.db).
    """

    def __init__(self, db_path: str = "~/.grafo-concierge/concierge.db", config: Optional["ConciergeConfig"] = None) -> None:
        resolved = str(Path(db_path).expanduser().absolute())
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)

        # 1. Schema PRIMEIRO (aplica DDL + FTS5 + triggers antes de qualquer conexão persistente)
        #    A conexão temporária é aberta e fechada aqui, sem competir com a fila.
        self._boot_schema(resolved)

        # 2. Conexões (WAL + busy_timeout + fila serializada) — inicia APÓS schema estar pronto
        self._conn_mgr = ConnectionManager(resolved)
        self._conn_mgr.start()

        # 3. Inteligência (centralidade, recência, decay, FTS5, CTE)
        #    Agora repassa ConciergeConfig para que os pesos obedeçam o config do usuário
        self._logic = GraphLogic(self._conn_mgr, config=config)

        logger.info("SqliteStore inicializado: %s", resolved)

    def _boot_schema(self, db_path: str) -> None:
        """Abre conexão temporária para aplicar o schema de forma idempotente."""
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            mgr = SchemaManager(conn)
            mgr.apply_full_schema()

            # Log de verificação
            tables = mgr.verify_tables_exist()
            missing = [t for t, exists in tables.items() if not exists]
            if missing:
                logger.error("Tabelas ausentes após boot: %s", missing)
                raise RuntimeError(f"Schema incompleto: {missing}")

            triggers = mgr.verify_triggers_exist()
            missing_t = [t for t, exists in triggers.items() if not exists]
            if missing_t:
                logger.error("Triggers FTS5 ausentes: %s", missing_t)
                raise RuntimeError(f"Triggers ausentes: {missing_t}")

            logger.info("Schema v%s verificado — todas as tabelas e triggers OK.", SchemaManager.SCHEMA_VERSION)
        finally:
            conn.close()

    def close(self) -> None:
        """Encerra a fila de escrita e conexões de leitura."""
        self._conn_mgr.close()
        logger.info("SqliteStore encerrado.")

    # ===================================================================
    # PROJECTS
    # ===================================================================

    def create_project(
        self, uuid: str, folder_name: str, primary_wing: str = "geral",
        privacy_level: str = "PUBLIC", summary: Optional[str] = None,
    ) -> dict:
        """Registra um novo projeto (alinhado com concierge_register)."""
        if privacy_level not in VALID_PRIVACY_LEVELS:
            raise ValueError(f"privacy_level inválido: '{privacy_level}'. Aceitos: {sorted(VALID_PRIVACY_LEVELS)}")

        def _do(conn, u, fn, pw, pl, s):
            conn.execute(
                "INSERT INTO projects (uuid, folder_name, primary_wing, privacy_level, summary) VALUES (?,?,?,?,?)",
                (u, fn, pw, pl, s))
            return {"uuid": u, "folder_name": fn, "primary_wing": pw, "privacy_level": pl}

        return self._conn_mgr.write(_do, uuid, folder_name, primary_wing, privacy_level, summary)

    def get_project(self, project_id: str) -> dict:
        """Busca projeto por UUID ou folder_name."""
        with self._conn_mgr.read() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE uuid = ? OR folder_name = ?",
                (project_id, project_id)).fetchone()
        if not row:
            raise ProjectNotFoundError(f"Projeto não encontrado: {project_id}")
        return dict(row)

    def update_project(self, uuid: str, **fields: Any) -> None:
        """Atualiza campos permitidos de um projeto."""
        allowed = {"folder_name", "primary_wing", "privacy_level", "summary"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "privacy_level" in updates and updates["privacy_level"] not in VALID_PRIVACY_LEVELS:
            raise ValueError(f"privacy_level inválido: {updates['privacy_level']}")
        updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [uuid]

        def _do(conn, sc, v):
            conn.execute(f"UPDATE projects SET {sc} WHERE uuid = ?", v)
        self._conn_mgr.write(_do, set_clause, vals)

    def delete_project(self, uuid: str) -> None:
        """Remove um projeto e todos os dados cascata."""
        def _do(conn, u):
            conn.execute("DELETE FROM projects WHERE uuid = ?", (u,))
        self._conn_mgr.write(_do, uuid)

    def list_projects(self) -> list[dict]:
        """Lista todos os projetos ordenados por updated_at DESC."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    # ===================================================================
    # NODES
    # ===================================================================

    def create_node(
        self, project_uuid: str, label: str, summary: Optional[str] = None,
        node_type: str = "FACT", type_: str = "file",
        tags: Optional[list[str]] = None, file_hash: Optional[str] = None,
        status: str = "ACTIVE", content: Optional[str] = None,
        valid_from_commit: Optional[str] = None,
        valid_to_commit: Optional[str] = None,
    ) -> int:
        """Cria um nó no grafo (alinhado com concierge_mine).

        Args:
            valid_from_commit: SHA do commit em que o nó passa a ser válido (opcional).
            valid_to_commit: SHA do commit em que o nó deixa de ser válido (opcional).
        """
        if node_type not in VALID_NODE_TYPES:
            raise ValueError(f"node_type inválido: '{node_type}'. Aceitos: {sorted(VALID_NODE_TYPES)}")
        if status not in VALID_STATUSES:
            raise ValueError(f"status inválido: '{status}'. Aceitos: {sorted(VALID_STATUSES)}")
        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        def _do(conn, pu, lb, sm, nt, tp, tg, fh, st, ct, vfc, vtc):
            cur = conn.execute(
                """INSERT INTO nodes
                   (project_uuid, label, summary, node_type, type, tags, file_hash, status, content,
                    valid_from_commit, valid_to_commit)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pu, lb, sm, nt, tp, tg, fh, st, ct, vfc, vtc))
            return cur.lastrowid
        return self._conn_mgr.write(
            _do, project_uuid, label, summary, node_type, type_, tags_json,
            file_hash, status, content, valid_from_commit, valid_to_commit,
        )

    def get_node(self, node_id: int) -> dict:
        """Retorna um nó pelo ID."""
        with self._conn_mgr.read() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if not row:
            raise NodeNotFoundError(f"Nó não encontrado: {node_id}")
        result = dict(row)
        if result.get("tags"):
            try:
                result["tags"] = json.loads(result["tags"])
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def get_nodes_by_project(
        self, project_uuid: str, node_type: Optional[str] = None, status: Optional[str] = None,
    ) -> list[dict]:
        """Lista nós de um projeto com filtros opcionais."""
        sql = "SELECT * FROM nodes WHERE project_uuid = ?"
        params: list[Any] = [project_uuid]
        if node_type:
            sql += " AND node_type = ?"
            params.append(node_type)
        if status:
            sql += " AND status = ?"
            params.append(status)
        with self._conn_mgr.read() as conn:
            rows = conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("tags"):
                try:
                    d["tags"] = json.loads(d["tags"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results

    def update_node(self, node_id: int, **fields: Any) -> None:
        """Atualiza campos permitidos de um nó (inclui campos temporais)."""
        allowed = {"label", "summary", "node_type", "type", "tags", "file_hash",
                    "last_accessed", "last_commit_at", "status",
                    "valid_from_commit", "valid_to_commit"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "node_type" in updates and updates["node_type"] not in VALID_NODE_TYPES:
            raise ValueError(f"node_type inválido: {updates['node_type']}")
        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"status inválido: {updates['status']}")
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [node_id]

        def _do(conn, sc, v):
            conn.execute(f"UPDATE nodes SET {sc} WHERE id = ?", v)
        self._conn_mgr.write(_do, set_clause, vals)

    def delete_node(self, node_id: int) -> None:
        """Remove um nó e suas arestas (CASCADE)."""
        def _do(conn, nid):
            conn.execute("DELETE FROM nodes WHERE id = ?", (nid,))
        self._conn_mgr.write(_do, node_id)

    def find_node_by_hash(self, project_uuid: str, file_hash: str) -> Optional[dict]:
        """Busca nó por SHA256 hash (delta update check no concierge_mine)."""
        with self._conn_mgr.read() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE project_uuid = ? AND file_hash = ?",
                (project_uuid, file_hash)).fetchone()
        return dict(row) if row else None

    def touch_node_commit(self, node_id: int) -> None:
        """Atualiza last_commit_at para agora (usado no commit_memory)."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self.update_node(node_id, last_commit_at=now)

    def create_nodes_and_edges_bulk(
        self,
        nodes_to_create: list[dict],
        edges_to_create: list[dict]
    ) -> list[int]:
        """Cria múltiplos nós e arestas em uma única transação SQLite (WAL-friendly).

        Suporta campos temporais e confidence_tag em cada dict de nó/aresta.
        """
        def _do(conn) -> list[int]:
            node_ids = []
            # Inserir nós
            for n in nodes_to_create:
                if n.get("node_type", "FACT") not in VALID_NODE_TYPES:
                    raise ValueError(f"node_type inválido no bulk: {n.get('node_type')}")
                if n.get("status", "ACTIVE") not in VALID_STATUSES:
                    raise ValueError(f"status inválido no bulk: {n.get('status')}")
                    
                tags_json = json.dumps(n.get("tags"), ensure_ascii=False) if n.get("tags") else None
                cur = conn.execute(
                    """INSERT INTO nodes
                       (project_uuid, label, summary, content, node_type, type, tags, file_hash, status,
                        valid_from_commit, valid_to_commit)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (n["project_uuid"], n["label"], n.get("summary"), n.get("content"),
                     n.get("node_type", "FACT"), n.get("type", "file"), tags_json,
                     n.get("file_hash"), n.get("status", "ACTIVE"),
                     n.get("valid_from_commit"), n.get("valid_to_commit"))
                )
                node_ids.append(cur.lastrowid)
                
            # Inserir arestas
            for e in edges_to_create:
                src_id = e["source_id"]
                tgt_id = e["target_id"]
                
                # Resolução de referências de índices temporários se passados como idx_0, idx_1 etc.
                if isinstance(src_id, str) and src_id.startswith("idx_"):
                    idx = int(src_id.split("_")[1])
                    src_id = node_ids[idx]
                if isinstance(tgt_id, str) and tgt_id.startswith("idx_"):
                    idx = int(tgt_id.split("_")[1])
                    tgt_id = node_ids[idx]
                    
                conn.execute(
                    """INSERT OR REPLACE INTO edges
                       (source_id, target_id, relation_type, weight,
                        valid_from_commit, valid_to_commit, confidence_tag)
                       VALUES (?,?,?,?,?,?,?)""",
                    (src_id, tgt_id, e.get("relation_type", "depends_on"), e.get("weight", 1.0),
                     e.get("valid_from_commit"), e.get("valid_to_commit"),
                     e.get("confidence_tag", "EXTRACTED"))
                )
            return node_ids
            
        return self._conn_mgr.write(_do)

    # ===================================================================
    # EDGES
    # ===================================================================

    def create_edge(
        self, source_id: int, target_id: int,
        relation_type: str = "depends_on", weight: float = 1.0,
        valid_from_commit: Optional[str] = None,
        valid_to_commit: Optional[str] = None,
        confidence_tag: str = "EXTRACTED",
    ) -> None:
        """Cria ou atualiza uma aresta entre dois nós.

        Args:
            valid_from_commit: SHA do commit em que a aresta passa a ser válida.
            valid_to_commit: SHA do commit em que a aresta deixa de ser válida.
            confidence_tag: Grau de confiança da relação ('EXTRACTED'|'INFERRED'|'AMBIGUOUS').
        """
        def _do(conn, s, t, r, w, vfc, vtc, ct):
            conn.execute(
                """INSERT OR REPLACE INTO edges
                   (source_id, target_id, relation_type, weight,
                    valid_from_commit, valid_to_commit, confidence_tag)
                   VALUES (?,?,?,?,?,?,?)""",
                (s, t, r, w, vfc, vtc, ct))
        self._conn_mgr.write(
            _do, source_id, target_id, relation_type, weight,
            valid_from_commit, valid_to_commit, confidence_tag,
        )

    def get_edges_from(self, node_id: int) -> list[dict]:
        """Arestas saindo de um nó (source → targets)."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM edges WHERE source_id = ?", (node_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_edges_to(self, node_id: int) -> list[dict]:
        """Arestas chegando em um nó (sources → target)."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT * FROM edges WHERE target_id = ?", (node_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_in_degree(self, node_id: int) -> int:
        """Conta arestas de entrada (in-degree) de um nó."""
        with self._conn_mgr.read() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM edges WHERE target_id = ?", (node_id,)).fetchone()
        return row["c"] if row else 0

    def delete_edge(self, source_id: int, target_id: int) -> None:
        """Remove uma aresta."""
        def _do(conn, s, t):
            conn.execute("DELETE FROM edges WHERE source_id = ? AND target_id = ?", (s, t))
        self._conn_mgr.write(_do, source_id, target_id)

    # ===================================================================
    # TRAJECTORIES
    # ===================================================================

    def create_trajectory(
        self, project_uuid: str, prompt_origem: str, tentativa_execucao: str,
        erro_encontrado: Optional[str] = None, solucao_aplicada: Optional[str] = None,
        status: str = "ACTIVE",
    ) -> int:
        """Registra uma trajetória episódica (Learning Loop)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"status inválido: '{status}'")

        def _do(conn, pu, po, te, ee, sa, st):
            cur = conn.execute(
                """INSERT INTO trajectories
                   (project_uuid, prompt_origem, tentativa_execucao, erro_encontrado, solucao_aplicada, status)
                   VALUES (?,?,?,?,?,?)""",
                (pu, po, te, ee, sa, st))
            return cur.lastrowid
        return self._conn_mgr.write(_do, project_uuid, prompt_origem, tentativa_execucao,
                                     erro_encontrado, solucao_aplicada, status)

    def get_trajectories(self, project_uuid: str, status: Optional[str] = None) -> list[dict]:
        """Lista trajetórias de um projeto com filtro opcional de status."""
        sql = "SELECT * FROM trajectories WHERE project_uuid = ?"
        params: list[Any] = [project_uuid]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC"
        with self._conn_mgr.read() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def decay_trajectory(self, trajectory_id: int, new_status: str) -> bool:
        """Delega ao GraphLogic (máquina de estados com validação)."""
        return self._logic.decay_trajectory(trajectory_id, new_status)

    # ===================================================================
    # COMMIT LOG (alinhado com concierge_commit)
    # ===================================================================

    def create_commit(
        self, project_uuid: str, phase: str, technical_changes: str,
        updated_pointers: list[str], revisor_approved: bool = False,
        partial_audit: bool = False,
    ) -> int:
        """Registra um commit de memória auditado.

        Validação obrigatória: technical_changes e updated_pointers não podem estar vazios.
        """
        if not technical_changes:
            raise CommitValidationError("technical_changes é obrigatório e não pode estar vazio.")
        if not updated_pointers:
            raise CommitValidationError("updated_pointers é obrigatório e não pode estar vazio.")
        pointers_json = json.dumps(updated_pointers, ensure_ascii=False)

        def _do(conn, pu, ph, tc, up, ra, pa):
            cur = conn.execute(
                """INSERT INTO commit_log
                   (project_uuid, phase, technical_changes, updated_pointers, revisor_approved, partial_audit)
                   VALUES (?,?,?,?,?,?)""",
                (pu, ph, tc, up, int(ra), int(pa)))
            return cur.lastrowid
        return self._conn_mgr.write(_do, project_uuid, phase, technical_changes,
                                     pointers_json, revisor_approved, partial_audit)

    def get_recent_commits(self, project_uuid: str, limit: int = 5) -> list[dict]:
        """Retorna os N commits mais recentes de um projeto."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute(
                "SELECT * FROM commit_log WHERE project_uuid = ? ORDER BY created_at DESC LIMIT ?",
                (project_uuid, limit)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("updated_pointers"):
                try:
                    d["updated_pointers"] = json.loads(d["updated_pointers"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results

    # ===================================================================
    # REFERENCE WINGS
    # ===================================================================

    def add_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Adiciona uma Reference Wing ao projeto."""
        def _do(conn, pu, wn):
            conn.execute("INSERT OR IGNORE INTO reference_wings (project_uuid, wing_name) VALUES (?,?)", (pu, wn))
        self._conn_mgr.write(_do, project_uuid, wing_name)

    def get_reference_wings(self, project_uuid: str) -> list[str]:
        """Lista Reference Wings de um projeto."""
        with self._conn_mgr.read() as conn:
            rows = conn.execute("SELECT wing_name FROM reference_wings WHERE project_uuid = ?", (project_uuid,)).fetchall()
        return [r["wing_name"] for r in rows]

    def remove_reference_wing(self, project_uuid: str, wing_name: str) -> None:
        """Remove uma Reference Wing."""
        def _do(conn, pu, wn):
            conn.execute("DELETE FROM reference_wings WHERE project_uuid = ? AND wing_name = ?", (pu, wn))
        self._conn_mgr.write(_do, project_uuid, wing_name)

    # ===================================================================
    # INTELIGÊNCIA (delegado ao GraphLogic)
    # ===================================================================

    def compute_centrality(self, node_id: int) -> float:
        """Centralidade normalizada: min(in_degree/10, 1.0)."""
        return self._logic.compute_centrality(node_id)

    def compute_recency_score(self, node_id: int) -> float:
        """Score de recência: max(e^(-λ×t), 0.01)."""
        return self._logic.compute_recency_score(node_id)

    def fts_search(self, query: str, project_uuid: Optional[str] = None,
                   node_type: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Busca FTS5 com BM25 normalizado (concierge_search — componente frequência)."""
        return self._logic.fts_search(query, project_uuid, node_type, limit)

    def hybrid_search_score(self, node_id: int, vector_score: float, fts_score: float) -> dict:
        """Score híbrido individual: 0.50×vet + 0.25×fts + 0.25×max(rec,cent)."""
        return self._logic.hybrid_search_score(node_id, vector_score, fts_score)

    def hybrid_search_score_batch(self, candidates: list[dict]) -> list[dict]:
        """Score híbrido em batch — usado pelo concierge_search."""
        return self._logic.hybrid_search_score_batch(candidates)

    def fts_rebuild(self) -> None:
        """Reconstrói o índice FTS5 (pós concierge_mine massivo)."""
        self._logic.fts_rebuild()

    def get_dependency_tree(self, start_node_id: int, max_depth: int = 10) -> list[dict]:
        """CTE: árvore de dependências com proteção anti-loop."""
        return self._logic.get_dependency_tree(start_node_id, max_depth)

    def get_reverse_dependency_tree(self, start_node_id: int, max_depth: int = 10) -> list[dict]:
        """CTE reversa: quem depende deste nó."""
        return self._logic.get_reverse_dependency_tree(start_node_id, max_depth)

    def get_project_stats(self, project_uuid: str) -> dict:
        """Estatísticas completas de um projeto."""
        return self._logic.get_project_stats(project_uuid)

    def get_last_commit_phase(self, project_uuid: str) -> Optional[str]:
        """Fase do commit mais recente."""
        return self._logic.get_last_commit_phase(project_uuid)

    def bulk_decay_stale_trajectories(self, project_uuid: str, stale_threshold_days: int = 30) -> int:
        """Decaimento em massa para o Background Janitor."""
        return self._logic.bulk_decay_stale_trajectories(project_uuid, stale_threshold_days)

    def search_symbols(self, query: str, project_uuid: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Busca por classes, métodos e funções indexados usando FTS5."""
        safe_query = query.replace('"', '""')
        sql = """
            SELECT n.id, n.label, n.type, n.project_uuid, n.file_hash
            FROM nodes_fts f
            JOIN nodes n ON n.id = f.rowid
            WHERE nodes_fts MATCH ? AND n.type IN ('class', 'function', 'method')
            ORDER BY CASE n.type WHEN 'class' THEN 1 WHEN 'function' THEN 2 WHEN 'method' THEN 3 ELSE 4 END, n.id
        """
        params: list[Any] = [f'"{safe_query}"']
        if project_uuid:
            sql += " AND n.project_uuid = ?"
            params.append(project_uuid)
        sql += " LIMIT ?"
        params.append(limit)
        return self._conn_mgr.execute_raw_read(sql, tuple(params))

    def get_callers(self, symbol_id: int) -> list[dict]:
        """Retorna todos os nós que chamam o símbolo especificado."""
        sql = """
            SELECT n.id, n.label, n.type, n.project_uuid
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ? AND e.relation_type = 'calls'
        """
        return self._conn_mgr.execute_raw_read(sql, (symbol_id,))


    # ===================================================================
    # ENCAPSULAMENTO — API pública para o JanitorService (Patch 2)
    # ===================================================================

    def is_write_queue_empty(self) -> bool:
        """Retorna True se a fila de escrita (SerializedWriteQueue) não tem jobs pendentes.

        Substitui o acesso direto _conn_mgr._write_queue._queue.empty() no Janitor.
        """
        return self._conn_mgr.is_write_queue_empty()

    def execute_read_sql(self, sql: str, params: tuple = ()) -> list[dict]:
        """Executa SQL de leitura arbitrária e retorna lista de dicts.

        Permite que o JanitorService faça queries complexas (WITH RECURSIVE,
        JOIN com FTS5, etc.) sem precisar acessar self._conn_mgr diretamente.

        Args:
            sql: Query SQL de leitura (SELECT / WITH RECURSIVE).
            params: Parâmetros posicionais para a query.

        Returns:
            Lista de dicionários com os resultados.
        """
        return self._conn_mgr.execute_raw_read(sql, params)

    # ===================================================================
    # USER CORE MEMORY — CRUD completo (Patch 1)
    # ===================================================================

    _VALID_SCOPE_TYPES: frozenset[str] = frozenset({"user", "session", "agent", "org"})

    def set_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
        content: str,
    ) -> int:
        """Grava ou atualiza um bloco de memória core do usuário/sessão.

        Usa INSERT OR REPLACE para garantir que block_label seja único por escopo.

        Args:
            scope_type: Tipo de escopo — 'user', 'session', 'agent' ou 'org'.
            scope_id: Identificador do escopo (ex: user UUID, session UUID).
            block_label: Rótulo do bloco de memória (ex: 'preferred_language').
            content: Conteúdo do bloco de memória.

        Returns:
            O id do registro inserido ou substituído.

        Raises:
            ValueError: Se scope_type for inválido ou campos obrigatórios estiverem vazios.
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"scope_type inválido: '{scope_type}'. Aceitos: {sorted(self._VALID_SCOPE_TYPES)}")
        if not scope_id or not scope_id.strip():
            raise ValueError("scope_id não pode ser vazio.")
        if not block_label or not block_label.strip():
            raise ValueError("block_label não pode ser vazio.")

        def _write(conn: "sqlite3.Connection") -> int:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO user_core_memory
                   (scope_type, scope_id, block_label, content, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (scope_type, scope_id.strip(), block_label.strip(), content),
            )
            return cursor.lastrowid

        return self._conn_mgr.write(_write)

    def get_core_memory(
        self,
        scope_type: str,
        scope_id: str,
        block_label: str,
    ) -> Optional[dict]:
        """Retorna um bloco de memória core específico, ou None se não existir.

        Args:
            scope_type: Tipo de escopo.
            scope_id: Identificador do escopo.
            block_label: Rótulo do bloco de memória.

        Returns:
            Dict com as colunas do registro, ou None.
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"scope_type inválido: '{scope_type}'.")
        rows = self._conn_mgr.execute_raw_read(
            """SELECT id, scope_type, scope_id, block_label, content, updated_at
               FROM user_core_memory
               WHERE scope_type = ? AND scope_id = ? AND block_label = ?
               LIMIT 1""",
            (scope_type, scope_id.strip(), block_label.strip()),
        )
        return rows[0] if rows else None

    def list_core_memory_blocks(
        self,
        scope_type: str,
        scope_id: str,
    ) -> list[dict]:
        """Retorna todos os blocos de memória core para um escopo.

        Args:
            scope_type: Tipo de escopo.
            scope_id: Identificador do escopo.

        Returns:
            Lista de dicts (pode ser vazia).
        """
        if scope_type not in self._VALID_SCOPE_TYPES:
            raise ValueError(f"scope_type inválido: '{scope_type}'.")
        return self._conn_mgr.execute_raw_read(
            """SELECT id, scope_type, scope_id, block_label, content, updated_at
               FROM user_core_memory
               WHERE scope_type = ? AND scope_id = ?
               ORDER BY block_label ASC""",
            (scope_type, scope_id.strip()),
        )
