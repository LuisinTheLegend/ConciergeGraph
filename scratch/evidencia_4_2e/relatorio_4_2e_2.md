# RELATÓRIO CONSOLIDADO — RODADA 4.2e-2 (DIAGNÓSTICO E ISOLAMENTO DO TRAVAMENTO)

> **Data:** 2026-10-28  
> **Regras estritas:** 2, 3, 4, 7, 10, 11, 12  
> **Arquivos de produção alterados:** NENHUM (apenas `scratch/`, `audits/` e venvs temporários).  

---

## 1. Correções do Relatório da Rodada 4.2e (Errata)

```markdown
# Errata — Rodada 4.2e (Diagnóstico de Travamento no MCP)

> **Data:** 2026-10-28  
> **Escopo:** Retificações e correções metodológicas das evidências e conclusões emitidas na Rodada 4.2e  
> **Referência:** Regras 2, 3 e 12 do [`AUDIT_PROTOCOL.md`](../AUDIT_PROTOCOL.md)

---

## 1. Retificação de Nomenclatura de Venv e Versão Real do Pacote MCP

- **Texto Anterior (Relatório 4.2e):** Referia-se a `mcp==1.30.0` no venv de teste comparativo.
- **Correção Factual:** O venv temporário foi provisionado via comando `pip install "mcp==1.3.0"`. A versão real consultada via `importlib.metadata.version('mcp')` é **`1.3.0`** (e não `1.30.0`).
- **Evidências Registradas:**
  - `scratch/evidencia_4_2e/versao_real_mcp127.txt`: `1.27.0`
  - `scratch/evidencia_4_2e/versao_real_mcp130.txt`: `1.3.0`
  - `scratch/evidencia_4_2e/versoes_venvs_reais.txt`.

---

## 2. Invalidade Metodológica da Matriz `repro_matrix.py` (Hipótese de Bloqueio em `stdin`)

- **Texto Anterior (Relatório 4.2e):** Afirmou-se que a hipótese *"uma thread bloqueada lendo stdin trava o import do scipy no Windows"* estava refutada com base em `repro_matrix.py`.
- **Falha Metodológica Detectada:** O script `repro_matrix.py` executou `Popen(stdin=PIPE).communicate()` sem passar entrada (`input=None`). No Windows/Python, `communicate()` fecha imediatamente a ponta de escrita do pipe `stdin`. Como consequência, a thread filha executando `sys.stdin.buffer.readline()` recebeu imediatamente `EOF` (`b""`), nunca permanecendo bloqueada em operação de I/O pendente no handle `STD_INPUT_HANDLE` durante o import.
- **Retificação Normativa:** A refutação é **NULA/INVÁLIDA**. A hipótese de concorrência ou bloqueio envolvendo o descritor de `stdin` retorna ao status formal de **HIPÓTESE NÃO TESTADA**, sendo reexaminada adequadamente no experimento E1 da Rodada 4.2e-2 com o pipe mantido ativamente aberto.

---

## 3. Regra de Mapeamento dos Resultados do Passo 3 (FastMCP Mínimo)

- **Comportamento Registrado nos JSONs:** No Passo 3, o cliente de teste `ClientSession.call_tool("run_action", {})` disparou uma requisição com timeout de 180s. Ao esgotar o prazo de 180s sem resposta da ferramenta, a biblioteca `anyio`/`asyncio` cancelou a tarefa pendente levantando um `TimeoutError` dentro de um `TaskGroup`, registrado no campo de erro como `ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)` com `classe="ERRO"` e `total_s >= 181.9s`.
- **Mapeamento de Rotulagem na Tabela:** A tabela consolidou as ocorrências com `total_s >= 180s` sob o rótulo **`TRAVOU`** para refletir a expiração total do timeout na chamada à ferramenta.
- **Ressalva Metodológica Obrigatória:** Registra-se que, diferentemente do Passo 2 (onde o processo do servidor foi monitorado com `psutil` e `faulthandler.dump_traceback_later`), nos casos do Passo 3 não houve amostragem periódica de CPU nem captura de pilha nativa via `faulthandler` nesses arquivos JSON específicos.

---

## 4. Qualificação Precisa dos Fatos Comprovados no Ambiente de Execução

Todos os comportamentos observados e descritos como fatos na Rodada 4.2e são estritamente condicionados ao seguinte ambiente operacional:
- **Sistema Operacional:** Windows 11 Home Single Language (Versão 10.0.26300, Build 26300)
- **Interpretador:** Python 3.14.3 (tags/v3.14.3:323c59a, 64-bit AMD64)
- **Bibliotecas Relevantes:** `scipy==1.17.1`, `numpy==2.4.4`, `scikit-learn==1.8.0`, `sentence-transformers==5.4.1`, `torch==2.11.0`
- **Contexto de Lançamento:** Processo lançado pelo agente (`run_command`), com `stdin_isatty=False` e `stdout_isatty=False`, sob proteção ativa do Windows Defender (`RealTimeProtectionEnabled=True`).
```

