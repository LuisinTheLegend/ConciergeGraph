# Relatório da Rodada 4.4f — Isolamento dos Testes (`F4-033`) e Docstring da Fila de Escrita

- **Data:** 2026-11-11
- **Base da Rodada:** `3dccf68d3085b553efe27a8175e5c5fcac29048d` (`3dccf68`)
- **HEAD no momento da geração:** `39bfbb01a327b4c4232d6812436d71298b3a22da`
- **Natureza da Rodada:** Mini-rodada exclusiva de higiene de teste e documentação. O único arquivo de código de produto modificado é `storage/connection.py`, restrito à docstring da classe `SerializedWriteQueue` (provado por comparação de AST sem docstrings com SHA-256 idêntico).
- **Gerado por script (Regra 12):** `scratch/generate_relatorio_4_4f.py`

---

## 1. Bloco 1 — Registro do Achado `F4-033`

### 1.1 Registro em `audits/fase4-achados.md:594-610`

```markdown
594: ### [F4-033] Caminhos Fixos Compartilhados em `tests/memory_stress_test.py` e `tests/test_lightweight.py` Causam Colisão em Execuções Paralelas de `pytest`
595: - **Status:** **corrigido pelo executor, aguardando verificação independente**
596: - **Severidade Proposta:** 🟢 BAIXA
597:   - **Justificativa da Severidade:** Afeta exclusivamente a infraestrutura de testes quando múltiplos processos `pytest` são executados em paralelo sobre o mesmo diretório de trabalho; não altera nem afeta o comportamento do código de produção.
598: - **Arquivos & Linhas (no commit `3dccf68`):** [`tests/memory_stress_test.py:40-43, 85-90, 644`](file:///c:/Nexus-Memory/GrafoConcierge/tests/memory_stress_test.py#L40-L46), [`tests/conftest.py:8, 10-25`](file:///c:/Nexus-Memory/GrafoConcierge/tests/conftest.py#L8-L25), [`tests/test_lightweight.py:38, 69`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_lightweight.py#L38)
599: - **Fato:**
600:   No commit `3dccf68`, `tests/memory_stress_test.py:40-43` definia `TEST_DIR`, `DB_PATH`, `CHROMA_PATH` e `PROJECT_DIR` apontando para o caminho fixo compartilhado `tests/_stress_test_workspace` (sobre o qual `setup_workspace()` e o teardown da fixture `stress_components` em `tests/conftest.py:22` executavam `shutil.rmtree(TEST_DIR, ignore_errors=True)`), e `tests/test_lightweight.py:38` definia `tmp_dir = "./tmp_chroma_test"` relativo ao diretório de execução. Esses caminhos fixos causam colisão determinística quando dois processos `pytest` executam simultaneamente no mesmo workspace.
601: - **Evidências Empíricas e Atribuição por Autor (Regra 14):**
602:   - **Medido pelo executor em Windows (Sonda 3c da 4.4e — `test_lightweight.py` no Python 3.10 em paralelo com `memory_stress_test.py` no Python 3.12):** **`10/10` pares com falha** (`sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid` em `storage/store.py:137`; fonte: [`scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt:104-108, 10238`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt#L104-L108)).
603:   - **Medido pelo executor em Windows (Prova em Vermelho da 4.4f no commit `3dccf68` — 2 processos `pytest tests/memory_stress_test.py` em paralelo no Python 3.12):** **`10/10` pares com falha** (`4` pares com `sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid`, `4` pares com `sqlite3.OperationalError: database is locked`, `1` par com `chromadb.errors.InternalError: Query error: Database error: error returned from database: (code: 5) database is locked` e `1` par com `chromadb.errors.InternalError: error returned from database: (code: 1) table collections already exists`; fonte: [`scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt:1-26`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt#L1-L26)).
604:   - **Reproduzido pelo auditor independente em Linux (2 processos `pytest tests/memory_stress_test.py` em paralelo):** **`3/4` pares com falha**, apresentando os erros `sqlite3.OperationalError: unable to open database file`, `ProjectNotFoundError` e `ValueError: Project not found`.
605: - **Limite Explícito (Bloco 1 e Bloco 4):**
606:   - **Não está provado** que essa colisão explique o erro intermitente do `chromadb` (`InternalError` / `PanicException` e `sqlite3.OperationalError: no such table: collections`) observado na 1ª tentativa da Rodada 4.4d. O erro reproduzido pela colisão é diferente daquele `chromadb` `InternalError` intermitente; **o `chromadb` intermitente segue aberto, com causa não provada**.
607: - **Correção Implementada na Rodada 4.4f (Bloco 2):**
608:   1. Em `tests/memory_stress_test.py:42-45`, `TEST_DIR` passou a usar `tempfile.mkdtemp(prefix=f"grafo_stress_{os.getpid()}_")` exclusivo por processo (compartilhado em `sys._grafo_stress_test_dir` caso o módulo seja importado como `tests.memory_stress_test` e como `memory_stress_test` na mesma sessão), com limpeza no teardown de `stress_components` (`tests/conftest.py:22`), no `finally` de `main()` (`tests/memory_stress_test.py:649`) e via `atexit.register`, preservando integralmente o contrato de importação dos consumidores (`tests/conftest.py:8`, `tests/test_lightweight.py:8`, `tests/test_chunk_cache.py:4`, `tests/test_ignore.py:3`).
609:   2. Em `tests/test_lightweight.py:10, 38`, `tmp_dir` passou a usar a fixture `tmp_path` (`str(tmp_path / "tmp_chroma_test")`).
610:   3. Validado com `0/10` falhas em 10 pares paralelos de `memory_stress_test.py` (`scratch/evidencia_4_4f/green_10_pairs_memory_stress.txt`), `0/10` falhas em 10 pares paralelos de `test_lightweight.py` vs. `memory_stress_test.py` (`scratch/evidencia_4_4f/green_10_pairs_lightweight_vs_stress.txt`), mutação `Ta` morta (`scratch/evidencia_4_4f/mutacao_Ta.txt`) e demonstração empírica da mutação `Tb` (`scratch/evidencia_4_4f/mutacao_Tb.txt`).
```

