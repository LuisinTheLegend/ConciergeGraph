"""
core/telemetry_schemas.py — SDD-SURVIVAL-13

Typed Data Schemas for Real-Time Telemetry.

Defines Pydantic v2 payload structures consumed by the Next.js Dashboard
via REST (snapshots) and SSE (streaming). Each schema maps directly to
a data domain within the local-first Concierge Graph ecosystem.

Schema Hierarchy:
    DirtyFileSchema          -> File flagged as dirty (is_dirty=1)
    SelfHealingEventSchema   -> Orphan reconciler self-healing event
    JanitorStatusSchema      -> Operational state of BackgroundJanitor
    CheckpointSchema         -> Agent checkpoint (SDD-12: 'init' -> 'protected')
    AgentSessionSchema       -> Agent session with checkpoint timeline
    TelemetryPayloadSchema   -> Consolidated telemetry payload for dashboard
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DirtyFileSchema(BaseModel):
    """File flagged as dirty (is_dirty=1) awaiting re-summarization."""
    path: str
    community_id: str
    last_modified: datetime


class SelfHealingEventSchema(BaseModel):
    """Self-healing event triggered by orphan vector reconciler."""
    timestamp: datetime
    event_type: str = "QUERY_TIME_FILTER"
    orphan_id: str
    context: str


class JanitorStatusSchema(BaseModel):
    """Operational state of BackgroundJanitor (SDD-06 / SDD-12)."""
    is_running: bool
    last_run: Optional[datetime] = None
    next_scheduled_run: datetime


class CheckpointSchema(BaseModel):
    """
    Agent checkpoint with status classification.

    Per SDD-12, the initial checkpoint of each session ('init')
    is classified as 'protected' (immutable point zero). Subsequent
    checkpoints receive 'active' or 'pruned_by_lru'.
    """
    id: str
    timestamp: datetime
    status: str  # "protected", "active", "pruned_by_lru"


class AgentSessionSchema(BaseModel):
    """Agent session with its checkpoint timeline."""
    session_id: str
    agent_id: str
    checkpoints: List[CheckpointSchema]


class TelemetryPayloadSchema(BaseModel):
    """
    Consolidated telemetry payload for Next.js Dashboard.

    Aggregates local-first health metrics: file counts, vector counts,
    dirty queue, self-healing events, Janitor status, and active agent sessions.
    """
    integrity_score: float
    sqlite_total_files: int
    qdrant_total_vectors: int
    orphans_detected: int
    tailscale_ip: Optional[str] = None
    queue_backlog: int
    dirty_queue: List[DirtyFileSchema]
    self_healing_events: List[SelfHealingEventSchema]
    janitor_status: JanitorStatusSchema
    agent_sessions: List[AgentSessionSchema]
