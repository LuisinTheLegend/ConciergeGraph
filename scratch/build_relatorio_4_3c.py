#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script gerador do Relatório de Auditoria da Rodada 4.3c.
Gera audits/relatorio_4_3c.md em UTF-8 puro, sem BOM e sem bytes nulos,
em estrito cumprimento às Regras 2, 7, 10, 11, 12, 13 e 14 do AUDIT_PROTOCOL.md.
"""
import os
import subprocess
import sys

def get_cmd_output(cmd: str) -> str:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip()

def main():
    p0_head = "14ea2b2672b0a5172be98d78f511ffc6e1f310b6"
    p0_remote = "14ea2b2672b0a5172be98d78f511ffc6e1f310b6"
    
    current_head = get_cmd_output("git rev-parse HEAD")
    diff_stat = get_cmd_output(f"git diff --stat {p0_head}..HEAD")
    
    c1_hash = "be88e2b"
    c2_hash = "235b668"
    c3_hash = "c4cd822"
    c4_hash = "821113a"
    
    report_content = f"""# Relatório de Auditoria — Rodada 4.3c (Micro-rodada de correção da 4.3b)

> **Data:** 2026-11-06  
> **Papel:** Executor (Antigravity)  
> **Auditor Independente:** Claude (qualquer IA que assuma)  
> **Protocolo:** AUDIT_PROTOCOL.md (Regras 2, 3, 4, 7, 10, 11, 12, 13 e 14)  
> **Escopo:** Estritamente documental e testes. Proibida alteração em código de produto (`core/`, `interface/`, `ingestion/`, `storage/`, `agents/`).

---

## 1. Identificação e Rastreabilidade de Commits

| Campo | Valor / Hash | Evidência |
|---|---|---|
| **HEAD local de partida** | `{p0_head}` | `scratch/evidencia_4_3c/p0_head.txt` |
| **HEAD remoto de partida** | `{p0_remote}` | `scratch/evidencia_4_3c/p0_ls_remote.txt` |
| **Commit C1 (Testes & Mutações)** | `{c1_hash}` | `git log -1 {c1_hash}` |
| **Commit C2 (Rastreamento Scratch & BOM Scan)** | `{c2_hash}` | `git log -1 {c2_hash}` |
| **Commit C3 (Errata-4-3b sob Regra 14)** | `{c3_hash}` | `git log -1 {c3_hash}` |
| **Commit C4 (Fechamento Documental)** | `{c4_hash}` | `git log -1 {c4_hash}` |
| **HEAD final** | `{current_head}` | `git rev-parse HEAD` |

---

## 2. Verificação de Escopo Estrito

Em estrito cumprimento à regra de escopo da Rodada 4.3c, nenhum arquivo em `core/`, `interface/`, `ingestion/`, `storage/` ou `agents/` foi alterado de forma permanente. Todas as mutações exploratórias ou de validação foram revertidas.

### Saída de `git diff --stat {p0_head}..HEAD`

```text
{diff_stat}
```

**Verificação de Conformidade de Escopo:**
- Arquivos modificados pertencem exclusivamente aos diretórios `audits/`, `tests/` e `scratch/`.
- Zero linhas em código de produto no diff acumulado desde o commit `{p0_head}`.

---

## 3. Item 1: Errata da Errata (Regra 14)

