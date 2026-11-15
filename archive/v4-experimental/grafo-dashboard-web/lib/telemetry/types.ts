/**
 * lib/telemetry/types.ts — SDD-SURVIVAL-16
 *
 * Contratos TypeScript espelhando rigorosamente os modelos Pydantic v2
 * do backend (core/telemetry_schemas.py). Fonte única de verdade para
 * todos os dados de telemetria consumidos pelo Dashboard.
 *
 * Hierarquia:
 *   DirtyFile              → Arquivo marcado is_dirty=1 aguardando re-sumarização
 *   SelfHealingEvent       → Evento de auto-cura do reconciliador de vetores
 *   JanitorStatus          → Estado operacional do BackgroundJanitor
 *   Checkpoint             → Checkpoint de agente (SDD-12: init → protected)
 *   AgentSession           → Sessão com sua linha do tempo de checkpoints
 *   TelemetryPayload       → Payload consolidado final do stream SSE
 */

// ─── Dirty Queue ────────────────────────────────────────────────────────────

export interface DirtyFile {
  /** Caminho relativo do arquivo no projeto */
  path: string;
  /** ID da comunidade/grafo a que pertence */
  community_id: string;
  /** Timestamp ISO 8601 UTC da última modificação */
  last_modified: string;
}

// ─── Self-Healing Events ────────────────────────────────────────────────────

export interface SelfHealingEvent {
  /** Timestamp ISO 8601 UTC do evento */
  timestamp: string;
  /** Tipo do evento de auto-cura (ex: QUERY_TIME_FILTER) */
  event_type: string;
  /** ID do vetor órfão interceptado */
  orphan_id: string;
  /** Contexto descritivo do evento */
  context: string;
}

// ─── Janitor Status ─────────────────────────────────────────────────────────

export interface JanitorStatus {
  /** Se o Janitor está executando agora */
  is_running: boolean;
  /** Timestamp ISO 8601 UTC da última execução (null se nunca executou) */
  last_run: string | null;
  /** Timestamp ISO 8601 UTC da próxima execução agendada */
  next_scheduled_run: string;
}

// ─── Agent Checkpoints (SDD-12 / SDD-13) ────────────────────────────────────

export type CheckpointStatus = "protected" | "active" | "pruned_by_lru";

export interface Checkpoint {
  /** Identificador do checkpoint (ex: "init", "step-3") */
  id: string;
  /** Timestamp ISO 8601 UTC de criação */
  timestamp: string;
  /** Status de retenção: protected (init), active, ou pruned_by_lru */
  status: CheckpointStatus;
}

export interface AgentSession {
  /** ID único da sessão */
  session_id: string;
  /** ID do agente que originou a sessão */
  agent_id: string;
  /** Lista ordenada de checkpoints da sessão */
  checkpoints: Checkpoint[];
}

// ─── Telemetry Payload (Consolidado) ────────────────────────────────────────

export interface TelemetryPayload {
  /** Score de integridade (0.0 a 1.0) — percentual de arquivos limpos */
  integrity_score: number;
  /** Total de arquivos indexados no SQLite (WAL) */
  sqlite_total_files: number;
  /** Total de vetores no Qdrant/ChromaDB */
  qdrant_total_vectors: number;
  /** Quantidade de vetores órfãos detectados */
  orphans_detected: number;
  /** IP Tailscale do host (null se não configurado) */
  tailscale_ip: string | null;
  /** Tamanho atual da fila de arquivos sujos */
  queue_backlog: number;
  /** Lista de arquivos aguardando re-sumarização */
  dirty_queue: DirtyFile[];
  /** Eventos de auto-cura registrados pelo reconciliador */
  self_healing_events: SelfHealingEvent[];
  /** Estado operacional do BackgroundJanitor */
  janitor_status: JanitorStatus;
  /** Sessões de agentes com seus checkpoints */
  agent_sessions: AgentSession[];
}

// ─── Connection Status ──────────────────────────────────────────────────────

export type TelemetryConnectionStatus =
  | "connecting"
  | "streaming"
  | "disconnected"
  | "error";

// ─── SDD-28: Rate Governor Quota Metrics ───────────────────────────────────

export interface GovernorMetrics {
  current_rpm: number;
  current_tpm: number;
  rpm_percentage: number;
  tpm_percentage: number;
  low_priority_frozen: boolean;
  medium_priority_frozen: boolean;
  max_rpm?: number;
  max_tpm?: number;
}

// ─── SDD-28: HSM State & History Node ──────────────────────────────────────

export interface HistoryNodeInfo {
  state_path: string;
  checkpoint_id: string;
  timestamp: number | string;
}

export interface HSMSessionState {
  session_id: string;
  current_full_path: string;
  super_state: string;
  active_substate: string;
  category: "READ_ONLY" | "LOCAL_MUTATION" | "DANGEROUS" | string;
  history_node: HistoryNodeInfo | null;
  turn_count: number;
  max_turns: number;
  state_tree?: Record<string, any>;
}

// ─── SDD-28: Live Event Stream Item ────────────────────────────────────────

export type EventCategoryBadge = "WAL" | "JANITOR" | "DELTA" | "HSM" | "GATING" | "MCP" | "SYSTEM";

export interface LiveTelemetryEvent {
  id: string;
  timestamp: string; // ISO 8601 UTC
  badge: EventCategoryBadge;
  message: string;
  level?: "info" | "warning" | "error" | "success";
  metadata?: Record<string, any>;
}

// ─── SDD-28: Consolidated Cockpit State ────────────────────────────────────

export interface CockpitTelemetryData {
  metrics: GovernorMetrics;
  hsm: HSMSessionState;
  events: LiveTelemetryEvent[];
  dirtyQueue: DirtyFile[];
  integrityScore: number;
  sqliteTotalFiles: number;
  janitorStatus: JanitorStatus;
}
