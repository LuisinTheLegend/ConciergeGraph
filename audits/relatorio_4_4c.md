# Relatório de Execução — Rodada 4.4c (Fechamento da 4.4b)

- **Data/Hora:** 2026-11-08
- **Base de Partida:** `5abba37`
- **Status Geral:** **corrigido pelo executor, aguardando verificação independente**
- **Protocolo:** AUDIT_PROTOCOL.md (incluindo Regra 15 - EGM)
- **Diretório de Evidências:** `scratch/evidencia_4_4c/` (UTF-8 puro, sem BOM, sem bytes nulos)

---

## Resumo Executivo

A rodada 4.4c encerra com rigor absoluto os resíduos da rodada 4.4b e soluciona a regressão comprovada pela auditoria independente no commit `5abba37`:
1. **Regra 15 Adotada no AUDIT_PROTOCOL.md:** Formalização do protocolo para subagentes EGM (não decidem, não commitam, exigem teste vermelho prévio, matriz de invariantes e mutações de validação). Relatórios de auditoria da 4.4b incorporados sem edição em `audits/egm/`.
2. **Resolução da Regressão de Busy Timeout no `queue_writer`:** A conexão persistente do worker do SQLite teve seu timeout de regime de 30s restaurado imediatamente após o handshake de inicialização (`PRAGMA busy_timeout = 30000;`), sem overhead de reconexão. O teste T9 comprovou a falha em vermelho no código do `5abba37` e o sucesso na 4.4c.
3. **Lacunas de Concorrência e Resiliência Eliminadas:** Mutações residuais Qb e Qg mortas com os testes T10 e T11; implementada falha rápida (<0.2s) para chamadas antes de `start()`; caracterização determinística de escritas em voo não-canceláveis no SQLite. Todas as 8 mutações do Bloco 1 (Qa a Qh) foram mortas com evidências registradas.
4. **Fixture Autouse Dinâmica de Globais em Três Níveis:** Substituição da lista estática por derivação dinâmica baseada em snapshot de `vars(mcp_server)` no início de cada escopo (`function`, `class`, `module`), com allowlist explícita documentada. Mutações M10a a M10e eliminadas e validação da suíte inteira em ordem padrão e invertida com 0 falhas (M10f).
5. **Registro Factual e Evidências:** Documentação com `arquivo:linha` da mutação de globais em testes de integração, funcionamento e limites do AST na guarda G2, e separação entre fato provado e hipótese no achado F4-029 (com relato dos 30 ciclos sem mock).

---

## Seção 1: Bloco 0 — Regra 15 e Rastreabilidade do EGM

### 1.1 Regra 15 no `AUDIT_PROTOCOL.md`
A Regra 15 foi adicionada verbatim ao final de `AUDIT_PROTOCOL.md` no commit `1dd388b`, sem qualquer outra modificação no arquivo (`git diff` comprovadamente limpo):
```markdown
Regra 15: Uso do EGM (Elephant-Goldfish Model).
(a) Subagentes EGM apenas propõem; não commitam, não alteram código e não decidem.
(b) O executor só implementa o que constar em pedido aprovado pelo humano.
(c) O relatório de cada revisor EGM é salvo em audits/egm/<rodada>-<papel>.md; o que não está em arquivo não conta como evidência (regra 12).
(d) Todo achado do EGM que gere mudança de código exige teste vermelho antes da correção, uma lista “o que não pode mudar” (invariantes) com teste ou mutação para cada item, e uma mutação que mata a correção.
(e) O EGM não substitui a verificação independente do auditor.
(f) Uso indicado: decisões de desenho caras de reverter e revisão de pedidos antes da execução; não usar para correções pequenas nem para verificar código.
```

### 1.2 Relatórios Originais EGM Preservados
Os relatórios gerados pelos subagentes EGM nos commits `8659813` e `5abba37` foram extraídos diretamente dos logs integrais do transcript (`transcript_full.jsonl`) e persistidos sem qualquer edição em:
- `audits/egm/4.4b-design.md`: Avaliação crítica de arquitetura, concorrência e riscos do worker daemon (11.805 bytes).
- `audits/egm/4.4b-codebase-details.md`: Auditoria técnica de implementação, contratos de erro e reuso de bibliotecas (17.475 bytes).

