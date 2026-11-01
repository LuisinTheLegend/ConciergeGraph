# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2g
## FECHAMENTO DAS 4 LACUNAS DA RODADA 4.2f (ACHADO F4-017)

> **Data de Emissão:** 2026-11-01 00:30:37
> **Regras aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos gerados por script).
> **Escopo:** Somente docstring de `decouple_stdin_from_fd0` em `main.py` (Item 2), `tests/test_stdin_decouple.py` (Itens 1 e 4a), `.github/workflows/windows-stdin.yml` (Item 4b), `audits/` e `scratch/evidencia_4_2g/`. Zero alteração em código executável de produção.

---

### 1. PASSO 0 — BASELINE
#### 1.1 Sincronização Git (`git pull`, `HEAD`, `origin/main`)
```text
git pull: Already up to date.
git rev-parse HEAD: 21610d851e47016c67e5f3cb8054aa37cd29900c
git ls-remote origin main: 21610d851e47016c67e5f3cb8054aa37cd29900c	refs/heads/main
```
#### 1.2 Suíte Completa no Baseline (`pytest tests/ -q`)
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
1 failed, 366 passed, 1 skipped, 22 warnings in 99.52s (0:01:39)
```

---

### 2. ITEM 1 & ITEM 4a — REMOÇÃO DO D5 FRÁGIL E SKIP EXPLÍCITO EM D1 SEM SCIPY
**Justificativa da remoção do D5 (2 linhas):**
O teste D5 apenas reexecutava em subprocesso os testes T1 e T2 de `tests/test_lazy_ml_imports.py` exigindo a string fixa `"2 passed"`, o que quebrava legitimamente em ambientes sem `sentence_transformers` (`"2 skipped"`).
Como T1 e T2 já integram a suíte oficial (e rodam diretamente no CI ao lado de `test_stdin_decouple.py`), a remoção de D5 elimina a duplicação frágil sem reduzir a cobertura de regressão.

#### 2.1 Item 1a — `pip freeze` do venv limpo sem ML (`venv_min_no_ml`)
```text
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
attrs==26.1.0
certifi==2026.10.23
cffi==2.1.1
click==8.5.0
colorama==0.4.6
cryptography==50.0.2
fastapi==0.162.0
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
httpx-sse==0.4.3
idna==3.20
iniconfig==2.3.1
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
mcp==1.30.0
numpy==2.5.4
opentelemetry-api==1.45.2
packaging==26.3
pluggy==1.7.0
pycparser==3.12
pydantic==2.14.2
pydantic-settings==2.16.2
pydantic_core==2.50.2
Pygments==2.21.0
PyJWT==2.15.1
pytest==9.2.0
python-dotenv==1.2.4
python-multipart==0.0.33
pywin32==312
referencing==0.37.0
rpds-py==2026.9.1
sse-starlette==3.6.0
starlette==1.10.0
typing-inspection==0.4.4
typing_extensions==4.16.0
uvicorn==0.54.0
```
#### 2.2 Item 1b — VERMELHO no `HEAD 21610d8` com `venv_min_no_ml`
```text
F...F                                                                    [100%]
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
    
            line2 = read_line_with_timeout(p.stdout, timeout=15.0)
>           assert line2 == "IMPORT_NUMPY_OK", f"Esperado IMPORT_NUMPY_OK, obtido: {line2}"
E           AssertionError: Esperado IMPORT_NUMPY_OK, obtido: 
E           assert '' == 'IMPORT_NUMPY_OK'
E             
E             - IMPORT_NUMPY_OK

tests\test_stdin_decouple.py:120: AssertionError

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
E           AssertionError: D1 Falhou: Esperado IMPORT_NUMPY_OK, obtido: 
E           assert '' == 'IMPORT_NUMPY_OK'
E             
E             - IMPORT_NUMPY_OK
E           STDOUT:
E           
E           STDERR:
E           Traceback (most recent call last):
E             File "<string>", line 34, in <module>
E               import scipy.special
E           ModuleNotFoundError: No module named 'scipy'
E           Fatal Python error: _enter_buffered_busy: could not acquire lock for <_io.BufferedReader name=4> at interpreter shutdown, possibly due to daemon threads
E           Python runtime state: finalizing (tstate=0x00007ff86247ed10)
E           
E           Current thread 0x000011d8 (most recent call first):
E             <no Python frame>
E           
E           Extension modules: numpy._core._multiarray_umath, numpy.linalg._umath_linalg (total: 2)

