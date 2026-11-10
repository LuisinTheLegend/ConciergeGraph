# Catálogo de Achados Empíricos — Fase 4, Rodada 4.1/B

> **Status:** Ativo e Auditado  
> **Natureza:** Achados de Engenharia e Inconsistências de Código Descobertos Durante a Prova de Execução (Fora do Backlog Congelado de 88 Itens)  
> **Base Normativa:** Regras 2, 3, 4, 7, 10 e 11 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Hash de Referência:** `aacca16d168886b88b54c3a7a1f070adc8a20b38`  

---

## 1. Visão Geral dos Novos Achados

Durante as rodadas de execução empírica e revisão técnica da Fase 4 (Rodadas 4.0b, 4.0c e 4.1/B), foram identificadas inconsistências funcionais, omissões de código e contratos fantasmas que **não faziam parte do catálogo histórico congelado de 88 itens (BL-001 a BL-088)**.

Em cumprimento à **Regra 2** ("NUNCA reporte um achado sem: (a) arquivo e linha exatos, (b) mecanismo técnico explicado, (c) reprodução real executada") e à **Regra 3** ("Se não conseguir reproduzir, classifique como HIPÓTESE NÃO CONFIRMADA"), todos os achados abaixo foram rigorosamente comprovados via scripts de execução em tempo real.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 NOVOS ACHADOS DE AUDITORIA (RODADA 4.1/B)                   │
│                                                                             │
│  🔴   F4-001: Ausência de Escritor em Produção para `ast_edges`             │
│  🟠   F4-002: Ausência de Escritor em Produção para `communities`           │
│  🟠   F4-003: Watcher Consulta Coluna Fantasma `structural_hash` em `files` │
│  🟡   F4-004: Violação de Neutralidade por Taxonomia Hardcoded em `config`   │
│  🟡   F4-005: `concierge_feedback` Retorna Falso Sucesso para IDs Inertes    │
│  🔴   F4-006: Crash de Formatação de Log em `orchestrator.py:222` (Corrigido)│
│  🔴   F4-007: Ausência de DDL para `agent_checkpoints` Rompe Ferramentas     │
│  🔴   F4-008: Fragilidade: Hash Gravado Antes de Embeddings (Decisão Humana) │
│  🟠   F4-009: Reparo Parcial Inativo no Janitor e Sem Reindexação na Ingestão│
│  🟠   F4-010: Descarte Silencioso de Sumários L0 e Gravação de NULL em Nós  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento dos Achados Confirmados

### [F4-001] Omissão Estrutural de Escritores para a Tabela `ast_edges` em Produção
- **Severidade Proposta:** 🔴 CRÍTICA
- **Arquivos & Linhas:** [`core/graph_rag.py:84, 94, 179, 210, 219`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L84), [`core/alias_tracker.py:228, 232`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L228), [`ingestion/orchestrator.py:644–720`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L644)
- **Mecanismo da Falha:** A ferramenta `concierge_get_call_chain` e os métodos `retrieve_multihop_context` e `detect_logical_communities` realizam consultas SQL diretas (`SELECT`) sobre a tabela `ast_edges`. Todavia, em todo o código-fonte de produção de `core/`, `ingestion/`, `services/`, `storage/` e `interface/`, **NÃO EXISTE UMA ÚNICA INSTRUÇÃO `INSERT INTO ast_edges`**. As únicas escritas em `ast_edges` no repositório inteiro residem em mocks artesanais dentro de `tests/`. Mesmo se a tabela `ast_edges` for criada no DDL de bootstrap (conforme proposto em BL-001), ela permanecerá eternamente vazia porque o pipeline de ingestão (`orchestrator.py`) grava arestas de AST exclusivamente na tabela `edges` com colunas inteiras (`source_id`, `target_id`).
- **Reprodução Executada:**
  Comando rodado:
  ```powershell
  git grep -n "INSERT INTO ast_edges" -- ":!tests" ":!scratch" ":!audits"
  ```
  Saída literal: Vazia (zero resultados em produção).
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Reimplementação de `concierge_get_call_chain` sobre tabelas canônicas `edges` e `nodes` na Rodada 4.3/4.3b)

---

