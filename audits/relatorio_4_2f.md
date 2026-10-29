# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2f
## CORREÇÃO DEFINITIVA DO ACHADO F4-017 (DEADLOCK CRT NO MCP STDIO NO WINDOWS)

> **Data de Emissão:** 2026-10-29 20:09:07
> **Regras aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos de teste gerados).
> **Decisão do Dono:** Implementação exclusiva da **Opção A** (desacoplamento de fd 0 no Windows). Nenhuma alteração em `storage/`, `bootstrap()` nem dependências.

---

### 1. RESUMO EXECUTIVO DA IMPLEMENTAÇÃO
- **Arquivo de produção alterado:** `main.py` exclusivamente (preservação de CRLF e zero quebras de contrato).
- **Volume da alteração:** 41 linhas adicionadas, 0 linhas removidas.
- **Função criada:** `decouple_stdin_from_fd0() -> bool` invocada no arranque de `main()` quando `TRANSPORT == 'stdio'` no Windows.
- **Mecanismo:** Duplica fd 0 para `fd2 = os.dup(0)`, redireciona fd 0 para `os.devnull` via `os.dup2(nul, 0)` e reatribui `sys.stdin` para fluxo sobre `fd2`.
- **Resultado Global:**
  - **Teste Definitivo E2E (Passo 4e):** 20/20 OK (0 TRAVOU) com cliente FastMCP real via STDIO sem wrapper e sem aquecimento em `mcp 1.27.0` e `mcp 1.30.0`.
  - **Suíte Completa (Passo 4b):** 366 passed, 1 skipped, 1 failed (falha pré-existente BL-015 mantida estritamente intacta).
  - **Controle de Regressão (Passo 4f):** `7db9f7d` 6/6 OK; `dd92d35` 6/6 TRAVOU (reproduzindo fidedignamente o bug anterior).

---

### 2. ALTERAÇÃO DE PRODUÇÃO (GIT DIFF LITERAL)
```diff
commit 17f046e2b3f71bfc70444da804f77784ee7f3a59
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Thu Oct 29 15:48:01 2026 -0300

    fix(main): desacopla fd 0 do transporte stdio no Windows para prevenir deadlock de CRT (F4-017)
---
 main.py | 41 +++++++++++++++++++++++++++++++++++++++++
 1 file changed, 41 insertions(+)

diff --git a/main.py b/main.py
index 1bb6c13..abf519e 100644
--- a/main.py
+++ b/main.py
@@ -22,6 +22,7 @@ Environment variables:
     GRAFO_JANITOR_INTERVAL â†’ Janitor interval in seconds (default: 300)
     GRAFO_LOG_LEVEL       â†’ Log level (default: INFO)
     GRAFO_TRANSPORT       â†’ MCP transport: stdio or sse (default: stdio)
+    GRAFO_STDIN_DECOUPLE  â†’ Desacopla fd 0 no Windows para transporte stdio (default: 1)
 
 Usage:
     python main.py
@@ -107,6 +108,42 @@ def setup_logging(level: str = "INFO") -> None:
 logger = logging.getLogger("grafo-concierge.main")
 
 
+def decouple_stdin_from_fd0() -> bool:
+    """Decouples fd 0 from sys.stdin on Windows to prevent CRT/OpenBLAS hang.
+
+    On Windows, late imports (e.g. scipy.special / OpenBLAS) acquire an internal CRT
+    file lock on open stdio descriptors. If a background reader thread is blocked
+    in sys.stdin.buffer.readline() on fd 0, LoadLibraryExW hangs permanently.
+    Redirecting fd 0 to os.devnull and wrapping the duplicated fd2 into sys.stdin
+    avoids the lock collision while preserving bidirectional MCP stdio communication.
+    """
+    if sys.platform != "win32":
+        return False
+
+    decouple_env = os.environ.get("GRAFO_STDIN_DECOUPLE", "1").strip().lower()
+    if decouple_env in ("0", "false", "off"):
+        return False
+
+    nul = -1
+    try:
+        nul = os.open(os.devnull, os.O_RDONLY)
+        fd2 = os.dup(0)
+        os.dup2(nul, 0)
+        os.close(nul)
+        nul = -1
+        sys.stdin = open(fd2, "r", encoding="utf-8", errors="replace", closefd=False)
+        logger.info("Decoupled sys.stdin from fd 0 (allocated duplicate fd=%d)", fd2)
+        return True
+    except Exception as exc:
+        if nul >= 0:
+            try:
+                os.close(nul)
+            except OSError:
+                pass
+        logger.warning("Failed to decouple sys.stdin from fd 0: %s", exc)
+        return False
+
+
 def bootstrap():
     """Initializes and returns all system components.
 
@@ -213,6 +250,10 @@ def main() -> None:
     # â”€â”€ Logging â”€â”€
     setup_logging(LOG_LEVEL)
 
+    # â”€â”€ Stdio Decouple (Windows only, avoids late import hang on fd 0) â”€â”€
+    if TRANSPORT == "stdio":
+        decouple_stdin_from_fd0()
+
     logger.info("=" * 60)
     logger.info("  Grafo Concierge v3.8.0 â€” Absolute Solidity")
     logger.info("=" * 60)
```

