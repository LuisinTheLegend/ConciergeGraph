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
| 2 | **ALTA** | [`core/checkpointer.py:195–210`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L195) — Falha de atomicidade e mascaramento silencioso de erros em `execute_time_travel`. O loop ignora o retorno de `write_fn` (`execute_write`), que retorna tupla `(False, error)` e não propaga exceções. Se o rollback falhar no banco, `execute_time_travel` retorna `target_data`, reportando falso sucesso de Time-Travel. |
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
| 1 | **CRÍTICA** | [`interface/queue_writer.py:32`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L32) vs [`storage/connection.py:59`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L59) — Duplicação arquitetural não coordenada de `SerializedWriteQueue`: duas threads escritoras disputando o mesmo arquivo físico `data/concierge.db` sem qualquer mutex ou coordenação em memória. |
| 2 | **CRÍTICA** | [`interface/mcp_server.py:166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L166) e [`core/database.py:56–70`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L56) — Ilusão de cobertura nos testes e código morto em produção: `interface/queue_writer.py` é instanciada em 11 suites de teste, mas em produção `ConciergeDatabaseManager` é chamado sem `write_queue`, executando escritas diretas efêmeras via `sqlite3.connect` por query, desprotegidas de fila. |
| 3 | **GRAVE** | [`interface/queue_writer.py:49–52`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L49), [`core/database.py:60`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L60) vs [`storage/connection.py:155`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L155) — Divergência de integridade referencial: `storage/connection.py` ativa `PRAGMA foreign_keys=ON;`, enquanto `interface/queue_writer.py` e `core/database.py` operam com `foreign_keys=OFF`. Provado empiricamente que `core/` grava arestas/registros com IDs órfãos no banco compartilhado, corrompendo a integridade referencial que `storage/` assume protegida. |
| 4 | **GRAVE** | [`storage/connection.py:154`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L154) vs [`interface/queue_writer.py:49`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L49) — Timeout assimétrico (5s vs 30s) e crash com `OperationalError: database is locked`: `storage/` esgota `busy_timeout=5000ms` e aborta aos 5.6s sob contenção pesada, enquanto `interface/` aguarda até 30s. |
| 5 | **MÉDIA** | [`interface/mcp_server.py:161–166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L161) — Quebra de encapsulamento privado para bifurcação de estado: acesso a `_store._conn_mgr._db_path` para instanciar gerenciador concorrente em vez de consumir fachada unificada. |

---

## 3. Arquivos Produzidos / Atualizados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/duplicacao-serialized-write-queue.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/duplicacao-serialized-write-queue.md) | Relatório | Relatório completo de auditoria do achado transversal com comparativo de PRAGMAs, análise de call sites e saídas brutas |
| [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `duplicacao-serialized-write-queue` marcado `[x]`, próximo: `▶ ingestion/ (todos os arquivos)` |
| [`scratch/test_duplicate_queue.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_duplicate_queue.py) | Script de Reprodução | Script que comprovou os 5 achados com execução concorrente, quebra de FKs e timeout assimétrico |
| [`walkthrough.md`](file:///c:/Nexus-Memory/GrafoConcierge/walkthrough.md) | Relatório de Sessão | Registro consolidado da auditoria transversal |

---

## 4. Estado Atual da Auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 15/18 itens concluídos (6 pré-existentes + delta_manager + mock-vs-real-audit + security_guard + rate_governor + background_janitor + vector_reconciler + checkpointer + storage + duplicacao-serialized-write-queue)
         ▶ Próximo: ingestion/ (todos os arquivos)
Fase 2: bloqueada (requer Fase 1 completa)
Fase 3: bloqueada (requer Fase 2 completa)
```

**Aguardando aprovação do humano para avançar** (Regra 7 — GATE OBRIGATÓRIO).


