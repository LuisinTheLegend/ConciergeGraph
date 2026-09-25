# Relatório de Auditoria: `agent/` e `agents/` (Runtime Cognitivo e Auditor Crítico)

> **Data:** 24 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE (Regra 7)  
> **Prioridade Geral:** 🟠 **ALTA ESTRUTURAL (SEVERIDADES CONDICIONAIS — CÓDIGO ÓRFÃO)**  
> **Arquivos Auditados:**
> - [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py) (267 linhas)
> - [`agent/agent_prompts.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/agent_prompts.py) (177 linhas)
> - [`agents/revisor_critico.py`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py) (611 linhas)

---

## 1. Resumo Executivo e Contexto de Execução

Conforme comprovado no item anterior (`bypass-governanca-por-session-id`, Achado #4), o servidor FastMCP em produção (`interface/mcp_server.py`) **não instancia nem acopla** as classes `CognitiveAgentRunner`, `HierarchicalStateMachine` ou `RevisorCritico`. O "estado" do servidor em execução resume-se a strings em um dicionário estático em memória gerenciado pelo `MCPToolGovernor`.

Portanto, **os três arquivos aqui auditados operam como código órfão em produção**, sendo exercitados exclusivamente por testes unitários e de integração isolados (`test_agent_hsm_coupling.py` e `test_revisor_critico.py`). 

### Nota Obrigatória sobre o Padrão de Severidade Condicional
Diferente dos módulos de `storage/`, `core/` e `ingestion/` (onde cada bug crítico representa uma falha ativa no servidor em produção), os achados deste relatório possuem **SEVERIDADE CONDICIONAL**:
- **Nenhum destes bugs afeta a operação do servidor real hoje**, enquanto este código permanecer desconectado.
- **Se e quando o time de desenvolvimento decidir "reconectar" ou unificar o runtime cognitivo ou os hooks de revisão**, estes bugs se tornarão imediatamente falhas em tempo de execução (vazamento de dados confidenciais, negação de serviço entre sessões, falsas aprovações de commits e falhas de reranking).
- Cada achado traz explicitamente a classificação `(CONDICIONAL / CÓDIGO ÓRFÃO)` para orientar a decisão arquitetural na Fase 3: **consertar integralmente antes de reconectar, ou expurgar o código morto do repositório**.

---

## 2. Tabela Consolidada de Achados

| # | Arquivo(s) | Linha(s) | Severidade | Mecanismo Resumido | Status |
|---|---|---|---|---|---|
| **#1** | [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L47) | `47, 82, 95, 123, 154, 160` | 🔴 **CRÍTICA (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Contaminação de Turnos Multi-Sessão no Circuit Breaker**: `self.current_substate_turn_count` é um inteiro único de instância da classe compartilhado entre todas as sessões. Inicializar ou transicionar uma sessão zera indevidamente o contador de outras; sessões concorrentes somam seus passos no mesmo contador global, provocando bloqueios espúrios em `STALL.ERROR_PAUSE` (*Cross-Session Denial of Service*). | **CONFIRMADO E REPRODUZIDO** |
| **#2** | [`agents/revisor_critico.py`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L555-L573) | `555–573` | 🔴 **CRÍTICA (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Vazamento de Privacidade por Fallback Inseguro e Sensibilidade a Caixa (Case-Sensitivity)**: `check_contamination` usa `privacy_hierarchy.get(source_privacy, 0)` sem normalizar `.upper()`. Qualquer string em minúsculas (`"restricted"`) ou sinônimo corporativo (`"CONFIDENTIAL"`, `"SECRET"`) recebe nível `0` (`PUBLIC`), avaliando `source_level > target_level` como `False` e aprovando a transferência de dados ultra-secretos para contextos públicos (violação do princípio de *Fail-Closed*). | **CONFIRMADO E REPRODUZIDO** |
| **#3** | [`agents/revisor_critico.py`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L331) | `331, 362–381` | 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Aprovação Espúria de Commits Inválidos e Incompatibilidade de Assinatura em `audit_with_retry`**: O docstring prescreve `Callable(task, outcome, feedback)`, mas o código chama `generate_fn(result.reason)` (1 argumento). Se a função lançar exceção no 1º loop, o bloco `except` aciona `break` e retorna `approved=True, partial_audit=True, loop_count=max_loops`, aprovando automaticamente um rascunho com defeito sem ter executado as tentativas. | **CONFIRMADO E REPRODUZIDO** |
| **#4** | [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L151-L217) | `151–217` | 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Dessincronização de Estado e Diretrizes em `step(target_transition=...)`**: `step()` constrói o prompt dinâmico usando o estado ANTERIOR (`current_path`) e só depois efetua a transição solicitada. O LLM recebe no prompt instruções e proibições da fase antiga (ex.: `PLANNING: Nenhuma mutação física autorizada`), enquanto o retorno já indica o novo estado (`EXECUTION.CODE_GEN`), gerando alucinações e bloqueios cognitivos. | **CONFIRMADO E REPRODUZIDO** |
| **#5** | [`agents/revisor_critico.py`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L433) | `433, 490–498, 504–513` | 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Defeitos de Tipagem e Crash em Reranking (`NoneType` e `int` vs `str`)**: (1) `_heuristic_rerank` quebra com `TypeError` se algum nó contiver `score_final: None`; (2) `_llm_rerank` força `relevance_map[int(nid)]`, descartando 100% dos candidatos caso `node_id` venha como `str` (padrão de nós vetoriais e paths); (3) se o mapa não casar, retorna lista vazia `[]`, violando a garantia de retornar ao menos 1 resultado. | **CONFIRMADO E REPRODUZIDO** |
| **#6** | [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L243-L262) | `243–262` | 🟡 **MÉDIA (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Incompatibilidade Estrutural Universal com Corrotinas e Bypass do RateGovernor em `execute_tool`**: Funções assíncronas (`async def`) nunca funcionam corretamente através do pipeline de governança, independente da configuração: (1) no caminho **COM Gating e COM Governor**, a worker thread (e o fast-path) do `RateGovernor.submit_request` executa `task_fn()` sem `await`, enquanto o `GatingInterceptor` executa `return execute_fn()` sincronicamente, devolvendo uma corrotina crua não executada (`Tool actually executed: False`); (2) no caminho **COM Gating e SEM Governor**, `execute_fn()` chama `dummy_fn()` sem `await`, também devolvendo corrotina não-executada; (3) no caminho **SEM Gating e COM Governor**, a linha `if inspect.iscoroutinefunction(dummy_fn): return await dummy_fn()` executa a ferramenta diretamente com `await`, mas **ignora e contorna 100% o enfileiramento do RateGovernor** (`Governor requests recorded: 0`). Em nenhuma configuração uma ferramenta assíncrona é governada e executada corretamente. | **CONFIRMADO E REPRODUZIDO** |
| **#7** | [`agent/agent_prompts.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/agent_prompts.py#L82-L132) | `82–132` | 🟡 **MÉDIA (CONDICIONAL / CÓDIGO ÓRFÃO)** | **Dessincronização Estrutural entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX`**: `parse_state_path` decompõe apenas o super-estado. As entradas de sub-estados declaradas na matriz do governor (`DISCOVERY`, `TDD_GREEN`, `REFACTORING`) nunca são consultadas pelo builder, tornando-se regras mortas. | **CONFIRMADO** |

---

## 3. Detalhamento Técnico dos Achados e Mecanismos de Falha

### Achado #1: Contaminação de Turnos Multi-Sessão no Circuit Breaker
- **Severidade:** 🔴 **CRÍTICA (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agent/run_agent.py:47, 82, 95, 123, 154, 160`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L47)
- **Mecanismo:**
  Na classe `CognitiveAgentRunner`, o contador de turnos no sub-estado é declarado como um inteiro simples na instância:
  ```python
  self.current_substate_turn_count = 0
  self.session_turn_counts: Dict[str, int] = {}
  ```
  Embora `self.session_turn_counts` seja um dicionário indexado por `session_id`, o Circuit Breaker (linhas 154–160) verifica exclusivamente `self.current_substate_turn_count`:
  ```python
  self.current_substate_turn_count += 1
  if self.current_substate_turn_count > self.max_substate_turns:
      # Transiciona para STALL.ERROR_PAUSE
  ```
  Isso gera duas anomalias graves sob qualquer uso concorrente ou multi-sessão:
  1. **Reset Cruzado Indevido:** Quando uma nova sessão é iniciada (`initialize_session(session_2)`) ou transicionada (`transition_to`), ela executa `self.current_substate_turn_count = 0`, zerando o orçamento de turnos de todas as outras sessões em andamento e permitindo que agentes em loop infinito nunca atinjam o limite.
  2. **Bloqueio Espúrio (Cross-Session Starvation):** Se a Sessão 1 executar 3 passos e a Sessão 2 executar 3 passos no mesmo runner, o contador global atinge 6. No passo seguinte da Sessão 1 (que seria apenas o seu 4º passo real), o Circuit Breaker dispara e força a sessão para `STALL.ERROR_PAUSE`, paralisando agentes legítimos sem que eles tenham excedido seus próprios orçamentos.

---

### Achado #2: Vazamento de Privacidade por Fallback Inseguro e Sensibilidade a Caixa (Case-Sensitivity)
- **Severidade:** 🔴 **CRÍTICA (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agents/revisor_critico.py:555-573`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L555-L573)
- **Mecanismo:**
  O método `check_contamination` implementa o modelo de segurança multinível (Bell-LaPadula simplificado) para impedir que dados de projetos `RESTRICTED` fluam para contextos `PUBLIC`:
  ```python
  source_privacy = source_project.get("privacy_level", "PUBLIC")
  target_privacy = target_project.get("privacy_level", "PUBLIC")

  privacy_hierarchy = {"PUBLIC": 0, "INTERNAL": 1, "RESTRICTED": 2}
  source_level = privacy_hierarchy.get(source_privacy, 0)
  target_level = privacy_hierarchy.get(target_privacy, 0)

  if source_level > target_level:
      return False, "CONTAMINATION BLOCKED..."
  return True, "OK — no contamination risk."
  ```
  A falha reside na violação do princípio de *Fail-Closed*:
  - Não há conversão para maiúsculas (`.upper()`). Se `source_project["privacy_level"]` contiver `"restricted"` (minúsculo), o lookup no dicionário falha e cai no valor padrão `0` (`PUBLIC`).
  - Se for utilizada uma nomenclatura comum em metadados externos (como `"CONFIDENTIAL"` ou `"SECRET"`), o valor também é mapeado para `0`.
  - Como `target_level` para `PUBLIC` é `0`, a comparação `source_level > target_level` avalia `0 > 0`, que é `False`.
  - O método retorna `is_safe = True`, autorizando formalmente a contaminação e **vazando segredos e códigos proprietários de projetos restritos para contextos públicos**.

---

### Achado #3: Aprovação Espúria de Commits Inválidos e Incompatibilidade de Assinatura em `audit_with_retry`
- **Severidade:** 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agents/revisor_critico.py:331, 362-381`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L331)
- **Mecanismo:**
  No método `audit_with_retry`, o docstring especifica o contrato:
  `generate_fn: Callable(task, outcome, feedback) -> dict`.
  No entanto, o código invoca:
  ```python
  try:
      current_draft = generate_fn(result.reason)
  except Exception as e:
      logger.error("Failed to regenerate draft: %s", e)
      break
  ```
  Se o cliente implementar `generate_fn` com a assinatura de 3 parâmetros documentada, a chamada falha com `TypeError`.
  O efeito colateral mais destrutivo ocorre após a captura da exceção:
  O bloco `except` aciona um `break` imediato no loop de retry (mesmo que estivesse na tentativa 1 de 3). Logo após o loop, o método assume cegamente que as tentativas foram esgotadas e retorna:
  ```python
  final = AuditResult(
      approved=True,
      reason=f"Approved by partial_audit after {self._max_loops} rejections.",
      technical_changes=current_draft.get("technical_changes", ""),
      updated_pointers=current_draft.get("updated_pointers", []),
      partial_audit=True,
      loop_count=self._max_loops,
  )
  return final
  ```
  Isso faz com que um commit **inválido, reprovado e não regenerado seja marcado como APROVADO (`approved=True`)** logo na primeira falha, emitindo ainda um falso log de que "3 tentativas foram executadas e rejeitadas".

---

### Achado #4: Dessincronização de Estado e Diretrizes em `step(target_transition=...)`
- **Severidade:** 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agent/run_agent.py:151-217`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L151-L217)
- **Mecanismo:**
  Em `CognitiveAgentRunner.step()`, a ordem dos procedimentos é:
  ```python
  current_path = self.hsm.get_current_state(session_id)
  ...
  # 2. Constrói o Prompt usando current_path (estado antigo)
  system_prompt = self.prompt_builder.build_prompt(
      session_id=session_id, current_state=current_path, ...
  )
  # 3. Executa a transição para target_transition (novo estado)
  if target_transition:
      self.transition_to(session_id=session_id, target_path=target_transition, ...)

  active_state = self.hsm.get_current_state(session_id)
  return {
      "status": "executed",
      "active_state": active_state,
      "prompt": system_prompt,
  }
  ```
  Quando o agente solicita uma transição direta (ex.: de `PLANNING.DISCOVERY` para `EXECUTION.CODE_GEN`), o `system_prompt` é gerado antes da transição.
  O LLM recebe um prompt dizendo:
  `[ESTADO ATIVO: PLANNING.DISCOVERY] - Nenhuma mutação física em arquivos é autorizada neste estágio.`
  Contudo, o retorno indica `active_state: EXECUTION.CODE_GEN`.
  Durante todo o ciclo de raciocínio deste turno, o modelo age sob as restrições cognitivas e de segurança da fase anterior, recusando-se a gerar código ou executando instruções incompatíveis.

