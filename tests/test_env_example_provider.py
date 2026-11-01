"""tests/test_env_example_provider.py

Teste unitário para F4-023 (Item 2 da Rodada 4.2h-2):
- .env.example NÃO deve trazer GRAFO_LLM_PROVIDER ativo (descomentado).
- Deve conter a linha comentada `# GRAFO_LLM_PROVIDER=` e aviso explícito de que,
  se o modelo não começar com "gemini-", o provedor deve ser definido explicitamente,
  senão o LLM fica desativado.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


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
    assert not active_lines, (
        f".env.example contém GRAFO_LLM_PROVIDER ativo nas linhas: {active_lines}"
    )

    commented_lines = [
        line
        for line in lines
        if re.match(r"^\s*#\s*GRAFO_LLM_PROVIDER\s*=", line)
    ]
    assert commented_lines, (
        ".env.example deve manter # GRAFO_LLM_PROVIDER=... comentado como exemplo."
    )
    lower_text = text.lower()
    assert "gemini-" in text and ("desativado" in lower_text or "disabled" in lower_text), (
        ".env.example deve avisar que modelos que não começam com 'gemini-' exigem provedor explícito, senão o LLM fica desativado."
    )
