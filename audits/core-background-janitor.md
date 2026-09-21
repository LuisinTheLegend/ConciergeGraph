# Auditoria — `core/background_janitor.py`

> **Item:** `core/background_janitor.py` (SDD-SURVIVAL-06 / SDD-SURVIVAL-12 / SDD-SURVIVAL-14: Background Community Summarizer, Smart Checkpoint Pruning, and Hardware-Aware Governor)  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-09-20  
> **Status:** Concluído, aguardando aprovação  

---

## 1. Ferramentas Estáticas Executadas

| Ferramenta | Comando | Resultado |
|------------|---------|-----------|
| **mypy** | `python -m mypy core/background_janitor.py --follow-imports=skip --ignore-missing-imports` | `Success: no issues found in 1 source file` |
| **unittest** | `python -m unittest tests/test_graph_rag_janitor.py tests/test_graph_rag_frugal.py tests/test_checkpoint_pruning.py` | 6 passed em 2.938s |

---

## 2. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `core/background_janitor.py` | 176–186 | **ALTA** | Falha de slice negativo em Python (`remaining[-keep_limit:]`) quando `keep_limit = 0`. Ao solicitar a retenção exclusiva do ponto-zero inicial (`keep_limit=0`), o slice `remaining[-0:]` é avaliado em Python como `remaining[0:]` (a lista inteira). Como resultado, `preserve_set` preserva 100% dos checkpoints da sessão e `ids_to_delete` fica vazio (`[]`), não apagando nenhum registro do banco. | Invocado `prune_session_checkpoints(keep_limit=0)` sobre sessão com 6 checkpoints: 0 deletados, todos os 6 permaneceram no banco. | **CONFIRMADO** |
| 2 | `core/background_janitor.py` | 270–284 | **ALTA** | Degradação irreversível da prioridade do processo inteiro do servidor (`p.nice(psutil.IDLE_PRIORITY_CLASS)` ou `nice(15)`). O método `process_community_summaries_frugal()` rebaixa a prioridade de todo o processo do Concierge (afetando o servidor MCP, API de telemetria, RateGovernor e threads de escrita) antes mesmo de checar a barreira térmica de hardware. Se a barreira falhar, a prioridade já foi rebaixada e nunca é restaurada. | Invocado `process_community_summaries_frugal()` com barreira térmica bloqueada: prioridade do processo caiu de 32 (NORMAL) para 64 (IDLE) e permaneceu degradada. | **CONFIRMADO** |
| 3 | `core/background_janitor.py` | 160–197 | **ALTA** | Destruição do ponto-zero em sessões multi-agente. A tabela relacional `agent_checkpoints` possui chave primária composta `(agent_id, session_id, checkpoint_id)`. Porém, a consulta `_prune_single_session` filtra apenas por `session_id`, ordenando todos os checkpoints cronologicamente e protegendo apenas `all_ids[0]`. O ponto-zero (`"init"`) de agentes subsequentes da mesma sessão é colocado em `remaining` e fisicamente deletado quando ultrapassa `keep_limit`. | Criada sessão com `agent_scout` e `agent_coder`: após 6 passos do scout, o ponto-zero `coder_init` foi deletado do banco relacional. | **CONFIRMADO** |
| 4 | `core/background_janitor.py` | 96–100 | **MÉDIA** | Crash com `TypeError` em `_summarize_community` quando `files.content` é `NULL`. Se algum arquivo da comunidade tiver conteúdo nulo no SQLite (arquivos binários, arquivos recém-descobertos sem corpo carregado, ou inicializados apenas com hashes), `payload = "\n".join(row[0] for row in files)` lança `TypeError: sequence item 0: expected str instance, NoneType found`, abortando toda a varredura de ociosidade. | Inserido arquivo com `content = NULL` em comunidade dirty: `run_idle_summarization()` explodiu com `TypeError`. | **CONFIRMADO** |
| 5 | `core/background_janitor.py` | 106–113 | **MÉDIA** | TOCTOU / Descarte cego de `is_dirty = 0` sobre arquivos modificados durante a geração da SLM. A chamada ao modelo local (`local_slm_callback`) leva de 5 a 30 segundos. Se um arquivo for alterado e marcado como `is_dirty = 1` enquanto a SLM gera o resumo, `UPDATE files SET is_dirty = 0 WHERE community_id = ?` reseta cegamente a flag, mascarando a nova edição sem que seu código tenha sido resumido. | Modificado arquivo concorrentemente durante o callback da SLM: flag `is_dirty` foi resetada para 0 ao término, perdendo o estado sujo. | **CONFIRMADO** |