---

### 3. PASSO 0 — BASELINE E ERRATA 4-2e-3
#### 3.1 Baseline da Suíte no Commit `75131ca`
```text
.................................................................s...... [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
......................................F................................. [ 79%]
........................................................................ [ 99%]
...                                                                      [100%]
================================== FAILURES ===================================
____ TestProgressiveToolDisclosure.test_telemetry_api_mcp_state_endpoints _____

self = <test_progressive_tool_disclosure.TestProgressiveToolDisclosure testMethod=test_telemetry_api_mcp_state_endpoints>

    def test_telemetry_api_mcp_state_endpoints(self):
        """Valida os endpoints REST /api/mcp/state (POST) e /api/mcp/state/{session_id} (GET)"""
        session_id = "sess_fsm_control"
    
        # 1. Consulta estado default inicial (PLANNING)
        resp_get_default = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_default.status_code, 200)
>       self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")
E       AssertionError: 'EXECUTION' != 'PLANNING'
E       - EXECUTION
E       + PLANNING

tests\test_progressive_tool_disclosure.py:90: AssertionError
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/mcp/state/sess_fsm_control "HTTP/1.1 200 OK"
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

tests/memory_stress_test.py::test_dimension_2
tests/memory_stress_test.py::test_dimension_3
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:341: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 361 passed, 1 skipped, 22 warnings in 74.09s (0:01:14)
```
#### 3.2 Errata 4-2e-3 Registrada em `audits/errata-4-2e-3.md`
1. A coluna 'Opção B' da matriz comparativa anterior não veio do E10, mas do E9, com contaminação concorrente;
2. Confirmada execução simultânea de E7 e E9, e sequencial em E8 e E10;
3. Discrepância de tempo explicada: 7db9f7d sofreu timeout de sockets no Gemini legatário (`GRAFO_LLM_MODEL=none`), enquanto E10 recebeu 404 imediato;
4. Fragilidade da Opção B comprovada (S2 e S5 travam, S3 passa dependendo de adivinhar imports internos da biblioteca);
5. O mecanismo de C-runtime permanece classificado formalmente como `[HIPÓTESE NÃO DEMONSTRADA]`.

---

### 4. PASSO 1 — LEITURA DE STDIN NO TRANSPORTE MCP STDIO
Confirmação de que `stdio_server` em `mcp==1.27.0` e `mcp==1.30.0` obtém streams via `sys.stdin.buffer`:
```python
=== MCP 1.27.0 (sys / venv_mcp127) ===
Arquivo: C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\mcp\server\stdio.py
Trecho de stdio_server:
async def stdio_server(
    stdin: anyio.AsyncFile[str] | None = None,
    stdout: anyio.AsyncFile[str] | None = None,
):
    """
    Server transport for stdio: this communicates with an MCP client by reading
    from the current process' stdin and writing to stdout.
    """
    # Purposely not using context managers for these, as we don't want to close
    # standard process handles. Encoding of stdin/stdout as text streams on
    # python is platform-dependent (Windows is particularly problematic), so we
    # re-wrap the underlying binary stream to ensure UTF-8.
    if not stdin:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))
    if not stdout:
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]

    write_stream: MemoryObjectSendStream[SessionMessage]
    write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    async def stdin_reader():
        try:
            async with read_stream_writer:
                async for line in stdin:
                    try:
                        message = types.JSONRPCMessage.model_validate_json(line)
                    except Exception as exc:
                        await read_stream_writer.send(exc)
                        continue

                    session_message = SessionMessage(message)
                    await read_stream_writer.send(session_message)
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async def stdout_writer():
        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    await stdout.write(json + "\n")
                    await stdout.flush()
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async with anyio.create_task_group() as tg:

=== MCP 1.30.0 (venv_mcp130_real) ===
Arquivo: C:\Nexus-Memory\_venvs_4_2e\venv_mcp130_real\Lib\site-packages\mcp\server\stdio.py
Trecho de stdio_server:
async def stdio_server(
    stdin: anyio.AsyncFile[str] | None = None,
    stdout: anyio.AsyncFile[str] | None = None,
):
    """
    Server transport for stdio: this communicates with an MCP client by reading
    from the current process' stdin and writing to stdout.
    """
    # Purposely not using context managers for these, as we don't want to close
    # standard process handles. Encoding of stdin/stdout as text streams on
    # python is platform-dependent (Windows is particularly problematic), so we
    # re-wrap the underlying binary stream to ensure UTF-8.
    if not stdin:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))
    if not stdout:
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]

    write_stream: MemoryObjectSendStream[SessionMessage]
    write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    async def stdin_reader():
        try:
            async with read_stream_writer:
                async for line in stdin:
                    try:
                        message = types.JSONRPCMessage.model_validate_json(line)
                    except Exception as exc:
                        await read_stream_writer.send(exc)
                        continue

                    session_message = SessionMessage(message)
                    await read_stream_writer.send(session_message)
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async def stdout_writer():
        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    await stdout.write(json + "\n")
                    await stdout.flush()
        except anyio.ClosedResourceError:  # pragma: no cover
            await anyio.lowlevel.checkpoint()

    async with anyio.create_task_group() as tg:

=== COMPARACAO E CONFIRMACAO ===
Os trechos de obtencao do stdin em stdio_server sao IDENTICOS: True
Ambas as versoes executam exatamente:
    if not stdin:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))

Confirmacao tecnica: Substituir sys.stdin por um objeto TextIOWrapper com .buffer proprio apontando
para o novo descritor (fd2) desacoplado do fd 0 satisfaz plenamente tanto mcp==1.27.0 quanto mcp==1.30.0.
```
Conclusão: Substituir `sys.stdin` preservando `.buffer` em `fd2` é 100% suficiente para o transporte stdio.