---

## Seção 2: Bloco 1 — Resiliência e Concorrência do `queue_writer`

### 2.1 Invariantes do Subsistema
| Invariante | Definição / Restrição | Mecanismo de Garantia / Teste |
|---|---|---|
| **I1** | Espera por lock em regime é de 30s | `REGIME_BUSY_TIMEOUT_MS = 30000` via PRAGMA; Teste T9 e mutação Qh |
| **I2** | Contrato de retorno `(False, e)` preservado | Preservado em `execute_write` sem levantar exceções não-tratadas |
| **I3** | Worker opera em WAL e `synchronous=NORMAL` | Executados no handshake inicial do SQLite |
| **I4** | Partida falha rápido (<10s) quando tentativas esgotam | Orçamento total (7.5s + 0.75s = 8.25s) < 10.0s; Teste T1 |
| **I5** | Tarefa com prazo vencido na fila não é executada | Checagem de `deadline` ao retirar item da fila; Teste T7 |
| **I6** | Nenhum `except: pass` novo | Tratamentos defensivos explícitos com log de debug |

### 2.2 Correção da Regressão do Busy Timeout (1.1)
- **Problema:** No commit `5abba37`, a abertura de conexão `sqlite3.connect(self.db_path, timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)` (1.5s) configurou permanentemente o busy timeout da conexão SQLite para 1500ms. Quando uma conexão concorrente segurava o lock por 3.0s, o worker falhava prematuramente com `sqlite3.OperationalError: database is locked`.
- **Solução Adotada:** Manter timeout de 1.5s exclusivo durante o handshake de conexão inicial e, imediatamente após a confirmação dos PRAGMAs WAL e synchronous, emitir:
  `conn.execute(f"PRAGMA busy_timeout = {REGIME_BUSY_TIMEOUT_MS};")`
  onde `REGIME_BUSY_TIMEOUT_MS = 30000`. Essa abordagem restaura o regime de 30s instantaneamente sem exigir fechamento e reabertura de socket/arquivo de banco (zero overhead).
- **Orçamento de Partida:** Constantes nomeadas:
  `MAX_CONNECT_RETRIES = 5`, `STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5`, `INITIAL_BACKOFF_SECONDS = 0.05`, `MAX_BACKOFF_SECONDS = 1.0`.
  O orçamento máximo de partida é `5 * 1.5s + (0.05 + 0.1 + 0.2 + 0.4)s = 7.5s + 0.75s = 8.25s < 10.0s (READY_TIMEOUT_SECONDS)`. Provado no teste `test_startup_budget_strictly_less_than_ready_timeout`.
- **Teste T9 e Vermelho:** Registrado em `scratch/evidencia_4_4c/t9_and_prestart_red.txt`. O código `5abba37` falhou com `sqlite3.OperationalError: database is locked` ao tentar escrever sob lock externo de 3s. O código atual aguarda os 3s e conclui com sucesso.
- **Mutação Qh:** Alterar `REGIME_BUSY_TIMEOUT_MS = 1500` faz o teste T9 falhar com retcode 1 (MORTA com sucesso).

### 2.3 Cobertura T10, T11, Pré-start e Caracterização (1.2 e 1.3)
- **T10:** Simula morte por exceção no laço principal do worker (`_execute_single` levantando `SystemError`). Chamadores esperando recebem `(False, ...)` em menos de 5s, e chamadas subsequentes falham em menos de 1s sem travar.
- **T11:** Múltiplas tarefas acumuladas concorrentemente na fila quando o laço do worker quebra. Todos os chamadores são drenados e notificados com falha rápida (<5s).
- **Pré-start:** Se `execute_write` for invocado antes de `.start()`, a checagem `if self.ident is None:` retorna imediatamente `(False, RuntimeError("SerializedWriteQueue worker thread has not been started."))` em menos de 0.2s, sem esperar os 10s de handshake.
- **Caracterização:** Teste determinístico `test_characterization_inflight_write_may_apply_after_timeout` comprova que uma escrita que já entrou no motor do SQLite (`cursor.execute`) quando o chamador Python estourou timeout não é cancelada e conclui a transação com `conn.commit()`, gravando o registro em disco. A semântica de `TimeoutError` foi devidamente documentada na docstring de `execute_write`.