---

## 3. Detalhamento de Cada Achado

### Achado #1 — Falha de Slice Negativo em Python (`keep_limit = 0`) Preserva 100% dos Checkpoints

- **Mecanismo da Falha:**  
  Em `core/background_janitor.py:176–186`:
  ```python
  # Protect initial checkpoint (immutable point zero)
  init_checkpoint = all_ids[0]
  remaining = all_ids[1:]

  # From remaining, preserve latest keep_limit
  if len(remaining) <= keep_limit:
      return 0

  # IDs to preserve: init + latest keep_limit
  recent_ids = remaining[-keep_limit:]
  preserve_set = {init_checkpoint} | set(recent_ids)

  # IDs to delete: all that are not in preserve set
  ids_to_delete = [cid for cid in all_ids if cid not in preserve_set]
  ```
  Na semântica de listas do Python, `-0 == 0`. Logo:
  `remaining[-0:]` é estritamente equivalente a `remaining[0:]` (isto é, a lista inteira).
  Quando `keep_limit = 0` é informado (operação padrão para podar todo o histórico recente e preservar estritamente o ponto-zero da sessão):
  1. `if len(remaining) <= 0:` é falso quando há mais de 1 checkpoint.
  2. `recent_ids = remaining[-0:]` seleciona **todos os checkpoints restantes**.
  3. `preserve_set` passa a conter o ponto zero somado a toda a lista de checkpoints.
  4. `ids_to_delete` torna-se `[]` (lista vazia).
  5. O método retorna `0` e nenhum checkpoint intermediário é deletado.
- **Impacto no Sistema:**  
  Tentativas de compactação agressiva para liberar espaço em disco ou arquivar sessões finalizadas (preservando unicamente o ponto-zero inicial para eventuais rollbacks) falham silenciosamente, mantendo a tabela `agent_checkpoints` com 100% dos dados.
- **Correção Conceitual Sugerida (Fase 3):**  
  Tratar explicitamente `keep_limit <= 0`:
  ```python
  recent_ids = remaining[-keep_limit:] if keep_limit > 0 else []
  ```

---

### Achado #2 — Degradação Irreversível da Prioridade do Processo Inteiro do Servidor

- **Mecanismo da Falha:**  
  Em `core/background_janitor.py:270–284`:
  ```python
  p = psutil.Process(os.getpid())
  if sys.platform == "win32":
      p.nice(psutil.IDLE_PRIORITY_CLASS)
  else:
      p.nice(15)

  # Execute hardware barrier
  if not self.check_hardware_clearance():
      return "skipped_due_to_hardware_constraints"
  ```
  1. `os.getpid()` altera a prioridade de agendamento do processo operacional do Concierge como um todo. Em uma arquitetura de processo único (onde o servidor MCP, os endpoints HTTP/REST da API de telemetria, o RateGovernor e as threads do banco operam sob o mesmo PID), rebaixar a prioridade para `IDLE_PRIORITY_CLASS` (no Windows) ou `nice(15)` (no Unix) afeta todas as threads do sistema.
  2. A alteração de prioridade ocorre **antes** de verificar se há folga de hardware (`check_hardware_clearance()`). Caso a barreira impeça o processamento (ex: CPU > 40% ou arquivo editado recentemente), o método retorna `"skipped_due_to_hardware_constraints"`, mas a prioridade do processo já foi degradada e **jamais é restaurada**.
  3. Não existe bloco `try ... finally` para restabelecer a prioridade original (`original_nice`). No Linux/Unix, um processo não-privilegiado sequer possui permissão (`CAP_SYS_NICE`) para voltar a um nível nice menor caso queira.
- **Impacto no Sistema:**  
  Uma única execução de rotina do Janitor condena todo o servidor Concierge a rodar com prioridade de fundo ociosa (IDLE) indefinidamente. Qualquer aplicação do sistema operacional (como navegadores, compiladores ou editores) monopoliza a CPU e faz com que requisições do MCP e telemetria sofram lentidão crítica.
- **Correção Conceitual Sugerida (Fase 3):**  
  1. Salvar `original_nice = p.nice()` e executar o rebaixamento de prioridade apenas dentro de um bloco protegido com `try ... finally` que restaure a prioridade original ao término.
  2. Executar a verificação de `check_hardware_clearance()` **antes** de alterar qualquer prioridade no sistema operacional.
  3. Alternativamente, isolar a invocação da SLM (Ollama) em subprocesso separado com prioridade própria sem contaminar o processo hospedeiro do Concierge.

