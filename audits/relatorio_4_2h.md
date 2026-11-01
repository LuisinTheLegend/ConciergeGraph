# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2h
## SEGURANÇA DO ADAPTADOR DE LLM (F4-019, F4-020, F4-021)

> **Data de Emissão:** 2026-11-01 11:57:54
> **Regras Aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos gerados por redirecionamento; relatório gerado por script), 13 (Scanner de segredos e chaves falsas em testes).
> **Escopo Tocado:** `ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py`, `interface/cli.py`, `.env.example`, `AUDIT_PROTOCOL.md`, `tests/test_llm_egress_guard.py`, `tests/test_no_secrets_in_tracked_files.py`, `tests/test_secret_redaction.py`, `scratch/tools/scan_secrets.py`, `scratch/evidencia_4_2h/`, e `audits/`. Zero alteração em `storage/`, esquema/FTS (`F4-018`), dependências, `data/` ou `README`.

---

## 1. PASSO 0 — BASELINE

### 1.1 Sincronização Git (`git pull`, `git rev-parse HEAD`, `git ls-remote origin main`)
#### `scratch/evidencia_4_2h/p0_git_pull.txt`
```text
Already up to date.
```
#### `scratch/evidencia_4_2h/p0_head.txt`
```text
96ba4d054ad687a4b45e88ba7fde46e1f8fec7fc
```
#### `scratch/evidencia_4_2h/p0_ls_remote.txt`
```text
96ba4d054ad687a4b45e88ba7fde46e1f8fec7fc	refs/heads/main
```

### 1.2 Suíte Completa no Baseline (`pytest tests/ -q`)
#### `scratch/evidencia_4_2h/p0_pytest.txt`
```text
.................................................................s...... [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
......................................F................................. [ 78%]
........................................................................ [ 98%]
.......                                                                  [100%]
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
1 failed, 365 passed, 1 skipped, 20 warnings in 179.76s (0:02:59)
```

---

## 2. PASSO 1 — MAPEAMENTO (SOMENTE LEITURA)

### 2.1 Saída de `git grep` em Código de Produção (`p1_mapeamento.txt` e `p1_mapeamento_extra.txt`)
#### `scratch/evidencia_4_2h/p1_mapeamento.txt`
```text
agents/revisor_critico.py:33:    - Reuses ingestion.summarizer.LLMAdapter for LLM calls
agents/revisor_critico.py:47:from ingestion.summarizer import LLMAdapter
agents/revisor_critico.py:180:        llm_adapter: Optional[LLMAdapter] = None,
core/memory_extractor.py:56:            llm_adapter: LLM adaptation object (e.g. LLMAdapter or equivalent mock).
ingestion/summarizer.py:137:# LLMAdapter — interface for LLM calls (Model Tiering)
ingestion/summarizer.py:140:class LLMAdapter:
ingestion/summarizer.py:164:        logger.info("LLMAdapter inicializado: model=%s, custom_fn=%s", model_name, call_fn is not None)
ingestion/summarizer.py:186:            client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
ingestion/summarizer.py:202:                model = legacy_genai.GenerativeModel(self._model_name)
ingestion/summarizer.py:228:                client = openai.OpenAI(
ingestion/summarizer.py:233:                client = openai.OpenAI(api_key=self._api_key)
ingestion/summarizer.py:258:            - OpenAI / compatible providers: uses native openai.AsyncOpenAI.
ingestion/summarizer.py:283:                client = openai.AsyncOpenAI(
ingestion/summarizer.py:288:                client = openai.AsyncOpenAI(api_key=self._api_key)
ingestion/summarizer.py:328:        llm_adapter: LLMAdapter,
interface/cli.py:56:    from ingestion.summarizer import LLMAdapter
interface/cli.py:73:    llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
interface/cli.py:80:    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
interface/cli.py:100:    llm_adapter = LLMAdapter(
main.py:21:    GRAFO_LLM_API_KEY     → LLM API Key (optional)
main.py:62:LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")
main.py:166:    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
main.py:192:    from ingestion.summarizer import LLMAdapter
main.py:194:    llm_adapter = LLMAdapter(
storage/vector_store.py:89:        tier: EmbeddingTier.FLASH or EmbeddingTier.ELITE.
storage/vector_store.py:90:        openai_api_key: OpenAI API key (required for tier ELITE).
storage/vector_store.py:100:        EmbeddingTier.ELITE: {
storage/vector_store.py:110:        openai_api_key: Optional[str] = None,
storage/vector_store.py:116:        self._openai_key = openai_api_key
storage/vector_store.py:169:            elif self._tier == EmbeddingTier.ELITE:
storage/vector_store.py:172:                        "openai_api_key is required for the ELITE tier."
storage/vector_store.py:176:                    self._model = openai.OpenAI(api_key=self._openai_key)
storage/vector_store.py:205:            elif self._tier == EmbeddingTier.ELITE:
storage/vector_store.py:248:        elif self._tier == EmbeddingTier.ELITE:
storage/vector_store.py:293:        self._embedding_mgr = embedding_manager or EmbeddingManager()
```
#### `scratch/evidencia_4_2h/p1_mapeamento_extra.txt`
```text
agents/revisor_critico.py:183:        self._llm = llm_adapter
agents/revisor_critico.py:224:        if self._llm is not None:
agents/revisor_critico.py:225:            return self._llm_audit(draft)
agents/revisor_critico.py:270:    def _llm_audit(self, draft: dict) -> AuditResult:
agents/revisor_critico.py:286:            raw_response = self._llm.generate(prompt, max_tokens=300)
agents/revisor_critico.py:413:        if self._llm is not None:
agents/revisor_critico.py:414:            reranked = self._llm_rerank(top_candidates, task_context)
agents/revisor_critico.py:451:    def _llm_rerank(self, candidates: list[dict], task_context: str) -> list[dict]:
agents/revisor_critico.py:479:            raw_response = self._llm.generate(prompt, max_tokens=400)
core/delta_manager.py:161:        self, community_id: str, cloud_llm_mock_callback
core/delta_manager.py:188:        new_summary = cloud_llm_mock_callback(payload)
ingestion/orchestrator.py:400:        from accessing self._ingestion._summarizer._llm directly (violation of Law of Demeter).
ingestion/orchestrator.py:409:        if not self._summarizer or not hasattr(self._summarizer, "_llm") or not self._summarizer._llm:
ingestion/orchestrator.py:421:            raw = self._summarizer._llm.generate(prompt, max_tokens=300)
ingestion/summarizer.py:201:                    legacy_genai.configure(api_key=self._api_key)
ingestion/summarizer.py:331:        self._llm = llm_adapter
ingestion/summarizer.py:350:                raw_response = self._llm.generate(prompt, max_tokens=MAX_L0_TOKENS)
ingestion/summarizer.py:367:                        model_used=self._llm.model_name,
ingestion/summarizer.py:435:                raw_response = await self._llm.generate_async(prompt, max_tokens=MAX_L0_TOKENS)
ingestion/summarizer.py:452:                        model_used=self._llm.model_name,
ingestion/summarizer.py:531:                raw_response = self._llm.generate(prompt, max_tokens=estimated_response_tokens)
ingestion/summarizer.py:570:                            model_used=self._llm.model_name,
ingestion/summarizer.py:622:                raw_response = self._llm.generate(prompt, max_tokens=MAX_L1_TOKENS)
ingestion/summarizer.py:637:                        model_used=self._llm.model_name,
ingestion/summarizer.py:730:                raw_response = self._llm.generate(prompt, max_tokens=MAX_L2_TOKENS)
ingestion/summarizer.py:745:                        model_used=self._llm.model_name,
interface/action_hooks.py:60:            "LLM" if revisor and revisor._llm else "heuristic",
interface/cli.py:72:    llm_model = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
interface/cli.py:73:    llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
interface/cli.py:74:    llm_base_url = os.environ.get("GRAFO_LLM_BASE_URL", "")
main.py:20:    GRAFO_LLM_MODEL       → LLM model for summarization (default: gemini-2.0-flash)
main.py:21:    GRAFO_LLM_API_KEY     → LLM API Key (optional)
main.py:61:LLM_MODEL = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
main.py:62:LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")
main.py:63:LLM_BASE_URL = os.environ.get("GRAFO_LLM_BASE_URL", "")
```

### 2.2 Pontos de Criação de Cliente LLM / Envio de `GRAFO_LLM_API_KEY` e Verificação de `storage/vector_store.py`
1. **`ingestion/summarizer.py` (`LLMAdapter.generate` e `LLMAdapter.generate_async`):** Único módulo de produção que instancia clientes de LLM (`google.genai.Client`, `google.generativeai`, `openai.OpenAI` e `openai.AsyncOpenAI`).
2. **`main.py` (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_PROVIDER` -> `ZoomSummarizer` em `bootstrap()`):** Lê variáveis de ambiente e repassa ao `ZoomSummarizer`, que instancia `LLMAdapter`.
3. **`interface/cli.py` (`cmd_mine`):** Lê `GRAFO_LLM_API_KEY`, `GRAFO_LLM_MODEL`, `GRAFO_LLM_BASE_URL` e `GRAFO_LLM_PROVIDER` e instancia `ZoomSummarizer`.
4. **Resposta sobre `storage/vector_store.py` (tier `ELITE`, `openai_api_key`):** Conforme provado em `p1_mapeamento_extra.txt`, `EmbeddingManager` em `storage/vector_store.py` possui suporte dormente a `EmbeddingTier.ELITE` (`openai_api_key`), mas todos os pontos do código de produção (`main.py:168`, `interface/cli.py:92`, `storage/vector_store.py:128,452`) instanciam `EmbeddingManager(tier=EmbeddingTier.FLASH)` sem nunca passar `openai_api_key` nem `GRAFO_LLM_API_KEY`. Nenhuma linha de `storage/vector_store.py` foi tocada (conforme restrição de escopo).

---

## 3. PASSOS 2 E 3 — F4-019 E F4-020 (TESTES VERMELHOS S1–S8, IMPLEMENTAÇÃO E VERDE)

### 3.1 Passo 2 — Testes Vermelhos no Código Anterior (`96ba4d0`)
#### `scratch/evidencia_4_2h/p2_red_egress_guard.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 14 items

tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] FAILED [  7%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] FAILED [ 14%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] FAILED [ 21%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] FAILED [ 28%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] FAILED [ 35%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled FAILED [ 42%]
tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai FAILED [ 50%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai FAILED [ 57%]
tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled FAILED [ 64%]
tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client PASSED [ 71%]
tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved PASSED [ 78%]
tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception FAILED [ 85%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks FAILED [ 92%]
tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged PASSED [100%]

================================== FAILURES ===================================
__________________ test_s1_disabled_models_zero_egress[none] __________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'none'

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(llm_spy: dict[str, Any], disabled_model: str) -> None:
        adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
>       assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
E       AssertionError: LLMAdapter com model_name='none' deve ter is_enabled=False
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x00000170434D8980>, 'is_enabled', None)

tests\test_llm_egress_guard.py:222: AssertionError
__________________ test_s1_disabled_models_zero_egress[NONE] __________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'NONE'

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(llm_spy: dict[str, Any], disabled_model: str) -> None:
        adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
>       assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
E       AssertionError: LLMAdapter com model_name='NONE' deve ter is_enabled=False
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x0000017042A8C410>, 'is_enabled', None)

tests\test_llm_egress_guard.py:222: AssertionError
____________________ test_s1_disabled_models_zero_egress[] ____________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = ''

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(llm_spy: dict[str, Any], disabled_model: str) -> None:
        adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
>       assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
E       AssertionError: LLMAdapter com model_name='' deve ter is_enabled=False
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x0000017042A8C7D0>, 'is_enabled', None)

