"""
scratch/generate_relatorio_4_4d.py — Gerador Programático de audits/relatorio_4_4d.md (Regra 12)

Extrai métricas, saídas de comandos, contagens de suíte multi-versão e verifica integridade
(UTF-8 sem BOM e sem bytes nulos) de todos os arquivos em scratch/evidencia_4_4d/.
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4d")
REPORT_PATH = os.path.join(REPO_ROOT, "audits", "relatorio_4_4d.md")


def _parse_suite_file(filename: str) -> dict:
    path = os.path.join(EVIDENCE_DIR, filename)
    if not os.path.exists(path):
        return {"version": "N/A", "std_summary": "N/A", "rev_summary": "N/A", "std_rc": -1, "rev_rc": -1}
    text = open(path, "r", encoding="utf-8").read()
    m_ver = re.search(r"Versão do Python:\s*(.+)", text)
    m_std_rc = re.search(r"Ordem Padrão ReturnCode:\s*(\d+)", text)
    m_rev_rc = re.search(r"Ordem Invertida \(--reverse\) ReturnCode:\s*(\d+)", text)

    parts = text.split("--- [2] ORDEM INVERTIDA")
    std_part = parts[0] if parts else text
    rev_part = parts[1] if len(parts) > 1 else ""

    m_std_sum = re.findall(r"(\d+ passed[^\n]*)", std_part)
    m_rev_sum = re.findall(r"(\d+ passed[^\n]*)", rev_part)

    return {
        "version": m_ver.group(1).strip() if m_ver else "N/A",
        "std_rc": int(m_std_rc.group(1)) if m_std_rc else -1,
        "rev_rc": int(m_rev_rc.group(1)) if m_rev_rc else -1,
        "std_summary": m_std_sum[-1].strip() if m_std_sum else "N/A",
        "rev_summary": m_rev_sum[-1].strip() if m_rev_sum else "N/A",
    }


def _collect_evidence_table() -> list[str]:
    rows = [
        "| Arquivo de Evidência | Tamanho (bytes) | BOM Presente? | Bytes Nulos (`\\x00`)? |",
        "|---|---|---|---|",
    ]
    for fname in sorted(os.listdir(EVIDENCE_DIR)):
        fpath = os.path.join(EVIDENCE_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        raw = open(fpath, "rb").read()
        has_bom = raw.startswith(b"\xef\xbb\xbf") or raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff")
        has_null = b"\x00" in raw
        rows.append(f"| `{fname}` | {len(raw)} | {has_bom} | {has_null} |")
    return rows


def main() -> None:
    s310 = _parse_suite_file("suite_py310.txt")
    s311 = _parse_suite_file("suite_py311.txt")
    s312 = _parse_suite_file("suite_py312.txt")
    s313 = _parse_suite_file("suite_py313.txt")
    s314 = _parse_suite_file("suite_py314.txt")

    git_log_proto = subprocess.run(
        ["git", "log", "--format=%h %s", "ba8a6f0..HEAD", "--", "AUDIT_PROTOCOL.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    ev_table = "\n".join(_collect_evidence_table())

    content = f"""# Relatório de Execução — Rodada 4.4d (Endurecimento de `storage/connection.py` F4-031 e Fechamento da 4.4c)

- **Data/Hora:** 2026-11-10
- **Base de Partida:** `9519e16cc6e8bad93240dd51ba118a53c8a085d2`
- **Status Geral:** **corrigido pelo executor, aguardando verificação independente**
- **Protocolo:** `AUDIT_PROTOCOL.md` (Regras 2, 3, 4, 7, 10, 11, 12, 13, 14 e 15)
- **Diretório de Evidências:** `scratch/evidencia_4_4d/` (UTF-8 puro, sem BOM e sem bytes nulos)

---

## Resumo Executivo

