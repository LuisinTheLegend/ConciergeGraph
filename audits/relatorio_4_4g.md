# Relatório da Rodada 4.4g — `chromadb` Intermitente em `stress_components` (`F4-034`)

- **Data:** 2026-11-12
- **Base da Rodada:** `26a43e2723488f5206c12f639c0a94a7ba3c483d` (`26a43e2`)
- **HEAD no momento da geração:** `c1eefbaa3858e5db6d8a49d590a54583166e621b`
- **Status do achado `F4-034`:** **aberto, causa não provada**
- **Natureza da Rodada:** Mini-rodada exclusiva de testes e documentação. **Zero alterações** em código de produto (`core/`, `storage/`, `ingestion/`, `interface/`, `services/`, `main.py`).
- **Regra 15 (EGM):** Não utilizado nesta rodada (sem código de produto modificado e sem alteração irreversível).
- **Gerado por script (Regra 12):** `scratch/generate_relatorio_4_4g.py`

---

## 1. Bloco 1 — Investigação na Base `26a43e2` (Sem Alterações no Código de Teste)

### 1.1 Fato do CI em `3dccf68` (Fonte Fornecida + API Pública do GitHub Actions)

- No CI de `3dccf68`, workflow run `43075938190`, job `Test (Python 3.10)` (`id=130715647420`), ocorreu `ERROR at setup of test_lightweight_mode_behavior` em **um único processo sequencial**, com a pilha:
  - `tests/conftest.py:14 stress_components` → `tests/memory_stress_test.py:265 bootstrap` → `storage/vector_store.py:321 get_or_create_collection` → `chromadb.errors.InternalError: ... (code: 1) no such table: acquire_write` (`473 passed, 1 skipped, 1 xfailed, 1 error`).
- Metadados públicos do job `130715647420` confirmam falha do step 7 (`Run tests with pytest`) em `2026-11-11T18:18:15Z`; os logs brutos do job via API pública retornaram `HTTP 403` sem autenticação.

### 1.2 Tentativa de Reprodução Sequencial: 30 Execuções Py3.10 + 30 Execuções Py3.12 (`0/60`)

- **Conclusão empírica:** **não reproduzido em 60 execuções (30 Py3.10 + 30 Py3.12)**. Todas as 60 execuções fecharam com `475 passed, 1 xfailed` (`0` erros de `chromadb`, `0` falhas).

#### Evidência: `scratch/evidencia_4_4g/bloco1_30x_results.txt:1-8, 36-42, 69-74`

```text
1: === BLOCO 1 (RODADA 4.4g): REPRODUÇÃO EM 30+30 EXECUÇÕES SEQUENCIAIS (ESTADO 26a43e2) ===
2: Comando: <python> -m pytest -v --tb=short (ordem normal, env: TOKENIZERS_PARALLELISM=false, GRAFO_LIGHTWEIGHT_MODE=false, HF_HUB_OFFLINE=1)
3: Interpretador Py3.10: Python=3.10.22 (main, Oct  9 2026, 15:18:58) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0
4: Interpretador Py3.12: Python=3.12.16 (main, Oct 26 2026, 14:10:56) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0
5: 
6: --- Execuções em py310 (30x) ---
7:   [py310 01/30] PASS (102.65s) | ============ 475 passed, 1 xfailed, 4 warnings in 97.34s (0:01:37) ============
8:   [py310 02/30] PASS (98.76s) | ============ 475 passed, 1 xfailed, 4 warnings in 93.79s (0:01:33) ============
...
36:   [py310 30/30] PASS (100.65s) | ============ 475 passed, 1 xfailed, 4 warnings in 95.58s (0:01:35) ============
37: => Resumo py310: total=30, chromadb_InternalError=0, outros_erros=0, total_falhas=0
38: 
39: --- Execuções em py312 (30x) ---
40:   [py312 01/30] PASS (100.47s) | =========== 475 passed, 1 xfailed, 21 warnings in 94.78s (0:01:34) ============
41:   [py312 02/30] PASS (94.87s) | =========== 475 passed, 1 xfailed, 21 warnings in 89.38s (0:01:29) ============
42:   [py312 03/30] PASS (94.95s) | =========== 475 passed, 1 xfailed, 21 warnings in 89.48s (0:01:29) ============
...
69:   [py312 30/30] PASS (95.16s) | =========== 475 passed, 1 xfailed, 21 warnings in 89.63s (0:01:29) ============
70: => Resumo py312: total=30, chromadb_InternalError=0, outros_erros=0, total_falhas=0
71: 
72: === CONSOLIDADO FINAL BLOCO 1 ===
73:   py310: 0/30 chromadb InternalError | 0/30 outros erros | 0/30 falhas totais
74:   py312: 0/30 chromadb InternalError | 0/30 outros erros | 0/30 falhas totais
```

### 1.3 Ordem de Coleta, Consumidores Reais e `--setup-plan`

- `pyproject.toml:117-118` configura `testpaths = ["tests"]` e `python_files = ["test_*.py", "*_test.py"]`, fazendo `pytest -v --tb=short` (`.github/workflows/ci.yml:50`) coletar automaticamente `tests/memory_stress_test.py` e os demais módulos `test_*.py`.
- Na ordem normal, `tests/test_lightweight.py` (`37/59`) roda após 3 ciclos anteriores de `SETUP M` / `TEARDOWN M stress_components` (`01. tests/memory_stress_test.py`, `09. tests/test_chunk_cache.py`, `32. tests/test_ignore.py`). Na ordem `--reverse`, `tests/test_lightweight.py` (`23/59`) passa primeiro.

#### Versões locais e consumidores (`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:3-8` e `10-23`)

```text
3: --- [1] VERSÕES LOCAIS (Python, chromadb, pytest, SharedSystemClient) ---
4:   [py310] Python=3.10.22 (main, Oct  9 2026, 15:18:58) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0 | has_clear_system_cache=True
5:   [py311] Python=3.11.18 (main, Oct 26 2026, 14:08:50) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0 | has_clear_system_cache=True
6:   [py312] Python=3.12.16 (main, Oct 26 2026, 14:10:56) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0 | has_clear_system_cache=True
7:   [py313] Python=3.13.18 (main, Oct 26 2026, 14:10:48) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0 | has_clear_system_cache=True
8:   [py314] Python=3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)] | chromadb=1.5.9 | pytest=9.2.0 | has_clear_system_cache=True
...
10: --- [2] FUNÇÕES EM tests/ COM PARÂMETROS DAS FIXTURES DE conftest.py ---
11:   tests/memory_stress_test.py:325 def test_dimension_1(store, vector, embedder, manager)
12:   tests/memory_stress_test.py:410 def test_dimension_2(store, manager)
13:   tests/memory_stress_test.py:445 def test_dimension_3(store, vector, manager, janitor)
14:   tests/memory_stress_test.py:505 def test_dimension_4(store, janitor)
15:   tests/stress_test_v2_parte1.py:18 def test_dim1(store, vector, embedder)
16:   tests/stress_test_v2_parte1.py:169 def test_dim2(store, vector, embedder, manager)
17:   tests/stress_test_v2_parte1.py:231 def test_dim3(store, vector, embedder)
18:   tests/stress_test_v2_parte2.py:205 def test_dim5(store)
19:   tests/stress_test_v2_parte2.py:326 def test_dim6(store)
20:   tests/stress_test_v2_parte3.py:147 def test_dim8(store, vector, manager)
21:   tests/test_chunk_cache.py:6 def test_chunk_cache_behavior(store, vector, manager)
22:   tests/test_ignore.py:5 def test_safe_ignore_behavior(store, manager)
23:   tests/test_lightweight.py:10 def test_lightweight_mode_behavior(store, manager)
```