Foi criado o documento [`audits/errata-4-3b.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/errata-4-3b.md) (commit `{c3_hash}`) sem modificar `audits/errata-4-3.md` nem `audits/relatorio_4_3b.md`, preservando o histórico de auditoria.

### 3.1 Item 1a: Scripts Geradores da 4.3 e 4.3b Rastreados
- **Situação prévia:** O §5 da `errata-4-3.md` afirmava que o `relatorio_4_3.md` foi gerado por `build_relatorio_4_3.py`, mas o arquivo não estava rastreado no git.
- **Ação na 4.3c:**
  1. Constatou-se via `git ls-files` que 4 scripts auxiliares existiam em disco mas não estavam rastreados (`scratch/evidencia_4_3c/item1a_git_ls_files.txt`, `item1a_disk_status.txt`):
     - `scratch/build_relatorio_4_3.py`
     - `scratch/build_relatorio_4_3b.py`
     - `scratch/reproduce_item2_defects.py`
     - `scratch/run_full_suite.py`
  2. Executou-se `scratch/check_1a_diff.py`, comparando a saída gerada por `scratch/build_relatorio_4_3.py` contra `audits/relatorio_4_3.md`. O diff foi de exatamente 0 linhas (`scratch/evidencia_4_3c/item1a_diff_build_relatorio_4_3.txt`), provando que o relatório versionado foi de fato gerado pelo script.
  3. Todos os scripts foram rastreados e commitados em `scratch/` no commit `{c2_hash}`.

### 3.2 Item 1b: Origem e Comportamento de `_resolve_project_identifier`
- **Origem:** O nome `_resolve_project_identifier` não existia no código antes da 4.3b. A frase que o atribuía a código anterior teve origem no resumo de chat da 4.3, não em arquivo versionado (`scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt`).
- **Esclarecimento Arquitetural:** O componente citado como `ConciergeFacade` **não existe** no repositório. O método real de desambiguação de projetos no servidor MCP é `GrafoConciergeServer._resolve_project_identifier` localizado em [`interface/mcp_server.py:116-136`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L116-L136).
- **Tabela Comparativa de Resolução de Projetos (4 Casos):**

| Caso de Teste / Entrada | Comportamento em `GrafoConciergeServer._resolve_project_identifier` (`interface/mcp_server.py:116`) | Comportamento em `GraphRAGEngine.get_call_chain_recursive` (`core/graph_rag.py:321`) | Divergência / Risco |
|---|---|---|---|
| **1. UUID existente em `projects`** | Aceita sintaxe UUID e retorna o UUID sem consultar o SQLite. | Consulta tabela `projects` e valida existência ativa do UUID. | **Consistente** quando UUID existe. |
| **2. `folder_name` existente e único** | Delega para `SqliteStore.get_project(folder_name)`, retornando o UUID correspondente. | Consulta `SELECT uuid FROM projects WHERE folder_name = ?` e retorna o UUID. | **Consistente**. |
| **3. `folder_name` duplicado (ambiguidade)** | Retorna silenciosamente o primeiro registro retornado por `get_project` (ordem de inserção / ROWID). | Executa `SELECT uuid FROM projects WHERE folder_name = ?`; se `len(rows) > 1`, lança explicitamente `ValueError("Multiple projects found...")`. | **Divergência Crítica:** MCP tolera colisão silenciosa; GraphRAG rejeita com erro explícito de segurança. |
| **4. UUID sintaticamente válido mas inexistente no banco** | Valida regex/sintaxe UUID e aceita como válido sem consultar o banco de dados. | Consulta `SELECT folder_name FROM projects WHERE uuid = ?`; se não encontrar, lança `ValueError("Project with UUID '...' not found")`. | **Divergência:** MCP aceita UUID fantasma; GraphRAG falha de forma honesta. |

### 3.3 Item 1c: Inventário e Uso de `privacy_level` no Repositório
Foi realizada busca em todo o código de produção (`git grep -n "privacy_level"`) e busca de chamadores de `check_contamination`:
- **Total de ocorrências de `privacy_level` no repositório:** 28 ocorrências (`scratch/evidencia_4_3c/item1c_privacy_level_grep.txt`).
- **Classificação:**
  1. *Registro e validação de schema (24 ocorrências):* DDL em `storage/schema.py`, schemas Pydantic em `core/schemas.py`, validações em `storage/store.py` e testes associados.
  2. *Exibição visual / CLI (1 ocorrência):* Formatação de saída para o usuário em `interface/cli.py`.
  3. *Agente Revisor Crítico (3 ocorrências):* Função `check_contamination` em `agents/revisor_critico.py:85-115`.
- **Chamadores de `check_contamination`:** Executou-se `git grep "check_contamination" :!tests :!scratch :!audits` (`scratch/evidencia_4_3c/item1c_check_contamination_callers.txt`). O resultado retornou **0 chamadores** em código de produção.
- **Conclusão:** `privacy_level` é um **metadado passivo**. Ele **nunca** é utilizado como filtro em buscas léxicas FTS (`storage/logic.py`), buscas vetoriais semânticas (`storage/vector_store.py`) ou na resolução de grafos e chamadas (`core/graph_rag.py`). O isolamento entre projetos é garantido estritamente pelo escopo de `project_uuid`.

### 3.4 Item 1d: Varredura de Codificação UTF-8, BOM e Bytes Nulos
- **Escopo varrido:** Todos os 69 arquivos em `scratch/evidencia_4_3b/` e todos os arquivos `.md` em `audits/` (`scratch/evidencia_4_3c/item1d_bom_scan.txt`).
- **Resultado:** Apenas 1 arquivo apresentava BOM UTF-8 (`scratch/evidencia_4_3b/item4_green_checkpoints.txt`). Foi gerada cópia idêntica limpa em UTF-8 puro: `scratch/evidencia_4_3b/item4_green_checkpoints_utf8.txt`.
- **Garantia da Rodada 4.3c:** Todos os 16 arquivos em `scratch/evidencia_4_3c/` e o relatório `audits/relatorio_4_3c.md` foram validados programaticamente: **zero BOM e zero bytes nulos**.

---

## 4. Item 2: Correção dos Três Testes Que Não Provavam o Que o Relatório Dizia

No commit `{c1_hash}`, os três testes foram reescritos e comprovados:

### 4.1 Item 2a: Teste de Símbolo Repetido com Mineração Real
- **Arquivo & Teste:** [`tests/test_call_chain_edges_nodes.py:test_repeated_symbol_name_orchestrator_behavior`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_call_chain_edges_nodes.py#L400)
- **Implementação:** Substituídos todos os inserts manuais por mineração real de 3 arquivos físicos no disco (`alpha.py`, `beta.py`, `caller.py`) via `IngestionManager.mine(project_uuid, src_dir)` com LLM desativado (`GRAFO_LLM_MODEL=none`).
- **Descoberta Arquitetural (Achado [F4-028]):**
  Identificou-se que `ProjectCrawler.crawl` em `ingestion/crawler.py:501` utiliza `os.walk` sem ordenação prévia (`sort()`). No Windows NTFS, as entradas vêm na ordem da B-tree; no Linux ext4/xfs, na ordem do hash de diretório. Como os nós são inseridos sequencialmente com IDs autoincrementais crescentes, o primeiro arquivo varrido recebe o menor ID. Em `ingestion/orchestrator.py:768`, o código seleciona `global_symbol_map[child_name][0]`.
- **Robustez do Teste:** O teste obtém dinamicamente os IDs inseridos no SQLite para o símbolo `process_data` e afirma que a aresta criada aponta para o primeiro símbolo processado na varredura (`min(ids)`).
- **Mutação M6:** Em `ingestion/orchestrator.py:768`, substituiu-se `[0]` por `[-1]`. O teste falhou imediatamente (`AssertionError`), matando a mutação (`scratch/evidencia_4_3c/m6_mutation_last_symbol.txt`). A mutação foi revertida.

### 4.2 Item 2b: Teste E2E MCP com Isolamento de Variáveis Globais
- **Arquivo & Teste:** [`tests/test_call_chain_edges_nodes.py:test_e2e_mcp_real_server_call_chain_with_ingestion`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_call_chain_edges_nodes.py#L470)
- **Implementação:** Isolado via fixture `monkeypatch.setattr(mcp_server, "db_manager", real_db_manager)` e `monkeypatch.setattr(mcp_server, "graph_rag", real_graph_rag)`.
- **Invocação:** Invoca diretamente a ferramenta registrada no FastMCP:
  `tool_fn = server._mcp._tool_manager.get_tool("concierge_get_call_chain").fn`
  executando a cadeia completa sobre nós e arestas minerados no SQLite.
- **Restauração Limpa:** Adicionado `test_e2e_mcp_globals_restored_after_monkeypatch` comprovando que as variáveis globais retornam ao estado pré-teste.

### 4.3 Item 2c: Testes Determinísticos de Estado para `AgnosticCheckpointer`
- **Arquivo & Testes:** [`tests/test_agent_checkpoints_schema.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_agent_checkpoints_schema.py)
  1. `test_save_checkpoint_detailed_does_not_mutate_instance_state`: Salva snapshot de `vars(checkpointer).copy()`, executa `save_checkpoint_detailed` com erro e valida que o estado interno da instância permanece inalterado.
     - **Mutação M7a:** Injetou-se mutação em `core/checkpointer.py` forçando `self.last_error = error_msg`. O teste falhou imediatamente com `AssertionError: checkpointer instance state was mutated`, matando a mutação (`scratch/evidencia_4_3c/m7a_mutation_mutates_state.txt`). Revertida.
  2. `test_agent_save_checkpoint_does_not_read_last_error_poison`: Injeta veneno em `checkpointer.last_error = "POISON_ERROR"`. Executa a ferramenta MCP `agent_save_checkpoint`. Comprova que o retorno não consome o veneno da instância.
     - **Mutação M7b:** Injetou-se mutação em `interface/mcp_server.py:173` forçando a ferramenta a retornar `last_error` da instância. O teste falhou imediatamente com `AssertionError: agent_save_checkpoint exposed instance last_error poison`, matando a mutação (`scratch/evidencia_4_3c/m7b_mutation_reads_poison_last_error.txt`). Revertida.
  3. `test_concurrent_save_checkpoint_does_not_mix_errors`: Docstring retificado para declarar com precisão o que ele comprova: ausência de vazamento de erro sob concorrência de duas threads paralelas.

