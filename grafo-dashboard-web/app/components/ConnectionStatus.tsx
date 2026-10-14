"use client";

/**
 * ConnectionStatus — Visual indicator of the MCP connection status
 *
 * Displays 🔴/🟡/🟢 with pulse animations for transient states,
 * as specified in the "Prova de Vida" SDD contract.
 */

import type { McpConnectionStatus, McpServerInfo } from "@/lib/mcp";

interface ConnectionStatusProps {
  status: McpConnectionStatus;
  serverInfo: McpServerInfo | null;
  error: string | null;
  sseUrl: string;
  reconnectAttempt: number;
  lastConnectedAt: Date | null;
  onReconnect: () => void;
}

const STATUS_CONFIG: Record<
  McpConnectionStatus,
  { label: string; colorClass: string; dotClass: string; pulse: boolean }
> = {
  connected: {
    label: "Connected",
    colorClass: "text-emerald-400",
    dotClass: "bg-emerald-400 shadow-emerald-400/50",
    pulse: false,
  },
  connecting: {
    label: "Connecting...",
    colorClass: "text-amber-400",
    dotClass: "bg-amber-400 shadow-amber-400/50",
    pulse: true,
  },
  reconnecting: {
    label: "Reconnecting...",
    colorClass: "text-amber-400",
    dotClass: "bg-amber-400 shadow-amber-400/50",
    pulse: true,
  },
  disconnected: {
    label: "Disconnected",
    colorClass: "text-red-400",
    dotClass: "bg-red-400 shadow-red-400/50",
    pulse: false,
  },
  error: {
    label: "Error",
    colorClass: "text-red-400",
    dotClass: "bg-red-400 shadow-red-400/50",
    pulse: false,
  },
};

export function ConnectionStatus({
  status,
  serverInfo,
  error,
  sseUrl,
  reconnectAttempt,
  lastConnectedAt,
  onReconnect,
}: ConnectionStatusProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className="connection-card">
      {/* Header with indicator */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div
              className={`w-3 h-3 rounded-full shadow-lg ${config.dotClass}`}
            />
            {config.pulse && (
              <div
                className={`absolute inset-0 w-3 h-3 rounded-full animate-ping ${config.dotClass} opacity-75`}
              />
            )}
          </div>
          <h2 className="text-lg font-semibold text-neutral-100">
            Grafo Concierge
          </h2>
        </div>
        <span
          className={`text-sm font-medium px-3 py-1 rounded-full border ${config.colorClass} border-current/20 bg-current/5`}
        >
          {config.label}
        </span>
      </div>

      {/* Server Info */}
      {serverInfo && (
        <div className="mb-4 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-neutral-500 text-xs uppercase tracking-wider">
                Server
              </span>
              <p className="text-neutral-200 font-mono">{serverInfo.name}</p>
            </div>
            <div>
              <span className="text-neutral-500 text-xs uppercase tracking-wider">
                Version
              </span>
              <p className="text-neutral-200 font-mono">{serverInfo.version}</p>
            </div>
          </div>
        </div>
      )}

      {/* Connection Details */}
      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-neutral-500">SSE Endpoint</span>
          <code className="text-neutral-400 font-mono text-xs bg-white/[0.03] px-2 py-0.5 rounded">
            {sseUrl}
          </code>
        </div>

        {lastConnectedAt && (
          <div className="flex items-center justify-between">
            <span className="text-neutral-500">Last connection</span>
            <span className="text-neutral-400 text-xs">
              {lastConnectedAt.toLocaleTimeString("en-US")}
            </span>
          </div>
        )}

        {reconnectAttempt > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-neutral-500">Attempt</span>
            <span className="text-amber-400 text-xs font-mono">
              #{reconnectAttempt}
            </span>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-start gap-2">
            <span className="text-red-400 text-sm shrink-0">⚠</span>
            <div>
              <p className="text-red-300 text-sm font-medium">
                MCP Server Offline
              </p>
              <p className="text-red-400/70 text-xs mt-1 font-mono">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Reconnect Button */}
      {(status === "disconnected" || status === "error") && (
        <button
          onClick={onReconnect}
          className="mt-4 w-full py-2 px-4 rounded-lg text-sm font-medium
                     text-neutral-200 bg-white/[0.06] border border-white/[0.08]
                     hover:bg-white/[0.10] hover:border-white/[0.12]
                     active:scale-[0.98] transition-all duration-150
                     cursor-pointer"
        >
          Try to Reconnect
        </button>
      )}
    </div>
  );
}
