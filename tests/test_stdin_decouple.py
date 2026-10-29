# tests/test_stdin_decouple.py
"""
Rodada 4.2f: Testes de unidade e integracao para decouple_stdin_from_fd0().
Cobre requisitos D1, D2, D3, D4 e D5.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

def read_line_with_timeout(pipe, timeout: float = 15.0) -> str:
    """Le uma linha do pipe com timeout rigido para evitar travamento indefinido."""
    res = []
    def _read():
        try:
            res.append(pipe.readline())
        except Exception as exc:
            res.append(exc)

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"Timeout de {timeout}s aguardando linha do pipe")
    if not res:
        return ""
    val = res[0]
    if isinstance(val, Exception):
        raise val
    return val.strip()

# Codigo do processo filho para o teste D1
CHILD_D1_SCRIPT = r"""
import sys, time, threading

# Assegura que o REPO_ROOT esta no sys.path
sys.path.insert(0, r"{repo_root}")
import main

# Chama a funcao sob teste
success = main.decouple_stdin_from_fd0()
if not success:
    print(f"FAIL_DECOUPLE: success={success}", flush=True)
    sys.exit(1)

received = []
def reader_thread():
    try:
        line = sys.stdin.buffer.readline()
        received.append(line)
    except Exception as e:
        received.append(str(e).encode())

t = threading.Thread(target=reader_thread, daemon=True)
t.start()

time.sleep(2.0)
if not t.is_alive():
    print("FAIL_READER_NOT_BLOCKED", flush=True)
    sys.exit(2)

print("READER_BLOCKED_OK", flush=True)

# Importacao critica
import numpy as np
import scipy.special

print("IMPORT_NUMPY_OK", flush=True)

# Aguarda recepcao do ping enviado pelo pai
t0 = time.time()
while time.time() - t0 < 10.0:
    if received:
        break
    time.sleep(0.05)

if received and received[0].strip() == b"ping":
    print("PING_RECEIVED_OK", flush=True)
    sys.exit(0)
else:
    print(f"FAIL_PING: {received}", flush=True)
    sys.exit(3)
"""

def test_d1_subprocess_decouple_windows():
    """D1: Subprocesso real no Windows desacopla fd 0 e leitor continua funcional."""
    if sys.platform != "win32":
        pytest.skip("D1 e exclusivo do ambiente Windows (verificacao de deadlock em fd 0 / CRT)")

    code = CHILD_D1_SCRIPT.replace("{repo_root}", str(REPO_ROOT))
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["GRAFO_STDIN_DECOUPLE"] = "1"

    p = subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )

    try:
        # Espera o filho confirmar que o leitor esta bloqueado e numpy importado
        line1 = read_line_with_timeout(p.stdout, timeout=15.0)
        assert line1 == "READER_BLOCKED_OK", f"Esperado READER_BLOCKED_OK, obtido: {line1}"

        line2 = read_line_with_timeout(p.stdout, timeout=15.0)
        assert line2 == "IMPORT_NUMPY_OK", f"Esperado IMPORT_NUMPY_OK, obtido: {line2}"

        # Envia ping pelo stdin herdado do pai
        p.stdin.write("ping\n")
        p.stdin.flush()

        line3 = read_line_with_timeout(p.stdout, timeout=15.0)
        assert line3 == "PING_RECEIVED_OK", f"Esperado PING_RECEIVED_OK, obtido: {line3}"

        rc = p.wait(timeout=10)
        assert rc == 0, f"Child exited with code {rc}"
    except Exception as exc:
        p.kill()
        try:
            stdout_rem, stderr_rem = p.communicate(timeout=2)
        except Exception:
            stdout_rem, stderr_rem = "", ""
        raise AssertionError(f"D1 Falhou: {exc}\nSTDOUT:\n{stdout_rem}\nSTDERR:\n{stderr_rem}") from exc


def test_d2_disabled_or_non_windows(monkeypatch):
    """D2: Em outro SO ou com variavel de desativacao, devolve False e nao altera stdin."""
    import main

    orig_stdin = sys.stdin

    # Caso 1: sys.platform simulando Linux
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("GRAFO_STDIN_DECOUPLE", raising=False)
    assert main.decouple_stdin_from_fd0() is False
    assert sys.stdin is orig_stdin

    # Caso 2: Windows com GRAFO_STDIN_DECOUPLE=0, false, off
    monkeypatch.setattr(sys, "platform", "win32")
    for val in ["0", "false", "False", "off", "OFF"]:
        monkeypatch.setenv("GRAFO_STDIN_DECOUPLE", val)
        assert main.decouple_stdin_from_fd0() is False
        assert sys.stdin is orig_stdin


def test_d3_os_dup_error_handling(monkeypatch, caplog):
    """D3: Se os.dup levantar OSError, devolve False, nao levanta, loga WARNING e preserva sys.stdin."""
    import main

    orig_stdin = sys.stdin
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("GRAFO_STDIN_DECOUPLE", raising=False)

    def mock_dup(fd):
        raise OSError("Falha simulada de descritor em os.dup")

    monkeypatch.setattr(os, "dup", mock_dup)

    with caplog.at_level(logging.WARNING):
        res = main.decouple_stdin_from_fd0()

    assert res is False
    assert sys.stdin is orig_stdin
    # Verifica que foi logado warning
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) >= 1, "Esperado pelo menos um log de WARNING na falha de os.dup"


def test_d4_main_wiring(monkeypatch):
    """D4: main.main() chama a funcao somente quando TRANSPORT=='stdio'."""
    import main

    called = []
    def mock_decouple():
        called.append(True)
        return True

    monkeypatch.setattr(main, "decouple_stdin_from_fd0", mock_decouple)
    monkeypatch.setattr(main, "bootstrap", lambda: (type("MockServer", (), {"run": lambda self, transport: None})(), None, None))

    # 1. Com stdio
    monkeypatch.setattr(main, "TRANSPORT", "stdio")
    called.clear()
    main.main()
    assert len(called) == 1, "Esperado que decouple_stdin_from_fd0 seja chamado com transport=stdio"

    # 2. Com sse
    monkeypatch.setattr(main, "TRANSPORT", "sse")
    called.clear()
    main.main()
    assert len(called) == 0, "Nao deve chamar decouple_stdin_from_fd0 com transport=sse"


def test_d5_lazy_ml_imports_remain_green():
    """D5: Verifica que os testes T1 e T2 de test_lazy_ml_imports.py continuam passando."""
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_lazy_ml_imports.py", "-k", "test_t1 or test_t2", "-q"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0, f"T1/T2 falharam: {res.stdout}\n{res.stderr}"
    assert "2 passed" in res.stdout