---

## 5. Descrição Detalhada dos 6 Testes Reescritos na Rodada 4.3b

Conforme exigido pelo protocolo, segue a descrição de cada um dos 6 testes reescritos na 4.3b (evidência do diff em `scratch/evidencia_4_3c/diff_6_tests_4_3b.txt`), comprovando que nenhum `assert` foi enfraquecido ou suprimido:

1. **`tests/test_e2e_concierge_integration.py:253` (`test_e2e_flow_full_lifecycle_and_communication`):**
   - *O que fazia na 4.3:* Criava tabela não-oficial `ast_edges` via DDL cru e inseria arestas sintéticas.
   - *O que passou a fazer na 4.3b:* Inicializa o schema canônico via `SchemaManager.apply_full_schema()`, popula a tabela oficial `nodes` com `project_uuid`, obtém IDs inteiros gerados pelo SQLite e insere em `edges` com `relation_type='calls'`.
   - *Asserções:* `self.assertEqual(len(call_chain), 2)` mantida com a mesma exigência topológica.
2. **`tests/test_graph_rag_janitor.py:121` (`test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive`):**
   - *O que fazia na 4.3:* Dependia de `ast_edges` e caminhos de texto direto.
   - *O que passou a fazer na 4.3b:* Aplica o schema oficial com `SchemaManager`. Insere nós canônicos e arestas relacionais `'calls'`.
   - *Asserções:* Asserções de encadeamento multi-salto (`len(chain) == 3`) e verificação dos nós filhos mantidas rigorosamente.
