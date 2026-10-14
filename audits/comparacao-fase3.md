# Comparação: Fase 3 refeita (v2) × Fase 3 consolidada (v1)

> **v1** = [`backlog-final.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md) (intacto).
> **v2** = [`backlog-final-v2.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final-v2.md), gerado só a partir dos 15 relatórios da Fase 1.
> **Scripts:** `scratch/fase3_redo_inventory.py`, `fase3_redo_build_v2.py`, `fase3_redo_compare.py`, `fase3_redo_repro_alias.py`.
> Este documento é uma **comparação**, não um novo relatório de achados.

## 1. Veredito

O inventário de **achados** do v1 está correto e completo. Refeito do zero, o v2 reproduz **87 itens** com as mesmas severidades e as mesmas fontes. As diferenças reais estão na **organização** do v1 (trilhas e fluxograma) e em **6 itens da Fase 1 que nunca viraram relatório** e por isso ficaram fora dos dois backlogs.

## 2. Onde v1 e v2 coincidem

| Verificação | Resultado |
|---|---|
| Linhas de achado nos 15 relatórios | 91 |
| Excluídas (2 falsos positivos + 2 duplicatas entre relatórios) | 4 |
| Esperado no backlog refeito | 87 (86 achados + 1 observação) |
| Achados esperados ausentes do v1 | **0** |
| BL do v1 que citam achado inexistente, falso positivo ou duplicata | **0** |
| Achado citado por mais de um BL | **0** |
| Divergências de severidade (fonte × BL) | **0** |
| Links `arquivo#Lnn` do v1 verificados contra o código atual | 128, **0 problemas** |

Totais por severidade:

| Severidade | v1 | v2 |
|---|:-:|:-:|
| Máxima | 3 | 3 |
| Crítica | 21 | 21 |
| Grave | 30 | 30 |
| Média | 28 | 28 |
| Baixa | 5 | 4 + 1 observação |
| **Total** | **87** | **87** |

A única diferença é de rótulo. A observação `core-delta-manager.md` #5 (BL-061) está como **Baixa** no v1 e como **Observação** no v2. O v1 já assume essa classificação em 86+1.

## 3. Diferenças encontradas no v1 (organização, não conteúdo)

1. **Faixas do fluxograma (Seção 3) não cobrem 22 itens.** BL-017 a 020, 022 a 024 e 037 a 051 não estão em nenhuma faixa. Os BL-017 a 024 estão na Seção 4 dentro de TRACK 2 e TRACK 4, e BL-037 a 051 estão em "Componentes de Suporte do Core".
2. **Existe um sétimo agrupamento não declarado.** O título diz "6 Tracks", mas há "Componentes de Suporte do Core (Checkpointer, Janitor, Governor)" com 16 itens, sem posição no fluxograma de dependências.
3. **Ordem de leitura quebrada.** BL-019 está no fim do arquivo (após BL-051), dentro de "Componentes de Suporte", mas é achado de `storage.md` (schema de checkpoints). BL-017/018/020/021 também aparecem fora da sequência numérica.
4. **Distribuição desigual.** TRACK 4 tem 22 itens e TRACK 1 tem 5. Isso pesa no planejamento, mas não é erro.

Nenhum desses pontos altera achados ou severidades. A correção seria só reorganizar ou corrigir as faixas, e isso fica para decisão sua.

## 4. Decisões de modelagem no v2

- **Trilhas por relatório de origem.** Mais simples de auditar, mas não segue dependência técnica. O v1 é melhor como roteiro de execução (por exemplo, o aviso de corrigir BL-033 e BL-034 juntos).
- **Perde-se no v2:** diretrizes de remediação, critérios de validação e dependências. O v2 é um índice rastreável, não um substituto do v1.
- **Ganha-se no v2:** nenhuma trilha fica fora do fluxo, e a rastreabilidade sai de um parser, não de edição manual.

## 5. Itens da Fase 1 sem relatório em `audits/` (lacuna dos dois backlogs)

O [AUDIT_PROTOCOL.md](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md) marca como `[x]` seis itens auditados "manualmente nesta conversa" e nunca registrados. O que verifiquei **agora**, no código atual:

| Item do protocolo | Verificação | Resultado |
|---|---|---|
| `core/alias_tracker.py`: `apply_alias_migration` não atômico | `scratch/fase3_redo_repro_alias.py` com o `ConciergeDatabaseManager` real: o 3º UPDATE falha com `no such column: parent_node_id`, mas `files` e `nodes` já ficaram migrados e commitados | **Reproduzido** |
| `core/alias_tracker.py`: referência a `task_id` inexistente em `fsm_checkpoints` | `storage/relational_db.py:14` define `task_id TEXT` na DDL | **Contradito** pelo código atual (a DDL tem a coluna) |
| `interface/queue_writer.py`: `queue.Queue` em memória, sem tratamento de sinal | Leitura: `queue.Queue()` (linhas 45 e 145); a única menção a "signal" é o sentinel `None`; sem `signal`/`atexit` | Confirmado por leitura, **não reproduzido** (hipótese) |
| `core/parser_factory.py`: só Python e TS/JS | `get_parser_for_file` retorna `None` (linha 66); extensões só `.py` e `.ts/.tsx/.js/.jsx` | Confirmado por leitura (limitação de cobertura) |
| `core/gating_interceptor.py`: `VALID_MODES` | `{"plan-only","ask","auto-approve"}` (linha 46). `01_ARCHITECTURE.md:456-457` e `02_MCP_TOOLS_REFERENCE.md:368` ainda documentam `auto_read`/`autonomous` | **Confirmado**: divergência documentação × código |
| `core/hsm_engine.py`: `ERROR` não existe | `ERROR_PAUSE`, `AWAITING_HUMAN`, `CONTEXT_FULL` existem (linhas 183-185); não há estado `ERROR` | Confirmado por leitura |
| `interface/mcp_server.py`: `concierge_feedback` classificado como `READ_ONLY` | `core/mcp_governor.py:116` classifica como `LOCAL_MUTATION` | **Contradito** pelo código atual |

Resumo: **1 reproduzido**, **1 divergência documental confirmada** (gating), **2 confirmados por leitura**, **1 hipótese não reproduzida** e **2 afirmações do protocolo contraditas** pelo código atual. Os dois contraditos precisam de decisão sua: o protocolo pode estar desatualizado, ou o código mudou depois da auditoria manual.

> [!NOTE]
> A `apply_alias_migration` (não atômica) é o único item novo com reprodução executada. Se quiser que entre no backlog, precisa de BL próprio e de relatório em `audits/` (Regras 2 e 6). Não alterei numeração, totais nem o v1.

## 6. Decisões para você

1. **Corrigir v1?** Reorganizar a Seção 3/4 para remover a lacuna das faixas e o "sétimo agrupamento" (só texto, sem mexer em BL).
2. **Alias tracker:** abrir relatório e BL novo, ou manter só como observação.
3. **Os 2 itens contraditos e o desvio de documentação do gating:** corrigir o protocolo, ou registrar em `fora-de-escopo.md`.
4. **Manter o v2** como índice mecânico auxiliar, ou removê-lo.
