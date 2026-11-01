# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2h-2
## FECHAMENTO DAS PENDÊNCIAS DA AUDITORIA DA 4.2h (F4-022, F4-023, ERRATA 4.2h E OBSERVAÇÕES MENORES)

> **Data de Emissão:** 2026-11-01 13:00:35
> **Regras Aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência por arquivo gerado por redirecionamento; relatório gerado por script), 13 (Scanner `scratch/tools/scan_secrets.py` antes de cada commit e chaves falsas explícitas em todos os subprocessos).
> **Escopo Tocado:** `main.py` (apenas filtro de redação e `setup_logging`), `scratch/tools/scan_secrets.py`, `.env.example`, `tests/test_secret_redaction.py`, `tests/test_env_example_provider.py`, `tests/test_llm_egress_guard.py` (apenas `pytest.importorskip("chromadb")` em `test_s1_orchestrator_skips_summarize_when_llm_disabled`), `audits/` e `scratch/evidencia_4_2h2/`.
> **Escopo Intocado:** `storage/`, esquema/FTS (`F4-018` é a `4.2i`), dependências, `data/`, `README.md`, `.env`.

---

## 1. PASSO 0 — BASELINE

### 1.1 Sincronização Git (`git pull`, `git rev-parse HEAD`, `git ls-remote origin main`)
#### `scratch/evidencia_4_2h2/p0_git_pull.txt`
```text
Already up to date.
```
#### `scratch/evidencia_4_2h2/p0_head.txt`
```text
c5e1c2c177896b81eacf821321a2086628f46f61
```
#### `scratch/evidencia_4_2h2/p0_ls_remote.txt`
```text
c5e1c2c177896b81eacf821321a2086628f46f61	refs/heads/main
```

### 1.2 Suíte Completa no Baseline (`pytest tests/ -q`)
#### `scratch/evidencia_4_2h2/p0_pytest.txt`
```text
.................................................................s...... [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
.....................................................F.................. [ 74%]
........................................................................ [ 93%]
...........................                                              [100%]
================================== FAILURES ===================================
____ TestProgressiveToolDisclosure.test_telemetry_api_mcp_state_endpoints _____

self = <test_progressive_tool_disclosure.TestProgressiveToolDisclosure testMethod=test_telemetry_api_mcp_state_endpoints>

    def test_telemetry_api_mcp_state_endpoints(self):
        """Valida os endpoints REST /api/mcp/state (POST) e /api/mcp/state/{session_id} (GET)"""
        session_id = "sess_fsm_control"
    
        # 1. Consulta estado default inicial (PLANNING)
        resp_get_default = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_default.status_code, 200)
>       self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")
E       AssertionError: 'EXECUTION' != 'PLANNING'
E       - EXECUTION
E       + PLANNING

tests\test_progressive_tool_disclosure.py:90: AssertionError
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/mcp/state/sess_fsm_control "HTTP/1.1 200 OK"
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:341: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 385 passed, 1 skipped, 20 warnings in 103.72s (0:01:43)
```

---

## 2. ITEM 1 — FALSOS POSITIVOS NO FILTRO E PARIDADE COM O SCANNER (F4-022, MÉDIA)

### 2.1 Revisão dos Padrões de Filtro (`main.py`) e Scanner (`scratch/tools/scan_secrets.py`)

| Padrão | Antes (Rodada 4.2h) | Depois (Rodada 4.2h-2) | O que mudou e motivo |
|---|---|---|---|
| `sk-` (`_LOG_SECRET_PATTERNS` e `SK_KEY_FRAGMENT`) | `r"sk-[\w*-]{6,}"` | `r"(?<![A-Za-z0-9_])sk-[\w*-]{6,}"` | Adicionado lookbehind negativo `(?<![A-Za-z0-9_])` para exigir que `sk-` não venha precedido de letra, número ou sublinhado, impedindo falsos positivos em `risk-assessment-notes.md`, `disk-cache-manifest.json`, `task-scheduler-config.yaml`, `desk-setup-checklist.md` e `mask-values-list`. |
| `AQ.` (`_LOG_SECRET_PATTERNS` e `AQ_KEY_FRAGMENT`) | `r"AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"` (filtro) / `r"AQ\.[\w*-]{4,}"` (scanner) | `r"(?<![A-Za-z0-9_])AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"` em ambos | Adicionado lookbehind negativo `(?<![A-Za-z0-9_])` e unificado o sufixo opcional `(?:\w{0,8}\.)?` entre filtro e scanner. |
| `AIza` (`_LOG_SECRET_PATTERNS` e `AIZA_KEY_FRAGMENT`) | `r"AIza[\w-]{10,}"` | `r"(?<![A-Za-z0-9_])AIza[\w-]{10,}"` em ambos | Adicionado lookbehind negativo `(?<![A-Za-z0-9_])` no filtro e no scanner para evitar casamento no meio de identificadores alfanuméricos. |
| `Bearer` (`_LOG_SECRET_PATTERNS` e `BEARER_TOKEN`) | `r'(Bearer\s+)[^\s"\',;)\]}]+'` (só no filtro) | `r'(?<![A-Za-z0-9_])(Bearer\s+)(?!\[REDACTED\])(?=[^\s"\',;)\]}]*[0-9])[A-Za-z0-9._~+/=-]{8,}'` em ambos | Adicionado lookbehind negativo `(?<![A-Za-z0-9_])`, lookahead para ignorar `[REDACTED]` já redigido e exigir ao menos um dígito em tokens de 8+ caracteres (evitando falso positivo em texto comum como `"Bearer token"`), além de incluir `BEARER_TOKEN` também em `scan_secrets.py` para paridade total. |
| Sufixo mascarado (`MASKED_KEY_SUFFIX`) | `r"\*{6,}\w{0,8}\."` | `r"\*{6,}\w{0,8}\."` (inalterado) | Mantido idêntico em ambos (6+ asteriscos seguidos de sufixo curto e ponto final). |

