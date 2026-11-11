# Desenho Técnico — Endurecimento da Fila de Escrita de Produção (`storage/connection.py`, F4-031)

- **Rodada:** 4.4d (Bloco 1, Item 1.0)
- **Alvo:** `storage/connection.py::SerializedWriteQueue` e `ConnectionManager`
- **Achado Relacionado:** `F4-031` (Severidade GRAVE)
- **Mapa de Chamadores:** `scratch/evidencia_4_4d/connection_queue_map.txt`

---

## 1. Contexto e Defeitos Estruturais no `9519e16`

O servidor MCP em produção utiliza a cadeia `main.py` → `SqliteStore` → `ConnectionManager` → `storage/connection.py::SerializedWriteQueue`. No commit `9519e16`, a implementação de `SerializedWriteQueue` apresenta três defeitos estruturais:

1. **Partida desprotegida em `_worker` (`storage/connection.py:141-147`):** `sqlite3.connect(self._db_path)` e os comandos `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;` e `PRAGMA foreign_keys=ON;` executam fora de qualquer bloco `try/except`. Se `connect` ou um `PRAGMA` levantar `sqlite3.OperationalError` (ex.: `database is locked`), a thread `sqlite-writer` encerra silenciosamente antes de entrar no laço principal.
2. **Espera infinita em `submit` (`storage/connection.py:130`):** O chamador executa `job.result_event.wait()` sem timeout e sem verificar `self._thread.is_alive()`. Se a thread morreu na partida ou durante o processamento, `ConnectionManager.write` bloqueia para sempre.
3. **Morte tardia sem drenagem de pendentes (`storage/connection.py:149-182`):** No laço do `_worker`, `self._conn.rollback()` dentro do `except Exception` não é protegido, e exceções fora do `except` do job (ou `BaseException`) encerram a thread sem sinalizar o `result_event` do job ativo nem dos jobs já enfileirados em `self._queue`.

---

## 2. Invariantes e Mapeamento de Verificação (Testes P1–P9 e Mutações Ra–Rh)

Nenhum dos invariantes abaixo pode ser violado pela correção:

| # | Invariante | Como é Garantido no Desenho | Teste(s) | Mutação(ões) |
|---|---|---|---|---|
| **I1** | **Regime de produção:** `PRAGMA busy_timeout=5000`, `journal_mode=WAL` e `foreign_keys=ON` na conexão do worker (valor da produção hoje é 5000 ms, não 30 s) | O timeout curto de conexão (`STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5`) é usado apenas no handshake; ao concluir o handshake, `PRAGMA busy_timeout=5000;` restaura o busy timeout do SQLite para 5000 ms | **P7** (inspeciona `PRAGMA busy_timeout`, `journal_mode` e `foreign_keys` de dentro de um job) | **Rf** (altera `REGIME_BUSY_TIMEOUT_MS` de `5000` para `1500`) |
| **I2** | **`row_factory = sqlite3.Row`** na conexão do worker | Definido imediatamente após `sqlite3.connect` antes da execução de jobs | **P7** (verifica `conn.row_factory is sqlite3.Row`) | — |
| **I3** | **Execução serializada transacional:** todo job roda na única thread `sqlite-writer`, com `commit` em sucesso, `rollback` em erro e exceção do job re-levantada no chamador | Laço único na thread `sqlite-writer`; `self._conn.commit()` após `job.fn(...)`; `self._conn.rollback()` em `except Exception as exc:`; `job.error = exc` re-levantado por `raise job.error` em `submit()` | Suíte existente + **P2**, **P5**, **P7**, **A1** (`commit` visível a conexão externa), **A2** (`rollback` em erro impede vazamento de escrita parcial), **A3** (falha de job não impede job seguinte) | **Sm** (remover `commit`), **Sn** (remover `rollback`), **So** (interromper worker após falha de job) |
| **I4** | **Ciclo de vida:** `start()` é idempotente, `stop()` encerra a thread (sem reinício da mesma instância), `is_empty()` continua igual, e `submit` antes do `start()` ou após `stop()` levanta `RuntimeError` imediatamente | Flag `self._started`, retorno imediato se já iniciado e vivo; `stop()` marca `self._stopped = True`, `self._running = False`, envia sentinela `_STOP_SENTINEL` (`None`) e faz `join`; `submit()` verifica `if not self._started or self._stopped:` antes de qualquer espera | **P6** (`submit` antes de `start()`), **P8** (`start()` idempotente e `stop()` encerra thread), **T-S1** (`start()` após `stop()` e `submit` subsequente), **T-S2** (jobs na fila antes do sentinela de parada) | **Sp** (não marcar `_stopped = True` em `stop()`), **Sq** (`while True` em vez de `while self._running` no `_worker`) |
| **I5** | **Job em execução não tem prazo total:** a espera em `submit()` é por liveness do worker, não por tempo total (sem `TimeoutError` para job rodando) | `while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):` verifica apenas se a thread morreu e o evento não foi sinalizado; nunca aborta por tempo decorrido enquanto o worker estiver vivo | **P5** (job de ~2 s termina com sucesso) | **Rg** (adiciona prazo total curto ao laço de espera do job em `submit`) |
| **I6** | **Partida com prazo limitado e falha rápida (< 10 s no pior caso):** orçamento de retry + backoff estritamente menor que `READY_TIMEOUT_SECONDS` | `5 * 1.5s + (0.05 + 0.10 + 0.20 + 0.40)s = 8.25s < 10.0s`; erros não-lock falham na 1ª tentativa sem retry e fecham conexão | **P1**, **P2**, **P3**, **P9** | **Ra** (sem retry), **Rd** (sem propagar erro de partida), **Rh** (sem fechar conexão na falha) |
| **I7** | **Nenhum `except: pass` novo** | Todo bloco `except` registra log contextual ou propaga erro encadeado | Inspeção estática (`git diff storage/connection.py`) | — |

