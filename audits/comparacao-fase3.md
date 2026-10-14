# Comparação: Fase 3 refeita (v2) × Fase 3 consolidada (v1)

> **v1** = [`backlog-final.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md) (intacto).
> **v2** = [`backlog-final-v2.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final-v2.md), gerado só a partir dos 16 relatórios da Fase 1.
> **Scripts:** `scratch/fase3_redo_inventory.py`, `fase3_redo_build_v2.py`, `fase3_redo_compare.py`, `fase3_redo_repro_alias.py`.
> Este documento é uma **comparação**, não um novo relatório de achados.

## 1. Veredito

O inventário de **achados** do v1 está correto e completo. Refeito do zero, o v2 reproduz **88 itens** com as mesmas severidades e as mesmas fontes. As diferenças reais estão na **organização** do v1 (trilhas e fluxograma) e em **5 itens da Fase 1 que nunca viraram relatório** (o sexto item, `core/alias_tracker.py`, foi confirmado e formalizado no relatório `core-alias-tracker.md` e BL-088).

## 2. Onde v1 e v2 coincidem

| Verificação | Resultado |
|---|---|
| Linhas de achado nos 16 relatórios | 92 |
| Excluídas (2 falsos positivos + 2 duplicatas entre relatórios) | 4 |
| Esperado no backlog refeito | 88 (87 achados + 1 observação) |
| Achados esperados ausentes do v1 | **0** |
| BL do v1 que citam achado inexistente, falso positivo ou duplicata | **0** |
| Achado citado por mais de um BL | **0** |
| Divergências de severidade (fonte × BL) | **0** |
| Links `arquivo#Lnn` do v1 verificados contra o código atual | 119 verificados no clone público (**0 problemas**) + 11 links de `grafo-dashboard-web/` verificados apenas na origem (diretório excluído pelo `.gitignore`, sem reprodução por revisão externa); total de 130 links |

Totais por severidade:

| Severidade | v1 | v2 |
|---|:-:|:-:|
| Máxima | 3 | 3 |
| Crítica | 21 | 21 |
| Grave | 30 | 30 |
| Média | 29 | 29 |
| Baixa | 5 | 4 + 1 observação |
| **Total** | **88** | **88** |

A única diferença é de rótulo. A observação `core-delta-manager.md` #5 (BL-061) está como **Baixa** no v1 e como **Observação** no v2. O v1 já assume essa classificação em 87+1.

## 3. Diferenças encontradas no v1 (organização, não conteúdo)

1. **Faixas do fluxograma (Seção 3) não cobrem 22 itens.** BL-017 a 020, 022 a 024 e 037 a 051 não estão em nenhuma faixa. Os BL-017 a 024 estão na Seção 4 dentro de TRACK 2 e TRACK 4, e BL-037 a 051 estão em "Componentes de Suporte do Core".
2. **Existe um sétimo agrupamento não declarado.** O título diz "6 Tracks", mas há "Componentes de Suporte do Core (Checkpointer, Janitor, Governor)" com 16 itens, sem posição no fluxograma de dependências.
3. **Ordem de leitura quebrada.** BL-019 está no fim do arquivo (após BL-051), dentro de "Componentes de Suporte", mas é achado de `storage.md` (schema de checkpoints). BL-017/018/020/021 também aparecem fora da sequência numérica.
4. **Distribuição desigual.** TRACK 4 tem 23 itens e TRACK 1 tem 5. Isso pesa no planejamento, mas não é erro.

Nenhum desses pontos altera achados ou severidades. A correção seria só reorganizar ou corrigir as faixas, e isso fica para decisão sua.

## 4. Decisões de modelagem no v2

- **Trilhas por relatório de origem.** Mais simples de auditar, mas não segue dependência técnica. O v1 é melhor como roteiro de execução (por exemplo, o aviso de corrigir BL-033 e BL-034 juntos).
- **Perde-se no v2:** diretrizes de remediação, critérios de validação e dependências. O v2 é um índice rastreável, não um substituto do v1.
- **Ganha-se no v2:** nenhuma trilha fica fora do fluxo, e a rastreabilidade sai de um parser, não de edição manual.

## 5. Itens da Fase 1 sem relatório em `audits/` (lacuna dos dois backlogs)

O [AUDIT_PROTOCOL.md](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) marca como `[x]` seis itens auditados "manualmente nesta conversa" e originalmente não formalizados em relatórios dedicados. O que verifiquei no código atual:

| Item do protocolo | Verificação | Resultado |
|---|---|---|
| `core/alias_tracker.py`: `apply_alias_migration` não atômico | `scratch/fase3_redo_repro_alias.py` com o `ConciergeDatabaseManager` real: o 3º UPDATE falha com `no such column: parent_node_id`, mas `files` e `nodes` já ficaram migrados e commitados | **Reproduzido e formalizado (BL-088 em `core-alias-tracker.md`)** |
| `core/alias_tracker.py`: referência a `task_id` inexistente em `fsm_checkpoints` | `storage/relational_db.py:14` define `task_id TEXT` na DDL | **Contradito** pelo código atual (a DDL tem a coluna) |
| `interface/queue_writer.py`: `queue.Queue` em memória, sem tratamento de sinal | Leitura: `queue.Queue()` (linhas 45 e 145); a única menção a "signal" é o sentinel `None`; sem `signal`/`atexit` | Confirmado por leitura, **não reproduzido** (hipótese) |
| `core/parser_factory.py`: só Python e TS/JS | `get_parser_for_file` retorna `None` (linha 66); extensões só `.py` e `.ts/.tsx/.js/.jsx` | Confirmado por leitura (limitação de cobertura) |
| `core/gating_interceptor.py`: `VALID_MODES` | `{"plan-only","ask","auto-approve"}` (linha 46). `01_ARCHITECTURE.md:456-457` e `02_MCP_TOOLS_REFERENCE.md:368` ainda documentam `auto_read`/`autonomous` | **Confirmado**: divergência documentação × código (registrada em `fora-de-escopo.md`) |
| `core/hsm_engine.py`: `ERROR` não existe | `ERROR_PAUSE`, `AWAITING_HUMAN`, `CONTEXT_FULL` existem (linhas 183-185); não há estado `ERROR` | Confirmado por leitura |
| `interface/mcp_server.py`: `concierge_feedback` classificado como `READ_ONLY` | `core/mcp_governor.py:116` classifica como `LOCAL_MUTATION` | **Contradito** pelo código atual |

Resumo: **1 reproduzido e resolvido como BL-088**, **1 divergência documental confirmada** (gating, movida para `fora-de-escopo.md`), **2 confirmados por leitura**, **1 hipótese não reproduzida** e **2 afirmações do protocolo contraditas** pelo código atual (corrigidas com notas explicativas pós-auditoria no protocolo).

> [!NOTE]
> A falha de atomicidade em `apply_alias_migration` foi formalizada em `audits/core-alias-tracker.md` e integrada ao backlog como BL-088 (Média).

## 6. Decisões para você

1. **Corrigir v1?** Reorganizar a Seção 3/4 para remover a lacuna das faixas e o "sétimo agrupamento" (só texto, sem mexer em BL).
2. **Dashboard (`grafo-dashboard-web/`):** Decidir se o diretório do frontend web entra no repositório versionado ou permanece excluído via `.gitignore`.
3. **Manter o v2** como índice mecânico auxiliar, ou removê-lo.
