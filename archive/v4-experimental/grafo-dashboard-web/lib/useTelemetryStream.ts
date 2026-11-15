"use client";

/**
 * lib/useTelemetryStream.ts — SDD-SURVIVAL-28
 *
 * Reactive Telemetry Streaming Hook (FastAPI SSE + REST Hydration).
 *
 * Responsibilities:
 * - Persistent SSE connection to `/api/telemetry/stream` (sub-second passive updates).
 * - Initial REST hydration from `/api/telemetry/snapshot`, `/api/governor/metrics`, and `/api/hsm/tree`.
 * - Resilient auto-reconnect with exponential/fixed backoff.
 * - Reactive state dispatch for Quota Gauges, HSM State, Live Event Logs, and Dirty Queue.
 * - Zero network polling when SSE is active.
 */

import { useEffect, useState, useRef, useCallback } from "react";
import type {
  TelemetryPayload,
  TelemetryConnectionStatus,
  GovernorMetrics,
  HSMSessionState,
  LiveTelemetryEvent,
  EventCategoryBadge,
  DirtyFile,
  JanitorStatus,
} from "./telemetry/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_CONCIERGE_API_URL || "http://127.0.0.1:8000";

const DEFAULT_METRICS: GovernorMetrics = {
  current_rpm: 0,
  current_tpm: 0,
  rpm_percentage: 0,
  tpm_percentage: 0,
  low_priority_frozen: false,
  medium_priority_frozen: false,
  max_rpm: 60,
  max_tpm: 40000,
};

const DEFAULT_HSM: HSMSessionState = {
  session_id: "default",
  current_full_path: "PLANNING.DISCOVERY",
  super_state: "PLANNING",
  active_substate: "DISCOVERY",
  category: "READ_ONLY",
  history_node: null,
  turn_count: 0,
  max_turns: 5,
};

const DEFAULT_JANITOR: JanitorStatus = {
  is_running: false,
  last_run: null,
  next_scheduled_run: new Date().toISOString(),
};

