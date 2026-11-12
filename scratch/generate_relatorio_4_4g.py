"""
scratch/generate_relatorio_4_4g.py — Gera audits/relatorio_4_4g.md programaticamente (Regra 12 e Regra 14),
extraindo citações reais com arquivo:linha e rotulando explicitamente limitações e hipóteses.
"""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_FILE = os.path.join(REPO_ROOT, "audits", "relatorio_4_4g.md")
BASE_SHA = "26a43e2"


def read_all_lines(rel_path: str) -> list[str]:
    with open(os.path.join(REPO_ROOT, rel_path), "r", encoding="utf-8") as f:
        return [line.rstrip("\r\n") for line in f.readlines()]


def extract_lines(rel_path: str, start: int, end: int) -> str:
    all_lines = read_all_lines(rel_path)
    end = min(end, len(all_lines))
    return "\n".join(f"{idx}: {all_lines[idx - 1]}" for idx in range(start, end + 1))


def find_block(rel_path: str, start_substr: str, end_substr: str | None = None, offset_before: int = 0, extra_after: int = 0) -> tuple[int, int, str]:
    all_lines = read_all_lines(rel_path)
    start_idx = None
    for idx, line in enumerate(all_lines, start=1):
        if start_substr in line:
            start_idx = max(1, idx - offset_before)
            break
    if start_idx is None:
        raise ValueError(f"Marcador '{start_substr}' não encontrado em {rel_path}")
    if end_substr is None:
        end_idx = min(len(all_lines), start_idx + extra_after)
    else:
        end_idx = None
        for idx in range(start_idx, len(all_lines) + 1):
            if end_substr in all_lines[idx - 1]:
                end_idx = min(len(all_lines), idx + extra_after)
                break
        if end_idx is None:
            end_idx = len(all_lines)
    text = "\n".join(f"{i}: {all_lines[i - 1]}" for i in range(start_idx, end_idx + 1))
    return start_idx, end_idx, text


