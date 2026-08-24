"""
core/telemetry_schemas.py — SDD-SURVIVAL-13

Esquemas de Dados Tipados para Telemetria em Tempo Real.

Define a estrutura rígida de payloads Pydantic v2 que o Dashboard Next.js
consumirá via REST (snapshot) e SSE (streaming). Cada classe mapeia
diretamente um domínio de dados do ecossistema local-first do Grafo Concierge.

Hierarquia de Schemas:
    DirtyFileSchema          → Arquivo marcado como sujo (is_dirty=1)
    SelfHealingEventSchema   → Evento de auto-cura do reconciliador
    JanitorStatusSchema      → Estado operacional do BackgroundJanitor
    CheckpointSchema         → Checkpoint de agente (SDD-12: 'init' → 'protected')
    AgentSessionSchema       → Sessão de agente com linha do tempo de checkpoints
    TelemetryPayloadSchema   → Payload consolidado final para o Dashboard
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DirtyFileSchema(BaseModel):
    """Arquivo marcado como sujo (is_dirty=1) aguardando re-sumarização."""
    path: str
    community_id: str
    last_modified: datetime


class SelfHealingEventSchema(BaseModel):
    """Evento de auto-cura disparado pelo reconciliador de vetores órfãos."""
    timestamp: datetime
    event_type: str = "QUERY_TIME_FILTER"
    orphan_id: str
    context: str


class JanitorStatusSchema(BaseModel):
    """Estado operacional do BackgroundJanitor (SDD-06 / SDD-12)."""
    is_running: bool
    last_run: Optional[datetime] = None
    next_scheduled_run: datetime


class CheckpointSchema(BaseModel):
    """
    Checkpoint de agente com classificação de status.

    Conforme o SDD-12, o primeiro checkpoint de cada sessão ('init')
    é classificado como 'protected' (ponto zero imutável). Os demais
    recebem status 'active' ou 'pruned_by_lru'.
    """
    id: str
    timestamp: datetime
    status: str  # "protected", "active", "pruned_by_lru"


class AgentSessionSchema(BaseModel):
    """Sessão de agente com sua linha do tempo de checkpoints."""
    session_id: str
    agent_id: str
    checkpoints: List[CheckpointSchema]


class TelemetryPayloadSchema(BaseModel):
    """
    Payload consolidado final para o Dashboard Next.js.

    Agrega todos os indicadores de saúde do ecossistema local-first:
    contadores de arquivos, vetores, fila suja, eventos de auto-cura,
    status do Janitor e sessões de agentes ativos.
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
