"""tests/test_secret_redaction.py

Testes TDD para o filtro de redação de segredos nos logs (Rodada 4.2h - Passo 4d):
- R1: chave na msg (sk-..., AQ...., AIza..., Bearer <token>) -> redigida para [REDACTED]
- R2: chave nos args (logger.info("Key: %s", key)) -> redigida para [REDACTED]
- R3: chave dentro de exceção formatada por logger.exception -> redigida para [REDACTED]
- R4: valor exato de GRAFO_LLM_API_KEY / GRAFO_API_KEY do ambiente (>= 8 chars) -> redigido
- R5: setup_logging instala o mecanismo globalmente (qualquer handler, inclusive handlers estilo RichHandler
      que leem record.getMessage() / exc_text) e chamá-lo duas vezes é idempotente.
"""

from __future__ import annotations

import io
import logging
import uuid
import pytest

import main as main_mod

FAKE_SK = "sk-" + "FAKEFAKEFAKE0001"
FAKE_AQ = "AQ." + "FAKEFAKEFAKE0001"
FAKE_AIZA = "AIza" + "SyFAKEFAKEFAKE0001"
FAKE_BEARER_TOKEN = "tok_secret_99887766"


class RichLikeHandler(logging.Handler):
    """Simula um handler externo (como RichHandler do FastMCP) que não herda filtros
    do StreamHandler raiz, mas consome record.getMessage() e formatter.formatException().
    """

    def __init__(self) -> None:
        super().__init__()
        self.rendered: list[str] = []
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.rendered.append(msg)


def _make_isolated_logger() -> tuple[logging.Logger, io.StringIO, RichLikeHandler]:
    lg = logging.getLogger(f"test.redaction.{uuid.uuid4().hex[:8]}")
    lg.setLevel(logging.DEBUG)
    lg.propagate = False
    buf = io.StringIO()
    sh = logging.StreamHandler(buf)
    sh.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    rh = RichLikeHandler()
    lg.addHandler(sh)
    lg.addHandler(rh)
    return lg, buf, rh


def test_r1_secret_in_msg_is_redacted() -> None:
    """R1: chave diretamente na string msg (sk-..., AQ...., AIza..., Bearer <token>)."""
    main_mod.setup_logging("INFO")
    lg, buf, rh = _make_isolated_logger()

    lg.error(f"Falha com chaves {FAKE_SK} e {FAKE_AQ} e {FAKE_AIZA} e Authorization: Bearer {FAKE_BEARER_TOKEN}")

    stream_out = buf.getvalue()
    rich_out = "\n".join(rh.rendered)

    for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
        leaked = any(s in out_text for s in (FAKE_SK, FAKE_AQ, FAKE_AIZA, FAKE_BEARER_TOKEN))
        assert not leaked, f"R1 falhou: segredo vazou sem redação em {out_name}"
        assert "[REDACTED]" in out_text, f"R1 falhou: '[REDACTED]' ausente em {out_name}"


def test_r2_secret_in_args_is_redacted() -> None:
    """R2: chave passada via args (logger.warning('Chave: %s / %s', k1, k2))."""
    main_mod.setup_logging("INFO")
    lg, buf, rh = _make_isolated_logger()

    lg.warning("Tentativa falhou para chave %s e %s", FAKE_AQ, FAKE_SK)

    stream_out = buf.getvalue()
    rich_out = "\n".join(rh.rendered)

    for out_name, out_text in (("StreamHandler", stream_out), ("RichLikeHandler", rich_out)):
        leaked = any(s in out_text for s in (FAKE_AQ, FAKE_SK))
        assert not leaked, f"R2 falhou: segredo em args vazou sem redação em {out_name}"
        assert "[REDACTED]" in out_text, f"R2 falhou: '[REDACTED]' ausente em {out_name}"


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
        assert not leaked, f"R3 falhou: segredo na exceção vazou sem redação em {out_name}"
        assert "[REDACTED]" in out_text, f"R3 falhou: '[REDACTED]' ausente na exceção em {out_name}"


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
        assert not leaked, f"R4 falhou: valor de variável de ambiente vazou em {out_name}"
        assert "[REDACTED]" in out_text, f"R4 falhou: '[REDACTED]' ausente em {out_name}"


def test_r5_setup_logging_installs_factory_and_is_idempotent() -> None:
    """R5: setup_logging instala o filtro/factory e chamá-lo duas vezes não duplica nem empilha wrappers."""
    main_mod.setup_logging("INFO")
    factory_after_first = logging.getLogRecordFactory()

    main_mod.setup_logging("INFO")
    factory_after_second = logging.getLogRecordFactory()

    assert factory_after_first is factory_after_second, (
        "Chamar setup_logging duas vezes não deve empilhar novas factories"
    )
    assert getattr(factory_after_second, "_grafo_secret_redacting", False) is True, (
        "A LogRecordFactory instalada por setup_logging deve estar marcada com _grafo_secret_redacting=True"
    )
    root_handlers = logging.getLogger().handlers
    grafo_handlers = [h for h in root_handlers if getattr(h, "_grafo_log_handler", False)]
    count_to_check = len(grafo_handlers) if grafo_handlers else len(root_handlers)
    assert count_to_check == 1, (
        f"Root logger deve ter exatamente 1 handler do Grafo após chamadas repetidas, mas tem {count_to_check}"
    )