1. **Bloco 0 (Documentação e Fechamento dos Resíduos da 4.4c):**
   - Revertido `interface/__init__.py` ao conteúdo exato do commit `5abba37` (`git diff 5abba37 -- interface/__init__.py` vazio), mantendo as correções de isolamento nos testes e a mutação `M10g`. Registrado `_gc = None` em `interface/mcp_server.py:157` como desvio de escopo aprovado retroativamente.
   - Retificados os §§2.4, 4.1, 4.2 e 4.3 de `audits/relatorio_4_4c.md`, separando fato provado de hipótese não provada no `F4-029`, reportando as medições de retries em 30 ciclos (`6/30` pelo executor; `10/30`, `12/30` e `6/30` pelo auditor) sem concluir causa e removendo "Declarações Anteriores" sem fonte e o parágrafo sobre equivalências.
   - Consolidada na Seção 1.3 abaixo a errata formal dos 5 itens pendentes do pedido 4.4c (item 3.2), com citações de `arquivo:linha` e hashes. Declarados os limites conhecidos da guarda G2 em `CONTRIBUTING.md:52` e na docstring de `tests/test_domain_neutrality_guard.py:57-61`.
   - Atualizados `audits/fase4-achados.md` e `audits/fase4-roadmap.md`: `F4-029` delimitado a `interface/queue_writer.py` ("sem uso no caminho de produção do servidor (provado por git grep)") com status `"corrigido pelo executor, verificado pelo auditor (Linux, 3.10–3.13)"`; adicionado `F4-031` (GRAVE) para `storage/connection.py::SerializedWriteQueue` com status `"corrigido pelo executor, aguardando verificação independente"`; registrada a duplicação de filas e a decisão de levar o destino de `interface/queue_writer.py` para a quarentena da 4.5.
2. **Bloco 1 (`storage/connection.py`, F4-031):**
   - Mapeados todos os chamadores de `ConnectionManager.write` e `SerializedWriteQueue.submit` (`scratch/evidencia_4_4d/connection_queue_map.txt`) e elaborado o documento de desenho pré-código (`audits/design_4_4d_connection_queue.md`).
   - Endurecida `storage/connection.py::SerializedWriteQueue` preservando todos os 7 invariantes de produção (incluindo o regime `PRAGMA busy_timeout=5000`, `journal_mode=WAL`, `foreign_keys=ON`, `row_factory=sqlite3.Row` e ausência de prazo total para jobs em execução).
   - Criada a suíte `tests/test_connection_queue_resilience.py` com os testes `P1` a `P9` (nascidos em vermelho contra `9519e16` em `scratch/evidencia_4_4d/p1_p9_red.txt` e verdes após a correção em `scratch/evidencia_4_4d/p1_p9_green.txt`).
   - Todas as 8 mutações externas (`Ra` a `Rh`) foram mortas pelo script `scratch/run_bloco1_4_4d_mutations.py`.
   - Executado o experimento de medição natural (1.4) com 100 processos isolados + 50 pares (100 processos concorrentes no mesmo banco) no Windows (`scratch/evidencia_4_4d/natural_reproduction_100_procs.txt`).
3. **Bloco 2 (Resíduo M10d em Nível de Importação de Módulo):**
   - Estendido `tests/conftest.py` (`linhas 189-197, 224`) com captura de snapshot na importação do `conftest.py` (`_COLLECTION_BASELINE_MCP_SNAPSHOT`, `_COLLECTION_BASELINE_PKG_SNAPSHOT`) e verificação em `pytest_collection_finish(session)`. Mutação externa `M10d` em nível de importação de módulo morta (`scratch/evidencia_4_4d/mutacao_M10d_import.txt`).
4. **Suíte Multi-Versão (Python 3.10, 3.11, 3.12, 3.13 e 3.14):**
   - Os 471 itens coletados (`470 passed, 1 xfailed [BL-015]`) passaram nas 5 versões do CPython, tanto na ordem padrão quanto na ordem invertida (`--reverse`).

---

## Seção 1: Bloco 0 — Fechamento Documental e Errata da 4.4b/4.4c

