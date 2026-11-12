# Relatório da Rodada 4.4e — Fechamento de Lacunas de Teste e de Registro da Fila de Produção

- **Base da Rodada:** `a565c4e9aaebf744515820004728c8e3d635443e` (`git rev-parse HEAD` == `git ls-remote origin main` verificado antes do início).
- **Commit de Código de Teste, Documentação e Evidências da 4.4e:** `b709ba5` (+ commit final deste relatório e roadmap).
- **Natureza da Rodada:** Pequena — **zero alteração em código de produto** (`storage/connection.py` e demais módulos de produto permanecem 100% intocados em `a565c4e..HEAD`).
- **Status Geral dos Achados Trabalhados:** **corrigido pelo executor, aguardando verificação independente** (`F4-031`) e **ABERTO (registrado na 4.4e, sem correção nesta rodada)** (`F4-032`).
- **Script Gerador deste Relatório (Regra 12):** `scratch/generate_relatorio_4_4e.py`
- **Diretório de Evidências:** `scratch/evidencia_4_4e/`

---

## 1. Bloco 1 — Testes da Invariante Commit/Rollback (`A1`, `A2`, `A3`) e Mutações (`Sm`, `Sn`, `So`)

Foram adicionados em `tests/test_connection_queue_resilience.py:379-453` os três testes de atomicidade transacional exercitando diretamente `storage/connection.py::SerializedWriteQueue`:

- **`A1` (`test_a1_commit_visible_to_external_connection`):** Executa um job de escrita via `q.submit(...)` e, imediatamente após o retorno de `submit`, abre uma segunda conexão `sqlite3.connect(db_path)` independente para consultar a tabela. Sem `self._conn.commit()` no worker, a leitura externa retorna `[]`.
- **`A2` (`test_a2_rollback_on_error_prevents_partial_write_leak`):** O primeiro job executa `INSERT INTO items VALUES ('PARCIAL')` e levanta `ValueError`. Em seguida, um segundo job insere `'ok'` e comita. Uma conexão externa verifica que a tabela contém exclusivamente `['ok']`. Sem `self._conn.rollback()` no worker, `'PARCIAL'` permanece pendente na transação da conexão do worker e vaza junto com o `commit()` do job seguinte (`['PARCIAL', 'ok']`).
- **`A3` (`test_a3_failed_job_does_not_block_subsequent_jobs`):** Verifica que um job que levanta `RuntimeError` não interrompe a thread `sqlite-writer` e que o job subsequente executa e persiste `'depois_da_falha'`.

### 1.1 Resumo de Mutações do Bloco 1 (Regra 15)

| Mutação | Alvo em `storage/connection.py` | Teste Matador | Com Mutação (Vermelho) | Sem Mutação (Verde) | Status | Evidência |
|---|---|---|---|---|---|---|
| **Sm** | Remover `self._conn.commit()` (`storage/connection.py:324`) | `test_a1_commit_visible_to_external_connection` | `FAILED (rc=1)` — `assert [] == ['visivel_externo']` | `PASSED (rc=0)` | **MORTA** | `scratch/evidencia_4_4e/mutacao_Sm.txt` |
| **Sn** | Remover `self._conn.rollback()` (`storage/connection.py:329`) | `test_a2_rollback_on_error_prevents_partial_write_leak` | `FAILED (rc=1)` — `assert ['PARCIAL', 'ok'] == ['ok']` | `PASSED (rc=0)` | **MORTA** | `scratch/evidencia_4_4e/mutacao_Sn.txt` |
| **So** | Adicionar `break` após falha de job no `_worker` (`storage/connection.py:338`) | `test_a3_failed_job_does_not_block_subsequent_jobs` | `FAILED (rc=1)` — `RuntimeError: write worker died` | `PASSED (rc=0)` | **MORTA** | `scratch/evidencia_4_4e/mutacao_So.txt` |

### 1.2 Citações Literais do Bloco 1 (Regra 14)

```text
# Fonte literal: tests/test_connection_queue_resilience.py:379-453
379: def test_a1_commit_visible_to_external_connection(tmp_db_path):
380:     """A1 (commit visível): Um job de escrita bem-sucedido em SerializedWriteQueue
381:     (storage/connection.py) deve ficar imediatamente visível para OUTRA conexão sqlite3,
382:     aberta separadamente, logo após o submit() retornar. Sem self._conn.commit() no worker
383:     (mutação Sm), a leitura externa não enxerga a linha inserida.
384:     """
385:     q = SerializedWriteQueue(tmp_db_path)
386:     q.start()
387:     try:
388:         q.submit(lambda conn: conn.execute("CREATE TABLE t_a1 (id INTEGER PRIMARY KEY, val TEXT)"))
389:         q.submit(lambda conn: conn.execute("INSERT INTO t_a1 (val) VALUES ('visivel_externo')"))
390: 
391:         # Abre outra conexão independente enquanto a fila ainda está viva e aberta
392:         ext_conn = sqlite3.connect(tmp_db_path)
393:         try:
394:             rows = [r[0] for r in ext_conn.execute("SELECT val FROM t_a1 ORDER BY id").fetchall()]
395:         finally:
396:             ext_conn.close()
397: 
398:         assert rows == ["visivel_externo"], (
399:             f"A1 falhou: escrita confirmada deveria estar visível para conexão externa; obteve {rows}"
400:         )
401:     finally:
402:         q.stop()
403: 
404: 
405: @pytest.mark.timeout(30)
406: def test_a2_rollback_on_error_prevents_partial_write_leak(tmp_db_path):
407:     """A2 (rollback no erro): Um primeiro job insere 'PARCIAL' e levanta ValueError;
408:     em seguida, um segundo job insere 'ok' e comita. A tabela deve conter somente ['ok'].
409:     Sem self._conn.rollback() no worker (mutação Sn), 'PARCIAL' vaza junto com o commit seguinte.
410:     """
411:     q = SerializedWriteQueue(tmp_db_path)
412:     q.start()
413:     try:
414:         q.submit(lambda conn: conn.execute("CREATE TABLE t_a2 (id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"))
415: 
416:         def _failing_partial_job(conn):
417:             conn.execute("INSERT INTO t_a2 (val) VALUES ('PARCIAL')")
418:             raise ValueError("falha intencional apos insercao parcial")
419: 
420:         with pytest.raises(ValueError, match="falha intencional apos insercao parcial"):
421:             q.submit(_failing_partial_job)
422: 
423:         # Segundo job insere 'ok' e comita normalmente
424:         q.submit(lambda conn: conn.execute("INSERT INTO t_a2 (val) VALUES ('ok')"))
425: 
426:         ext_conn = sqlite3.connect(tmp_db_path)
427:         try:
428:             rows = [r[0] for r in ext_conn.execute("SELECT val FROM t_a2 ORDER BY id").fetchall()]
429:         finally:
430:             ext_conn.close()
431: 
432:         assert rows == ["ok"], (
433:             f"A2 falhou: linha 'PARCIAL' do job com erro não deveria ter sido comitada; obteve {rows}"
434:         )
435:     finally:
436:         q.stop()
437: 
438: 
439: @pytest.mark.timeout(30)
440: def test_a3_failed_job_does_not_block_subsequent_jobs(tmp_db_path):
441:     """A3: A falha de um job (re-levantada no chamador) não impede que o job seguinte
442:     seja executado e retorne seu resultado normalmente na mesma fila.
443:     """
444:     q = SerializedWriteQueue(tmp_db_path)
445:     q.start()
446:     try:
447:         def _bad_job(conn):
448:             raise KeyError("erro isolado no job 1")
449: 
450:         with pytest.raises(KeyError, match="erro isolado no job 1"):
451:             q.submit(_bad_job)
452: 
453:         res = q.submit(lambda conn: conn.execute("SELECT 42 AS answer").fetchone()["answer"])
```

