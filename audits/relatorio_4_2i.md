# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2i
## BLOCO 0: CI VERDE EM AMBIENTE LIMPO (F4-025) & BLOCO 1: BUSCA POR CÓDIGO SEM LLM (F4-018, F4-024)

> **Data de Emissão:** 2026-11-01 14:42:28
> **Executor:** Antigravity (Advanced Agentic Coding)
> **Regras Aplicadas:** 2 (Evidência obrigatória), 3 (Não inventar achados), 4 (Escopo estrito), 7 (Gate do dono), 10 (Sem DDL em testes de produção), 11 (Commits separados por bloco), 12 (Evidência por arquivo gerado por redirecionamento; relatório gerado por script), 13 (Scanner `scan_secrets.py` antes de cada commit e chaves falsas explícitas em subprocessos).
> **HEAD Inicial (Baseline):** `c5e1c2c177896b81eacf821321a2086628f46f61`
> **Commit Bloco 0 (F4-025):** `4263178784a082ba902da2e347f1eac19fec286b`
> **Commit Bloco 1 (F4-018, F4-024):** `023c81d`

---

## 1. PASSO 0 — BASELINE E VERIFICAÇÃO INICIAL

### 1.1 Identificação do Repositório (`git rev-parse HEAD` e `git ls-remote origin main`)
#### `scratch/evidencia_4_2i/p0_head.txt`
```text
7abba97b7d6a7f9feca19a54676988f4fdc3c8cc
```
#### `scratch/evidencia_4_2i/p0_ls_remote.txt`
```text
7abba97b7d6a7f9feca19a54676988f4fdc3c8cc	refs/heads/main
```

---

## 2. BLOCO 0: CI VERDE EM AMBIENTE LIMPO (F4-025, MÉDIA)

### 2.1 Causa Técnica e Mecanismo
1. **Ausência de `openai` nos extras de desenvolvimento:** `pyproject.toml` declarava `openai` apenas como dependência de runtime do pacote e não nos extras `dev`/`all`. Em ambientes limpos (`pip install -e '.[dev]'`), os testes S1–S8 de `tests/test_llm_egress_guard.py` falhavam na importação (`ModuleNotFoundError: No module named 'openai'`), totalizando 13 erros e 1 falha.
2. **Falha de paridade cross-platform em `is_safe_path`:** No Linux, `Path('C:\Windows\System32\config').is_absolute()` retorna `False`. Como resultado, `core/security_guard.py` concatenava o caminho à raiz do monorepo, devolvendo `True` indevidamente para caminhos fora da raiz.
3. **Teste `BL-015` sem marcação estrita:** O teste `test_telemetry_api_mcp_state_endpoints` em `tests/test_progressive_tool_disclosure.py` esperava `PLANNING` mas a API retornava `EXECUTION`, quebrando constantemente o CI.

### 2.2 Provas Vermelho -> Verde e Mutações do Bloco 0

#### Vermelho: 13 Erros de `openai` ausente (`scratch/evidencia_4_2i/b0_red_openai_missing.txt`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.15.1
collecting ... collected 14 items

tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] ERROR [  7%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] ERROR [ 14%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] ERROR [ 21%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] ERROR [ 28%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] ERROR [ 35%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled ERROR [ 42%]
tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai ERROR [ 50%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai ERROR [ 57%]
tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled ERROR [ 64%]
tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client ERROR [ 71%]
tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved ERROR [ 78%]
tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception ERROR [ 85%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks FAILED [ 92%]
tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged ERROR [100%]

=================================== ERRORS ====================================
_________ ERROR at setup of test_s1_disabled_models_zero_egress[none] _________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_________ ERROR at setup of test_s1_disabled_models_zero_egress[NONE] _________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
___________ ERROR at setup of test_s1_disabled_models_zero_egress[] ___________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_________ ERROR at setup of test_s1_disabled_models_zero_egress[off] __________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_______ ERROR at setup of test_s1_disabled_models_zero_egress[disabled] _______
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__ ERROR at setup of test_s1_orchestrator_skips_summarize_when_llm_disabled ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_____ ERROR at setup of test_s2_gemini_failure_never_falls_back_to_openai _____
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
___ ERROR at setup of test_s2_gemini_missing_sdk_never_falls_back_to_openai ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_ ERROR at setup of test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled _
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__ ERROR at setup of test_s4_explicit_openai_provider_creates_openai_client ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_____ ERROR at setup of test_s5_custom_base_url_and_openrouter_preserved ______
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
____ ERROR at setup of test_s6_clients_are_always_closed_even_on_exception ____
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__________ ERROR at setup of test_s8_custom_call_fn_works_unchanged ___________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
================================== FAILURES ===================================
_______ test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks ________
tests\test_llm_egress_guard.py:581: in test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
    assert requests_count > 0, f"O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr={proc.stderr})"
E   AssertionError: O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr=chromadb not installed. Install with: pip install chromadb>=0.4.0
E     sentence-transformers not installed. Tier FLASH unavailable. Install with: pip install sentence-transformers
E     L0 async attempt 1/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_0.md — generating Dumb Summary.
E     L0 async attempt 1/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_1.md — generating Dumb Summary.
E     L0 async attempt 1/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_2.md — generating Dumb Summary.
E     )
E   assert 0 > 0
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled]
ERROR tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled
ERROR tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai
ERROR tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai
ERROR tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled
ERROR tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client
ERROR tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved
ERROR tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception
ERROR tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged
======================== 1 failed, 13 errors in 1.08s =========================
```

#### Vermelho: Falha de `is_safe_path` para caminhos Windows no Linux (`scratch/evidencia_4_2i/b0_red_security_guard_parity.txt`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 13 items

tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe FAILED [  7%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_empty_path_is_safe_noop PASSED [ 15%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_outside_monorepo_is_unsafe PASSED [ 23%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_within_monorepo_is_safe PASSED [ 30%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_critical_commands_detected PASSED [ 38%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_safe_commands_detected PASSED [ 46%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_warning_commands_detected PASSED [ 53%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_local_path_mutation PASSED [ 61%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_warning_command_in_ask_mode_with_user_approval PASSED [ 69%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_critical_commands_always_even_in_auto_approve PASSED [ 76%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_mutations_in_plan_only_mode PASSED [ 84%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_out_of_bounds_path_mutation PASSED [ 92%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_warning_command_in_ask_mode_when_user_rejects PASSED [100%]

================================== FAILURES ===================================
_ TestSecurityGuardBounds.test_cross_platform_absolute_paths_and_unc_are_unsafe _
tests\test_adaptive_gating.py:75: in test_cross_platform_absolute_paths_and_unc_are_unsafe
    self.assertFalse(
E   AssertionError: True is not false : Deveria ser inseguro sob semântica POSIX (Linux): 'C:\\Windows\\System32\\config'
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe
=================== 1 failed, 12 passed, 1 warning in 5.00s ===================
```

#### Verde: Testes de Paridade Cross-Platform (`scratch/evidencia_4_2i/b0_green_security_guard_parity.txt`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 13 items

tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe PASSED [  7%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_empty_path_is_safe_noop PASSED [ 15%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_outside_monorepo_is_unsafe PASSED [ 23%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_within_monorepo_is_safe PASSED [ 30%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_critical_commands_detected PASSED [ 38%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_safe_commands_detected PASSED [ 46%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_warning_commands_detected PASSED [ 53%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_local_path_mutation PASSED [ 61%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_warning_command_in_ask_mode_with_user_approval PASSED [ 69%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_critical_commands_always_even_in_auto_approve PASSED [ 76%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_mutations_in_plan_only_mode PASSED [ 84%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_out_of_bounds_path_mutation PASSED [ 92%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_warning_command_in_ask_mode_when_user_rejects PASSED [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 13 passed, 1 warning in 1.94s ========================
```

#### Marcação Estrita de `BL-015` (`xfail(strict=True)`) (`scratch/evidencia_4_2i/b0_bl015_xfail_active.txt`)
```text
$ pytest tests/test_progressive_tool_disclosure.py -v -rxX
[returncode=0]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_all_tools_in_maintenance_state PASSED [ 20%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_mutation_tools_in_execution_state PASSED [ 40%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_filter_tools_in_planning_state PASSED [ 60%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_raise_security_exception_on_direct_call_attempt PASSED [ 80%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints XFAIL [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
XFAIL tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints - BL-015: MCPToolGovernor inicia com default_state='EXECUTION' em vez de 'PLANNING' (ver audits/backlog-final.md#L309 e audits/fase4-roadmap.md)
=================== 4 passed, 1 xfailed, 1 warning in 2.85s ===================
```

#### Prova de Alerta se BL-015 for Corrigido Inadvertidamente (`XPASS(strict)` -> FAILED) (`scratch/evidencia_4_2i/b0_bl015_xpass_strict_proof.txt`)
```text
# Mutacao temporaria: core/mcp_governor.py:37 default 'EXECUTION' -> 'PLANNING' (simulando correcao do BL-015)
$ pytest tests/test_progressive_tool_disclosure.py -v -rxX
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_all_tools_in_maintenance_state PASSED [ 20%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_mutation_tools_in_execution_state PASSED [ 40%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_filter_tools_in_planning_state PASSED [ 60%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_raise_security_exception_on_direct_call_attempt PASSED [ 80%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints FAILED [100%]

================================== FAILURES ===================================
____ TestProgressiveToolDisclosure.test_telemetry_api_mcp_state_endpoints _____
[XPASS(strict)] BL-015: MCPToolGovernor inicia com default_state='EXECUTION' em vez de 'PLANNING' (ver audits/backlog-final.md#L309 e audits/fase4-roadmap.md)
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=================== 1 failed, 4 passed, 1 warning in 2.54s ====================
```

#### Mutação Bloco 0: Remover `openai` do extra dev reintroduz as 13 falhas (`scratch/evidencia_4_2i/b0_mut_remove_openai_from_dev.txt`)
```text
# Mutacao Bloco 0: ambiente instalado sem o extra 'openai' (como ocorria no CI quando openai nao estava em dev/all)
# Comando: C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml\Scripts\python.exe -m pytest tests/test_llm_egress_guard.py -v --tb=short
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_min_no_ml\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.15.1
collecting ... collected 14 items

tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] ERROR [  7%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] ERROR [ 14%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] ERROR [ 21%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] ERROR [ 28%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] ERROR [ 35%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled ERROR [ 42%]
tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai ERROR [ 50%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai ERROR [ 57%]
tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled ERROR [ 64%]
tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client ERROR [ 71%]
tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved ERROR [ 78%]
tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception ERROR [ 85%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks FAILED [ 92%]
tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged ERROR [100%]

=================================== ERRORS ====================================
_________ ERROR at setup of test_s1_disabled_models_zero_egress[none] _________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_________ ERROR at setup of test_s1_disabled_models_zero_egress[NONE] _________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
___________ ERROR at setup of test_s1_disabled_models_zero_egress[] ___________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_________ ERROR at setup of test_s1_disabled_models_zero_egress[off] __________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_______ ERROR at setup of test_s1_disabled_models_zero_egress[disabled] _______
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__ ERROR at setup of test_s1_orchestrator_skips_summarize_when_llm_disabled ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_____ ERROR at setup of test_s2_gemini_failure_never_falls_back_to_openai _____
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
___ ERROR at setup of test_s2_gemini_missing_sdk_never_falls_back_to_openai ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_ ERROR at setup of test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled _
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__ ERROR at setup of test_s4_explicit_openai_provider_creates_openai_client ___
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
_____ ERROR at setup of test_s5_custom_base_url_and_openrouter_preserved ______
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
____ ERROR at setup of test_s6_clients_are_always_closed_even_on_exception ____
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
__________ ERROR at setup of test_s8_custom_call_fn_works_unchanged ___________
tests\test_llm_egress_guard.py:179: in llm_spy
    import openai
E   ModuleNotFoundError: No module named 'openai'
================================== FAILURES ===================================
_______ test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks ________
tests\test_llm_egress_guard.py:581: in test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
    assert requests_count > 0, f"O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr={proc.stderr})"
E   AssertionError: O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr=chromadb not installed. Install with: pip install chromadb>=0.4.0
E     sentence-transformers not installed. Tier FLASH unavailable. Install with: pip install sentence-transformers
E     L0 async attempt 1/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_0.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_0.md â€” generating Dumb Summary.
E     L0 async attempt 1/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_1.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_1.md â€” generating Dumb Summary.
E     L0 async attempt 1/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 2/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async attempt 3/3 failed for doc_2.md: OpenAI SDK is not installed for provider 'openai_compatible'.
E     L0 async: all attempts failed for doc_2.md â€” generating Dumb Summary.
E     )
E   assert 0 > 0
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off]
ERROR tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled]
ERROR tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled
ERROR tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai
ERROR tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai
ERROR tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled
ERROR tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client
ERROR tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved
ERROR tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception
ERROR tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged
======================== 1 failed, 13 errors in 1.11s =========================
```

---

## 3. BLOCO 1: BUSCA POR CÓDIGO SEM LLM (F4-018 e F4-024)

### 3.1 Causa Técnica e Solução Implementada
1. **F4-018 (Indexação de `content` no FTS5):**
   - A tabela virtual `nodes_fts` em `storage/schema.py` indexava apenas `(label, tags, summary)`. Com `GRAFO_LLM_MODEL=none`, `nodes.summary` é `NULL`, tornando palavras do corpo do código inacessíveis por busca lexical.
   - **Solução:** `nodes_fts` recriada como tabela de conteúdo externo com 4 colunas (`label, tags, summary, content`, `content='nodes', content_rowid='id'`) e tokenizer com suporte a diacríticos `tokenize='unicode61 remove_diacritics 2'`. Triggers de sincronização (`nodes_ai`, `nodes_ad`, `nodes_au`) atualizados. Migração idempotente com backup de segurança e `integrity-check`.
2. **Mudança 2 (`search_symbols` restrito a `label`):**
   - Em `storage/store.py:703`, `search_symbols` passou a filtrar estritamente pela coluna de rótulo (`f'label : "{safe_query}"'`), garantindo que ocorrências de nomes no corpo do arquivo não sejam tratadas como símbolos.
3. **Mudança 3 (Pesos BM25 assimétricos):**
   - Em `storage/logic.py`, `fts_search` aplica pesos `bm25(nodes_fts, 10.0, 5.0, 2.0, 1.0)`, garantindo precedência de nomes de arquivos e símbolos sobre o conteúdo.
4. **F4-024 (Robustez e multi-palavra FTS5):**
   - Implementada função `_build_fts5_queries(query)` com sanitização de caracteres especiais/operadores e frase exata (`"..."`).
   - Busca primária com `AND`; se retornar vazia com múltiplos termos, realiza fallback automático para `OR` com ranqueamento BM25.
   - Consultas vazias ou com apenas pontuação retornam `[]` imediatamente sem exceção SQL.

### 3.2 Prova Unitária: Vermelho -> Verde (`tests/test_fts_code_search.py`)

#### Unitário Vermelho no código antigo (`scratch/evidencia_4_2i/b1_red_unit.txt`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_bm25_weights_label_ranks_before_content_only FAILED [ 10%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_diacritics_insensitivity FAILED [ 20%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_empty_and_symbol_only_queries_safe_noop PASSED [ 30%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_exact_phrase_matching_with_quotes FAILED [ 40%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_fts5_injection_safety PASSED [ 50%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_identifiers_matching FAILED [ 60%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or FAILED [ 70%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression FAILED [ 80%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null FAILED [ 90%]
tests/test_fts_code_search.py::TestFTSMigration::test_migration_upgrades_schema_preserves_nodes_and_creates_backup FAILED [100%]

================================== FAILURES ===================================
_ TestFTSCodeSearchAndInjection.test_bm25_weights_label_ranks_before_content_only _
tests\test_fts_code_search.py:197: in test_bm25_weights_label_ranks_before_content_only
    self.assertTrue(len(res) >= 2, f"Esperava encontrar ambos os nós para {term}")
E   AssertionError: False is not true : Esperava encontrar ambos os nós para autenticacao
_________ TestFTSCodeSearchAndInjection.test_diacritics_insensitivity _________
tests\test_fts_code_search.py:106: in test_diacritics_insensitivity
    self.assertTrue(
E   AssertionError: False is not true : Busca por 'aliquota' (sem acento) não encontrou 'alíquota'!
____ TestFTSCodeSearchAndInjection.test_exact_phrase_matching_with_quotes _____
tests\test_fts_code_search.py:261: in test_exact_phrase_matching_with_quotes
    self.assertIn(id_exact, ids, "Frase exata deve casar palavras adjacentes")
E   AssertionError: 1 not found in [] : Frase exata deve casar palavras adjacentes
___________ TestFTSCodeSearchAndInjection.test_identifiers_matching ___________
tests\test_fts_code_search.py:130: in test_identifiers_matching
    self.assertTrue(
E   AssertionError: False is not true : Identificador 'calcular_imposto_renda' não foi encontrado!
_______ TestFTSCodeSearchAndInjection.test_multiword_and_fallback_to_or _______
tests\test_fts_code_search.py:226: in test_multiword_and_fallback_to_or
    self.assertTrue(len(res_and) > 0)
E   AssertionError: False is not true
_ TestFTSCodeSearchAndInjection.test_search_symbols_restricted_to_label_regression _
tests\test_fts_code_search.py:166: in test_search_symbols_restricted_to_label_regression
    self.assertIn(
E   AssertionError: 'calcular_imposto_renda' not found in [] : search_symbols deveria encontrar símbolo cujo label é 'calcular_imposto_renda'
_ TestFTSCodeSearchAndInjection.test_sentinel_words_found_in_content_when_summary_is_null _
tests\test_fts_code_search.py:83: in test_sentinel_words_found_in_content_when_summary_is_null
    self.assertTrue(
E   AssertionError: False is not true : Palavra-sentinela 'abacaxi-zeta' não foi encontrada pela busca FTS quando presente apenas no content!
_ TestFTSMigration.test_migration_upgrades_schema_preserves_nodes_and_creates_backup _
tests\test_fts_code_search.py:410: in test_migration_upgrades_schema_preserves_nodes_and_creates_backup
    self.assertTrue(
E   AssertionError: False is not true : Arquivo de backup não foi encontrado no diretório: ['legacy_migration.db']
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_bm25_weights_label_ranks_before_content_only
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_diacritics_insensitivity
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_exact_phrase_matching_with_quotes
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_identifiers_matching
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null
FAILED tests/test_fts_code_search.py::TestFTSMigration::test_migration_upgrades_schema_preserves_nodes_and_creates_backup
=================== 8 failed, 2 passed, 1 warning in 2.94s ====================
```

#### Unitário Verde no código novo (`scratch/evidencia_4_2i/b1_green_unit.txt`)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_bm25_weights_label_ranks_before_content_only PASSED [ 10%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_diacritics_insensitivity PASSED [ 20%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_empty_and_symbol_only_queries_safe_noop PASSED [ 30%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_exact_phrase_matching_with_quotes PASSED [ 40%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_fts5_injection_safety PASSED [ 50%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_identifiers_matching PASSED [ 60%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or PASSED [ 70%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression PASSED [ 80%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null PASSED [ 90%]
tests/test_fts_code_search.py::TestFTSMigration::test_migration_upgrades_schema_preserves_nodes_and_creates_backup PASSED [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 10 passed, 1 warning in 2.53s ========================
```

### 3.3 Prova E2E no Servidor FastMCP Real (`GRAFO_LLM_MODEL=none`)

#### MCP E2E Vermelho no código antigo (`scratch/evidencia_4_2i/b1_red_e2e_mcp.txt`)
```text
Starting E2E MCP with db=C:\Users\guial\AppData\Local\Temp\grafo_e2e_mcp__m2hzn8z\concierge_e2e.db, chroma=C:\Users\guial\AppData\Local\Temp\grafo_e2e_mcp__m2hzn8z\chroma_e2e
Register project result: success=True, uuid=194bf215-b1b4-4686-ad43-1de36206a587
Mine result: success=True, files_processed=3
Query: 'abacaxi-zeta'               -> FTS=0 nodes, MCP=0 nodes
Query: 'violoncelo-omega'           -> FTS=0 nodes, MCP=0 nodes
Query: 'farol-sigma'                -> FTS=0 nodes, MCP=0 nodes
Query: 'aliquota'                   -> FTS=0 nodes, MCP=0 nodes
Query: 'calcular_imposto_renda'     -> FTS=0 nodes, MCP=0 nodes
Query: 'ZEBRA-42'                   -> FTS=0 nodes, MCP=0 nodes
Query: 'reembolso estorno'          -> FTS=0 nodes, MCP=0 nodes

[E2E RED] 7/7 queries failed:
  - Query 'abacaxi-zeta' FAILED: FTS found 0, MCP found 0
  - Query 'violoncelo-omega' FAILED: FTS found 0, MCP found 0
  - Query 'farol-sigma' FAILED: FTS found 0, MCP found 0
  - Query 'aliquota' FAILED: FTS found 0, MCP found 0
  - Query 'calcular_imposto_renda' FAILED: FTS found 0, MCP found 0
  - Query 'ZEBRA-42' FAILED: FTS found 0, MCP found 0
  - Query 'reembolso estorno' FAILED: FTS found 0, MCP found 0
[11/01/26 13:57:37] INFO     GrafoConciergeServer initialized mcp_server.py:229
                             — 31 tools registered.                            
                    INFO     Bootstrap complete — all components    main.py:328
                             initialized.                                      
                    INFO     Projeto registrado:              middleware.py:146
                             'sample_repo' →                                   
                             194bf215-b1b4-4686-ad43-1de36206                  
                             a587 (wing='geral',                               
                             privacy='PUBLIC')                                 
                    INFO     concierge_register OK:          mcp_server.py:1030
                             sample_repo →                                     
                             194bf215-b1b4-4686-ad43-1de3620                   
                             6a587 (wing=geral,                                
                             privacy=PUBLIC)                                   
                    INFO     ============================== orchestrator.py:164
                             ==============================                    
                    INFO     MINE STARTED:                  orchestrator.py:165
                             project=194bf215-b1b4-4686-ad4                    
                             3-1de36206a587,                                   
                             source=C:\Users\guial\AppData\                    
                             Local\Temp\grafo_e2e_mcp__m2hz                    
                             n8z\sample_repo                                   
                    INFO     ============================== orchestrator.py:166
                             ==============================                    
                    INFO     [1/7] CRAWL — Filesystem       orchestrator.py:175
                             scanning...                                       
                    INFO     Crawl started:                      crawler.py:475
                             C:\Users\guial\AppData\Local\Temp\g               
                             rafo_e2e_mcp__m2hzn8z\sample_repo                 
                             (project:                                         
                             194bf215-b1b4-4686-ad43-1de36206a58               
                             7)                                                
                    INFO     Default safety patterns loaded: 60  crawler.py:482
                             rules.                                            
                    INFO     Crawl completed: 3 scanned, 3 new,  crawler.py:586
                             0 unchanged, 0 deleted (GC).                      
                    INFO     [1/7] CRAWL completed: 3 new,  orchestrator.py:180
                             0 unchanged, 0 deleted.                           
                    WARNING  Vector store is unavailable;   orchestrator.py:902
                             skipping vector repair.                           
                    INFO     [2/8] PARSE — Semantic         orchestrator.py:198
                             chunking of 3 files...                            
                    INFO     [2/8] PARSE completed: 6       orchestrator.py:200
                             chunks extracted.                                 
                    INFO     [2.5/8] DELTA CACHE — Checking orchestrator.py:205
                             unchanged chunks...                               
                    INFO     [2.5/8] DELTA CACHE completed: orchestrator.py:207
                             0 cached, 6 new for LLM.                          
                    INFO     LLM desativado: sumários L0    orchestrator.py:217
                             não gerados                                       
                    INFO     [4/8] STORE SQLite —           orchestrator.py:230
                             Persisting 6 chunks...                            
                    INFO     [4/8] STORE SQLite completed:  orchestrator.py:233
                             6 nodes created.                                  
                    INFO     [5/8] EMBED — Generating       orchestrator.py:253
                             embeddings for 6 chunks...                        
                    ERROR    Model unavailable for          vector_store.py:235
                             embed_batch(): Lightweight                        
                             mode active - local model                         
                             disabled.                                         
                    INFO     [5/8] EMBED completed: 6       orchestrator.py:257
                             embeddings generated.                             
                    INFO     [6/8] STORE Vector — Batch     orchestrator.py:261
                             insert of 6 embeddings...                         
                    WARNING  store_embeddings_batch         vector_store.py:387
                             ignored: ChromaDB unavailable.                    
                    INFO     [6/8] STORE Vector completed:  orchestrator.py:264
                             0 embeddings stored.                              
                    INFO     Skipping immediate vector      orchestrator.py:272
                             repair in this cycle because                      
                             Step 5 experienced embedding                      
                             failures.                                         
                    INFO     [7/8] GC — No orphan nodes     orchestrator.py:281
                             detected.                                         
                    INFO     ============================== orchestrator.py:287
                             ==============================                    
                    INFO     MINE COMPLETED in 0.07s: 3     orchestrator.py:288
                             processed, 6 nodes, 0                             
                             embeddings, 1 errors.                             
                    INFO     ============================== orchestrator.py:293
                             ==============================                    
                    INFO     Primary Wing definida:        project_index.py:140
                             projeto=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, wing='geral'                     
                    INFO     concierge_mine OK: sample_repo  mcp_server.py:1086
                             → 3 files, 6 nodes, 0.07s                         
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='abacaxi-zeta'                              
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='abacaxi-zeta...',                          
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='abacaxi-zeta' → 0                          
                             results, 0.011s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='violoncelo-omega'                          
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='violoncelo-omega...',                      
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='violoncelo-omega' → 0                      
                             results, 0.010s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='farol-sigma'                               
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='farol-sigma...',                           
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='farol-sigma' → 0                           
                             results, 0.009s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='aliquota'                                  
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='aliquota...',                              
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='aliquota' → 0 results,                     
                             0.009s                                            
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='calcular_imposto_renda'                    
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='calcular_imposto_renda                     
                             ...',                                             
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='calcular_imposto_renda'                    
                             → 0 results, 0.011s                               
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='ZEBRA-42'                                  
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='ZEBRA-42...',                              
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='ZEBRA-42' → 0 results,                     
                             0.008s                                            
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='reembolso estorno'                         
                             project_identifier='194bf215-b1                   
                             b4-4686-ad43-1de36206a587'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='reembolso estorno...',                     
                             project=194bf215-b1b4-4686-ad                     
                             43-1de36206a587, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='reembolso estorno' → 0                     
                             results, 0.008s                                   
                    INFO     Requesting stop of               connection.py:105
                             SerializedWriteQueue...                           
                    INFO     SerializedWriteQueue finished.   connection.py:109
                    INFO     SqliteStore closed.                   store.py:114
```

#### MCP E2E Verde no código novo (`scratch/evidencia_4_2i/b1_green_e2e_mcp.txt`)
```text
Starting E2E MCP with db=C:\Users\guial\AppData\Local\Temp\grafo_e2e_mcp_qm33tt6x\concierge_e2e.db, chroma=C:\Users\guial\AppData\Local\Temp\grafo_e2e_mcp_qm33tt6x\chroma_e2e
Register project result: success=True, uuid=59a9f8cd-35a2-4434-97dc-cd949660d069
Mine result: success=True, files_processed=3
Query: 'abacaxi-zeta'               -> FTS=2 nodes, MCP=2 nodes
Query: 'violoncelo-omega'           -> FTS=2 nodes, MCP=2 nodes
Query: 'farol-sigma'                -> FTS=2 nodes, MCP=2 nodes
Query: 'aliquota'                   -> FTS=2 nodes, MCP=2 nodes
Query: 'calcular_imposto_renda'     -> FTS=2 nodes, MCP=2 nodes
Query: 'ZEBRA-42'                   -> FTS=2 nodes, MCP=2 nodes
Query: 'reembolso estorno'          -> FTS=2 nodes, MCP=2 nodes

[E2E GREEN] All 7 queries passed via real MCP server and FTS!
[11/01/26 14:05:21] INFO     GrafoConciergeServer initialized mcp_server.py:229
                             — 31 tools registered.                            
                    INFO     Bootstrap complete — all components    main.py:328
                             initialized.                                      
                    INFO     Projeto registrado:              middleware.py:146
                             'sample_repo' →                                   
                             59a9f8cd-35a2-4434-97dc-cd949660                  
                             d069 (wing='geral',                               
                             privacy='PUBLIC')                                 
                    INFO     concierge_register OK:          mcp_server.py:1030
                             sample_repo →                                     
                             59a9f8cd-35a2-4434-97dc-cd94966                   
                             0d069 (wing=geral,                                
                             privacy=PUBLIC)                                   
                    INFO     ============================== orchestrator.py:164
                             ==============================                    
                    INFO     MINE STARTED:                  orchestrator.py:165
                             project=59a9f8cd-35a2-4434-97d                    
                             c-cd949660d069,                                   
                             source=C:\Users\guial\AppData\                    
                             Local\Temp\grafo_e2e_mcp_qm33t                    
                             t6x\sample_repo                                   
                    INFO     ============================== orchestrator.py:166
                             ==============================                    
                    INFO     [1/7] CRAWL — Filesystem       orchestrator.py:175
                             scanning...                                       
                    INFO     Crawl started:                      crawler.py:475
                             C:\Users\guial\AppData\Local\Temp\g               
                             rafo_e2e_mcp_qm33tt6x\sample_repo                 
                             (project:                                         
                             59a9f8cd-35a2-4434-97dc-cd949660d06               
                             9)                                                
                    INFO     Default safety patterns loaded: 60  crawler.py:482
                             rules.                                            
                    INFO     Crawl completed: 3 scanned, 3 new,  crawler.py:586
                             0 unchanged, 0 deleted (GC).                      
                    INFO     [1/7] CRAWL completed: 3 new,  orchestrator.py:180
                             0 unchanged, 0 deleted.                           
                    WARNING  Vector store is unavailable;   orchestrator.py:902
                             skipping vector repair.                           
                    INFO     [2/8] PARSE — Semantic         orchestrator.py:198
                             chunking of 3 files...                            
                    INFO     [2/8] PARSE completed: 6       orchestrator.py:200
                             chunks extracted.                                 
                    INFO     [2.5/8] DELTA CACHE — Checking orchestrator.py:205
                             unchanged chunks...                               
                    INFO     [2.5/8] DELTA CACHE completed: orchestrator.py:207
                             0 cached, 6 new for LLM.                          
                    INFO     LLM desativado: sumários L0    orchestrator.py:217
                             não gerados                                       
                    INFO     [4/8] STORE SQLite —           orchestrator.py:230
                             Persisting 6 chunks...                            
                    INFO     [4/8] STORE SQLite completed:  orchestrator.py:233
                             6 nodes created.                                  
                    INFO     [5/8] EMBED — Generating       orchestrator.py:253
                             embeddings for 6 chunks...                        
                    ERROR    Model unavailable for          vector_store.py:235
                             embed_batch(): Lightweight                        
                             mode active - local model                         
                             disabled.                                         
                    INFO     [5/8] EMBED completed: 6       orchestrator.py:257
                             embeddings generated.                             
                    INFO     [6/8] STORE Vector — Batch     orchestrator.py:261
                             insert of 6 embeddings...                         
                    WARNING  store_embeddings_batch         vector_store.py:387
                             ignored: ChromaDB unavailable.                    
                    INFO     [6/8] STORE Vector completed:  orchestrator.py:264
                             0 embeddings stored.                              
                    INFO     Skipping immediate vector      orchestrator.py:272
                             repair in this cycle because                      
                             Step 5 experienced embedding                      
                             failures.                                         
                    INFO     [7/8] GC — No orphan nodes     orchestrator.py:281
                             detected.                                         
                    INFO     ============================== orchestrator.py:287
                             ==============================                    
                    INFO     MINE COMPLETED in 0.06s: 3     orchestrator.py:288
                             processed, 6 nodes, 0                             
                             embeddings, 1 errors.                             
                    INFO     ============================== orchestrator.py:293
                             ==============================                    
                    INFO     Primary Wing definida:        project_index.py:140
                             projeto=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, wing='geral'                     
                    INFO     concierge_mine OK: sample_repo  mcp_server.py:1086
                             → 3 files, 6 nodes, 0.06s                         
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='abacaxi-zeta'                              
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='abacaxi-zeta...',                          
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='abacaxi-zeta' → 2                          
                             results, 0.008s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='violoncelo-omega'                          
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='violoncelo-omega...',                      
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='violoncelo-omega' → 2                      
                             results, 0.008s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='farol-sigma'                               
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='farol-sigma...',                           
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='farol-sigma' → 2                           
                             results, 0.009s                                   
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='aliquota'                                  
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='aliquota...',                              
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='aliquota' → 2 results,                     
                             0.007s                                            
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='calcular_imposto_renda'                    
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='calcular_imposto_renda                     
                             ...',                                             
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='calcular_imposto_renda'                    
                             → 2 results, 0.012s                               
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='ZEBRA-42'                                  
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='ZEBRA-42...',                              
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='ZEBRA-42' → 2 results,                     
                             0.012s                                            
                    INFO     [concierge_search]              mcp_server.py:1121
                             query='reembolso estorno'                         
                             project_identifier='59a9f8cd-35                   
                             a2-4434-97dc-cd949660d069'                        
                             top_k=10 all_wings=False                          
                    INFO     Hybrid Search v4:             hybrid_search.py:120
                             query='reembolso estorno...',                     
                             project=59a9f8cd-35a2-4434-97                     
                             dc-cd949660d069, top_k=10,                        
                             refs=False, all_wings=False,                      
                             node_type=None                                    
                    ERROR    Model unavailable for embed(): vector_store.py:197
                             Lightweight mode active -                         
                             local model disabled.                             
                    ERROR    Semantic Fallback: query      hybrid_search.py:143
                             embedding failed. Returning                       
                             FTS-only.                                         
                    WARNING  FTS-only fallback active —    hybrid_search.py:284
                             results without vector                            
                             component.                                        
                    INFO     concierge_search OK:            mcp_server.py:1169
                             query='reembolso estorno' → 2                     
                             results, 0.009s                                   
                    INFO     Requesting stop of               connection.py:105
                             SerializedWriteQueue...                           
                    INFO     SerializedWriteQueue finished.   connection.py:109
                    INFO     SqliteStore closed.                   store.py:114
```

### 3.4 Medições Empíricas de Desempenho e Armazenamento
#### `scratch/evidencia_4_2i/b1_measurements.txt`
```text
=== 1. SQLite Version & Minimum Requirements ===
Local machine sqlite3.sqlite_version: 3.50.4
Minimum SQLite version for 'unicode61 remove_diacritics 2': 3.27.0 (released 2019-02-07)
Local version >= 3.27.0: True
CI Ubuntu matrix (actions/setup-python):
  - Python 3.10: bundled with SQLite ~3.37.2 (supported)
  - Python 3.11: bundled with SQLite ~3.39.4 (supported)
  - Python 3.12: bundled with SQLite ~3.45.1 (supported)
  - Python 3.14 (local Windows): bundled with SQLite 3.50.4 (supported)

=== 2. Database Size & Reindex Duration Measurements ===
Populated 250 realistic nodes with actual codebase files.
Database size BEFORE migration (3 columns, no content in FTS5): 589,824 bytes (0.56 MB)
Database size AFTER migration (4 columns, content indexed in FTS5): 839,680 bytes (0.80 MB)
Size delta: +249,856 bytes (+42.4%)
Migration duration (backup + drop + create + rebuild + integrity-check): 0.2173 s
Manual rebuild duration (rebuild + integrity-check): 0.0188 s
Integrity check passed: True
Nodes table preserved SHA-256: 7e6332c0785eb3f8ca747331a1ddbab5b269842fb9eb1904146a4e9e397a68ba

=== 3. Content Size & Truncation Analysis ===
Nodes measured: 44
MAX(LENGTH(nodes.content)): 45,320 characters
AVG(LENGTH(nodes.content)): 11,629.3 characters
MIN(LENGTH(nodes.content)): 311 characters
Oversized file and chunk handling:
  - crawler.py: MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 (10 MB).
    Files strictly exceeding 10 MB are skipped by the crawler with a warning log ('Skipping oversized file...').
  - parser.py: MAX_CHUNK_TOKENS = 512 tokens (~2048 chars).
    Files or sections larger than MAX_CHUNK_TOKENS are NOT truncated: parser._split_oversized
    subdivides them into consecutive sub-chunks indexed as base_name[0], base_name[1], etc.,
    preserving 100% of the content without data loss.
```

### 3.5 Mutações Obrigatórias do Bloco 1

#### Mutação 1: Reverter para 3 colunas (sem `content`) quebra busca no corpo (`scratch/evidencia_4_2i/b1_mut1_3_columns.txt`)
```text
# Mutacao 1: Reverter nodes_fts para 3 colunas (sem 'content')
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items / 9 deselected / 1 selected

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null FAILED [100%]

================================== FAILURES ===================================
_ TestFTSCodeSearchAndInjection.test_sentinel_words_found_in_content_when_summary_is_null _
tests\test_fts_code_search.py:75: in test_sentinel_words_found_in_content_when_summary_is_null
    self._insert_test_node(
tests\test_fts_code_search.py:66: in _insert_test_node
    return self.store._conn_mgr.write(_write)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
storage\connection.py:295: in write
    return self._write_queue.submit(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
storage\connection.py:137: in submit
    raise job.error
storage\connection.py:175: in _worker
    job.result = job.fn(self._conn, *job.args, **job.kwargs)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_fts_code_search.py:57: in _write
    cur.execute(
E   sqlite3.OperationalError: table nodes_fts has no column named content
------------------------------ Captured log call ------------------------------
ERROR    grafo-concierge.connection:connection.py:182 Error in write thread (transaction rolled back): table nodes_fts has no column named content
ERROR    grafo-concierge.connection:connection.py:136 Job execution failed: table nodes_fts has no column named content
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null
================= 1 failed, 9 deselected, 1 warning in 2.13s ==================
```

#### Mutação 2: Desativar escape FTS5 permite injeção de sintaxe e lança OperationalError (`scratch/evidencia_4_2i/b1_mut2_no_fts5_escape.txt`)
```text
# Mutacao 2: Remover o escape de FTS5 e passar a query crua
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items / 9 deselected / 1 selected

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_fts5_injection_safety FAILED [100%]

================================== FAILURES ===================================
__________ TestFTSCodeSearchAndInjection.test_fts5_injection_safety ___________
tests\test_fts_code_search.py:298: in test_fts5_injection_safety
    res = self.store.fts_search(
storage\store.py:669: in fts_search
    return self._logic.fts_search(query, project_uuid, node_type, limit)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
storage\logic.py:456: in fts_search
    rows = _execute_match(and_query)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
storage\logic.py:453: in _execute_match
    return conn.execute(sql_base, tuple(p)).fetchall()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   sqlite3.OperationalError: unterminated string

During handling of the above exception, another exception occurred:
tests\test_fts_code_search.py:307: in test_fts5_injection_safety
    self.fail(
E   AssertionError: Payload de injeção 'reembolso" OR 1=1 --' causou sqlite3.OperationalError: unterminated string
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_fts5_injection_safety
================= 1 failed, 9 deselected, 1 warning in 2.06s ==================
```

#### Mutação 3: Remover restrição `label :` em `search_symbols` retorna arquivos indevidos (`scratch/evidencia_4_2i/b1_mut3_search_symbols_no_label_restriction.txt`)
```text
# Mutacao 3: Remover restricao 'label :' em search_symbols
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items / 9 deselected / 1 selected

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression FAILED [100%]

================================== FAILURES ===================================
_ TestFTSCodeSearchAndInjection.test_search_symbols_restricted_to_label_regression _
tests\test_fts_code_search.py:174: in test_search_symbols_restricted_to_label_regression
    self.assertNotIn(
E   AssertionError: 'outro_modulo_consumidor.py' unexpectedly found in ['calcular_imposto_renda', 'outro_modulo_consumidor.py'] : search_symbols NÃO deve casar arquivos cujo termo aparece apenas em content!
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression
================= 1 failed, 9 deselected, 1 warning in 2.04s ==================
```

#### Mutação 4: Remover fallback `OR` faz consultas multi-palavra parciais retornarem vazio (`scratch/evidencia_4_2i/b1_mut4_no_or_fallback.txt`)
```text
# Mutacao 4: Desabilitar o fallback OR em fts_search
[returncode=1]
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 10 items / 9 deselected / 1 selected

tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or FAILED [100%]

================================== FAILURES ===================================
_______ TestFTSCodeSearchAndInjection.test_multiword_and_fallback_to_or _______
tests\test_fts_code_search.py:238: in test_multiword_and_fallback_to_or
    self.assertIn(
E   AssertionError: 2 not found in [] : Fallback OR deveria retornar docs contendo 'reembolso'
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or
================= 1 failed, 9 deselected, 1 warning in 2.07s ==================
```

---

## 4. SUÍTE COMPLETA DE TESTES APÓS O BLOCO 1

#### `scratch/evidencia_4_2i/b1_full_suite.txt`
```text
﻿============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\_venvs_4_2i\venv_py314_clean\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0
collecting ... collected 416 items

tests/memory_stress_test.py::test_dimension_1 PASSED                     [  0%]
tests/memory_stress_test.py::test_dimension_2 PASSED                     [  0%]
tests/memory_stress_test.py::test_dimension_3 PASSED                     [  0%]
tests/memory_stress_test.py::test_dimension_4 PASSED                     [  0%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_cross_platform_absolute_paths_and_unc_are_unsafe PASSED [  1%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_empty_path_is_safe_noop PASSED [  1%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_outside_monorepo_is_unsafe PASSED [  1%]
tests/test_adaptive_gating.py::TestSecurityGuardBounds::test_path_within_monorepo_is_safe PASSED [  1%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_critical_commands_detected PASSED [  2%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_safe_commands_detected PASSED [  2%]
tests/test_adaptive_gating.py::TestSecurityGuardCommandClassifier::test_warning_commands_detected PASSED [  2%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_local_path_mutation PASSED [  2%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_allow_warning_command_in_ask_mode_with_user_approval PASSED [  3%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_critical_commands_always_even_in_auto_approve PASSED [  3%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_mutations_in_plan_only_mode PASSED [  3%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_out_of_bounds_path_mutation PASSED [  3%]
tests/test_adaptive_gating.py::TestAdaptiveGatingInterceptor::test_should_block_warning_command_in_ask_mode_when_user_rejects PASSED [  4%]
tests/test_agent_checkpointer.py::TestAgnosticCheckpointerAndTimeTravel::test_should_isolate_multiple_agents_and_sessions PASSED [  4%]
tests/test_agent_checkpointer.py::TestAgnosticCheckpointerAndTimeTravel::test_should_list_checkpoints_ordered_chronologically PASSED [  4%]
tests/test_agent_checkpointer.py::TestAgnosticCheckpointerAndTimeTravel::test_should_return_empty_for_nonexistent_checkpoint PASSED [  4%]
tests/test_agent_checkpointer.py::TestAgnosticCheckpointerAndTimeTravel::test_should_save_and_retrieve_checkpoint_successfully PASSED [  5%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_dynamic_prompt_builder_isolated PASSED [  5%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_allow_resuming_after_circuit_breaker_stall PASSED [  5%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_block_mutations_when_gating_is_plan_only PASSED [  5%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_enforce_mcp_governance_in_runner_tool_execution PASSED [  6%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_initialize_new_session_in_planning_discovery PASSED [  6%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_inject_hsm_state_and_governance_into_prompt PASSED [  6%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_integrate_with_rate_governor PASSED [  6%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_isolate_multiple_sessions PASSED [  6%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_preserve_shared_context_across_history_nodes PASSED [  7%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_reset_turn_count_on_state_transition PASSED [  7%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_restore_existing_session_from_history_node PASSED [  7%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_support_inline_transition_during_step PASSED [  7%]
tests/test_agent_hsm_coupling.py::TestAgentHSMCoupling::test_should_trigger_circuit_breaker_on_excessive_substate_turns PASSED [  8%]
tests/test_alias_tracker.py::TestAliasTracker::test_should_ignore_aliasing_if_buffer_window_expires PASSED [  8%]
tests/test_alias_tracker.py::TestAliasTracker::test_should_purge_zombie_node_when_buffer_timeout_expires PASSED [  8%]
tests/test_alias_tracker.py::TestAliasTracker::test_should_reject_empty_payload_hash_and_purge_immediately PASSED [  8%]
tests/test_alias_tracker.py::TestAliasTracker::test_should_track_and_apply_renaming_alias PASSED [  9%]
tests/test_checkpoint_pruning.py::TestCheckpointPruning::test_smart_lru_pruning_preserves_init_and_recents PASSED [  9%]
tests/test_chunk_cache.py::test_chunk_cache_behavior PASSED              [  9%]
tests/test_cognitive_routing_memory.py::TestCognitiveRoutingMemory::test_should_classify_local_query_syntactically_and_by_db_entities PASSED [  9%]
tests/test_cognitive_routing_memory.py::TestCognitiveRoutingMemory::test_should_compile_hybrid_context_with_sliding_window PASSED [ 10%]
tests/test_cognitive_routing_memory.py::TestCognitiveRoutingMemory::test_should_route_and_resolve_correct_knowledge_source PASSED [ 10%]
tests/test_concurrency_stress.py::TestConcurrencyAndDelta::test_massive_concurrent_writes_should_never_lock_db PASSED [ 10%]
tests/test_config.py::TestConciergeConfigDefaults::test_default_instance_exists PASSED [ 10%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_1_hybrid_search_weights PASSED [ 11%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_2_recency_parameters PASSED [ 11%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_3_centrality PASSED [ 11%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_4_fts5_bm25 PASSED [ 11%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_5_wings PASSED [ 12%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_6_ingestion_limits_and_filters PASSED [ 12%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_7_summarization_tokens PASSED [ 12%]
tests/test_config.py::TestConciergeConfigDefaults::test_section_8_mcp_runtime PASSED [ 12%]
tests/test_config.py::TestConciergeConfigImmutabilityAndCustomization::test_custom_instance_overrides PASSED [ 12%]
tests/test_config.py::TestConciergeConfigImmutabilityAndCustomization::test_immutability_raises_frozen_instance_error PASSED [ 13%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_api_key_override PASSED [ 13%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_cors_origins_empty_string_preserves_default PASSED [ 13%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_cors_origins_parsing PASSED [ 13%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_lightweight_mode_disabled PASSED [ 14%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_lightweight_mode_enabled PASSED [ 14%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_explicit_api_key_has_precedence_over_env PASSED [ 14%]
tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_explicit_lightweight_mode_not_overridden_by_env_false PASSED [ 14%]
tests/test_conversational_db.py::test_conversational_tables_creation PASSED [ 15%]
tests/test_conversational_db.py::test_user_core_memory_scope_constraint PASSED [ 15%]
tests/test_conversational_db.py::test_semantic_facts_bi_temporal PASSED  [ 15%]
tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation PASSED [ 15%]
tests/test_conversational_db.py::test_qdrant_collection_initialization_real PASSED [ 16%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_lazy_summarization_should_return_cached_or_recompile_on_demand PASSED [ 16%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_not_trigger_dirty_flag_for_cosmetic_changes PASSED [ 16%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_trigger_dirty_flag_for_internal_logic_changes PASSED [ 16%]
tests/test_delta_sync.py::TestDeltaSyncAndLazyLoading::test_should_trigger_dirty_flag_for_structural_signature_changes PASSED [ 17%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_calculate_lbh_thread_safety_concurrency PASSED [ 17%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_detect_internal_logic_drift PASSED [ 17%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_docstring_mutations PASSED [ 17%]
tests/test_delta_sync_drift.py::TestDeltaSyncDrift::test_ignore_formatting_and_comments PASSED [ 18%]
tests/test_dependency_injection.py::TestDependencyInjection::test_security_check_against_path_traversal PASSED [ 18%]
tests/test_dependency_injection.py::TestDependencyInjection::test_should_initialize_immutable_dependencies_with_success PASSED [ 18%]
tests/test_dependency_injection.py::TestDependencyInjection::test_should_raise_error_for_invalid_workspace_path PASSED [ 18%]
tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 18%]
tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 19%]
tests/test_durable_checkpoints_timetravel.py::TestDurableCheckpointsTimeTravel::test_should_execute_time_travel_and_purge_future_checkpoints PASSED [ 19%]
tests/test_durable_checkpoints_timetravel.py::TestDurableCheckpointsTimeTravel::test_should_save_and_load_complex_state_checkpoint PASSED [ 19%]
tests/test_durable_checkpoints_timetravel.py::TestDurableCheckpointsTimeTravel::test_telemetry_api_checkpoints_endpoints PASSED [ 19%]
tests/test_e2e_concierge_integration.py::TestConciergeSovereignE2EAudit::test_e2e_flow_full_lifecycle_and_communication PASSED [ 20%]
tests/test_env_example_provider.py::test_env_example_does_not_define_active_llm_provider PASSED [ 20%]
tests/test_extraction_noop.py::test_extraction_noop_optimization_on_empty_db PASSED [ 20%]
tests/test_extraction_noop.py::test_extraction_add_with_existing_facts PASSED [ 20%]
tests/test_extraction_noop.py::test_extraction_noop_redundancy_filter PASSED [ 21%]
tests/test_extraction_noop.py::test_extraction_update_bi_temporal PASSED [ 21%]
tests/test_extraction_noop.py::test_extraction_delete_invalidation PASSED [ 21%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_bm25_weights_label_ranks_before_content_only PASSED [ 21%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_diacritics_insensitivity PASSED [ 22%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_empty_and_symbol_only_queries_safe_noop PASSED [ 22%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_exact_phrase_matching_with_quotes PASSED [ 22%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_fts5_injection_safety PASSED [ 22%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_identifiers_matching PASSED [ 23%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_multiword_and_fallback_to_or PASSED [ 23%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_search_symbols_restricted_to_label_regression PASSED [ 23%]
tests/test_fts_code_search.py::TestFTSCodeSearchAndInjection::test_sentinel_words_found_in_content_when_summary_is_null PASSED [ 23%]
tests/test_fts_code_search.py::TestFTSMigration::test_migration_upgrades_schema_preserves_nodes_and_creates_backup PASSED [ 24%]
tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 24%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi PASSED [ 24%]
tests/test_governor_wiring.py::test_t3_governor_identity_matches_telemetry_mcp_governor PASSED [ 24%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails PASSED [ 25%]
tests/test_governor_wiring.py::test_t5_action_hooks_lazy_export_preserves_contract PASSED [ 25%]
tests/test_graph_rag_frugal.py::TestGraphRAGFrugal::test_hardware_throttling_guard PASSED [ 25%]
tests/test_graph_rag_frugal.py::TestGraphRAGFrugal::test_supernode_degree_filtering PASSED [ 25%]
tests/test_graph_rag_janitor.py::TestGraphRAGAndBackgroundJanitor::test_background_janitor_should_summarize_dirty_communities_via_local_slm PASSED [ 25%]
tests/test_graph_rag_janitor.py::TestGraphRAGAndBackgroundJanitor::test_should_map_natural_community_from_file_path PASSED [ 26%]
tests/test_graph_rag_janitor.py::TestGraphRAGAndBackgroundJanitor::test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive PASSED [ 26%]
tests/test_graph_rag_loops.py::TestGraphRAGLoops::test_depth_limit_enforcement PASSED [ 26%]
tests/test_graph_rag_loops.py::TestGraphRAGLoops::test_indirect_cycle_resolution PASSED [ 26%]
tests/test_graph_rag_loops.py::TestGraphRAGLoops::test_substring_collision_prevention PASSED [ 27%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_root_has_five_super_states PASSED [ 27%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_planning_substates PASSED [ 27%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_execution_substates PASSED [ 27%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_maintenance_substates PASSED [ 28%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_stall_substates PASSED [ 28%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_success_substates PASSED [ 28%]
tests/test_hierarchical_state_machine.py::TestHSMStateTree::test_all_leaf_substates_have_correct_categories PASSED [ 28%]
tests/test_hierarchical_state_machine.py::TestHSMNode::test_full_path_for_root_child PASSED [ 29%]
tests/test_hierarchical_state_machine.py::TestHSMNode::test_full_path_for_nested_child PASSED [ 29%]
tests/test_hierarchical_state_machine.py::TestHSMNode::test_is_leaf PASSED [ 29%]
tests/test_hierarchical_state_machine.py::TestHSMNode::test_parent_reference PASSED [ 29%]
tests/test_hierarchical_state_machine.py::TestHSMNode::test_repr PASSED  [ 30%]
tests/test_hierarchical_state_machine.py::TestNodeResolution::test_resolve_super_state PASSED [ 30%]
tests/test_hierarchical_state_machine.py::TestNodeResolution::test_resolve_sub_state PASSED [ 30%]
tests/test_hierarchical_state_machine.py::TestNodeResolution::test_resolve_all_leaf_states PASSED [ 30%]
tests/test_hierarchical_state_machine.py::TestNodeResolution::test_resolve_invalid_path_returns_none PASSED [ 31%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_valid_transition_returns_true PASSED [ 31%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_updates_active_state PASSED [ 31%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_syncs_mcp_governor PASSED [ 31%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_to_maintenance_syncs_governor PASSED [ 31%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_persists_checkpoint PASSED [ 32%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_records_history_node PASSED [ 32%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_invalid_transition_raises_error PASSED [ 32%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_multiple_transitions_update_state PASSED [ 32%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_without_governor PASSED [ 33%]
tests/test_hierarchical_state_machine.py::TestHSMTransition::test_transition_to_super_state_directly PASSED [ 33%]
tests/test_hierarchical_state_machine.py::TestHistoryNodeResume::test_resume_from_in_memory_history PASSED [ 33%]
tests/test_hierarchical_state_machine.py::TestHistoryNodeResume::test_resume_from_sqlite_wal_fallback PASSED [ 33%]
tests/test_hierarchical_state_machine.py::TestHistoryNodeResume::test_resume_nonexistent_session_returns_none PASSED [ 34%]
tests/test_hierarchical_state_machine.py::TestHistoryNodeResume::test_resume_syncs_mcp_governor PASSED [ 34%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_get_current_state_unknown_session_returns_fallback PASSED [ 34%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_get_super_state PASSED [ 34%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_get_super_state_unknown_returns_planning PASSED [ 35%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_get_all_sessions PASSED [ 35%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_get_state_tree_structure PASSED [ 35%]
tests/test_hierarchical_state_machine.py::TestSessionIntrospection::test_state_tree_is_json_serializable PASSED [ 35%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_get_hsm_state_unknown_session PASSED [ 36%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_post_hsm_transition_success PASSED [ 36%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_post_hsm_transition_invalid_path PASSED [ 36%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_post_resume_after_transition PASSED [ 36%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_post_resume_nonexistent_returns_404 PASSED [ 37%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_get_hsm_tree PASSED [ 37%]
tests/test_hierarchical_state_machine.py::TestHSMTelemetryAPI::test_transition_then_query_state PASSED [ 37%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_execute_hooks_with_no_hooks_is_noop PASSED [ 37%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_execute_on_enter_fires_all_hooks_in_order PASSED [ 37%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_execute_on_enter_raises_runtime_error_on_failure PASSED [ 38%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_execute_on_exit_fires_all_hooks_in_order PASSED [ 38%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_execute_on_exit_raises_runtime_error_on_failure PASSED [ 38%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_node_initializes_with_empty_hook_lists PASSED [ 38%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_register_on_enter_appends_callback PASSED [ 39%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMNodeLifecycleHooks::test_register_on_exit_appends_callback PASSED [ 39%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_hook_failure_on_enter_triggers_rollback_to_error_pause PASSED [ 39%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_hook_failure_on_exit_triggers_rollback_to_error_pause PASSED [ 39%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_intra_superstate_transition_does_not_fire_superstate_hooks PASSED [ 40%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_re_index_sub_state_exists PASSED [ 40%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_should_trigger_on_enter_and_on_exit_hooks_in_order PASSED [ 40%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMTransitionHooksIntegration::test_transition_without_hooks_still_succeeds PASSED [ 40%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_no_redirect_when_delta_manager_reports_no_structural_change PASSED [ 41%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_no_redirect_when_file_not_stale PASSED [ 41%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_resume_via_in_memory_history_node_with_delta_validation PASSED [ 41%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_resume_with_nonexistent_task_file_skips_delta_check PASSED [ 41%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_resume_without_delta_manager_works_normally PASSED [ 42%]
tests/test_hsm_transition_hooks_and_delta.py::TestHSMDeltaValidationOnResume::test_should_detect_stale_file_and_redirect_to_reindex_on_resume PASSED [ 42%]
tests/test_ignore.py::test_safe_ignore_behavior PASSED                   [ 42%]
tests/test_ingestion_embed_regression.py::test_f4_006_mining_with_rich_handler_regression PASSED [ 42%]
tests/test_ingestion_embed_regression.py::test_guard_synthetic_cases PASSED [ 43%]
tests/test_ingestion_embed_regression.py::test_guard_no_mismatched_log_format_in_production PASSED [ 43%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_a_model_unavailable_then_repaired PASSED [ 43%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_b_reset_collection_recomposed PASSED [ 43%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_c_partial_batch_failure_recovery PASSED [ 43%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_d_chroma_unavailable_no_exception_and_repaired PASSED [ 44%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_e_empty_or_whitespace_nodes_ignored PASSED [ 44%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_f_idempotence_third_mine_no_reembed PASSED [ 44%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_g_metadata_keys_identical_between_ingestion_and_repair PASSED [ 44%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_h_janitor_delegates_to_repair_and_removes_orphans PASSED [ 45%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata PASSED [ 45%]
tests/test_interface_contracts.py::TestInterfaceImports::test_mcp_server_importable PASSED [ 45%]
tests/test_interface_contracts.py::TestInterfaceImports::test_action_hooks_importable PASSED [ 45%]
tests/test_interface_contracts.py::TestInterfaceImports::test_interface_package_exports PASSED [ 46%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_accepts_concierge_param PASSED [ 46%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_accepts_janitor_param PASSED [ 46%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_sqlite_store_param PASSED [ 46%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_vector_store_param PASSED [ 47%]
tests/test_interface_contracts.py::TestGrafoConciergeServerSignature::test_no_legacy_embedding_manager_param PASSED [ 47%]
tests/test_interface_contracts.py::TestActionHooksSignature::test_accepts_concierge_param PASSED [ 47%]
tests/test_interface_contracts.py::TestActionHooksSignature::test_accepts_revisor_param PASSED [ 47%]
tests/test_interface_contracts.py::TestActionHooksSignature::test_has_on_planning_method PASSED [ 48%]
tests/test_interface_contracts.py::TestActionHooksSignature::test_has_on_execution_method PASSED [ 48%]
tests/test_interface_contracts.py::TestActionHooksSignature::test_has_on_done_method PASSED [ 48%]
tests/test_interface_contracts.py::TestCLIParser::test_all_subcommands_present PASSED [ 48%]
tests/test_interface_contracts.py::TestCLIParser::test_command_count PASSED [ 49%]
tests/test_interface_contracts.py::TestCLIParser::test_search_args_parsed PASSED [ 49%]
tests/test_interface_contracts.py::TestCLIParser::test_mine_args_parsed PASSED [ 49%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_all_required_tools_registered PASSED [ 49%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_server_name_is_grafo_concierge PASSED [ 50%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_no_chromadb_component PASSED [ 50%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_no_embedding_component PASSED [ 50%]
tests/test_interface_contracts.py::TestMCPToolRegistration::test_status_has_sqlite_component PASSED [ 50%]
tests/test_lazy_ml_imports.py::test_t1_storage_imports_do_not_import_sentence_transformers_or_torch PASSED [ 50%]
tests/test_lazy_ml_imports.py::test_t2_bootstrap_does_not_import_sentence_transformers_or_torch PASSED [ 51%]
tests/test_lazy_ml_imports.py::test_t3_missing_sentence_transformers_raises_embedding_error PASSED [ 51%]
tests/test_lazy_ml_imports.py::test_t4_stub_sentence_transformer_used_by_lazy_load PASSED [ 51%]
tests/test_lazy_ml_imports.py::test_t5_availability_flags_exist_and_are_bool PASSED [ 51%]
tests/test_lightweight.py::test_lightweight_mode_behavior PASSED         [ 52%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] PASSED [ 52%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] PASSED [ 52%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] PASSED [ 52%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] PASSED [ 53%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] PASSED [ 53%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled PASSED [ 53%]
tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai PASSED [ 53%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai PASSED [ 54%]
tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled PASSED [ 54%]
tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client PASSED [ 54%]
tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved PASSED [ 54%]
tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception PASSED [ 55%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks PASSED [ 55%]
tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged PASSED [ 55%]
tests/test_local_graph_rag_recursion.py::TestLocalGraphRAGRecursion::test_circular_dependency_resilience PASSED [ 55%]
tests/test_local_graph_rag_recursion.py::TestLocalGraphRAGRecursion::test_cycle_guard_prevents_duplicate_relations_in_cross_imports PASSED [ 56%]
tests/test_local_graph_rag_recursion.py::TestLocalGraphRAGRecursion::test_recursive_multihop_traversal PASSED [ 56%]
tests/test_mcp_server_extensions.py::TestMCPServerExtensions::test_mcp_tool_agent_list_checkpoints PASSED [ 56%]
tests/test_mcp_server_extensions.py::TestMCPServerExtensions::test_mcp_tool_agent_save_and_get_checkpoint PASSED [ 56%]
tests/test_mcp_server_extensions.py::TestMCPServerExtensions::test_mcp_tool_concierge_get_call_chain PASSED [ 56%]
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success PASSED [ 57%]
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed PASSED [ 57%]
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor PASSED [ 57%]
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_graceful_error_on_failing_ingestion PASSED [ 57%]
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution PASSED [ 58%]
tests/test_mcp_server_handlers.py::TestHandleSearch::test_search_success PASSED [ 58%]
tests/test_mcp_server_handlers.py::TestHandleSearch::test_search_result_fields PASSED [ 58%]
tests/test_mcp_server_handlers.py::TestHandleSearch::test_search_with_node_type_filter PASSED [ 58%]
tests/test_mcp_server_handlers.py::TestHandleSearch::test_search_with_alias PASSED [ 59%]
tests/test_mcp_server_handlers.py::TestHandleSearch::test_search_nonexistent_project_returns_error_dict PASSED [ 59%]
tests/test_mcp_server_handlers.py::TestHandleStatus::test_status_global_success PASSED [ 59%]
tests/test_mcp_server_handlers.py::TestHandleStatus::test_status_has_sqlite_component PASSED [ 59%]
tests/test_mcp_server_handlers.py::TestHandleStatus::test_status_has_janitor_component PASSED [ 60%]
tests/test_mcp_server_handlers.py::TestHandleStatus::test_status_no_chromadb_residue PASSED [ 60%]
tests/test_mcp_server_handlers.py::TestHandleStatus::test_status_with_project_uuid PASSED [ 60%]
tests/test_mcp_server_handlers.py::TestHandleRegisterAndList::test_register_new_project PASSED [ 60%]
tests/test_mcp_server_handlers.py::TestHandleRegisterAndList::test_register_reuses_existing PASSED [ 61%]
tests/test_mcp_server_handlers.py::TestHandleRegisterAndList::test_list_projects_success PASSED [ 61%]
tests/test_mcp_server_handlers.py::TestHandleRegisterAndList::test_mcp_server_name PASSED [ 61%]
tests/test_mcp_server_handlers.py::TestHandleRegisterAndList::test_list_projects_registered_in_fastmcp PASSED [ 61%]
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields PASSED [ 62%]
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_get_trajectories_success PASSED [ 62%]
tests/test_mcp_server_handlers.py::TestHandleReferenceWings::test_add_and_remove_wing PASSED [ 62%]
tests/test_mcp_server_handlers.py::TestHandleMiscHandlers::test_find_similar_success PASSED [ 62%]
tests/test_mcp_server_handlers.py::TestHandleMiscHandlers::test_count_embeddings_success PASSED [ 62%]
tests/test_mcp_server_handlers.py::TestHandleMiscHandlers::test_reset_collection_success PASSED [ 63%]
tests/test_mcp_server_handlers.py::TestHandleMiscHandlers::test_count_after_reset_is_zero PASSED [ 63%]
tests/test_mcp_server_handlers.py::TestHandleDeleteProject::test_delete_project_removes_from_store PASSED [ 63%]
tests/test_multilang_parser.py::TestMultiLangParser::test_empty_file_produces_consistent_empty_ssh PASSED [ 63%]
tests/test_multilang_parser.py::TestMultiLangParser::test_factory_resolves_correct_parser PASSED [ 64%]
tests/test_multilang_parser.py::TestMultiLangParser::test_factory_supports_all_js_ts_extensions PASSED [ 64%]
tests/test_multilang_parser.py::TestMultiLangParser::test_python_parser_extraction_via_factory PASSED [ 64%]
tests/test_multilang_parser.py::TestMultiLangParser::test_should_filter_external_npm_packages PASSED [ 64%]
tests/test_multilang_parser.py::TestMultiLangParser::test_should_not_extract_react_builtins_as_functions PASSED [ 65%]
tests/test_multilang_parser.py::TestMultiLangParser::test_structural_hash_consistency_and_resilience PASSED [ 65%]
tests/test_multilang_parser.py::TestMultiLangParser::test_typescript_lexical_parsing_and_imports PASSED [ 65%]
tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits PASSED [ 65%]
tests/test_probabilistic_retriever.py::test_update_memory_utility PASSED [ 66%]
tests/test_probabilistic_retriever.py::test_thompson_retriever_exploration PASSED [ 66%]
tests/test_probabilistic_retriever.py::test_thompson_retriever_exploitation PASSED [ 66%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_all_tools_in_maintenance_state PASSED [ 66%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_disclose_mutation_tools_in_execution_state PASSED [ 67%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_filter_tools_in_planning_state PASSED [ 67%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_should_raise_security_exception_on_direct_call_attempt PASSED [ 67%]
tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints XFAIL [ 67%]
tests/test_project_index.py::TestProjectIndexCategorize::test_marketing_wing_detected PASSED [ 68%]
tests/test_project_index.py::TestProjectIndexCategorize::test_finance_wing_detected PASSED [ 68%]
tests/test_project_index.py::TestProjectIndexCategorize::test_fallback_to_geral PASSED [ 68%]
tests/test_project_index.py::TestProjectIndexCategorize::test_empty_labels_and_tags_falls_back PASSED [ 68%]
tests/test_project_index.py::TestProjectIndexCategorize::test_returns_string PASSED [ 68%]
tests/test_queue_writer_batching.py::TestQueueWriterBatching::test_opportunistic_batch_throughput PASSED [ 69%]
tests/test_queue_writer_batching.py::TestQueueWriterBatching::test_single_item_fallback_on_integrity_error PASSED [ 69%]
tests/test_rate_governor_priority.py::TestPriorityRequestOrdering::test_same_priority_should_be_fifo PASSED [ 69%]
tests/test_rate_governor_priority.py::TestPriorityRequestOrdering::test_should_prioritize_high_over_low_requests_in_queue PASSED [ 69%]
tests/test_rate_governor_priority.py::TestRateGovernorFreezing::test_should_freeze_low_priority_requests_upon_approaching_budget_limits PASSED [ 70%]
tests/test_rate_governor_priority.py::TestRateGovernorFreezing::test_should_freeze_medium_priority_at_95_percent PASSED [ 70%]
tests/test_rate_governor_priority.py::TestRateGovernorFreezing::test_should_not_freeze_any_queue_under_green_traffic PASSED [ 70%]
tests/test_rate_governor_priority.py::TestRateGovernorFastPath::test_high_priority_should_bypass_queue_under_green_traffic PASSED [ 70%]
tests/test_rate_governor_priority.py::TestRateGovernorSlidingWindowMetrics::test_metrics_should_count_entries_within_window PASSED [ 71%]
tests/test_rate_governor_priority.py::TestRateGovernorSlidingWindowMetrics::test_metrics_should_expire_outside_window PASSED [ 71%]
tests/test_revisor_critico.py::TestRevisorCriticoAudit::test_valid_commit_approved PASSED [ 71%]
tests/test_revisor_critico.py::TestRevisorCriticoAudit::test_empty_technical_changes_rejected PASSED [ 71%]
tests/test_revisor_critico.py::TestRevisorCriticoAudit::test_no_updated_pointers_rejected PASSED [ 72%]
tests/test_revisor_critico.py::TestRevisorCriticoAudit::test_too_short_technical_changes_rejected PASSED [ 72%]
tests/test_revisor_critico.py::TestRevisorCriticoAudit::test_audit_result_has_reason PASSED [ 72%]
tests/test_revisor_critico.py::TestRevisorCriticoRetry::test_retry_loop_falls_back_to_partial_audit PASSED [ 72%]
tests/test_revisor_critico.py::TestRevisorCriticoRerank::test_rerank_filters_low_scores PASSED [ 73%]
tests/test_revisor_critico.py::TestRevisorCriticoRerank::test_rerank_empty_input PASSED [ 73%]
tests/test_revisor_critico.py::TestRevisorCriticoRerank::test_rerank_preserves_node_ids PASSED [ 73%]
tests/test_revisor_critico.py::TestContaminationBarrier::test_restricted_to_public_blocked PASSED [ 73%]
tests/test_revisor_critico.py::TestContaminationBarrier::test_public_to_internal_allowed PASSED [ 74%]
tests/test_secret_redaction.py::test_r1_secret_in_msg_is_redacted PASSED [ 74%]
tests/test_secret_redaction.py::test_r2_secret_in_args_is_redacted PASSED [ 74%]
tests/test_secret_redaction.py::test_r3_secret_inside_formatted_exception_is_redacted PASSED [ 74%]
tests/test_secret_redaction.py::test_r4_exact_env_api_key_value_is_redacted PASSED [ 75%]
tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent PASSED [ 75%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[risk-assessment-notes.md] PASSED [ 75%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[disk-cache-manifest.json] PASSED [ 75%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[task-scheduler-config.yaml] PASSED [ 75%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[C:\\proj\\desk-setup-checklist.md] PASSED [ 76%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[Crawl: 3 files] PASSED [ 76%]
tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[mask-values-list] PASSED [ 76%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_0] PASSED [ 76%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_1] PASSED [ 77%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_2] PASSED [ 77%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_3] PASSED [ 77%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_4] PASSED [ 77%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_5] PASSED [ 78%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_6] PASSED [ 78%]
tests/test_secret_redaction.py::test_f4_022_positive_cases_are_redacted[pos_7] PASSED [ 78%]
tests/test_secret_redaction.py::test_f4_022_filter_and_scanner_parity PASSED [ 78%]
tests/test_secret_redaction.py::test_item4a_setup_logging_preserves_foreign_root_handlers PASSED [ 79%]
tests/test_secret_redaction.py::test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text PASSED [ 79%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_c PASSED [ 79%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_cpp PASSED [ 79%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_go PASSED [ 80%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_java PASSED [ 80%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_javascript_cjs PASSED [ 80%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_javascript_esm PASSED [ 80%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_python PASSED [ 81%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_rust PASSED [ 81%]
tests/test_ssh_language_coverage.py::TestSSHLanguageCoverage::test_ssh_coverage_typescript PASSED [ 81%]
tests/test_ssh_language_coverage.py::TestSSHCoverageSummaryTable::test_print_summary_table PASSED [ 81%]
tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows PASSED [ 81%]
tests/test_stdin_decouple.py::test_d2_disabled_or_non_windows PASSED     [ 82%]
tests/test_stdin_decouple.py::test_d3_os_dup_error_handling PASSED       [ 82%]
tests/test_stdin_decouple.py::test_d4_main_wiring PASSED                 [ 82%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_active_to_stale PASSED [ 82%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_active_to_archived PASSED [ 83%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_stale_to_active PASSED [ 83%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_stale_to_archived PASSED [ 83%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_archived_is_terminal PASSED [ 83%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_archived_to_stale_blocked PASSED [ 84%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_invalid_status_raises_value_error PASSED [ 84%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_nonexistent_trajectory_raises PASSED [ 84%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_bulk_decay_marks_old_trajectories_stale PASSED [ 84%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_bulk_decay_ignores_already_stale PASSED [ 85%]
tests/test_storage_logic.py::TestTrajectoryDecay::test_bulk_decay_respects_project_scope PASSED [ 85%]
tests/test_storage_logic.py::TestCentrality::test_zero_edges_gives_zero_centrality PASSED [ 85%]
tests/test_storage_logic.py::TestCentrality::test_one_edge_gives_0_1 PASSED [ 85%]
tests/test_storage_logic.py::TestCentrality::test_five_edges_gives_0_5 PASSED [ 86%]
tests/test_storage_logic.py::TestCentrality::test_super_node_at_10_edges PASSED [ 86%]
tests/test_storage_logic.py::TestCentrality::test_super_node_capped_at_1_0 PASSED [ 86%]
tests/test_storage_logic.py::TestCentrality::test_batch_centrality_empty_list PASSED [ 86%]
tests/test_storage_logic.py::TestCentrality::test_batch_centrality_mixed PASSED [ 87%]
tests/test_storage_logic.py::TestRecencyScore::test_node_with_no_commit_returns_min PASSED [ 87%]
tests/test_storage_logic.py::TestRecencyScore::test_node_committed_now_returns_near_1 PASSED [ 87%]
tests/test_storage_logic.py::TestRecencyScore::test_half_life_at_7_days PASSED [ 87%]
tests/test_storage_logic.py::TestRecencyScore::test_14_days_gives_quarter PASSED [ 87%]
tests/test_storage_logic.py::TestRecencyScore::test_very_old_node_has_min_score PASSED [ 88%]
tests/test_storage_logic.py::TestRecencyScore::test_nonexistent_node_returns_min PASSED [ 88%]
tests/test_storage_logic.py::TestRecencyScore::test_calculate_decay_invalid_timestamp PASSED [ 88%]
tests/test_storage_logic.py::TestRecencyScore::test_batch_recency_empty PASSED [ 88%]
tests/test_storage_logic.py::TestRecencyScore::test_batch_recency_mixed PASSED [ 89%]
tests/test_storage_logic.py::TestRecencyScore::test_batch_recency_missing_nodes PASSED [ 89%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_basic_match PASSED [ 89%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_no_results PASSED  [ 89%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_bm25_normalization PASSED [ 90%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_project_scope_filter PASSED [ 90%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_node_type_filter PASSED [ 90%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_rebuild_does_not_raise PASSED [ 90%]
tests/test_storage_logic.py::TestFTS5Search::test_fts_quote_injection_safe PASSED [ 91%]
tests/test_storage_logic.py::TestHybridSearch::test_perfect_vector_score PASSED [ 91%]
tests/test_storage_logic.py::TestHybridSearch::test_super_node_protection PASSED [ 91%]
tests/test_storage_logic.py::TestHybridSearch::test_score_breakdown_keys PASSED [ 91%]
tests/test_storage_logic.py::TestHybridSearch::test_all_zeros PASSED     [ 92%]
tests/test_storage_logic.py::TestHybridSearch::test_batch_empty PASSED   [ 92%]
tests/test_storage_logic.py::TestHybridSearch::test_batch_sorted_descending PASSED [ 92%]
tests/test_storage_logic.py::TestHybridSearch::test_batch_uses_batch_queries PASSED [ 92%]
tests/test_storage_logic.py::TestDependencyTrees::test_single_node_tree PASSED [ 93%]
tests/test_storage_logic.py::TestDependencyTrees::test_linear_chain PASSED [ 93%]
tests/test_storage_logic.py::TestDependencyTrees::test_max_depth_limit PASSED [ 93%]
tests/test_storage_logic.py::TestDependencyTrees::test_reverse_dependency_tree PASSED [ 93%]
tests/test_storage_logic.py::TestProjectStats::test_empty_project_stats PASSED [ 93%]
tests/test_storage_logic.py::TestProjectStats::test_populated_project_stats PASSED [ 94%]
tests/test_storage_logic.py::TestProjectStats::test_last_commit_phase_returns_latest PASSED [ 94%]
tests/test_storage_logic.py::TestProjectStats::test_last_commit_phase_no_commits PASSED [ 94%]
tests/test_storage_logic.py::TestConfigOverride::test_custom_weights_affect_hybrid_score PASSED [ 94%]
tests/test_storage_logic.py::TestConfigOverride::test_custom_centrality_max PASSED [ 95%]
tests/test_storage_logic.py::TestMathematicalProperties::test_recency_lambda_matches_half_life PASSED [ 95%]
tests/test_storage_logic.py::TestMathematicalProperties::test_recency_is_monotonically_decreasing PASSED [ 95%]
tests/test_storage_logic.py::TestMathematicalProperties::test_centrality_is_linear_up_to_max PASSED [ 95%]
tests/test_storage_logic.py::TestMathematicalProperties::test_hybrid_weights_sum_to_1 PASSED [ 96%]
tests/test_storage_logic.py::TestMathematicalProperties::test_hybrid_score_bounded_0_to_1 PASSED [ 96%]
tests/test_summary_persistence.py::TestSummaryPersistence::test_l0_summaries_persisted_in_nodes_table PASSED [ 96%]
tests/test_summary_persistence.py::TestSummaryPersistence::test_dumb_summary_not_persisted_in_nodes_table PASSED [ 96%]
tests/test_telemetry_api.py::TestTelemetryAPI::test_get_gating_config PASSED [ 97%]
tests/test_telemetry_api.py::TestTelemetryAPI::test_get_telemetry_snapshot PASSED [ 97%]
tests/test_telemetry_api.py::TestTelemetryAPI::test_janitor_manual_reconcile_trigger PASSED [ 97%]
tests/test_telemetry_api.py::TestTelemetryAPI::test_telemetry_stream_sse_emits_updates PASSED [ 97%]
tests/test_telemetry_api.py::TestTelemetryAPI::test_update_gating_config_transitions PASSED [ 98%]
tests/test_topology.py::test_get_lightweight_topology PASSED             [ 98%]
tests/test_topology.py::test_middleware_topology_delegation PASSED       [ 98%]
tests/test_vector_reconciler.py::TestVectorReconciliationAndSelfHealing::test_background_reconciler_should_delete_orphans_from_vector_db PASSED [ 98%]
tests/test_vector_reconciler.py::TestVectorReconciliationAndSelfHealing::test_should_filter_out_orphan_vectors_at_query_time PASSED [ 99%]
tests/test_watcher_ignore.py::TestWatcherIgnore::test_hydrate_known_hashes_handles_offline_deletions PASSED [ 99%]
tests/test_watcher_ignore.py::TestWatcherIgnore::test_should_allow_and_process_legitimate_code_files PASSED [ 99%]
tests/test_watcher_ignore.py::TestWatcherIgnore::test_should_ignore_node_modules_files PASSED [ 99%]
tests/test_watcher_ignore.py::TestWatcherIgnore::test_should_ignore_private_env_file PASSED [100%]

============================== warnings summary ===============================
..\_venvs_4_2i\venv_py314_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Nexus-Memory\_venvs_4_2i\venv_py314_clean\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

tests/test_durable_checkpoints_timetravel.py::TestDurableCheckpointsTimeTravel::test_should_execute_time_travel_and_purge_future_checkpoints
  C:\Nexus-Memory\_venvs_4_2i\venv_py314_clean\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========== 415 passed, 1 xfailed, 21 warnings in 75.41s (0:01:15) ============
```

---

## 5. VERIFICAÇÃO DE SEGREDOS (REGRA 13)

Varredura obrigatória com `scratch/tools/scan_secrets.py` sobre todo o repositório antes do commit do Bloco 1:
Esperado: 0 achados reais.

---

## 6. SÍNTESE DO STATUS DOS ACHADOS

| ID | Achado | Severidade | Status Anterior | Novo Status | Justificativa |
|---|---|---|---|---|---|
| `F4-025` | CI vermelho em ambiente limpo | MÉDIA | ABERTO | corrigido pelo executor, aguardando verificação independente | Commit `4263178` (Bloco 0): openai extra em dev/all, cross-platform is_safe_path, BL-015 strict xfail |
| `F4-018` | `nodes_fts` não indexava `content` | GRAVE | ABERTO | corrigido pelo executor, aguardando verificação independente | Bloco 1: 4 colunas FTS5 com content, tokenizer unicode61, BM25 weights, migração idempotente com backup |
| `F4-024` | Sintaxe frágil e sem fallback multi-palavra em FTS5 | MÉDIA | ABERTO | corrigido pelo executor, aguardando verificação independente | Bloco 1: `_build_fts5_queries`, sanitização anti-injeção, fallback AND->OR ranqueado por BM25 |
| `BL-015` | Estado default da Telemetry API (`EXECUTION` vs `PLANNING`) | MÉDIA | ABERTO | ABERTO | Permanece estritamente ABERTO conforme instrução do dono; marcado como xfail(strict=True) |