export function useTelemetryStream() {
  const [status, setStatus] = useState<TelemetryConnectionStatus>("connecting");
  const [error, setError] = useState<string | null>(null);

  // Core reactive states
  const [metrics, setMetrics] = useState<GovernorMetrics>(DEFAULT_METRICS);
  const [hsmState, setHsmState] = useState<HSMSessionState>(DEFAULT_HSM);
  const [dirtyQueue, setDirtyQueue] = useState<DirtyFile[]>([]);
  const [integrityScore, setIntegrityScore] = useState<number>(1.0);
  const [sqliteTotalFiles, setSqliteTotalFiles] = useState<number>(0);
  const [janitorStatus, setJanitorStatus] = useState<JanitorStatus>(DEFAULT_JANITOR);
  const [telemetryPayload, setTelemetryPayload] = useState<TelemetryPayload | null>(null);
  const [events, setEvents] = useState<LiveTelemetryEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Helper to push a new event into the event feed buffer (max 200 items)
  const addEvent = useCallback(
    (
      badge: EventCategoryBadge,
      message: string,
      level: "info" | "warning" | "error" | "success" = "info",
      metadata?: Record<string, any>
    ) => {
      const newEvent: LiveTelemetryEvent = {
        id: `ev_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        timestamp: new Date().toISOString(),
        badge,
        message,
        level,
        metadata,
      };
      setEvents((prev) => [newEvent, ...prev.slice(0, 199)]);
    },
    []
  );

  // 1. Initial REST Hydration (Fast boot)
  const hydrateRest = useCallback(async () => {
    try {
      // Fetch telemetry snapshot
      const snapshotRes = await fetch(`${API_BASE_URL}/api/telemetry/snapshot`).catch(() => null);
      if (snapshotRes && snapshotRes.ok) {
        const snap: TelemetryPayload = await snapshotRes.json();
        setTelemetryPayload(snap);
        setDirtyQueue(snap.dirty_queue || []);
        setIntegrityScore(snap.integrity_score ?? 1.0);
        setSqliteTotalFiles(snap.sqlite_total_files ?? 0);
        if (snap.janitor_status) setJanitorStatus(snap.janitor_status);

        // Convert self-healing events if available
        if (snap.self_healing_events && snap.self_healing_events.length > 0) {
          const mappedEvents: LiveTelemetryEvent[] = snap.self_healing_events.map((e, idx) => ({
            id: `sh_${idx}_${e.timestamp}`,
            timestamp: e.timestamp,
            badge: "JANITOR",
            message: `[Self-Healing] ${e.event_type} - Orphan ${e.orphan_id}: ${e.context}`,
            level: "info",
          }));
          setEvents((prev) => {
            const existingIds = new Set(prev.map((p) => p.id));
            const newOnes = mappedEvents.filter((m) => !existingIds.has(m.id));
            return [...newOnes, ...prev].slice(0, 200);
          });
        }
      }

      // Fetch Governor Metrics
      const govRes = await fetch(`${API_BASE_URL}/api/governor/metrics`).catch(() => null);
      if (govRes && govRes.ok) {
        const govData = await govRes.json();
        setMetrics({
          current_rpm: govData.current_rpm ?? 0,
          current_tpm: govData.current_tpm ?? 0,
          rpm_percentage: govData.rpm_percentage ?? 0,
          tpm_percentage: govData.tpm_percentage ?? 0,
          low_priority_frozen: !!govData.low_priority_frozen,
          medium_priority_frozen: !!govData.medium_priority_frozen,
          max_rpm: govData.max_rpm ?? 60,
          max_tpm: govData.max_tpm ?? 40000,
        });
      }

      // Fetch HSM Tree / State
      const hsmTreeRes = await fetch(`${API_BASE_URL}/api/hsm/tree`).catch(() => null);
      const hsmStateRes = await fetch(`${API_BASE_URL}/api/hsm/state/default`).catch(() => null);

      let treeData = null;
      if (hsmTreeRes && hsmTreeRes.ok) {
        const treeJson = await hsmTreeRes.json();
        treeData = treeJson.state_tree;
      }

      if (hsmStateRes && hsmStateRes.ok) {
        const stateJson = await hsmStateRes.json();
        const fullPath = stateJson.current_full_path || "PLANNING.DISCOVERY";
        const parts = fullPath.split(".");
        const superState = parts[0] || "PLANNING";
        const subState = parts[1] || parts[0];

        let historyNodeInfo = null;
        if (stateJson.history_node) {
          historyNodeInfo = {
            state_path: stateJson.history_node[0],
            checkpoint_id: stateJson.history_node[1],
            timestamp: stateJson.history_node[2],
          };
        }

        setHsmState({
          session_id: stateJson.session_id || "default",
          current_full_path: fullPath,
          super_state: superState,
          active_substate: subState,
          category: superState === "MAINTENANCE" ? "DANGEROUS" : superState === "EXECUTION" ? "LOCAL_MUTATION" : "READ_ONLY",
          history_node: historyNodeInfo,
          turn_count: 0,
          max_turns: 5,
          state_tree: treeData,
        });
      } else if (treeData) {
        setHsmState((prev) => ({ ...prev, state_tree: treeData }));
      }
    } catch (err) {
      console.warn("[Telemetry] REST hydration warning (FastAPI backend may be starting):", err);
    }
  }, []);

  // 2. Persistent SSE Connection
  useEffect(() => {
    let isMounted = true;
    hydrateRest();

    const connectSSE = () => {
      if (!isMounted) return;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      setStatus("connecting");

      try {
        const es = new EventSource(`${API_BASE_URL}/api/telemetry/stream`);
        eventSourceRef.current = es;

        es.onopen = () => {
          if (!isMounted) return;
          setStatus("streaming");
          setError(null);
          addEvent("SYSTEM", "Connected to FastAPI Telemetry SSE Stream", "success");
        };

        es.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const raw = JSON.parse(event.data);

            // Check if message is a typed telemetry event
            if (raw.event_type) {
              switch (raw.event_type) {
                case "RATE_GOVERNOR_UPDATE":
                  if (raw.data) {
                    setMetrics((prev) => ({ ...prev, ...raw.data }));
                    if (raw.data.medium_priority_frozen) {
                      addEvent("GATING", "Medium Priority Frozen: Quota >= 95%", "error");
                    } else if (raw.data.low_priority_frozen) {
                      addEvent("GATING", "Low Priority Frozen: Quota >= 85%", "warning");
                    }
                  }
                  break;

                case "HSM_STATE_UPDATE":
                  if (raw.data) {
                    const fullPath = raw.data.current_full_path || "PLANNING.DISCOVERY";
                    const parts = fullPath.split(".");
                    setHsmState((prev) => ({
                      ...prev,
                      current_full_path: fullPath,
                      super_state: parts[0],
                      active_substate: parts[1] || parts[0],
                      history_node: raw.data.history_node || prev.history_node,
                      turn_count: raw.data.turn_count ?? prev.turn_count,
                    }));
                    addEvent("HSM", `State transitioned to ${fullPath}`, "info");
                  }
                  break;

                case "WAL_WRITE_JOB":
                  addEvent("WAL", `Write job ${raw.job_id || ""} committed to SQLite WAL`, "info");
                  break;

                case "DELTA_DETECTED":
                  addEvent("DELTA", `Stale code detected in ${raw.file || "file"}: redirecting to RE_INDEX`, "warning");
                  break;

                default:
                  addEvent("SYSTEM", `Telemetry event: ${raw.event_type}`, "info");
                  break;
              }
            } else {
              // Standard consolidated TelemetryPayload
              const payload: TelemetryPayload = raw;
              setTelemetryPayload(payload);
              setDirtyQueue(payload.dirty_queue || []);
              setIntegrityScore(payload.integrity_score ?? 1.0);
              setSqliteTotalFiles(payload.sqlite_total_files ?? 0);
              if (payload.janitor_status) setJanitorStatus(payload.janitor_status);

              // Log dirty count changes if present
              if (payload.dirty_queue && payload.dirty_queue.length > 0) {
                addEvent("DELTA", `${payload.dirty_queue.length} dirty file(s) awaiting sync in WAL queue`, "warning");
              }
            }
          } catch (parseErr) {
            console.error("[Telemetry] Failed to parse SSE message:", parseErr);
          }
        };

        es.onerror = () => {
          if (!isMounted) return;
          setStatus("disconnected");
          setError("SSE connection lost. Reconnecting in 3s...");
          es.close();
          eventSourceRef.current = null;

          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMounted) connectSSE();
          }, 3000);
        };
      } catch (e) {
        if (!isMounted) return;
        setStatus("error");
        setError("Failed to initialize EventSource stream.");
      }
    };

    connectSSE();

    return () => {
      isMounted = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [hydrateRest, addEvent]);

  // Helper trigger for Janitor reconcile
  const triggerReconcile = useCallback(async () => {
    try {
      addEvent("JANITOR", "Manual Vector Reconciliation triggered", "info");
      const res = await fetch(`${API_BASE_URL}/api/janitor/reconcile`, { method: "POST" });
      if (res.ok) {
        addEvent("JANITOR", "Vector Reconciliation accepted by background task", "success");
      }
    } catch (e) {
      addEvent("JANITOR", `Vector Reconciliation trigger failed: ${e}`, "error");
    }
  }, [addEvent]);

  return {
    data: telemetryPayload,
    status,
    isConnected: status === "streaming",
    error,
    metrics,
    hsmState,
    dirtyQueue,
    integrityScore,
    sqliteTotalFiles,
    janitorStatus,
    events,
    triggerReconcile,
    refetchAll: hydrateRest,
    apiBaseUrl: API_BASE_URL,
  };
}
