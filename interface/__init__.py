"""
interface/ - External Interface of Grafo Concierge v3.8.0

Modules:
    mcp_server.py    -> FastMCP server with 7 tools (mine, search, commit, wakeup, resume, load, status)
    action_hooks.py  -> Reactive lifecycle triggers (on_planning, on_execution, on_done)
    cli.py           -> Terminal interface (argparse) with 9 commands
"""

from interface.mcp_server import GrafoConciergeServer
from interface.action_hooks import ActionHooks

__all__ = [
    "GrafoConciergeServer",
    "ActionHooks",
]