"""
run_e1_isolation.py - Experimento E1 da Rodada 4.2e-2:
Isolar a causa SEM MCP e SEM asyncio mantendo o pipe stdin ATIVAMENTE ABERTO.

Parent: Popen(stdin=PIPE, stdout=PIPE, stderr=PIPE)
        NUNCA chama communicate(); NUNCA fecha p.stdin antes do fim.
Child:  Thread daemon fazendo sys.stdin.buffer.readline();
        A main espera 2.0s, verifica se a thread leitora está viva.
        Se viva, escreve 'reader_blocked=True\n' no stdout e executa o import sob teste.
        Se concluído com sucesso, escreve 'import_ok=True\n'.

Casos:
  (i)   scipy_special_main   : import scipy.special na thread principal
  (ii)  scipy_special_thread : import scipy.special numa thread secundária
  (iii) numpy_only           : import numpy
  (iv)  scipy_linalg         : import scipy.linalg
  (v)   sklearn_array_api    : import sklearn.utils._array_api
  (vi)  torch_only           : import torch
  (vii) sentence_transformers: import sentence_transformers
  (viii)control_stdin_closed : caso (i) mas com o stdin fechado logo após o spawn (EOF esperado)

n=5 repetições por caso, timeout duro de 120s por repetição.
Gera arquivos em scratch/evidencia_4_2e/e1_isolation/ e tabela_e1.txt.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e1_isolation"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e1.txt"

# Código do processo filho para casos com stdin aberto
CHILD_OPEN_TEMPLATE = r"""
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

# Executa o import sob teste
{import_statement}

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

# Código do processo filho para caso (ii) - import em thread secundária
CHILD_THREAD_TEMPLATE = r"""
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

def do_import():
    import scipy.special

t_imp = threading.Thread(target=do_import, name="importer-thread")
t_imp.start()
t_imp.join()

sys.stdout.write("import_ok=True\n")
sys.stdout.flush()
sys.exit(0)
"""

# Código para o controle (viii) - stdin fechado logo após o spawn
CHILD_CLOSED_TEMPLATE = r"""
import sys, threading, time

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

# Com stdin fechado pelo parent logo no spawn, a thread deve ter retornado EOF imediatamente
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

CASES = {
    "i_scipy_special_main": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import scipy.special")),
    "ii_scipy_special_thread": ("open", CHILD_THREAD_TEMPLATE),
    "iii_numpy_only": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import numpy")),
    "iv_scipy_linalg": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import scipy.linalg")),
    "v_sklearn_array_api": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import sklearn.utils._array_api")),
    "vi_torch_only": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import torch")),
    "vii_sentence_transformers": ("open", CHILD_OPEN_TEMPLATE.format(import_statement="import sentence_transformers")),
    "viii_control_stdin_closed": ("close_immediately", CHILD_CLOSED_TEMPLATE),
}

TIMEOUT = 120.0
REPS = 5

def run_case_rep(case_name: str, mode: str, code: str, rep: int) -> dict:
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
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    if mode == "close_immediately":
        # Fecha stdin imediatamente após o spawn para o caso de controle
        try:
            p.stdin.close()
        except Exception:
            pass

    # Monitora o processo com timeout duro mantendo o pipe aberto
    timed_out = False
    stdout_lines = []
    stderr_content = ""

    while True:
        elapsed = time.perf_counter() - t0
        if elapsed > TIMEOUT:
            timed_out = True
            try:
                p.kill()
            except Exception:
                pass
            break

        ret = p.poll()
        if ret is not None:
            break
        time.sleep(0.1)

    dt = time.perf_counter() - t0

    # Coleta saídas se disponíveis
    try:
        if not timed_out:
            # Já terminou, lê stdout restante
            out_rest, err_rest = p.communicate(timeout=5)
            stdout_content = out_rest
            stderr_content = err_rest
        else:
            try:
                p.kill()
                out_rest, err_rest = p.communicate(timeout=5)
                stdout_content = out_rest
                stderr_content = err_rest
            except Exception:
                stdout_content = ""
                stderr_content = ""
    except Exception:
        stdout_content = ""
        stderr_content = ""

    out_file.write_text(stdout_content, encoding="utf-8")
    err_file.write_text(stderr_content, encoding="utf-8")

    reader_blocked = "reader_blocked=True" in stdout_content
    import_ok = "import_ok=True" in stdout_content

    if timed_out:
        classe = "TRAVOU"
    elif p.returncode == 0 and import_ok:
        classe = "OK"
    else:
        classe = f"ERRO_RC_{p.returncode}"

    res = {
        "case": case_name,
        "rep": rep,
        "mode": mode,
        "classe": classe,
        "time_s": round(dt, 2),
        "reader_blocked": reader_blocked,
        "import_ok": import_ok,
        "returncode": p.returncode,
    }
    res_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res

def main():
    log = open(OUTDIR / "progress.log", "a", encoding="utf-8")
    def say(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    say("INICIANDO EXPERIMENTO E1 — ISOLAMENTO SEM MCP E SEM ASYNCIO")
    results = []

    for rep in range(1, REPS + 1):
        for case_name, (mode, code) in CASES.items():
            say(f"INICIO rep={rep} caso={case_name} (modo={mode})")
            r = run_case_rep(case_name, mode, code, rep)
            results.append(r)
            say(f"FIM    rep={rep} caso={case_name} -> {r['classe']} em {r['time_s']:.2f}s (reader_blocked={r['reader_blocked']})")

    # Gera Tabela
    lines = []
    lines.append("=" * 95)
    lines.append("TABELA EXPERIMENTO E1 — ISOLAMENTO SEM MCP E SEM ASYNCIO (PIPE STDIN ABERTO)")
    lines.append("=" * 95)
    lines.append(f"{'Caso':<28} | {'Rep':<4} | {'Status':<8} | {'Tempo (s)':<10} | {'Reader Blocked':<15} | Detalhes")
    lines.append("-" * 95)
    results.sort(key=lambda x: (x["case"], x["rep"]))
    for r in results:
        lines.append(f"{r['case']:<28} | {r['rep']:<4} | {r['classe']:<8} | {r['time_s']:<10.2f} | {str(r['reader_blocked']):<15} | rc={r['returncode']}")
    lines.append("=" * 95)

    lines.append("\nRESUMO ESTATÍSTICO DO EXPERIMENTO E1:")
    lines.append("-" * 65)
    for c in CASES.keys():
        subset = [r for r in results if r["case"] == c]
        oks = sum(1 for r in subset if r["classe"] == "OK")
        travou = sum(1 for r in subset if r["classe"] == "TRAVOU")
        erros = sum(1 for r in subset if r["classe"] not in ("OK", "TRAVOU"))
        lines.append(f"Caso {c:<26} | OK: {oks}/5 | TRAVOU: {travou}/5 | ERRO: {erros}/5")
    lines.append("=" * 95)

    table_txt = "\n".join(lines) + "\n"
    TABLE_OUT.write_text(table_txt, encoding="utf-8")
    print("\n" + table_txt)

if __name__ == "__main__":
    main()