### 1.2 Índice em `audits/fase4-roadmap.md:59-60, 97-98`

```markdown
59: | 4.4e | `b709ba5`, `3dccf68` | Bloco 1 (testes A1, A2, A3 da invariante commit/rollback de `storage/connection.py::SerializedWriteQueue` e mutações Sm, Sn, So); Bloco 2 (reescrita do item de reprodução natural de `F4-031` com Exp A vs Exp B e atribuição Windows/Linux); Bloco 3 (registro de `F4-032` sobre `get_read_connection()` sem retry); Bloco 4 (testes de caracterização T-S1 e T-S2 de `start()` após `stop()` e jobs descartados na parada + mutações Sp, Sq + documentação em `design_4_4d_connection_queue.md`); Bloco 5 (investigação de 30 execuções de `test_lightweight.py` e `memory_stress_test.py`) | corrigido pelo executor, aguardando verificação independente | Sim (reproduzida colisão paralela 3/4 pares em Linux -> F4-033) |
60: | 4.4f | `39bfbb0` | Bloco 1 (registro de `F4-033` sobre caminhos fixos compartilhados em `memory_stress_test.py` e `test_lightweight.py`); Bloco 2 (isolamento por diretório exclusivo via `tempfile.mkdtemp` e `tmp_path`, provas vermelho->verde em 10 pares paralelos, mutações Ta e Tb, suíte sequencial 3.10–3.14); Bloco 3 (docstring de `SerializedWriteQueue` em `storage/connection.py` com prova de AST sem docstrings idêntica); Bloco 4 (adendo em `relatorio_4_4e.md` e em `F4-033` esclarecendo que o erro de colisão difere do `chromadb` `InternalError`, que segue aberto com causa não provada) | corrigido pelo executor, aguardando verificação independente | — |
...
97: | F4-032 | `ConnectionManager.get_read_connection()` executa conexão e PRAGMAs de leitura sem retry (levanta `OperationalError`, não trava; observado apenas no Windows no Exp A 97/100, não no caminho `SqliteStore` real Exp B 0/100) | BAIXA | ABERTO (registrado na 4.4e, sem correção nesta rodada) | `storage/connection.py:382-386, 427-443`, `scratch/evidencia_4_4d/natural_reproduction_100_procs.txt:15, 243`, `audits/fase4-achados.md` |
98: | F4-033 | Caminhos fixos compartilhados em `tests/memory_stress_test.py:40-43` (`_stress_test_workspace`) e `tests/test_lightweight.py:38` (`./tmp_chroma_test`) causam colisão em execuções paralelas de `pytest` (10/10 pares no Windows pelo executor; 3/4 pares no Linux pelo auditor; não explica o `chromadb` `InternalError`, que segue aberto com causa não provada) | BAIXA | corrigido pelo executor, aguardando verificação independente | `tests/memory_stress_test.py`, `tests/test_lightweight.py`, `scratch/evidencia_4_4f/`, `audits/fase4-achados.md` |
```

---

## 2. Bloco 2 — Correção do Isolamento de Testes (`F4-033`)

### 2.1 Mudanças Implementadas em `tests/memory_stress_test.py` e `tests/test_lightweight.py`

- **Observação técnica sobre dupla importação no mesmo processo `pytest`:** Como `tests/` não possui `__init__.py`, `tests/conftest.py:8` (`from tests.memory_stress_test import ...`) importa o módulo sob `sys.modules['tests.memory_stress_test']`, enquanto a coleta direta de `tests/memory_stress_test.py` pelo `pytest` o importa sob `sys.modules['memory_stress_test']`. Armazenar o diretório criado por `tempfile.mkdtemp(prefix=f'grafo_stress_{os.getpid()}_')` em `sys._grafo_stress_test_dir` garante que ambas as referências dentro do mesmo processo Python apontem para o mesmo diretório temporário exclusivo daquele processo, enquanto processos paralelos possuem `PID`s e diretórios temporários distintos.

#### `tests/memory_stress_test.py:38-51` e `641-653`

```python
38: # ---------------------------------------------------------------------------
39: # Configuração de paths (diretório exclusivo por execução via tempfile.mkdtemp)
40: # ---------------------------------------------------------------------------
41: 
42: if not hasattr(sys, "_grafo_stress_test_dir"):
43:     sys._grafo_stress_test_dir = tempfile.mkdtemp(prefix=f"grafo_stress_{os.getpid()}_")
44:     atexit.register(lambda: shutil.rmtree(sys._grafo_stress_test_dir, ignore_errors=True))
45: TEST_DIR = sys._grafo_stress_test_dir
46: DB_PATH = os.path.join(TEST_DIR, "stress_test.db")
47: CHROMA_PATH = os.path.join(TEST_DIR, "chroma")
48: PROJECT_DIR = os.path.join(TEST_DIR, "fake_project")
49: PROJECT_UUID = "stress-test-project-uuid-static-12345"
50: PROJECT_NAME = "stress-test-project"
51: 
...
641:     finally:
642:         # --- Cleanup ---
643:         if store is not None:
644:             try:
645:                 store.close()
646:             except Exception:
647:                 pass
648:         try:
649:             shutil.rmtree(TEST_DIR, ignore_errors=True)
650:         except Exception:
651:             pass
652: 
653:     return print_final_report()
```

