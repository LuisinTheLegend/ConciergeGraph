import faulthandler, os, sys
from mcp.server.fastmcp import FastMCP

m = FastMCP("minimal-server-a")

@m.tool(name="run_action")
def run_action() -> str:
    dump_path = os.environ.get("TRACE_DUMP_FILE")
    f = None
    if dump_path:
        f = open(dump_path, "w", encoding="utf-8")
        faulthandler.dump_traceback_later(15, repeat=False, file=f)
    try:
        import scipy.special
    finally:
        if dump_path:
            faulthandler.cancel_dump_traceback_later()
            try:
                f.close()
            except Exception:
                pass
    return "ok"

if __name__ == "__main__":
    m.run(transport="stdio")
