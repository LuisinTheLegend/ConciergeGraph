# scratch/evidencia_4_2f/run_shutdown_check.py
import subprocess
import sys
import time
import os
import tempfile
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

results = []
for rep in range(1, 4):
    tmp = tempfile.mkdtemp(prefix=f"shutdown_check_{rep}_")
    try:
        env = os.environ.copy()
        env.update({
            "GRAFO_DB_PATH": os.path.join(tmp, "test.db"),
            "GRAFO_CHROMA_PATH": os.path.join(tmp, "chroma"),
            "GRAFO_TRANSPORT": "stdio",
            "PYTHONUNBUFFERED": "1",
            "PYTHONUTF8": "1",
            "PYTHONPATH": str(REPO_ROOT),
        })
        p = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
        )
        started = False
        t_boot_start = time.perf_counter()
        while time.perf_counter() - t_boot_start < 30.0:
            line = p.stderr.readline()
            if "Starting MCP server" in line:
                started = True
                break
            if not line and p.poll() is not None:
                break
        if not started:
            results.append((rep, "FALHA_STARTUP", 0.0, p.poll()))
            continue

        t0 = time.perf_counter()
        p.stdin.close()
        try:
            rc = p.wait(timeout=15.0)
            dur = time.perf_counter() - t0
            status = "OK" if dur < 15.0 and rc == 0 else f"ERRO(rc={rc})"
            results.append((rep, status, dur, rc))
        except subprocess.TimeoutExpired:
            p.kill()
            results.append((rep, "TIMEOUT", 15.0, -1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

out = []
out.append("=== TESTE DE ENCERRAMENTO GRACIOSO APOS FECHAMENTO DE STDIN (Passo 4h) ===")
out.append(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
out.append("Limite maximo aceitavel: < 15.0s")
out.append("")
out.append("Repeticao | Status | Tempo Encerramento (s) | Codigo Saida")
out.append("-----------------------------------------------------------")
for rep, status, dur, rc in results:
    out.append(f"{rep:^9} | {status:^6} | {dur:^22.4f} | {rc:^12}")
out.append("-----------------------------------------------------------")
all_ok = all(s == "OK" for _, s, _, _ in results)
out.append(f"Conclusao: {'TODOS PASSARAM (<15s)' if all_ok else 'HOUVE FALHA'}")

text = "\n".join(out) + "\n"
out_path = REPO_ROOT / "scratch" / "evidencia_4_2f" / "shutdown_check.txt"
out_path.write_text(text, encoding="utf-8")
print(text)

