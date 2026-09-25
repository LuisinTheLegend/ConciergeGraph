# Walkthrough — Sessão de Auditoria `core/delta_manager.py`

> **Data:** 2026-09-18 → 2026-09-19  
> **Item auditado:** `core/delta_manager.py` (Fase 1 do AUDIT_PROTOCOL.md)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar

---

## 1. Execução da auditoria

### Leitura do protocolo
- Lido [`AUDIT_PROTOCOL.md`](file:///c:/projetos/GrafoConcierge/AUDIT_PROTOCOL.md) na íntegra
- Identificado o item **▶ EM ANDAMENTO:** `core/delta_manager.py`
- Regras Globais internalizadas (escopo estrito, reprodução obrigatória, gate obrigatório, somente-leitura)

### Ferramentas estáticas (Regra 5)
- `ruff`, `mypy`, `bandit` — **não instalados** no ambiente (registrado no relatório)
- `pytest` — executado nos testes existentes:
  - [`tests/test_delta_sync.py`](file:///c:/projetos/GrafoConcierge/tests/test_delta_sync.py) — 4 passed
  - [`tests/test_delta_sync_drift.py`](file:///c:/projetos/GrafoConcierge/tests/test_delta_sync_drift.py) — 3 passed

### Análise de código
Arquivos lidos na íntegra:
- [`core/delta_manager.py`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py) (266 linhas)
- [`core/database.py`](file:///c:/projetos/GrafoConcierge/core/database.py) (74 linhas)
- [`core/hsm_engine.py`](file:///c:/projetos/GrafoConcierge/core/hsm_engine.py) — método `resume_from_history_node` (linhas 385–494)
- [`core/delta_manager.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py) (266 linhas)
- [`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py) (74 linhas)
- [`core/hsm_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py) — método `resume_from_history_node` (linhas 385–494)
- [`core/delta_sync.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_sync.py) (re-export wrapper)
- [`tests/test_hsm_transition_hooks_and_delta.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py) — `MockDeltaManager` (linhas 25–41)
- [`tests/test_delta_sync.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_delta_sync.py) (233 linhas)
- [`tests/test_delta_sync_drift.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_delta_sync_drift.py) (87 linhas)

### Reprodução
Script de reprodução escrito e executado — **6/6 achados confirmados** com saída bruta do terminal colada no relatório.

---

## 2. Achados (5 reais + 1 falso positivo resolvido)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`hsm_engine.py:458`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L458) chama `delta_manager.has_structural_change()` — método **inexistente** no DeltaManager. `AttributeError` em runtime. Mascarado por `MockDeltaManager` nos testes. |
| 2 | **FALSO POSITIVO** (anteriormente MÉDIA) | [`delta_manager.py:81`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L81) — `_stripper` é atributo de classe compartilhado. Reavaliado: `DocstringStripper` é 100% stateless (`__dict__ == {}`) e a AST é gerada em escopo thread-local via `ast.parse`. Teste de estresse com 50 threads e 10.000 chamadas simultâneas provou 0 erros. Compartilhamento seguro (flyweight). |
| 3 | **MÉDIA** | [`delta_manager.py:204-265`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L204-L265) — Operações multi-write sem transação atômica. Crash entre writes = estado inconsistente. |
| 4 | **BAIXA** | [`delta_manager.py:186`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L186) — `TypeError` se `files.content` for `NULL` no banco. |
| 5 | **OBSERVAÇÃO** | [`delta_manager.py:83-97`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L83-L97) — SSH context-free (captura `def`/`class` em qualquer nível de indentação). Conservadoramente correto. |
| 6 | **ALTA** | [`delta_manager.py:99-116`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L99-L116) — Change detection parcialmente cego para non-Python. LBH universalmente cego; SSH incidentalmente funcional (0–43% dependendo da linguagem). |

---

## 3. Rodadas de revisão com o humano

### Rodada 1 — Achado #6 impreciso
**Feedback do humano:** `calculate_ssh()` não retorna sempre vazio para non-Python — só quando o arquivo não tem linhas começando com `def `/`class `/`import `/`from `.

**Ação:** Reformulado o texto em `audits/core-delta-manager.md`, `AUDIT_PROTOCOL.md` e `walkthrough.md`.

### Rodada 2 — Go classificado incorretamente
**Feedback do humano:** Go não é totalmente cego — `import "fmt"` bate no prefixo `import `. Generalizar corretamente: SSH funciona de forma incidental para qualquer linguagem que use literalmente essas palavras-prefixo.

**Ação:** Corrigido nos três arquivos.

### Rodada 3 — Eliminar prosa, usar teste verificável
**Feedback do humano:** Em vez de ficar corrigindo frase por frase, criar um teste parametrizado que documente exatamente quais linhas cada linguagem tem capturadas. Colar a saída real do pytest no relatório. Isso fecha a questão de forma permanente.

**Ação:** Criado [`tests/test_ssh_language_coverage.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_ssh_language_coverage.py) com:
- 9 linguagens testadas (Python, TypeScript, JavaScript ESM, JavaScript CJS, Go, Rust, Java, C++, C)
- 1 teste parametrizado por linguagem + 1 teste de tabela resumo
- **10 passed** no primeiro run após fix do TypeScript (`export class` ≠ `class`)

Tabela gerada pelo teste (colada no relatório):

| Language | SSH captured | SSH missed | Coverage | LBH |
|----------|-------------|------------|----------|-----|
| Python | 5 lines | 0 lines | 5/5 (100%) | ✓ full |
| TypeScript | 2 lines | 7 lines | 2/9 (22%) | ✗ blind |
| JavaScript_ESM | 3 lines | 4 lines | 3/7 (43%) | ✗ blind |
| JavaScript_CJS | 1 lines | 4 lines | 1/5 (20%) | ✗ blind |
| Go | 2 lines | 5 lines | 2/7 (29%) | ✗ blind |
| Rust | 0 lines | 7 lines | 0/7 (0%) | ✗ blind |
| Java | 2 lines | 5 lines | 2/7 (29%) | ✗ blind |
| Cpp | 1 lines | 7 lines | 1/8 (12%) | ✗ blind |
| C | 0 lines | 7 lines | 0/7 (0%) | ✗ blind |

### Rodada 4 — Limpeza do teste e resolução do Achado #2 (thread-safety)
**Feedback do humano:** Limpar código morto/narrativo no `test_ssh_language_coverage.py`, trocar prefixos hardcoded por `from core.delta_manager import _STRUCTURAL_PREFIXES`, e resolver o Achado #2 (thread-safety) — que continha apenas prova de compartilhamento de objeto e nenhuma reprodução de corrupção real.

**Ações executadas:**
1. **Limpeza e refatoração de `tests/test_ssh_language_coverage.py`**:
   - Trocado `prefixes = ("def ", "class ", "import ", "from ")` pela importação canônica `from core.delta_manager import _STRUCTURAL_PREFIXES`.
   - Removido o bloco morto/narrativo de ajuste manual pós-declaração de Java (linhas 446–482).
   - Java consolidado diretamente no dicionário `LANGUAGE_CASES`.
   - Testes executados: **10 passed em 0.09s**.
2. **Resolução técnica do Achado #2 (thread-safety)**:
   - Investigado o mecanismo interno de `DeltaManager.calculate_lbh()` e `DocstringStripper`:
     * `DocstringStripper` herda de `ast.NodeTransformer` e é **completamente stateless** (`self.__dict__ == {}` antes e depois do `visit()`).
     * A AST mutada por `visit()` é instanciada via `tree = ast.parse(file_content)` diretamente dentro de `calculate_lbh()`, pertencendo exclusivamente ao stack frame da thread chamadora.
     * Nenhuma AST é compartilhada entre threads ou instâncias de `DeltaManager`.
     * Executado teste de estresse concorrente com **50 threads simultâneas e 10.000 chamadas**: **0 divergências de hash e 0 exceções**.
      * Adicionado teste automatizado de regressão `test_calculate_lbh_thread_safety_concurrency` em [`tests/test_delta_sync_drift.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_delta_sync_drift.py).

## 4. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) | Relatório | Tabela de achados atualizada (Achado #2 reclassificado para Falso Positivo), saída de concorrência |
| [`tests/test_ssh_language_coverage.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_ssh_language_coverage.py) | Teste | Limpo de código morto/narrativo; usa `_STRUCTURAL_PREFIXES` |
| [`tests/test_delta_sync_drift.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_delta_sync_drift.py) | Teste | Adicionado teste concorrente provando thread-safety de `calculate_lbh()` |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | Resumo atualizado com 5 achados reais + 1 falso positivo resolvido |

---

## 5. Arquivos não modificados

Nenhum arquivo de código de produção foi editado (Regra 8 — Fases 1 e 2 são somente-leitura).

---

# Sessão de Auditoria — `mock-vs-real-audit`

> **Data:** 2026-09-19  
> **Item auditado:** `mock-vs-real-audit` (Tarefa transversal de Mocks da Fase 1)  
> **Commit:** `00d9c4e` (`docs(audit): mock-vs-real-audit concluído`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `core/security_guard.py`  

---

## 1. Execução da auditoria
- Inspecionadas todas as **18 classes de Mock / Test Double** em `tests/`.
- Mapeada cada classe de mock à sua correspondente classe real de produção em `core/`, `storage/`, `services/`, `ingestion/`.
- Executado script comparador de assinaturas e extração de métodos (`ast` + inspeção dinâmica).
- Reproduzidos em terminal os erros em runtime causados pelas discrepâncias encontradas.

## 2. Achados de Mock vs Real (7 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`test_vector_reconciler.py:83`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L83) — `MockVectorDatabase` define `get_all_ids()`, ausente em `ChromaVectorStore` e `BaseVectorBackend` (método canônico é `get_all_stored_node_ids()`). `core/vector_reconciler.py:39` chama `get_all_ids()` e falha com `AttributeError` em produção. Padrão idêntico ao Achado #1 de `delta_manager.py`. |
| 2 | **CRÍTICA** | [`test_hsm_transition_hooks_and_delta.py:32`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py#L32) — `MockDeltaManager` define `has_structural_change()`, ausente em `DeltaManager`. `core/hsm_engine.py:458` sofre `AttributeError` em runtime. |
| 3 | **ALTA (AMBÍGUO)** | [`test_cognitive_routing_memory.py:30`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_cognitive_routing_memory.py#L30) — `MockExternalMCP` define `query_docs()`, chamado por `core/federated_knowledge_router.py:73`. Nenhuma classe real existe no repositório inteiro com esse método (contrato fantasma). |
| 4 | **FALSO POSITIVO (OBSERVAÇÃO)** | [`test_mcp_server_handlers.py:116`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L116) — `MockJanitor` define 4 métodos (`signal_mine_start/end`, `is_running`, `last_reports`) que coincidem com `services/janitor.py` (`JanitorService`), a classe real injetada em `interface/mcp_server.py:135`. Sem falha em runtime (falso positivo de defeito). Permanece a observação arquitetural de duplicidade de nomenclatura com `core/background_janitor.py` (`BackgroundJanitor`). |
| 5 | **MÉDIA** | [`test_vector_reconciler.py:73`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L73) — `MockVectorDatabase` define `insert(vector_id, payload)` que não existe na interface canônica `BaseVectorBackend` (`store_embedding`). |
| 6 | **MÉDIA** | [`test_cognitive_routing_memory.py:24`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_cognitive_routing_memory.py#L24) — `MockGraphRAGEngine` define `retrieve_multihop_context(query) -> str`, enquanto `GraphRAGEngine` real espera `(entry_node: str, max_depth: int) -> Dict[str, Any]`. |
| 7 | **BAIXA** | [`test_interface_contracts.py:62`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L62) — `_MockVectorStore.reset_collection()` existe apenas na implementação concreta `ChromaVectorStore`, fora da interface abstrata `BaseVectorBackend`. |

> **Validação Adicional de Test Doubles Especiais:**
> - `FailingIngestion` ([`tests/test_mcp_server_handlers.py:209`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_mcp_server_handlers.py#L209)) vs [`IngestionManager`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L94): **0 métodos ausentes no real** (`mine` e `generate_project_context` presentes). Conforme.
> - `InMemoryConnManager` ([`tests/test_storage_logic.py:42`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_storage_logic.py#L42)) vs [`ConnectionManager`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L196): **0 métodos ausentes no real** (`read`, `write`, `close` presentes). Conforme.

## 3. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/mock-vs-real-audit.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/mock-vs-real-audit.md) | Relatório | Mapeamento completo dos 18 mocks, tabela oficial de achados e saída bruta de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `mock-vs-real-audit` marcado `[x]` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

# Sessão de Auditoria — `core/security_guard.py`

> **Data:** 2026-09-20  
> **Item auditado:** `core/security_guard.py` (SDD-SURVIVAL-24: Boundary Guard & Hazard Classifier)  
> **Commit:** `d32f244` (`docs(audit): core/security_guard.py concluído`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `core/rate_governor.py`  

---

## 1. Execução da auditoria
- Inspecionado [`core/security_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py) na íntegra (102 linhas).
- Verificada integração com [`core/gating_interceptor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/gating_interceptor.py) e [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py).
- Ferramentas estáticas:
  - `mypy core/security_guard.py --follow-imports=skip` -> `Success: no issues found in 1 source file`.
  - `unittest tests/test_adaptive_gating.py` -> 12 passed em 0.023s.
  - `unittest tests/test_agent_hsm_coupling.py` -> 13 passed em 0.759s.
- Desenvolvido script de reprodução abrangente cobrindo 5 achados confirmados com saída bruta em terminal.

---

## 2. Achados de `core/security_guard.py` (5 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`core/security_guard.py:42-45, 94-95`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L42-L45) — Regex `\brm\s+-rf\s+/` é facilmente contornada por `rm -fr /`, `rm -r -f /`, `rm --recursive --force /`, deleção do diretório corrente (`rm -rf .`, `rm -rf *`), comandos de deleção do Windows (`del /f /s /q C:\*`, `format C:`). Em modo `auto-approve`, qualquer comando não-CRITICAL roda sem aprovação humana. |
| 2 | **ALTA** | [`core/security_guard.py:94`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L94) — `classify_command(None)` lança `TypeError: expected string or bytes-like object, got 'NoneType'` não tratado. |
| 3 | **MÉDIA** | [`core/security_guard.py:75-77`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L75-L77) — Concatenação `self.project_root + os.sep` gera barra dupla (`C:\\\\` ou `//`) se `project_root` for raiz de disco ou partição, fazendo `is_safe_path` retornar `False` para 100% dos arquivos do projeto. |
| 4 | **MÉDIA** | [`core/security_guard.py:72-77`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L72-L77) — Resolução de caminhos relativos em `is_safe_path` ancorada a `os.getcwd()` em vez de `self.project_root`. Falsos bloqueios para projetos externos registrados fora do CWD do servidor. |
| 5 | **BAIXA** | [`core/security_guard.py:48-54, 98-99`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L48-L54) — Substring match ingênuo em `warning_terms` contendo `"build"` gera falsos positivos de WARNING para comandos inofensivos (`git log --grep="build"`, `cat build.py`, `git checkout build-fix`, `ls -la build/`). |

---

## 3. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-security-guard.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-security-guard.md) | Relatório | Relatório oficial completo com análise técnica detalhada e saída de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/security_guard.py` marcado `[x]` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

# Sessão de Auditoria — `core/rate_governor.py`

> **Data:** 2026-09-20  
> **Item auditado:** `core/rate_governor.py` (SDD-SURVIVAL-23: RateGovernor with Priority Traffic & Queue Freezing)  
> **Commit:** `3256e37` (`docs(audit): refinar Achado #2 do rate_governor (starvation na faixa de 75% a 100%)`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `core/background_janitor.py`  

---

## 1. Execução da auditoria
- Inspecionado [`core/rate_governor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py) na íntegra (281 linhas).
- Verificada integração com [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py) e [`tests/test_rate_governor_priority.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_rate_governor_priority.py).
- Ferramentas estáticas:
  - `mypy core/rate_governor.py --follow-imports=skip` -> `Success: no issues found in 1 source file`.
  - `unittest tests/test_rate_governor_priority.py` -> 8 passed em 1.679s.
  - `unittest tests/test_agent_hsm_coupling.py` -> 13 passed em 0.759s.
- Desenvolvido script de reprodução cobrindo 5 achados confirmados com saída bruta em terminal.

---

## 2. Achados de `core/rate_governor.py` (5 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`core/rate_governor.py:250, 255, 261, 272`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L250) — Vazamento cumulativo de `unfinished_tasks` na `PriorityQueue` e starvation de cabeça de fila (Head-of-Line). Re-enfileiramento com `put(req)` sem `task_done()` vaza tarefas fantasmas (+1 a cada 0.5s); `request_queue.join()` trava para sempre em Deadlock. |
| 2 | **ALTA** | [`core/rate_governor.py:231-252`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L231-L252) — Starvation de tarefas LOW envelhecidas em toda a faixa de 75% a 100% de carga. O branch de envelhecimento (aging) só promove com `max_pct < 75.0`. Como a fila LOW só congela oficialmente com `>= 85.0`, qualquer tarefa LOW envelhecida fica impedida de executar em toda a faixa de 75% a 100% (mesmo entre 75% e 84.9%, onde a fila nem sequer está congelada), sofrendo inanição contínua até que a carga caia abaixo de 75%. |
| 3 | **ALTA** | [`core/rate_governor.py:91, 116-150`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L91) — Data Race / Lost Updates em `get_current_metrics()`. Método limpa e reatribui `self.history = [...]` sem deter `self.lock`. Chamadas concorrentes da API de telemetria disputam com `report_usage()`, provocando sobrescrita e perda de registros recentes. |
| 4 | **ALTA** | [`core/rate_governor.py:196-203, 278-280`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L196-L203) — Deadlock permanente em `submit_request` se o governor não estiver rodando ou após `shutdown()`. `submit_request` bloqueia em `future_result.get()` sem timeout, e `shutdown()` finaliza a thread sem drenar a fila nem responder aos futures pendentes. |
| 5 | **MÉDIA** | [`core/rate_governor.py:185-194`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L185-L194) — Cegueira de RPM no Fast-Path. Requisições prioritárias sob tráfego verde (< 50%) executam inline sem registrar o timestamp em `self.history`, mantendo `current_rpm` em 0 e mascarando rajadas de chamadas rápidas. |

---

## 3. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-rate-governor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-rate-governor.md) | Relatório | Relatório oficial completo com análise técnica detalhada e saída de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/rate_governor.py` marcado `[x]`, próximo: `▶ core/background_janitor.py` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

# Sessão de Auditoria — `core/background_janitor.py`

> **Data:** 2026-09-20  
> **Item auditado:** `core/background_janitor.py` (SDD-SURVIVAL-06 / SDD-SURVIVAL-12 / SDD-SURVIVAL-14: Background Community Summarizer, Smart Checkpoint Pruning, and Hardware-Aware Governor)  
> **Commit:** `8d8b95d` (`docs(audit): adicionar variante de delecao cruzada de checkpoints ao Achado #3 do background_janitor`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `core/vector_reconciler.py`  

---

## 1. Execução da auditoria
- Inspecionado [`core/background_janitor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py) na íntegra (291 linhas).
- Verificada integração com [`core/graph_rag.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py), [`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py) e [`interface/queue_writer.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py).
- Ferramentas estáticas:
  - `mypy core/background_janitor.py --follow-imports=skip --ignore-missing-imports` -> `Success: no issues found in 1 source file`.
  - `unittest tests/test_graph_rag_janitor.py tests/test_graph_rag_frugal.py tests/test_checkpoint_pruning.py` -> 6 passed em 2.938s.
- Desenvolvido script de reprodução cobrindo 5 achados confirmados com saída bruta em terminal.

---

## 2. Achados de `core/background_janitor.py` (5 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **ALTA** | [`core/background_janitor.py:176–186`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L176) — Falha de slice negativo em Python (`remaining[-keep_limit:]`) quando `keep_limit = 0`. `-0 == 0`, logo `remaining[-0:]` avalia para a lista inteira. `preserve_set` protege 100% dos checkpoints da sessão, e 0 registros são deletados. |
| 2 | **ALTA** | [`core/background_janitor.py:270–284`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L270) — Degradação irreversível da prioridade do processo inteiro do servidor (`p.nice(psutil.IDLE_PRIORITY_CLASS)`). Rebaixa todo o processo do Concierge antes mesmo da checagem da barreira térmica e jamais restaura a prioridade original. |
| 3 | **ALTA** | [`core/background_janitor.py:160–197`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L160) — Destruição de ponto-zero e deleção cruzada de checkpoints entre agentes na mesma sessão. Como `agent_save_checkpoint` recebe `checkpoint_id` livre sem namespace, e o `DELETE` filtra apenas por `session_id` e `checkpoint_id IN (...)` sem `agent_id`, checkpoints homônimos (ex: `step_1`, `plan`) de outros agentes são deletados indevidamente como dano colateral. |
| 4 | **MÉDIA** | [`core/background_janitor.py:96–100`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L96) — Crash com `TypeError: sequence item 0: expected str instance, NoneType found` em `_summarize_community` quando `files.content` é `NULL`, abortando toda a varredura de ociosidade. |
| 5 | **MÉDIA** | [`core/background_janitor.py:106–113`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L106) — TOCTOU / Descarte cego de `is_dirty = 0` sobre arquivos modificados durante a geração de resumos pela SLM (5 a 30s), mascarando permanentemente alterações de código recentes. |

---

## 3. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) | Relatório | Relatório oficial completo com análise técnica detalhada e saída de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/background_janitor.py` marcado `[x]`, próximo: `▶ core/vector_reconciler.py` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

## 4. Estado atual da auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 11/17 itens concluídos (6 pré-existentes + delta_manager + mock-vs-real-audit + security_guard + rate_governor + background_janitor)
         ▶ Concluído: core/vector_reconciler.py
         ▶ Próximo: core/checkpointer.py
Fase 2: bloqueada (requer Fase 1 completa)
Fase 3: bloqueada (requer Fase 2 completa)
```

---

# Sessão de Auditoria — `core/vector_reconciler.py`

> **Data:** 2026-09-20  
> **Item auditado:** `core/vector_reconciler.py` (SDD-SURVIVAL-05: Eventual Consistency Janitor & Background Vector Reconciler)  
> **Commit:** `18675ba` (`docs(audit): refinar achados 3 e 4 do vector_reconciler com node_id 106 e nota de threshold arbitrario`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `core/checkpointer.py`  

---

## 1. Execução da auditoria
- Inspecionado [`core/vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py) na íntegra (57 linhas).
- Verificado alinhamento com interfaces e backends reais: [`storage/base_backend.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py), [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) (`ChromaVectorStore`), [`core/vector_backend.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_backend.py) (`QdrantVectorStore`), e [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py).
- Ferramentas estáticas:
  - `mypy core/vector_reconciler.py --follow-imports=skip` -> `Success: no issues found in 1 source file`.
  - `unittest tests/test_vector_reconciler.py` -> 2 passed em 0.046s (passou apenas pelo uso do mock permissivo `MockVectorDatabase`).
- Desenvolvido script de reprodução abrangente cobrindo 4 achados confirmados com saída bruta em terminal.

---

## 2. Achados de `core/vector_reconciler.py` (4 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`core/vector_reconciler.py:39`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py#L39) — Invocação de método fantasma `self.vector_db.get_all_ids()`. Conforme já identificado no Achado #1 de [`audits/mock-vs-real-audit.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/mock-vs-real-audit.md#L72), o método `get_all_ids()` não existe em `BaseVectorBackend`, `ChromaVectorStore` (canônico: `get_all_stored_node_ids()`) nem em `QdrantVectorStore`. Quebra em runtime com `AttributeError`. |
| 2 | **CRÍTICA** | [`core/vector_reconciler.py:40–49, 54`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py#L40-L49) — Incompatibilidade de TIPO (`int` vs `str`) e Domínio Semântico -> Purga Total Garantida de Vetores (Catastrophic Data Loss). `get_all_stored_node_ids()` retorna `set[int]`, enquanto `_get_all_sqlite_paths()` retorna caminhos de arquivos `set[str]`. Como `int != str`, a interseção é estritamente vazia (`set()`), e `vector_ids - sqlite_paths` avalia para 100% dos vetores legítimos, deletando toda a base vetorial. **Dependência Crítica:** corrigir #1 isoladamente faz o sistema passar de 'seguro por estar quebrado' para 'roda e apaga tudo'. Devem ser corrigidos estritamente no mesmo commit / mini-plano. |
| 3 | **ALTA** | [`core/vector_reconciler.py:31–50`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py#L31-L50) — Ausência de sincronização atômica e race condition destrutiva com ingestão concorrente (TOCTOU). Válido mesmo após a correção de #1 e #2: testado com `node_id = 106` (int) e tabela `nodes`. Como a ingestão grava vetores no Step 6 e comita no SQLite no Step 7/8, uma reconciliação no meio do caminho apaga o vetor legítimo recém-gerado, deixando o SQLite com o nó mas sem vetor. |
| 4 | **MÉDIA** | [`core/vector_reconciler.py:48–50`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py#L48-L50) — Falta de paginação em lote e ausência de tratamento de exceções em `delete_batch`. Lista inteira de órfãos é enviada de uma só vez (ex: lote único de 500 itens). O limite de 250 itens no teste foi uma fixture didática arbitrária; no código real, `ChromaVectorStore` adota `BATCH_SIZE = 100`, enquanto o reconciliador não pagina nem trata exceções. |

---

## 3. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-vector-reconciler.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-vector-reconciler.md) | Relatório | Relatório oficial completo com inventário de chamadas, análise técnica detalhada e saída de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/vector_reconciler.py` marcado `[x]`, próximo: `▶ core/checkpointer.py` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

## 4. Estado atual da auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 12/17 itens concluídos (6 pré-existentes + delta_manager + mock-vs-real-audit + security_guard + rate_governor + background_janitor + vector_reconciler)
         ▶ Concluído: core/vector_reconciler.py
         ▶ Próximo: core/checkpointer.py
Fase 2: bloqueada (requer Fase 1 completa)
Fase 3: bloqueada (requer Fase 2 completa)
```

---

# Sessão de Auditoria — `core/checkpointer.py`

> **Data:** 2026-09-21  
> **Item auditado:** `core/checkpointer.py` (SDD-SURVIVAL-07: Agnostic Agent State Checkpointer & SDD-SURVIVAL-20: Durable FSM Checkpoints & Time-Travel)  
> **Commit:** `af19f98` (`docs(audit): core/checkpointer.py concluido`)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar para `storage/`  

---

## 1. Execução da auditoria
- Inspecionado [`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py) na íntegra (256 linhas).
- Verificadas integrações e chamadores reais: [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py) (`agent_save_checkpoint`, `agent_get_checkpoint`, `agent_list_checkpoints`), [`core/hsm_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py), [`core/background_janitor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py) e [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py).
- Ferramentas estáticas:
  - `mypy core/checkpointer.py --follow-imports=skip` -> ❌ **4 erros encontrados** (chamada de `None` e tuplas incompatíveis em queries).
  - `unittest tests/test_agent_checkpointer.py tests/test_durable_checkpoints_timetravel.py` -> 7 passed em 2.633s (passou por viés de fixtures que evitaram o cenário ambíguo real).
- Desenvolvido script de reprodução abrangente cobrindo 4 testes empíricos com saída bruta em terminal.

---

## 2. Achados de `core/checkpointer.py` (5 achados confirmados)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`core/checkpointer.py:73–78, 80–117`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L73) — Despacho ambíguo em `save_checkpoint` baseado em heurística de tipos (`len(args) == 4 and isinstance(args[3], str)`). Na chamada real em [`interface/mcp_server.py:1741`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1741), são passados 4 argumentos posicionais. Se `state_dict` for string JSON ou mensagem textual, o método despacha erroneamente para `fsm_checkpoints` em vez de `agent_checkpoints`, inverte colunas primárias (`session_id` recebe `agent_id`, `checkpoint_id` recebe `session_id`, `agent_id` recebe `checkpoint_id`) e **descarta o estado** gravando `shared_state_blob = "{}"`. |
| 2 | **ALTA** | [`core/checkpointer.py:195–210`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L195) — Falha de atomicidade e mascaramento silencioso de erros em `execute_time_travel`. O loop ignora o retorno de `write_fn` (`execute_write`), que retorna tupla `(False, error)` e não propaga exceções. Se o rollback falhar no banco, `execute_time_travel` retorna `target_data`, reportando falso sucesso de Time-Travel. *Adendo pós-descoberta de duplicacao-serialized-write-queue:* o módulo opera com `ConciergeDatabaseManager` sem `write_queue`, executando conexões efêmeras cruas sem fila e sem `foreign_keys=ON;`, expondo ainda mais as não-atomicidades a corrupção concorrente. |
| 3 | **ALTA** | [`core/checkpointer.py:196`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L196) — Granularidade temporal insuficiente (1s de `CURRENT_TIMESTAMP`) em `execute_time_travel`. Em rajadas rápidas de transição de estado, checkpoints no mesmo segundo têm timestamp idêntico, e a cláusula `WHERE created_at > ?` falha em deletar checkpoints futuros. |
| 4 | **MÉDIA** | [`core/checkpointer.py:226–234`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L226) — Crash com `json.JSONDecodeError` não tratado em `get_checkpoint` para blobs corrompidos ou truncados no SQLite (ao contrário de `load_checkpoint` que possui fallback seguro). |
| 5 | **MÉDIA** | [`core/checkpointer.py:112–113, 137–138, 201–206`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L112) — Tipagem insegura do Mypy e risco de `TypeError: 'NoneType' object is not callable` na resolução dinâmica de `write_fn`. 4 erros apontados pelo Mypy. |

---

## 3. Matriz de Interação Crítica entre Achados

1. **Interação entre #1 (Despacho) e Time-Travel (#2 e #3):** Se `save_checkpoint` for corrigido para gravar dados de agente estritamente em `agent_checkpoints`, esses checkpoints ficarão permanentemente invisíveis para `execute_time_travel` (que opera apenas sobre `fsm_checkpoints`). Se `execute_time_travel` for expandido para podar `agent_checkpoints`, deve obrigatoriamente filtrar por `agent_id` e `session_id` para não reintroduzir a deleção cruzada multi-agente do `BackgroundJanitor`.
2. **Interação entre #2 (Mascaramento) e #3 (Timestamp):** Ajustar o timestamp para float sem antes remover o mascaramento de erro de #2 fará qualquer incompatibilidade de tipo no SQLite ser engolida silenciosamente, mascarando a falha do rollback.

---

## 4. Arquivos produzidos / atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-checkpointer.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-checkpointer.md) | Relatório | Relatório oficial completo com análise técnica detalhada, matriz de interação e saída bruta de reprodução |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/checkpointer.py` marcado `[x]`, próximo: `▶ storage/ (todos os arquivos)` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria |

---

# Sessão de Auditoria: `storage/` (Todos os Arquivos)

> **Data:** 2026-09-21 → 2026-09-22  
> **Item auditado:** `storage/` (todos os 9 arquivos)  
> **Status final:** ✅ Concluído, aguardando aprovação para avançar (GATE OBRIGATÓRIO)

---

## 1. Execução da Auditoria

### Escopo e Análise dos 9 Módulos:
1. [`storage/__init__.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/__init__.py) — Exportações públicas da camada de persistência.
2. [`storage/base_backend.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/base_backend.py) — Contrato abstrato `BaseVectorBackend`.
3. [`storage/connection.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py) — Gerenciamento thread-safe com `SerializedWriteQueue` e `ConnectionManager`.
4. [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) — Fachada unificada SQLite `SqliteStore`.
5. [`storage/schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py) — DDL, tabelas, índices e triggers FTS5.
6. [`storage/logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py) — Inteligência de grafo, BM25, decaimento e CTE recursiva.
7. [`storage/semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py) — Operações sobre fatos semânticos.
8. [`storage/relational_db.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py) — DDL de checkpoints relacionais.
9. [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) — Implementação concreta em ChromaDB.

### Ferramentas Estáticas e Testes:
- `mypy storage/ --follow-imports=skip` executado: 13 erros detectados (11 em `vector_store.py`, 1 em `store.py:749`, 1 em `semantic_logic.py:50`).
- `pytest tests/test_storage_logic.py` executado: 57 passed em 12.13s (14 deprecation warnings em `datetime.utcnow()`).
- Script empírico executado: [`scratch/reproduce_storage_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_storage_findings.py) confirmou os 9 achados com saída bruta de terminal colada no relatório oficial.

---

## 2. Tabela de Achados de `storage/`

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`storage/connection.py:111–140`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L111) — Deadlock inevitável em escritas reentrantes/aninhadas no `SerializedWriteQueue` travando permanentemente o worker thread `sqlite-writer`. |
| 2 | **GRAVE** | [`storage/connection.py:257–273`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L257) — Vazamento contínuo de conexões SQLite de threads finalizadas em `ConnectionManager._read_connections` (memory & descriptor leak). |
| 3 | **MÉDIA** | [`storage/connection.py:75, 81–110`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L75) — Impossibilidade de reiniciar `SerializedWriteQueue` após `stop()` (`RuntimeError: threads can only be started once`). |
| 4 | **GRAVE** | [`storage/relational_db.py:27–35`](file:///c:/Nexus-Memory/GrafoConcierge/storage/relational_db.py#L27) — Incompatibilidade de contrato: `init_fsm_checkpoints_schema` falha silenciosamente na fachada `SqliteStore` e `SchemaManager` não cria tabelas de checkpoint. |
| 5 | **GRAVE** | [`storage/logic.py:330–350`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L330) — `TypeError` em `GraphLogic._calculate_decay` com timestamps ISO offset-aware, degradando silenciosamente o score de recência para o mínimo 0.01. |
| 6 | **CRÍTICA** | [`storage/vector_store.py:711–740`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L711) — Bypass de Strict Scoping em `ChromaVectorStore.search` quando `project_uuids=[]` (Cross-Project Leakage). *Nota de Call Site:* Não há call site em produção que passe `[]`, pois `HybridSearchEngine:134` intercepta e retorna `[]` antes da chamada; a falha é de ausência de defesa em profundidade / contrato público do backend vetorial. *Adendo:* Existe uma segunda classe `HybridSearchEngine` em `core/search_engine.py` (código morto) sem parâmetros de escopo de projeto, gerando risco de colisão de nomes e uso acidental futuro. Recomendado remover o arquivo morto ou renomear a classe. |
| 7 | **MÉDIA** | [`storage/vector_store.py:477`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L477) — Crash com `ValueError` em `ChromaVectorStore.search` quando `node_id` no metadata é `None` ou string vazia. |
| 8 | **MÉDIA** | [`storage/logic.py:578–593`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L578) — Duplicação de nós em consultas CTE recursivas `get_dependency_tree` e `get_reverse_dependency_tree` devido à inclusão de `depth` em `SELECT DISTINCT *`. |
| 9 | **BAIXA** | [`storage/semantic_logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py) e [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) — Isolamento total de `semantic_logic.py` na fachada `SqliteStore`, forçando chamadores externos a quebrarem encapsulamento. |

---

## 3. Matriz de Interação Interna

- Mapeadas as interações entre os 9 componentes de `storage/` entre si no relatório oficial [`audits/storage.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/storage.md).
- Identificadas desconexões estruturais críticas:
  - `store.py` não coordena deleções com `vector_store.py`, gerando vetores órfãos.
  - `store.py` não integra `semantic_logic.py`, forçando chamadores externos a acessarem `_conn_mgr.read()`.
  - `relational_db.py` assume contrato de banco incompatível com `store.py` e `connection.py`.

---

# Auditoria Transversal: `duplicacao-serialized-write-queue` (Concluída)

**Item:** `duplicacao-serialized-write-queue` — Prioridade Alta (Achado Transversal)  
**Relatório Oficial:** [`audits/duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md)  
**Script de Reprodução Empírica:** [`scratch/test_duplicate_queue.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_duplicate_queue.py)  

## 1. Resumo da Investigação
Investigação profunda sobre a existência de duas classes com o mesmo nome (`SerializedWriteQueue`) no repositório, sua coordenação, configuração de PRAGMAs e comportamento sob concorrência e integridade referencial:
1. `interface/queue_writer.py::SerializedWriteQueue` (usada por `core/database.py::ConciergeDatabaseManager`)
2. `storage/connection.py::SerializedWriteQueue` (usada por `storage/store.py::SqliteStore` via `ConnectionManager`)

Confirmada em `interface/mcp_server.py:162` a extração forçada de `resolved_db_path = str(self._gc._store._conn_mgr._db_path)`.

## 2. Tabela de Achados Confirmados

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`storage/connection.py:59`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L59) vs [`core/database.py:56–70`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L56) — **Colisão entre Fila Real (`storage/`) e Zero Fila (`core/`) sobre o Mesmo Banco**: A moldura arquitetural desenhava duas filas, mas em produção ([`interface/mcp_server.py:166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L166)) `ConciergeDatabaseManager` opera com `write_queue=None`. A topologia real é uma fila real ativa em `storage/connection.py` coexistindo com zero fila em `core/database.py`, que dispara conexões SQLite físicas efêmeras cruas por query, sem fila, sem mutex e sem `foreign_keys=ON;`. |
| 2 | **CRÍTICA** | [`interface/mcp_server.py:166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L166) e [`core/database.py:56–70`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L56) — Ilusão de cobertura nos testes e código morto em produção: `interface/queue_writer.py::SerializedWriteQueue` é instanciada e coberta em 11 suites de teste, mas em produção `ConciergeDatabaseManager` é chamado sem `write_queue`, tornando a fila de interface código morto e executando escritas diretas efêmeras via `sqlite3.connect` por query. |
| 3 | **GRAVE** | [`interface/queue_writer.py:49–52`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L49), [`core/database.py:60`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L60) vs [`storage/connection.py:155`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L155) — Divergência de integridade referencial: `storage/connection.py` ativa `PRAGMA foreign_keys=ON;`, enquanto `interface/queue_writer.py` e `core/database.py` operam com `foreign_keys=OFF`. Provado empiricamente que `core/` grava arestas/registros com IDs órfãos no banco compartilhado, corrompendo a integridade referencial que `storage/` assume protegida. |
| 4 | **GRAVE** | [`storage/connection.py:154`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L154) vs [`interface/queue_writer.py:49`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L49) — Timeout assimétrico (5s vs 30s) e crash com `OperationalError: database is locked`: `storage/` esgota `busy_timeout=5000ms` e aborta aos 5.6s sob contenção pesada, enquanto `interface/` aguarda até 30s. |
| 5 | **MÉDIA** | [`interface/mcp_server.py:161–166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L161) — Quebra de encapsulamento privado para bifurcação de estado: acesso a `_store._conn_mgr._db_path` para instanciar gerenciador concorrente em vez de consumir fachada unificada. |

---

## 3. Arquivos Produzidos / Atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) | Relatório | Relatório completo de auditoria do achado transversal com comparativo de PRAGMAs, análise de call sites e saídas brutas (enquadramento corrigido: Fila Real vs Zero Fila) |
| [`audits/core-delta-manager.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-delta-manager.md) | Relatório | Aplicado adendo de persistência efêmera crua, sem serialização, sem foreign keys e duas conexões físicas distintas em mutações não-atômicas (Achado #3) |
| [`audits/core-background-janitor.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/core-background-janitor.md) | Relatório | Aplicado adendo de persistência efêmera crua, sem serialização, sem foreign keys e duas conexões físicas distintas no ciclo de summarização da comunidade (Achado #5) |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `duplicacao-serialized-write-queue` marcado `[x]` e refinado; notas de adendo transversais aplicadas em delta-manager, background-janitor e rate-governor (100% in-memory) |
| [`scratch/test_duplicate_queue.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_duplicate_queue.py) | Script de Reprodução | Script que comprovou os 5 achados com execução concorrente, quebra de FKs e timeout assimétrico |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria transversal e adendos aplicados aos módulos core afetados |

---

# Relatório da Auditoria: `ingestion/` (Orquestração e Processamento)

## 1. Resumo da Investigação
Auditoria aprofundada de todos os 6 módulos do pacote `ingestion/`: `crawler.py`, `extractor.py`, `summarizer.py`, `dispatcher.py`, `orchestrator.py` e `pipeline.py`.
Total de 8 achados confirmados, com 2 bugs de severidade CRÍTICA e 2 de severidade ALTA/GRAVE.

## 2. Tabela de Achados Confirmados

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`ingestion/crawler.py:108-112`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L108) vs [`ingestion/orchestrator.py:270-305`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L270) — **Perda Total de Nós e Metadados no Grafo na Renomeação de Arquivos**: O crawler detecta renomeação consultando `find_node_by_hash(content_hash)`. Como o nó retornado tem o caminho antigo, o orquestrador não atualiza o nó no grafo nem reaponta arestas, e no Step 6 (GC de nós obsoletos) identifica o caminho antigo como deletado, purgando o nó do SQLite e da base vetorial. |
| 2 | **CRÍTICA** | [`ingestion/summarizer.py:175-185`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py#L175) vs [`ingestion/orchestrator.py:228-232`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L228) — **Descarte Silencioso de 100% dos Resumos L0 com Esterilização de L1 e L2**: `summarizer.generate_file_summary` retorna tupla `(summary_text, metadata_dict)`. O orquestrador espera dicionário e tenta acessar `summary.get("summary")`, resultando em fallback para string vazia ou `NULL` em `nodes.summary`. Consequentemente, as etapas hierárquicas L1 e L2 recebem resumos vazios para agregação. |
| 3 | **GRAVE** | [`ingestion/orchestrator.py:254-256`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L254) vs [`storage/store.py:180-188`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L180) — **Falha Silenciosa de Persistência do L2 Compass com Falsa Confirmação no Log**: O orquestrador passa `folder_name` (string) como identificador de projeto para `update_project(project_id=...)`, que exige UUID. O UPDATE SQLite falha silenciosamente (0 linhas afetadas não geram exceção), e o código emite log informativo de sucesso. |
| 4 | **GRAVE** | [`ingestion/orchestrator.py:295-310`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L295) vs [`storage/vector_store.py:210`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L210) — **Acúmulo Perpétuo de Vetores Zumbis no ChromaDB na Atualização de Conteúdo**: O GC de purga só remove vetores se o arquivo tiver sido inteiramente removido do disco. Se um arquivo for modificado, novos embeddings são gerados com novos IDs sem exclusão dos embeddings antigos, inflando a base vetorial indefinidamente. |
| 5 | **MÉDIA** | [`ingestion/dispatcher.py:84`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/dispatcher.py#L84) — Silenciamento incondicional de exceções em `run_background` com `logger.error` e retorno falso de conclusão. |
| 6 | **MÉDIA** | [`ingestion/extractor.py:142`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/extractor.py#L142) — Truncamento cego de tokens via slice de caracteres (`text[:4000]`) podendo cortar entidades sintáticas no meio. |
| 7 | **BAIXA** | [`ingestion/pipeline.py:95`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/pipeline.py#L95) — Redundância estrutural com `orchestrator.py` gerando acoplamento circular e caminhos de execução mortos. |
| 8 | **BAIXA** | [`ingestion/crawler.py:48`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L48) — Inconsistência na normalização de caminhos Windows (mistura de `/` e `\\`). |

---

# Relatório da Auditoria: `bypass-governanca-por-session-id` (Segurança Transversal)

## 1. Resumo da Investigação
Investigação do mecanismo de controle de estados do `MCPToolGovernor` (`core/mcp_governor.py`) integrado ao servidor FastMCP (`interface/mcp_server.py`).
Confirmado que a governança é completamente contornável a partir de qualquer estado por injeção de `session_id`, e que o subsistema de checkpoints não possui autenticação, permitindo roubo de credenciais e envenenamento de estado de agentes.

## 2. Tabela de Achados Confirmados

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA MÁXIMA** | [`interface/mcp_server.py:246-258`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L246) e [`core/mcp_governor.py:100`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L100) — **Bypass Total do MCPToolGovernor via Ghost Token e FastMCP Descarte de Parâmetros**: Um chamador em sessão travada em `PLANNING` registra uma sessão fantasma (ex: `bypass_token`) como `MAINTENANCE` via `concierge_set_state` (categorizada erroneamente como `READ_ONLY`). Ao chamar `reset_collection({"session_id": "bypass_token"})`, o interceptor valida o token fantasma, o FastMCP descarta o argumento não declarado na função alvo e executa a operação destrutiva `DANGEROUS`, destruindo a base vetorial. |
| 2 | **CRÍTICA** | [`interface/mcp_server.py:897-960, 1731-1775`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L897) e [`core/checkpointer.py:138-144, 226-234`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L138) — **Ausência Total de Verificação de Posse em Checkpoints (Independente do Achado #1)**: `agent_get_checkpoint` (`READ_ONLY`) e `agent_save_checkpoint` (`LOCAL_MUTATION`) já estão abertas por padrão no estado `EXECUTION`. Sem autenticação ou verificação de posse de `agent_id`/`session_id`, qualquer chamador pode exfiltrar segredos ou sobrescrever/envenenar checkpoints alheios sem precisar burlar o governor nem alterar nenhum estado. |
| 3 | **GRAVE** | [`interface/mcp_server.py:261-270`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L261) — **Vazamento de 100% das 31 Ferramentas em `list_tools()` para Clientes MCP Padrão**: O protocolo JSON-RPC oficial de `tools/list` não envia `session_id`. O interceptor recebe `None`, ignorando o filtro e exibindo ferramentas perigosas a agentes em qualquer estado. |
| 4 | **GRAVE** | [`agent/run_agent.py:28-57`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L28) vs [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py) — **Desconexão Total do Runtime Cognitivo (`CognitiveAgentRunner` e `HSMEngine` Órfãos)**: Em produção, o servidor MCP nunca instancia a máquina de estados hierárquica; o estado é apenas uma string manual gerenciada pelo `MCPToolGovernor`. |
| 5 | **MÉDIA** | [`core/mcp_governor.py:37-38`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L37) — **Inicialização Insegura por Padrão (`default_state = "EXECUTION"`)**: Servidor inicia liberando mutações locais (`concierge_mine`, `concierge_commit`) por padrão em vez de modo estrito de leitura. |

---

# Relatório da Auditoria: `agent/` e `agents/` (Runtime Cognitivo e Auditor Crítico)

## 1. Resumo da Investigação
Auditoria aprofundada dos 3 arquivos de runtime cognitivo e auditoria crítica:
- [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py) (`CognitiveAgentRunner` / `HermesAgentRunner`)
- [`agent/agent_prompts.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/agent_prompts.py) (`DynamicPromptBuilder`)
- [`agents/revisor_critico.py`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py) (`RevisorCritico`, `AuditResult`, `RerankResult`)

**Nota Estrutural Mandatória (Severidade Condicional):** Conforme demonstrado no item anterior, estes módulos operam como **código órfão em produção**, desconectados do servidor FastMCP. Por isso, todas as severidades aqui registradas são estritamente **CONDICIONAIS**: não afetam o servidor em execução hoje, mas representam falhas críticas imediatas se e quando alguém decidir reconectar ou reaproveitar este código.

## 2. Tabela de Achados Confirmados

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA CONDICIONAL** | [`agent/run_agent.py:47, 82, 123, 154, 160`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L47) — **Contaminação de Turnos Multi-Sessão no Circuit Breaker**: `self.current_substate_turn_count` é um inteiro único de instância da classe compartilhado entre todas as sessões. Inicializar ou transicionar uma sessão zera indevidamente o contador de outras; sessões concorrentes somam passos no mesmo contador, gerando bloqueios espúrios em `STALL.ERROR_PAUSE` (*Cross-Session Denial of Service*). |
| 2 | **CRÍTICA CONDICIONAL** | [`agents/revisor_critico.py:555–573`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L555) — **Vazamento de Privacidade por Fallback Inseguro e Sensibilidade a Caixa (Case-Sensitivity)**: `check_contamination` usa `privacy_hierarchy.get(source_privacy, 0)` sem normalizar `.upper()`. Qualquer string em minúsculas (`"restricted"`) ou sinônimo corporativo (`"CONFIDENTIAL"`, `"SECRET"`) recebe nível `0` (`PUBLIC`), avaliando `source_level > target_level` como `False` e aprovando a transferência de dados ultra-secretos para contextos públicos (violação do princípio de *Fail-Closed*). |
| 3 | **GRAVE CONDICIONAL** | [`agents/revisor_critico.py:331, 362–381`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L331) — **Aprovação Espúria de Commits Inválidos e Incompatibilidade de Assinatura em `audit_with_retry`**: O docstring prescreve `Callable(task, outcome, feedback)`, mas o código chama `generate_fn(result.reason)` (1 argumento). Se a função lançar exceção no 1º loop, o bloco `except` aciona `break` e retorna `approved=True, partial_audit=True, loop_count=max_loops`, aprovando automaticamente um rascunho com defeito sem ter executado as tentativas. |
| 4 | **GRAVE CONDICIONAL** | [`agent/run_agent.py:151–217`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L151) — **Dessincronização de Estado e Diretrizes em `step(target_transition=...)`**: `step()` constrói o prompt dinâmico usando o estado ANTERIOR (`current_path`) e só depois efetua a transição solicitada. O LLM recebe no prompt instruções e proibições da fase antiga (ex.: `PLANNING: Nenhuma mutação física autorizada`), enquanto o retorno já indica o novo estado (`EXECUTION.CODE_GEN`), gerando alucinações e bloqueios cognitivos. |
| 5 | **GRAVE CONDICIONAL** | [`agents/revisor_critico.py:433, 490–498, 504–513`](file:///c:/Nexus-Memory/GrafoConcierge/agents/revisor_critico.py#L433) — **Defeitos de Tipagem e Crash em Reranking (`NoneType` e `int` vs `str`)**: (1) `_heuristic_rerank` quebra com `TypeError` se algum nó contiver `score_final: None`; (2) `_llm_rerank` força `relevance_map[int(nid)]`, descartando 100% dos candidatos caso `node_id` venha como `str` (padrão de nós vetoriais e paths); (3) se o mapa não casar, retorna lista vazia `[]`, violando a garantia de retornar ao menos 1 resultado. |
| 6 | **MÉDIA CONDICIONAL** | [`agent/run_agent.py:243–262`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L243) — **Incompatibilidade Estrutural Universal com Corrotinas e Bypass do RateGovernor em `execute_tool`**: Ferramentas assíncronas nunca executam através do pipeline de governança: no caminho COM Gating e COM Governor, a worker thread do `RateGovernor.submit_request` executa `task_fn()` sem `await` e `intercept_tool_call` retorna sincronicamente sem `await`, devolvendo um objeto corrotina cru não-executado (`Tool actually executed: False`); no caminho SEM Gating e COM Governor, `inspect.iscoroutinefunction` executa com `await`, mas **contorna 100% o RateGovernor** (`Governor requests recorded: 0`). |
| 7 | **MÉDIA CONDICIONAL** | [`agent/agent_prompts.py:82–132`](file:///c:/Nexus-Memory/GrafoConcierge/agent/agent_prompts.py#L82) vs [`core/mcp_governor.py:43–76`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L43) — **Dessincronização Estrutural entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX`**: `parse_state_path` decompõe apenas o super-estado. As entradas de sub-estados declaradas na matriz do governor (`DISCOVERY`, `TDD_GREEN`, `REFACTORING`) nunca são consultadas pelo builder, tornando-se regras mortas. |

---

# Relatório da Auditoria: `interface/telemetry_api.py` (Camada REST e Streaming SSE)

## 1. Resumo da Investigação
Auditoria minuciosa de [`interface/telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py) (596 linhas) e seus testes associados em [`tests/test_telemetry_api.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_telemetry_api.py).

O módulo foi submetido a execução contra o banco real do repositório ([`data/concierge.db`](file:///c:/Nexus-Memory/GrafoConcierge/data/concierge.db)) e sob inicialização limpa via FastAPI. Foram identificados 7 achados graves: quebra fatal com HTTP 500 em produção por suposição de tabelas inexistentes no esquema oficial (`files` e `agent_checkpoints`), inoperância fora da caixa por dependência não configurada (`get_db_manager`), mutilação do streaming SSE por trava de teste hardcoded (`max_checks = 5`), quebra perpétua da detecção de mudanças por timestamp dinâmico no SHA-256, permissividade irrestrita de CORS combinada com rotas mutantes sem autenticação, e crash na deserialização de datas SQLite.

## 2. Tabela de Achados Confirmados

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`interface/telemetry_api.py:153–161, 181–184`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L153) — **Falha Fatal em Produção por Suposição de Esquema Inexistente (`OperationalError: no such table: files`)**: `_build_telemetry_payload` executa queries diretas em `files` e `agent_checkpoints`. No banco real de produção (`data/concierge.db`), estas tabelas não existem (foram criadas artesanalmente apenas no `setUp` dos testes). Qualquer chamada a `/api/telemetry/snapshot` ou `/api/telemetry/stream` em produção quebra com HTTP 500 imediato. |
| 2 | **CRÍTICA** | [`interface/telemetry_api.py:114–126`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L114) — **Inoperância Fora da Caixa por Dependência Não Configurada (`RuntimeError`)**: `_db_manager_instance` inicia como `None`. `get_db_manager()` é exigido por quase todos os endpoints. Sem um `lifespan` handler que leia `GRAFO_DB_PATH` ou inicialização automática, subir a API com `uvicorn interface.telemetry_api:app` resulta em HTTP 500 em 100% das rotas de dados. |
| 3 | **GRAVE** | [`interface/telemetry_api.py:556–572`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L556) — **Falso Stream Contínuo: SSE Aborta após 5 Segundos por Trava de Teste Codificada em Produção (`max_checks = 5`)**: O gerador assíncrono `_telemetry_event_generator` limita o loop a `max_checks = 5` ("Limit to prevent infinite loop in tests"). A conexão com o dashboard web é abruptamente encerrada a cada 5 segundos, forçando o frontend a cair em ciclo infinito de reconexões (`reconnect loop`). |
| 4 | **GRAVE** | [`interface/telemetry_api.py:226, 234–237`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L226) — **Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico (`datetime.now()`)**: O gerador SSE promete emitir dados apenas quando o hash do payload mudar. Porém, `_build_telemetry_payload` gera `next_scheduled_run = datetime.now(tz=timezone.utc)` com milissegundos em cada execução. O hash SHA-256 é diferente a cada segundo mesmo em banco ocioso, anulando 100% o algoritmo de detecção de mudanças e saturando a rede. |
| 5 | **GRAVE** | [`interface/telemetry_api.py:98–105, 357–369`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L98) — **Insegurança Total de CORS e Ausência Completa de Autenticação em Endpoints Mutantes**: Configuração de CORS com `allow_origins=["*"]` e `allow_credentials=True` combinada com ausência total de tokens ou API keys. Qualquer página web aberta no navegador do usuário pode disparar `POST`s para `http://localhost:8000` alterando o estado do MCP (`/api/mcp/state`), relaxando o regime de segurança para `auto-approve` (`/api/gating/config`) ou corrompendo checkpoints (`/api/checkpoints/time-travel`). |
| 6 | **MÉDIA** | [`interface/telemetry_api.py:166, 199, 304–319`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L166) — **Dessincronização de Esquema e Crash de Tipagem em Timestamps (`NoneType` e `str`)**: (1) `_build_telemetry_payload` chama `datetime.fromtimestamp(ts)`, falhando com `TypeError` se `ts` for `NULL` ou string ISO (`'2026-09-24 21:00:00'`); (2) dessincronização interna: enquanto o snapshot lê de `agent_checkpoints` com coluna `timestamp`, o endpoint `/api/checkpoints/{session_id}` lê de `fsm_checkpoints` com colunas `state_name, task_id, created_at`. |
| 7 | **MÉDIA** | [`interface/telemetry_api.py:56–68`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L56) — **Thread Daemônica Órfã e Singletons Desconectados no Import do Módulo**: A mera importação de `interface.telemetry_api` (feita por `interface/mcp_server.py:151`) invoca `rate_governor_service.start()`, subindo uma thread consumidora que roda em loop contínuo consumindo CPU sem receber requisições de produção. Singletons de `SecurityGuard` e `GatingInterceptor` também são instanciados sem governar as ferramentas reais do FastMCP. |

---

## 3. Arquivos Produzidos / Atualizados Nesta Etapa

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/interface-telemetry-api.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/interface-telemetry-api.md) | Relatório | Relatório detalhado dos 7 achados com comprovação de crash em produção, travas de teste e brechas de CORS/auth |
| [`scratch/reproduce_telemetry_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_telemetry_findings.py) | Script de Reprodução | Script comprovando empiricamente os 6 principais bugs (crash em produção, db_manager None, abort em 5s no SSE, hash inválido perpétuo, CORS/mutações desprotegidas e crash de tipagem) |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | Atualizado com o fechamento do item `interface/telemetry_api.py` (19/20) e transição do foco para `grafo-dashboard-web/` |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado atualizado com os novos achados e evidências empíricas |

---

## 4. Estado Atual da Auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 19/20 concluídos
        [x] storage/ (9 achados)
        [x] duplicacao-serialized-write-queue (5 achados)
        [x] ingestion/ (8 achados)
        [x] bypass-governanca-por-session-id (5 achados)
        [x] agent/ e agents/ (7 achados condicionais)
        [x] interface/telemetry_api.py (7 achados)
        ▶ Próximo: grafo-dashboard-web/ (último item da Fase 1!)
Fase 2: bloqueada (aguarda fim da Fase 1)
Fase 3: bloqueada (aguarda fim da Fase 2)
```

**Aguardando aprovação do humano para avançar** (Regra 7 — GATE OBRIGATÓRIO).


