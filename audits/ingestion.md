# Relatório de Auditoria: `ingestion/` (Todos os Arquivos)

> **Data:** 22 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE (Regra 7)  
> **Escopo:** Diretório [`ingestion/`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion):
> - [`ingestion/__init__.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/__init__.py)
> - [`ingestion/crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py)
> - [`ingestion/parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py)
> - [`ingestion/summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py)
> - [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py)

---

## 1. Resumo Executivo e Tabela Consolidada de Achados

O pipeline de ingestão (`ingestion/`) é o motor primário responsável pela extração de código, geração de AST/chunks semânticos, sumarização multinível (L0/L1/L2) via LLMs, e inserção coordenada nas bases relacional (SQLite) e vetorial (ChromaDB).

A auditoria estática e empírica aprofundada de todos os 5 arquivos de `ingestion/` revelou **8 achados técnicos confirmados com 100% de reprodução empírica**. Entre as falhas descobertas estão:
1. **Perda total no grafo na renomeação de arquivos** provocada por colisão cega de hash no crawler combinada com a purga destrutiva do Garbage Collector do orquestrador;
2. **Descarte silencioso de 100% dos resumos L0** gerados por LLM, gravando `nodes.summary = NULL` no banco e esterilizando a geração subsequente de L1 e L2;
3. **Falha silenciosa de persistência do L2 Compass** na tabela `projects` por passagem do nome da pasta (`folder_name`) no lugar da chave primária (`uuid`);
4. **Acúmulo perpétuo de vetores zumbis no ChromaDB** na modificação de arquivos de código, deteriorando a busca vetorial;
5. **Poluição de erros e quebra de contrato (`AttributeError`)** quando o summarizer é instanciado como `None`;
6. **Descarte arbitrário de arquivos essenciais** como `requirements.txt` por inclusão indevida de `*.txt` nos padrões padrão de ignore;
7. **Poluição severa de taxonomia/tags** por checagem ingênua de substrings (`reaction` -> `react`, `next()` -> `nextjs`);
8. **Truncamento prematuro de código em JS/TS** devido a contagem ingênua de chaves `{}` que não ignora strings ou comentários.

### Tabela Geral de Achados (Protocolo Regra 6)