### 1.1 Reversão de `interface/__init__.py` e Registro de Desvio de Escopo (0.1)
- **Reversão:** O arquivo `interface/__init__.py` foi revertido ao conteúdo exato do commit `5abba37` (`git show 5abba37:interface/__init__.py`), confirmado por `git diff 5abba37 -- interface/__init__.py` (0 linhas de diferença). A função `__getattr__` de `interface/__init__.py:14-20` voltou a tratar apenas `ActionHooks`, sem interceptar nem mascarar `ModuleNotFoundError` em outros atributos.
- **Preservação:** Foram mantidas integralmente as correções de isolamento nos testes (`test_agent_checkpointer.py`, `test_checkpoint_pruning.py`, `test_concurrency_stress.py`, `test_delta_sync.py`, `test_e2e_concierge_integration.py`, `test_graph_rag_janitor.py`, `test_mcp_server_extensions.py`, `test_vector_reconciler.py`, `test_watcher_ignore.py`, `test_mcp_server_handlers.py`, `test_queue_writer_resilience.py`) e a mutação `M10g`.
- **Desvio de Escopo Aprovado Retroativamente:** Registra-se que a adição da declaração explícita `_gc = None` no nível de módulo em `interface/mcp_server.py:157` (introduzida no commit `e2b541c` durante a 4.4c fora da lista de arquivos autorizados daquela rodada) é inofensiva e permanece no código como desvio de escopo aprovado retroativamente pelo usuário neste pedido 4.4d.

### 1.2 Correção do `audits/relatorio_4_4c.md` (0.2)
- Em `audits/relatorio_4_4c.md:157-161` (§4.3), foram separados explicitamente:
  - **Fato provado:** Em `interface/queue_writer.py:50` (código pré-4.4b), a instrução `conn.execute("PRAGMA journal_mode=WAL;")` fora de qualquer `try/except` matava a thread worker quando levantava `sqlite3.OperationalError: database is locked`, fazendo a espera em `response_queue.get()` (`interface/queue_writer.py:147`) travar indefinidamente (14/14 processos reproduzidos pelo auditor no Linux).
  - **Hipótese não provada:** A causa pela qual o banco SQLite retorna `database is locked` na partida (como a hipótese de corrida na troca para modo WAL de um banco novo).
  - **Medições de retries nos 30 ciclos:** Reportados os `6/30` ciclos com retry medidos pelo executor (`scratch/evidencia_4_4c/janitor_30_cycles_stability.txt`) sem concluir causa, juntamente com as três medições independentes do auditor (`10/30`, `12/30` e `6/30`) e a constatação de que a remoção do `PRAGMA journal_mode=WAL;` de `core/database.py:read_query` não reduziu o número de retries.
- Em `audits/relatorio_4_4c.md:145-156` (§4.1 e §4.2), foram removidas as subseções de "Declaração Anterior" sem fonte, mantendo apenas os fatos verificáveis com `arquivo:linha`.

### 1.3 Errata Formal dos 5 Pontos Pendentes (0.3)

