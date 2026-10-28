import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

REPO_ROOT = Path(r"c:\Nexus-Memory\GrafoConcierge")
sys.path.insert(0, str(REPO_ROOT))

def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

tmp_dir = tempfile.mkdtemp(prefix="diag_")
os.environ["GRAFO_DB_PATH"] = os.path.join(tmp_dir, "d.db")
os.environ["GRAFO_CHROMA_PATH"] = os.path.join(tmp_dir, "chroma")
os.environ["GRAFO_CHROMA_COLLECTION"] = "diag_col"

log("1. Calling main.bootstrap()...")
from main import bootstrap
server, janitor, store = bootstrap()
gc = server._gc
log("2. Bootstrap OK! Registering project...")

from scratch.evidencia_4_2e.mcp_e2e_v2 import create_sample_project
proj_dir = os.path.join(tmp_dir, "proj")
create_sample_project(proj_dir)
proj_uuid = gc.register_project(proj_dir, "geral", "PUBLIC", "Diag")
log(f"3. Registered {proj_uuid}. Now hooking EmbeddingManager._load_model...")

from storage.vector_store import EmbeddingManager
orig_load = EmbeddingManager._load_model

def traced_load(self):
    log("   -> ENTERED _load_model()")
    import builtins
    orig_imp = builtins.__import__
    def imp(name, globals=None, locals=None, fromlist=(), level=0):
        t0 = time.perf_counter()
        if level == 0 and any(name.startswith(p) for p in ("torch", "transformers", "sentence_transformers", "scipy", "sklearn")):
            log(f"      [import start] {name} (fromlist={fromlist})")
        r = orig_imp(name, globals, locals, fromlist, level)
        dt = time.perf_counter() - t0
        if dt > 0.2:
            log(f"      [import done ] {name} in {dt:.2f}s")
        return r
    builtins.__import__ = imp
    try:
        return orig_load(self)
    finally:
        builtins.__import__ = orig_imp
        log("   -> EXITED _load_model()")

EmbeddingManager._load_model = traced_load

log("4. Calling gc.mine()...")
res = gc.mine(proj_uuid, proj_dir, auto_tag=True)
log(f"5. gc.mine() DONE! res={res}")
store.close()
shutil.rmtree(tmp_dir, ignore_errors=True)
