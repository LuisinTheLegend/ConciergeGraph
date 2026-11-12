"""
scratch/investigate_bloco1_4_4g_part1.py — Coleta versões locais (Python, chromadb, pytest),
consumidores reais da fixture `stress_components`, e saída de `--collect-only` / `--setup-plan`
nas ordens padrão e `--reverse` (Rodada 4.4g — Bloco 1).
"""

import ast
import os
import subprocess
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV_DIR = os.path.join(REPO_ROOT, "scratch", "evidencia_4_4g")
os.makedirs(EV_DIR, exist_ok=True)

ENVS = [
    ("py310", os.path.join(REPO_ROOT, ".venv_310", "Scripts", "python.exe")),
    ("py311", os.path.join(REPO_ROOT, ".venv_311", "Scripts", "python.exe")),
    ("py312", os.path.join(REPO_ROOT, ".venv_312", "Scripts", "python.exe")),
    ("py313", os.path.join(REPO_ROOT, ".venv_313", "Scripts", "python.exe")),
    ("py314", os.path.join(REPO_ROOT, ".venv_clean", "Scripts", "python.exe")),
]


def find_stress_fixture_consumers() -> list[tuple[str, int, str, list[str]]]:
    fixtures = {"stress_components", "store", "vector", "embedder", "manager", "janitor"}
    results = []
    tests_dir = os.path.join(REPO_ROOT, "tests")
    for fname in sorted(os.listdir(tests_dir)):
        if not fname.endswith(".py") or fname == "conftest.py":
            continue
        fpath = os.path.join(tests_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=fname)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                matched = [a for a in args if a in fixtures]
                # Filtra testes que definem seu próprio fixture com o mesmo nome no arquivo?
                # Checa se há @pytest.fixture no mesmo arquivo definindo esse nome
                if matched and (node.name.startswith("test_") or any(
                    isinstance(d, ast.Attribute) and d.attr == "fixture" or isinstance(d, ast.Name) and d.id == "fixture"
                    for d in node.decorator_list
                )):
                    results.append((f"tests/{fname}", node.lineno, node.name, matched))
    return results


def run_collect(py_exe: str, reverse: bool = False) -> str:
    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44g-collect"
    env["GRAFO_LLM_MODEL"] = "none"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    cmd = [py_exe, "-m", "pytest", "--collect-only", "-q"]
    if reverse:
        cmd.append("--reverse")
    p = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout


def run_setup_plan(py_exe: str, reverse: bool = False) -> str:
    env = os.environ.copy()
    env["GRAFO_LLM_API_KEY"] = "sk-FAKE-44g-setupplan"
    env["GRAFO_LLM_MODEL"] = "none"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    cmd = [py_exe, "-m", "pytest", "--setup-plan"]
    if reverse:
        cmd.append("--reverse")
    p = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout


def main() -> None:
    lines = ["=== BLOCO 1 (PARTE 1): VERSÕES LOCAIS, CONSUMIDORES DE stress_components E ORDEM DE COLETA ==="]

    lines.append("\n--- [1] VERSÕES LOCAIS (Python, chromadb, pytest, SharedSystemClient) ---")
    for tag, py_exe in ENVS:
        code = (
            "import sys, chromadb, pytest; "
            "from chromadb.api.client import SharedSystemClient; "
            "has_clear = hasattr(SharedSystemClient, 'clear_system_cache'); "
            "print(f'Python={sys.version.splitlines()[0]} | chromadb={chromadb.__version__} | pytest={pytest.__version__} | has_clear_system_cache={has_clear}')"
        )
        p = subprocess.run([py_exe, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
        lines.append(f"  [{tag}] {p.stdout.strip() or p.stderr.strip()}")

    lines.append("\n--- [2] FUNÇÕES EM tests/ COM PARÂMETROS DAS FIXTURES DE conftest.py ---")
    for rel, lineno, fn_name, matched in find_stress_fixture_consumers():
        lines.append(f"  {rel}:{lineno} def {fn_name}({', '.join(matched)})")

    py310 = ENVS[0][1]
    for label, rev in [("ORDEM NORMAL", False), ("ORDEM INVERTIDA (--reverse)", True)]:
        col_out = run_collect(py310, reverse=rev)
        setup_out = run_setup_plan(py310, reverse=rev)

        # Extrair módulos na ordem executada (preservando ordem de aparição)
        modules_order = []
        seen = set()
        for line in col_out.splitlines():
            line = line.strip()
            if "::" in line and line.startswith("tests/"):
                mod = line.split("::", 1)[0]
                if mod not in seen:
                    seen.add(mod)
                    modules_order.append(mod)

        lines.append(f"\n--- [3] {label}: ORDEM DE MÓDULOS VIA pytest --collect-only -q {'--reverse' if rev else ''} ---")
        for idx, mod in enumerate(modules_order, 1):
            marker = "  <== usa stress_components" if mod in (
                "tests/memory_stress_test.py",
                "tests/test_chunk_cache.py",
                "tests/test_ignore.py",
                "tests/test_lightweight.py",
            ) else ""
            lines.append(f"  {idx:02d}. {mod}{marker}")

        lines.append(f"\n--- [4] {label}: EVENTOS SETUP/TEARDOWN DE stress_components EM pytest --setup-plan ---")
        for line in setup_out.splitlines():
            if "stress_components" in line or "test_chunk_cache" in line or "test_ignore" in line or "test_lightweight" in line or "memory_stress_test" in line:
                lines.append("  " + line.rstrip())

    # Verificar pyproject.toml testpaths
    lines.append("\n--- [5] NOTA SOBRE pyproject.toml testpaths ---")
    lines.append("  Em pyproject.toml:117-118, testpaths = ['tests'], python_files = ['test_*.py', '*_test.py'].")
    lines.append("  Portanto, `pytest` / `pytest -v --tb=short` (como no .github/workflows/ci.yml:50) coleta AUTOMATICAMENTE todos os módulos test_*.py E *_test.py (incluindo tests/memory_stress_test.py).")

    out_path = os.path.join(EV_DIR, "bloco1_collect_order_and_versions.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