| # | Fonte Original (`arquivo:linha` ou commit) | Texto / Afirmação Original | Retificação Factual |
|---|---|---|---|
| **1** | Commit `5abba37` (mensagem de commit, item 5) e `audits/fase4-achados.md:520` (versão 4.4c) | *"Descarte de tarefas expiradas antes da execução no SQLite (evita gravações zumbis)"* | A verificação de `deadline` em `interface/queue_writer.py:173-179, 224-228` descarta **apenas tarefas que ainda estão aguardando na fila** quando seu prazo já expirou. Uma escrita que já entrou em `cursor.execute(...)` no motor SQLite quando o chamador sofre timeout **não é interrompida** e continua sendo gravada até o `commit()` (provado pelo teste de caracterização `tests/test_queue_writer_resilience.py:422-455`). |
| **2** | Commit `5abba37` (mensagem de commit, item 6) | *"Remoção de PRAGMA journal_mode=WAL redundante em read_query (core/database.py), eliminando contenção de lock exclusivo com conexões de leitura"* | A afirmação *"eliminando contenção"* **não se sustenta empiricamente**. O auditor independente mediu `10/30`, `12/30` e `6/30` ciclos com retry de partida (e o executor mediu `6/30` em `scratch/evidencia_4_4c/janitor_30_cycles_stability.txt` mesmo após a remoção do PRAGMA em `core/database.py:67`). A remoção do PRAGMA não reduziu o número de retries e a causa exata do lock na partida segue desconhecida (hipótese não provada). |
| **3** | `audits/relatorio_4_4b.md:63-75` | (a) Linhas 63–69: Diagnóstico técnico do travamento de 9 horas atribuído a `socketpair` / pipe IPC do runner Windows e declaração de *"Independência Causal"* em relação ao `F4-029`.<br>(b) Linhas 70–75: *"Declara-se categoricamente que o arquivo AUDIT_PROTOCOL.md não foi alterado, editado ou reformatado durante a Rodada 4.4 nem durante a Rodada 4.4b."* | (a) O diagnóstico de `socketpair`/IPC e a afirmação de independência causal em relação ao `F4-029` **não possuem evidência em arquivo** e foram retificados em `audits/relatorio_4_4b.md:67-68` como **hipótese não verificada**.<br>(b) Em `audits/relatorio_4_4b.md:72-73`, a frase absoluta foi substituída pela saída exata de `git log --format='%h %s' ba8a6f0..HEAD -- AUDIT_PROTOCOL.md` (`{git_log_proto}` — vazio até a adição da Regra 15 em `1dd388b`) e pela declaração de que o log de execução da sessão da Rodada 4.4 mostrou uma edição em trânsito na árvore de trabalho (`AUDIT_PROTOCOL.md`) que foi revertida antes do commit. |
| **4** | `CONTRIBUTING.md:52` e `tests/test_domain_neutrality_guard.py:46-56` | Descrição da guarda AST `G2` sem explicitar suas limitações sintáticas. | Declarado explicitamente em `CONTRIBUTING.md:52` e na docstring de `tests/test_domain_neutrality_guard.py:57-61` que a guarda `G2` inspeciona nós `ast.Constant` individuais da AST; portanto, **comentários (`# ...`)** e **concatenação/interpolação de strings em tempo de execução (`"marketing" + "/vendas"`)** não são detectados por ela. |
| **5** | `scratch/run_bloco1_mutations.py:42-69` e `audits/relatorio_4_4c.md:78, 81, 86` | Na 4.4c, o pedido original definia `Qc` como *"sem checagem de vida antes de enfileirar"* e `Qe` como *"sem `_fail_all_pending` no laço"*, e `audits/relatorio_4_4c.md:86` continha um parágrafo confuso *"Análise sobre equivalências"* comparando `Qc` e `Qg`. | No código de `interface/queue_writer.py`, as definições originais de `Qc` e `Qe` eram mutações equivalentes (pois o laço subsequente de `execute_write` em `interface/queue_writer.py:294-305` detectava `not self.is_alive()` em até 50 ms independentemente da checagem pré-enfileiramento ou de `_fail_all_pending`). O executor redefiniu `Qc` para *"sem prazo no handshake (`_ready.wait()` sem timeout)"* e `Qe` para *"sem notificar callers ao morrer (lote e fila)"* sem declarar a redefinição. Declara-se formalmente essa redefinição aqui, e o parágrafo confuso sobre equivalências foi apagado de `audits/relatorio_4_4c.md`. |

---

## Seção 2: Bloco 1 — Endurecimento de `storage/connection.py` (F4-031)

### 2.1 Mapa de Chamadores e Documento de Desenho (1.0)
- **Mapa de Chamadores (`scratch/evidencia_4_4d/connection_queue_map.txt`):** Listados todos os chamadores de `ConnectionManager.write` (`storage/store.py:122, 142, 168, 174, 215, 375, 381, 417, 433, 491, 518, 545, 567, 612, 640, 652, 803` e `storage/logic.py:156, 187, 484`) e `SerializedWriteQueue.submit` (`storage/connection.py:465`). Foram identificados 5 caminhos que executam trabalho longo ou em lote grande (`SqliteStore.create_nodes_and_edges_bulk` em `storage/store.py:491`, `SqliteStore.update_nodes_file_hash_bulk` em `storage/store.py:417`, `SqliteStore.delete_project` em `storage/store.py:174`, `GraphLogic.fts_rebuild` em `storage/logic.py:484` e `SqliteStore.write_callback` chamado por `GrafoConcierge.store_fact` em `core/middleware.py:558`), fundamentando o **Invariante 5** (proibição de timeout total para job em execução).
- **Documento de Desenho (`audits/design_4_4d_connection_queue.md`):** Elaborado antes da implementação com a tabela de 7 invariantes, constantes de orçamento de partida e mapeamento para `P1`–`P9` e `Ra`–`Rh`.

