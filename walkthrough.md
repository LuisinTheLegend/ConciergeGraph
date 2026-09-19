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
- [`core/delta_sync.py`](file:///c:/projetos/GrafoConcierge/core/delta_sync.py) (re-export wrapper)
- [`tests/test_hsm_transition_hooks_and_delta.py`](file:///c:/projetos/GrafoConcierge/tests/test_hsm_transition_hooks_and_delta.py) — `MockDeltaManager` (linhas 25–41)
- [`tests/test_delta_sync.py`](file:///c:/projetos/GrafoConcierge/tests/test_delta_sync.py) (233 linhas)
- [`tests/test_delta_sync_drift.py`](file:///c:/projetos/GrafoConcierge/tests/test_delta_sync_drift.py) (87 linhas)

### Reprodução
Script de reprodução escrito e executado — **6/6 achados confirmados** com saída bruta do terminal colada no relatório.

---

## 2. Achados (6 total)

| # | Severidade | Resumo |
|---|-----------|--------|
| 1 | **CRÍTICA** | [`hsm_engine.py:458`](file:///c:/projetos/GrafoConcierge/core/hsm_engine.py#L458) chama `delta_manager.has_structural_change()` — método **inexistente** no DeltaManager. `AttributeError` em runtime. Mascarado por `MockDeltaManager` nos testes. |
| 2 | **MÉDIA** | [`delta_manager.py:81`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py#L81) — `_stripper` é atributo de classe compartilhado. `visit()` muta AST in-place (`pop`). Não thread-safe. |
| 3 | **MÉDIA** | [`delta_manager.py:204-265`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py#L204-L265) — Operações multi-write sem transação atômica. Crash entre writes = estado inconsistente. |
| 4 | **BAIXA** | [`delta_manager.py:186`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py#L186) — `TypeError` se `files.content` for `NULL` no banco. |
| 5 | **OBSERVAÇÃO** | [`delta_manager.py:83-97`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py#L83-L97) — SSH context-free (captura `def`/`class` em qualquer nível de indentação). Conservadoramente correto. |
| 6 | **ALTA** | [`delta_manager.py:99-116`](file:///c:/projetos/GrafoConcierge/core/delta_manager.py#L99-L116) — Change detection parcialmente cego para non-Python. LBH universalmente cego; SSH incidentalmente funcional (0–43% dependendo da linguagem). |

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

**Ação:** Criado [`tests/test_ssh_language_coverage.py`](file:///c:/projetos/GrafoConcierge/tests/test_ssh_language_coverage.py) com:
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

---

## 4. Arquivos produzidos

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| [`audits/core-delta-manager.md`](file:///c:/projetos/GrafoConcierge/audits/core-delta-manager.md) | Relatório | Tabela de achados, saída bruta de reprodução, tabela de cobertura SSH |
| [`tests/test_ssh_language_coverage.py`](file:///c:/projetos/GrafoConcierge/tests/test_ssh_language_coverage.py) | Teste | 10 testes parametrizados documentando cobertura SSH por linguagem |
| [`AUDIT_PROTOCOL.md`](file:///c:/projetos/GrafoConcierge/AUDIT_PROTOCOL.md) | Protocolo | `core/delta_manager.py` marcado `[x]`, próximo: `▶ core/security_guard.py` |

## 5. Arquivos **não** modificados

Nenhum arquivo de código de produção foi editado (Regra 8 — Fases 1 e 2 são somente-leitura).

---

## 6. Estado atual da auditoria

```
Fase 0: [ ] baseline (não iniciada)
Fase 1: 7/16 itens concluídos (6 pré-existentes + 1 nesta sessão)
         ▶ Próximo: core/security_guard.py
Fase 2: bloqueada (requer Fase 1 completa)
Fase 3: bloqueada (requer Fase 2 completa)
```

**Aguardando aprovação do humano para avançar** (Regra 7 — GATE OBRIGATÓRIO).