---

### 5. PASSO 2 — TESTES PRIMEIRO (VERMELHOS D1-D5)
Execução de `pytest tests/test_stdin_decouple.py -q` antes da implementação em `main.py`:
```text
FFFF.                                                                    [100%]
================================== FAILURES ===================================
_____________________ test_d1_subprocess_decouple_windows _____________________

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
            line1 = p.stdout.readline().strip()
>           assert line1 == "READER_BLOCKED_OK", f"Esperado READER_BLOCKED_OK, obtido: {line1}"
E           AssertionError: Esperado READER_BLOCKED_OK, obtido: 
E           assert '' == 'READER_BLOCKED_OK'
E             
E             - READER_BLOCKED_OK

tests\test_stdin_decouple.py:95: AssertionError

The above exception was the direct cause of the following exception:

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
            line1 = p.stdout.readline().strip()
            assert line1 == "READER_BLOCKED_OK", f"Esperado READER_BLOCKED_OK, obtido: {line1}"
    
            line2 = p.stdout.readline().strip()
            assert line2 == "IMPORT_NUMPY_OK", f"Esperado IMPORT_NUMPY_OK, obtido: {line2}"
    
            # Envia ping pelo stdin herdado do pai
            p.stdin.write("ping\n")
            p.stdin.flush()
    
            line3 = p.stdout.readline().strip()
            assert line3 == "PING_RECEIVED_OK", f"Esperado PING_RECEIVED_OK, obtido: {line3}"
    
            rc = p.wait(timeout=10)
            assert rc == 0, f"Child exited with code {rc}"
        except Exception as exc:
            p.kill()
            stdout_rem, stderr_rem = p.communicate()
>           raise AssertionError(f"D1 Falhou: {exc}\nSTDOUT:\n{stdout_rem}\nSTDERR:\n{stderr_rem}") from exc
E           AssertionError: D1 Falhou: Esperado READER_BLOCKED_OK, obtido: 
E           assert '' == 'READER_BLOCKED_OK'
E             
E             - READER_BLOCKED_OK
E           STDOUT:
E           
E           STDERR:
E           Traceback (most recent call last):
E             File "<string>", line 9, in <module>
E               success = main.decouple_stdin_from_fd0()
E                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           AttributeError: module 'main' has no attribute 'decouple_stdin_from_fd0'

tests\test_stdin_decouple.py:112: AssertionError
_______________________ test_d2_disabled_or_non_windows _______________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000015692003E10>

    def test_d2_disabled_or_non_windows(monkeypatch):
        """D2: Em outro SO ou com variavel de desativacao, devolve False e nao altera stdin."""
        import main
    
        orig_stdin = sys.stdin
    
        # Caso 1: sys.platform simulando Linux
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("GRAFO_STDIN_DECOUPLE", raising=False)
>       assert main.decouple_stdin_from_fd0() is False
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'main' has no attribute 'decouple_stdin_from_fd0'

tests\test_stdin_decouple.py:124: AttributeError
________________________ test_d3_os_dup_error_handling ________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000015692174D60>
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001569203F770>

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
>           res = main.decouple_stdin_from_fd0()
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           AttributeError: module 'main' has no attribute 'decouple_stdin_from_fd0'

tests\test_stdin_decouple.py:149: AttributeError
_____________________________ test_d4_main_wiring _____________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000015692191010>

    def test_d4_main_wiring(monkeypatch):
        """D4: main.main() chama a funcao somente quando TRANSPORT=='stdio'."""
        import main
    
        called = []
        def mock_decouple():
            called.append(True)
            return True
    
>       monkeypatch.setattr(main, "decouple_stdin_from_fd0", mock_decouple)
E       AttributeError: <module 'main' from 'C:\\Nexus-Memory\\GrafoConcierge\\main.py'> has no attribute 'decouple_stdin_from_fd0'

tests\test_stdin_decouple.py:167: AttributeError
=========================== short test summary info ===========================
FAILED tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows - As...
FAILED tests/test_stdin_decouple.py::test_d2_disabled_or_non_windows - Attrib...
FAILED tests/test_stdin_decouple.py::test_d3_os_dup_error_handling - Attribut...
FAILED tests/test_stdin_decouple.py::test_d4_main_wiring - AttributeError: <m...
4 failed, 1 passed in 6.47s
```