### 2.2 Saída Vermelha (RED) no Código de `c5e1c2c` (Itens 1a, 1c, 4a, 4b)
#### `scratch/evidencia_4_2h2/item1_red_secret_redaction.txt`
```text
.....FFFF.F........FFF                                                   [100%]
================================== FAILURES ===================================
____ test_f4_022_negative_cases_remain_identical[risk-assessment-notes.md] ____

neg_text = 'risk-assessment-notes.md'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ri[REDACTED].md' == 'risk-assessment-notes.md'
E         
E         - risk-assessment-notes.md
E         + ri[REDACTED].md

tests\test_secret_redaction.py:175: AssertionError
____ test_f4_022_negative_cases_remain_identical[disk-cache-manifest.json] ____

neg_text = 'disk-cache-manifest.json'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'di[REDACTED].json' == 'disk-cache-manifest.json'
E         
E         - disk-cache-manifest.json
E         + di[REDACTED].json

tests\test_secret_redaction.py:175: AssertionError
___ test_f4_022_negative_cases_remain_identical[task-scheduler-config.yaml] ___

neg_text = 'task-scheduler-config.yaml'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ta[REDACTED].yaml' == 'task-scheduler-config.yaml'
E         
E         - task-scheduler-config.yaml
E         + ta[REDACTED].yaml

tests\test_secret_redaction.py:175: AssertionError
_ test_f4_022_negative_cases_remain_identical[C:\\proj\\desk-setup-checklist.md] _

neg_text = 'C:\\proj\\desk-setup-checklist.md'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'C:\\proj\\de[REDACTED].md' == 'C:\\proj\\de...-checklist.md'
E         
E         - C:\proj\desk-setup-checklist.md
E         + C:\proj\de[REDACTED].md

tests\test_secret_redaction.py:175: AssertionError
________ test_f4_022_negative_cases_remain_identical[mask-values-list] ________

neg_text = 'mask-values-list'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ma[REDACTED]' == 'mask-values-list'
E         
E         - mask-values-list
E         + ma[REDACTED]

tests\test_secret_redaction.py:175: AssertionError
____________________ test_f4_022_filter_and_scanner_parity ____________________

    def test_f4_022_filter_and_scanner_parity() -> None:
        """Item 1c: O filtro de logs (main.py) e o scanner (scan_secrets.py) dão o mesmo resultado
        sobre todos os casos positivos e negativos de F4-022.
        """
        import importlib.util
        from pathlib import Path
    
        scanner_path = Path(__file__).resolve().parent.parent / "scratch" / "tools" / "scan_secrets.py"
        spec = importlib.util.spec_from_file_location("scan_secrets_mod", scanner_path)
        assert spec is not None and spec.loader is not None
        scanner_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner_mod)
    
        def scanner_matches(text: str) -> bool:
            return any(regex.search(text) is not None for _, regex in scanner_mod.SECRET_PATTERNS)
    
        def filter_redacts(text: str) -> bool:
            return main_mod.redact_log_secrets(text) != text
    
        for neg in NEGATIVE_CASES_F4_022:
            f_res = filter_redacts(neg)
            s_res = scanner_matches(neg)
>           assert f_res == s_res == False, (  # noqa: E712
                f"Divergência ou falso positivo em caso negativo {neg!r}: filter={f_res}, scanner={s_res}"
            )
E           AssertionError: Divergência ou falso positivo em caso negativo 'risk-assessment-notes.md': filter=True, scanner=True
E           assert True == False

tests\test_secret_redaction.py:215: AssertionError
__________ test_item4a_setup_logging_preserves_foreign_root_handlers __________

    def test_item4a_setup_logging_preserves_foreign_root_handlers() -> None:
        """Item 4a: um handler alheio já presente no root logger NÃO é removido por setup_logging;
        chamar setup_logging duas vezes deixa exatamente um handler do Grafo.
        """
        root = logging.getLogger()
        foreign_buf = io.StringIO()
        foreign_handler = logging.StreamHandler(foreign_buf)
        root.addHandler(foreign_handler)
        try:
            main_mod.setup_logging("INFO")
            main_mod.setup_logging("INFO")
    
>           assert foreign_handler in root.handlers, (
                "Handler alheio presente no root logger foi removido por setup_logging!"
            )
E           AssertionError: Handler alheio presente no root logger foi removido por setup_logging!
E           assert <StreamHandler (NOTSET)> in [<StreamHandler <_TemporaryFileWrapper file=<_io.FileIO name='C:\\Users\\guial\\AppData\\Local\\Temp\\tmppjc3icuz' mode='rb+' closefd=True>> (INFO)>]
E            +  where [<StreamHandler <_TemporaryFileWrapper file=<_io.FileIO name='C:\\Users\\guial\\AppData\\Local\\Temp\\tmppjc3icuz' mode='rb+' closefd=True>> (INFO)>] = <RootLogger root (INFO)>.handlers

tests\test_secret_redaction.py:243: AssertionError
_ test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text _

    def test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text() -> None:
        """Item 4b (R6): docstring de _SecretRedactingLogRecord documenta o efeito colateral em exc.args,
        e apenas o trecho que casa com padrão de segredo muda em exc.args, preservando o restante.
        """
        doc = main_mod._SecretRedactingLogRecord.__doc__ or ""
>       assert "exc.args" in doc and "efeito colateral" in doc.lower(), (
            "Docstring de _SecretRedactingLogRecord deve documentar explicitamente o efeito colateral em exc.args"
        )
E       AssertionError: Docstring de _SecretRedactingLogRecord deve documentar explicitamente o efeito colateral em exc.args
E       assert ('exc.args' in 'LogRecord que garante redação em getMessage() e em exceções formatadas\npara qualquer Handler (incluindo StreamHandler e RichHandler do FastMCP).\n')

tests\test_secret_redaction.py:263: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[risk-assessment-notes.md]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[disk-cache-manifest.json]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[task-scheduler-config.yaml]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[C:\\proj\\desk-setup-checklist.md]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[mask-values-list]
FAILED tests/test_secret_redaction.py::test_f4_022_filter_and_scanner_parity
FAILED tests/test_secret_redaction.py::test_item4a_setup_logging_preserves_foreign_root_handlers
FAILED tests/test_secret_redaction.py::test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text
8 failed, 14 passed in 0.53s
```

### 2.3 Saída Verde (GREEN) de `tests/test_secret_redaction.py` (Itens 1 e 4)
#### `scratch/evidencia_4_2h2/item4_green_secret_redaction.txt`
```text
......................                                                   [100%]
22 passed in 0.17s
```

### 2.4 Varredura do Repositório Versionado (`scratch/tools/scan_secrets.py --tracked-only`)
#### `scratch/evidencia_4_2h2/item1_d_scan_repo_tracked.txt`
```text
scanned_files=1008
files_with_findings=0
total_pattern_hits=0
```

### 2.5 Prova Funcional Real via MCP `stdio` (Item 1e — $n=3$ sequenciais antes e depois)
#### `scratch/evidencia_4_2h2/item1_e_mcp_filenames.txt`
```text
=== ITEM 1e: PROVA FUNCIONAL MCP STDIO (NOMES DE ARQUIVO COM 'sk-' INTERNO, n=3 SEQUENCIAIS) ===
Arquivos no projeto de teste: risk-assessment-notes.md, disk-cache-manifest.md, task-scheduler-config.md
Configuracao: GRAFO_LLM_MODEL=none, GRAFO_LLM_API_KEY=<falsa explicita>, GRAFO_LOG_LEVEL=DEBUG

Alvo            | Rep | St   | t(s)   | Files | Nodes | risk-.. | disk-.. | task-.. | [REDACTED]
------------------------------------------------------------------------------------------------
before_c5e1c2c  | 1   | OK   | 17.69  | 3     | 3     | 0       | 0       | 0       | 3         
before_c5e1c2c  | 2   | OK   | 18.56  | 3     | 3     | 0       | 0       | 0       | 3         
before_c5e1c2c  | 3   | OK   | 20.20  | 3     | 3     | 0       | 0       | 0       | 3         
after_fix       | 1   | OK   | 19.64  | 3     | 3     | 1       | 1       | 1       | 0         
after_fix       | 2   | OK   | 15.87  | 3     | 3     | 1       | 1       | 1       | 0         
after_fix       | 3   | OK   | 16.12  | 3     | 3     | 1       | 1       | 1       | 0         
------------------------------------------------------------------------------------------------

=== LINHAS LITERAIS DO STDERR CONTENDO OS NOMES DOS ARQUIVOS OU '[REDACTED]' ===

[before_c5e1c2c | rep=1] redacted_total=3 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:42:11 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of di[REDACTED].md removed.
  2026-11-01 12:42:11 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ri[REDACTED].md removed.
  2026-11-01 12:42:11 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ta[REDACTED].md removed.

[before_c5e1c2c | rep=2] redacted_total=3 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:42:28 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of di[REDACTED].md removed.
  2026-11-01 12:42:28 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ri[REDACTED].md removed.
  2026-11-01 12:42:28 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ta[REDACTED].md removed.

[before_c5e1c2c | rep=3] redacted_total=3 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:42:47 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of di[REDACTED].md removed.
  2026-11-01 12:42:47 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ri[REDACTED].md removed.
  2026-11-01 12:42:47 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of ta[REDACTED].md removed.

[after_fix | rep=1] redacted_total=0 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:43:07 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of disk-cache-manifest.md removed.
  2026-11-01 12:43:07 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of risk-assessment-notes.md removed.
  2026-11-01 12:43:07 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of task-scheduler-config.md removed.

[after_fix | rep=2] redacted_total=0 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:43:26 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of disk-cache-manifest.md removed.
  2026-11-01 12:43:26 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of risk-assessment-notes.md removed.
  2026-11-01 12:43:26 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of task-scheduler-config.md removed.

[after_fix | rep=3] redacted_total=0 db_labels=['<root>', 'disk-cache-manifest.md::Disk Cache Manifest', 'risk-assessment-notes.md::Risk Assessment Notes', 'task-scheduler-config.md::Task Scheduler Configuration']
  2026-11-01 12:43:42 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of disk-cache-manifest.md removed.
  2026-11-01 12:43:42 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of risk-assessment-notes.md removed.
  2026-11-01 12:43:42 │ DEBUG   │ grafo-concierge.orchestrator │ Cleanup post-ingestion: obsolete nodes of task-scheduler-config.md removed.
```

