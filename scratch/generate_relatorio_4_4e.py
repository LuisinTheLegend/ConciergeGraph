"""
scratch/generate_relatorio_4_4e.py — Gerador determinístico de audits/relatorio_4_4e.md (Regra 12 e Regra 14)

Extrai citações literais diretamente dos arquivos com numeração de linha exata (arquivo:linha)
e gera audits/relatorio_4_4e.md em UTF-8 puro (sem BOM e sem bytes nulos).
"""

from __future__ import annotations

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(REPO_ROOT, "audits", "relatorio_4_4e.md")


def extract_lines(rel_path: str, start_line: int, end_line: int) -> str:
    abs_path = os.path.join(REPO_ROOT, rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    selected = all_lines[start_line - 1 : end_line]
    out = [f"# Fonte literal: {rel_path}:{start_line}-{end_line}"]
    for idx, line in enumerate(selected, start=start_line):
        out.append(f"{idx}: {line.rstrip()}")
    return "\n".join(out)


def main() -> None:
    q_tests_a1_a3 = extract_lines("tests/test_connection_queue_resilience.py", 379, 453)
    q_tests_ts1_ts2 = extract_lines("tests/test_connection_queue_resilience.py", 456, 572)
    q_sm = extract_lines("scratch/evidencia_4_4e/mutacao_Sm.txt", 1, 36)
    q_sn = extract_lines("scratch/evidencia_4_4e/mutacao_Sn.txt", 1, 37)
    q_so = extract_lines("scratch/evidencia_4_4e/mutacao_So.txt", 1, 35)
    q_sp = extract_lines("scratch/evidencia_4_4e/mutacao_Sp.txt", 1, 35)
    q_sq = extract_lines("scratch/evidencia_4_4e/mutacao_Sq.txt", 1, 35)
    q_f4031 = extract_lines("audits/fase4-achados.md", 563, 575)
    q_f4032 = extract_lines("audits/fase4-achados.md", 578, 592)
    q_design = extract_lines("audits/design_4_4d_connection_queue.md", 101, 125)
    q_conn_read = extract_lines("storage/connection.py", 382, 386) + "\n...\n" + extract_lines("storage/connection.py", 427, 443)
    q_chroma_inv = extract_lines("scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt", 1, 108)
    q_ci_status = extract_lines("scratch/evidencia_4_4e/ci_status.txt", 1, 36)

    content = f"""# Relatório da Rodada 4.4e — Fechamento de Lacunas de Teste e de Registro da Fila de Produção

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
{q_tests_a1_a3}
```

```text
{q_sm}
```

```text
{q_sn}
```

```text
{q_so}
```

---

## 2. Bloco 2 — Correção do Texto de Reprodução Natural de `F4-031` em `audits/fase4-achados.md`

O item de reprodução natural de `F4-031` em `audits/fase4-achados.md:563-575` foi reescrito para apresentar os dois experimentos (Exp A e Exp B) com citação exata de `scratch/evidencia_4_4d/natural_reproduction_100_procs.txt`, atribuição explícita entre as medições do executor em Windows e as do auditor independente em Linux (`0/40`, `0/40` e `0/30`), frase explícita sobre o limite metodológico (Exp A não representa o caminho de produção e Exp B não mostrou o problema) e rotulagem de qualquer explicação causal como **hipótese** não provada.

### 2.1 Citação Literal de `audits/fase4-achados.md:563-575` (Regra 14)

```text
{q_f4031}
```

---

## 3. Bloco 3 — Registro de `F4-032` em `audits/fase4-achados.md` e `audits/fase4-roadmap.md`

Foi aberta a entrada `[F4-032]` em `audits/fase4-achados.md:578-592` (e indexada em `audits/fase4-roadmap.md:96`), registrando que `ConnectionManager.get_read_connection()` (`storage/connection.py:427-443`) executa conexão e `PRAGMAS` (`storage/connection.py:382-386`) sem retry, levantando `sqlite3.OperationalError` sem travar em caso de lock, observado apenas no Windows no Exp A (`97/100`) e não observado no caminho `SqliteStore` real (Exp B, `0/100`). A severidade proposta é **BAIXA** e a ideia de posicionar `busy_timeout` antes de `journal_mode` fica registrada como **hipótese não medida**, sem nenhuma alteração em `storage/connection.py`.

### 3.1 Citações Literais do Bloco 3 (Regra 14)

```text
{q_conn_read}
```

```text
{q_f4032}
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
{q_tests_ts1_ts2}
```

```text
{q_design}
```

```text
{q_sp}
```

```text
{q_sq}
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
| **Bateria 1 (isolado, Py 3.10)** | `C:\\Nexus-Memory\\GrafoConcierge\\.venv_310\\Scripts\\python.exe -m pytest tests/test_lightweight.py -v --tb=long` | **30** (+ 22 prévias sem `HF_HUB_OFFLINE=1`) | **0/30 falhas** (**não reproduzido em 30 execuções**; 0/52 no total) |
| **Bateria 2 (isolado, Py 3.12)** | `C:\\Nexus-Memory\\GrafoConcierge\\.venv_312\\Scripts\\python.exe -m pytest tests/memory_stress_test.py -v --tb=long` | **30** | **0/30 falhas** (**não reproduzido em 30 execuções**) |
| **Sonda 3a (mesmo processo, ordem normal, Py 3.10)** | `C:\\Nexus-Memory\\GrafoConcierge\\.venv_310\\Scripts\\python.exe -m pytest tests/memory_stress_test.py tests/test_lightweight.py -v --tb=long` | **5** | **0/5 falhas** |
| **Sonda 3b (mesmo processo, ordem reversa, Py 3.12)** | `C:\\Nexus-Memory\\GrafoConcierge\\.venv_312\\Scripts\\python.exe -m pytest tests/test_lightweight.py tests/memory_stress_test.py -v --tb=long` | **5** | **0/5 falhas** |
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
  1. Em `tests/conftest.py:10-25` e `tests/memory_stress_test.py:40-43`, parametrizar `setup_workspace` e `bootstrap` para receber um diretório temporário exclusivo criado via `tmp_path_factory.mktemp("stress_test_workspace")` (ou `tempfile.mkdtemp(prefix=f"stress_{os.getpid()}_")`), eliminando o compartilhamento de `tests/_stress_test_workspace` entre processos ou execuções.
  2. Em `tests/test_lightweight.py:38`, substituir `tmp_dir = "./tmp_chroma_test"` pela fixture nativa `tmp_path` do `pytest` (`str(tmp_path / "chroma_test")`).

### 5.3 Citação Literal de `scratch/evidencia_4_4e/chromadb_30_runs_investigation.txt:1-108` (Regra 14)

```text
{q_chroma_inv}
```

---

## 6. Verificação de Integridade, Segredos (Regra 13), CI e Git Push (Regra 11)

### 6.1 Status dos 6 Jobs do CI (`9519e16` e `a565c4e`)

Consultado via API do GitHub Actions (`scratch/check_ci_status_4_4e.py` -> `scratch/evidencia_4_4e/ci_status.txt`):
- **`9519e16` (HEAD da 4.4c):** **6/6 jobs verdes** (`conclusion=success` nos 3 jobs Ubuntu 3.10/3.11/3.12 do workflow `CI` e nos 3 jobs Windows 3.10/3.12/3.14 do workflow `Windows Stdin Decouple & Lazy ML Imports`).
- **`a565c4e` (HEAD da 4.4d, base desta 4.4e):** **6/6 jobs verdes** (`conclusion=success` nos 3 jobs Ubuntu 3.10/3.11/3.12 e nos 3 jobs Windows 3.10/3.12/3.14).

```text
{q_ci_status}
```

### 6.2 Garantias da Rodada 4.4e

- **Zero alteração em código de produto:** `git diff a565c4e..HEAD -- storage/ core/ ingestion/ interface/ services/ main.py` é vazio.
- **Scanner de segredos (Regra 13):** `scratch/tools/scan_secrets.py` executado com `0` achados (`scratch/evidencia_4_4e/scan_secrets.txt`).
- **Codificação (UTF-8 sem BOM e sem bytes nulos):** Conferida por comando em todos os arquivos de `scratch/evidencia_4_4e/` e `audits/` (`scratch/evidencia_4_4e/utf8_check.txt`).
"""

    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"Relatório gerado com sucesso em: {REPORT_PATH}")


if __name__ == "__main__":
    main()