#### Plano de setup/teardown de `stress_components` (`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:86-119`)

```text
86: --- [4] ORDEM NORMAL: EVENTOS SETUP/TEARDOWN DE stress_components EM pytest --setup-plan ---
87:   tests\memory_stress_test.py
88:       SETUP    M stress_components
89:       SETUP    M store (fixtures used: stress_components)
90:       SETUP    M vector (fixtures used: stress_components)
91:       SETUP    M embedder (fixtures used: stress_components)
92:       SETUP    M manager (fixtures used: stress_components)
93:           tests/memory_stress_test.py::test_dimension_1 (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, embedder, manager, store, stress_components, vector)
94:           tests/memory_stress_test.py::test_dimension_2 (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, manager, store, stress_components)
95:       SETUP    M janitor (fixtures used: stress_components)
96:           tests/memory_stress_test.py::test_dimension_3 (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, janitor, manager, store, stress_components, vector)
97:           tests/memory_stress_test.py::test_dimension_4 (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, janitor, store, stress_components)
98:       TEARDOWN M stress_components
99:   tests\test_chunk_cache.py
100:       SETUP    M stress_components
101:       SETUP    M store (fixtures used: stress_components)
102:       SETUP    M vector (fixtures used: stress_components)
103:       SETUP    M manager (fixtures used: stress_components)
104:           tests/test_chunk_cache.py::test_chunk_cache_behavior (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, manager, store, stress_components, vector)
105:       TEARDOWN M stress_components
106:           tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_docstring_mutations (fixtures used: _unittest_setUpClass_fixture_TestDeltaSyncDrift, check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, request)
107:           tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_formatting_and_comments (fixtures used: _unittest_setUpClass_fixture_TestDeltaSyncDrift, check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, request)
108:   tests\test_ignore.py
109:       SETUP    M stress_components
110:       SETUP    M store (fixtures used: stress_components)
111:       SETUP    M manager (fixtures used: stress_components)
112:           tests/test_ignore.py::test_safe_ignore_behavior (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, manager, store, stress_components)
113:       TEARDOWN M stress_components
114:   tests\test_lightweight.py
115:       SETUP    M stress_components
116:       SETUP    M store (fixtures used: stress_components)
117:       SETUP    M manager (fixtures used: stress_components)
118:           tests/test_lightweight.py::test_lightweight_mode_behavior (fixtures used: check_mcp_globals_leak_class, check_mcp_globals_leak_function, check_mcp_globals_leak_module, manager, request, store, stress_components, tmp_path, tmp_path_factory)
119:       TEARDOWN M stress_components
```

### 1.4 Versões de `chromadb` e Sonda Local no Windows vs. Linux (Hipótese Não Provada)

- **Fato observado na sonda mínima Windows (`scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt:1-12`):** Ao tentar `shutil.rmtree` sobre diretório com `PersistentClient` vivo, o Windows levanta `PermissionError: [WinError 32]` porque `chroma.sqlite3` está bloqueado pelo processo. Com `ignore_errors=True` (`tests/conftest.py:22`), `chroma.sqlite3` permanece no disco (`sqlite_remained_after_ignore_errors=True`), e o segundo cliente abre sem erro (`c2_err=None` em `3/3` Py3.10 + `3/3` Py3.12).
- **Contraste com o Linux:** Na sonda do auditor em Linux (`chromadb 1.5.9`), o mesmo padrão levantou `InternalError ... (code: 1032) attempt to write a readonly database` (`6/6`), que também difere da mensagem do CI (`(code: 1) no such table: acquire_write`).
- **HIPÓTESE (não provada):** A semântica de exclusão de arquivos abertos (`unlink` em POSIX vs. `[WinError 32]` no Windows) pode influenciar a não reprodução no Windows, **mas a causa raiz de `no such table: acquire_write` no CI continua NÃO PROVADA**.

```text
1: === BLOCO 1 (PARTE 3): SONDA LOCAL DE COMPORTAMENTO WINDOWS & CONFIG CI CHROMADB ===
2: 
3: --- Sonda mínima (rmtree no caminho vivo, Windows) em py310 ---
4: trial=1 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_0_ye1ev1zj\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
5: trial=2 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_1_meelm8_z\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
6: trial=3 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_2_3d86730l\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
7: 
8: --- Sonda mínima (rmtree no caminho vivo, Windows) em py312 ---
9: trial=1 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_0_m6bn3wpy\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
10: trial=2 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_1_xqnjsgbi\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
11: trial=3 | rmtree_err=PermissionError: [WinError 32] O arquivo já está sendo usado por outro processo: 'C:\\Users\\guial\\AppData\\Local\\Temp\\chroma_min_probe_2_tzjt4fyj\\chroma.sqlite3' | c2_err=None | sqlite_remained_after_ignore_errors=True
12: 
13: --- Versão de chromadb nos arquivos do projeto vs local ---
14: [pyproject.toml]
15:   37: dependencies = [
16:   38:     "chromadb>=1.0",
17:   39:     "mcp>=1.27,<2",
18:   40:     "sentence-transformers>=3.0",
19: [requirements.txt]
20:   3: # Core System & Framework
21:   4: chromadb>=1.0.0
22:   5: mcp>=1.27,<2
23:   6: sentence-transformers>=3.0.0
24: [.github/workflows/ci.yml]
25:   30:         python-version: ${{ matrix.python-version }}
26:   31:         cache: 'pip'
27:   32:         cache-dependency-path: pyproject.toml
28:   33: 
29:   34:     - name: Prepare test environment
30:   35:       run: |
31:   36:         cp .env.example .env
32:   37: 
33:   38:     - name: Install dependencies
34:   39:       run: |
35:   40:         python -m pip install --upgrade pip
36:   41:         pip install -e .[dev]
37:   42: 
38:   43:     - name: Lint with flake8 (critical errors & syntax)
39:   44:       run: |
40:   45:         # stop the build if there are Python syntax errors or undefined names
41:   46:         flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
42:   47: 
43:   48:     - name: Run tests with pytest
44:   49:       run: |
45:   50:         pytest -v --tb=short
```

---

## 2. Bloco 2 — Endurecimento Defensivo em `tests/memory_stress_test.py::bootstrap()` (Sem Código de Produto)