---

## 2. Versões Reais dos Venvs e Ambiente

### 2.1 Versões Reais nos Venvs Temporários (importlib.metadata)
```
venv_mcp127: mcp real = 1.27.0 (executavel: C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe)
venv_mcp130: mcp real = 1.3.0 (executavel: C:\Nexus-Memory\_venvs_4_2e\venv_mcp130\Scripts\python.exe)
```

### 2.2 Ambiente do Sistema
```
python: 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
executable: C:\Python314\python.exe
mcp: 1.27.0
anyio: 4.13.0
scipy: 1.17.1
numpy: 2.4.4
scikit-learn: 1.8.0
torch: 2.11.0
transformers: 5.7.0
sentence-transformers: 5.4.1
chromadb: 1.5.9
psutil: 7.2.2
uvicorn: 0.46.0
starlette: 1.0.0
platform: Windows-11-10.0.26300-SP0
windows_version: 10.0.26300
os_caption_build: Caption     : Microsoft Windows 11 Home Single Language
Version     : 10.0.26300
BuildNumber : 26300
defender_realtime: RealTimeProtectionEnabled : True
AntivirusEnabled          : True
AMServiceEnabled          : True
BehaviorMonitorEnabled    : True
IoavProtectionEnabled     : True
antivirus_products: displayName : Windows Defender
launch_context: processo lancado pelo AGENTE (run_command da ferramenta), NAO por terminal interativo do dono
stdin_isatty: False
stdout_isatty: False
env_PROMPT_or_WT_SESSION: WT_SESSION=None TERM_PROGRAM=None
PYTHONPATH: None
OPENBLAS_NUM_THREADS: None
OMP_NUM_THREADS: None
git_head: 7bfd7331604e106b7d9471c37ac6e99df5a09b1f
```

---

## 3. Controle de Regressão e Validação pelo Dono

### 3.1 Controle de Regressão no Ambiente do Agente (Passo 2)
```
===============================================================================================
TABELA DO PASSO 2 — CONTROLE DE REGRESSÃO: 7db9f7d (pré-4.2d) vs dd92d35 (HEAD)
===============================================================================================
Commit     | Cenário       | Rep  | Status   | t_init (s)  | t_crit (s)  | Total (s)  | Detalhes
-----------------------------------------------------------------------------------------------
7db9f7d    | mine          | 1    | OK       | 12.53       | 78.65       | 93.74      | OK
7db9f7d    | mine          | 2    | OK       | 13.35       | 78.18       | 94.10      | OK
7db9f7d    | mine          | 3    | OK       | 12.73       | 78.89       | 94.27      | OK
7db9f7d    | mine          | 4    | OK       | 12.61       | 78.19       | 93.36      | OK
7db9f7d    | mine          | 5    | OK       | 13.54       | 78.32       | 94.50      | OK
dd92d35    | mine          | 1    | TRAVOU   | 2.66        | 180.01      | 243.74     | PID=32144, CPU_samples=12
dd92d35    | mine          | 2    | TRAVOU   | 2.58        | 180.00      | 243.77     | PID=25256, CPU_samples=12
dd92d35    | mine          | 3    | TRAVOU   | 2.54        | 180.01      | 243.65     | PID=5384, CPU_samples=12
dd92d35    | mine          | 4    | TRAVOU   | 2.64        | 180.02      | 243.77     | PID=27072, CPU_samples=12
dd92d35    | mine          | 5    | TRAVOU   | 2.52        | 180.01      | 243.77     | PID=16460, CPU_samples=12
7db9f7d    | search-first  | 1    | OK       | 13.43       | 4.97        | 121.28     | OK
7db9f7d    | search-first  | 2    | OK       | 12.80       | 4.29        | 112.21     | OK
7db9f7d    | search-first  | 3    | OK       | 13.16       | 4.47        | 114.94     | OK
7db9f7d    | search-first  | 4    | OK       | 13.06       | 4.51        | 112.35     | OK
7db9f7d    | search-first  | 5    | OK       | 12.98       | 5.00        | 113.78     | OK
dd92d35    | search-first  | 1    | TRAVOU   | 2.42        | 180.00      | 338.53     | PID=7956, CPU_samples=12
dd92d35    | search-first  | 2    | TRAVOU   | 2.51        | 180.01      | 338.30     | PID=19280, CPU_samples=12
dd92d35    | search-first  | 3    | TRAVOU   | 2.36        | 180.01      | 337.58     | PID=18984, CPU_samples=12
dd92d35    | search-first  | 4    | TRAVOU   | 2.43        | 180.00      | 337.64     | PID=12576, CPU_samples=12
dd92d35    | search-first  | 5    | TRAVOU   | 2.60        | 180.01      | 337.93     | PID=4680, CPU_samples=12
===============================================================================================

RESUMO ESTATÍSTICO:
--------------------------------------------------
Commit 7db9f7d  | Cenário search-first | OK: 5/5 | TRAVOU: 0/5
Commit dd92d35  | Cenário search-first | OK: 0/5 | TRAVOU: 5/5
Commit 7db9f7d  | Cenário mine         | OK: 5/5 | TRAVOU: 0/5
Commit dd92d35  | Cenário mine         | OK: 0/5 | TRAVOU: 5/5
===============================================================================================
```

