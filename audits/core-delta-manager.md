# Auditoria — `core/delta_manager.py`

> **Item:** `core/delta_manager.py`  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-09-18  
> **Status:** Concluído  

---

## Ferramentas Estáticas

`ruff`, `mypy` e `bandit` **não estão instalados** no ambiente (`No module named ruff/mypy/bandit`).  
Ferramentas alternativas usadas: `pytest` (testes existentes) e script de reprodução manual.

### Testes existentes — saída bruta

```
$ python -m pytest tests/test_delta_sync.py -v --tb=short
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_lazy_summarization_should_return_cached_or_recompile_on_demand PASSED [ 25%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_not_trigger_dirty_flag_for_cosmetic_changes PASSED [ 50%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_trigger_dirty_flag_for_internal_logic_changes PASSED [ 75%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_trigger_dirty_flag_for_structural_signature_changes PASSED [100%]
============================== 4 passed in 0.26s ==============================

$ python -m pytest tests/test_delta_sync_drift.py -v --tb=short
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_detect_internal_logic_drift PASSED [ 33%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_docstring_mutations PASSED [ 66%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_formatting_and_comments PASSED [100%]
============================== 3 passed in 0.12s ==============================
```

---

## Achados

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `delta_manager.py` / `hsm_engine.py` | dm: N/A (método ausente); hsm: 458 | **CRÍTICA** | `hsm_engine.py:458` chama `delta_manager.has_structural_change(target_task_id)`. Este método **não existe** no `DeltaManager`. Os únicos métodos públicos são: `calculate_ssh`, `calculate_lbh`, `process_file_change`, `compile_community_summary_jit`. Em runtime, isso lança `AttributeError`. Os testes em `test_hsm_transition_hooks_and_delta.py` passam porque usam um `MockDeltaManager` que **define** `has_structural_change()` — o mock oculta o bug no código real. | Script de reprodução: `hasattr(DeltaManager(...), 'has_structural_change') = False` — ver saída abaixo. | **CONFIRMADO** |
| 2 | `delta_manager.py` | 81 | **MÉDIA** | `_stripper = DocstringStripper()` é atributo de **classe** (compartilhado entre todas as instâncias). `DocstringStripper` herda de `ast.NodeTransformer`; o `visit()` **muta a AST in-place** via `node.body.pop(0)`. Se duas threads chamarem `calculate_lbh()` simultaneamente na mesma instância (ou instâncias diferentes — é o mesmo objeto), os `pop()` podem interferir mutuamente. `DocstringStripper` é stateless em si, mas as mutações in-place na AST criam uma janela de race condition se a mesma árvore for revisitada. | Script de reprodução: `dm_a._stripper is dm_b._stripper = True`; tree mutada de 2→1 body nodes após `visit()`. | **CONFIRMADO** |
| 3 | `delta_manager.py` | 204–265, 160–200 | **MÉDIA** | Todos os métodos internos (`_insert_new_file`, `_update_structural_change`, `_update_content_only`, `compile_community_summary_jit`) executam **2 write_query separadas** sem transação envolvente (`BEGIN` / `COMMIT`). O `database.py:execute_write()` faz `conn.commit()` individualmente por query. Se o processo morrer (SIGKILL, OOM) entre o primeiro e o segundo write, o estado do banco fica inconsistente: ex. arquivo marcado DIRTY mas comunidade limpa, ou vice-versa. Padrão idêntico ao achado de `alias_tracker.py` (operações não-atômicas). | Análise estática do código `database.py:54-69` — cada `execute_write` faz commit individual. Não há API de transação no `ConciergeDatabaseManager`. | **CONFIRMADO** |
| 4 | `delta_manager.py` | 186 | **BAIXA** | `compile_community_summary_jit()` linha 186: `payload = "\n".join(row[0] for row in files)`. Se `files.content` for `NULL` no banco, `row[0]` é `None` e o `str.join()` lança `TypeError: sequence item 0: expected str instance, NoneType found`. Nenhum dos caminhos de inserção (`_insert_new_file`) define `content` como NOT NULL, e não há constraint na DDL do teste. | Script de reprodução: inseriu arquivo com `content=NULL`, chamou `compile_community_summary_jit()` → `TypeError` capturado. | **CONFIRMADO** |
| 5 | `delta_manager.py` | 83–97 | **OBSERVAÇÃO** | `calculate_ssh()` captura todas as linhas com prefixos `def `, `class `, `import `, `from ` **independentemente de indentação** (usa `line.strip()`). Isso significa que `def inner_method(self):` dentro de uma classe é tratado igual a `def top_level()`. O SSH é context-free — não distingue nível de aninhamento. Isso é **conservadoramente correto** (gera false positives, nunca false negatives para mudanças estruturais), mas reduz a precisão do hash. | Script de reprodução: linhas capturadas incluem `def inner_method(self):` junto com `def handle():` e `class Outer:`. | **CONFIRMADO** |
| 6 | `delta_manager.py` | 99–116, 83–97, 146–151 | **ALTA** | `calculate_lbh()` retorna `""` para todo non-Python (LBH universalmente cego). `calculate_ssh()` captura apenas linhas cujo `strip()` começa com `def `/`class `/`import `/`from ` — cobertura incidental e incompleta para non-Python. Ver tabela abaixo. | `tests/test_ssh_language_coverage.py` — 10 passed, saída colada abaixo. | **CONFIRMADO** |

### Achado #6 — Tabela de cobertura SSH por linguagem (gerada por `test_ssh_language_coverage.py`)

