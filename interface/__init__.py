"""
interface/ - External Interface of Grafo Concierge v3.8.0

Modules:
    mcp_server.py    -> FastMCP server with 7 tools (mine, search, commit, wakeup, resume, load, status)
    action_hooks.py  -> Reactive lifecycle triggers (on_planning, on_execution, on_done)
    cli.py           -> Terminal interface (argparse) with 9 commands
"""

import importlib
import sys
from typing import Any

from interface.mcp_server import GrafoConciergeServer

__all__ = [
    "GrafoConciergeServer",
    "ActionHooks",
]


def __getattr__(name: str) -> Any:
    """Exportação preguiçosa (PEP 562) para cortar a cadeia de importação de agents.revisor_critico e expor submódulos."""
    if name == "ActionHooks":
        from interface.action_hooks import ActionHooks
        return ActionHooks
    submod_name = f"interface.{name}"
    if submod_name in sys.modules:
        val = sys.modules[submod_name]
        globals()[name] = val
        return val
    try:
        val = importlib.import_module(submod_name)
        globals()[name] = val
        return val
    except (ImportError, ModuleNotFoundError):
        pass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")