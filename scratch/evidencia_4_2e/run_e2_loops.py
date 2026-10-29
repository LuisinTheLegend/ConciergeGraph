# run_e2_loops.py
# Experimento E2: Loop de eventos com stdin aberto e leitor bloqueado
# Variantes: (a) Proactor ativo; (b) Selector ativo; (c) sem asyncio
# n=5 por variante, timeout 120s

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e2_loops"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e2.txt"

CHILD_TEMPLATE_PROACTOR = r"""
import sys, threading, time, asyncio

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()
else:
    sys.stdout.write("reader_blocked=False\n")
    sys.stdout.flush()

async def main():
    import scipy.special

asyncio.run(main())

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

CHILD_TEMPLATE_SELECTOR = r"""
import sys, threading, time, asyncio

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()
else:
    sys.stdout.write("reader_blocked=False\n")
    sys.stdout.flush()

async def main():
    import scipy.special

with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
    runner.run(main())

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

CHILD_TEMPLATE_NO_ASYNCIO = r"""
import sys, threading, time

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write("reader_blocked=True\n")
    sys.stdout.flush()
else:
    sys.stdout.write("reader_blocked=False\n")
    sys.stdout.flush()

import scipy.special

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

VARIANTS = {
    "a_proactor": CHILD_TEMPLATE_PROACTOR,
    "b_selector": CHILD_TEMPLATE_SELECTOR,
    "c_no_asyncio": CHILD_TEMPLATE_NO_ASYNCIO,
}

TIMEOUT = 120.0
REPS = 5

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_variant_rep(v_name: str, code: str, rep: int) -> dict:
    case_dir = OUTDIR / f"{v_name}__rep{rep}"
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
        stdin=subprocess.PIPE,
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
        "variant": v_name,
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
    log("INICIANDO EXPERIMENTO E2 — LOOP DE EVENTOS COM STDIN ABERTO")
    results = []
    for rep in range(1, REPS + 1):
        for v_name, code in VARIANTS.items():
            log(f"INICIO rep={rep} variante={v_name}")
            res = run_variant_rep(v_name, code, rep)
            log(f"FIM    rep={rep} variante={v_name} -> {res['classe']} em {res['time_s']:.2f}s (reader_blocked={res['reader_blocked']})")
            results.append(res)

    lines = []
    lines.append("=== TABELA EXPERIMENTO E2: LOOP DE EVENTOS COM STDIN ABERTO (n=5 cada) ===")
    lines.append(f"{'Variante':<20} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'Reader Blocked':<15} | {'Import OK':<10}")
    lines.append("-" * 75)
    for r in results:
        lines.append(
            f"{r['variant']:<20} | {r['rep']:<4} | {r['classe']:<8} | {r['time_s']:<9.2f} | "
            f"{str(r['reader_blocked']):<15} | {str(r['import_ok']):<10}"
        )
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    main()