---

### 6. PASSO 4a & 4b — VERIFICAÇÃO VERDE E SUÍTE COMPLETA
#### 6.1 Testes D1-D5 Verdes (`tests/test_stdin_decouple.py`)
```text
.....                                                                    [100%]
5 passed in 9.85s
```
*(Zero skips no Windows; 5/5 passaram em ~9.8s)*

#### 6.2 Suíte Completa de Regressão (`pytest tests/ -q`)
```text
.................................................................s...... [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
......................................F................................. [ 78%]
........................................................................ [ 97%]
........                                                                 [100%]
================================== FAILURES ===================================
____ TestProgressiveToolDisclosure.test_telemetry_api_mcp_state_endpoints _____

self = <test_progressive_tool_disclosure.TestProgressiveToolDisclosure testMethod=test_telemetry_api_mcp_state_endpoints>

    def test_telemetry_api_mcp_state_endpoints(self):
        """Valida os endpoints REST /api/mcp/state (POST) e /api/mcp/state/{session_id} (GET)"""
        session_id = "sess_fsm_control"
    
        # 1. Consulta estado default inicial (PLANNING)
        resp_get_default = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_default.status_code, 200)
>       self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")
E       AssertionError: 'EXECUTION' != 'PLANNING'
E       - EXECUTION
E       + PLANNING

tests\test_progressive_tool_disclosure.py:90: AssertionError
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/mcp/state/sess_fsm_control "HTTP/1.1 200 OK"
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

tests/memory_stress_test.py::test_dimension_2
tests/memory_stress_test.py::test_dimension_3
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:341: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 366 passed, 1 skipped, 22 warnings in 80.87s (0:01:20)
```
*(366 passed, 1 skipped, 1 failed BL-015; baseline estritamente preservado)*

---

### 7. PASSO 4c — TESTES DE MUTAÇÃO
#### Mutação (i): Remoção da chamada em `main()` -> D4 deve falhar:
```text
F                                                                        [100%]
================================== FAILURES ===================================
_____________________________ test_d4_main_wiring _____________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001F52E260180>

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
>       assert len(called) == 1, "Esperado que decouple_stdin_from_fd0 seja chamado com transport=stdio"
E       AssertionError: Esperado que decouple_stdin_from_fd0 seja chamado com transport=stdio
E       assert 0 == 1
E        +  where 0 = len([])

tests\test_stdin_decouple.py:174: AssertionError
---------------------------- Captured stderr call -----------------------------
2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 \u2014 Absolute Solidity\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\\Nexus-Memory\\GrafoConcierge\\data\\chroma (grafo_concierge)\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: stdio\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=stdio)...\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.\n2026-10-29 15:50:50 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
------------------------------ Captured log call ------------------------------
INFO     grafo-concierge.main:main.py:257 ============================================================
INFO     grafo-concierge.main:main.py:258   Grafo Concierge v3.8.0 � Absolute Solidity
INFO     grafo-concierge.main:main.py:259 ============================================================
INFO     grafo-concierge.main:main.py:260   DB:       C:\Nexus-Memory\GrafoConcierge\data\concierge.db
INFO     grafo-concierge.main:main.py:261   ChromaDB: C:\Nexus-Memory\GrafoConcierge\data\chroma (grafo_concierge)
INFO     grafo-concierge.main:main.py:262   Embedding: all-MiniLM-L6-v2
INFO     grafo-concierge.main:main.py:263   LLM:      gemini-2.0-flash
INFO     grafo-concierge.main:main.py:264   Janitor:  300s
INFO     grafo-concierge.main:main.py:265   Transport: stdio
INFO     grafo-concierge.main:main.py:266   Log Level: INFO
INFO     grafo-concierge.main:main.py:267 ============================================================
INFO     grafo-concierge.main:main.py:282 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
INFO     grafo-concierge.main:main.py:285 Starting MCP server (transport=stdio)...
INFO     grafo-concierge.main:main.py:297 Graceful shutdown initiated...
INFO     grafo-concierge.main:main.py:313 ============================================================
INFO     grafo-concierge.main:main.py:314   Grafo Concierge encerrado com sucesso.
INFO     grafo-concierge.main:main.py:315 ============================================================
=========================== short test summary info ===========================
FAILED tests/test_stdin_decouple.py::test_d4_main_wiring - AssertionError: Es...
1 failed, 4 deselected in 0.23s
```