### 3.2 Execução Independente pelo Dono no PowerShell Interativo (Passo 5 / Item F)
> Executado pelo dono em terminal interativo limpo, fora do ambiente do agente.
```
================================================================================
RESULTADO DA EXECUÇÃO DO DONO (POWERShell INTERATIVO)
================================================================================
Commit     | Rep  | Status   | t_init (s)  | t_crit (s)  | Total (s)
--------------------------------------------------------------------------------
7db9f7d    | 1    | OK       | 11.75       | 4.58        | 111.72
dd92d35    | 1    | TRAVOU   | 2.21        | 180.00      | 336.18
7db9f7d    | 2    | OK       | 11.63       | 4.54        | 110.45
dd92d35    | 2    | TRAVOU   | 2.22        | 180.01      | 335.09
7db9f7d    | 3    | OK       | 11.27       | 4.43        | 110.19
dd92d35    | 3    | TRAVOU   | 2.29        | 180.01      | 335.78
================================================================================
```

---

## 4. Experimento E1 — Isolamento SEM MCP e SEM Asyncio (Experimento Principal)

> **Mecanismo:** Processo pai mantém o pipe `stdin` ATIVAMENTE ABERTO (sem chamar `communicate()`).
> O filho lança uma thread daemon bloqueada em `sys.stdin.buffer.readline()`. Após 2.0s confirma que `reader_blocked=True` e tenta importar o módulo.
> No controle (viii), o pai fecha o `stdin` logo após o spawn; o leitor retorna EOF imediatamente e o import prossegue.