---

## 3. Especificação Detalhada da Solução

### 3.1 Constantes Nomeadas em `storage/connection.py`

```python
MAX_CONNECT_RETRIES = 5
STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5
INITIAL_BACKOFF_SECONDS = 0.05
MAX_BACKOFF_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.05
REGIME_BUSY_TIMEOUT_MS = 5000
```

Orçamento máximo de partida quando todas as 5 tentativas bloqueiam pelo timeout de conexão:
$$5 \times 1{,}5\text{ s} + (0{,}05 + 0{,}10 + 0{,}20 + 0{,}40)\text{ s} = 7{,}5\text{ s} + 0{,}75\text{ s} = 8{,}25\text{ s} < 10{,}0\text{ s}$$

### 3.2 Partida Robusta e Escolha de Sincronização (Item 1.1)

- **Decisão entre (a) e (b):** Escolhe-se **(a) `start()` aguarda o handshake (`self._ready.wait(timeout=READY_TIMEOUT_SECONDS)`) e levanta `RuntimeError` com a causa encadeada (`raise RuntimeError(...) from self._startup_error`)** (mantendo também a verificação defensiva em `submit()` caso `submit` seja chamado após falha).
- **Justificativa em uma linha:** Falhar diretamente em `start()` impede que `SqliteStore.__init__` conclua com um `ConnectionManager` já morto e expõe a causa raiz imediatamente na construção do store (atendendo também a `submit()` caso `start()` tenha falhado).
- **Fluxo do Handshake em `_worker`:**
  1. Em laço `for attempt in range(1, MAX_CONNECT_RETRIES + 1):`, abre `conn = sqlite3.connect(self._db_path, timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)`, configura `conn.row_factory = sqlite3.Row`, e executa:
     - `conn.execute("PRAGMA journal_mode=WAL;")`
     - `conn.execute(f"PRAGMA busy_timeout={REGIME_BUSY_TIMEOUT_MS};")`
     - `conn.execute("PRAGMA foreign_keys=ON;")`
  2. Se todos os comandos tiverem sucesso, atribui `self._conn = conn`, sinaliza `self._ready.set()` e avança para o laço de processamento de jobs.
  3. Se ocorrer `sqlite3.OperationalError as exc`:
     - Fecha `conn` imediatamente (`conn.close()`) caso já tenha sido aberta na tentativa atual, evitando vazamento de descritor de arquivo (mutação **Rh**).
     - Verifica se `"database is locked"` ou `"database is busy"` está em `str(exc).lower()`.
     - Se for lock/busy e `attempt < MAX_CONNECT_RETRIES`: calcula `sleep_time = min(INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)`, emite `logger.warning(...)`, aguarda `time.sleep(sleep_time)` e tenta novamente.
     - Se **não** for lock/busy (ex.: `"disk I/O error"`, teste **P3**) ou se as tentativas se esgotarem (teste **P1**): registra `self._startup_error = exc`, `self._running = False`, drena eventuais jobs pendentes na fila, sinaliza `self._ready.set()` e retorna de `_worker`.
  4. Se ocorrer qualquer outra `BaseException as exc` na partida: fecha `conn` se aberta, registra `self._startup_error = exc`, `self._running = False`, drena pendentes, sinaliza `self._ready.set()` e encerra `_worker`.

