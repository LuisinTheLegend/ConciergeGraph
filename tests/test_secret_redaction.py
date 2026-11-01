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
    assert len(logging.getLogger().handlers) == 1, (
        f"Root logger deve ter exatamente 1 handler após chamadas repetidas, mas tem {len(logging.getLogger().handlers)}"
    )