| # | Arquivo | Linha | Severidade | Mecanismo | Reprodução | Status |
|---|---|---|---|---|---|---|
| **#1** | [`ingestion/crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L560) <br> [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L765) | `560`, `765` | 🔴 **CRÍTICA** | `find_node_by_hash` busca nó apenas por `(project_uuid, file_hash)` ignorando `relative_path`. Ao renomear um arquivo sem alterar conteúdo, o crawler classifica o novo arquivo como inalterado (`is_new=False`), não o ingere, e `_detect_deleted_nodes` marca o caminho antigo como deletado. O GC do orquestrador purga os nós do caminho antigo, resultando na **perda total do arquivo no grafo (0 nós)**. | Script empírico reproduz rename `a.py -> b.py`: nós caem de 2 para 0 | **CONFIRMADO** |
| **#2** | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L191) <br> [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L571) | `191`, `201`, `571` | 🔴 **CRÍTICA** | `_step_summarize` chama o LLM e retorna `list[SummaryResult]`, mas essa lista **nunca é atribuída aos chunks** nem repassada para `_step_store_sqlite`. Em `_step_store_sqlite:571`, o código busca `chunk.cached_summary` (que é sempre `None` para novos chunks). Todos os nós são gravados no SQLite com `summary = NULL`. Como consequência, `generate_project_context:843` encontra 0 resumos e pula L1 e L2. | LLM executa 5 chamadas com sucesso, mas todos os nós no SQLite ficam com `summary = None` | **CONFIRMADO** |
| **#3** | [`ingestion/summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py#L789) <br> [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L880) | `789`, `880-883` | 🟠 **GRAVE** | `summarize_l2` recebe `project_name` (`folder_name`, ex: `"MeuProjeto"`) vindo do orquestrador e chama `_store.update_project(project_name, summary=...)`. `SqliteStore.update_project` executa `WHERE uuid = ?`. A query não casa com o UUID real (`proj-uuid-...`), afeta 0 linhas e não lança exceção no SQLite. O `try/except` nunca captura a falha e o código emite `logger.info("L2 Compass persisted...")`, gerando uma **falsa confirmação de sucesso no log** enquanto o resumo L2 é permanentemente perdido. | Projeto com UUID real não recebe o L2 retornado pelo summarizer (`projects.summary` permanece `None`) | **CONFIRMADO** |
| **#4** | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L213) <br> [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L234) | `213`, `234-239` | 🟠 **GRAVE** | Ao reingerir um arquivo modificado, `_store.cleanup_obsolete_nodes` deleta chunks antigos apenas no SQLite. O Step 7 (`_step_garbage_collection`), que reconcilia o Chroma via `verify_sync`, é protegido por `if crawl_report.deleted_node_ids:`. Como a modificação não deleta arquivos do disco, `deleted_node_ids` fica vazio, o GC é pulado e os **vetores antigos permanecem para sempre como zumbis no ChromaDB**. | Após edição com remoção de função, SQLite fica com 2 nós vivos e Chroma acumula 5 vetores (3 zumbis) | **CONFIRMADO** |
| **#5** | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L442) <br> [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L449) | `442`, `449` | 🟡 **MÉDIA** | Em `_step_summarize`, a Fase 2 checa `if small_chunks and self._summarizer:`, mas a Fase 3 (regular chunks) checa apenas `if regular_chunks:`. Se `self._summarizer is None`, a task assíncrona invoca `await self._summarizer.summarize_l0_async(chunk)`, explodindo com `AttributeError: 'NoneType' object has no attribute 'summarize_l0_async'` e poluindo `result.errors` para cada chunk. | Ingestão com `summarizer=None` gera erro interno `AttributeError` em `result.errors` | **CONFIRMADO** |
| **#6** | [`ingestion/crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L395) <br> [`ingestion/crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L481) | `395`, `481` | 🟡 **MÉDIA** | `DEFAULT_IGNORE_PATTERNS` inclui indevidamente `"*.txt"`. Na inicialização do crawler sem `.gitignore` de usuário, a Camada 1 injeta essa regra, fazendo com que arquivos como `requirements.txt` e documentações `.txt` sejam sumariamente descartados do grafo, em contradição direta com o `EXTENSION_MAP` que mapeia `.txt` para `FileCategory.DOC`. | Crawler escaneia diretório com `requirements.txt` e retorna lista vazia de arquivos | **CONFIRMADO** |
| **#7** | [`ingestion/parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L973) <br> [`ingestion/parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L100-L111) | `100-111`, `973-975` | 🟡 **MÉDIA** | `_detect_tags` faz busca ingênua de substring `keyword in content_lower` sem limites de palavra (`\b`). Termos comuns de código Python como chamadas à builtin `next()` e identificadores contendo `reaction` provocam a inclusão espúria de tags de frameworks frontend como `nextjs` e `react` em código puramente backend. | Código Python contendo `reaction` e `next()` recebe tags falsas `['nextjs', 'react']` | **CONFIRMADO** |
| **#8** | [`ingestion/parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L701) <br> [`ingestion/parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L715) | `701-715` | 🟡 **MÉDIA** | O parser de JS/TS usa contagem ingênua de caracteres `{` e `}` (`_find_block_end_braces`) sem máquina de estados léxica. Strings contendo chaves (ex.: templates HTML `<div>}</div>`), expressões regulares ou comentários de código fecham prematuramente o bloco da função, truncando o chunk antes do `return` e corrompendo a integridade do grafo. | Função JS com string contendo `}` é cortada na linha 2, omitindo o corpo restante | **CONFIRMADO** |

---

## 2. Matriz de Interação Interna (Entre os Arquivos de `ingestion/` entre si)

Esta matriz mapeia as dependências, contratos e falhas de acoplamento entre os componentes de `ingestion/`:

