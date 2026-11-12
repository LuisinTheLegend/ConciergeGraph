"""
scratch/generate_relatorio_4_4f.py — Gera audits/relatorio_4_4f.md programaticamente (Regra 12 e Regra 14).
"""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_FILE = os.path.join(REPO_ROOT, "audits", "relatorio_4_4f.md")


def extract_lines(rel_path: str, start: int, end: int) -> str:
    abs_path = os.path.join(REPO_ROOT, rel_path)
    with open(abs_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    selected = []
    for idx in range(start, min(end, len(all_lines)) + 1):
        selected.append(f"{idx}: {all_lines[idx - 1].rstrip()}")
    return "\n".join(selected)


def run_git(args: list[str]) -> str:
    p = subprocess.run(["git"] + args, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    return p.stdout.strip()


def main() -> None:
    head_sha = run_git(["rev-parse", "HEAD"])
    diff_product = run_git(["diff", "3dccf68..HEAD", "--", "core/", "ingestion/", "interface/", "services/", "main.py"])
    diff_stat = run_git(["diff", "--stat", "3dccf68"])

    achados_f4033 = extract_lines("audits/fase4-achados.md", 594, 610)
    roadmap_44f = extract_lines("audits/fase4-roadmap.md", 59, 60)
    roadmap_f4033 = extract_lines("audits/fase4-roadmap.md", 97, 98)
    rel44e_addendum = extract_lines("audits/relatorio_4_4e.md", 759, 764)

    stress_paths = extract_lines("tests/memory_stress_test.py", 38, 51)
    stress_cleanup = extract_lines("tests/memory_stress_test.py", 641, 653)
    lightweight_code = extract_lines("tests/test_lightweight.py", 8, 42)
    lightweight_cleanup = extract_lines("tests/test_lightweight.py", 65, 71)

    red_parallel = extract_lines("scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt", 1, 26)
    green_stress = extract_lines("scratch/evidencia_4_4f/green_10_pairs_memory_stress.txt", 1, 17)
    green_lw_stress = extract_lines("scratch/evidencia_4_4f/green_10_pairs_lightweight_vs_stress.txt", 1, 18)
    consumers_check = extract_lines("scratch/evidencia_4_4f/consumers_and_guards_check.txt", 1, 45)
    mut_ta = extract_lines("scratch/evidencia_4_4f/mutacao_Ta.txt", 1, 46)
    mut_tb = extract_lines("scratch/evidencia_4_4f/mutacao_Tb.txt", 1, 26)

    conn_docstring = extract_lines("storage/connection.py", 85, 95)
    ast_proof = extract_lines("scratch/evidencia_4_4f/bloco3_ast_and_tests.txt", 1, 34)

    suite_310 = extract_lines("scratch/evidencia_4_4f/suite_py310.txt", 1, 7) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py310.txt", 82, 84) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py310.txt", 162, 164)
    suite_311 = extract_lines("scratch/evidencia_4_4f/suite_py311.txt", 1, 7) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py311.txt", 88, 90) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py311.txt", 174, 176)
    suite_312 = extract_lines("scratch/evidencia_4_4f/suite_py312.txt", 1, 7) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py312.txt", 98, 100) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py312.txt", 194, 196)
    suite_313 = extract_lines("scratch/evidencia_4_4f/suite_py313.txt", 1, 7) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py313.txt", 104, 106) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py313.txt", 206, 208)
    suite_314 = extract_lines("scratch/evidencia_4_4f/suite_py314.txt", 1, 7) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py314.txt", 108, 110) + "\n...\n" + extract_lines("scratch/evidencia_4_4f/suite_py314.txt", 214, 216)

    ci_status = extract_lines("scratch/evidencia_4_4f/ci_status.txt", 1, 35)

    lines = [
        "# Relatório da Rodada 4.4f — Isolamento dos Testes (`F4-033`) e Docstring da Fila de Escrita",
        "",
        f"- **Data:** 2026-11-11",
        f"- **Base da Rodada:** `3dccf68d3085b553efe27a8175e5c5fcac29048d` (`3dccf68`)",
        f"- **HEAD no momento da geração:** `{head_sha}`",
        "- **Natureza da Rodada:** Mini-rodada exclusiva de higiene de teste e documentação. O único arquivo de código de produto modificado é `storage/connection.py`, restrito à docstring da classe `SerializedWriteQueue` (provado por comparação de AST sem docstrings com SHA-256 idêntico).",
        "- **Gerado por script (Regra 12):** `scratch/generate_relatorio_4_4f.py`",
        "",
        "---",
        "",
        "## 1. Bloco 1 — Registro do Achado `F4-033`",
        "",
        "### 1.1 Registro em `audits/fase4-achados.md:594-610`",
        "",
        "```markdown",
        achados_f4033,
        "```",
        "",
        "### 1.2 Índice em `audits/fase4-roadmap.md:59-60, 97-98`",
        "",
        "```markdown",
        roadmap_44f,
        "...",
        roadmap_f4033,
        "```",
        "",
        "---",
        "",
        "## 2. Bloco 2 — Correção do Isolamento de Testes (`F4-033`)",
        "",
        "### 2.1 Mudanças Implementadas em `tests/memory_stress_test.py` e `tests/test_lightweight.py`",
        "",
        "- **Observação técnica sobre dupla importação no mesmo processo `pytest`:** Como `tests/` não possui `__init__.py`, `tests/conftest.py:8` (`from tests.memory_stress_test import ...`) importa o módulo sob `sys.modules['tests.memory_stress_test']`, enquanto a coleta direta de `tests/memory_stress_test.py` pelo `pytest` o importa sob `sys.modules['memory_stress_test']`. Armazenar o diretório criado por `tempfile.mkdtemp(prefix=f'grafo_stress_{os.getpid()}_')` em `sys._grafo_stress_test_dir` garante que ambas as referências dentro do mesmo processo Python apontem para o mesmo diretório temporário exclusivo daquele processo, enquanto processos paralelos possuem `PID`s e diretórios temporários distintos.",
        "",
        "#### `tests/memory_stress_test.py:38-51` e `641-653`",
        "",
        "```python",
        stress_paths,
        "...",
        stress_cleanup,
        "```",
        "",
        "#### `tests/test_lightweight.py:8-42` e `65-71`",
        "",
        "```python",
        lightweight_code,
        "...",
        lightweight_cleanup,
        "```",
        "",
        "### 2.2 Preservação do Contrato dos Consumidores e das Guardas (`check_mcp_globals_leak`, Hook `M10d` e `G2`)",
        "",
        "- Consumidores verificados sem alteração de contrato:",
        "  - `tests/conftest.py:8` (`from tests.memory_stress_test import setup_workspace, bootstrap, TEST_DIR`)",
        "  - `tests/test_lightweight.py:8` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR`)",
        "  - `tests/test_chunk_cache.py:4` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR, UTILS_FILE`)",
        "  - `tests/test_ignore.py:3` (`from tests.memory_stress_test import PROJECT_UUID, PROJECT_DIR`)",
        "",
        "#### Evidência: `scratch/evidencia_4_4f/consumers_and_guards_check.txt:1-45`",
        "",
        "```text",
        consumers_check,
        "```",
        "",
        "### 2.3 Prova em Vermelho (no commit `3dccf68`) — 10 Pares Paralelos de `memory_stress_test.py` (Python 3.12)",
        "",
        "- **Resultado em `3dccf68`:** **`10/10` pares paralelos falharam** (`4` pares com `sqlite3.IntegrityError: UNIQUE constraint failed: projects.uuid`, `4` pares com `sqlite3.OperationalError: database is locked`, `1` par com `chromadb.errors.InternalError: ... (code: 5) database is locked` e `1` par com `chromadb.errors.InternalError: ... (code: 1) table collections already exists`).",
        "",
        "#### Evidência: `scratch/evidencia_4_4f/red_10_pairs_memory_stress_3dccf68.txt:1-26`",
        "",
        "```text",
        red_parallel,
        "```",
        "",
        "### 2.4 Prova em Verde (Versão Corrigida) — 10 Pares Paralelos",
        "",
        "#### (a) 10 Pares Paralelos de `memory_stress_test.py` (Python 3.12): `0/10` falhas (`scratch/evidencia_4_4f/green_10_pairs_memory_stress.txt:1-17`)",
        "",
        "```text",
        green_stress,
        "```",
        "",
        "#### (b) 10 Pares Paralelos de `test_lightweight.py` (Python 3.10) vs. `memory_stress_test.py` (Python 3.12): `0/10` falhas (`scratch/evidencia_4_4f/green_10_pairs_lightweight_vs_stress.txt:1-18`)",
        "",
        "```text",
        green_lw_stress,
        "```",
        "",
        "### 2.5 Mutações Matadoras (`Ta` e `Tb`)",
        "",
        "| Mutação | Alvo | Comportamento com Mutação | Comportamento sem Mutação | Status | Evidência |",
        "|---|---|---|---|---|---|",
        "| `Ta` | Reintroduzir caminho fixo `_stress_test_workspace` em `TEST_DIR` (`tests/memory_stress_test.py:42-45`) | `5/5` pares paralelos falham (`UNIQUE constraint failed: projects.uuid` / `database is locked`) | `0` falhas (`ProcA rc=0, ProcB rc=0`) | **MORTA (OK)** | `scratch/evidencia_4_4f/mutacao_Ta.txt` |",
        "| `Tb` | Reintroduzir `'./tmp_chroma_test'` em `tmp_dir` (`tests/test_lightweight.py:38`) | `0/5` pares paralelos falham (explicado e demonstrado abaixo: `ChromaVectorStore` em modo lightweight é `NO-OP` e não cria `persist_dir` no disco) | `0` falhas | **Explicada e demonstrada empiricamente** | `scratch/evidencia_4_4f/mutacao_Tb.txt` |",
        "",
        "#### Evidência Mutação `Ta`: `scratch/evidencia_4_4f/mutacao_Ta.txt:1-46`",
        "",
        "```text",
        mut_ta,
        "```",
        "",
        "#### Evidência e Demonstração Mutação `Tb`: `scratch/evidencia_4_4f/mutacao_Tb.txt:1-26`",
        "",
        "```text",
        mut_tb,
        "```",
        "",
        "### 2.6 Execução Sequencial Normal nas 5 Versões de Python (`3.10`, `3.11`, `3.12`, `3.13`, `3.14`)",
        "",
        "- Em todas as 5 versões, o número de testes coletados e executados permaneceu idêntico ao de `3dccf68`: **`475 passed, 1 xfailed`** (`476` itens coletados: `471 passed, 1 xfailed` da suíte `tests/` + `4 passed` de `tests/memory_stress_test.py`), tanto na ordem padrão quanto na ordem inversa (`--reverse`).",
        "",
        "```text",
        suite_310,
        "---",
        suite_311,
        "---",
        suite_312,
        "---",
        suite_313,
        "---",
        suite_314,
        "```",
        "",
        "---",
        "",
        "## 3. Bloco 3 — Docstring de `SerializedWriteQueue` (`storage/connection.py`)",
        "",
        "### 3.1 Texto Aplicado em `storage/connection.py:85-95`",
        "",
        "```python",
        conn_docstring,
        "```",
        "",
        "### 3.2 Prova de Zero Mudança de Comportamento (Comparação de AST sem Docstrings + Testes `T-S1` e `T-S2`)",
        "",
        "- A AST de `storage/connection.py` no commit base `3dccf68` e na árvore atual, após remoção exclusiva de nós de docstring (`Expr(Constant(str))` no início de `Module`, `ClassDef`, `FunctionDef` e `AsyncFunctionDef`), produz `ast.dump()` **idêntico byte a byte** (`SHA-256: ff60541a00feecebaf3b8d9a394a8d5a9d3e2e7e2b4ad1cb4c648afe22ab17cf`).",
        "- Nenhum outro arquivo de código de produto (`core/`, `ingestion/`, `interface/`, `services/`, `main.py`) sofreu qualquer modificação (`diff` vazio: `" + (diff_product if diff_product else "vazio") + "`).",
        "",
        "#### Evidência: `scratch/evidencia_4_4f/bloco3_ast_and_tests.txt:1-34`",
        "",
        "```text",
        ast_proof,
        "```",
        "",
        "---",
        "",
        "## 4. Bloco 4 — Esclarecimento sobre a Hipótese do `chromadb`",
        "",
        "### 4.1 Adendo Adicionado ao Fim de `audits/relatorio_4_4e.md:759-764`",
        "",
        "```markdown",
        rel44e_addendum,
        "```",
        "",
        "- **Monitoramento pós-isolamento na Rodada 4.4f:** Durante todas as execuções após o isolamento de `F4-033` (20 pares paralelos em verde no Bloco 2 + 10 execuções completas da suíte sequencial nas versões Python 3.10 a 3.14 em ordem padrão e `--reverse`), o `chromadb` `InternalError` intermitente não voltou a se manifestar localmente.",
        "",
        "---",
        "",
        "## 5. Governança, CI e Conformidade (Regras 11 a 15)",
        "",
        "### 5.1 Status dos 6 Jobs do GitHub Actions CI para `3dccf68` (`scratch/evidencia_4_4f/ci_status.txt:1-35`)",
        "",
        "```text",
        ci_status,
        "```",
        "",
        "### 5.2 Resumo de Alterações (`git diff --stat 3dccf68`)",
        "",
        "```text",
        diff_stat,
        "```",
        "",
        "### 5.3 Verificações Finais de Higiene e Segurança",
        "",
        "- **Restrição de código de produto:** Apenas `storage/connection.py` alterado, e unicamente na docstring de `SerializedWriteQueue` (provado por AST sem docstrings idêntica em `scratch/evidencia_4_4f/bloco3_ast_and_tests.txt`).",
        "- **Diretórios residuais:** `tests/_stress_test_workspace` e `tmp_chroma_test` verificados como inexistentes (`False`).",
        "- **Scanner de segredos (Regra 13):** `scratch/tools/scan_secrets.py` executado com `0` achados (`scratch/evidencia_4_4f/scan_secrets.txt`).",
        "- **Codificação UTF-8 sem BOM e sem bytes nulos:** Conferida por script em todos os arquivos de `scratch/evidencia_4_4f/` e `audits/` (`scratch/evidencia_4_4f/utf8_check.txt`).",
        "",
    ]

    content = "\n".join(lines)
    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"Gerado {OUT_FILE} ({len(lines)} linhas).")


if __name__ == "__main__":
    main()

