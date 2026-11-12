"""
tests/test_stress_components_reuse.py — Caracterização do ciclo de reuso de
`stress_components` / `setup_workspace()` + `bootstrap()` + teardown (F4-034).

IMPORTANTE (Regra 15 / Rodada 4.4g Bloco 3):
- `test_stress_components_reuse_cycle_characterization` é um teste de
  **caracterização do ciclo de reuso, não prova de correção**: na base `26a43e2`
  e em 60 execuções sequenciais da suíte no Windows (30 Py3.10 + 30 Py3.12),
  o erro intermitente do chromadb (`InternalError`) observado no CI Ubuntu 3.10
  (run 43075938190) NÃO foi reproduzido (`0/60`), portanto não existe teste
  vermelho reproduzindo `F4-034`.
- `test_bootstrap_uses_distinct_chroma_subdir_per_call` verifica apenas a
  invariante estrutural do endurecimento defensivo aplicado no Bloco 2
  (subdiretório Chroma exclusivo por chamada em `bootstrap()`), também sem
  alegar prova de causa para `F4-034`.
"""

import os
import shutil

from tests.memory_stress_test import (
    CHROMA_PATH,
    PROJECT_UUID,
    TEST_DIR,
    bootstrap,
    setup_workspace,
)


def _run_one_cycle() -> tuple[str | None, set[str]]:
    """Executa um ciclo setup_workspace -> bootstrap -> verificação -> teardown."""
    assert os.environ.get("GRAFO_LIGHTWEIGHT_MODE", "false").lower() != "true"
    setup_workspace()
    before_subdirs = (
        {
            d
            for d in os.listdir(CHROMA_PATH)
            if d.startswith("run_") and os.path.isdir(os.path.join(CHROMA_PATH, d))
        }
        if os.path.isdir(CHROMA_PATH)
        else set()
    )

    store = None
    try:
        store, vector, _embedder, _manager, _janitor = bootstrap()

        # Garante que o ChromaDB NÃO operou em modo NO-OP (lightweight)
        assert vector._available is True
        assert vector._client is not None
        assert vector._collection is not None
        assert vector.count() == 0
        assert store.get_project(PROJECT_UUID) is not None

        after_subdirs = (
            {
                d
                for d in os.listdir(CHROMA_PATH)
                if d.startswith("run_") and os.path.isdir(os.path.join(CHROMA_PATH, d))
            }
            if os.path.isdir(CHROMA_PATH)
            else set()
        )
        client_id = getattr(vector._client, "_identifier", None)
        return client_id, (after_subdirs - before_subdirs)
    finally:
        if store is not None:
            try:
                store.close()
            except Exception:
                pass
        try:
            shutil.rmtree(TEST_DIR, ignore_errors=True)
        except Exception:
            pass


def test_stress_components_reuse_cycle_characterization():
    """Caracterização do ciclo de reuso, não prova de correção (F4-034 / Bloco 3).

    Executa setup_workspace(), bootstrap() e o teardown de stress_components
    duas vezes seguidas no mesmo processo sem GRAFO_LIGHTWEIGHT_MODE,
    restaurando o ambiente ao final.
    """
    prev_lw = os.environ.get("GRAFO_LIGHTWEIGHT_MODE")
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
    try:
        _run_one_cycle()
        _run_one_cycle()
    finally:
        if prev_lw is None:
            os.environ.pop("GRAFO_LIGHTWEIGHT_MODE", None)
        else:
            os.environ["GRAFO_LIGHTWEIGHT_MODE"] = prev_lw
        try:
            shutil.rmtree(TEST_DIR, ignore_errors=True)
        except Exception:
            pass


def test_bootstrap_uses_distinct_chroma_subdir_per_call():
    """Verifica a invariante estrutural do endurecimento defensivo do Bloco 2 (F4-034).

    Não reproduz nem prova causa do bug intermitente do chromadb; valida apenas que
    duas chamadas consecutivas a bootstrap() no mesmo processo utilizam subdiretórios
    Chroma exclusivos (e identificadores SharedSystemClient distintos) quando o modo
    lightweight está desligado, restaurando o ambiente ao final.
    """
    prev_lw = os.environ.get("GRAFO_LIGHTWEIGHT_MODE")
    os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "false"
    try:
        id_1, subdirs_1 = _run_one_cycle()
        id_2, subdirs_2 = _run_one_cycle()

        assert len(subdirs_1) == 1, f"Esperava 1 subdiretório Chroma exclusivo na 1ª chamada, obteve {subdirs_1}"
        assert len(subdirs_2) == 1, f"Esperava 1 subdiretório Chroma exclusivo na 2ª chamada, obteve {subdirs_2}"
        assert subdirs_1.isdisjoint(subdirs_2), f"Subdiretórios Chroma colidiram: {subdirs_1} vs {subdirs_2}"
        if id_1 is not None and id_2 is not None:
            assert id_1 != id_2, f"Identificadores PersistentClient colidiram: {id_1} == {id_2}"
    finally:
        if prev_lw is None:
            os.environ.pop("GRAFO_LIGHTWEIGHT_MODE", None)
        else:
            os.environ["GRAFO_LIGHTWEIGHT_MODE"] = prev_lw
        try:
            shutil.rmtree(TEST_DIR, ignore_errors=True)
        except Exception:
            pass