### 2.4 Matriz de Mutações do Bloco 1 (Qa a Qh)
Todas as 8 mutações foram executadas externamente pelo script `scratch/run_bloco1_mutations.py` contra `interface/queue_writer.py`, gerando evidências individuais em `scratch/evidencia_4_4c/`:

| Mutação | Descrição | Arquivo / Alvo | Resultado c/ Mutação | Resultado s/ Mutação | Status |
|---|---|---|---|---|---|
| **Qa** | Sem retry na inicialização (`MAX_CONNECT_RETRIES = 1`) | `test_t2_connect_retry_and_eventual_success` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **Qb** | Sem checagem de vida no laço de espera (`is_alive` removido do poll) | `test_t10_worker_death_in_loop...` | TIMEOUT (ret=999) | PASSA (ret=0) | **MORTA (OK)** |
| **Qc** | Sem prazo no handshake (`_ready.wait()` sem timeout) | `test_t5_unready_worker_handshake...` | TIMEOUT (ret=999) | PASSA (ret=0) | **MORTA (OK)** |
| **Qd** | Sem nenhuma checagem de vida (`is_alive` removido totalmente) | `test_t3_worker_thread_late_death...` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **Qe** | Sem notificar callers ao morrer (notificação de lote e fila removida) | `test_t6_batch_fatal_error_notifies...` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **Qf** | Sem sinalizar prontidão na falha final (`_ready.set` removido na falha) | `test_t1_connect_persistent_failure...` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **Qg** | `response_queue.get()` bloqueante sem timeout | `test_t10_worker_death_in_loop...` | TIMEOUT (ret=999) | PASSA (ret=0) | **MORTA (OK)** |
| **Qh** | Espera de regime reduzida para 1,5s (`REGIME_BUSY_TIMEOUT_MS = 1500`) | `test_t9_busy_timeout_regime...` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |

### 2.5 Mapeamento de Uso em Produção e Runtime (1.5)
Registrado em `scratch/evidencia_4_4c/queue_writer_map.txt`:
1. **Dualidade de Filas:**
   - `interface/queue_writer.py::SerializedWriteQueue`: Herda de `threading.Thread`, implementa `execute_write(query, params) -> Tuple[bool, Any]`, auto-batching e fallback atômico. É utilizada em 11 suítes de teste de integração. No entanto, em produção no servidor MCP (`interface/mcp_server.py:162`), `ConciergeDatabaseManager` é instanciado sem passar `write_queue` (`write_queue=None`), executando conexões efêmeras diretas via `sqlite3.connect`.
   - `storage/connection.py::SerializedWriteQueue`: Implementa classe independente que gerencia thread `sqlite-writer` e método `submit(fn, *args, **kwargs) -> Any`. É utilizada internamente por `storage/store.py::SqliteStore`.
2. **Tratamento de TimeoutError:**
   - Todos os chamadores de `execute_write` (`core/alias_tracker.py`, `core/checkpointer.py`, `storage/relational_db.py`) tratam o par `(False, err)` capturando o erro ou registrando em log sem permitir que exceções não-tratadas subam para a camada externa.

### 2.6 Estabilidade em 30 Ciclos Sem Mock (1.6)
Registrado em `scratch/evidencia_4_4c/janitor_30_cycles_stability.txt`:
- **Execução:** 30 ciclos consecutivos de `pytest tests/test_graph_rag_janitor.py tests/test_graph_rag_loops.py` sem instrumentação ou mocks.
- **Resultado:** 30 de 30 ciclos verdes (100% de sucesso).
- **Tempo:** Total de 147.23s (média de 4.91s por ciclo, min: 4.68s, max: 5.29s).
- **Retries de Inicialização Observados:** Em 6 dos 30 ciclos (ciclos 9, 15, 19, 21, 27, 29), foram detectadas colisões transitórias de abertura do SQLite WAL registradas em log de aviso (`WARNING: SerializedWriteQueue startup connection attempt ... Retrying in ...`). Em todos os 6 casos, o backoff exponencial recuperou a conexão nas tentativas subsequentes com sucesso absoluto, provando na prática a eficácia da proteção contra corridas de abertura sob concorrência real.