---

## 3. ITEM 2 — `.env.example` SEM `GRAFO_LLM_PROVIDER` ATIVO (F4-023, BAIXA)

### 3.1 Saída Vermelha (RED) Antes da Edição de `.env.example`
#### `scratch/evidencia_4_2h2/item2_red_env_example.txt`
```text
F                                                                        [100%]
================================== FAILURES ===================================
____________ test_env_example_does_not_define_active_llm_provider _____________

    def test_env_example_does_not_define_active_llm_provider() -> None:
        """F4-023: .env.example não traz GRAFO_LLM_PROVIDER ativo para não anular a regra de modelos gemini-*."""
        assert ENV_EXAMPLE_PATH.is_file(), f".env.example não encontrado em {ENV_EXAMPLE_PATH}"
        text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
        lines = text.splitlines()
    
        active_lines = [
            (idx + 1, line)
            for idx, line in enumerate(lines)
            if re.match(r"^\s*GRAFO_LLM_PROVIDER\s*=", line)
        ]
>       assert not active_lines, (
            f".env.example contém GRAFO_LLM_PROVIDER ativo nas linhas: {active_lines}"
        )
E       AssertionError: .env.example contém GRAFO_LLM_PROVIDER ativo nas linhas: [(22, 'GRAFO_LLM_PROVIDER=gemini')]
E       assert not [(22, 'GRAFO_LLM_PROVIDER=gemini')]

tests\test_env_example_provider.py:30: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_env_example_provider.py::test_env_example_does_not_define_active_llm_provider
1 failed in 0.47s
```

### 3.2 Saída Verde (GREEN) Após Comentar `# GRAFO_LLM_PROVIDER=gemini` e Scanner de Segredos
#### `scratch/evidencia_4_2h2/item2_green_env_example.txt`
```text
.                                                                        [100%]
1 passed in 0.12s
```
#### `scratch/evidencia_4_2h2/item2_scan_secrets.txt`
```text
scanned_files=1025
files_with_findings=0
total_pattern_hits=0
```

---

## 4. ITEM 3 — ERRATA DA RODADA 4.2h (`audits/errata-4-2h.md`)

```markdown
# Errata da Rodada 4.2h

> **Data:** 2026-11-01  
> **Referência:** Auditoria independente do commit `c5e1c2c177896b81eacf821321a2086628f46f61` (Rodada `4.2h`), tratada na Rodada `4.2h-2`.

---

## (a) A prova E2E por Tripwire Proxy (`p6_tripwire_summary.txt`) não reproduz o `F4-020`; a prova de `F4-020` são os testes `S6` e `S7`

- **Fato observado na evidência da 4.2h (`scratch/evidencia_4_2h/p6_tripwire_summary.txt`):** Em todas as repetições de `old_96ba4d0` (`E1`, `E2`, `E3`), a coluna `LoopCl` (`"Event loop is closed"`) e a coluna `TaskEx` (`"Task exception was never retrieved"`) registraram **`0`**.
- **Causa técnica:** O `TripwireProxyServer` recusa o método `CONNECT api.openai.com:443` imediatamente com `HTTP 403 Forbidden` antes que um túnel TLS/HTTP seja estabelecido. Sem conexão HTTP/TLS ativa estabelecida pelo `httpx.AsyncClient`, não resta transporte aberto pendente de fechamento assíncrono (`aclose()`) quando `asyncio.run(...)` encerra o event loop.
- **Retificação:** A prova E2E por Tripwire Proxy comprova exclusivamente o **`F4-019`** (egress de rede bloqueado em `E1`/`E2` com `0` conexões no código novo vs `27 CONNECT` no código antigo, e `27 CONNECT` quando `GRAFO_LLM_PROVIDER=openai` é definido explicitamente em `E3`). Ela **não** reproduz o **`F4-020`**. A prova executável e determinística do **`F4-020`** reside nos testes **`S6`** (verificação direta de `__enter__`/`__exit__` e `__aenter__`/`__aexit__` mesmo sob exceção) e **`S7`** (`test_s7_orchestrator_asyncio_run_closes_clients_no_unraisable_loop_closed` em [`tests/test_llm_egress_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_llm_egress_guard.py), que utiliza um servidor HTTP local respondendo `HTTP 401` sem túnel `CONNECT`, reproduzindo o `RuntimeError: Event loop is closed` no código sem `async with` e provando `0` ocorrências com `async with`).

---

## (b) Redação em `audits/bypass-governanca-por-session-id.md` (linhas 249 e 256)