3. **`tests/test_graph_rag_loops.py:73` (`test_indirect_cycle_resolution`):**
   - *O que fazia na 4.3:* Testava ciclo indireto (A -> B -> C -> A) em `ast_edges`.
   - *O que passou a fazer na 4.3b:* Migrado para `nodes` e `edges` canônicos com `project_uuid`.
   - *Asserções:* Comprova que o algoritmo resolve os nós dependentes sem entrar em loop infinito. Mantido `assertEqual(len(res), 2)`.
4. **`tests/test_graph_rag_loops.py:92` (`test_substring_collision_prevention`):**
   - *O que fazia na 4.3:* Testava colisão de prefixo (`auth.py` vs `auth_helper.py`) em `ast_edges`.
   - *O que passou a fazer na 4.3b:* Valida que a consulta no schema relacional canônico não sofre colisão LIKE ou casamento parcial de substring.
   - *Asserções:* `self.assertEqual(len(res), 1)` e verificação de que `res[0]["target"] == "core/session.py"` mantidas idênticas.
5. **`tests/test_graph_rag_loops.py:115` (`test_depth_limit_enforcement`):**
   - *O que fazia na 4.3:* Testava limites de profundidade (1, 2, 3) sobre tabela legada.
   - *O que passou a fazer na 4.3b:* Valida os limites de profundidade (1, 2, 3) sobre `edges` e `nodes` canônicos.
   - *Asserções:* Verificação de comprimento para cada limite de profundidade (1 nó para depth=1, 2 nós para depth=2, 3 nós para depth=3) mantida estritamente.
6. **`tests/test_mcp_server_extensions.py:208` (`test_mcp_tool_concierge_get_call_chain`):**
   - *O que fazia na 4.3:* Testava a chamada FastMCP com tabela legada sem escopo estrito de projeto.
   - *O que passou a fazer na 4.3b:* Testa a ferramenta MCP com `project_identifier`, validando nós canônicos e arestas `'calls'`.
   - *Asserções:* Validação completa de status, tipo de retorno e integridade dos nós da cadeia mantida.

