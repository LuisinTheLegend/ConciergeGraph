"use client";

/**
 * useGraphTopology — Hook to load full Graph topology via MCP
 *
 * Loading strategy (Slice Front-3: The Big Bang):
 * 1. Makes a single call to 'get_full_topology' tool
 * 2. Maps the light and direct list of nodes and edges from the payload
 * 3. Calculates the size (val) of each node dynamically based on its degree (number of connections)
 * 4. Updates the state all at once to avoid lag or partial renderings
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { getMcpClient } from "@/lib/mcp";
import {
  type ForceGraphData,
  type ForceGraphNode,
  type ForceGraphLink,
  getNodeColor,
} from "@/lib/graph/types";

export type TopologyLoadingState = "idle" | "loading-nodes" | "loading-edges" | "ready" | "error";

interface UseGraphTopologyReturn {
  graphData: ForceGraphData;
  loadingState: TopologyLoadingState;
  error: string | null;
  stats: {
    totalNodes: number;
    totalLinks: number;
    nodeTypes: Record<string, number>;
  };
  reload: () => void;
}

const EMPTY_GRAPH: ForceGraphData = { nodes: [], links: [] };

interface McpTopologyNode {
  node_id: number;
  name: string;
  node_type: string;
  summary?: string | null;
  tags?: string[] | null;
  hybrid_score?: number;
  is_super_node?: boolean;
}

interface McpTopologyEdge {
  source: number;
  target: number;
  edge_type?: string | null;
}

interface McpTopologyResponse {
  success: boolean;
  nodes?: McpTopologyNode[];
  edges?: McpTopologyEdge[];
}

export function useGraphTopology(isConnected: boolean): UseGraphTopologyReturn {
  const [graphData, setGraphData] = useState<ForceGraphData>(EMPTY_GRAPH);
  const [loadingState, setLoadingState] = useState<TopologyLoadingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalNodes: 0,
    totalLinks: 0,
    nodeTypes: {} as Record<string, number>,
  });
  const loadingRef = useRef(false);

  const loadTopology = useCallback(async () => {
    if (loadingRef.current || !isConnected) return;
    loadingRef.current = true;
    setError(null);
    setLoadingState("loading-nodes");

    const client = getMcpClient();

    try {
      // Call get_full_topology tool
      const response = (await client.callTool("get_full_topology", {})) as McpTopologyResponse;

      if (!response || !response.success || !response.nodes || !response.edges) {
        throw new Error("Invalid or empty response from MCP server");
      }

      const mcpNodes = response.nodes;
      const mcpEdges = response.edges;

      // 1) Calculate connectivity degree (in/out degree) of each node to define proportional size
      const degreeMap: Record<number, number> = {};
      for (const edge of mcpEdges) {
        degreeMap[edge.source] = (degreeMap[edge.source] || 0) + 1;
        degreeMap[edge.target] = (degreeMap[edge.target] || 0) + 1;
      }

      // 2) Map nodes
      const nodes: ForceGraphNode[] = mcpNodes.map((node) => {
        const degree = degreeMap[node.node_id] || 0;
        // Super nodes get large highlight, common nodes scale with the square root of their connectivity degree
        const val = node.is_super_node
          ? 24
          : Math.max(4, Math.min(20, 3 + Math.sqrt(degree) * 2));

        return {
          id: node.node_id,
          label: node.name,
          summary: node.summary || null,
          node_type: node.node_type,
          tags: node.tags || null,
          hybrid_score: node.hybrid_score || 0,
          is_super_node: !!node.is_super_node,
          color: getNodeColor(node.node_type),
          val,
        };
      });

      // 3) Map edges
      const links: ForceGraphLink[] = mcpEdges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        relation_type: edge.edge_type || undefined,
      }));

      // 4) Remove duplicate links if any
      const dedupedLinks = deduplicateLinks(links);

      // 5) Calculate node types statistics
      const nodeTypes: Record<string, number> = {};
      for (const node of nodes) {
        nodeTypes[node.node_type] = (nodeTypes[node.node_type] || 0) + 1;
      }

      // 6) Update state all at once (Big Bang!)
      setStats({
        totalNodes: nodes.length,
        totalLinks: dedupedLinks.length,
        nodeTypes,
      });

      setGraphData({ nodes, links: dedupedLinks });
      setLoadingState("ready");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error loading full topology";
      setError(msg);
      setLoadingState("error");
    } finally {
      loadingRef.current = false;
    }
  }, [isConnected]);

  // Auto-load when connected
  useEffect(() => {
    if (isConnected && loadingState === "idle") {
      loadTopology();
    }
  }, [isConnected, loadingState, loadTopology]);

  return {
    graphData,
    loadingState,
    error,
    stats,
    reload: loadTopology,
  };
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function deduplicateLinks(links: ForceGraphLink[]): ForceGraphLink[] {
  const seen = new Set<string>();
  return links.filter((link) => {
    const srcId = typeof link.source === "object" ? link.source.id : link.source;
    const tgtId = typeof link.target === "object" ? link.target.id : link.target;
    const key = `${srcId}->${tgtId}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
