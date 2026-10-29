# run_e9_preimport_matrix.py
# Experimento E9 da Rodada 4.2e-3:
# Conjuntos minimos de pre-import + caminho tardio completo
#
# Procedimento:
#   1. Filho pre-importa o conjunto S ANTES de iniciar a thread leitora;
#   2. Inicia thread leitora (sys.stdin.buffer.readline()) com stdin=PIPE do pai aberto;
#   3. Confirma reader_blocked apos 2.0s;
#   4. Executa caminho tardio:
#      - import sentence_transformers (se nao foi pre-importado em S)
#      - model = SentenceTransformer("all-MiniLM-L6-v2")
#      - model.encode(...)
#   5. Mede tempos de cada fase: t_pre, t_import, t_load_model, t_encode, total_s.
#   6. Timeout: 180s por execucao.
#   7. Repeticoes: n=5 por conjunto.

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "e9_preimport"
OUTDIR.mkdir(parents=True, exist_ok=True)
TABLE_OUT = HERE / "tabela_e9.txt"

SETS = {
    "S0_vazio": [],
    "S1_numpy": ["import numpy"],
    "S2_numpy_scipy": ["import numpy", "import scipy.special"],
    "S3_numpy_scipy_sklearn": [
        "import numpy",
        "import scipy.special",
        "import sklearn.utils._array_api",
    ],
    "S4_torch": ["import torch"],
    "S5_numpy_scipy_torch": [
        "import numpy",
        "import scipy.special",
        "import torch",
    ],
    "S6_sentence_transformers": ["import sentence_transformers"],
}

CHILD_CODE_TEMPLATE = r"""
import sys, time, threading, json

# FASE 0: Pre-import de S antes de iniciar leitora de stdin
t_pre0 = time.perf_counter()
{pre_imports}
t_pre_duration = time.perf_counter() - t_pre0

# FASE 1: Iniciar thread leitora daemon em sys.stdin.buffer.readline()
def stdin_reader():
    try:
        sys.stdin.buffer.readline()
    except Exception:
        pass

t = threading.Thread(target=stdin_reader, daemon=True, name="stdin-reader")
t.start()
time.sleep(2.0)

reader_blocked = t.is_alive()
sys.stdout.write(f"reader_blocked={reader_blocked}\n")
sys.stdout.flush()

if not reader_blocked:
    sys.stderr.write("ERRO: thread leitora nao bloqueou!\n")
    sys.exit(3)

# FASE 3: Import tardio de sentence_transformers (se ainda nao foi)
t_imp0 = time.perf_counter()
{late_import}
t_import = time.perf_counter() - t_imp0

# FASE 4: Instanciar SentenceTransformer
t_mod0 = time.perf_counter()
model = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
t_load_model = time.perf_counter() - t_mod0

# FASE 5: Fazer um encode
t_enc0 = time.perf_counter()
emb = model.encode("teste de representacao semantica com sentence-transformers")
t_encode = time.perf_counter() - t_enc0

total_s = t_import + t_load_model + t_encode

out_data = {
    "t_pre_duration": round(t_pre_duration, 3),
    "t_import": round(t_import, 3),
    "t_load_model": round(t_load_model, 3),
    "t_encode": round(t_encode, 3),
    "total_s": round(total_s, 3),
    "dim": len(emb) if hasattr(emb, '__len__') else 0
}
sys.stdout.write("RESULT_JSON=" + json.dumps(out_data) + "\n")
sys.stdout.flush()
os._exit(0)
"""

REPS = 5
TIMEOUT = 180.0

