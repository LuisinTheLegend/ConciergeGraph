import os, subprocess, sys, time
S = r"C:\Users\guial\.gemini\antigravity\brain\74748901-a8f5-45d9-a8b8-d486be789891\scratch\dump_mine_hang.py"
for mode in ("sync", "thread"):
    e = dict(os.environ, DIAG_ACTION="search", DIAG_TIMEOUT="75", DIAG_PREIMPORT=mode)
    t0 = time.time()
    r = subprocess.run([sys.executable, S], env=e, capture_output=True, text=True, timeout=150)
    out = r.stdout
    status = "TRAVOU" if "TIMED OUT" in out else ("OK" if "completed" in out else "?")
    print(f"preimport={mode}: {status} em {time.time()-t0:.1f}s | {out.strip().splitlines()[-1][:160] if out.strip() else ''}", flush=True)
