"use client";

/**
 * useMcpConnection — React hook to manage MCP connection state
 *
 * Automatically connects to the Grafo Concierge MCP server via SSE
 * and provides the reactive connection state to UI components.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { getMcpClient, type McpConnectionState, INITIAL_MCP_STATE } from "@/lib/mcp";

export function useMcpConnection() {
  const [connectionState, setConnectionState] =
    useState<McpConnectionState>(INITIAL_MCP_STATE);
  const clientRef = useRef(getMcpClient());

  useEffect(() => {
    const client = clientRef.current;

    // Subscribe to state changes
    const unsubscribe = client.subscribe((state) => {
      setConnectionState(state);
    });

    // Initiate connection
    client.connect();

    return () => {
      unsubscribe();
    };
  }, []);

  const reconnect = useCallback(() => {
    clientRef.current.connect();
  }, []);

  const sseUrl = clientRef.current.getSseUrl();

  return {
    ...connectionState,
    sseUrl,
    reconnect,
    isOnline: connectionState.status === "connected",
    isLoading:
      connectionState.status === "connecting" ||
      connectionState.status === "reconnecting",
  };
}
