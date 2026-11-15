"use client";

/**
 * app/components/SelfHealingConsole.tsx — SDD-SURVIVAL-16
 *
 * Terminal de Logs de Auto-Cura e Console Operacional do Janitor.
 *
 * Exibe:
 * - Logs ao vivo de auto-cura em tempo real (vetores órfãos interceptados e descartados).
 * - Status operacional do BackgroundJanitor.
 * - Botão ativo de disparo manual de reconciliação de órfãos (POST /api/janitor/reconcile).
 */

import React, { useEffect, useRef, useState } from "react";
import type { TelemetryPayload } from "@/lib/telemetry/types";

interface SelfHealingConsoleProps {
  telemetry: TelemetryPayload | null;
  isLoading?: boolean;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_CONCIERGE_API_URL || "http://127.0.0.1:8000";

export function SelfHealingConsole({
  telemetry,
  isLoading = false,
}: SelfHealingConsoleProps) {
  const terminalEndRef = useRef<HTMLDivElement | null>(null);
  const [isTriggering, setIsTriggering] = useState(false);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  const self_healing_events = telemetry?.self_healing_events ?? [];
  const janitor_status = telemetry?.janitor_status;

  // Auto-scroll no terminal ao receber novos eventos de auto-cura
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [self_healing_events.length]);

  // Disparo manual do Janitor Reconcile
  const handleTriggerJanitor = async () => {
    setIsTriggering(true);
    setActionStatus("Disparando reconciliador em background...");

    try {
      const res = await fetch(`${API_BASE_URL}/api/janitor/reconcile`, {
        method: "POST",
      });

      if (res.ok) {
        setActionStatus("Janitor iniciado com sucesso! Reconciliação em andamento.");
        setTimeout(() => setActionStatus(null), 4000);
      } else {
        throw new Error(`Status HTTP: ${res.status}`);
      }
    } catch (err) {
      setActionStatus("Falha ao acionar Janitor. Verifique o servidor FastAPI.");
      setTimeout(() => setActionStatus(null), 4000);
    } finally {
      setIsTriggering(false);
    }
  };

  if (isLoading || !telemetry) {
    return <SelfHealingConsoleSkeleton />;
  }

  return (
    <div className="panel-overlay space-y-4">
      {/* Header com Ação */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">🛡️</span>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-200 font-mono">
              Self-Healing & Janitor Console
            </h3>
            <p className="text-[10px] text-neutral-500 font-mono">
              Monitor de auto-cura quente e descarte de órfãos
            </p>
          </div>
        </div>

        {/* Botão de Disparo Manual */}
        <button
          onClick={handleTriggerJanitor}
          disabled={isTriggering || janitor_status?.is_running}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
            janitor_status?.is_running
              ? "bg-amber-500/10 border border-amber-500/30 text-amber-400 animate-pulse"
              : "bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 active:scale-95"
          }`}
          title="Disparar reconciliação de vetores órfãos no backend"
        >
          <span>{janitor_status?.is_running ? "⏳" : "⚡"}</span>
          <span>
            {janitor_status?.is_running
              ? "Janitor Executando..."
              : isTriggering
              ? "Disparando..."
              : "Forçar Reconciliação"}
          </span>
        </button>
      </div>

      {/* Status Bar / Feedback */}
      {actionStatus && (
        <div className="text-xs text-neutral-300 bg-white/[0.03] p-2 rounded-lg border border-white/[0.08] font-mono flex items-center gap-2">
          <span className="text-amber-400">ℹ️</span>
          <span>{actionStatus}</span>
        </div>
      )}

      {/* Terminal de Logs */}
      <div className="bg-black/90 rounded-xl border border-white/[0.08] p-3.5 h-64 flex flex-col justify-between font-mono text-xs shadow-inner">
        <div className="overflow-y-auto space-y-2 flex-1 pr-1">
          <div className="text-neutral-600 text-[11px]">
            // Grafo Concierge v4.1.0 — Stream de Telemetria JIT Ativo
          </div>

          {janitor_status && (
            <div className="text-neutral-400 text-[11px] bg-white/[0.02] p-1.5 rounded border border-white/[0.04]">
              <span className="text-cyan-400">[JANITOR]</span> Próxima varredura:{" "}
              <span className="text-neutral-300">
                {new Date(janitor_status.next_scheduled_run).toLocaleTimeString()}
              </span>
              {janitor_status.last_run && (
                <span className="text-neutral-500 ml-2">
                  (Última: {new Date(janitor_status.last_run).toLocaleTimeString()})
                </span>
              )}
            </div>
          )}

          {self_healing_events.length === 0 ? (
            <div className="text-emerald-400/90 text-[11px] pt-1">
              [AUTO-CURA] Monitor de auto-cura JIT ativo. Nenhuma anomalia de busca ou vetor órfão interceptado no momento.
            </div>
          ) : (
            self_healing_events.map((evt, idx) => (
              <div
                key={`${evt.orphan_id}-${idx}`}
                className="border-l-2 border-emerald-500 pl-2.5 py-1 my-1 bg-white/[0.01] rounded-r"
              >
                <div className="flex items-center gap-2 text-[10px]">
                  <span className="text-neutral-500">
                    [{new Date(evt.timestamp).toLocaleTimeString()}]
                  </span>
                  <span className="text-emerald-400 font-bold uppercase">
                    [{evt.event_type}]
                  </span>
                </div>
                <p className="text-neutral-300 text-[11px] mt-0.5">
                  Vetor órfão interceptado:{" "}
                  <span className="text-neutral-100 font-bold">{evt.orphan_id}</span>
                </p>
                <p className="text-neutral-500 text-[10px] truncate">{evt.context}</p>
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
}

function SelfHealingConsoleSkeleton() {
  return (
    <div className="panel-overlay animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="h-3 w-48 bg-white/[0.06] rounded" />
        <div className="h-6 w-32 bg-white/[0.06] rounded" />
      </div>
      <div className="h-64 rounded-xl bg-white/[0.03]" />
    </div>
  );
}
