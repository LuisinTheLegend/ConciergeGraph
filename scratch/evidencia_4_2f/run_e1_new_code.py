# scratch/evidencia_4_2f/run_e1_new_code.py
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CHILD_SCRIPT = r"""
import os, sys, threading, time
sys.path.insert(0, r"{repo_root}")
import main

# Chama explicitamente o novo codigo de desacoplamento
decoupled = main.decouple_stdin_from_fd0()
if not decoupled:
    sys.stderr.write("ERRO: decouple_stdin_from_fd0 retornou False\n")
    sys.exit(1)

def reader():
    try:
        sys.stdin.buffer.readline()
    except Exception:
        pass

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()
else:
    sys.stdout.write("reader_blocked=False\n")
    sys.stdout.flush()
    sys.exit(2)

# Importacao critica que antes travava sob fd 0
import scipy.special

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()

# Saida limpa com os._exit(0) para evitar colisão do CRT durante encerramento com thread leitora em background
os._exit(0)
"""

results = []
code = CHILD_SCRIPT.replace("{repo_root}", str(REPO_ROOT))

for rep in range(1, 6):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["GRAFO_STDIN_DECOUPLE"] = "1"

    t0 = time.perf_counter()
    p = subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )

    # Monitora mantendo o stdin ativamente ABERTO (nunca chamar communicate() antes do processo encerrar)
    timed_out = False
    while True:
        elapsed = time.perf_counter() - t0
        if elapsed > 60.0:
            timed_out = True
            p.kill()
            break
        if p.poll() is not None:
            break
        time.sleep(0.1)

    dur = time.perf_counter() - t0
    stdout, stderr = p.communicate(timeout=5.0)
    rc = p.returncode
    reader_blocked = "reader_blocked=True" in stdout
    import_ok = "import_ok=True" in stdout

    if not timed_out and rc == 0 and reader_blocked and import_ok:
        status = "OK"
    elif timed_out:
        status = "TRAVOU(TIMEOUT)"
    else:
        status = f"FALHA(rc={rc})"
    results.append((rep, status, dur, reader_blocked, import_ok, rc))

out = []
out.append("=== EXPERIMENTO E1-(i) COM main.decouple_stdin_from_fd0() (Passo 4g) ===")
out.append(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")
out.append("Cenário: import scipy.special na thread principal com leitor de stdin bloqueado")
out.append("Número de repetições: n=5, Timeout: 60s por repetição")
out.append("")
out.append("Rep | Status | Tempo (s) | reader_blocked | import_ok | Codigo Saida")
out.append("--------------------------------------------------------------------")
for rep, status, dur, rb, imp, rc in results:
    out.append(f"{rep:^3} | {status:^6} | {dur:^9.4f} | {str(rb):^14} | {str(imp):^9} | {rc:^12}")
out.append("--------------------------------------------------------------------")
all_ok = all(s == "OK" for _, s, _, _, _, _ in results)
out.append(f"Conclusão: {'5/5 OK - Deadlock eliminado com sucesso' if all_ok else 'HOUVE FALHA'}")

text = "\n".join(out) + "\n"
out_file = REPO_ROOT / "scratch" / "evidencia_4_2f" / "e1_new_code.txt"
out_file.write_text(text, encoding="utf-8")
print(text)