---

### Achado #3 — Destruição do Ponto-Zero em Sessões Multi-Agente

- **Mecanismo da Falha:**  
  Conforme o esquema de arquitetura (SDD-SURVIVAL-12) e os testes em `test_checkpoint_pruning.py`, a chave primária de `agent_checkpoints` é composta:
  ```sql
  PRIMARY KEY (agent_id, session_id, checkpoint_id)
  ```
  Porém, `_prune_single_session()` faz a seleção agregando apenas por `session_id`:
  ```python
  all_checkpoints = self.db_manager.read_query(
      "SELECT checkpoint_id FROM agent_checkpoints "
      "WHERE session_id = ? "
      "ORDER BY created_at ASC;",
      (session_id,),
  )
  ```
  O método trata a lista inteira como uma única cadeia linear:
  - Protege apenas `all_ids[0]` (o primeiro checkpoint gravado na sessão).
  - Em uma sessão multi-agente (onde agentes como Scout, Architect e Coder operam juntos na mesma sessão), o checkpoint inicial do segundo agente (ex: `coder_init`) vai para a lista `remaining`.
  - Conforme o primeiro agente acumula novos passos que ultrapassam `keep_limit`, o ponto-zero do segundo agente é marcado como obsoleto e deletado do banco relacional por:
    ```sql
    DELETE FROM agent_checkpoints WHERE session_id = ? AND checkpoint_id IN (?);
    ```
- **Impacto no Sistema:**  
  Destruição física silenciosa do ponto de restauração inicial de agentes secundários em sessões compartilhadas. Quebra da garantia de hard reset e time-travel para agentes que não foram os primeiros a gravar na sessão.
- **Correção Conceitual Sugerida (Fase 3):**  
  Executar a auto-poda iterando separadamente sobre cada tupla `(agent_id, session_id)`:
  ```sql
  SELECT DISTINCT agent_id, session_id FROM agent_checkpoints;
  ```
  Garantindo que cada agente mantenha seu próprio ponto-zero inviolável e seus próprios $N$ passos mais recentes.

---

### Achado #4 — Crash com `TypeError` em `_summarize_community` quando `files.content` é `NULL`

- **Mecanismo da Falha:**  
  Em `core/background_janitor.py:96–100`:
  ```python
  files = self.db_manager.read_query(
      "SELECT content FROM files WHERE community_id = ?;",
      (community_id,),
  )
  payload = "\n".join(row[0] for row in files)
  ```
  Se a tabela `files` possuir qualquer registro com `content IS NULL` (como arquivos binários, arquivos ainda não sincronizados pelo body hash, ou inicializados apenas com metadados de path e hash), `row[0]` retorna `None`.
  A chamada `"\n".join(...)` lança imediatamente:
  `TypeError: sequence item 0: expected str instance, NoneType found`.
  Como `run_idle_summarization()` não encapsula a chamada em `try ... except`, a exceção propaga e aborta o processamento de todas as comunidades sujas daquele ciclo.
- **Impacto no Sistema:**  
  Falha catastrófica da rotina de summarização em segundo plano na presença de arquivos sem conteúdo populado, paralisando a atualização de resumos no GraphRAG.
- **Correção Conceitual Sugerida (Fase 3):**  
  Filtrar nulos ou usar fallback de string vazia / cláusula SQL:
  ```python
  payload = "\n".join(row[0] or "" for row in files if row[0] is not None)
  ```
  E adicionar bloco `try ... except Exception` individual por comunidade em `run_idle_summarization`.

---

### Achado #5 — Descarte Cego de `is_dirty = 0` (TOCTOU) sobre Arquivos Modificados Durante a SLM

- **Mecanismo da Falha:**  
  Em `core/background_janitor.py:96–113`:
  ```python
  files = self.db_manager.read_query(
      "SELECT content FROM files WHERE community_id = ?;",
      (community_id,),
  )
  payload = "\n".join(...)
  new_summary = local_slm_callback(payload)

  self.db_manager.write_query(
      "UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;",
      (new_summary, community_id),
  )
  self.db_manager.write_query(
      "UPDATE files SET is_dirty = 0 WHERE community_id = ?;",
      (community_id,),
  )
  ```
  A execução de `local_slm_callback` é síncrona e demorada (inferência em modelo local). Se durante esse intervalo de tempo algum arquivo da comunidade for editado por um agente ou usuário, o subsistema de ingestão marca o arquivo com `is_dirty = 1`.
  Ao concluir a geração, `_summarize_community` emite `UPDATE files SET is_dirty = 0 WHERE community_id = ?` incondicionalmente para toda a comunidade.
