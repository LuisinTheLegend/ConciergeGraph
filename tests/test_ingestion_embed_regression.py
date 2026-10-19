"""
tests/test_ingestion_embed_regression.py — Testes de regressão e guarda para F4-006.

Valida:
1. Regressão do F4-006: Mineração completa com RichHandler instalado no logger raiz
   deve processar chunks, gerar embeddings e persistir vetores sem estourar TypeError.
2. Teste-guarda: Varredura AST sobre todo o código de produção garantindo que
   nenhuma chamada de log possua argumentos incompatíveis com os especificadores '%'.
"""

import ast
import logging
import re
from pathlib import Path

import pytest
from rich.logging import RichHandler

from storage import SqliteStore, ChromaVectorStore, EmbeddingTier
from ingestion.orchestrator import IngestionManager


SPECIFIER_RE = re.compile(
    r"%(?:%|(?:\([a-zA-Z0-9_]+\))?[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrsa%])"
)
MAPPING_SPECIFIER_RE = re.compile(r"%\([a-zA-Z0-9_]+\)")
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "critical", "exception"}


def find_mismatched_log_calls(source: str, filename: str = "<string>") -> list[str]:
    """Varre código-fonte em busca de chamadas de log com contagem de argumentos

    incompatível com os especificadores '%' da string literal de formato.
    """
    mismatches: list[str] = []
    try:
        tree = ast.parse(source, filename=filename)
    except Exception:
        return mismatches

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = None
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        if func_name not in LOG_METHODS:
            continue

        if not node.args:
            continue

        # Chamadas com *args são ignoradas
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            continue

        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            fmt_str = first_arg.value

            # Estilo de dicionário ("%(key)s") não valida contagem posicional
            if MAPPING_SPECIFIER_RE.search(fmt_str):
                continue

            matches = SPECIFIER_RE.findall(fmt_str)
            expected_args = sum(1 for m in matches if m != "%%")
            actual_args = len(node.args) - 1

            # Detecção bidirecional: argumentos a mais ou a menos
            if actual_args != expected_args:
                mismatches.append(
                    f"{filename}:{node.lineno} -> {func_name}('{fmt_str}', ...) "
                    f"[esperado: {expected_args}, fornecido: {actual_args}]"
                )

    return mismatches


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


def test_guard_synthetic_cases():
    """Valida comportamento da função find_mismatched_log_calls sobre código sintético:

    (a) argumentos a mais são detectados;
    (b) argumentos a menos ("%d %d" com um valor) são detectados;
    (c) %% literal não conta como especificador;
    (d) estilo de dicionário ("%(a)s") não gera falso positivo;
    (e) chamadas com *args são ignoradas;
    (f) uma chamada correta não é sinalizada.
    """
    # (a) argumentos a mais são detectados
    src_a = "logger.info('hello %d', 1, 2)"
    res_a = find_mismatched_log_calls(src_a, "synthetic_a.py")
    assert len(res_a) == 1, f"Caso (a) deveria detectar 1 incompatibilidade, obteve: {res_a}"

    # (b) argumentos a menos ("%d %d" com um valor) são detectados
    src_b = "logger.info('hello %d %d', 1)"
    res_b = find_mismatched_log_calls(src_b, "synthetic_b.py")
    assert len(res_b) == 1, f"Caso (b) deveria detectar 1 incompatibilidade, obteve: {res_b}"

    # (c) %% literal não conta como especificador
    src_c = "logger.info('100%% complete with %d items', 5)"
    res_c = find_mismatched_log_calls(src_c, "synthetic_c.py")
    assert len(res_c) == 0, f"Caso (c) não deveria detectar incompatibilidade, obteve: {res_c}"

    # (d) estilo de dicionário ("%(a)s") não gera falso positivo
    src_d = "logger.info('%(a)s %(b)d', {'a': 'alpha', 'b': 2})"
    res_d = find_mismatched_log_calls(src_d, "synthetic_d.py")
    assert len(res_d) == 0, f"Caso (d) não deveria detectar incompatibilidade, obteve: {res_d}"

    # (e) chamadas com *args são ignoradas
    src_e = "logger.info('prefix %s %d', *extra_args)"
    res_e = find_mismatched_log_calls(src_e, "synthetic_e.py")
    assert len(res_e) == 0, f"Caso (e) não deveria detectar incompatibilidade, obteve: {res_e}"

    # (f) uma chamada correta não é sinalizada
    src_f = "logger.info('hello %s %d', 'world', 42)"
    res_f = find_mismatched_log_calls(src_f, "synthetic_f.py")
    assert len(res_f) == 0, f"Caso (f) não deveria detectar incompatibilidade, obteve: {res_f}"


def test_guard_no_mismatched_log_format_in_production():
    """Teste-guarda: Varredura AST sobre todo o código de produção garantindo que

    nenhuma chamada de log contenha contagem de argumentos incompatível com '%'.
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

    mismatches = []
    for filepath in files_to_scan:
        rel_path = filepath.relative_to(repo_root).as_posix()
        content = filepath.read_text(encoding="utf-8")
        found = find_mismatched_log_calls(content, filename=rel_path)
        mismatches.extend(found)

    assert mismatches == [], (
        f"Encontradas {len(mismatches)} chamada(s) de log com formato incompatível:\n"
        + "\n".join(f"  - {m}" for m in mismatches)
    )
