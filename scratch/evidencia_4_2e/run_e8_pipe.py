# run_e8_pipe.py
# Experimento E8 da Rodada 4.2e-3:
# Leitor em pipe que NÃO é o stdin (os.pipe criado no proprio filho, sem escritor)
# Child com stdin=DEVNULL. Thread leitora bloqueada em os.read(r, 1).
# Testes: (1) import numpy; (2) import scipy.special
# n=5 por caso, timeout 120s.

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e8_pipe"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e8.txt"

CHILD_TEMPLATE = r"""
import os, sys, threading, time

r, w = os.pipe()

def reader():
    try:
        os.read(r, 1)
    except Exception:
        pass

t = threading.Thread(target=reader, daemon=True, name="pipe-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()
else:
    sys.stdout.write("reader_blocked=False\n")
    sys.stdout.flush()

# Executa o import sob teste
{import_statement}

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

CASES = {
    "numpy": CHILD_TEMPLATE.format(import_statement="import numpy"),
    "scipy_special": CHILD_TEMPLATE.format(import_statement="import scipy.special"),
}

REPS = 5
TIMEOUT = 120.0

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_case_rep(case_name: str, code: str, rep: int) -> dict:
    case_dir = OUTDIR / f"{case_name}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    out_file = case_dir / "stdout.txt"
    err_file = case_dir / "stderr.txt"
    res_file = case_dir / "result.json"

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    t0 = time.perf_counter()
    p = subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    timed_out = False
    stdout_lines = []
    stderr_content = ""

    while True:
        elapsed = time.perf_counter() - t0
        if elapsed > TIMEOUT:
            timed_out = True
            break
        ret = p.poll()
        if ret is not None:
            break
        time.sleep(0.5)

    duration = time.perf_counter() - t0

    if timed_out:
        classe = "TRAVOU"
        try:
            p.kill()
            stdout_data, stderr_data = p.communicate(timeout=5)
            if stdout_data:
                stdout_lines.append(stdout_data)
            if stderr_data:
                stderr_content = stderr_data
        except Exception:
            pass
    else:
        try:
            stdout_data, stderr_data = p.communicate(timeout=5)
            if stdout_data:
                stdout_lines.append(stdout_data)
            if stderr_data:
                stderr_content = stderr_data
        except Exception:
            pass
        classe = "OK" if p.returncode == 0 else "ERRO"

    full_stdout = "".join(stdout_lines)
    reader_blocked = "reader_blocked=True" in full_stdout
    import_ok = "import_ok=True" in full_stdout

    if timed_out:
        classe = "TRAVOU"
    elif not import_ok:
        classe = "ERRO"

    out_file.write_text(full_stdout, encoding="utf-8")
    err_file.write_text(stderr_content, encoding="utf-8")

    result = {
        "case": case_name,
        "rep": rep,
        "classe": classe,
        "time_s": round(duration, 2),
        "reader_blocked": reader_blocked,
        "import_ok": import_ok,
        "returncode": p.returncode,
    }
    res_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def main():
    log("INICIANDO EXPERIMENTO E8 — LEITOR EM PIPE QUE NÃO É STDIN (n=5 cada)")
    results = []
    for rep in range(1, REPS + 1):
        for case_name, code in CASES.items():
            log(f"INICIO rep={rep} caso={case_name}")
            res = run_case_rep(case_name, code, rep)
            log(f"FIM    rep={rep} caso={case_name} -> {res['classe']} em {res['time_s']:.2f}s (reader_blocked={res['reader_blocked']})")
            results.append(res)

    lines = []
    lines.append("=== TABELA EXPERIMENTO E8: LEITOR EM PIPE QUE NÃO É STDIN (n=5 cada) ===")
    lines.append(f"{'Caso':<15} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'Reader Blocked':<15} | {'Import OK':<10}")
    lines.append("-" * 75)
    for r in results:
        lines.append(
            f"{r['case']:<15} | {r['rep']:<4} | {r['classe']:<8} | {r['time_s']:<9.2f} | "
            f"{str(r['reader_blocked']):<15} | {str(r['import_ok']):<10}"
        )
    lines.append("-" * 75)
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    main()

