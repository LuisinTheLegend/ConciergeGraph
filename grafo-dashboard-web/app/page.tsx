"use client";

/**
 * Grafo Dashboard — Cognitive HUD + 3D Engine + Telemetry
 *
 * Slice Front-4 + SDD-SURVIVAL-16:
 * - Real-time SSE Telemetry integration (FastAPI stream on port 8000)
 * - Memory Integrity Board (KPIs & Dirty Queue sync)
 * - Self-Healing Console & Operational Reconciler Trigger
 * - Agent Checkpoints Timeline & Time-Travel visualization
 * - Universal Navigation Tab with Client-side filtering (Zero Network)
 * - FastMCP SSE diagnostics & Cognitive HUD
 */

import { useState, useMemo, useCallback, startTransition } from "react";
import { useMcpConnection } from "./hooks/useMcpConnection";
import { useGraphTopology } from "./hooks/useGraphTopology";
import { useCognitiveData } from "./hooks/useCognitiveData";
import { useTelemetryStream } from "./hooks/useTelemetryStream";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { ToolsList } from "./components/ToolsList";
import { GrafoUniverse } from "./components/GrafoUniverse";
import { CoreMemoryPanel } from "./components/CoreMemoryPanel";
import { SemanticFactsPanel } from "./components/SemanticFactsPanel";
import { UniversalNavigatorPanel } from "./components/UniversalNavigatorPanel";
import { InspectorDrawer } from "./components/InspectorDrawer";
import { MemoryIntegrityBoard } from "./components/MemoryIntegrityBoard";
import { SelfHealingConsole } from "./components/SelfHealingConsole";
import { AgentTimelinePanel } from "./components/AgentTimelinePanel";
import { CodeGraphViewer } from "@/components/topology/CodeGraphViewer";
import { QuotaGauges } from "@/components/governor/QuotaGauges";
import { HSMStateInspector } from "@/components/hsm/HSMStateInspector";
import { LiveEventFeed } from "@/components/telemetry/LiveEventFeed";
import type { ForceGraphNode } from "@/lib/graph/types";
import { NODE_TYPE_COLORS } from "@/lib/graph/types";

// ─── Tab Types ──────────────────────────────────────────────────────────────

type PanelTab =
  | "navigator"
  | "integrity"
  | "healing"
  | "timeline"
  | "memory"
  | "facts"
  | "diagnostics";

const TABS: { id: PanelTab; label: string; icon: string }[] = [
  { id: "navigator", label: "Navigator", icon: "🧭" },
  { id: "integrity", label: "Integridade", icon: "📊" },
  { id: "healing", label: "Auto-Cura", icon: "🛡️" },
  { id: "timeline", label: "Timeline", icon: "⏳" },
  { id: "memory", label: "Memory", icon: "🧠" },
  { id: "facts", label: "Facts", icon: "⚡" },
  { id: "diagnostics", label: "Diagnostics", icon: "⚙️" },
];

// Helper to dynamically extract directory/project structure from labels
function getProjectFromLabel(label: string): string {
  if (!label) return "Others";
  const firstSlashIndex = label.indexOf("/");
  if (firstSlashIndex !== -1) {
    return label.substring(0, firstSlashIndex);
  }
  const doubleColonIndex = label.indexOf("::");
  if (doubleColonIndex !== -1) {
    const filePart = label.substring(0, doubleColonIndex);
    if (filePart.includes(".")) {
      return "Root Files";
    }
  }
  return "Others";
}

// ─── Page Component ────────────────-----------------------------------------

