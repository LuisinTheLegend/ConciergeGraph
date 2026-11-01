"""tests/test_llm_egress_guard.py

Testes TDD para F4-019 e F4-020 (Rodada 4.2h):
- S1: modelo "none" ("", "off", "disabled") + chave falsa -> zero construtores, zero DNS, LLM desativado;
      orquestrador pula SUMMARIZE com summary NULL e sem "[DUMB]".
- S2: modelo "gemini-2.0-flash", Google falha ou ausente -> zero fallback para OpenAI (sync e async).
- S3: modelo "gpt-4o-mini" + chave falsa sem provedor explícito e sem base_url -> desativado + WARNING único.
- S4: GRAFO_LLM_PROVIDER=openai explícito -> cliente OpenAI criado com endpoint padrão.
- S5: base_url configurado (GRAFO_LLM_BASE_URL) -> cliente criado com esse base_url; chave "sk-or-..." sem base_url -> openrouter.ai.
- S6: fechamento -> todo cliente OpenAI/AsyncOpenAI criado é fechado (with / async with), mesmo em exceção.
- S7: subprocesso com asyncio.run contra servidor HTTP local 401 -> stderr sem "Event loop is closed" nem "Task exception was never retrieved".
- S8: chamadas com call_fn customizado continuam funcionando sem mudança.
"""

from __future__ import annotations

import asyncio
import http.server
import logging
import os
import socket
import subprocess
import sys
import threading
import types
from pathlib import Path
from typing import Any, Optional

import pytest

from ingestion.summarizer import LLMAdapter, ZoomSummarizer

FAKE_AQ_KEY = "AQ." + "FAKEFAKEFAKE0001"
FAKE_SK_KEY = "sk-" + "FAKEFAKEFAKE0001"
FAKE_OR_KEY = "sk-or-" + "v1-FAKEFAKE0001"


# ---------------------------------------------------------------------------
# Dublês de construtores e guarda de DNS
# ---------------------------------------------------------------------------

class FakeSyncCompletions:
    def __init__(self, parent: "FakeOpenAIClient") -> None:
        self._parent = parent

    def create(self, **kwargs: Any) -> Any:
        self._parent.calls.append(kwargs)
        if self._parent.fail_exc is not None:
            raise self._parent.fail_exc
        msg = types.SimpleNamespace(content='{"summary": "fake sync", "tags": ["test"]}')
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])


class FakeAsyncCompletions:
    def __init__(self, parent: "FakeAsyncOpenAIClient") -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> Any:
        self._parent.calls.append(kwargs)
        if self._parent.fail_exc is not None:
            raise self._parent.fail_exc
        msg = types.SimpleNamespace(content='{"summary": "fake async", "tags": ["test"]}')
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])