tests\test_llm_egress_guard.py:222: AssertionError
__________________ test_s1_disabled_models_zero_egress[off] ___________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'off'

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(llm_spy: dict[str, Any], disabled_model: str) -> None:
        adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
>       assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
E       AssertionError: LLMAdapter com model_name='off' deve ter is_enabled=False
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x00000170433C9220>, 'is_enabled', None)

tests\test_llm_egress_guard.py:222: AssertionError
________________ test_s1_disabled_models_zero_egress[disabled] ________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'disabled'

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(llm_spy: dict[str, Any], disabled_model: str) -> None:
        adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
>       assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
E       AssertionError: LLMAdapter com model_name='disabled' deve ter is_enabled=False
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x00000170433C9A70>, 'is_enabled', None)

tests\test_llm_egress_guard.py:222: AssertionError
___________ test_s1_orchestrator_skips_summarize_when_llm_disabled ____________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-70/test_s1_orchestrator_skips_sum0')
caplog = <_pytest.logging.LogCaptureFixture object at 0x00000170434D9400>

    def test_s1_orchestrator_skips_summarize_when_llm_disabled(
        llm_spy: dict[str, Any], tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Quando is_enabled é False, o orquestrador pula SUMMARIZE com log INFO e mantém summary NULL."""
        from storage.store import SqliteStore
        from ingestion.orchestrator import IngestionManager
    
        db_path = str(tmp_path / "test_s1_orch.db")
        proj_dir = tmp_path / "sample_proj"
        proj_dir.mkdir()
        (proj_dir / "note.md").write_text("# Titulo\nTexto de exemplo abacaxi-zeta para ingestao.\n", encoding="utf-8")
    
        store = SqliteStore(db_path)
        try:
>           proj = store.create_project(name="proj-s1", path=str(proj_dir))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           TypeError: SqliteStore.create_project() got an unexpected keyword argument 'name'

tests\test_llm_egress_guard.py:255: TypeError
______________ test_s2_gemini_failure_never_falls_back_to_openai ______________

llm_spy = {'clients': [{'kind': 'GenAIClient', 'base_url': None, 'instance': <test_llm_egress_guard.FakeGenAIClient object at 0x...A510>}], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': RuntimeError('Simulated Gemini 503 failure')}}

    def test_s2_gemini_failure_never_falls_back_to_openai(llm_spy: dict[str, Any]) -> None:
        llm_spy["config"]["gemini_fail"] = RuntimeError("Simulated Gemini 503 failure")
        adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)
    
        with pytest.raises(RuntimeError):
            adapter.generate("Prompt sync")
    
>       with pytest.raises(RuntimeError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE RuntimeError

tests\test_llm_egress_guard.py:296: Failed
------------------------------ Captured log call ------------------------------
ERROR    grafo-concierge.summarizer:summarizer.py:215 Failed to call Google GenAI (gemini-2.0-flash): Simulated Gemini 503 failure
ERROR    grafo-concierge.summarizer:summarizer.py:215 Failed to call Google GenAI (gemini-2.0-flash): Simulated Gemini 503 failure
WARNING  grafo-concierge.summarizer:summarizer.py:272 Failed initial asynchronous attempt with Gemini SDK: LLM call failed: Simulated Gemini 503 failure. Trying OpenAI...
____________ test_s2_gemini_missing_sdk_never_falls_back_to_openai ____________

llm_spy = {'clients': [{'kind': 'OpenAI', 'base_url': None, 'instance': <test_llm_egress_guard.FakeOpenAIClient object at 0x00000170434DA120>}], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001704357E120>

    def test_s2_gemini_missing_sdk_never_falls_back_to_openai(
        llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _disable_google_sdk(monkeypatch)
    
        adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)
    
>       with pytest.raises(RuntimeError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE RuntimeError

tests\test_llm_egress_guard.py:312: Failed
____ test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled _____

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
caplog = <_pytest.logging.LogCaptureFixture object at 0x00000170435687D0>

    def test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled(
        llm_spy: dict[str, Any], caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name="gpt-4o-mini", api_key=FAKE_SK_KEY)
    
>       assert getattr(adapter, "is_enabled", None) is False, (
            "Sem GRAFO_LLM_PROVIDER explícito e sem base_url, gpt-4o-mini deve ficar desativado"
        )
E       AssertionError: Sem GRAFO_LLM_PROVIDER explícito e sem base_url, gpt-4o-mini deve ficar desativado
E       assert None is False
E        +  where None = getattr(<ingestion.summarizer.LLMAdapter object at 0x000001704347E140>, 'is_enabled', None)

tests\test_llm_egress_guard.py:334: AssertionError
_____________ test_s6_clients_are_always_closed_even_on_exception _____________

llm_spy = {'clients': [{'kind': 'OpenAI', 'base_url': None, 'instance': <test_llm_egress_guard.FakeOpenAIClient object at 0x0000...5B5B50>}], 'dns_hosts': [], 'config': {'openai_fail': RuntimeError('401 Unauthorized simulated'), 'gemini_fail': None}}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000170434E13D0>

    def test_s6_clients_are_always_closed_even_on_exception(
        llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _disable_google_sdk(monkeypatch)
        monkeypatch.setenv("GRAFO_LLM_PROVIDER", "openai")
        adapter = LLMAdapter(model_name="gpt-4o-mini", api_key=FAKE_SK_KEY)
    
        # 1. Sucesso
        adapter.generate("ok sync")
        asyncio.run(adapter.generate_async("ok async"))
    
        # 2. Exceção durante a chamada
        llm_spy["config"]["openai_fail"] = RuntimeError("401 Unauthorized simulated")
        with pytest.raises(RuntimeError):
            adapter.generate("fail sync")
        with pytest.raises(RuntimeError):
            asyncio.run(adapter.generate_async("fail async"))
    
        assert len(llm_spy["clients"]) == 4
        for idx, entry in enumerate(llm_spy["clients"]):
            inst = entry["instance"]
>           assert inst.entered is True, f"Cliente #{idx} ({entry['kind']}) não usou context manager (__enter__/__aenter__)"
E           AssertionError: Cliente #0 (OpenAI) não usou context manager (__enter__/__aenter__)
E           assert False is True
E            +  where False = <test_llm_egress_guard.FakeOpenAIClient object at 0x00000170433CB360>.entered

tests\test_llm_egress_guard.py:440: AssertionError
------------------------------ Captured log call ------------------------------
ERROR    grafo-concierge.summarizer:summarizer.py:244 Failed to call OpenAI/Compatible Provider (gpt-4o-mini): 401 Unauthorized simulated
ERROR    grafo-concierge.summarizer:summarizer.py:299 Async: Failed to call OpenAI/Provider (gpt-4o-mini): 401 Unauthorized simulated
_______ test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks ________

    def test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks() -> None:
        """Roda subprocesso com asyncio.run que falha 401 contra servidor local e verifica stderr."""
        requests_count = 0
    
        class Handler401(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
    
            def do_POST(self) -> None:
                nonlocal requests_count
                requests_count += 1
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len:
                    self.rfile.read(content_len)
                body = (
                    b'{"error": {"message": "Simulated 401 unauthorized response", '
                    b'"type": "invalid_request_error", "code": "invalid_api_key"}}'
                )
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                self.wfile.write(body)
    
            def log_message(self, format: str, *args: Any) -> None:
                pass
    
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler401)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
    
        repo_root = str(Path(__file__).resolve().parent.parent)
        code = f"""
    import asyncio
    import gc
    import os
    import sys
    
    fake_key = "sk-" + "FAKEFAKEFAKE0001"
    os.environ["GRAFO_LLM_API_KEY"] = fake_key
    os.environ["GRAFO_LLM_PROVIDER"] = "openai-compatible"
    os.environ["GRAFO_LLM_BASE_URL"] = "http://127.0.0.1:{port}/v1"
    
    from ingestion.summarizer import LLMAdapter, ZoomSummarizer
    from ingestion.parser import ParsedChunk, ChunkType
    from ingestion.crawler import FileCategory
    
    adapter = LLMAdapter(
        model_name="gpt-4o-mini",
        api_key=fake_key,
        base_url="http://127.0.0.1:{port}/v1",
    )
    summarizer = ZoomSummarizer(llm_adapter=adapter)
    
    chunks = [
        ParsedChunk(
            content=f"Conteudo de teste {{i}} " * 30,
            armored_content=f"Conteudo de teste {{i}} " * 30,
            chunk_type=ChunkType.SECTION,
            chunk_index=i,
            source_file=f"doc_{{i}}.md",
            file_hash=f"hash_{{i}}",
            category=FileCategory.DOC,
            start_line=1,
            end_line=5,
            symbol_name=f"doc_{{i}}",
        )
        for i in range(3)
    ]
    
    async def run_batch():
        await asyncio.gather(*(summarizer.summarize_l0_async(c) for c in chunks))
    
    # Loop #1: executa batch de sumarização assíncrona (como orchestrator._step_summarize)
    asyncio.run(run_batch())
    
    # Loop #2: simula o loop principal do servidor MCP onde o GC coleta clientes órfãos
    async def mcp_loop_tick():
        gc.collect()
        await asyncio.sleep(0.05)
    
    asyncio.run(mcp_loop_tick())
    """
        env = os.environ.copy()
        env["GRAFO_LLM_API_KEY"] = FAKE_SK_KEY
        env["GRAFO_LLM_PROVIDER"] = "openai-compatible"
        env["GRAFO_LLM_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
        env["PYTHONPATH"] = repo_root
    
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        finally:
            server.shutdown()
            server.server_close()
    
        assert requests_count > 0, f"O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr={proc.stderr})"
        assert proc.returncode == 0, f"Subprocesso falhou (rc={proc.returncode}): {proc.stderr}"
>       assert "Event loop is closed" not in proc.stderr, (
            f"stderr contém 'Event loop is closed':\n{proc.stderr}"
        )
E       AssertionError: stderr contém 'Event loop is closed':
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_2.md — generating Dumb Summary.
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_0.md — generating Dumb Summary.
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_1.md — generating Dumb Summary.
E         Task exception was never retrieved
E         future: <Task finished name='Task-8' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-9' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-10' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-11' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-12' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-13' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-14' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-15' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-16' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         
E       assert 'Event loop is closed' not in 'Async: Fail... is closed\n'
E         
E         'Event loop is closed' is contained here:
E           Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E           L0 async attempt 1/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E           Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type':...
E         
E         ...Full output truncated (281 lines hidden), use '-vv' to show

tests\test_llm_egress_guard.py:553: AssertionError
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled]
FAILED tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled
FAILED tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai
FAILED tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai
FAILED tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled
FAILED tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception
FAILED tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
================== 11 failed, 3 passed, 1 warning in 10.95s ===================
```

### 3.2 Passo 3 — Diff de Produção (`ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py`, `interface/cli.py`, `.env.example`)
#### `scratch/evidencia_4_2h/p3_diff_producao.txt`
```diff
diff --git a/.env.example b/.env.example
index b9dd9b4..73d2604 100644
--- a/.env.example
+++ b/.env.example
@@ -14,9 +14,13 @@ GRAFO_LLM_API_KEY=your_api_key_here_without_quotes
 GEMINI_API_KEY=your_api_key_here_without_quotes
 
 # LLM model for AST summarization and cognitive reasoning
-# Recommended models: gemini-2.0-flash, gemini-1.5-flash, gpt-4o-mini
+# Recommended models: gemini-2.0-flash, gemini-1.5-flash, gpt-4o-mini (or 'none' to disable LLM)
 GRAFO_LLM_MODEL=gemini-2.0-flash
 
+# Explicit LLM provider: gemini, openai, openai-compatible, openrouter, none
+# Required when using OpenAI models without GRAFO_LLM_BASE_URL
+GRAFO_LLM_PROVIDER=gemini
+
 # Custom base URL for alternative LLM providers (Optional)
 # Useful for OpenRouter, DeepSeek, Groq, Ollama, local vLLM, etc.
 # OpenRouter example: https://openrouter.ai/api/v1
diff --git a/ingestion/orchestrator.py b/ingestion/orchestrator.py
index a2c3526..8a60e22 100644
--- a/ingestion/orchestrator.py
+++ b/ingestion/orchestrator.py
@@ -212,7 +212,10 @@ class IngestionManager:
         # --- STEP 3: SUMMARIZE (L0) ---
         uncached_chunks = [c for c in chunks if not c.cached]
         summaries: list[SummaryResult] = []
-        if uncached_chunks and self._summarizer:
+        summarizer_enabled = bool(self._summarizer and getattr(self._summarizer, "is_enabled", True))
+        if self._summarizer and not summarizer_enabled:
+            logger.info("LLM desativado: sumários L0 não gerados")
+        elif uncached_chunks and summarizer_enabled:
             logger.info("[3/8] SUMMARIZE — Generating %d L0 summaries (skipping %d cached)...",
                         len(uncached_chunks), cached_count)
             summaries = self._step_summarize(uncached_chunks, result)
@@ -220,7 +223,7 @@ class IngestionManager:
             logger.info("[3/8] SUMMARIZE completed: %d L0 summaries generated.", len(summaries))
         else:
             logger.info("[3/8] SUMMARIZE — Ignored (summarizer=%s, new=%d).",
-                        "OFF" if not self._summarizer else "ON", len(uncached_chunks))
+                        "OFF" if not summarizer_enabled else "ON", len(uncached_chunks))
 
         # --- STEP 4: STORE SQLite ---
         if chunks:
@@ -406,7 +409,12 @@ class IngestionManager:
             Dict with 'summary' (str) and 'tags' (list[str]), or None if LLM
             is not configured or fails.
         """
-        if not self._summarizer or not hasattr(self._summarizer, "_llm") or not self._summarizer._llm:
+        if (
+            not self._summarizer
+            or not hasattr(self._summarizer, "_llm")
+            or not self._summarizer._llm
+            or not getattr(self._summarizer._llm, "is_enabled", True)
+        ):
             return None
         try:
             prompt = (
diff --git a/ingestion/summarizer.py b/ingestion/summarizer.py
index adb0051..cb35473 100644
--- a/ingestion/summarizer.py
+++ b/ingestion/summarizer.py
@@ -30,6 +30,7 @@ from __future__ import annotations
 
 import json
 import logging
+import os
 import re
 from dataclasses import dataclass, field
 from enum import Enum
@@ -137,6 +138,66 @@ Respond with ONLY the JSON object, no markdown fences, no extra text."""
 # LLMAdapter — interface for LLM calls (Model Tiering)
 # ---------------------------------------------------------------------------
 
+_DISABLED_LLM_TOKENS = {"", "none", "off", "disabled", "false", "0"}
+
+
+def resolve_llm_provider(
+    model_name: Optional[str],
+    api_key: Optional[str] = None,
+    base_url: Optional[str] = None,
+    explicit: Optional[str] = None,
+) -> str:
+    """Resolves the target LLM provider without cross-provider fallbacks.
+
+    Returns one of: 'disabled' | 'gemini' | 'openai' | 'openai_compatible' | 'openrouter'.
+    """
+    raw_explicit = explicit if explicit is not None else os.environ.get("GRAFO_LLM_PROVIDER", "")
+    exp = (raw_explicit or "").strip().lower()
+    model_clean = (model_name or "").strip().lower()
+    base_clean = (base_url or "").strip()
+    key_clean = (api_key or "").strip()
+
+    if model_clean in _DISABLED_LLM_TOKENS:
+        return "disabled"
+
+    if exp:
+        if exp in _DISABLED_LLM_TOKENS:
+            return "disabled"
+        if exp == "gemini":
+            return "gemini"
+        if exp == "openai":
+            return "openai"
+        if exp in ("openai-compatible", "openai_compatible"):
+            if not base_clean:
+                logger.warning(
+                    "GRAFO_LLM_PROVIDER=%r requer GRAFO_LLM_BASE_URL definido; LLM desativado.",
+                    raw_explicit,
+                )
+                return "disabled"
+            return "openai_compatible"
+        if exp == "openrouter":
+            return "openrouter"
+        logger.warning(
+            "Valor inválido para GRAFO_LLM_PROVIDER=%r (defina GRAFO_LLM_PROVIDER como gemini, openai, "
+            "openai-compatible, openrouter ou none); LLM desativado.",
+            raw_explicit,
+        )
+        return "disabled"
+    if model_clean.startswith("gemini-") and not base_clean:
+        return "gemini"
+    if base_clean:
+        return "openai_compatible"
+    if key_clean.startswith("sk-or-"):
+        return "openrouter"
+
+    logger.warning(
+        "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER "
+        "(ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.",
+        model_name,
+    )
+    return "disabled"
+
+
 class LLMAdapter:
     """Adapter for LLM calls with support for Model Tiering.
 
@@ -144,10 +205,12 @@ class LLMAdapter:
     Accepts a custom call_fn for testing and alternative providers.
 
     Args:
-        model_name: Model name (e.g. 'gemini-2.0-flash', 'claude-haiku').
+        model_name: Model name (e.g. 'gemini-2.0-flash', 'gpt-4o-mini', 'none').
         api_key: Provider API key.
+        base_url: Custom OpenAI-compatible base URL.
         call_fn: Custom call function.
                  Signature: (prompt: str, max_tokens: int) -> str
+        provider: Explicit provider override (GRAFO_LLM_PROVIDER).
     """
 
     def __init__(
@@ -156,154 +219,181 @@ class LLMAdapter:
         api_key: Optional[str] = None,
         base_url: Optional[str] = None,
         call_fn: Optional[Callable[[str, int], str]] = None,
+        provider: Optional[str] = None,
     ) -> None:
         self._model_name = model_name
         self._api_key = api_key
-        self._base_url = base_url
+        effective_base_url = base_url if base_url is not None else (os.environ.get("GRAFO_LLM_BASE_URL") or None)
+        if effective_base_url is not None:
+            effective_base_url = effective_base_url.strip() or None
+        self._base_url = effective_base_url
         self._call_fn = call_fn
-        logger.info("LLMAdapter inicializado: model=%s, custom_fn=%s", model_name, call_fn is not None)
+
+        if call_fn is not None:
+            self._provider = "custom"
+            self._is_enabled = True
+        else:
+            self._provider = resolve_llm_provider(
+                model_name=self._model_name,
+                api_key=self._api_key,
+                base_url=self._base_url,
+                explicit=provider,
+            )
+            self._is_enabled = self._provider != "disabled"
+
+        logger.info(
+            "LLMAdapter inicializado: model=%s, provider=%s, enabled=%s, custom_fn=%s",
+            model_name, self._provider, self._is_enabled, call_fn is not None,
+        )
 
     @property
     def model_name(self) -> str:
         return self._model_name
 
+    @property
+    def provider(self) -> str:
+        return self._provider
+
+    @property
+    def is_enabled(self) -> bool:
+        return self._is_enabled
+
     def generate(self, prompt: str, max_tokens: int = 300) -> str:
-        """Sends prompt to LLM and returns the response.
+        """Sends prompt to the resolved LLM provider and returns the response.
 
-        If call_fn was provided, uses it directly.
-        Otherwise, attempts to use google.generativeai (Gemini).
+        Dispatches strictly to the resolved provider without cross-provider fallback.
 
         Raises:
-            RuntimeError: If no LLM backend is available.
+            RuntimeError: If LLM is disabled or the resolved backend fails.
         """
-        # Custom mode (for testing or alternative providers)
         if self._call_fn is not None:
             return self._call_fn(prompt, max_tokens)
 
-        # Attempt with Google GenAI SDK (google.genai)
-        try:
-            from google import genai
-            client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
-            response = client.models.generate_content(
-                model=self._model_name,
-                contents=prompt,
+        if not self._is_enabled:
+            raise RuntimeError(
+                f"LLM is disabled (provider={self._provider}, model={self._model_name!r})."
             )
-            if response.text:
-                return response.text
-        except ImportError:
-            # Attempt with legacy Google Generative AI
+
+        if self._provider == "gemini":
             try:
-                import warnings
-                with warnings.catch_warnings():
-                    warnings.simplefilter("ignore")
-                    import google.generativeai as legacy_genai
-                if self._api_key:
-                    legacy_genai.configure(api_key=self._api_key)
-                model = legacy_genai.GenerativeModel(self._model_name)
-                response = model.generate_content(
-                    prompt,
-                    generation_config=legacy_genai.GenerationConfig(max_output_tokens=max_tokens),
+                from google import genai
+                client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
+                response = client.models.generate_content(
+                    model=self._model_name,
+                    contents=prompt,
                 )
-                if response.text:
-                    return response.text
+                return response.text or ""
             except ImportError:
-                pass
+                try:
+                    import warnings
+                    with warnings.catch_warnings():
+                        warnings.simplefilter("ignore")
+                        import google.generativeai as legacy_genai
+                    if self._api_key:
+                        legacy_genai.configure(api_key=self._api_key)
+                    model = legacy_genai.GenerativeModel(self._model_name)
+                    response = model.generate_content(
+                        prompt,
+                        generation_config=legacy_genai.GenerationConfig(max_output_tokens=max_tokens),
+                    )
+                    return response.text or ""
+                except ImportError as exc:
+                    raise RuntimeError(
+                        "Google Gemini SDK ('google-genai' or 'google-generativeai') is not installed."
+                    ) from exc
+                except Exception as e:
+                    logger.error("Failed to call legacy Gemini (%s): %s", self._model_name, e)
+                    raise RuntimeError(f"LLM call failed: {e}") from e
             except Exception as e:
-                logger.error("Failed to call legacy Gemini (%s): %s", self._model_name, e)
+                logger.error("Failed to call Google GenAI (%s): %s", self._model_name, e)
                 raise RuntimeError(f"LLM call failed: {e}") from e
-        except Exception as e:
-            logger.error("Failed to call Google GenAI (%s): %s", self._model_name, e)
-            raise RuntimeError(f"LLM call failed: {e}") from e
 
-        # Attempt with OpenAI / Compatible Provider
-        try:
-            import openai
-            
-            # Auto-detection of OpenRouter by key if no base_url is informed
-            target_base_url = self._base_url
-            if not target_base_url and self._api_key and self._api_key.startswith("sk-or-"):
-                target_base_url = "https://openrouter.ai/api/v1"
-                
-            if target_base_url:
-                client = openai.OpenAI(
-                    api_key=self._api_key,
-                    base_url=target_base_url
-                )
-            else:
-                client = openai.OpenAI(api_key=self._api_key)
-                
-            response = client.chat.completions.create(
-                model=self._model_name,
-                messages=[{"role": "user", "content": prompt}],
-                max_tokens=max_tokens,
-            )
-            return response.choices[0].message.content or ""
-        except ImportError:
-            pass
-        except Exception as e:
-            logger.error("Failed to call OpenAI/Compatible Provider (%s): %s", self._model_name, e)
-            raise RuntimeError(f"LLM call failed: {e}") from e
+        if self._provider in ("openai", "openai_compatible", "openrouter"):
+            try:
+                import openai
+            except ImportError as exc:
+                raise RuntimeError(
+                    f"OpenAI SDK is not installed for provider '{self._provider}'."
+                ) from exc
 
-        raise RuntimeError(
-            "No LLM backend available. Install 'google-generativeai' or 'openai', "
-            "or provide a custom call_fn."
-        )
+            try:
+                target_base_url = self._base_url
+                if not target_base_url and self._provider == "openrouter":
+                    target_base_url = "https://openrouter.ai/api/v1"
+
+                if target_base_url:
+                    client_ctx = openai.OpenAI(
+                        api_key=self._api_key,
+                        base_url=target_base_url,
+                    )
+                else:
+                    client_ctx = openai.OpenAI(api_key=self._api_key)
+
+                with client_ctx as client:
+                    response = client.chat.completions.create(
+                        model=self._model_name,
+                        messages=[{"role": "user", "content": prompt}],
+                        max_tokens=max_tokens,
+                    )
+                    return response.choices[0].message.content or ""
+            except Exception as e:
+                logger.error("Failed to call OpenAI/Compatible Provider (%s): %s", self._model_name, e)
+                raise RuntimeError(f"LLM call failed: {e}") from e
+
+        raise RuntimeError(f"Unsupported LLM provider: {self._provider!r}")
 
     async def generate_async(self, prompt: str, max_tokens: int = 300) -> str:
         """Asynchronous version of generate() for high throughput.
 
-        Strategy by backend:
-            - custom call_fn: uses asyncio.to_thread (safe fallback).
-            - Native Gemini models (no custom base_url): prioritizes native Gemini SDK.
-            - OpenAI / compatible providers: uses native openai.AsyncOpenAI.
+        Dispatches strictly to the resolved provider without cross-provider fallback,
+        and always closes AsyncOpenAI clients via 'async with'.
         """
         import asyncio
 
-        # Custom mode
         if self._call_fn is not None:
             return await asyncio.to_thread(self._call_fn, prompt, max_tokens)
 
-        # If it is a native Gemini model and does not have an external custom base_url,
-        # prioritize native Gemini SDK to avoid conflict with the openai library
-        if self._model_name.startswith("gemini-") and not self._base_url:
-            try:
-                return await asyncio.to_thread(self.generate, prompt, max_tokens)
-            except Exception as e:
-                logger.warning("Failed initial asynchronous attempt with Gemini SDK: %s. Trying OpenAI...", e)
-
-        # Attempt with OpenAI / Compatible Provider (native async)
-        try:
-            import openai
+        if not self._is_enabled:
+            raise RuntimeError(
+                f"Async LLM is disabled (provider={self._provider}, model={self._model_name!r})."
+            )
 
-            target_base_url = self._base_url
-            if not target_base_url and self._api_key and self._api_key.startswith("sk-or-"):
-                target_base_url = "https://openrouter.ai/api/v1"
+        if self._provider == "gemini":
+            return await asyncio.to_thread(self.generate, prompt, max_tokens)
 
-            if target_base_url:
-                client = openai.AsyncOpenAI(
-                    api_key=self._api_key,
-                    base_url=target_base_url,
-                )
-            else:
-                client = openai.AsyncOpenAI(api_key=self._api_key)
+        if self._provider in ("openai", "openai_compatible", "openrouter"):
+            try:
+                import openai
+            except ImportError as exc:
+                raise RuntimeError(
+                    f"OpenAI SDK is not installed for provider '{self._provider}'."
+                ) from exc
 
-            response = await client.chat.completions.create(
-                model=self._model_name,
-                messages=[{"role": "user", "content": prompt}],
-                max_tokens=max_tokens,
-            )
-            return response.choices[0].message.content or ""
-        except ImportError:
-            pass
-        except Exception as e:
-            logger.error("Async: Failed to call OpenAI/Provider (%s): %s", self._model_name, e)
-            raise RuntimeError(f"Async LLM call failed: {e}") from e
+            try:
+                target_base_url = self._base_url
+                if not target_base_url and self._provider == "openrouter":
+                    target_base_url = "https://openrouter.ai/api/v1"
+
+                if target_base_url:
+                    client_ctx = openai.AsyncOpenAI(
+                        api_key=self._api_key,
+                        base_url=target_base_url,
+                    )
+                else:
+                    client_ctx = openai.AsyncOpenAI(api_key=self._api_key)
+
+                async with client_ctx as client:
+                    response = await client.chat.completions.create(
+                        model=self._model_name,
+                        messages=[{"role": "user", "content": prompt}],
+                        max_tokens=max_tokens,
+                    )
+                    return response.choices[0].message.content or ""
+            except Exception as e:
+                logger.error("Async: Failed to call OpenAI/Provider (%s): %s", self._model_name, e)
+                raise RuntimeError(f"Async LLM call failed: {e}") from e
 
-        # General fallback
-        try:
-            return await asyncio.to_thread(self.generate, prompt, max_tokens)
-        except Exception as e:
-            raise RuntimeError(f"Async LLM fallback failed: {e}") from e
+        raise RuntimeError(f"Unsupported async LLM provider: {self._provider!r}")
 
 
 
@@ -331,6 +421,10 @@ class ZoomSummarizer:
         self._llm = llm_adapter
         self._store = sqlite_store
 
+    @property
+    def is_enabled(self) -> bool:
+        return bool(getattr(self._llm, "is_enabled", True))
+
     # ===================================================================
     # L0 — Summary of individual chunk
     # ===================================================================
diff --git a/interface/cli.py b/interface/cli.py
index 2a36a4b..5d52b40 100644
--- a/interface/cli.py
+++ b/interface/cli.py
@@ -70,6 +70,7 @@ def _bootstrap_concierge():
     chroma_path = resolve_project_path(os.environ.get("GRAFO_CHROMA_PATH", ""), "data/chroma")
     chroma_collection = os.environ.get("GRAFO_CHROMA_COLLECTION", "grafo_concierge")
     llm_model = os.environ.get("GRAFO_LLM_MODEL", "gemini-2.0-flash")
+    llm_provider = os.environ.get("GRAFO_LLM_PROVIDER", "")
     llm_api_key = os.environ.get("GRAFO_LLM_API_KEY", "")
     llm_base_url = os.environ.get("GRAFO_LLM_BASE_URL", "")
 
@@ -101,6 +102,7 @@ def _bootstrap_concierge():
         model_name=llm_model,
         api_key=llm_api_key or None,
         base_url=llm_base_url or None,
+        provider=llm_provider or None,
     )
     summarizer = ZoomSummarizer(llm_adapter=llm_adapter, sqlite_store=store)
```

### 3.3 Passo 3 — Testes Verdes (`tests/test_llm_egress_guard.py`)
#### `scratch/evidencia_4_2h/p3_green_egress_guard.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 14 items

tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] PASSED [  7%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] PASSED [ 14%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] PASSED [ 21%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] PASSED [ 28%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] PASSED [ 35%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled PASSED [ 42%]
tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai PASSED [ 50%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai PASSED [ 57%]
tests/test_llm_egress_guard.py::test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled PASSED [ 64%]
tests/test_llm_egress_guard.py::test_s4_explicit_openai_provider_creates_openai_client PASSED [ 71%]
tests/test_llm_egress_guard.py::test_s5_custom_base_url_and_openrouter_preserved PASSED [ 78%]
tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception PASSED [ 85%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks PASSED [ 92%]
tests/test_llm_egress_guard.py::test_s8_custom_call_fn_works_unchanged PASSED [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 1 warning in 10.73s ========================
```

### 3.4 Passo 3 — Regressão dos Testes de Persistência de Sumários e Reparo Vetorial (Rodada 4.1)
#### `scratch/evidencia_4_2h/p3_summary_persistence.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 11 items

tests/test_summary_persistence.py::TestSummaryPersistence::test_l0_summaries_persisted_in_nodes_table PASSED [  9%]
tests/test_summary_persistence.py::TestSummaryPersistence::test_dumb_summary_not_persisted_in_nodes_table PASSED [ 18%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_a_model_unavailable_then_repaired PASSED [ 27%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_b_reset_collection_recomposed PASSED [ 36%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_c_partial_batch_failure_recovery PASSED [ 45%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_d_chroma_unavailable_no_exception_and_repaired PASSED [ 54%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_e_empty_or_whitespace_nodes_ignored PASSED [ 63%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_f_idempotence_third_mine_no_reembed PASSED [ 72%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_g_metadata_keys_identical_between_ingestion_and_repair PASSED [ 81%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_h_janitor_delegates_to_repair_and_removes_orphans PASSED [ 90%]
tests/test_ingestion_vector_repair.py::TestIngestionVectorRepair::test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata PASSED [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 11 passed, 1 warning in 4.88s ========================
```

---

## 4. PASSO 4 — F4-021: SCANNER DE SEGREDOS, REDAÇÃO DE EVIDÊNCIAS, FILTRO DE LOGS E REGRA 13

### 4.1 Passo 4a — Scanner `scratch/tools/scan_secrets.py` (Antes e Depois da Redação)
#### `scratch/evidencia_4_2h/p4a_scan_before.txt`
```text
scanned_files=987
files_with_findings=4
total_pattern_hits=218
FINDING: audits/bypass-governanca-por-session-id.md | lines=249,256 | patterns=[SK_KEY_FRAGMENT:2]
FINDING: scratch/evidencia_4_2/p3_matrix_run.txt | lines=519,520,521,533,534,569,570,571,583,584,...(+125 lines) | patterns=[AQ_KEY_FRAGMENT:54, INCORRECT_API_KEY_MSG:27, MASKED_KEY_SUFFIX:54]
FINDING: scratch/evidencia_4_2d/teste_funcional_real.txt | lines=223,224,225,237,238,257,258,259,271,272,...(+35 lines) | patterns=[AQ_KEY_FRAGMENT:18, INCORRECT_API_KEY_MSG:9, MASKED_KEY_SUFFIX:18]
FINDING: scratch/evidencia_4_2e/diag/out__dump_mine_2yfwxq1r__stderr.txt | lines=66,67,70,71,72,73,78,79,81,82,...(+2 lines) | patterns=[AQ_KEY_FRAGMENT:12, INCORRECT_API_KEY_MSG:12, MASKED_KEY_SUFFIX:12]
```
#### `scratch/evidencia_4_2h/p4a_scan_after.txt`
```text
scanned_files=998
files_with_findings=0
total_pattern_hits=0
```

### 4.2 Passo 4b — `git diff --stat` dos Arquivos Redigidos e `git grep` Pós-Redação
#### `scratch/evidencia_4_2h/p4b_diff_stat.txt`
```text
warning: in the working copy of 'audits/bypass-governanca-por-session-id.md', LF will be replaced by CRLF the next time Git touches it
 audits/bypass-governanca-por-session-id.md         |   4 +-
 scratch/evidencia_4_2/p3_matrix_run.txt            | 270 ++++++++++-----------
 scratch/evidencia_4_2d/teste_funcional_real.txt    |  90 +++----
 .../diag/out__dump_mine_2yfwxq1r__stderr.txt       |  24 +-
 4 files changed, 194 insertions(+), 194 deletions(-)
```
#### `scratch/evidencia_4_2h/p4b_git_grep_after.txt`
```text
EXIT_CODE_1_ZERO_MATCHES
```

### 4.3 Passo 4c — Teste `tests/test_no_secrets_in_tracked_files.py` (Vermelho e Verde)
#### `scratch/evidencia_4_2h/p4c_red_no_secrets.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits FAILED [100%]

================================== FAILURES ===================================
____________________ test_no_secrets_in_scratch_or_audits _____________________

    def test_no_secrets_in_scratch_or_audits() -> None:
        """Garante zero achados de segredos ou fragmentos de chaves em scratch/ e audits/."""
        scanner, repo_root = _load_scanner()
        findings, scanned_count = scanner.scan_files(repo_root=repo_root, include_untracked=True)
        assert scanned_count > 0, "O scanner deveria ter varrido pelo menos 1 arquivo em scratch/ ou audits/."
    
        if findings:
            summary_lines = []
            for rel_path, hits in sorted(findings.items()):
                pats = sorted({pat_name for _, pat_name, _ in hits})
                lines = sorted({lineno for lineno, _, _ in hits})
                summary_lines.append(
                    f"{rel_path}: {len(hits)} hit(s) on line(s) {lines[:10]} patterns={pats}"
                )
>           raise AssertionError(
                f"Encontrados padrões de segredo em {len(findings)} arquivo(s):\n"
                + "\n".join(summary_lines)
            )
E           AssertionError: Encontrados padrões de segredo em 4 arquivo(s):
E           audits/bypass-governanca-por-session-id.md: 2 hit(s) on line(s) [249, 256] patterns=['SK_KEY_FRAGMENT']
E           scratch/evidencia_4_2/p3_matrix_run.txt: 135 hit(s) on line(s) [519, 520, 521, 533, 534, 569, 570, 571, 583, 584] patterns=['AQ_KEY_FRAGMENT', 'INCORRECT_API_KEY_MSG', 'MASKED_KEY_SUFFIX']
E           scratch/evidencia_4_2d/teste_funcional_real.txt: 45 hit(s) on line(s) [223, 224, 225, 237, 238, 257, 258, 259, 271, 272] patterns=['AQ_KEY_FRAGMENT', 'INCORRECT_API_KEY_MSG', 'MASKED_KEY_SUFFIX']
E           scratch/evidencia_4_2e/diag/out__dump_mine_2yfwxq1r__stderr.txt: 36 hit(s) on line(s) [66, 67, 70, 71, 72, 73, 78, 79, 81, 82] patterns=['AQ_KEY_FRAGMENT', 'INCORRECT_API_KEY_MSG', 'MASKED_KEY_SUFFIX']

tests\test_no_secrets_in_tracked_files.py:38: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits
============================== 1 failed in 0.76s ==============================
```
#### `scratch/evidencia_4_2h/p4c_green_no_secrets.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits PASSED [100%]

============================== 1 passed in 0.64s ==============================
```

### 4.4 Passo 4d — Filtro de Segredos em `main.py` (`setup_logging`) e Testes R1–R5 (`tests/test_secret_redaction.py`)
#### `scratch/evidencia_4_2h/p4d_red_secret_redaction.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_secret_redaction.py::test_r1_secret_in_msg_is_redacted FAILED [ 20%]
tests/test_secret_redaction.py::test_r2_secret_in_args_is_redacted FAILED [ 40%]
tests/test_secret_redaction.py::test_r3_secret_inside_formatted_exception_is_redacted FAILED [ 60%]
tests/test_secret_redaction.py::test_r4_exact_env_api_key_value_is_redacted FAILED [ 80%]
tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent FAILED [100%]

================================== FAILURES ===================================
______________________ test_r1_secret_in_msg_is_redacted ______________________

    def test_r1_secret_in_msg_is_redacted() -> None:
        """R1: chave diretamente na string msg (sk-..., AQ...., AIza..., Bearer <token>)."""
        main_mod.setup_logging("INFO")
        lg, buf, rh = _make_isolated_logger()
    
        lg.error(f"Falha com chaves {FAKE_SK} e {FAKE_AQ} e {FAKE_AIZA} e Authorization: Bearer {FAKE_BEARER_TOKEN}")
    
        stream_out = buf.getvalue()
        rich_out = "\n".join(rh.rendered)
    
        for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
            leaked = any(s in out_text for s in (FAKE_SK, FAKE_AQ, FAKE_AIZA, FAKE_BEARER_TOKEN))
>           assert not leaked, f"R1 falhou: segredo vazou sem redação em {out_name}"
E           AssertionError: R1 falhou: segredo vazou sem redação em StreamHandler
E           assert not True

tests\test_secret_redaction.py:67: AssertionError
_____________________ test_r2_secret_in_args_is_redacted ______________________

    def test_r2_secret_in_args_is_redacted() -> None:
        """R2: chave passada via args (logger.warning('Chave: %s / %s', k1, k2))."""
        main_mod.setup_logging("INFO")
        lg, buf, rh = _make_isolated_logger()
    
        lg.warning("Tentativa falhou para chave %s e %s", FAKE_AQ, FAKE_SK)
    
        stream_out = buf.getvalue()
        rich_out = "\n".join(rh.rendered)
    
        for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
            leaked = any(s in out_text for s in (FAKE_AQ, FAKE_SK))
>           assert not leaked, f"R2 falhou: segredo em args vazou sem redação em {out_name}"
E           AssertionError: R2 falhou: segredo em args vazou sem redação em StreamHandler
E           assert not True

tests\test_secret_redaction.py:83: AssertionError
____________ test_r3_secret_inside_formatted_exception_is_redacted ____________

    def test_r3_secret_inside_formatted_exception_is_redacted() -> None:
        """R3: chave dentro de exceção formatada por logger.exception."""
        main_mod.setup_logging("INFO")
        lg, buf, rh = _make_isolated_logger()
    
        try:
            raise RuntimeError(f"401 Error: key {FAKE_AQ} or {FAKE_SK} rejected by upstream")
        except RuntimeError:
            lg.exception("Erro ao chamar provedor")
    
        stream_out = buf.getvalue()
        rich_out = "\n".join(rh.rendered)
    
        for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
            leaked = any(s in out_text for s in (FAKE_AQ, FAKE_SK))
>           assert not leaked, f"R3 falhou: segredo na exceção vazou sem redação em {out_name}"
E           AssertionError: R3 falhou: segredo na exceção vazou sem redação em StreamHandler
E           assert not True

tests\test_secret_redaction.py:102: AssertionError
_________________ test_r4_exact_env_api_key_value_is_redacted _________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000021455110E90>

    def test_r4_exact_env_api_key_value_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
        """R4: valor exato de GRAFO_LLM_API_KEY e GRAFO_API_KEY do ambiente (>= 8 chars) é redigido."""
        custom_llm_secret = "my_custom_provider_secret_val_12345"
        custom_http_secret = "my_custom_sse_bearer_secret_67890"
        monkeypatch.setenv("GRAFO_LLM_API_KEY", custom_llm_secret)
        monkeypatch.setenv("GRAFO_API_KEY", custom_http_secret)
    
        main_mod.setup_logging("INFO")
        lg, buf, rh = _make_isolated_logger()
    
        lg.error("Credenciais rejeitadas: llm=%s http=%s", custom_llm_secret, custom_http_secret)
    
        stream_out = buf.getvalue()
        rich_out = "\n".join(rh.rendered)
    
        for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
            leaked = (custom_llm_secret in out_text) or (custom_http_secret in out_text)
>           assert not leaked, f"R4 falhou: valor de variável de ambiente vazou em {out_name}"
E           AssertionError: R4 falhou: valor de variável de ambiente vazou em StreamHandler
E           assert not True

tests\test_secret_redaction.py:123: AssertionError
__________ test_r5_setup_logging_installs_factory_and_is_idempotent ___________

    def test_r5_setup_logging_installs_factory_and_is_idempotent() -> None:
        """R5: setup_logging instala o filtro/factory e chamá-lo duas vezes não duplica nem empilha wrappers."""
        main_mod.setup_logging("INFO")
        factory_after_first = logging.getLogRecordFactory()
    
        main_mod.setup_logging("INFO")
        factory_after_second = logging.getLogRecordFactory()
    
        assert factory_after_first is factory_after_second, (
            "Chamar setup_logging duas vezes não deve empilhar novas factories"
        )
>       assert getattr(factory_after_second, "_grafo_secret_redacting", False) is True, (
            "A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True"
        )
E       AssertionError: A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True
E       assert False is True
E        +  where False = getattr(<class 'logging.LogRecord'>, '_grafo_secret_redacting', False)

tests\test_secret_redaction.py:138: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_r1_secret_in_msg_is_redacted - As...
FAILED tests/test_secret_redaction.py::test_r2_secret_in_args_is_redacted - A...
FAILED tests/test_secret_redaction.py::test_r3_secret_inside_formatted_exception_is_redacted
FAILED tests/test_secret_redaction.py::test_r4_exact_env_api_key_value_is_redacted
FAILED tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent
============================== 5 failed in 0.24s ==============================
```
#### `scratch/evidencia_4_2h/p4d_green_secret_redaction.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_secret_redaction.py::test_r1_secret_in_msg_is_redacted PASSED [ 20%]
tests/test_secret_redaction.py::test_r2_secret_in_args_is_redacted PASSED [ 40%]
tests/test_secret_redaction.py::test_r3_secret_inside_formatted_exception_is_redacted PASSED [ 60%]
tests/test_secret_redaction.py::test_r4_exact_env_api_key_value_is_redacted PASSED [ 80%]
tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent PASSED [100%]

============================== 5 passed in 0.12s ==============================
```

### 4.5 Passo 4d/4e — Diff de `main.py` e `AUDIT_PROTOCOL.md` (Regra 13)
#### `scratch/evidencia_4_2h/p4d_diff_main_proto.txt`
```diff
diff --git a/AUDIT_PROTOCOL.md b/AUDIT_PROTOCOL.md
index 61848ac..57472fb 100644
--- a/AUDIT_PROTOCOL.md
+++ b/AUDIT_PROTOCOL.md
@@ -43,6 +43,7 @@
     arquivo é a fonte de verdade.
 11. Commit obrigatório a cada gate. Imediatamente após marcar um item [x] e antes de reportar o Walkthrough como concluído, rode: git add -A && git commit -m "docs(audit): <slug-do-item> concluído". O trabalho de auditoria é feito em múltiplas máquinas (PC e notebook) — nunca deixe um item aprovado sem commit. Antes de encerrar qualquer sessão (fim de dia, troca de máquina), rode git push e confirme a saída ao humano. Ao iniciar uma sessão numa máquina diferente, rode git pull e git status ANTES de ler o item ▶ EM ANDAMENTO, e reporte o resultado — nunca assuma que o estado local está atualizado.
 12. Toda evidência (código, saída de comando, diff) deve ser gerada por redirecionamento para arquivo e incluída por cópia mecânica desse arquivo. É proibido digitar, resumir ou reconstruir trechos. Trecho sem arquivo de origem é inválido.
+13. Nenhuma evidência é commitada sem passar por `scratch/tools/scan_secrets.py` (zero achados em `scratch/` e `audits/`); chaves reais nunca entram em testes.
 ---
 
 ## Fase 0 — Baseline objetiva (sem interpretação)
diff --git a/main.py b/main.py
index f9d1fa8..824416e 100644
--- a/main.py
+++ b/main.py
@@ -74,13 +74,83 @@ TRANSPORT = os.environ.get("GRAFO_TRANSPORT", "stdio")
 
 
 # ---------------------------------------------------------------------------
-# 2. LOGGING — Console with timestamps and levels
+# 2. LOGGING — Console with timestamps, levels, and secret redaction (F4-021)
 # ---------------------------------------------------------------------------
 
+import re as _re
+
+_LOG_SECRET_PATTERNS: list[tuple[_re.Pattern[str], str]] = [
+    (_re.compile(r'(Bearer\s+)[^\s"\',;)\]}]+', _re.IGNORECASE), r"\1[REDACTED]"),
+    (_re.compile(r"AQ\.[\w*-]{4,}(?:\w{0,8}\.)?"), "[REDACTED]"),
+    (_re.compile(r"AIza[\w-]{10,}"), "[REDACTED]"),
+    (_re.compile(r"sk-[\w*-]{6,}"), "[REDACTED]"),
+    (_re.compile(r"\*{6,}\w{0,8}\."), "[REDACTED]"),
+]
+
+
+def redact_log_secrets(text: str) -> str:
+    """Redige chaves de API e tokens Bearer em mensagens de log e tracebacks."""
+    if not text or not isinstance(text, str):
+        return text
+
+    result = text
+    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY"):
+        secret_val = os.environ.get(env_var, "").strip()
+        if len(secret_val) >= 8 and secret_val in result:
+            result = result.replace(secret_val, "[REDACTED]")
+
+    for pattern, replacement in _LOG_SECRET_PATTERNS:
+        result = pattern.sub(replacement, result)
+
+    return result
+
+
+class _SecretRedactingLogRecord(logging.LogRecord):
+    """LogRecord que garante redação em getMessage() e em exceções formatadas
+    para qualquer Handler (incluindo StreamHandler e RichHandler do FastMCP).
+    """
+
+    def __init__(self, *args, **kwargs) -> None:
+        super().__init__(*args, **kwargs)
+        self._redacted_exc_text: str | None = None
+        if self.exc_info and isinstance(self.exc_info, tuple) and len(self.exc_info) == 3:
+            exc_val = self.exc_info[1]
+            if exc_val is not None and getattr(exc_val, "args", None):
+                try:
+                    exc_val.args = tuple(
+                        redact_log_secrets(a) if isinstance(a, str) else a
+                        for a in exc_val.args
+                    )
+                except Exception:
+                    pass
+
+    def getMessage(self) -> str:
+        return redact_log_secrets(super().getMessage())
+
+    @property
+    def exc_text(self) -> str | None:
+        return self._redacted_exc_text
+
+    @exc_text.setter
+    def exc_text(self, value: str | None) -> None:
+        self._redacted_exc_text = redact_log_secrets(value) if isinstance(value, str) else value
+
+
+def _secret_redacting_record_factory(*args, **kwargs) -> logging.LogRecord:
+    return _SecretRedactingLogRecord(*args, **kwargs)
+
+
+_secret_redacting_record_factory._grafo_secret_redacting = True  # type: ignore[attr-defined]
+
+
 def setup_logging(level: str = "INFO") -> None:
-    """Configures global logging for Grafo Concierge."""
+    """Configures global logging for Grafo Concierge with idempotent secret redaction."""
     numeric_level = getattr(logging, level, logging.INFO)
 
+    current_factory = logging.getLogRecordFactory()
+    if not getattr(current_factory, "_grafo_secret_redacting", False):
+        logging.setLogRecordFactory(_secret_redacting_record_factory)
+
     formatter = logging.Formatter(
         fmt="%(asctime)s │ %(levelname)-7s │ %(name)-28s │ %(message)s",
         datefmt="%Y-%m-%d %H:%M:%S",
@@ -91,9 +161,10 @@ def setup_logging(level: str = "INFO") -> None:
     handler.setLevel(numeric_level)
     handler.setFormatter(formatter)
 
-    # Root logger
+    # Root logger (idempotent handler setup)
     root = logging.getLogger()
     root.setLevel(numeric_level)
+    root.handlers.clear()
     root.addHandler(handler)
 
     # Silence noisy third-party loggers
```

---

## 5. PASSO 5 — SUÍTE COMPLETA E 5 VERIFICAÇÕES DE MUTAÇÃO

### 5.1 Suíte Completa (`pytest tests/ -q`)
#### `scratch/evidencia_4_2h/p5_full_pytest.txt`
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
1 failed, 385 passed, 1 skipped, 20 warnings in 102.59s (0:01:42)
```

### 5.2 Mutação (i): Restaurar Fallback Gemini -> OpenAI no Async (`S2` falha)
#### `scratch/evidencia_4_2h/p5_mut1_s2.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: c:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 14 items / 12 deselected / 2 selected

tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai FAILED [ 50%]
tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai FAILED [100%]

================================== FAILURES ===================================
______________ test_s2_gemini_failure_never_falls_back_to_openai ______________

llm_spy = {'clients': [{'kind': 'GenAIClient', 'base_url': None, 'instance': <test_llm_egress_guard.FakeGenAIClient object at 0x...D940>}], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': RuntimeError('Simulated Gemini 503 failure')}}

    def test_s2_gemini_failure_never_falls_back_to_openai(llm_spy: dict[str, Any]) -> None:
        llm_spy["config"]["gemini_fail"] = RuntimeError("Simulated Gemini 503 failure")
        adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)
    
        with pytest.raises(RuntimeError):
            adapter.generate("Prompt sync")
    
>       with pytest.raises(RuntimeError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE RuntimeError

tests\test_llm_egress_guard.py:325: Failed
------------------------------ Captured log call ------------------------------
ERROR    grafo-concierge.summarizer:summarizer.py:308 Failed to call Google GenAI (gemini-2.0-flash): Simulated Gemini 503 failure
ERROR    grafo-concierge.summarizer:summarizer.py:308 Failed to call Google GenAI (gemini-2.0-flash): Simulated Gemini 503 failure
____________ test_s2_gemini_missing_sdk_never_falls_back_to_openai ____________

llm_spy = {'clients': [{'kind': 'AsyncOpenAI', 'base_url': None, 'instance': <test_llm_egress_guard.FakeAsyncOpenAIClient object at 0x000001AE5BC73750>}], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001AE5BBAF230>

    def test_s2_gemini_missing_sdk_never_falls_back_to_openai(
        llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _disable_google_sdk(monkeypatch)
    
        adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)
    
        with pytest.raises(RuntimeError):
            adapter.generate("Prompt sync sem SDK")
    
>       with pytest.raises(RuntimeError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE RuntimeError

tests\test_llm_egress_guard.py:344: Failed
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s2_gemini_failure_never_falls_back_to_openai
FAILED tests/test_llm_egress_guard.py::test_s2_gemini_missing_sdk_never_falls_back_to_openai
================= 2 failed, 12 deselected, 1 warning in 3.20s =================
```

### 5.3 Mutação (ii): Remover Tratamento de `"none"` (`S1` falha)
#### `scratch/evidencia_4_2h/p5_mut2_s1.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: c:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 14 items / 8 deselected / 6 selected

tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none] FAILED [ 16%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE] FAILED [ 33%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[] FAILED [ 50%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off] FAILED [ 66%]
tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled] FAILED [ 83%]
tests/test_llm_egress_guard.py::test_s1_orchestrator_skips_summarize_when_llm_disabled PASSED [100%]

================================== FAILURES ===================================
__________________ test_s1_disabled_models_zero_egress[none] __________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'none'
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001747D2ECC20>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001747C71BCE0>

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(
        llm_spy: dict[str, Any],
        disabled_model: str,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
        assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
>       assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
            f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
        )
E       AssertionError: model_name='none' é desativação intencional e não deve emitir WARNING: ["Modelo LLM 'none' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança."]
E       assert [<LogRecord: ... segurança.">] == []
E         
E         Left contains one more item: <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %...r explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">
E         
E         Full diff:
E         - []
E         + [
E         +     <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">,
E         + ]

tests\test_llm_egress_guard.py:231: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  grafo-concierge.summarizer:summarizer.py:193 Modelo LLM 'none' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.
__________________ test_s1_disabled_models_zero_egress[NONE] __________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'NONE'
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001747D131E50>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001747D1E0C30>

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(
        llm_spy: dict[str, Any],
        disabled_model: str,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
        assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
>       assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
            f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
        )
E       AssertionError: model_name='NONE' é desativação intencional e não deve emitir WARNING: ["Modelo LLM 'NONE' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança."]
E       assert [<LogRecord: ... segurança.">] == []
E         
E         Left contains one more item: <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %...r explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">
E         
E         Full diff:
E         - []
E         + [
E         +     <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">,
E         + ]

tests\test_llm_egress_guard.py:231: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  grafo-concierge.summarizer:summarizer.py:193 Modelo LLM 'NONE' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.
____________________ test_s1_disabled_models_zero_egress[] ____________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = ''
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001747D132AD0>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001747D3CC4D0>

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(
        llm_spy: dict[str, Any],
        disabled_model: str,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
        assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
>       assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
            f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
        )
E       AssertionError: model_name='' é desativação intencional e não deve emitir WARNING: ["Modelo LLM '' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança."]
E       assert [<LogRecord: ... segurança.">] == []
E         
E         Left contains one more item: <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %...r explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">
E         
E         Full diff:
E         - []
E         + [
E         +     <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">,
E         + ]

tests\test_llm_egress_guard.py:231: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  grafo-concierge.summarizer:summarizer.py:193 Modelo LLM '' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.
__________________ test_s1_disabled_models_zero_egress[off] ___________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'off'
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001747D1E1810>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001747D274270>

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(
        llm_spy: dict[str, Any],
        disabled_model: str,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
        assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
>       assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
            f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
        )
E       AssertionError: model_name='off' é desativação intencional e não deve emitir WARNING: ["Modelo LLM 'off' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança."]
E       assert [<LogRecord: ... segurança.">] == []
E         
E         Left contains one more item: <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %...r explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">
E         
E         Full diff:
E         - []
E         + [
E         +     <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">,
E         + ]

tests\test_llm_egress_guard.py:231: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  grafo-concierge.summarizer:summarizer.py:193 Modelo LLM 'off' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.
________________ test_s1_disabled_models_zero_egress[disabled] ________________

llm_spy = {'clients': [], 'dns_hosts': [], 'config': {'openai_fail': None, 'gemini_fail': None}}
disabled_model = 'disabled'
caplog = <_pytest.logging.LogCaptureFixture object at 0x000001747D1E2520>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001747D274D10>

    @pytest.mark.parametrize("disabled_model", ["none", "NONE", "", "off", "disabled"])
    def test_s1_disabled_models_zero_egress(
        llm_spy: dict[str, Any],
        disabled_model: str,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
            adapter = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
        assert getattr(adapter, "is_enabled", None) is False, (
            f"LLMAdapter com model_name={disabled_model!r} deve ter is_enabled=False"
        )
>       assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
            f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
        )
E       AssertionError: model_name='disabled' é desativação intencional e não deve emitir WARNING: ["Modelo LLM 'disabled' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança."]
E       assert [<LogRecord: ... segurança.">] == []
E         
E         Left contains one more item: <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %...r explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">
E         
E         Full diff:
E         - []
E         + [
E         +     <LogRecord: grafo-concierge.summarizer, 30, c:\Nexus-Memory\GrafoConcierge\ingestion\summarizer.py, 193, "Modelo LLM %r sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.">,
E         + ]

tests\test_llm_egress_guard.py:231: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  grafo-concierge.summarizer:summarizer.py:193 Modelo LLM 'disabled' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_PROVIDER=openai). LLM desativado por segurança.
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[none]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[NONE]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[off]
FAILED tests/test_llm_egress_guard.py::test_s1_disabled_models_zero_egress[disabled]
============ 5 failed, 1 passed, 8 deselected, 1 warning in 3.46s =============
```

### 5.4 Mutação (iii): Remover `async with` no `AsyncOpenAI` (`S6` e `S7` falham)
#### `scratch/evidencia_4_2h/p5_mut3_s6_s7.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: c:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 14 items / 12 deselected / 2 selected

tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception FAILED [ 50%]
tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks FAILED [100%]

================================== FAILURES ===================================
_____________ test_s6_clients_are_always_closed_even_on_exception _____________

llm_spy = {'clients': [{'kind': 'OpenAI', 'base_url': None, 'instance': <test_llm_egress_guard.FakeOpenAIClient object at 0x0000...6DA850>}], 'dns_hosts': [], 'config': {'openai_fail': RuntimeError('401 Unauthorized simulated'), 'gemini_fail': None}}
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001F840CB7A80>

    def test_s6_clients_are_always_closed_even_on_exception(
        llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _disable_google_sdk(monkeypatch)
        monkeypatch.setenv("GRAFO_LLM_PROVIDER", "openai")
        adapter = LLMAdapter(model_name="gpt-4o-mini", api_key=FAKE_SK_KEY)
    
        # 1. Sucesso
        adapter.generate("ok sync")
        asyncio.run(adapter.generate_async("ok async"))
    
        # 2. Exceção durante a chamada
        llm_spy["config"]["openai_fail"] = RuntimeError("401 Unauthorized simulated")
        with pytest.raises(RuntimeError):
            adapter.generate("fail sync")
        with pytest.raises(RuntimeError):
            asyncio.run(adapter.generate_async("fail async"))
    
        assert len(llm_spy["clients"]) == 4
        for idx, entry in enumerate(llm_spy["clients"]):
            inst = entry["instance"]
>           assert inst.entered is True, f"Cliente #{idx} ({entry['kind']}) não usou context manager (__enter__/__aenter__)"
E           AssertionError: Cliente #1 (AsyncOpenAI) não usou context manager (__enter__/__aenter__)
E           assert False is True
E            +  where False = <test_llm_egress_guard.FakeAsyncOpenAIClient object at 0x000001F84188D6A0>.entered

tests\test_llm_egress_guard.py:469: AssertionError
------------------------------ Captured log call ------------------------------
ERROR    grafo-concierge.summarizer:summarizer.py:340 Failed to call OpenAI/Compatible Provider (gpt-4o-mini): 401 Unauthorized simulated
ERROR    grafo-concierge.summarizer:summarizer.py:393 Async: Failed to call OpenAI/Provider (gpt-4o-mini): 401 Unauthorized simulated
_______ test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks ________

    def test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks() -> None:
        """Roda subprocesso com asyncio.run que falha 401 contra servidor local e verifica stderr."""
        requests_count = 0
    
        class Handler401(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
    
            def do_POST(self) -> None:
                nonlocal requests_count
                requests_count += 1
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len:
                    self.rfile.read(content_len)
                body = (
                    b'{"error": {"message": "Simulated 401 unauthorized response", '
                    b'"type": "invalid_request_error", "code": "invalid_api_key"}}'
                )
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                self.wfile.write(body)
    
            def log_message(self, format: str, *args: Any) -> None:
                pass
    
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler401)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
    
        repo_root = str(Path(__file__).resolve().parent.parent)
        code = f"""
    import asyncio
    import gc
    import os
    import sys
    
    fake_key = "sk-" + "FAKEFAKEFAKE0001"
    os.environ["GRAFO_LLM_API_KEY"] = fake_key
    os.environ["GRAFO_LLM_PROVIDER"] = "openai-compatible"
    os.environ["GRAFO_LLM_BASE_URL"] = "http://127.0.0.1:{port}/v1"
    
    from ingestion.summarizer import LLMAdapter, ZoomSummarizer
    from ingestion.parser import ParsedChunk, ChunkType
    from ingestion.crawler import FileCategory
    
    adapter = LLMAdapter(
        model_name="gpt-4o-mini",
        api_key=fake_key,
        base_url="http://127.0.0.1:{port}/v1",
    )
    summarizer = ZoomSummarizer(llm_adapter=adapter)
    
    chunks = [
        ParsedChunk(
            content=f"Conteudo de teste {{i}} " * 30,
            armored_content=f"Conteudo de teste {{i}} " * 30,
            chunk_type=ChunkType.SECTION,
            chunk_index=i,
            source_file=f"doc_{{i}}.md",
            file_hash=f"hash_{{i}}",
            category=FileCategory.DOC,
            start_line=1,
            end_line=5,
            symbol_name=f"doc_{{i}}",
        )
        for i in range(3)
    ]
    
    async def run_batch():
        await asyncio.gather(*(summarizer.summarize_l0_async(c) for c in chunks))
    
    # Loop #1: executa batch de sumarização assíncrona (como orchestrator._step_summarize)
    asyncio.run(run_batch())
    
    # Loop #2: simula o loop principal do servidor MCP onde o GC coleta clientes órfãos
    async def mcp_loop_tick():
        gc.collect()
        await asyncio.sleep(0.05)
    
    asyncio.run(mcp_loop_tick())
    """
        env = os.environ.copy()
        env["GRAFO_LLM_API_KEY"] = FAKE_SK_KEY
        env["GRAFO_LLM_PROVIDER"] = "openai-compatible"
        env["GRAFO_LLM_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
        env["PYTHONPATH"] = repo_root
    
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        finally:
            server.shutdown()
            server.server_close()
    
        assert requests_count > 0, f"O subprocesso deveria ter feito requisições HTTP ao servidor local (stderr={proc.stderr})"
        assert proc.returncode == 0, f"Subprocesso falhou (rc={proc.returncode}): {proc.stderr}"
>       assert "Event loop is closed" not in proc.stderr, (
            f"stderr contém 'Event loop is closed':\n{proc.stderr}"
        )
E       AssertionError: stderr contém 'Event loop is closed':
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 1/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 2/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_0.md — generating Dumb Summary.
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_1.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_1.md — generating Dumb Summary.
E         Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async attempt 3/3 failed for doc_2.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E         L0 async: all attempts failed for doc_2.md — generating Dumb Summary.
E         Task exception was never retrieved
E         future: <Task finished name='Task-8' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-9' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-10' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-11' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-12' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-13' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-14' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-15' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         Task exception was never retrieved
E         future: <Task finished name='Task-16' coro=<AsyncClient.aclose() done, defined at C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py:1978> exception=RuntimeError('Event loop is closed')>
E         Traceback (most recent call last):
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_client.py", line 1985, in aclose
E             await self._transport.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpx\_transports\default.py", line 406, in aclose
E             await self._pool.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 353, in aclose
E             await self._close_connections(closing_connections)
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection_pool.py", line 345, in _close_connections
E             await connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\connection.py", line 173, in aclose
E             await self._connection.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_async\http11.py", line 258, in aclose
E             await self._network_stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\httpcore\_backends\anyio.py", line 53, in aclose
E             await self._stream.aclose()
E           File "C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\anyio\_backends\_asyncio.py", line 1344, in aclose
E             self._transport.close()
E             ~~~~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\proactor_events.py", line 109, in close
E             self._loop.call_soon(self._call_connection_lost, None)
E             ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 827, in call_soon
E             self._check_closed()
E             ~~~~~~~~~~~~~~~~~~^^
E           File "C:\Python314\Lib\asyncio\base_events.py", line 550, in _check_closed
E             raise RuntimeError('Event loop is closed')
E         RuntimeError: Event loop is closed
E         
E       assert 'Event loop is closed' not in 'Async: Fail... is closed\n'
E         
E         'Event loop is closed' is contained here:
E           Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E           L0 async attempt 1/3 failed for doc_0.md: Async LLM call failed: Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type': 'invalid_request_error', 'code': 'invalid_api_key'}}
E           Async: Failed to call OpenAI/Provider (gpt-4o-mini): Error code: 401 - {'error': {'message': 'Simulated 401 unauthorized response', 'type':...
E         
E         ...Full output truncated (281 lines hidden), use '-vv' to show

tests\test_llm_egress_guard.py:582: AssertionError
============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_llm_egress_guard.py::test_s6_clients_are_always_closed_even_on_exception
FAILED tests/test_llm_egress_guard.py::test_s7_subprocess_asyncio_run_401_no_unclosed_loop_tracebacks
================ 2 failed, 12 deselected, 1 warning in 10.58s =================
```

### 5.5 Mutação (iv): Remover Instalação do Filtro em `setup_logging` (`R5` falha)
#### `scratch/evidencia_4_2h/p5_mut4_r5.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: c:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items / 4 deselected / 1 selected

tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent FAILED [100%]

================================== FAILURES ===================================
__________ test_r5_setup_logging_installs_factory_and_is_idempotent ___________

    def test_r5_setup_logging_installs_factory_and_is_idempotent() -> None:
        """R5: setup_logging instala o filtro/factory e chamá-lo duas vezes não duplica nem empilha wrappers."""
        main_mod.setup_logging("INFO")
        factory_after_first = logging.getLogRecordFactory()
    
        main_mod.setup_logging("INFO")
        factory_after_second = logging.getLogRecordFactory()
    
        assert factory_after_first is factory_after_second, (
            "Chamar setup_logging duas vezes não deve empilhar novas factories"
        )
>       assert getattr(factory_after_second, "_grafo_secret_redacting", False) is True, (
            "A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True"
        )
E       AssertionError: A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True
E       assert False is True
E        +  where False = getattr(<class 'logging.LogRecord'>, '_grafo_secret_redacting', False)

tests\test_secret_redaction.py:138: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_secret_redaction.py::test_r5_setup_logging_installs_factory_and_is_idempotent
======================= 1 failed, 4 deselected in 0.22s =======================
```

### 5.6 Mutação (v): Inserir Token de Chave Falsa em Arquivo de `scratch/` (`4c` falha)
#### `scratch/evidencia_4_2h/p5_mut5_4c.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: c:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits FAILED [100%]

================================== FAILURES ===================================
____________________ test_no_secrets_in_scratch_or_audits _____________________

    def test_no_secrets_in_scratch_or_audits() -> None:
        """Garante zero achados de segredos ou fragmentos de chaves em scratch/ e audits/."""
        scanner, repo_root = _load_scanner()
        findings, scanned_count = scanner.scan_files(repo_root=repo_root, include_untracked=True)
        assert scanned_count > 0, "O scanner deveria ter varrido pelo menos 1 arquivo em scratch/ ou audits/."
    
        if findings:
            summary_lines = []
            for rel_path, hits in sorted(findings.items()):
                pats = sorted({pat_name for _, pat_name, _ in hits})
                lines = sorted({lineno for lineno, _, _ in hits})
                summary_lines.append(
                    f"{rel_path}: {len(hits)} hit(s) on line(s) {lines[:10]} patterns={pats}"
                )
>           raise AssertionError(
                f"Encontrados padrões de segredo em {len(findings)} arquivo(s):\n"
                + "\n".join(summary_lines)
            )
E           AssertionError: Encontrados padrões de segredo em 1 arquivo(s):
E           scratch/_temp_mut5_secret_probe.txt: 1 hit(s) on line(s) [1] patterns=['AQ_KEY_FRAGMENT']

tests\test_no_secrets_in_tracked_files.py:38: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_no_secrets_in_tracked_files.py::test_no_secrets_in_scratch_or_audits
============================== 1 failed in 0.76s ==============================
```

---

## 6. PASSO 6 — PROVA DE REDE COM TRIPWIRE PROXY (E2E) E HARNESS F4-017

### 6.1 Passo 6A — Tripwire Proxy E2E (`E1`, `E2`, `E3`, $n=3$ sequenciais no Commit Antigo `96ba4d0` e no `HEAD` Novo)
#### `scratch/evidencia_4_2h/p6_tripwire_summary.txt`
```text
=== PASSO 6A: PROVA DE REDE COM TRIPWIRE PROXY (E2E MCP STDIO) ===
Commit antigo (worktree): 96ba4d0
Commit novo (HEAD):       6b3202b

Commit    | Cen | Rep | St   | t(s)   | Nodes | Vecs | SumNULL | Sum!=NULL | PrxTot | OpenAI | Google | LoopCl | TaskEx | ERR  | WARN
-------------------------------------------------------------------------------------------------------------------------------------
old_96ba4d0 | E1  | 1   | OK   | 41.77  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E1  | 2   | OK   | 36.12  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E1  | 3   | OK   | 37.42  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E2  | 1   | OK   | 37.01  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E2  | 2   | OK   | 38.50  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E2  | 3   | OK   | 38.50  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E3  | 1   | OK   | 36.93  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E3  | 2   | OK   | 38.05  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
old_96ba4d0 | E3  | 3   | OK   | 34.52  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
new_6b3202b | E1  | 1   | OK   | 16.61  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 0   
new_6b3202b | E1  | 2   | OK   | 15.75  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 0   
new_6b3202b | E1  | 3   | OK   | 17.39  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 0   
new_6b3202b | E2  | 1   | OK   | 16.70  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 1   
new_6b3202b | E2  | 2   | OK   | 16.72  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 1   
new_6b3202b | E2  | 3   | OK   | 16.81  | 4     | 3    | 4       | 0         | 0      | 0      | 0      | 0      | 0      | 0    | 1   
new_6b3202b | E3  | 1   | OK   | 34.82  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
new_6b3202b | E3  | 2   | OK   | 34.38  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
new_6b3202b | E3  | 3   | OK   | 34.11  | 4     | 3    | 4       | 0         | 27     | 27     | 0      | 0      | 0      | 12   | 9   
-------------------------------------------------------------------------------------------------------------------------------------

=== DETALHAMENTO DE EVENTOS DO PROXY E CONTAGEM DE ERROR / WARNING POR EXECUÇÃO ===

[old_96ba4d0 | E1 | rep=1] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:06:22.692332+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:06:22.692759+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:06:22.693490+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:06:23.083103+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:06:23.113737+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (none): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E1 | rep=2] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:07:04.374270+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:04.374482+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:04.375978+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:04.770915+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:04.802091+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (none): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E1 | rep=3] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:07:41.635881+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:41.636153+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:41.636358+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:42.028472+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:07:42.063163+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (none): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E2 | rep=1] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:08:18.829083+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:18.829537+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:18.829660+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:19.234696+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:19.284121+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E2 | rep=2] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:08:58.297120+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:58.297327+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:58.299487+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:58.707147+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:08:58.721609+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E2 | rep=3] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:09:35.715091+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:09:35.715343+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:09:35.715549+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:09:36.150071+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:09:36.161548+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E3 | rep=1] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:10:14.955910+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:14.956076+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:14.956579+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:15.343093+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:15.407473+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E3 | rep=2] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:10:53.103641+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:53.103846+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:53.104041+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:53.514865+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:10:53.515117+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1}

[old_96ba4d0 | E3 | rep=3] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:11:30.766277+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:11:30.766568+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:11:30.766821+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:11:31.185864+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:11:31.276420+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[new_6b3202b | E1 | rep=1] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (0 total): {}

[new_6b3202b | E1 | rep=2] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (0 total): {}

[new_6b3202b | E1 | rep=3] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (0 total): {}

[new_6b3202b | E2 | rep=1] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (1 total): {"│ grafo-concierge.summarizer   │ Modelo LLM 'gpt-4o-mini' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_P...": 1}

[new_6b3202b | E2 | rep=2] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (1 total): {"│ grafo-concierge.summarizer   │ Modelo LLM 'gpt-4o-mini' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_P...": 1}

[new_6b3202b | E2 | rep=3] proxy_total=0 targets=[]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (0 total): {}
  WARNING lines (1 total): {"│ grafo-concierge.summarizer   │ Modelo LLM 'gpt-4o-mini' sem provedor explícito e sem base_url: defina GRAFO_LLM_PROVIDER (ex.: GRAFO_LLM_P...": 1}

[new_6b3202b | E3 | rep=1] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:13:49.280272+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:13:49.280410+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:13:49.281954+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:13:49.699770+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:13:49.754189+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1}

[new_6b3202b | E3 | rep=2] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:14:24.445069+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:24.445264+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:24.447459+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:24.870368+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:24.920830+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1}

[new_6b3202b | E3 | rep=3] proxy_total=27 targets=['CONNECT api.openai.com:443']
  Amostra eventos proxy (ate 5): [{"timestamp": "2026-11-01T14:14:59.501495+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:59.501706+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:59.501880+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:59.925849+00:00", "method": "CONNECT", "target": "api.openai.com:443"}, {"timestamp": "2026-11-01T14:14:59.967231+00:00", "method": "CONNECT", "target": "api.openai.com:443"}]
  stderr: Event loop is closed=0, Task exception was never retrieved=0
  ERROR lines (12 total): {"│ grafo-concierge.summarizer   │ Async: Failed to call OpenAI/Provider (gpt-4o-mini): Connection error.": 9, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for politica_seguranca.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for pipeline_ingestao.md — generating Dumb Summary.": 1, "│ grafo-concierge.summarizer   │ L0 async: all attempts failed for arquitetura_rede.md — generating Dumb Summary.": 1}
  WARNING lines (9 total): {"│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 1/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 2/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for politica_seguranca.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for pipeline_ingestao.md: Async LLM call failed: Connection error.": 1, "│ grafo-concierge.summarizer   │ L0 async attempt 3/3 failed for arquitetura_rede.md: Async LLM call failed: Connection error.": 1}
```

**Observação Técnica sobre `Event loop is closed` no Subprocesso Curto vs. Sessão Longa:**
- No commit antigo (`old_96ba4d0`), cada execução de `E1`, `E2` e `E3` disparou **27 requisições `CONNECT api.openai.com:443`** no Tripwire Proxy (`3 arquivos × 3 tentativas do tenacity × 3 tentativas internas do SDK openai = 27`), **12 linhas `ERROR`** (`9` falhas de chamada OpenAI + `3` quedas para Dumb Summary) e **9 linhas `WARNING`** (`3 arquivos × 3 tentativas`). Como o subprocesso de teste encerrou logo após `count_embeddings`, o coletor de lixo do CPython (`gc`) pode não executar um ciclo de coleta dos objetos `httpx.AsyncClient` órfãos antes do término do processo (motivo pelo qual `test_s7_orchestrator_asyncio_run_closes_clients_no_unraisable_loop_closed` em `tests/test_llm_egress_guard.py` invoca `gc.collect()` explicitamente após `asyncio.run`, reproduzindo deterministamente o `RuntimeError: Event loop is closed` sem `async with` e provando `0` ocorrências com `async with`).
- No commit novo (`new_6b3202b`), `E1` (`GRAFO_LLM_MODEL=none`) e `E2` (`GRAFO_LLM_MODEL=gpt-4o-mini` sem provedor explícito) geraram **0 requisições no proxy** (`PrxTot=0, OpenAI=0, Google=0`), `0` linhas `ERROR`, e persistiram `nodes=4, vecs=3, SumNULL=4, Sum!=NULL=0`. Já `E3` (`GRAFO_LLM_PROVIDER=openai` explícito) gerou as **27 requisições `CONNECT api.openai.com:443`** esperadas, comprovando que a escolha explícita do provedor funciona e respeita o proxy.

### 6.2 Passo 6B — Harness de Regressão F4-017 (`search-first` e `mine`, $n=3$ por cenário, sequencial) em `venv_mcp127` e `venv_mcp130_full` com `GRAFO_LLM_MODEL=none`
#### `scratch/evidencia_4_2h/p6_f4_017_regression.txt`
```text
=== PASSO 6B: HARNESS F4-017 EM venv_mcp127 E venv_mcp130_full (GRAFO_LLM_MODEL=none) ===
Commit: 6b3202b

Venv             | MCP    | Cenário      | Rep | Classe   | t_init | t_crit | t_sec | Vecs | NO-OP | LoopCl | TaskEx | ERR | WARN
---------------------------------------------------------------------------------------------------------------------------------
venv_mcp127      | 1.27.0 | search-first | 1   | OK       | 3.02   | 11.88  | 0.01  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | search-first | 2   | OK       | 2.51   | 11.26  | 0.01  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | search-first | 3   | OK       | 2.43   | 11.21  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 1   | OK       | 2.63   | 11.73  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 2   | OK       | 2.62   | 11.7   | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp127      | 1.27.0 | mine         | 3   | OK       | 2.68   | 12.27  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 1   | OK       | 2.48   | 11.7   | 0.01  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 2   | OK       | 2.44   | 11.51  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | search-first | 3   | OK       | 2.41   | 11.47  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 1   | OK       | 2.74   | 12.83  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 2   | OK       | 2.69   | 11.9   | 0.02  | 13   | False | 0      | 0      | 0   | 0   
venv_mcp130_full | 1.30.0 | mine         | 3   | OK       | 2.69   | 11.98  | 0.02  | 13   | False | 0      | 0      | 0   | 0   
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

## 7. VERIFICAÇÃO FINAL DE SEGREDOS, SINCRONIZAÇÃO GIT E LIMITAÇÕES (O QUE NÃO FOI VERIFICADO)

### 7.1 Execução Final do Scanner `scratch/tools/scan_secrets.py` e Teste `test_no_secrets_in_tracked_files.py`
#### `scratch/evidencia_4_2h/p7_final_scan_secrets.txt`
```text
scanned_files=1010

files_with_findings=0

total_pattern_hits=0
```

### 7.2 Lista Explícita do que NÃO Foi Verificado (Regra 12)
1. **Outras máquinas e sistemas operacionais:** **NÃO VERIFICADO** (todos os testes E2E desta rodada foram executados exclusivamente nesta máquina Windows local; o CI Windows executa os testes de `windows-stdin.yml` no GitHub Actions).
2. **Provedores reais de LLM com chaves válidas (OpenAI, Gemini, endpoint customizado real):** **NÃO VERIFICADO** (por força da regra dura de segredos desta rodada, nenhuma execução tentou rede real com chave real; todas as verificações usaram chaves falsas explícitas, dublês de construtores ou o Tripwire Proxy local respondendo `403`).
3. **Re-teste interativo manual no aplicativo Claude Desktop após os commits da Rodada 4.2h:** **NÃO VERIFICADO** (a verificação E2E desta rodada foi realizada via cliente MCP real `stdio_client` automatizado em `run_tripwire_e2e.py` e `run_f4_017_regression.py`).
