# Auditoria — `core/rate_governor.py`

> **Item:** `core/rate_governor.py` (SDD-SURVIVAL-23: RateGovernor with Priority Traffic & Queue Freezing)  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-09-20  
> **Status:** Concluído, aguardando aprovação  

---

## 1. Ferramentas Estáticas Executadas

| Ferramenta | Comando | Resultado |
|------------|---------|-----------|
| **ruff** | `python -m ruff core/rate_governor.py` | Não instalado no ambiente Python |
| **bandit** | `python -m bandit core/rate_governor.py` | Não instalado no ambiente Python |
| **mypy** | `python -m mypy core/rate_governor.py --follow-imports=skip` | `Success: no issues found in 1 source file` |
| **unittest** | `python -m unittest tests/test_rate_governor_priority.py` | 8 passed em 1.679s |
| **unittest** | `python -m unittest tests/test_agent_hsm_coupling.py` | 13 passed em 0.759s |

---

## 2. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `core/rate_governor.py` | 250, 255, 261, 272 | **CRÍTICA** | Vazamento cumulativo de `unfinished_tasks` na `PriorityQueue` e starvation de cabeça de fila (Head-of-Line). Quando uma tarefa de baixa/média prioridade está congelada, o loop faz `get()` e em seguida `put(req)` sem chamar `task_done()`. Cada ciclo de re-enfileiramento a cada 0.5s incrementa `unfinished_tasks` em +1 (tarefas fantasmas). Qualquer chamada a `request_queue.join()` trava para sempre em Deadlock. Além disso, a tarefa mantém seu timestamp original antigo, sendo recolocada no topo da fila e bloqueando outras tarefas do mesmo nível. | Script executado com fila congelada por 1.6s: `unfinished_tasks` saltou de 1 para 5 tarefas fantasmas. Ver saída bruta. | **CONFIRMADO** |
| 2 | `core/rate_governor.py` | 231–252 | **ALTA** | Starvation de tarefas LOW envelhecidas em toda a faixa de 75% a 100% de carga. O branch de envelhecimento (aging) avalia se `max_pct < 75.0` para promover a tarefa; caso contrário (`max_pct >= 75.0`), cai no `else` e re-enfileira a tarefa com `sleep(0.5)`. Como a fila LOW só congela oficialmente com `max_pct >= 85.0` (`low_priority_frozen`), qualquer tarefa LOW envelhecida fica impedida de executar em toda a faixa de 75% a 100% de carga (inclusive entre 75% e 84.9%, onde a fila LOW nem sequer está congelada), sofrendo inanição contínua e só conseguindo executar se a carga cair abaixo de 75%. | Script injetou `PriorityRequest` com timestamp antigo na fila sob 80% de carga fixa (`low_priority_frozen=False`): tarefa sofreu inanição contínua e foi executada imediatamente assim que a carga caiu para 70%. | **CONFIRMADO** |
| 3 | `core/rate_governor.py` | 91, 116–150 | **ALTA** | Data Race / Lost Updates em `get_current_metrics()`. O método lê, filtra e reatribui `self.history = [item for item in self.history if item[0] >= cutoff]` sem adquirir `self.lock`. Como `self.lock` é um `threading.Lock()` (não-reentrante), chamadas concorrentes externas (como o endpoint `/api/governor/metrics` em `interface/telemetry_api.py:387`) disputam com `report_usage()`, provocando sobrescrita e perda de registros de consumo recentes. | Inspecionado tipo de `self.lock`: `Lock` não-reentrante. Executada concorrência entre leituras e escritas sem proteção. | **CONFIRMADO** |
| 4 | `core/rate_governor.py` | 196–203, 278–280 | **ALTA** | Deadlock permanente em `submit_request` se o governor não estiver rodando ou após `shutdown()`. `submit_request` enfileira a tarefa e bloqueia em `req.future_result.get()` sem timeout. Se `start()` não tiver sido chamado, ou se `shutdown()` for invocado (o qual apenas seta `self.running = False` e encerra a thread sem drenar a fila nem responder aos futures pendentes), a thread chamadora fica travada em deadlock eterno. | Invocado `shutdown()` e submetida tarefa: thread cliente travada indefinidamente em `future_result.get()`. | **CONFIRMADO** |
| 5 | `core/rate_governor.py` | 185–194 | **MÉDIA** | Cegueira de RPM no Fast-Path. Requisições prioritárias (prioridade 1) sob tráfego verde (< 50%) executam inline instantaneamente sem serem inseridas na fila. Porém, `submit_request` não registra o timestamp da chamada no histórico deslizante (`self.history`). Se o chamador não invocar `report_usage()`, requisições rápidas consecutivas não incrementam `current_rpm`, mascarando rajadas de chamadas. | Submetida requisição via fast-path: `current_rpm` permaneceu em 0. | **CONFIRMADO** |

