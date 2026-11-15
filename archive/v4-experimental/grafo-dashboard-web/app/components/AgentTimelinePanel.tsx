"use client";

/**
 * app/components/AgentTimelinePanel.tsx — SDD-SURVIVAL-16
 *
 * Linha do Tempo de Checkpoints e Time-Travel dos Agentes (SDD-12 / SDD-13).
 *
 * Exibe:
 * - Seletor horizontal de sessões ativas agrupadas por agent_id / session_id.
 * - Linha do tempo física vertical dos checkpoints.
 * - Distinção visual explícita entre nós imutáveis protegidos (init/protected),
 *   checkpoints ativos e checkpoints podados pelo algoritmo LRU (pruned_by_lru).
 */

import React, { useState } from "react";
import type { TelemetryPayload, CheckpointStatus } from "@/lib/telemetry/types";

interface AgentTimelinePanelProps {
  telemetry: TelemetryPayload | null;
  isLoading?: boolean;
}

export function AgentTimelinePanel({
  telemetry,
  isLoading = false,
}: AgentTimelinePanelProps) {
  const agent_sessions = telemetry?.agent_sessions ?? [];

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    agent_sessions.length > 0 ? agent_sessions[0].session_id : null
  );

  // Mantém a sessão selecionada sincronizada com as sessões disponíveis
  const activeSession =
    agent_sessions.find((s) => s.session_id === selectedSessionId) ||
    agent_sessions[0] ||
    null;

  const getStatusBadge = (status: CheckpointStatus) => {
    switch (status) {
      case "protected":
        return {
          badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
          dot: "bg-emerald-500 text-black border-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.4)]",
          label: "🛡️ PROTEGER (init)",
        };
      case "pruned_by_lru":
        return {
          badge: "bg-neutral-800/60 border-neutral-700/40 text-neutral-500",
          dot: "bg-neutral-700 text-neutral-400 border-neutral-600 opacity-60",
          label: "✂️ Podado por LRU",
        };
      case "active":
      default:
        return {
          badge: "bg-blue-500/10 border-blue-500/30 text-blue-400",
          dot: "bg-blue-500 text-white border-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.3)]",
          label: "🟢 Ativo",
        };
    }
  };

  if (isLoading || !telemetry) {
    return <AgentTimelineSkeleton />;
  }

  return (
    <div className="panel-overlay space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">⏳</span>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-200 font-mono">
              Agent Time-Travel Timeline
            </h3>
            <p className="text-[10px] text-neutral-500 font-mono">
              Controle de checkpoints e recuperação de estados (SDD-12/13)
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono text-neutral-500 px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.06]">
          {agent_sessions.length} sess{agent_sessions.length !== 1 ? "ões" : "ão"}
        </span>
      </div>

      {/* Seletor de Sessões */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {agent_sessions.length === 0 ? (
          <p className="text-xs text-neutral-500 py-3 font-mono">
            Nenhuma sessão de agente ativa no momento.
          </p>
        ) : (
          agent_sessions.map((session) => {
            const isSelected = activeSession?.session_id === session.session_id;
            return (
              <button
                key={session.session_id}
                onClick={() => setSelectedSessionId(session.session_id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono border whitespace-nowrap transition-all cursor-pointer ${
                  isSelected
                    ? "bg-amber-500/15 border-amber-500/40 text-amber-300 font-semibold shadow-[0_0_12px_rgba(245,158,11,0.15)]"
                    : "bg-white/[0.02] border-white/[0.06] text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.04]"
                }`}
              >
                <span className="text-neutral-500 mr-1">Agente:</span>
                <span className="text-neutral-200">{session.agent_id}</span>
                <span className="text-neutral-600 ml-1.5">
                  ({session.checkpoints.length} cps)
                </span>
              </button>
            );
          })
        )}
      </div>

      {/* Linha do Tempo Física dos Checkpoints */}
      {activeSession && (
        <div className="p-4 bg-black/40 rounded-xl border border-white/[0.04] max-h-80 overflow-y-auto pr-2">
          <div className="relative border-l-2 border-white/[0.10] pl-6 ml-3 space-y-4">
            {activeSession.checkpoints.map((cp, idx) => {
              const theme = getStatusBadge(cp.status);

              return (
                <div key={`${cp.id}-${idx}`} className="relative group">
                  {/* Indicador de eixo */}
                  <div
                    className={`absolute -left-[33px] top-1.5 w-4 h-4 rounded-full border flex items-center justify-center transition-transform group-hover:scale-125 ${theme.dot}`}
                  >
                    {cp.status === "protected" && (
                      <span className="text-[8px]">🛡️</span>
                    )}
                  </div>

                  {/* Card do Checkpoint */}
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] transition-all flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-mono text-neutral-200">
                          {cp.id}
                        </span>
                      </div>
                      <span className="text-[10px] text-neutral-500 block font-mono mt-0.5">
                        Salvo em: {new Date(cp.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <span
                      className={`text-[9px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded border ${theme.badge}`}
                    >
                      {theme.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function AgentTimelineSkeleton() {
  return (
    <div className="panel-overlay animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="h-3 w-44 bg-white/[0.06] rounded" />
        <div className="h-3 w-16 bg-white/[0.06] rounded" />
      </div>
      <div className="flex gap-2">
        <div className="h-7 w-32 bg-white/[0.03] rounded-lg" />
        <div className="h-7 w-32 bg-white/[0.03] rounded-lg" />
      </div>
      <div className="h-44 rounded-xl bg-white/[0.03]" />
    </div>
  );
}
