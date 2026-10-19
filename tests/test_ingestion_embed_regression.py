"""
tests/test_ingestion_embed_regression.py — Testes de regressão e guarda para F4-006.

Valida:
1. Regressão do F4-006: Mineração completa com RichHandler instalado no logger raiz
   deve processar chunks, gerar embeddings e persistir vetores sem estourar TypeError.
2. Teste-guarda: Varredura AST sobre todo o código de produção garantindo que
   nenhuma chamada de log possua mais argumentos que especificadores '%'.
"""

import ast
import logging
import re
from pathlib import Path

import pytest
from rich.logging import RichHandler

from storage import SqliteStore, ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager


class StubEmbeddingManager:
    """Stub determinístico de EmbeddingManager para testes de unidade/regressão."""
    def __init__(self):
        self.tier = EmbeddingTier.FLASH
        self.model_name = "stub-embedder"
        self.dimensions = 384

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * self.dimensions for _ in texts]

    def embed(self, text: str) -> list[float]:
        return [0.05] * self.dimensions


def test_f4_006_mining_with_rich_handler_regression(tmp_path: Path):
    """F4-006: RichHandler propaga TypeError quando logger.info possui argumentos

    sobressalentes sem especificador correspondente. A mineração deve concluir
    completamente, gravando nós no SQLite e vetores no ChromaDB.
    """
    root_logger = logging.getLogger()
    rich_handler = RichHandler(rich_tracebacks=True)
    rich_handler.setLevel(logging.INFO)
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(rich_handler)

    try:
        # Fixture de arquivos: 3 .py e 1 .md
        src_dir = tmp_path / "project_src"
        src_dir.mkdir()
        (src_dir / "mod_alpha.py").write_text("def alpha_func():\n    return 1\n", encoding="utf-8")
        (src_dir / "mod_beta.py").write_text("class BetaClass:\n    def beta_method(self):\n        pass\n", encoding="utf-8")
        (src_dir / "mod_gamma.py").write_text("gamma_val = 100\ndef gamma_func():\n    return gamma_val * 2\n", encoding="utf-8")
        (src_dir / "guide.md").write_text("# Project Guide\nThis is project documentation.\n", encoding="utf-8")

        # Configura banco SQLite e Chroma isolados em tmp_path
        db_path = tmp_path / "test_concierge.db"
        chroma_dir = tmp_path / "test_chroma"
        chroma_dir.mkdir()

        store = SqliteStore(str(db_path))
        embedder = StubEmbeddingManager()
        vector_store = ChromaVectorStore(
            persist_dir=str(chroma_dir),
            collection_name="regression_f4_006",
            embedding_manager=embedder,
        )

        project_uuid = "proj-regression-f4006"
        store.create_project(project_uuid, "Regression F4-006", str(src_dir))

        manager = IngestionManager(
            sqlite_store=store,
            vector_store=vector_store,
            embedding_manager=embedder,
            summarizer=None,
        )

        # Executa mineração — deve passar por todos os 8 passos sem estourar TypeError
        result = manager.mine(project_uuid, str(src_dir))

        assert result.files_processed > 0, "Deveria ter processado arquivos"
        assert result.nodes_created > 0, "Deveria ter criado nós no SQLite"
        assert result.embeddings_stored > 0, "Deveria ter gravado embeddings no Chroma"
        assert len(result.errors) == 0, f"Erros durante mineração: {result.errors}"

        # Verifica persistência no ChromaVectorStore
        chroma_count = vector_store.count()
        assert chroma_count > 0, "ChromaVectorStore deve conter vetores indexados"
        assert chroma_count == result.embeddings_stored, "Contagem do Chroma deve bater com embeddings_stored"

        store.close()
    finally:
        root_logger.removeHandler(rich_handler)


def test_guard_no_mismatched_log_format_in_production():
    """Teste-guarda: Varredura AST sobre todo o código de produção garantindo que

    nenhuma chamada de log contenha mais argumentos do que especificadores '%'.
    """
    repo_root = Path(__file__).parent.parent.resolve()
    production_dirs = ["core", "ingestion", "interface", "services", "storage", "agent", "agents"]
    root_files = ["main.py"]

    files_to_scan: list[Path] = []
    for d in production_dirs:
        dp = repo_root / d
        if dp.exists():
            files_to_scan.extend(dp.rglob("*.py"))
    for rf in root_files:
        fp = repo_root / rf
        if fp.exists():
            files_to_scan.append(fp)

    files_to_scan = sorted(set(files_to_scan))
    assert len(files_to_scan) > 0, "Nenhum arquivo de produção encontrado para varredura"

    specifier_re = re.compile(r"%(?:%|(?:\([a-zA-Z0-9_]+\))?[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrsa%])")
    log_methods = {"debug", "info", "warning", "warn", "error", "critical", "exception"}

    mismatches = []
    for filepath in files_to_scan:
        rel_path = filepath.relative_to(repo_root).as_posix()
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = None
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name not in log_methods:
                continue

            if not node.args:
                continue

            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                fmt_str = first_arg.value
                matches = specifier_re.findall(fmt_str)
                expected_args = sum(1 for m in matches if m != "%%")
                actual_args = len(node.args) - 1

                if actual_args > expected_args:
                    mismatches.append(
                        f"{rel_path}:{node.lineno} -> {func_name}('{fmt_str}', ...) "
                        f"[esperado: {expected_args}, fornecido: {actual_args}]"
                    )

    assert mismatches == [], (
        f"Encontradas {len(mismatches)} chamada(s) de log com argumentos a mais que '%':\n"
        + "\n".join(f"  - {m}" for m in mismatches)
    )
