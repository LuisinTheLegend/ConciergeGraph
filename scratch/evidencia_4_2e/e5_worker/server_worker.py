
import sys, subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WorkerFeasibilityServer")

@mcp.tool()
def test_import_worker() -> str:
    res = subprocess.run(
        [sys.executable, "-c", "import scipy.special"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120
    )
    return f"worker_exit={res.returncode};stdout={res.stdout.strip()};stderr={res.stderr.strip()}"

if __name__ == "__main__":
    mcp.run()