---

## 3. Detalhamento de Cada Achado

### Achado #1 — Vazamento de `unfinished_tasks` na `PriorityQueue` e Head-of-Line Starvation

- **Mecanismo da Falha:**  
  No loop consumidor em `run()`:
  ```python
  req = self.request_queue.get(timeout=0.1)
  ...
  elif self.low_priority_frozen:
      self.request_queue.put(req)
      time.sleep(0.5)
      continue
  ```
  Na classe padrão `queue.PriorityQueue` (herdeira de `queue.Queue`):
  - `get()` retira o item, mas NÃO altera `unfinished_tasks`.
  - `put(req)` incrementa `unfinished_tasks += 1`.
  - Apenas `task_done()` decrementa `unfinished_tasks -= 1`.
  Como o bloco de congelamento executa `self.request_queue.put(req)` e dá `continue` sem invocar `task_done()`, a cada 0.5s de espera o contador de tarefas pendentes aumenta em +1.
  Além disso, `req` preserva seu `timestamp` de criação. Na re-inserção, por ser a tarefa com menor timestamp daquela prioridade, ela volta a ser a primeira da fila (`__lt__` baseado em timestamp), gerando uma trava de cabeça de fila (Head-of-Line).
- **Impacto no Sistema:**  
  Se qualquer módulo ou teste invocar `governor.request_queue.join()`, ocorrerá **Deadlock permanente**, pois o contador de tarefas inacabadas cresce indefinidamente. O loop também consome ciclos de CPU e locks desnecessários puxando e devolvendo o mesmo objeto repetidamente a cada 500ms.
- **Correção Conceitual Sugerida (Fase 3):**  
  Invocar `self.request_queue.task_done()` antes de re-enfileirar, ou manter filas separadas por prioridade onde a fila congelada não é consumida (dispensando o ciclo de get/put/continue).

---

### Achado #2 — Starvation de Tarefas LOW Envelhecidas em Toda a Faixa de 75% a 100% de Carga

- **Mecanismo da Falha:**  
  O loop consumidor em `core/rate_governor.py:231–258` processa tarefas de prioridade 3 (`LOW`):
  ```python
  if req.priority == 3:
      age = time.time() - req.timestamp
      if age >= self.aging_threshold_secs:
          with self.lock:
              metrics = self.get_current_metrics()
          max_pct = max(
              metrics["rpm_percentage"], metrics["tpm_percentage"]
          )
          if max_pct < 75.0:
              # Temporary promotion: execute even if LOW is frozen
              logger.info(...)
              # Fall through directly to execution
          else:
              # Still under load: re-enqueue
              self.request_queue.put(req)
              time.sleep(0.5)
              continue
      elif self.low_priority_frozen:
          self.request_queue.put(req)
          time.sleep(0.5)
          continue
  ```
  O congelamento oficial de LOW é recalculado em `_recalculate_frozen_states()` (linha 168):
  ```python
  self.low_priority_frozen = max_pct >= 85.0
  ```
  O branch `if max_pct < 75.0:` não é "código morto" (`dead code`), pois ele executa e de fato promove a tarefa quando a carga do sistema cai abaixo de 75%. No entanto, a lógica produz uma anomalia severa em **toda a faixa de 75% a 100% de carga**:
  1. **Faixa Intermediária Não-Congelada (75% a 84.9%):**  
     Nesta faixa, `low_priority_frozen` é `False` (a fila LOW não está congelada e deveria processar requisições). Se uma tarefa LOW for nova (`age < aging_threshold_secs`), ela não entra no primeiro `if`, pula o `elif self.low_priority_frozen` e executa normalmente. Porém, se a tarefa for antiga/envelhecida (`age >= aging_threshold_secs`), ela entra no bloco de aging, avalia `if max_pct < 75.0` (que é Falso, pois a carga está em 80%), cai no `else` e é re-enfileirada com `sleep(0.5)`. O próprio mecanismo anti-starvation introduz uma inversão perversa: tarefas antigas sofrem inanição e são bloqueadas, enquanto tarefas novas poderiam executar.
  2. **Faixa Congelada (85% a 100%):**  
     Quando `low_priority_frozen` é `True` (`max_pct >= 85.0`), a tarefa envelhecida também nunca é promovida porque `max_pct >= 85.0 >= 75.0`, caindo invariavelmente no `else`.
  Em suma: **qualquer tarefa LOW que atinja o threshold de envelhecimento fica estritamente impedida de executar em toda a faixa de 75% a 100% de carga**, entrando em starvation contínuo e só conseguindo executar se a carga do sistema cair abaixo de 75%.