- Em vez de alterar `storage/vector_store.py`, aplicou-se **apenas endurecimento defensivo em código de teste**: `bootstrap()` passou a isolar cada chamada em um subdiretório exclusivo `run_<uuid4>` dentro de `CHROMA_PATH`, preservando integralmente o símbolo `CHROMA_PATH` e os contratos de importação dos consumidores (`tests/conftest.py:8`, `tests/test_lightweight.py:8`, `tests/test_chunk_cache.py:4`, `tests/test_ignore.py:3`).
- **Limite explícito:** Como `F4-034` não foi reproduzido (`0/60`), **não** afirmamos que esta mudança corrija a causa raiz; trata-se exclusivamente de **endurecimento defensivo** para evitar reuso de `persist_dir`/entrada em `SharedSystemClient` dentro do mesmo processo.

### 2.1 Alteração em `tests/memory_stress_test.py:270-277`

```python
270:     # Endurecimento defensivo (F4-034, causa não provada): subdiretório Chroma exclusivo por chamada
271:     # para evitar que clientes consecutivos no mesmo processo reusem o mesmo persist_dir/SharedSystemClient.
272:     chroma_dir = os.path.join(CHROMA_PATH, f"run_{uuid.uuid4().hex}")
273:     vector = ChromaVectorStore(
274:         persist_dir=chroma_dir,
275:         collection_name="stress_test",
276:         embedding_manager=embedder,
277:     )
```

### 2.2 Consumidores de `stress_components` e Guardas (`test_domain_neutrality_guard.py`, `check_mcp_globals_leak`, `M10d`)

```text
1: === BLOCO 2/3 (RODADA 4.4g): CONSUMIDORES DE stress_components E GUARDAS ===
2: 
3: --- py310 (normal) | RC=0 ---
4: ============================= test session starts =============================
5: platform win32 -- Python 3.10.22, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
6: cachedir: .pytest_cache
7: rootdir: C:\Nexus-Memory\GrafoConcierge
8: configfile: pyproject.toml
9: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
10: timeout: 300.0s
11: timeout method: thread
12: timeout func_only: False
13: collecting ... collected 13 items
14: 
15: tests/memory_stress_test.py::test_dimension_1 PASSED                     [  7%]
16: tests/memory_stress_test.py::test_dimension_2 PASSED                     [ 15%]
17: tests/memory_stress_test.py::test_dimension_3 PASSED                     [ 23%]
18: tests/memory_stress_test.py::test_dimension_4 PASSED                     [ 30%]
19: tests/test_chunk_cache.py::test_chunk_cache_behavior PASSED              [ 38%]
20: tests/test_ignore.py::test_safe_ignore_behavior PASSED                   [ 46%]
21: tests/test_lightweight.py::test_lightweight_mode_behavior PASSED         [ 53%]
22: tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization PASSED [ 61%]
23: tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call PASSED [ 69%]
24: tests/test_domain_neutrality_guard.py::test_g1_concierge_config_has_no_wing_keywords PASSED [ 76%]
25: tests/test_domain_neutrality_guard.py::test_g2_no_retired_domain_strings_in_product_code PASSED [ 84%]
26: tests/test_domain_neutrality_guard.py::test_g3_real_mining_never_alters_primary_wing PASSED [ 92%]
27: tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project PASSED [100%]
28: 
29: ============================= 13 passed in 28.97s =============================
30: 
...
125: ======================= 13 passed, 1 warning in 27.56s ========================
126: 
127: --- Guarda M10d / check_mcp_globals_leak (Py3.12) | RC=0 ---
128: M10d_import: mut1=3, mut2=3, clean=0 -> MORTA (OK)
```

---

## 3. Bloco 3 — Teste de Caracterização, Invariante Estrutural e Mutação Externa

- **Declaração de honestidade (sem teste vermelho para `F4-034`):**
  1. Executado antes do Bloco 2 sobre `26a43e2`, `test_stress_components_reuse_cycle_characterization` **já passava** (`RC=0` em Py3.10 e Py3.12, `scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt`).
  2. Aplicada mutação externa reintroduzindo `persist_dir=CHROMA_PATH` fixo em `bootstrap()`, `test_stress_components_reuse_cycle_characterization` **continua passando** (`RC=0`), comprovando que é estritamente um **teste de caracterização do ciclo de reuso, não prova de correção**.
  3. O segundo teste, `test_bootstrap_uses_distinct_chroma_subdir_per_call`, verifica apenas a invariante estrutural do endurecimento defensivo do Bloco 2 e **falha (`RC=1`) sob a mutação externa**, passando (`RC=0`) sem ela e restaurando `GRAFO_LIGHTWEIGHT_MODE` ao estado original (`None` ou `'true'`).

### 3.1 Baseline sobre `26a43e2` (`scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt:1-35`)

```text
1: === BLOCO 3 (BASE 26a43e2): EXECUÇÃO DO TESTE DE CARACTERIZAÇÃO ANTES DO ENDURECIMENTO ===
2: 
3: --- py310 (base 26a43e2, sem alteração em bootstrap) | ReturnCode=0 ---
4: ============================= test session starts =============================
5: platform win32 -- Python 3.10.22, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
6: cachedir: .pytest_cache
7: rootdir: C:\Nexus-Memory\GrafoConcierge
8: configfile: pyproject.toml
9: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
10: timeout: 300.0s
11: timeout method: thread
12: timeout func_only: False
13: collecting ... collected 1 item
14: 
15: tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization PASSED [100%]
16: 
17: ============================== 1 passed in 0.68s ==============================
18: 
19: --- py312 (base 26a43e2, sem alteração em bootstrap) | ReturnCode=0 ---
20: ============================= test session starts =============================
21: platform win32 -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe
22: cachedir: .pytest_cache
23: rootdir: C:\Nexus-Memory\GrafoConcierge
24: configfile: pyproject.toml
25: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
26: timeout: 300.0s
27: timeout method: thread
28: timeout func_only: False
29: collecting ... collected 1 item
30: 
31: tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization PASSED [100%]
32: 
33: ============================== 1 passed in 0.92s ==============================
34: 
35: Conclusão Bloco 3 (sobre 26a43e2): O teste de caracterização do ciclo de reuso PASSA em 26a43e2 em Py3.10 e Py3.12 (RC=0). Não há teste vermelho reproduzindo o bug F4-034.
```

### 3.2 Testes em `tests/test_stress_components_reuse.py:78-128`

