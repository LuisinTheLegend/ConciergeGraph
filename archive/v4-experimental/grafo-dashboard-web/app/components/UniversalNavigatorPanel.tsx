"use client";

/**
 * UniversalNavigatorPanel — Navigation Tab and Dynamic Filters
 *
 * Allows filtering nodes and edges by:
 * - Project/Module (root directory extracted from the label)
 * - Node Type (provenance)
 *
 * Filtering is done entirely client-side (Zero Network).
 */

import { NODE_TYPE_COLORS } from "@/lib/graph/types";

interface UniversalNavigatorPanelProps {
  totalNodesCount: number;
  filteredNodesCount: number;
  totalLinksCount: number;
  filteredLinksCount: number;

  // Projects
  availableProjects: { name: string; count: number }[];
  selectedProjects: Set<string>;
  onToggleProject: (project: string) => void;
  onSelectAllProjects: () => void;
  onClearProjects: () => void;

  // Node Types
  availableTypes: { name: string; count: number }[];
  selectedTypes: Set<string>;
  onToggleType: (type: string) => void;
  onSelectAllTypes: () => void;
  onClearTypes: () => void;
}

export function UniversalNavigatorPanel({
  totalNodesCount,
  filteredNodesCount,
  totalLinksCount,
  filteredLinksCount,
  availableProjects,
  selectedProjects,
  onToggleProject,
  onSelectAllProjects,
  onClearProjects,
  availableTypes,
  selectedTypes,
  onToggleType,
  onSelectAllTypes,
  onClearTypes,
}: UniversalNavigatorPanelProps) {
  const nodePct = totalNodesCount > 0 ? Math.round((filteredNodesCount / totalNodesCount) * 100) : 0;
  const linkPct = totalLinksCount > 0 ? Math.round((filteredLinksCount / totalLinksCount) * 100) : 0;

  return (
    <div className="space-y-5">
      {/* ─── Stats Indicator ────────────────────────────────────────────────── */}
      <div className="panel-overlay space-y-3">
        <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
          <span>🧭</span> Display Status
        </h3>
        
        {/* Visible nodes progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px] font-mono">
            <span className="text-neutral-400">Visible Nodes</span>
            <span className="text-amber-400 font-medium">
              {filteredNodesCount.toLocaleString()} <span className="text-neutral-600">/ {totalNodesCount.toLocaleString()} ({nodePct}%)</span>
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full bg-amber-500 transition-all duration-500"
              style={{ width: `${nodePct}%` }}
            />
          </div>
        </div>

        {/* Active edges progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px] font-mono">
            <span className="text-neutral-400">Active Edges</span>
            <span className="text-indigo-400 font-medium">
              {filteredLinksCount.toLocaleString()} <span className="text-neutral-600">/ {totalLinksCount.toLocaleString()} ({linkPct}%)</span>
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${linkPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* ─── Node Types ──────────────────────────────────────────────────── */}
      <div className="panel-overlay space-y-3">
        <div className="flex items-center justify-between border-b border-white/[0.04] pb-2">
          <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
            <span>🏷️</span> Node Types
          </h3>
          <div className="flex gap-2 text-[9px] font-mono">
            <button
              onClick={onSelectAllTypes}
              className="text-neutral-400 hover:text-white transition-colors cursor-pointer"
            >
              All
            </button>
            <span className="text-neutral-700">|</span>
            <button
              onClick={onClearTypes}
              className="text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer"
            >
              None
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {availableTypes.map((type) => {
            const isChecked = selectedTypes.has(type.name);
            const color = NODE_TYPE_COLORS[type.name] ?? NODE_TYPE_COLORS.DEFAULT;
            return (
              <button
                key={type.name}
                onClick={() => onToggleType(type.name)}
                className={`flex items-center justify-between p-2 rounded-lg border text-left transition-all duration-150 cursor-pointer
                           ${isChecked 
                             ? "bg-white/[0.03] border-amber-500/35 shadow-[0_0_8px_rgba(255,162,3,0.04)]" 
                             : "bg-transparent border-white/[0.04] opacity-50 hover:opacity-80"
                           }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-[11px] font-mono font-medium text-neutral-200 truncate uppercase">
                    {type.name}
                  </span>
                </div>
                <span className="text-[9px] font-mono text-neutral-500 ml-1.5 shrink-0">
                  {type.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── Projects / Modules ────────────────────────────────────────────── */}
      <div className="panel-overlay space-y-3">
        <div className="flex items-center justify-between border-b border-white/[0.04] pb-2">
          <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
            <span>📂</span> Projects & Modules
          </h3>
          <div className="flex gap-2 text-[9px] font-mono">
            <button
              onClick={onSelectAllProjects}
              className="text-neutral-400 hover:text-white transition-colors cursor-pointer"
            >
              All
            </button>
            <span className="text-neutral-700">|</span>
            <button
              onClick={onClearProjects}
              className="text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer"
            >
              None
            </button>
          </div>
        </div>

        <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
          {availableProjects.map((proj) => {
            const isChecked = selectedProjects.has(proj.name);
            return (
              <label
                key={proj.name}
                className={`flex items-center justify-between p-2 rounded-lg border transition-all duration-150 cursor-pointer
                           ${isChecked
                             ? "bg-white/[0.03] border-amber-500/25 text-neutral-200"
                             : "bg-transparent border-white/[0.04] text-neutral-500 hover:text-neutral-400"
                           }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleProject(proj.name)}
                    className="w-3.5 h-3.5 rounded border-white/[0.08] bg-transparent text-amber-500 focus:ring-0 cursor-pointer"
                  />
                  <span className="text-[11px] font-mono truncate font-medium">
                    {proj.name}
                  </span>
                </div>
                <span className="text-[9px] font-mono text-neutral-500 shrink-0">
                  {proj.count}
                </span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}