- **Fato observado:** No commit `498f995` da Rodada `4.2h`, o script de redação de evidências modificou as linhas `249` e `256` de [`audits/bypass-governanca-por-session-id.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/bypass-governanca-por-session-id.md#L249-L256) (relatório da Fase 2).
- **Retificação:** Os valores presentes naquelas duas linhas eram chaves falsas de mock de teste (`sk-proj-...` fictício criado pelo script de PoC da Fase 2), e não chaves reais. A substituição por `[REDACTED]` é inócua para o conteúdo técnico do relatório, mas alterou um arquivo histórico da Fase 2 fora dos 3 arquivos de evidência da Fase 4 listados originalmente em `F4-021`.

---

## (c) Link incorreto para a Regra 13 do `AUDIT_PROTOCOL.md` no resumo da 4.2h

- **Fato observado:** A resposta/resumo da Rodada `4.2h` referenciou a Regra 13 com o link `AUDIT_PROTOCOL.md#L131-L142`.
- **Retificação:** No arquivo [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md#L46), a **Regra 13** está localizada na **linha 46** (uma única linha):
  > `13. Nenhuma evidência é commitada sem passar por scratch/tools/scan_secrets.py (zero achados em scratch/ e audits/); chaves reais nunca entram em testes.`

---

## (d) Omissão dos itens (a) e (b) no resumo de chat da Rodada 4.2h

- **Fato observado:** O resumo apresentado no chat ao final da Rodada `4.2h` não destacou espontaneamente que `p6_tripwire_summary.txt` mostrava `"Event loop is closed" = 0` no código antigo (item `a`) nem que o quarto arquivo redigido (`audits/bypass-governanca-por-session-id.md`) continha apenas mock de teste da Fase 2 (item `b`).
- **Retificação:** Ambos os pontos ficam formalmente registrados nesta errata como parte da documentação auditável do repositório.
```

---

## 5. ITEM 4 — OBSERVAÇÕES MENORES (`setup_logging`, `R6` / `exc.args`, `importorskip("chromadb")`)

### 5.1 Diff Consolidado de Produção e Testes (`c5e1c2c..HEAD`)
#### `scratch/evidencia_4_2h2/diff_c5e1c2c_head.txt`
```diff
diff --git a/.env.example b/.env.example
index 73d2604..5f1f61d 100644
--- a/.env.example
+++ b/.env.example
@@ -18,8 +18,10 @@ GEMINI_API_KEY=your_api_key_here_without_quotes
 GRAFO_LLM_MODEL=gemini-2.0-flash
 
 # Explicit LLM provider: gemini, openai, openai-compatible, openrouter, none
-# Required when using OpenAI models without GRAFO_LLM_BASE_URL
-GRAFO_LLM_PROVIDER=gemini
+# WARNING: If GRAFO_LLM_MODEL does not start with "gemini-", you MUST explicitly
+# set GRAFO_LLM_PROVIDER (e.g., GRAFO_LLM_PROVIDER=openai), otherwise the LLM
+# remains disabled (desativado) for safety.
+# GRAFO_LLM_PROVIDER=gemini
 
 # Custom base URL for alternative LLM providers (Optional)
 # Useful for OpenRouter, DeepSeek, Groq, Ollama, local vLLM, etc.
diff --git a/main.py b/main.py
index 824416e..e235b7a 100644
--- a/main.py
+++ b/main.py
@@ -80,10 +80,16 @@ TRANSPORT = os.environ.get("GRAFO_TRANSPORT", "stdio")
 import re as _re
 
 _LOG_SECRET_PATTERNS: list[tuple[_re.Pattern[str], str]] = [
-    (_re.compile(r'(Bearer\s+)[^\s"\',;)\]}]+', _re.IGNORECASE), r"\1[REDACTED]"),
-    (_re.compile(r"AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"), "[REDACTED]"),
-    (_re.compile(r"AIza[\w-]{10,}"), "[REDACTED]"),
-    (_re.compile(r"sk-[\w*-]{6,}"), "[REDACTED]"),
+    (
+        _re.compile(
+            r'(?<![A-Za-z0-9_])(Bearer\s+)(?!\[REDACTED\])(?=[^\s"\',;)\]}]*[0-9])[A-Za-z0-9._~+/=-]{8,}',
+            _re.IGNORECASE,
+        ),
+        r"\1[REDACTED]",
+    ),
+    (_re.compile(r"(?<![A-Za-z0-9_])AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"), "[REDACTED]"),
+    (_re.compile(r"(?<![A-Za-z0-9_])AIza[\w-]{10,}"), "[REDACTED]"),
+    (_re.compile(r"(?<![A-Za-z0-9_])sk-[\w*-]{6,}"), "[REDACTED]"),
     (_re.compile(r"\*{6,}\w{0,8}\."), "[REDACTED]"),
 ]
 
@@ -108,6 +114,10 @@ def redact_log_secrets(text: str) -> str:
 class _SecretRedactingLogRecord(logging.LogRecord):
     """LogRecord que garante redação em getMessage() e em exceções formatadas
     para qualquer Handler (incluindo StreamHandler e RichHandler do FastMCP).
+
+    Nota: possui efeito colateral em `exc.args` da exceção logada (muta `exc.args`
+    in-place aplicando `redact_log_secrets` apenas nas partes que casam com padrões
+    de segredos, preservando o texto ao redor idêntico).
     """
 
     def __init__(self, *args, **kwargs) -> None:
@@ -160,11 +170,14 @@ def setup_logging(level: str = "INFO") -> None:
     handler = logging.StreamHandler(sys.stderr)
     handler.setLevel(numeric_level)
     handler.setFormatter(formatter)
+    handler._grafo_log_handler = True  # type: ignore[attr-defined]
 
-    # Root logger (idempotent handler setup)
+    # Root logger (idempotent handler setup: remove only previous Grafo handlers)
     root = logging.getLogger()
     root.setLevel(numeric_level)
-    root.handlers.clear()
+    for existing_h in list(root.handlers):
+        if getattr(existing_h, "_grafo_log_handler", False):
+            root.removeHandler(existing_h)
     root.addHandler(handler)
 
     # Silence noisy third-party loggers
diff --git a/scratch/tools/scan_secrets.py b/scratch/tools/scan_secrets.py
index 32324f7..19d21a0 100644
--- a/scratch/tools/scan_secrets.py
+++ b/scratch/tools/scan_secrets.py
@@ -20,9 +20,16 @@ REPO_ROOT = Path(__file__).resolve().parent.parent.parent
 ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".log"}
 
 SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
-    ("AQ_KEY_FRAGMENT", re.compile(r"AQ\.[\w*-]{4,}")),
-    ("AIZA_KEY_FRAGMENT", re.compile(r"AIza[\w-]{10,}")),
-    ("SK_KEY_FRAGMENT", re.compile(r"sk-[\w*-]{6,}")),
+    (
+        "BEARER_TOKEN",
+        re.compile(
+            r'(?<![A-Za-z0-9_])Bearer\s+(?!\[REDACTED\])(?=[^\s"\',;)\]}]*[0-9])[A-Za-z0-9._~+/=-]{8,}',
+            re.IGNORECASE,
+        ),
+    ),
+    ("AQ_KEY_FRAGMENT", re.compile(r"(?<![A-Za-z0-9_])AQ\.[\w*-]{4,}(?:\w{0,8}\.)?")),
+    ("AIZA_KEY_FRAGMENT", re.compile(r"(?<![A-Za-z0-9_])AIza[\w-]{10,}")),
+    ("SK_KEY_FRAGMENT", re.compile(r"(?<![A-Za-z0-9_])sk-[\w*-]{6,}")),
     ("INCORRECT_API_KEY_MSG", re.compile(r"Incorrect API key provided")),
     ("MASKED_KEY_SUFFIX", re.compile(r"\*{6,}\w{0,8}\.")),
 ]
