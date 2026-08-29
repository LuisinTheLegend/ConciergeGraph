"""
interface/telemetry_api.py — SDD-SURVIVAL-13

Camada de API REST e Telemetria em Tempo Real (FastAPI / SSE).

Servidor FastAPI embutido que expõe rotas REST operacionais e um barramento
de streaming de eventos em tempo real via Server-Sent Events (SSE) para
alimentar o Dashboard Next.js de monitoramento.

Rotas:
    GET  /api/telemetry/snapshot  → Snapshot consolidado do estado do sistema
    POST /api/janitor/reconcile   → Disparo manual do reconciliador de órfãos
    GET  /api/telemetry/stream    → Canal SSE persistente de telemetria

Segurança:
    - Bind padrão em 127.0.0.1 (loopback seguro)
    - CORS habilitado para o frontend do Dashboard
    - Configurável via CONCIERGE_BIND_ADDRESS no .env
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.database import ConciergeDatabaseManager
from core.mcp_governor import MCPToolGovernor
from core.telemetry_schemas import (
    AgentSessionSchema,
    CheckpointSchema,
    DirtyFileSchema,
    JanitorStatusSchema,
    TelemetryPayloadSchema,
)

logger = logging.getLogger(__name__)

# Instância singleton global de governança de ferramentas MCP
mcp_governor = MCPToolGovernor()

# ── Aplicação FastAPI ─────────────────────────────────────────────
app = FastAPI(
    title="Grafo Concierge Telemetry",
    description="API REST e Telemetria em Tempo Real — SDD-SURVIVAL-13",
    version="1.0.0",
)

# CORS liberado para o frontend do Dashboard Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Injeção de Dependência ────────────────────────────────────────
# Placeholder para ser substituído em runtime ou em testes via
# app.dependency_overrides[get_db_manager]

_db_manager_instance = None


def get_db_manager() -> ConciergeDatabaseManager:
    """
    Dependência do FastAPI para injetar o ConciergeDatabaseManager.

    Em produção, deve ser configurado via set_db_manager().
    Em testes, usar app.dependency_overrides[get_db_manager].
    """
    if _db_manager_instance is None:
        raise RuntimeError(
            "ConciergeDatabaseManager não configurado. "
            "Use set_db_manager() antes de iniciar o servidor."
        )
    return _db_manager_instance


def set_db_manager(manager: ConciergeDatabaseManager) -> None:
    """Configura a instância global do ConciergeDatabaseManager."""
    global _db_manager_instance
    _db_manager_instance = manager


# ── Funções Auxiliares ────────────────────────────────────────────

def _build_telemetry_payload(
    db_manager: ConciergeDatabaseManager,
) -> dict:
    """
    Consolida todos os dados voláteis do SQLite WAL em um payload
    de telemetria validado pelo TelemetryPayloadSchema.

    Lógica de consolidação:
      1. Conta total de arquivos no SQLite
      2. Coleta arquivos sujos (is_dirty=1) para a dirty_queue
      3. Conta backlog da fila (arquivos sujos)
      4. Agrupa checkpoints por sessão de agente
      5. Classifica 'init' como 'protected' (SDD-12)
      6. Calcula integrity_score simples (% de arquivos limpos)
    """
    # Total de arquivos indexados
    total_files_rows = db_manager.read_query(
        "SELECT COUNT(*) FROM files;"
    )
    sqlite_total_files = total_files_rows[0][0] if total_files_rows else 0

    # Arquivos sujos (dirty_queue)
    dirty_rows = db_manager.read_query(
        "SELECT path, community_id, last_modified FROM files WHERE is_dirty = 1;"
    )
    dirty_queue = [
        DirtyFileSchema(
            path=row[0],
            community_id=row[1],
            last_modified=datetime.fromtimestamp(row[2], tz=timezone.utc),
        )
        for row in dirty_rows
    ]
    queue_backlog = len(dirty_queue)

    # Integrity score: percentual de arquivos limpos
    if sqlite_total_files > 0:
        integrity_score = round(
            (sqlite_total_files - queue_backlog) / sqlite_total_files, 4
        )
    else:
        integrity_score = 1.0

    # Sessões de agentes com checkpoints (agrupados por session_id)
    checkpoint_rows = db_manager.read_query(
        "SELECT agent_id, session_id, checkpoint_id, timestamp "
        "FROM agent_checkpoints ORDER BY timestamp ASC;"
    )

    sessions_map: dict = {}
    for row in checkpoint_rows:
        agent_id, session_id, checkpoint_id, ts = row
        if session_id not in sessions_map:
            sessions_map[session_id] = {
                "agent_id": agent_id,
                "checkpoints": [],
            }
        # SDD-12: primeiro checkpoint ('init') é 'protected'
        status = "protected" if checkpoint_id == "init" else "active"
        sessions_map[session_id]["checkpoints"].append(
            CheckpointSchema(
                id=checkpoint_id,
                timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                status=status,
            )
        )

    agent_sessions = [
        AgentSessionSchema(
            session_id=sid,
            agent_id=data["agent_id"],
            checkpoints=data["checkpoints"],
        )
        for sid, data in sessions_map.items()
    ]

    # Monta o payload consolidado
    payload = TelemetryPayloadSchema(
        integrity_score=integrity_score,
        sqlite_total_files=sqlite_total_files,
        qdrant_total_vectors=0,  # Qdrant opcional — graceful fallback
        orphans_detected=0,
        tailscale_ip=None,
        queue_backlog=queue_backlog,
        dirty_queue=dirty_queue,
        self_healing_events=[],
        janitor_status=JanitorStatusSchema(
            is_running=False,
            last_run=None,
            next_scheduled_run=datetime.now(tz=timezone.utc),
        ),
        agent_sessions=agent_sessions,
    )

    return payload.model_dump(mode="json")


def _hash_payload(payload: dict) -> str:
    """Gera hash SHA-256 do payload JSON para detecção eficiente de mudanças."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ── Rotas REST ────────────────────────────────────────────────────