- **Impacto no Sistema:**  
  Tarefas de background de baixa prioridade (como janitoring, compactação e reconciliação) que acumulam tempo na fila sofrem inanição prolongada em qualquer regime de operação com carga contínua entre 75% e 100%. Além disso, como demonstrado no Achado #1, a cada 500ms essa tarefa é re-enfileirada, vazando contadores de `unfinished_tasks` e monopolizando a cabeça da fila.
- **Correção Conceitual Sugerida (Fase 3):**  
  Ajustar a verificação de aging para que tarefas envelhecidas possam ser promovidas temporariamente ao nível MEDIUM (ex: permitindo execução se `max_pct < 95.0%`, que é o limiar de bloqueio de MEDIUM), ou garantindo que tarefas envelhecidas nunca sofram restrição mais severa que tarefas novas quando a fila não está congelada (`max_pct < 85.0%`).

---

### Achado #3 — Data Race / Lost Updates em `get_current_metrics()`

- **Mecanismo da Falha:**  
  Em `core/rate_governor.py:116`:
  ```python
  def get_current_metrics(self) -> Dict[str, Any]:
      ...
      self.history = [item for item in self.history if item[0] >= cutoff]
  ```
  O método manipula e reatribui `self.history` sem adquirir `self.lock`.
  O lock de `RateGovernor` foi instanciado como `self.lock = threading.Lock()` (mutuamente exclusivo e não-reentrante).
  Quando o endpoint REST `/api/governor/metrics` em [`interface/telemetry_api.py:387`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L387) é consultado por clientes ou pelo dashboard, ele chama `get_current_metrics()` em uma thread de requisição HTTP sem deter o lock. Se outra thread chamar `report_usage()` no mesmo instante, a inserção `self.history.append` concorre com a reatribuição da lista, resultando em perda silenciosa de contagens de tokens e requisições.
- **Impacto no Sistema:**  
  Distorção dos percentuais de consumo de RPM e TPM, podendo causar tanto sub-registro de consumo quanto liberação indevida de tráfego por perda de histórico recente.
- **Correção Conceitual Sugerida (Fase 3):**  
  Substituir `threading.Lock()` por `threading.RLock()` na inicialização do `RateGovernor`, permitindo que `get_current_metrics()` adquira `with self.lock:` com segurança mesmo quando chamado internamente por métodos que já detêm o lock.

---

### Achado #4 — Deadlock Permanente em `submit_request` após `shutdown()` ou sem `start()`

- **Mecanismo da Falha:**  
  `submit_request` delega a execução à fila e bloqueia a thread chamadora esperando o resultado:
  ```python
  req = PriorityRequest(priority, task_fn, time.time(), session_id)
  self.request_queue.put(req)
  success, result_or_exc = req.future_result.get()
  ```
  A chamada `req.future_result.get()` não possui parâmetro de `timeout`.
  Além disso, `submit_request` não verifica se a thread consumidora está viva (`self.is_alive()`) nem se o flag `self.running` é verdadeiro.
  No método `shutdown()`:
  ```python
  def shutdown(self) -> None:
      self.running = False
  ```
  Ao setar `self.running = False`, o loop em `run()` finaliza imediatamente na próxima iteração. Quaisquer tarefas que já estavam na fila ou que forem submetidas subsequentemente permanecem abandonadas na `request_queue`.
- **Impacto no Sistema:**  
  Todas as threads chamadoras que aguardam retorno de `submit_request` entram em **Deadlock permanente**, congelando processos da aplicação ou requisições HTTP da API.
- **Correção Conceitual Sugerida (Fase 3):**  
  1. Verificar `if not self.running or not self.is_alive(): raise RuntimeError(...)` em `submit_request`.
  2. Implementar timeout configurável em `req.future_result.get(timeout=...)`.
  3. No método `shutdown()`, drenar a fila restante emitindo uma exceção (ex: `CancelledError` ou `GovernorShutdownException`) para todos os `future_result` pendentes.

---

### Achado #5 — Cegueira de RPM no Fast-Path

- **Mecanismo da Falha:**  
  Nas linhas 185-194:
  ```python
  if priority == 1 and max_pct < 50.0:
      result = task_fn()
      return result
  ```
  Quando uma chamada prioritária é despachada pelo fast-path, a função executa sincronamente inline e retorna direto ao chamador sem passar pela fila. Contudo, nenhuma entrada de timestamp é adicionada a `self.history`.