export default function Home() {
  // ── 1. MCP Connection ──
  const {
    status: mcpStatus,
    serverInfo,
    tools,
    resources,
    error: mcpError,
    sseUrl,
    reconnectAttempt,
    lastConnectedAt,
    isOnline: isMcpOnline,
    reconnect: reconnectMcp,
  } = useMcpConnection();

  // ── 2. Graph Topology ──
  const {
    graphData,
    loadingState: graphLoadingState,
    error: graphError,
    stats,
    reload: reloadGraph,
  } = useGraphTopology(isMcpOnline);

  // ── 3. Cognitive Data ──
  const {
    memoryBlocks,
    semanticFacts,
    loadingState: cognitiveLoadingState,
    error: cognitiveError,
    reload: reloadCognitive,
  } = useCognitiveData(isMcpOnline);

  // ── 4. Telemetry Stream (SDD-16 + SDD-28) ──
  const {
    data: telemetryData,
    status: telemetryStatus,
    isConnected: isTelemetryOnline,
    error: telemetryError,
    metrics: governorMetrics,
    hsmState,
    dirtyQueue,
    events: telemetryEvents,
  } = useTelemetryStream();

  const [viewMode, setViewMode] = useState<"cockpit" | "universe">("cockpit");
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<PanelTab>("navigator");

  // Multidimensional navigation and inspection states
  const [dimensionMode, setDimensionMode] = useState<"2D" | "3D">("3D");
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null);

  // ─── Local Filters (Client-side) ───────────────────────────────────────

  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set());
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());

  // Dynamically extract unique list of types and projects based on received data
  const { availableProjects, availableTypes } = useMemo(() => {
    const projMap: Record<string, number> = {};
    const typeMap: Record<string, number> = {};

    graphData.nodes.forEach((node) => {
      const proj = getProjectFromLabel(node.label);
      projMap[proj] = (projMap[proj] || 0) + 1;
      typeMap[node.node_type] = (typeMap[node.node_type] || 0) + 1;
    });

    const projects = Object.entries(projMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    const types = Object.entries(typeMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    return { availableProjects: projects, availableTypes: types };
  }, [graphData.nodes]);

  // Apply dynamic filters in memory (Zero Network)
  const filteredGraphData = useMemo(() => {
    const hasProjectFilter = selectedProjects.size > 0;
    const hasTypeFilter = selectedTypes.size > 0;

    if (!hasProjectFilter && !hasTypeFilter) {
      return graphData;
    }

    const nodes = graphData.nodes.filter((node) => {
      const nodeProject = getProjectFromLabel(node.label);
      const projectMatch = !hasProjectFilter || selectedProjects.has(nodeProject);
      const typeMatch = !hasTypeFilter || selectedTypes.has(node.node_type);
      return projectMatch && typeMatch;
    });

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graphData.links.filter((link) => {
      const srcId = typeof link.source === "object" ? (link.source as any).id : link.source;
      const tgtId = typeof link.target === "object" ? (link.target as any).id : link.target;
      return nodeIds.has(srcId) && nodeIds.has(tgtId);
    });

    return { nodes, links };
  }, [graphData, selectedProjects, selectedTypes]);

  // Topology node mapping for 2D CodeGraphViewer
  const topologyNodes = useMemo(() => {
    if (filteredGraphData.nodes.length === 0) return undefined;
    return filteredGraphData.nodes.map((n) => ({
      id: n.id,
      name: n.label || String(n.id),
      path: n.label || String(n.id),
      node_type: n.node_type,
      val: n.val ? Math.max(6, Math.min(24, n.val)) : 8,
    }));
  }, [filteredGraphData.nodes]);

  const topologyLinks = useMemo(() => {
    if (filteredGraphData.links.length === 0) return undefined;
    return filteredGraphData.links.map((l) => ({
      source: typeof l.source === "object" ? (l.source as any).id : l.source,
      target: typeof l.target === "object" ? (l.target as any).id : l.target,
    }));
  }, [filteredGraphData.links]);

  // Handlers for the filters
  const handleToggleProject = useCallback((project: string) => {
    startTransition(() => {
      setSelectedProjects((prev) => {
        const next = new Set(prev);
        if (next.has(project)) {
          next.delete(project);
        } else {
          next.add(project);
        }
        return next;
      });
    });
  }, []);

  const handleToggleType = useCallback((type: string) => {
    startTransition(() => {
      setSelectedTypes((prev) => {
        const next = new Set(prev);
        if (next.has(type)) {
          next.delete(type);
        } else {
          next.add(type);
        }
        return next;
      });
    });
  }, []);

  const handleSelectAllProjects = useCallback(() => {
    startTransition(() => {
      setSelectedProjects(new Set(availableProjects.map((p) => p.name)));
    });
  }, [availableProjects]);

  const handleClearProjects = useCallback(() => {
    startTransition(() => {
      setSelectedProjects(new Set());
    });
  }, []);

  const handleSelectAllTypes = useCallback(() => {
    startTransition(() => {
      setSelectedTypes(new Set(availableTypes.map((t) => t.name)));
    });
  }, [availableTypes]);

  const handleClearTypes = useCallback(() => {
    startTransition(() => {
      setSelectedTypes(new Set());
    });
  }, []);

  // Formatted integrity score for header pill
  const headerIntegrityScore = telemetryData
    ? telemetryData.integrity_score <= 1.0
      ? Math.round(telemetryData.integrity_score * 100)
      : Math.round(telemetryData.integrity_score)
    : null;

  return (
    <main className="h-screen flex flex-col overflow-hidden">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <header className="border-b border-white/[0.06] bg-black/60 backdrop-blur-md z-20 shrink-0">
        <div className="max-w-full mx-auto px-4 py-2.5 flex items-center justify-between">
          {/* Left: Logo + Title */}
          <div className="flex items-center gap-3">
            <div className="logo-pulse text-xl" style={{ color: "#ffa203" }}>
              ◆
            </div>
            <div>
              <h1 className="text-base font-semibold text-gradient">
                Grafo Dashboard
              </h1>
              <p className="text-[10px] text-neutral-600 font-mono tracking-wider uppercase">
                HUD Cognitivo · Concierge v4.1.0
              </p>
            </div>
          </div>

          {/* Center: Graph Stats (Totals) */}
          <div className="hidden lg:flex items-center gap-4 text-xs font-mono">
            {stats.totalNodes > 0 && (
              <>
                <span className="text-neutral-500">
                  Nodes{" "}
                  <span className="text-neutral-300 font-medium">
                    {stats.totalNodes.toLocaleString()}
                  </span>
                </span>
                <span className="text-neutral-700">|</span>
                <span className="text-neutral-500">
                  Edges{" "}
                  <span className="text-neutral-300 font-medium">
                    {stats.totalLinks.toLocaleString()}
                  </span>
                </span>
                <span className="text-neutral-700">|</span>
                <div className="flex items-center gap-2">
                  {Object.entries(stats.nodeTypes).map(([type, count]) => (
                    <span key={type} className="flex items-center gap-1">
                      <span
                        className="w-1.5 h-1.5 rounded-full inline-block"
                        style={{
                          backgroundColor:
                            NODE_TYPE_COLORS[type] ??
                            NODE_TYPE_COLORS.DEFAULT,
                        }}
                      />
                      <span className="text-neutral-600 uppercase">
                        {type}
                        <span className="text-neutral-400 ml-0.5 font-medium">
                          {count}
                        </span>
                      </span>
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Right: Telemetry pill + Status + Dimension Toggle + Panel Toggle */}
          <div className="flex items-center gap-3">
            {/* Integrity Score Badge */}
            {headerIntegrityScore !== null && (
              <button
                onClick={() => {
                  setActiveTab("integrity");
                  setIsPanelOpen(true);
                }}
                className={`hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-mono border transition-all cursor-pointer ${
                  headerIntegrityScore >= 98
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                }`}
                title="Score de Integridade de Memória (Clique para inspecionar)"
              >
                <span>📊</span>
                <span className="font-bold">{headerIntegrityScore}%</span>
              </button>
            )}

            {/* Dirty Queue mini-badge */}
            {telemetryData && telemetryData.queue_backlog > 0 && (
              <div className="hidden md:flex items-center gap-1 text-[10px] font-mono text-amber-400/90 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full animate-pulse">
                <span>🟡</span>
                <span>{telemetryData.queue_backlog} dirty</span>
              </div>
            )}

            {/* Cognitive stats mini-badges */}
            {memoryBlocks.length > 0 && (
              <div className="hidden xl:flex items-center gap-1.5 text-[10px] font-mono text-neutral-500">
                <span>🧠</span>
                <span className="text-neutral-400">{memoryBlocks.length}</span>
              </div>
            )}
            {semanticFacts.length > 0 && (
              <div className="hidden xl:flex items-center gap-1.5 text-[10px] font-mono text-neutral-500">
                <span>⚡</span>
                <span className="text-amber-400/70">{semanticFacts.length}</span>
              </div>
            )}

            {/* View Mode Switcher: Cockpit 2x2 vs Universe */}
            <div className="flex items-center bg-white/[0.04] p-0.5 rounded-lg border border-white/[0.06]">
              <button
                onClick={() => setViewMode("cockpit")}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                  viewMode === "cockpit"
                    ? "bg-amber-500 text-black font-bold shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
                title="Cockpit de Observabilidade (Grid 2x2)"
              >
                <span>🚀</span>
                <span>Cockpit</span>
              </button>
              <button
                onClick={() => setViewMode("universe")}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                  viewMode === "universe"
                    ? "bg-amber-500 text-black font-bold shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
                title="Universo 3D/2D do Grafo"
              >
                <span>🌐</span>
                <span>Universo</span>
              </button>
            </div>

            {/* Dimension Toggle Button (3D / 2D Switch - only in Universe view) */}
            {viewMode === "universe" && (
              <button
                onClick={() => {
                  setDimensionMode((prev) => (prev === "3D" ? "2D" : "3D"));
                  setSelectedNode(null);
                }}
                className="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold
                           bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                           text-neutral-300 hover:text-white transition-all cursor-pointer flex items-center gap-1.5"
                title="Alternar entre motor 2D e 3D"
              >
                <span>{dimensionMode === "3D" ? "🌐" : "🗺️"}</span>
                View: <span className="text-amber-500 font-bold">{dimensionMode}</span>
              </button>
            )}

            {/* SSE Telemetry Status Dot */}
            <div
              className="flex items-center gap-1.5 text-xs text-neutral-500 font-mono px-2 py-1 rounded bg-white/[0.02] border border-white/[0.04]"
              title={`Telemetria SSE: ${telemetryStatus.toUpperCase()}`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  isTelemetryOnline
                    ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"
                    : telemetryStatus === "connecting"
                    ? "bg-amber-400 animate-pulse"
                    : "bg-red-400"
                }`}
              />
              <span className="text-[10px] hidden sm:inline uppercase">
                {isTelemetryOnline ? "SSE" : telemetryStatus}
              </span>
            </div>

            {/* Panel toggle button */}
            <button
              onClick={() => setIsPanelOpen(!isPanelOpen)}
              className="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-300
                         bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06]
                         transition-all cursor-pointer text-sm font-semibold"
              title={isPanelOpen ? "Fechar HUD" : "Abrir HUD Cognitivo"}
            >
              {isPanelOpen ? "✕" : "☰"}
            </button>
          </div>
        </div>
      </header>

      {/* ─── Main Content ────────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden">
        {/* Main Content: Cockpit 2x2 Grid or Universe Canvas */}
        {viewMode === "cockpit" ? (
          <div className="absolute inset-0 p-3 md:p-4 grid grid-cols-1 lg:grid-cols-2 grid-rows-none lg:grid-rows-2 gap-3 md:gap-4 overflow-y-auto lg:overflow-hidden bg-neutral-950">
            {/* Panel 1: Top-Left - Topology CodeGraph */}
            <div className="h-[430px] lg:h-full min-h-[380px] rounded-xl overflow-hidden shadow-2xl">
              <CodeGraphViewer
                nodes={topologyNodes}
                links={topologyLinks}
                dirtyQueue={dirtyQueue}
                onNodeSelect={(node) => {
                  if (node) {
                    const originalNode = graphData.nodes.find((n) => n.id === node.id);
                    if (originalNode) setSelectedNode(originalNode);
                  }
                }}
                className="h-full"
              />
            </div>

            {/* Panel 2: Top-Right - Rate Governor Quotas */}
            <div className="h-[430px] lg:h-full min-h-[380px] rounded-xl overflow-hidden shadow-2xl">
              <QuotaGauges
                metrics={governorMetrics}
                queueBacklog={dirtyQueue.length || telemetryData?.queue_backlog || 0}
                className="h-full"
              />
            </div>

            {/* Panel 3: Bottom-Left - HSM State Inspector */}
            <div className="h-[430px] lg:h-full min-h-[380px] rounded-xl overflow-hidden shadow-2xl">
              <HSMStateInspector
                hsmState={hsmState}
                className="h-full"
              />
            </div>

            {/* Panel 4: Bottom-Right - Live Event Feed Cyber Console */}
            <div className="h-[430px] lg:h-full min-h-[380px] rounded-xl overflow-hidden shadow-2xl">
              <LiveEventFeed
                events={telemetryEvents}
                className="h-full"
              />
            </div>
          </div>
        ) : (
          /* Graph Canvas — Full viewport */
          <div className="absolute inset-0">
            <GrafoUniverse
              graphData={filteredGraphData}
              loadingState={graphLoadingState}
              error={graphError}
              stats={stats}
              dimensionMode={dimensionMode}
              onNodeClick={setSelectedNode}
              onReload={reloadGraph}
            />
          </div>
        )}

        {/* Lateral Inspection Drawer */}
        {selectedNode && (
          <InspectorDrawer
            node={selectedNode}
            allNodes={graphData.nodes}
            allLinks={graphData.links}
            onClose={() => setSelectedNode(null)}
            onSelectNode={setSelectedNode}
            isPanelOpen={isPanelOpen}
          />
        )}

        {/* ─── Side Panel with Tabs ─────────────────────────────────────── */}
        <div
          className={`absolute top-0 right-0 h-full w-[450px] max-w-[95vw] z-30 transform transition-transform duration-300 ease-out ${
            isPanelOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="h-full flex flex-col bg-black/90 backdrop-blur-xl border-l border-white/[0.06]">
            {/* Tab Bar */}
            <div className="shrink-0 flex border-b border-white/[0.06] overflow-x-auto scrollbar-thin">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 min-w-[60px] flex items-center justify-center gap-1 px-2.5 py-3
                             text-xs font-medium transition-all cursor-pointer whitespace-nowrap
                             ${
                               activeTab === tab.id
                                 ? "text-neutral-200 border-b-2 border-amber-500 bg-white/[0.03]"
                                 : "text-neutral-500 hover:text-neutral-400 border-b-2 border-transparent"
                             }`}
                  title={tab.label}
                >
                  <span className="text-sm">{tab.icon}</span>
                  <span className="hidden md:inline text-[11px]">{tab.label}</span>
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* ─── Tab: Universal Navigator ──────────────────────────── */}
              {activeTab === "navigator" && (
                <UniversalNavigatorPanel
                  totalNodesCount={graphData.nodes.length}
                  filteredNodesCount={filteredGraphData.nodes.length}
                  totalLinksCount={graphData.links.length}
                  filteredLinksCount={filteredGraphData.links.length}
                  availableProjects={availableProjects}
                  selectedProjects={selectedProjects}
                  onToggleProject={handleToggleProject}
                  onSelectAllProjects={handleSelectAllProjects}
                  onClearProjects={handleClearProjects}
                  availableTypes={availableTypes}
                  selectedTypes={selectedTypes}
                  onToggleType={handleToggleType}
                  onSelectAllTypes={handleSelectAllTypes}
                  onClearTypes={handleClearTypes}
                />
              )}

              {/* ─── Tab: Memory Integrity Board (SDD-16) ──────────────── */}
              {activeTab === "integrity" && (
                <MemoryIntegrityBoard
                  telemetry={telemetryData}
                  isLoading={!telemetryData && telemetryStatus === "connecting"}
                />
              )}

              {/* ─── Tab: Self-Healing Console (SDD-16) ────────────────── */}
              {activeTab === "healing" && (
                <SelfHealingConsole
                  telemetry={telemetryData}
                  isLoading={!telemetryData && telemetryStatus === "connecting"}
                />
              )}

              {/* ─── Tab: Agent Checkpoints Timeline (SDD-16) ──────────── */}
              {activeTab === "timeline" && (
                <AgentTimelinePanel
                  telemetry={telemetryData}
                  isLoading={!telemetryData && telemetryStatus === "connecting"}
                />
              )}

              {/* ─── Tab: Diagnostics ──────────────────────────────────── */}
              {activeTab === "diagnostics" && (
                <>
                  <ConnectionStatus
                    status={mcpStatus}
                    serverInfo={serverInfo}
                    error={mcpError}
                    sseUrl={sseUrl}
                    reconnectAttempt={reconnectAttempt}
                    lastConnectedAt={lastConnectedAt}
                    onReconnect={reconnectMcp}
                  />

                  {telemetryError && (
                    <div className="panel-overlay border-rose-500/20">
                      <p className="text-xs text-rose-400 font-mono">
                        ⚠️ Telemetria SSE: {telemetryError}
                      </p>
                    </div>
                  )}

                  <ToolsList
                    tools={tools}
                    resources={resources}
                    isOnline={isMcpOnline}
                  />

                  {stats.totalNodes > 0 && (
                    <div className="panel-overlay">
                      <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                        <span className="text-base">📊</span>
                        General Topology
                      </h3>
                      <div className="space-y-2">
                        {Object.entries(stats.nodeTypes).map(
                          ([type, count]) => {
                            const pct = Math.round(
                              (count / stats.totalNodes) * 100
                            );
                            return (
                              <div key={type}>
                                <div className="flex justify-between text-xs mb-1">
                                  <span className="flex items-center gap-1.5 font-mono text-neutral-400">
                                    <span
                                      className="w-2 h-2 rounded-full inline-block"
                                      style={{
                                        backgroundColor:
                                          NODE_TYPE_COLORS[type] ??
                                          NODE_TYPE_COLORS.DEFAULT,
                                      }}
                                    />
                                    {type}
                                  </span>
                                  <span className="text-neutral-500">
                                    {count}{" "}
                                    <span className="text-neutral-600">
                                      ({pct}%)
                                    </span>
                                  </span>
                                </div>
                                <div className="h-1 rounded-full bg-white/[0.04] overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all duration-700"
                                    style={{
                                      width: `${pct}%`,
                                      backgroundColor:
                                        NODE_TYPE_COLORS[type] ??
                                        NODE_TYPE_COLORS.DEFAULT,
                                      opacity: 0.6,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* ─── Tab: Core Memory ──────────────────────────────────── */}
              {activeTab === "memory" && (
                <>
                  <CoreMemoryPanel
                    blocks={memoryBlocks}
                    loadingState={cognitiveLoadingState}
                  />

                  {cognitiveError && (
                    <div className="panel-overlay border-red-500/20">
                      <p className="text-xs text-red-400">{cognitiveError}</p>
                      <button
                        onClick={reloadCognitive}
                        className="mt-2 text-[10px] text-neutral-400 hover:text-neutral-300 underline cursor-pointer"
                      >
                        Try again
                      </button>
                    </div>
                  )}
                </>
              )}

              {/* ─── Tab: Fatos Semânticos ─────────────────────────────── */}
              {activeTab === "facts" && (
                <SemanticFactsPanel
                  facts={semanticFacts}
                  loadingState={cognitiveLoadingState}
                />
              )}

              {/* Footer */}
              <p className="text-[10px] text-neutral-700 font-mono text-center pt-2 border-t border-white/[0.04] mt-4">
                grafo-dashboard-web v0.4.0 · SDD-16 Telemetry Ready
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