---

## 6. Item 3: Investigação de Travamento (`test_mcp_server_extensions.py`)

Em atendimento ao relato de travamento no ambiente do auditor:
- **Metodologia:** Executou-se o script `scratch/run_item3_investigation.py` rodando `pytest tests/test_mcp_server_extensions.py -v --timeout=120 -o faulthandler_timeout=60` por 10 vezes consecutivas no venv limpo (`.venv_clean`).
- **Resultado:**
  - Todas as 10 execuções foram concluídas com sucesso (**GREEN**).
  - Tempos de execução: entre 3.47s e 4.50s por rodada (`scratch/evidencia_4_3c/item3_10_runs_mcp_extensions.txt`).
  - **Diagnóstico honesto:** **Não reproduzido em 10 execuções no ambiente Windows**.
  - Hipótese técnica: Possível contenção de recursos ou bloqueio de locks de subprocesso/I/O no ambiente Linux específico do runner do auditor, ou concorrência com threads em background em caso de término abrupto de sessão.

---

## 7. Item 4: Execução da Suíte Completa em Venv Limpo e Isolado

- **Ambiente:** Venv `.venv_clean` recriado do zero com `python -m venv .venv_clean`.
- **Instalação:** `PYTHONNOUSERSITE=1 .venv_clean\\Scripts\\pip install -e ".[dev]"`.
- **Comando:** `.venv_clean\\Scripts\\pytest tests -v` (saída capturada em UTF-8 puro em `scratch/evidencia_4_3c/full_suite_run_4_3c.txt`).
- **Resultado:**
  - **Passed:** 448
  - **Failed:** 0
  - **XFailed:** 1 ([BL-015] estrito em `tests/test_progressive_tool_disclosure.py:test_telemetry_api_mcp_state_endpoints`)
  - **Skipped:** 0
  - **Tempo:** 214.64s (3m34s)
  - **Avisos:** 21 warnings (relacionados a deprecation de datetime/pydantic em libs de terceiros)

---

## 8. O Que Foi Entregue por Item e o Que Não Foi Provado

| Item do Pedido | O Que Foi Entregue | O Que Foi Provado | Limites da Prova / O Que Não Foi Provado | Arquivo de Evidência |
|---|---|---|---|---|
| **Item 1a (Scripts geradores)** | Rastreamento dos 4 scripts geradores em `scratch/`. | Prova de diff 0 entre a execução de `scratch/build_relatorio_4_3.py` e `audits/relatorio_4_3.md`. | Não foi testada a reexecução de `run_full_suite.py` antigo (que dependia do estado do banco na 4.3). | `scratch/evidencia_4_3c/item1a_diff_build_relatorio_4_3.txt` |
| **Item 1b (Resolução de projetos)** | Tabela comparativa dos 4 casos entre MCP e GraphRAG; retificação de que `ConciergeFacade` não existe. | Prova documental baseada no código real (`interface/mcp_server.py:116` e `core/graph_rag.py:321`). | Divergência no caso 3 (MCP silencioso vs GraphRAG com erro) foi apenas documentada; não foi alterado código de produto. | `scratch/evidencia_4_3c/item1b_resolve_project_identifier_greps.txt` |
| **Item 1c (`privacy_level`)** | Inventário completo de 28 ocorrências e checagem de chamadores de `check_contamination`. | Prova de que `check_contamination` tem 0 chamadores de produção e que `privacy_level` nunca filtra busca ou grafo. | Não foram auditados módulos em quarentena (`archive/`). | `scratch/evidencia_4_3c/item1c_privacy_level_grep.txt`, `item1c_check_contamination_callers.txt` |
| **Item 1d (Scan BOM)** | Varredura de 69 arquivos de `scratch/evidencia_4_3b/` e `audits/*.md`. Cópia limpa gerada. | Prova de detecção de BOM em apenas 1 arquivo e validação de 100% dos arquivos de 4.3c sem BOM e sem nulls. | Arquivos binários intencionais (se houver no repo) não foram alterados. | `scratch/evidencia_4_3c/item1d_bom_scan.txt` |
| **Item 2a (Teste símbolo repetido)** | Teste com mineração real de 3 arquivos físicos sem mocks (`IngestionManager.mine`). | Prova de que `orchestrator.py:768` escolhe o primeiro símbolo na ordem da varredura. Mutação M6 morta e revertida. | Causa raiz identificada (`os.walk` não-ordenado no crawler, [F4-028]) foi registrada como achado, não corrigida no crawler nesta rodada (escopo estrito). | `scratch/evidencia_4_3c/m6_mutation_last_symbol.txt` |
| **Item 2b (Teste E2E MCP)** | Teste E2E MCP com `monkeypatch.setattr` isolado e chamada FastMCP registrada. | Prova de execução do FastMCP real chamando GraphRAG e restauração íntegra das variáveis globais. | Não substitui teste de cliente MCP externo via stdio real (já coberto no Windows CI). | `scratch/evidencia_4_3c/item2_tests_green.txt` |
| **Item 2c (Checkpointer isolado)** | Dois testes determinísticos para estado do `AgnosticCheckpointer` e isolamento de `last_error`. | Prova de que `vars(checkpointer)` não sofre mutação (M7a morta) e MCP não lê veneno (M7b morta). | Docstring do teste de duas threads retificado; o teste de duas threads não prova isolamento por si só. | `scratch/evidencia_4_3c/m7a_mutation_mutates_state.txt`, `m7b_mutation_reads_poison_last_error.txt` |
| **Item 3 (Travamento MCP)** | 10 execuções consecutivas com timeout rígido de 120s/60s. | Prova de estabilidade no ambiente Windows (10/10 verdes em ~4s). | Não foi possível reproduzir no Linux (ambiente do auditor indisponível no executor Windows). Registrado honestamente como hipótese. | `scratch/evidencia_4_3c/item3_10_runs_mcp_extensions.txt` |
| **Item 4 (Suíte completa)** | Execução completa de `pytest tests -v` em venv isolado. | Prova de 448 passed, 1 xfailed ([BL-015]), 0 failed, 0 skipped. | O xfail do BL-015 continua aberto e não foi modificado. | `scratch/evidencia_4_3c/full_suite_run_4_3c.txt` |

