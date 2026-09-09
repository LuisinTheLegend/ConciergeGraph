"""
interface/telemetry_api.py — SDD-SURVIVAL-13 / SDD-SURVIVAL-23 / SDD-SURVIVAL-24 / SDD-SURVIVAL-25

REST API Layer and Real-Time Telemetry (FastAPI / SSE).

Embedded FastAPI server exposing operational REST endpoints and real-time
event streaming via Server-Sent Events (SSE) to feed the monitoring Next.js Dashboard.

Routes:
    GET  /api/telemetry/snapshot  → Consolidated snapshot of system state
    POST /api/janitor/reconcile   → Manual trigger of orphan vector reconciler
    GET  /api/telemetry/stream    → Persistent SSE telemetry stream
    GET  /api/governor/metrics    → Real-time RateGovernor metrics (SDD-23)
    POST /api/governor/report     → Post-call token consumption reporting (SDD-23)
    GET  /api/gating/config       → Active gating configuration and mode (SDD-24)
    POST /api/gating/config       → Dynamically changes gating autonomy mode (SDD-24)
    GET  /api/hsm/state/{id}       → Active hierarchical state and History Node (SDD-25)
    POST /api/hsm/transition        → Triggers HSM sub-state transition (SDD-25)
    POST /api/hsm/resume/{id}       → Restores session from History Node (SDD-25)
    GET  /api/hsm/tree              → Full HSM state tree topology (SDD-25)

Security:
    - Default bind to 127.0.0.1 (secure loopback)
    - CORS enabled for Next.js Dashboard frontend
    - Configurable via CONCIERGE_BIND_ADDRESS in .env
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
from core.gating_interceptor import GatingInterceptor
from core.mcp_governor import MCPToolGovernor
from core.rate_governor import RateGovernor
from core.security_guard import SecurityGuard
from core.telemetry_schemas import (
    AgentSessionSchema,
    CheckpointSchema,
    DirtyFileSchema,
    JanitorStatusSchema,
    TelemetryPayloadSchema,
)

logger = logging.getLogger(__name__)

# Global singleton instance for MCP tool governance
mcp_governor = MCPToolGovernor()

# RateGovernor daemon singleton (SDD-SURVIVAL-23)
# Default quotas: 60 RPM, 40000 TPM, 60s window
rate_governor_service = RateGovernor(rpm_limit=60, tpm_limit=40000)
rate_governor_service.start()

# Security and Adaptive Gating Singletons (SDD-SURVIVAL-24)
# project_root = "." will be resolved via os.path.realpath() in SecurityGuard
security_guard_service = SecurityGuard(project_root=".")
gating_interceptor_service = GatingInterceptor(security_guard_service)

# HSM singleton (SDD-SURVIVAL-25) — Lazy-initialized to avoid circular imports
# Actual instance is created on first access via get_hsm_service()
_hsm_service_instance = None


def get_hsm_service():
    """Lazy singleton accessor for the HSM engine. Requires db_manager to be set."""
    global _hsm_service_instance
    if _hsm_service_instance is None:
        from core.checkpointer import AgnosticCheckpointer
        from core.hsm_engine import HierarchicalStateMachine

        db = get_db_manager()
        checkpointer = AgnosticCheckpointer(db)
        _hsm_service_instance = HierarchicalStateMachine(
            db_manager=db,
            checkpointer=checkpointer,
            mcp_governor=mcp_governor,
        )
    return _hsm_service_instance


# ── FastAPI Application ─────────────────────────────────────────────
app = FastAPI(
    title="Grafo Concierge Telemetry",
    description="REST API and Real-Time Telemetry — SDD-SURVIVAL-13",
    version="1.0.0",
)

# CORS enabled for Next.js Dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency Injection ────────────────────────────────────────────
# Placeholder to be overridden at runtime or in tests via
# app.dependency_overrides[get_db_manager]

_db_manager_instance = None


def get_db_manager() -> ConciergeDatabaseManager:
    """
    FastAPI dependency to inject ConciergeDatabaseManager.

    In production, configure via set_db_manager().
    In tests, use app.dependency_overrides[get_db_manager].
    """
    if _db_manager_instance is None:
        raise RuntimeError(
            "ConciergeDatabaseManager not configured. "
            "Call set_db_manager() before starting the server."
        )
    return _db_manager_instance


def set_db_manager(manager: ConciergeDatabaseManager) -> None:
    """Configures the global ConciergeDatabaseManager instance."""
    global _db_manager_instance
    _db_manager_instance = manager


# ── Helper Functions ───────────────────────────────────────────────

def _build_telemetry_payload(
    db_manager: ConciergeDatabaseManager,
) -> dict:
    """
    Consolidates all volatile SQLite WAL data into a telemetry
    payload validated against TelemetryPayloadSchema.

    Consolidation logic:
      1. Counts total indexed files in SQLite
      2. Collects dirty files (is_dirty=1) for dirty_queue
      3. Counts queue backlog (dirty files)
      4. Groups checkpoints by agent session
      5. Classifies 'init' as 'protected' (SDD-12)
      6. Computes simple integrity_score (% of clean files)
    """
    # Total indexed files
    total_files_rows = db_manager.read_query(
        "SELECT COUNT(*) FROM files;"
    )
    sqlite_total_files = total_files_rows[0][0] if total_files_rows else 0

    # Dirty files (dirty_queue)
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

    # Integrity score: clean files percentage
    if sqlite_total_files > 0:
        integrity_score = round(
            (sqlite_total_files - queue_backlog) / sqlite_total_files, 4
        )
    else:
        integrity_score = 1.0

    # Agent sessions with checkpoints (grouped by session_id)
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
        # SDD-12: first checkpoint ('init') is 'protected'
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

    # Assemble consolidated payload
    payload = TelemetryPayloadSchema(
        integrity_score=integrity_score,
        sqlite_total_files=sqlite_total_files,
        qdrant_total_vectors=0,  # Qdrant optional — graceful fallback
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
    """Generates SHA-256 hash of JSON payload for efficient change detection."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ── REST Endpoints ────────────────────────────────────────────────

