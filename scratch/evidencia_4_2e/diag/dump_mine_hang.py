"""Dump stack of MCP server child process when it hangs in concierge_mine."""
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(r"c:\Nexus-Memory\GrafoConcierge")

WRAPPER = r"""
import os, sys, threading, time, traceback

def dumper():
    start = time.time()
    while True:
        time.sleep(5.0)
        elapsed = int(time.time() - start)
        with open(os.environ["STACK_DUMP_FILE"], "a", encoding="utf-8") as f:
            f.write(f"\n=== SERVER STACK AT +{elapsed}s ===\n")
            for tid, frame in sys._current_frames().items():
                tname = next((t.name for t in threading.enumerate() if t.ident == tid), "unknown")
                f.write(f"--- Thread {tid} ({tname}) ---\n")
                f.write("".join(traceback.format_stack(frame)))
            f.flush()

threading.Thread(target=dumper, daemon=True, name="stack-dumper").start()
import main
_mode = os.environ.get("DIAG_PREIMPORT", "")
if _mode == "sync":
    import sentence_transformers
elif _mode == "thread":
    threading.Thread(target=lambda: __import__("sentence_transformers"), daemon=True, name="pre").start()
main.main()
"""

async def run_test():
    d = Path(tempfile.mkdtemp(prefix="dump_mine_"))
    proj = d / "proj"
    proj.mkdir()
    (proj / "a.py").write_text("def foo(): return 42\n", encoding="utf-8")
    stack_file = d / "stacks.txt"
    err_file = d / "stderr.txt"

    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = str(d / "db.sqlite")
    env["GRAFO_CHROMA_PATH"] = str(d / "chroma")
    env["STACK_DUMP_FILE"] = str(stack_file)
    env["PYTHONUTF8"] = "1"
    if os.environ.get("DIAG_NO_LLM") == "1":
        env["GRAFO_LLM_API_KEY"] = ""
        env["GRAFO_LLM_MODEL"] = "none"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", WRAPPER],
        env=env,
        cwd=str(REPO_ROOT),
    )

    with open(err_file, "w", encoding="utf-8") as ef:
        async with stdio_client(params, errlog=ef) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                print("Initialized!", flush=True)
                await session.call_tool("concierge_register", {"project_path": str(proj), "wing": "w"})
                print("Registered! Calling concierge_mine...", flush=True)
                try:
                    if os.environ.get("DIAG_ACTION") == "search":
                        call = session.call_tool("concierge_search", {"query": "foo", "project_identifier": "proj"})
                    else:
                        call = session.call_tool("concierge_mine", {"path": str(proj), "project_identifier": "proj"})
                    res = await asyncio.wait_for(
                        call,
                        timeout=float(os.environ.get("DIAG_TIMEOUT", "35")),
                    )
                    print("concierge_mine completed!", res, flush=True)
                except asyncio.TimeoutError:
                    print("concierge_mine TIMED OUT after 35s! Reading stack dump:", flush=True)
                    if stack_file.exists():
                        txt = stack_file.read_text(encoding="utf-8", errors="replace")
                        print(txt[-4000:], flush=True)
                    os._exit(0)

if __name__ == "__main__":
    asyncio.run(run_test())