### 3.3 `submit` Sem Espera Infinita (Item 1.2)

1. **Antes de enfileirar:**
   - Se `not self._started` (ou se `stop()` já encerrou intencionalmente a fila): levanta `RuntimeError("SerializedWriteQueue is not running. Call start() first.")` imediatamente (teste **P6**).
   - Se `self._startup_error is not None` ou `self._fatal_error is not None` ou `not self._thread.is_alive()`: obtém `cause = self._fatal_error or self._startup_error or RuntimeError("sqlite-writer thread is not alive")` e levanta `RuntimeError(f"write worker died: {cause}") from cause`.
2. **Espera pós-enfileiramento em laço curto (sem prazo total):**
   ```python
   while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):
       if not self._thread.is_alive() and not job.result_event.is_set():
           cause = (
               self._fatal_error
               or self._startup_error
               or RuntimeError("sqlite-writer thread terminated unexpectedly")
           )
           raise RuntimeError(f"write worker died: {cause}") from cause
   ```
   - Enquanto `self._thread.is_alive()` for `True`, o laço continua aguardando sem limite de tempo total, permitindo que jobs de mineração/ingestão ou reconstrução FTS de vários segundos completem normalmente (invariante 5, teste **P5**, mutação **Rg**).
   - Se o worker morrer antes de sinalizar `job.result_event`, o chamador acorda em até `POLL_INTERVAL_SECONDS` (50 ms) e recebe `RuntimeError("write worker died: ...")` encadeado (mutações **Rb**, **Rc**).

### 3.4 Morte Tardia e Drenagem de Pendentes (Item 1.3)

1. No laço principal de `_worker`:
   - Dentro do `except Exception as exc:` de execução do `job`: tenta `self._conn.rollback()` protegido por `try/except Exception as rb_exc:`. Se o `rollback()` falhar, a falha é tratada como erro fatal do worker; caso contrário, `job.error = exc` é enviado normalmente ao chamador no `finally` do job (`job.result_event.set()`).
   - Todo o laço `while True:` do `_worker` é envolvido por `try ... except BaseException as fatal_exc:`. Se qualquer exceção escapar fora do tratamento normal do job (por exemplo, falha na leitura da fila, falha no `rollback`, ou erro injetado no laço como em **P4**):
     - Armazena `self._fatal_error = fatal_exc` e `self._running = False`.
     - Se houver um `current_job` ainda não sinalizado, define `current_job.error = RuntimeError(f"write worker died: {fatal_exc}")` (com `__cause__ = fatal_exc`) e aciona `current_job.result_event.set()`.
2. No bloco `finally:` do `_worker`:
   - Marca `self._running = False`.
   - Executa `self._drain_pending_with_error(cause)` para retirar todos os `_WriteJob` remanescentes em `self._queue`, preenchendo `pending.error = RuntimeError(f"write worker died: {cause}")` (com `__cause__ = cause`) e acionando `pending.result_event.set()` (mutação **Re**).
   - Fecha `self._conn` com segurança se estiver aberta.