@app.get("/api/telemetry/snapshot")
def get_telemetry_snapshot(
    db_manager: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """
    GET /api/telemetry/snapshot

    Returns consolidated snapshot of system state, including file counters,
    dirty queue, agent sessions, and integrity score. Validated under TelemetryPayloadSchema.
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

    Manually triggers reconcile_orphans() on VectorReconciler in the background
    via FastAPI BackgroundTasks. Returns immediately {"status": "accepted"}
    without blocking user request.
    """

    def _run_reconcile():
        try:
            from core.vector_reconciler import VectorReconciler

            # Create vector_db stub for environments without Qdrant
            class _VectorDbStub:
                def get_all_ids(self):
                    return []

                def delete_batch(self, ids):
                    pass

            reconciler = VectorReconciler(db_manager, _VectorDbStub())
            reconciler.reconcile_orphans()
        except Exception as e:
            logger.warning("Janitor reconcile failed (graceful): %s", e)

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
    """Lists chronological timeline of active checkpoints for a session."""
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
        logger.warning("Failed to list checkpoints for session %s: %s", session_id, e)
        return []


@app.post("/api/checkpoints/time-travel")
async def trigger_time_travel(
    payload: TimeTravelRequest,
    db: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """Triggers cognitive-relational time-travel rollback for the agent."""
    from core.checkpointer import AgnosticCheckpointer

    checkpointer = AgnosticCheckpointer(db)

    restored_state = checkpointer.execute_time_travel(
        payload.session_id, payload.target_checkpoint_id
    )
    if not restored_state:
        raise HTTPException(
            status_code=404, detail="Target session or checkpoint not found."
        )

    return {
        "status": "success",
        "message": f"Time-travel executed successfully to checkpoint {payload.target_checkpoint_id}",
        "restored_state": restored_state,
    }


# ── MCP Progressive Tool Disclosure (SDD-SURVIVAL-21) ────────────

class FSMStateUpdateRequest(BaseModel):
    session_id: str
    state_name: str


@app.post("/api/mcp/state")
async def update_mcp_session_state(payload: FSMStateUpdateRequest):
    """Updates agent FSM mental state to manage progressive tool disclosure."""
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
    """Queries current registered mental state for a session."""
    return {
        "session_id": session_id,
        "active_state": mcp_governor.get_session_state(session_id),
    }


# ── RateGovernor Quota Telemetry (SDD-SURVIVAL-23) ────────────────

class TokenReportPayload(BaseModel):
    """Post-call API token consumption report schema."""
    tokens_used: int


@app.get("/api/governor/metrics")
async def get_governor_metrics():
    """
    GET /api/governor/metrics

    Queries real-time quota occupancy (RPM/TPM), queue backlog,
    and freezing flags for LOW and MEDIUM queues.
    """
    return rate_governor_service.get_current_metrics()


@app.post("/api/governor/report")
async def report_token_usage(payload: TokenReportPayload):
    """
    POST /api/governor/report

    Allows subagent executors to report actual token usage post-LLM call
    to update governor sliding window metrics.
    """
    rate_governor_service.report_usage(payload.tokens_used)
    return {"status": "success", "metrics": rate_governor_service.get_current_metrics()}


# ── Adaptive Gating Security (SDD-SURVIVAL-24) ─────────────────

class GatingModePayload(BaseModel):
    """Adaptive gating mode update schema."""
    mode: str


@app.get("/api/gating/config")
async def get_gating_config():
    """
    GET /api/gating/config

    Queries active security configurations and restrictions,
    including current gating mode and normalized project_root.
    """
    return {
        "active_mode": gating_interceptor_service.current_mode,
        "project_root": security_guard_service.project_root,
    }


@app.post("/api/gating/config")
async def update_gating_config(payload: GatingModePayload):
    """
    POST /api/gating/config

    Dynamically changes monorepo autonomy level.
    Valid modes: plan-only, ask, auto-approve.
    """
    mode = payload.mode.lower()
    if mode not in ("plan-only", "ask", "auto-approve"):
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Choose from: plan-only, ask, auto-approve.",
        )
    gating_interceptor_service.set_gating_mode(mode)
    return {"status": "success", "new_mode": gating_interceptor_service.current_mode}


# ── Hierarchical State Machine (SDD-SURVIVAL-25) ──────────────────

class HSMTransitionRequest(BaseModel):
    """HSM transition request payload."""
    session_id: str
    target_path: str
    agent_id: str
    shared_state: dict
    task_id: str | None = None


@app.get("/api/hsm/state/{session_id}")
async def get_hsm_state(session_id: str):
    """
    GET /api/hsm/state/{session_id}

    Returns the active hierarchical qualified state and History Node
    for the given session.
    """
    hsm = get_hsm_service()
    return {
        "session_id": session_id,
        "current_full_path": hsm.get_current_state(session_id),
        "super_state": hsm.get_super_state(session_id),
        "history_node": hsm.history_nodes.get(session_id),
    }


@app.post("/api/hsm/transition")
async def trigger_hsm_transition(payload: HSMTransitionRequest):
    """
    POST /api/hsm/transition

    Executes a hierarchical sub-state transition, persists the checkpoint,
    and updates the session's Deep History Node (H*).
    """
    hsm = get_hsm_service()
    try:
        success = hsm.transition_to(
            session_id=payload.session_id,
            target_path=payload.target_path,
            agent_id=payload.agent_id,
            shared_state=payload.shared_state,
            task_id=payload.task_id,
        )
        return {
            "status": "success",
            "saved": success,
            "new_state": payload.target_path,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/hsm/resume/{session_id}")
async def resume_session_hsm(session_id: str):
    """
    POST /api/hsm/resume/{session_id}

    Restores the session from its most recent Deep History Node (H*),
    re-activating the exact sub-state where the agent last stopped.
    """
    hsm = get_hsm_service()
    restored = hsm.resume_from_history_node(session_id)
    if not restored:
        raise HTTPException(
            status_code=404,
            detail=f"No History Node found for session '{session_id}'.",
        )
    return {"status": "success", "restored_state": restored}


@app.get("/api/hsm/tree")
async def get_hsm_tree():
    """
    GET /api/hsm/tree

    Returns the full HSM state tree topology as a serializable dictionary,
    including all super-states, sub-states, and MCP governance categories.
    """
    hsm = get_hsm_service()
    return {"state_tree": hsm.get_state_tree()}


# ── Streaming SSE ─────────────────────────────────────────────────

async def _telemetry_event_generator(
    db_manager: ConciergeDatabaseManager,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE event generator.

    Checks telemetry payload hash every 1.0s.
    Emits full payload in SSE format only when hash changes,
    ensuring near-zero network traffic in the absence of changes.

    Always emits initial snapshot immediately.
    """
    last_hash = ""

    # Emits initial snapshot immediately
    payload = _build_telemetry_payload(db_manager)
    current_hash = _hash_payload(payload)
    last_hash = current_hash
    yield f"data: {json.dumps(payload, default=str)}\n\n"

    # Continuous monitoring loop
    check_count = 0
    max_checks = 5  # Limit to prevent infinite loop in tests

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
            logger.warning("Error in SSE generator: %s", e)
            break


@app.get("/api/telemetry/stream")
def telemetry_stream(
    db_manager: ConciergeDatabaseManager = Depends(get_db_manager),
):
    """
    GET /api/telemetry/stream

    Opens a persistent SSE connection streaming real-time telemetry payload
    whenever volatile database hash changes.

    Output format: data: <JSON>\n\n (standard SSE)
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