```python
78: def test_stress_components_reuse_cycle_characterization():
79:     """Caracterização do ciclo de reuso, não prova de correção (F4-034 / Bloco 3).
80: 
81:     Executa setup_workspace(), bootstrap() e o teardown de stress_components
82:     duas vezes seguidas no mesmo processo sem GRAFO_LIGHTWEIGHT_MODE,
83:     restaurando o ambiente ao final.
84:     """
85:     prev_lw = os.environ.get("GRAFO_LIGHTWEIGHT_MODE")
86:     os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
87:     try:
88:         _run_one_cycle()
89:         _run_one_cycle()
90:     finally:
91:         if prev_lw is None:
92:             os.environ.pop("GRAFO_LIGHTWEIGHT_MODE", None)
93:         else:
94:             os.environ["GRAFO_LIGHTWEIGHT_MODE"] = prev_lw
95:         try:
96:             shutil.rmtree(TEST_DIR, ignore_errors=True)
97:         except Exception:
98:             pass
99: 
100: 
101: def test_bootstrap_uses_distinct_chroma_subdir_per_call():
102:     """Verifica a invariante estrutural do endurecimento defensivo do Bloco 2 (F4-034).
103: 
104:     Não reproduz nem prova causa do bug intermitente do chromadb; valida apenas que
105:     duas chamadas consecutivas a bootstrap() no mesmo processo utilizam subdiretórios
106:     Chroma exclusivos (e identificadores SharedSystemClient distintos) quando o modo
107:     lightweight está desligado, restaurando o ambiente ao final.
108:     """
109:     prev_lw = os.environ.get("GRAFO_LIGHTWEIGHT_MODE")
110:     os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
111:     try:
112:         id_1, subdirs_1 = _run_one_cycle()
113:         id_2, subdirs_2 = _run_one_cycle()
114: 
115:         assert len(subdirs_1) == 1, f"Esperava 1 subdiretório Chroma exclusivo na 1ª chamada, obteve {subdirs_1}"
116:         assert len(subdirs_2) == 1, f"Esperava 1 subdiretório Chroma exclusivo na 2ª chamada, obteve {subdirs_2}"
117:         assert subdirs_1.isdisjoint(subdirs_2), f"Subdiretórios Chroma colidiram: {subdirs_1} vs {subdirs_2}"
118:         if id_1 is not None and id_2 is not None:
119:             assert id_1 != id_2, f"Identificadores PersistentClient colidiram: {id_1} == {id_2}"
120:     finally:
121:         if prev_lw is None:
122:             os.environ.pop("GRAFO_LIGHTWEIGHT_MODE", None)
123:         else:
124:             os.environ["GRAFO_LIGHTWEIGHT_MODE"] = prev_lw
125:         try:
126:             shutil.rmtree(TEST_DIR, ignore_errors=True)
127:         except Exception:
128:             pass
```

### 3.3 Mutação Externa e Restauração de Ambiente (`scratch/evidencia_4_4g/bloco3_mutation_and_env.txt:1-63`)

```text
1: === BLOCO 3 (RODADA 4.4g): MUTAÇÃO EXTERNA (REINTRODUZIR persist_dir=CHROMA_PATH FIXO EM bootstrap) ===
2: Objetivo: comprovar separadamente (a) o comportamento do teste de caracterização do ciclo de reuso e (b) a proteção estrutural da medida defensiva do Bloco 2.
3: 
4: --- COM MUTAÇÃO | tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization | RC=0 ---
5: ============================= test session starts =============================
6: platform win32 -- Python 3.10.22, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
7: cachedir: .pytest_cache
8: rootdir: C:\Nexus-Memory\GrafoConcierge
9: configfile: pyproject.toml
10: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
11: timeout: 300.0s
12: timeout method: thread
13: timeout func_only: False
14: collecting ... collected 1 item
15: 
16: tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization PASSED [100%]
17: 
18: ============================== 1 passed in 0.62s ==============================
19: 
20: --- COM MUTAÇÃO | tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call | RC=1 ---
21: ============================= test session starts =============================
22: platform win32 -- Python 3.10.22, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
23: cachedir: .pytest_cache
24: rootdir: C:\Nexus-Memory\GrafoConcierge
25: configfile: pyproject.toml
26: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
27: timeout: 300.0s
28: timeout method: thread
29: timeout func_only: False
30: collecting ... collected 1 item
31: 
32: tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call FAILED [100%]
33: 
34: ================================== FAILURES ===================================
35: _____________ test_bootstrap_uses_distinct_chroma_subdir_per_call _____________
36: tests\test_stress_components_reuse.py:115: in test_bootstrap_uses_distinct_chroma_subdir_per_call
37:     assert len(subdirs_1) == 1, f"Esperava 1 subdiretório Chroma exclusivo na 1ª chamada, obteve {subdirs_1}"
38: E   AssertionError: Esperava 1 subdiretório Chroma exclusivo na 1ª chamada, obteve set()
39: E   assert 0 == 1
40: E    +  where 0 = len(set())
41: =========================== short test summary info ===========================
42: FAILED tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call
43: ============================== 1 failed in 1.82s ==============================
44: 
45: --- SEM MUTAÇÃO (código corrigido) | tests/test_stress_components_reuse.py | RC=0 ---
46: ============================= test session starts =============================
47: platform win32 -- Python 3.10.22, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
48: cachedir: .pytest_cache
49: rootdir: C:\Nexus-Memory\GrafoConcierge
50: configfile: pyproject.toml
51: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
52: timeout: 300.0s
53: timeout method: thread
54: timeout func_only: False
55: collecting ... collected 2 items
56: 
57: tests/test_stress_components_reuse.py::test_stress_components_reuse_cycle_characterization PASSED [ 50%]
58: tests/test_stress_components_reuse.py::test_bootstrap_uses_distinct_chroma_subdir_per_call PASSED [100%]
59: 
60: ============================== 2 passed in 1.04s ==============================
61: 
62: --- RESTAURAÇÃO DE AMBIENTE ---
63: Env restoration OK: after_unset=None, after_true='true'
```

---

## 4. Bloco 4 — Registro do `F4-034` e Adendos Documentais

### 4.1 Adendo em `audits/relatorio_4_4e.md:766-769`

```markdown
766: ## Adendo (2026-11-11 — Rodada 4.4g, Bloco 4): Falha Sequencial no CI (`F4-034`) Não Explicada por `F4-033`
767: 
768: - No CI do commit `3dccf68` (run `43075938190`, job `Test (Python 3.10)`), ocorreu novamente `ERROR at setup of test_lightweight_mode_behavior` com a pilha `tests/conftest.py:14` (`stress_components`) → `tests/memory_stress_test.py:265` (`bootstrap`) → `storage/vector_store.py:321` (`get_or_create_collection`) → `chromadb.errors.InternalError: ... (code: 1) no such table: acquire_write` (`473 passed, 1 skipped, 1 xfailed, 1 error`).
769: - Essa execução ocorreu em **um único processo sequencial**, portanto **não** decorre da colisão paralela entre processos em caminhos fixos tratada em `F4-033`. O erro intermitente do `chromadb` em `stress_components` (`F4-034`) permanece **aberto, com causa não provada**.
```

### 4.2 Adendo ao `F4-033` em `audits/fase4-achados.md:605-607`