### 3.5 Semântica de `start()` após `stop()` e de Jobs Pendentes na Parada (Bloco 4 da Rodada 4.4e — Caracterização `T-S1` e `T-S2`)

Dois comportamentos do código atual em `storage/connection.py` foram fixados por testes de caracterização na Rodada 4.4e (`tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization`), sem alteração do código de produto:

1. **Chamada de `start()` após `stop()` (`T-S1`, mutação `Sp`):**
   - `SerializedWriteQueue` é de ciclo único (uma instância `threading.Thread` por objeto, `storage/connection.py:92-101`).
   - Quando `stop()` é chamado (`storage/connection.py:146-162`), define `self._stopped = True` e `self._running = False`, enfileira o sentinela `None` e aguarda `self._thread.join(timeout=timeout)`. Contudo, `self._started` permanece `True`, `self._ready` permanece sinalizado (`is_set() == True`) e `self._startup_error` permanece `None`.
   - Se `start()` (`storage/connection.py:103-140`) for chamado novamente depois de `stop()`:
     - O guard de idempotência inicial (`if self._started and self._thread.is_alive() ...`, linhas 112-119) avalia `False` porque a thread já encerrou.
     - O bloco `if not self._started:` (linhas 121-124) não executa porque `self._started` já é `True`.
     - `self._ready.wait(timeout=READY_TIMEOUT_SECONDS)` (linha 126) retorna `True` imediatamente e `self._startup_error` é `None` (linha 135), fazendo `start()` retornar silenciosamente (`None`) sem recriar nem reiniciar a thread worker.
     - Em seguida, qualquer chamada a `submit()` cai imediatamente em `if not self._started or self._stopped:` (`storage/connection.py:206-207`) e levanta `RuntimeError("SerializedWriteQueue is not running. Call start() first.")`.

2. **Jobs enfileirados antes do sentinela de parada (`T-S2`, mutação `Sq`):**
   - Enquanto um job $J_1$ está em execução no worker e outro job $J_2$ já foi colocado em `self._queue` antes da chamada de `stop()`:
     - `stop()` (`storage/connection.py:157-159`) define `self._stopped = True` e `self._running = False`, e coloca `None` no fim da fila (após $J_2$).
     - Quando $J_1$ termina, o laço `while self._running:` (`storage/connection.py:311`) reavalia a condição no topo, vê `self._running == False` e sai do laço **antes** de desempilhar $J_2$ ou o sentinela `None`.
     - No bloco `finally:` do `_worker` (`storage/connection.py:345-352`), a condição `elif not self._stopped:` é `False` (pois `self._stopped` é `True`), de modo que `_drain_pending_with_error` não é chamado no `finally`; a thread `sqlite-writer` fecha a conexão e termina.
     - A thread chamadora de $J_2$, que aguarda no laço de polling de `submit()` (`while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):`, `storage/connection.py:220-222`), detecta `not self._thread.is_alive() and not job.result_event.is_set()` em até `POLL_INTERVAL_SECONDS` (50 ms) e levanta `self._build_worker_dead_error()` (`storage/connection.py:164-173`):
       `RuntimeError("write worker died: sqlite-writer thread terminated unexpectedly")`, sem executar $J_2$.

3. **Nota sobre Docstring e Proposta de Melhoria (Regra de Zero Alteração de Código de Produto na 4.4e):**
   - Como a regra de topo do Pedido 4.4e determina *"Esta rodada não altera nenhum código de produto. Se você achar que precisa alterar storage/connection.py ou qualquer outro arquivo de produto, PARE, registre o motivo no relatório e aguarde aprovação"*, a docstring de caracterização foi registrada na classe `TestStopAndRestartCharacterization` (`tests/test_connection_queue_resilience.py:456-481`) e o texto exato sugerido para a docstring de `storage/connection.py::SerializedWriteQueue` (bem como uma proposta opcional caso se deseje alterar a semântica no futuro) consta na Seção 4 do `audits/relatorio_4_4e.md` para deliberação do usuário.


