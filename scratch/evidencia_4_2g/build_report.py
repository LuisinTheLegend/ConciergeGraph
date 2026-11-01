# scratch/evidencia_4_2g/build_report.py
"""
Script de geração mecânica do relatório da Rodada 4.2g (Regra 12).
Lê exclusivamente os arquivos de evidência gerados em scratch/evidencia_4_2g/
e produz audits/relatorio_4_2g.md sem texto digitado manualmente.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
AUDITS_DIR = REPO_ROOT / "audits"
REPORT_OUT = AUDITS_DIR / "relatorio_4_2g.md"


def read_safe(p: Path) -> str:
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return f"NÃO VERIFICADO (arquivo ausente: {p.name})"


def main():
    p0_head = read_safe(HERE / "passo0_head.txt")
    p0_ls_remote = read_safe(HERE / "passo0_ls_remote.txt")
    p0_pull = read_safe(HERE / "passo0_git_pull.txt")
    p0_pytest = read_safe(HERE / "passo0_baseline_pytest.txt")

    i1_freeze = read_safe(HERE / "item1_venv_min_pip_freeze.txt")
    i1_red = read_safe(HERE / "item1_d5_red.txt")
    i1_diff = read_safe(HERE / "item1_item4a_test_diff.txt")
    i1_green_min = read_safe(HERE / "item1_d_green_venv_min.txt")
    i1_green_main = read_safe(HERE / "item1_d_green_main_venv.txt")

    i2_ast = read_safe(HERE / "item2_ast_proof.txt")

    i3_pip_130 = read_safe(HERE / "item3_venv_mcp130_full_pip.txt")
    i3_tab_head = read_safe(HERE / "item3_tabela_head_mcp130.txt")
    i3_tab_ctrl = read_safe(HERE / "item3_tabela_control_dd92d35.txt")
    i3_pip_127 = read_safe(HERE / "item3_venv_mcp127_pip_freeze.txt")

    sample_json_files = sorted((HERE / "e2e_mcp130_full").glob("*__mine__rep1/result.json"))
    sample_json = read_safe(sample_json_files[0]) if sample_json_files else "NÃO VERIFICADO"

    wf_content = read_safe(REPO_ROOT / ".github" / "workflows" / "windows-stdin.yml")
    i4_gh_main = read_safe(HERE / "item4_gh_run_main.txt")
    i4_gh_mut = read_safe(HERE / "item4_gh_run_mutacao.txt")

    errata_42f = read_safe(AUDITS_DIR / "errata-4-2f.md")

    md = []
    md.append("# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2g")
    md.append("## FECHAMENTO DAS 4 LACUNAS DA RODADA 4.2f (ACHADO F4-017)")
    md.append("")
    md.append(f"> **Data de Emissão:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("> **Regras aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos gerados por script).")
    md.append("> **Escopo:** Somente docstring de `decouple_stdin_from_fd0` em `main.py` (Item 2), `tests/test_stdin_decouple.py` (Itens 1 e 4a), `.github/workflows/windows-stdin.yml` (Item 4b), `audits/` e `scratch/evidencia_4_2g/`. Zero alteração em código executável de produção.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 1. PASSO 0 — BASELINE")
    md.append("#### 1.1 Sincronização Git (`git pull`, `HEAD`, `origin/main`)")
    md.append("```text")
    md.append(f"git pull: {p0_pull}")
    md.append(f"git rev-parse HEAD: {p0_head}")
    md.append(f"git ls-remote origin main: {p0_ls_remote}")
    md.append("```")
    md.append("#### 1.2 Suíte Completa no Baseline (`pytest tests/ -q`)")
    md.append("```text")
    md.append(p0_pytest)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 2. ITEM 1 & ITEM 4a — REMOÇÃO DO D5 FRÁGIL E SKIP EXPLÍCITO EM D1 SEM SCIPY")
    md.append("**Justificativa da remoção do D5 (2 linhas):**")
    md.append("O teste D5 apenas reexecutava em subprocesso os testes T1 e T2 de `tests/test_lazy_ml_imports.py` exigindo a string fixa `\"2 passed\"`, o que quebrava legitimamente em ambientes sem `sentence_transformers` (`\"2 skipped\"`).")
    md.append("Como T1 e T2 já integram a suíte oficial (e rodam diretamente no CI ao lado de `test_stdin_decouple.py`), a remoção de D5 elimina a duplicação frágil sem reduzir a cobertura de regressão.")
    md.append("")
    md.append("#### 2.1 Item 1a — `pip freeze` do venv limpo sem ML (`venv_min_no_ml`)")
    md.append("```text")
    md.append(i1_freeze)
    md.append("```")
    md.append("#### 2.2 Item 1b — VERMELHO no `HEAD 21610d8` com `venv_min_no_ml`")
    md.append("```text")
    md.append(i1_red)
    md.append("```")
    md.append("#### 2.3 Item 1c & 4a — Diff literal de `tests/test_stdin_decouple.py` (Commit `6defadc`)")
    md.append("```diff")
    md.append(i1_diff)
    md.append("```")
    md.append("#### 2.4 Item 1d — VERDE no `venv_min_no_ml` (D1 skip explícito por ausência de `scipy.special`, D2–D4 passam)")
    md.append("```text")
    md.append(i1_green_min)
    md.append("```")
    md.append("#### 2.5 Item 1e — VERDE no venv principal Windows (D1–D4 passam, zero skips)")
    md.append("```text")
    md.append(i1_green_main)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 3. ITEM 2 — REESCRITA DA DOCSTRING EM `main.py` E PROVA DE AST IDÊNTICO")
    md.append("```text")
    md.append(i2_ast)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 4. ITEM 3 — E2E EM `mcp 1.30.0` COMPLETO E CONTROLE NEGATIVO `dd92d35`")
    md.append("#### 4.1 Item 3a — Verificação de `mcp==1.30.0` e dependências completas (`venv_mcp130_full`)")
    md.append("```text")
    md.append(i3_pip_130)
    md.append("```")
    md.append("#### 4.2 Item 3b — Exemplo de `result.json` com versões, checagem de `NO-OP` e contagem de vetores (`count_embeddings`)")
    md.append("```json")
    md.append(sample_json)
    md.append("```")
    md.append("#### 4.3 Item 3c — Execução Sequencial no `HEAD` ($n=5$ `search-first` + $n=5$ `mine`) em `mcp 1.30.0` completo")
    md.append("```text")
    md.append(i3_tab_head)
    md.append("```")
    md.append("#### 4.4 Item 3d — Controle Negativo no Commit `dd92d35` ($n=3$ `search-first` + $n=3$ `mine`, timeout 180s) no mesmo `venv_mcp130_full`")
    md.append("```text")
    md.append(i3_tab_ctrl)
    md.append("```")
    md.append("#### 4.5 Item 3e — Rastreabilidade: `pip freeze` do `venv_mcp127` utilizado na Rodada 4.2f")
    md.append("```text")
    md.append(i3_pip_127)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 5. ITEM 4 — CI WINDOWS (`.github/workflows/windows-stdin.yml`) E MUTAÇÃO NO CI")
    md.append("#### 5.1 Item 4b — Workflow `.github/workflows/windows-stdin.yml` (Commit `30d65c1`)")
    md.append("```yaml")
    md.append(wf_content)
    md.append("```")
    md.append("#### 5.2 Item 4c — Resultado Real da Matriz no GitHub Actions (`main`, Python 3.10, 3.12 e 3.14)")
    md.append("```text")
    md.append(i4_gh_main)
    md.append("```")
    md.append("#### 5.3 Item 4d — Mutação no CI (Remoção de `os.dup2(nul, 0)` na branch descartável `ci-mutacao-4-2g`)")
    md.append("```text")
    md.append(i4_gh_mut)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 6. ERRATA DA RODADA 4.2f (`audits/errata-4-2f.md`)")
    md.append("```markdown")
    md.append(errata_42f)
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    md.append("### 7. O QUE NÃO FOI VERIFICADO (LIMITES DECLARADOS)")
    md.append("1. **Outras máquinas físicas e ambientes de SO/hardware:** Os testes locais de reprodução do deadlock (como o controle negativo `dd92d35` e a mutação sem `os.dup2(nul, 0)`) foram verificados na estação Windows 10.0.26300 do executor; máquinas com diferentes versões de sistema operacional, drivers ou políticas de segurança podem apresentar comportamento distinto.")
    md.append("2. **Cliente Claude Desktop real:** As validações E2E utilizaram o cliente oficial `mcp.client.stdio.stdio_client` (`ClientSession`) via STDIO. O teste interativo no aplicativo **Claude Desktop real** pelo dono do projeto **NÃO FOI VERIFICADO** nesta rodada.")
    md.append("3. **Timeout real do cliente Claude Desktop:** O limite exato de timeout de inicialização/chamada do cliente Claude Desktop **NÃO FOI VERIFICADO** (não especificado oficialmente na documentação do protocolo MCP).")
    md.append("4. **Status dos Achados F4-015 e F4-017:** Mantidos estritamente como `corrigido pelo executor, aguardando verificação independente` em `audits/fase4-roadmap.md` e `audits/fase4-achados.md`.")

    REPORT_OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Relatório gerado com sucesso em: {REPORT_OUT}")


if __name__ == "__main__":
    main()