def log(msg: str):
    timestamp = time.strftime("[%H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line, flush=True)
    with (OUTDIR / "progress.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_e9_case(set_name: str, rep: int) -> dict:
    case_dir = OUTDIR / f"{set_name}__rep{rep}"
    case_dir.mkdir(parents=True, exist_ok=True)
    out_file = case_dir / "stdout.txt"
    err_file = case_dir / "stderr.txt"
    res_file = case_dir / "result.json"

    if res_file.exists():
        try:
            cached = json.loads(res_file.read_text(encoding="utf-8"))
            if cached.get("classe") in ("OK", "TRAVOU"):
                return cached
        except Exception:
            pass

    pre_imports_list = SETS[set_name]
    pre_imports_str = "\n".join(pre_imports_list) if pre_imports_list else "pass"
    if set_name == "S6_sentence_transformers":
        late_import_str = "pass"
    else:
        late_import_str = "import sentence_transformers"

    code = (
        CHILD_CODE_TEMPLATE.replace("{pre_imports}", pre_imports_str)
        .replace("{late_import}", late_import_str)
    )

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

    def stdout_reader():
        try:
            for line in iter(p.stdout.readline, ""):
                stdout_lines.append(line)
        except Exception:
            pass

    t_read = threading.Thread(target=stdout_reader, daemon=True)
    t_read.start()

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

    full_stdout = "".join(stdout_lines)
    if not timed_out:
        if "RESULT_JSON=" in full_stdout:
            classe = "OK"
        elif p.returncode == 0:
            classe = "OK"
        else:
            classe = "ERRO"
    reader_blocked = "reader_blocked=True" in full_stdout

    result_data = {}
    for line in full_stdout.splitlines():
        if line.startswith("RESULT_JSON="):
            try:
                result_data = json.loads(line[len("RESULT_JSON="):])
            except Exception:
                pass

    out_file.write_text(full_stdout, encoding="utf-8")
    err_file.write_text(stderr_content, encoding="utf-8")

    result = {
        "set": set_name,
        "rep": rep,
        "classe": classe,
        "time_s": round(duration, 2),
        "reader_blocked": reader_blocked,
        "t_pre": result_data.get("t_pre_duration"),
        "t_import": result_data.get("t_import"),
        "t_load_model": result_data.get("t_load_model"),
        "t_encode": result_data.get("t_encode"),
        "total_s": result_data.get("total_s"),
        "returncode": p.returncode,
    }
    res_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def save_table(results: list[dict]):
    lines = []
    lines.append("=== TABELA EXPERIMENTO E9: CONJUNTOS DE PRE-IMPORT + CAMINHO TARDIO (n=5 cada) ===")
    lines.append(
        f"{'Conjunto':<26} | {'Rep':<4} | {'Classe':<8} | {'Tempo(s)':<9} | {'t_pre':<8} | {'t_import':<9} | {'t_load':<8} | {'t_enc':<8} | {'Blocked'}"
    )
    lines.append("-" * 105)
    for r in results:
        t_pre_s = f"{r['t_pre']:.2f}" if r['t_pre'] is not None else "-"
        t_imp_s = f"{r['t_import']:.2f}" if r['t_import'] is not None else "-"
        t_load_s = f"{r['t_load_model']:.2f}" if r['t_load_model'] is not None else "-"
        t_enc_s = f"{r['t_encode']:.2f}" if r['t_encode'] is not None else "-"
        lines.append(
            f"{r['set']:<26} | {r['rep']:<4} | {r['classe']:<8} | {r['time_s']:<9.2f} | "
            f"{t_pre_s:<8} | {t_imp_s:<9} | {t_load_s:<8} | {t_enc_s:<8} | {str(r['reader_blocked'])}"
        )
    lines.append("-" * 105)
    TABLE_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    log("INICIANDO EXPERIMENTO E9 — CONJUNTOS MINIMOS DE PRE-IMPORT (n=5 cada)")
    results = []

    set_order = [
        "S6_sentence_transformers",
        "S5_numpy_scipy_torch",
        "S4_torch",
        "S3_numpy_scipy_sklearn",
        "S2_numpy_scipy",
        "S1_numpy",
        "S0_vazio",
    ]

    for set_name in set_order:
        for rep in range(1, REPS + 1):
            log(f"INICIO rep={rep} set={set_name}")
            res = run_e9_case(set_name, rep)
            timing_info = (
                f"total={res['total_s']}s (imp={res['t_import']}s, mod={res['t_load_model']}s, enc={res['t_encode']}s)"
                if res['classe'] == "OK"
                else f"tempo={res['time_s']}s"
            )
            log(f"FIM    rep={rep} set={set_name} -> {res['classe']} ({timing_info})")
            results.append(res)
            save_table(results)

    save_table(results)
    log(f"Tabela gerada com sucesso em: {TABLE_OUT}")

if __name__ == "__main__":
    main()
