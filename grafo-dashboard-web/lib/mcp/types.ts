/**
 * MCP (Model Context Protocol) Type Definitions
 *
 * Strict TypeScript types mapping the MCP protocol payloads
 * according to the JSON-RPC 2.0 specification used by the FastMCP backend.
 */

// ─── Connection State Machine ───────────────────────────────────────────────
export type McpConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

// ─── JSON-RPC 2.0 Base Types ────────────────────────────────────────────────
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: number | string;
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: number | string;
  result?: unknown;
  error?: JsonRpcError;
}

export interface JsonRpcError {
  code: number;
  message: string;
  data?: unknown;
}

// ─── MCP SSE Event Types ────────────────────────────────────────────────────
export interface McpSseEndpointEvent {
  /** The endpoint URL for sending JSON-RPC messages */
  endpoint: string;
}

// ─── MCP Tool Schema (from tools/list) ──────────────────────────────────────
export interface McpToolInputSchema {
  type: "object";
  properties?: Record<string, McpToolPropertySchema>;
  required?: string[];
  title?: string;
}

export interface McpToolPropertySchema {
  type: string;
  title?: string;
  description?: string;
  default?: unknown;
  anyOf?: Array<{ type: string }>;
}

export interface McpTool {
  name: string;
  description?: string;
  inputSchema: McpToolInputSchema;
}

export interface McpToolsListResult {
  tools: McpTool[];
}

// ─── MCP Resource Schema (from resources/list) ─────────────────────────────
export interface McpResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

export interface McpResourcesListResult {
  resources: McpResource[];
}

// ─── MCP Server Info (from initialize) ──────────────────────────────────────
export interface McpServerCapabilities {
  tools?: Record<string, unknown>;
  resources?: Record<string, unknown>;
  prompts?: Record<string, unknown>;
}

export interface McpServerInfo {
  name: string;
  version: string;
}

export interface McpInitializeResult {
  protocolVersion: string;
  capabilities: McpServerCapabilities;
  serverInfo: McpServerInfo;
}

// ─── Aggregate Connection State ─────────────────────────────────────────────
export interface McpConnectionState {
  status: McpConnectionStatus;
  serverInfo: McpServerInfo | null;
  tools: McpTool[];
  resources: McpResource[];
  error: string | null;
  lastConnectedAt: Date | null;
  reconnectAttempt: number;
}

export const INITIAL_MCP_STATE: McpConnectionState = {
  status: "disconnected",
  serverInfo: null,
  tools: [],
  resources: [],
  error: null,
  lastConnectedAt: null,
  reconnectAttempt: 0,
};