class FakeOpenAIClient:
    def __init__(
        self,
        recorder: list[dict[str, Any]],
        fail_exc: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        self.api_key = kwargs.get("api_key")
        self.base_url = kwargs.get("base_url")
        self.entered = False
        self.closed = False
        self.fail_exc = fail_exc
        self.calls: list[dict[str, Any]] = []
        self.chat = types.SimpleNamespace(completions=FakeSyncCompletions(self))
        recorder.append({
            "kind": "OpenAI",
            "base_url": self.base_url,
            "instance": self,
        })

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "FakeOpenAIClient":
        self.entered = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.closed = True
        return False


class FakeAsyncOpenAIClient:
    def __init__(
        self,
        recorder: list[dict[str, Any]],
        fail_exc: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        self.api_key = kwargs.get("api_key")
        self.base_url = kwargs.get("base_url")
        self.entered = False
        self.closed = False
        self.fail_exc = fail_exc
        self.calls: list[dict[str, Any]] = []
        self.chat = types.SimpleNamespace(completions=FakeAsyncCompletions(self))
        recorder.append({
            "kind": "AsyncOpenAI",
            "base_url": self.base_url,
            "instance": self,
        })

    async def aclose(self) -> None:
        self.closed = True

    async def __aenter__(self) -> "FakeAsyncOpenAIClient":
        self.entered = True
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.closed = True
        return False


class FakeGenAIClient:
    def __init__(
        self,
        recorder: list[dict[str, Any]],
        fail_exc: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        self.api_key = kwargs.get("api_key")
        self.fail_exc = fail_exc
        recorder.append({
            "kind": "GenAIClient",
            "base_url": None,
            "instance": self,
        })
        self.models = types.SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, **kwargs: Any) -> Any:
        if self.fail_exc is not None:
            raise self.fail_exc
        return types.SimpleNamespace(text='{"summary": "fake gemini", "tags": ["gemini"]}')


@pytest.fixture
def llm_spy(monkeypatch: pytest.MonkeyPatch):
    """Instala dublês em openai e google.genai + guarda em socket.getaddrinfo."""
    monkeypatch.delenv("GRAFO_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GRAFO_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("GRAFO_LLM_API_KEY", FAKE_AQ_KEY)

    created_clients: list[dict[str, Any]] = []
    dns_hosts: list[str] = []
    config: dict[str, Any] = {
        "openai_fail": None,
        "gemini_fail": None,
    }

    orig_getaddrinfo = socket.getaddrinfo

    def guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
        host_str = str(host)
        dns_hosts.append(host_str)
        if host_str not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(f"DNS resolution blocked by test guard for host: {host_str}")
        return orig_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)

    import openai
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kw: FakeOpenAIClient(created_clients, fail_exc=config["openai_fail"], **kw),
    )
    monkeypatch.setattr(
        openai,
        "AsyncOpenAI",
        lambda **kw: FakeAsyncOpenAIClient(created_clients, fail_exc=config["openai_fail"], **kw),
    )

    fake_genai_mod = types.ModuleType("google.genai")
    fake_genai_mod.Client = lambda **kw: FakeGenAIClient(  # type: ignore[attr-defined]
        created_clients, fail_exc=config["gemini_fail"], **kw
    )
    fake_google_pkg = types.ModuleType("google")
    fake_google_pkg.genai = fake_genai_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", fake_google_pkg)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai_mod)
    monkeypatch.setitem(sys.modules, "google.generativeai", None)

    return {
        "clients": created_clients,
        "dns_hosts": dns_hosts,
        "config": config,
    }


def _disable_google_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula ambiente sem google.genai / google.generativeai instalados (levanta ImportError)."""
    monkeypatch.setitem(sys.modules, "google", None)
    monkeypatch.setitem(sys.modules, "google.genai", None)
    monkeypatch.setitem(sys.modules, "google.generativeai", None)


# ---------------------------------------------------------------------------
# S1 — Modelo "none" ("", "off", "disabled") + chave falsa
# ---------------------------------------------------------------------------

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
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
        f"model_name={disabled_model!r} é desativação intencional e não deve emitir WARNING: {caplog.messages}"
    )

    # Mesmo se GRAFO_LLM_PROVIDER estiver definido, model_name=none deve continuar desativado
    monkeypatch.setenv("GRAFO_LLM_PROVIDER", "openai")
    adapter_with_prov = LLMAdapter(model_name=disabled_model, api_key=FAKE_AQ_KEY)
    assert getattr(adapter_with_prov, "is_enabled", None) is False

    with pytest.raises(RuntimeError):
        adapter.generate("Summarize this")

    with pytest.raises(RuntimeError):
        asyncio.run(adapter.generate_async("Summarize this"))

    assert llm_spy["clients"] == [], (
        f"Nenhum construtor de cliente deveria ser chamado para model={disabled_model!r}, "
        f"mas foram criados: {llm_spy['clients']}"
    )
    assert llm_spy["dns_hosts"] == [], (
        f"Nenhuma resolução de DNS deveria ocorrer, mas houve: {llm_spy['dns_hosts']}"
    )


def test_s1_orchestrator_skips_summarize_when_llm_disabled(
    llm_spy: dict[str, Any], tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Quando is_enabled é False, o orquestrador pula SUMMARIZE com log INFO e mantém summary NULL."""
    pytest.importorskip("chromadb")
    from storage.store import SqliteStore
    from storage.vector_store import ChromaVectorStore, EmbeddingTier
    from ingestion.orchestrator import IngestionManager

    class _StubEmbedder:
        tier = EmbeddingTier.FLASH
        dimensions = 384

        def embed(self, text: str) -> list[float]:
            return [0.1] * 384

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 384 for _ in texts]

    db_path = str(tmp_path / "test_s1_orch.db")
    chroma_dir = str(tmp_path / "chroma_s1")
    proj_dir = tmp_path / "sample_proj"
    proj_dir.mkdir()
    (proj_dir / "note.md").write_text("# Titulo\nTexto de exemplo abacaxi-zeta para ingestao.\n", encoding="utf-8")

    store = SqliteStore(db_path)
    try:
        project_uuid = "proj_s1_uuid"
        store.create_project(project_uuid, "proj-s1")
        vector_store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="col_s1")
        embedder = _StubEmbedder()

        adapter = LLMAdapter(model_name="none", api_key=FAKE_AQ_KEY)
        summarizer = ZoomSummarizer(llm_adapter=adapter, sqlite_store=store)
        mgr = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            summarizer=summarizer,
        )

        with caplog.at_level(logging.INFO, logger="grafo-concierge.orchestrator"):
            res = mgr.mine(project_uuid, str(proj_dir))

        assert res.nodes_created > 0
        assert res.embeddings_stored > 0
        assert llm_spy["clients"] == []
        assert any("LLM desativado" in r.getMessage() for r in caplog.records), (
            f"Esperado log INFO 'LLM desativado: sumários L0 não gerados', logs={caplog.messages}"
        )

        nodes = store.get_nodes_by_project(project_uuid)
        chunk_nodes = [n for n in nodes if n.get("type") != "directory"]
        assert len(chunk_nodes) > 0
        for n in chunk_nodes:
            assert n.get("summary") is None, f"Esperado summary=None quando LLM desativado, obteve {n.get('summary')!r}"
    finally:
        store.close()


