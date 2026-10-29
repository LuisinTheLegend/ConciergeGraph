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