```text
# Fonte literal: scratch/evidencia_4_4e/mutacao_Sm.txt:1-36
1: === MUTAÇÃO Sm: Remover self._conn.commit() no _worker (storage/connection.py:324); A1 deve falhar ===
2: Alvo: storage/connection.py
3: Teste: tests/test_connection_queue_resilience.py::test_a1_commit_visible_to_external_connection
4: Resultado COM mutação (VERMELHO): returncode=1 (esperado != 0)
5: Resultado SEM mutação (VERDE): returncode=0 (esperado == 0)
6: Status: MORTA (OK)
7: 
8: --- [1] EXECUÇÃO COM MUTAÇÃO Sm (VERMELHO) ---
9: STDOUT:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 1 item
20: 
21: tests/test_connection_queue_resilience.py::test_a1_commit_visible_to_external_connection FAILED [100%]
22: 
23: ================================== FAILURES ===================================
24: ________________ test_a1_commit_visible_to_external_connection ________________
25: tests\test_connection_queue_resilience.py:398: in test_a1_commit_visible_to_external_connection
26:     assert rows == ["visivel_externo"], (
27: E   AssertionError: A1 falhou: escrita confirmada deveria estar visível para conexão externa; obteve []
28: E   assert [] == ['visivel_externo']
29: E
30: E     Right contains one more item: 'visivel_externo'
31: E
32: E     Full diff: (-: missing in left side, +: extra in left side)
33: E     + []
34: E     - [
35: E     -     'visivel_externo',
36: E     - ]
```

```text
# Fonte literal: scratch/evidencia_4_4e/mutacao_Sn.txt:1-37
1: === MUTAÇÃO Sn: Remover self._conn.rollback() no _worker (storage/connection.py:329); A2 deve falhar ===
2: Alvo: storage/connection.py
3: Teste: tests/test_connection_queue_resilience.py::test_a2_rollback_on_error_prevents_partial_write_leak
4: Resultado COM mutação (VERMELHO): returncode=1 (esperado != 0)
5: Resultado SEM mutação (VERDE): returncode=0 (esperado == 0)
6: Status: MORTA (OK)
7: 
8: --- [1] EXECUÇÃO COM MUTAÇÃO Sn (VERMELHO) ---
9: STDOUT:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 1 item
20: 
21: tests/test_connection_queue_resilience.py::test_a2_rollback_on_error_prevents_partial_write_leak FAILED [100%]
22: 
23: ================================== FAILURES ===================================
24: ____________ test_a2_rollback_on_error_prevents_partial_write_leak ____________
25: tests\test_connection_queue_resilience.py:432: in test_a2_rollback_on_error_prevents_partial_write_leak
26:     assert rows == ["ok"], (
27: E   AssertionError: A2 falhou: linha 'PARCIAL' do job com erro não deveria ter sido comitada; obteve ['PARCIAL', 'ok']
28: E   assert ['PARCIAL', 'ok'] == ['ok']
29: E
30: E     At index 0 diff: 'PARCIAL' != 'ok'
31: E     Left contains one more item: 'ok'
32: E
33: E     Full diff: (-: missing in left side, +: extra in left side)
34: E       [
35: E     +     'PARCIAL',
36: E           'ok',
37: E       ]
```

```text
# Fonte literal: scratch/evidencia_4_4e/mutacao_So.txt:1-35
1: === MUTAÇÃO So: Interromper laço do worker após falha de um job (storage/connection.py:338); A3 deve falhar ===
2: Alvo: storage/connection.py
3: Teste: tests/test_connection_queue_resilience.py::test_a3_failed_job_does_not_block_subsequent_jobs
4: Resultado COM mutação (VERMELHO): returncode=1 (esperado != 0)
5: Resultado SEM mutação (VERDE): returncode=0 (esperado == 0)
6: Status: MORTA (OK)
7: 
8: --- [1] EXECUÇÃO COM MUTAÇÃO So (VERMELHO) ---
9: STDOUT:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 1 item
20: 
21: tests/test_connection_queue_resilience.py::test_a3_failed_job_does_not_block_subsequent_jobs FAILED [100%]
22: 
23: ================================== FAILURES ===================================
24: ______________ test_a3_failed_job_does_not_block_subsequent_jobs ______________
25: RuntimeError: sqlite-writer thread terminated unexpectedly
26: 
27: The above exception was the direct cause of the following exception:
28: tests\test_connection_queue_resilience.py:453: in test_a3_failed_job_does_not_block_subsequent_jobs
29:     res = q.submit(lambda conn: conn.execute("SELECT 42 AS answer").fetchone()["answer"])
30:           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31: storage\connection.py:222: in submit
32:     raise self._build_worker_dead_error()
33: E   RuntimeError: write worker died: sqlite-writer thread terminated unexpectedly
34: ------------------------------ Captured log call ------------------------------
35: ERROR    grafo-concierge.connection:connection.py:337 Error in write thread (transaction rolled back): 'erro isolado no job 1'
```

---

## 2. Bloco 2 — Correção do Texto de Reprodução Natural de `F4-031` em `audits/fase4-achados.md`

O item de reprodução natural de `F4-031` em `audits/fase4-achados.md:563-575` foi reescrito para apresentar os dois experimentos (Exp A e Exp B) com citação exata de `scratch/evidencia_4_4d/natural_reproduction_100_procs.txt`, atribuição explícita entre as medições do executor em Windows e as do auditor independente em Linux (`0/40`, `0/40` e `0/30`), frase explícita sobre o limite metodológico (Exp A não representa o caminho de produção e Exp B não mostrou o problema) e rotulagem de qualquer explicação causal como **hipótese** não provada.

### 2.1 Citação Literal de `audits/fase4-achados.md:563-575` (Regra 14)

