"use client";

/**
 * InspectorDrawer — Side Panel for Property Inspection (Slice Front-5)
 *
 * Displays detailed metadata of the selected node:
 * - Name/Symbol (with quick copy button)
 * - Node Type (with colored badge)
 * - Descriptive Summary
 * - Tags
 * - Active Relationships:
 *   - Callers (Incoming: Nodes that point/call this node)
 *   - Callees (Outgoing: Nodes that this node points/calls)
 */

import { useMemo } from "react";
import type { ForceGraphNode, ForceGraphLink } from "@/lib/graph/types";
import { NODE_TYPE_COLORS } from "@/lib/graph/types";

interface InspectorDrawerProps {
  node: ForceGraphNode | null;
  allNodes: ForceGraphNode[];
  allLinks: ForceGraphLink[];
  onClose: () => void;
  onSelectNode: (node: ForceGraphNode) => void;
  isPanelOpen?: boolean;
}

export function InspectorDrawer({
  node,
  allNodes,
  allLinks,
  onClose,
  onSelectNode,
  isPanelOpen = false,
}: InspectorDrawerProps) {
  if (!node) return null;

  // Find incoming and outgoing connections
  const { incoming, outgoing } = useMemo(() => {
    const inc: ForceGraphNode[] = [];
    const out: ForceGraphNode[] = [];

    allLinks.forEach((link) => {
      const srcId = typeof link.source === "object" ? (link.source as any).id : link.source;
      const tgtId = typeof link.target === "object" ? (link.target as any).id : link.target;

      if (srcId === node.id) {
        // This node points to another
        const targetNode = allNodes.find((n) => n.id === tgtId);
        if (targetNode && !out.some((n) => n.id === targetNode.id)) {
          out.push(targetNode);
        }
      } else if (tgtId === node.id) {
        // Another node points to this one
        const sourceNode = allNodes.find((n) => n.id === srcId);
        if (sourceNode && !inc.some((n) => n.id === sourceNode.id)) {
          inc.push(sourceNode);
        }
      }
    });

    return {
      incoming: inc.sort((a, b) => a.label.localeCompare(b.label)),
      outgoing: out.sort((a, b) => a.label.localeCompare(b.label)),
    };
  }, [node, allNodes, allLinks]);

  const color = NODE_TYPE_COLORS[node.node_type] ?? NODE_TYPE_COLORS.DEFAULT;

  const handleCopyLabel = () => {
    navigator.clipboard.writeText(node.label);
  };

  return (
    <div
      className={`absolute top-4 bottom-4 w-[380px] z-40 flex flex-col
                 bg-[#161b22]/90 backdrop-blur-xl border border-white/[0.08] rounded-2xl
                 shadow-[0_20px_50px_rgba(0,0,0,0.5)] transition-all duration-300
                 ${isPanelOpen ? "right-[436px]" : "right-4"}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06] shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm">🧭</span>
          <h2 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider font-mono">
            Inspection Panel
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-neutral-500 hover:text-neutral-300 transition-colors p-1 hover:bg-white/[0.04] rounded-lg cursor-pointer"
          title="Close panel"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Identity */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span
              className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-wide uppercase"
              style={{ backgroundColor: `${color}22`, color }}
            >
              {node.node_type}
            </span>
            <button
              onClick={handleCopyLabel}
              className="text-[10px] font-mono text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer"
              title="Copy symbol name"
            >
              📋 Copy
            </button>
          </div>
          <h1 className="text-sm font-semibold text-neutral-200 font-mono break-all leading-relaxed bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
            {node.label}
          </h1>
        </div>

        {/* Summary */}
        {node.summary && (
          <div className="space-y-1">
            <h3 className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider font-mono">
              Pipeline Description
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed font-sans">
              {node.summary}
            </p>
          </div>
        )}

        {/* Tags */}
        {node.tags && node.tags.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider font-mono">
              Semantic Tags
            </h3>
            <div className="flex flex-wrap gap-1">
              {node.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded text-[9px] font-mono text-neutral-400 bg-white/[0.03] border border-white/[0.05]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Relationships / Web */}
        <div className="space-y-4 pt-2 border-t border-white/[0.04]">
          {/* Incoming connections */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono flex items-center justify-between">
              <span>📥 Callers</span>
              <span className="text-neutral-600 font-normal">{incoming.length}</span>
            </h3>
            {incoming.length === 0 ? (
              <p className="text-[10px] text-neutral-600 font-mono italic">No external dependencies</p>
            ) : (
              <div className="space-y-1 max-h-[140px] overflow-y-auto pr-1">
                {incoming.map((src) => {
                  const srcColor = NODE_TYPE_COLORS[src.node_type] ?? NODE_TYPE_COLORS.DEFAULT;
                  return (
                    <button
                      key={src.id}
                      onClick={() => onSelectNode(src)}
                      className="w-full flex items-center justify-between p-1.5 rounded text-left
                                 hover:bg-white/[0.04] transition-colors group cursor-pointer text-xs"
                    >
                      <span className="font-mono text-neutral-400 truncate group-hover:text-neutral-200">
                        {src.label.split("::").pop()}
                      </span>
                      <span
                        className="text-[8px] font-mono uppercase px-1 rounded shrink-0 ml-1.5"
                        style={{ backgroundColor: `${srcColor}15`, color: srcColor }}
                      >
                        {src.node_type}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Outgoing connections */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono flex items-center justify-between">
              <span>📤 Callees</span>
              <span className="text-neutral-600 font-normal">{outgoing.length}</span>
            </h3>
            {outgoing.length === 0 ? (
              <p className="text-[10px] text-neutral-600 font-mono italic">Does not make external calls</p>
            ) : (
              <div className="space-y-1 max-h-[140px] overflow-y-auto pr-1">
                {outgoing.map((tgt) => {
                  const tgtColor = NODE_TYPE_COLORS[tgt.node_type] ?? NODE_TYPE_COLORS.DEFAULT;
                  return (
                    <button
                      key={tgt.id}
                      onClick={() => onSelectNode(tgt)}
                      className="w-full flex items-center justify-between p-1.5 rounded text-left
                                 hover:bg-white/[0.04] transition-colors group cursor-pointer text-xs"
                    >
                      <span className="font-mono text-neutral-400 truncate group-hover:text-neutral-200">
                        {tgt.label.split("::").pop()}
                      </span>
                      <span
                        className="text-[8px] font-mono uppercase px-1 rounded shrink-0 ml-1.5"
                        style={{ backgroundColor: `${tgtColor}15`, color: tgtColor }}
                      >
                        {tgt.node_type}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
