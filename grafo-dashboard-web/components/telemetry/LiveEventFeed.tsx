"use client";

/**
 * components/telemetry/LiveEventFeed.tsx — SDD-SURVIVAL-28
 *
 * Painel 4: Stream de Eventos em Tempo Real (SSE Logs).
 *
 * Features:
 * - Real-time terminal console with auto-scroll and pause toggle.
 * - Automatic UTC ISO 8601 to browser local time conversion (HH:mm:ss.SSS).
 * - High-contrast categorised badges: [WAL], [JANITOR], [DELTA], [HSM], [GATING].
 * - Full-text filtering and quick category chips.
 * - Zero network polling — powered directly by useTelemetryStream SSE.
 */

import React, { useState, useEffect, useRef, useMemo } from "react";
import type { LiveTelemetryEvent, EventCategoryBadge } from "@/lib/telemetry/types";

export interface LiveEventFeedProps {
  events?: LiveTelemetryEvent[];
  maxHeight?: string | number;
  className?: string;
}

const BADGE_STYLES: Record<EventCategoryBadge, { bg: string; text: string; border: string }> = {
  WAL: {
    bg: "bg-sky-500/15",
    text: "text-sky-300",
    border: "border-sky-500/30",
  },
  JANITOR: {
    bg: "bg-purple-500/15",
    text: "text-purple-300",
    border: "border-purple-500/30",
  },
  DELTA: {
    bg: "bg-amber-500/15",
    text: "text-amber-300",
    border: "border-amber-500/30",
  },
  HSM: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-300",
    border: "border-emerald-500/30",
  },
  GATING: {
    bg: "bg-rose-500/15",
    text: "text-rose-300",
    border: "border-rose-500/30",
  },
  MCP: {
    bg: "bg-indigo-500/15",
    text: "text-indigo-300",
    border: "border-indigo-500/30",
  },
  SYSTEM: {
    bg: "bg-zinc-500/15",
    text: "text-zinc-300",
    border: "border-zinc-500/30",
  },
};

// Formats ISO 8601 UTC timestamp to local browser time with milliseconds
function formatLocalTimestamp(isoString: string): string {
  if (!isoString) return "--:--:--.---";
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    const pad = (n: number, z = 2) => String(n).padStart(z, "0");
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());
    const seconds = pad(date.getSeconds());
    const millis = pad(date.getMilliseconds(), 3);

    return `${hours}:${minutes}:${seconds}.${millis}`;
  } catch {
    return isoString;
  }
}

