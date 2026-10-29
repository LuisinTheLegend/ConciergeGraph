import os, sys
import scipy.special
import sklearn.utils._array_api
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server-f")

@m.tool(name="run_action")
def run_action() -> str:
    import scipy.special
    return "ok"

if __name__ == "__main__":
    m.run(transport="stdio")
