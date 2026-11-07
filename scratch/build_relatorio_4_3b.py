# -*- coding: utf-8 -*-
"""
Script gerador do Relatório da Rodada 4.3b (Regras 12 e 14 do AUDIT_PROTOCOL.md)
Produz audits/relatorio_4_3b.md em UTF-8 puro, sem BOM e sem bytes nulos.
"""
import os
import subprocess
import sys


def main():
    p0_head = "1a12c03d6dd8ad3425075593483303e58b3855c9"
    p0_ls_remote = "1a12c03d6dd8ad3425075593483303e58b3855c9"

    res = subprocess.run(
        ["git", "log", "--oneline", f"{p0_head}..HEAD"],
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )
    commit_lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]

    commits_md = "\n".join([f"- `{c}`" for c in commit_lines]) if commit_lines else "- *(Commits em andamento)*"

    doc = f"""# Relatório da Rodada 4.3b (Executor: Antigravity)

**Data:** 2026-11-06  
**Status da Rodada:** corrigido pelo executor, aguardando verificação independente  
**Conformidade Normativa:** Regras 2, 3, 4, 10, 11, 12, 13 e 14 do `AUDIT_PROTOCOL.md`

---

## 1. Contexto & HEAD de Partida

- **HEAD local de partida:** `{p0_head}` (comprovado em [`scratch/evidencia_4_3b/p0_head.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/p0_head.txt))
- **HEAD remoto de partida:** `{p0_ls_remote}` (`origin/main`, comprovado em [`scratch/evidencia_4_3b/p0_ls_remote.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/p0_ls_remote.txt))
- **Alinhamento inicial:** Local e remoto perfeitamente idênticos no início da rodada.

---

## 2. Propósito do Projeto & Decisões Arquiteturais

O Grafo Concierge foi desenhado para ser a ferramenta de memória mais sólida para agentes de IA: **confiável**, **honesta sobre o que sabe** e **sem vazamento entre projetos** (*zero cross-project leakage*).

Na Rodada 4.3b, cada decisão arquitetural foi pautada estritamente por esse tríptico:

1. **Exclusão do Arquivo de Origem na Busca por Símbolo (Item 2a):**
   - *Problema:* Quando o usuário ou agente consulta a cadeia de chamadas partindo de um símbolo específico (ex: `process_data`), o arquivo onde a função está declarada (ex: `core/pipeline.py`) não é uma dependência que o símbolo chama. Incluí-lo na lista de retornos induzia a alucinação de que a função chamava a si própria ou ao seu módulo pai.
   - *Decisão:* O arquivo de origem é omitido da lista final retornada, mas o algoritmo continua a explorar as arestas BFS através de outros símbolos declarados no mesmo arquivo, preservando fidelidade semântica.
2. **Eliminação de Colisões por Caracteres Curinga LIKE (Item 2b):**
   - *Problema:* No SQLite, consultas `LIKE 'prefix/%'` tratam `_` como curinga de caractere único. Caminhos como `a_b.py` capturavam falsamente chamadas de `axb.py`.
   - *Decisão:* Substituição de consultas `LIKE` desprotegidas por comparação exata de substring `substr(label, 1, ?) = ?` para caminhos de arquivos e comparação estrita `label = ?` para símbolos.
3. **Detecção e Rejeição de Pastas Homônimas entre Projetos (Item 2c):**
   - *Problema:* Múltiplos projetos registrados podem possuir a mesma pasta raiz (`folder_name`, ex: `src`, `app` ou `workspace`). Aceitar silenciosamente qualquer um causava contaminação de contexto entre bases de código distintas.
   - *Decisão:* Se `folder_name` existir em mais de um projeto ativo, o sistema levanta `ValueError` explícito indicando ambiguidade e orientando o uso do UUID canônico do projeto.
4. **Anonimização da Mensagem de Ambiguidade de Projetos (Item 2d):**
   - *Problema:* Mensagens de erro contendo os nomes ou UUIDs de todos os projetos concorrentes vazavam informações confidenciais sobre quais projetos existem no mesmo servidor para um agente sem autorização.
   - *Decisão:* A mensagem de erro reporta unicamente a contagem anônima (`found in N projects; specify project_identifier`), sem vazar nomes ou identificadores de outros projetos.
5. **Rejeição Estrita de Tipos Booleanos em `depth_limit` (Item 2e):**
   - *Problema:* Em Python, `bool` é subclasse de `int` (`isinstance(True, int) == True`, com valor 1). Chamadas com `depth_limit=True` eram silenciosamente executadas com profundidade 1.
   - *Decisão:* Validação explícita `if isinstance(depth_limit, bool) or not isinstance(depth_limit, int) or depth_limit <= 0:` levantando `ValueError`.
6. **Eliminação de Estado Compartilhado Concorrente no Checkpointer (Item 4):**
   - *Problema:* `AgnosticCheckpointer` mantinha um atributo de instância mutável `self.last_error`. Se duas threads executassem `save_checkpoint` simultaneamente, a mensagem de erro da Thread A sobrescrevia a da Thread B antes que ela pudesse ser serializada na resposta MCP.
   - *Decisão:* Criação do método `save_checkpoint_detailed(...) -> Tuple[bool, Optional[str]]`, retornando o erro localmente por chamada sem estado global. O método `save_checkpoint` original foi preservado como wrapper retrocompatível.

---

## 3. Lista de Commits Desta Rodada

| Commit | Escopo | Mensagem |
|---|---|---|
| `019eee8` | Itens 1, 2, 3 e 4 | `fix(graph,checkpointer): fix call chain defects, rewrite broken tests, and isolate checkpointer errors (4.3b)` |
| `fb40d69` | Item 5 (Documental) | `docs(audit): create errata-4-3 under Rule 14` |
| *(este commit)* | Encerramento | `docs(audit): finalize relatorio_4_3b, update roadmap and findings for 4.3b` |

---

## 4. Matriz de Resultados (Vermelho, Verde, Mutações & Evidências)

### 4.1. Item 1: Reescrita dos 6 Testes Quebrados sobre o Esquema Canônico
Os testes legados que dependiam da tabela extinta `ast_edges` ou de assinaturas antigas foram reescritos utilizando fixtures oficiais com `SchemaManager.apply_full_schema()` e a tabela canônica `edges` (`relation_type='calls'`).

- **Reprodução (RED):** [`scratch/evidencia_4_3b/item1_6_tests_red.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item1_6_tests_red.txt) (6 falhas confirmadas com `no such table: ast_edges` e divergências de retorno).
- **Correção (GREEN):** [`scratch/evidencia_4_3b/item1_6_tests_green.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item1_6_tests_green.txt) (Todos os 6 testes passando 100%):
  1. `tests/test_graph_rag_loops.py::test_depth_limit_enforcement` -> PASSED
  2. `tests/test_graph_rag_loops.py::test_indirect_cycle_resolution` -> PASSED
  3. `tests/test_graph_rag_loops.py::test_substring_collision_prevention` -> PASSED (comprovando que `a.py` não captura `aa.py` nem `a_b.py`)
  4. `tests/test_graph_rag_janitor.py::test_should_resolve_multi_hop_dependencies_via_sqlite_cte_recursive` -> PASSED
  5. `tests/test_mcp_server_extensions.py::test_mcp_tool_concierge_get_call_chain` -> PASSED
  6. `tests/test_e2e_concierge_integration.py::test_e2e_flow_full_lifecycle_and_communication` -> PASSED

### 4.2. Item 2: Defeitos 2a a 2e de `get_call_chain_recursive`
- **Reprodução (RED):** [`scratch/evidencia_4_3b/item2_defects_red.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item2_defects_red.txt) (Falhas nos 5 cenários reprodutores).
- **Correção (GREEN):** [`scratch/evidencia_4_3b/item2_defects_green.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item2_defects_green.txt) (Todos os 5 cenários passando).
- **Comportamento 2f (Símbolo Global Repetido):** Documentado e testado. O orquestrador de ingestão utiliza `global_symbol_map[name][0]` quando há colisão global não qualificada; o `GraphRAGEngine` reflete esse mapeamento de forma determinística sem alterações na lógica central do orquestrador.

### 4.3. Item 3: Suíte Expandida de Testes em `tests/test_call_chain_edges_nodes.py`
A suíte foi expandida para 15 testes completos, cobrindo todos os requisitos e cenários de borda:
- Nós `STALE` e `ARCHIVED` ignorados como raiz e destino;
- Início por símbolo exclui arquivo de origem;
- Caminhos com caracteres curinga (`_`, `%`, `\`);
- `folder_name` duplicado entre projetos;
- Mensagem de ambiguidade estritamente anônima;
- Identificador de projeto inexistente;
- Símbolo com nomes repetidos em múltiplos nós;
- Teste E2E MCP real com ingestão completa de 3 arquivos (`GRAFO_LLM_MODEL=none`).
- **Evidência GREEN (15 testes passando):** [`scratch/evidencia_4_3b/item3_15_tests_green.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item3_15_tests_green.txt).

### 4.4. Mutações Obrigatórias Executadas e Mortas (Item 3)
Todas as 5 mutações do Bloco 2 foram executadas individualmente contra a nova suíte de testes e foram mortas com falhas esperadas:

| Mutação | Descrição | Status | Arquivo de Evidência |
|---|---|---|---|
| **Mutação 1** | Incluir arquivo de origem ao pesquisar por símbolo | **KILLED** (`FAILED`) | [`scratch/evidencia_4_3b/b2_mutation_include_origin_file.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/b2_mutation_include_origin_file.txt) |
| **Mutação 2** | Retornar para consulta `LIKE` desprotegida | **KILLED** (`FAILED`) | [`scratch/evidencia_4_3b/b2_mutation_unescaped_like.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/b2_mutation_unescaped_like.txt) |
| **Mutação 3** | Desativar verificação de duplicidade de `folder_name` | **KILLED** (`FAILED`) | [`scratch/evidencia_4_3b/b2_mutation_remove_folder_ambiguity.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/b2_mutation_remove_folder_ambiguity.txt) |
| **Mutação 4** | Incluir nomes e UUIDs de projetos na mensagem de erro | **KILLED** (`FAILED`) | [`scratch/evidencia_4_3b/b2_mutation_leak_names_uuids.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/b2_mutation_leak_names_uuids.txt) |
| **Mutação 5** | Aceitar `depth_limit=True` sem validar tipo booleano | **KILLED** (`FAILED`) | [`scratch/evidencia_4_3b/b2_mutation_accept_bool.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/b2_mutation_accept_bool.txt) |

### 4.5. Item 4: Eliminação de Estado Concorrente em `AgnosticCheckpointer`
- Criado método `save_checkpoint_detailed(...) -> Tuple[bool, Optional[str]]`.
- Atualizado `interface/mcp_server.py:agent_save_checkpoint` para consumir `save_checkpoint_detailed`.
- Adicionado teste de concorrência com 2 threads simultâneas (`test_concurrent_save_checkpoint_does_not_mix_errors`) e teste de compatibilidade do wrapper (`test_save_checkpoint_legacy_wrapper`).
- **Evidência GREEN (9 testes passando):** [`scratch/evidencia_4_3b/item4_green_checkpoints.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item4_green_checkpoints.txt).

### 4.6. Item 5: Errata Oficial da Rodada 4.3 sob a Regra 14
- Criado arquivo [`audits/errata-4-3.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/errata-4-3.md) retificando formalmente:
  1. Assinatura e nomes de parâmetros de `concierge_get_call_chain` (`start_node`, `depth_limit`, `project_identifier`);
  2. Implementação de resolução de escopo via SQL próprio direto em `core/graph_rag.py`;
  3. Ausência de filtro ou checagem de `privacy_level` nas consultas de leitura;
  4. Omissão da suíte completa de testes no relatório anterior;
  5. Rastreabilidade do script gerador `scratch/build_relatorio_4_3.py`.
- Todas as citações foram extraídas por comando `grep -n` e registradas em [`scratch/evidencia_4_3b/item5_errata_greps.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/item5_errata_greps.txt).

---

## 5. Execução da Suíte Completa de Testes em Venv Limpo Isolado

Em conformidade com a exigência estrita do Pedido 4.3b, a suíte completa de testes foi executada em um ambiente virtual inteiramente novo e isolado:
- **Criação do ambiente:** `python -m venv .venv_clean`
- **Instalação isolada:** `PYTHONNOUSERSITE=1 .venv_clean\\Scripts\\pip install -e ".[dev]"`
- **Execução:** `.venv_clean\\Scripts\\pytest tests -v`
- **Arquivo de Evidência Completa (UTF-8 puro):** [`scratch/evidencia_4_3b/full_suite_run.txt`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/evidencia_4_3b/full_suite_run.txt)

### Placar Oficial da Suíte Completa:
- **Passed:** `445`
- **Failed:** `0`
- **Skipped:** `0`
- **XFailed:** `1`
- **Total Coletado:** `446`
- **Tempo Total de Execução:** `294.49s` (~4 minutos e 54 segundos)

### Justificativa Comprovada do Único Teste XFAIL:
- **Teste:** `tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints`
- **Motivo:** O teste está explicitamente marcado com `@pytest.mark.xfail(strict=True, reason="BL-015: MCPToolGovernor inicia com default_state='EXECUTION' em vez de 'PLANNING' (ver audits/backlog-final.md#L309 e audits/fase4-roadmap.md)")`. Esse é um comportamento já catalogado no backlog pendente de decisão de produto (BL-015), não se tratando de regressão.

---

## 6. Declarações Normativas do Auditor/Executor

1. **Cláusula de Status da Auditoria:** Nenhum status do projeto foi alterado para "CORRIGIDO". Todos os itens sanados nesta rodada foram marcados estritamente como **"corrigido pelo executor, aguardando verificação independente"**, preservando o rigor do `AUDIT_PROTOCOL.md`.
2. **Scan de Segredos e Chaves:** O script oficial de varredura heurística (`scratch/tools/scan_secrets.py`) foi executado antes de cada commit.
   - Total de arquivos escaneados: > 1.140 arquivos;
   - Violações ou segredos encontrados: **Zero (0)**.
3. **Integridade de Codificação:** Todos os arquivos de evidência em `scratch/evidencia_4_3b/` e os documentos Markdown em `audits/` foram gravados em **UTF-8 puro, sem BOM e com zero bytes nulos**.

---

## 7. Próximos Passos & Regra de Parada (Regra 7)

A Rodada 4.3b está concluída em seu escopo integral. Conforme a **Regra 7** do protocolo de auditoria, a execução é interrompida imediatamente após o push dos commits na branch `main`. Nenhuma ação da Rodada 4.4 será iniciada de forma autônoma. O executor aguarda a avaliação da auditoria independente.
"""

    relatorio_path = r"audits\relatorio_4_3b.md"
    with open(relatorio_path, "wb") as f:
        f.write(doc.encode("utf-8"))

    # Validacao de UTF-8 puro
    with open(relatorio_path, "rb") as f:
        raw = f.read()

    assert not raw.startswith(b"\xef\xbb\xbf"), "BOM detectado em relatorio_4_3b.md!"
    assert b"\x00" not in raw, "Byte nulo detectado em relatorio_4_3b.md!"
    print(f"Relatório {relatorio_path} gerado com sucesso! Bytes: {len(raw)}, UTF-8 puro garantido.")


if __name__ == "__main__":
    main()

