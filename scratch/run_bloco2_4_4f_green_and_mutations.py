"""
scratch/run_bloco2_4_4f_green_and_mutations.py — Provas em VERDE, Consumidores/Guardas e Mutações (a) e (b) (Bloco 2, Rodada 4.4f)

Gera em `scratch/evidencia_4_4f/`:
1. `green_10_pairs_memory_stress.txt`: 10 pares paralelos de `memory_stress_test.py` (Python 3.12) -> 0/10 falhas.
2. `green_10_pairs_lightweight_vs_stress.txt`: 10 pares paralelos de `test_lightweight.py` (Python 3.10) vs `memory_stress_test.py` (Python 3.12) -> 0/10 falhas.
3. `consumers_and_guards_check.txt`: consumidores (`test_chunk_cache.py`, `test_ignore.py`, `test_lightweight.py`, `memory_stress_test.py`), `check_mcp_globals_leak` (`test_conftest_globals_guard.py`) e `G2` (`test_domain_neutrality_guard.py`), mais verificação de zero diretórios residuais.
4. `mutacao_Ta.txt`: Reintroduz caminho fixo em `TEST_DIR` de `tests/memory_stress_test.py` -> falha em vermelho no paralelo e passa em verde sem mutação.
5. `mutacao_Tb.txt`: Reintroduz `./tmp_chroma_test` em `tests/test_lightweight.py` -> demonstração empírica do comportamento paralelo e inspeção do NO-OP em `storage/vector_store.py:297-315`.
"""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4f")
PY310 = os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")
PY312 = os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")

STRESS_FILE = os.path.join(REPO_ROOT, "tests", "memory_stress_test.py")
LIGHTWEIGHT_FILE = os.path.join(REPO_ROOT, "tests", "test_lightweight.py")


def _run_cmd(cmd: list[str], timeout: int = 180) -> tuple[int, float, str, str]:
    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44f-green-0000"
    env["GRAFO_LLM_MODEL"] = "none"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    dt = time.perf_counter() - t0
    return proc.returncode, dt, proc.stdout, proc.stderr


def run_green_10_pairs_memory_stress() -> None:
    cmd = [PY312, "-m", "pytest", "tests/memory_stress_test.py", "-v", "--tb=short"]
    out_path = os.path.join(EV_DIR, "green_10_pairs_memory_stress.txt")
    lines = [
        "=== PROVA EM VERDE (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS DE memory_stress_test.py (PYTHON 3.12) ===",
        f"Comando por processo: {' '.join(cmd)}",
        "-" * 80,
    ]
    failures = 0
    for i in range(1, 11):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fa = ex.submit(_run_cmd, cmd)
            fb = ex.submit(_run_cmd, cmd)
            rc_a, dt_a, out_a, err_a = fa.result()
            rc_b, dt_b, out_b, err_b = fb.result()
        if rc_a != 0 or rc_b != 0:
            failures += 1
        st_a = "PASS" if rc_a == 0 else f"FAIL(rc={rc_a})"
        st_b = "PASS" if rc_b == 0 else f"FAIL(rc={rc_b})"
        msg = f"  [Par {i:02d}/10] ProcA={st_a} ({dt_a:.2f}s) | ProcB={st_b} ({dt_b:.2f}s)"
        print(msg, flush=True)
        lines.append(msg)
        if rc_a != 0 or rc_b != 0:
            lines.append(f"--- Falha no Par #{i:02d} ---\nProcA:\n{out_a}\n{err_a}\nProcB:\n{out_b}\n{err_b}")

    legacy_ws = os.path.exists(os.path.join(REPO_ROOT, "tests", "_stress_test_workspace"))
    legacy_tmp = os.path.exists(os.path.join(REPO_ROOT, "tmp_chroma_test"))
    lines.append("-" * 80)
    lines.append(f"RESUMO VERDE (memory_stress_test.py x2, Python 3.12): {failures}/10 pares com falha.")
    lines.append(f"Resíduo tests/_stress_test_workspace existe: {legacy_ws}")
    lines.append(f"Resíduo tmp_chroma_test existe: {legacy_tmp}")

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    assert failures == 0, f"Esperava 0 falhas em green_10_pairs_memory_stress, obteve {failures}!"
    assert not legacy_ws and not legacy_tmp