# ---------------------------------------------------------------------------
# Rodada 4.2h-2 — Item 1 (F4-022): Falsos positivos, positivos e paridade
# ---------------------------------------------------------------------------

NEGATIVE_CASES_F4_022: list[str] = [
    "risk-assessment-notes.md",
    "disk-cache-manifest.json",
    "task-scheduler-config.yaml",
    "C:\\proj\\desk-setup-checklist.md",
    "Crawl: 3 files",
    "mask-values-list",
]

POSITIVE_CASES_F4_022: list[str] = [
    "sk-" + "FAKEFAKEFAKE0001",
    "sk-proj-" + "FAKE_KEY_XYZ123",
    "key=sk-" + "FAKEFAKEFAKE0001",
    "(sk-" + "FAKEFAKE0001)",
    '"api_key": "sk-' + 'FAKEFAKE0001"',
    "AQ." + "FAKEFAKEFAKE0001",
    "AIza" + "FAKEFAKEFAKE00000001",
    "Bearer " + "abc123token456",
]


@pytest.mark.parametrize("neg_text", NEGATIVE_CASES_F4_022)
def test_f4_022_negative_cases_remain_identical(neg_text: str) -> None:
    """Item 1a (Negativos): nomes de arquivos e textos normais com 'sk-' interno saem idênticos."""
    main_mod.setup_logging("INFO")
    assert main_mod.redact_log_secrets(neg_text) == neg_text

    lg, buf, rh = _make_isolated_logger()
    lg.info("Processando item: %s", neg_text)
    assert f"Processando item: {neg_text}" in buf.getvalue()
    assert "[REDACTED]" not in buf.getvalue()
    assert f"Processando item: {neg_text}" in "\n".join(rh.rendered)


@pytest.mark.parametrize(
    "pos_text",
    POSITIVE_CASES_F4_022,
    ids=[f"pos_{i}" for i in range(len(POSITIVE_CASES_F4_022))],
)
def test_f4_022_positive_cases_are_redacted(pos_text: str) -> None:
    """Item 1a (Positivos): chaves isoladas ou precedidas por pontuação/aspas são redigidas."""
    main_mod.setup_logging("INFO")
    redacted = main_mod.redact_log_secrets(pos_text)
    assert redacted != pos_text, f"Esperava redação para entrada positiva, mas saiu intacta: {redacted!r}"
    assert "[REDACTED]" in redacted


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
        assert f_res == s_res == False, (  # noqa: E712
            f"Divergência ou falso positivo em caso negativo {neg!r}: filter={f_res}, scanner={s_res}"
        )

    for pos in POSITIVE_CASES_F4_022:
        f_res = filter_redacts(pos)
        s_res = scanner_matches(pos)
        assert f_res == s_res == True, (  # noqa: E712
            f"Divergência ou falso negativo em caso positivo: filter={f_res}, scanner={s_res}"
        )


# ---------------------------------------------------------------------------
# Rodada 4.2h-2 — Item 4a e 4b: Preservação de handlers alheios e R6 (exc.args)
# ---------------------------------------------------------------------------

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

        assert foreign_handler in root.handlers, (
            "Handler alheio presente no root logger foi removido por setup_logging!"
        )
        grafo_handlers = [
            h for h in root.handlers if getattr(h, "_grafo_log_handler", False) is True
        ]
        assert len(grafo_handlers) == 1, (
            f"Esperado exatamente 1 handler do Grafo após duas chamadas a setup_logging, "
            f"mas encontrou {len(grafo_handlers)}"
        )
    finally:
        if foreign_handler in root.handlers:
            root.removeHandler(foreign_handler)


def test_r6_exception_args_side_effect_documented_and_preserves_non_secret_text() -> None:
    """Item 4b (R6): docstring de _SecretRedactingLogRecord documenta o efeito colateral em exc.args,
    e apenas o trecho que casa com padrão de segredo muda em exc.args, preservando o restante.
    """
    doc = main_mod._SecretRedactingLogRecord.__doc__ or ""
    assert "exc.args" in doc and "efeito colateral" in doc.lower(), (
        "Docstring de _SecretRedactingLogRecord deve documentar explicitamente o efeito colateral em exc.args"
    )

    main_mod.setup_logging("INFO")
    lg, buf, _ = _make_isolated_logger()

    prefix = "Falha ao autenticar no arquivo risk-assessment-notes.md com chave "
    suffix = " durante etapa de ingestão (código=401)."
    captured_exc: RuntimeError | None = None

    try:
        raise RuntimeError(prefix + FAKE_SK + suffix)
    except RuntimeError as exc:
        captured_exc = exc
        lg.exception("Erro capturado no teste R6")

    assert captured_exc is not None
    assert captured_exc.args == (prefix + "[REDACTED]" + suffix,), (
        f"Apenas o segredo deveria mudar em exc.args, mas obteve: {captured_exc.args!r}"
    )
    assert (prefix + "[REDACTED]" + suffix) in buf.getvalue()


