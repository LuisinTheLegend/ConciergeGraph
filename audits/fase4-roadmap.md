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
| 4.1/G | `4c505d1`, `4a55d6e`, `933f62a` | Resíduo F4-009 + investigação de nodes.summary (somente leitura) | Concluída | Sim (2026-10-21; trechos não literais corrigidos na 4.1/H) |
| 4.1/H | `933f62a`, `17abc47`, `4a9893a`, `cbdcb9d` | Migração dos sumários [DUMB] para NULL (Opção B); backup SQLite; FTS íntegro | Concluída | Sim (2026-10-21; erros menores de relato: mensagem de commit, número 977 sem prova, PID 15544 sem arquivo, atribuição errada a F4-009) |
| 4.2 | `8640165`, `0244183` | Desacoplar `mcp_governor` de `telemetry_api`; cortar `interface/__init__`→`ActionHooks`→`RevisorCritico` | Concluída | Sim (2026-10-22; T4 frágil e fim de linha de interface/__init__.py, corrigidos/tratados na 4.2b) |
| 4.2b | `28dd2a7`, `b38a510`, `5f6a9c6` | Limite de versão do `mcp` (F4-013), prova de instalação limpa e correção do T4 | Concluída | Sim (2026-10-24) |
| 4.2c | `64e0d65` | Medição do tempo de inicialização (profile de bootstrap, imports e cliente MCP real) | Concluída | — |
| 4.2d | `34ad6d5`, `8366860` | Import tardio de sentence_transformers/torch (F4-015); bootstrap reduzido para 2,77s | Concluída | — |
| 4.2e | — | Diagnóstico do travamento na 1ª carga do modelo via MCP (OpenBLAS/CRT hang) | Concluída (diagnóstico) | — |
| 4.2e-2 | — | Isolamento mecânico: deadlock CRT em `ReadFile` no fd 0 durante `LoadLibraryExW` | Concluída (diagnóstico) | — |
| 4.2e-3 | — | Comparação de opções de solução (Opção A desacoplamento fd 0 vs Opção B pré-import) | Concluída (diagnóstico) | — |
| 4.2f | `17f046e`, `a64f5f1` | Correção F4-017: Opção A (desacoplamento de fd 0 no Windows); E2E 1.27.0 OK (1.30.0 rodou sem chromadb, ver `errata-4-2f.md`) | Concluída (com errata na 4.2g) | Sim (4 lacunas apontadas para 4.2g) |
| 4.2g | `6defadc`, `5b173fd`, `30d65c1`, `96ba4d0` | Fechamento das 4 lacunas da 4.2f: remoção D5 frágil + skip explícito D1; docstring separando PROVADO/HIPÓTESE (AST idêntico); E2E `mcp 1.30.0` completo (10/10 OK, 13 vetores) + controle `dd92d35` (6/6 TRAVOU); CI Windows (`.github/workflows/windows-stdin.yml`) | Concluída (ver `audits/errata-4-2g.md`) | Sim (2026-11-01; F4-015/F4-017 aceitos pelo dono no Claude Desktop real, n=1) |
| 4.2h | `e395ee7`, `498f995`, `6b3202b`, `9ed18b3`, `c5e1c2c` | Segurança do adaptador de LLM (F4-019 egress/fallback, F4-020 fechamento de clientes AsyncOpenAI/OpenAI, F4-021 redação de evidências versionadas, filtro em `setup_logging`, scanner `scan_secrets.py` e Regra 13); E2E Tripwire Proxy | Concluída (com errata na 4.2h-2) | Sim (F4-019 e F4-020 verificados; F4-022 e F4-023 apontados para 4.2h-2) |
| 4.2h-2 | `1ce99de`, `215fafa`, `77eec6f`, `cb64576` | Fechamento das pendências da 4.2h: lookbehind negativo no filtro e scanner + paridade + E2E MCP com nomes `sk-` (F4-022); `# GRAFO_LLM_PROVIDER=gemini` comentado no `.env.example` (F4-023); preservação de handlers alheios em `setup_logging`, docstring/teste R6 de `exc.args`, `importorskip("chromadb")`; `audits/errata-4-2h.md` | Concluída | — |
| 4.2i | `4263178` (B0), `023c81d` (B1) | Bloco 0 (F4-025): openai em dev/all, is_safe_path cross-platform, BL-015 strict xfail; Bloco 1 (F4-018/F4-024): nodes_fts 4 colunas (content), BM25 weights, fallback OR multi-palavra, migração com backup | Concluída | — |
| 4.2j | `b360bb9` (I1), `4313351` (I2), `ca110d4` (I3/4/5) | Item 1 (F4-026): migração atômica FTS e consistência na inicialização; Item 2 (F4-027): remoção de filtro AND/OR/NOT/NEAR no builder FTS; Item 3: errata-4-2i; Item 4: prova de mutação F4-017 e scipy; Item 5: medições SQLite e ambiente | Em verificação independente | — |
| 4.2k | `a902e78`, `3f63805` | Correção documental da errata-4-2i (citações verbatim com arquivo:linha, separação chat vs arquivo versionado, diffs reais, rastreabilidade e causa do skip Qdrant); Regra 14 no AUDIT_PROTOCOL.md | Concluída | — |
| 4.2l | `1c81fdc` | Ajustes documentais finais da errata-4-2i sob Regra 14: retificação de frases sem comprovação ("origem não determinada"), resíduo de relatorio_4_2j.md:65, comprovação da inexistência de test_is_safe_path_security e atualização da tabela de rastreabilidade | Concluída | — |
| 4.3 | `f17cc7d` (B0), `d63b638` (B1), `f25d319` (B2), `ad39881` (B3) | Bloco 0 (documental: F4-018, errata §§13-14, relatorio_4_2k UTF-8 puro); Bloco 1 (schema oficial DDL `agent_checkpoints`, índice, `verify_tables_exist`, `last_error`, ordenação determinística); Bloco 2 (reimplementação de call chain sobre `edges`/`nodes` canônicos, Opção A escopo estrito de projeto, proteção de ciclo, relation_type='calls', 1..10 profundidade); Bloco 3 (remoção de `test_log` de `core/database.py` e isolamento em teste) | Concluída pelo executor, com correções na 4.3b | — |
| 4.3b | `019eee8` (C1), `fb40d69` (C2) | Correção da 4.3: 6 testes legados de call chain reescritos para schema canônico; eliminação de colisões LIKE em call chain; exclusão do arquivo de origem na busca por símbolo; rejeição de depth_limit bool; tratamento de folder_name ambíguo com contagem anônima; eliminação de last_error compartilhado em AgnosticCheckpointer com save_checkpoint_detailed; errata-4-3 sob Regra 14; suíte completa 445 passed, 1 xfailed (BL-015) | Concluída pelo executor, aguardando verificação independente | — |
| 4.3c | `be88e2b` (C1), `235b668` (C2), `c4cd822` (C3), `821113a` (C4) | Micro-rodada de correção da 4.3b (somente documentos e testes): teste do 2f com mineração real e ordem de varredura robusta (M6); teste E2E com monkeypatch isolado e chamada FastMCP registrada; 2 testes determinísticos para vars() e poison last_error (M7a, M7b); rastreamento de scripts em scratch/ (C2); errata-4-3b sob Regra 14; investigação de travamento (0/10); suíte completa 448 passed, 1 xfailed (BL-015) | Concluída pelo executor, aguardando verificação independente | — |
| 4.4 | — | Remover `wing_keywords` de vez, com teste-guarda e regra de neutralidade no protocolo/CONTRIBUTING | PLANEJADO, NÃO AUTORIZADO | — |
| 4.5 | — | Quarentena do código dormente em `archive/v4-experimental` (após 4.2) | PLANEJADO, NÃO AUTORIZADO | — |

