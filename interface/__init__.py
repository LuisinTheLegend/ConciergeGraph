"""
interface/ — Interface Externa do Grafo Concierge v3.8.0

Módulos:
    mcp_server.py    → Servidor FastMCP com 7 tools (mine, search, commit, wakeup, resume, load, status)
    action_hooks.py  → Gatilhos reativos de ciclo de vida (on_planning, on_execution, on_done)
    cli.py           → Interface de terminal (argparse) com 9 comandos
"""

from interface.mcp_server import GrafoConciergeServer
from interface.action_hooks import ActionHooks

__all__ = [
    "GrafoConciergeServer",
    "ActionHooks",
]