```markdown
605: - **Limite Explícito (Bloco 1 e Bloco 4):**
606:   - **Não está provado** que essa colisão explique o erro intermitente do `chromadb` (`InternalError` / `PanicException` e `sqlite3.OperationalError: no such table: collections`) observado na 1ª tentativa da Rodada 4.4d. O erro reproduzido pela colisão é diferente daquele `chromadb` `InternalError` intermitente; **o `chromadb` intermitente segue aberto, com causa não provada**.
607:   - **Adendo (2026-11-11 — Rodada 4.4g, Bloco 4):** No CI do commit `3dccf68` (run `43075938190`, job `Test (Python 3.10)`, id `130715647420`), ocorreu novamente `ERROR at setup of test_lightweight_mode_behavior` com a pilha `tests/conftest.py:14 stress_components` → `tests/memory_stress_test.py:265 bootstrap` → `storage/vector_store.py:321 get_or_create_collection` → `chromadb.errors.InternalError: ... (code: 1) no such table: acquire_write` (`473 passed, 1 skipped, 1 xfailed, 1 error`). Essa falha ocorreu em **um único processo sequencial**, portanto **não** decorre da colisão paralela entre processos tratada em `F4-033` (ver `F4-034`).
```

### 4.3 Novo Achado `[F4-034]` em `audits/fase4-achados.md:615-634`

```markdown
615: ### [F4-034] Erro Interno Intermitente do `chromadb` em `stress_components` (`no such table: acquire_write`)
616: - **Status:** **ABERTO (causa não provada)**
617: - **Severidade Proposta:** 🟢 BAIXA
618:   - **Justificativa:** Falha intermitente exclusiva do setup da fixture de teste `stress_components` em execução de CI no Linux; não reproduzida em 60 execuções sequenciais locais (`0/30` Py3.10 + `0/30` Py3.12) nem no caminho de produção do servidor MCP.
619: - **Arquivos & Linhas:** [`tests/conftest.py:10-25`](file:///c:/Nexus-Memory/GrafoConcierge/tests/conftest.py#L10-L25), [`tests/memory_stress_test.py:270-277`](file:///c:/Nexus-Memory/GrafoConcierge/tests/memory_stress_test.py#L270-L277), [`storage/vector_store.py:317-321`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L317-L321), [`tests/test_lightweight.py:10`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_lightweight.py#L10), [`tests/test_stress_components_reuse.py:1-128`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_stress_components_reuse.py#L1-L128)
620: - **Fato Observado no CI (commit `3dccf68`, run `43075938190`, job `Test (Python 3.10)` / `id=130715647420`):**
621:   - Em execução de **um único processo sequencial**, o job falhou com `ERROR at setup of test_lightweight_mode_behavior`, pilha `tests/conftest.py:14 stress_components` → `tests/memory_stress_test.py:265 bootstrap` → `storage/vector_store.py:321 get_or_create_collection` → `chromadb.errors.InternalError: ... (code: 1) no such table: acquire_write` (`473 passed, 1 skipped, 1 xfailed, 1 error`).
622:   - Os logs brutos do job `130715647420` retornaram `HTTP 403` sem autenticação via API pública; nos metadados públicos do job consta a falha do step 7 (`Run tests with pytest`) em `2026-11-11T18:18:15Z`.
623: - **Investigação na Rodada 4.4g (Bloco 1, sobre a base `26a43e2`):**
624:   1. **Tentativa de reprodução 30 + 30 (não reproduzido):** Executada a suíte completa sequencialmente com o comando do CI (`pytest -v --tb=short`, `TOKENIZERS_PARALLELISM=false`, `GRAFO_LIGHTWEIGHT_MODE=false`, `HF_HUB_OFFLINE=1`) **30 vezes em Python `3.10.22`** e **30 vezes em Python `3.12.16`** (ambos com `chromadb=1.5.9`, `pytest=9.2.0`): resultado **`0/30` em Py3.10 e `0/30` em Py3.12 (`0/60` no total)**, todas com `475 passed, 1 xfailed` (fonte: [`scratch/evidencia_4_4g/bloco1_30x_results.txt:1-74`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco1_30x_results.txt#L1-L74)).
625:   2. **Consumidores e ordem de coleta:** Em ordem normal (`pytest --collect-only -q`), `test_lightweight.py` é o 4º consumidor da fixture `stress_components` (módulo `37` de `59`, após `01. memory_stress_test.py`, `09. test_chunk_cache.py` e `32. test_ignore.py`), sofrendo 3 ciclos prévios de `SETUP M stress_components` / `TEARDOWN M stress_components` no mesmo processo; em `--reverse`, a ordem inverte e `test_lightweight.py` roda primeiro (fonte: [`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:25-219`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt#L25-L219)). Arquivos standalone `tests/stress_test_v2_parte{1,2,3}.py` importam as funções, mas não são coletados por `pyproject.toml:117-118`.
626:   3. **Versões e requisitos:** `pyproject.toml:38` declara `"chromadb>=1.0"`, `requirements.txt:4` declara `chromadb>=1.0.0`, e `.github/workflows/ci.yml:30-42` instala com `pip install -e .[dev]` usando `cache: 'pip'`. Nos 5 ambientes virtuais locais (Python `3.10.22`, `3.11.18`, `3.12.16`, `3.13.18`, `3.14.3`), todos utilizam `chromadb=1.5.9`, `pytest=9.2.0` e expõem `SharedSystemClient.clear_system_cache` (`True`; fonte: [`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:3-8`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt#L3-L8)).
627:   4. **Sonda mínima no Windows vs. observação do auditor em Linux:** Enquanto a sonda mínima do auditor independente em Linux (`PersistentClient` vivo → `shutil.rmtree` → novo cliente no mesmo caminho) falhou em 6/6 com `InternalError ... (code: 1032) attempt to write a readonly database` (mensagem diferente de `no such table: acquire_write`, `(code: 1)`), no Windows `shutil.rmtree` sobre cliente vivo levanta `PermissionError: [WinError 32]` e, com `ignore_errors=True` (`tests/conftest.py:22`), o arquivo `chroma.sqlite3` permanece em disco (`sqlite_remained_after_ignore_errors=True`, `c2_err=None` em `3/3` Py3.10 + `3/3` Py3.12; fonte: [`scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt:3-12`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt#L3-L12)).
628:   5. **Hipótese Explícita (Causa Não Provada):** Embora a divergência entre `unlink` em POSIX e lock de arquivo aberto (`WinError 32`) no Windows possa estar relacionada à não reprodução local em Windows, **a causa raiz de `no such table: acquire_write` no CI continua NÃO PROVADA**.
629: - **Endurecimento Defensivo Aplicado na Rodada 4.4g (Bloco 2 — sem código de produto):**
630:   - Em `tests/memory_stress_test.py:270-277`, `bootstrap()` passou a instanciar `ChromaVectorStore` com subdiretório exclusivo por chamada (`chroma_dir = os.path.join(CHROMA_PATH, f"run_{uuid.uuid4().hex}")`), preservando o símbolo `CHROMA_PATH` e evitando o reuso do mesmo `persist_dir` e entrada em `SharedSystemClient` entre chamadas sucessivas no mesmo processo.
631:   - **Limite:** Sem reprodução prévia (`0/60`), essa mudança é estritamente **endurecimento defensivo**; **não** constitui prova de correção do `F4-034`, que permanece **aberto, causa não provada**.
632: - **Testes Adicionados na Rodada 4.4g (Bloco 3):**
633:   - `tests/test_stress_components_reuse.py:78-99`: `test_stress_components_reuse_cycle_characterization` (**caracterização do ciclo de reuso, não prova de correção**; passa em `26a43e2` e também sobrevive quando mutação externa reintroduz `persist_dir=CHROMA_PATH`, logo não há teste vermelho para `F4-034`, fonte: [`scratch/evidencia_4_4g/bloco3_mutation_and_env.txt:4-18`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco3_mutation_and_env.txt#L4-L18)).
634:   - `tests/test_stress_components_reuse.py:101-128`: `test_bootstrap_uses_distinct_chroma_subdir_per_call` (verifica a invariante estrutural do Bloco 2 e falha `RC=1` quando a mutação reintroduz `persist_dir=CHROMA_PATH`, fonte: [`scratch/evidencia_4_4g/bloco3_mutation_and_env.txt:20-63`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4g/bloco3_mutation_and_env.txt#L20-L63)).
```