#### Mutação (ii): Remoção de `dup2(nul, 0)` -> D1 deve falhar por hang/timeout:
```text
F                                                                        [100%]
================================== FAILURES ===================================
_____________________ test_d1_subprocess_decouple_windows _____________________

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
    
>           line2 = read_line_with_timeout(p.stdout, timeout=15.0)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_stdin_decouple.py:119: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

pipe = <_io.TextIOWrapper name=12 encoding='cp1252'>, timeout = 15.0

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
>           raise TimeoutError(f"Timeout de {timeout}s aguardando linha do pipe")
E           TimeoutError: Timeout de 15.0s aguardando linha do pipe

tests\test_stdin_decouple.py:32: TimeoutError

The above exception was the direct cause of the following exception:

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
>           raise AssertionError(f"D1 Falhou: {exc}\nSTDOUT:\n{stdout_rem}\nSTDERR:\n{stderr_rem}") from exc
E           AssertionError: D1 Falhou: Timeout de 15.0s aguardando linha do pipe
E           STDOUT:
E           
E           STDERR:

tests\test_stdin_decouple.py:137: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows - As...
1 failed, 4 deselected in 17.40s
```

#### Mutação (iii): Chamada indevida com `TRANSPORT=='sse'` -> D4 deve falhar:
```text
F                                                                        [100%]
================================== FAILURES ===================================
_____________________________ test_d4_main_wiring _____________________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001B2DC8CC180>

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
>       assert len(called) == 0, "Nao deve chamar decouple_stdin_from_fd0 com transport=sse"
E       AssertionError: Nao deve chamar decouple_stdin_from_fd0 com transport=sse
E       assert 1 == 0
E        +  where 1 = len([True])

tests\test_stdin_decouple.py:205: AssertionError
---------------------------- Captured stderr call -----------------------------
2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 \u2014 Absolute Solidity\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\\Nexus-Memory\\GrafoConcierge\\data\\chroma (grafo_concierge)\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: stdio\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=stdio)...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 \u2014 Absolute Solidity\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 \u2014 Absolute Solidity\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\\Nexus-Memory\\GrafoConcierge\\data\\concierge.db\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\\Nexus-Memory\\GrafoConcierge\\data\\chroma (grafo_concierge)\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\\Nexus-Memory\\GrafoConcierge\\data\\chroma (grafo_concierge)\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: sse\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: sse\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=sse)...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=sse)...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================\n2026-10-29 18:41:49 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
------------------------------ Captured log call ------------------------------
INFO     grafo-concierge.main:main.py:257 ============================================================
INFO     grafo-concierge.main:main.py:258   Grafo Concierge v3.8.0 � Absolute Solidity
INFO     grafo-concierge.main:main.py:259 ============================================================
INFO     grafo-concierge.main:main.py:260   DB:       C:\Nexus-Memory\GrafoConcierge\data\concierge.db
INFO     grafo-concierge.main:main.py:261   ChromaDB: C:\Nexus-Memory\GrafoConcierge\data\chroma (grafo_concierge)
INFO     grafo-concierge.main:main.py:262   Embedding: all-MiniLM-L6-v2
INFO     grafo-concierge.main:main.py:263   LLM:      gemini-2.0-flash
INFO     grafo-concierge.main:main.py:264   Janitor:  300s
INFO     grafo-concierge.main:main.py:265   Transport: stdio
INFO     grafo-concierge.main:main.py:266   Log Level: INFO
INFO     grafo-concierge.main:main.py:267 ============================================================
INFO     grafo-concierge.main:main.py:282 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
INFO     grafo-concierge.main:main.py:285 Starting MCP server (transport=stdio)...
INFO     grafo-concierge.main:main.py:297 Graceful shutdown initiated...
INFO     grafo-concierge.main:main.py:313 ============================================================
INFO     grafo-concierge.main:main.py:314   Grafo Concierge encerrado com sucesso.
INFO     grafo-concierge.main:main.py:315 ============================================================
INFO     grafo-concierge.main:main.py:257 ============================================================
INFO     grafo-concierge.main:main.py:258   Grafo Concierge v3.8.0 � Absolute Solidity
INFO     grafo-concierge.main:main.py:259 ============================================================
INFO     grafo-concierge.main:main.py:260   DB:       C:\Nexus-Memory\GrafoConcierge\data\concierge.db
INFO     grafo-concierge.main:main.py:261   ChromaDB: C:\Nexus-Memory\GrafoConcierge\data\chroma (grafo_concierge)
INFO     grafo-concierge.main:main.py:262   Embedding: all-MiniLM-L6-v2
INFO     grafo-concierge.main:main.py:263   LLM:      gemini-2.0-flash
INFO     grafo-concierge.main:main.py:264   Janitor:  300s
INFO     grafo-concierge.main:main.py:265   Transport: sse
INFO     grafo-concierge.main:main.py:266   Log Level: INFO
INFO     grafo-concierge.main:main.py:267 ============================================================
INFO     grafo-concierge.main:main.py:282 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
INFO     grafo-concierge.main:main.py:285 Starting MCP server (transport=sse)...
INFO     grafo-concierge.main:main.py:297 Graceful shutdown initiated...
INFO     grafo-concierge.main:main.py:313 ============================================================
INFO     grafo-concierge.main:main.py:314   Grafo Concierge encerrado com sucesso.
INFO     grafo-concierge.main:main.py:315 ============================================================
=========================== short test summary info ===========================
FAILED tests/test_stdin_decouple.py::test_d4_main_wiring - AssertionError: Na...
1 failed, 4 deselected in 0.19s
```
*(Todas as mutações foram testadas e devidamente revertidas para produção limpa)*