---

### Achado #5: Defeitos de Tipagem e Crash em Reranking (`NoneType` e `int` vs `str`)
- **Severidade:** 🟠 **GRAVE (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agents/revisor_critico.py:433, 490-498, 504-513`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L433)
- **Mecanismo:**
  1. **Crash em `_heuristic_rerank`:** O método calcula `max_score = max(c.get("score_final", 0) for c in candidates)`. Se um candidato tiver explicitamente `{"node_id": 1, "score_final": None}`, `.get("score_final", 0)` retorna `None` (a chave existe). O `max()` entre float e `None` lança `TypeError: '>' not supported between instances of 'NoneType' and 'float'`.
  2. **Descarte Total de Resultados em `_llm_rerank` por Incompatibilidade de Tipo:**
     O método popula o mapa de relevâncias com chaves inteiras forçadas:
     `relevance_map[int(nid)] = float(rel)`.
     Ao filtrar os candidatos:
     `nid = c.get("node_id")`
     `relevance = relevance_map.get(nid, 0.0)`.
     Nos sistemas de busca e grafo (`storage/`, `ingestion/`), identificadores de nós frequentemente trafegam como strings (ex.: `"42"`, paths ou hashes). A busca de uma chave string num dicionário com chaves inteiras (`{42: 0.95}.get("42", 0.0)`) retorna `0.0`. Todos os candidatos são rejeitados por estarem abaixo do threshold de 0.5.
  3. **Violação da Garantia de Retorno Mínimo:** A documentação afirma que o método garante ao menos 1 resultado (`Guarantees at least 1 result`). Porém, quando `relevance_map` não cruza com os candidatos, o bloco de recuperação (`if not approved and candidates:`) tenta encontrar `best_nid`, falha e retorna `[]` (lista vazia).

---

### Achado #6: Incompatibilidade Estrutural Universal com Corrotinas e Bypass do RateGovernor em `execute_tool`
- **Severidade:** 🟡 **MÉDIA (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agent/run_agent.py:243-262`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L243-L262), [`core/gating_interceptor.py:139`](file:///c:/Nexus-Memory/GrafoConcierge/core/gating_interceptor.py#L139), [`core/rate_governor.py:192, 267`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L192)
- **Mecanismo:**
  O método `execute_tool` tenta integrar três camadas sucessivas de governança (`MCPToolGovernor` -> `GatingInterceptor` -> `RateGovernor`):
  ```python
  def _run_with_governor():
      if self.governor:
          return self.governor.submit_request(priority=1, session_id=session_id, task_fn=dummy_fn)
      return dummy_fn()

  if self.gating:
      return await self.gating.intercept_tool_call(..., execute_fn=_run_with_governor)

  if inspect.iscoroutinefunction(dummy_fn):
      return await dummy_fn()
  return _run_with_governor()
  ```
  Quando a ferramenta fornecida em `execute_fn` é assíncrona (`async def` ou função que retorna corrotina, como é o padrão no ecossistema MCP/FastMCP), a execução falha estruturalmente em **todos os cenários de configuração**:

  1. **Caminho COM Gating e COM Governor:**
     - `execute_tool` chama `await self.gating.intercept_tool_call(..., execute_fn=_run_with_governor)`.
     - Dentro de `GatingInterceptor.intercept_tool_call`, a linha 139 faz `return execute_fn()`, chamando `_run_with_governor` de forma **estritamente síncrona** (sem `await`).
     - `_run_with_governor` despacha a tarefa chamando `self.governor.submit_request(..., task_fn=dummy_fn)`.
     - Conforme documentado e confirmado na auditoria de `core/rate_governor.py`:
       - No fast-path (linha 192), o governor executa `result = task_fn()`.
       - No loop consumidor da worker thread (linha 267), a thread do daemon executa `result = req.task_fn()`.
     - Em ambos os pontos do `RateGovernor`, a execução ocorre **sincronicamente sem `await` e sem um event loop associado à thread trabalhadora**. Invocar uma corrotina assíncrona dessa forma apenas instancia o objeto corrotina (`<coroutine object ...>`), sem nunca agendá-lo ou aguardá-lo.
     - O governor devolve o objeto corrotina cru; `GatingInterceptor` o devolve intacto; e `execute_tool` aguarda apenas a conclusão do interceptor, retornando o objeto corrotina cru para o chamador.
     - **Resultado:** A ferramenta **nunca é executada** (`Tool actually executed: False`), abortando silenciosamente e disparando `RuntimeWarning: coroutine was never awaited`.

  2. **Caminho COM Gating e SEM Governor:**
     - `execute_fn()` chama `dummy_fn()` diretamente.
     - Como `intercept_tool_call` retorna `execute_fn()` sem `await`, o objeto corrotina é retornado cru.
     - **Resultado:** A ferramenta **nunca é executada** (`Tool actually executed: False`).

  3. **Caminho SEM Gating e COM Governor:**
     - `self.gating` é nulo. O código atinge as linhas 260–262:
       ```python
       if inspect.iscoroutinefunction(dummy_fn):
           return await dummy_fn()
       return _run_with_governor()
       ```
     - O desenvolvedor tentou remediar a falta de `await` inserindo `if inspect.iscoroutinefunction(dummy_fn): return await dummy_fn()`.
     - Porém, ao fazer isso, **o fluxo salta diretamente por cima de `_run_with_governor()`**, contornando 100% o `RateGovernor` (`Governor requests recorded: 0`). Prioridade de tráfego, orçamentos de RPM/TPM e congelamento reativo de filas são totalmente ignorados.
     - Se `dummy_fn` for um callable assíncrono que não passe no teste estrito de `inspect.iscoroutinefunction` (ex.: decorador, closure ou objeto com `__call__` assíncrono), ela cai no `_run_with_governor()` e sofre exatamente o mesmo defeito do Caminho 1 (retorna corrotina crua não-executada).

  4. **Caminho SEM Gating e SEM Governor:**
     - A ferramenta executa diretamente via `await dummy_fn()`, sem nenhuma barreira de governança.

  **Conclusão Estrutural:** Não se trata de uma falha isolada de um branch ou de esquecimento pontual de um `await`: **não existe suporte arquitetural no pipeline de governança (`RateGovernor` + `GatingInterceptor`) para executar ferramentas assíncronas**. O `RateGovernor` foi concebido com modelo síncrono baseado em threads (`threading.Thread` + `queue.Queue`), enquanto o `CognitiveAgentRunner` é assíncrono (`async/await`), criando uma incompatibilidade de paradigmas que inviabiliza a execução correta sob qualquer combinação de flags.

---

### Achado #7: Dessincronização Estrutural entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX`
- **Severidade:** 🟡 **MÉDIA (CONDICIONAL / CÓDIGO ÓRFÃO)**
- **Arquivo:** [`agent/agent_prompts.py:82-132`](file:///c:/Nexus-Memory/GrafoConcierge/agent/agent_prompts.py#L82-L132) vs [`core/mcp_governor.py:43-76`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L43-L76)
- **Mecanismo:**
  `DynamicPromptBuilder.get_governance_block()` faz:
  `super_state, _ = self.parse_state_path(state_path)`
  `rules = matrix.get(super_state) or matrix.get("PLANNING", ...)`
  Ele consulta a matriz exclusivamente pela chave de `super_state` (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `STALL`, `SUCCESS`).
  Entretanto, a `TOOL_DISCLOSURE_MATRIX` em `core/mcp_governor.py` define categorias específicas para sub-estados como `DISCOVERY`, `TDD_GREEN` e `REFACTORING` no primeiro nível do dicionário.
  Como o caminho qualificado do HSM (ex.: `EXECUTION.TDD_GREEN`) sempre extrai `EXECUTION` como super-estado, as regras finas para `TDD_GREEN` e `REFACTORING` nunca são atingidas, tornando-se código morto no governor.

---

## 4. Saída Bruta da Reprodução Empírica

Execução do script de verificação [`scratch/reproduce_agent_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_agent_findings.py):

```text
======================================================================
TESTE 1: Contaminação de Turnos Multi-Sessão no Circuit Breaker
======================================================================
Sessão 1 executou 3 passos. current_substate_turn_count = 3
Sessão 2 foi inicializada. current_substate_turn_count = 0 (RESET INDEVIDO!)
Sessão 2 executou 4 passos. current_substate_turn_count = 4
Sessão 1 executou mais 1 passo. current_substate_turn_count = 5
[CIRCUIT-BREAKER] Circuit Breaker ativado no sub-estado PLANNING.DISCOVERY. Pausando em STALL.ERROR_PAUSE.
Sessão 1 resultado no 5º turno: status='stalled', state='STALL.ERROR_PAUSE'
-> [CONFIRMADO] Bloqueio indevido por contaminação entre sessões: True

======================================================================
TESTE 2: Dessincronização entre Prompt e Estado Ativo em step()
======================================================================
Retorno do step: active_state = 'EXECUTION.CODE_GEN'
Prompt contém '[ESTADO ATIVO: PLANNING.DISCOVERY]': True
Prompt contém '[ESTADO ATIVO: EXECUTION.CODE_GEN]': False
-> [CONFIRMADO] Prompt e estado ativo fora de sincronia: True

======================================================================
TESTE 3: Bypass na Barreira de Contaminação por Fallback Inseguro
======================================================================
Origem='restricted' (minúsculo) -> Destino='PUBLIC':
   is_safe = True (Deveria ser False!)
   reason  = OK — no contamination risk.
Origem='CONFIDENTIAL' -> Destino='PUBLIC':
   is_safe = True (Deveria ser False!)
   reason  = OK — no contamination risk.
-> [CONFIRMADO] Vazamento de dados confidenciais aprovado como seguro: True

======================================================================
TESTE 4: Falsa Aprovação de Commit Inválido quando generate_fn Falha
======================================================================
Commit inválido com generate_fn quebrando na tentativa 1:
   approved      = True (Deveria ser False!)
   partial_audit = True
   loop_count    = 3
   reason        = Approved by partial_audit after 3 rejections.
-> [CONFIRMADO] Commit inválido aprovado automaticamente após crash: True

======================================================================
TESTE 5: Falha em Rerank (NoneType crash e Type Mismatch)
======================================================================
5.1 Crash em _heuristic_rerank quando score_final=None: '>' not supported between instances of 'NoneType' and 'float'
5.2 LLM Rerank com candidato node_id='42' (str) e LLM avaliando 42 (int):
    Candidatos aprovados: []
    Candidato legítimo descartado por incompatibilidade de tipo: True
-> [CONFIRMADO] Defeitos em Reranking confirmados: True

======================================================================
TESTE 6: Incompatibilidade Estrutural com Corrotinas e Bypass do RateGovernor
======================================================================
6.1 Caminho COM Gating e COM Governor:
    Tipo do retorno: <class 'coroutine'>
    Retorno é objeto corrotina cru (não-awaited): True
    Ferramenta assíncrona foi executada: False
6.2 Caminho SEM Gating e COM Governor:
    Tipo do retorno: <class 'dict'>
    Ferramenta assíncrona foi executada: True
    Requisições registradas no RateGovernor: 0
    RateGovernor foi completamente ignorado/bypassed: True
-> [CONFIRMADO] Incompatibilidade universal com funções assíncronas: True

======================================================================
RESUMO DE REPRODUÇÃO (agent/ e agents/):
Achado 1 (Contaminação Turnos Circuit Breaker): REPRODUZIDO
Achado 2 (Dessincronização Prompt-Estado em step): REPRODUZIDO
Achado 3 (Bypass Barreira Contaminação): REPRODUZIDO
Achado 4 (Aprovação Espúria Commit Inválido): REPRODUZIDO
Achado 5 (Defeitos de Tipo e Crash em Reranking): REPRODUZIDO
Achado 6 (Incompatibilidade com Corrotinas e Bypass): REPRODUZIDO
======================================================================
```

---

## 5. Recomendações Estruturais para a Fase 3 (Backlog Consolidado)

1. **Decisão Arquitetural Mandatória — Consertar ou Remover:**
   - Como `CognitiveAgentRunner` e `RevisorCritico` estão 100% desconectados de `interface/mcp_server.py`, a equipe deve decidir se a visão de Harel Statecharts e Auditoria por LLM será de fato integrada à arquitetura central. Se a decisão for remover, estes três arquivos e seus testes associados devem ser apagados, eliminando 1.055 linhas de dívida técnica.
2. **Se a Decisão for Manter / Reconectar:**
   - **Isolar Turnos por Sessão:** Transformar `self.current_substate_turn_count` em `Dict[str, int]` (`session_substate_turns`), garantindo que o Circuit Breaker seja estritamente individual.
   - **Fail-Closed na Contaminação:** Em `check_contamination`, normalizar com `.upper()` e tratar qualquer valor não reconhecido como nível máximo (`RESTRICTED`), bloqueando qualquer tráfego duvidoso.
   - **Corrigir Ciclo de Retry de Commits:** Se `generate_fn` falhar com exceção, o commit deve permanecer reprovado (`approved=False`), sem concessão de `partial_audit=True`.
   - **Sincronizar Geração de Prompt com Novo Estado:** Em `step()`, efetuar a transição de estado *antes* de construir o prompt dinâmico.
   - **Coerência de Tipagem em Rerank:** Tratar `node_id` como `str` consistente ou tolerante (`str(nid)`) em `relevance_map`, e sanitizar `score_final` tratando `None` como `0.0`.
   - **Compatibilidade Assíncrona no Pipeline de Governança:** Se o pipeline de governança for mantido, `RateGovernor` deve suportar despacho assíncrono nativo (ex.: via `asyncio.Queue` / `run_coroutine_threadsafe`), e `GatingInterceptor.intercept_tool_call` deve avaliar `await execute_fn()` caso o retorno ou a função sejam corrotinas, garantindo que a execução ocorra dentro do event loop correto sob controle do governor sem bypass.
