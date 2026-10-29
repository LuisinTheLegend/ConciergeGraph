# run_e4_pyspy.py
# Experimento E4: Captura de pilha nativa via py-spy durante o travamento de E1(i)

import os
import sys
import time
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT_FILE = HERE / "pyspy_native_dump.txt"

TEMP_PYSPY = Path(os.environ.get("TEMP", "C:/Temp")) / "venv_pyspy" / "Scripts" / "py-spy.exe"

CHILD_CODE = r"""
import sys, threading, time

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()

import scipy.special

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
"""

def run_e4():
    print(f"py-spy binary: {TEMP_PYSPY}")
    if not TEMP_PYSPY.exists():
        msg = f"ERRO: py-spy nao encontrado em {TEMP_PYSPY}\n"
        OUTPUT_FILE.write_text(msg, encoding="utf-8")
        print(msg)
        return

    print("Iniciando processo travado (E1(i) com stdin aberto)...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    p = subprocess.Popen(
        [sys.executable, "-u", "-c", CHILD_CODE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    
    # Aguarda 5 segundos para garantir que a thread de leitura bloqueou e o import iniciou e travou
    time.sleep(5)
    
    print(f"Processo filho PID: {p.pid}, poll={p.poll()}")
    if p.poll() is not None:
        stdout, stderr = p.communicate()
        msg = f"PROCESSO TERMINOU PREMATURAMENTE (exit={p.returncode})\nstdout={stdout}\nstderr={stderr}\n"
        OUTPUT_FILE.write_text(msg, encoding="utf-8")
        print(msg)
        return

    print("Executando py-spy dump --native...")
    py_spy_cmd = [str(TEMP_PYSPY), "dump", "--native", "--pid", str(p.pid)]
    try:
        res = subprocess.run(
            py_spy_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        dump_output = (
            f"=== PY-SPY DUMP NATIVE (PID {p.pid}) ===\n"
            f"Exit code: {res.returncode}\n"
            f"--- STDOUT ---\n{res.stdout}\n"
            f"--- STDERR ---\n{res.stderr}\n"
        )
    except Exception as e:
        dump_output = f"ERRO AO EXECUTAR PY-SPY: {type(e).__name__}: {e}\n"

    print("Salvando saida em:", OUTPUT_FILE)
    OUTPUT_FILE.write_text(dump_output, encoding="utf-8")
    print(dump_output)

    # Mata o processo filho
    try:
        p.kill()
        p.communicate()
    except Exception:
        pass
    print("Processo filho finalizado.")

if __name__ == "__main__":
    run_e4()