> **Nota de Encerramento:** A Fase 4.1 encerra na Rodada 4.1/H. A criação das tabelas faltantes (`agent_checkpoints` via Caminho B) está planejada para a Rodada 4.3.

## 4. Achados da Fase 4 (índice; detalhe em `fase4-achados.md`)

| ID | Resumo | Severidade | Status | Evidência |
|---|---|---|---|---|
| F4-002…F4-005 | Achados de alcance/estrutura da 4.0b/4.0c | ver arquivo | Abertos (F4-003: avaliar rebaixar, é dormente) | `fase4-achados.md` |
| F4-001 | Omissão de escritores para ast_edges (call chain reimplementada sobre edges/nodes canônicos na 4.3/4.3b) | CRÍTICA | corrigido pelo executor, aguardando verificação independente | `core/graph_rag.py`, `tests/test_call_chain_edges_nodes.py` |
| F4-007 | Omissão de DDL para agent_checkpoints (adicionado ao schema oficial na 4.3, isolamento thread-safe na 4.3b) | CRÍTICA | corrigido pelo executor, aguardando verificação independente | `storage/schema.py`, `core/checkpointer.py`, `tests/test_agent_checkpoints_schema.py` |
| F4-006 | Formato de log abortava a mineração antes dos embeddings (RichHandler) | CRÍTICA | CORRIGIDO | `f98aaea`, `f07cb65`; E2E com modelo real |
| F4-008 | Hash gravado antes de embeddings/vetores; vetores ausentes nunca refeitos | CRÍTICA | CORRIGIDO | `de90005`, reparo reproduzido; red→green reproduzido na 4.1/E |
| F4-009 | Sem caminho de reindexação (texto precisa mencionar o `_sync_vectors` do Janitor, inativo por padrão) | GRAVE | CORRIGIDO (texto ajustado na 4.1/G) | `de90005` |
| F4-010 | Sumários L0 gerados e descartados | GRAVE | CORRIGIDO | `8e6f887` |
| F4-011 | Filtro `node_type` no Chroma excluía vetores sem a chave | GRAVE | CORRIGIDO | `8d963ae`; teste (i) vermelho em `af9001a`, verde em HEAD (reproduzido) |
| F4-012 | `[DUMB]` persistido quando não há LLM | A confirmar (observação) | CORRIGIDO: [DUMB] omitido (`8d963ae`), teste efetivo (`9b70eef`) | ver §5 |
| F4-013 | Incompatibilidade com `mcp>=2.0` por ausência de teto de versão | CRÍTICA | CORRIGIDO (verificado pelo auditor; commits 28dd2a7, b38a510, 5f6a9c6) | `pyproject.toml:39`, `requirements.txt:5`; `tests/test_dependency_pins.py`, provas em `scratch/evidencia_4_2b/` |
| F4-014 | Tree-sitter e parsers de linguagem ausentes em dependências (degradação silenciosa de AST) | MÉDIA | ABERTO | `ingestion/parser.py:180-245`; prova em `scratch/evidencia_4_2b/p6_tree_sitter_probe.txt` |
| F4-015 | Latência excessiva de inicialização por imports antecipados de ML (`torch`/`sentence_transformers`) no bootstrap | MÉDIA | corrigido; verificado pelo auditor; aceito pelo dono no Claude Desktop real (n=1, uma máquina) em 2026-11-01 | `storage/vector_store.py:45-56, 151-177`; testes `tests/test_lazy_ml_imports.py`; provas em `scratch/evidencia_4_2d/` e `4_2f/` |
| F4-017 | 1ª chamada que usa o modelo trava dentro do servidor MCP no Windows (leitor bloqueado em fd 0) | CRÍTICA | corrigido; verificado pelo auditor; aceito pelo dono no Claude Desktop real (n=1, uma máquina) em 2026-11-01 | `main.py:111-146`, `tests/test_stdin_decouple.py`, `.github/workflows/windows-stdin.yml`; provas em `scratch/evidencia_4_2f/` e `scratch/evidencia_4_2g/` |
| F4-018 | FTS (`nodes_fts`) não indexava `nodes.content` (apenas `label, tags, summary`) | GRAVE | corrigido pelo executor, aguardando verificação independente | `storage/schema.py`, `storage/store.py`, `storage/logic.py`, `tests/test_fts_code_search.py`, `scratch/evidencia_4_2i/` |
| F4-019 | Com `GRAFO_LLM_MODEL=none` o LLM não era desligado e enviava chave à OpenAI; fallback Gemini->OpenAI entre provedores | CRÍTICA | corrigido; verificado pelo auditor (reprodução independente dos testes S1-S7 e das mutações em Linux; E2E por tripwire apenas por evidência do executor) | `ingestion/summarizer.py`, `ingestion/orchestrator.py`, `main.py`, `interface/cli.py`, `tests/test_llm_egress_guard.py`, `scratch/evidencia_4_2h/` |
| F4-020 | `AsyncOpenAI`/`OpenAI` criados por chamada e nunca fechados (`Event loop is closed / Task exception was never retrieved`) | MÉDIA | corrigido; verificado pelo auditor (reprodução independente dos testes S1-S7 e das mutações em Linux; E2E por tripwire apenas por evidência do executor) | `ingestion/summarizer.py`, `tests/test_llm_egress_guard.py` (S6/S7), `audits/errata-4-2h.md` |
| F4-021 | Trechos de chave mascarada pelo provedor em arquivos de evidência versionados e ausência de filtro de segredos em logs | MÉDIA | corrigido pelo executor, aguardando verificação independente | `scratch/tools/scan_secrets.py`, `main.py`, `AUDIT_PROTOCOL.md` (Regra 13), `tests/test_no_secrets_in_tracked_files.py`, `tests/test_secret_redaction.py`, `scratch/evidencia_4_2h/`, `scratch/evidencia_4_2h2/` |
| F4-022 | Padrão `sk-[\w*-]{6,}` sem lookbehind negativo corrompia nomes de arquivos e textos normais com `sk-` interno | MÉDIA | corrigido pelo executor, aguardando verificação independente | `main.py`, `scratch/tools/scan_secrets.py`, `tests/test_secret_redaction.py`, `scratch/evidencia_4_2h2/item1_e_mcp_filenames.txt` |
| F4-023 | `.env.example` trazia `GRAFO_LLM_PROVIDER=gemini` ativo por padrão | BAIXA | corrigido pelo executor, aguardando verificação independente | `.env.example`, `tests/test_env_example_provider.py`, `scratch/evidencia_4_2h2/` |
| F4-024 | Fragilidade sintática e ausência de fallback multi-palavra em buscas lexicais FTS5 | MÉDIA | corrigido pelo executor, aguardando verificação independente | `storage/logic.py`, `tests/test_fts_code_search.py`, `scratch/evidencia_4_2i/` |
| F4-025 | CI vermelho em ambiente limpo (openai ausente em dev/all, is_safe_path cross-platform, BL-015 sem xfail estrito) | MÉDIA | corrigido pelo executor, aguardando verificação independente | `pyproject.toml`, `core/security_guard.py`, `tests/test_adaptive_gating.py`, `tests/test_progressive_tool_disclosure.py`, `scratch/evidencia_4_2i/` |
| F4-026 | Migração FTS não-atômica deixava índice vazio após queda; verificação de consistência na inicialização | MÉDIA | corrigido pelo executor, aguardando verificação independente | `storage/schema.py`, `tests/test_fts_atomic_migration.py`, `scratch/evidencia_4_2j/` |
| F4-027 | Filtro de AND/OR/NOT/NEAR no builder FTS impedia buscas com termos literais legítimos | BAIXA | corrigido pelo executor, aguardando verificação independente | `storage/logic.py`, `tests/test_fts_code_search.py`, `scratch/evidencia_4_2j/` |
| BL-006 | Checkpoints salvos fora da fila serializada SerializedWriteQueue (risco de lock sob concorrência) | MÉDIA | ABERTO (registrado na 4.3) | `core/checkpointer.py:113-114, 139-140, 206-209`, `interface/mcp_server.py:164-166`, `audits/fase4-achados.md` |
| F4-028 | Ordem não-determinística de varredura no ProjectCrawler.crawl afeta resolução de símbolos repetidos | MÉDIA | ABERTO (registrado na 4.3c) | `ingestion/crawler.py:501`, `ingestion/orchestrator.py:768`, `audits/fase4-achados.md` |
| F4-029 | Bloqueio indefinido em queue_writer.py:147 (response_queue.get()) em testes de concorrência | CRÍTICA | ABERTO (reproduzido na 4.4, correção de produto alocada para 4.4b) | `interface/queue_writer.py:147`, `tests/test_graph_rag_janitor.py:84`, `audits/fase4-achados.md` |


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

- Trechos de evidência não literais (4.1/D e 4.1/G).
- Saída de teste vermelho que não corresponde aos testes commitados.
- Achado novo com causa errada e status "CORRIGIDO" sem prova (F4-011 original).
- **Teste que passa antes e depois da correção** (4.1/E, `[DUMB]`). Todo teste novo precisa falhar no código anterior.
- Afirmações absolutas sem checar tudo ("não existe caminho de reindexação", "100% viável", "29 de 31").
- Do lado do auditor: aceitar uma afirmação sem olhar o Janitor; verificar versão de biblioteca só no próprio sandbox.