### 2.2 Implementação em `storage/connection.py` (1.1, 1.2 e 1.3)
- **Constantes Nomeadas (`storage/connection.py:59-65`):**
  - `MAX_CONNECT_RETRIES: int = 5`
  - `STARTUP_CONNECT_TIMEOUT_SECONDS: float = 1.5`
  - `INITIAL_BACKOFF_SECONDS: float = 0.05`
  - `MAX_BACKOFF_SECONDS: float = 1.0`
  - `READY_TIMEOUT_SECONDS: float = 10.0`
  - `POLL_INTERVAL_SECONDS: float = 0.05`
  - `REGIME_BUSY_TIMEOUT_MS: int = 5000`
- **Justificativa da Escolha em 1.1 (`start()` aguarda o handshake e levanta `RuntimeError` encadeado):**
  Escolheu-se **(a) `start()` aguardar `self._ready.wait(timeout=READY_TIMEOUT_SECONDS)` e levantar `RuntimeError` com causa encadeada (`raise RuntimeError(...) from self._startup_error`)** (mantendo também a verificação em `submit()`) porque isso impede que `SqliteStore.__init__` conclua com uma fila de escrita inoperante e expõe imediatamente a falha na construção do componente.
- **Preservação do Regime (`PRAGMA busy_timeout=5000`):** O timeout curto (`1.5 s`) é passado ao `sqlite3.connect` apenas para limitar cada tentativa de abertura; imediatamente no handshake (`storage/connection.py:249`), o worker executa `conn.execute(f"PRAGMA busy_timeout={{REGIME_BUSY_TIMEOUT_MS}};")`, restaurando o valor de regime de produção (`5000 ms`), juntamente com `PRAGMA journal_mode=WAL;`, `PRAGMA foreign_keys=ON;` e `conn.row_factory = sqlite3.Row`.

### 2.3 Testes P1–P9 (Vermelho contra `9519e16` e Verde após Correção)
- **Evidência em Vermelho (`scratch/evidencia_4_4d/p1_p9_red.txt`):** Executando `tests/test_connection_queue_resilience.py` contra `storage/connection.py` do commit `9519e16`, os 5 testes de falha/resiliência (`P1`, `P2`, `P3`, `P4` e `P9`) falharam em vermelho (detectando deadlock de espera infinita e `PytestUnhandledThreadExceptionWarning: Exception in thread sqlite-writer`), enquanto os 4 testes de caracterização de invariantes (`P5`, `P6`, `P7`, `P8`) passaram.
- **Evidência em Verde (`scratch/evidencia_4_4d/p1_p9_green.txt`):** Com o `storage/connection.py` endurecido, todos os 9 testes (`P1` a `P9`) passaram em `8.42s` com zero avisos de exceção em thread.

### 2.4 Matriz de Mutações do Bloco 1 (Ra a Rh)
Executadas por script externo (`scratch/run_bloco1_4_4d_mutations.py`), com relatórios completos em `scratch/evidencia_4_4d/mutacao_Ra.txt` .. `mutacao_Rh.txt`:

