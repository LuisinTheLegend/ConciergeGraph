"use client";

/**
 * CoreMemoryPanel — Core Memory Lens (Agent Identity)
 *
 * Displays the agent's persistent memory blocks:
 * - persona: Who the agent is
 * - context_rules: Architecture/behavior rules
 * - preferred_language: Preferred language
 * - Other custom blocks
 */

import type { MemoryBlock, CognitiveLoadingState } from "../hooks/useCognitiveData";

// ─── Block Label → Display Config ───────────────────────────────────────────

const BLOCK_CONFIG: Record<string, { icon: string; title: string; accent: string }> = {
  persona: {
    icon: "🧠",
    title: "Persona",
    accent: "#ffa203",
  },
  context_rules: {
    icon: "📐",
    title: "Context Rules",
    accent: "#22d3ee",
  },
  preferred_language: {
    icon: "🌐",
    title: "Preferred Language",
    accent: "#34d399",
  },
};

function getBlockConfig(label: string) {
  return (
    BLOCK_CONFIG[label] ?? {
      icon: "📦",
      title: label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      accent: "#a78bfa",
    }
  );
}

// ─── Props ──────────────────────────────────────────────────────────────────

interface CoreMemoryPanelProps {
  blocks: MemoryBlock[];
  loadingState: CognitiveLoadingState;
}

// ─── Component ──────────────────────────────────────────────────────────────

export function CoreMemoryPanel({ blocks, loadingState }: CoreMemoryPanelProps) {
  const isLoading =
    loadingState === "loading-memory" || loadingState === "idle";

  if (isLoading) {
    return (
      <div className="space-y-3">
        <SectionHeader />
        <MemoryBlockSkeleton />
        <MemoryBlockSkeleton />
        <MemoryBlockSkeleton />
      </div>
    );
  }

  if (blocks.length === 0) {
    return (
      <div className="space-y-3">
        <SectionHeader />
        <div className="panel-overlay text-center py-8">
          <span className="text-3xl mb-3 block">🫥</span>
          <p className="text-sm text-neutral-500">
            No memory block found.
          </p>
          <p className="text-xs text-neutral-600 mt-1">
            Use <code className="text-amber-500/70 text-[10px]">concierge_set_memory</code> to define identity.
          </p>
        </div>
      </div>
    );
  }

  // Sort: persona first, context_rules second, rest by label
  const sorted = [...blocks].sort((a, b) => {
    const order = ["persona", "context_rules", "preferred_language"];
    const aIdx = order.indexOf(a.block_label);
    const bIdx = order.indexOf(b.block_label);
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
    if (aIdx !== -1) return -1;
    if (bIdx !== -1) return 1;
    return a.block_label.localeCompare(b.block_label);
  });

  return (
    <div className="space-y-3">
      <SectionHeader count={blocks.length} />
      {sorted.map((block) => (
        <MemoryBlockCard key={block.id} block={block} />
      ))}
    </div>
  );
}

// ─── Sub Components ─────────────────────────────────────────────────────────

function SectionHeader({ count }: { count?: number }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
        <span className="text-base">🧠</span>
        Core Memory
      </h3>
      {count !== undefined && (
        <span className="text-[10px] font-mono text-neutral-600 px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
          {count} {count === 1 ? "block" : "blocks"}
        </span>
      )}
    </div>
  );
}

function MemoryBlockCard({ block }: { block: MemoryBlock }) {
  const config = getBlockConfig(block.block_label);

  // For context_rules, render each line as a list item
  const isRules = block.block_label === "context_rules";
  const lines = isRules
    ? block.content
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
    : [];

  const formattedDate = new Date(block.updated_at + "Z").toLocaleString(
    "en-US",
    {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }
  );

  return (
    <div
      className="panel-overlay transition-all duration-300 hover:border-white/[0.12]"
      style={{
        borderLeft: `2px solid ${config.accent}`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">{config.icon}</span>
          <span
            className="text-xs font-semibold tracking-wide uppercase"
            style={{ color: config.accent }}
          >
            {config.title}
          </span>
        </div>
        <span className="text-[9px] font-mono text-neutral-600">
          {formattedDate}
        </span>
      </div>

      {/* Content */}
      {isRules ? (
        <ol className="space-y-1.5 text-xs text-neutral-300 leading-relaxed">
          {lines.map((line, i) => {
            // Remove numbering prefix if present (e.g., "1. ")
            const cleanLine = line.replace(/^\d+\.\s*/, "");
            return (
              <li key={i} className="flex gap-2">
                <span
                  className="shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-mono mt-0.5"
                  style={{
                    backgroundColor: `${config.accent}15`,
                    color: config.accent,
                  }}
                >
                  {i + 1}
                </span>
                <span>{cleanLine}</span>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-xs text-neutral-300 leading-relaxed">
          {block.content}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/[0.04]">
        <span className="text-[9px] font-mono text-neutral-600">
          {block.scope_type}/{block.scope_id}
        </span>
        <span className="text-neutral-700">·</span>
        <span className="text-[9px] font-mono text-neutral-600">
          id:{block.id}
        </span>
      </div>
    </div>
  );
}

function MemoryBlockSkeleton() {
  return (
    <div className="panel-overlay animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-5 h-5 rounded-full bg-white/[0.06]" />
        <div className="h-3 w-24 rounded bg-white/[0.06]" />
      </div>
      <div className="space-y-2">
        <div className="h-2.5 w-full rounded bg-white/[0.04]" />
        <div className="h-2.5 w-4/5 rounded bg-white/[0.04]" />
        <div className="h-2.5 w-3/5 rounded bg-white/[0.04]" />
      </div>
    </div>
  );
}