```text
# Fonte literal: audits/fase4-achados.md:563-575
563: - **Medições de Reprodução Natural (Dois Lados — Windows vs. Linux) e Limites:**
564:   - **Experimento A (uso direto de `ConnectionManager` sobre banco novo sem `_boot_schema`, medido pelo executor em Windows):** `21/100` processos tiveram retries de partida do worker (`WARNING:grafo-concierge.connection:SerializedWriteQueue startup attempt 1/5 failed with 'database is locked'`, `0/100` hangs e `0/100` falhas finais na escrita após retry) e `97/100` processos apresentaram `OperationalError('database is locked')` nas threads leitoras (fonte: [`scratch/evidencia_4_4d/natural_reproduction_100_procs.txt:7-16`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4d/natural_reproduction_100_procs.txt#L7-L16)).
565:   - **Experimento B (caminho real de produção via `SqliteStore` com `_boot_schema`, 50 pares / 100 processos em bancos novos compartilhados, medido pelo executor em Windows):** `0/100` hangs, `0/100` exceções de processo, `0/100` retries de partida do worker e `0/100` erros nas threads leitoras (fonte: [`scratch/evidencia_4_4d/natural_reproduction_100_procs.txt:235-247`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4d/natural_reproduction_100_procs.txt#L235-L247)).
566:   - **Atribuição e Reprodução Independente:** Os números do Windows acima (`21/100` e `97/100` no Exp A; `0/100` no Exp B) são do executor. O auditor independente não os reproduziu em Linux (`0/40`, `0/40` e `0/30` em Linux).
567:   - **Limite Metodológico:** O Exp A não representa o caminho de produção (que passa por `SqliteStore` com inicialização prévia de schema em `_boot_schema`), e o Exp B (que exercita o caminho real de `SqliteStore`) não mostrou o problema (`0/100`).
568:   - **Causa Raiz (Hipótese Não Provada):** Não se conclui causa raiz para a contenção observada no Exp A no Windows; qualquer explicação mecânica (como disputa na transição inicial para `journal_mode=WAL` antes da aplicação de `busy_timeout`) permanece como **hipótese** não provada.
569: - **Correção Implementada na Rodada 4.4d (Bloco 1) e Complemento de Testes na Rodada 4.4e:**
570:   1. **Partida robusta com handshake sincronizado (`start()`):** `_worker` envolve `sqlite3.connect(..., timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)` e os PRAGMAs em `try/except`, aplicando retry com backoff exponencial limitado (`MAX_CONNECT_RETRIES = 5`, `STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5`, `INITIAL_BACKOFF_SECONDS = 0.05`, `MAX_BACKOFF_SECONDS = 1.0`) exclusivamente para `database is locked` e `database is busy`. Outros erros de `OperationalError` (como `disk I/O error`) falham imediatamente sem retry, fechando a conexão parcial. Em falha definitiva, armazena `self._startup_error`, fecha a conexão, drena jobs pendentes, sinaliza `self._ready.set()` e encerra a thread. `start()` aguarda `self._ready.wait(timeout=READY_TIMEOUT_SECONDS)` (< 10 s) e levanta `RuntimeError` com causa encadeada (`raise RuntimeError(...) from self._startup_error`).
571:   2. **Preservação estrita do regime de produção (`PRAGMA busy_timeout=5000`):** Imediatamente após o handshake com timeout curto (1.5 s), o worker aplica `PRAGMA busy_timeout=5000;`, `PRAGMA journal_mode=WAL;` e `PRAGMA foreign_keys=ON;`, mantendo `row_factory = sqlite3.Row` (provado pelo teste P7 e mutação Rf).
572:   3. **`submit` sem espera infinita e sem prazo total para jobs em execução:** Substituído `job.result_event.wait()` sem argumentos por espera em laço curto (`POLL_INTERVAL_SECONDS = 0.05`), checando a cada volta se `self._thread.is_alive()` e se houve erro fatal ou de partida. Se o worker morrer sem sinalizar o job, levanta `RuntimeError("write worker died: ...")` com causa encadeada. Jobs longos em execução não sofrem `TimeoutError` artificial (invariante 5, provado por P5 e mutação Rg).
573:   4. **Tratamento de morte tardia:** Qualquer falha fatal fora do `except` normal do job (incluindo falha em `rollback()` ou `BaseException`) registra `self._fatal_error`, notifica o job em voo e drena todos os jobs pendentes em `self._queue` no bloco `finally`, fazendo chamadas seguintes a `submit` falharem imediatamente.
574:   5. **Validação (Rodadas 4.4d e 4.4e):** Testes P1 a P9 (nascidos em vermelho contra `9519e16`) e mutações Ra a Rh mortas por script externo (`scratch/evidencia_4_4d/`); acrescidos na Rodada 4.4e dos testes de atomicidade transacional A1 (`commit` visível a conexão externa), A2 (`rollback` em erro impedindo vazamento de escrita parcial) e A3 (falha de job não bloqueia job seguinte), testes de caracterização T-S1 e T-S2, e mutações Sm, Sn, So, Sp e Sq mortas por script externo (`scratch/evidencia_4_4e/`).
575: 
```

---

## 3. Bloco 3 — Registro de `F4-032` em `audits/fase4-achados.md` e `audits/fase4-roadmap.md`

Foi aberta a entrada `[F4-032]` em `audits/fase4-achados.md:578-592` (e indexada em `audits/fase4-roadmap.md:96`), registrando que `ConnectionManager.get_read_connection()` (`storage/connection.py:427-443`) executa conexão e `PRAGMAS` (`storage/connection.py:382-386`) sem retry, levantando `sqlite3.OperationalError` sem travar em caso de lock, observado apenas no Windows no Exp A (`97/100`) e não observado no caminho `SqliteStore` real (Exp B, `0/100`). A severidade proposta é **BAIXA** e a ideia de posicionar `busy_timeout` antes de `journal_mode` fica registrada como **hipótese não medida**, sem nenhuma alteração em `storage/connection.py`.

### 3.1 Citações Literais do Bloco 3 (Regra 14)

```text
# Fonte literal: storage/connection.py:382-386
382:     PRAGMAS: list[str] = [
383:         "PRAGMA journal_mode=WAL;",
384:         "PRAGMA busy_timeout=5000;",
385:         "PRAGMA foreign_keys=ON;",
386:     ]
...
# Fonte literal: storage/connection.py:427-443
427:     def get_read_connection(self) -> sqlite3.Connection:
428:         """Returns the read connection of the current thread (creates if necessary).
429: 
430:         Returns:
431:             sqlite3.Connection configured with row_factory=sqlite3.Row.
432:         """
433:         conn = getattr(self._local, "conn", None)
434:         if conn is None:
435:             logger.debug("Creating new read connection for the current thread.")
436:             conn = sqlite3.connect(self._db_path, check_same_thread=False)
437:             conn.row_factory = sqlite3.Row
438:             for pragma in self.PRAGMAS:
439:                 conn.execute(pragma)
440:             self._local.conn = conn
441:             with self._read_conns_lock:
442:                 self._read_connections.append(conn)
443:         return conn
```

