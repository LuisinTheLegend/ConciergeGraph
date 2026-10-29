import os, sys
import sentence_transformers
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server")

@m.tool(name="run_action")
def run_action() -> str:
    return "ok"

if __name__ == "__main__":
    m.run(transport="stdio")

