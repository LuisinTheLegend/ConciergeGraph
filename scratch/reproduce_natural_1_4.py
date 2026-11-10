"""
scratch/reproduce_natural_1_4.py — Tentativa de Reprodução Natural (Bloco 1, Item 1.4 - Rodada 4.4d)

Somente mede, sem alterar código de produto:
1. Experimento A (100 processos isolados no Windows):
   Cada processo cria um banco SQLite novo em diretório temporário, dispara 3 threads leitoras
   chamando ConnectionManager.get_read_connection() concorrentemente enquanto o worker inicia
   (ConnectionManager.start()) e executa um ConnectionManager.write(), com limite de 30 s por processo.
2. Experimento B (50 pares = 100 processos em dupla concorrente sobre o mesmo banco novo):
   Dois processos independentes iniciam ConnectionManager/SqliteStore simultaneamente sobre o
   mesmo arquivo de banco SQLite novo, com 3 threads leitoras por processo e 1 write por processo
   (simulando duas instâncias do servidor iniciando ao mesmo tempo), com limite de 30 s por processo.

Contabiliza hangs (timeouts > 30s), exceções não-tratadas e retries de partida observados no log.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON_EXE = os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

WORKER_SNIPPET_SINGLE = """
import logging, os, sys, threading, time
logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(levelname)s:%(name)s:%(message)s")
from storage.connection import ConnectionManager
from storage.schema import SchemaManager
import sqlite3

db_path = sys.argv[1]
cm = ConnectionManager(db_path)
barrier = threading.Barrier(4)
read_errors = []

def reader(idx):
    try:
        barrier.wait(timeout=5.0)
        for _ in range(5):
            conn = cm.get_read_connection()
            conn.execute("SELECT sqlite_version();").fetchone()
    except BaseException as exc:
        read_errors.append(repr(exc))

threads = [threading.Thread(target=reader, args=(i,), daemon=True) for i in range(3)]
for t in threads:
    t.start()

barrier.wait(timeout=5.0)
cm.start()

def do_write(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY, v TEXT);")
    conn.execute("INSERT INTO probe (v) VALUES ('ok');")
    return conn.execute("SELECT COUNT(*) FROM probe;").fetchone()[0]

cnt = cm.write(do_write)
for t in threads:
    t.join(timeout=5.0)
cm.close()
if read_errors:
    print("READ_ERRORS:" + ";".join(read_errors))
print(f"OK:{cnt}")
"""

WORKER_SNIPPET_DUAL = """
import logging, os, sys, threading, time
logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(levelname)s:%(name)s:%(message)s")
from storage.store import SqliteStore

db_path = sys.argv[1]
proc_id = sys.argv[2]
store = SqliteStore(db_path)
barrier = threading.Barrier(4)
read_errors = []

def reader(idx):
    try:
        barrier.wait(timeout=5.0)
        for _ in range(5):
            with store._conn_mgr.read() as conn:
                conn.execute("SELECT COUNT(*) FROM projects;").fetchone()
    except BaseException as exc:
        read_errors.append(repr(exc))

threads = [threading.Thread(target=reader, args=(i,), daemon=True) for i in range(3)]
for t in threads:
    t.start()

barrier.wait(timeout=5.0)
store.create_project(f"uuid-{proc_id}", f"folder-{proc_id}")
for t in threads:
    t.join(timeout=5.0)
store.close()
if read_errors:
    print("READ_ERRORS:" + ";".join(read_errors))
