"use client";

/**
 * components/hsm/HSMStateInspector.tsx — SDD-SURVIVAL-28
 *
 * Painel 3: Inspector de Estados HSM & History Nodes.
 *
 * Features:
 * - Navigable hierarchical visual tree for super-states (PLANNING, EXECUTION, MAINTENANCE, STALL, SUCCESS).
 * - Highlights active qualified path (e.g. EXECUTION.TDD_GREEN) with pulsating emerald glow.
 * - Deep History Node (H*) metadata card displaying checkpoint ID, formatted UTC timestamp, and target state.
 * - Circuit Breaker indicator: visual turn counter (0 to 5) tracking turn consumption in the current substate.
 */

import React, { useState, useMemo } from "react";
import type { HSMSessionState } from "@/lib/telemetry/types";

export interface HSMStateInspectorProps {
  hsmState?: HSMSessionState;
  onSelectState?: (statePath: string) => void;
  className?: string;
}

// Canonical HSM Hierarchy
const HSM_TOPOLOGY: Record<string, { category: string; substates: string[]; color: string }> = {
  PLANNING: {
    category: "READ_ONLY",
    color: "#38bdf8", // Sky Blue
    substates: ["DISCOVERY", "ARCHITECTURE", "KANBAN_GEN"],
  },
  EXECUTION: {
    category: "LOCAL_MUTATION",
    color: "#34d399", // Emerald
    substates: ["CODE_GEN", "TDD_GREEN", "REFACTORING", "RE_INDEX"],
  },
  MAINTENANCE: {
    category: "DANGEROUS",
    color: "#f43f5e", // Rose/Red
    substates: ["PURGE_CACHE", "RECONCILE", "RESET_DB"],
  },
  STALL: {
    category: "READ_ONLY",
    color: "#fbbf24", // Amber
    substates: ["AWAITING_HUMAN", "CONTEXT_FULL", "ERROR_PAUSE"],
  },
  SUCCESS: {
    category: "READ_ONLY",
    color: "#a855f7", // Purple
    substates: ["IDLE_COMPLETE"],
  },
};

