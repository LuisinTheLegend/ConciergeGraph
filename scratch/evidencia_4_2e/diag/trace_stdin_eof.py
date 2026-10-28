"""Trace where main.py blocks when stdin is closed."""
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

CHILD_CODE = r"""
import os, sys, threading, time, traceback

def dump_stacks():
    for attempt in range(1, 10):
        time.sleep(2.0)
        with open(os.environ["DIAG_STACK_FILE"], "a", encoding="utf-8") as f:
            f.write(f"\n=== STACK DUMP AT +{attempt*2}s ===\n")
            for tid, frame in sys._current_frames().items():
                f.write(f"--- Thread {tid} ---\n")
                f.write("".join(traceback.format_stack(frame)))
            f.flush()

t = threading.Thread(target=dump_stacks, daemon=True)
t.start()

import main
main.main()
"""

def run():
    d = Path(tempfile.mkdtemp(prefix="diag_stack_"))
    stack_file = d / "stacks.txt"
    err_file = d / "stderr.txt"
    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = str(d / "db.sqlite")
    env["GRAFO_CHROMA_PATH"] = str(d / "chroma")
    env["DIAG_STACK_FILE"] = str(stack_file)
    env["PYTHONUTF8"] = "1"

    with open(err_file, "wb") as ef:
        p = subprocess.Popen(
            [sys.executable, "-c", CHILD_CODE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=ef,
            env=env,
        )
        p.stdin.close()
        try:
            rc = p.wait(timeout=7)
            print("EXITED WITH RC:", rc)
        except subprocess.TimeoutExpired:
            print("TIMED OUT AFTER 7s! Killing child.")
            p.kill()
            p.wait()

    if stack_file.exists():
        print(stack_file.read_text(encoding="utf-8", errors="replace"))
    else:
        print("No stack file produced!")
        print("STDERR:", err_file.read_text(encoding="utf-8", errors="replace"))

if __name__ == "__main__":
    run()
