# Fase 4 — Roadmap e diário de auditoria

> **Documento vivo, somente-adição.** É um índice: o detalhe de cada achado fica em `audits/fase4-achados.md`, e as decisões do dono em `audits/fase4-decisoes.md`. Não duplicar o conteúdo deles aqui.
> **Regras de manutenção:** (1) toda linha aponta para uma evidência (commit, arquivo ou saída de comando); (2) novas entradas vão no fim de cada tabela; mudança de status é feita na própria linha, com a rodada e o commit que a justificam; (3) "CORRIGIDO" só com prova executável (teste vermelho→verde reproduzido por auditor independente); (4) quem audita redige o texto da atualização, o executor só o commita (Regra 11), e o auditor confere na rodada seguinte.
> Última atualização: 2026-10-20, HEAD 4a55d6e (4.1/G). Criado pelo auditor independente; mantido pelo executor.

## 1. Papéis

| Papel | Quem | Função |
|---|---|---|
| Dono | Luis Filipe | Decide (gates da Regra 7); não é programador |
| Executor | Antigravity | Executa cada rodada, commita, devolve relatório |
| Auditor independente | Claude (qualquer IA que assuma) | Clona o repo público, verifica cada afirmação, redige o próximo pedido |

Preferências do dono: honestidade acima de tudo, caminho mais eficiente e profissional, sem bajulação, em português.

## 2. Backlog congelado

88 itens (87 achados + 1 observação): 3 Máxima, 21 Crítica, 30 Grave, 29 Média, 5 Baixa. Fonte: `audits/backlog-final.md`. Fase 3 aprovada pelo dono no commit `40b20c9`. Novos achados entram só em `fase4-achados.md`.

## 3. Rodadas

| Rodada | Commit(s) | Entregou | Status | Verificado pelo auditor |
|---|---|---|---|---|
| 4 (regras) | `a227616` | Regras da Fase 4; retificações BL-001/003/004 | Concluída | Sim |
| 4.1/A | `5f641c3` | Inventário de DDL das 5 tabelas ausentes | Concluída | Sim |
| 4.0 | `9fe1d6d` | Mapa de dependências para poda | Concluída | Sim (com ressalvas) |
| 4.0b | `aacca16` | Prova de execução do alcance | Concluída, **com erros** corrigidos na 4.0c | Sim (errata §11) |
| 4.0c | `153d1ff` | Prova corrigida, matriz de ferramentas, F4-001…F4-007 | Concluída | Sim |
| 4.1/B | `f98aaea`, `f67fdf6` | F4-006 corrigido (log abortava mineração) | Concluída | Sim, com modelo real |
| 4.1/C | `f07cb65`, `76e6a7e` | Guarda de log bidirecional; investigação F4-008/F4-009 | Concluída | Sim |
| 4.1/D | `de90005`, `8e6f887`, `af9001a` | Reparo de vetores (F4-008/009); sumários persistidos (F4-010) | Código OK; relatório tinha trechos inventados | Sim (veredito 2026-10-19) |
| 4.1/E | `8d963ae`, `d7a88ff`, `641d327` | F4-011 via SQLite; dedup de falhas; consulta leve do reparo; `[DUMB]` omitido; teste (g) em todos os vetores; relatório retificado | Código OK; teste do [DUMB] corrigido na 4.1/F | Sim (2026-10-20) |
| 4.1/F | `9b70eef`, `bd821e7` | Corrigir o teste vazio do `[DUMB]`; commitar este roadmap; ajustar relatório | Concluída | Sim (2026-10-19) |
| 4.1/G | `4c505d1`, `4a55d6e` | Resíduo F4-009 + investigação de nodes.summary (somente leitura) | Concluída | — |
| 4.2 | — | Desacoplar `mcp_governor` de `telemetry_api`; cortar `interface/__init__`→`ActionHooks`→`RevisorCritico` (inclui BL-015) | PLANEJADO, NÃO AUTORIZADO | — |
| 4.3 | — | DDL só de `agent_checkpoints`; reimplementar `concierge_get_call_chain` sobre `edges`/`nodes` (caminhos de arquivo, só `calls`) | PLANEJADO, NÃO AUTORIZADO | — |
| 4.4 | — | Remover `wing_keywords` de vez, com teste-guarda e regra de neutralidade no protocolo/CONTRIBUTING | PLANEJADO, NÃO AUTORIZADO | — |
| 4.5 | — | Quarentena do código dormente em `archive/v4-experimental` (após 4.2) | PLANEJADO, NÃO AUTORIZADO | — |

## 4. Achados da Fase 4 (índice; detalhe em `fase4-achados.md`)