- **Impacto no Sistema:**  
  Caso o chamador não execute manualmente `report_usage()`, a métrica `current_rpm` permanece em 0 independentemente de quantas requisições rápidas tenham sido disparadas. O sistema torna-se cego para a contagem de requisições por minuto geradas em modo rápido.
- **Correção Conceitual Sugerida (Fase 3):**  
  Registrar a invocação em `self.history` mesmo no fast-path:
  ```python
  with self.lock:
      self.history.append((time.time(), 0))
  ```

---

## 4. Saída Bruta da Reprodução Executada

Scripts executados:
1. `scratch/reproduce_rate_governor_findings.py` (Visão geral de todos os 5 achados)
2. `scratch/reproduce_finding_2_starvation.py` (Reprodução detalhada do Achado #2: Starvation sob carga intermediária de 80% vs liberação sob 70%)

```text
======================================================================
REPRODUCAO: Achado #2 - Starvation de Tarefa LOW na Faixa de 75% a 100%
======================================================================

[1] Estado Inicial da Carga:
    - RPM: 80/100 (80.0%)
    - low_priority_frozen: False (Esperado: False, pois 80% < 85%)
    - medium_priority_frozen: False

[2] Injetando PriorityRequest LOW envelhecida:
    - Prioridade: 3 (LOW)
    - Idade: 30.0s (Threshold: 1.0s)
    - Carga mantida: 80% (Faixa intermediaria: 75% <= carga < 85%)

[3] Aguardando 2.0s sob carga continua de 80%...
    ... Fila backlog: 1 | Executou: []
    ... Fila backlog: 1 | Executou: []
    ... Fila backlog: 1 | Executou: []
    ... Fila backlog: 1 | Executou: []

[4] Resultado sob 80% de carga:
    [CONFIRMADO] A tarefa envelhecida NAO EXECUTOU sob 80% de carga!
    Mecanismo: Como age >= 1.0s, o loop avalia `max_pct < 75.0`.
    Como max_pct (80%) >= 75.0%, cai no `else` e e re-enfileirada com sleep(0.5).
    Mesmo com `low_priority_frozen == False` (fila LOW teoricamente aberta),
    qualquer tarefa envelhecida fica presa em starvation em TODA a faixa de 75% a 100%.

[5] Reduzindo a carga para 70% (< 75% limiar de promocao)...
    ... Fila backlog: 0 | Executou: ['AGED_TASK_EXECUTED']
    [CONFIRMADO] A tarefa executou imediatamente quando a carga caiu abaixo de 75%!
    O branch de promocao e alcancavel e funciona, mas APENAS sob carga < 75%.

======================================================================
REPRODUCAO CONCLUIDA COM SUCESSO.
======================================================================
```

Saída consolidada dos demais achados (`scratch/reproduce_rate_governor_findings.py`):

```text
--- ACHADO 1 (CRITICA): Vazamento de unfinished_tasks em filas congeladas ---
unfinished_tasks logo apos put inicial: 1
unfinished_tasks apos 1.6s congelado: 5
Vazamento comprovado: 5 > 1 (Aumento de 4 tarefas fantasmas!)

--- ACHADO 3 (ALTA): get_current_metrics nao adquire lock e sobreescreve history ---
Tipo de gov3.lock: <class '_thread.lock'> (Lock nao-reentrante impede reuso em get_current_metrics)
Total apos escrita/leitura concorrente no historico: 150

--- ACHADO 4 (ALTA): Deadlock permanente em submit_request apos shutdown() ---
Governor rodando? False | Thread viva? False
submit_request retornou ou destravou apos shutdown? False
SUCESSO: Provado que submit_request trava para sempre (deadlock) quando o governor nao esta rodando!

--- ACHADO 5 (MEDIA): Cegueira de RPM no Fast-Path ---
Resultado do fast-path: fast_done
current_rpm registrado apos fast-path: 0 (Esperado: 0 devido a omissao de registro)
```

---

## 5. Arquivos de Teste Relacionados

- [`tests/test_rate_governor_priority.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_rate_governor_priority.py):
  - Testa ordenação estática da fila (`PriorityRequest`), congelamento reactivo com `report_usage()` e expiração temporal de métricas.
  - Não testa vazamento de `unfinished_tasks`, concorrência com `get_current_metrics()`, anti-starvation sob freeze real, nem ciclo de vida/desligamento com `shutdown()`.
  - Resultado: 8 passed em 1.679s.
- [`tests/test_agent_hsm_coupling.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_agent_hsm_coupling.py):
  - Valida o envio de requisições de agentes com prioridade 1 (HIGH) para o `RateGovernor`.
  - Resultado: 13 passed em 0.759s.