---

## Seção 3: Bloco 2 — Fixture Autouse de Detecção de Vazamento de Globais

### 3.1 Arquitetura da Fixture em Três Níveis
Implementada em `tests/conftest.py` com três fixtures autouse independentes:
1. `check_mcp_globals_leak_function` (`scope="function"`): Audita vazamentos entre funções de teste individuais.
2. `check_mcp_globals_leak_class` (`scope="class"`): Audita vazamentos gerados no `setup_class` ou entre métodos de classes de teste.
3. `check_mcp_globals_leak_module` (`scope="module"`): Audita vazamentos em nível de módulo de teste ou fixtures com escopo de módulo.

*Justificativa da Abordagem:* O uso de fixtures separadas por escopo é a abordagem idiomática do pytest. Ela respeita o ciclo de vida nativo das estruturas de teste, garantindo que snapshots sejam capturados exatamente antes da execução de cada camada e validados imediatamente ao término da respectiva camada, isolando o ponto exato da contaminação.

### 3.2 Derivação Dinâmica e Allowlist
- **Snapshot Dinâmico:** Inspeciona `vars(mcp_server)` filtrando todos os atributos que sejam candidatos mutáveis (exclui dunders, módulos, funções puras, métodos, classes puras, tipos de `typing` e features do `__future__`).
- **Validações Executadas no Teardown:**
  1. *Deleções:* Detecta se qualquer global presente no início foi removido via `del` (M10e).
  2. *Adições:* Detecta se qualquer global novo foi injetado dinamicamente no módulo (M10d).
  3. *Mutação por Identidade:* Compara `id(curr) == id(orig)`. Se a identidade do objeto for alterada, o teste falha reportando o nome da variável, o valor esperado e o valor obtido (M10a, M10b, M10c).
- **Allowlist Documentada:**
  ```python
  _MCP_GLOBALS_ALLOWLIST = {
      # Allowlist documentada: nenhuma variável global de interface.mcp_server possui autorização
      # para vazar mutações permanentes entre testes, classes ou módulos.
  }
  ```

### 3.3 Matriz de Mutações do Bloco 2 (M10a a M10f)
Todas as mutações foram executadas pelo script `scratch/run_bloco2_mutations.py` e comprovadas:

| Mutação | Escopo / Nível | Arquivo Alvo | Resultado c/ Mutação | Resultado s/ Mutação | Status |
|---|---|---|---|---|---|
| **M10a** | Função (`scope="function"`) | `test_e2e_concierge_integration.py` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **M10b** | Classe (`scope="class"`) | `test_mcp_server_handlers.py::TestHandleMine` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **M10c** | Módulo (`scope="module"`) | `test_mcp_server_handlers.py` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **M10d** | Adição de global novo | `test_e2e_concierge_integration.py` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **M10e** | Remoção de global (`del _gc`) | `test_e2e_concierge_integration.py` | FALHA (ret=1) | PASSA (ret=0) | **MORTA (OK)** |
| **M10f** | Ausência de falso positivo (ordem padrão e invertida) | Suíte inteira (57 arquivos, 457 testes) | PASSA em ambas as ordens (ret=0) | - | **VALIDADO (0 falhas)** |

*Efeito Colateral Sanado Durante M10f:* A introdução da fixture de escopo de módulo revelou que as fixtures de módulo `server` em `tests/test_mcp_server_handlers.py` e `tests/test_interface_contracts.py` instanciavam `GrafoConciergeServer` sem restaurar os globais `db_manager`, `checkpointer`, `graph_rag`, `_gc` e `governor` ao final dos respectivos módulos. Ambas foram devidamente corrigidas com blocos `yield` e restauração completa de estado no teardown, eliminando a poluição cruzada entre suítes.

