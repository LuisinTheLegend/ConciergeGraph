"use client";

/**
 * components/topology/CodeGraphViewer.tsx — SDD-SURVIVAL-28
 *
 * Painel 1: Visualizador de Topologia de Código (Force-Directed Graph 2D).
 *
 * Features:
 * - Canvas 2D ultralight memory rendering via react-force-graph-2d.
 * - Files rendered as nodes, imports/dependencies as directed edges.
 * - Natural directory grouping with curated community color palette.
 * - Pulsing halo animation in Canvas 2D for nodes marked as is_dirty = 1 in SQLite WAL.
 * - Interactive node selection, zoom-to-fit, and filter by dirty-only state.
 */

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import type { DirtyFile } from "@/lib/telemetry/types";

// Dynamically import react-force-graph-2d to avoid SSR canvas issues
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-zinc-950/80 text-xs font-mono text-zinc-500">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-ping rounded-full bg-emerald-400" />
        Carregando Topologia Canvas 2D...
      </div>
    </div>
  ),
});

export interface TopologyNode {
  id: string | number;
  name: string;
  path?: string;
  community?: string;
  node_type?: string;
  is_dirty?: boolean | number;
  val?: number; // size
  x?: number;
  y?: number;
  color?: string;
}

export interface TopologyLink {
  source: string | number | any;
  target: string | number | any;
  edge_type?: string;
}

export interface CodeGraphViewerProps {
  nodes?: TopologyNode[];
  links?: TopologyLink[];
  dirtyQueue?: DirtyFile[];
  onNodeSelect?: (node: TopologyNode | null) => void;
  height?: number | string;
  className?: string;
}

// Community Palette for directories
const COMMUNITY_COLORS: Record<string, string> = {
  core: "#38bdf8",       // Sky Blue
  agent: "#a855f7",      // Purple
  agents: "#c084fc",     // Light Purple
  interface: "#34d399",  // Emerald
  storage: "#f59e0b",    // Amber
  ingestion: "#ec4899",  // Pink
  tests: "#94a3b8",      // Slate
  docs: "#6ee7b7",       // Teal
  default: "#64748b",    // Gray
};

function extractCommunity(pathOrName: string): string {
  if (!pathOrName) return "default";
  const normalized = pathOrName.replace(/\\/g, "/");
  const parts = normalized.split("/");
  if (parts.length > 1) {
    const dir = parts[0].toLowerCase();
    if (COMMUNITY_COLORS[dir]) return dir;
  }
  return "default";
}

