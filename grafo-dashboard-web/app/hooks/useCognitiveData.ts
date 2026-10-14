"use client";

/**
 * useCognitiveData — Hook to load Agent cognitive data via MCP
 *
 * Loads two sources:
 * 1. Core Memory (persona, context_rules, etc.) via concierge_get_memory
 * 2. Semantic Facts (documentary facts FACT) via concierge_search
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { getMcpClient } from "@/lib/mcp";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface MemoryBlock {
  id: number;
  scope_type: string;
  scope_id: string;
  block_label: string;
  content: string;
  updated_at: string;
}

export interface SemanticFact {
  node_id: number;
  label: string;
  summary: string | null;
  node_type: string;
  tags: string[] | null;
  hybrid_score: number;
  is_super_node: boolean;
}

export type CognitiveLoadingState =
  | "idle"
  | "loading-memory"
  | "loading-facts"
  | "ready"
  | "error";

interface UseCognitiveDataReturn {
  memoryBlocks: MemoryBlock[];
  semanticFacts: SemanticFact[];
  loadingState: CognitiveLoadingState;
  error: string | null;
  reload: () => void;
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useCognitiveData(
  isConnected: boolean
): UseCognitiveDataReturn {
  const [memoryBlocks, setMemoryBlocks] = useState<MemoryBlock[]>([]);
  const [semanticFacts, setSemanticFacts] = useState<SemanticFact[]>([]);
  const [loadingState, setLoadingState] =
    useState<CognitiveLoadingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false);

  const loadCognitiveData = useCallback(async () => {
    if (loadingRef.current || !isConnected) return;
    loadingRef.current = true;
    setError(null);

    const client = getMcpClient();

    try {
      // ─── Phase 1: Core Memory ──────────────────────────────────────
      setLoadingState("loading-memory");

      // Try multiple scopes to find memory blocks
      const scopes = [
        { scope_type: "agent", scope_id: "grafo-concierge" },
        { scope_type: "user", scope_id: "default" },
        { scope_type: "agent", scope_id: "default" },
      ];

      const allBlocks: MemoryBlock[] = [];
      const seenBlockIds = new Set<number>();

      for (const scope of scopes) {
        try {
          const result = (await client.callTool(
            "concierge_get_memory",
            scope
          )) as {
            success: boolean;
            blocks?: MemoryBlock[];
          };

          if (result?.success && result.blocks) {
            for (const block of result.blocks) {
              if (!seenBlockIds.has(block.id)) {
                seenBlockIds.add(block.id);
                allBlocks.push(block);
              }
            }
          }
        } catch {
          // Scope might not exist
        }
      }

      setMemoryBlocks(allBlocks);

      // ─── Phase 2: Semantic Facts ───────────────────────────────────
      setLoadingState("loading-facts");

      const factQueries = [
        "API documentation schema configuration architecture",
        "behavior learning preference pattern system design",
        "database model structure pipeline workflow migration",
      ];

      const allFacts: SemanticFact[] = [];
      const seenFactIds = new Set<number>();

      for (const query of factQueries) {
        try {
          const result = (await client.callTool("concierge_search", {
            query,
            all_wings: true,
            top_k: 20,
          })) as {
            success: boolean;
            results?: SemanticFact[];
          };

          if (result?.success && result.results) {
            for (const fact of result.results) {
              // Include ALL types (FACT is highlighted, but CLASS/MODULE/METHOD are also useful)
              if (!seenFactIds.has(fact.node_id)) {
                seenFactIds.add(fact.node_id);
                allFacts.push(fact);
              }
            }
          }
        } catch {
          // Individual query might fail
        }
      }

      // Sort by descending score
      allFacts.sort((a, b) => b.hybrid_score - a.hybrid_score);
      setSemanticFacts(allFacts);

      setLoadingState("ready");
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Error loading cognitive data";
      setError(msg);
      setLoadingState("error");
    } finally {
      loadingRef.current = false;
    }
  }, [isConnected]);

  // Auto-load quando conectar
  useEffect(() => {
    if (isConnected && loadingState === "idle") {
      loadCognitiveData();
    }
  }, [isConnected, loadingState, loadCognitiveData]);

  return {
    memoryBlocks,
    semanticFacts,
    loadingState,
    error,
    reload: loadCognitiveData,
  };
}
