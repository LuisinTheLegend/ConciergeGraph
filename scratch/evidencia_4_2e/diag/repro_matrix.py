"""Matriz de reprodução: import scipy.special com/sem leitor de stdin bloqueado. Cada caso roda em subprocesso com timeout duro."""
import subprocess, sys, time

CASES = {
    "A_import_sem_stdin_reader": "import scipy.special; print('ok')",
    "B_thread_le_stdin_buffer_depois_import_na_main": (
        "import sys, threading, time\n"
        "threading.Thread(target=lambda: sys.stdin.buffer.readline(), daemon=True).start()\n"
        "time.sleep(0.5)\n"
        "import scipy.special; print('ok')"
    ),
    "C_thread_le_stdin_import_na_thread_secundaria": (
        "import sys, threading, time\n"
        "threading.Thread(target=lambda: sys.stdin.buffer.readline(), daemon=True).start()\n"
        "time.sleep(0.5)\n"
        "def f():\n    import scipy.special; print('ok')\n"
        "t=threading.Thread(target=f); t.start(); t.join()"
    ),
    "D_stdin_DEVNULL_import": "import scipy.special; print('ok')",
}

for name, code in CASES.items():
    stdin = subprocess.DEVNULL if name.startswith("D_") else subprocess.PIPE
    t0 = time.time()
    p = subprocess.Popen([sys.executable, "-c", code], stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=60) if stdin == subprocess.DEVNULL else p.communicate(timeout=60)
        print(f"{name}: rc={p.returncode} {time.time()-t0:.1f}s out={out.strip()!r} err={err.strip()[-120:]!r}", flush=True)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate()
        print(f"{name}: TIMEOUT 60s (travou)", flush=True)
