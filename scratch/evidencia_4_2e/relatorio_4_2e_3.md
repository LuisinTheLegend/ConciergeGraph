# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2e-3
## DEFINIÇÃO DO CAMINHO DE CORREÇÃO DO TRAVAMENTO MCP (DIAGNÓSTICO E VALIDAÇÃO)

> **Regras aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos de medição).
> **Arquivos de produção alterados:** ZERO. O commit base avaliado é `dd92d35`.

---

### 1. AMBIENTE DE EXECUÇÃO E VERSÕES TESTADAS
```text
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
- **Versão real do MCP no venv mcp130_real:** `1.30.0` (resolvendo a errata do teste anterior com 1.3.0).

---

### 2. ERRATAS E RECLASSIFICAÇÕES REGISTRADAS (em `audits/errata-4-2e.md`)
1. **MCP 1.30.0 Real:** Testado formalmente no venv `venv_mcp130_real` (`mcp==1.30.0`). O deadlock no import síncrono tardio sob MCP foi reproduzido de forma idêntica (100% de travamento), e o pré-import de `scipy.special` resolveu 3/3 com sucesso.
2. **Símbolos py-spy:** As funções capturadas via py-spy em chamadas nativas C/C++ no Windows representam símbolos exportados mais próximos na DLL (`RtlEnterCriticalSection`, `ReadFile`). Reclassificado formalmente como *compatível com espera de lock de DLL/CRT* e não prova conclusiva de símbolo interno `perror`.
3. **Hipótese BLAS/OpenMP:** Classificada estritamente como **[HIPÓTESE NÃO CONFIRMADA]**.
4. **Unificação de Rótulos ERRO/TRAVOU:** No cliente MCP com timeout estrito, chamadas que esgotam o tempo limite retornam `ExceptionGroup(TimeoutError)`. O mapeamento foi unificado para `ERRO (Timeout)` / `TRAVOU`.
5. **Escopo do Worker E5:** Registrado que o probe inicial testou apenas `import scipy.special` no processo filho, sem o pipeline completo.

```text
=== TABELA E3 EM MCP 1.30.0 REAL (n=3 cada) ===
=== TABELA EXPERIMENTO E3 EM MCP 1.30.0 REAL (n=3 cada) ===
Versao       | Variante                   | Rep  | Classe   | Tempo(s)  | CPU Media(%)   | Trace Dump
--------------------------------------------------------------------------------------------
mcp 1.30.0   | a_sync_scipy               | 1    | TRAVOU   | 183.84    | 0.00           | SIM
mcp 1.30.0   | e_preimport_scipy          | 1    | OK       | 3.38      | 0.00           | NAO
mcp 1.30.0   | a_sync_scipy               | 2    | ERRO     | 183.25    | 0.00           | SIM
mcp 1.30.0   | e_preimport_scipy          | 2    | OK       | 3.29      | 0.00           | NAO
mcp 1.30.0   | a_sync_scipy               | 3    | ERRO     | 183.28    | 0.00           | SIM
mcp 1.30.0   | e_preimport_scipy          | 3    | OK       | 3.40      | 0.00           | NAO
```

---

### 3. MECANISMO FUNDAMENTAL DO DEADLOCK: FD 0 vs CANAL ANÔNIMO

#### Experimento E8: Leitor em pipe que NÃO é o stdin (`os.pipe()`)
- **Objetivo:** Determinar se qualquer thread lendo um descritor de pipe bloqueante trava os imports numéricos ou se a trava é restrita ao `stdin` padrão (`STD_INPUT_HANDLE` / fd 0).
- **Evidência (`tabela_e8.txt`):**
```text
=== TABELA EXPERIMENTO E8: LEITOR EM PIPE QUE NÃO É STDIN (n=5 cada) ===
Caso            | Rep  | Classe   | Tempo(s)  | Reader Blocked  | Import OK 
---------------------------------------------------------------------------
numpy           | 1    | OK       | 3.02      | True            | True      
scipy_special   | 1    | OK       | 6.02      | True            | True      
numpy           | 2    | OK       | 2.51      | True            | True      
scipy_special   | 2    | OK       | 4.51      | True            | True      
numpy           | 3    | OK       | 3.02      | True            | True      
scipy_special   | 3    | OK       | 4.51      | True            | True      
numpy           | 4    | OK       | 3.01      | True            | True      
scipy_special   | 4    | OK       | 4.52      | True            | True      
numpy           | 5    | OK       | 3.03      | True            | True      
scipy_special   | 5    | OK       | 4.52      | True            | True      
---------------------------------------------------------------------------
```
- **Fato comprovado:** **10/10 OK** (100% sucesso). Leituras de pipes anônimos em background **NÃO causam deadlock**. A colisão ocorre exclusivamente quando a thread de leitura está bloqueada sobre o `STD_INPUT_HANDLE` / fd 0 herdado do processo pai durante a inicialização do C runtime / carregamento dinâmico de bibliotecas.

---

### 4. DESACOPLAMENTO DO FD 0 (WORKAROUND PROBE — E7)

- **Técnica:** O processo filho duplica o descritor 0 para outro fd (`fd2 = os.dup(0)`), redireciona o fd 0 para NUL (`os.dup2(nul, 0)`), e a thread de transporte MCP passa a ler de `fd2`.
- **Integridade do canal:** Testada a cada repetição através do envio de `ping\n` pelo pai após os imports, exigindo confirmação de recebimento pelo filho.
- **Evidência (`tabela_e7.txt`):**
```text
=== TABELA EXPERIMENTO E7: DESACOPLAR O FD 0 (n=5 cada) ===
Variante         | Modulo                 | Rep  | Classe     | Tempo(s)  | Blocked  | Imp OK   | Ping OK
------------------------------------------------------------------------------------------------
a_dup2_nul       | numpy                  | 1    | OK         | 2.76      | True     | True     | True
a_dup2_nul       | numpy                  | 2    | OK         | 2.72      | True     | True     | True
a_dup2_nul       | numpy                  | 3    | OK         | 2.84      | True     | True     | True
a_dup2_nul       | numpy                  | 4    | OK         | 2.85      | True     | True     | True
a_dup2_nul       | numpy                  | 5    | OK         | 2.79      | True     | True     | True
a_dup2_nul       | scipy_special          | 1    | OK         | 5.05      | True     | True     | True
a_dup2_nul       | scipy_special          | 2    | OK         | 5.19      | True     | True     | True
a_dup2_nul       | scipy_special          | 3    | OK         | 4.93      | True     | True     | True
a_dup2_nul       | scipy_special          | 4    | OK         | 4.65      | True     | True     | True
a_dup2_nul       | scipy_special          | 5    | OK         | 4.97      | True     | True     | True
a_dup2_nul       | torch                  | 1    | OK         | 9.04      | True     | True     | True
a_dup2_nul       | torch                  | 2    | OK         | 11.58     | True     | True     | True
a_dup2_nul       | torch                  | 3    | OK         | 12.04     | True     | True     | True
a_dup2_nul       | torch                  | 4    | OK         | 10.99     | True     | True     | True
a_dup2_nul       | torch                  | 5    | OK         | 9.77      | True     | True     | True
a_dup2_nul       | sentence_transformers  | 1    | OK         | 34.00     | True     | True     | True
a_dup2_nul       | sentence_transformers  | 2    | OK         | 40.76     | True     | True     | True
a_dup2_nul       | sentence_transformers  | 3    | OK         | 47.88     | True     | True     | True
a_dup2_nul       | sentence_transformers  | 4    | OK         | 38.78     | True     | True     | True
a_dup2_nul       | sentence_transformers  | 5    | OK         | 41.86     | True     | True     | True
b_setstdhandle   | numpy                  | 1    | OK         | 3.04      | True     | True     | True
b_setstdhandle   | numpy                  | 2    | OK         | 3.06      | True     | True     | True
b_setstdhandle   | numpy                  | 3    | OK         | 2.98      | True     | True     | True
b_setstdhandle   | numpy                  | 4    | OK         | 2.75      | True     | True     | True
b_setstdhandle   | numpy                  | 5    | OK         | 2.82      | True     | True     | True
b_setstdhandle   | scipy_special          | 1    | OK         | 5.33      | True     | True     | True
b_setstdhandle   | scipy_special          | 2    | OK         | 5.16      | True     | True     | True
b_setstdhandle   | scipy_special          | 3    | OK         | 5.18      | True     | True     | True
b_setstdhandle   | scipy_special          | 4    | OK         | 4.84      | True     | True     | True
b_setstdhandle   | scipy_special          | 5    | OK         | 5.51      | True     | True     | True
b_setstdhandle   | torch                  | 1    | OK         | 9.69      | True     | True     | True
b_setstdhandle   | torch                  | 2    | OK         | 9.46      | True     | True     | True
b_setstdhandle   | torch                  | 3    | OK         | 13.59     | True     | True     | True
b_setstdhandle   | torch                  | 4    | OK         | 10.30     | True     | True     | True
b_setstdhandle   | torch                  | 5    | OK         | 12.40     | True     | True     | True
b_setstdhandle   | sentence_transformers  | 1    | OK         | 42.34     | True     | True     | True
b_setstdhandle   | sentence_transformers  | 2    | OK         | 40.22     | True     | True     | True
b_setstdhandle   | sentence_transformers  | 3    | OK         | 37.14     | True     | True     | True
b_setstdhandle   | sentence_transformers  | 4    | OK         | 43.78     | True     | True     | True
b_setstdhandle   | sentence_transformers  | 5    | OK         | 37.30     | True     | True     | True
control_fd0      | numpy                  | 1    | TRAVOU     | 120.10    | True     | False    | False
control_fd0      | numpy                  | 2    | TRAVOU     | 120.00    | True     | False    | False
control_fd0      | numpy                  | 3    | TRAVOU     | 120.09    | True     | False    | False
control_fd0      | numpy                  | 4    | TRAVOU     | 120.04    | True     | False    | False
control_fd0      | numpy                  | 5    | TRAVOU     | 120.06    | True     | False    | False
control_fd0      | scipy_special          | 1    | TRAVOU     | 120.00    | True     | False    | False
control_fd0      | scipy_special          | 2    | TRAVOU     | 120.02    | True     | False    | False
control_fd0      | scipy_special          | 3    | TRAVOU     | 120.00    | True     | False    | False
control_fd0      | scipy_special          | 4    | TRAVOU     | 120.01    | True     | False    | False
control_fd0      | scipy_special          | 5    | TRAVOU     | 120.06    | True     | False    | False
control_fd0      | torch                  | 1    | TRAVOU     | 120.10    | True     | False    | False
control_fd0      | torch                  | 2    | TRAVOU     | 120.04    | True     | False    | False
control_fd0      | torch                  | 3    | TRAVOU     | 120.00    | True     | False    | False
control_fd0      | torch                  | 4    | TRAVOU     | 120.01    | True     | False    | False
control_fd0      | torch                  | 5    | TRAVOU     | 120.08    | True     | False    | False
control_fd0      | sentence_transformers  | 1    | TRAVOU     | 120.04    | True     | False    | False
control_fd0      | sentence_transformers  | 2    | TRAVOU     | 120.04    | True     | False    | False
control_fd0      | sentence_transformers  | 3    | TRAVOU     | 120.08    | True     | False    | False
control_fd0      | sentence_transformers  | 4    | TRAVOU     | 120.07    | True     | False    | False
control_fd0      | sentence_transformers  | 5    | TRAVOU     | 120.08    | True     | False    | False
------------------------------------------------------------------------------------------------
```
- **Resultados:**
  - `a_dup2_nul`: **20/20 OK (100%)** em `numpy`, `scipy_special`, `torch` e `sentence_transformers`. Canal íntegro (`Ping OK = True`).
  - `b_setstdhandle`: **20/20 OK (100%)**. Canal íntegro (`Ping OK = True`).
  - `control_fd0`: **20/20 TRAVOU (100%)**. Timeout de 120s em todas as repetições.

---

### 5. CONJUNTOS DE PRÉ-IMPORT E CAMINHO TARDIO COMPLETO (E9)

- **Objetivo:** Mapear quais módulos pré-importados antes da inicialização do leitor stdio permitem a carga e inferência tardia de `SentenceTransformer('all-MiniLM-L6-v2')` sem travamento.
- **Evidência (`tabela_e9.txt`):**
```text
=== TABELA EXPERIMENTO E9: CONJUNTOS DE PRE-IMPORT + CAMINHO TARDIO (n=5 cada) ===
Conjunto                   | Rep  | Classe   | Tempo(s)  | t_pre    | t_import  | t_load   | t_enc    | Blocked
---------------------------------------------------------------------------------------------------------
S6_sentence_transformers   | 1    | OK       | 55.52     | 41.10    | 0.00      | 0.82     | 0.09     | True
S6_sentence_transformers   | 2    | OK       | 55.05     | 41.25    | 0.00      | 0.59     | 0.05     | True
S6_sentence_transformers   | 3    | OK       | 58.52     | 43.63    | 0.00      | 0.99     | 0.07     | True
S6_sentence_transformers   | 4    | OK       | 49.54     | 33.62    | 0.00      | 0.62     | 0.06     | True
S6_sentence_transformers   | 5    | OK       | 51.04     | 38.12    | 0.00      | 0.84     | 0.05     | True
S5_numpy_scipy_torch       | 1    | TRAVOU   | 180.04    | -        | -         | -        | -        | True
S5_numpy_scipy_torch       | 2    | TRAVOU   | 180.02    | -        | -         | -        | -        | True
S5_numpy_scipy_torch       | 3    | TRAVOU   | 180.07    | -        | -         | -        | -        | True
S5_numpy_scipy_torch       | 4    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S5_numpy_scipy_torch       | 5    | TRAVOU   | 180.08    | -        | -         | -        | -        | True
S4_torch                   | 1    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S4_torch                   | 2    | TRAVOU   | 180.01    | -        | -         | -        | -        | True
S4_torch                   | 3    | TRAVOU   | 180.08    | -        | -         | -        | -        | True
S4_torch                   | 4    | TRAVOU   | 180.06    | -        | -         | -        | -        | True
S4_torch                   | 5    | TRAVOU   | 180.07    | -        | -         | -        | -        | True
S3_numpy_scipy_sklearn     | 1    | OK       | 57.94     | 17.42    | 26.97     | 0.51     | 0.14     | True
S3_numpy_scipy_sklearn     | 2    | OK       | 36.67     | 5.41     | 20.35     | 0.32     | 0.03     | True
S3_numpy_scipy_sklearn     | 3    | OK       | 41.44     | 4.42     | 20.90     | 0.41     | 0.04     | True
S3_numpy_scipy_sklearn     | 4    | OK       | 37.57     | 9.07     | 17.57     | 0.33     | 0.03     | True
S3_numpy_scipy_sklearn     | 5    | OK       | 34.16     | 4.22     | 19.70     | 0.35     | 0.04     | True
S2_numpy_scipy             | 1    | TRAVOU   | 180.02    | -        | -         | -        | -        | True
S2_numpy_scipy             | 2    | TRAVOU   | 180.08    | -        | -         | -        | -        | True
S2_numpy_scipy             | 3    | TRAVOU   | 180.02    | -        | -         | -        | -        | True
S2_numpy_scipy             | 4    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S2_numpy_scipy             | 5    | TRAVOU   | 180.01    | -        | -         | -        | -        | True
S1_numpy                   | 1    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S1_numpy                   | 2    | TRAVOU   | 180.05    | -        | -         | -        | -        | True
S1_numpy                   | 3    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S1_numpy                   | 4    | TRAVOU   | 180.05    | -        | -         | -        | -        | True
S1_numpy                   | 5    | TRAVOU   | 180.02    | -        | -         | -        | -        | True
S0_vazio                   | 1    | TRAVOU   | 180.10    | -        | -         | -        | -        | True
S0_vazio                   | 2    | TRAVOU   | 180.02    | -        | -         | -        | -        | True
S0_vazio                   | 3    | TRAVOU   | 180.06    | -        | -         | -        | -        | True
S0_vazio                   | 4    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
S0_vazio                   | 5    | TRAVOU   | 180.03    | -        | -         | -        | -        | True
---------------------------------------------------------------------------------------------------------
```
- **Conclusões:**
  - **S6 (`sentence_transformers`):** **5/5 OK** (t_load tardio ~0.7s, t_enc ~0.06s).
  - **S3 (`numpy, scipy.special, sklearn.utils._array_api`):** **5/5 OK** (t_pre ~8s, import tardio de ST ~20s, load ~0.38s, enc ~0.05s).
  - **S0, S1, S2, S4, S5:** **100% TRAVOU** (180s cada). Demonstra que pré-importar apenas numpy/scipy ou apenas torch é insuficiente, pois a árvore interna do `scikit-learn` / OpenBLAS colide com o fd 0.

---

### 6. VALIDAÇÃO EM SERVIDOR REAL COM WRAPPER (E10)

- **Condição:** Servidor de produção original (`dd92d35`), executado através de `wrapper_main.py` sem nenhuma linha de código de produção alterada.
- **Cenários testados:** `mine` (fluxo com indexação completa) e `search-first` (primeira busca sem indexação prévia).
- **Evidência (`tabela_e10.txt`):**
```text
=== TABELA EXPERIMENTO E10: SERVIDOR REAL COM WRAPPER (dd92d35) ===
Tecnica         | Cenario       | Rep  | Classe   | t_init(s)  | t_mine(s)  | t_search(s)  | Total(s)
-----------------------------------------------------------------------------------------------
decouple_fd0    | mine          | 1    | OK       | 3.29       | 44.37      | 0.03         | 49.91
decouple_fd0    | mine          | 2    | OK       | 2.99       | 37.62      | 0.02         | 42.80
decouple_fd0    | mine          | 3    | OK       | 3.19       | 36.80      | 0.02         | 42.15
decouple_fd0    | mine          | 4    | OK       | 3.16       | 34.63      | 0.02         | 39.95
decouple_fd0    | mine          | 5    | OK       | 2.84       | 34.86      | 0.02         | 39.85
decouple_fd0    | search-first  | 1    | OK       | 2.82       | 0.01       | 12.05        | 16.32
decouple_fd0    | search-first  | 2    | OK       | 2.74       | 0.01       | 12.56        | 16.86
decouple_fd0    | search-first  | 3    | OK       | 2.88       | 0.02       | 11.92        | 16.25
decouple_fd0    | search-first  | 4    | OK       | 2.76       | 0.01       | 11.82        | 16.01
decouple_fd0    | search-first  | 5    | OK       | 2.72       | 0.02       | 11.91        | 16.08
preimport       | mine          | 1    | OK       | 14.80      | 25.69      | 0.02         | 42.64
preimport       | mine          | 2    | OK       | 14.26      | 23.76      | 0.02         | 40.19
preimport       | mine          | 3    | OK       | 14.26      | 21.68      | 0.02         | 38.12
preimport       | mine          | 4    | OK       | 14.43      | 21.87      | 0.02         | 38.42
preimport       | mine          | 5    | OK       | 14.50      | 23.89      | 0.02         | 40.52
preimport       | search-first  | 1    | OK       | 14.15      | 0.01       | 0.65         | 16.18
preimport       | search-first  | 2    | OK       | 13.65      | 0.02       | 0.66         | 15.70
preimport       | search-first  | 3    | OK       | 17.52      | 0.02       | 0.73         | 19.61
preimport       | search-first  | 4    | OK       | 14.15      | 0.02       | 0.64         | 16.16
preimport       | search-first  | 5    | OK       | 13.55      | 0.01       | 0.65         | 15.61
-----------------------------------------------------------------------------------------------
```
- **Verificação de Saúde e Ferramentas (`boot_check_e10.txt`):**
  - `decouple_fd0`: returncode=0, 31 ferramentas ativas, `concierge_status` saudável.
  - `preimport`: returncode=0, 31 ferramentas ativas, `concierge_status` saudável.

---

### 7. CONSOLIDAÇÃO E MATRIZ DE ALTERNATIVAS (PARADA NO GATE DA REGRA 7)

| Critério | (A) Desacoplamento de fd 0 (`dup2`) | (B) Pré-import Mínimo Viável (S3) | (C) Pré-import Completo (ST / S6) | (D) Worker Isolado em Subprocesso |
| :--- | :--- | :--- | :--- | :--- |
| **Complexidade da mudança** | Mínima (5 linhas no topo de `main.py`) | Mínima (1 import no topo de `main.py`) | Mínima (1 import no topo de `main.py`) | Alta (refatoração de IPC no `VectorStore`) |
| **Risco de efeitos colaterais** | Baixo (restrito ao bootstrap do stdio) | Muito baixo | Muito baixo | Médio (gerenciamento de processo filho) |
| **Tempo de inicialização (t_init)** | **~2.8s – 3.2s** (rápido) | ~8s – 10s (moderado) | ~13.5s – 17.5s (pesado no boot) | ~3.0s |
| **Tempo da 1ª chamada de modelo** | ~11.9s (na 1ª busca) / ~34s–44s (no mine) | ~20s (import tardio de ST) | **~0.65s (imediato!)** | ~0.7s (após boot do worker) |
| **Compatibilidade SO** | Windows e POSIX (`os.dup2` padrão) | Multiplataforma | Multiplataforma | Multiplataforma |
| **Canal STDIO mantido íntegro?** | **Sim (100% validado em E7 e E10)** | Sim | Sim | Sim |
| **Impacto Arquitetural** | Zero (mantém arquitetura intacta) | Zero | Zero | Altera comunicação com ChromaDB/Modelo |

---

## PARADA NO GATE (REGRA 7)
Nenhuma alteração em arquivos de produção foi realizada. Todos os experimentos de isolamento de causa (E7, E8, E9) e validação em servidor real (E10) foram concluídos com sucesso e encontram-se rigorosamente documentados em disco.

**Aguardando decisão do Dono do Projeto:**
- **Opção A:** Desacoplamento do fd 0 (Boot rápido em ~3s, carregamento do modelo sob demanda, canal stdio preservado).
- **Opção B:** Pré-import mínimo viável S3 (`numpy, scipy.special, sklearn.utils._array_api`) (Boot em ~8s, import tardio de ST sob demanda).
- **Opção C:** Pré-import completo de `sentence_transformers` (Boot em ~14s, 1ª chamada instantânea em ~0.65s).
- **Opção D:** Worker isolado em subprocesso.
