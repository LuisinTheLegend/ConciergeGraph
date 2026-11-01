"""scratch/evidencia_4_2h/build_report.py

Gera mecanicamente o relatorio consolidado audits/relatorio_4_2h.md
a partir dos arquivos de evidencia em scratch/evidencia_4_2h/ (Regra 12).
Nenhum texto de saída de comando é digitado manualmente.
"""

from __future__ import annotations

import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
AUDITS_DIR = REPO_ROOT / "audits"


def read_ev(filename: str) -> str:
    p = HERE / filename
    if not p.exists():
        return f"[ARQUIVO NÃO ENCONTRADO: {filename}]"
    return p.read_text(encoding="utf-8", errors="replace").strip()


def main() -> int:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections: list[str] = []

    sections.append(
        f"""# RELATÓRIO TÉCNICO CONSOLIDADO — RODADA 4.2h
## SEGURANÇA DO ADAPTADOR DE LLM (F4-019, F4-020, F4-021)

> **Data de Emissão:** {now_str}
> **Regras Aplicadas:** 2, 3, 4, 7 (Gate), 10, 11 (Git sync), 12 (Evidência estrita por arquivos gerados por redirecionamento; relatório gerado por script), 13 (Scanner de segredos e chaves falsas em testes).
> **Escopo Tocado:** `ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py`, `interface/cli.py`, `.env.example`, `AUDIT_PROTOCOL.md`, `tests/test_llm_egress_guard.py`, `tests/test_no_secrets_in_tracked_files.py`, `tests/test_secret_redaction.py`, `scratch/tools/scan_secrets.py`, `scratch/evidencia_4_2h/`, e `audits/`. Zero alteração em `storage/`, esquema/FTS (`F4-018`), dependências, `data/` ou `README`.

---

## 1. PASSO 0 — BASELINE

### 1.1 Sincronização Git (`git pull`, `git rev-parse HEAD`, `git ls-remote origin main`)
#### `scratch/evidencia_4_2h/p0_git_pull.txt`
```text
{read_ev("p0_git_pull.txt")}
```
#### `scratch/evidencia_4_2h/p0_head.txt`
```text
{read_ev("p0_head.txt")}
```
#### `scratch/evidencia_4_2h/p0_ls_remote.txt`
```text
{read_ev("p0_ls_remote.txt")}
```

### 1.2 Suíte Completa no Baseline (`pytest tests/ -q`)
#### `scratch/evidencia_4_2h/p0_pytest.txt`
```text
{read_ev("p0_pytest.txt")}
```

---

## 2. PASSO 1 — MAPEAMENTO (SOMENTE LEITURA)

### 2.1 Saída de `git grep` em Código de Produção (`p1_mapeamento.txt` e `p1_mapeamento_extra.txt`)
#### `scratch/evidencia_4_2h/p1_mapeamento.txt`
```text
{read_ev("p1_mapeamento.txt")}
```
#### `scratch/evidencia_4_2h/p1_mapeamento_extra.txt`
```text
{read_ev("p1_mapeamento_extra.txt")}
```

### 2.2 Pontos de Criação de Cliente LLM / Envio de `GRAFO_LLM_API_KEY` e Verificação de `storage/vector_store.py`
1. **`ingestion/summarizer.py` (`LLMAdapter.generate` e `LLMAdapter.generate_async`):** Único módulo de produção que instancia clientes de LLM (`google.genai.Client`, `google.generativeai`, `openai.OpenAI` e `openai.AsyncOpenAI`).
2. **`main.py` (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_PROVIDER` -> `ZoomSummarizer` em `bootstrap()`):** Lê variáveis de ambiente e repassa ao `ZoomSummarizer`, que instancia `LLMAdapter`.
3. **`interface/cli.py` (`cmd_mine`):** Lê `GRAFO_LLM_API_KEY`, `GRAFO_LLM_MODEL`, `GRAFO_LLM_BASE_URL` e `GRAFO_LLM_PROVIDER` e instancia `ZoomSummarizer`.
4. **Resposta sobre `storage/vector_store.py` (tier `ELITE`, `openai_api_key`):** Conforme provado em `p1_mapeamento_extra.txt`, `EmbeddingManager` em `storage/vector_store.py` possui suporte dormente a `EmbeddingTier.ELITE` (`openai_api_key`), mas todos os pontos do código de produção (`main.py:168`, `interface/cli.py:92`, `storage/vector_store.py:128,452`) instanciam `EmbeddingManager(tier=EmbeddingTier.FLASH)` sem nunca passar `openai_api_key` nem `GRAFO_LLM_API_KEY`. Nenhuma linha de `storage/vector_store.py` foi tocada (conforme restrição de escopo).

---

## 3. PASSOS 2 E 3 — F4-019 E F4-020 (TESTES VERMELHOS S1–S8, IMPLEMENTAÇÃO E VERDE)

### 3.1 Passo 2 — Testes Vermelhos no Código Anterior (`96ba4d0`)
#### `scratch/evidencia_4_2h/p2_red_egress_guard.txt`
```text
{read_ev("p2_red_egress_guard.txt")}
```

### 3.2 Passo 3 — Diff de Produção (`ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py`, `interface/cli.py`, `.env.example`)
#### `scratch/evidencia_4_2h/p3_diff_producao.txt`
```diff
{read_ev("p3_diff_producao.txt")}
```

### 3.3 Passo 3 — Testes Verdes (`tests/test_llm_egress_guard.py`)
#### `scratch/evidencia_4_2h/p3_green_egress_guard.txt`
```text
{read_ev("p3_green_egress_guard.txt")}
```

### 3.4 Passo 3 — Regressão dos Testes de Persistência de Sumários e Reparo Vetorial (Rodada 4.1)
#### `scratch/evidencia_4_2h/p3_summary_persistence.txt`
```text
{read_ev("p3_summary_persistence.txt")}
```

---

## 4. PASSO 4 — F4-021: SCANNER DE SEGREDOS, REDAÇÃO DE EVIDÊNCIAS, FILTRO DE LOGS E REGRA 13

### 4.1 Passo 4a — Scanner `scratch/tools/scan_secrets.py` (Antes e Depois da Redação)
#### `scratch/evidencia_4_2h/p4a_scan_before.txt`
```text
{read_ev("p4a_scan_before.txt")}
```
#### `scratch/evidencia_4_2h/p4a_scan_after.txt`
```text
{read_ev("p4a_scan_after.txt")}
```

### 4.2 Passo 4b — `git diff --stat` dos Arquivos Redigidos e `git grep` Pós-Redação
#### `scratch/evidencia_4_2h/p4b_diff_stat.txt`
```text
{read_ev("p4b_diff_stat.txt")}
```
#### `scratch/evidencia_4_2h/p4b_git_grep_after.txt`
```text
{read_ev("p4b_git_grep_after.txt")}
```

### 4.3 Passo 4c — Teste `tests/test_no_secrets_in_tracked_files.py` (Vermelho e Verde)
#### `scratch/evidencia_4_2h/p4c_red_no_secrets.txt`
```text
{read_ev("p4c_red_no_secrets.txt")}
```
#### `scratch/evidencia_4_2h/p4c_green_no_secrets.txt`
```text
{read_ev("p4c_green_no_secrets.txt")}
```

### 4.4 Passo 4d — Filtro de Segredos em `main.py` (`setup_logging`) e Testes R1–R5 (`tests/test_secret_redaction.py`)
#### `scratch/evidencia_4_2h/p4d_red_secret_redaction.txt`
```text
{read_ev("p4d_red_secret_redaction.txt")}
```
#### `scratch/evidencia_4_2h/p4d_green_secret_redaction.txt`
```text
{read_ev("p4d_green_secret_redaction.txt")}
```

### 4.5 Passo 4d/4e — Diff de `main.py` e `AUDIT_PROTOCOL.md` (Regra 13)
#### `scratch/evidencia_4_2h/p4d_diff_main_proto.txt`
```diff
{read_ev("p4d_diff_main_proto.txt")}
```

---

## 5. PASSO 5 — SUÍTE COMPLETA E 5 VERIFICAÇÕES DE MUTAÇÃO

### 5.1 Suíte Completa (`pytest tests/ -q`)
#### `scratch/evidencia_4_2h/p5_full_pytest.txt`
```text
{read_ev("p5_full_pytest.txt")}
```

### 5.2 Mutação (i): Restaurar Fallback Gemini -> OpenAI no Async (`S2` falha)
#### `scratch/evidencia_4_2h/p5_mut1_s2.txt`
```text
{read_ev("p5_mut1_s2.txt")}
```

### 5.3 Mutação (ii): Remover Tratamento de `"none"` (`S1` falha)
#### `scratch/evidencia_4_2h/p5_mut2_s1.txt`
```text
{read_ev("p5_mut2_s1.txt")}
```

### 5.4 Mutação (iii): Remover `async with` no `AsyncOpenAI` (`S6` e `S7` falham)
#### `scratch/evidencia_4_2h/p5_mut3_s6_s7.txt`
```text
{read_ev("p5_mut3_s6_s7.txt")}
```

### 5.5 Mutação (iv): Remover Instalação do Filtro em `setup_logging` (`R5` falha)
#### `scratch/evidencia_4_2h/p5_mut4_r5.txt`
```text
{read_ev("p5_mut4_r5.txt")}
```

### 5.6 Mutação (v): Inserir Token de Chave Falsa em Arquivo de `scratch/` (`4c` falha)
#### `scratch/evidencia_4_2h/p5_mut5_4c.txt`
```text
{read_ev("p5_mut5_4c.txt")}
```

---

## 6. PASSO 6 — PROVA DE REDE COM TRIPWIRE PROXY (E2E) E HARNESS F4-017

### 6.1 Passo 6A — Tripwire Proxy E2E (`E1`, `E2`, `E3`, $n=3$ sequenciais no Commit Antigo `96ba4d0` e no `HEAD` Novo)
#### `scratch/evidencia_4_2h/p6_tripwire_summary.txt`
```text
{read_ev("p6_tripwire_summary.txt")}
```

**Observação Técnica sobre `Event loop is closed` no Subprocesso Curto vs. Sessão Longa:**
- No commit antigo (`old_96ba4d0`), cada execução de `E1`, `E2` e `E3` disparou **27 requisições `CONNECT api.openai.com:443`** no Tripwire Proxy (`3 arquivos × 3 tentativas do tenacity × 3 tentativas internas do SDK openai = 27`), **12 linhas `ERROR`** (`9` falhas de chamada OpenAI + `3` quedas para Dumb Summary) e **9 linhas `WARNING`** (`3 arquivos × 3 tentativas`). Como o subprocesso de teste encerrou logo após `count_embeddings`, o coletor de lixo do CPython (`gc`) pode não executar um ciclo de coleta dos objetos `httpx.AsyncClient` órfãos antes do término do processo (motivo pelo qual `test_s7_orchestrator_asyncio_run_closes_clients_no_unraisable_loop_closed` em `tests/test_llm_egress_guard.py` invoca `gc.collect()` explicitamente após `asyncio.run`, reproduzindo deterministamente o `RuntimeError: Event loop is closed` sem `async with` e provando `0` ocorrências com `async with`).
- No commit novo (`new_6b3202b`), `E1` (`GRAFO_LLM_MODEL=none`) e `E2` (`GRAFO_LLM_MODEL=gpt-4o-mini` sem provedor explícito) geraram **0 requisições no proxy** (`PrxTot=0, OpenAI=0, Google=0`), `0` linhas `ERROR`, e persistiram `nodes=4, vecs=3, SumNULL=4, Sum!=NULL=0`. Já `E3` (`GRAFO_LLM_PROVIDER=openai` explícito) gerou as **27 requisições `CONNECT api.openai.com:443`** esperadas, comprovando que a escolha explícita do provedor funciona e respeita o proxy.

### 6.2 Passo 6B — Harness de Regressão F4-017 (`search-first` e `mine`, $n=3$ por cenário, sequencial) em `venv_mcp127` e `venv_mcp130_full` com `GRAFO_LLM_MODEL=none`
#### `scratch/evidencia_4_2h/p6_f4_017_regression.txt`
```text
{read_ev("p6_f4_017_regression.txt")}
```

---

## 7. VERIFICAÇÃO FINAL DE SEGREDOS, SINCRONIZAÇÃO GIT E LIMITAÇÕES (O QUE NÃO FOI VERIFICADO)

### 7.1 Execução Final do Scanner `scratch/tools/scan_secrets.py` e Teste `test_no_secrets_in_tracked_files.py`
#### `scratch/evidencia_4_2h/p7_final_scan_secrets.txt`
```text
{read_ev("p7_final_scan_secrets.txt")}
```

### 7.2 Lista Explícita do que NÃO Foi Verificado (Regra 12)
1. **Outras máquinas e sistemas operacionais:** **NÃO VERIFICADO** (todos os testes E2E desta rodada foram executados exclusivamente nesta máquina Windows local; o CI Windows executa os testes de `windows-stdin.yml` no GitHub Actions).
2. **Provedores reais de LLM com chaves válidas (OpenAI, Gemini, endpoint customizado real):** **NÃO VERIFICADO** (por força da regra dura de segredos desta rodada, nenhuma execução tentou rede real com chave real; todas as verificações usaram chaves falsas explícitas, dublês de construtores ou o Tripwire Proxy local respondendo `403`).
3. **Re-teste interativo manual no aplicativo Claude Desktop após os commits da Rodada 4.2h:** **NÃO VERIFICADO** (a verificação E2E desta rodada foi realizada via cliente MCP real `stdio_client` automatizado em `run_tripwire_e2e.py` e `run_f4_017_regression.py`).
"""
    )

    out_file = AUDITS_DIR / "relatorio_4_2h.md"
    out_file.write_text("\n".join(sections), encoding="utf-8")
    print(f"Generated {out_file} ({out_file.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

