"""tests/test_lazy_ml_imports.py

Valida o import tardio (lazy loading) de sentence_transformers e torch (F4-015).
Garante que o arranque do subsistema de storage e o bootstrap do servidor MCP
ocorram sem importar as bibliotecas pesadas de ML ate a primeira operacao de embedding.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_t1_storage_imports_do_not_import_sentence_transformers_or_torch():
    """T1: Importar storage, SqliteStore, EmbeddingManager e ChromaVectorStore nao deve
    carregar sentence_transformers nem torch em sys.modules."""
    code = f"""
import sys
import site
user_site = site.getusersitepackages()
if user_site:
    site.addsitedir(user_site)

sys.path.insert(0, {repr(str(REPO_ROOT))})

import importlib.util
if importlib.util.find_spec("sentence_transformers") is None:
    print("SKIP: sentence_transformers nao instalado")
    sys.exit(0)

import storage
from storage import SqliteStore, EmbeddingManager, ChromaVectorStore

st_imported = "sentence_transformers" in sys.modules
torch_imported = "torch" in sys.modules

if st_imported or torch_imported:
    print(f"FAIL: sentence_transformers={{st_imported}}, torch={{torch_imported}}")
    sys.exit(1)
print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if "SKIP:" in result.stdout:
        pytest.skip("sentence_transformers nao instalado no ambiente de teste")
    assert result.returncode == 0, (
        f"T1 falhou: sentence_transformers ou torch foram importados antecipadamente.\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_t2_bootstrap_does_not_import_sentence_transformers_or_torch():
    """T2: Executar o bootstrap do servidor MCP completo (sem operacao de embedding)
    nao deve carregar sentence_transformers nem torch em sys.modules."""
    code = f"""
import os
import sys
import site
import tempfile

user_site = site.getusersitepackages()
if user_site:
    site.addsitedir(user_site)

sys.path.insert(0, {repr(str(REPO_ROOT))})

import importlib.util
if importlib.util.find_spec("sentence_transformers") is None:
    print("SKIP: sentence_transformers nao instalado")
    sys.exit(0)

tmp_dir = tempfile.mkdtemp(prefix="grafo_t2_")
os.environ["GRAFO_DB_PATH"] = os.path.join(tmp_dir, "t2_test.db")
os.environ["GRAFO_CHROMA_PATH"] = os.path.join(tmp_dir, "t2_chroma")
os.environ["GRAFO_CHROMA_COLLECTION"] = "t2_collection"
os.environ["GRAFO_TRANSPORT"] = "stdio"
os.environ["GRAFO_LOG_LEVEL"] = "WARNING"

from main import bootstrap
server, janitor, store = bootstrap()
store.close()

st_imported = "sentence_transformers" in sys.modules
torch_imported = "torch" in sys.modules

if st_imported or torch_imported:
    print(f"FAIL: sentence_transformers={{st_imported}}, torch={{torch_imported}}")
    sys.exit(1)
print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if "SKIP:" in result.stdout:
        pytest.skip("sentence_transformers nao instalado no ambiente de teste")
    assert result.returncode == 0, (
        f"T2 falhou: bootstrap carregou sentence_transformers ou torch.\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_t3_missing_sentence_transformers_raises_embedding_error(monkeypatch):
    """T3 (preservacao): Quando sentence_transformers esta indisponivel/quebrado
    (sys.modules['sentence_transformers'] = None), EmbeddingManager._load_model()
    deve levantar EmbeddingError contendo mensagem sobre sentence-transformers."""
    from storage.vector_store import EmbeddingError, EmbeddingManager, EmbeddingTier

    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    embedder._model = None

    with pytest.raises(EmbeddingError) as exc_info:
        embedder._load_model()

    assert "sentence-transformers" in str(exc_info.value).lower() or "sentence_transformers" in str(exc_info.value).lower()


def test_t4_stub_sentence_transformer_used_by_lazy_load(monkeypatch):
    """T4: Injetar um stub de SentenceTransformer em sys.modules deve fazer com que
    _load_model() use o stub dinamicamente e embed() devolva o vetor do stub."""
    from storage.vector_store import EmbeddingManager, EmbeddingTier

    class StubVector:
        def __init__(self, data):
            self._data = data

        def tolist(self):
            return self._data

    class StubModel:
        is_stub = True

        def __init__(self, model_name: str):
            self.model_name = model_name

        def encode(self, texts, **kwargs):
            return StubVector([0.42] * 384)

    stub_mod = types.ModuleType("sentence_transformers")
    stub_mod.SentenceTransformer = StubModel

    monkeypatch.setitem(sys.modules, "sentence_transformers", stub_mod)

    embedder = EmbeddingManager(tier=EmbeddingTier.FLASH)
    embedder._model = None

    embedder._load_model()

    # Confirma que o modelo carregado e o stub injetado dinamicamente
    assert getattr(embedder._model, "is_stub", False) is True, (
        "O modelo carregado nao e o stub injetado; o import nao foi realizado dinamicamente em _load_model()."
    )

    vec = embedder.embed("texto de teste para o stub")
    assert vec is not None
    assert len(vec) == 384
    assert vec[0] == 0.42


def test_t5_availability_flags_exist_and_are_bool():
    """T5 (preservacao de contrato): CHROMADB_AVAILABLE e SENTENCE_TRANSFORMERS_AVAILABLE
    continuam existindo em storage.vector_store como booleans."""
    import storage.vector_store as vs

    assert hasattr(vs, "CHROMADB_AVAILABLE"), "CHROMADB_AVAILABLE ausente em storage.vector_store"
    assert isinstance(vs.CHROMADB_AVAILABLE, bool), "CHROMADB_AVAILABLE nao e bool"

    assert hasattr(vs, "SENTENCE_TRANSFORMERS_AVAILABLE"), "SENTENCE_TRANSFORMERS_AVAILABLE ausente em storage.vector_store"
    assert isinstance(vs.SENTENCE_TRANSFORMERS_AVAILABLE, bool), "SENTENCE_TRANSFORMERS_AVAILABLE nao e bool"