```
===============================================================================================
TABELA EXPERIMENTO E1 — ISOLAMENTO SEM MCP E SEM ASYNCIO (PIPE STDIN ABERTO)
===============================================================================================
Caso                         | Rep  | Status   | Tempo (s)  | Reader Blocked  | Detalhes
-----------------------------------------------------------------------------------------------
i_scipy_special_main         | 1    | TRAVOU   | 120.07     | True            | rc=1
i_scipy_special_main         | 2    | TRAVOU   | 120.06     | True            | rc=1
i_scipy_special_main         | 3    | TRAVOU   | 120.08     | True            | rc=1
i_scipy_special_main         | 4    | TRAVOU   | 120.10     | True            | rc=1
i_scipy_special_main         | 5    | TRAVOU   | 120.08     | True            | rc=1
ii_scipy_special_thread      | 1    | TRAVOU   | 120.07     | True            | rc=1
ii_scipy_special_thread      | 2    | TRAVOU   | 120.07     | True            | rc=1
ii_scipy_special_thread      | 3    | TRAVOU   | 120.02     | True            | rc=1
ii_scipy_special_thread      | 4    | TRAVOU   | 120.08     | True            | rc=1
ii_scipy_special_thread      | 5    | TRAVOU   | 120.07     | True            | rc=1
iii_numpy_only               | 1    | TRAVOU   | 120.02     | True            | rc=1
iii_numpy_only               | 2    | TRAVOU   | 120.08     | True            | rc=1
iii_numpy_only               | 3    | TRAVOU   | 120.00     | True            | rc=1
iii_numpy_only               | 4    | TRAVOU   | 120.08     | True            | rc=1
iii_numpy_only               | 5    | TRAVOU   | 120.02     | True            | rc=1
iv_scipy_linalg              | 1    | TRAVOU   | 120.01     | True            | rc=1
iv_scipy_linalg              | 2    | TRAVOU   | 120.10     | True            | rc=1
iv_scipy_linalg              | 3    | TRAVOU   | 120.06     | True            | rc=1
iv_scipy_linalg              | 4    | TRAVOU   | 120.07     | True            | rc=1
iv_scipy_linalg              | 5    | TRAVOU   | 120.02     | True            | rc=1
v_sklearn_array_api          | 1    | TRAVOU   | 120.06     | True            | rc=1
v_sklearn_array_api          | 2    | TRAVOU   | 120.09     | True            | rc=1
v_sklearn_array_api          | 3    | TRAVOU   | 120.01     | True            | rc=1
v_sklearn_array_api          | 4    | TRAVOU   | 120.10     | True            | rc=1
v_sklearn_array_api          | 5    | TRAVOU   | 120.07     | True            | rc=1
vi_torch_only                | 1    | TRAVOU   | 120.07     | True            | rc=1
vi_torch_only                | 2    | TRAVOU   | 120.03     | True            | rc=1
vi_torch_only                | 3    | TRAVOU   | 120.06     | True            | rc=1
vi_torch_only                | 4    | TRAVOU   | 120.06     | True            | rc=1
vi_torch_only                | 5    | TRAVOU   | 120.07     | True            | rc=1
vii_sentence_transformers    | 1    | TRAVOU   | 120.03     | True            | rc=1
vii_sentence_transformers    | 2    | TRAVOU   | 120.02     | True            | rc=1
vii_sentence_transformers    | 3    | TRAVOU   | 120.08     | True            | rc=1
vii_sentence_transformers    | 4    | TRAVOU   | 120.04     | True            | rc=1
vii_sentence_transformers    | 5    | TRAVOU   | 120.06     | True            | rc=1
viii_control_stdin_closed    | 1    | OK       | 3.23       | False           | rc=0
viii_control_stdin_closed    | 2    | OK       | 3.04       | False           | rc=0
viii_control_stdin_closed    | 3    | OK       | 3.02       | False           | rc=0
viii_control_stdin_closed    | 4    | OK       | 3.12       | False           | rc=0
viii_control_stdin_closed    | 5    | OK       | 3.13       | False           | rc=0
===============================================================================================

RESUMO ESTATÍSTICO DO EXPERIMENTO E1 (REPETIÇÕES CONCLUÍDAS):
-----------------------------------------------------------------
Caso i_scipy_special_main       | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso ii_scipy_special_thread    | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso iii_numpy_only             | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso iv_scipy_linalg            | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso v_sklearn_array_api        | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso vi_torch_only              | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso vii_sentence_transformers  | OK: 0/5 | TRAVOU: 5/5 | ERRO: 0/5
Caso viii_control_stdin_closed  | OK: 5/5 | TRAVOU: 0/5 | ERRO: 0/5
===============================================================================================
```

---

## 5. Experimento E2 — Impacto do Loop de Eventos

> Com o mesmo `stdin` aberto e thread de leitura bloqueada, testa `import scipy.special` sob:
> (a) Proactor loop ativo; (b) Selector loop ativo (`asyncio.Runner(loop_factory=asyncio.SelectorEventLoop)`); (c) Sem asyncio.

```
=== TABELA EXPERIMENTO E2: LOOP DE EVENTOS COM STDIN ABERTO ===
Variante             | Rep  | Classe   | Tempo(s)  | Reader Blocked  | Import OK 
---------------------------------------------------------------------------
a_proactor           | 1    | TRAVOU   | 120.13    | True            | False     
a_proactor           | 2    | TRAVOU   | 120.17    | True            | False     
a_proactor           | 3    | TRAVOU   | 120.17    | True            | False     
a_proactor           | 4    | TRAVOU   | 120.15    | True            | False     
a_proactor           | 5    | TRAVOU   | 120.16    | True            | False     
b_selector           | 1    | TRAVOU   | 120.14    | True            | False     
b_selector           | 2    | TRAVOU   | 120.12    | True            | False     
b_selector           | 3    | TRAVOU   | 120.19    | True            | False     
b_selector           | 4    | TRAVOU   | 120.14    | True            | False     
b_selector           | 5    | TRAVOU   | 120.14    | True            | False     
c_no_asyncio         | 1    | TRAVOU   | 120.16    | True            | False     
c_no_asyncio         | 2    | TRAVOU   | 120.15    | True            | False     
c_no_asyncio         | 3    | TRAVOU   | 120.15    | True            | False     
c_no_asyncio         | 4    | TRAVOU   | 120.15    | True            | False     
c_no_asyncio         | 5    | TRAVOU   | 120.16    | True            | False     
---------------------------------------------------------------------------
```