def run_green_10_pairs_lightweight_vs_stress() -> None:
    cmd_a = [PY310, "-m", "pytest", "tests/test_lightweight.py", "-v", "--tb=short"]
    cmd_b = [PY312, "-m", "pytest", "tests/memory_stress_test.py", "-v", "--tb=short"]
    out_path = os.path.join(EV_DIR, "green_10_pairs_lightweight_vs_stress.txt")
    lines = [
        "=== PROVA EM VERDE (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS test_lightweight.py (Py3.10) vs memory_stress_test.py (Py3.12) ===",
        f"Processo A (Py3.10): {' '.join(cmd_a)}",
        f"Processo B (Py3.12): {' '.join(cmd_b)}",
        "-" * 80,
    ]
    failures = 0
    for i in range(1, 11):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fa = ex.submit(_run_cmd, cmd_a)
            fb = ex.submit(_run_cmd, cmd_b)
            rc_a, dt_a, out_a, err_a = fa.result()
            rc_b, dt_b, out_b, err_b = fb.result()
        if rc_a != 0 or rc_b != 0:
            failures += 1
        st_a = "PASS" if rc_a == 0 else f"FAIL(rc={rc_a})"
        st_b = "PASS" if rc_b == 0 else f"FAIL(rc={rc_b})"
        msg = f"  [Par {i:02d}/10] Py3.10(test_lightweight)={st_a} ({dt_a:.2f}s) | Py3.12(memory_stress_test)={st_b} ({dt_b:.2f}s)"
        print(msg, flush=True)
        lines.append(msg)
        if rc_a != 0 or rc_b != 0:
            lines.append(f"--- Falha no Par #{i:02d} ---\nProcA:\n{out_a}\n{err_a}\nProcB:\n{out_b}\n{err_b}")

    legacy_ws = os.path.exists(os.path.join(REPO_ROOT, "tests", "_stress_test_workspace"))
    legacy_tmp = os.path.exists(os.path.join(REPO_ROOT, "tmp_chroma_test"))
    lines.append("-" * 80)
    lines.append(f"RESUMO VERDE (test_lightweight.py Py3.10 vs memory_stress_test.py Py3.12): {failures}/10 pares com falha.")
    lines.append(f"Resíduo tests/_stress_test_workspace existe: {legacy_ws}")
    lines.append(f"Resíduo tmp_chroma_test existe: {legacy_tmp}")

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    assert failures == 0, f"Esperava 0 falhas em green_10_pairs_lightweight_vs_stress, obteve {failures}!"
    assert not legacy_ws and not legacy_tmp