diff --git a/tests/test_env_example_provider.py b/tests/test_env_example_provider.py
new file mode 100644
index 0000000..d1d6e73
--- /dev/null
+++ b/tests/test_env_example_provider.py
@@ -0,0 +1,45 @@
+"""tests/test_env_example_provider.py
+
+Teste unitário para F4-023 (Item 2 da Rodada 4.2h-2):
+- .env.example NÃO deve trazer GRAFO_LLM_PROVIDER ativo (descomentado).
+- Deve conter a linha comentada `# GRAFO_LLM_PROVIDER=` e aviso explícito de que,
+  se o modelo não começar com "gemini-", o provedor deve ser definido explicitamente,
+  senão o LLM fica desativado.
+"""
+
+from __future__ import annotations
+
+import re
+from pathlib import Path
+
+REPO_ROOT = Path(__file__).resolve().parent.parent
+ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
+
+
+def test_env_example_does_not_define_active_llm_provider() -> None:
+    """F4-023: .env.example não traz GRAFO_LLM_PROVIDER ativo para não anular a regra de modelos gemini-*."""
+    assert ENV_EXAMPLE_PATH.is_file(), f".env.example não encontrado em {ENV_EXAMPLE_PATH}"
+    text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
+    lines = text.splitlines()
+
+    active_lines = [
+        (idx + 1, line)
+        for idx, line in enumerate(lines)
+        if re.match(r"^\s*GRAFO_LLM_PROVIDER\s*=", line)
+    ]
+    assert not active_lines, (
+        f".env.example contém GRAFO_LLM_PROVIDER ativo nas linhas: {active_lines}"
+    )
+
+    commented_lines = [
+        line
+        for line in lines
+        if re.match(r"^\s*#\s*GRAFO_LLM_PROVIDER\s*=", line)
+    ]
+    assert commented_lines, (
+        ".env.example deve manter # GRAFO_LLM_PROVIDER=... comentado como exemplo."
+    )
+    lower_text = text.lower()
+    assert "gemini-" in text and ("desativado" in lower_text or "disabled" in lower_text), (
+        ".env.example deve avisar que modelos que não começam com 'gemini-' exigem provedor explícito, senão o LLM fica desativado."
+    )
diff --git a/tests/test_llm_egress_guard.py b/tests/test_llm_egress_guard.py
index 3247409..297a374 100644
--- a/tests/test_llm_egress_guard.py
+++ b/tests/test_llm_egress_guard.py
@@ -256,6 +256,7 @@ def test_s1_orchestrator_skips_summarize_when_llm_disabled(
     llm_spy: dict[str, Any], tmp_path: Path, caplog: pytest.LogCaptureFixture
 ) -> None:
     """Quando is_enabled é False, o orquestrador pula SUMMARIZE com log INFO e mantém summary NULL."""
+    pytest.importorskip("chromadb")
     from storage.store import SqliteStore
     from storage.vector_store import ChromaVectorStore, EmbeddingTier
     from ingestion.orchestrator import IngestionManager
diff --git a/tests/test_secret_redaction.py b/tests/test_secret_redaction.py
index cfdf95b..961f446 100644
--- a/tests/test_secret_redaction.py
+++ b/tests/test_secret_redaction.py
@@ -138,7 +138,152 @@ def test_r5_setup_logging_installs_factory_and_is_idempotent() -> None:
     assert getattr(factory_after_second, "_grafo_secret_redacting", False) is True, (
         "A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True"
     )