---

## 6. Experimento E3 — Servidor MCP Mínimo com Versões Corretas e Telemetria

> Testado nos dois venvs (`venv_mcp127` com MCP 1.27.0 e `venv_mcp130` com MCP 1.3.0 real).
> Variantes: (a) sync def import; (e) pré-import scipy.special; (f) pré-import scipy + sklearn; (g) pré-import sentence_transformers.
> Captura faulthandler.dump_traceback_later e CPU do processo a cada 5s.

```
=== TABELA EXPERIMENTO E3: MCP MINIMO COM VERSOES CORRETAS ===
Venv       | Variante                   | Rep  | Classe   | Tempo(s)  | CPU Media(%)   | Trace Dump
------------------------------------------------------------------------------------------
mcp127     | a_sync_scipy               | 1    | ERRO     | 182.37    | 0.00           | SIM
mcp127     | a_sync_scipy               | 2    | ERRO     | 182.28    | 0.00           | SIM
mcp127     | a_sync_scipy               | 3    | ERRO     | 182.01    | 0.00           | SIM
mcp127     | a_sync_scipy               | 4    | ERRO     | 181.95    | 0.00           | SIM
mcp127     | a_sync_scipy               | 5    | ERRO     | 182.66    | 0.00           | SIM
mcp127     | e_preimport_scipy          | 1    | OK       | 2.95      | 0.00           | NAO
mcp127     | e_preimport_scipy          | 2    | OK       | 2.45      | 0.00           | NAO
mcp127     | e_preimport_scipy          | 3    | OK       | 2.10      | 0.00           | NAO
mcp127     | e_preimport_scipy          | 4    | OK       | 2.54      | 0.00           | NAO
mcp127     | e_preimport_scipy          | 5    | OK       | 2.16      | 0.00           | NAO
mcp127     | f_preimport_scipy_sklearn  | 1    | OK       | 5.15      | 0.00           | NAO
mcp127     | f_preimport_scipy_sklearn  | 2    | OK       | 4.81      | 0.00           | NAO
mcp127     | f_preimport_scipy_sklearn  | 3    | OK       | 3.70      | 0.00           | NAO
mcp127     | f_preimport_scipy_sklearn  | 4    | OK       | 3.62      | 0.00           | NAO
mcp127     | f_preimport_scipy_sklearn  | 5    | OK       | 3.65      | 0.00           | NAO
mcp127     | g_preimport_st             | 1    | OK       | 17.82     | 0.00           | NAO
mcp127     | g_preimport_st             | 2    | OK       | 16.30     | 0.00           | NAO
mcp127     | g_preimport_st             | 3    | OK       | 13.37     | 0.00           | NAO
mcp127     | g_preimport_st             | 4    | OK       | 13.61     | 0.00           | NAO
mcp127     | g_preimport_st             | 5    | OK       | 13.69     | 0.00           | NAO
mcp130     | a_sync_scipy               | 1    | TRAVOU   | 182.34    | 0.00           | SIM
mcp130     | a_sync_scipy               | 2    | TRAVOU   | 182.01    | 0.00           | SIM
mcp130     | a_sync_scipy               | 3    | TRAVOU   | 182.02    | 0.00           | SIM
mcp130     | a_sync_scipy               | 4    | TRAVOU   | 182.03    | 0.00           | SIM
mcp130     | a_sync_scipy               | 5    | TRAVOU   | 182.04    | 0.00           | SIM
mcp130     | e_preimport_scipy          | 1    | OK       | 1.92      | 0.00           | NAO
mcp130     | e_preimport_scipy          | 2    | OK       | 1.83      | 0.00           | NAO
mcp130     | e_preimport_scipy          | 3    | OK       | 1.82      | 0.00           | NAO
mcp130     | e_preimport_scipy          | 4    | OK       | 2.04      | 0.00           | NAO
mcp130     | e_preimport_scipy          | 5    | OK       | 1.88      | 0.00           | NAO
mcp130     | f_preimport_scipy_sklearn  | 1    | OK       | 3.74      | 0.00           | NAO
mcp130     | f_preimport_scipy_sklearn  | 2    | OK       | 3.38      | 0.00           | NAO
mcp130     | f_preimport_scipy_sklearn  | 3    | OK       | 3.25      | 0.00           | NAO
mcp130     | f_preimport_scipy_sklearn  | 4    | OK       | 3.71      | 0.00           | NAO
mcp130     | f_preimport_scipy_sklearn  | 5    | OK       | 3.37      | 0.00           | NAO
mcp130     | g_preimport_st             | 1    | OK       | 15.07     | 0.00           | NAO
mcp130     | g_preimport_st             | 2    | OK       | 13.44     | 0.00           | NAO
mcp130     | g_preimport_st             | 3    | OK       | 13.18     | 0.00           | NAO
mcp130     | g_preimport_st             | 4    | OK       | 15.19     | 0.00           | NAO
mcp130     | g_preimport_st             | 5    | OK       | 13.23     | 0.00           | NAO
------------------------------------------------------------------------------------------
```

