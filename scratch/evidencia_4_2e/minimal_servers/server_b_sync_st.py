import os, sys
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server")

@m.tool(name="run_action")
def run_action() -> str:
    import sentence_transformers
    return "ok"

if __name__ == "__main__":
    m.run(transport="stdio")

