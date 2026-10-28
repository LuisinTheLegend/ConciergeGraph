"""Isolate why scipy.special / sentence_transformers hangs inside MCP stdio server."""
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(r"c:\Nexus-Memory\GrafoConcierge")


async def run_case(name: str, action: str) -> None:
    print(f"\n=== CASE: {name} ===", flush=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"diag_{name}_"))
    proj_dir = tmp_dir / "proj"
    proj_dir.mkdir()
    (proj_dir / "mod.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["GRAFO_DB_PATH"] = str(tmp_dir / "db.sqlite")
    env["GRAFO_CHROMA_PATH"] = str(tmp_dir / "chroma")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(REPO_ROOT / "main.py")],
        env=env,
        cwd=str(REPO_ROOT),
    )
    err_path = tmp_dir / "stderr.log"
    t0 = time.perf_counter()
    try:
        with open(err_path, "w", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as (r, w):
                async with ClientSession(r, w) as session:
                    await asyncio.wait_for(session.initialize(), timeout=15)
                    print(f"  initialize ok ({time.perf_counter() - t0:.2f}s)", flush=True)
                    reg = await asyncio.wait_for(
                        session.call_tool("concierge_register", {"project_path": str(proj_dir), "wing": "diag"}),
                        timeout=15,
                    )
                    print(f"  register ok ({time.perf_counter() - t0:.2f}s)", flush=True)
                    if action == "search_first":
                        t_s = time.perf_counter()
                        res = await asyncio.wait_for(
                            session.call_tool("concierge_search", {"query": "add", "project_identifier": "diag"}),
                            timeout=45,
                        )
                        print(f"  search_first ok in {time.perf_counter() - t_s:.2f}s", flush=True)
                        t_m = time.perf_counter()
                        res_m = await asyncio.wait_for(
                            session.call_tool("concierge_mine", {"path": str(proj_dir), "project_identifier": "diag"}),
                            timeout=60,
                        )
                        print(f"  mine after search ok in {time.perf_counter() - t_m:.2f}s", flush=True)
                    elif action == "mine_first":
                        t_m = time.perf_counter()
                        res_m = await asyncio.wait_for(
                            session.call_tool("concierge_mine", {"path": str(proj_dir), "project_identifier": "diag"}),
                            timeout=60,
                        )
                        print(f"  mine_first ok in {time.perf_counter() - t_m:.2f}s", flush=True)
    except asyncio.TimeoutError:
        print(f"  TIMEOUT after {time.perf_counter() - t0:.2f}s!", flush=True)
        print("  --- stderr tail ---", flush=True)
        print(err_path.read_text(encoding="utf-8", errors="replace")[-1500:], flush=True)


async def main() -> None:
    await run_case("search_first", "search_first")
    await run_case("mine_first", "mine_first")


if __name__ == "__main__":
    asyncio.run(main())