| ID | Resumo | Severidade | Status | Evidência |
|---|---|---|---|---|
| F4-001…F4-005, F4-007 | Achados de alcance/estrutura da 4.0b/4.0c | ver arquivo | Abertos (F4-003: avaliar rebaixar, é dormente) | `fase4-achados.md` |
| F4-006 | Formato de log abortava a mineração antes dos embeddings (RichHandler) | CRÍTICA | CORRIGIDO | `f98aaea`, `f07cb65`; E2E com modelo real |
| F4-008 | Hash gravado antes de embeddings/vetores; vetores ausentes nunca refeitos | CRÍTICA | CORRIGIDO | `de90005`, reparo reproduzido; red→green reproduzido na 4.1/E |
| F4-009 | Sem caminho de reindexação (texto precisa mencionar o `_sync_vectors` do Janitor, inativo por padrão) | GRAVE | CORRIGIDO (texto ajustado na 4.1/G) | `de90005` |
| F4-010 | Sumários L0 gerados e descartados | GRAVE | CORRIGIDO | `8e6f887` |
| F4-011 | Filtro `node_type` no Chroma excluía vetores sem a chave | GRAVE | CORRIGIDO | `8d963ae`; teste (i) vermelho em `af9001a`, verde em HEAD (reproduzido) |
| F4-012 | `[DUMB]` persistido quando não há LLM | A confirmar (observação) | CORRIGIDO: [DUMB] omitido (`8d963ae`), teste efetivo (`9b70eef`) | ver §5 |

## 5. Verificação independente da 4.1/E (2026-10-20)

Conferi diretamente o código e rodei testes em worktree.
- **Confirmado:** o filtro `node_type` saiu do Chroma e passou para o SQLite (`get_node_types_batch`, `hybrid_search.py`); o `node_type` volta no resultado. Testes novos da 4.1/E contra a produção de `af9001a`: `test_scenario_a` (dedup) e `test_scenario_i` (F4-011) **falham**; em HEAD passam. Os 14 testes dos três arquivos da Fase 4 passam em HEAD.
- **Confirmado:** `repair_missing_vectors` agora consulta só ids (`get_active_node_ids_with_content`) e carrega conteúdo só dos ausentes; a re-tentativa imediata é pulada quando o passo 5 falhou, e `embeddings_failed` deixa de duplicar.
- **Problema:** `test_dumb_summary_not_persisted_in_nodes_table` **passa também no código antigo**. O stub só define `summarize_l0`; o pipeline chama `summarize_l0_async`/`summarize_l0_grouped`, que o stub não tem, então nenhum resumo `[DUMB]` é gerado (medi: 0 objetos criados). Com um stub completo, o código antigo grava `[DUMB] ...` e o novo deixa `summary` nulo, ou seja, a correção funciona, mas o teste não a protege.
- **Limitação deliberada de projeto:** sem filtro no Chroma, a busca vetorial pega `top_k*5` candidatos e filtra depois. Para um `node_type` raro entre muitos, pode não sobrar candidato vetorial. Trade-off aceitável, mas deve constar como observação.
- **Não reproduzido por mim:** os números de benchmark (1.000/10.000 nós) vieram de execução do Antigravity no Windows; não rodei `scratch/scale_benchmark_repair.py`. Tratar como informado, não verificado.
- **Não verificado:** suíte completa. No meu ambiente 3 arquivos de teste não coletam (`fastapi` ausente), então não confirmei a contagem de testes do relatório.
- **Efeito residual:** nós minerados entre `af9001a` e `8d963ae` podem ter `[DUMB]` já gravado no `nodes.summary`; nenhuma rodada limpou isso.

## 6. Decisões do dono (data da decisão no `fase4-decisoes.md`)

1. Caminho B: só `agent_checkpoints`; Delta/Survival dormente; quarentena depois de desacoplar.
2. `wing_keywords` removido em definitivo.
3. F4-006 CRÍTICA; `get_call_chain` por caminhos de arquivo, só `calls`.
4. Desenho "reparo de vetores + relato honesto": F4-008 CRÍTICA, F4-009 GRAVE, F4-010 GRAVE; F4-010 na mesma rodada.
5. Laya: estacionado.
6. Este roadmap: aprovado como documento vivo (2026-10-19).
7. Escopo da 4.1/E: aprovado. Política `[DUMB]`: confirmada pelo dono ("sem LLM, nodes.summary permanece NULL").

## 7. Pendências abertas

- Corrigir o teste do `[DUMB]` (4.1/F); decidir sobre limpeza de `[DUMB]` já gravados.
- Ajustar texto de F4-009 (Janitor).
- Severidade do BL-088; reorganizar Seções 3 e 4 do backlog-final; nota de evidência em BL-011 (`set_state` permite autoescalada); backfill de sumários nulos; ruído de CRLF/`.gitattributes`.

## 8. Padrões de erro já vistos (verificar sempre)

- Trechos "literais" reconstruídos de memória em vez de colados (4.1/D).
- Saída de teste vermelho que não corresponde aos testes commitados.
- Achado novo com causa errada e status "CORRIGIDO" sem prova (F4-011 original).
- **Teste que passa antes e depois da correção** (4.1/E, `[DUMB]`). Todo teste novo precisa falhar no código anterior.
- Afirmações absolutas sem checar tudo ("não existe caminho de reindexação", "100% viável", "29 de 31").
- Do lado do auditor: aceitar uma afirmação sem olhar o Janitor; verificar versão de biblioteca só no próprio sandbox.