-    assert len(logging.getLogger().handlers) == 1, (
-        f"Root logger deve ter exatamente 1 handler após chamadas repetidas, mas tem {len(logging.getLogger().handlers)}"
+    root_handlers = logging.getLogger().handlers
+    grafo_handlers = [h for h in root_handlers if getattr(h, "_grafo_log_handler", False)]
+    count_to_check = len(grafo_handlers) if grafo_handlers else len(root_handlers)
+    assert count_to_check == 1, (
+        f"Root logger deve ter exatamente 1 handler do Grafo após chamadas repetidas, mas tem {count_to_check}"
     )
 
+
+# ---------------------------------------------------------------------------
+# Rodada 4.2h-2 — Item 1 (F4-022): Falsos positivos, positivos e paridade
+# ---------------------------------------------------------------------------
+
+NEGATIVE_CASES_F4_022: list[str] = [
+    "risk-assessment-notes.md",
+    "disk-cache-manifest.json",
+    "task-scheduler-config.yaml",
+    "C:\\proj\\desk-setup-checklist.md",
+    "Crawl: 3 files",
+    "mask-values-list",
+]
+
+POSITIVE_CASES_F4_022: list[str] = [
+    "sk-" + "FAKEFAKEFAKE0001",
+    "sk-proj-" + "FAKE_KEY_XYZ123",
+    "key=sk-" + "FAKEFAKEFAKE0001",
+    "(sk-" + "FAKEFAKE0001)",
+    '"api_key": "sk-' + 'FAKEFAKE0001"',
+    "AQ." + "FAKEFAKEFAKE0001",
+    "AIza" + "FAKEFAKEFAKE00000001",
+    "Bearer " + "abc123token456",
+]
+
+
+@pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
+def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
+    """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
+    main_mod.setup_logging("INFO")
+    assert main_mod.redact_log_secrets(neg_text) == neg_text
+
+    lg, buf, rh = _make_isolated_logger()
+    lg.info("Processando item: %s", neg_text)
+    assert f"Processando item: {neg_text}" in buf.getvalue()
+    assert "[REDACTED]" not in buf.getvalue()
+    assert f"Processando item: {neg_text}" in "\n".join(rh.rendered)
+
+
+@pytest.mark.parametrize("pos_text", POSITIVE_CASES_F4_022)
+def test_f4_022_positive_cases_are_redacted(pos_text: str) -> None:
+    """Item 1a (Positivos): chaves isoladas ou precedidas por pontuação/aspas são redigidas."""
+    main_mod.setup_logging("INFO")
+    redacted = main_mod.redact_log_secrets(pos_text)
+    assert redacted != pos_text, f"Esperava redação para entrada positiva, mas saiu intacta: {redacted!r}"
+    assert "[REDACTED]" in redacted
+
+
+def test_f4_022_filter_and_scanner_parity() -> None:
+    """Item 1c: O filtro de logs (main.py) e o scanner (scan_secrets.py) dão o mesmo resultado
+    sobre todos os casos positivos e negativos de F4-022.
+    """
+    import importlib.util
+    from pathlib import Path
+
+    scanner_path = Path(__file__).resolve().parent.parent / "scratch" / "tools" / "scan_secrets.py"
+    spec = importlib.util.spec_from_file_location("scan_secrets_mod", scanner_path)
+    assert spec is not None and spec.loader is not None
+    scanner_mod = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(scanner_mod)
+
+    def scanner_matches(text: str) -> bool:
+        return any(regex.search(text) is not None for _, regex in scanner_mod.SECRET_PATTERNS)
+
+    def filter_redacts(text: str) -> bool:
+        return main_mod.redact_log_secrets(text) != text
+
+    for neg in NEGATIVE_CASES_F4_022:
+        f_res = filter_redacts(neg)
+        s_res = scanner_matches(neg)
+        assert f_res == s_res == False, (  # noqa: E712
+            f"Divergência ou falso positivo em caso negativo {neg!r}: filter={f_res}, scanner={s_res}"
+        )
+
+    for pos in POSITIVE_CASES_F4_022:
+        f_res = filter_redacts(pos)
+        s_res = scanner_matches(pos)
+        assert f_res == s_res == True, (  # noqa: E712
+            f"Divergência ou falso negativo em caso positivo: filter={f_res}, scanner={s_res}"
+        )
+
+
+# ---------------------------------------------------------------------------
+# Rodada 4.2h-2 — Item 4a e 4b: Preservação de handlers alheios e R6 (exc.args)
+# ---------------------------------------------------------------------------
+
+def test_item4a_setup_logging_preserves_foreign_root_handlers() -> None:
+    """Item 4a: um handler alheio já presente no root logger NÃO é removido por setup_logging;
+    chamar setup_logging duas vezes deixa exatamente um handler do Grafo.
+    """
+    root = logging.getLogger()
+    foreign_buf = io.StringIO()
+    foreign_handler = logging.StreamHandler(foreign_buf)
+    root.addHandler(foreign_handler)
+    try:
+        main_mod.setup_logging("INFO")
+        main_mod.setup_logging("INFO")
+
+        assert foreign_handler in root.handlers, (
+            "Handler alheio presente no root logger foi removido por setup_logging!"
+        )
+        grafo_handlers = [
+            h for h in root.handlers if getattr(h, "_grafo_log_handler", False) is True
+        ]
+        assert len(grafo_handlers) == 1, (
+            f"Esperado exatamente 1 handler do Grafo após duas chamadas a setup_logging, "
+            f"mas encontrou {len(grafo_handlers)}"
+        )
+    finally:
+        if foreign_handler in root.handlers:
+            root.removeHandler(foreign_handler)
+
+
+def test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text() -> None:
+    """Item 4b (R6): docstring de _SecretRedactingLogRecord documenta o efeito colateral em exc.args,
+    e apenas o trecho que casa com padrão de segredo muda em exc.args, preservando o restante.
+    """
+    doc = main_mod._SecretRedactingLogRecord.__doc__ or ""
+    assert "exc.args" in doc and "efeito colateral" in doc.lower(), (
+        "Docstring de _SecretRedactingLogRecord deve documentar explicitamente o efeito colateral em exc.args"
+    )
+
+    main_mod.setup_logging("INFO")
+    lg, buf, _ = _make_isolated_logger()
+
+    prefix = "Falha ao autenticar no arquivo risk-assessment-notes.md com chave "
+    suffix = " durante etapa de ingestão (código=401)."
+    captured_exc: RuntimeError | None = None
+
+    try:
+        raise RuntimeError(prefix + FAKE_SK + suffix)
+    except RuntimeError as exc:
+        captured_exc = exc
+        lg.exception("Erro capturado no teste R6")
+
+    assert captured_exc is not None
+    assert captured_exc.args == (prefix + "[REDACTED]" + suffix,), (
+        f"Apenas o segredo deveria mudar em exc.args, mas obteve: {captured_exc.args!r}"
+    )
+    assert (prefix + "[REDACTED]" + suffix) in buf.getvalue()
+
+
```

---

## 6. VERDE, 4 MUTAÇÕES, `boot_check.py` E HARNESS F4-017

### 6.1 Quatro Mutações Obrigatórias (Cada Uma Falha Pelo Motivo Certo e Foi Revertida)

#### Mutação (i): Remover o lookbehind de `"sk-"` em `main.py` $\to$ Testes negativos do Item 1 falham
#### `scratch/evidencia_4_2h2/mut1_remove_sk_lookbehind.txt`
```text
FFFF.F                                                                   [100%]
================================== FAILURES ===================================
____ test_f4_022_negative_cases_remain_identical[risk-assessment-notes.md] ____

neg_text = 'risk-assessment-notes.md'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem id�nticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ri[REDACTED].md' == 'risk-assessment-notes.md'
E         
E         - risk-assessment-notes.md
E         + ri[REDACTED].md

tests\test_secret_redaction.py:178: AssertionError
____ test_f4_022_negative_cases_remain_identical[disk-cache-manifest.json] ____

neg_text = 'disk-cache-manifest.json'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem id�nticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'di[REDACTED].json' == 'disk-cache-manifest.json'
E         
E         - disk-cache-manifest.json
E         + di[REDACTED].json

tests\test_secret_redaction.py:178: AssertionError
___ test_f4_022_negative_cases_remain_identical[task-scheduler-config.yaml] ___

neg_text = 'task-scheduler-config.yaml'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem id�nticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ta[REDACTED].yaml' == 'task-scheduler-config.yaml'
E         
E         - task-scheduler-config.yaml
E         + ta[REDACTED].yaml

tests\test_secret_redaction.py:178: AssertionError
_ test_f4_022_negative_cases_remain_identical[C:\\proj\\desk-setup-checklist.md] _

neg_text = 'C:\\proj\\desk-setup-checklist.md'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem id�nticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'C:\\proj\\de[REDACTED].md' == 'C:\\proj\\de...-checklist.md'
E         
E         - C:\proj\desk-setup-checklist.md
E         + C:\proj\de[REDACTED].md

tests\test_secret_redaction.py:178: AssertionError
________ test_f4_022_negative_cases_remain_identical[mask-values-list] ________

neg_text = 'mask-values-list'

    @pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
    def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
        """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem id�nticos."""
        main_mod.setup_logging("INFO")
>       assert main_mod.redact_log_secrets(neg_text) == neg_text
E       AssertionError: assert 'ma[REDACTED]' == 'mask-values-list'
E         
E         - mask-values-list
E         + ma[REDACTED]

tests\test_secret_redaction.py:178: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[risk-assessment-notes.md]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[disk-cache-manifest.json]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[task-scheduler-config.yaml]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[C:\\proj\\desk-setup-checklist.md]
FAILED tests/test_secret_redaction.py::test_f4_022_negative_cases_remain_identical[mask-values-list]
5 failed, 1 passed, 16 deselected in 0.42s
```

#### Mutação (ii): Aplicar a correção só no filtro, não no scanner $\to$ Teste de paridade falha
#### `scratch/evidencia_4_2h2/mut2_scanner_divergence_parity.txt`
```text
F                                                                        [100%]
================================== FAILURES ===================================
____________________ test_f4_022_filter_and_scanner_parity ____________________

    def test_f4_022_filter_and_scanner_parity() -> None:
        """Item 1c: O filtro de logs (main.py) e o scanner (scan_secrets.py) d�o o mesmo resultado
        sobre todos os casos positivos e negativos de F4-022.
        """
        import importlib.util
        from pathlib import Path
    
        scanner_path = Path(__file__).resolve().parent.parent / "scratch" / "tools" / "scan_secrets.py"
        spec = importlib.util.spec_from_file_location("scan_secrets_mod", scanner_path)
        assert spec is not None and spec.loader is not None
        scanner_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner_mod)
    
        def scanner_matches(text: str) -> bool:
            return any(regex.search(text) is not None for _, regex in scanner_mod.SECRET_PATTERNS)
    
        def filter_redacts(text: str) -> bool:
            return main_mod.redact_log_secrets(text) != text
    
        for neg in NEGATIVE_CASES_F4_022:
            f_res = filter_redacts(neg)
            s_res = scanner_matches(neg)
>           assert f_res == s_res == False, (  # noqa: E712
                f"Diverg�ncia ou falso positivo em caso negativo {neg!r}: filter={f_res}, scanner={s_res}"
            )
E           AssertionError: Diverg�ncia ou falso positivo em caso negativo 'risk-assessment-notes.md': filter=False, scanner=True
E           assert False == True

tests\test_secret_redaction.py:218: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_f4_022_filter_and_scanner_parity
1 failed, 21 deselected in 0.35s
```

#### Mutação (iii): Restaurar `root.handlers.clear()` em `main.py` $\to$ Teste do Item 4a falha
#### `scratch/evidencia_4_2h2/mut3_restore_handlers_clear.txt`
```text
F                                                                        [100%]
================================== FAILURES ===================================
__________ test_item4a_setup_logging_preserves_foreign_root_handlers __________

    def test_item4a_setup_logging_preserves_foreign_root_handlers() -> None:
        """Item 4a: um handler alheio j� presente no root logger N�O � removido por setup_logging;
        chamar setup_logging duas vezes deixa exatamente um handler do Grafo.
        """
        root = logging.getLogger()
        foreign_buf = io.StringIO()
        foreign_handler = logging.StreamHandler(foreign_buf)
        root.addHandler(foreign_handler)
        try:
            main_mod.setup_logging("INFO")
            main_mod.setup_logging("INFO")
    
>           assert foreign_handler in root.handlers, (
                "Handler alheio presente no root logger foi removido por setup_logging!"
            )
E           AssertionError: Handler alheio presente no root logger foi removido por setup_logging!
E           assert <StreamHandler (NOTSET)> in [<StreamHandler <_TemporaryFileWrapper file=<_io.FileIO name='C:\\Users\\guial\\AppData\\Local\\Temp\\tmpa9suposo' mode='rb+' closefd=True>> (INFO)>]
E            +  where [<StreamHandler <_TemporaryFileWrapper file=<_io.FileIO name='C:\\Users\\guial\\AppData\\Local\\Temp\\tmpa9suposo' mode='rb+' closefd=True>> (INFO)>] = <RootLogger root (INFO)>.handlers

tests\test_secret_redaction.py:246: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_item4a_setup_logging_preserves_foreign_root_handlers
1 failed, 21 deselected in 0.37s
```

#### Mutação (iv): Descomentar `GRAFO_LLM_PROVIDER=gemini` em `.env.example` $\to$ Teste do Item 2 falha
#### `scratch/evidencia_4_2h2/mut4_uncomment_env_example_provider.txt`
```text
F                                                                        [100%]
================================== FAILURES ===================================
____________ test_env_example_does_not_define_active_llm_provider _____________

    def test_env_example_does_not_define_active_llm_provider() -> None:
        """F4-023: .env.example n�o traz GRAFO_LLM_PROVIDER ativo para n�o anular a regra de modelos gemini-*."""
        assert ENV_EXAMPLE_PATH.is_file(), f".env.example n�o encontrado em {ENV_EXAMPLE_PATH}"
        text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
        lines = text.splitlines()
    
        active_lines = [
            (idx + 1, line)
            for idx, line in enumerate(lines)
            if re.match(r"^\s*GRAFO_LLM_PROVIDER\s*=", line)
        ]
>       assert not active_lines, (
            f".env.example cont�m GRAFO_LLM_PROVIDER ativo nas linhas: {active_lines}"
        )
E       AssertionError: .env.example cont�m GRAFO_LLM_PROVIDER ativo nas linhas: [(24, 'GRAFO_LLM_PROVIDER=gemini')]
E       assert not [(24, 'GRAFO_LLM_PROVIDER=gemini')]

tests\test_env_example_provider.py:30: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_env_example_provider.py::test_env_example_does_not_define_active_llm_provider
1 failed in 0.29s
```

### 6.2 Suíte Completa (`pytest tests/ -q`) no Código Corrigido
#### `scratch/evidencia_4_2h2/full_pytest_green.txt`
```text
.................................................................s...... [ 17%]
........................................................................ [ 35%]
........................................................................ [ 53%]
......................................................F................. [ 71%]
........................................................................ [ 88%]
.............................................                            [100%]
================================== FAILURES ===================================
____ TestProgressiveToolDisclosure.test_telemetry_api_mcp_state_endpoints _____

self = <test_progressive_tool_disclosure.TestProgressiveToolDisclosure testMethod=test_telemetry_api_mcp_state_endpoints>

    def test_telemetry_api_mcp_state_endpoints(self):
        """Valida os endpoints REST /api/mcp/state (POST) e /api/mcp/state/{session_id} (GET)"""
        session_id = "sess_fsm_control"
    
        # 1. Consulta estado default inicial (PLANNING)
        resp_get_default = self.client.get(f"/api/mcp/state/{session_id}")
        self.assertEqual(resp_get_default.status_code, 200)
>       self.assertEqual(resp_get_default.json()["active_state"], "PLANNING")
E       AssertionError: 'EXECUTION' != 'PLANNING'
E       - EXECUTION
E       + PLANNING

tests\test_progressive_tool_disclosure.py:90: AssertionError
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1025 HTTP Request: GET http://testserver/api/mcp/state/sess_fsm_control "HTTP/1.1 200 OK"
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_success
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_returns_files_processed
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_signals_janitor
tests/test_mcp_server_handlers.py::TestHandleMine::test_mine_alias_resolution
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:341: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 403 passed, 1 skipped, 20 warnings in 95.17s (0:01:35)
```

### 6.3 `scratch/boot_check.py` com `mcp 1.27.0` (`venv_mcp127`) e `mcp 1.30.0` (`venv_mcp130_full`), $n=1$ cada
#### `scratch/evidencia_4_2h2/boot_check_127.txt`
```text
======================================================================
BOOT CHECK — Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.27.0
Entrypoint Mode:    python-main
Timeout:            180.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_chroma
======================================================================
Executando comando: C:\Nexus-Memory\_venvs_4_2e\venv_mcp127\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.27.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.002
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │ Decoupled sys.stdin from fd 0 (allocated duplicate fd=4)
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   Grafo Concierge v3.8.0 — Absolute Solidity
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   DB:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_concierge.db
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   ChromaDB: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_chroma (test_boot_collection)
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   Embedding: all-MiniLM-L6-v2
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   LLM:      none
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   Janitor:  300s
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   Transport: stdio
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │   Log Level: INFO
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:53 │ INFO    │ grafo-concierge.main         │ Initializing SqliteStore: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_concierge.db
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.schema       │ Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.store        │ Schema v3.8.0 verified - all tables and triggers OK.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.connection   │ SerializedWriteQueue started successfully (db: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_concierge.db)
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.store        │ SqliteStore initialized: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_concierge.db
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing EmbeddingManager: tier=FLASH
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.vector-store │ EmbeddingManager initialized: tier=flash, model=all-MiniLM-L6-v2, dims=384
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing ChromaVectorStore: path=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_chroma, collection=test_boot_collection
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.vector-store │ ChromaVectorStore initialized: dir=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_njjkcyzo\test_chroma, collection=test_boot_collection, tier=flash
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing ZoomSummarizer: model=none
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.summarizer   │ LLMAdapter inicializado: model=none, provider=disabled, enabled=False, custom_fn=False
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing IngestionManager
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.crawler      │ ProjectCrawler initialized: 22 active ignore patterns.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.orchestrator │ IngestionManager inicializado: summarizer=ON, embedder_tier=flash
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing JanitorService: interval=300s
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.janitor      │ JanitorService initialized: stale=30d, zoom_threshold=10, inactive=60d, super_node_threshold=10
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConcierge Central Facade
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.middleware   │ GrafoConcierge (Facade) initialized successfully.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConciergeServer
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.mcp          │ GrafoConciergeServer initialized — 31 tools registered.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Bootstrap complete — all components initialized.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Starting MCP server (transport=stdio)...
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.mcp          │ Starting Grafo Concierge MCP Server (transport=stdio)...
2026-11-01 12:50:55 │ INFO    │ mcp.server.lowlevel.server   │ Processing request of type ListToolsRequest
2026-11-01 12:50:55 │ INFO    │ mcp.server.lowlevel.server   │ Processing request of type CallToolRequest
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.mcp          │ concierge_status OK
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Graceful shutdown initiated...
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ Janitor encerrado.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.connection   │ Requesting stop of SerializedWriteQueue...
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.connection   │ SerializedWriteQueue finished.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.store        │ SqliteStore closed.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ SqliteStore encerrado.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │   Grafo Concierge encerrado com sucesso.
2026-11-01 12:50:55 │ INFO    │ grafo-concierge.main         │ ============================================================
```
#### `scratch/evidencia_4_2h2/boot_check_130.txt`
```text
======================================================================
BOOT CHECK — Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.30.0
Entrypoint Mode:    python-main
Timeout:            180.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_chroma
======================================================================
Executando comando: C:\Nexus-Memory\_venvs_4_2g\venv_mcp130_full\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.30.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.001
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │ Decoupled sys.stdin from fd 0 (allocated duplicate fd=4)
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   Grafo Concierge v3.8.0 — Absolute Solidity
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   DB:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_concierge.db
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   ChromaDB: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_chroma (test_boot_collection)
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   Embedding: all-MiniLM-L6-v2
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   LLM:      none
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   Janitor:  300s
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   Transport: stdio
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │   Log Level: INFO
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:50:58 │ INFO    │ grafo-concierge.main         │ Initializing SqliteStore: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_concierge.db
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.schema       │ Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.store        │ Schema v3.8.0 verified - all tables and triggers OK.
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.connection   │ SerializedWriteQueue started successfully (db: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_concierge.db)
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.store        │ SqliteStore initialized: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_concierge.db
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.main         │ Initializing EmbeddingManager: tier=FLASH
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.vector-store │ EmbeddingManager initialized: tier=flash, model=all-MiniLM-L6-v2, dims=384
2026-11-01 12:51:00 │ INFO    │ grafo-concierge.main         │ Initializing ChromaVectorStore: path=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_chroma, collection=test_boot_collection
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.vector-store │ ChromaVectorStore initialized: dir=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_c6msqhx1\test_chroma, collection=test_boot_collection, tier=flash
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Initializing ZoomSummarizer: model=none
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.summarizer   │ LLMAdapter inicializado: model=none, provider=disabled, enabled=False, custom_fn=False
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Initializing IngestionManager
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.crawler      │ ProjectCrawler initialized: 22 active ignore patterns.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.orchestrator │ IngestionManager inicializado: summarizer=ON, embedder_tier=flash
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Initializing JanitorService: interval=300s
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.janitor      │ JanitorService initialized: stale=30d, zoom_threshold=10, inactive=60d, super_node_threshold=10
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConcierge Central Facade
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.middleware   │ GrafoConcierge (Facade) initialized successfully.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConciergeServer
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.mcp          │ GrafoConciergeServer initialized — 31 tools registered.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Bootstrap complete — all components initialized.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Janitor in idle mode (no GRAFO_JANITOR_PROJECT defined).
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Starting MCP server (transport=stdio)...
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.mcp          │ Starting Grafo Concierge MCP Server (transport=stdio)...
2026-11-01 12:51:01 │ INFO    │ mcp.server.lowlevel.server   │ Processing request of type ListToolsRequest
2026-11-01 12:51:01 │ INFO    │ mcp.server.lowlevel.server   │ Processing request of type CallToolRequest
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.mcp          │ concierge_status OK
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Graceful shutdown initiated...
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ Janitor encerrado.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.connection   │ Requesting stop of SerializedWriteQueue...
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.connection   │ SerializedWriteQueue finished.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.store        │ SqliteStore closed.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ SqliteStore encerrado.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │   Grafo Concierge encerrado com sucesso.
2026-11-01 12:51:01 │ INFO    │ grafo-concierge.main         │ ============================================================
```

### 6.4 Harness de Regressão F4-017 (`search-first` e `mine`, $n=3$ por cenário, sequenciais, `GRAFO_LLM_MODEL=none`) em `venv_mcp127` e `venv_mcp130_full`
#### `scratch/evidencia_4_2h2/p6_f4_017_regression.txt`
```text
=== PASSO 6B: HARNESS F4-017 EM venv_mcp127 E venv_mcp130_full (GRAFO_LLM_MODEL=none) ===
Commit: 77eec6f

Venv             | MCP    | Cenário      | Rep | Classe   | t_init | t_crit | t_sec | Vecs | NO-OP | LoopCl | TaskEx | ERR | WARN
---------------------------------------------------------------------------------------------------------------------------------
venv_mcp127      | 1.27.0 | search-first | 1   | OK       | 4.03   | 19.02  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | search-first | 2   | OK       | 3.25   | 14.78  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | search-first | 3   | OK       | 2.8    | 13.83  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 1   | OK       | 2.7    | 13.98  | 0.03  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 2   | OK       | 2.79   | 14.26  | 0.03  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 3   | OK       | 3.1    | 15.61  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 1   | OK       | 2.73   | 11.61  | 0.01  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 2   | OK       | 2.45   | 11.5   | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 3   | OK       | 2.58   | 11.61  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 1   | OK       | 2.66   | 12.24  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 2   | OK       | 2.69   | 12.0   | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 3   | OK       | 2.59   | 12.03  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
---------------------------------------------------------------------------------------------------------------------------------
Resumo Geral: OK=12/12 | TRAVOU=0/12

=== DETALHAMENTO DE ERROR / WARNING POR EXECUÇÃO ===
[venv_mcp127 | search-first | rep=1] ERROR(0)={} | WARNING(0)={}
[venv_mcp127 | search-first | rep=2] ERROR(0)={} | WARNING(0)={}
[venv_mcp127 | search-first | rep=3] ERROR(0)={} | WARNING(0)={}
[venv_mcp127 | mine | rep=1] ERROR(0)={} | WARNING(0)={}
[venv_mcp127 | mine | rep=2] ERROR(0)={} | WARNING(0)={}
[venv_mcp127 | mine | rep=3] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | search-first | rep=1] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | search-first | rep=2] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | search-first | rep=3] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | mine | rep=1] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | mine | rep=2] ERROR(0)={} | WARNING(0)={}
[venv_mcp130_full | mine | rep=3] ERROR(0)={} | WARNING(0)={}
```

---

## 7. VERIFICAÇÃO FINAL DE SEGREDOS E DECLARAÇÃO DO QUE NÃO FOI VERIFICADO

### 7.1 Execução Final do Scanner `scratch/tools/scan_secrets.py` (Regra 13)
#### `scratch/evidencia_4_2h2/final_scan_secrets.txt`
```text
scanned_files=1039
files_with_findings=0
total_pattern_hits=0
```

### 7.2 Lista Explícita do que NÃO Foi Verificado (Regra 12)
1. **Outras máquinas e sistemas operacionais:** **NÃO VERIFICADO** localmente pelo executor nesta rodada (toda a execução do executor ocorreu nesta máquina Windows; o auditor independente verificou S1–S7 e mutações da 4.2h em Linux).
2. **Chamadas de rede reais contra provedores de LLM com chaves reais:** **NÃO VERIFICADO** (proibido pela regra dura de segredos; todos os subprocessos usaram `GRAFO_LLM_API_KEY` falsa explícita e `GRAFO_LLM_MODEL=none`).
3. **Reprodução E2E de `F4-020` via Tripwire Proxy HTTP CONNECT:** **NÃO VERIFICADO via proxy CONNECT** (conforme documentado em `audits/errata-4-2h.md`, o proxy recusa `CONNECT` com `403` antes de existir transporte TLS/HTTP ativo; `F4-020` é provado pelos testes `S6` e `S7` com servidor HTTP local `401`).