def run_git(args: list[str]) -> str:
    p = subprocess.run(["git"] + args, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    return p.stdout.strip()


def extract_suite_summary(rel_path: str) -> tuple[str, str]:
    all_lines = read_all_lines(rel_path)
    header = "\n".join(f"{i}: {all_lines[i - 1]}" for i in range(1, min(9, len(all_lines) + 1)))
    tails = []
    for idx, line in enumerate(all_lines, start=1):
        if "passed" in line and ("in " in line or "xfailed" in line or "failed" in line):
            tails.append(f"{idx}: {line}")
        elif line.startswith("--- [1]") or line.startswith("--- [2]"):
            tails.append(f"{idx}: {line}")
    return header, "\n".join(tails)


def main() -> None:
    head_sha = run_git(["rev-parse", "HEAD"])
    diff_product = run_git(["diff", BASE_SHA, "--", "core/", "storage/", "ingestion/", "interface/", "services/", "main.py"])
    diff_stat = run_git(["diff", "--stat", f"{BASE_SHA}..HEAD"])
    if not diff_stat:
        diff_stat = run_git(["diff", "--stat", BASE_SHA])

    b1_vers_s, b1_vers_e, b1_vers = find_block(
        "scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt",
        "--- [1] VERSÕES LOCAIS",
        "[py314]",
    )
    b1_cons_s, b1_cons_e, b1_cons = find_block(
        "scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt",
        "--- [2] FUNÇÕES EM tests/",
        "test_lightweight_mode_behavior",
    )
    b1_plan_s, b1_plan_e, b1_plan = find_block(
        "scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt",
        "--- [4] ORDEM NORMAL",
        "--- [3] ORDEM INVERTIDA",
        extra_after=-2,
    )
    b1_30x_head = extract_lines("scratch/evidencia_4_4g/bloco1_30x_results.txt", 1, 8)
    b1_30x_tail = extract_lines("scratch/evidencia_4_4g/bloco1_30x_results.txt", 36, 42) + "\n...\n" + extract_lines("scratch/evidencia_4_4g/bloco1_30x_results.txt", 69, 74)
    b1_sonda = extract_lines("scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt", 1, 50)

    b2_boot_s, b2_boot_e, b2_boot = find_block(
        "tests/memory_stress_test.py",
        "# Endurecimento defensivo",
        "embedding_manager=embedder,",
        extra_after=1,
    )
    b2_guards = extract_lines("scratch/evidencia_4_4g/bloco2_consumers_and_guards.txt", 1, 30) + "\n...\n" + extract_lines("scratch/evidencia_4_4g/bloco2_consumers_and_guards.txt", 125, 128)

    b3_base = extract_lines("scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt", 1, 35)
    b3_tests_s, b3_tests_e, b3_tests = find_block(
        "tests/test_stress_components_reuse.py",
        "def test_stress_components_reuse_cycle_characterization",
        extra_after=55,
    )
    b3_mut = extract_lines("scratch/evidencia_4_4g/bloco3_mutation_and_env.txt", 1, 63)

    rel44e_s, rel44e_e, rel44e_addendum = find_block(
        "audits/relatorio_4_4e.md",
        "## Adendo (2026-11-11 — Rodada 4.4g",
        "permanece **aberto, com causa não provada**",
    )
    f4033_ad_s, f4033_ad_e, f4033_ad = find_block(
        "audits/fase4-achados.md",
        "- **Limite Explícito (Bloco 1 e Bloco 4):**",
        "Adendo (2026-11-11 — Rodada 4.4g",
    )
    f4034_s, f4034_e, f4034_txt = find_block(
        "audits/fase4-achados.md",
        "### [F4-034]",
        "bloco3_mutation_and_env.txt:20-63",
    )
    rm_44g_s, rm_44g_e, rm_44g = find_block("audits/fase4-roadmap.md", "| 4.4g |")
    rm_f034_s, rm_f034_e, rm_f034 = find_block("audits/fase4-roadmap.md", "| F4-034 |")

    suite_sections = []
    for tag in ("py310", "py311", "py312", "py313", "py314"):
        rel = f"scratch/evidencia_4_4g/suite_{tag}.txt"
        if os.path.exists(os.path.join(REPO_ROOT, rel)):
            hdr, tails = extract_suite_summary(rel)
            suite_sections.append(f"#### `{rel}`\n\n```text\n{hdr}\n...\n{tails}\n```")
        else:
            suite_sections.append(f"#### `{rel}`\n\n- Pendente de geração.")

    scan_sec = extract_lines("scratch/evidencia_4_4g/scan_secrets.txt", 1, 50) if os.path.exists(os.path.join(REPO_ROOT, "scratch/evidencia_4_4g/scan_secrets.txt")) else "Aguardando verify_4_4g_integrity.py"
    utf8_chk = extract_lines("scratch/evidencia_4_4g/utf8_check.txt", 1, 200) if os.path.exists(os.path.join(REPO_ROOT, "scratch/evidencia_4_4g/utf8_check.txt")) else "Aguardando verify_4_4g_integrity.py"
    ci_txt = extract_lines("scratch/evidencia_4_4g/ci_status.txt", 1, 150) if os.path.exists(os.path.join(REPO_ROOT, "scratch/evidencia_4_4g/ci_status.txt")) else "Aguardando verificação pós-push em check_ci_status_4_4g.py"

    lines = [
        "# Relatório da Rodada 4.4g — `chromadb` Intermitente em `stress_components` (`F4-034`)",
        "",
        "- **Data:** 2026-11-12",
        f"- **Base da Rodada:** `26a43e2723488f5206c12f639c0a94a7ba3c483d` (`{BASE_SHA}`)",
        f"- **HEAD no momento da geração:** `{head_sha}`",
        "- **Status do achado `F4-034`:** **aberto, causa não provada**",
        "- **Natureza da Rodada:** Mini-rodada exclusiva de testes e documentação. **Zero alterações** em código de produto (`core/`, `storage/`, `ingestion/`, `interface/`, `services/`, `main.py`).",
        "- **Regra 15 (EGM):** Não utilizado nesta rodada (sem código de produto modificado e sem alteração irreversível).",
        "- **Gerado por script (Regra 12):** `scratch/generate_relatorio_4_4g.py`",
        "",
        "---",
        "",
        "## 1. Bloco 1 — Investigação na Base `26a43e2` (Sem Alterações no Código de Teste)",
        "",
        "### 1.1 Fato do CI em `3dccf68` (Fonte Fornecida + API Pública do GitHub Actions)",
        "",
        "- No CI de `3dccf68`, workflow run `43075938190`, job `Test (Python 3.10)` (`id=130715647420`), ocorreu `ERROR at setup of test_lightweight_mode_behavior` em **um único processo sequencial**, com a pilha:",
        "  - `tests/conftest.py:14 stress_components` → `tests/memory_stress_test.py:265 bootstrap` → `storage/vector_store.py:321 get_or_create_collection` → `chromadb.errors.InternalError: ... (code: 1) no such table: acquire_write` (`473 passed, 1 skipped, 1 xfailed, 1 error`).",
        "- Metadados públicos do job `130715647420` confirmam falha do step 7 (`Run tests with pytest`) em `2026-11-11T18:18:15Z`; os logs brutos do job via API pública retornaram `HTTP 403` sem autenticação.",
        "",
        "### 1.2 Tentativa de Reprodução Sequencial: 30 Execuções Py3.10 + 30 Execuções Py3.12 (`0/60`)",
        "",
        "- **Conclusão empírica:** **não reproduzido em 60 execuções (30 Py3.10 + 30 Py3.12)**. Todas as 60 execuções fecharam com `475 passed, 1 xfailed` (`0` erros de `chromadb`, `0` falhas).",
        "",
        "#### Evidência: `scratch/evidencia_4_4g/bloco1_30x_results.txt:1-8, 36-42, 69-74`",
        "",
        "```text",
        b1_30x_head,
        "...",
        b1_30x_tail,
        "```",
        "",
        "### 1.3 Ordem de Coleta, Consumidores Reais e `--setup-plan`",
        "",
        "- `pyproject.toml:117-118` configura `testpaths = [\"tests\"]` e `python_files = [\"test_*.py\", \"*_test.py\"]`, fazendo `pytest -v --tb=short` (`.github/workflows/ci.yml:50`) coletar automaticamente `tests/memory_stress_test.py` e os demais módulos `test_*.py`.",
        "- Na ordem normal, `tests/test_lightweight.py` (`37/59`) roda após 3 ciclos anteriores de `SETUP M` / `TEARDOWN M stress_components` (`01. tests/memory_stress_test.py`, `09. tests/test_chunk_cache.py`, `32. tests/test_ignore.py`). Na ordem `--reverse`, `tests/test_lightweight.py` (`23/59`) passa primeiro.",
        "",
        f"#### Versões locais e consumidores (`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:{b1_vers_s}-{b1_vers_e}` e `{b1_cons_s}-{b1_cons_e}`)",
        "",
        "```text",
        b1_vers,
        "...",
        b1_cons,
        "```",
        "",
        f"#### Plano de setup/teardown de `stress_components` (`scratch/evidencia_4_4g/bloco1_collect_order_and_versions.txt:{b1_plan_s}-{b1_plan_e}`)",
        "",
        "```text",
        b1_plan,
        "```",
        "",
        "### 1.4 Versões de `chromadb` e Sonda Local no Windows vs. Linux (Hipótese Não Provada)",
        "",
        "- **Fato observado na sonda mínima Windows (`scratch/evidencia_4_4g/bloco1_sonda_and_ci_versions.txt:1-12`):** Ao tentar `shutil.rmtree` sobre diretório com `PersistentClient` vivo, o Windows levanta `PermissionError: [WinError 32]` porque `chroma.sqlite3` está bloqueado pelo processo. Com `ignore_errors=True` (`tests/conftest.py:22`), `chroma.sqlite3` permanece no disco (`sqlite_remained_after_ignore_errors=True`), e o segundo cliente abre sem erro (`c2_err=None` em `3/3` Py3.10 + `3/3` Py3.12).",
        "- **Contraste com o Linux:** Na sonda do auditor em Linux (`chromadb 1.5.9`), o mesmo padrão levantou `InternalError ... (code: 1032) attempt to write a readonly database` (`6/6`), que também difere da mensagem do CI (`(code: 1) no such table: acquire_write`).",
        "- **HIPÓTESE (não provada):** A semântica de exclusão de arquivos abertos (`unlink` em POSIX vs. `[WinError 32]` no Windows) pode influenciar a não reprodução no Windows, **mas a causa raiz de `no such table: acquire_write` no CI continua NÃO PROVADA**.",
        "",
        "```text",
        b1_sonda,
        "```",
        "",
        "---",
        "",
        "## 2. Bloco 2 — Endurecimento Defensivo em `tests/memory_stress_test.py::bootstrap()` (Sem Código de Produto)",
        "",
        "- Em vez de alterar `storage/vector_store.py`, aplicou-se **apenas endurecimento defensivo em código de teste**: `bootstrap()` passou a isolar cada chamada em um subdiretório exclusivo `run_<uuid4>` dentro de `CHROMA_PATH`, preservando integralmente o símbolo `CHROMA_PATH` e os contratos de importação dos consumidores (`tests/conftest.py:8`, `tests/test_lightweight.py:8`, `tests/test_chunk_cache.py:4`, `tests/test_ignore.py:3`).",
        "- **Limite explícito:** Como `F4-034` não foi reproduzido (`0/60`), **não** afirmamos que esta mudança corrija a causa raiz; trata-se exclusivamente de **endurecimento defensivo** para evitar reuso de `persist_dir`/entrada em `SharedSystemClient` dentro do mesmo processo.",
        "",
        f"### 2.1 Alteração em `tests/memory_stress_test.py:{b2_boot_s}-{b2_boot_e}`",
        "",
        "```python",
        b2_boot,
        "```",
        "",
        "### 2.2 Consumidores de `stress_components` e Guardas (`test_domain_neutrality_guard.py`, `check_mcp_globals_leak`, `M10d`)",
        "",
        "```text",
        b2_guards,
        "```",
        "",
        "---",
        "",
        "## 3. Bloco 3 — Teste de Caracterização, Invariante Estrutural e Mutação Externa",
        "",
        "- **Declaração de honestidade (sem teste vermelho para `F4-034`):**",
        "  1. Executado antes do Bloco 2 sobre `26a43e2`, `test_stress_components_reuse_cycle_characterization` **já passava** (`RC=0` em Py3.10 e Py3.12, `scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt`).",
        "  2. Aplicada mutação externa reintroduzindo `persist_dir=CHROMA_PATH` fixo em `bootstrap()`, `test_stress_components_reuse_cycle_characterization` **continua passando** (`RC=0`), comprovando que é estritamente um **teste de caracterização do ciclo de reuso, não prova de correção**.",
        "  3. O segundo teste, `test_bootstrap_uses_distinct_chroma_subdir_per_call`, verifica apenas a invariante estrutural do endurecimento defensivo do Bloco 2 e **falha (`RC=1`) sob a mutação externa**, passando (`RC=0`) sem ela e restaurando `GRAFO_LIGHTWEIGHT_MODE` ao estado original (`None` ou `'true'`).",
        "",
        "### 3.1 Baseline sobre `26a43e2` (`scratch/evidencia_4_4g/bloco3_base_26a43e2_check.txt:1-35`)",
        "",
        "```text",
        b3_base,
        "```",
        "",
        f"### 3.2 Testes em `tests/test_stress_components_reuse.py:{b3_tests_s}-{b3_tests_e}`",
        "",
        "```python",
        b3_tests,
        "```",
        "",
        "### 3.3 Mutação Externa e Restauração de Ambiente (`scratch/evidencia_4_4g/bloco3_mutation_and_env.txt:1-63`)",
        "",
        "```text",
        b3_mut,
        "```",
        "",
        "---",
        "",
        "## 4. Bloco 4 — Registro do `F4-034` e Adendos Documentais",
        "",
        f"### 4.1 Adendo em `audits/relatorio_4_4e.md:{rel44e_s}-{rel44e_e}`",
        "",
        "```markdown",
        rel44e_addendum,
        "```",
        "",
        f"### 4.2 Adendo ao `F4-033` em `audits/fase4-achados.md:{f4033_ad_s}-{f4033_ad_e}`",
        "",
        "```markdown",
        f4033_ad,
        "```",
        "",
        f"### 4.3 Novo Achado `[F4-034]` em `audits/fase4-achados.md:{f4034_s}-{f4034_e}`",
        "",
        "```markdown",
        f4034_txt,
        "```",
        "",
        f"### 4.4 Entradas em `audits/fase4-roadmap.md:{rm_44g_s}-{rm_44g_e}` e `{rm_f034_s}-{rm_f034_e}`",
        "",
        "```markdown",
        rm_44g,
        "...",
        rm_f034,
        "```",
        "",
        "---",
        "",
        "## 5. Suíte Completa Multi-Versão (`Python 3.10`–`3.14`, Normal e `--reverse`)",
        "",
        *suite_sections,
        "",
        "---",
        "",
        "## 6. Conformidade, Segurança, Diff de Produto e CI",
        "",
        f"- **Alterações em código de produto vs `{BASE_SHA}` (`core/ storage/ ingestion/ interface/ services/ main.py`):** `" + (diff_product if diff_product else "VAZIO (nenhum arquivo alterado)") + "`",
        "",
        "### 6.1 `git diff --stat` vs `26a43e2`",
        "",
        "```text",
        diff_stat,
        "```",
        "",
        "### 6.2 `scratch/tools/scan_secrets.py` (Regra 13) e Checagem UTF-8 / Nulos",
        "",
        "```text",
        scan_sec,
        "---",
        utf8_chk,
        "```",
        "",
        "### 6.3 Status do GitHub Actions CI (`scratch/evidencia_4_4g/ci_status.txt`)",
        "",
        "```text",
        ci_txt,
        "```",
        "",
    ]

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print(f"Gerado {OUT_FILE} ({len(lines)} linhas).")


if __name__ == "__main__":
    main()
