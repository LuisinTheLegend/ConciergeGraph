"use client";

/**
 * SemanticFactsPanel — Semantic Facts Sub-Graph
 *
 * Displays documentary facts (node_type: FACT) extracted by the
 * Grafo Concierge ingestion pipeline. Each fact shows:
 * - Label (documentary origin)
 * - Summary (fact description)
 * - Associated tags
 * - Relevance score (hybrid_score)
 *
 * Uses the orange branding palette #ffa203 for consistency with the 3D engine.
 */

import { useState } from "react";
import type { SemanticFact, CognitiveLoadingState } from "../hooks/useCognitiveData";

// ─── Props ──────────────────────────────────────────────────────────────────

interface SemanticFactsPanelProps {
  facts: SemanticFact[];
  loadingState: CognitiveLoadingState;
}

// ─── Component ──────────────────────────────────────────────────────────────

export function SemanticFactsPanel({
  facts,
  loadingState,
}: SemanticFactsPanelProps) {
  const [expandedFactId, setExpandedFactId] = useState<number | null>(null);
  const isLoading =
    loadingState === "loading-facts" ||
    loadingState === "loading-memory" ||
    loadingState === "idle";

  if (isLoading) {
    return (
      <div className="space-y-3">
        <SectionHeader />
        <FactSkeleton />
        <FactSkeleton />
        <FactSkeleton />
        <FactSkeleton />
      </div>
    );
  }

  if (facts.length === 0) {
    return (
      <div className="space-y-3">
        <SectionHeader />
        <div className="panel-overlay text-center py-8">
          <span className="text-3xl mb-3 block">📭</span>
          <p className="text-sm text-neutral-500">
            No semantic facts found.
          </p>
          <p className="text-xs text-neutral-600 mt-1">
            Ingest a project with{" "}
            <code className="text-amber-500/70 text-[10px]">concierge_mine</code>{" "}
            to generate facts.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <SectionHeader count={facts.length} />
      <div className="space-y-2">
        {facts.map((fact) => (
          <FactCard
            key={fact.node_id}
            fact={fact}
            isExpanded={expandedFactId === fact.node_id}
            onToggle={() =>
              setExpandedFactId(
                expandedFactId === fact.node_id ? null : fact.node_id
              )
            }
          />
        ))}
      </div>
    </div>
  );
}

// ─── Sub Components ─────────────────────────────────────────────────────────

function SectionHeader({ count }: { count?: number }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
        <span className="text-base">⚡</span>
        Semantic Facts
      </h3>
      {count !== undefined && (
        <span className="text-[10px] font-mono text-neutral-600 px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
          {count} {count === 1 ? "fact" : "facts"}
        </span>
      )}
    </div>
  );
}

function FactCard({
  fact,
  isExpanded,
  onToggle,
}: {
  fact: SemanticFact;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  // Formats the score as a visual percentage
  const scorePct = Math.round(fact.hybrid_score * 100);
  const scoreColor =
    scorePct >= 30 ? "#ffa203" : scorePct >= 15 ? "#fbbf24" : "#6b7280";

  // Extracts the short name of the label
  const shortLabel = getFactShortLabel(fact.label);

  return (
    <div
      className="panel-overlay cursor-pointer transition-all duration-200 hover:border-amber-500/20"
      style={{
        borderLeft: `2px solid ${scoreColor}`,
      }}
      onClick={onToggle}
    >
      {/* Header Row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0 flex items-center gap-2">
          {/* Type Badge */}
          <span
            className="shrink-0 px-1.5 py-0.5 rounded text-[8px] font-mono uppercase tracking-wider"
            style={{
              backgroundColor: `${getTypeColor(fact.node_type)}18`,
              color: getTypeColor(fact.node_type),
              border: `1px solid ${getTypeColor(fact.node_type)}25`,
            }}
          >
            {fact.node_type}
          </span>
          <p className="text-xs font-medium text-neutral-200 font-mono truncate">
            {shortLabel}
          </p>
        </div>

        {/* Score Badge */}
        <div
          className="shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono"
          style={{
            backgroundColor: `${scoreColor}12`,
            color: scoreColor,
          }}
        >
          <ScoreBar value={scorePct} color={scoreColor} />
          {scorePct}%
        </div>
      </div>

      {/* Summary (always visible, clamped) */}
      {fact.summary && (
        <p
          className={`text-[11px] text-neutral-400 leading-relaxed mt-1.5 ${
            isExpanded ? "" : "line-clamp-2"
          }`}
        >
          {cleanSummary(fact.summary)}
        </p>
      )}

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-3 pt-2 border-t border-white/[0.04] space-y-2">
          {/* Full Label */}
          <div>
            <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-wider">
              Origin
            </span>
            <p className="text-[10px] font-mono text-neutral-400 mt-0.5 break-all">
              {fact.label}
            </p>
          </div>

          {/* Tags */}
          {fact.tags && fact.tags.length > 0 && (
            <div>
              <span className="text-[9px] font-mono text-neutral-600 uppercase tracking-wider">
                Tags
              </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {fact.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 rounded text-[9px] font-mono
                               text-amber-400/80 bg-amber-500/[0.08] border border-amber-500/[0.12]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Meta */}
          <div className="flex items-center gap-3 text-[9px] font-mono text-neutral-600">
            <span>node:{fact.node_id}</span>
            <span>·</span>
            <span>type:{fact.node_type}</span>
            {fact.is_super_node && (
              <>
                <span>·</span>
                <span className="text-amber-500">⭐ super</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Expand indicator */}
      <div className="flex justify-center mt-1.5">
        <span
          className={`text-[8px] text-neutral-600 transition-transform duration-200 ${
            isExpanded ? "rotate-180" : ""
          }`}
        >
          ▼
        </span>
      </div>
    </div>
  );
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-8 h-1 rounded-full bg-white/[0.06] overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
      />
    </div>
  );
}

function FactSkeleton() {
  return (
    <div className="panel-overlay animate-pulse">
      <div className="flex items-center justify-between mb-2">
        <div className="h-3 w-32 rounded bg-white/[0.06]" />
        <div className="h-3 w-10 rounded bg-white/[0.04]" />
      </div>
      <div className="space-y-1.5">
        <div className="h-2 w-full rounded bg-white/[0.04]" />
        <div className="h-2 w-3/4 rounded bg-white/[0.04]" />
      </div>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function getFactShortLabel(label: string): string {
  if (!label) return "Fact";
  // "docs-grafo-concierge/grafo-concierge-api.md::..." → "grafo-concierge-api.md"
  const parts = label.split("::");
  const filePart = parts[0];
  const pathParts = filePart.split("/");
  return pathParts[pathParts.length - 1] || filePart;
}

function cleanSummary(summary: string): string {
  // Remove [DUMB] prefixes and clean up
  return summary.replace(/^\[DUMB\]\s*/i, "").trim();
}

const TYPE_COLORS: Record<string, string> = {
  FACT: "#ffa203",
  CLASS: "#818cf8",
  MODULE: "#22d3ee",
  FUNCTION: "#34d399",
  METHOD: "#a78bfa",
  DEFAULT: "#6b7280",
};

function getTypeColor(nodeType: string): string {
  return TYPE_COLORS[nodeType] ?? TYPE_COLORS.DEFAULT;
}
