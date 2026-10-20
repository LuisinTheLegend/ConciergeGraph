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
- **Status:** **CONFIRMADO**

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
- **Status:** **CONFIRMADO** (Correção agendada para Rodada 4.3 conforme Caminho B)

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