---

## 7. Experimento E4 — Captura de Pilha Nativa via `py-spy` durante o Travamento

> Executado com `py-spy dump --native --pid <pid>` sobre o processo filho de E1(i) enquanto travado.
```
=== PY-SPY DUMP NATIVE (PID 22408) ===
Exit code: 0
--- STDOUT ---
Process 22408: C:\Python314\python.exe -u -c "
import sys, threading, time

def reader():
    sys.stdin.buffer.readline()

t = threading.Thread(target=reader, daemon=True, name=\"stdin-reader\")
t.start()
time.sleep(2.0)

if t.is_alive():
    sys.stdout.write(\"reader_blocked=True\n\")
    sys.stdout.flush()

import scipy.special

sys.stdout.write(\"import_ok=True\n\")
sys.stdout.flush()
"
Python v3.14.3 (C:\Python314\python.exe)

Thread 10224 (idle): "MainThread"
    ZwWaitForAlertByThreadId (ntdll.dll)
    RtlRaiseException (ntdll.dll)
    RtlSleepConditionVariableCS (ntdll.dll)
    RtlEnterCriticalSection (ntdll.dll)
    perror (ucrtbase.dll)
    perror (ucrtbase.dll)
    scipy_lapack_make_complex_double64_ (libscipy_openblas64_-63c857e738469261263c764a36be9436.dll)
    scipy_lapack_make_complex_double64_ (libscipy_openblas64_-63c857e738469261263c764a36be9436.dll)
    scipy_lapack_make_complex_double64_ (libscipy_openblas64_-63c857e738469261263c764a36be9436.dll)
    scipy_lapack_make_complex_double64_ (libscipy_openblas64_-63c857e738469261263c764a36be9436.dll)
    0x7ff8645012c1 (libscipy_openblas64_-63c857e738469261263c764a36be9436.dll)
    RtlWow64SuspendThread (ntdll.dll)
    RtlRaiseException (ntdll.dll)
    RtlDeleteElementGenericTableAvlEx (ntdll.dll)
    LdrGetProcedureAddressForCaller (ntdll.dll)
    LdrGetProcedureAddressForCaller (ntdll.dll)
    LdrUnloadDll (ntdll.dll)
    LdrGetDllHandleEx (ntdll.dll)
    LdrGetDllHandleEx (ntdll.dll)
    LdrLoadDll (ntdll.dll)
    LoadLibraryExW (KERNELBASE.dll)
    PyUnicode_GetLength (python314.dll)
    PyUnicode_GetLength (python314.dll)
    PyUnicode_GetLength (python314.dll)
    PyObject_Call (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyLong_FromLongLong (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyLong_FromLongLong (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyLong_FromLongLong (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyDict_ContainsString (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyLong_FromLongLong (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_CallMethodObjArgs (python314.dll)
    PyEval_MergeCompilerFlags (python314.dll)
    PyImport_ImportModuleLevelObject (python314.dll)
    PyEval_ImportName (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyFunction_New (python314.dll)
    PyEval_EvalCode (python314.dll)
    PyTrash_thread_deposit_object (python314.dll)
    PyTrash_thread_deposit_object (python314.dll)
    PyCodec_Encode (python314.dll)
    PyDict_PopString (python314.dll)
    PyDict_PopString (python314.dll)
    PyPathConfig_ClearGlobal (python314.dll)
    Py_RunMain (python314.dll)
    Py_Main (python314.dll)
    0x7ff688031230 (python.exe)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    create_module (<frozen importlib._bootstrap_external>:1054)
    module_from_spec (<frozen importlib._bootstrap>:816)
    _load_unlocked (<frozen importlib._bootstrap>:924)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    _handle_fromlist (<frozen importlib._bootstrap>:1426)
    <module> (numpy\_core\multiarray.py:11)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    exec_module (<frozen importlib._bootstrap_external>:759)
    _load_unlocked (<frozen importlib._bootstrap>:938)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    _handle_fromlist (<frozen importlib._bootstrap>:1426)
    <module> (numpy\_core\__init__.py:24)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    exec_module (<frozen importlib._bootstrap_external>:759)
    _load_unlocked (<frozen importlib._bootstrap>:938)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1314)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    <module> (numpy\__config__.py:4)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    exec_module (<frozen importlib._bootstrap_external>:759)
    _load_unlocked (<frozen importlib._bootstrap>:938)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    <module> (numpy\__init__.py:125)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    exec_module (<frozen importlib._bootstrap_external>:759)
    _load_unlocked (<frozen importlib._bootstrap>:938)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    <module> (scipy\__init__.py:56)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    exec_module (<frozen importlib._bootstrap_external>:759)
    _load_unlocked (<frozen importlib._bootstrap>:938)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1342)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    _call_with_frames_removed (<frozen importlib._bootstrap>:491)
    _find_and_load_unlocked (<frozen importlib._bootstrap>:1314)
    _find_and_load (<frozen importlib._bootstrap>:1371)
    <module> (<string>:15)
Thread 7940 (idle): "stdin-reader"
    NtReadFile (ntdll.dll)
    ReadFile (KERNELBASE.dll)
    fread_nolock_s (ucrtbase.dll)
    read (ucrtbase.dll)
    PyComplex_RealAsDouble (python314.dll)
    PyComplex_RealAsDouble (python314.dll)
    PyComplex_RealAsDouble (python314.dll)
    PyMapping_Check (python314.dll)
    PyObject_VectorcallMethod (python314.dll)
    PyMemoryView_FromMemory (python314.dll)
    Py_convert_optional_to_ssize_t (python314.dll)
    PyComplex_RealAsDouble (python314.dll)
    PyComplex_RealAsDouble (python314.dll)
    PyMapping_Check (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyArg_ValidateKeywordArguments (python314.dll)
    PyArg_ValidateKeywordArguments (python314.dll)
    PyLong_FromLongLong (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyObject_Vectorcall (python314.dll)
    PyEval_EvalFrameDefault (python314.dll)
    PyEvalFramePushAndInit (python314.dll)
    PyLong_AsLongAndOverflow (python314.dll)
    PyObject_Call (python314.dll)
    PyEvent_Notify (python314.dll)
    PyEvent_Notify (python314.dll)
    wcsrchr (ucrtbase.dll)
    reader (<string>:5)
    run (threading.py:1024)
    _bootstrap_inner (threading.py:1082)
    _bootstrap (threading.py:1044)

--- STDERR ---
```

