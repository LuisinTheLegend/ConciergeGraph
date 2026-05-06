"""
server/ — Servidor MCP do Grafo Concierge v3.8.0

Módulos:
    mcp_server.py → Servidor FastMCP com tools concierge_mine, concierge_search, concierge_status
"""

from server.mcp_server import GrafoConciergeServer

__all__ = [
    "GrafoConciergeServer",
]