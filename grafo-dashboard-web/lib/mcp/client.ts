/**
 * MCP Client — Nervous System of the Visual Layer
 *
 * MCP Client via SSE (Server-Sent Events) for communication with the
 * Grafo Concierge backend (FastMCP/Python).
 *
 * Responsibilities:
 * - Establish SSE connection with the MCP server
 * - Send JSON-RPC 2.0 messages via POST
 * - Manage connection lifecycle with exponential reconnect
 * - Expose reactive state via callbacks
 *
 * @module lib/mcp/client
 */

import {
  type McpConnectionState,
  type McpConnectionStatus,
  type McpInitializeResult,
  type McpTool,
  type McpResource,
  type JsonRpcRequest,
  type JsonRpcResponse,
  INITIAL_MCP_STATE,
} from "./types";

// ─── Configuration ──────────────────────────────────────────────────────────

const MCP_URL_FALLBACK = "http://127.0.0.1:7077/sse";

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 30000;
const RECONNECT_JITTER_FACTOR = 0.3;

// ─── State Listener ─────────────────────────────────────────────────────────

type StateListener = (state: McpConnectionState) => void;

// ─── MCP Client Class ───────────────────────────────────────────────────────

export class McpClient {
  private sseUrl: string;
  private messageEndpoint: string | null = null;
  private eventSource: EventSource | null = null;
  private state: McpConnectionState = { ...INITIAL_MCP_STATE };
  private listeners: Set<StateListener> = new Set();
  private requestIdCounter = 0;
  private pendingRequests = new Map<
    number | string,
    {
      resolve: (value: JsonRpcResponse) => void;
      reject: (reason: Error) => void;
      timeout: ReturnType<typeof setTimeout>;
    }
  >();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isDestroyed = false;

  constructor() {
    const envUrl = process.env.NEXT_PUBLIC_GRAFO_MCP_URL;
    this.sseUrl = envUrl && envUrl.trim() !== "" ? envUrl.trim() : MCP_URL_FALLBACK;
  }

  // ─── Public API ─────────────────────────────────────────────────────────

  /**
   * Initiates the SSE connection with the MCP server.
   * Idempotent: calling multiple times does not create duplicate connections.
   */
  connect(): void {
    if (this.isDestroyed) return;
    if (this.eventSource?.readyState === EventSource.OPEN) return;

    this.closeExistingConnection();
    this.updateStatus("connecting");

    try {
      this.eventSource = new EventSource(this.sseUrl);
      this.setupEventHandlers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create SSE connection";
      this.handleConnectionError(message);
    }
  }

  /**
   * Disconnects from the MCP server and cleans up all resources.
   * After calling destroy(), the client cannot be reused.
   */
  destroy(): void {
    this.isDestroyed = true;
    this.clearReconnectTimer();
    this.closeExistingConnection();
    this.rejectAllPending("Client destroyed");
    this.updateState({
      ...INITIAL_MCP_STATE,
      status: "disconnected",
    });
    this.listeners.clear();
  }

  /**
   * Registers a listener for state changes.
   * Returns the unsubscribe function.
   */
  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    // Emits the current state immediately
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /** Returns an immutable snapshot of the current state */
  getState(): Readonly<McpConnectionState> {
    return this.state;
  }

  /** Returns the configured SSE URL (for diagnostics) */
  getSseUrl(): string {
    return this.sseUrl;
  }

  /**
   * Invokes an MCP tool by name via JSON-RPC.
   * Can only be called when status is 'connected'.
   */
  async callTool(
    toolName: string,
    args: Record<string, unknown> = {}
  ): Promise<unknown> {
    if (this.state.status !== "connected") {
      throw new Error("MCP Client is not connected");
    }

    const response = await this.sendRequest("tools/call", {
      name: toolName,
      arguments: args,
    });

    if (response.error) {
      throw new Error(
        `Tool '${toolName}' failed: ${response.error.message}`
      );
    }

    // MCP tools/call returns { content: [{type, text}] }
    const result = response.result as {
      content?: Array<{ type: string; text?: string }>;
    };

    if (result?.content?.[0]?.text) {
      try {
        return JSON.parse(result.content[0].text);
      } catch {
        return result.content[0].text;
      }
    }

    return result;
  }

  // ─── SSE Event Handlers ─────────────────────────────────────────────────