#### `tests/test_lightweight.py:8-42` e `65-71`

```python
8: from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR
9: 
10: def test_lightweight_mode_behavior(store, manager, tmp_path):
11:     """Valida o funcionamento e isolamento do Modo Lightweight.
12: 
13:     Verifica se:
14:     1. A flag GRAFO_LIGHTWEIGHT_MODE ativa corretamente o lightweight_mode na config.
15:     2. O EmbeddingManager não faz o carregamento do modelo e retorna None ao gerar embeds.
16:     3. O ChromaVectorStore entra em modo NO-OP e desativa a inicialização do PersistentClient.
17:     4. A busca híbrida (HybridSearchEngine) realiza o fallback gracioso para FTS5-only.
18:     """
19:     # 0. Garante que há dados no banco SQLite FTS5 antes do teste
20:     result = manager.mine(PROJECT_UUID, PROJECT_DIR, auto_tag=True)
21:     assert result.files_processed > 0, "Ingestão inicial para popular banco FTS5 falhou."
22: 
23:     # Define a variável de ambiente para ativar o modo Lightweight
24:     os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "true"
25: 
26:     try:
27:         # 1. Valida detecção na configuração
28:         config = ConciergeConfig()
29:         assert config.lightweight_mode is True, "Configuração deveria ter lightweight_mode=True com env var ativa."
30: 
31:         # 2. Valida bypass do modelo no EmbeddingManager
32:         embedder = EmbeddingManager()
33:         # Não deve levantar erro ao inicializar, mas ao tentar embedar deve dar fallback/None silencioso
34:         embedding = embedder.embed("test query")
35:         assert embedding is None, "EmbeddingManager deveria retornar None no modo lightweight (bypass do modelo)."
36: 
37:         # 3. Valida bypass de inicialização no ChromaVectorStore
38:         tmp_dir = str(tmp_path / "tmp_chroma_test")
39:         vector_store = ChromaVectorStore(persist_dir=tmp_dir)
40:         assert vector_store._available is False, "ChromaVectorStore deveria estar com _available=False no modo lightweight."
41:         assert vector_store._client is None, "ChromaVectorStore não deveria ter instanciado o PersistentClient."
42: 
...
65:     finally:
66:         # Restaura a variável de ambiente original
67:         os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
68:         try:
69:             shutil.rmtree(tmp_dir, ignore_errors=True)
70:         except Exception:
71:             pass
```

### 2.2 Preservação do Contrato dos Consumidores e das Guardas (`check_mcp_globals_leak`, Hook `M10d` e `G2`)