export function LiveEventFeed({ events: propEvents = [], className = "" }: LiveEventFeedProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const [filterBadge, setFilterBadge] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Default demonstration events if stream is empty
  const defaultEvents: LiveTelemetryEvent[] = useMemo(
    () => [
      {
        id: "ev_1",
        timestamp: new Date(Date.now() - 32000).toISOString(),
        badge: "WAL",
        message: "Write Job #402 committed to SQLite WAL (sync_mode=NORMAL, dirty_delta=0)",
        level: "info",
      },
      {
        id: "ev_2",
        timestamp: new Date(Date.now() - 25000).toISOString(),
        badge: "JANITOR",
        message: "Smart Checkpoint Pruning: 12 stale checkpoints purged (init 'init' protected)",
        level: "info",
      },
      {
        id: "ev_3",
        timestamp: new Date(Date.now() - 18000).toISOString(),
        badge: "DELTA",
        message: "Dual-Hash verification: 72 files clean (SSH match), 0 structural drift",
        level: "success",
      },
      {
        id: "ev_4",
        timestamp: new Date(Date.now() - 11000).toISOString(),
        badge: "HSM",
        message: "Transition PLANNING.DISCOVERY -> EXECUTION.CODE_GEN committed (checkpoint=cp_hsm_992)",
        level: "info",
      },
      {
        id: "ev_5",
        timestamp: new Date(Date.now() - 4000).toISOString(),
        badge: "GATING",
        message: "Adaptive Gating: mode='ask', rate quota 20.0% RPM / 35.5% TPM (NORMAL)",
        level: "info",
      },
    ],
    []
  );

  const activeEvents = propEvents.length > 0 ? propEvents : defaultEvents;

  // Filtered event list
  const filteredEvents = useMemo(() => {
    return activeEvents.filter((ev) => {
      const matchesBadge = filterBadge === "ALL" || ev.badge === filterBadge;
      const matchesSearch =
        !searchQuery.trim() ||
        ev.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ev.badge.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesBadge && matchesSearch;
    });
  }, [activeEvents, filterBadge, searchQuery]);

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [filteredEvents, autoScroll]);

  return (
    <div className={`relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950 shadow-2xl ${className}`}>
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-cyan-400 ring-2 ring-cyan-400/20" />
          <span className="font-semibold text-zinc-200">4. Stream de Eventos em Tempo Real</span>
          <span className="font-mono text-[10px] text-zinc-500">
            ({filteredEvents.length} eventos)
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Auto-scroll Toggle Button */}
          <button
            onClick={() => setAutoScroll((prev) => !prev)}
            className={`flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono transition ${
              autoScroll
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${autoScroll ? "bg-emerald-400 animate-pulse" : "bg-zinc-500"}`}
            />
            {autoScroll ? "Auto-Scroll: ON" : "Auto-Scroll: PAUSED"}
          </button>

          {/* Quick text filter */}
          <input
            type="text"
            placeholder="Filtrar logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-6 w-24 rounded bg-zinc-900 px-2 text-[10px] text-zinc-300 placeholder-zinc-600 border border-zinc-800 focus:border-cyan-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-1.5 border-b border-zinc-800/40 bg-zinc-900/20 px-3 py-1.5 text-[10px] font-mono overflow-x-auto">
        <span className="text-zinc-500 mr-1">Filtros:</span>
        {["ALL", "WAL", "JANITOR", "DELTA", "HSM", "GATING"].map((badge) => {
          const isSelected = filterBadge === badge;
          return (
            <button
              key={badge}
              onClick={() => setFilterBadge(badge)}
              className={`rounded px-1.5 py-0.5 transition ${
                isSelected
                  ? "bg-zinc-700 text-white font-bold"
                  : "bg-zinc-900/60 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {badge}
            </button>
          );
        })}
      </div>

      {/* Terminal Log Console */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-2.5 font-mono text-[11px] leading-relaxed space-y-1 bg-black/60 select-text"
        style={{ minHeight: 200 }}
      >
        {filteredEvents.length === 0 ? (
          <div className="flex h-full items-center justify-center text-zinc-600 italic">
            Nenhum evento registrado no canal SSE.
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const badgeStyle = BADGE_STYLES[ev.badge] || BADGE_STYLES.SYSTEM;
            const localTimestamp = formatLocalTimestamp(ev.timestamp);

            return (
              <div
                key={ev.id}
                className="group flex items-start gap-2 rounded px-1.5 py-0.5 hover:bg-zinc-900/50 transition-colors"
              >
                {/* Local Timestamp */}
                <span className="text-zinc-500 text-[10px] whitespace-nowrap select-none">
                  [{localTimestamp}]
                </span>

                {/* Subsystem Badge */}
                <span
                  className={`inline-flex items-center rounded border px-1.5 py-0.2 text-[9px] font-semibold tracking-wider select-none ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
                >
                  {ev.badge}
                </span>

                {/* Message Body */}
                <span
                  className={`flex-1 break-words ${
                    ev.level === "error"
                      ? "text-rose-400 font-semibold"
                      : ev.level === "warning"
                      ? "text-amber-300"
                      : ev.level === "success"
                      ? "text-emerald-300"
                      : "text-zinc-300"
                  }`}
                >
                  {ev.message}
                </span>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info Line */}
      <div className="flex items-center justify-between border-t border-zinc-800/50 bg-zinc-900/30 px-3 py-1 text-[9px] font-mono text-zinc-500">
        <span>Fuso Horário Local: {Intl.DateTimeFormat().resolvedOptions().timeZone}</span>
        <span>Canal SSE: /api/telemetry/stream</span>
      </div>
    </div>
  );
}