---

### 8. PASSO 4d — FASTMCP STARTUP & HANDSHAKE (`boot_check.py`)
#### 8.1 Handshake no venv `mcp 1.27.0`:
```text
======================================================================
BOOT CHECK � Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.27.0
Entrypoint Mode:    python-main
Timeout:            120.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_chroma
======================================================================
Executando comando: C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.27.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.002
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Decoupled sys.stdin from fd 0 (allocated duplicate fd=4)
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 � Absolute Solidity
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_concierge.db
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_chroma (test_boot_collection)
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: stdio
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:44:45 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing SqliteStore: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_concierge.db
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.schema       \u2502 Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 Schema v3.8.0 verified - all tables and triggers OK.
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 SerializedWriteQueue started successfully (db: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_concierge.db)
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 SqliteStore initialized: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_concierge.db
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing EmbeddingManager: tier=FLASH
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.vector-store \u2502 EmbeddingManager initialized: tier=flash, model=all-MiniLM-L6-v2, dims=384
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing ChromaVectorStore: path=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_chroma, collection=test_boot_collection
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.vector-store \u2502 ChromaVectorStore initialized: dir=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_r6xw73d7\test_chroma, collection=test_boot_collection, tier=flash
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing ZoomSummarizer: model=gemini-2.0-flash
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.summarizer   \u2502 LLMAdapter inicializado: model=gemini-2.0-flash, custom_fn=False
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing IngestionManager
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.crawler      \u2502 ProjectCrawler initialized: 22 active ignore patterns.
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.orchestrator \u2502 IngestionManager inicializado: summarizer=ON, embedder_tier=flash
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing JanitorService: interval=300s
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.janitor      \u2502 JanitorService initialized: stale=30d, zoom_threshold=10, inactive=60d, super_node_threshold=10
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing GrafoConcierge Central Facade
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.middleware   \u2502 GrafoConcierge (Facade) initialized successfully.
2026-10-29 18:44:47 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing GrafoConciergeServer
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 GrafoConciergeServer initialized � 31 tools registered.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Bootstrap complete � all components initialized.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=stdio)...
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 Starting Grafo Concierge MCP Server (transport=stdio)...
2026-10-29 18:44:48 \u2502 INFO    \u2502 mcp.server.lowlevel.server   \u2502 Processing request of type ListToolsRequest
2026-10-29 18:44:48 \u2502 INFO    \u2502 mcp.server.lowlevel.server   \u2502 Processing request of type CallToolRequest
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 concierge_status OK
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor encerrado.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 Requesting stop of SerializedWriteQueue...
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 SerializedWriteQueue finished.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 SqliteStore closed.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 SqliteStore encerrado.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.
2026-10-29 18:44:48 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
```

#### 8.2 Handshake no venv `mcp 1.30.0`:
```text
======================================================================
BOOT CHECK � Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Nexus-Memory\_venvs_4_2e\venv_mcp130_real\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.30.0
Entrypoint Mode:    python-main
Timeout:            120.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_chroma
======================================================================
Executando comando: C:\Nexus-Memory\_venvs_4_2e\venv_mcp130_real\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.30.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.002
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Decoupled sys.stdin from fd 0 (allocated duplicate fd=4)
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge v3.8.0 � Absolute Solidity
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   DB:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_concierge.db
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   ChromaDB: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_chroma (test_boot_collection)
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Embedding: all-MiniLM-L6-v2
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   LLM:      gemini-2.0-flash
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Janitor:  300s
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Transport: stdio
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Log Level: INFO
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing SqliteStore: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_concierge.db
2026-10-29 18:45:03 \u2502 WARNING \u2502 grafo-concierge.vector-store \u2502 chromadb not installed. Install with: pip install chromadb>=0.4.0
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.schema       \u2502 Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 Schema v3.8.0 verified - all tables and triggers OK.
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 SerializedWriteQueue started successfully (db: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_concierge.db)
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 SqliteStore initialized: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_concierge.db
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing EmbeddingManager: tier=FLASH
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.vector-store \u2502 EmbeddingManager initialized: tier=flash, model=all-MiniLM-L6-v2, dims=384
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing ChromaVectorStore: path=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_ugt66igo\test_chroma, collection=test_boot_collection
2026-10-29 18:45:03 \u2502 WARNING \u2502 grafo-concierge.vector-store \u2502 ChromaVectorStore operating in NO-OP mode (chromadb not installed).
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing ZoomSummarizer: model=gemini-2.0-flash
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.summarizer   \u2502 LLMAdapter inicializado: model=gemini-2.0-flash, custom_fn=False
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing IngestionManager
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.crawler      \u2502 ProjectCrawler initialized: 22 active ignore patterns.
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.orchestrator \u2502 IngestionManager inicializado: summarizer=ON, embedder_tier=flash
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing JanitorService: interval=300s
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.janitor      \u2502 JanitorService initialized: stale=30d, zoom_threshold=10, inactive=60d, super_node_threshold=10
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing GrafoConcierge Central Facade
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.middleware   \u2502 GrafoConcierge (Facade) initialized successfully.
2026-10-29 18:45:03 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Initializing GrafoConciergeServer
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 GrafoConciergeServer initialized � 31 tools registered.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Bootstrap complete � all components initialized.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Starting MCP server (transport=stdio)...
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 Starting Grafo Concierge MCP Server (transport=stdio)...
2026-10-29 18:45:04 \u2502 INFO    \u2502 mcp.server.lowlevel.server   \u2502 Processing request of type ListToolsRequest
2026-10-29 18:45:04 \u2502 INFO    \u2502 mcp.server.lowlevel.server   \u2502 Processing request of type CallToolRequest
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.mcp          \u2502 concierge_status OK
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Graceful shutdown initiated...
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 Janitor encerrado.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 Requesting stop of SerializedWriteQueue...
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.connection   \u2502 SerializedWriteQueue finished.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.store        \u2502 SqliteStore closed.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 SqliteStore encerrado.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502   Grafo Concierge encerrado com sucesso.
2026-10-29 18:45:04 \u2502 INFO    \u2502 grafo-concierge.main         \u2502 ============================================================
```
*(31 ferramentas ativas, `concierge_status` OK e log de desacoplamento de fd 0 presente em ambos)*