export function HSMStateInspector({ hsmState, onSelectState, className = "" }: HSMStateInspectorProps) {
  const currentState = hsmState || {
    session_id: "default",
    current_full_path: "EXECUTION.CODE_GEN",
    super_state: "EXECUTION",
    active_substate: "CODE_GEN",
    category: "LOCAL_MUTATION",
    history_node: {
      state_path: "EXECUTION.CODE_GEN",
      checkpoint_id: "cp_hsm_992",
      timestamp: Date.now() - 120000,
    },
    turn_count: 2,
    max_turns: 5,
  };

  const [expandedSuperState, setExpandedSuperState] = useState<string | null>(
    currentState.super_state || "EXECUTION"
  );

  const activeSuper = currentState.super_state;
  const activeSub = currentState.active_substate;
  const activePath = currentState.current_full_path;

  // Format History Node timestamp
  const formattedHistoryTime = useMemo(() => {
    if (!currentState.history_node?.timestamp) return "Nenhum nó ativo";
    try {
      const ts = typeof currentState.history_node.timestamp === "number"
        ? currentState.history_node.timestamp * (currentState.history_node.timestamp < 10000000000 ? 1000 : 1)
        : Date.parse(currentState.history_node.timestamp);
      return new Date(ts).toLocaleString("pt-BR", {
        timeZone: "America/Sao_Paulo",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return String(currentState.history_node.timestamp);
    }
  }, [currentState.history_node]);

  // Turn count ratio for Circuit Breaker
  const turnCount = currentState.turn_count ?? 0;
  const maxTurns = currentState.max_turns ?? 5;
  const isCircuitBreakerWarning = turnCount >= 4;

  return (
    <div className={`relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950 shadow-2xl ${className}`}>
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-purple-400 ring-2 ring-purple-400/20" />
          <span className="font-semibold text-zinc-200">3. Árvore de Estados HSM & History</span>
        </div>

        {/* Active Super State Badge */}
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className="text-zinc-500">Sessão:</span>
          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-zinc-300 font-semibold">
            {currentState.session_id}
          </span>
          <span className="rounded bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-emerald-400 font-semibold">
            {activePath}
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto p-3 space-y-3">
        {/* Hierarchical State Tree */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
            Topologia Hierárquica (Super & Sub-Estados)
          </div>

          <div className="grid grid-cols-1 gap-1.5">
            {Object.entries(HSM_TOPOLOGY).map(([superName, def]) => {
              const isSuperActive = activeSuper === superName;
              const isExpanded = expandedSuperState === superName || isSuperActive;

              return (
                <div
                  key={superName}
                  className={`rounded-lg border transition-all duration-200 ${
                    isSuperActive
                      ? "border-zinc-700 bg-zinc-900/70 shadow-lg"
                      : "border-zinc-800/50 bg-zinc-900/30 hover:border-zinc-750"
                  }`}
                >
                  {/* Super-state row */}
                  <div
                    onClick={() => setExpandedSuperState(isExpanded ? null : superName)}
                    className="flex cursor-pointer items-center justify-between px-2.5 py-1.5 text-xs select-none"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{
                          backgroundColor: def.color,
                          boxShadow: isSuperActive ? `0 0 8px ${def.color}` : undefined,
                        }}
                      />
                      <span className={`font-mono font-semibold ${isSuperActive ? "text-white" : "text-zinc-300"}`}>
                        {superName}
                      </span>
                      {isSuperActive && (
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                      )}
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[10px]">
                      <span
                        className={`rounded px-1.5 py-0.2 text-[9px] ${
                          def.category === "DANGEROUS"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : def.category === "LOCAL_MUTATION"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : "bg-sky-500/10 text-sky-400 border border-sky-500/30"
                        }`}
                      >
                        {def.category}
                      </span>
                      <span className="text-zinc-500">{isExpanded ? "▼" : "▶"}</span>
                    </div>
                  </div>

                  {/* Sub-states list */}
                  {isExpanded && (
                    <div className="border-t border-zinc-800/50 px-3 py-1.5 space-y-1 bg-black/20">
                      <div className="flex flex-wrap gap-1.5">
                        {def.substates.map((sub) => {
                          const isSubActive = isSuperActive && activeSub === sub;
                          const qualified = `${superName}.${sub}`;

                          return (
                            <button
                              key={sub}
                              onClick={() => onSelectState && onSelectState(qualified)}
                              className={`flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-mono transition-all ${
                                isSubActive
                                  ? "bg-emerald-500/20 border border-emerald-400 text-emerald-300 font-bold shadow-[0_0_10px_rgba(52,211,153,0.3)]"
                                  : "bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                              }`}
                            >
                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  isSubActive ? "bg-emerald-400 animate-pulse" : "bg-zinc-500"
                                }`}
                              />
                              <span>{sub}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Section: History Node (H*) & Circuit Breaker */}
        <div className="grid grid-cols-2 gap-2 border-t border-zinc-800/60 pt-2.5">
          {/* Deep History Node (H*) Card */}
          <div className="rounded-lg border border-purple-500/30 bg-purple-950/20 p-2 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-purple-300">
              <span className="font-mono text-sm">H*</span>
              <span>Deep History Node</span>
            </div>
            <div className="mt-1 space-y-0.5 font-mono text-[10px] text-zinc-400">
              <p className="truncate">
                CP ID:{" "}
                <span className="text-purple-200 font-semibold">
                  {currentState.history_node?.checkpoint_id || "cp_none"}
                </span>
              </p>
              <p className="truncate">
                Restaurável em:{" "}
                <span className="text-zinc-300">
                  {currentState.history_node?.state_path || activePath}
                </span>
              </p>
              <p className="text-zinc-500 text-[9px]">{formattedHistoryTime}</p>
            </div>
          </div>

          {/* Circuit Breaker Turn Counter */}
          <div
            className={`rounded-lg border p-2 text-xs transition-colors ${
              isCircuitBreakerWarning
                ? "border-amber-500/40 bg-amber-950/20"
                : "border-zinc-800 bg-zinc-900/50"
            }`}
          >
            <div className="flex items-center justify-between font-semibold">
              <span className={isCircuitBreakerWarning ? "text-amber-400" : "text-zinc-300"}>
                Circuit Breaker
              </span>
              <span className="font-mono text-[10px] text-zinc-400">
                {turnCount} / {maxTurns} turnos
              </span>
            </div>

            {/* Turn dots */}
            <div className="mt-2 flex items-center justify-between gap-1">
              {Array.from({ length: maxTurns }).map((_, idx) => {
                const isFilled = idx < turnCount;
                const isWarningDot = isFilled && idx >= 3;

                return (
                  <div
                    key={idx}
                    className={`h-2 flex-1 rounded-full transition-all ${
                      isFilled
                        ? isWarningDot
                          ? "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]"
                          : "bg-emerald-400"
                        : "bg-zinc-800"
                    }`}
                  />
                );
              })}
            </div>

            <p className="mt-1 text-[9px] font-mono text-zinc-500">
              {turnCount >= maxTurns
                ? "⚠️ Limite excedido! STALL.ERROR_PAUSE disparado."
                : `${maxTurns - turnCount} turno(s) até pausa preventiva.`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