```
                    ┌─────────────────────────┐
                    │     orchestrator.py     │
                    │   (IngestionManager)    │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│    crawler.py    │  │    parser.py     │  │  summarizer.py   │
│ (ProjectCrawler) │  │   (FileParser)   │  │ (ZoomSummarizer) │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

| Arquivo Origem | Arquivo Destino | Tipo de Relação | Status / Incompatibilidade Identificada |
|---|---|---|---|
| [`orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | [`crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py) | Coordenação de Varredura | **Falha Crítica de Renomeação**: `crawler.crawl()` retorna `CrawlReport`. Se um arquivo foi renomeado, `crawler` o ignora por colisão de hash (**Achado #1**), mas adiciona o caminho antigo em `deleted_node_ids`. O orquestrador então purga o caminho antigo no Garbage Collector sem que o novo arquivo tenha sido ingerido. |
| [`orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | [`summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py) | Sumarização L0/L1/L2 | **Quebra de Contrato Dupla**: (1) `_step_summarize` chama `summarizer`, mas descarta a lista de retorno, fazendo `nodes.summary` ser gravado como `NULL` (**Achado #2**). (2) `orchestrator.generate_project_context` passa `folder_name` em vez de `uuid` para `summarizer.summarize_l2`, impedindo a persistência do L2 Compass (**Achado #3**). (3) Se `self._summarizer is None`, `_step_summarize` não tem early-exit e lança `AttributeError` (**Achado #5**). |
| [`orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | [`parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py) | Extração de Chunks | **Propagação de Chunks Quebrados**: `orchestrator` recebe os `ParsedChunk`s de `parser.py`. Chunks truncados por contagem ingênua de chaves (**Achado #8**) e tags poluídas por substring (**Achado #7**) são persistidos sem validação no banco de dados e na base vetorial. |
| [`crawler.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py) | [`parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py) | Tipos e Extensões | **Conflito de Regras de Ignore**: `crawler.py` ignora `*.txt` por padrão (**Achado #6**), impedindo que o `parser.py` (que possui lógica explícita para arquivos `_MD_EXTS = {..., '.txt'}`) processe documentações e manifestos de dependência. |
| [`summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py) | [`parser.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py) | Consumo de `ParsedChunk` | **Sensibilidade a Tamanho de Chunks**: `summarizer.py` depende de `chunk.estimated_tokens` para decidir se usa batch grouping (< 50 tokens) ou chamadas individuais. Se o parser trunca um chunk erroneamente (**Achado #8**), chunks artificiais pequenos são gerados em excesso. |

---

## 3. Matriz de Interação Transversal (Entre `ingestion/` e Outros Módulos)

| Módulo Externo | Componente de `ingestion/` | Ponto de Contato | Status / Impacto de Risco |
|---|---|---|---|
| [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | `cleanup_obsolete_nodes` e Bulk Insert | **Dessincronização com ChromaDB**: `cleanup_obsolete_nodes` remove nós antigos no SQLite em modificações de arquivo, mas o `orchestrator` não remove os vetores correspondentes no ChromaDB, gerando vetores zumbis permanentes (**Achado #4**). |
| [`storage/store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py) | [`ingestion/summarizer.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py) | `update_project(uuid, ...)` | **Incompatibilidade de Parâmetro**: `summarizer._persist_l2` passa `project_name` (`folder_name`) onde o SQLite espera `uuid`, falhando silenciosamente a gravação do resumo arquitetural global (**Achado #3**). |
| [`storage/vector_store.py`](file:///c:/Nexus-Memory/GrafoConcierge/storage/vector_store.py) | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | `vector_db.upsert()` e `verify_sync()` | **Dependência Cruzada de Formato**: `_step_embed_and_store_vectors` grava IDs no formato `node_{node_id}`. O GC do orquestrador só roda se houver deleção de arquivos no disco, deixando o Chroma poluído em meras modificações de arquivos. |
| [`core/vector_reconciler.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/vector_reconciler.py) | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | Reconciliação Periódica | O `VectorReconciler` foi desenhado para mitigar a assimetria SQLite-Chroma, mas possui bugs próprios já catalogados (`get_all_ids` inexistente e incompatibilidade de tipos `int` vs `str`). Assim, a falha do orquestrador em limpar vetores obsoletos no Step 7 (**Achado #4**) não é corrigida pelo reconciler. |
| [`core/database.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/database.py) | [`ingestion/orchestrator.py`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py) | Conexão SQLite / WAL | O orquestrador usa `store.write_callback`, que submete operações à fila serializada de `storage/connection.py`. Como auditado em `duplicacao-serialized-write-queue`, escritas pesadas de bulk insert da ingestão concorrem diretamente com leituras e escritas sem mutex de `core/database.py`. |

---

## 4. Detalhamento Técnico dos Achados e Prova Empírica

### Achado #1: Perda Total no Grafo na Renomeação de Arquivos (GC False Purge)
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivos:** [`ingestion/crawler.py:560`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L560), [`ingestion/crawler.py:690-708`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L690-L708), [`ingestion/orchestrator.py:765`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L765)
- **Mecanismo:** 
  No método `ProjectCrawler._scan_file`, a verificação de arquivo existente é feita invocando:
  ```python
  existing_node = self._store.find_node_by_hash(project_uuid, file_hash)
  ```
  O método `find_node_by_hash` consulta o SQLite buscando **apenas por `(project_uuid, file_hash)`**, sem levar em conta o `relative_path`.
  Quando um arquivo é renomeado no disco sem alteração no conteúdo textual (ex.: `mv a.py b.py`):
  1. O crawler calcula o hash de `b.py`, que é idêntico ao hash anterior de `a.py`;
  2. `find_node_by_hash` encontra o nó antigo correspondente a `a.py`;
  3. O crawler assume que o arquivo não mudou (`is_new = False`), adiciona `b.py` à lista `skipped_files` e **não o envia para parsing nem reingestão**;
  4. Em seguida, `ProjectCrawler._detect_deleted_nodes` compara os caminhos no banco contra os caminhos escaneados no disco. Como `a.py` não existe mais no disco, todos os nós de `a.py` são marcados como órfãos e adicionados em `report.deleted_node_ids`;
  5. No final do fluxo, `orchestrator.mine()` invoca `_step_garbage_collection`, que executa `_store.delete_node(node_id)` para cada ID em `deleted_node_ids`.
  **Resultado Catastrófico:** O nó de `a.py` é fisicamente purgado do banco de dados, e o novo arquivo `b.py` nunca é inserido. O arquivo simplesmente **desaparece completamente do Grafo Concierge** (0 nós). O mesmo bug afeta repositórios que possuem múltiplos arquivos com conteúdos idênticos (ex.: múltiplos `__init__.py` vazios): apenas o primeiro é ingerido; os demais colidem no hash e são descartados.
- **Reprodução Empírica:**
  ```
  1ª Ingestão: 2 nós criados: ['a.py::calculate_total', 'a.py::<module>']
  2ª Ingestão (após rename a.py -> b.py):
    files_processed: 0, files_skipped: 1, files_deleted: 2
    Nós sobreviventes no SQLite: []
    [CONFIRMADO ACHADO 1]: True — O arquivo renomeado b.py NÃO foi ingerido e o nó de a.py foi DELETADO pelo GC!
  ```

---

### Achado #2: Descarte Silencioso de 100% dos Resumos L0 (Tokens Gastos Desperdiçados)
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivos:** [`ingestion/orchestrator.py:191-201`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L191-L201), [`ingestion/orchestrator.py:571`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L571), [`ingestion/orchestrator.py:840-850`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L840-L850)
- **Mecanismo:**
  No método principal de ingestão `mine()` em `orchestrator.py`:
  ```python
  # Step 3: Summarization
  summaries = self._step_summarize(all_chunks, result)
  
  # Step 4: Storage SQLite
  self._step_store_sqlite(all_chunks, project_uuid, auto_tag, result)
  ```
  O método `_step_summarize` consome chamadas à API do LLM, gera instâncias de `SummaryResult` e as retorna na variável `summaries`. Porém:
  1. A variável `summaries` **nunca é repassada como argumento** para `_step_store_sqlite`;
  2. `_step_summarize` **não atualiza os objetos `ParsedChunk`** dentro da lista `all_chunks`;
  3. Dentro de `_step_store_sqlite` (linha 571), a inserção do nó no banco é executada lendo:
     ```python
     summary_text = chunk.cached_summary  # None para novos chunks!
     ```
  4. Como `cached_summary` só é preenchido pelo Delta Cache para chunks pré-existentes, todos os novos nós são inseridos no SQLite com `summary = NULL`;
  5. Mais grave: quando `generate_project_context` roda (linha 843), ele executa:
     ```python
     summary = node.get("summary")
     if not summary:
         continue
     ```
     Como 100% dos nós têm `summary is None`, o laço ignora todos os nós do projeto, encontrando zero L0s e abortando a geração dos níveis L1 e L2.
  **Impacto:** Consumo inútil de quota de tokens de LLM para gerar resumos que são imediatamente jogados no lixo da memória volátil, deixando o banco de dados desprovido de qualquer resumo semântico.
- **Reprodução Empírica:**
  ```
  Resumos reportados como gerados pelo IngestionResult: 2
  Chamadas ao LLM realizadas: 5
    Nó: math_utils.py::add | summary: None
    Nó: math_utils.py::<module> | summary: None
    [CONFIRMADO ACHADO 2]: True — O LLM gerou o resumo, mas nodes.summary no SQLite foi gravado como NULL!
  ```

---

### Achado #3: Falha Silenciosa de Persistência do L2 Compass (`folder_name` vs `uuid`) e Falsa Confirmação de Sucesso no Log
- **Severidade:** 🟠 **GRAVE**
- **Arquivos:** [`ingestion/summarizer.py:786-793`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/summarizer.py#L786-L793), [`ingestion/orchestrator.py:879-888`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L879-L888), [`storage/store.py:154`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L154)
- **Mecanismo:**
  Em `orchestrator.py`, a geração do Compass L2 é engatilhada por:
  ```python
  project = self._store.get_project(project_uuid)
  project_name = project.get("folder_name", project_uuid)
  l2 = self._summarizer.summarize_l2(l1_summaries, project_name)
  ```
  O orquestrador passa `project_name` (que é o `folder_name`, ex: `"ConciergeGraph"`) como identificador do projeto.
  Dentro de `summarizer.py`:
  ```python
  def _persist_l2(self, project_name: str, result: SummaryResult) -> None:
      """Writes the L2 Compass in the summary field of the project in SqliteStore."""
      try:
          self._store.update_project(project_name, summary=result.summary)
          logger.info("L2 Compass persisted for project %s.", project_name)
      except Exception as e:
          logger.error("Failed to persist L2 Compass for %s: %s", project_name, e)
  ```
  Porém, a assinatura de `SqliteStore.update_project` é:
  ```python
  def update_project(self, uuid: str, **fields: Any) -> None:
      conn.execute(f"UPDATE projects SET {sc} WHERE uuid = ?", vals)
  ```
  O `SqliteStore` espera estritamente o **UUID** do projeto na cláusula `WHERE uuid = ?`.
  Como recebe `project_name` (`"ConciergeGraph"` ou `"MeuProjetoNome"`), a cláusula `WHERE uuid = 'MeuProjetoNome'` não encontra nenhuma linha (`rowcount = 0`).

  > [!WARNING]
  > **Mecanismo de Falsa Confirmação de Sucesso no Log:**
  > O bloco `try/except` em `_persist_l2` **nunca captura essa falha**. No SQLite (e no driver `sqlite3` do Python), um comando `UPDATE` cuja cláusula `WHERE` não casa com nenhuma linha é considerado uma transação bem-sucedida que simplesmente afetou 0 linhas — **nenhuma exceção é lançada**.
  > Consequentemente, o fluxo nunca atinge o bloco `except Exception as e:`. Em vez disso, o código executa incondicionalmente a linha seguinte:
  > ```python
  > logger.info("L2 Compass persisted for project %s.", project_name)
  > ```
  > Isso é substancialmente mais perigoso do que uma falha silenciosa comum: trata-se de uma **falsa confirmação ativa de sucesso no log**. Desenvolvedores, operadores e sistemas de observabilidade veem no log que o resumo arquitetural L2 foi persistido com sucesso, enquanto no banco relacional a coluna `projects.summary` permanece `NULL` e o dado foi permanentemente perdido na memória volátil.

- **Impacto:** O resumo executivo de nível mais alto do sistema (L2 Compass) nunca é gravado no banco de dados, enquanto o log atesta falsamente que a operação teve sucesso pleno.
- **Reprodução Empírica:**
  ```
  L2 retornado pelo summarizer: Visao global do projeto de teste
  projects.summary no banco para uuid=proj-uuid-real-12345: None
    [CONFIRMADO ACHADO 3]: True — store.update_project('MeuProjetoNome') não atualizou a linha com uuid='proj-uuid-real-12345'!
  ```

---

### Achado #4: Acúmulo Perpétuo de Vetores Zumbis no ChromaDB em Modificações de Arquivo
- **Severidade:** 🟠 **GRAVE**
- **Arquivos:** [`ingestion/orchestrator.py:213`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L213), [`ingestion/orchestrator.py:234-239`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L234-L239), [`storage/store.py:368-385`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L368-L385)
- **Mecanismo:**
  Quando um arquivo é modificado no disco (por exemplo, funções removidas ou reestruturadas), o orquestrador executa:
  ```python
  self._store.cleanup_obsolete_nodes(project_uuid, valid_node_ids)
  ```
  Esse método limpa nós obsoletos **estritamente na base relacional SQLite**. Ele não tem acesso e nem notifica o `ChromaVectorStore`.
  O único ponto de reconciliação vetorial no orquestrador é o Step 7:
  ```python
  # Step 7: Garbage Collection (nodes + vectors)
  if crawl_report.deleted_node_ids:
      self._step_garbage_collection(...)
  ```
  Como o arquivo continuou existindo (apenas o seu conteúdo interno mudou), `crawl_report.deleted_node_ids` é uma lista vazia `[]`.
  Portanto, o Step 7 é completamente ignorado! Os embeddings dos nós e funções antigas que foram deletadas do SQLite permanecem na coleção do ChromaDB indefinidamente.
  **Impacto:** A busca híbrida vetorial retorna nós que já não existem no SQLite (ou com IDs obsoletos), degradando o recall semântico e gerando inconsistências graves no motor de busca.
- **Reprodução Empírica:**
  ```
  Versão 1: 3 nós no SQLite, 3 vetores no Chroma
  Versão 2 (arquivo modificado com remoção de função):
    Nós vivos no SQLite: 2 (IDs: [5, 6])
    Vetores no Chroma: 5
    Diferença (vetores zumbis sem nó correspondente no SQLite): 3
    [CONFIRMADO ACHADO 4]: True — Chroma manteve os vetores antigos de chunks obsoletos!
  ```

---

### Achado #5: Crash Interno com `AttributeError` em `_step_summarize` quando `self._summarizer is None`
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`ingestion/orchestrator.py:422`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L422), [`ingestion/orchestrator.py:442-452`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L442-L452)
- **Mecanismo:**
  No pipeline de sumarização em `orchestrator.py`:
  - Na Fase 2 (chunks pequenos), há verificação defensiva:
    ```python
    if small_chunks and self._summarizer:
    ```
  - Porém, na Fase 3 (chunks regulares), a checagem é feita sem validar a existência do summarizer:
    ```python
    if regular_chunks:
        ...
        async def _bounded_summarize(idx: int, chunk: ParsedChunk):
            async with sem:
                try:
                    s = await self._summarizer.summarize_l0_async(chunk)
    ```
  Se o `IngestionManager` for instanciado com `summarizer=None` (modo de ingestão rápida sem LLM), a corrotina tenta executar `self._summarizer.summarize_l0_async`, provocando `AttributeError: 'NoneType' object has no attribute 'summarize_l0_async'`.
  Esse erro é capturado pelo `except Exception as e:` interno da corrotina e anexado a `result.errors` para cada chunk individual. Em um repositório com 500 chunks, `result.errors` é inundado com 500 mensagens idênticas de falha interna.
- **Reprodução Empírica:**
  ```
  Erros registrados no result: ["Async L0 failed for test.py: 'NoneType' object has no attribute 'summarize_l0_async'"]
    [CONFIRMADO ACHADO 5]: True — Falha ao verificar self._summarizer is None causou AttributeError interno!
  ```

---

### Achado #6: Arquivos `.txt` Ignorados por Padrão sem `.gitignore` de Usuário
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`ingestion/crawler.py:395`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L395), [`ingestion/crawler.py:481`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/crawler.py#L481)
- **Mecanismo:**
  A constante `DEFAULT_IGNORE_PATTERNS` em `crawler.py:395` inclui:
  ```python
  DEFAULT_IGNORE_PATTERNS = [
      ".git", "node_modules", ..., "*.txt", ...
  ]
  ```
  Na Camada 1 do `GitignoreParser` (linha 481), esses padrões são carregados automaticamente como regras globais de exclusão.
  Isso faz com que qualquer arquivo com extensão `.txt` seja ignorado antes de chegar ao parser.
  Entretanto, na mesma pasta, o `crawler.py:365` define em `EXTENSION_MAP`:
  ```python
  ".txt": FileCategory.DOC,
  ```
  E o `parser.py:131` define explicitamente suporte para `.txt`:
  ```python
  _MD_EXTS = {".md", ".mdx", ".rst", ".adoc", ".txt"}
  ```
  Arquivos cruciais de projetos como `requirements.txt`, `license.txt`, `robots.txt` e notas de arquitetura em texto puro são silenciosamente omitidos da ingestão caso o projeto não forneça regras de un-ignore (`!*.txt`) no `.gitignore`.
- **Reprodução Empírica:**
  ```
  Arquivos escaneados pelo crawler em diretório contendo requirements.txt: []
    [CONFIRMADO ACHADO 6]: True — requirements.txt foi ignorado por padrão sem haver .gitignore!
  ```

---

### Achado #7: Poluição de Tags por Substring Ingênua (`reaction` -> `react`, `next()` -> `nextjs`)
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`ingestion/parser.py:100-111`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L100-L111), [`ingestion/parser.py:973-975`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L973-L975)
- **Mecanismo:**
  O método `FileParser._detect_tags` realiza a identificação automática de tecnologias através do loop:
  ```python
  for keyword, tag in _FRAMEWORK_KEYWORDS.items():
      if keyword in content_lower:
          tags.add(tag)
  ```
  O dicionário `_FRAMEWORK_KEYWORDS` mapeia, entre outros:
  - `"react": "react"`
  - `"next": "nextjs"`
  - `"torch": "pytorch"`
  A busca é realizada via operador `in` em strings completas de código sem qualquer delimitação de palavra (`\b` regex) ou tokenização léxica.
  Qualquer código Python que consuma um iterador via builtin `next(iter(x))` ou manipule eventos de reação (`handle_reaction`, `reaction_count`, `reactor`) recebe compulsoriamente as tags `'nextjs'` e `'react'`.
  **Impacto:** Poluição maciça dos metadados dos nós no banco relacional e vetorial. Consultas no dashboard ou buscas híbridas filtrando por tecnologias retornam funções e módulos puramente backend que nada têm a ver com os frameworks atribuídos.
- **Reprodução Empírica:**
  ```
  Código Python com 'reaction' e 'next()':
  Tags detectadas: ['nextjs', 'react']
    [CONFIRMADO ACHADO 7]: True — Código Python puro recebeu tags 'react' e 'nextjs'!
  ```

---

### Achado #8: Quebra de Chunking em JS/TS por Contador Ingênuo de Chaves em Strings/Comentários
- **Severidade:** 🟡 **MÉDIA**
- **Arquivos:** [`ingestion/parser.py:701-715`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/parser.py#L701-L715)
- **Mecanismo:**
  Para extrair o corpo de funções e classes em JavaScript/TypeScript, `parser.py` utiliza a função auxiliar `_find_block_end_braces`:
  ```python
  brace_count = 0
  for i in range(start_idx, len(lines)):
      line = lines[i]
      brace_count += line.count("{") - line.count("}")
      if brace_count == 0 and found_open:
          return i
  ```
  Essa lógica realiza uma contagem crua de caracteres `{` e `}` sem ignorar:
  - Strings literais com aspas simples (`'...'`), aspas duplas (`"..."`) ou crases template literals (`` `...` ``);
  - Expressões regulares (`/{/`);
  - Comentários de linha (`// }`) e bloco (`/* } */`).
  Se uma função contém uma string como `const html = "<div>}</div>";`, a chave fechando decrementa o contador `brace_count` para zero no meio da função. O parser encerra o chunk naquela linha, omitindo instruções cruciais e `return`s subsequentes.
  Adicionalmente, arrow functions sem bloco de chaves (ex.: `const add = (a, b) => a + b;`) têm `brace_count == 0` na primeira iteração e causam comportamentos indefinidos no delimitador.
- **Reprodução Empírica:**
  ```
  Chunks gerados para getTemplate com string contendo '}':
    - Chunk: getTemplate (function) linhas 1-2:
      Conteúdo: 'function getTemplate() {\n    const html = "<div class=\'container\'>}</div>";'
    - Chunk: secondFunction (function) linhas 6-9:
      Conteúdo: '\nfunction secondFunction() {\n    return 100;\n}'
    Função getTemplate foi truncada antes do return? True
    [CONFIRMADO ACHADO 8]: True — A chave dentro da string literal '}</div>' encerrou o bloco da função prematuramente!
  ```

---

## 5. Saída Bruta Completa da Reprodução Empírica

Abaixo transcreve-se a saída bruta gerada pela execução do script de verificação empírica [`scratch/reproduce_ingestion_findings.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_ingestion_findings.py):

```text
Garbage Collection: 2 orphan nodes detected in project test_rename_proj.
L0 grouped attempt 1/3: invalid response (2 chunks).
L0 grouped attempt 2/3: invalid response (2 chunks).
L0 grouped attempt 3/3: invalid response (2 chunks).
L0 grouped: all attempts failed for 2 chunks.
Async L0 failed for test.py: 'NoneType' object has no attribute 'summarize_l0_async'

======================================================================
TESTE ACHADO 1: Renomeação de arquivo causa perda total no grafo (GC False Purge)
======================================================================
1ª Ingestão: 2 nós criados: ['a.py::calculate_total', 'a.py::<module>']
2ª Ingestão (após rename a.py -> b.py):
  files_processed: 0, files_skipped: 1, files_deleted: 2
  Nós sobreviventes no SQLite: []
  [CONFIRMADO ACHADO 1]: True — O arquivo renomeado b.py NÃO foi ingerido e o nó de a.py foi DELETADO pelo GC!

======================================================================
TESTE ACHADO 2: Resumos L0 gerados pelo LLM são descartados e nodes.summary fica NULL
======================================================================
Resumos reportados como gerados pelo IngestionResult: 2
Chamadas ao LLM realizadas: 5
  Nó: math_utils.py::add | summary: None
  Nó: math_utils.py::<module> | summary: None
  [CONFIRMADO ACHADO 2]: True — O LLM gerou o resumo, mas nodes.summary no SQLite foi gravado como NULL!

======================================================================
TESTE ACHADO 3: Falha ao persistir L2 Compass por passar folder_name como UUID
======================================================================
L2 retornado pelo summarizer: Visao global do projeto de teste
projects.summary no banco para uuid=proj-uuid-real-12345: None
  [CONFIRMADO ACHADO 3]: True — store.update_project('MeuProjetoNome') não atualizou a linha com uuid='proj-uuid-real-12345'!

======================================================================
TESTE ACHADO 4: Vetores zumbis no ChromaDB após modificação de arquivo
======================================================================
Versão 1: 3 nós no SQLite, 3 vetores no Chroma
Versão 2:
  Nós vivos no SQLite: 2 (IDs: [5, 6])
  Vetores no Chroma: 5
  Diferença (vetores zumbis sem nó correspondente no SQLite): 3
  [CONFIRMADO ACHADO 4]: True — Chroma manteve os vetores antigos de chunks obsoletos!

======================================================================
TESTE ACHADO 5: AttributeError em _step_summarize quando self._summarizer is None
======================================================================
Erros registrados no result: ["Async L0 failed for test.py: 'NoneType' object has no attribute 'summarize_l0_async'"]
  [CONFIRMADO ACHADO 5]: True — Falha ao verificar self._summarizer is None causou AttributeError interno!

======================================================================
TESTE ACHADO 6: Arquivos .txt (ex: requirements.txt) ignorados por padrão
======================================================================
Arquivos escaneados pelo crawler: []
  [CONFIRMADO ACHADO 6]: True — requirements.txt foi ignorado por padrão sem haver .gitignore!

======================================================================
TESTE ACHADO 7: Poluição de tags por substring ingênua (reaction -> react, next() -> nextjs)
======================================================================
Código Python com 'reaction' e 'next()':
Tags detectadas: ['nextjs', 'react']
  [CONFIRMADO ACHADO 7]: True — Código Python puro recebeu tags 'react' e 'nextjs'!

======================================================================
TESTE ACHADO 8: Quebra de chunking em JS/TS por contador ingênuo de chaves
======================================================================
Chunks gerados para getTemplate com string contendo '}':
  - Chunk: getTemplate (function) linhas 1-2:
    Conteúdo: 'function getTemplate() {\n    const html = "<div class=\'container\'>}</div>";'
  - Chunk: secondFunction (function) linhas 6-9:
    Conteúdo: '\nfunction secondFunction() {\n    return 100;\n}'
  Função getTemplate foi truncada antes do return? True
  [CONFIRMADO ACHADO 8]: True — A chave dentro da string literal '}</div>' encerrou o bloco da função prematuramente!

======================================================================
RESUMO DOS ACHADOS: F1=True, F2=True, F3=True, F4=True, F5=True, F6=True, F7=True, F8=True
======================================================================
```

---

## 6. Testes Existentes Analisados e Falsos Positivos

Durante a auditoria, foram executadas e analisadas as suítes de teste de ingestão:
- `tests/test_multilang_parser.py`: Testa o parser com arquivos sintéticos bem-comportados. **Falso Positivo**: Não inclui casos de strings com chaves dentro de funções JS, encobrindo o Achado #8.
- `tests/test_ignore.py` e `tests/test_watcher_ignore.py`: Validam que arquivos em `.gitignore` são respeitados. **Omissão**: Não verificam que arquivos de texto legítimos (`requirements.txt`) são bloqueados por padrão pelos defaults do crawler (Achado #6).
- `tests/test_extraction_noop.py` e `tests/test_chunk_cache.py`: Focam na extração de nós quando nada muda no disco. Não testam renomeações sem alteração de conteúdo (Achado #1).
- `tests/test_e2e_concierge_integration.py`: Instancia os componentes em fluxo fim-a-fim, mas utiliza mocks simplificados para LLM e não inspeciona se a coluna `nodes.summary` no banco de dados SQLite foi preenchida ou se permaneceu `NULL` (Achado #2).

---

## 7. Recomendações para a Fase 3 (Backlog de Correção)

1. **Correção do Crawler e Renomeação (`crawler.py:560`)**:
   - Alterar `find_node_by_hash(project_uuid, file_hash)` para validar também o `relative_path`, ou implementar detecção explícita de `git mv`/rename antes de declarar um nó como órfão para o Garbage Collector.
2. **Atribuição e Persistência de Resumos L0 (`orchestrator.py:191, 571`)**:
   - Garantir que `_step_summarize` mapeie cada `SummaryResult` gerado de volta ao respectivo `ParsedChunk` (preenchendo `chunk.cached_summary = summary.summary`), para que `_step_store_sqlite` grave o texto real na coluna `summary` do SQLite.
3. **Correção do Contrato de Persistência L2 (`orchestrator.py:883` e `summarizer.py:789`)**:
   - Fazer `orchestrator.generate_project_context` passar o `project_uuid` (ou uma tupla `(project_uuid, project_name)`) para `summarizer.summarize_l2`, e fazer `_persist_l2` invocar `update_project(project_uuid, summary=...)`.
4. **Coordenação Bidirecional na Modificação de Arquivos (`orchestrator.py:213`)**:
   - Fazer `_store.cleanup_obsolete_nodes` retornar os IDs dos nós purgados do SQLite, e invocar imediatamente `vector_db.delete_batch([f"node_{nid}" for nid in obsolete_ids])`, evitando acúmulo de vetores zumbis.
5. **Early Exit em `_step_summarize` (`orchestrator.py:395`)**:
   - Inserir no topo de `_step_summarize`: `if not self._summarizer: return []`.
6. **Remoção de `*.txt` de `DEFAULT_IGNORE_PATTERNS` (`crawler.py:395`)**:
   - Remover `*.txt` da lista padrão de ignores, permitindo a ingestão de documentações e `requirements.txt`.
7. **Detecção de Tags com Fronteiras de Palavra (`parser.py:973`)**:
   - Substituir `keyword in content_lower` por verificação com regex `rf"\b{re.escape(keyword)}\b"`, eliminando falsos positivos como `reaction` -> `react`.
8. **Lexer Básico para Blocos JS/TS (`parser.py:701`)**:
   - Atualizar `_find_block_end_braces` para rastrear estado de aspas e comentários antes de incrementar/decrementar contadores de chaves.
