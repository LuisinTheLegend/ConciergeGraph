import os, sys
import anyio.to_thread
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server")

def _do_import():
    import sentence_transformers
    return "ok"

@m.tool(name="run_action")
async def run_action() -> str:
    return await anyio.to_thread.run_sync(_do_import)

if __name__ == "__main__":
    m.run(transport="stdio")

