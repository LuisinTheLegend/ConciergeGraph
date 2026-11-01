"""scratch/build_relatorio_4_2i.py

Gera mecanicamente o relatório consolidado audits/relatorio_4_2i.md a partir
dos arquivos de evidência gerados por redirecionamento em scratch/evidencia_4_2i/
(Regra 12 do AUDIT_PROTOCOL.md).
"""

from __future__ import annotations

import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
EV_DIR = REPO_ROOT / "scratch" / "evidencia_4_2i"
REPORT_PATH = REPO_ROOT / "audits" / "relatorio_4_2i.md"


def read_ev(name: str) -> str:
    p = EV_DIR / name
    if not p.exists():
        return f"[ARQUIVO NÃO ENCONTRADO: {name}]"
    return p.read_text(encoding="utf-8", errors="replace").rstrip()


def main() -> int:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections: list[str] = [
        "# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2i",
        "## BLOCO 0: CI VERDE EM AMBIENTE LIMPO (F4-025) & BLOCO 1: BUSCA POR CÓDIGO SEM LLM (F4-018, F4-024)",
        "",
        f"> **Data de Emissão:** {now_str}",
        "> **Executor:** Antigravity (Advanced Agentic Coding)",
        "> **Regras Aplicadas:** 2 (Evidência obrigatória), 3 (Não inventar achados), 4 (Escopo estrito), 7 (Gate do dono), 10 (Sem DDL em testes de produção), 11 (Commits separados por bloco), 12 (Evidência por arquivo gerado por redirecionamento; relatório gerado por script), 13 (Scanner `scan_secrets.py` antes de cada commit e chaves falsas explícitas em subprocessos).",
        "> **HEAD Inicial (Baseline):** `c5e1c2c177896b81eacf821321a2086628f46f61`",
        "> **Commit Bloco 0 (F4-025):** `4263178784a082ba902da2e347f1eac19fec286b`",
        "> **Commit Bloco 1 (F4-018, F4-024):** `023c81d`",
        "",
        "---",
        "",
        "## 1. PASSO 0 — BASELINE E VERIFICAÇÃO INICIAL",
        "",
        "### 1.1 Identificação do Repositório (`git rev-parse HEAD` e `git ls-remote origin main`)",
        "#### `scratch/evidencia_4_2i/p0_head.txt`",
        "```text",
        read_ev("p0_head.txt"),
        "```",
        "#### `scratch/evidencia_4_2i/p0_ls_remote.txt`",
        "```text",
        read_ev("p0_ls_remote.txt"),
        "```",
        "",
        "---",
        "",
        "## 2. BLOCO 0: CI VERDE EM AMBIENTE LIMPO (F4-025, MÉDIA)",
        "",
        "### 2.1 Causa Técnica e Mecanismo",
        "1. **Ausência de `openai` nos extras de desenvolvimento:** `pyproject.toml` declarava `openai` apenas como dependência de runtime do pacote e não nos extras `dev`/`all`. Em ambientes limpos (`pip install -e '.[dev]'`), os testes S1–S8 de `tests/test_llm_egress_guard.py` falhavam na importação (`ModuleNotFoundError: No module named 'openai'`), totalizando 13 erros e 1 falha.",
        "2. **Falha de paridade cross-platform em `is_safe_path`:** No Linux, `Path('C:\\Windows\\System32\\config').is_absolute()` retorna `False`. Como resultado, `core/security_guard.py` concatenava o caminho à raiz do monorepo, devolvendo `True` indevidamente para caminhos fora da raiz.",
        "3. **Teste `BL-015` sem marcação estrita:** O teste `test_telemetry_api_mcp_state_endpoints` em `tests/test_progressive_tool_disclosure.py` esperava `PLANNING` mas a API retornava `EXECUTION`, quebrando constantemente o CI.",
        "",
        "### 2.2 Provas Vermelho -> Verde e Mutações do Bloco 0",
        "",
        "#### Vermelho: 13 Erros de `openai` ausente (`scratch/evidencia_4_2i/b0_red_openai_missing.txt`)",
        "```text",
        read_ev("b0_red_openai_missing.txt"),
        "```",
        "",
        "#### Vermelho: Falha de `is_safe_path` para caminhos Windows no Linux (`scratch/evidencia_4_2i/b0_red_security_guard_parity.txt`)",
        "```text",
        read_ev("b0_red_security_guard_parity.txt"),
        "```",
        "",
        "#### Verde: Testes de Paridade Cross-Platform (`scratch/evidencia_4_2i/b0_green_security_guard_parity.txt`)",
        "```text",
        read_ev("b0_green_security_guard_parity.txt"),
        "```",
        "",
        "#### Marcação Estrita de `BL-015` (`xfail(strict=True)`) (`scratch/evidencia_4_2i/b0_bl015_xfail_active.txt`)",
        "```text",
        read_ev("b0_bl015_xfail_active.txt"),
        "```",
        "",
        "#### Prova de Alerta se BL-015 for Corrigido Inadvertidamente (`XPASS(strict)` -> FAILED) (`scratch/evidencia_4_2i/b0_bl015_xpass_strict_proof.txt`)",
        "```text",
        read_ev("b0_bl015_xpass_strict_proof.txt"),
        "```",
        "",
        "#### Mutação Bloco 0: Remover `openai` do extra dev reintroduz as 13 falhas (`scratch/evidencia_4_2i/b0_mut_remove_openai_from_dev.txt`)",
        "```text",
        read_ev("b0_mut_remove_openai_from_dev.txt"),
        "```",
        "",
        "---",
        "",
        "## 3. BLOCO 1: BUSCA POR CÓDIGO SEM LLM (F4-018 e F4-024)",
        "",
        "### 3.1 Causa Técnica e Solução Implementada",
        "1. **F4-018 (Indexação de `content` no FTS5):**",
        "   - A tabela virtual `nodes_fts` em `storage/schema.py` indexava apenas `(label, tags, summary)`. Com `GRAFO_LLM_MODEL=none`, `nodes.summary` é `NULL`, tornando palavras do corpo do código inacessíveis por busca lexical.",
        "   - **Solução:** `nodes_fts` recriada como tabela de conteúdo externo com 4 colunas (`label, tags, summary, content`, `content='nodes', content_rowid='id'`) e tokenizer com suporte a diacríticos `tokenize='unicode61 remove_diacritics 2'`. Triggers de sincronização (`nodes_ai`, `nodes_ad`, `nodes_au`) atualizados. Migração idempotente com backup de segurança e `integrity-check`.",
        "2. **Mudança 2 (`search_symbols` restrito a `label`):**",
        "   - Em `storage/store.py:703`, `search_symbols` passou a filtrar estritamente pela coluna de rótulo (`f'label : \"{safe_query}\"'`), garantindo que ocorrências de nomes no corpo do arquivo não sejam tratadas como símbolos.",
        "3. **Mudança 3 (Pesos BM25 assimétricos):**",
        "   - Em `storage/logic.py`, `fts_search` aplica pesos `bm25(nodes_fts, 10.0, 5.0, 2.0, 1.0)`, garantindo precedência de nomes de arquivos e símbolos sobre o conteúdo.",
        "4. **F4-024 (Robustez e multi-palavra FTS5):**",
        "   - Implementada função `_build_fts5_queries(query)` com sanitização de caracteres especiais/operadores e frase exata (`\"...\"`).",
        "   - Busca primária com `AND`; se retornar vazia com múltiplos termos, realiza fallback automático para `OR` com ranqueamento BM25.",
        "   - Consultas vazias ou com apenas pontuação retornam `[]` imediatamente sem exceção SQL.",
        "",
        "### 3.2 Prova Unitária: Vermelho -> Verde (`tests/test_fts_code_search.py`)",
        "",
        "#### Unitário Vermelho no código antigo (`scratch/evidencia_4_2i/b1_red_unit.txt`)",
        "```text",
        read_ev("b1_red_unit.txt"),
        "```",
        "",
        "#### Unitário Verde no código novo (`scratch/evidencia_4_2i/b1_green_unit.txt`)",
        "```text",
        read_ev("b1_green_unit.txt"),
        "```",
        "",
        "### 3.3 Prova E2E no Servidor FastMCP Real (`GRAFO_LLM_MODEL=none`)",
        "",
        "#### MCP E2E Vermelho no código antigo (`scratch/evidencia_4_2i/b1_red_e2e_mcp.txt`)",
        "```text",
        read_ev("b1_red_e2e_mcp.txt"),
        "```",
        "",
        "#### MCP E2E Verde no código novo (`scratch/evidencia_4_2i/b1_green_e2e_mcp.txt`)",
        "```text",
        read_ev("b1_green_e2e_mcp.txt"),
        "```",
        "",
        "### 3.4 Medições Empíricas de Desempenho e Armazenamento",
        "#### `scratch/evidencia_4_2i/b1_measurements.txt`",
        "```text",
        read_ev("b1_measurements.txt"),
        "```",
        "",
        "### 3.5 Mutações Obrigatórias do Bloco 1",
        "",
        "#### Mutação 1: Reverter para 3 colunas (sem `content`) quebra busca no corpo (`scratch/evidencia_4_2i/b1_mut1_3_columns.txt`)",
        "```text",
        read_ev("b1_mut1_3_columns.txt"),
        "```",
        "",
        "#### Mutação 2: Desativar escape FTS5 permite injeção de sintaxe e lança OperationalError (`scratch/evidencia_4_2i/b1_mut2_no_fts5_escape.txt`)",
        "```text",
        read_ev("b1_mut2_no_fts5_escape.txt"),
        "```",
        "",
        "#### Mutação 3: Remover restrição `label :` em `search_symbols` retorna arquivos indevidos (`scratch/evidencia_4_2i/b1_mut3_search_symbols_no_label_restriction.txt`)",
        "```text",
        read_ev("b1_mut3_search_symbols_no_label_restriction.txt"),
        "```",
        "",
        "#### Mutação 4: Remover fallback `OR` faz consultas multi-palavra parciais retornarem vazio (`scratch/evidencia_4_2i/b1_mut4_no_or_fallback.txt`)",
        "```text",
        read_ev("b1_mut4_no_or_fallback.txt"),
        "```",
        "",
        "---",
        "",
        "## 4. SUÍTE COMPLETA DE TESTES APÓS O BLOCO 1",
        "",
        "#### `scratch/evidencia_4_2i/b1_full_suite.txt`",
        "```text",
        read_ev("b1_full_suite.txt"),
        "```",
        "",
        "---",
        "",
        "## 5. VERIFICAÇÃO DE SEGREDOS (REGRA 13)",
        "",
        "Varredura obrigatória com `scratch/tools/scan_secrets.py` sobre todo o repositório antes do commit do Bloco 1:",
        "Esperado: 0 achados reais.",
        "",
        "---",
        "",
        "## 6. SÍNTESE DO STATUS DOS ACHADOS",
        "",
        "| ID | Achado | Severidade | Status Anterior | Novo Status | Justificativa |",
        "|---|---|---|---|---|---|",
        "| `F4-025` | CI vermelho em ambiente limpo | MÉDIA | ABERTO | corrigido pelo executor, aguardando verificação independente | Commit `4263178` (Bloco 0): openai extra em dev/all, cross-platform is_safe_path, BL-015 strict xfail |",
        "| `F4-018` | `nodes_fts` não indexava `content` | GRAVE | ABERTO | corrigido pelo executor, aguardando verificação independente | Bloco 1: 4 colunas FTS5 com content, tokenizer unicode61, BM25 weights, migração idempotente com backup |",
        "| `F4-024` | Sintaxe frágil e sem fallback multi-palavra em FTS5 | MÉDIA | ABERTO | corrigido pelo executor, aguardando verificação independente | Bloco 1: `_build_fts5_queries`, sanitização anti-injeção, fallback AND->OR ranqueado por BM25 |",
        "| `BL-015` | Estado default da Telemetry API (`EXECUTION` vs `PLANNING`) | MÉDIA | ABERTO | ABERTO | Permanece estritamente ABERTO conforme instrução do dono; marcado como xfail(strict=True) |",
        "",
    ]

    report_content = "\n".join(sections) + "\n"
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(f"Report written to {REPORT_PATH} ({len(report_content)} chars)")
    return 0


if __name__ == "__main__":
    main()

