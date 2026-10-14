"use client";

/**
 * ToolsList — List of tools exposed by the MCP Server
 *
 * Displays all tools that Grafo Concierge is making
 * available via MCP protocol, including the input schema.
 */

import { useState } from "react";
import type { McpTool, McpResource } from "@/lib/mcp";

interface ToolsListProps {
  tools: McpTool[];
  resources: McpResource[];
  isOnline: boolean;
}

export function ToolsList({ tools, resources, isOnline }: ToolsListProps) {
  const [expandedTool, setExpandedTool] = useState<string | null>(null);

  if (!isOnline) {
    return (
      <div className="tools-card">
        <h2 className="text-lg font-semibold text-neutral-100 mb-4">
          MCP Tools
        </h2>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-12 h-12 rounded-full bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-4">
            <span className="text-2xl opacity-40">🔌</span>
          </div>
          <p className="text-neutral-500 text-sm">
            Waiting for server connection...
          </p>
          <p className="text-neutral-600 text-xs mt-1">
            Tools will be listed after MCP handshake
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="tools-card">
      {/* Tools Section */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-100">
          MCP Tools
        </h2>
        <span className="text-xs font-mono text-neutral-500 bg-white/[0.04] px-2 py-1 rounded">
          {tools.length} tool{tools.length !== 1 ? "s" : ""}
        </span>
      </div>

      {tools.length === 0 ? (
        <p className="text-neutral-500 text-sm py-4 text-center">
          No tools registered
        </p>
      ) : (
        <ul className="space-y-2">
          {tools.map((tool) => {
            const isExpanded = expandedTool === tool.name;
            const paramCount = tool.inputSchema?.properties
              ? Object.keys(tool.inputSchema.properties).length
              : 0;
            const requiredParams = tool.inputSchema?.required ?? [];

            return (
              <li key={tool.name}>
                <button
                  onClick={() =>
                    setExpandedTool(isExpanded ? null : tool.name)
                  }
                  className="w-full text-left p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]
                             hover:bg-white/[0.05] hover:border-white/[0.10]
                             transition-all duration-150 cursor-pointer group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-emerald-400/80 text-xs shrink-0">
                        ⚡
                      </span>
                      <span className="text-neutral-200 font-mono text-sm truncate">
                        {tool.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {paramCount > 0 && (
                        <span className="text-neutral-600 text-xs font-mono">
                          {paramCount} param{paramCount !== 1 ? "s" : ""}
                        </span>
                      )}
                      <span
                        className={`text-neutral-600 text-xs transition-transform duration-200 ${
                          isExpanded ? "rotate-90" : ""
                        }`}
                      >
                        ›
                      </span>
                    </div>
                  </div>

                  {tool.description && (
                    <p className="text-neutral-500 text-xs mt-1.5 pl-5 line-clamp-2">
                      {tool.description}
                    </p>
                  )}
                </button>

                {/* Expanded Schema View */}
                {isExpanded && tool.inputSchema?.properties && (
                  <div className="mt-1 ml-5 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs">
                    <p className="text-neutral-500 uppercase tracking-wider text-[10px] mb-2 font-semibold">
                      Input Schema
                    </p>
                    <div className="space-y-1.5">
                      {Object.entries(tool.inputSchema.properties).map(
                        ([key, prop]) => (
                          <div
                            key={key}
                            className="flex items-baseline gap-2 font-mono"
                          >
                            <span className="text-cyan-400/80">{key}</span>
                            <span className="text-neutral-600">:</span>
                            <span className="text-amber-400/70">
                              {prop.type}
                            </span>
                            {requiredParams.includes(key) && (
                              <span className="text-red-400/60 text-[10px]">
                                required
                              </span>
                            )}
                            {prop.default !== undefined && (
                              <span className="text-neutral-600">
                                = {JSON.stringify(prop.default)}
                              </span>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {/* Resources Section */}
      {resources.length > 0 && (
        <div className="mt-6 pt-4 border-t border-white/[0.06]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-neutral-300">
              Resources
            </h3>
            <span className="text-xs font-mono text-neutral-500 bg-white/[0.04] px-2 py-1 rounded">
              {resources.length}
            </span>
          </div>
          <ul className="space-y-1.5">
            {resources.map((resource) => (
              <li
                key={resource.uri}
                className="flex items-center gap-2 p-2 rounded text-sm"
              >
                <span className="text-blue-400/70 text-xs">📄</span>
                <span className="text-neutral-300 font-mono text-xs truncate">
                  {resource.name}
                </span>
                {resource.mimeType && (
                  <span className="text-neutral-600 text-[10px] font-mono ml-auto shrink-0">
                    {resource.mimeType}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