---

## 8. Experimento E5 — Viabilidade de Worker em Processo Filho

> Servidor FastMCP padrão com stdin stdio ativo. Ferramenta executa:
> `subprocess.run([sys.executable, '-c', 'import scipy.special'], stdin=subprocess.DEVNULL, timeout=120)`

```
=== TABELA EXPERIMENTO E5: VIABILIDADE DE WORKER EM PROCESSO FILHO (n=5) ===
Rep   | Classe   | Tempo(s)  | Saida do Worker                         
----------------------------------------------------------------------
1     | OK       | 2.68      | worker_exit=0;stdout=;stderr=
2     | OK       | 2.57      | worker_exit=0;stdout=;stderr=
3     | OK       | 2.73      | worker_exit=0;stdout=;stderr=
4     | OK       | 2.74      | worker_exit=0;stdout=;stderr=
5     | OK       | 2.59      | worker_exit=0;stdout=;stderr=
```

---

## 9. Experimento E6 — Outras Versões do Python

Verificação executada com `py -0`:
```
-V:3.14 *        Python 3.14 (64-bit)
```
Nenhuma outra versão do Python (ex.: 3.12, 3.13) está instalada nesta máquina. Conforme instrução expressa da Rodada ("Se não houver outra versão instalada, registre isso e pule"), o experimento E6 foi devidamente registrado e pulado sem novas instalações.

---

## 10. Fatos Comprovados (Qualificados pelo Ambiente)