```text
# Fonte literal: audits/fase4-achados.md:578-592
578: ### [F4-032] `ConnectionManager.get_read_connection()` Executa Conexão e PRAGMAs de Leitura Sem Retry em Caso de Lock
579: - **Status:** **ABERTO** (registrado pelo executor na Rodada 4.4e; somente registro, sem correção nesta rodada)
580: - **Severidade Proposta:** 🟢 BAIXA
581:   - **Justificativa da Severidade:** Não é crítica nem grave porque: (1) em caso de lock, `get_read_connection()` levanta `sqlite3.OperationalError: database is locked` imediatamente e **não trava** (não há espera infinita nem thread órfã); e (2) o erro **não é observado** no caminho real de produção do servidor MCP via `SqliteStore` (Experimento B: `0/100`, onde `SqliteStore._boot_schema` inicializa o banco e o modo WAL antes da abertura concorrente de leitores).
582: - **Arquivos & Linhas:** [`storage/connection.py:382-386, 427-443`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L427-L443)
583: - **Fato:**
584:   Em `storage/connection.py:427-443`, o método `ConnectionManager.get_read_connection()` abre `sqlite3.connect(self._db_path, check_same_thread=False)` e executa em sequência os três comandos de `ConnectionManager.PRAGMAS` (`storage/connection.py:382-386`: `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;`, `PRAGMA foreign_keys=ON;`) sem laço de retry. Caso ocorra contenção de lock antes ou durante a aplicação desses PRAGMAs (especialmente antes de `PRAGMA busy_timeout=5000;` entrar em vigor ou durante `PRAGMA journal_mode=WAL;`), a chamada levanta `sqlite3.OperationalError: database is locked` e não entra em espera infinita.
585: - **Observado (Dados Empíricos):**
586:   - **Onde ocorreu:** Somente no Windows, no **Experimento A** (uso sintético direto de `ConnectionManager` em banco recém-criado sem `_boot_schema`, com 3 threads leitoras abrindo conexões simultaneamente ao `ConnectionManager.start()`): observado em **`97/100` processos** (fonte: [`scratch/evidencia_4_4d/natural_reproduction_100_procs.txt:15, 18-231`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4d/natural_reproduction_100_procs.txt#L15)).
587:   - **Onde NÃO ocorreu:** Não foi observado no caminho real `SqliteStore` (**Experimento B**, 50 pares / `100` processos iniciando `SqliteStore` simultaneamente sobre o mesmo banco novo: **`0/100`** erros nas leitoras, fonte: [`scratch/evidencia_4_4d/natural_reproduction_100_procs.txt:243`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_4d/natural_reproduction_100_procs.txt#L243)), nem nos experimentos do auditor independente em Linux (`0/40`, `0/40` e `0/30`).
588: - **Fora de Escopo / Hipótese Não Medida:**
589:   - Nenhuma correção em `storage/connection.py` e nenhuma reordenação de `PRAGMAS` é realizada na Rodada 4.4e.
590:   - A proposta de posicionar `PRAGMA busy_timeout=5000;` antes de `PRAGMA journal_mode=WAL;` (ou de não executar `PRAGMA journal_mode=WAL;` a partir de conexões leitoras) fica registrada estritamente como **hipótese não medida**. Qualquer eventual alteração exige medição prévia dedicada e aprovação em rodada própria.
```

---

## 4. Bloco 4 — Semântica de `start()` após `stop()` e Jobs Descartados na Parada (`T-S1` e `T-S2`)

Foram criados os testes de caracterização `T-S1` e `T-S2` na classe `TestStopAndRestartCharacterization` (`tests/test_connection_queue_resilience.py:456-572`) e documentada a semântica atual na docstring da classe e na Seção 3.5 de `audits/design_4_4d_connection_queue.md:101-125`:

1. **`T-S1` (`test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running`):** Fixa que chamar `start()` após `stop()` retorna silenciosamente (`None`) porque `self._started` é `True`, `self._ready` permanece sinalizado e `self._startup_error` é `None` (`storage/connection.py:112-140`), e que o `submit()` seguinte levanta `RuntimeError("SerializedWriteQueue is not running. Call start() first.")` porque `self._stopped` é `True` (`storage/connection.py:206-207`). Morta pela **Mutação Sp** (`scratch/evidencia_4_4e/mutacao_Sp.txt`).
2. **`T-S2` (`test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died`):** Fixa que jobs já enfileirados em `self._queue` antes do sentinela `None` de `stop()` não são executados quando `while self._running:` (`storage/connection.py:311`) encerra ao fim do job em voo, e seus chamadores em `submit()` recebem `RuntimeError("write worker died: sqlite-writer thread terminated unexpectedly")` (`storage/connection.py:164-173, 220-222`). Morta pela **Mutação Sq** (`scratch/evidencia_4_4e/mutacao_Sq.txt`).

### 4.1 Motivo de Não Tocar em `storage/connection.py` e Propostas para Aprovação

- **Cumprimento da trava da rodada:** O cabeçalho do Pedido 4.4e determina: *"Esta rodada não altera nenhum código de produto. Se você achar que precisa alterar storage/connection.py ou qualquer outro arquivo de produto, PARE, registre o motivo no relatório e aguarde aprovação."* Por isso, `storage/connection.py` foi mantido com `git diff` vazio, a docstring de caracterização foi incluída em `TestStopAndRestartCharacterization` e em `audits/design_4_4d_connection_queue.md`, e submetemos abaixo duas propostas opcionais para decisão do dono:
  - **Proposta 4A (Apenas Docstring em `storage/connection.py::SerializedWriteQueue`):** Acrescentar ao docstring de `SerializedWriteQueue` (`storage/connection.py:73-90`) a nota:
    > *"Lifecycle note: `SerializedWriteQueue` is single-use. Calling `start()` after `stop()` returns without restarting the worker thread, and any subsequent `submit()` raises `RuntimeError('SerializedWriteQueue is not running. Call start() first.')`. When `stop()` is called while a job is running, queued jobs waiting behind the active job are not executed and fail in `submit()` with `RuntimeError('write worker died: ...')`."*
  - **Proposta 4B (Mudança futura de comportamento, se desejada):** Caso se deseje no futuro tornar o ciclo de parada mais explícito: (1) fazer `start()` após `stop()` levantar `RuntimeError("Cannot restart a stopped SerializedWriteQueue")` em vez de retornar silenciosamente; e (2) decidir se `stop()` deve drenar e executar os jobs enfileirados antes do sentinela `None` (`while True:` parando apenas em `job is None`) ou rejeitá-los com mensagem dedicada `"SerializedWriteQueue stopped before job execution"`. **Não implementado nesta rodada.**

### 4.2 Citações Literais do Bloco 4 (Regra 14)