- **Impacto no Sistema:**  
  A nova edição é marcada falsamente como limpa (`is_dirty = 0`), porém o seu conteúdo novo não estava presente no `payload` enviado à SLM. A comunidade permanece com um resumo defasado e nunca mais será marcada como suja até que uma edição subsequente ocorra.
- **Correção Conceitual Sugerida (Fase 3):**  
  Resetar `is_dirty = 0` apenas para os arquivos e timestamps que foram efetivamente lidos no início do ciclo, ou verificar se o arquivo não sofreu novas modificações antes de limpar a flag:
  ```sql
  UPDATE files SET is_dirty = 0 WHERE path IN (...) AND last_modified <= ?;
  ```

---

## 4. Saída Bruta da Reprodução Executada

Script executado: `scratch/reproduce_janitor_findings.py`

```text
======================================================================
EXECUCAO DAS PROVAS DE REPRODUCAO — core/background_janitor.py
======================================================================

--- TESTE ACHADO 1: keep_limit=0 preserva 100% dos checkpoints (Bug de slice [-0:]) ---
Checkpoints restantes no banco com keep_limit=0: ['init', 'step_1', 'step_2', 'step_3', 'step_4', 'step_5']
Total deletado retornado por prune_session_checkpoints: 0
[CONFIRMADO ACHADO 1]: keep_limit=0 avaliou remaining[-0:], resultando em remaining[:] (fatia inteira). 0 checkpoints foram deletados!

--- TESTE ACHADO 2: Degradação Irreversível de Prioridade do Processo ---
Prioridade original do processo (10516): 32
Resultado de process_community_summaries_frugal(): skipped_due_to_hardware_constraints
Nova prioridade do processo apos a chamada: 64
[CONFIRMADO ACHADO 2]: O processo inteiro foi rebaixado para IDLE_PRIORITY_CLASS (64) e NUNCA restaurado!

--- TESTE ACHADO 3: Destruição do Ponto-Zero de Múltiplos Agentes na Mesma Sessão ---
Checkpoints restantes para sessao 'collab_sess': [('agent_scout', 'scout_init'), ('agent_scout', 'scout_step_4'), ('agent_scout', 'scout_step_5'), ('agent_scout', 'scout_step_6')]
Checkpoints do agent_coder restantes: []
[CONFIRMADO ACHADO 3]: 'coder_init' (ponto zero do agent_coder) foi DELETADO porque o algoritmo so protegeu o ponto zero do primeiro agente!

--- TESTE ACHADO 4: Crash em _summarize_community quando content é NULL ---
Exceção capturada com sucesso: TypeError: sequence item 0: expected str instance, NoneType found
[CONFIRMADO ACHADO 4]: _summarize_community lanca TypeError ao tentar join de NoneType!

--- TESTE ACHADO 5: TOCTOU / Descarte Cego de is_dirty em arquivos concorrentes ---
Estado de file1.py apos summarizacao: content='code v2 NOVO', is_dirty=0
[CONFIRMADO ACHADO 5]: is_dirty foi resetado para 0, mascarando a edicao 'code v2 NOVO' feita durante a geracao!

======================================================================
RESULTADO: F1=True, F2=True, F3=True, F4=True, F5=True
======================================================================
```

---

## 5. Arquivos de Teste Relacionados

- [`tests/test_graph_rag_janitor.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_janitor.py):
  - Testa extração de comunidade natural, resolução multi-hop via CTE recursivo e execução básica de `run_idle_summarization` com mock síncrono.
  - Não cobre `content` nulo, concorrência durante summarização, nem erro no callback.
  - Resultado: 3 passed.
- [`tests/test_graph_rag_frugal.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_frugal.py):
  - Testa detecção com teto de in-degree (supernó) e barreira de `check_hardware_clearance()`.
  - Não cobre os efeitos colaterais de `p.nice()` em `process_community_summaries_frugal()`.
  - Resultado: 2 passed.
- [`tests/test_checkpoint_pruning.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_checkpoint_pruning.py):
  - Testa a auto-poda em um único agente isolado com `keep_limit=5`.
  - Não testa `keep_limit=0`, sessões multi-agente, nem empates em `created_at`.
  - Resultado: 1 passed.