---

## Seção 4: Registro Factual sobre Testes de Integração, Guarda G2 e Achado F4-029

Em conformidade com as exigências de precisão factual e separação entre fato provado e hipótese do `AUDIT_PROTOCOL.md`, registram-se os fatos verificáveis com `arquivo:linha`:

### 4.1 Mutações de Globais em Testes de Integração (`interface.mcp_server`)
- **Fato Provado:** Múltiplos testes de integração modificam atributos globais do módulo `interface.mcp_server` (`db_manager`, `checkpointer`, `graph_rag`, `governor`, `_gc`), seja por atribuição direta, `monkeypatch.setattr` ou instanciação de `GrafoConciergeServer`: `tests/test_mcp_server_extensions.py:72-76`, `tests/test_mcp_server_handlers.py:42-56, 300-303`, `tests/test_interface_contracts.py:29-42`, `tests/test_governor_wiring.py:130-141` e `tests/test_call_chain_edges_nodes.py:390-415`. Os testes foram ajustados com restauração explícita em teardown e são fiscalizados pelas fixtures autouse de `tests/conftest.py:92-125`.

### 4.2 Funcionamento e Limites do AST da Guarda G2
- **Fato Provado:** A guarda G2 (`tests/test_domain_neutrality_guard.py:46-130`) descobre dinamicamente os arquivos Python rastreados via `git ls-files '*.py'`, analisa a árvore sintática abstrata (`ast.parse`) e inspeciona cada nó literal (`ast.Constant` com `isinstance(node.value, str)`) através de `ast.walk`, incluindo docstrings de módulos, classes e funções. Fiscaliza os 7 termos compostos proibidos por busca de substring normalizada (sem acentos e case-insensitive) e o termo isolado `"estatística"` / `"estatistica"` por igualdade exata.
- **Limites Conhecidos da Guarda G2:** Por inspecionar apenas nós `ast.Constant` individuais da árvore sintática, a guarda G2 **não detecta** termos escritos em comentários (`# ...`, que são descartados pelo parser AST) nem strings formadas por concatenação ou interpolação em tempo de execução (por exemplo, `"marketing" + "/vendas"`).

### 4.3 Fatos Provados vs. Hipóteses no Achado F4-029
- **Fato Provado:** Em `interface/queue_writer.py:50` (antes da Rodada 4.4b), a instrução `conn.execute("PRAGMA journal_mode=WAL;")` era executada fora de qualquer bloco `try/except`. Quando essa instrução levantava `sqlite3.OperationalError: database is locked`, a thread trabalhadora (`SerializedWriteQueue.run`) encerrava prematuramente e qualquer chamada a `execute_write` (`interface/queue_writer.py:147`) ficava bloqueada indefinidamente em `response_queue.get()` sem timeout (reproduzido pelo auditor em 14 de 14 processos no Linux).
- **Hipótese Não Provada:** A causa pela qual o SQLite retorna `database is locked` na partida (como a hipótese de corrida na troca para modo WAL de um banco recém-criado sob conexões concorrentes) **não está provada**.
- **Medições de Retries em 30 Ciclos (Sem Concluir Causa):** Na bateria de 30 ciclos sem mock executada pelo executor no Windows (`scratch/evidencia_4_4c/janitor_30_cycles_stability.txt`), observaram-se retries de partida em `6/30` ciclos (ciclos 9, 15, 19, 21, 27 e 29). O auditor independente mediu `10/30`, `12/30` e `6/30` em três medições de 30 ciclos, e verificou que a remoção de `PRAGMA journal_mode=WAL;` de `core/database.py:read_query` não reduziu o número de retries observados.

---

## Seção 5: Tabela de Evidências e Integridade dos Arquivos

Todos os arquivos de evidência foram gravados sob `scratch/evidencia_4_4c/`, em formato UTF-8 puro, sem marca de ordem de byte (BOM) e com verificação de zero bytes nulos (`\x00`):