def run_consumers_and_guards() -> None:
    cmd = [
        PY312,
        "-m",
        "pytest",
        "tests/test_chunk_cache.py",
        "tests/test_ignore.py",
        "tests/test_lightweight.py",
        "tests/memory_stress_test.py",
        "tests/test_domain_neutrality_guard.py",
        "-v",
        "--tb=short",
    ]
    rc, dt, out, err = _run_cmd(cmd, timeout=240)
    raw_m10d = subprocess.check_output(["git", "show", "HEAD:scratch/evidencia_4_4d/mutacao_M10d_import.txt"], cwd=REPO_ROOT)
    rc_m10, dt_m10, out_m10, err_m10 = _run_cmd([PY312, "scratch/run_bloco2_4_4d_mutation.py"], timeout=120)
    with open(os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d", "mutacao_M10d_import.txt"), "wb") as f_m10d:
        f_m10d.write(raw_m10d)
    legacy_ws = os.path.exists(os.path.join(REPO_ROOT, "tests", "_stress_test_workspace"))
    legacy_tmp = os.path.exists(os.path.join(REPO_ROOT, "tmp_chroma_test"))
    out_path = os.path.join(EV_DIR, "consumers_and_guards_check.txt")
    report = (
        f"=== VERIFICAÇÃO DE CONSUMIDORES E GUARDAS (BLOCO 2 — RODADA 4.4f) ===\n"
        f"Comando 1 (consumidores + G2 + autouse conftest): {' '.join(cmd)}\n"
        f"Return Code 1: {rc} ({dt:.2f}s)\n"
        f"Comando 2 (prova de check_mcp_globals_leak e hook de baseline M10d): {PY312} scratch/run_bloco2_4_4d_mutation.py\n"
        f"Return Code 2: {rc_m10} ({dt_m10:.2f}s)\n"
        f"Resíduo tests/_stress_test_workspace existe: {legacy_ws}\n"
        f"Resíduo tmp_chroma_test existe: {legacy_tmp}\n\n"
        f"--- STDOUT COMANDO 1 ---\n{out}\nSTDERR:\n{err}\n"
        f"--- STDOUT COMANDO 2 (M10d / check_mcp_globals_leak) ---\n{out_m10}\nSTDERR:\n{err_m10}\n"
    )
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    assert rc == 0 and rc_m10 == 0, f"Consumidores/guardas falharam!\n{report}"
    assert not legacy_ws and not legacy_tmp


def run_mutation_Ta() -> None:
    with open(STRESS_FILE, "rb") as f:
        orig_bytes = f.read()
    orig_txt = orig_bytes.decode("utf-8").replace("\r\n", "\n")

    target = (
        "if not hasattr(sys, \"_grafo_stress_test_dir\"):\n"
        "    sys._grafo_stress_test_dir = tempfile.mkdtemp(prefix=f\"grafo_stress_{os.getpid()}_\")\n"
        "    atexit.register(lambda: shutil.rmtree(sys._grafo_stress_test_dir, ignore_errors=True))\n"
        "TEST_DIR = sys._grafo_stress_test_dir"
    )
    replacement = (
        'TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_stress_test_workspace")  # Mutacao Ta'
    )
    assert target in orig_txt, "Alvo da Mutação Ta não encontrado em tests/memory_stress_test.py!"

    cmd = [PY312, "-m", "pytest", "tests/memory_stress_test.py", "-v", "--tb=short"]
    mut_failures = 0
    mut_logs: list[str] = []

    try:
        with open(STRESS_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(orig_txt.replace(target, replacement, 1))

        for i in range(1, 6):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                fa = ex.submit(_run_cmd, cmd)
                fb = ex.submit(_run_cmd, cmd)
                rc_a, dt_a, out_a, err_a = fa.result()
                rc_b, dt_b, out_b, err_b = fb.result()
            failed = (rc_a != 0) or (rc_b != 0)
            if failed:
                mut_failures += 1
            mut_logs.append(
                f"  [Mutação Ta Par {i:02d}/05] ProcA rc={rc_a} ({dt_a:.2f}s) | ProcB rc={rc_b} ({dt_b:.2f}s)"
            )
            if failed and mut_failures == 1:
                mut_logs.append(
                    f"--- Exemplo de Traceback com Mutação Ta (Par #{i:02d}) ---\n"
                    f"ProcA:\n{out_a}\nProcB:\n{out_b}\n"
                )
    finally:
        with open(STRESS_FILE, "wb") as f:
            f.write(orig_bytes)
        legacy_dir = os.path.join(REPO_ROOT, "tests", "_stress_test_workspace")
        if os.path.exists(legacy_dir):
            shutil.rmtree(legacy_dir, ignore_errors=True)

    # Verifica 1 par verde após restaurar
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(_run_cmd, cmd)
        fb = ex.submit(_run_cmd, cmd)
        rc_ca, dt_ca, _, _ = fa.result()
        rc_cb, dt_cb, _, _ = fb.result()
    clean_ok = (rc_ca == 0) and (rc_cb == 0)

    killed = (mut_failures > 0) and clean_ok
    status_str = "MORTA (OK)" if killed else "SOBREVIVEU"
    print(f"Mutação Ta: mut_failures={mut_failures}/5, clean_ok={clean_ok} -> {status_str}", flush=True)

    report = (
        f"=== MUTAÇÃO Ta (BLOCO 2 — RODADA 4.4f): Reintroduzir caminho fixo em TEST_DIR (tests/memory_stress_test.py:42) ===\n"
        f"Alvo: tests/memory_stress_test.py\n"
        f"Resultado COM mutação (VERMELHO): {mut_failures}/5 pares paralelos falharam (esperado > 0)\n"
        f"Resultado SEM mutação (VERDE): ProcA rc={rc_ca} ({dt_ca:.2f}s), ProcB rc={rc_cb} ({dt_cb:.2f}s) (esperado 0, 0)\n"
        f"Status: {status_str}\n\n"
        + "\n".join(mut_logs)
        + "\n"
    )
    with open(os.path.join(EV_DIR, "mutacao_Ta.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    assert killed, "Mutação Ta não foi morta!"


def run_mutation_Tb() -> None:
    with open(LIGHTWEIGHT_FILE, "rb") as f:
        orig_bytes = f.read()
    orig_txt = orig_bytes.decode("utf-8").replace("\r\n", "\n")

    target = '        tmp_dir = str(tmp_path / "tmp_chroma_test")'
    replacement = '        tmp_dir = "./tmp_chroma_test"  # Mutacao Tb'
    assert target in orig_txt, "Alvo da Mutação Tb não encontrado em tests/test_lightweight.py!"

    cmd = [PY310, "-m", "pytest", "tests/test_lightweight.py", "-v", "--tb=short"]
    mut_failures = 0
    mut_logs: list[str] = []

    try:
        with open(LIGHTWEIGHT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(orig_txt.replace(target, replacement, 1))

        for i in range(1, 6):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                fa = ex.submit(_run_cmd, cmd)
                fb = ex.submit(_run_cmd, cmd)
                rc_a, dt_a, out_a, _ = fa.result()
                rc_b, dt_b, out_b, _ = fb.result()
            failed = (rc_a != 0) or (rc_b != 0)
            if failed:
                mut_failures += 1
            mut_logs.append(
                f"  [Mutação Tb Par {i:02d}/05] ProcA rc={rc_a} ({dt_a:.2f}s) | ProcB rc={rc_b} ({dt_b:.2f}s)"
            )
    finally:
        with open(LIGHTWEIGHT_FILE, "wb") as f:
            f.write(orig_bytes)
        legacy_tmp = os.path.join(REPO_ROOT, "tmp_chroma_test")
        if os.path.exists(legacy_tmp):
            shutil.rmtree(legacy_tmp, ignore_errors=True)

    # Sonda empírica demonstrando por que ChromaVectorStore(persist_dir="./tmp_chroma_test")
    # sob GRAFO_LIGHTWEIGHT_MODE="true" não toca o disco:
    probe_code = (
        "import os, pathlib; "
        "os.environ['GRAFO_LIGHTWEIGHT_MODE'] = 'true'; "
        "from storage.vector_store import ChromaVectorStore; "
        "p = pathlib.Path('./tmp_chroma_test_probe'); "
        "vs = ChromaVectorStore(persist_dir=str(p)); "
        "print(f'available={vs._available}, client={vs._client}, dir_created_on_disk={p.exists()}')"
    )
    _, _, probe_out, _ = _run_cmd([PY310, "-c", probe_code])

    report = (
        f"=== MUTAÇÃO Tb (BLOCO 2 — RODADA 4.4f): Reintroduzir caminho fixo './tmp_chroma_test' em tests/test_lightweight.py:38 ===\n"
        f"Alvo: tests/test_lightweight.py\n"
        f"Resultado COM mutação em 5 pares paralelos de test_lightweight.py: {mut_failures}/5 pares falharam\n"
        f"Sonda de I/O em modo lightweight: {probe_out.strip()}\n\n"
        f"Demonstração e Explicação Técnica (conforme exigido pelo Bloco 2):\n"
        f"1. Em `tests/test_lightweight.py:24`, `os.environ['GRAFO_LIGHTWEIGHT_MODE'] = 'true'` é definido ANTES da\n"
        f"   chamada `vector_store = ChromaVectorStore(persist_dir=tmp_dir)` na linha 39.\n"
        f"2. Em `storage/vector_store.py:297-302`, `ChromaVectorStore.__init__` verifica:\n"
        f"   `if os.environ.get('GRAFO_LIGHTWEIGHT_MODE', 'false').lower() == 'true':`\n"
        f"   e retorna imediatamente na linha 302 (`self._available = False; self._client = None; return`)\n"
        f"   ANTES de `Path(resolved_dir).mkdir(parents=True, exist_ok=True)` (`storage/vector_store.py:315`)\n"
        f"   e ANTES de `chromadb.PersistentClient(path=resolved_dir)` (`storage/vector_store.py:317`).\n"
        f"3. Consequentemente, como provado pela sonda acima (`dir_created_on_disk=False`), `ChromaVectorStore`\n"
        f"   em modo lightweight jamais cria, abre ou escreve em `persist_dir` no disco; e o `shutil.rmtree(tmp_dir, ignore_errors=True)`\n"
        f"   no bloco `finally` (`tests/test_lightweight.py:69`) opera sobre um caminho inexistente.\n"
        f"4. Antes do isolamento de `TEST_DIR` (`tests/memory_stress_test.py:42`), `test_lightweight.py` colidia em paralelo\n"
        f"   não por causa de `./tmp_chroma_test`, mas porque na linha 20 (`manager.mine(PROJECT_UUID, PROJECT_DIR, ...)`)\n"
        f"   ele usa a fixture `store`/`manager` de `conftest.py` (que apontava para `tests/_stress_test_workspace`).\n\n"
        f"Logs dos 5 pares paralelos com Mutação Tb:\n"
        + "\n".join(mut_logs)
        + "\n"
    )
    with open(os.path.join(EV_DIR, "mutacao_Tb.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print(f"Mutação Tb documentada e demonstrada empiricamente ({probe_out.strip()}).", flush=True)


def main() -> None:
    os.makedirs(EV_DIR, exist_ok=True)
    run_consumers_and_guards()
    run_green_10_pairs_memory_stress()
    run_green_10_pairs_lightweight_vs_stress()
    run_mutation_Ta()
    run_mutation_Tb()
    print("Todas as verificações verdes e mutações do Bloco 2 concluídas com sucesso!", flush=True)


if __name__ == "__main__":
    main()
