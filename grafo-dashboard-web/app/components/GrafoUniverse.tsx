"use client";

/**
 * GrafoUniverse — Safe Wrapper for 3D Rendering Engine
 *
 * Uses next/dynamic with ssr: false to guarantee that the WebGL component
 * is NEVER rendered on the server (where window/document do not exist).
 *
 * Responsibilities:
 * - Dynamic import of ForceGraph3DRenderer
 * - Management of responsive dimensions
 * - Tooltip on hover
 * - Loading skeleton while 3D initializes
 */

import { useState, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import type { ForceGraphData, ForceGraphNode } from "@/lib/graph/types";
import type { TopologyLoadingState } from "@/app/hooks/useGraphTopology";

// ─── Dynamic Import (SSR: false — SDD Contract) ────────────────────────────

const ForceGraph3DRenderer = dynamic(
  () => import("./ForceGraph3DRenderer"),
  {
    ssr: false,
    loading: () => <GraphSkeleton message="Initializing WebGL engine..." />,
  }
);

// ─── Props ──────────────────────────────────────────────────────────────────

interface GrafoUniverseProps {
  graphData: ForceGraphData;
  loadingState: TopologyLoadingState;
  error: string | null;
  stats: {
    totalNodes: number;
    totalLinks: number;
    nodeTypes: Record<string, number>;
  };
  dimensionMode: "2D" | "3D";
  onNodeClick: (node: ForceGraphNode | null) => void;
  onReload: () => void;
}

// ─── Component ──────────────────────────────────────────────────────────────

export function GrafoUniverse({
  graphData,
  loadingState,
  error,
  stats,
  dimensionMode,
  onNodeClick,
  onReload,
}: GrafoUniverseProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<ForceGraphNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // ─── Responsive dimensions ──────────────────────────────────────────

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    observer.observe(container);

    // Initial measure
    setDimensions({
      width: container.clientWidth,
      height: container.clientHeight,
    });

    return () => observer.disconnect();
  }, []);

  // ─── Track mouse for tooltip position ─────────────────────────────────

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setTooltipPos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // ─── Handlers ─────────────────────────────────────────────────────────

  const handleNodeHover = useCallback((node: ForceGraphNode | null) => {
    setHoveredNode(node);
  }, []);

  const handleNodeClick = useCallback(
    (node: ForceGraphNode | null) => {
      onNodeClick(node);
    },
    [onNodeClick]
  );

  // ─── Render States ────────────────────────────────────────────────────

  if (error) {
    return (
      <div ref={containerRef} className="graph-container">
        <div className="flex flex-col items-center justify-center h-full text-center px-6">
          <span className="text-4xl mb-4">⚠️</span>
          <h3 className="text-lg font-semibold text-red-400 mb-2">
            Error loading topology
          </h3>
          <p className="text-neutral-500 text-sm mb-4 max-w-md">{error}</p>
          <button
            onClick={onReload}
            className="px-4 py-2 rounded-lg text-sm font-medium text-neutral-200
                       bg-white/[0.06] border border-white/[0.08]
                       hover:bg-white/[0.10] transition-all cursor-pointer"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (loadingState === "idle" || loadingState === "loading-nodes") {
    return (
      <div ref={containerRef} className="graph-container">
        <GraphSkeleton
          message={
            loadingState === "idle"
              ? "Waiting for MCP connection..."
              : "Loading Graph nodes..."
          }
        />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="graph-container relative">
      {/* 3D Graph */}
      <ForceGraph3DRenderer
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        dimensionMode={dimensionMode}
        onNodeHover={handleNodeHover}
        onNodeClick={handleNodeClick}
      />

      {/* Stats Overlay */}
      <div className="absolute top-4 right-4 flex gap-3 pointer-events-none">
        <StatBadge label="Nodes" value={stats.totalNodes} />
        <StatBadge label="Edges" value={stats.totalLinks} />
      </div>

      {/* Loading edges indicator */}
      {loadingState === "loading-edges" && (
        <div className="absolute top-4 left-4 flex items-center gap-2
                        px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-sm
                        border border-amber-500/20 text-xs text-amber-400 font-mono">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          Mapping edges...
        </div>
      )}

      {/* Hover Tooltip */}
      {hoveredNode && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{
            left: tooltipPos.x + 16,
            top: tooltipPos.y - 8,
          }}
        >
          <NodeTooltip node={hoveredNode} />
        </div>
      )}
    </div>
  );
}

// ─── Sub Components ─────────────────────────────────────────────────────────

function GraphSkeleton({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      {/* Animated orbital rings */}
      <div className="relative w-24 h-24 mb-6">
        <div className="absolute inset-0 rounded-full border border-white/[0.06] animate-spin"
             style={{ animationDuration: "8s" }} />
        <div className="absolute inset-2 rounded-full border border-white/[0.08] animate-spin"
             style={{ animationDuration: "5s", animationDirection: "reverse" }} />
        <div className="absolute inset-4 rounded-full border border-white/[0.10] animate-spin"
             style={{ animationDuration: "3s" }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full bg-[#ffa203]/60 animate-pulse" />
        </div>
      </div>
      <p className="text-neutral-500 text-sm font-mono">{message}</p>
    </div>
  );
}

function StatBadge({ label, value }: { label: string; value: number }) {
  return (
    <div className="px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-sm
                    border border-white/[0.08] text-xs font-mono">
      <span className="text-neutral-500">{label} </span>
      <span className="text-neutral-200">{value.toLocaleString()}</span>
    </div>
  );
}

function NodeTooltip({ node }: { node: ForceGraphNode }) {
  const truncatedSummary = node.summary
    ? node.summary.length > 150
      ? node.summary.slice(0, 147) + "..."
      : node.summary
    : null;

  return (
    <div className="max-w-xs p-3 rounded-xl bg-neutral-900/95 backdrop-blur-md
                    border border-white/[0.10] shadow-2xl shadow-black/50">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: node.color }}
        />
        <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider">
          {node.node_type}
        </span>
      </div>

      {/* Label */}
      <p className="text-sm font-medium text-neutral-100 font-mono leading-snug mb-1">
        {node.label}
      </p>

      {/* Summary */}
      {truncatedSummary && (
        <p className="text-xs text-neutral-400 leading-relaxed">
          {truncatedSummary}
        </p>
      )}

      {/* Tags */}
      {node.tags && node.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {node.tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 rounded text-[9px] font-mono
                         text-neutral-400 bg-white/[0.04] border border-white/[0.06]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