  private setupEventHandlers(): void {
    if (!this.eventSource) return;

    // FastMCP sends an "endpoint" event with the URL for POST JSON-RPC
    this.eventSource.addEventListener("endpoint", (event: MessageEvent) => {
      try {
        const sseUrlObj = new URL(this.sseUrl);
        const endpointPath = event.data as string;

        // The endpoint can be a relative or absolute path
        if (endpointPath.startsWith("http")) {
          this.messageEndpoint = endpointPath;
        } else {
          this.messageEndpoint = `${sseUrlObj.protocol}//${sseUrlObj.host}${endpointPath}`;
        }

        this.performHandshake();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Invalid endpoint";
        this.handleConnectionError(message);
      }
    });

    // Response JSON-RPC messages arrive via SSE "message" events
    this.eventSource.addEventListener("message", (event: MessageEvent) => {
      try {
        const response = JSON.parse(event.data as string) as JsonRpcResponse;
        this.handleJsonRpcResponse(response);
      } catch {
        // Ignores non-JSON messages (heartbeats, etc.)
      }
    });

    this.eventSource.onerror = () => {
      // EventSource auto-reconnects, but we need to update the state
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.handleConnectionError("SSE connection closed by the server");
      }
    };
  }

  // ─── MCP Handshake Protocol ─────────────────────────────────────────────

  private async performHandshake(): Promise<void> {
    try {
      // Step 1: Initialize
      const initResponse = await this.sendRequest("initialize", {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: {
          name: "grafo-dashboard-web",
          version: "0.1.0",
        },
      });

      if (initResponse.error) {
        throw new Error(
          `Initialize failed: ${initResponse.error.message}`
        );
      }

      const initResult = initResponse.result as McpInitializeResult;

      // Step 2: Send initialized notification (no response expected)
      await this.sendNotification("notifications/initialized", {});

      // Step 3: List tools
      const toolsResponse = await this.sendRequest("tools/list", {});
      const tools = toolsResponse.error
        ? []
        : ((toolsResponse.result as { tools: McpTool[] })?.tools ?? []);

      // Step 4: List resources (might not be available)
      let resources: McpResource[] = [];
      try {
        const resourcesResponse = await this.sendRequest("resources/list", {});
        if (!resourcesResponse.error) {
          resources =
            (resourcesResponse.result as { resources: McpResource[] })
              ?.resources ?? [];
        }
      } catch {
        // resources/list is optional in MCP
      }

      // Handshake complete — update state
      this.updateState({
        status: "connected",
        serverInfo: initResult?.serverInfo ?? null,
        tools,
        resources,
        error: null,
        lastConnectedAt: new Date(),
        reconnectAttempt: 0,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "MCP Handshake failed";
      this.handleConnectionError(message);
    }
  }

  // ─── JSON-RPC Transport ─────────────────────────────────────────────────

  private sendRequest(
    method: string,
    params: Record<string, unknown>
  ): Promise<JsonRpcResponse> {
    return new Promise((resolve, reject) => {
      if (!this.messageEndpoint) {
        reject(new Error("Message endpoint not available"));
        return;
      }

      const id = ++this.requestIdCounter;
      const request: JsonRpcRequest = {
        jsonrpc: "2.0",
        id,
        method,
        params,
      };

      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Timeout: ${method} (id=${id})`));
      }, 15000);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      fetch(this.messageEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }).catch((err) => {
        clearTimeout(timeout);
        this.pendingRequests.delete(id);
        reject(err);
      });
    });
  }

  private async sendNotification(
    method: string,
    params: Record<string, unknown>
  ): Promise<void> {
    if (!this.messageEndpoint) return;

    const request = {
      jsonrpc: "2.0" as const,
      method,
      params,
    };

    try {
      await fetch(this.messageEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
    } catch {
      // Notifications are fire-and-forget
    }
  }

  private handleJsonRpcResponse(response: JsonRpcResponse): void {
    const pending = this.pendingRequests.get(response.id);
    if (pending) {
      clearTimeout(pending.timeout);
      this.pendingRequests.delete(response.id);
      pending.resolve(response);
    }
  }

  // ─── Connection Resilience ──────────────────────────────────────────────

  private handleConnectionError(message: string): void {
    this.closeExistingConnection();
    this.rejectAllPending(message);

    const attempt = this.state.reconnectAttempt + 1;

    this.updateState({
      ...this.state,
      status: "reconnecting",
      error: message,
      reconnectAttempt: attempt,
      // Preserves serverInfo/tools from the last connected state
    });

    this.scheduleReconnect(attempt);
  }

  private scheduleReconnect(attempt: number): void {
    if (this.isDestroyed) return;
    this.clearReconnectTimer();

    // Exponential backoff with jitter
    const baseDelay = Math.min(
      RECONNECT_BASE_DELAY_MS * Math.pow(2, attempt - 1),
      RECONNECT_MAX_DELAY_MS
    );
    const jitter = baseDelay * RECONNECT_JITTER_FACTOR * Math.random();
    const delay = baseDelay + jitter;

    this.reconnectTimer = setTimeout(() => {
      if (!this.isDestroyed) {
        this.connect();
      }
    }, delay);
  }

  // ─── Internal Helpers ───────────────────────────────────────────────────

  private closeExistingConnection(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.messageEndpoint = null;
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private rejectAllPending(reason: string): void {
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new Error(reason));
      this.pendingRequests.delete(id);
    }
  }

  private updateStatus(status: McpConnectionStatus): void {
    this.updateState({ ...this.state, status });
  }

  private updateState(newState: McpConnectionState): void {
    this.state = newState;
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch {
        // Listener errors should not crash the client
      }
    }
  }
}

// ─── Singleton ──────────────────────────────────────────────────────────────

let clientInstance: McpClient | null = null;

/**
 * Returns the singleton instance of McpClient.
 * Guarantees that only one SSE connection exists per browser session.
 */
export function getMcpClient(): McpClient {
  if (!clientInstance) {
    clientInstance = new McpClient();
  }
  return clientInstance;
}