print(f"OK:{proc_id}")
"""


def run_experiment_a(n_procs: int = 100) -> dict:
    tmp_root = tempfile.mkdtemp(prefix="nat_repro_a_")
    hangs = 0
    exceptions = 0
    retries_procs = 0
    total_retry_lines = 0
    read_error_procs = 0
    details = []
    t0 = time.monotonic()

    try:
        # Executa em lotes de 10 processos paralelos para concluir rápido mantendo isolamento por banco
        batch_size = 10
        for batch_start in range(0, n_procs, batch_size):
            procs = []
            for idx in range(batch_start, min(batch_start + batch_size, n_procs)):
                db_path = os.path.join(tmp_root, f"db_{idx}.sqlite")
                p = subprocess.Popen(
                    [PYTHON_EXE, "-c", WORKER_SNIPPET_SINGLE, db_path],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
                procs.append((idx, p))

            for idx, p in procs:
                try:
                    out, err = p.communicate(timeout=30.0)
                    retry_cnt = err.count("SerializedWriteQueue startup attempt")
                    if retry_cnt > 0:
                        retries_procs += 1
                        total_retry_lines += retry_cnt
                        details.append(f"[ExpA proc #{idx}] {retry_cnt} retry(s): {err.strip()}")
                    if "READ_ERRORS:" in out:
                        read_error_procs += 1
                        details.append(f"[ExpA proc #{idx}] read_error: {out.strip()}")
                    if p.returncode != 0 or "OK:" not in out:
                        exceptions += 1
                        details.append(
                            f"[ExpA proc #{idx}] rc={p.returncode} out={out.strip()} err={err.strip()}"
                        )
                except subprocess.TimeoutExpired:
                    p.kill()
                    hangs += 1
                    details.append(f"[ExpA proc #{idx}] HANG (>30s)")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    return {
        "n_procs": n_procs,
        "elapsed_s": time.monotonic() - t0,
        "hangs": hangs,
        "exceptions": exceptions,
        "retries_procs": retries_procs,
        "total_retry_lines": total_retry_lines,
        "read_error_procs": read_error_procs,
        "details": details,
    }


def run_experiment_b(n_pairs: int = 50) -> dict:
    tmp_root = tempfile.mkdtemp(prefix="nat_repro_b_")
    hangs = 0
    exceptions = 0
    retries_procs = 0
    total_retry_lines = 0
    read_error_procs = 0
    details = []
    t0 = time.monotonic()

    try:
        batch_pairs = 5
        for batch_start in range(0, n_pairs, batch_pairs):
            active = []
            for pair_idx in range(batch_start, min(batch_start + batch_pairs, n_pairs)):
                db_path = os.path.join(tmp_root, f"shared_{pair_idx}.sqlite")
                p1 = subprocess.Popen(
                    [PYTHON_EXE, "-c", WORKER_SNIPPET_DUAL, db_path, f"{pair_idx}_A"],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
                p2 = subprocess.Popen(
                    [PYTHON_EXE, "-c", WORKER_SNIPPET_DUAL, db_path, f"{pair_idx}_B"],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
                active.append((f"pair{pair_idx}_A", p1))
                active.append((f"pair{pair_idx}_B", p2))

            for label, p in active:
                try:
                    out, err = p.communicate(timeout=30.0)
                    retry_cnt = err.count("SerializedWriteQueue startup attempt")
                    if retry_cnt > 0:
                        retries_procs += 1
                        total_retry_lines += retry_cnt
                        details.append(f"[ExpB {label}] {retry_cnt} retry(s): {err.strip()}")
                    if "READ_ERRORS:" in out:
                        read_error_procs += 1
                        details.append(f"[ExpB {label}] read_error: {out.strip()}")
                    if p.returncode != 0 or "OK:" not in out:
                        exceptions += 1
                        details.append(
                            f"[ExpB {label}] rc={p.returncode} out={out.strip()} err={err.strip()}"
                        )
                except subprocess.TimeoutExpired:
                    p.kill()
                    hangs += 1
                    details.append(f"[ExpB {label}] HANG (>30s)")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    return {
        "n_pairs": n_pairs,
        "n_procs": n_pairs * 2,
        "elapsed_s": time.monotonic() - t0,
        "hangs": hangs,
        "exceptions": exceptions,
        "retries_procs": retries_procs,
        "total_retry_lines": total_retry_lines,
        "read_error_procs": read_error_procs,
        "details": details,
    }


def main() -> None:
    print("Iniciando Experimento A (100 processos isolados: banco novo + 3 leitores + worker start + write)...")
    res_a = run_experiment_a(100)
    print("Iniciando Experimento B (50 pares = 100 processos: 2 instâncias abrindo mesmo banco novo ao mesmo tempo)...")
    res_b = run_experiment_b(50)

    report = [
        "=== TENTATIVA DE REPRODUÇÃO NATURAL (BLOCO 1, ITEM 1.4 — RODADA 4.4d) ===",
        f"Sistema Operacional: Windows ({sys.platform})",
        f"Python: {sys.version.splitlines()[0]}",
        "Limite por processo: 30.0s",
        "",
        "--------------------------------------------------------------------------------",
        "1. EXPERIMENTO A: 100 processos independentes (1 banco novo por processo,",
        "   3 threads leitoras via get_read_connection() + ConnectionManager.start() + 1 write)",
        "--------------------------------------------------------------------------------",
        f"- Total de processos executados: {res_a['n_procs']}",
        f"- Tempo total decorrido: {res_a['elapsed_s']:.2f}s",
        f"- Hangs (timeouts > 30s): {res_a['hangs']} / {res_a['n_procs']}",
        f"- Exceções não-tratadas (returncode != 0): {res_a['exceptions']} / {res_a['n_procs']}",
        f"- Processos com retries de partida do worker: {res_a['retries_procs']} / {res_a['n_procs']} (total de linhas de retry: {res_a['total_retry_lines']})",
        f"- Processos com erros nas threads leitoras: {res_a['read_error_procs']} / {res_a['n_procs']}",
        "",
        "Detalhes do Experimento A:",
        *(res_a["details"] if res_a["details"] else ["  (Nenhuma falha, hang ou retry registrado nos 100 processos)"]),
        "",
        "--------------------------------------------------------------------------------",
        "2. EXPERIMENTO B: 50 pares (100 processos) — 2 processos iniciando o MESMO banco",
        "   novo simultaneamente (duas instâncias de SqliteStore + 3 threads leitoras + create_project)",
        "--------------------------------------------------------------------------------",
        f"- Total de pares (bancos compartilhados): {res_b['n_pairs']} ({res_b['n_procs']} processos)",
        f"- Tempo total decorrido: {res_b['elapsed_s']:.2f}s",
        f"- Hangs (timeouts > 30s): {res_b['hangs']} / {res_b['n_procs']}",
        f"- Exceções de processo (returncode != 0): {res_b['exceptions']} / {res_b['n_procs']}",
        f"- Processos com retries de partida do worker: {res_b['retries_procs']} / {res_b['n_procs']} (total de linhas de retry: {res_b['total_retry_lines']})",
        f"- Processos com erros nas threads leitoras: {res_b['read_error_procs']} / {res_b['n_procs']}",
        "",
        "Detalhes do Experimento B:",
        *(res_b["details"] if res_b["details"] else ["  (Nenhuma falha, hang ou retry registrado nos 100 processos)"]),
        "",
        "Nota Metodológica: Números reportados de forma estritamente observacional, sem concluir causa.",
    ]

    out_text = "\n".join(report) + "\n"
    out_path = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d", "natural_reproduction_100_procs.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text)
    print(out_text)


if __name__ == "__main__":
    main()