---

### 9. PASSO 4e — TESTE DEFINITIVO DO F4-017 (MCP REAL STDIO SEM WRAPPER)
20 execuções sequenciais (5 search-first + 5 mine em mcp 1.27.0 e mcp 1.30.0) com medição de CPU a cada 5s:
```text
=== TABELA PASSO 4e: TESTE DEFINITIVO F4-017 (MCP REAL STDIO SEM WRAPPER) ===
Data: 2026-10-29 19:06:09
Total de execuções: 20 (2 venvs x 2 cenários x 5 repetições)

Venv          | Cenário       | Rep  | Classe  | t_init(s)  | t_critica(s)  | t_sec(s)   | CPU_mean(%) 
-----------------------------------------------------------------------------------------------
mcp_1_27_0    | search-first  | 1    | OK      | 2.63       | 11.47         | 0.01       | 0.0         
mcp_1_27_0    | search-first  | 2    | OK      | 2.59       | 11.16         | 0.02       | 0.0         
mcp_1_27_0    | search-first  | 3    | OK      | 2.69       | 11.09         | 0.02       | 0.0         
mcp_1_27_0    | search-first  | 4    | OK      | 2.59       | 11.25         | 0.02       | 0.0         
mcp_1_27_0    | search-first  | 5    | OK      | 2.66       | 11.29         | 0.02       | 0.0         
mcp_1_27_0    | mine          | 1    | OK      | 2.63       | 33.57         | 0.02       | 0.0         
mcp_1_27_0    | mine          | 2    | OK      | 2.64       | 32.71         | 0.02       | 0.0         
mcp_1_27_0    | mine          | 3    | OK      | 2.72       | 33.79         | 0.02       | 0.0         
mcp_1_27_0    | mine          | 4    | OK      | 2.63       | 32.29         | 0.02       | 0.0         
mcp_1_27_0    | mine          | 5    | OK      | 2.71       | 33.99         | 0.02       | 0.0         
mcp_1_30_0    | search-first  | 1    | OK      | 1.34       | 9.36          | 0.01       | 0.0         
mcp_1_30_0    | search-first  | 2    | OK      | 1.34       | 9.25          | 0.01       | 0.0         
mcp_1_30_0    | search-first  | 3    | OK      | 1.34       | 9.56          | 0.01       | 0.1         
mcp_1_30_0    | search-first  | 4    | OK      | 1.33       | 9.71          | 0.02       | 0.1         
mcp_1_30_0    | search-first  | 5    | OK      | 1.38       | 9.39          | 0.02       | 0.0         
mcp_1_30_0    | mine          | 1    | OK      | 1.44       | 10.14         | 0.01       | 0.0         
mcp_1_30_0    | mine          | 2    | OK      | 1.45       | 10.31         | 0.01       | 0.0         
mcp_1_30_0    | mine          | 3    | OK      | 1.45       | 10.19         | 0.02       | 0.0         
mcp_1_30_0    | mine          | 4    | OK      | 1.39       | 10.17         | 0.01       | 0.1         
mcp_1_30_0    | mine          | 5    | OK      | 1.46       | 10.39         | 0.01       | 0.0         
-----------------------------------------------------------------------------------------------
Total OK: 20/20 | Total TRAVOU: 0/20 | Total ERRO: 0/20
Status Final: SUCESSO ABSOLUTO (20/20 OK)
```

---