```
$ python -m pytest tests/test_ssh_language_coverage.py -v -s
============================= test session starts =============================
10 passed in 0.07s
```

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

**Regra geral:** SSH captura declarações non-Python apenas quando a linguagem
usa literalmente `import`, `class`, `def` ou `from` como prefixo de linha
(coincidência lexical). Declarações com prefixos de visibilidade (`export class`,
`public class`) ou keywords distintas (`func`, `fn`, `use`, `function`,
`#include`, `type`, `struct`, `impl`) são invisíveis. LBH é universalmente
cego — mudanças de lógica interna em non-Python nunca são detectadas.

Evidência completa: [`tests/test_ssh_language_coverage.py`](file:///c:/projetos/GrafoConcierge/tests/test_ssh_language_coverage.py)

---

## Saída bruta do script de reprodução

```
======================================================================
ACHADO 1: has_structural_change() NÃO EXISTE no DeltaManager
======================================================================
  hasattr(DeltaManager, 'has_structural_change') = False
  >>> CONFIRMADO: Método NÃO existe.
  >>> hsm_engine.py:458 chama delta_manager.has_structural_change()
  >>> Chamada resultará em AttributeError em runtime.
  >>> Métodos disponíveis: ['calculate_lbh', 'calculate_ssh', 'compile_community_summary_jit', 'db_manager', 'process_file_change']

======================================================================
ACHADO 2: _stripper é atributo de CLASSE (compartilhado, mutável)
======================================================================
  dm_a._stripper is dm_b._stripper = True
  id(dm_a._stripper) = 1713129437040
  id(dm_b._stripper) = 1713129437040
  Before visit - tree1.body[0].body length: 2
  After visit  - tree1.body[0].body length: 1
  >>> NodeTransformer.visit() MUTA a árvore in-place (pop).
  >>> _stripper compartilhado NÃO é thread-safe se chamado concorrentemente.

======================================================================
ACHADO 3: Operações multi-write não são atômicas (sem transação)
======================================================================
  _insert_new_file(): 2 write_query (INSERT files + UPDATE communities)
  _update_structural_change(): 2 write_query (UPDATE files + UPDATE communities)
  compile_community_summary_jit(): 2 write_query (UPDATE communities + UPDATE files)
  >>> Cada write_query é delegado individualmente ao SerializedWriteQueue
  >>> Se o processo morrer entre os dois writes, o estado fica inconsistente
  >>> database.py:execute_write() commita individualmente cada query
  >>> Não há BEGIN TRANSACTION / COMMIT envolvente

======================================================================
ACHADO 4: compile_community_summary_jit() — NoneType em row[0]
======================================================================
  Se files.content for NULL no banco, payload terá 'None' como string
  Linha 186: payload = '\n'.join(row[0] for row in files)
  row[0] sendo None → str(None) → 'None' na concatenação
  TypeError capturado: sequence item 0: expected str instance, NoneType found
  >>> CONFIRMADO: row[0] None causa TypeError no join

======================================================================
ACHADO 5: calculate_ssh — decorators e indented defs escapam
======================================================================
  Linhas capturadas pelo SSH: ['def handle():', 'class Outer:', 'def inner_method(self):']
  @app.route('/api') NÃO é capturado (correto)
  'def inner_method(self):' É capturado (indented method)
  >>> SSH não distingue top-level de nested defs.
  >>> Mover um método entre classes muda SSH incorretamente? Não, mover
  >>>   muda contexto mas SSH é context-free — cosmético vs. estrutural
  >>>   é conservadoramente correto (false positive, not false negative)

======================================================================
ACHADO 6: calculate_lbh retorna '' para non-Python — SSH também '' se no structural lines
======================================================================
  TypeScript code LBH: '' (empty = parse failure)
  TypeScript code SSH: ''
  Se LBH='' e SSH='', o comparison new_ssh != old_ssh é '' != '' = False
  E new_lbh != old_lbh is '' != '' = False
  >>> Toda mudança em non-Python files será classificada como COSMÉTICA
  >>> Nunca sujará comunidade — change detection está SILENCIOSAMENTE CEGO

  Após mudança ESTRUTURAL em TypeScript:
    process_file_change retornou: False
    file is_dirty: 0
    community is_dirty: 0
  >>> CONFIRMADO: Mudança estrutural em TypeScript NÃO suja a comunidade

======================================================================
FIM DA REPRODUÇÃO
======================================================================
```

---

## Resumo

6 achados totais: 1 CRÍTICO, 1 ALTO, 2 MÉDIOS, 1 BAIXO, 1 OBSERVAÇÃO.

- **CRÍTICO** (#1): Método `has_structural_change()` chamado pelo HSM mas inexistente no DeltaManager — `AttributeError` em runtime. Testes passam apenas por usar mock que mascara o bug.
- **ALTO** (#6): Change detection parcialmente cego para non-Python — ver tabela de cobertura SSH por linguagem acima (gerada por `tests/test_ssh_language_coverage.py`, 10 passed). LBH universalmente cego; SSH incidentalmente funcional (22–43% para TS/JS/Go/Java/C++, 0% para Rust/C).
- **MÉDIO** (#2): `_stripper` compartilhado entre instâncias; thread-safety duvidosa.
- **MÉDIO** (#3): Operações de DB multi-write sem transação (padrão repetido do projeto).
- **BAIXO** (#4): `TypeError` ao sumarizar comunidade com arquivo de `content=NULL`.
- **OBSERVAÇÃO** (#5): SSH context-free — conservadoramente correto mas impreciso.
