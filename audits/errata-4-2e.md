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


---

## 5. Adendo à Errata — Retificações da Rodada 4.2e-2

Em decorrência da revisão da Rodada 4.2e-2 e alinhamento com a Especificação 4.2e-3:

### 5.1 Ausência de Teste em `mcp==1.30.0` no E3 Original
- O experimento E3 da 4.2e-2 utilizou `venv_mcp127` (mcp 1.27.0) e `venv_mcp130` (mcp 1.3.0 real).
- A versão `1.3.0` está fora da faixa suportada especificada pelo projeto (`>=1.27.0,<2`).
- A afirmação de que o teste cobriu "ambas as versões pretendidas" é retificada: a versão `mcp==1.30.0` **NÃO havia sido testada**.
- Foi provisionado o venv `venv_mcp130_real` com `mcp==1.30.0` estrito para executar a repetição formal de E3(a) e E3(e) com $n=3$.

### 5.2 Qualificação da Pilha Nativa do E4 (`py-spy`)
- No Windows, a resolução de pilha nativa pelo `py-spy` utiliza heurísticas de símbolos exportados mais próximos das DLLs carregadas, constituindo aproximações.
- A expressão "comprova que a thread aguarda perror/CRT" é retificada e substituída pelo rigor metodológico: o dump é **compatível com** a `MainThread` em espera de seção crítica/condição de sincronização dentro de `LoadLibraryExW` / `libscipy_openblas64`, enquanto a thread leitora está bloqueada na chamada síncrona `read` / `ReadFile`. A atribuição direta a `perror`/CRT é reclassificada como aproximação simbólica.

### 5.3 Reclassificação da Causa em `torch` e `sentence_transformers`
- A atribuição de que os travamentos de `torch` e `sentence_transformers` ocorrem por "BLAS/OpenMP" é reclassificada formalmente como **HIPÓTESE NÃO CONFIRMADA**, visto que não foram inspecionadas pilhas internas isoladas para esses módulos específicos.

### 5.4 Unificação de Rotulagem ERRO/TRAVOU e Métrica de CPU no E3
- No E3, a variante (a) esgotou o timeout total de 180 s em ambas as versões. No cliente AnyIO/Asyncio, o esgotamento do prazo é capturado internamente como `TimeoutError` (rotulado como `TRAVOU` quando tratado no cliente ou `ERRO` com `ExceptionGroup` quando levantado pelo TaskGroup). Ambos os rótulos representam esgotamento total de timeout da ferramenta (180 s).
- Nas variantes OK (onde a chamada respondeu em <5 s), a coluna de amostragem de CPU periódica refletia o valor inicial (0.00%) pois nenhuma iteração de 5 s do monitor foi disparada antes da conclusão imediata da ferramenta.

### 5.5 Limitação de Escopo do Experimento E5 (Worker)
- O Experimento E5 demonstrou viabilidade de execução isolada em processo filho com `stdin=subprocess.DEVNULL` exclusivamente para a instrução `import scipy.special`.
- Registra-se expressamente que o ciclo completo de `sentence_transformers` + carga do modelo + inferência (encode) **NÃO foi testado** em E5, escopo este investigado na Rodada 4.2e-3.