### 4.4 Entradas em `audits/fase4-roadmap.md:61-61` e `100-100`

```markdown
61: | 4.4g | `c1eefba` | Bloco 1 (investigação de `F4-034` no estado `26a43e2`: 0/30 Py3.10 + 0/30 Py3.12 = 0/60 reproduções sequenciais, mapeamento de coleta e sonda Windows `WinError 32` vs Linux); Bloco 2 (endurecimento defensivo em `tests/memory_stress_test.py:270-277` com subdiretório Chroma exclusivo `run_<uuid4>` por chamada em `bootstrap()`, sem alteração em código de produto); Bloco 3 (`tests/test_stress_components_reuse.py` com teste de caracterização e teste estrutural + mutação externa); Bloco 4 (registro de `F4-034` e adendos em `F4-033` e `relatorio_4_4e.md`) | aberto, causa não provada | — |
...
100: | F4-034 | Erro interno intermitente do `chromadb` em setup de `stress_components` no CI do commit `3dccf68` (run `43075938190`, job `Test (Python 3.10)`, `no such table: acquire_write`, `code: 1`, em execução sequencial de processo único); não reproduzido localmente (`0/30` Py3.10 + `0/30` Py3.12 = `0/60`); subdiretório Chroma exclusivo `run_<uuid4>` por chamada em `bootstrap()` (`tests/memory_stress_test.py:270-277`) aplicado apenas como endurecimento defensivo, sem código de produto alterado | BAIXA | aberto, causa não provada | `tests/memory_stress_test.py`, `tests/test_stress_components_reuse.py`, `scratch/evidencia_4_4g/`, `audits/fase4-achados.md`, `audits/relatorio_4_4g.md` |
```

---

## 5. Suíte Completa Multi-Versão (`Python 3.10`–`3.14`, Normal e `--reverse`)

#### `scratch/evidencia_4_4g/suite_py310.txt`

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4g — PÓS BLOQUEIO DEFENSIVO F4-034) ===
2: Tag: py310
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
4: Versão do Python: Python 3.10.22 (main, Oct  9 2026, 15:18:58) [MSC v.1944 64 bit (AMD64)]
5: Versão do chromadb: 1.5.9
6: Ordem Padrão ReturnCode: 0
7: Ordem Invertida (--reverse) ReturnCode: 0
8: 
...
9: --- [1] ORDEM PADRÃO (pytest -v --tb=short) ---
568: ============ 477 passed, 1 xfailed, 4 warnings in 98.67s (0:01:38) ============
573: --- [2] ORDEM INVERTIDA (pytest -v --tb=short --reverse) ---
1132: ============ 477 passed, 1 xfailed, 4 warnings in 96.15s (0:01:36) ============
```
#### `scratch/evidencia_4_4g/suite_py311.txt`

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4g — PÓS BLOQUEIO DEFENSIVO F4-034) ===
2: Tag: py311
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_311\Scripts\python.exe
4: Versão do Python: Python 3.11.18 (main, Oct 26 2026, 14:08:50) [MSC v.1944 64 bit (AMD64)]
5: Versão do chromadb: 1.5.9
6: Ordem Padrão ReturnCode: 0
7: Ordem Invertida (--reverse) ReturnCode: 0
8: 
...
9: --- [1] ORDEM PADRÃO (pytest -v --tb=short) ---
574: ============ 477 passed, 1 xfailed, 4 warnings in 93.94s (0:01:33) ============
579: --- [2] ORDEM INVERTIDA (pytest -v --tb=short --reverse) ---
1144: ============ 477 passed, 1 xfailed, 4 warnings in 89.60s (0:01:29) ============
```
#### `scratch/evidencia_4_4g/suite_py312.txt`

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4g — PÓS BLOQUEIO DEFENSIVO F4-034) ===
2: Tag: py312
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe
4: Versão do Python: Python 3.12.16 (main, Oct 26 2026, 14:10:56) [MSC v.1944 64 bit (AMD64)]
5: Versão do chromadb: 1.5.9
6: Ordem Padrão ReturnCode: 0
7: Ordem Invertida (--reverse) ReturnCode: 0
8: 
...
9: --- [1] ORDEM PADRÃO (pytest -v --tb=short) ---
584: =========== 477 passed, 1 xfailed, 21 warnings in 92.21s (0:01:32) ============
589: --- [2] ORDEM INVERTIDA (pytest -v --tb=short --reverse) ---
1164: =========== 477 passed, 1 xfailed, 21 warnings in 90.56s (0:01:30) ============
```
#### `scratch/evidencia_4_4g/suite_py313.txt`

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4g — PÓS BLOQUEIO DEFENSIVO F4-034) ===
2: Tag: py313
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe
4: Versão do Python: Python 3.13.18 (main, Oct 26 2026, 14:10:48) [MSC v.1944 64 bit (AMD64)]
5: Versão do chromadb: 1.5.9
6: Ordem Padrão ReturnCode: 0
7: Ordem Invertida (--reverse) ReturnCode: 0
8: 
...
9: --- [1] ORDEM PADRÃO (pytest -v --tb=short) ---
590: =========== 477 passed, 1 xfailed, 21 warnings in 93.85s (0:01:33) ============
595: --- [2] ORDEM INVERTIDA (pytest -v --tb=short --reverse) ---
1176: =========== 477 passed, 1 xfailed, 21 warnings in 90.94s (0:01:30) ============
```
#### `scratch/evidencia_4_4g/suite_py314.txt`

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4g — PÓS BLOQUEIO DEFENSIVO F4-034) ===
2: Tag: py314
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
4: Versão do Python: Python 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
5: Versão do chromadb: 1.5.9
6: Ordem Padrão ReturnCode: 0
7: Ordem Invertida (--reverse) ReturnCode: 0
8: 
...
9: --- [1] ORDEM PADRÃO (pytest -v --tb=short) ---
594: =========== 477 passed, 1 xfailed, 22 warnings in 99.92s (0:01:39) ============
599: --- [2] ORDEM INVERTIDA (pytest -v --tb=short --reverse) ---
1184: =========== 477 passed, 1 xfailed, 22 warnings in 93.72s (0:01:33) ============
```

---

## 6. Conformidade, Segurança, Diff de Produto e CI

- **Alterações em código de produto vs `26a43e2` (`core/ storage/ ingestion/ interface/ services/ main.py`):** `VAZIO (nenhum arquivo alterado)`

### 6.1 `git diff --stat` vs `26a43e2`

```text
audits/fase4-achados.md                            |   24 +
 audits/fase4-roadmap.md                            |    2 +
 audits/relatorio_4_4e.md                           |    5 +
 audits/relatorio_4_4g.md                           |  685 +++++++++++
 scratch/check_ci_status_4_4g.py                    |  141 +++
 scratch/evidencia_4_4g/bloco1_30x_results.txt      |   74 ++
 .../bloco1_collect_order_and_versions.txt          |  219 ++++
 .../bloco1_sonda_and_ci_versions.txt               |   45 +
 scratch/evidencia_4_4g/bloco1_tracebacks.txt       |    1 +
 .../evidencia_4_4g/bloco2_consumers_and_guards.txt |  128 +++
 .../evidencia_4_4g/bloco3_base_26a43e2_check.txt   |   35 +
 scratch/evidencia_4_4g/bloco3_mutation_and_env.txt |   63 ++
 scratch/evidencia_4_4g/ci_status.txt               |   20 +
 scratch/evidencia_4_4g/scan_secrets.txt            |    8 +
 scratch/evidencia_4_4g/suite_py310.txt             | 1135 +++++++++++++++++++
 scratch/evidencia_4_4g/suite_py311.txt             | 1147 +++++++++++++++++++
 scratch/evidencia_4_4g/suite_py312.txt             | 1167 +++++++++++++++++++
 scratch/evidencia_4_4g/suite_py313.txt             | 1179 +++++++++++++++++++
 scratch/evidencia_4_4g/suite_py314.txt             | 1187 ++++++++++++++++++++
 scratch/evidencia_4_4g/utf8_check.txt              |   86 ++
 scratch/generate_relatorio_4_4g.py                 |  317 ++++++
 scratch/investigate_bloco1_4_4g_part1.py           |  138 +++
 scratch/probe_bloco1_4_4g.py                       |   76 ++
 scratch/run_bloco1_30x_4_4g.py                     |  138 +++
 scratch/run_bloco3_on_base_4_4g.py                 |   62 +
 scratch/run_multiversion_suites_4_4g.py            |   91 ++
 scratch/verify_4_4g_integrity.py                   |  118 ++
 scratch/verify_bloco2_bloco3_4_4g.py               |  178 +++
 tests/memory_stress_test.py                        |    5 +-
 tests/test_stress_components_reuse.py              |  128 +++
 30 files changed, 8601 insertions(+), 1 deletion(-)
