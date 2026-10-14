"use client";

/**
 * components/governor/QuotaGauges.tsx — SDD-SURVIVAL-28
 *
 * Painel 2: Telemetria de Cotas (RateGovernor Gauges).
 *
 * Displays:
 * - Semicircular SVG radial gauges for RPM (max 60) and TPM (max 40,000).
 * - Animated stroke-dashoffset transitions for smooth real-time 60s sliding window updates.
 * - Reactive freezing badges:
 *   - 🟢 NORMAL: Quota < 85%. All queues flowing.
 *   - 🟡 LOW FROZEN: Quota >= 85%. Janitor/GraphRAG queue suspended.
 *   - 🟠 MEDIUM FROZEN: Quota >= 95%. Subagents suspended (Primary Agent exclusive).
 */

import React, { useMemo } from "react";
import type { GovernorMetrics } from "@/lib/telemetry/types";

export interface QuotaGaugesProps {
  metrics?: GovernorMetrics;
  queueBacklog?: number;
  className?: string;
}

// Single SVG Semi-Circular Radial Gauge Component
interface RadialGaugeProps {
  value: number;
  max: number;
  label: string;
  unit: string;
  percentage: number;
  color: string;
}

function RadialGauge({
  value,
  max,
  label,
  unit,
  percentage,
  color,
}: RadialGaugeProps) {
  // SVG circular arc geometry
  const radius = 64;
  const strokeWidth = 10;
  const circumference = Math.PI * radius; // Half circle arc length
  const clampedPct = Math.min(Math.max(percentage, 0), 100);
  const strokeDashoffset = circumference - (circumference * clampedPct) / 100;

  return (
    <div className="flex flex-col items-center justify-center p-3">
      <div className="relative flex items-center justify-center">
        <svg
          width="160"
          height="95"
          viewBox="0 0 160 95"
          className="overflow-visible"
        >
          {/* Background track arc */}
          <path
            d="M 16 80 A 64 64 0 0 1 144 80"
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Foreground colored animated progress arc */}
          <path
            d="M 16 80 A 64 64 0 0 1 144 80"
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{
              transition: "stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s ease",
              filter: `drop-shadow(0 0 6px ${color}66)`,
            }}
          />

          {/* Tick markers */}
          <line x1="16" y1="83" x2="16" y2="88" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <line x1="80" y1="16" x2="80" y2="10" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <line x1="144" y1="83" x2="144" y2="88" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
        </svg>

        {/* Center digital readout */}
        <div className="absolute top-10 flex flex-col items-center">
          <span className="text-xl font-bold tracking-tight text-white font-mono">
            {value.toLocaleString()}
          </span>
          <span className="text-[10px] font-mono text-zinc-400">
            {clampedPct.toFixed(1)}% ({unit})
          </span>
        </div>
      </div>

      <div className="mt-1 text-center">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
          {label}
        </span>
        <p className="text-[10px] font-mono text-zinc-500">
          Teto Máximo: {max.toLocaleString()} {unit}
        </p>
      </div>
    </div>
  );
}

export function QuotaGauges({ metrics, queueBacklog = 0, className = "" }: QuotaGaugesProps) {
  const currentMetrics = metrics || {
    current_rpm: 12,
    current_tpm: 14200,
    rpm_percentage: 20.0,
    tpm_percentage: 35.5,
    low_priority_frozen: false,
    medium_priority_frozen: false,
    max_rpm: 60,
    max_tpm: 40000,
  };

  const rpm = currentMetrics.current_rpm;
  const tpm = currentMetrics.current_tpm;
  const maxRpm = currentMetrics.max_rpm || 60;
  const maxTpm = currentMetrics.max_tpm || 40000;

  const rpmPct = currentMetrics.rpm_percentage || (rpm / maxRpm) * 100;
  const tpmPct = currentMetrics.tpm_percentage || (tpm / maxTpm) * 100;

  // Derive status tier based on SDD-28 spec
  const statusInfo = useMemo(() => {
    if (currentMetrics.medium_priority_frozen || rpmPct >= 95 || tpmPct >= 95) {
      return {
        label: "MEDIUM FROZEN (≥95%)",
        badgeColor: "bg-rose-500/20 text-rose-300 border-rose-500/40",
        statusDot: "bg-rose-500 animate-ping",
        tier: "CRITICAL",
        description: "Sub-agentes congelados. Fila exclusiva do Agente Primário ativa.",
      };
    }
    if (currentMetrics.low_priority_frozen || rpmPct >= 85 || tpmPct >= 85) {
      return {
        label: "LOW FROZEN (≥85%)",
        badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/40",
        statusDot: "bg-amber-500 animate-pulse",
        tier: "WARNING",
        description: "Fila de Janitor/GraphRAG em pausa preventiva.",
      };
    }
    return {
      label: "NORMAL (<85%)",
      badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
      statusDot: "bg-emerald-400",
      tier: "OK",
      description: "Todas as filas operando em taxa nominal.",
    };
  }, [currentMetrics, rpmPct, tpmPct]);

  // Dynamic colors for gauge bars based on percentage
  const rpmColor = rpmPct >= 95 ? "#f43f5e" : rpmPct >= 85 ? "#f59e0b" : "#38bdf8";
  const tpmColor = tpmPct >= 95 ? "#f43f5e" : tpmPct >= 85 ? "#f59e0b" : "#34d399";

  return (
    <div className={`relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950 shadow-2xl ${className}`}>
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-emerald-400/20" />
          <span className="font-semibold text-zinc-200">2. Rate Governor (Métricas de Cota)</span>
          <span className="font-mono text-[10px] text-zinc-500">Janela 60s</span>
        </div>

        {/* Reactive Freezing Status Badge */}
        <div
          className={`flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-semibold tracking-wider ${statusInfo.badgeColor}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${statusInfo.statusDot}`} />
          <span>{statusInfo.label}</span>
        </div>
      </div>

      {/* Main Gauges Container */}
      <div className="flex flex-1 flex-col items-center justify-around p-3">
        {/* Dynamic Alert Banner */}
        <div className="w-full rounded-lg border border-zinc-800/60 bg-zinc-900/50 p-2 text-center text-[11px] text-zinc-300">
          <p className="font-mono">{statusInfo.description}</p>
        </div>

        {/* Dual Gauges: RPM & TPM */}
        <div className="grid w-full grid-cols-2 gap-2">
          <RadialGauge
            value={rpm}
            max={maxRpm}
            label="RPM (Requests / min)"
            unit="req/m"
            percentage={rpmPct}
            color={rpmColor}
          />
          <RadialGauge
            value={tpm}
            max={maxTpm}
            label="TPM (Tokens / min)"
            unit="tok/m"
            percentage={tpmPct}
            color={tpmColor}
          />
        </div>

        {/* Footer Metrics Row */}
        <div className="flex w-full items-center justify-between border-t border-zinc-800/60 pt-2 text-[10px] font-mono text-zinc-400">
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500">Fila WAL Backlog:</span>
            <span className={`font-semibold ${queueBacklog > 0 ? "text-amber-400" : "text-emerald-400"}`}>
              {queueBacklog} jobs
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  currentMetrics.low_priority_frozen ? "bg-amber-400" : "bg-zinc-600"
                }`}
              />
              Low Queue: {currentMetrics.low_priority_frozen ? "FROZEN" : "ACTIVE"}
            </span>

            <span className="flex items-center gap-1">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  currentMetrics.medium_priority_frozen ? "bg-orange-500" : "bg-zinc-600"
                }`}
              />
              Medium Queue: {currentMetrics.medium_priority_frozen ? "FROZEN" : "ACTIVE"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