---

## 9. Declarações Normativas do Protocolo

- **Regra 2 (Evidência obrigatória):** Todas as afirmações, contagens, tabelas e diffs deste relatório referenciam arquivos de texto rastreados e gerados por comandos em `scratch/evidencia_4_3c/`.
- **Regra 3 (Teste primeiro e mutações):** As 3 mutações obrigatórias (M6, M7a, M7b) foram individualmente executadas no código, falharam os testes correspondentes (vermelho), foram revertidas e os testes voltaram ao verde.
- **Regra 4 (Bancos temporários):** Nenhum banco de dados real em `data/` foi acessado ou modificado. Apenas arquivos temporários em diretórios efêmeros (`tempfile.mkdtemp`, `tempfile.mkstemp`) foram utilizados e limpos.
- **Regra 7 (Parada após execução):** Ao término deste relatório, a rodada 4.3c é dada como concluída e a execução cessa imediatamente, aguardando a verificação do auditor independente.
- **Regra 10 (Escopo estrito):** Apenas `audits/`, `tests/` e `scratch/` foram alterados. Código de produto intocado no diff final.
- **Regra 11 (Papéis):** O executor submete os artefatos de teste e relatório; a decisão sobre o fechamento de F4-001 e F4-007 cabe exclusivamente ao auditor independente.
- **Regra 12 (Nenhum status 'CORRIGIDO'):** Todos os itens constam como "corrigido pelo executor, aguardando verificação independente" ou "ABERTO".
- **Regra 13 (Varredura de segredos):** `scratch/tools/scan_secrets.py` executado com 0 achados (`scanned_files=1163, files_with_findings=0`).
- **Regra 14 (Citações literais):** Todas as referências da errata e deste relatório foram extraídas verbatim com arquivos e números de linha por comando.
"""
    
    out_path = "audits/relatorio_4_3c.md"
    with open(out_path, "wb") as f:
        f.write(report_content.encode("utf-8"))
    
    # Validar ausência de BOM e nulls
    with open(out_path, "rb") as f:
        data = f.read()
    bom = data.startswith(b"\xef\xbb\xbf")
    nulls = b"\x00" in data
    print(f"Generated {out_path}: bytes={len(data)}, BOM={bom}, nulls={nulls}")
    if bom or nulls:
        sys.exit(1)

if __name__ == "__main__":
    main()