```text
# Fonte literal: tests/test_connection_queue_resilience.py:456-572
456:         q.stop()
457: 
458: 
459: # ---------------------------------------------------------------------------
460: # Bloco 4 (4.4e) — Caracterização de start-após-stop e jobs na fila durante stop() (T-S1 e T-S2)
461: # ---------------------------------------------------------------------------
462: 
463: class TestStopAndRestartCharacterization:
464:     """Caracterização formal da semântica atual de parada (stop) e pós-parada de
465:     storage.connection.SerializedWriteQueue (Pedido 4.4e - Bloco 4):
466: 
467:     1. Single-use lifecycle (T-S1 — start() após stop()):
468:        Uma instância de SerializedWriteQueue possui ciclo de vida único (`start() -> submit() -> stop()`).
469:        Como `start()` verifica `if not self._started:` (`storage/connection.py:121`) e aguarda
470:        `self._ready.wait()` (`storage/connection.py:126`, que já permanece sinalizado desde a primeira
471:        partida), chamar `start()` novamente após `stop()` retorna silenciosamente sem criar nem iniciar
472:        nova thread, e qualquer chamada subsequente a `submit()` levanta imediatamente
473:        `RuntimeError("SerializedWriteQueue is not running. Call start() first.")` porque
474:        `self._stopped` permanece `True` (`storage/connection.py:157, 204`).
475: 
476:     2. Descarte de jobs enfileirados antes do sentinela de parada (T-S2):
477:        Como `stop()` define `self._stopped = True` e `self._running = False` antes de enfileirar o
478:        sentinela `None` (`storage/connection.py:157-159`), assim que o job atualmente em execução no
479:        `_worker` termina, a condição do laço `while self._running:` (`storage/connection.py:311`)
480:        avalia `False` imediatamente, encerrando a thread `sqlite-writer` sem consumir os jobs que
481:        aguardavam na fila antes do sentinela. Os chamadores desses jobs pendentes detectam no laço de
482:        polling de `submit()` (`storage/connection.py:218-220`) que `not self._thread.is_alive()` e
483:        recebem `RuntimeError("write worker died: sqlite-writer thread terminated unexpectedly")`.
484:     """
485: 
486:     @pytest.mark.timeout(30)
487:     def test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running(self, tmp_db_path):
488:         """T-S1: start() chamado depois de stop() retorna silenciosamente (sem reviver a thread),
489:         e o submit() seguinte levanta RuntimeError contendo 'not running'.
490:         """
491:         q = SerializedWriteQueue(tmp_db_path)
492:         q.start()
493:         assert q._thread.is_alive()
494: 
495:         q.stop()
496:         assert not q._thread.is_alive()
497:         assert q._stopped is True
498: 
499:         # Chamada a start() após stop() retorna silenciosamente
500:         ret = q.start()
501:         assert ret is None
502:         assert not q._thread.is_alive()
503: 
504:         # O submit() seguinte levanta RuntimeError("SerializedWriteQueue is not running. Call start() first.")
505:         with pytest.raises(RuntimeError, match="not running"):
506:             q.submit(lambda conn: conn.execute("SELECT 1"))
507: 
508:     @pytest.mark.timeout(30)
509:     def test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died(self, tmp_db_path):
510:         """T-S2: Jobs que estavam aguardando na fila antes do sentinela de stop() não são
511:         executados quando o laço while self._running encerra após o job ativo, e seus
512:         chamadores recebem RuntimeError('write worker died').
513:         """
514:         q = SerializedWriteQueue(tmp_db_path)
515:         q.start()
516: 
517:         job1_started = threading.Event()
518:         release_job1 = threading.Event()
519: 
520:         def _active_job(conn):
521:             job1_started.set()
522:             release_job1.wait(timeout=5.0)
523:             return "job1_done"
524: 
525:         active_result: dict[str, Any] = {}
526:         t1 = threading.Thread(
527:             target=lambda: active_result.setdefault("val", q.submit(_active_job)),
528:             daemon=True,
529:         )
530:         t1.start()
531:         assert job1_started.wait(timeout=3.0), "Job 1 deveria ter iniciado no worker"
532: 
533:         # Enfileira job 2 enquanto job 1 ocupa o worker
534:         queued_Outcome: dict[str, Any] = {}
535: 
536:         def _queued_caller():
537:             try:
538:                 queued_Outcome["val"] = q.submit(lambda conn: conn.execute("SELECT 2").fetchone()[0])
539:             except BaseException as exc:
540:                 queued_Outcome["err"] = exc
541: 
542:         t2 = threading.Thread(target=_queued_caller, daemon=True)
543:         t2.start()
544: 
545:         deadline = time.monotonic() + 2.0
546:         while q._queue.qsize() < 1 and time.monotonic() < deadline:
547:             time.sleep(0.01)
548:         assert q._queue.qsize() == 1, "Job 2 deve estar aguardando na fila antes de stop()"
549: 
550:         # Dispara stop() em thread auxiliar (pois stop() faz join até job 1 liberar)
551:         t_stop = threading.Thread(target=q.stop, kwargs={"timeout": 5.0}, daemon=True)
552:         t_stop.start()
553: 
554:         # Aguarda stop() marcar _stopped=True e _running=False e enfileirar o sentinela
555:         deadline = time.monotonic() + 2.0
556:         while not q._stopped and time.monotonic() < deadline:
557:             time.sleep(0.01)
558:         assert q._stopped is True
559: 
560:         # Libera o job 1 em execução
561:         release_job1.set()
562: 
563:         t1.join(timeout=3.0)
564:         t2.join(timeout=3.0)
565:         t_stop.join(timeout=3.0)
566: 
567:         assert active_result.get("val") == "job1_done"
568:         assert "err" in queued_Outcome, "Job 2 enfileirado antes do sentinela deveria falhar ao parar"
569:         assert isinstance(queued_Outcome["err"], RuntimeError)
570:         assert "write worker died" in str(queued_Outcome["err"]).lower()
571: 
572: 
```

```text
# Fonte literal: audits/design_4_4d_connection_queue.md:101-125
101: ### 3.5 Semântica de `start()` após `stop()` e de Jobs Pendentes na Parada (Bloco 4 da Rodada 4.4e — Caracterização `T-S1` e `T-S2`)
102: 
103: Dois comportamentos do código atual em `storage/connection.py` foram fixados por testes de caracterização na Rodada 4.4e (`tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization`), sem alteração do código de produto:
104: 
105: 1. **Chamada de `start()` após `stop()` (`T-S1`, mutação `Sp`):**
106:    - `SerializedWriteQueue` é de ciclo único (uma instância `threading.Thread` por objeto, `storage/connection.py:92-101`).
107:    - Quando `stop()` é chamado (`storage/connection.py:146-162`), define `self._stopped = True` e `self._running = False`, enfileira o sentinela `None` e aguarda `self._thread.join(timeout=timeout)`. Contudo, `self._started` permanece `True`, `self._ready` permanece sinalizado (`is_set() == True`) e `self._startup_error` permanece `None`.
108:    - Se `start()` (`storage/connection.py:103-140`) for chamado novamente depois de `stop()`:
109:      - O guard de idempotência inicial (`if self._started and self._thread.is_alive() ...`, linhas 112-119) avalia `False` porque a thread já encerrou.
110:      - O bloco `if not self._started:` (linhas 121-124) não executa porque `self._started` já é `True`.
111:      - `self._ready.wait(timeout=READY_TIMEOUT_SECONDS)` (linha 126) retorna `True` imediatamente e `self._startup_error` é `None` (linha 135), fazendo `start()` retornar silenciosamente (`None`) sem recriar nem reiniciar a thread worker.
112:      - Em seguida, qualquer chamada a `submit()` cai imediatamente em `if not self._started or self._stopped:` (`storage/connection.py:206-207`) e levanta `RuntimeError("SerializedWriteQueue is not running. Call start() first.")`.
113: 
114: 2. **Jobs enfileirados antes do sentinela de parada (`T-S2`, mutação `Sq`):**
115:    - Enquanto um job $J_1$ está em execução no worker e outro job $J_2$ já foi colocado em `self._queue` antes da chamada de `stop()`:
116:      - `stop()` (`storage/connection.py:157-159`) define `self._stopped = True` e `self._running = False`, e coloca `None` no fim da fila (após $J_2$).
117:      - Quando $J_1$ termina, o laço `while self._running:` (`storage/connection.py:311`) reavalia a condição no topo, vê `self._running == False` e sai do laço **antes** de desempilhar $J_2$ ou o sentinela `None`.
118:      - No bloco `finally:` do `_worker` (`storage/connection.py:345-352`), a condição `elif not self._stopped:` é `False` (pois `self._stopped` é `True`), de modo que `_drain_pending_with_error` não é chamado no `finally`; a thread `sqlite-writer` fecha a conexão e termina.
119:      - A thread chamadora de $J_2$, que aguarda no laço de polling de `submit()` (`while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):`, `storage/connection.py:220-222`), detecta `not self._thread.is_alive() and not job.result_event.is_set()` em até `POLL_INTERVAL_SECONDS` (50 ms) e levanta `self._build_worker_dead_error()` (`storage/connection.py:164-173`):
120:        `RuntimeError("write worker died: sqlite-writer thread terminated unexpectedly")`, sem executar $J_2$.
121: 
122: 3. **Nota sobre Docstring e Proposta de Melhoria (Regra de Zero Alteração de Código de Produto na 4.4e):**
123:    - Como a regra de topo do Pedido 4.4e determina *"Esta rodada não altera nenhum código de produto. Se você achar que precisa alterar storage/connection.py ou qualquer outro arquivo de produto, PARE, registre o motivo no relatório e aguarde aprovação"*, a docstring de caracterização foi registrada na classe `TestStopAndRestartCharacterization` (`tests/test_connection_queue_resilience.py:456-481`) e o texto exato sugerido para a docstring de `storage/connection.py::SerializedWriteQueue` (bem como uma proposta opcional caso se deseje alterar a semântica no futuro) consta na Seção 4 do `audits/relatorio_4_4e.md` para deliberação do usuário.
124: 
125: 
```