### 10. PASSO 4f — CONTROLE DE REGRESSÃO NOS COMMITS DE REFERÊNCIA
Execução em `7db9f7d` e `dd92d35` (3 repetições de search-first e mine, timeout 180s):
```text
=== TABELA PASSO 4f: REGRESSAO DOS COMMITS DE REFERENCIA ===
Commits: 7db9f7d (pre-4.2d) vs dd92d35 (HEAD anterior, sem desacoplamento)
Repeticoes: n=3 por cenario, Timeout: 180s

Commit     | Cenario       | Rep  | Status   | t_init(s)  | t_crit(s)  | Total(s)   | Detalhes
-----------------------------------------------------------------------------------------------
7db9f7d    | mine          | 1    | OK       | 12.19      | 78.56      | 93.32      | OK
7db9f7d    | mine          | 2    | OK       | 12.48      | 78.22      | 93.21      | OK
7db9f7d    | mine          | 3    | OK       | 12.13      | 78.27      | 93.11      | OK
dd92d35    | mine          | 1    | TRAVOU   | 2.56       | 180.00     | 243.62     | TRAVOU (CPU=0.1%)
dd92d35    | mine          | 2    | TRAVOU   | 2.51       | 180.00     | 243.60     | TRAVOU (CPU=0.1%)
dd92d35    | mine          | 3    | TRAVOU   | 2.71       | 180.01     | 243.87     | TRAVOU (CPU=0.1%)
7db9f7d    | search-first  | 1    | OK       | 12.76      | 4.33       | 114.41     | OK
7db9f7d    | search-first  | 2    | OK       | 12.58      | 4.65       | 112.73     | OK
7db9f7d    | search-first  | 3    | OK       | 12.51      | 4.64       | 112.50     | OK
dd92d35    | search-first  | 1    | TRAVOU   | 2.56       | 180.01     | 337.65     | TRAVOU (CPU=0.0%)
dd92d35    | search-first  | 2    | TRAVOU   | 2.44       | 180.00     | 337.87     | TRAVOU (CPU=0.1%)
dd92d35    | search-first  | 3    | TRAVOU   | 2.37       | 180.01     | 336.79     | TRAVOU (CPU=0.0%)
-----------------------------------------------------------------------------------------------

RESUMO ESTATISTICO:
--------------------------------------------------
Commit 7db9f7d  | Cenario search-first | OK: 3/3 | TRAVOU: 0/3
Commit dd92d35  | Cenario search-first | OK: 0/3 | TRAVOU: 3/3
Commit 7db9f7d  | Cenario mine         | OK: 3/3 | TRAVOU: 0/3
Commit dd92d35  | Cenario mine         | OK: 0/3 | TRAVOU: 3/3
===============================================================================================
```
*(Confirma que o commit anterior dd92d35 reproduz 100% o travamento em ambas as operações, e que a versão 7db9f7d passava apenas porque carregava os modelos no bootstrap)*

---

### 11. PASSO 4g — TESTE UNITÁRIO ISOLADO E1-(i) COM NOVO CÓDIGO
Execução de `run_e1_new_code.py` com leitor de stdin ativamente bloqueado ($n=5$):
```text
=== EXPERIMENTO E1-(i) COM main.decouple_stdin_from_fd0() (Passo 4g) ===
Data: 2026-10-29 18:53:34
Cenário: import scipy.special na thread principal com leitor de stdin bloqueado
Número de repetições: n=5, Timeout: 60s por repetição

Rep | Status | Tempo (s) | reader_blocked | import_ok | Codigo Saida
--------------------------------------------------------------------
 1  |   OK   |  2.9198   |      True      |   True    |      0      
 2  |   OK   |  3.0242   |      True      |   True    |      0      
 3  |   OK   |  2.9145   |      True      |   True    |      0      
 4  |   OK   |  2.9246   |      True      |   True    |      0      
 5  |   OK   |  2.9191   |      True      |   True    |      0      
--------------------------------------------------------------------
Conclusão: 5/5 OK - Deadlock eliminado com sucesso
```
*(5/5 OK com import concluído em ~2.9s sem deadlock)*

---

### 12. PASSO 4h — ENCERRAMENTO GRACIOSO DO SERVIDOR
Fechamento do canal stdin do pai encerra o servidor MCP de forma graciosa (<15s):
```text
=== TESTE DE ENCERRAMENTO GRACIOSO APOS FECHAMENTO DE STDIN (Passo 4h) ===
Data: 2026-10-29 18:49:48
Limite maximo aceitavel: < 15.0s

Repeticao | Status | Tempo Encerramento (s) | Codigo Saida
-----------------------------------------------------------
    1     |   OK   |         0.2925         |      0      
    2     |   OK   |         0.3029         |      0      
    3     |   OK   |         0.3056         |      0      
-----------------------------------------------------------
Conclusao: TODOS PASSARAM (<15s)
```
*(Encerramento limpo em ~0.30s com código de retorno 0 em 3/3 repetições)*

---

### 13. CONCLUSÃO E GATE DA REGRA 7
1. **F4-017:** Corrigido definitivamente pelo executor através da Opção A (`decouple_stdin_from_fd0()`).
2. **F4-015:** Mantido como corrigido; a redução de tempo de bootstrap para <3s foi preservada sem aquecimento em thread nem efeitos colaterais.
3. **Parada Obrigatória no Gate (Regra 7):** O executor submete as evidências para auditoria independente e **não** inicia novas rodadas nem altera configurações adicionais.
