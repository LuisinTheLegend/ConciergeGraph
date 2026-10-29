# run_e7_decouple.py
# Experimento E7 da Rodada 4.2e-3:
# Desacoplar o fd 0 (workaround probe)
# Variantes:
#   (a) a_dup2_nul: nul=os.open(os.devnull), fd2=os.dup(0), os.dup2(nul, 0)
#   (b) b_setstdhandle: alem de (a), SetStdHandle(STD_INPUT_HANDLE, nul_handle)
#   (c) control_fd0: leitor direto em fd 0 (sys.stdin.buffer), esperado TRAVOU
# Imports testados: (1) numpy, (2) scipy.special, (3) torch, (4) sentence_transformers
# n=5 por variante e import, timeout 120s.
# Integridade do canal: pai envia "ping\n" e filho confirma recebimento pelo leitor.

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e7_decouple"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e7.txt"

CHILD_TEMPLATE_VAR_A = r"""
import os, sys, threading, time

nul = os.open(os.devnull, os.O_RDONLY)
fd2 = os.dup(0)
os.dup2(nul, 0)

reader_file = os.fdopen(fd2, "rb")
ping_received = False

def reader():
    global ping_received
    try:
        line = reader_file.readline()
        if b"ping" in line:
            ping_received = True
            sys.stdout.write("ping_received=True\n")
            sys.stdout.flush()
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

{import_statement}

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()

# Aguarda recepcao do ping
for _ in range(50):
    if ping_received:
        break
    time.sleep(0.1)

sys.exit(0 if ping_received else 2)
"""

CHILD_TEMPLATE_VAR_B = r"""
import os, sys, threading, time, ctypes, msvcrt

nul = os.open(os.devnull, os.O_RDONLY)
fd2 = os.dup(0)
os.dup2(nul, 0)

kernel32 = ctypes.windll.kernel32
STD_INPUT_HANDLE = -10
nul_handle = msvcrt.get_osfhandle(nul)
kernel32.SetStdHandle(STD_INPUT_HANDLE, nul_handle)

reader_file = os.fdopen(fd2, "rb")
ping_received = False

def reader():
    global ping_received
    try:
        line = reader_file.readline()
        if b"ping" in line:
            ping_received = True
            sys.stdout.write("ping_received=True\n")
            sys.stdout.flush()
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

{import_statement}

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()

for _ in range(50):
    if ping_received:
        break
    time.sleep(0.1)

sys.exit(0 if ping_received else 2)
"""

CHILD_TEMPLATE_CONTROL = r"""
import sys, threading, time

ping_received = False

def reader():
    global ping_received
    try:
        line = sys.stdin.buffer.readline()
        if b"ping" in line:
            ping_received = True
            sys.stdout.write("ping_received=True\n")
            sys.stdout.flush()
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

{import_statement}

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()

for _ in range(50):
    if ping_received:
        break
    time.sleep(0.1)

sys.exit(0 if ping_received else 2)
"""

VARIANTS = {
    "a_dup2_nul": CHILD_TEMPLATE_VAR_A,
    "b_setstdhandle": CHILD_TEMPLATE_VAR_B,
    "control_fd0": CHILD_TEMPLATE_CONTROL,
}

IMPORTS = {
    "numpy": "import numpy",
    "scipy_special": "import scipy.special",
    "torch": "import torch",
    "sentence_transformers": "import sentence_transformers",
}

REPS = 5
TIMEOUT = 120.0

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_e7_case(var_name: str, imp_name: str, rep: int) -> dict:
    case_dir = OUTDIR / f"{var_name}__{imp_name}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    out_file = case_dir / "stdout.txt"
    err_file = case_dir / "stderr.txt"
    res_file = case_dir / "result.json"

    template = VARIANTS[var_name]
    code = template.format(import_statement=IMPORTS[imp_name])

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TQDM_DISABLE"] = "1"

    t0 = time.perf_counter()
    p = subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    stdout_lines = []
    
    def stdout_reader_thread():
        try:
            for line in iter(p.stdout.readline, ''):
                stdout_lines.append(line)
                if "import_ok=True" in line:
                    try:
                        p.stdin.write("ping\n")
                        p.stdin.flush()
                    except Exception:
                        pass
        except Exception:
            pass

    t_reader = threading.Thread(target=stdout_reader_thread, daemon=True)
    t_reader.start()

    timed_out = False
    while True:
        elapsed = time.perf_counter() - t0
        if elapsed > TIMEOUT:
            timed_out = True
            break
        if p.poll() is not None:
            break
        time.sleep(0.1)

    duration = time.perf_counter() - t0
    stderr_content = ""

    if timed_out:
        classe = "TRAVOU"
        try:
            p.kill()
            rem_out, rem_err = p.communicate(timeout=5)
            if rem_out:
                stdout_lines.append(rem_out)
            if rem_err:
                stderr_content = rem_err
        except Exception:
            pass
    else:
        try:
            rem_out, rem_err = p.communicate(timeout=5)
            if rem_out:
                stdout_lines.append(rem_out)
            if rem_err:
                stderr_content = rem_err
        except Exception:
            pass
        full_out = "".join(stdout_lines)
        if p.returncode == 0 and "import_ok=True" in full_out and "ping_received=True" in full_out:
            classe = "OK"
        elif "import_ok=True" in full_out and "ping_received=True" not in full_out:
            classe = "ERRO_PING"
        else:
            classe = "ERRO"

    full_stdout = "".join(stdout_lines)
    reader_blocked = "reader_blocked=True" in full_stdout
    import_ok = "import_ok=True" in full_stdout
    ping_received = "ping_received=True" in full_stdout

    out_file.write_text(full_stdout, encoding="utf-8")
    err_file.write_text(stderr_content, encoding="utf-8")

    result = {
        "variant": var_name,
        "import": imp_name,
        "rep": rep,
        "classe": classe,
        "time_s": round(duration, 2),
        "reader_blocked": reader_blocked,
        "import_ok": import_ok,
        "ping_received": ping_received,
        "returncode": p.returncode,
    }
    res_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def save_table(results: list[dict]):
    lines = []
    lines.append("=== TABELA EXPERIMENTO E7: DESACOPLAR O FD 0 (n=5 cada) ===")
    lines.append(f"{'Variante':<16} | {'Modulo':<22} | {'Rep':<4} | {'Classe':<10} | {'Tempo(s)':<9} | {'Blocked':<8} | {'Imp OK':<8} | {'Ping OK'}")
    lines.append("-" * 96)
    for r in results:
        lines.append(
            f"{r['variant']:<16} | {r['import']:<22} | {r['rep']:<4} | {r['classe']:<10} | {r['time_s']:<9.2f} | "
            f"{str(r['reader_blocked']):<8} | {str(r['import_ok']):<8} | {str(r['ping_received'])}"
        )
    lines.append("-" * 96)
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    log("INICIANDO EXPERIMENTO E7 — DESACOPLAR O FD 0 (n=5 cada)")
    results = []

    variant_order = ["a_dup2_nul", "b_setstdhandle", "control_fd0"]
    for var_name in variant_order:
        for imp_name in IMPORTS.keys():
            for rep in range(1, REPS + 1):
                log(f"INICIO rep={rep} var={var_name} imp={imp_name}")
                res = run_e7_case(var_name, imp_name, rep)
                log(f"FIM    rep={rep} var={var_name} imp={imp_name} -> {res['classe']} em {res['time_s']:.2f}s (blocked={res['reader_blocked']}, imp_ok={res['import_ok']}, ping={res['ping_received']})")
                results.append(res)
                save_table(results)

    save_table(results)
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    main()