```text
# Fonte literal: scratch/evidencia_4_4e/mutacao_Sp.txt:1-35
1: === MUTAÇÃO Sp: Não marcar self._stopped = True em stop() (storage/connection.py:157); T-S1 deve falhar ===
2: Alvo: storage/connection.py
3: Teste: tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running
4: Resultado COM mutação (VERMELHO): returncode=1 (esperado != 0)
5: Resultado SEM mutação (VERDE): returncode=0 (esperado == 0)
6: Status: MORTA (OK)
7: 
8: --- [1] EXECUÇÃO COM MUTAÇÃO Sp (VERMELHO) ---
9: STDOUT:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 1 item
20: 
21: tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running FAILED [100%]
22: 
23: ================================== FAILURES ===================================
24: _ TestStopAndRestartCharacterization.test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running _
25: tests\test_connection_queue_resilience.py:497: in test_ts1_start_after_stop_returns_silently_and_submit_raises_not_running
26:     assert q._stopped is True
27: E   assert False is True
28: E    +  where False = <storage.connection.SerializedWriteQueue object at 0x00000238F5131BE0>._stopped
29: ============================== warnings summary ===============================
30: .venv_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
31:   C:\Nexus-Memory\GrafoConcierge\.venv_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
32:     if asyncio.iscoroutinefunction(f):
33: 
34: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
35: =========================== short test summary info ===========================
```

```text
# Fonte literal: scratch/evidencia_4_4e/mutacao_Sq.txt:1-35
1: === MUTAÇÃO Sq: Manter while True no _worker em vez de while self._running (storage/connection.py:311); T-S2 deve falhar ===
2: Alvo: storage/connection.py
3: Teste: tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died
4: Resultado COM mutação (VERMELHO): returncode=1 (esperado != 0)
5: Resultado SEM mutação (VERDE): returncode=0 (esperado == 0)
6: Status: MORTA (OK)
7: 
8: --- [1] EXECUÇÃO COM MUTAÇÃO Sq (VERMELHO) ---
9: STDOUT:
10: ============================= test session starts =============================
11: platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_clean\Scripts\python.exe
12: cachedir: .pytest_cache
13: rootdir: C:\Nexus-Memory\GrafoConcierge
14: configfile: pyproject.toml
15: plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
16: timeout: 300.0s
17: timeout method: thread
18: timeout func_only: False
19: collecting ... collected 1 item
20: 
21: tests/test_connection_queue_resilience.py::TestStopAndRestartCharacterization::test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died FAILED [100%]
22: 
23: ================================== FAILURES ===================================
24: _ TestStopAndRestartCharacterization.test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died _
25: tests\test_connection_queue_resilience.py:568: in test_ts2_jobs_queued_before_stop_sentinel_fail_with_write_worker_died
26:     assert "err" in queued_Outcome, "Job 2 enfileirado antes do sentinela deveria falhar ao parar"
27: E   AssertionError: Job 2 enfileirado antes do sentinela deveria falhar ao parar
28: E   assert 'err' in {'val': 2}
29: ============================== warnings summary ===============================
30: .venv_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
31:   C:\Nexus-Memory\GrafoConcierge\.venv_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
32:     if asyncio.iscoroutinefunction(f):
33: 
34: -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
35: =========================== short test summary info ===========================
```

---

## 5. Bloco 5 — Investigação do `chromadb` Intermitente (Somente Investigação)

Executado pelo script `scratch/investigate_chromadb_4_4e.py` e salvo integralmente em `scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt`:

### 5.1 Versões, Comandos Exatos e Resultados das Baterias

- **Ambiente Python 3.10:** `Python=3.10.22 | pytest=9.2.0 | chromadb=1.5.9 | sqlite3=3.53.1` em `Windows 11 (10.0.26300)`
- **Ambiente Python 3.12:** `Python=3.12.16 | pytest=9.2.0 | chromadb=1.5.9 | sqlite3=3.53.1` em `Windows 11 (10.0.26300)`
- **Variável `HF_HUB_OFFLINE`:** Estado original `None`; definido `HF_HUB_OFFLINE=1` durante a bateria para evitar timeouts de rede de ~85s por processo no sandbox ao carregar `SentenceTransformer("all-MiniLM-L6-v2")` do cache local, e restaurado para `None` no bloco `finally` (`scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt:10240`).

| Bateria | Comando Exato | Execuções | Resultado |
|---|---|---|---|
| **Bateria 1 (isolado, Py 3.10)** | `C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/test_lightweight.py -v --tb=long` | **30** (+ 22 prévias sem `HF_HUB_OFFLINE=1`) | **0/30 falhas** (**não reproduzido em 30 execuções**; 0/52 no total) |
| **Bateria 2 (isolado, Py 3.12)** | `C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=long` | **30** | **0/30 falhas** (**não reproduzido em 30 execuções**) |
| **Sonda 3a (mesmo processo, ordem normal, Py 3.10)** | `C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/memory_stress_test.py tests/test_lightweight.py -v --tb=long` | **5** | **0/5 falhas** |
| **Sonda 3b (mesmo processo, ordem reversa, Py 3.12)** | `C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/test_lightweight.py tests/memory_stress_test.py -v --tb=long` | **5** | **0/5 falhas** |
| **Sonda 3c (2 processos simultâneos no mesmo workspace)** | Processo A (`Py3.10 test_lightweight.py`) em paralelo com Processo B (`Py3.12 memory_stress_test.py`) | **10 pares** | **10/10 pares com falha** (`sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid` em `storage/store.py:137`) |

### 5.2 Fato vs. Hipótese e Proposta de Correção (Sem Alterar Testes nem Fixture Nesta Rodada)

- **Fatos provados:**
  1. Em execução sequencial isolada, o erro interno do `chromadb` (`PanicException` e `sqlite3.OperationalError: no such table: collections`) **não foi reproduzido em 30 execuções** de `tests/test_lightweight.py` no Python 3.10 (`0/30`) e **não foi reproduzido em 30 execuções** de `tests/memory_stress_test.py` no Python 3.12 (`0/30`).
  2. Tanto `tests/memory_stress_test.py` quanto `tests/test_lightweight.py` dependem da fixture `stress_components` (`tests/conftest.py:10-25`), que chama `setup_workspace()` (`tests/memory_stress_test.py:85-90`) e `bootstrap()` (`tests/memory_stress_test.py:249-285`) usando caminhos **fixos e compartilhados** no disco:
     - `TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_stress_test_workspace")` (`tests/memory_stress_test.py:40`)
     - `DB_PATH = os.path.join(TEST_DIR, "stress_test.db")` (`tests/memory_stress_test.py:41`)
     - `CHROMA_PATH = os.path.join(TEST_DIR, "chroma")` (`tests/memory_stress_test.py:42`)
     Além disso, `tests/test_lightweight.py:38` usa outro caminho fixo `tmp_dir = "./tmp_chroma_test"`.
  3. Quando dois processos `pytest` executam simultaneamente no mesmo diretório de trabalho (Sonda 3c, reproduzindo o cenário da validação da 4.4d em que múltiplos processos de versões de Python rodaram em paralelo no mesmo repositório), há colisão determinística (`10/10` pares falharam) porque ambos executam `shutil.rmtree(TEST_DIR, ignore_errors=True)` e escrevem simultaneamente em `tests/_stress_test_workspace/`.