tests\test_stdin_decouple.py:137: AssertionError
____________________ test_d5_lazy_ml_imports_remain_green _____________________

    def test_d5_lazy_ml_imports_remain_green():
        """D5: Verifica que os testes T1 e T2 de test_lazy_ml_imports.py continuam passando."""
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_lazy_ml_imports.py", "-k", "test_t1 or test_t2", "-q"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert res.returncode == 0, f"T1/T2 falharam: {res.stdout}\n{res.stderr}"
>       assert "2 passed" in res.stdout
E       AssertionError: assert '2 passed' in 'ss                                                                       [100%]\n2 skipped, 3 deselected in 0.28s\n'
E        +  where 'ss                                                                       [100%]\n2 skipped, 3 deselected in 0.28s\n' = CompletedProcess(args=['C:\\Nexus-Memory\\_venvs_4_2g\\venv_min_no_ml\\Scripts\\python.exe', '-m', 'pytest', 'tests/te...                                                                [100%]\n2 skipped, 3 deselected in 0.28s\n', stderr='').stdout

tests\test_stdin_decouple.py:217: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows - As...
FAILED tests/test_stdin_decouple.py::test_d5_lazy_ml_imports_remain_green - A...
2 failed, 3 passed in 9.08s
```
#### 2.3 Item 1c & 4a — Diff literal de `tests/test_stdin_decouple.py` (Commit `6defadc`)
```diff
diff --git a/tests/test_stdin_decouple.py b/tests/test_stdin_decouple.py
index 699f0a2..75de7f3 100644
--- a/tests/test_stdin_decouple.py
+++ b/tests/test_stdin_decouple.py
@@ -1,10 +1,11 @@
 # tests/test_stdin_decouple.py
 """
-Rodada 4.2f: Testes de unidade e integracao para decouple_stdin_from_fd0().
-Cobre requisitos D1, D2, D3, D4 e D5.
+Rodada 4.2f / 4.2g: Testes de unidade e integracao para decouple_stdin_from_fd0().
+Cobre requisitos D1, D2, D3 e D4.
 """
 from __future__ import annotations
 
+import importlib.util
 import logging
 import os
 import subprocess
@@ -94,6 +95,8 @@ def test_d1_subprocess_decouple_windows():
     """D1: Subprocesso real no Windows desacopla fd 0 e leitor continua funcional."""
     if sys.platform != "win32":
         pytest.skip("D1 e exclusivo do ambiente Windows (verificacao de deadlock em fd 0 / CRT)")
+    if importlib.util.find_spec("scipy") is None or importlib.util.find_spec("scipy.special") is None:
+        pytest.skip("D1 requer scipy.special instalado para exercitar o gatilho do travamento no Windows")
 
     code = CHILD_D1_SCRIPT.replace("{repo_root}", str(REPO_ROOT))
     env = os.environ.copy()
@@ -204,14 +207,3 @@ def test_d4_main_wiring(monkeypatch):
     main.main()
     assert len(called) == 0, "Nao deve chamar decouple_stdin_from_fd0 com transport=sse"
 
-
-def test_d5_lazy_ml_imports_remain_green():
-    """D5: Verifica que os testes T1 e T2 de test_lazy_ml_imports.py continuam passando."""
-    res = subprocess.run(
-        [sys.executable, "-m", "pytest", "tests/test_lazy_ml_imports.py", "-k", "test_t1 or test_t2", "-q"],
-        capture_output=True,
-        text=True,
-        cwd=str(REPO_ROOT),
-    )
-    assert res.returncode == 0, f"T1/T2 falharam: {res.stdout}\n{res.stderr}"
-    assert "2 passed" in res.stdout
warning: in the working copy of 'tests/test_stdin_decouple.py', LF will be replaced by CRLF the next time Git touches it
```
#### 2.4 Item 1d — VERDE no `venv_min_no_ml` (D1 skip explícito por ausência de `scipy.special`, D2–D4 passam)
```text
s...                                                                     [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_stdin_decouple.py:99: D1 requer scipy.special instalado para exercitar o gatilho do travamento no Windows
3 passed, 1 skipped in 0.10s
```
#### 2.5 Item 1e — VERDE no venv principal Windows (D1–D4 passam, zero skips)
```text
....                                                                     [100%]
4 passed in 3.32s
```

---

### 3. ITEM 2 — REESCRITA DA DOCSTRING EM `main.py` E PROVA DE AST IDÊNTICO
```text
=== PROVA DE AST IDENTICO EM main.py (ITEM 2) ===
Comparacao: ast.dump(include_attributes=False) sem docstrings entre 21610d8:main.py e 5b173fd:main.py
Resultado: AST IDÊNTICO (zero linhas de código executável alteradas)
Tamanho do ast.dump (caracteres): 45631

=== GIT DIFF LITERAL DE main.py (21610d8..5b173fd) ===
diff --git a/main.py b/main.py
index abf519e..03683e4 100644
--- a/main.py
+++ b/main.py
@@ -109,13 +109,15 @@ logger = logging.getLogger("grafo-concierge.main")
 
 
 def decouple_stdin_from_fd0() -> bool:
-    """Decouples fd 0 from sys.stdin on Windows to prevent CRT/OpenBLAS hang.
-
-    On Windows, late imports (e.g. scipy.special / OpenBLAS) acquire an internal CRT
-    file lock on open stdio descriptors. If a background reader thread is blocked
-    in sys.stdin.buffer.readline() on fd 0, LoadLibraryExW hangs permanently.
-    Redirecting fd 0 to os.devnull and wrapping the duplicated fd2 into sys.stdin
-    avoids the lock collision while preserving bidirectional MCP stdio communication.
+    """Desacopla o fd 0 de sys.stdin no Windows para evitar travamento em imports nativos tardios.
+
+    - PROVADO (ver scratch/evidencia_4_2e e scratch/evidencia_4_2f): com um leitor
+      bloqueado em fd 0 do stdin (ex.: sys.stdin.buffer.readline()), o primeiro
+      import de bibliotecas nativas (scipy.special, openblas, torch) trava no
+      Windows; desacoplar o fd 0 (redirecionando fd 0 para os.devnull e envolvendo
+      o descritor duplicado fd2 em sys.stdin) elimina o travamento preservando o
+      canal stdio bidirecional do MCP.
+    - HIPÓTESE NÃO DEMONSTRADA: o mecanismo interno do Windows (lock do CRT / loader).
     """
     if sys.platform != "win32":
         return False
```

---

### 4. ITEM 3 — E2E EM `mcp 1.30.0` COMPLETO E CONTROLE NEGATIVO `dd92d35`
#### 4.1 Item 3a — Verificação de `mcp==1.30.0` e dependências completas (`venv_mcp130_full`)
```text
=== PIP SHOW MCP (venv_mcp130_full) ===
Name: mcp
Version: 1.30.0
Summary: Model Context Protocol SDK
Home-page: https://modelcontextprotocol.io
Author: Anthropic, PBC.
Author-email: 
License: MIT
Location: C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Lib\site-packages
Requires: anyio, httpx, httpx-sse, jsonschema, pydantic, pydantic-settings, pyjwt, python-multipart, pywin32, sse-starlette, starlette, typing-extensions, typing-inspection, uvicorn
Required-by:

=== RUNTIME IMPORT & VERSIONS CHECK ===
{'mcp': '1.30.0', 'chromadb': '1.5.9', 'sentence-transformers': '5.4.1', 'scipy': '1.17.1', 'numpy': '2.4.4', 'torch': '2.11.0'}
mcp.__file__ = C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Lib\site-packages\mcp\__init__.py

=== PIP FREEZE (venv_mcp130_full) ===
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
attrs==26.1.0
bcrypt==5.0.0
beautifulsoup4==4.15.0
build==1.5.0
certifi==2026.4.22
cffi==2.0.0
charset-normalizer==3.4.7
chromadb==1.5.9
click==8.3.3
colorama==0.4.6
coverage==7.16.2
cryptography==48.0.0
distro==1.9.0
docutils==0.23
durationpy==0.10
et_xmlfile==2.0.0
fastapi==0.141.1
filelock==3.29.0
flake8==7.3.0
flatbuffers==25.12.19
fsspec==2026.4.0
google-ai-generativelanguage==0.6.15
google-api-core==2.25.2
google-api-python-client==2.198.0
google-auth==2.62.0
google-auth-httplib2==0.4.0
google-genai==2.34.0
google-generativeai==0.8.6
googleapis-common-protos==1.74.0
grpcio==1.80.0
grpcio-status==1.71.2
h11==0.16.0
h2==4.4.1
hf-xet==1.4.3
hpack==4.2.0
httpcore==1.0.9
httplib2==0.32.0
httptools==0.7.1
httpx==0.28.1
httpx-sse==0.4.3
huggingface_hub==1.13.0
hyperframe==6.1.0
id==1.6.1
idna==3.13
importlib_metadata==8.7.1
importlib_resources==7.1.0
iniconfig==2.3.0
jaraco.classes==3.4.0
jaraco.context==6.1.2
jaraco.functools==4.6.0
Jinja2==3.1.6
jiter==0.16.0
joblib==1.5.3
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
keyring==25.7.0
kubernetes==35.0.0
librt==0.9.0
lxml==6.1.1
markdown-it-py==4.0.0
MarkupSafe==3.0.3
mccabe==0.7.0
mcp==1.30.0
mdurl==0.1.2
mmh3==5.2.1
more-itertools==11.1.0
mpmath==1.3.0
mypy==1.20.2
mypy_extensions==1.1.0
networkx==3.6.1
nh3==0.3.6
numpy==2.4.4
oauthlib==3.3.1
onnxruntime==1.25.1
openai==2.44.0
openpyxl==3.1.5
opentelemetry-api==1.41.1
opentelemetry-exporter-otlp-proto-common==1.41.1
opentelemetry-exporter-otlp-proto-grpc==1.41.1
opentelemetry-proto==1.41.1
opentelemetry-sdk==1.41.1
opentelemetry-semantic-conventions==0.62b1
orjson==3.11.8
overrides==7.7.0
packaging==26.2
pandas==3.0.3
pathspec==1.1.1
pdf2image==1.17.0
pillow==12.2.0
pluggy==1.6.0
portalocker==4.4.2
proto-plus==1.28.1
protobuf==5.29.6
psutil==7.2.2
pyasn1==0.6.4
pyasn1_modules==0.4.2
pybase64==1.4.3
pycodestyle==2.14.0
pycparser==3.0
pydantic==2.13.3
pydantic-settings==2.14.0
pydantic_core==2.46.3
pyflakes==3.4.0
Pygments==2.20.0
PyJWT==2.12.1
pyparsing==3.3.2
pypdf==6.13.2
PyPika==0.51.1
pyproject_hooks==1.2.0
pytesseract==0.3.13
pytest==9.1.1
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.2
python-multipart==0.0.27
pywin32==311
pywin32-ctypes==0.2.3
PyYAML==6.0.3
qdrant-client==1.20.0
readme_renderer==45.0
referencing==0.37.0
regex==2026.4.4
requests==2.33.1
requests-oauthlib==2.0.0
requests-toolbelt==1.0.0
responses==0.26.1
rfc3986==2.0.0
rich==15.0.0
rpds-py==0.30.0
safetensors==0.7.0
scikit-learn==1.8.0
scipy==1.17.1
sentence-transformers==5.4.1
setuptools==81.0.0
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
soupsieve==2.8.4
sse-starlette==3.4.1
starlette==1.0.0
sympy==1.14.0
tenacity==9.1.4
threadpoolctl==3.6.0
tokenizers==0.22.2
torch==2.11.0
tqdm==4.67.3
transformers==5.7.0
tree-sitter==0.25.2
tree-sitter-go==0.25.0
tree-sitter-javascript==0.25.0
tree-sitter-python==0.25.0
tree-sitter-rust==0.24.2
tree-sitter-typescript==0.23.2
twine==6.2.0
typer==0.25.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2026.2
uritemplate==4.2.0
urllib3==2.6.3
uvicorn==0.46.0
watchdog==6.0.0
watchfiles==1.1.1
websocket-client==1.9.0
websockets==16.0
whatthepatch==1.0.7
zipp==3.23.1
```
#### 4.2 Item 3b — Exemplo de `result.json` com versões, checagem de `NO-OP` e contagem de vetores (`count_embeddings`)
```json
{
  "commit": "5b173fd",
  "venv": "mcp_1_30_0_full",
  "python": "C:\\Nexus-Memory\\_venvs_4_2g\\venv_mcp130_full\\Scripts\\python.exe",
  "versions": {
    "mcp": "1.30.0",
    "chromadb": "1.5.9",
    "sentence_transformers": "5.4.1",
    "scipy": "1.17.1",
    "numpy": "2.4.4",
    "torch": "2.11.0"
  },
  "scenario": "mine",
  "rep": 1,
  "classe": "OK",
  "raw_classe": "OK",
  "t_init": 3.2912,
  "dur_critica": 29.9448,
  "dur_secundaria": 0.0263,
  "seed_vectors": 0,
  "post_mine_vectors": 13,
  "stderr_contains_noop": false,
  "stderr_contains_not_installed": false,
  "cpu_samples": [
    0.0,
    0.3,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0
  ],
  "mean_cpu": 0.04,
  "max_cpu": 0.3,
  "details": "OK"
}
```
#### 4.3 Item 3c — Execução Sequencial no `HEAD` ($n=5$ `search-first` + $n=5$ `mine`) em `mcp 1.30.0` completo
```text
=== TABELA ITEM 3c: E2E NO HEAD COM MCP 1.30.0 COMPLETO (SEM WRAPPER / SEM WARMUP) ===
Data: 2026-11-01 00:03:02
Commit alvo: 5b173fd
Versões no venv: mcp=1.30.0, chromadb=1.5.9, sentence_transformers=5.4.1, scipy=1.17.1, numpy=2.4.4, torch=2.11.0
Total de execuções sequenciais: 10 (2 cenários x 5 repetições)

Commit     | Cenário       | Rep | Classe   | t_init(s) | t_crit(s)  | t_sec(s)  | Vetores | NO-OP | not_inst | CPU(%)
----------------------------------------------------------------------------------------------------------------------
5b173fd    | search-first  | 1   | OK       | 2.97      | 12.93      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | search-first  | 2   | OK       | 2.88      | 14.23      | 0.01      | 13      | False | False    | 0.0   
5b173fd    | search-first  | 3   | OK       | 2.73      | 13.38      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | search-first  | 4   | OK       | 4.52      | 20.49      | 0.03      | 13      | False | False    | 0.0   
5b173fd    | search-first  | 5   | OK       | 2.87      | 18.33      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | mine          | 1   | OK       | 3.29      | 29.94      | 0.03      | 13      | False | False    | 0.0   
5b173fd    | mine          | 2   | OK       | 3.19      | 28.72      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | mine          | 3   | OK       | 2.83      | 20.66      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | mine          | 4   | OK       | 2.85      | 21.13      | 0.02      | 13      | False | False    | 0.0   
5b173fd    | mine          | 5   | OK       | 3.32      | 21.80      | 0.02      | 13      | False | False    | 0.0   
----------------------------------------------------------------------------------------------------------------------
Resumo: OK=10/10 | TRAVOU=0/10 | INVÁLIDA=0/10 | ERRO=0/10
```
#### 4.4 Item 3d — Controle Negativo no Commit `dd92d35` ($n=3$ `search-first` + $n=3$ `mine`, timeout 180s) no mesmo `venv_mcp130_full`
```text
=== TABELA ITEM 3d: CONTROLE NEGATIVO NO COMMIT dd92d35 COM MCP 1.30.0 COMPLETO ===
Data: 2026-11-01 00:23:07
Commit alvo: dd92d35
Versões no venv: mcp=1.30.0, chromadb=1.5.9, sentence_transformers=5.4.1, scipy=1.17.1, numpy=2.4.4, torch=2.11.0
Total de execuções sequenciais: 6 (2 cenários x 3 repetições)

Commit     | Cenário       | Rep | Classe   | t_init(s) | t_crit(s)  | t_sec(s)  | Vetores | NO-OP | not_inst | CPU(%)
----------------------------------------------------------------------------------------------------------------------
dd92d35    | search-first  | 1   | TRAVOU   | 2.49      | 180.01     | N/A       | 0       | False | False    | 0.0   
dd92d35    | search-first  | 2   | TRAVOU   | 2.40      | 180.00     | N/A       | 0       | False | False    | 0.0   
dd92d35    | search-first  | 3   | TRAVOU   | 3.07      | 180.00     | N/A       | 0       | False | False    | 0.0   
dd92d35    | mine          | 1   | TRAVOU   | 3.12      | 180.01     | N/A       | 0       | False | False    | 0.0   
dd92d35    | mine          | 2   | TRAVOU   | 2.81      | 180.01     | N/A       | 0       | False | False    | 0.0   
dd92d35    | mine          | 3   | TRAVOU   | 2.88      | 180.01     | N/A       | 0       | False | False    | 0.0   
----------------------------------------------------------------------------------------------------------------------
Resumo: OK=0/6 | TRAVOU=6/6 | INVÁLIDA=0/6 | ERRO=0/6
```
#### 4.5 Item 3e — Rastreabilidade: `pip freeze` do `venv_mcp127` utilizado na Rodada 4.2f
```text
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
attrs==26.1.0
bcrypt==5.0.0
beautifulsoup4==4.15.0
build==1.5.0
certifi==2026.4.22
cffi==2.0.0
charset-normalizer==3.4.7
chromadb==1.5.9
click==8.3.3
colorama==0.4.6
coverage==7.16.2
cryptography==48.0.0
distro==1.9.0
docutils==0.23
durationpy==0.10
et_xmlfile==2.0.0
fastapi==0.141.1
filelock==3.29.0
flake8==7.3.0
flatbuffers==25.12.19
fsspec==2026.4.0
google-ai-generativelanguage==0.6.15
google-api-core==2.25.2
google-api-python-client==2.198.0
google-auth==2.55.2
google-auth-httplib2==0.4.0
google-generativeai==0.8.6
googleapis-common-protos==1.74.0
grpcio==1.80.0
grpcio-status==1.71.2
h11==0.16.0
hf-xet==1.4.3
httpcore==1.0.9
httplib2==0.32.0
httptools==0.7.1
httpx==0.28.1
httpx-sse==0.4.3
huggingface_hub==1.13.0
id==1.6.1
idna==3.13
importlib_metadata==8.7.1
importlib_resources==7.1.0
iniconfig==2.3.0
jaraco.classes==3.4.0
jaraco.context==6.1.2
jaraco.functools==4.6.0
Jinja2==3.1.6
jiter==0.16.0
joblib==1.5.3
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
keyring==25.7.0
kubernetes==35.0.0
librt==0.9.0
lxml==6.1.1
markdown-it-py==4.0.0
MarkupSafe==3.0.3
mccabe==0.7.0
mcp==1.27.0
mdurl==0.1.2
mmh3==5.2.1
more-itertools==11.1.0
mpmath==1.3.0
mypy==1.20.2
mypy_extensions==1.1.0
networkx==3.6.1
nh3==0.3.6
numpy==2.4.4
oauthlib==3.3.1
onnxruntime==1.25.1
openai==2.44.0
openpyxl==3.1.5
opentelemetry-api==1.41.1
opentelemetry-exporter-otlp-proto-common==1.41.1
opentelemetry-exporter-otlp-proto-grpc==1.41.1
opentelemetry-proto==1.41.1
opentelemetry-sdk==1.41.1
opentelemetry-semantic-conventions==0.62b1
orjson==3.11.8
overrides==7.7.0
packaging==26.2
pandas==3.0.3
pathspec==1.1.1
pdf2image==1.17.0
pillow==12.2.0
pluggy==1.6.0
proto-plus==1.28.1
protobuf==5.29.6
psutil==7.2.2
pyasn1==0.6.4
pyasn1_modules==0.4.2
pybase64==1.4.3
pycodestyle==2.14.0
pycparser==3.0
pydantic==2.13.3
pydantic-settings==2.14.0
pydantic_core==2.46.3
pyflakes==3.4.0
Pygments==2.20.0
PyJWT==2.12.1
pyparsing==3.3.2
pypdf==6.13.2
PyPika==0.51.1
pyproject_hooks==1.2.0
pytesseract==0.3.13
pytest==9.1.1
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.2
python-multipart==0.0.27
pywin32==311
pywin32-ctypes==0.2.3
PyYAML==6.0.3
readme_renderer==45.0
referencing==0.37.0
regex==2026.4.4
requests==2.33.1
requests-oauthlib==2.0.0
requests-toolbelt==1.0.0
responses==0.26.1
rfc3986==2.0.0
rich==15.0.0
rpds-py==0.30.0
safetensors==0.7.0
scikit-learn==1.8.0
scipy==1.17.1
sentence-transformers==5.4.1
setuptools==81.0.0
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
soupsieve==2.8.4
sse-starlette==3.4.1
starlette==1.0.0
sympy==1.14.0
tenacity==9.1.4
threadpoolctl==3.6.0
tokenizers==0.22.2
torch==2.11.0
tqdm==4.67.3
transformers==5.7.0
tree-sitter==0.25.2
tree-sitter-go==0.25.0
tree-sitter-javascript==0.25.0
tree-sitter-python==0.25.0
tree-sitter-rust==0.24.2
tree-sitter-typescript==0.23.2
twine==6.2.0
typer==0.25.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2026.2
uritemplate==4.2.0
urllib3==2.6.3
uvicorn==0.46.0
watchdog==6.0.0
watchfiles==1.1.1
websocket-client==1.9.0
websockets==16.0
whatthepatch==1.0.7
zipp==3.23.1
```

---

### 5. ITEM 4 — CI WINDOWS (`.github/workflows/windows-stdin.yml`) E MUTAÇÃO NO CI
#### 5.1 Item 4b — Workflow `.github/workflows/windows-stdin.yml` (Commit `30d65c1`)
```yaml
name: Windows Stdin Decouple & Lazy ML Imports

on:
  push:
    branches:
      - main
      - "ci-mutacao-*"
  pull_request:
    branches:
      - main
  workflow_dispatch:

jobs:
  windows-stdin-tests:
    name: Windows (${{ matrix.python-version }})
    runs-on: windows-latest
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12", "3.14"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          allow-prereleases: true
          cache: "pip"

      - name: Upgrade pip and install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt scipy

      - name: Run stdin decouple and lazy ML import tests
        run: |
          pytest tests/test_stdin_decouple.py tests/test_lazy_ml_imports.py -v -rs
```
#### 5.2 Item 4c — Resultado Real da Matriz no GitHub Actions (`main`, Python 3.10, 3.12 e 3.14)
```text
gh CLI path: NAO INSTALADO NO PATH
Consultando GitHub REST API pública para LuisinTheLegend/ConciergeGraph (commit prefix: 30d65c1)...

Run ID: 41267621956
Workflow: Windows Stdin Decouple & Lazy ML Imports
Branch: main
Head SHA: 30d65c1d859858b8407f8bb0d72f14c7732c1688
Status: completed | Conclusion: success
URL: https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/41267621956

Jobs da Matriz:
  - Job: Windows (3.10) | status=completed | conclusion=success | started=2026-11-01T03:03:35Z | completed=2026-11-01T03:07:18Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.10: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=success
      step [9] Post Set up Python 3.10: status=completed, conclusion=success
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success
  - Job: Windows (3.14) | status=completed | conclusion=success | started=2026-11-01T03:03:35Z | completed=2026-11-01T03:06:39Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.14: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=success
      step [9] Post Set up Python 3.14: status=completed, conclusion=success
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success
  - Job: Windows (3.12) | status=completed | conclusion=success | started=2026-11-01T03:03:35Z | completed=2026-11-01T03:09:22Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.12: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=success
      step [9] Post Set up Python 3.12: status=completed, conclusion=success
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success
```
#### 5.3 Item 4d — Mutação no CI (Remoção de `os.dup2(nul, 0)` na branch descartável `ci-mutacao-4-2g`)
```text
=== ITEM 4d: MUTACAO NO CI WINDOWS (BRANCH DESCARTAVEL ci-mutacao-4-2g) ===
Mutacao aplicada: remocao de `os.dup2(nul, 0)` em `decouple_stdin_from_fd0()` de `main.py`

=== GIT DIFF DA MUTACAO NA BRANCH ci-mutacao-4-2g ===
diff --git a/main.py b/main.py
index 03683e4..c604d7b 100644
--- a/main.py
+++ b/main.py
@@ -130,7 +130,6 @@ def decouple_stdin_from_fd0() -> bool:
     try:
         nul = os.open(os.devnull, os.O_RDONLY)
         fd2 = os.dup(0)
-        os.dup2(nul, 0)
         os.close(nul)
         nul = -1
         sys.stdin = open(fd2, "r", encoding="utf-8", errors="replace", closefd=False)

=== RESULTADO DO WORKFLOW NO GITHUB ACTIONS (MUTACAO SEM os.dup2(nul, 0)) ===
Run ID: 41269127942
Workflow: Windows Stdin Decouple & Lazy ML Imports
Branch: ci-mutacao-4-2g
Head SHA: 4fe080302db85b130fdf50e6e08a5cfb47f73ef9
Status: completed | Conclusion: failure
URL: https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/41269127942

Jobs da Matriz:
  - Job: Windows (3.12) | status=completed | conclusion=failure | started=2026-11-01T03:25:46Z | completed=2026-11-01T03:29:36Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.12: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=failure
      step [9] Post Set up Python 3.12: status=completed, conclusion=skipped
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success
  - Job: Windows (3.10) | status=completed | conclusion=failure | started=2026-11-01T03:25:42Z | completed=2026-11-01T03:29:24Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.10: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=failure
      step [9] Post Set up Python 3.10: status=completed, conclusion=skipped
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success
  - Job: Windows (3.14) | status=completed | conclusion=failure | started=2026-11-01T03:25:41Z | completed=2026-11-01T03:29:11Z
      step [1] Set up job: status=completed, conclusion=success
      step [2] Checkout repository: status=completed, conclusion=success
      step [3] Set up Python 3.14: status=completed, conclusion=success
      step [4] Upgrade pip and install dependencies: status=completed, conclusion=success
      step [5] Run stdin decouple and lazy ML import tests: status=completed, conclusion=failure
      step [9] Post Set up Python 3.14: status=completed, conclusion=skipped
      step [10] Post Checkout repository: status=completed, conclusion=success
      step [11] Complete job: status=completed, conclusion=success

=== LIMPEZA DA BRANCH DESCARTAVEL ===
git push origin --delete ci-mutacao-4-2g: To https://github.com/LuisinTheLegend/ConciergeGraph.git
 - [deleted]         ci-mutacao-4-2g
git branch -D ci-mutacao-4-2g: Deleted branch ci-mutacao-4-2g (was 4fe0803).
Branch ativa apos limpeza: main (HEAD=30d65c1d859858b8407f8bb0d72f14c7732c1688)
```

---

### 6. ERRATA DA RODADA 4.2f (`audits/errata-4-2f.md`)
```markdown
# Errata da Rodada 4.2f (`audits/relatorio_4_2f.md`)

> **Data:** 2026-10-31  
> **Referência:** Auditoria independente do commit `21610d8` (Rodada 4.2f) e correções aplicadas na Rodada 4.2g.

---

## 1. Execução E2E do Passo 4e em `mcp 1.30.0` rodou sem `chromadb` (modo `NO-OP`)

- **O que foi afirmado na 4.2f:** O relatório da 4.2f afirmou que o teste definitivo E2E (Passo 4e) obteve `20/20 OK` exercitando o caminho completo tanto em `mcp 1.27.0` quanto em `mcp 1.30.0`.
- **Correção factual:** O resultado `20/20` da 4.2f valia plenamente **apenas para as 10 execuções em `mcp 1.27.0`** (`venv_mcp127`, onde `chromadb` estava instalado e a mineração levou ~32–34 s). No ambiente `venv_mcp130_real` (`mcp 1.30.0`), o pacote `chromadb` não estava instalado (`WARNING | chromadb not installed` e `WARNING | ChromaVectorStore operating in NO-OP mode`, visível em `scratch/evidencia_4_2f/boot_check_mcp130.txt`), o que reduziu a carga e o tempo de mineração para ~10 s e não exercitou o armazenamento vetorial real no Chroma.
- **Resolução na 4.2g (Item 3):** Criado `venv_mcp130_full` com `mcp==1.30.0` e todas as dependências do projeto (`chromadb`, `sentence-transformers`, `scipy`, `numpy`, `torch`), validando em cada `result.json` as versões instaladas, a ausência de `"NO-OP"` / `"not installed"` no `stderr`, a contagem real de vetores (`count_embeddings > 0`) após `mine`, e o controle negativo no commit `dd92d35`.

---

## 2. Fragilidade do Teste `D5` em `tests/test_stdin_decouple.py`

- **O que ocorria na 4.2f:** O teste `test_d5_lazy_ml_imports_remain_green` (D5) invocava `pytest tests/test_lazy_ml_imports.py -k "test_t1 or test_t2" -q` em subprocesso e exigia literalmente `assert "2 passed" in res.stdout`. Em qualquer ambiente sem `sentence_transformers` instalado, `T1` e `T2` são legitimamente pulados (`2 skipped`), fazendo o `D5` falhar por asserção de string.
- **Resolução na 4.2g (Item 1):** Reproduzida a falha em venv limpo sem `sentence_transformers` (`scratch/evidencia_4_2g/item1_d5_red.txt`) e removido o `D5` de `tests/test_stdin_decouple.py` (pois apenas duplicava `T1`/`T2`, que já fazem parte de `tests/test_lazy_ml_imports.py`), adicionando também guarda de skip explícita em `D1` quando `scipy.special` não está instalado.

---

## 3. Docstring de `decouple_stdin_from_fd0` em `main.py` afirmava mecanismo interno como fato

- **O que ocorria na 4.2f:** A docstring de `decouple_stdin_from_fd0()` em `main.py` continha a afirmação `"acquire an internal CRT file lock on open stdio descriptors"`, apresentando como fato provado um mecanismo interno do Windows/CRT que não foi demonstrado diretamente.
- **Resolução na 4.2g (Item 2):** A docstring em `main.py` foi reescrita separando explicitamente o que está **PROVADO** (`scratch/evidencia_4_2e` e `scratch/evidencia_4_2f`: com leitor bloqueado em `fd 0` do `stdin`, o primeiro import de bibliotecas nativas como `scipy.special`, `openblas` e `torch` trava no Windows, e desacoplar o `fd 0` elimina o travamento) do que permanece **HIPÓTESE NÃO DEMONSTRADA** (o mecanismo interno de lock do CRT / loader do Windows). Provado via `ast.dump` sem docstrings (`scratch/evidencia_4_2g/item2_ast_proof.txt`) que zero linhas de código executável mudaram em `main.py`.
```

---

### 7. O QUE NÃO FOI VERIFICADO (LIMITES DECLARADOS)
1. **Outras máquinas físicas e ambientes de SO/hardware:** Os testes locais de reprodução do deadlock (como o controle negativo `dd92d35` e a mutação sem `os.dup2(nul, 0)`) foram verificados na estação Windows 10.0.26300 do executor; máquinas com diferentes versões de sistema operacional, drivers ou políticas de segurança podem apresentar comportamento distinto.
2. **Cliente Claude Desktop real:** As validações E2E utilizaram o cliente oficial `mcp.client.stdio.stdio_client` (`ClientSession`) via STDIO. O teste interativo no aplicativo **Claude Desktop real** pelo dono do projeto **NÃO FOI VERIFICADO** nesta rodada.
3. **Timeout real do cliente Claude Desktop:** O limite exato de timeout de inicialização/chamada do cliente Claude Desktop **NÃO FOI VERIFICADO** (não especificado oficialmente na documentação do protocolo MCP).
4. **Status dos Achados F4-015 e F4-017:** Mantidos estritamente como `corrigido pelo executor, aguardando verificação independente` em `audits/fase4-roadmap.md` e `audits/fase4-achados.md`.