# ---------------------------------------------------------------------------
# S2 — Modelo "gemini-2.0-flash", Google falha ou ausente -> ZERO OpenAI
# ---------------------------------------------------------------------------

def test_s2_gemini_failure_never_falls_back_to_openai(llm_spy: dict[str, Any]) -> None:
    llm_spy["config"]["gemini_fail"] = RuntimeError("Simulated Gemini 503 failure")
    adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)

    with pytest.raises(RuntimeError):
        adapter.generate("Prompt sync")

    with pytest.raises(RuntimeError):
        asyncio.run(adapter.generate_async("Prompt async"))

    openai_clients = [c for c in llm_spy["clients"] if c["kind"] in ("OpenAI", "AsyncOpenAI")]
    assert openai_clients == [], (
        f"Falha no Gemini NUNCA deve acionar fallback para OpenAI, mas criou: {openai_clients}"
    )


def test_s2_gemini_missing_sdk_never_falls_back_to_openai(
    llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_google_sdk(monkeypatch)

    adapter = LLMAdapter(model_name="gemini-2.0-flash", api_key=FAKE_AQ_KEY)

    with pytest.raises(RuntimeError):
        adapter.generate("Prompt sync sem SDK")

    with pytest.raises(RuntimeError):
        asyncio.run(adapter.generate_async("Prompt async sem SDK"))

    openai_clients = [c for c in llm_spy["clients"] if c["kind"] in ("OpenAI", "AsyncOpenAI")]
    assert openai_clients == [], (
        f"Ausência do SDK Gemini NUNCA deve cair para OpenAI, mas criou: {openai_clients}"
    )


# ---------------------------------------------------------------------------
# S3 — Modelo "gpt-4o-mini" + chave falsa SEM provedor explícito e SEM base_url
# ---------------------------------------------------------------------------

def test_s3_ambiguous_openai_model_without_explicit_provider_is_disabled(
    llm_spy: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="grafo-concierge.summarizer"):
        adapter = LLMAdapter(model_name="gpt-4o-mini", api_key=FAKE_SK_KEY)

    assert getattr(adapter, "is_enabled", None) is False, (
        "Sem GRAFO_LLM_PROVIDER explícito e sem base_url, gpt-4o-mini deve ficar desativado"
    )

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "GRAFO_LLM_PROVIDER" in r.getMessage()]
    assert len(warnings) == 1, (
        f"Deve emitir exatamente 1 WARNING mencionando GRAFO_LLM_PROVIDER, mas emitiu: "
        f"{[r.getMessage() for r in caplog.records]}"
    )

    with pytest.raises(RuntimeError):
        adapter.generate("Prompt sync")

    with pytest.raises(RuntimeError):
        asyncio.run(adapter.generate_async("Prompt async"))

    assert llm_spy["clients"] == [], (
        f"Nenhum cliente deve ser criado sem provedor explícito, mas criou: {llm_spy['clients']}"
    )


# ---------------------------------------------------------------------------
# S4 — GRAFO_LLM_PROVIDER=openai explícito
# ---------------------------------------------------------------------------