| Arquivo de Evidência | Tamanho (bytes) | BOM Presente? | Bytes Nulos (`\x00`)? |
|---|---|---|---|
| `janitor_30_cycles_stability.txt` | 5120 | False | False |
| `mutacao_M10a.txt` | 6955 | False | False |
| `mutacao_M10b.txt` | 6610 | False | False |
| `mutacao_M10c.txt` | 12194 | False | False |
| `mutacao_M10d.txt` | 6770 | False | False |
| `mutacao_M10e.txt` | 6677 | False | False |
| `mutacao_M10f.txt` | 2122 | False | False |
| `mutacao_M10g.txt` | 7489 | False | False |
| `mutacao_Qa.txt` | 4625 | False | False |
| `mutacao_Qb.txt` | 3370 | False | False |
| `mutacao_Qc.txt` | 1889 | False | False |
| `mutacao_Qd.txt` | 5082 | False | False |
| `mutacao_Qe.txt` | 9835 | False | False |
| `mutacao_Qf.txt` | 5848 | False | False |
| `mutacao_Qg.txt` | 3277 | False | False |
| `mutacao_Qh.txt` | 4991 | False | False |
| `python310_reproduce_red.txt` | 17356 | False | False |
| `queue_writer_green.txt` | 7065 | False | False |
| `queue_writer_map.txt` | 4661 | False | False |
| `suite_py310.txt` | 11471 | False | False |
| `suite_py311.txt` | 12086 | False | False |
| `suite_py312.txt` | 14758 | False | False |
| `suite_py314.txt` | 13885 | False | False |
| `t9_and_prestart_red.txt` | 4833 | False | False |

---

## Seção 6: Bloco 0b — Resolução da Suíte no Python 3.10 (Falha de CI Ubuntu 3.10) e Suíte Multi-Versão

### 6.1 Reprodução do Teste Vermelho (0b.1)
- **Fato Apurado:** No Python 3.10 (Ubuntu CI e localmente em Windows via CPython 3.10.22), a execução de `test_queue_writer_resilience.py` após qualquer um dos 8 arquivos geradores de poluição falhava com:
  `AttributeError: module 'interface' has no attribute 'queue_writer'`
- **Reprodução:** Evidenciada em `scratch/evidencia_4_4c/python310_reproduce_red.txt`. Três testes (`test_t1`, `test_t2`, `test_t5`) falharam imediatamente com o `AttributeError`.

### 6.2 Correção dos Testes Novos (0b.2)
Em `tests/test_queue_writer_resilience.py`, todas as ocorrências de `unittest.mock.patch("interface.queue_writer...")` por string foram substituídas por patches diretos no objeto importado (`patch.object(qw_module.sqlite3, "connect", ...)`, `patch.object(qw_module, "READY_TIMEOUT_SECONDS", 0.05)`, etc.), desacoplando os testes da navegação de pacotes via `getattr` no Python 3.10.

### 6.3 Diagnóstico e Tratamento da Poluição do Namespace `interface` (0b.3)
1. **Causa Raiz:**
   - **Mecanismo Python 3.10 vs 3.11+:** No Python 3.10, `unittest.mock.patch("a.b.c")` navega recursivamente atributo a atributo a partir do pacote pai com `getattr(a, "b")`. A partir do Python 3.11+, o mock tenta consultar `sys.modules.get("a.b")` diretamente antes de recorrer ao `getattr`.
   - **Poluição por Carga Cirúrgica Órfã:** 8 arquivos de teste (`test_agent_checkpointer.py`, `test_checkpoint_pruning.py`, `test_concurrency_stress.py`, `test_delta_sync.py`, `test_e2e_concierge_integration.py`, `test_graph_rag_janitor.py`, `test_mcp_server_extensions.py`, `test_vector_reconciler.py`) e `test_watcher_ignore.py` utilizavam `importlib.util.spec_from_file_location` registrando submódulos em `sys.modules` (`sys.modules["interface.queue_writer"]`, `sys.modules["interface.watcher"]`) sem importar o pacote pai `interface` nem vincular o atributo correspondente no pacote pai.
   - **Stubs Desalinhados:** Testes criavam módulos stub genéricos `types.ModuleType("interface")` sem os atributos dos submódulos e sem o `__getattr__` dinâmico do pacote real, e o `tearDownClass` removia `interface` via `sys.modules.pop("interface")`, deixando os submódulos órfãos em `sys.modules`.
   - **PEP 562 em `interface/__init__.py`:** A função `__getattr__` original só tratava `ActionHooks` e levantava `AttributeError` para qualquer outro nome, tornando invisíveis submódulos já carregados em `sys.modules`.