### [F4-002] Omissão Estrutural de Escritores para a Tabela `communities` em Produção
- **Severidade Proposta:** 🟠 GRAVE
- **Arquivos & Linhas:** [`core/background_janitor.py:157`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L157), [`services/janitor.py:506–557`](file:///c:/Nexus-Memory/GrafoConcierge/services/janitor.py#L506)
- **Mecanismo da Falha:** A especificação original previa que as comunidades semânticas do repositório fossem materializadas na tabela relacional `communities`. O módulo dormente `core/background_janitor.py` lê essa tabela (`SELECT community_id, summary FROM communities;`). Contudo, o módulo de produção ativo (`services/janitor.py`) calcula comunidades sob demanda via CTE recursivo sobre `edges` e mantém agrupamentos em memória temporária de processo, jamais gravando na tabela física `communities`. A tabela não possui escritor de produção ativo.
- **Reprodução Executada:**
  Comando rodado:
  ```powershell
  git grep -n "INSERT INTO communities" -- ":!tests" ":!scratch" ":!audits"
  ```
  Saída literal: Vazia (zero inserções de comunidades em código de produção).
- **Status:** **CONFIRMADO**

---

### [F4-003] Watcher Consulta Coluna Inexistente `structural_hash` na Tabela `files`
- **Severidade Proposta:** 🟠 GRAVE
- **Arquivos & Linhas:** [`interface/watcher.py:86, 208`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L86)
- **Mecanismo da Falha:** O componente `interface/watcher.py` tenta hidratar o cache de hashes de arquivos no disco executando `SELECT path, structural_hash FROM files;` (linha 86) e `SELECT structural_hash FROM files WHERE path = ? LIMIT 1;` (linha 208). Contudo, nenhuma instrução DDL ou DML em todo o projeto cria ou grava a coluna `structural_hash`. No módulo `core/delta_manager.py:204`, a coluna de hash estrutural é denominada `ssh_hash`. Caso a tabela `files` seja criada sem essa coluna específica, qualquer tentativa de ativação do watcher lançará `sqlite3.OperationalError: no such column: structural_hash`.
- **Reprodução Executada:**
  Comando rodado:
  ```powershell
  python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('CREATE TABLE files (path TEXT, file_hash TEXT);'); conn.execute('SELECT path, structural_hash FROM files;')"
  ```
  Saída literal: `sqlite3.OperationalError: no such column: structural_hash`.
- **Status:** **CONFIRMADO**

---

### [F4-004] Violação de Neutralidade de Domínio por Dicionário Fixo Hardcoded em `core/config.py`
- **Severidade Proposta:** 🟡 MÉDIA
- **Arquivos & Linhas:** [`core/config.py:77–99`](file:///c:/Nexus-Memory/GrafoConcierge/core/config.py#L77), [`core/project_index.py:18, 91`](file:///c:/Nexus-Memory/GrafoConcierge/core/project_index.py#L18)
- **Mecanismo da Falha:** O arquivo de configuração central do motor genérico embute estaticamente uma taxonomia fixa com 5 domínios específicos de negócio (`marketing/vendas`, `finanças/quant`, `gestão/saas`, `automação/rh`, `estatística`) e listas de palavras-chave em português ("tráfego", "bolsa", "daytrade", "rh", "planilha"). O motor perde a neutralidade de domínio para monorepos de outras áreas (ex: compiladores, bioinformática, IoT, jogos), classificando-os arbitrariamente no fallback `"geral"` ou forçando categorizações espúrias.
- **Reprodução Executada:**
  Invocação de `ProjectIndex.categorize_project(labels=['marketing_campaign.py'])` com `wing_keywords={}`:
  O sistema opera de forma 100% resiliente retornando `default_wing="geral"` e suporta alas customizadas passadas pelo usuário sem depender da taxonomia embutida.
- **Status:** **CONFIRMADO**

---

### [F4-005] Falsa Confirmação de Sucesso em `concierge_feedback` para `fact_id` Inexistente
- **Severidade Proposta:** 🟡 MÉDIA
- **Arquivos & Linhas:** [`storage/semantic_logic.py:100–120`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py#L100), [`interface/mcp_server.py:530–545`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L530)
- **Mecanismo da Falha:** Ao invocar a ferramenta MCP `concierge_feedback(fact_id=99999, was_useful=True)` contra um banco onde o fato 99999 não existe, o servidor responde `{"success": true, "fact_id": 99999, "was_useful": true}`. A implementação subjacente em SQLite executa `UPDATE semantic_facts SET ... WHERE id = ?`. O SQLite aceita o comando sem erros, mas afeta 0 linhas (`rowcount == 0`). O código não valida se o registro realmente existia, emitindo uma falsa confirmação de sucesso para o cliente MCP.
- **Reprodução Executada:**
  Execução literal no Passo 1 da Rodada 4.0c:
  ```json
  {
    "duration_seconds": 0.001,
    "fact_id": 99999,
    "success": true,
    "was_useful": true
  }
  ```
- **Status:** **CONFIRMADO**

---

### [F4-006] Crash de Formatação de Log em `orchestrator.py:222` Causa Falso Aborto da Ingestão
- **Severidade:** 🔴 CRÍTICA (Elevada por Decisão do Usuário na Rodada 4.1/B)
- **Arquivos & Linhas:** [`ingestion/orchestrator.py:222`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L222)
- **Mecanismo da Falha Completo:**
  1. **Origem do RichHandler:** No processo real, o handler `rich.logging.RichHandler` é instalado no logger raiz pela biblioteca `mcp` durante o `main.bootstrap()`. Especificamente, `interface/mcp_server.py:177` instancia `FastMCP("Grafo Concierge")`. O construtor `FastMCP.__init__` em `mcp/server/fastmcp/server.py:242` chama `configure_logging(self.settings.log_level)`. Essa função, em `mcp/server/fastmcp/utilities/logging.py:32, 39`, executa `logging.basicConfig(level=level, format="%(message)s", handlers=[RichHandler(...)])` (versões de runtime: `mcp==1.27.0`, `rich==15.0.0`).
  2. **Por que StreamHandler engolia e RichHandler propaga:**
     - Em `logging.StreamHandler.emit` (`logging/__init__.py:1150–1159`), a formatação `msg = self.format(record)` é executada **dentro** de um bloco `try ... except Exception: self.handleError(record)`. O método `Handler.handleError` apenas escreve uma mensagem de aviso em `sys.stderr` sem relançar a exceção (`del exc`), permitindo que o processo continue executando.
     - Em `rich.logging.RichHandler.emit` (`rich/logging.py:140`), a instrução `message = self.format(record)` é chamada **desprotegida no topo do método**, fora do bloco `try/except` (que na classe `RichHandler` protege apenas o `self.console.print` na linha 185). Quando `self.format(record)` chama `record.getMessage()` e avalia `record.msg % record.args`, a ausência do especificador de formato lança:
       ```
       TypeError: not all arguments converted during string formatting
       ```
       Essa exceção não tratada escapa do `logger.info()` e aborta imediatamente o método chamador (`IngestionManager.mine`).
  3. **Varredura AST no Código de Produção:**
     O script `scratch/fase4_1_log_format_scan.py` varreu todos os 63 arquivos Python de produção (`core/`, `ingestion/`, `interface/`, `services/`, `storage/`, `agent/`, `agents/`, `main.py`). A chamada em `ingestion/orchestrator.py:222` foi o **único ponto** em todo o código de produção com argumentos sobressalentes sem especificador `%` correspondente.
  4. **Cadeia Completa Observada:**
     - 1ª mineração: O Passo 4 (`STORE SQLite`) persiste e confirma nós, arestas e `file_hash` no SQLite. Em seguida, o Passo 5 (`EMBED`) executa a linha 222, estourando `TypeError`. O servidor captura a exceção e retorna `{"success": false, "error": "not all arguments converted..."}`. Os passos 5 a 8 nunca são executados, e nenhum vetor é gravado no Chroma (`embeddings_stored: 0`).
     - 2ª mineração: O crawler roda novamente e encontra os hashes já gravados em `nodes`. Considera todos os arquivos inalterados e encerra com `{"success": true, "files_skipped": N, "files_processed": 0}`.
     - Consequência: O banco vetorial permanece com 0 embeddings indefinidamente (`count_embeddings = 0`) e qualquer busca híbrida subsequente retorna `vector_score: 0.0`.
- **Reprodução Executada:**
  Confirmado em teste de regressão `tests/test_ingestion_embed_regression.py::test_f4_006_mining_with_rich_handler_regression` e na prova e2e em worktree `153d1ff`.
- **Status:** **CORRIGIDO NA RODADA 4.1/B** (Commit `f98aaea`)

---

### [F4-007] Omissão Estrutural de DDL para `agent_checkpoints` Rompe 3 Ferramentas MCP
- **Severidade Proposta:** 🔴 CRÍTICA
- **Arquivos & Linhas:** [`storage/schema.py:51–144`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py#L51), [`core/checkpointer.py:65–110`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L65), [`interface/mcp_server.py:1731–1775`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1731)
- **Mecanismo da Falha:** O módulo `interface/mcp_server.py` expõe 3 ferramentas oficiais para checkpoints de agentes: `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`. Todas delegam para `core/checkpointer.py`, que executa queries SQL contra a tabela `agent_checkpoints`. Todavia, `agent_checkpoints` não existe no schema oficial de produção (`storage/schema.py`). Como resultado, qualquer chamada com parâmetros válidos falha com `sqlite3.OperationalError: no such table: agent_checkpoints`.
- **Reprodução Executada:**
  Matriz de ferramentas da 4.0c (Passo 1):
  ```
  agent_get_checkpoint  -> EXCEÇÃO (OperationalError: no such table: agent_checkpoints)
  agent_list_checkpoints -> EXCEÇÃO (OperationalError: no such table: agent_checkpoints)
  agent_save_checkpoint -> ERRO DE NEGÓCIO (captura exceção interna e retorna success: false)
  ```
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Adicionado DDL e validações no SchemaManager na Rodada 4.3, e isolamento thread-safe na 4.3b)

---

### [F4-008] Fragilidade Arquitetural: Gravação do `file_hash` em SQLite Precede a Geração de Embeddings e Vetores
- **Severidade:** 🔴 CRÍTICA (Homologada na Rodada 4.1/D)
- **Arquivos & Linhas:** [`ingestion/orchestrator.py:186–275`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L186), [`ingestion/crawler.py:559–576`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L559)
- **Mecanismo da Falha:** No pipeline de mineração (`IngestionManager.mine`), o Passo 4 (`STORE SQLite`) grava imediatamente os nós e o respectivo `file_hash` na tabela relacional `nodes`. Os passos 5 (`EMBED`) e 6 (`STORE Vector`) ocorrem subsequentemente. Como os IDs dos vetores no Chroma derivam estritamente do ID inteiro do SQLite (`doc_id = f"node_{node_id}"`), qualquer falha de download do modelo na 1ª execução, interrupção de rede, timeout ou falha parcial de lote resulta em:
  1. O retorno da mineração reportava falsamente `success: true` e `errors: []` devido ao fallback semântico silencioso (`[None] * len(texts)`).
  2. O banco relacional SQLite persiste os nós com `file_hash` preenchido.
  3. Em qualquer mineração subsequente, o crawler executa `existing_node = self._store.find_node_by_hash(project_uuid, file_hash)` e classifica os arquivos como `unchanged`, pulando-os permanentemente (`files_skipped: N`) e deixando o índice vetorial no Chroma com 0 vetores para sempre.
- **Reproduções Executadas (Rodadas 4.1/B e 4.1/C):**
  1. *Simulação com Erro Sintético:* Script `scratch/fase4_1_reproduce_fragility.py` com `RuntimeError` no passo 5.
  2. *Gatilho Real com Modelo Real Offline (`scratch/fase4_1c_offline_hf_probe.py`):* Servidor real iniciado via `main.bootstrap()` com `HF_HUB_OFFLINE=1` e cache HF vazio:
     - 1ª mineração: `success: true, files_processed: 2, nodes_created: 5, embeddings_stored: 0, errors: [], Chroma count: 0`.
     - 2ª mineração (rede/modelo restaurados): `success: true, files_processed: 0, files_skipped: 2, embeddings_stored: 0, errors: [], Chroma count: 0`.
  3. *Falha Parcial de Lotes (`scratch/fase4_1c_partial_batch_probe.py`):* Lote 1 gravado (2 vetores), lote 2 falha. A 2ª mineração pula todos os arquivos e congela o Chroma com apenas 2 vetores em vez de 6.
- **Resolução Arquitetural (Alternativa A + Relato Honesto):**
  Implementada a rotina unificada `repair_missing_vectors(project_uuid)` em `IngestionManager`. A rotina é executada:
  1. Antes do atalho de encerramento prematuro `noop` (quando não há novos arquivos nem exclusões), garantindo que arquivos inalterados com vetores ausentes sejam imediatamente reparados.
  2. Após o Passo 6 na mineração normal, reparando falhas parciais ocorridas durante a execução.
  Adicionalmente, `IngestionResult` passou a expor `embeddings_failed` e `embeddings_repaired`. Em caso de modelo indisponível durante o embedding (Semantic Fallback), o resultado registra explicitamente uma mensagem de erro descritiva.
- **Ajuste de Precisão (Rodada 4.1/E — Deduplicação de Telemetria):**
  A rodada 4.1/D contabilizava as mesmas falhas em dobro no cenário offline (ex.: 14 falhas para 7 chunks): o Passo 5 registrava `embeddings_failed += none_count` e o reparo imediato subsequente tentava re-gerar os mesmos 7 embeddings, falhava novamente e somava mais 7 ao mesmo contador. Corrigido em `ingestion/orchestrator.py` (Passo 5/6 do `mine`): um flag `step5_had_failures` suprime a chamada imediata a `repair_missing_vectors` no mesmo ciclo quando o Passo 5 acabou de registrar falhas por indisponibilidade de modelo, registrando em log `Skipping immediate vector repair in this cycle...`. O reparo continua disponível para o próximo ciclo (via atalho `noop`) e pelo Janitor.
- **Status:** **CORRIGIDO NA RODADA 4.1/D** (Commit `de90005d377fc7dc5ba137b9854576c64669ed42`) + **DEDUPLICADO NA RODADA 4.1/E** (Commit `8d963ae61c2e6b8fccbb2ed86d621c302fbac334`)

---

### [F4-009] Mecanismo de Reparo Parcial Inativo no Janitor e Omissão de Reindexação Forçada na Ingestão
- **Severidade:** 🟠 GRAVE (Homologada na Rodada 4.1/D)
- **Arquivos & Linhas:** [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py), [`services/janitor.py:346–392`](file:///c:/Nexus-Memory/GrafoConcierge/services/janitor.py#L346), [`interface/mcp_server.py:1690–1720`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1690)
- **Retificação do Achado (Caminho Parcial Pré-existente vs Inexistência na Ingestão):**
  - O Janitor (`services/janitor.py:346–392`, método `_sync_vectors`) **já era um caminho de reparo parcial** antes da Rodada 4.1/D, permitindo sincronizar nós do SQLite com o Chroma. Contudo, esse caminho permanecia **inativo por padrão** em produção, pois o Janitor só executa se a variável de ambiente `GRAFO_JANITOR_PROJECT` estiver explicitamente configurada (`main.py:66, 237–241`; sem ela, o bootstrap registra `janitor.is_running: False`). Além disso, operava de forma isolada e sem testes automatizados na suíte (0 ocorrências em `tests/`). Nota de precisão sobre metadados: o Janitor já gravava `project_uuid` corretamente; a única divergência real em relação à ingestão padrão residia no campo `node_type` (recebia `n.get("type")`, o tipo estrutural do chunk, em vez do `node_type` do nó).
  - No fluxo principal de ingestão (`ingestion/orchestrator.py`), não existia qualquer parâmetro de reindexação forçada, reconciliação ativa nem invalidação de cache de hashes para reprocessar arquivos já registrados em `nodes`. A afirmação inicial de inexistência absoluta de qualquer mecanismo de sincronização referia-se ao pipeline de mineração da ingestão, devendo ser contextualizada pela existência desse reparo parcial dormente no Janitor.
- **Resolução:**
  A lógica de reparo foi centralizada em `IngestionManager.repair_missing_vectors`, que opera em lotes via `embed_batch`. `JanitorService._sync_vectors` foi refatorado para delegar diretamente para essa rotina única, preservando a limpeza de nós órfãos sem duplicidade de código.
- **Status:** **CORRIGIDO NA RODADA 4.1/D** (Commit `de90005d377fc7dc5ba137b9854576c64669ed42`)

---

### [F4-010] Descarte Silencioso de Sumários L0 Gerados pelo LLM e Persistência como `NULL` em `nodes.summary`
- **Severidade:** 🟠 GRAVE (Homologada na Rodada 4.1/D)
- **Arquivos & Linhas:** [`ingestion/orchestrator.py:215–235, 595–625`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L215), [`interface/mcp_server.py:1158`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1158)
- **Mecanismo da Falha:** No pipeline de mineração (`IngestionManager.mine`):
  1. No Passo 3 (`_step_summarize`), o orquestrador invoca o LLM (Gemini/OpenAI), gera os sumários L0 para todos os `uncached_chunks`, registra a contagem em `result.summaries_generated` e retorna a lista de objetos `SummaryResult`.
  2. A lista retornada `summaries` **nunca era associada aos chunks nem repassada para o Passo 4 (`_step_store_sqlite`)**, sendo sumariamente descartada pelo coletor de lixo da memória.
  3. No Passo 4 (`_step_store_sqlite`), ao montar `nodes_to_create`, o código lê `summary_text = chunk.cached_summary`. Para qualquer nó novo (uncached), `chunk.cached_summary` permanecia estritamente `None`.
  4. O bulk insert inseria `summary = NULL` em todas as novas linhas da tabela `nodes`.
  5. Como consequência, na busca (`concierge_search`), a consulta ao SQLite lia `node.get("summary")` como `NULL`, retornando `"summary": null` mesmo quando o resultado da mineração reportou dezenas de sumários gerados.
- **Resolução:**
  Em `_step_summarize`, após obter cada `SummaryResult`, o orquestrador atribui diretamente `chunk.cached_summary = res.summary` e atualiza `chunk.detected_tags`. O bulk insert no SQLite persiste o sumário gerado.
- **Limitação Conhecida:**
  Não foi realizado backfill de bancos existentes nesta rodada. Nós já minerados em versões anteriores mantêm `summary = NULL` até que o arquivo seja editado e seu hash alterado.
- **Política do Placeholder `[DUMB]` (Definida na Rodada 4.1/E):**
  O `ZoomSummarizer` insere o prefixo `[DUMB]` nos sumários de truncamento gerados quando não há LLM configurado (marcados com `is_dumb_summary=True`). Decisão homologada: **esses placeholders NÃO devem ser persistidos**. A partir do Commit `8d963ae61c2e6b8fccbb2ed86d621c302fbac334`, `_step_summarize` só atribui `chunk.cached_summary` quando o resultado é um sumário genuíno de LLM (`is_dumb_summary=False`); em ambientes sem LLM, `nodes.summary` permanece `NULL` até que a integração com LLM esteja disponível. Teste-guarda: `test_dumb_summary_not_persisted_in_nodes_table` (`tests/test_summary_persistence.py:124`).
- **Status:** **CORRIGIDO NA RODADA 4.1/D** (Commit `8e6f887629ec7260a07311d0ca9b0f6c7edec55f`) + **POLÍTICA [DUMB] NA RODADA 4.1/E** (Commit `8d963ae61c2e6b8fccbb2ed86d621c302fbac334`)

---

### [F4-011] Dependência Indevida de Metadados do Chroma para Filtragem por `node_type` Rompe o Sinal Vetorial em Bases Legadas
- **Severidade:** 🟠 GRAVE (Homologada na Rodada 4.1/D)
- **Arquivos & Linhas:** [`core/hybrid_search.py:146–152, 186–200, 222–227`](file:///c:/Nexus-Memory/GrafoConcierge/core/hybrid_search.py#L146), [`storage/store.py:295–309`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L295), [`tests/test_ingestion_vector_repair.py:430–503`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_ingestion_vector_repair.py#L430)
- **Mecanismo da Falha:**
  Originalmente, a busca híbrida (`core/hybrid_search.py:148`) repassava `filters={"node_type": node_type}` diretamente para a consulta vetorial no Chroma (`self._vector.search`). Coleções vetoriais criadas por versões pré-existentes da ingestão ou restauradas sem a chave de metadados não continham `node_type` no dicionário de metadados do Chroma. Como o banco vetorial descarta sumariamente qualquer registro que não possua a chave pesquisada, toda busca com filtro de tipo perdia 100% dos candidatos vetoriais (`score_breakdown.vetorial = 0.0`), degradando a precisão da busca híbrida para apenas FTS5.
- **Resolução Arquitetural (Desacoplamento via SQLite e Compatibilidade Retroativa):**
  1. A dependência do metadado no Chroma foi eliminada no Passo 3 do `HybridSearchEngine`. A busca vetorial recupera uma margem ampliada (`top_k * 5`) sem filtrar por tipo no banco vetorial.
  2. A filtragem por `node_type` foi movida para o Passo 5 (Merge), consultando a fonte canônica da verdade na tabela relacional `nodes` via método em lote `SqliteStore.get_node_types_batch(all_node_ids)`.
  3. No Passo 8 (Pós-processamento), o `node_type` canônico vindo do SQLite é anexado a cada item do resultado final.
  4. Essa solução garante compatibilidade retroativa total com coleções existentes sem necessidade de migrações ou reindexação destrutiva.
- **Homologação (Rodada 4.1/E):** Compatibilidade retroativa comprovada pelo teste `test_scenario_i_backward_compatible_node_type_search_without_chroma_metadata` (`tests/test_ingestion_vector_repair.py:430`), que insere vetores no Chroma **sem** a chave `node_type` nos metadados (simulando base legada) e valida que a busca filtrada por `node_type="FACT"` retorna apenas o nó FACT com `score_breakdown.vetorial > 0.0` e com o `node_type` canônico anexado no pós-processamento.
- **Status:** **CORRIGIDO E HOMOLOGADO NA RODADA 4.1/D** (Implementação consolidada no Commit `8d963ae61c2e6b8fccbb2ed86d621c302fbac334`, Rodada 4.1/E)
---

### [F4-013] Incompatibilidade com `mcp>=2.0` por Ausência de Teto de Versão em `pyproject.toml` e `requirements.txt`
- **Severidade:** 🔴 CRÍTICA (Severidade Proposta: quebra imediata de novas instalações limpas)
- **Arquivos & Linhas:** [`pyproject.toml:39`](file:///c:/Nexus-Memory/GrafoConcierge/pyproject.toml#L39), [`requirements.txt:5`](file:///c:/Nexus-Memory/GrafoConcierge/requirements.txt#L5), [`interface/mcp_server.py:47`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L47)
- **Mecanismo da Falha:**
  `pyproject.toml:39` e `requirements.txt:5` declaram dependência `mcp>=1.0` (e `mcp>=1.0.0`) sem limite superior (`<2.0`). O ecossistema MCP lançou a versão `2.x` (versão 2.3.0 no PyPI em 2026-10-21). No `mcp 2.x`, o módulo `mcp.server.fastmcp` foi descontinuado e renomeado para `mcp.server.mcpserver` com alterações de API, e o arquivo `fastmcp.py` legado lança `ModuleNotFoundError` orientando a migração ou o pin `mcp<2`. Em qualquer clone limpo ou ambiente novo (`pip install -e .` ou `pip install -r requirements.txt`), o `pip` resolve a versão mais recente (`mcp 2.x`), colapsando o servidor no boot com `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`.
- **Reprodução Experimental:**
  Executado em venv temporário isolado fora do repositório (`scratch/evidencia_4_2/p0_mcp2_import_fail.txt`):
  `from mcp.server.fastmcp import FastMCP` lança:
  ```text
  ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import MCPServer) and other APIs changed; see the migration guide at https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver or pin 'mcp<2' to keep running v1 code.
  ```
- **Status:** **CORRIGIDO** (verificado pelo auditor; commits `28dd2a7`, `b38a510`, `5f6a9c6`)
- **Resolução (Rodada 4.2b, Commit `b38a510`):**
  1. `pyproject.toml:39` e `requirements.txt:5` foram atualizados para fixar o limite `mcp>=1.27,<2`.
  2. Implementado teste-guarda em [`tests/test_dependency_pins.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_dependency_pins.py) (Commit `28dd2a7`) que assegura que `Version("2.0.0")` é rejeitado e `Version("1.27.0")` é aceito (vermelho provado em `scratch/evidencia_4_2b/p3_test_pins_red.txt`, verde em `scratch/evidencia_4_2b/p3_test_pins_green.txt`).
  3. Criado script de validação real [`scratch/boot_check.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/boot_check.py) exercitando cliente MCP real via stdio (initialize, list_tools 31 ferramentas, call_tool `concierge_status`).
  4. Provas de boot bem-sucedidas com código 0 e 31 ferramentas realizadas em venvs limpos isolados:
     - Com `mcp==1.27.0`: `scratch/evidencia_4_2b/p4_boot_check_1_27.txt`
     - Com `mcp==1.30.0`: `scratch/evidencia_4_2b/p4_boot_check_1_30.txt`
     - Instalação limpa via `pip install <repo>` em `%TEMP%\inst_green` resolvendo `mcp 1.30.0` com código 0 tanto via `python main.py` (`scratch/evidencia_4_2b/p4_boot_check_green_main.txt`) quanto via console script `concierge-mcp` (`scratch/evidencia_4_2b/p4_boot_check_green_console.txt`).

---

### [F4-014] Ausência de Dependências do Tree-Sitter e Parsers de Linguagem Gerando Degradação Silenciosa de AST
- **Severidade:** 🟡 MÉDIA (Severidade Proposta: perda silenciosa de funcionalidade de parsing estruturado)
- **Arquivos & Linhas:** [`ingestion/parser.py:180-245`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L180-L245), [`ingestion/parser.py:376-384`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L376-L384), [`pyproject.toml:37-46`](file:///c:/Nexus-Memory/GrafoConcierge/pyproject.toml#L37-L46)
- **Mecanismo da Falha:**
  O módulo `ingestion/parser.py` tenta carregar `tree_sitter` e parsers específicos de linguagem (`tree_sitter_python`, `tree_sitter_javascript`, `tree_sitter_typescript`, `tree_sitter_go`, `tree_sitter_rust`). No entanto, nenhum desses pacotes está declarado em `dependencies` no `pyproject.toml` nem no `requirements.txt`. Em uma instalação limpa padrão (`pip install -e .`), nenhum módulo de tree-sitter está presente. Ao tentar processar arquivos dessas linguagens durante a mineração, o parser emite warnings silenciosos nos logs (`Error loading tree-sitter parser for <ext>: No module named 'tree_sitter'`) e degrada o parsing para expressões regulares básicas ou diretamente para `_parse_raw` (chunking de texto puro sem AST, sem extração semântica de chamadas nem relações de símbolos).
- **Reprodução Experimental:**
  Executado no ambiente de instalação limpa (`scratch/evidencia_4_2b/p6_tree_sitter_probe.txt`):
  ```text
  tree_sitter              : NOT INSTALLED (No module named 'tree_sitter')
  tree_sitter_python       : NOT INSTALLED (No module named 'tree_sitter_python')
  tree_sitter_javascript   : NOT INSTALLED (No module named 'tree_sitter_javascript')
  tree_sitter_typescript   : NOT INSTALLED (No module named 'tree_sitter_typescript')
  tree_sitter_go           : NOT INSTALLED (No module named 'tree_sitter_go')
  tree_sitter_rust         : NOT INSTALLED (No module named 'tree_sitter_rust')
  ```
- **Status:** **ABERTO** (Somente documentado, aguardando decisão do dono sobre inclusão de dependências opcionais ou extras).

---

### [F4-015] Latência Excessiva de Inicialização por Imports Antecipados de ML (`torch`/`sentence_transformers`) no Bootstrap
- **Severidade:** 🟡 MÉDIA (Severidade Operacional: risco de timeout de clientes MCP durante handshake de inicialização)
- **Arquivos & Linhas:** [`storage/vector_store.py:45-56, 151-177`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py#L45-L56), [`storage/__init__.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/__init__.py), [`main.py:122`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L122)
- **Mecanismo da Falha:**
  No arranque do servidor (`main.py:bootstrap`), a linha 122 executa `from storage import SqliteStore`. Como `storage/__init__.py:18` exporta `from .vector_store import ChromaVectorStore`, o Python avaliava `storage/vector_store.py`, que continha imports no nível do módulo de `from sentence_transformers import SentenceTransformer`. Isso forçava o carregamento antecipado de toda a pilha de machine learning (`sentence_transformers`, `torch`, `transformers`) durante o bootstrap, antes mesmo do servidor MCP poder responder a qualquer mensagem `initialize` ou `list_tools`.
- **Histórico da 4.2b vs. Medições Reais:**
  - *Histórico de Logs da 4.2b (Não medido de forma decomposta):* O intervalo entre `"Initializing SqliteStore"` e `"Schema v3.8.0 verified"` foi registrado em logs como ~100 s (no venv red) e ~29 s (no venv green).
  - *Hipótese de Antivírus / Windows Defender:* **HIPÓTESE NÃO CONFIRMADA** (Regra 3: nenhuma evidência experimental conclusiva confirmou ação ativa de escaneamento de DLLs pelo Windows Defender durante as medições).
  - *Timeout de ~60 s do Claude Desktop:* **NÃO VERIFICADO** (Mencionado em tópicos de fóruns/busca na internet; valor oficial e parâmetros exatos do watchdog do cliente permanecem desconhecidos e não documentados pela especificação MCP).
- **Medições Fidedignas (Rodada 4.2c — Antes da Correção):**
  - Bootstrap completo: **13,22 s** (ambiente do desenvolvedor) a **22,47 s** (venv novo frio).
  - Decomposição de imports (`p1_top20_bootstrap_imports.txt`): dos 13,52 s gastos em `storage`, **11,46 s** (84,8%) eram devidos a `sentence_transformers`, **2,58 s** a `torch` e **2,03 s** a `chromadb`.
  - Tempo até `initialize` E2E: **13,90 s** (`scratch/evidencia_4_2c/c3_e2e_profile.txt`).
- **Resolução Implementada (Rodada 4.2d, Commits `34ad6d5` e `8366860`):**
  1. `SENTENCE_TRANSFORMERS_AVAILABLE` em `storage/vector_store.py` passa a ser verificado sem carregar o pacote via `importlib.util.find_spec("sentence_transformers") is not None`.
  2. O import `from sentence_transformers import SentenceTransformer` foi movido para dentro do método `EmbeddingManager._load_model()`, protegido por `threading.Lock()` thread-safe com double-checked locking.
  3. Falhas no import tardio são capturadas e convertidas em `EmbeddingError` (preservando o contrato de erro).
  4. Testes automatizados criados em [`tests/test_lazy_ml_imports.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_lazy_ml_imports.py) (T1 a T5) garantem isolamento estrito contra regressões.
- **Medições Fidedignas (Rodada 4.2d — Depois da Correção):**
  - Tempo de bootstrap: reduzido de **13,22 s** para **2,77 s** (**-79,1%**, economia de 10,45 s).
  - Tempo até resposta `initialize` E2E: reduzido de **13,90 s** para **3,03 s** (**-78,2%**, economia de 10,87 s).
  - Presença no startup: `sentence_transformers` e `torch` foram **100% eliminados** do bootstrap (`depois_top20_imports.txt`).
  - Tempo residual de startup: consumido principalmente por `chromadb` (1,83 s de import + 0,20 s de instanciação).
  - Trade-off documentado: a carga de pesos e imports de ML passou para a 1ª chamada de embedding, variando de 4,59 s para **15,70 s** (+11,11 s); chamadas subsequentes realizam inferência quente em **~0,016 s**.
- **Status:** **corrigido; verificado pelo auditor; aceito pelo dono no Claude Desktop real (n=1, uma máquina) em 2026-11-01** (Commits `34ad6d5`, `8366860`, `17f046e`, `6defadc`, `30d65c1`). Os testes de lazy import da 4.2d (T1 a T5 em `tests/test_lazy_ml_imports.py`) continuam preservados, 100% verdes e integrados ao workflow `.github/workflows/windows-stdin.yml` (o D5 duplicado e frágil em `tests/test_stdin_decouple.py` foi removido na 4.2g). A Opção A adotada na 4.2f não exigiu aquecimento.
- **Observações Importantes sobre Desempenho e Arquitetura:**
  1. A regressão de latência na 1ª chamada que usa o modelo é esperada e decorre do carregamento sob demanda autorizado pelo dono do projeto para viabilizar um handshake FastMCP imediato (< 3s).
  2. As medições de 4.2e-3 com pré-import mostram latência de ~21-25 s no `mine` e ~4-5 s no `search-first`.
  3. Se a Opção D (aquecimento em thread de baixa prioridade) for desejada no futuro, ela requer rodada própria com medições de CPU/latência em concorrência com o handshake do cliente MCP.

---

### [F4-017] 1ª chamada que usa o modelo trava dentro do servidor MCP no Windows (leitor bloqueado em fd 0)
- **Status:** **corrigido; verificado pelo auditor; aceito pelo dono no Claude Desktop real (n=1, uma máquina) em 2026-11-01** (Commits `17f046e`, `a64f5f1`, `6defadc`, `5b173fd`, `30d65c1`, `96ba4d0`).
- **Severidade:** 🔴 CRÍTICA (Bloqueio total do servidor MCP stdio na 1ª requisição que importa bibliotecas nativas com leitor bloqueado em fd 0 no Windows).
- **Arquivos & Linhas:** [`main.py:111-146, 252-258`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L111-L146), [`tests/test_stdin_decouple.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_stdin_decouple.py), [`.github/workflows/windows-stdin.yml`](file:///c:/Nexus-Memory/GrafoConcierge/.github/workflows/windows-stdin.yml)
- **Fatos Provados vs. Hipótese Não Demonstrada:**
  - **PROVADO (`scratch/evidencia_4_2e`, `4_2f` e `4_2g`):** Com uma thread leitora bloqueada em `fd 0` do `stdin` (`sys.stdin.buffer.readline()`), o primeiro import tardio de bibliotecas nativas (`scipy.special`, `openblas`, `torch`, `sentence_transformers`) trava no Windows com CPU em ~0,0%; desacoplar o `fd 0` antes de iniciar o transporte stdio elimina o travamento.
  - **HIPÓTESE NÃO DEMONSTRADA:** O mecanismo interno do Windows (sincronização/lock interno do CRT ou do loader em `LoadLibraryExW`).
- **Técnica Adotada (Opção A — Desacoplamento de fd 0):**
  Implementada a função `decouple_stdin_from_fd0() -> bool` em `main.py`, invocada antes de iniciar o transporte FastMCP stdio no Windows (`TRANSPORT == "stdio"`). A função:
  1. Duplica o descritor herdado do pai (`fd2 = os.dup(0)`);
  2. Redireciona o `fd 0` para o dispositivo nulo (`os.dup2(os.open(os.devnull, os.O_RDONLY), 0)`);
  3. Reatribui `sys.stdin` a um fluxo de texto envolvendo `fd2` (`closefd=False`).
- **Comprovações Experimentais e Evidências (Rodadas 4.2f e 4.2g):**
  1. **Testes Unitários e Integração (D1–D4 em `tests/test_stdin_decouple.py`):** 4/4 passam no ambiente principal Windows (`scratch/evidencia_4_2g/item1_d_green_main_venv.txt`) e 3 passam + 1 skip explícito (D1 sem `scipy.special`) em venv mínimo sem ML (`scratch/evidencia_4_2g/item1_d_green_venv_min.txt`).
  2. **Docstring e Prova de AST Idêntico (Item 2 da 4.2g):** Docstring retificada em `5b173fd` sem alterar nenhuma linha de código executável (`ast.dump` sem docstrings idêntico entre `21610d8` e `5b173fd` em `scratch/evidencia_4_2g/item2_ast_proof.txt`).
  3. **Teste Definitivo E2E em `mcp 1.27.0` (4.2f) e `mcp 1.30.0` completo (4.2g Item 3c):**
     - Em `mcp 1.27.0` (`venv_mcp127`, 4.2f): 10/10 OK (5 `search-first` + 5 `mine`, `scratch/evidencia_4_2f/tabela_passo4e.txt`; `pip freeze` registrado em `scratch/evidencia_4_2g/item3_venv_mcp127_pip_freeze.txt`). *(Nota: as 10 execuções de `mcp 1.30.0` da 4.2f rodaram sem `chromadb` em modo `NO-OP`, conforme registrado em `audits/errata-4-2f.md`).*
     - Em `mcp 1.30.0` completo (`venv_mcp130_full`, 4.2g Item 3c, com `chromadb=1.5.9`, `sentence_transformers=5.4.1`, `scipy=1.17.1`, `numpy=2.4.4`, `torch=2.11.0`): **10/10 OK** (`0 TRAVOU`, `0 INVÁLIDA`, `13 vetores` no Chroma após cada `mine`, `NO-OP=False`, `scratch/evidencia_4_2g/item3_tabela_head_mcp130.txt`).
  4. **Controle Negativo no Commit `dd92d35` (4.2f Passo 4f e 4.2g Item 3d):** No mesmo `venv_mcp130_full` completo ($n=3$ `search-first` + $n=3$ `mine`, timeout 180s), **6/6 TRAVOU** (`0 OK`, `CPU=0.0%`, `scratch/evidencia_4_2g/item3_tabela_control_dd92d35.txt`), confirmando que o ambiente exercita o travamento real e que o desacoplamento em `HEAD` o elimina.
  5. **CI Windows (`.github/workflows/windows-stdin.yml`, 4.2g Item 4):** Matriz executada em `windows-latest` com Python 3.10, 3.12 e 3.14 (`scratch/evidencia_4_2g/item4_gh_run_main.txt` e teste de mutação na branch descartável `ci-mutacao-4-2g` em `scratch/evidencia_4_2g/item4_gh_run_mutacao.txt`).

---

### [F4-018] Tabela Virtual `nodes_fts` (FTS5) Não Indexava `nodes.content`
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2i`).
- **Severidade:** 🟠 GRAVE (Perda de alcance na busca lexical FTS5 para termos presentes exclusivamente no corpo do documento/código quando `nodes.summary` é `NULL`).
- **Arquivos & Linhas:** [`storage/schema.py:163-238`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py#L163-L238), [`storage/store.py:703`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L703), [`storage/logic.py:440-520`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L440-L520), [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py)
- **Mecanismo da Falha:**
  A tabela virtual FTS5 `nodes_fts` era definida em `storage/schema.py:163-168` indexando apenas `(label, tags, summary)` com `content='nodes'`. Ela não indexava a coluna `content` da tabela `nodes`. Quando o LLM está desativado (`GRAFO_LLM_MODEL=none`) ou indisponível, `nodes.summary` permanece `NULL` (política homologada na Rodada 4.1/E para não gravar placeholders `[DUMB]`). Como consequência, a consulta FTS5 (`SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ...`) buscava apenas em `label` e `tags`, retornando vazio para palavras presentes apenas em `nodes.content` (observado no teste de aceitação do Claude Desktop real para as palavras-sentinela nos arquivos `.md`, onde a recuperação ocorreu exclusivamente pelo canal vetorial do Chroma).
- **Resolução Implementada (Rodadas 4.2i e 4.2j):**
  1. Recriada a tabela virtual FTS5 `nodes_fts` como tabela de conteúdo externo com 4 colunas (`label, tags, summary, content`, `content='nodes', content_rowid='id'`) e tokenizer com suporte diacrítico `tokenize='unicode61 remove_diacritics 2'`.
  2. Triggers de sincronização `nodes_ai`, `nodes_ad` e `nodes_au` em `storage/schema.py:171-187` atualizados para propagar `content` diretamente (`VALUES (new.id, new.label, new.tags, new.summary, new.content)` sem cláusula `COALESCE`, que esteve presente exclusivamente em fixtures de teste).
  3. Migração versionada e idempotente em `storage/schema.py:265-355` (versão de schema bumpada para `3.8.2`): detecta tabelas legadas com 3 colunas inspecionando o DDL de `nodes_fts` em `sqlite_master` (`"SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"` verificando ausência de `content`); realiza backup físico prévio do banco (`<db_path>.pre_fts_v2.bak`) em regime de melhor esforço caso a tabela `nodes` já contenha registros; na Rodada 4.2j a migração foi envolvida em transação atômica única (`BEGIN IMMEDIATE;` ... `COMMIT;` / `ROLLBACK;` sem `executescript`); recria tabela/triggers, executa `rebuild` via `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');` e verificação de integridade via `INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check')`.
  4. Verificação de consistência na inicialização (adicionada na Rodada 4.2j via `_check_and_repair_fts_consistency`): compara `SELECT COUNT(*) FROM nodes` com `SELECT COUNT(*) FROM nodes_fts_docsize`; havendo divergência, emite aviso em log e dispara `rebuild_fts_index()` automático.
  5. Restrição de escopo em `search_symbols` ([`storage/store.py:703`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L703)): a busca por símbolos foi restrita explicitamente à coluna de rótulo (`f'label : "{safe_query}"'`), garantindo com teste de regressão que ocorrências textuais de nomes de funções dentro do corpo de outros arquivos não sejam retornadas espuriamente como definições de símbolos.
  6. Pesos BM25 em `fts_search` ([`storage/logic.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py)): pontuação ranqueada usando pesos hierárquicos `bm25(nodes_fts, 10.0, 5.0, 2.0, 1.0)`, conferindo peso 10x maior para correspondência no `label` (nome do arquivo/símbolo) em relação a menções incidentais no `content`.
  7. Validação por suíte de testes dedicados em [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py) e [`tests/test_fts_atomic_migration.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_atomic_migration.py), teste E2E FastMCP real contra projeto minerado com `GRAFO_LLM_MODEL=none` em `scratch/evidencia_4_2i/b1_green_e2e_mcp.txt`, medições de desempenho/tamanho em `scratch/evidencia_4_2i/b1_measurements.txt` e mutações obrigatórias comprovadas.

---

### [F4-019] Egress Indevido de Chave de API e Fallback Silencioso Entre Provedores em `LLMAdapter` (`GRAFO_LLM_MODEL=none` e falha em `gemini-*`)
- **Status:** **corrigido; verificado pelo auditor (reprodução independente dos testes S1-S7 e das mutações em Linux; E2E por tripwire apenas por evidência do executor)** (Rodadas `4.2h` e `4.2h-2`).
- **Severidade:** 🔴 CRÍTICA (Vazamento de chave de API para endpoint de terceiro não autorizado / chamada externa quando o LLM deveria estar desligado).
- **Arquivos & Linhas:** [`ingestion/summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py), [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py), [`main.py`](file:///c:/Nexus-Memory/GrafoConcierge/main.py), [`interface/cli.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/cli.py), [`.env.example`](file:///c:/Nexus-Memory/GrafoConcierge/.env.example)
- **Mecanismo da Falha:**
  1. Com `GRAFO_LLM_MODEL=none`, `generate_async` em `ingestion/summarizer.py` não desligava o LLM: qualquer modelo que não começasse com `"gemini-"` (e sem `base_url`) caía no ramo `else:` e instanciava `openai.AsyncOpenAI(api_key=self.api_key)`, enviando a chave configurada no ambiente (mesmo sendo de outro provedor) para `https://api.openai.com/v1/chat/completions`.
  2. Com modelos `"gemini-*"`, se a chamada ao Gemini falhasse em `generate_async` (ou se as bibliotecas do Google não estivessem instaladas no caminho síncrono `generate`), a execução prosseguia para o bloco da OpenAI com a mesma chave.
- **Resolução Implementada (Rodada 4.2h):**
  1. Implementada `resolve_llm_provider(model_name, provider, base_url, api_key)` e propriedade `is_enabled` em `LLMAdapter` e `ZoomSummarizer`:
     - Modelos `""`, `"none"`, `"off"`, `"disabled"` (case-insensitive) ou `GRAFO_LLM_PROVIDER` em `("none", "off", "disabled")` ou ausência de chave/URL desativam estritamente o adaptador (`provider="disabled"`, `is_enabled=False`), sem instanciar nenhum cliente e sem chamadas de rede/DNS.
     - Removido 100% do fallback entre provedores (falha ou `ImportError` no Gemini nunca cai para OpenAI).
     - Para usar OpenAI ou endpoint compatível sem `gemini-*`, exige-se escolha explícita via `GRAFO_LLM_PROVIDER=openai` ou `GRAFO_LLM_PROVIDER=openai-compatible` + `GRAFO_LLM_BASE_URL`; sem isso, emite um único `WARNING` claro por instância e opera desativado.
  2. Em `ingestion/orchestrator.py`, quando `not self._summarizer.is_enabled`, a etapa `SUMMARIZE` é pulada com log informativo `"LLM desativado: sumários L0 não gerados"`.
  3. Testes em [`tests/test_llm_egress_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_llm_egress_guard.py) (S1–S8) e prova E2E com Tripwire Proxy em `scratch/evidencia_4_2h/`.

---

### [F4-020] Clientes `AsyncOpenAI` / `OpenAI` Criados por Chamada e Nunca Fechados (`RuntimeError: Event loop is closed`)
- **Status:** **corrigido; verificado pelo auditor (reprodução independente dos testes S1-S7 e das mutações em Linux; E2E por tripwire apenas por evidência do executor)** (Rodadas `4.2h` e `4.2h-2`; ver [`audits/errata-4-2h.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/errata-4-2h.md)).
- **Severidade:** 🟡 MÉDIA (Vazamento de recursos/sockets e 9 tracebacks `RuntimeError: Event loop is closed / Task exception was never retrieved` no fechamento do loop por mineração).
- **Arquivos & Linhas:** [`ingestion/summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py), [`tests/test_llm_egress_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_llm_egress_guard.py)
- **Mecanismo da Falha:**
  Em `ingestion/summarizer.py`, `openai.OpenAI` e `openai.AsyncOpenAI` eram instanciados dentro de `generate` e `generate_async` a cada tentativa sem contexto `with` / `async with` e sem chamada a `close()` / `await aclose()`. Como `ingestion/orchestrator.py` executa `asyncio.run(...)` para processar os chunks, o loop de eventos encerrava antes do coletor de lixo tentar fechar o cliente `httpx.AsyncClient` subjacente, disparando `RuntimeError: Event loop is closed` e `Task exception was never retrieved`.
- **Resolução Implementada (Rodada 4.2h):**
  - Caminho síncrono (`generate`): `with openai.OpenAI(...) as client:` garante `client.close()` determinístico mesmo em exceção.
  - Caminho assíncrono (`generate_async`): `async with openai.AsyncOpenAI(...) as client:` garante `await client.__aexit__(...)` / `aclose()` antes do encerramento do loop de eventos, mesmo quando as 3 tentativas do `tenacity` falham.
  - Provado pelos testes **`S6`** e **`S7`** em [`tests/test_llm_egress_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_llm_egress_guard.py) (`S7` usa servidor HTTP local respondendo `401` sem túnel `CONNECT`, reproduzindo o `Event loop is closed` no código sem `async with` e provando `0` ocorrências com `async with`; conforme registrado em [`audits/errata-4-2h.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/errata-4-2h.md), a prova E2E por Tripwire Proxy não reproduz `F4-020` porque o proxy recusa o `CONNECT` com `403` antes de existir conexão TLS/HTTP ativa a fechar).

---

### [F4-021] Trechos de Chaves Mascaradas pelo Provedor Presentes em Arquivos de Evidência Versionados e Ausência de Redação Automática em Logs
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodadas `4.2h` e `4.2h-2`).
- **Severidade:** 🟡 MÉDIA (Exposição de fragmentos parciais de chave em logs de erro versionados no repositório público).
- **Arquivos & Linhas:** [`scratch/tools/scan_secrets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/tools/scan_secrets.py), [`main.py`](file:///c:/Nexus-Memory/GrafoConcierge/main.py), [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md#L46), [`tests/test_no_secrets_in_tracked_files.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_no_secrets_in_tracked_files.py), [`tests/test_secret_redaction.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_secret_redaction.py)
- **Mecanismo da Falha:**
  Quando uma requisição com chave inválida retornava erro HTTP 401 da OpenAI, a mensagem de exceção incluía o prefixo e o sufixo mascarados da chave (`[REDACTED]`) e era gravada literalmente nos logs de `stderr` capturados em arquivos de evidência versionados (`scratch/evidencia_4_2/p3_matrix_run.txt`, `scratch/evidencia_4_2d/teste_funcional_real.txt`, `scratch/evidencia_4_2e/diag/out__dump_mine_2yfwxq1r__stderr.txt`; também havia um mock de teste em `audits/bypass-governanca-por-session-id.md`, ver `audits/errata-4-2h.md`).
- **Resolução Implementada (Rodadas 4.2h e 4.2h-2):**
  1. Criado scanner determinístico [`scratch/tools/scan_secrets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/tools/scan_secrets.py) e teste de regressão [`tests/test_no_secrets_in_tracked_files.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_no_secrets_in_tracked_files.py).
  2. Redigidos os arquivos versionados substituindo apenas os tokens que casavam com padrões de chave por `[REDACTED]` (`0` achados após redação).
  3. Implementado filtro idempotente de redação de segredos em `main.py` (`setup_logging` via `logging.setLogRecordFactory`), cobrindo `getMessage()` (`msg` + `args`) e exceções formatadas (`exc_info` / `exc_text`) em todos os handlers (incluindo `RichHandler`), redigindo `sk-...`, `AQ....`, `AIza...`, `Bearer <token>` e valores exatos de `GRAFO_LLM_API_KEY` / `GRAFO_API_KEY` ($\ge 8$ caracteres), e refinado na Rodada `4.2h-2` (`F4-022`) com lookbehind negativo `(?<![A-Za-z0-9_])` e paridade estrita com `scan_secrets.py`. Validado por [`tests/test_secret_redaction.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_secret_redaction.py) (R1–R6 e casos de F4-022).
  4. Adicionada a **Regra 13** ao [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md#L46) (linha 46).

---

### [F4-022] Falsos Positivos no Filtro de Redação de Segredos e no Scanner (`sk-[\w*-]{6,}` sem Limite de Palavra Corrompe Nomes de Arquivos)
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2h-2`).
- **Severidade:** 🟡 MÉDIA (Corrupção de texto normal e nomes de arquivos contendo `"sk-"` interno nos logs do servidor MCP, como `"risk-assessment-notes.md"` $\to$ `"ri[REDACTED].md"`).
- **Arquivos & Linhas:** [`main.py:82-95`](file:///c:/Nexus-Memory/GrafoConcierge/main.py#L82-L95), [`scratch/tools/scan_secrets.py:22-35`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/tools/scan_secrets.py#L22-L35), [`tests/test_secret_redaction.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_secret_redaction.py)
- **Mecanismo da Falha:**
  Na Rodada `4.2h`, o padrão `sk-[\w*-]{6,}` em `_LOG_SECRET_PATTERNS` (`main.py`) e em `SECRET_PATTERNS` (`scratch/tools/scan_secrets.py`) não exigia limite de palavra à esquerda. Qualquer palavra inglesa terminada em `"sk"` seguida de hífen e 6+ caracteres (`risk-assessment-notes.md`, `disk-cache-manifest.json`, `task-scheduler-config.yaml`, `desk-setup-checklist.md`, `mask-values-list`) casava a partir de `sk-` e era truncada para `ri[REDACTED].md`, `di[REDACTED].json`, `ta[REDACTED].yaml`, etc. Além disso, o padrão `Bearer\s+[^\s"',;)\]}]+` em `main.py` não exigia dígito no token nem estava presente em `scan_secrets.py`.
- **Resolução Implementada (Rodada 4.2h-2):**
  1. Adicionado lookbehind negativo `(?<![A-Za-z0-9_])` nos padrões `sk-`, `AQ.`, `AIza` e `Bearer\s+` tanto em `main.py` quanto em `scratch/tools/scan_secrets.py`, exigindo que o prefixo do segredo não venha colado a letra, número ou sublinhado.
  2. Unificado o padrão de `Bearer` entre `main.py` e `scan_secrets.py` (`(?<![A-Za-z0-9_])(Bearer\s+)(?!\[REDACTED\])(?=[^\s"',;)\]}]*[0-9])[A-Za-z0-9._~+/=-]{8,}`), evitando falso positivo em frases como `"Bearer token"` sem dígito e mantendo paridade entre filtro e scanner.
  3. Adicionados testes negativos, positivos e de paridade filtro-scanner em [`tests/test_secret_redaction.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_secret_redaction.py), além de prova funcional E2E via MCP `stdio` ($n=3$ sequenciais antes e depois) em `scratch/evidencia_4_2h2/item1_e_mcp_filenames.txt`.

---

### [F4-023] `.env.example` Traz `GRAFO_LLM_PROVIDER=gemini` Ativo por Padrão
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2h-2`).
- **Severidade:** 🟢 BAIXA (Se o usuário copiar `.env.example` para `.env` e trocar apenas `GRAFO_LLM_MODEL` para um modelo não-`gemini-*`, `GRAFO_LLM_PROVIDER=gemini` permaneceria ativo e anularia a trava de segurança de provedor explícito).
- **Arquivos & Linhas:** [`.env.example:20-24`](file:///c:/Nexus-Memory/GrafoConcierge/.env.example#L20-L24), [`tests/test_env_example_provider.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_env_example_provider.py)
- **Mecanismo da Falha:**
  Na Rodada `4.2h`, `.env.example` documentou `GRAFO_LLM_PROVIDER` deixando a linha `GRAFO_LLM_PROVIDER=gemini` descomentada (ativa). Como `resolve_llm_provider` prioriza `GRAFO_LLM_PROVIDER` explícito sobre o prefixo de `GRAFO_LLM_MODEL`, um `.env` derivado diretamente de `.env.example` forçaria o provedor `gemini` mesmo que o usuário mudasse `GRAFO_LLM_MODEL` para outro modelo sem ajustar `GRAFO_LLM_PROVIDER`.
- **Resolução Implementada (Rodada 4.2h-2):**
  1. Comentada a linha `# GRAFO_LLM_PROVIDER=gemini` em [`.env.example`](file:///c:/Nexus-Memory/GrafoConcierge/.env.example#L20-L24) com aviso explícito de que, se `GRAFO_LLM_MODEL` não começar com `"gemini-"`, o provedor deve ser definido explicitamente, caso contrário o LLM permanece desativado por segurança.
  2. Criado teste unitário [`tests/test_env_example_provider.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_env_example_provider.py) (vermelho antes, verde depois, e validado por mutação).


---

### [F4-024] Sintaxe Frágil e Ausência de Fallback Multi-Palavra em Consultas Lexicais FTS5
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2i`).
- **Severidade:** 🟡 MÉDIA (Consultas com múltiplos termos retornavam vazio quando nem todos estavam presentes, consultas vazias ou com caracteres de pontuação geravam exceção `OperationalError` de sintaxe FTS5, e consultas com aspas desbalanceadas ou palavras reservadas podiam causar injeção de sintaxe).
- **Arquivos & Linhas:** [`storage/logic.py:440-520`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L440-L520), [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py)
- **Mecanismo da Falha:**
  O método `fts_search` em `storage/logic.py` passava a string de consulta para a cláusula `MATCH` sem sanitização de caracteres especiais da gramática FTS5 (como `*`, `"`, `:`, `AND`, `OR`, `NOT`, `NEAR`). Se o usuário digitasse uma string com aspas sem fechamento, hífen ou operadores booleanos, o SQLite lançava `sqlite3.OperationalError: fts5: syntax error`. Além disso, para consultas com múltiplos termos sem operadores explícitos, o SQLite FTS5 exige que todos os termos estejam presentes no documento, retornando vazio caso apenas parte dos termos coincida e não oferecendo estratégia de fallback ordenado por relevância.
- **Resolução Implementada (Rodada 4.2i - Bloco 1):**
  1. Implementada a função interna `_build_fts5_queries(query)`:
     - Escapa aspas e remove caracteres de controle e palavras reservadas que possam corromper a gramática do FTS5.
     - Suporta preservação de frases exatas delimitadas por aspas (`"..."`).
     - Gera uma consulta primária com conjunção estrita `AND` entre os termos (`"termo1" AND "termo2"`) e uma consulta alternativa com disjunção `OR` (`"termo1" OR "termo2"`).
     - Retorna tupla vazia para consultas que contenham apenas pontuação, caracteres nulos ou espaços em branco, fazendo com que `fts_search` retorne lista vazia imediatamente sem executar chamada SQL.
  2. Em `fts_search`: tenta primeiramente a consulta `AND`; caso ela retorne zero registros e haja múltiplos termos na busca, executa automaticamente a consulta de fallback com o operador `OR`, cujos resultados são ranqueados naturalmente pela relevância BM25 (priorizando documentos que contêm mais termos correspondentes).
  3. Validado por testes unitários e de mutação em [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py) e prova E2E FastMCP real em `scratch/evidencia_4_2i/b1_green_e2e_mcp.txt`.

---

### [F4-025] CI Vermelho em Ambiente Limpo por Ausência do Extra `openai`, Falha de Paridade em `is_safe_path` no Linux e Falha Não-Marcada de `BL-015`
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2i - Bloco 0`, commit `4263178`).
- **Severidade:** 🟡 MÉDIA (Quebra contínua da pipeline de CI no GitHub Actions em runners Ubuntu para Python 3.10, 3.11 e 3.12, gerando 13 erros de `ModuleNotFoundError: No module named 'openai'` e 3 falhas de teste).
- **Arquivos & Linhas:** [`pyproject.toml:57-70`](file:///c:/Nexus-Memory/GrafoConcierge/pyproject.toml#L57-L70), [`requirements.txt`](file:///c:/Nexus-Memory/GrafoConcierge/requirements.txt), [`core/security_guard.py:30-58`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py#L30-L58), [`tests/test_adaptive_gating.py:27-60`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py#L27-L60), [`tests/test_progressive_tool_disclosure.py:80-92`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_progressive_tool_disclosure.py#L80-L92), [`.github/workflows/windows-stdin.yml`](file:///c:/Nexus-Memory/GrafoConcierge/.github/workflows/windows-stdin.yml)
- **Mecanismo da Falha:**
  1. A biblioteca `openai` não estava declarada nos extras opcionais de desenvolvimento em `pyproject.toml`. Em instalações limpas do CI (`pip install -e ".[dev]"`), o pacote não era instalado, fazendo com que a suíte de testes `tests/test_llm_egress_guard.py` (adicionada na 4.2h) falhasse na importação (testes S1 a S8, 13 erros).
  2. Em `core/security_guard.py`, a função `is_safe_path` utilizava exclusivamente `Path(path).is_absolute()`. No Linux, caminhos com formato Windows (como letra de drive `C:\Windows\System32` ou compartilhamentos UNC `\\server\share`) não são considerados absolutos pelo `pathlib.Path` POSIX. Consequentemente, `Path(project_root) / path` resolvia para `project_root / "C:\Windows\..."`, que ficava contido na raiz do projeto e retornava `True` indevidamente, quebrando o teste `test_path_outside_monorepo_is_unsafe` no Ubuntu.
  3. O teste `test_telemetry_api_mcp_state_endpoints` (`BL-015`) esperava o estado inicial `PLANNING`, mas a API retornava `EXECUTION`. O teste falhava continuamente no CI sem marcação de falha esperada estrita, gerando falso alarme e mascarando regressões.
- **Resolução Implementada (Rodada 4.2i - Bloco 0):**
  1. Em `pyproject.toml`, criado o extra `openai = ["openai>=1.0"]` e adicionado aos extras `dev` e `all`, mantendo `openai` estritamente opcional fora de dependências obrigatórias. Documentado no `requirements.txt`.
  2. Em `core/security_guard.py`, a função `is_safe_path` foi atualizada com verificação multiplataforma (`is_posix_abs = raw_path.startswith("/")`, `is_win_drive = bool(re.match(r"^[a-zA-Z]:[\\/]", raw_path))`, `is_win_unc = raw_path.startswith(("\\\\", "//"))`), garantindo que caminhos absolutos de qualquer sistema operacional sejam rejeitados quando fora do diretório do projeto, mesmo rodando em runner Linux. Adicionados testes de paridade cross-platform em `tests/test_adaptive_gating.py`.
  3. Marcado o teste `test_telemetry_api_mcp_state_endpoints` em `tests/test_progressive_tool_disclosure.py` com o decorador `@pytest.mark.xfail(strict=True, reason="BL-015:...")`, provando com teste de controle que uma correção do estado avisará imediatamente como `XPASS(strict)` e mantendo o item `BL-015` aberto no roadmap.
  4. Atualizado o workflow `.github/workflows/windows-stdin.yml` para instalar `pip install -e ".[dev]" scipy`.


---

### [F4-026] Migração FTS Não-Atômica e Ausência de Verificação de Consistência na Inicialização
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2j`, commit `b360bb9`).
- **Severidade:** 🟡 MÉDIA (Se o processo caísse após o `DROP TABLE nodes_fts` e antes do `rebuild`, ou durante o `rebuild`, o uso de `executescript` gerava commit implícito deixando o FTS vazio na versão 3.8.2; a inicialização subsequente não detectava a inconsistência e a busca por nós existentes retornava 0 resultados sem erro).
- **Arquivos & Linhas:** [`storage/schema.py:268-355`](file:///c:/Nexus-Memory/GrafoConcierge/storage/schema.py#L268-L355), [`tests/test_fts_atomic_migration.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_atomic_migration.py)
- **Mecanismo da Falha:**
  Em `storage/schema.py`, a migração do FTS para 4 colunas utilizava `self._conn.executescript(FTS5_TABLE_SQL)` e `self._conn.executescript(FTS5_TRIGGERS_SQL)`. No SQLite/Python, `executescript` emite um `COMMIT` implícito antes de executar cada script. Se o processo sofresse uma interrupção (crash, SIGKILL, falta de energia) após o `DROP` e criação das tabelas mas antes do `rebuild`, as tabelas e triggers FTS ficavam criados vazios e persistidos. Na inicialização seguinte, o `SchemaManager` via a versão `3.8.2` e a tabela `nodes_fts` já existente com 4 colunas e não executava novo `rebuild`. Como o FTS externo (`content='nodes'`) utiliza tabelas shadow (`nodes_fts_docsize`) para saber quais documentos foram indexados, o índice permanecia completamente vazio enquanto a tabela `nodes` continha centenas de registros.
- **Resolução Implementada (Rodada 4.2j - Item 1):**
  1. A sequência de migração (`DROP TRIGGER IF EXISTS ...`, `DROP TABLE IF EXISTS ...`, `CREATE VIRTUAL TABLE ...`, criação individual de cada trigger via `self._conn.execute(...)`, `rebuild` e `integrity-check`) foi envolvida em uma única transação explícita com `BEGIN IMMEDIATE;` ... `COMMIT;` e `ROLLBACK;` em bloco `try...except`, sem qualquer chamada a `executescript`.
  2. Implementada verificação de consistência na inicialização (`_check_and_repair_fts_consistency`): se `nodes` tem registros (`node_count > 0`), compara com `SELECT COUNT(*) FROM nodes_fts_docsize`. Se houver divergência (`doc_count != node_count`), emite aviso em log (`logger.warning`) e executa rebuild automático com `rebuild_fts_index()`.
  3. O backup pré-migração foi documentado e logado explicitamente como "melhor esforço" (`melhor esforço`), emitindo `logger.warning` em caso de falha sem abortar a migração atômica.
  4. Criada suíte de testes em [`tests/test_fts_atomic_migration.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_atomic_migration.py), com prova de atomicidade (falha no rebuild reverte ao banco de 3 colunas e busca legada segue funcionando), detecção do cenário do auditor e idempotência com preservação exata do hash dos dados de `nodes`. Validação por 2 mutações obrigatórias.

---

### [F4-027] Filtro de Palavras-Chave FTS5 (AND, OR, NOT, NEAR) no Construtor de Consultas
- **Status:** **corrigido pelo executor, aguardando verificação independente** (Rodada `4.2j`, commit `4313351`).
- **Severidade:** 🟢 BAIXA (Palavras perfeitamente legítimas da língua e de código-fonte como "not found", "AND", "NEAR(a b)" e "a AND b OR c" tinham seus termos removidos indevidamente antes do envio ao FTS5).
- **Arquivos & Linhas:** [`storage/logic.py:386-403`](file:///c:/Nexus-Memory/GrafoConcierge/storage/logic.py#L386-L403), [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py)
- **Mecanismo da Falha:**
  Em `storage/logic.py`, o método `_build_fts5_queries` continha uma lista de palavras reservadas `fts_keywords = {"AND", "OR", "NOT", "NEAR"}` e removia qualquer token que coincidisse com elas. Porém, como cada token é delimitado individualmente por aspas duplas (`'"' + t.replace('"', '""') + '"'`), a gramática do SQLite FTS5 trata palavras entre aspas como literais puros, e não como operadores de consulta. A remoção indevida fazia com que buscas por "not found" virassem apenas `"found"` (retornando documentos que não continham "not"), buscas por "NEAR(a b)" virassem `"a" AND "b"`, e buscas por "AND" em expressões tivessem palavras suprimidas.
- **Resolução Implementada (Rodada 4.2j - Item 2):**
  1. Removida a filtragem de `fts_keywords` em `_build_fts5_queries`: todos os tokens extraídos por expressão regular recebem aspas duplas, desarmando operadores booleanos do FTS5 e buscando-os como palavras literais.
  2. Adicionados testes em [`tests/test_fts_code_search.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_fts_code_search.py) cobrindo especificamente: `"not found"`, `"AND"` isolado, `"NEAR(a b)"` e `"a AND b OR c"`, provando que antes da correção documentos que continham apenas `found` casavam indevidamente e após a correção apenas documentos contendo ambos os termos são retornados. Validado por mutação.


---

### [BL-006] Checkpoints Salvos Fora da Fila Serializada SerializedWriteQueue
- **Status:** **ABERTO (registrado na Rodada 4.3 pelo executor, aguardando priorização e planejamento)**
- **Severidade Proposta:** 🟡 MÉDIA (Risco de contenção transacional e falhas do tipo `database is locked` sob concorrência de múltiplos agentes ou quando o `JanitorService` / `Store` executam escritas em segundo plano via `SerializedWriteQueue`).
- **Arquivos & Linhas:** [`core/checkpointer.py:113-114, 139-140, 206-209`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L113-L114), [`interface/mcp_server.py:164-166`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L164-L166)
- **Mecanismo da Falha:**
  Em `core/checkpointer.py`, os métodos de escrita de checkpoints (`save_checkpoint`, `restore_checkpoint`, `_cleanup_old_checkpoints`) invocam `write_fn` diretamente através de reflexão:
  `write_fn = getattr(self.db, "execute_write", getattr(self.db, "write_query", None))`
  e realizam chamadas diretas como `write_fn(query, params)`.
  No MCP Server (`interface/mcp_server.py:166`), a instância de `AgnosticCheckpointer` é conectada a `db_manager` (`ConciergeDatabaseManager`). Se `db_manager` for instanciado sem fila (`write_queue=None`), as escritas abrem conexões efêmeras imediatas (`sqlite3.connect`) fora do controle do thread único de gravação. Mesmo quando há uma fila conectada, a arquitetura mantém dois subsistemas de gravação concorrentes (a fila de `core/database.py` e a fila de `storage/store.py`), violando o princípio do escritor único e criando risco real de bloqueio em cenários de alta frequência de checkpoints.
- **Justificativa da Severidade (MÉDIA):**
  Embora o SQLite WAL permita múltiplos leitores concorrentes, ele admite apenas um escritor por vez. Quando múltiplos agentes tentam salvar checkpoints simultaneamente à ingestão ou compactação do Janitor, a escrita direta contorna a política central de serialização transacional do sistema, gerando potenciais exceções e degradação de confiabilidade na retenção de memória de longo prazo dos agentes.
- **Resolução Recomendada (Para Rodada Futura):**
  Unificar o canal de persistência do `AgnosticCheckpointer` para utilizar estritamente a fila central de escrita serializada de produção (`SerializedWriteQueue`), padronizando o timeout e o tratamento transacional assíncrono.

---

### [F4-028] Ordem Não-Determinística de Varredura no ProjectCrawler.crawl Afeta Resolução de Símbolos Repetidos
- **Status:** **ABERTO (registrado na Rodada 4.3c pelo executor, aguardando priorização e planejamento)**
- **Severidade Proposta:** 🟡 MÉDIA (Em projetos com múltiplos arquivos contendo símbolos de mesmo nome, a ordem em que os arquivos são inseridos em `global_symbol_map` depende da ordem de retorno do sistema de arquivos subjacente via `os.walk`, tornando a resolução de chamadas não-determinística entre diferentes sistemas operacionais ou instalações).
- **Arquivos & Linhas:** [`ingestion/crawler.py:501`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L501), [`ingestion/orchestrator.py:682-684, 768`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L682)
- **Mecanismo da Falha:**
  Em `ingestion/crawler.py:501`, o método `crawl` itera pela árvore de diretórios utilizando `os.walk(root)` sem pré-ordenação de `dirnames` ou `filenames`. No Windows NTFS, as entradas costumam ser retornadas na ordem de B-tree do sistema de arquivos; em sistemas Linux (ext4/xfs), são retornadas na ordem de hash dos diretórios.
  Durante a mineração (`ingestion/orchestrator.py`), cada arquivo varrido tem seus símbolos extraídos e gravados na tabela `nodes` do SQLite em sequência, gerando IDs autoincrementais crescentes (`id=1, 2, 3...`). O dicionário em memória `global_symbol_map[sym]` acumula os IDs na ordem exata de inserção (`ingestion/orchestrator.py:682-684`):
  ```python
  if sym not in global_symbol_map:
      global_symbol_map[sym] = []
  global_symbol_map[sym].append(nid)
  ```
  Na resolução de chamadas AST de funções/métodos repetidos (`ingestion/orchestrator.py:768`), o código seleciona:
  ```python
  if not target_node_id and call_name in global_symbol_map:
      target_node_id = global_symbol_map[call_name][0]
  ```
  Ou seja, o primeiro símbolo encontrado na varredura. Como a ordem de varredura depende do sistema de arquivos e do disco, o mesmo repositório clonado em máquinas distintas ou sistemas de arquivos diferentes pode resolver a chamada para nós distintos.
- **Justificativa da Severidade (MÉDIA):**
  Embora funções e métodos homônimos em módulos distintos devam idealmente ser desambiguados por escopo de módulo ou namespace no AST, a dependência da ordem não-ordenada do `os.walk` introduz comportamento divergente não-reprodutível entre ambientes (ex: Windows vs Linux CI), afetando a estabilidade da topologia do grafo.
  Descoberto e isolado na Rodada 4.3c durante a elaboração do teste com mineração real no Item 2a, que foi projetado de forma robusta para comparar dinamicamente contra a ordem real de inserção no banco de dados (`min(ids)`).
- **Resolução Recomendada (Para Rodada Futura):**
  1. Em `ingestion/crawler.py:501`, ordenar deterministicamente `dirnames.sort()` e `filenames.sort()` antes de cada iteração.
  2. Em `ingestion/orchestrator.py:768`, considerar o caminho relativo do módulo importado ou heurística explícita de proximidade de namespace antes de recorrer ao fallback de desambiguação global.

---

### [F4-029] Travamento Indefinido no Handshake e Espera em response_queue.get() por Morte Silenciosa da Thread Daemon em interface/queue_writer.py
- **Status:** **corrigido pelo executor, verificado pelo auditor (Linux, 3.10–3.13)**
- **Escopo:** Explicitamente restrito a `interface/queue_writer.py`, **sem uso no caminho de produção do servidor (provado por `git grep`)** — o servidor MCP em produção utiliza `main.py` → `SqliteStore` → `ConnectionManager` → `storage/connection.py::SerializedWriteQueue` (tratado em `F4-031`).
- **Severidade:** 🟠 GRAVE (Restrito a `interface/queue_writer.py`, utilizado em suítes de teste e `ConciergeDatabaseManager` quando instanciado com `write_queue`).
- **Arquivos & Linhas:** [`interface/queue_writer.py:33-40, 65-73, 267-268, 294-304`](file:///c:/Nexus-Memory/GrafoConcierge/interface/queue_writer.py#L33), [`core/database.py:51, 67`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py#L51), [`tests/test_graph_rag_janitor.py:84`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_graph_rag_janitor.py#L84)
- **Fato (reproduzido pelo auditor, Linux):**
  Em `interface/queue_writer.py:50`, a instrução `conn.execute("PRAGMA journal_mode=WAL;")` ficava fora de qualquer bloco `try/except`. Quando essa instrução levantava `sqlite3.OperationalError: database is locked`, a thread daemon (`SerializedWriteQueue.run`) morria prematuramente antes de entrar no loop de processamento.
  Posteriormente, qualquer chamada a `execute_write` (linha 147) submetia uma mensagem e esperava indefinidamente em `response_queue.get()` sem timeout. Como a thread daemon já havia encerrado, a resposta nunca era postada e quem chamou travava para sempre.
  Evidência: 14 de 14 exceções capturadas, em 14 processos no ambiente do auditor, bloquearam exatamente nessa linha.
- **Hipóteses (não provadas):**
  1. A causa pela qual o banco SQLite está travado na linha 50 (corrida na troca para WAL de um banco recém-criado com outra conexão aberta concorrentemente).
  2. Se essa colisão de PRAGMA/lock ocorre ou pode ocorrer no caminho ordinário de produção em regime mono-servidor.
- **Correção Implementada na Rodada 4.4b (Bloco 1):**
  1. Loop de retry com backoff exponencial com constantes nomeadas para inicialização da conexão SQLite e execução dos PRAGMAs na thread trabalhadora, capturando `sqlite3.OperationalError` ("database is locked" / "database is busy").
  2. Salvamento de erro em `self._startup_error` e sinalização de prontidão via `threading.Event` (`self._ready`).
  3. Loop não-bloqueante em `execute_write` com timeout total (`EXECUTE_TIMEOUT_SECONDS`), verificando periodicamente se a thread está viva (`self.is_alive()`) e se houve erro de inicialização.
  4. Detecção de morte tardia da thread: descarte com falha dos itens pendentes e falha rápida em chamadas subsequentes, preservando o contrato de retorno `(False, e)`.
  5. Ajustes adicionais no `5abba37`: Alinhamento do orçamento de handshake com `STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5s`, checagem estrita de timeout no handshake de `execute_write` com `TimeoutError` descritivo, notificação do lote ativo em falhas de worker, descarte de tarefas ainda na fila cujo deadline já expirou (nota: uma escrita já em execução no SQLite não é interrompida e continua sendo gravada) e remoção do comando `PRAGMA journal_mode=WAL;` em `core/database.py:read_query()` (nota: a remoção do PRAGMA não reduziu os retries medidos e a causa do lock segue desconhecida).
- **Regressão Identificada no Commit 5abba37 e Correção Definitiva na Rodada 4.4c:**
  1. *Regressão comprovada pela auditoria independente no 5abba37:* A introdução de `sqlite3.connect(..., timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)` (1.5s) restringiu permanentemente o busy handler da conexão persistente do worker SQLite para 1.5s durante todo o regime de operação. Quando outra conexão externa segurava o lock por 3.0s, o worker no commit `8659813` aguardava os 30s de regime e obtinha sucesso, mas no `5abba37` falhava prematuramente após 1.5s com `database is locked`.
  2. *Correção na Rodada 4.4c (Bloco 1 e Bloco 0b):*
     - Constantes nomeadas de resiliência: `STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5` (curto, exclusivo para a janela de conexão e PRAGMAs do handshake) e `REGIME_BUSY_TIMEOUT_MS = 30000` (30s de regime padrão).
     - Imediatamente após a conclusão bem-sucedida do handshake WAL e synchronous, o worker executa `conn.execute(f"PRAGMA busy_timeout = {REGIME_BUSY_TIMEOUT_MS};")`, restaurando a espera de regime de 30s sem o overhead ou risco de reconexão física.
     - Teste T9 (`test_t9_busy_timeout_regime_allows_lock_held_for_3s_to_succeed`): demonstrou em vermelho a regressão no código `5abba37` (falha após 1.5s) e verde no código corrigido (sucesso em ~3.0s). Mutação Qh aplicada e morta.
     - Cobertura de morte no laço e espera limitada: Testes T10 e T11 adicionados, matando as mutações Qb e Qg que sobreviviam na 4.4b.
     - Pré-start e caracterização: `execute_write` falha imediatamente (<0.2s com `RuntimeError`) se a thread sequer foi iniciada (`self.ident is None`), e teste determinístico de caracterização comprova que tarefas já em voo no SQLite completam seu ciclo de escrita mesmo após o chamador sofrer timeout local.
     - Verificado pelo auditor independente em Linux nos Python 3.10–3.13 (após o Bloco 0b no commit `9519e16`).

---

### [F4-030] Mineração Sobrescreve Silenciosamente a Ala Escolhida pelo Usuário no Cadastro via `auto_categorize_project`
- **Status:** **corrigido pelo executor, aguardando verificação independente**
- **Severidade Proposta:** 🟠 GRAVE / ALTA (Violação do propósito de honestidade e neutralidade: um projeto explicitamente categorizado pelo usuário ou agente tinha sua ala primária alterada em silêncio durante a mineração ordinária).
- **Arquivos & Linhas:** [`core/middleware.py:219, 239-242`](file:///c:/Nexus-Memory/GrafoConcierge/core/middleware.py#L219), [`core/project_index.py:142-172`](file:///c:/Nexus-Memory/GrafoConcierge/core/project_index.py#L142), [`core/config.py:77-99`](file:///c:/Nexus-Memory/GrafoConcierge/core/config.py#L77)
- **Mecanismo da Falha:**
  O método `GrafoConcierge.mine` possuía o parâmetro `auto_categorize: bool = True` como padrão.
  Ao término da mineração com `nodes_created > 0`, invocava incondicionalmente `self._project_index.auto_categorize_project(project_uuid)`.
  Este método, por sua vez, analisava os labels e tags contra o dicionário fixo `wing_keywords` e executava `self.set_primary_wing(project_uuid, wing)`, sobrescrevendo no banco a `primary_wing` escolhida pelo usuário no momento do cadastro (`concierge_register`).
- **Reprodução Real na Rodada 4.4 (Bloco 1):**
  Provado em vermelho em `scratch/evidencia_4_4/b1_mine_overwrite_red.txt`:
  Um projeto registrado com `wing="minha-ala"` teve sua `primary_wing` silenciosamente alterada para `"marketing/vendas"` após minerar um arquivo com termos de marketing.
- **Correção Implementada na Rodada 4.4 (Bloco 1):**
  1. Remoção do campo `wing_keywords` de `ConciergeConfig` (`core/config.py`).
  2. Remoção dos métodos `categorize_project` e `auto_categorize_project` de `ProjectIndex` (`core/project_index.py`).
  3. Remoção do parâmetro `auto_categorize`, da chave `auto_categorized_wing` e da mutação de ala em `GrafoConcierge.mine` (`core/middleware.py`).
  4. Criação dos testes-guarda G1, G2, G3 e G4 em `tests/test_domain_neutrality_guard.py` e eliminação das mutações (a), (b) e (c). Na Rodada 4.4b, a guarda G2 foi fortalecida: varre todos os arquivos Python descobertos dinamicamente via `git ls-files '*.py'` (incluindo `main.py` e `scripts/`), aplicando busca por substring em literais AST/docstrings para os 7 termos proibidos (`marketing/vendas`, `finanças/quant`, `financas/quant`, `gestão/saas`, `gestao/saas`, `automação/rh`, `automacao/rh`) e igualdade exata para o domínio isolado `estatística` / `estatistica`. Exclusões estritas restritas à allowlist documentada. Mutações (i), (ii) e (iii) eliminadas com sucesso.



---

### [F4-031] Fila de Escrita de Produção (`storage/connection.py::SerializedWriteQueue`) Pode Travar Indefinidamente na Partida ou em Morte da Thread Worker
- **Status:** **corrigido pelo executor, aguardando verificação independente**
- **Severidade:** 🟠 GRAVE (Aprovada pelo usuário na Rodada 4.4d; afeta o caminho real de produção do servidor MCP: `main.py` → `SqliteStore` → `ConnectionManager` → `storage/connection.py::SerializedWriteQueue`).
- **Arquivos & Linhas:** [`storage/connection.py:59-190`](file:///c:/Nexus-Memory/GrafoConcierge/storage/connection.py#L59), [`storage/store.py:72-76`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L72), [`tests/test_connection_queue_resilience.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_connection_queue_resilience.py)
- **Fato Provado (reproduzido por injeção pelo auditor independente):**
  1. Em `storage/connection.py` (no commit `9519e16`), o método `_worker` executava `sqlite3.connect(self._db_path)` e os comandos `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=5000;` e `PRAGMA foreign_keys=ON;` fora de qualquer bloco `try/except`. Se `sqlite3.connect` ou qualquer PRAGMA levantasse `sqlite3.OperationalError: database is locked`, a thread `sqlite-writer` morria em silêncio antes de entrar no laço de consumo.
  2. O método `submit` aguardava em `job.result_event.wait()` sem prazo e sem checar `self._thread.is_alive()`, fazendo `ConnectionManager.write` travar para sempre.
  3. Caso a thread morresse após a partida (ex.: exceção fora do `except Exception` do job, falha em `rollback()` ou `BaseException`), os jobs pendentes na fila e chamadas subsequentes ficavam sem resposta.
- **Hipótese Não Provada:**
  - O gatilho natural de `database is locked` na partida da fila de produção **não foi reproduzido** (0 de 40 processos no Linux pelo auditor; medido também em 100 processos no Windows na Rodada 4.4d sem concluir causa).
- **Correção Implementada na Rodada 4.4d (Bloco 1):**
  1. **Partida robusta com handshake sincronizado (`start()`):** `_worker` envolve `sqlite3.connect(..., timeout=STARTUP_CONNECT_TIMEOUT_SECONDS)` e os PRAGMAs em `try/except`, aplicando retry com backoff exponencial limitado (`MAX_CONNECT_RETRIES = 5`, `STARTUP_CONNECT_TIMEOUT_SECONDS = 1.5`, `INITIAL_BACKOFF_SECONDS = 0.05`, `MAX_BACKOFF_SECONDS = 1.0`) exclusivamente para `database is locked` e `database is busy`. Outros erros de `OperationalError` (como `disk I/O error`) falham imediatamente sem retry, fechando a conexão parcial. Em falha definitiva, armazena `self._startup_error`, fecha a conexão, drena jobs pendentes, sinaliza `self._ready.set()` e encerra a thread. `start()` aguarda `self._ready.wait(timeout=READY_TIMEOUT_SECONDS)` (< 10 s) e levanta `RuntimeError` com causa encadeada (`raise RuntimeError(...) from self._startup_error`).
  2. **Preservação estrita do regime de produção (`PRAGMA busy_timeout=5000`):** Imediatamente após o handshake com timeout curto (1.5 s), o worker aplica `PRAGMA busy_timeout=5000;`, `PRAGMA journal_mode=WAL;` e `PRAGMA foreign_keys=ON;`, mantendo `row_factory = sqlite3.Row` (provado pelo teste P7 e mutação Rf).
  3. **`submit` sem espera infinita e sem prazo total para jobs em execução:** Substituído `job.result_event.wait()` sem argumentos por espera em laço curto (`POLL_INTERVAL_SECONDS = 0.05`), checando a cada volta se `self._thread.is_alive()` e se houve erro fatal ou de partida. Se o worker morrer sem sinalizar o job, levanta `RuntimeError("write worker died: ...")` com causa encadeada. Jobs longos em execução não sofrem `TimeoutError` artificial (invariante 5, provado por P5 e mutação Rg).
  4. **Tratamento de morte tardia:** Qualquer falha fatal fora do `except` normal do job (incluindo falha em `rollback()` ou `BaseException`) registra `self._fatal_error`, notifica o job em voo e drena todos os jobs pendentes em `self._queue` no bloco `finally`, fazendo chamadas seguintes a `submit` falharem imediatamente.
  5. **Validação:** Testes P1 a P9 (nascidos em vermelho contra `9519e16`) e mutações Ra a Rh mortas por script externo, com evidências em `scratch/evidencia_4_4d/`.