- **Hipótese (não provada para `PanicException` / `no such table: collections`):**
  - Como `PanicException` e `no such table: collections` não ocorreram nas execuções isoladas (0/30 e 0/30), permanece como **hipótese** que sua ocorrência na 1ª tentativa da 4.4d tenha sido causada por corrida entre processos `pytest` paralelos no mesmo workspace (um processo executando `shutil.rmtree(TEST_DIR, ignore_errors=True)` sobre `tests/_stress_test_workspace/chroma` enquanto outro processo inicializava ou consultava o `PersistentClient` do `chromadb` naquele mesmo diretório).
- **Proposta de Correção (Aguardando Aprovação — Não Implementada na 4.4e):**
  1. Em `tests/conftest.py:10-25` e `tests/memory_stress_test.py:40-43`, parametrizar `setup_workspace` e `bootstrap` para receber um diretório temporário exclusivo criado via `tmp_path_factory.mktemp("stress_test_workspace")` (ou `tempfile.mkdtemp(prefix=f"stress_10860_")`), eliminando o compartilhamento de `tests/_stress_test_workspace` entre processos ou execuções.
  2. Em `tests/test_lightweight.py:38`, substituir `tmp_dir = "./tmp_chroma_test"` pela fixture nativa `tmp_path` do `pytest` (`str(tmp_path / "chroma_test")`).

### 5.3 Citação Literal de `scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt:1-108` (Regra 14)

```text
# Fonte literal: scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt:1-108
1: === INVESTIGAÇÃO DO CHROMADB INTERMITENTE (BLOCO 5 — RODADA 4.4e) ===
2: Sistema Operacional: Windows 11 (10.0.26300)
3: Ambiente Python 3.10 (C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe): Python=3.10.22 | pytest=9.2.0 | chromadb=1.5.9 | sqlite3=3.53.1
4: Ambiente Python 3.12 (C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe): Python=3.12.16 | pytest=9.2.0 | chromadb=1.5.9 | sqlite3=3.53.1
5: Estado original de HF_HUB_OFFLINE: None
6: Nota: HF_HUB_OFFLINE=1 e TRANSFORMERS_OFFLINE=1 ativos durante as baterias (cache local do SentenceTransformer).
7: Nota adicional: Na tentativa anterior sem HF_HUB_OFFLINE=1, 22/22 execuções de test_lightweight.py no Python 3.10 passaram (~92s cada).
8: 
9: --------------------------------------------------------------------------------
10: 1. BATERIA 1: 30 execuções sequenciais isoladas de tests/test_lightweight.py (Python 3.10)
11: Comando exato: HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/test_lightweight.py -v --tb=long
12: --------------------------------------------------------------------------------
13:   [B1 run 01/30] PASS (24.29s)
14:   [B1 run 02/30] PASS (24.18s)
15:   [B1 run 03/30] PASS (23.93s)
16:   [B1 run 04/30] PASS (23.06s)
17:   [B1 run 05/30] PASS (22.41s)
18:   [B1 run 06/30] PASS (22.41s)
19:   [B1 run 07/30] PASS (22.30s)
20:   [B1 run 08/30] PASS (22.14s)
21:   [B1 run 09/30] PASS (22.18s)
22:   [B1 run 10/30] PASS (22.14s)
23:   [B1 run 11/30] PASS (22.22s)
24:   [B1 run 12/30] PASS (22.19s)
25:   [B1 run 13/30] PASS (22.19s)
26:   [B1 run 14/30] PASS (22.88s)
27:   [B1 run 15/30] PASS (23.68s)
28:   [B1 run 16/30] PASS (22.07s)
29:   [B1 run 17/30] PASS (22.04s)
30:   [B1 run 18/30] PASS (22.55s)
31:   [B1 run 19/30] PASS (21.89s)
32:   [B1 run 20/30] PASS (22.51s)
33:   [B1 run 21/30] PASS (22.17s)
34:   [B1 run 22/30] PASS (22.16s)
35:   [B1 run 23/30] PASS (22.02s)
36:   [B1 run 24/30] PASS (21.93s)
37:   [B1 run 25/30] PASS (21.93s)
38:   [B1 run 26/30] PASS (22.66s)
39:   [B1 run 27/30] PASS (25.35s)
40:   [B1 run 28/30] PASS (22.92s)
41:   [B1 run 29/30] PASS (22.53s)
42:   [B1 run 30/30] PASS (21.78s)
43: Resumo Bateria 1 (test_lightweight.py isolado, Python 3.10): 0/30 falhas em 678.73s (não reproduzido em 30 execuções)
44: 
45: --------------------------------------------------------------------------------
46: 2. BATERIA 2: 30 execuções sequenciais isoladas de tests/memory_stress_test.py (Python 3.12)
47: Comando exato: HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=long
48: --------------------------------------------------------------------------------
49:   [B2 run 01/30] PASS (31.81s)
50:   [B2 run 02/30] PASS (25.29s)
51:   [B2 run 03/30] PASS (25.45s)
52:   [B2 run 04/30] PASS (25.27s)
53:   [B2 run 05/30] PASS (25.36s)
54:   [B2 run 06/30] PASS (25.20s)
55:   [B2 run 07/30] PASS (25.42s)
56:   [B2 run 08/30] PASS (25.18s)
57:   [B2 run 09/30] PASS (24.91s)
58:   [B2 run 10/30] PASS (25.37s)
59:   [B2 run 11/30] PASS (28.18s)
60:   [B2 run 12/30] PASS (27.96s)
61:   [B2 run 13/30] PASS (26.07s)
62:   [B2 run 14/30] PASS (25.34s)
63:   [B2 run 15/30] PASS (25.58s)
64:   [B2 run 16/30] PASS (28.20s)
65:   [B2 run 17/30] PASS (28.00s)
66:   [B2 run 18/30] PASS (25.60s)
67:   [B2 run 19/30] PASS (25.33s)
68:   [B2 run 20/30] PASS (25.18s)
69:   [B2 run 21/30] PASS (25.39s)
70:   [B2 run 22/30] PASS (25.38s)
71:   [B2 run 23/30] PASS (25.46s)
72:   [B2 run 24/30] PASS (25.50s)
73:   [B2 run 25/30] PASS (25.11s)
74:   [B2 run 26/30] PASS (25.59s)
75:   [B2 run 27/30] PASS (25.16s)
76:   [B2 run 28/30] PASS (25.36s)
77:   [B2 run 29/30] PASS (25.06s)
78:   [B2 run 30/30] PASS (24.81s)
79: Resumo Bateria 2 (memory_stress_test.py isolado, Python 3.12): 0/30 falhas em 777.55s (não reproduzido em 30 execuções)
80: 
81: --------------------------------------------------------------------------------
82: 3a. SONDA DE MESMO PROCESSO (ordem normal: memory_stress_test.py -> test_lightweight.py, Python 3.10, 5 execuções)
83: Comando exato: HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/memory_stress_test.py tests/test_lightweight.py -v --tb=long
84: --------------------------------------------------------------------------------
85:   [B3a run 01/05] PASS (25.89s)
86:   [B3a run 02/05] PASS (23.82s)
87:   [B3a run 03/05] PASS (23.56s)
88:   [B3a run 04/05] PASS (24.84s)
89:   [B3a run 05/05] PASS (23.83s)
90: Resumo B3a: 0/5 falhas
91: 
92: --------------------------------------------------------------------------------
93: 3b. SONDA DE MESMO PROCESSO (ordem reversa: test_lightweight.py -> memory_stress_test.py, Python 3.12, 5 execuções)
94: Comando exato: HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/test_lightweight.py tests/memory_stress_test.py -v --tb=long
95: --------------------------------------------------------------------------------
96:   [B3b run 01/05] PASS (28.17s)
97:   [B3b run 02/05] PASS (26.66s)
98:   [B3b run 03/05] PASS (27.17s)
99:   [B3b run 04/05] PASS (26.38s)
100:   [B3b run 05/05] PASS (26.11s)
101: Resumo B3b: 0/5 falhas
102: 
103: --------------------------------------------------------------------------------
104: 3c. SONDA DE CONCORRÊNCIA ENTRE PROCESSOS (10 pares simultâneos compartilhando tests/_stress_test_workspace)
105: Processo A (Py3.10): HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_310\Scripts\python.exe -m pytest tests/test_lightweight.py -v --tb=long
106: Processo B (Py3.12): HF_HUB_OFFLINE=1 C:\Nexus-Memory\GrafoConcierge\.venv_312\Scripts\python.exe -m pytest tests/memory_stress_test.py -v --tb=long
107: --------------------------------------------------------------------------------
108:   [B3c par 01/10] Py3.10(test_lightweight)=PASS (22.40s) | Py3.12(memory_stress_test)=FAIL(rc=1) (6.40s)
```

