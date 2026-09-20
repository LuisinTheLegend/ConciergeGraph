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
| 2 | **ALTA** | [`core/rate_governor.py:231-252`](file:///c:/Nexus-Memory/GrafoConcierge/core/rate_governor.py#L231-L252) — Condição inalcançável no anti-starvation aging de prioridade 3 (`LOW`). Exige `max_pct < 75.0` para promover tarefa, mas LOW só congela com `>= 85.0`. A promoção durante congelamento é matematicamente inalcançável (`dead code`). |
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

## 4. Estado atual da auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 10/16 itens concluídos (6 pré-existentes + delta_manager + mock-vs-real-audit + security_guard + rate_governor)
         ▶ Próximo: core/background_janitor.py
Fase 2: bloqueada (requer Fase 1 completa)
Fase 3: bloqueada (requer Fase 2 completa)
```

**Aguardando aprovação do humano para avançar** (Regra 7 — GATE OBRIGATÓRIO).