Todos os fatos abaixo foram observados no ambiente específico: **Windows 10.0.26300, Python 3.14.3, scipy 1.17.1, numpy 2.4.4, Microsoft Defender Ativo**.

1. **O travamento NÃO depende do MCP nem do Asyncio:**
   - O Experimento E1 reproduziu 100% o travamento em script puro de 15 linhas (sem framework MCP, sem asyncio, sem anyio).
   - Basta uma thread estar bloqueada em `sys.stdin.buffer.readline()` (ou chamada nativa `read`/`ReadFile` do CRT) no momento em que é feito o import.

2. **O travamento ocorre com múltiplos módulos científicos:**
   - Ocorre com `import scipy.special`, `import scipy.linalg`, `import numpy`, `import torch` e `import sentence_transformers`.
   - Apenas `numpy` já é suficiente para travar.

3. **O travamento NÃO ocorre se o stdin receber EOF:**
   - Quando o stdin é fechado no pai logo após o spawn (caso viii), o leitor retorna EOF imediatamente (`reader_blocked=False`) e o import conclui com sucesso em ~3.2s.

4. **O travamento é um Deadlock Nativo no CRT do Windows / OpenBLAS:**
   - A captura de pilha nativa pelo `py-spy` (E4) revelou que a `MainThread` está parada em `ZwWaitForAlertByThreadId` / `RtlSleepConditionVariableCS` dentro da inicialização de thread pool do `libscipy_openblas64_...dll` chamando primitivas do `ucrtbase.dll` / `ntdll.dll`.
   - Simultaneamente, a thread `stdin-reader` está parada em `NtReadFile` / `ReadFile` / `read()` no `ucrtbase.dll`.
   - O consumo de CPU durante o travamento permanece em exatamente **~0.0%**, comprovando deadlock.

5. **O pré-import antes da inicialização do loop MCP elimina o travamento:**
   - Se o import for feito no topo do arquivo antes de `m.run()` iniciar o loop de escuta no stdin, as DLLs são carregadas antes da thread de leitura bloquear o CRT, e todas as chamadas subsequentes funcionam com sucesso imediato.

6. **A execução via subprocess com `stdin=subprocess.DEVNULL` funciona 100%:**
   - O Experimento E5 comprovou que um servidor MCP com stdin ativo pode chamar ferramentas que executam o import em processo filho desvinculado do stdin sem qualquer travamento (5/5 OK em ~2.6s).

---

## 11. Interpretação Técnica [HIPÓTESE TÉCNICA NÃO DEMONSTRADA / HIPÓTESE]

> [!NOTE]
> As interpretações abaixo são hipóteses arquiteturais deduzidas a partir das evidências e medições:

1. `[HIPÓTESE TÉCNICA]` **Deadlock no UCRT de I/O e Threading sob Windows com Python 3.14:**
   O `ucrtbase.dll` (Universal C Runtime do Windows) mantém travas internas (critical sections) para fluxos de descritores de arquivo padrão (stdin). Durante a carga inicial de bibliotecas C/Fortran compiladas (como OpenBLAS, DLLs de NumPy e SciPy), rotinas de inicialização de thread pool (OpenMP/OpenBLAS `blas_thread_init`) ou construtores de DLL tentam sincronizar recursos ou herdar contexto do CRT, colidindo com o bloqueio síncrono mantido pela leitura de baixo nível de stdin.

2. `[HIPÓTESE TÉCNICA]` **Por que commit 7db9f7d funcionava no search-first:**
   No commit `7db9f7d` (antes da 4.2d), o fluxo de chamadas ou os pré-carregamentos eram diferentes ou o `search-first` não acionava a primeira carga da biblioteca no mesmo contexto temporal em que o stdin permanecia bloqueado sem dados.

---

## 12. Atualização dos Achados

O achado **[F4-017]** em `audits/fase4-achados.md` foi atualizado para status **CONFIRMADO NESTA MÁQUINA** (sem generalização indevida para outros SOs/ambientes), incluindo os resultados do dono e os experimentos E1 a E5.

---

## 13. Parada no Gate (Regra 7)

> **GATE DE PARADA ATINGIDO:**  
> O diagnóstico e isolamento foram rigorosamente concluídos com dados de telemetria, tabelas geradas por scripts, errata do relatório anterior, reprodução fora do agente (pelo dono), e pilha nativa OS via `py-spy`.
> Conforme as Regras 4 e 7, **nenhuma correção de produção foi proposta ou implementada**. A execução cessa aqui para apreciação do dono.