def test_s4_explicit_openai_provider_creates_openai_client(
    llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_google_sdk(monkeypatch)
    monkeypatch.setenv("GRAFO_LLM_PROVIDER", "openai")
    adapter = LLMAdapter(model_name="gpt-4o-mini", api_key=FAKE_SK_KEY)
    assert getattr(adapter, "is_enabled", True) is True

    res_sync = adapter.generate("Hello sync")
    assert "fake sync" in res_sync

    res_async = asyncio.run(adapter.generate_async("Hello async"))
    assert "fake async" in res_async

    openai_clients = [c for c in llm_spy["clients"] if c["kind"] in ("OpenAI", "AsyncOpenAI")]
    assert [c["kind"] for c in openai_clients] == ["OpenAI", "AsyncOpenAI"]
    assert all(c["base_url"] is None for c in openai_clients)
    assert all(c["instance"].api_key == FAKE_SK_KEY for c in openai_clients)


# ---------------------------------------------------------------------------
# S5 — base_url configurado e preservação de sk-or-... (OpenRouter)
# ---------------------------------------------------------------------------

def test_s5_custom_base_url_and_openrouter_preserved(
    llm_spy: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_google_sdk(monkeypatch)
    # Caso A: base_url configurado
    monkeypatch.setenv("GRAFO_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    adapter_base = LLMAdapter(
        model_name="llama3-local",
        api_key=FAKE_SK_KEY,
        base_url="http://127.0.0.1:11434/v1",
    )
    assert getattr(adapter_base, "is_enabled", True) is True

    adapter_base.generate("Sync local")
    asyncio.run(adapter_base.generate_async("Async local"))

    assert len(llm_spy["clients"]) == 2
    assert all(c["base_url"] == "http://127.0.0.1:11434/v1" for c in llm_spy["clients"])

    # Caso B: Chave sk-or-... sem base_url -> vai para openrouter.ai
    llm_spy["clients"].clear()
    monkeypatch.delenv("GRAFO_LLM_BASE_URL", raising=False)
    adapter_or = LLMAdapter(model_name="anthropic/claude-3-haiku", api_key=FAKE_OR_KEY)
    assert getattr(adapter_or, "is_enabled", True) is True

    adapter_or.generate("Sync openrouter")
    asyncio.run(adapter_or.generate_async("Async openrouter"))

    assert len(llm_spy["clients"]) == 2
    assert all(c["base_url"] == "https://openrouter.ai/api/v1" for c in llm_spy["clients"])


# ---------------------------------------------------------------------------
# S6 — Fechamento (with / async with) mesmo quando lança exceção
# ---------------------------------------------------------------------------

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
        assert inst.entered is True, f"Cliente #{idx} ({entry['kind']}) não usou context manager (__enter__/__aenter__)"
        assert inst.closed is True, f"Cliente #{idx} ({entry['kind']}) não foi fechado (__exit__/__aexit__)"


# ---------------------------------------------------------------------------
# S7 — Subprocesso: asyncio.run contra servidor local 401 sem tracebacks de loop
# ---------------------------------------------------------------------------

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
    assert "Event loop is closed" not in proc.stderr, (
        f"stderr contém 'Event loop is closed':\n{proc.stderr}"
    )
    assert "Task exception was never retrieved" not in proc.stderr, (
        f"stderr contém 'Task exception was never retrieved':\n{proc.stderr}"
    )


# ---------------------------------------------------------------------------
# S8 — Chamadas com call_fn customizado continuam funcionando sem mudança
# ---------------------------------------------------------------------------

def test_s8_custom_call_fn_works_unchanged(llm_spy: dict[str, Any]) -> None:
    calls: list[tuple[str, int]] = []

    def my_call_fn(prompt: str, max_tokens: int) -> str:
        calls.append((prompt, max_tokens))
        return '{"summary": "custom summary", "tags": ["custom"]}'

    adapter = LLMAdapter(model_name="none", api_key=FAKE_AQ_KEY, call_fn=my_call_fn)
    assert getattr(adapter, "is_enabled", True) is True

    res_sync = adapter.generate("p1", max_tokens=111)
    res_async = asyncio.run(adapter.generate_async("p2", max_tokens=222))

    assert "custom summary" in res_sync
    assert "custom summary" in res_async
    assert calls == [("p1", 111), ("p2", 222)]
    assert llm_spy["clients"] == []
