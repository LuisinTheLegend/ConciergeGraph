import os, sys
import scipy.special
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server-e")

@m.tool(name="run_action")
def run_action() -> str:
    import scipy.special
    return "ok"

if __name__ == "__main__":
    m.run(transport="stdio")