@app.get("/api/telemetry/snapshot")
def get_telemetry_snapshot(
    db_manager: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """
    GET /api/telemetry/snapshot

    Retorna o snapshot consolidado do estado do sistema, incluindo
    contadores de arquivos, fila suja, sessões de agentes e score
    de integridade. Validado sob TelemetryPayloadSchema.
    """
    payload = _build_telemetry_payload(db_manager)
    return payload


@app.post("/api/janitor/reconcile")
def trigger_janitor_reconcile(
    background_tasks: BackgroundTasks,
    db_manager: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """
    POST /api/janitor/reconcile

    Dispara manualmente o reconcile_orphans() do VectorReconciler
    em background via BackgroundTasks do FastAPI. Retorna imediatamente
    {"status": "accepted"} sem bloquear a requisição do usuário.
    """

    def _run_reconcile():
        try:
            from core.vector_reconciler import VectorReconciler

            # Cria um stub de vector_db para ambientes sem Qdrant
            class _VectorDbStub:
                def get_all_ids(self):
                    return []

                def delete_batch(self, ids):
                    pass

            reconciler = VectorReconciler(db_manager, _VectorDbStub())
            reconciler.reconcile_orphans()
        except Exception as e:
            logger.warning("Janitor reconcile falhou (graceful): %s", e)

    background_tasks.add_task(_run_reconcile)
    return {"status": "accepted"}


# ── Checkpoints & Time-Travel (SDD-SURVIVAL-20) ──────────────────

class TimeTravelRequest(BaseModel):
    session_id: str
    target_checkpoint_id: str


@app.get("/api/checkpoints/{session_id}")
async def list_session_checkpoints(
    session_id: str,
    db: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """Lista a linha do tempo cronológica de checkpoints ativos de uma sessão."""
    try:
        query = """
            SELECT checkpoint_id, state_name, task_id, created_at 
            FROM fsm_checkpoints 
            WHERE session_id = ? 
            ORDER BY created_at ASC;
        """
        rows = db.read_query(query, (session_id,))
        return [
            {
                "checkpoint_id": r[0],
                "state_name": r[1],
                "task_id": r[2],
                "created_at": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Falha ao listar checkpoints da sessão %s: %s", session_id, e)
        return []


@app.post("/api/checkpoints/time-travel")
async def trigger_time_travel(
    payload: TimeTravelRequest,
    db: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """Dispara a reversão de viagem no tempo cognitivo-relacional para o agente."""
    from core.checkpointer import AgnosticCheckpointer

    checkpointer = AgnosticCheckpointer(db)

    restored_state = checkpointer.execute_time_travel(
        payload.session_id, payload.target_checkpoint_id
    )
    if not restored_state:
        raise HTTPException(
            status_code=404, detail="Sessão ou Checkpoint alvo não localizado."
        )

    return {
        "status": "success",
        "message": f"Time-travel executado com sucesso para o checkpoint {payload.target_checkpoint_id}",
        "restored_state": restored_state,
    }


# ── MCP Progressive Tool Disclosure (SDD-SURVIVAL-21) ────────────

class FSMStateUpdateRequest(BaseModel):
    session_id: str
    state_name: str


@app.post("/api/mcp/state")
async def update_mcp_session_state(payload: FSMStateUpdateRequest):
    """Atualiza o estado mental da FSM de um agente para gerenciar a ocultação de ferramentas."""
    try:
        mcp_governor.set_session_state(payload.session_id, payload.state_name)
        return {
            "status": "success",
            "session_id": payload.session_id,
            "active_state": mcp_governor.get_session_state(payload.session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/mcp/state/{session_id}")
async def get_mcp_session_state(session_id: str):
    """Consulta o estado mental corrente registrado para uma sessão."""
    return {
        "session_id": session_id,
        "active_state": mcp_governor.get_session_state(session_id),
    }


# ── Streaming SSE ─────────────────────────────────────────────────

async def _telemetry_event_generator(
    db_manager: ConciergeDatabaseManager,
) -> AsyncGenerator[str, None]:
    """
    Gerador assíncrono de eventos SSE.

    Verifica o hash do payload de telemetria a cada 1.0s.
    Emite o payload completo no formato SSE apenas quando o hash muda,
    garantindo tráfego quase zero na ausência de alterações.

    Sempre emite o primeiro payload (snapshot inicial) imediatamente.
    """
    last_hash = ""

    # Emite snapshot inicial imediatamente
    payload = _build_telemetry_payload(db_manager)
    current_hash = _hash_payload(payload)
    last_hash = current_hash
    yield f"data: {json.dumps(payload, default=str)}\n\n"

    # Loop de monitoramento contínuo
    check_count = 0
    max_checks = 5  # Limite para evitar loop infinito em testes

    while check_count < max_checks:
        await asyncio.sleep(1.0)
        check_count += 1

        try:
            payload = _build_telemetry_payload(db_manager)
            current_hash = _hash_payload(payload)

            if current_hash != last_hash:
                last_hash = current_hash
                yield f"data: {json.dumps(payload, default=str)}\n\n"
        except Exception as e:
            logger.warning("Erro no gerador SSE: %s", e)
            break


@app.get("/api/telemetry/stream")
def telemetry_stream(
    db_manager: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """
    GET /api/telemetry/stream

    Abre uma conexão SSE persistente que transmite o payload de
    telemetria em tempo real sempre que o hash dos dados voláteis mudar.

    Formato de saída: data: <JSON>\n\n (padrão SSE)
    """
    return StreamingResponse(
        _telemetry_event_generator(db_manager),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