2. **Correção do Padrão Comum:**
   - Em `interface/__init__.py`, `__getattr__` foi atualizado para verificar se `f"interface.{name}"` já existe em `sys.modules` ou é importável, registrando no `globals()` antes de retornar o módulo.
   - Nos 8 arquivos de teste e em `test_watcher_ignore.py`, a criação de stubs foi eliminada em favor de `import interface` e vinculação explícita de `setattr(sys.modules["interface"], "<submod>", _mod)`.
   - Em `test_e2e_concierge_integration.py` e `test_mcp_server_extensions.py`, o `tearDownClass` restaura e sincroniza `interface.mcp_server` e `interface.queue_writer` com `sys.modules`.
   - Em `test_mcp_server_handlers.py`, restauração segura de globais no `finally` de `TestHandleDeleteProject` e dos campos de projeto em `TestHandleUpdateProject`.
3. **Fixture de Integridade em Três Níveis e Mutação M10g:**
   - A fixture autouse de `tests/conftest.py` foi estendida com `_verify_package_integrity` nos escopos `function`, `class` e `module`. Para qualquer submódulo `interface.<submod>` em `sys.modules`, a fixture valida que `sys.modules.get("interface")` existe, `submod in vars(interface)` é verdadeiro e o objeto é idêntico por `is`.
   - **Mutação M10g:** Executada externamente via `scratch/run_bloco0b_mutation.py`, desvincula `queue_writer` de `sys.modules["interface"]`. A fixture capturou a mutação nos três níveis (`[function]`, `[class]`, `[module]`) com retcode 1, e sem a mutação a suíte passou limpa com retcode 0 (`scratch/evidencia_4_4c/mutacao_M10g.txt`).

### 6.4 Critério de Aceite: Suíte Completa Multi-Versão (0b.4)
A suíte completa de 462 testes foi executada em **quatro versões do interpretador CPython**, nas ordens padrão e invertida (`--reverse`), alcançando **100% de aprovação**:

| Versão CPython | Ambiente | Ordem Padrão | Ordem Invertida (`--reverse`) | Testes Totais | Status |
|---|---|---|---|---|---|
| **Python 3.10.22** | `.venv_310` | 461 passed, 1 xfailed (128.45s) | 461 passed, 1 xfailed (119.60s) | 462 | **PASSOU (0 falhas, 0 erros)** |
| **Python 3.11.18** | `.venv_311` | 461 passed, 1 xfailed (117.21s) | 461 passed, 1 xfailed (117.96s) | 462 | **PASSOU (0 falhas, 0 erros)** |
| **Python 3.12.16** | `.venv_312` | 461 passed, 1 xfailed (226.02s) | 461 passed, 1 xfailed (117.04s) | 462 | **PASSOU (0 falhas, 0 erros)** |
| **Python 3.14.3** | `.venv_clean` | 461 passed, 1 xfailed (220.99s) | 461 passed, 1 xfailed (192.65s) | 462 | **PASSOU (0 falhas, 0 erros)** |

Evidências completas registradas em:
- `scratch/evidencia_4_4c/suite_py310.txt`
- `scratch/evidencia_4_4c/suite_py311.txt`
- `scratch/evidencia_4_4c/suite_py312.txt`
- `scratch/evidencia_4_4c/suite_py314.txt`

---

## Verificação Final de Segurança e Rastreabilidade

1. **Scan de Segredos:** Executado via `scripts/scan_secrets.py` com zero ocorrências de credenciais, chaves ou tokens.
2. **Histórico e Commits:** Trabalho executado linearmente sobre `5abba37`, sem `rebase`, sem `amend` e sem `--force`.
3. **Sincronização Remota:** Todos os blocos entregues em commits separados e validados contra `origin/main`.
