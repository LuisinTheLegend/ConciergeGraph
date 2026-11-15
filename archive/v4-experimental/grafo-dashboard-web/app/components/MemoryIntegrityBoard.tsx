"use client";

/**
 * app/components/MemoryIntegrityBoard.tsx — SDD-SURVIVAL-16
 *
 * Painel de Integridade de Memória e Consistência de Bancos de Dados.
 *
 * Exibe:
 * - Gauge visual de consistência eventual (SQLite WAL vs Qdrant/Chroma).
 * - Cards de contadores técnicos (Arquivos SQLite, Vetores e Órfãos).
 * - Fila de sincronização delta (dirty_queue) colapsável com badges animados.
 */

import React, { useState } from "react";
import type { TelemetryPayload } from "@/lib/telemetry/types";

interface MemoryIntegrityBoardProps {
  telemetry: TelemetryPayload | null;
  isLoading?: boolean;
}

export function MemoryIntegrityBoard({
  telemetry,
  isLoading = false,
}: MemoryIntegrityBoardProps) {
  const [isDirtyQueueExpanded, setIsDirtyQueueExpanded] = useState(true);

  if (isLoading || !telemetry) {
    return <MemoryIntegrityBoardSkeleton />;
  }

  const {
    integrity_score,
    sqlite_total_files,
    qdrant_total_vectors,
    orphans_detected,
    queue_backlog,
    dirty_queue,
    tailscale_ip,
  } = telemetry;

  // Normaliza o score para porcentagem (trata se vier 0.0..1.0 ou 0..100)
  const scorePct =
    integrity_score <= 1.0
      ? Math.round(integrity_score * 100)
      : Math.round(integrity_score);

  // Define cor baseado no score
  const getScoreTheme = (score: number) => {
    if (score >= 98) {
      return {
        text: "text-emerald-400",
        border: "border-emerald-500/30",
        bg: "bg-emerald-500/10",
        stroke: "#10b981",
        label: "Excelente",
      };
    }
    if (score >= 80) {
      return {
        text: "text-amber-400",
        border: "border-amber-500/30",
        bg: "bg-amber-500/10",
        stroke: "#f59e0b",
        label: "Atenção (Fila Ativa)",
      };
    }
    return {
      text: "text-rose-400",
      border: "border-rose-500/30",
      bg: "bg-rose-500/10",
      stroke: "#f43f5e",
      label: "Degradação Detectada",
    };
  };

  const theme = getScoreTheme(scorePct);

  // SVG Radial Gauge calculation
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (scorePct / 100) * circumference;

  return (
    <div className="panel-overlay space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">📊</span>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-200 font-mono">
              Memory Integrity Board
            </h3>
            <p className="text-[10px] text-neutral-500 font-mono">
              Consistência de dados SQLite WAL & Vetores
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-[10px] font-mono text-neutral-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>IP: {tailscale_ip || "127.0.0.1"}</span>
        </div>
      </div>

      {/* Grid Central: Radial Gauge + KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
        {/* Radial Progress Gauge */}
        <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-white/[0.02] border border-white/[0.04]">
          <div className="relative w-28 h-28 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              {/* Background circle */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                className="text-white/[0.05]"
                strokeWidth="8"
                stroke="currentColor"
                fill="transparent"
              />
              {/* Progress circle */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                stroke={theme.stroke}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                style={{
                  transition: "stroke-dashoffset 0.8s ease-in-out",
                }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-2xl font-bold font-mono ${theme.text}`}>
                {scorePct}%
              </span>
              <span className="text-[8px] uppercase tracking-widest text-neutral-500 font-mono">
                Integridade
              </span>
            </div>
          </div>
          <span
            className={`mt-2 text-[10px] font-mono font-medium px-2 py-0.5 rounded-full border ${theme.border} ${theme.bg} ${theme.text}`}
          >
            {theme.label}
          </span>
        </div>

        {/* Technical Counters */}
        <div className="space-y-2">
          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs">📁</span>
              <span className="text-[11px] text-neutral-400 font-mono">SQLite (WAL)</span>
            </div>
            <span className="text-xs font-bold font-mono text-neutral-200">
              {sqlite_total_files.toLocaleString()} files
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs">🧬</span>
              <span className="text-[11px] text-neutral-400 font-mono">Vetores</span>
            </div>
            <span className="text-xs font-bold font-mono text-cyan-400">
              {qdrant_total_vectors.toLocaleString()} vectors
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs">👻</span>
              <span className="text-[11px] text-neutral-400 font-mono">Órfãos Detectados</span>
            </div>
            <span
              className={`text-xs font-bold font-mono ${
                orphans_detected > 0 ? "text-rose-400" : "text-emerald-400"
              }`}
            >
              {orphans_detected}
            </span>
          </div>
        </div>
      </div>

      {/* Tabela de Fila Suja (Dirty Queue) */}
      <div className="space-y-2 pt-2 border-t border-white/[0.04]">
        <button
          onClick={() => setIsDirtyQueueExpanded(!isDirtyQueueExpanded)}
          className="w-full flex items-center justify-between text-left cursor-pointer group"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs">🟡</span>
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400 font-mono group-hover:text-neutral-300">
              Fila de Sincronização Delta
            </h4>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full border ${
                queue_backlog > 0
                  ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                  : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              }`}
            >
              {queue_backlog} pendente{queue_backlog !== 1 ? "s" : ""}
            </span>
          </div>
          <span
            className={`text-neutral-600 text-xs transition-transform duration-200 ${
              isDirtyQueueExpanded ? "rotate-180" : ""
            }`}
          >
            ▼
          </span>
        </button>

        {isDirtyQueueExpanded && (
          <div>
            {dirty_queue.length === 0 ? (
              <div className="p-3.5 rounded-lg bg-emerald-500/[0.04] border border-emerald-500/15 text-center">
                <p className="text-xs text-emerald-400 font-medium">
                  ✨ Grafo perfeitamente consistente! Fila limpa.
                </p>
              </div>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {dirty_queue.map((file, idx) => (
                  <div
                    key={`${file.path}-${idx}`}
                    className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:border-amber-500/30 transition-all text-xs"
                  >
                    <div className="min-w-0 pr-2">
                      <span className="font-mono text-neutral-300 truncate block text-[11px]">
                        {file.path}
                      </span>
                      <span className="text-[9px] text-neutral-500 font-mono">
                        Comunidade: {file.community_id}
                      </span>
                    </div>
                    <span className="text-[9px] bg-amber-500/10 border border-amber-500/20 text-amber-400 px-2 py-0.5 rounded font-mono font-semibold animate-pulse shrink-0">
                      JIT Sumarização
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MemoryIntegrityBoardSkeleton() {
  return (
    <div className="panel-overlay animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="h-3 w-40 bg-white/[0.06] rounded" />
        <div className="h-3 w-20 bg-white/[0.06] rounded" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="h-28 rounded-xl bg-white/[0.03]" />
        <div className="space-y-2">
          <div className="h-7 rounded bg-white/[0.03]" />
          <div className="h-7 rounded bg-white/[0.03]" />
          <div className="h-7 rounded bg-white/[0.03]" />
        </div>
      </div>
    </div>
  );
}