---

## 6. Verificação de Integridade, Segredos (Regra 13), CI e Git Push (Regra 11)

### 6.1 Status dos 6 Jobs do CI (`9519e16` e `a565c4e`)

Consultado via API do GitHub Actions (`scratch/check_ci_status_4_4e.py` -> `scratch/evidencia_4_4e/ci_status.txt`):
- **`9519e16` (HEAD da 4.4c):** **6/6 jobs verdes** (`conclusion=success` nos 3 jobs Ubuntu 3.10/3.11/3.12 do workflow `CI` e nos 3 jobs Windows 3.10/3.12/3.14 do workflow `Windows Stdin Decouple & Lazy ML Imports`).
- **`a565c4e` (HEAD da 4.4d, base desta 4.4e):** **6/6 jobs verdes** (`conclusion=success` nos 3 jobs Ubuntu 3.10/3.11/3.12 e nos 3 jobs Windows 3.10/3.12/3.14).

```text
# Fonte literal: scratch/evidencia_4_4e/ci_status.txt:1-36
1: === GITHUB ACTIONS CI STATUS (RODADA 4.4e) ===
2: 
3: Commit a565c4e (a565c4e9aaebf744515820004728c8e3d635443e):
4:   Workflow: CI (run_id=42863276492, status=completed, conclusion=success)
5:     - Job: Test (Python 3.11) | status=completed | conclusion=success
6:     - Job: Test (Python 3.12) | status=completed | conclusion=success
7:     - Job: Test (Python 3.10) | status=completed | conclusion=success
8:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=42863276453, status=completed, conclusion=success)
9:     - Job: Windows (3.12) | status=completed | conclusion=success
10:     - Job: Windows (3.10) | status=completed | conclusion=success
11:     - Job: Windows (3.14) | status=completed | conclusion=success
12:   => Resumo a565c4e: 6/6 jobs verdes (success)
13: 
14: Commit 9519e16 (9519e16cc6e8bad93240dd51ba118a53c8a085d2):
15:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=42553400294, status=completed, conclusion=success)
16:     - Job: Windows (3.12) | status=completed | conclusion=success
17:     - Job: Windows (3.14) | status=completed | conclusion=success
18:     - Job: Windows (3.10) | status=completed | conclusion=success
19:   Workflow: CI (run_id=42553400260, status=completed, conclusion=success)
20:     - Job: Test (Python 3.12) | status=completed | conclusion=success
21:     - Job: Test (Python 3.11) | status=completed | conclusion=success
22:     - Job: Test (Python 3.10) | status=completed | conclusion=success
23:   => Resumo 9519e16: 6/6 jobs verdes (success)
24: 
25: Commit 8eccea7 (8eccea747f4fee5160045a1350c6f5e48596fc4a):
26:   Workflow: Windows Stdin Decouple & Lazy ML Imports (run_id=42545089510, status=completed, conclusion=success)
27:     - Job: Windows (3.10) | status=completed | conclusion=success
28:     - Job: Windows (3.14) | status=completed | conclusion=success
29:     - Job: Windows (3.12) | status=completed | conclusion=success
30:   Workflow: CI (run_id=42545089499, status=completed, conclusion=failure)
31:     - Job: Test (Python 3.10) | status=completed | conclusion=failure
32:     - Job: Test (Python 3.11) | status=completed | conclusion=success
33:     - Job: Test (Python 3.12) | status=completed | conclusion=success
34:   => Resumo 8eccea7: 5/6 jobs verdes (success)
35: 
36: Commit 6606b9a (6606b9a373847fa17e5723821703a48212c5dc1c):
```

### 6.2 Garantias da Rodada 4.4e

- **Zero alteração em código de produto:** `git diff a565c4e..HEAD -- storage/ core/ ingestion/ interface/ services/ main.py` é vazio.
- **Scanner de segredos (Regra 13):** `scratch/tools/scan_secrets.py` executado com `0` achados (`scratch/evidencia_4_4e/scan_secrets.txt`).
- **Codificação (UTF-8 sem BOM e sem bytes nulos):** Conferida por comando em todos os arquivos de `scratch/evidencia_4_4e/` e `audits/` (`scratch/evidencia_4_4e/utf8_check.txt`).

---

## Adendo (2026-11-11 — Rodada 4.4f, Bloco 4): Esclarecimento sobre a Hipótese do `chromadb`

- O erro reproduzido pela colisão de caminhos fixos em execuções paralelas (`sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid` na Sonda 3c do executor em Windows; e `sqlite3.OperationalError: unable to open database file`, `ProjectNotFoundError` e `ValueError: Project not found` na reprodução de 3/4 pares pelo auditor independente em Linux, registrado como `F4-033`) **é diferente** do erro interno intermitente do `chromadb` (`InternalError` / `PanicException` / `sqlite3.OperationalError: no such table: collections`) observado na 1ª tentativa da Rodada 4.4d.
- A ligação entre os dois permanece estritamente como **hipótese** e não deve ser afirmada como causa: **o `chromadb` intermitente segue aberto, com causa não provada**.