```

### 6.2 `scratch/tools/scan_secrets.py` (Regra 13) e Checagem UTF-8 / Nulos

```text
1: ReturnCode: 0
2: STDOUT:
3: scanned_files=1331
4: files_with_findings=0
5: total_pattern_hits=0
6: 
7: STDERR:
8: 
---
1: === VERIFICAÇÃO DE INTEGRIDADE, UTF-8 SEM BOM/NULOS E ZERO PRODUTO (RODADA 4.4g) ===
2: Diff de código de produto vs 26a43e2 (core/ storage/ ingestion/ interface/ services/ main.py): VAZIO (OK)
3: Diretórios residuais (_stress_test_workspace, tmp_chroma_test, grafo_stress_*): NENHUM (OK)
4: scratch/evidencia_4_4g/bloco1_30x_results.txt: bytes=7667, utf8=True, bom=False, null=False
5: scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt: bytes=13797, utf8=True, bom=False, null=False
6: scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt: bytes=2791, utf8=True, bom=False, null=False
7: scratch/evidencia_4_4g/bloco1_tracebacks.txt: bytes=76, utf8=True, bom=False, null=False
8: scratch/evidencia_4_4g/bloco2_consumers_and_guards.txt: bytes=8230, utf8=True, bom=False, null=False
9: scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt: bytes=1683, utf8=True, bom=False, null=False
10: scratch/evidencia_4_4g/bloco3_mutation_and_env.txt: bytes=3378, utf8=True, bom=False, null=False
11: scratch/evidencia_4_4g/ci_status.txt: bytes=1326, utf8=True, bom=False, null=False
12: scratch/evidencia_4_4g/scan_secrets.txt: bytes=94, utf8=True, bom=False, null=False
13: scratch/evidencia_4_4g/suite_py310.txt: bytes=116737, utf8=True, bom=False, null=False
14: scratch/evidencia_4_4g/suite_py311.txt: bytes=117340, utf8=True, bom=False, null=False
15: scratch/evidencia_4_4g/suite_py312.txt: bytes=119167, utf8=True, bom=False, null=False
16: scratch/evidencia_4_4g/suite_py313.txt: bytes=119512, utf8=True, bom=False, null=False
17: scratch/evidencia_4_4g/suite_py314.txt: bytes=119073, utf8=True, bom=False, null=False
18: scratch/evidencia_4_4g/utf8_check.txt: bytes=6081, utf8=True, bom=False, null=False
19: audits/agent-and-agents.md: bytes=27646, utf8=True, bom=False, null=False
20: audits/backlog-final-v2.md: bytes=24365, utf8=True, bom=False, null=False
21: audits/backlog-final.md: bytes=135137, utf8=True, bom=False, null=False
22: audits/bypass-governanca-por-session-id.md: bytes=26942, utf8=True, bom=False, null=False
23: audits/comparacao-fase3.md: bytes=6478, utf8=True, bom=False, null=False
24: audits/core-alias-tracker.md: bytes=4137, utf8=True, bom=False, null=False
25: audits/core-background-janitor.md: bytes=22060, utf8=True, bom=False, null=False
26: audits/core-checkpointer.md: bytes=27174, utf8=True, bom=False, null=False
27: audits/core-delta-manager.md: bytes=15218, utf8=True, bom=False, null=False
28: audits/core-rate-governor.md: bytes=17321, utf8=True, bom=False, null=False
29: audits/core-security-guard.md: bytes=12654, utf8=True, bom=False, null=False
30: audits/core-vector-reconciler.md: bytes=19998, utf8=True, bom=False, null=False
31: audits/cruzamento-modulos.md: bytes=28102, utf8=True, bom=False, null=False
32: audits/design_4_4d_connection_queue.md: bytes=14999, utf8=True, bom=False, null=False
33: audits/duplicacao-serialized-write-queue.md: bytes=20887, utf8=True, bom=False, null=False
34: audits/errata-4-2c.md: bytes=5226, utf8=True, bom=False, null=False
35: audits/errata-4-2e-3.md: bytes=4125, utf8=True, bom=False, null=False
36: audits/errata-4-2e.md: bytes=6484, utf8=True, bom=False, null=False
37: audits/errata-4-2f.md: bytes=3299, utf8=True, bom=False, null=False
38: audits/errata-4-2g.md: bytes=3420, utf8=True, bom=False, null=False
39: audits/errata-4-2h.md: bytes=3785, utf8=True, bom=False, null=False
40: audits/errata-4-2i.md: bytes=32152, utf8=True, bom=False, null=False
41: audits/errata-4-3.md: bytes=6465, utf8=True, bom=False, null=False
42: audits/errata-4-3b.md: bytes=15321, utf8=True, bom=False, null=False
43: audits/errata-4-3c.md: bytes=11789, utf8=True, bom=False, null=False
44: audits/fase4-0-mapa-poda.md: bytes=61121, utf8=True, bom=False, null=False
45: audits/fase4-0b-prova-de-execucao.md: bytes=70404, utf8=True, bom=False, null=False
46: audits/fase4-0c-prova-corrigida.md: bytes=36714, utf8=True, bom=False, null=False
47: audits/fase4-1-inventario-ddl.md: bytes=43259, utf8=True, bom=False, null=False
48: audits/fase4-1c-investigacao-f4-008.md: bytes=14138, utf8=True, bom=False, null=False
49: audits/fase4-1d-relatorio-retificado.md: bytes=19850, utf8=True, bom=False, null=False
50: audits/fase4-1g-investigacao-summary.md: bytes=33812, utf8=True, bom=False, null=False
51: audits/fase4-1h-migracao-summary.md: bytes=19047, utf8=True, bom=False, null=False
52: audits/fase4-2-desacoplamento-governor.md: bytes=13285, utf8=True, bom=False, null=False
53: audits/fase4-2b-pin-mcp-e-correcao-t4.md: bytes=27423, utf8=True, bom=False, null=False
54: audits/fase4-2c-medicao-inicializacao.md: bytes=14759, utf8=True, bom=False, null=False
55: audits/fase4-achados.md: bytes=103814, utf8=True, bom=False, null=False
56: audits/fase4-decisoes.md: bytes=7649, utf8=True, bom=False, null=False
57: audits/fase4-roadmap.md: bytes=27939, utf8=True, bom=False, null=False
58: audits/fora-de-escopo.md: bytes=7905, utf8=True, bom=False, null=False
59: audits/grafo-dashboard-web.md: bytes=35990, utf8=True, bom=False, null=False
60: audits/ingestion.md: bytes=39787, utf8=True, bom=False, null=False
61: audits/interface-telemetry-api.md: bytes=21308, utf8=True, bom=False, null=False
62: audits/mock-vs-real-audit.md: bytes=19569, utf8=True, bom=False, null=False
63: audits/relatorio_4_2e_3.md: bytes=22983, utf8=True, bom=False, null=False
64: audits/relatorio_4_2f.md: bytes=71722, utf8=True, bom=False, null=False
65: audits/relatorio_4_2g.md: bytes=41446, utf8=True, bom=False, null=False
66: audits/relatorio_4_2h.md: bytes=205351, utf8=True, bom=False, null=False
67: audits/relatorio_4_2h2.md: bytes=75830, utf8=True, bom=False, null=False
68: audits/relatorio_4_2i.md: bytes=142768, utf8=True, bom=False, null=False
69: audits/relatorio_4_2j.md: bytes=11735, utf8=True, bom=False, null=False
70: audits/relatorio_4_2k.md: bytes=16385, utf8=True, bom=False, null=False
71: audits/relatorio_4_2l.md: bytes=12506, utf8=True, bom=False, null=False
72: audits/relatorio_4_3.md: bytes=8599, utf8=True, bom=False, null=False
73: audits/relatorio_4_3b.md: bytes=13300, utf8=True, bom=False, null=False
74: audits/relatorio_4_3c.md: bytes=25361, utf8=True, bom=False, null=False
75: audits/relatorio_4_4.md: bytes=26079, utf8=True, bom=False, null=False
76: audits/relatorio_4_4b.md: bytes=33567, utf8=True, bom=False, null=False
77: audits/relatorio_4_4c.md: bytes=25275, utf8=True, bom=False, null=False
78: audits/relatorio_4_4d.md: bytes=23626, utf8=True, bom=False, null=False
79: audits/relatorio_4_4e.md: bytes=58142, utf8=True, bom=False, null=False
80: audits/relatorio_4_4f.md: bytes=42616, utf8=True, bom=False, null=False
81: audits/relatorio_4_4g.md: bytes=49672, utf8=True, bom=False, null=False
82: audits/schema-oficial-incompleto.md: bytes=31416, utf8=True, bom=False, null=False
83: audits/storage.md: bytes=36574, utf8=True, bom=False, null=False
84: audits/egm/4.4b-codebase-details.md: bytes=17475, utf8=True, bom=False, null=False
85: audits/egm/4.4b-design.md: bytes=11805, utf8=True, bom=False, null=False
86: Total verificados: 82 arquivos — TODOS OK.
```

### 6.3 Status do GitHub Actions CI (`scratch/evidencia_4_4g/ci_status.txt`)

```text
1: === GITHUB ACTIONS CI STATUS (RODADA 4.4g) ===
2: 
3: Referência de falha histórica no 3dccf68 (run 43075938190):
4:   Job 130715647420 (Test (Python 3.10)) | status=completed | conclusion=failure | completed_at=2026-11-11T18:18:17Z
5:     - Step 7: Run tests with pytest | conclusion=failure | completed_at=2026-11-11T18:18:15Z
6:     - Step 13: Post Set up Python 3.10 | conclusion=skipped | completed_at=2026-11-11T18:18:15Z
7:   Endpoint logs públicos: HTTP 403 (HTTP Error 403: Forbidden)
8: 
9: Commit 26a43e2 (26a43e2723488f5206c12f639c0a94a7ba3c483d):
10:   Workflow: CI (run_id=43134755874, status=completed, conclusion=success)
11:     - Job: Test (Python 3.11) (id=130907309022) | status=completed | conclusion=success
12:     - Job: Test (Python 3.10) (id=130907309047) | status=completed | conclusion=success
13:     - Job: Test (Python 3.12) (id=130907309265) | status=completed | conclusion=success
14:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=43134755757, status=completed, conclusion=success)
15:     - Job: Windows (3.10) (id=130907310662) | status=completed | conclusion=success
16:     - Job: Windows (3.12) (id=130907310839) | status=completed | conclusion=success
17:     - Job: Windows (3.14) (id=130907310931) | status=completed | conclusion=success
18:   => Resumo 26a43e2: 6/6 jobs verdes (success)
19: 
20: all_completed=True, any_failed=False
```
