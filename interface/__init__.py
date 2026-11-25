"""
interface/ - External Interface of Grafo Concierge

Modules:
    mcp_server.py -> FastMCP server with 31 MCP tools (governed by MCPToolGovernor)
    cli.py        -> Terminal interface (argparse) with 10 commands
"""

from interface.mcp_server import GrafoConciergeServer

__all__ = [
    "GrafoConciergeServer",
]