- Consumidores verificados sem alteração de contrato:
  - `tests/conftest.py:8` (`from tests.memory_stress_test import setup_workspace, bootstrap, TEST_DIR`)
  - `tests/test_lightweight.py:8` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR`)
  - `tests/test_chunk_cache.py:4` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR, UTILS_FILE`)
  - `tests/test_ignore.py:3` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR`)

#### Evidência: `scratch/evidencia_4_4f/consumers_and_guards_check.txt:1-45`

```text
1: === VERIFICAÇÃO DE CONSUMIDORES E GUARDAS (BLOCO 2 — RODADA 4.4f) ===
2: Comando 1 (consumidores + G2 + autouse conftest): C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/test_chunk_cache.py tests/test_ignore.py tests/test_lightweight.py tests/memory_stress_test.py tests/test_domain_neutrality_guard.py -v --tb=short
3: Return Code 1: 0 (33.04s)
4: Comando 2 (prova de check_mcp_globals_leak e hook de baseline M10d): C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe scratch/run_bloco2_4_4d_mutation.py
5: Return Code 2: 0 (17.40s)
6: Resíduo tests/_stress_test_workspace existe: False
7: Resíduo tmp_chroma_test existe: False
8: 
9: --- STDOUT COMANDO 1 ---
10: ============================= test session starts =============================
11: platform win32 -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 11 items
20: 
21: tests/test_chunk_cache.py::test_chunk_cache_behavior PASSED              [  9%]
22: tests/test_ignore.py::test_safe_ignore_behavior PASSED                   [ 18%]
23: tests/test_lightweight.py::test_lightweight_mode_behavior PASSED         [ 27%]
24: tests/memory_stress_test.py::test_dimension_1 PASSED                     [ 36%]
25: tests/memory_stress_test.py::test_dimension_2 PASSED                     [ 45%]
26: tests/memory_stress_test.py::test_dimension_3 PASSED                     [ 54%]
27: tests/memory_stress_test.py::test_dimension_4 PASSED                     [ 63%]
28: tests/test_domain_neutrality_guard.py::test_g1_concierge_config_has_no_wing_keywords PASSED [ 72%]
29: tests/test_domain_neutrality_guard.py::test_g2_no_retired_domain_strings_in_product_code PASSED [ 81%]
30: tests/test_domain_neutrality_guard.py::test_g3_real_mining_never_alters_primary_wing PASSED [ 90%]
31: tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project PASSED [100%]
32: 
33: ============================== warnings summary ===============================
34: tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
35:   C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
36:     updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
37: 
38: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
39: ======================= 11 passed, 1 warning in 26.78s ========================
40: 
41: STDERR:
42: 
43: --- STDOUT COMANDO 2 (M10d / check_mcp_globals_leak) ---
44: M10d_import: mut1=3, mut2=3, clean=0 -> MORTA (OK)
45: 
```

### 2.3 Prova em Vermelho (no commit `3dccf68`) — 10 Pares Paralelos de `memory_stress_test.py` (Python 3.12)

- **Resultado em `3dccf68`:** **`10/10` pares paralelos falharam** (`4` pares com `sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid`, `4` pares com `sqlite3.OperationalError: database is locked`, `1` par com `chromadb.errors.InternalError: ... (code: 5) database is locked` e `1` par com `chromadb.errors.InternalError: ... (code: 1) table collections already exists`).

#### Evidência: `scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt:1-26`

```text
1: === PROVA EM VERMELHO (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS DE memory_stress_test.py NO COMMIT 3dccf68 ===
2: Commit HEAD: 3dccf68d3085b553efe27a8175e5c5fcac29048d
3: Sistema Operacional: Windows 11 (10.0.26300)
4: Comando por processo: C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=short
5: --------------------------------------------------------------------------------
6:   [Par 01/10] ProcA=FAIL(rc=1) (18.23s) | ProcB=PASS (51.93s) | Erros=['sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid']
7:   [Par 02/10] ProcA=FAIL(rc=1) (7.30s) | ProcB=PASS (27.32s) | Erros=['InternalError', 'chromadb.errors.InternalError: Query error: Database error: error returned from database: (code: 5) database is locked']
8:   [Par 03/10] ProcA=PASS (27.10s) | ProcB=FAIL(rc=1) (6.01s) | Erros=['sqlite3.OperationalError: database is locked']
9:   [Par 04/10] ProcA=FAIL(rc=1) (7.02s) | ProcB=PASS (27.71s) | Erros=['sqlite3.OperationalError: database is locked']
10:   [Par 05/10] ProcA=PASS (27.32s) | ProcB=FAIL(rc=1) (6.99s) | Erros=['sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid']
11:   [Par 06/10] ProcA=PASS (27.24s) | ProcB=FAIL(rc=1) (6.87s) | Erros=['sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid']
12:   [Par 07/10] ProcA=FAIL(rc=1) (6.28s) | ProcB=PASS (25.93s) | Erros=['sqlite3.OperationalError: database is locked']
13:   [Par 08/10] ProcA=PASS (25.63s) | ProcB=FAIL(rc=1) (6.62s) | Erros=['sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid']
14:   [Par 09/10] ProcA=FAIL(rc=1) (7.57s) | ProcB=PASS (26.50s) | Erros=['InternalError', 'chromadb.errors.InternalError: error returned from database: (code: 1) table collections already exists']
15:   [Par 10/10] ProcA=PASS (25.11s) | ProcB=FAIL(rc=1) (6.04s) | Erros=['sqlite3.OperationalError: database is locked']
16: --------------------------------------------------------------------------------
17: RESUMO VERMELHO (commit 3dccf68): 10/10 pares paralelos falharam.
18: Contagem por tipo de erro observado nos pares com falha:
19:   - sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid: 4 par(es)
20:   - sqlite3.OperationalError: database is locked: 4 par(es)
21:   - InternalError: 2 par(es)
22:   - chromadb.errors.InternalError: Query error: Database error: error returned from database: (code: 5) database is locked: 1 par(es)
23:   - chromadb.errors.InternalError: error returned from database: (code: 1) table collections already exists: 1 par(es)
24: --------------------------------------------------------------------------------
25: 
26: === TRACEBACKS COMPLETOS DOS PARES COM FALHA ===
```

### 2.4 Prova em Verde (Versão Corrigida) — 10 Pares Paralelos

#### (a) 10 Pares Paralelos de `memory_stress_test.py` (Python 3.12): `0/10` falhas (`scratch/evidencia_4_4f/green_10_pairs_memory_stress.txt:1-17`)

```text
1: === PROVA EM VERDE (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS DE memory_stress_test.py (PYTHON 3.12) ===
2: Comando por processo: C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=short
3: --------------------------------------------------------------------------------
4:   [Par 01/10] ProcA=PASS (27.08s) | ProcB=PASS (27.16s)
5:   [Par 02/10] ProcA=PASS (29.37s) | ProcB=PASS (29.35s)
6:   [Par 03/10] ProcA=PASS (29.88s) | ProcB=PASS (30.00s)
7:   [Par 04/10] ProcA=PASS (31.33s) | ProcB=PASS (31.24s)
8:   [Par 05/10] ProcA=PASS (29.97s) | ProcB=PASS (29.93s)
9:   [Par 06/10] ProcA=PASS (28.73s) | ProcB=PASS (28.80s)
10:   [Par 07/10] ProcA=PASS (28.13s) | ProcB=PASS (28.06s)
11:   [Par 08/10] ProcA=PASS (27.88s) | ProcB=PASS (27.96s)
12:   [Par 09/10] ProcA=PASS (28.26s) | ProcB=PASS (28.25s)
13:   [Par 10/10] ProcA=PASS (29.68s) | ProcB=PASS (29.72s)
14: --------------------------------------------------------------------------------
15: RESUMO VERDE (memory_stress_test.py x2, Python 3.12): 0/10 pares com falha.
16: Resíduo tests/_stress_test_workspace existe: False
17: Resíduo tmp_chroma_test existe: False
```

#### (b) 10 Pares Paralelos de `test_lightweight.py` (Python 3.10) vs. `memory_stress_test.py` (Python 3.12): `0/10` falhas (`scratch/evidencia_4_4f/green_10_pairs_lightweight_vs_stress.txt:1-18`)

```text
1: === PROVA EM VERDE (BLOCO 2 — RODADA 4.4f): 10 PARES PARALELOS test_lightweight.py (Py3.10) vs memory_stress_test.py (Py3.12) ===
2: Processo A (Py3.10): C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/test_lightweight.py -v --tb=short
3: Processo B (Py3.12): C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=short
4: --------------------------------------------------------------------------------
5:   [Par 01/10] Py3.10(test_lightweight)=PASS (74.56s) | Py3.12(memory_stress_test)=PASS (27.61s)
6:   [Par 02/10] Py3.10(test_lightweight)=PASS (23.06s) | Py3.12(memory_stress_test)=PASS (27.70s)
7:   [Par 03/10] Py3.10(test_lightweight)=PASS (24.03s) | Py3.12(memory_stress_test)=PASS (28.22s)
8:   [Par 04/10] Py3.10(test_lightweight)=PASS (23.94s) | Py3.12(memory_stress_test)=PASS (28.11s)
9:   [Par 05/10] Py3.10(test_lightweight)=PASS (23.94s) | Py3.12(memory_stress_test)=PASS (28.05s)
10:   [Par 06/10] Py3.10(test_lightweight)=PASS (24.38s) | Py3.12(memory_stress_test)=PASS (28.54s)
11:   [Par 07/10] Py3.10(test_lightweight)=PASS (24.55s) | Py3.12(memory_stress_test)=PASS (28.71s)
12:   [Par 08/10] Py3.10(test_lightweight)=PASS (23.90s) | Py3.12(memory_stress_test)=PASS (28.09s)
13:   [Par 09/10] Py3.10(test_lightweight)=PASS (24.48s) | Py3.12(memory_stress_test)=PASS (28.54s)
14:   [Par 10/10] Py3.10(test_lightweight)=PASS (23.95s) | Py3.12(memory_stress_test)=PASS (28.14s)
15: --------------------------------------------------------------------------------
16: RESUMO VERDE (test_lightweight.py Py3.10 vs memory_stress_test.py Py3.12): 0/10 pares com falha.
17: Resíduo tests/_stress_test_workspace existe: False
18: Resíduo tmp_chroma_test existe: False
```

### 2.5 Mutações Matadoras (`Ta` e `Tb`)

| Mutação | Alvo | Comportamento com Mutação | Comportamento sem Mutação | Status | Evidência |
|---|---|---|---|---|---|
| `Ta` | Reintroduzir caminho fixo `_stress_test_workspace` em `TEST_DIR` (`tests/memory_stress_test.py:42-45`) | `5/5` pares paralelos falham (`UNIQUE constraint failed: projects.uuid` / `database is locked`) | `0` falhas (`ProcA rc=0, ProcB rc=0`) | **MORTA (OK)** | `scratch/evidencia_4_4f/mutacao_Ta.txt` |
| `Tb` | Reintroduzir `'./tmp_chroma_test'` em `tmp_dir` (`tests/test_lightweight.py:38`) | `0/5` pares paralelos falham (explicado e demonstrado abaixo: `ChromaVectorStore` em modo lightweight é `NO-OP` e não cria `persist_dir` no disco) | `0` falhas | **Explicada e demonstrada empiricamente** | `scratch/evidencia_4_4f/mutacao_Tb.txt` |

#### Evidência Mutação `Ta`: `scratch/evidencia_4_4f/mutacao_Ta.txt:1-46`

```text
1: === MUTAÇÃO Ta (BLOCO 2 — RODADA 4.4f): Reintroduzir caminho fixo em TEST_DIR (tests/memory_stress_test.py:42) ===
2: Alvo: tests/memory_stress_test.py
3: Resultado COM mutação (VERMELHO): 5/5 pares paralelos falharam (esperado > 0)
4: Resultado SEM mutação (VERDE): ProcA rc=0 (28.44s), ProcB rc=0 (28.41s) (esperado 0, 0)
5: Status: MORTA (OK)
6: 
7:   [Mutação Ta Par 01/05] ProcA rc=1 (7.18s) | ProcB rc=0 (26.97s)
8: --- Exemplo de Traceback com Mutação Ta (Par #01) ---
9: ProcA:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 4 items
20: 
21: tests/memory_stress_test.py::test_dimension_1 ERROR                      [ 25%]
22: tests/memory_stress_test.py::test_dimension_2 ERROR                      [ 50%]
23: tests/memory_stress_test.py::test_dimension_3 ERROR                      [ 75%]
24: tests/memory_stress_test.py::test_dimension_4 ERROR                      [100%]
25: 
26: =================================== ERRORS ====================================
27: _____________________ ERROR at setup of test_dimension_1 ______________________
28: tests\memory_stress_test.py:274: in bootstrap
29:     store.create_project(
30: storage\store.py:142: in create_project
31:     return self._conn_mgr.write(_do, uuid, folder_name, primary_wing, privacy_level, summary)
32:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
33: storage\connection.py:473: in write
34:     return self._write_queue.submit(fn, *args, **kwargs)
35:            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
36: storage\connection.py:234: in submit
37:     raise job.error
38: storage\connection.py:331: in _worker
39:     job.result = job.fn(self._conn, *job.args, **job.kwargs)
40:                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
41: storage\store.py:137: in _do
42:     conn.execute(
43: E   sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid
44: ----------------------------- Captured log setup ------------------------------
45: ERROR    grafo-concierge.connection:connection.py:345 Error in write thread (transaction rolled back): UNIQUE constraint failed: projects.uuid
46: ERROR    grafo-concierge.connection:connection.py:233 Job execution failed: UNIQUE constraint failed: projects.uuid
```

#### Evidência e Demonstração Mutação `Tb`: `scratch/evidencia_4_4f/mutacao_Tb.txt:1-26`

```text
1: === MUTAÇÃO Tb (BLOCO 2 — RODADA 4.4f): Reintroduzir caminho fixo './tmp_chroma_test' em tests/test_lightweight.py:38 ===
2: Alvo: tests/test_lightweight.py
3: Resultado COM mutação em 5 pares paralelos de test_lightweight.py: 0/5 pares falharam
4: Sonda de I/O em modo lightweight: available=False, client=None, dir_created_on_disk=False
5: 
6: Demonstração e Explicação Técnica (conforme exigido pelo Bloco 2):
7: 1. Em `tests/test_lightweight.py:24`, `os.environ['GRAFO_LIGHTWEIGHT_MODE'] = 'true'` é definido ANTES da
8:    chamada `vector_store = ChromaVectorStore(persist_dir=tmp_dir)` na linha 39.
9: 2. Em `storage/vector_store.py:297-302`, `ChromaVectorStore.__init__` verifica:
10:    `if os.environ.get('GRAFO_LIGHTWEIGHT_MODE', 'false').lower() == 'true':`
11:    e retorna imediatamente na linha 302 (`self._available = False; self._client = None; return`)
12:    ANTES de `Path(resolved_dir).mkdir(parents=True, exist_ok=True)` (`storage/vector_store.py:315`)
13:    e ANTES de `chromadb.PersistentClient(path=resolved_dir)` (`storage/vector_store.py:317`).
14: 3. Consequentemente, como provado pela sonda acima (`dir_created_on_disk=False`), `ChromaVectorStore`
15:    em modo lightweight jamais cria, abre ou escreve em `persist_dir` no disco; e o `shutil.rmtree(tmp_dir, ignore_errors=True)`
16:    no bloco `finally` (`tests/test_lightweight.py:69`) opera sobre um caminho inexistente.
17: 4. Antes do isolamento de `TEST_DIR` (`tests/memory_stress_test.py:42`), `test_lightweight.py` colidia em paralelo
18:    não por causa de `./tmp_chroma_test`, mas porque na linha 20 (`manager.mine(PROJECT_UUID, PROJECT_DIR, ...)`)
19:    ele usa a fixture `store`/`manager` de `conftest.py` (que apontava para `tests/_stress_test_workspace`).
20: 
21: Logs dos 5 pares paralelos com Mutação Tb:
22:   [Mutação Tb Par 01/05] ProcA rc=0 (25.57s) | ProcB rc=0 (25.56s)
23:   [Mutação Tb Par 02/05] ProcA rc=0 (25.23s) | ProcB rc=0 (25.25s)
24:   [Mutação Tb Par 03/05] ProcA rc=0 (25.71s) | ProcB rc=0 (25.68s)
25:   [Mutação Tb Par 04/05] ProcA rc=0 (26.17s) | ProcB rc=0 (26.20s)
26:   [Mutação Tb Par 05/05] ProcA rc=0 (26.11s) | ProcB rc=0 (26.14s)
```

### 2.6 Execução Sequencial Normal nas 5 Versões de Python (`3.10`, `3.11`, `3.12`, `3.13`, `3.14`)

- Em todas as 5 versões, o número de testes coletados e executados permaneceu idêntico ao de `3dccf68`: **`475 passed, 1 xfailed`** (`476` itens coletados: `471 passed, 1 xfailed` da suíte `tests/` + `4 passed` de `tests/memory_stress_test.py`), tanto na ordem padrão quanto na ordem inversa (`--reverse`).

```text
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===
2: Tag: py310
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe
4: Versão do Python: Python 3.10.22 (main, Oct  9 2026, 15:18:58) [MSC v.1944 64 bit (AMD64)]
5: Ordem Padrão ReturnCode: 0
6: Ordem Invertida (--reverse) ReturnCode: 0
7: 
...
82: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
83: 475 passed, 1 xfailed, 4 warnings in 103.12s (0:01:43)
84: 
...
162: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
163: 475 passed, 1 xfailed, 4 warnings in 93.92s (0:01:33)
164: 
---
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===
2: Tag: py311
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_311\Scripts\python.exe
4: Versão do Python: Python 3.11.18 (main, Oct 26 2026, 14:08:50) [MSC v.1944 64 bit (AMD64)]
5: Ordem Padrão ReturnCode: 0
6: Ordem Invertida (--reverse) ReturnCode: 0
7: 
...
88: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
89: 475 passed, 1 xfailed, 4 warnings in 131.93s (0:02:11)
90: 
...
174: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
175: 475 passed, 1 xfailed, 4 warnings in 88.53s (0:01:28)
176: 
---
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===
2: Tag: py312
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe
4: Versão do Python: Python 3.12.16 (main, Oct 26 2026, 14:10:56) [MSC v.1944 64 bit (AMD64)]
5: Ordem Padrão ReturnCode: 0
6: Ordem Invertida (--reverse) ReturnCode: 0
7: 
...
98: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
99: 475 passed, 1 xfailed, 21 warnings in 94.50s (0:01:34)
100: 
...
194: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
195: 475 passed, 1 xfailed, 21 warnings in 90.51s (0:01:30)
196: 
---
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===
2: Tag: py313
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe
4: Versão do Python: Python 3.13.18 (main, Oct 26 2026, 14:10:48) [MSC v.1944 64 bit (AMD64)]
5: Ordem Padrão ReturnCode: 0
6: Ordem Invertida (--reverse) ReturnCode: 0
7: 
...
104: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
105: 475 passed, 1 xfailed, 21 warnings in 135.92s (0:02:15)
106: 
...
206: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
207: 475 passed, 1 xfailed, 21 warnings in 88.22s (0:01:28)
208: 
---
1: === SUÍTE COMPLETA MULTI-VERSÃO (RODADA 4.4f — PÓS-ISOLAMENTO F4-033) ===
2: Tag: py314
3: Interpretador: C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
4: Versão do Python: Python 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
5: Ordem Padrão ReturnCode: 0
6: Ordem Invertida (--reverse) ReturnCode: 0
7: 
...
108: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
109: 475 passed, 1 xfailed, 22 warnings in 116.91s (0:01:56)
110: 
...
214: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
215: 475 passed, 1 xfailed, 22 warnings in 95.52s (0:01:35)
216: 
```

---

## 3. Bloco 3 — Docstring de `SerializedWriteQueue` (`storage/connection.py`)

### 3.1 Texto Aplicado em `storage/connection.py:85-95`

```python
85:     Lifecycle:
86:         start() → submit() → ... → stop()
87: 
88:         Lifecycle note: ``SerializedWriteQueue`` is single-use. Calling
89:         ``start()`` after ``stop()`` returns silently without restarting the
90:         worker thread, and any subsequent ``submit()`` raises
91:         ``RuntimeError('SerializedWriteQueue is not running. Call start() first.')``.
92:         When ``stop()`` is called while a job is running, jobs queued before
93:         the stop sentinel that have not yet started are not executed and fail
94:         in ``submit()`` with ``RuntimeError('write worker died: ...')``.
95:     """
```

### 3.2 Prova de Zero Mudança de Comportamento (Comparação de AST sem Docstrings + Testes `T-S1` e `T-S2`)

- A AST de `storage/connection.py` no commit base `3dccf68` e na árvore atual, após remoção exclusiva de nós de docstring (`Expr(Constant(str))` no início de `Module`, `ClassDef`, `FunctionDef` e `AsyncFunctionDef`), produz `ast.dump()` **idêntico byte a byte** (`SHA-256: ff60541a00feecebaf3b8d9a394a8d5a9d3e2e7e2b4ad1cb4c648afe22ab17cf`).
- Nenhum outro arquivo de código de produto (`core/`, `ingestion/`, `interface/`, `services/`, `main.py`) sofreu qualquer modificação (`diff` vazio: `vazio`).

#### Evidência: `scratch/evidencia_4_4f/bloco3_ast_and_tests.txt:1-34`

```text
1: === BLOCO 3 (RODADA 4.4f): PROVA DE AST IDÊNTICA (SEM DOCSTRINGS) E TESTES T-S1 / T-S2 ===
2: Commit base comparado: 3dccf68d3085b553efe27a8175e5c5fcac29048d
3: Arquivo: storage/connection.py
4: AST bruta (com docstrings) alterada: True
5: SHA-256 AST sem docstrings (ANTES):  ff60541a00feecebaf3b8d9a394a8d5a9d3e2e7e2b4ad1cb4c648afe22ab17cf
6: SHA-256 AST sem docstrings (DEPOIS): ff60541a00feecebaf3b8d9a394a8d5a9d3e2e7e2b4ad1cb4c648afe22ab17cf
7: AST sem docstrings IDÊNTICA:         True
8: 
9: --- GIT DIFF DE storage/connection.py ---
10: diff --git a/storage/connection.py b/storage/connection.py
11: index 9febfb2..10d0d54 100644
12: --- a/storage/connection.py
13: +++ b/storage/connection.py
14: @@ -84,6 +84,14 @@ class SerializedWriteQueue:
15: 
16:      Lifecycle:
17:          start() → submit() → ... → stop()
18: +
19: +        Lifecycle note: ``SerializedWriteQueue`` is single-use. Calling
20: +        ``start()`` after ``stop()`` returns silently without restarting the
21: +        worker thread, and any subsequent ``submit()`` raises
22: +        ``RuntimeError('SerializedWriteQueue is not running. Call start() first.')``.
23: +        When ``stop()`` is called while a job is running, jobs queued before
24: +        the stop sentinel that have not yet started are not executed and fail
25: +        in ``submit()`` with ``RuntimeError('write worker died: ...')``.
26:      """
27: 
28:      def __init__(self, db_path: str) -> None:
29: 
30: --- EXECUÇÃO DE tests/test_connection_queue_resilience.py (INCLUINDO T-S1 E T-S2) ---
31: Return Code: 0
32: STDOUT:
33: ============================= test session starts =============================
34: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
```

---

## 4. Bloco 4 — Esclarecimento sobre a Hipótese do `chromadb`

### 4.1 Adendo Adicionado ao Fim de `audits/relatorio_4_4e.md:759-764`

```markdown
759: ---
760: 
761: ## Adendo (2026-11-11 — Rodada 4.4f, Bloco 4): Esclarecimento sobre a Hipótese do `chromadb`
762: 
763: - O erro reproduzido pela colisão de caminhos fixos em execuções paralelas (`sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid` na Sonda 3c do executor em Windows; e `sqlite3.OperationalError: unable to open database file`, `ProjectNotFoundError` e `ValueError: Project not found` na reprodução de 3/4 pares pelo auditor independente em Linux, registrado como `F4-033`) **é diferente** do erro interno intermitente do `chromadb` (`InternalError` / `PanicException` / `sqlite3.OperationalError: no such table: collections`) observado na 1ª tentativa da Rodada 4.4d.
764: - A ligação entre os dois permanece estritamente como **hipótese** e não deve ser afirmada como causa: **o `chromadb` intermitente segue aberto, com causa não provada**.
```

- **Monitoramento pós-isolamento na Rodada 4.4f:** Durante todas as execuções após o isolamento de `F4-033` (20 pares paralelos em verde no Bloco 2 + 10 execuções completas da suíte sequencial nas versões Python 3.10 a 3.14 em ordem padrão e `--reverse`), o `chromadb` `InternalError` intermitente não voltou a se manifestar localmente.

---

## 5. Governança, CI e Conformidade (Regras 11 a 15)

### 5.1 Status dos 6 Jobs do GitHub Actions CI para `3dccf68` (`scratch/evidencia_4_4f/ci_status.txt:1-35`)

```text
1: === GITHUB ACTIONS CI STATUS (RODADA 4.4f) ===
2: 
3: Commit 3dccf68 (3dccf68d3085b553efe27a8175e5c5fcac29048d):
4:   Workflow: CI (run_id=43075938190, status=completed, conclusion=failure)
5:     - Job: Test (Python 3.12) | status=completed | conclusion=success
6:     - Job: Test (Python 3.11) | status=completed | conclusion=success
7:     - Job: Test (Python 3.10) | status=completed | conclusion=failure
8:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=43075938030, status=completed, conclusion=success)
9:     - Job: Windows (3.12) | status=completed | conclusion=success
10:     - Job: Windows (3.14) | status=completed | conclusion=success
11:     - Job: Windows (3.10) | status=completed | conclusion=success
12:   => Resumo 3dccf68: 5/6 jobs verdes (success)
13: 
14: Commit a565c4e (a565c4e9aaebf744515820004728c8e3d635443e):
15:   Workflow: CI (run_id=42863276492, status=completed, conclusion=success)
16:     - Job: Test (Python 3.11) | status=completed | conclusion=success
17:     - Job: Test (Python 3.12) | status=completed | conclusion=success
18:     - Job: Test (Python 3.10) | status=completed | conclusion=success
19:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=42863276453, status=completed, conclusion=success)
20:     - Job: Windows (3.12) | status=completed | conclusion=success
21:     - Job: Windows (3.10) | status=completed | conclusion=success
22:     - Job: Windows (3.14) | status=completed | conclusion=success
23:   => Resumo a565c4e: 6/6 jobs verdes (success)
24: 
25: Commit 9519e16 (9519e16cc6e8bad93240dd51ba118a53c8a085d2):
26:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=42553400294, status=completed, conclusion=success)
27:     - Job: Windows (3.12) | status=completed | conclusion=success
28:     - Job: Windows (3.14) | status=completed | conclusion=success
29:     - Job: Windows (3.10) | status=completed | conclusion=success
30:   Workflow: CI (run_id=42553400260, status=completed, conclusion=success)
31:     - Job: Test (Python 3.12) | status=completed | conclusion=success
32:     - Job: Test (Python 3.11) | status=completed | conclusion=success
33:     - Job: Test (Python 3.10) | status=completed | conclusion=success
34:   => Resumo 9519e16: 6/6 jobs verdes (success)
35: 
```

### 5.2 Resumo de Alterações (`git diff --stat 3dccf68`)

```text
audits/fase4-achados.md                            |   21 +
 audits/fase4-roadmap.md                            |    6 +-
 audits/relatorio_4_4e.md                           |    8 +
 audits/relatorio_4_4f.md                           |  591 +++++++++++
 scratch/check_ci_status_4_4f.py                    |   53 +
 scratch/evidencia_4_4f/bloco3_ast_and_tests.txt    |   68 ++
 scratch/evidencia_4_4f/ci_status.txt               |   85 ++
 .../evidencia_4_4f/consumers_and_guards_check.txt  |   47 +
 .../green_10_pairs_lightweight_vs_stress.txt       |   18 +
 .../green_10_pairs_memory_stress.txt               |   17 +
 scratch/evidencia_4_4f/mutacao_Ta.txt              |  128 +++
 scratch/evidencia_4_4f/mutacao_Tb.txt              |   26 +
 .../red_10_pairs_memory_stress_3dccf68.txt         | 1066 ++++++++++++++++++++
 scratch/evidencia_4_4f/scan_secrets.txt            |    8 +
 scratch/evidencia_4_4f/suite_py310.txt             |  166 +++
 scratch/evidencia_4_4f/suite_py311.txt             |  178 ++++
 scratch/evidencia_4_4f/suite_py312.txt             |  198 ++++
 scratch/evidencia_4_4f/suite_py313.txt             |  210 ++++
 scratch/evidencia_4_4f/suite_py314.txt             |  218 ++++
 scratch/evidencia_4_4f/utf8_check.txt              |   83 ++
 scratch/generate_relatorio_4_4f.py                 |  250 +++++
 scratch/run_bloco2_4_4f_green_and_mutations.py     |  327 ++++++
 scratch/run_bloco2_4_4f_red.py                     |  151 +++
 scratch/run_multiversion_suites_4_4f.py            |   77 ++
 scratch/verify_4_4f_integrity.py                   |   83 ++
 scratch/verify_bloco3_ast_4_4f.py                  |  131 +++
 storage/connection.py                              |    8 +
 tests/memory_stress_test.py                        |    9 +-
 tests/test_lightweight.py                          |    4 +-
 29 files changed, 4229 insertions(+), 6 deletions(-)
```

### 5.3 Verificações Finais de Higiene e Segurança

- **Restrição de código de produto:** Apenas `storage/connection.py` alterado, e unicamente na docstring de `SerializedWriteQueue` (provado por AST sem docstrings idêntica em `scratch/evidencia_4_4f/bloco3_ast_and_tests.txt`).
- **Diretórios residuais:** `tests/_stress_test_workspace` e `tmp_chroma_test` verificados como inexistentes (`False`).
- **Scanner de segredos (Regra 13):** `scratch/tools/scan_secrets.py` executado com `0` achados (`scratch/evidencia_4_4f/scan_secrets.txt`).
- **Codificação UTF-8 sem BOM e sem bytes nulos:** Conferida por script em todos os arquivos de `scratch/evidencia_4_4f/` e `audits/` (`scratch/evidencia_4_4f/utf8_check.txt`).