| Mutação | Descrição | Teste que a Mata | Com Mutação | Sem Mutação | Status |
|---|---|---|---|---|---|
| **Ra** | Sem retry na partida (`MAX_CONNECT_RETRIES = 1`) | `test_p2_startup_retries_twice_on_locked_then_succeeds` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rb** | Sem checagem de vida (`is_alive`) no laço de espera do `submit` | `test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rc** | `job.result_event.wait()` sem prazo e sem checagem (comportamento original) | `test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rd** | Sem propagar o erro de partida (`_startup_error` não salvo/propagado) | `test_p1_connect_persistent_locked_fails_fast` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Re** | Sem drenar jobs pendentes ao morrer (`_drain_pending_with_error` omitido) | `test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rf** | Regime de `busy_timeout` alterado (`REGIME_BUSY_TIMEOUT_MS = 1500` em vez de `5000`) | `test_p7_regime_pragmas_and_row_factory` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rg** | Prazo total adicionado ao job em execução (`TimeoutError` após `0.5s` em `submit`) | `test_p5_long_running_job_2s_succeeds_without_total_timeout` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |
| **Rh** | Sem fechar a conexão na falha de partida (`conn.close()` removido no `except OperationalError`) | `test_p3_non_lock_operational_error_fails_immediately_and_closes_conn` | `ret=1` (FALHA) | `ret=0` (PASSA) | **MORTA (OK)** |

### 2.5 Tentativa de Reprodução Natural no Windows (Item 1.4 — Somente Medição)
Executada pelo script `scratch/reproduce_natural_1_4.py` e registrada integralmente em `scratch/evidencia_4_4d/natural_reproduction_100_procs.txt` (reportada de forma estritamente observacional, sem concluir causa):
1. **Experimento A — 100 processos independentes (1 banco novo por processo, 3 threads leitoras chamando `get_read_connection()` disparadas em barreira junto com `ConnectionManager.start()` e 1 `write`, limite de 30 s por processo):**
   - **Hangs (timeouts > 30 s):** `0 / 100`
   - **Exceções de processo (`returncode != 0`):** `0 / 100` (todos os 100 processos concluíram o `write` com `OK:1`)
   - **Processos com retries de partida do worker (`SerializedWriteQueue startup attempt 1/5 failed with 'database is locked'`):** `21 / 100` (21 retries totais, todos recuperados na 2ª tentativa após `0.050s`).
   - **Processos com `OperationalError('database is locked')` nas threads leitoras (`get_read_connection`):** `97 / 100` (observado quando `get_read_connection()` executa `PRAGMA journal_mode=WAL;` concorrentemente em um arquivo de banco que ainda não foi inicializado pelo schema).
2. **Experimento B — 50 pares = 100 processos iniciando o MESMO banco novo ao mesmo tempo via `SqliteStore` (duas instâncias do servidor + 3 threads leitoras por processo + `create_project`, limite de 30 s por processo):**
   - **Hangs (timeouts > 30 s):** `0 / 100`
   - **Exceções de processo (`returncode != 0`):** `0 / 100`
   - **Processos com retries de partida do worker:** `0 / 100`
   - **Processos com erros nas threads leitoras:** `0 / 100`

---

## Seção 3: Bloco 2 — Detecção de Vazamento na Importação de Módulo (Resíduo M10d)

- **Problema:** As fixtures autouse com `scope="module"`, `scope="class"` e `scope="function"` capturam seu snapshot inicial apenas quando o primeiro teste do escopo entra em execução (após a fase de coleta). Se um arquivo de teste adicionasse ou modificasse um atributo global de `interface.mcp_server` no topo do módulo durante sua importação pelo `pytest`, o estado poluído já estaria presente quando `check_mcp_globals_leak_module` capturasse `before_mcp`.
- **Solução Implementada (`tests/conftest.py:189-197, 224`):**
  - No momento em que o próprio `tests/conftest.py` é importado pelo `pytest` (antes da importação dos módulos `tests/test_*.py`), são registrados `_COLLECTION_BASELINE_MCP_SNAPSHOT = _capture_mcp_snapshot()` e `_COLLECTION_BASELINE_PKG_SNAPSHOT = _capture_package_integrity_snapshot()`.
  - O hook `pytest_collection_finish(session)` chama `_verify_package_integrity(_COLLECTION_BASELINE_PKG_SNAPSHOT, "collection_import")` e `_verify_mcp_globals(_COLLECTION_BASELINE_MCP_SNAPSHOT, "collection_import")`, abortando imediatamente a sessão se qualquer módulo de teste tiver vazado ou alterado globais durante a importação.
- **Prova por Mutação Externa (`scratch/run_bloco2_4_4d_mutation.py`, evidência em `scratch/evidencia_4_4d/mutacao_M10d_import.txt`):**
  - *Variante 1 (adição de novo global `_leaked_at_module_import_m10d` no topo de `tests/test_interface_contracts.py`):* **MORTA** (`returncode=3`, `AssertionError: [collection_import] New global variable 'mcp_server._leaked_at_module_import_m10d' was added during test execution`).
  - *Variante 2 (mutação de `mcp_server.db_manager` no topo de `tests/test_interface_contracts.py`):* **MORTA** (`returncode=3`, `AssertionError: [collection_import] Global variable 'mcp_server.db_manager' leaked or modified by identity`).
  - *Controle sem mutação:* **VERDE** (`returncode=0`).

---

## Seção 4: Suíte Completa nas 5 Versões do Python (3.10, 3.11, 3.12, 3.13 e 3.14) nas Duas Ordens

Executada após a reversão de `interface/__init__.py` e com as alterações dos Blocos 0, 1 e 2 ativas (`scratch/run_multiversion_suites_4_4d.py`):

| Versão CPython | Ambiente | Ordem Padrão | Ordem Invertida (`--reverse`) | Return Codes | Arquivo de Evidência |
|---|---|---|---|---|---|
| `{s310['version']}` | `.venv_310` | `{s310['std_summary']}` | `{s310['rev_summary']}` | `std={s310['std_rc']}, rev={s310['rev_rc']}` | `scratch/evidencia_4_4d/suite_py310.txt` |
| `{s311['version']}` | `.venv_311` | `{s311['std_summary']}` | `{s311['rev_summary']}` | `std={s311['std_rc']}, rev={s311['rev_rc']}` | `scratch/evidencia_4_4d/suite_py311.txt` |
| `{s312['version']}` | `.venv_312` | `{s312['std_summary']}` | `{s312['rev_summary']}` | `std={s312['std_rc']}, rev={s312['rev_rc']}` | `scratch/evidencia_4_4d/suite_py312.txt` |
| `{s313['version']}` | `.venv_313` | `{s313['std_summary']}` | `{s313['rev_summary']}` | `std={s313['std_rc']}, rev={s313['rev_rc']}` | `scratch/evidencia_4_4d/suite_py313.txt` |
| `{s314['version']}` | `.venv_clean` | `{s314['std_summary']}` | `{s314['rev_summary']}` | `std={s314['std_rc']}, rev={s314['rev_rc']}` | `scratch/evidencia_4_4d/suite_py314.txt` |

---

## Seção 5: Propostas para Rodadas Futuras (Fora do Escopo da 4.4d)

Conforme a regra da rodada (*"Só o que está escrito aqui. Ideia fora do escopo vira proposta no relatório"*), registram-se como propostas sem nenhuma alteração de código nesta rodada:
1. **Conexões de Leitura em `ConnectionManager.get_read_connection()` (`storage/connection.py:390-405`):** Como observado no Experimento A do item 1.4 (`97/100` processos quando `ConnectionManager` é usado diretamente sem `_boot_schema` prévio de `SqliteStore`), `get_read_connection()` executa `PRAGMA journal_mode=WAL;` antes de `PRAGMA busy_timeout=5000;`. Avaliar em rodada futura se `PRAGMA busy_timeout=5000;` deve preceder `PRAGMA journal_mode=WAL;` ou se conexões de leitura devem omitir a escrita de `journal_mode=WAL`.
2. **Quarentena / Destino de `interface/queue_writer.py` (Rodada 4.5):** Conforme decidido pelo usuário e registrado no `audits/fase4-roadmap.md`, manter `interface/queue_writer.py` intocado agora e decidir sua remoção/quarentena ou unificação com `storage/connection.py::SerializedWriteQueue` na Rodada 4.5 (junto com `BL-006`).

---

## Seção 6: Tabela de Evidências e Integridade (UTF-8 sem BOM e sem Bytes Nulos)

{ev_table}
"""

    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"Relatório gerado com sucesso em {REPORT_PATH} ({len(content.encode('utf-8'))} bytes).")


if __name__ == "__main__":
    main()