export function CodeGraphViewer({
  nodes: propNodes,
  links: propLinks,
  dirtyQueue = [],
  onNodeSelect,
  height = "100%",
  className = "",
}: CodeGraphViewerProps) {
  const fgRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [filterDirtyOnly, setFilterDirtyOnly] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [pulsePhase, setPulsePhase] = useState(0);

  // Animation frame loop for pulsing dirty nodes
  useEffect(() => {
    let animId: number;
    const animate = () => {
      setPulsePhase((prev) => (prev + 0.05) % (Math.PI * 2));
      animId = requestAnimationFrame(animate);
    };
    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Quick lookup set for dirty paths
  const dirtyPathSet = useMemo(() => {
    const set = new Set<string>();
    dirtyQueue.forEach((d) => {
      set.add(d.path.toLowerCase().replace(/\\/g, "/"));
    });
    return set;
  }, [dirtyQueue]);

  // Generate fallback demonstration graph if propNodes is empty
  const defaultGraph = useMemo(() => {
    const mockNodes: TopologyNode[] = [
      { id: "core/hsm_engine.py", name: "hsm_engine.py", path: "core/hsm_engine.py", community: "core", val: 12 },
      { id: "core/mcp_governor.py", name: "mcp_governor.py", path: "core/mcp_governor.py", community: "core", val: 9 },
      { id: "core/checkpointer.py", name: "checkpointer.py", path: "core/checkpointer.py", community: "core", val: 8 },
      { id: "core/database.py", name: "database.py", path: "core/database.py", community: "core", val: 10 },
      { id: "agent/run_agent.py", name: "run_agent.py", path: "agent/run_agent.py", community: "agent", val: 11 },
      { id: "agent/agent_prompts.py", name: "agent_prompts.py", path: "agent/agent_prompts.py", community: "agent", val: 7 },
      { id: "interface/telemetry_api.py", name: "telemetry_api.py", path: "interface/telemetry_api.py", community: "interface", val: 10 },
      { id: "interface/mcp_server.py", name: "mcp_server.py", path: "interface/mcp_server.py", community: "interface", val: 11 },
      { id: "storage/store.py", name: "store.py", path: "storage/store.py", community: "storage", val: 8 },
      { id: "tests/test_hsm_transition_hooks_and_delta.py", name: "test_hsm.py", path: "tests/test_hsm_transition_hooks_and_delta.py", community: "tests", val: 6 },
      { id: "tests/test_agent_hsm_coupling.py", name: "test_agent.py", path: "tests/test_agent_hsm_coupling.py", community: "tests", val: 6 },
    ];

    const mockLinks: TopologyLink[] = [
      { source: "agent/run_agent.py", target: "core/hsm_engine.py" },
      { source: "agent/run_agent.py", target: "agent/agent_prompts.py" },
      { source: "agent/run_agent.py", target: "core/mcp_governor.py" },
      { source: "core/hsm_engine.py", target: "core/checkpointer.py" },
      { source: "core/hsm_engine.py", target: "core/database.py" },
      { source: "core/hsm_engine.py", target: "core/mcp_governor.py" },
      { source: "interface/telemetry_api.py", target: "core/hsm_engine.py" },
      { source: "interface/mcp_server.py", target: "interface/telemetry_api.py" },
      { source: "tests/test_hsm_transition_hooks_and_delta.py", target: "core/hsm_engine.py" },
      { source: "tests/test_agent_hsm_coupling.py", target: "agent/run_agent.py" },
    ];

    return { nodes: mockNodes, links: mockLinks };
  }, []);

  // Filtered & enriched graph data
  const graphData = useMemo(() => {
    const rawNodes = propNodes && propNodes.length > 0 ? propNodes : defaultGraph.nodes;
    const rawLinks = propLinks && propLinks.length > 0 ? propLinks : defaultGraph.links;

    const processedNodes = rawNodes.map((node) => {
      const pathStr = (node.path || String(node.id)).toLowerCase().replace(/\\/g, "/");
      const isDirty = node.is_dirty === 1 || node.is_dirty === true || dirtyPathSet.has(pathStr);
      const community = node.community || extractCommunity(node.path || node.name);
      const baseColor = COMMUNITY_COLORS[community] || COMMUNITY_COLORS.default;

      return {
        ...node,
        community,
        is_dirty: isDirty,
        color: isDirty ? "#eab308" : baseColor,
        val: node.val || 7,
      };
    });

    let filteredNodes = processedNodes;
    if (filterDirtyOnly) {
      filteredNodes = filteredNodes.filter((n) => n.is_dirty);
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filteredNodes = filteredNodes.filter(
        (n) => n.name.toLowerCase().includes(term) || (n.path && n.path.toLowerCase().includes(term))
      );
    }

    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredLinks = rawLinks.filter((l) => {
      const sourceId = typeof l.source === "object" ? l.source.id : l.source;
      const targetId = typeof l.target === "object" ? l.target.id : l.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });

    return { nodes: filteredNodes, links: filteredLinks };
  }, [propNodes, propLinks, defaultGraph, dirtyPathSet, filterDirtyOnly, searchTerm]);

  // Zoom-to-fit action
  const handleZoomFit = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 30);
    }
  }, []);

  // Custom 2D Canvas Node Rendering with Pulsing Halo for Dirty Nodes
  const renderCustomNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const { x, y, val = 7, color = "#38bdf8", is_dirty, name } = node;
      if (x === undefined || y === undefined) return;

      const radius = Math.max(3, Math.sqrt(val) * 2.5);

      // 1. Pulsing Halo if is_dirty === 1 (Aura amarela pulsante)
      if (is_dirty) {
        const pulseFactor = (Math.sin(pulsePhase) + 1) / 2; // 0 to 1
        const haloRadius = radius + 3 + pulseFactor * 5;
        const alpha = 0.2 + pulseFactor * 0.4;

        ctx.beginPath();
        ctx.arc(x, y, haloRadius, 0, 2 * Math.PI, false);
        ctx.fillStyle = `rgba(234, 179, 8, ${alpha})`;
        ctx.fill();

        ctx.lineWidth = 1.5 / globalScale;
        ctx.strokeStyle = `rgba(250, 204, 21, ${0.4 + pulseFactor * 0.5})`;
        ctx.stroke();
      }

      // 2. Main node circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = is_dirty ? "#eab308" : color;
      ctx.fill();

      // Selected ring
      if (selectedNode && selectedNode.id === node.id) {
        ctx.lineWidth = 2.5 / globalScale;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
      } else {
        ctx.lineWidth = 1 / globalScale;
        ctx.strokeStyle = "rgba(0,0,0,0.5)";
        ctx.stroke();
      }

      // 3. Node label when zoomed in or dirty
      if (globalScale > 1.2 || is_dirty || (selectedNode && selectedNode.id === node.id)) {
        const fontSize = Math.max(9 / globalScale, 2.5);
        ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = is_dirty ? "#fef08a" : "#f1f5f9";
        ctx.fillText(name, x, y + radius + fontSize + 1);
      }
    },
    [pulsePhase, selectedNode]
  );

  return (
    <div className={`relative flex h-full w-full flex-col overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950 shadow-2xl ${className}`}>
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-sky-400 ring-2 ring-sky-400/20" />
          <span className="font-semibold text-zinc-200">1. Topologia de Código</span>
          <span className="font-mono text-zinc-500 text-[10px]">
            ({graphData.nodes.length} nós, {graphData.links.length} arestas)
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Buscar arquivo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-6 w-28 rounded bg-zinc-900 px-2 text-[10px] text-zinc-300 placeholder-zinc-600 border border-zinc-800 focus:border-sky-500 focus:outline-none"
          />

          <button
            onClick={() => setFilterDirtyOnly((prev) => !prev)}
            className={`flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium transition ${
              filterDirtyOnly
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "bg-zinc-800/80 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            Dirty Only
          </button>

          <button
            onClick={handleZoomFit}
            className="rounded bg-zinc-800/80 px-2 py-0.5 text-[10px] text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition"
          >
            Ajustar
          </button>
        </div>
      </div>

      {/* Force-Directed Canvas */}
      <div className="relative flex-1 w-full bg-zinc-950 overflow-hidden" style={{ minHeight: 280 }}>
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeCanvasObject={renderCustomNode}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            const { x, y, val = 7 } = node;
            const radius = Math.max(3, Math.sqrt(val) * 2.5) + 4;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
          linkColor={() => "rgba(148, 163, 184, 0.2)"}
          linkWidth={1}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={0.9}
          linkDirectionalArrowColor={() => "rgba(148, 163, 184, 0.4)"}
          onNodeClick={(node: any) => {
            setSelectedNode(node);
            if (onNodeSelect) onNodeSelect(node);
          }}
          onBackgroundClick={() => {
            setSelectedNode(null);
            if (onNodeSelect) onNodeSelect(null);
          }}
          cooldownTicks={60}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.3}
        />

        {/* Community Legend Chips */}
        <div className="absolute bottom-2 left-2 flex flex-wrap gap-1.5 rounded-lg border border-zinc-800/60 bg-zinc-900/80 p-1.5 text-[9px] backdrop-blur-md">
          {Object.entries(COMMUNITY_COLORS)
            .filter(([k]) => k !== "default")
            .map(([comm, col]) => (
              <div key={comm} className="flex items-center gap-1 font-mono text-zinc-400">
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: col }} />
                <span>{comm}</span>
              </div>
            ))}
          <div className="flex items-center gap-1 font-mono text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
            <span>is_dirty=1</span>
          </div>
        </div>

        {/* Selected Node Inspector Badge */}
        {selectedNode && (
          <div className="absolute top-2 right-2 max-w-xs rounded-lg border border-zinc-700 bg-zinc-900/90 p-2 text-xs shadow-xl backdrop-blur-md">
            <div className="flex items-center justify-between gap-2 border-b border-zinc-800 pb-1 font-semibold text-zinc-200">
              <span className="truncate">{selectedNode.name}</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                ✕
              </button>
            </div>
            <div className="mt-1.5 space-y-1 font-mono text-[10px] text-zinc-400">
              <p className="truncate">Caminho: {selectedNode.path || selectedNode.id}</p>
              <p>Comunidade: {selectedNode.community}</p>
              <p className="flex items-center gap-1">
                Status:
                {selectedNode.is_dirty ? (
                  <span className="text-amber-400 font-semibold">🟡 DIRTY (WAL sync pendente)</span>
                ) : (
                  <span className="text-emerald-400">🟢 LIMPO</span>
                )}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
