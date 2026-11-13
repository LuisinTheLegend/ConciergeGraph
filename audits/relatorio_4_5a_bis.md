# Relatório da Rodada 4.5a-bis — Retificação do Inventário (Somente Texto)

- **Data:** 2026-11-12
- **Base verificada:** HEAD `60f24aecd3d189c1564d40143c9c7ff188a8ffde` (`git rev-parse HEAD` == `git ls-remote origin main`)
- **Natureza:** Mini-rodada exclusivamente documental (`audits/` e `scratch/`). Zero alterações em código de produto, testes, CI, `pyproject.toml`, `README*` ou `grafo-dashboard-web/`. Arquivos não rastreados em `audits/egm/` permaneceram intactos fora do commit.
- **Regra 12 / Regra 14:** Relatório gerado mecanicamente por `scratch/build_4_5a_bis_docs.py` a partir das saídas brutas em `scratch/evidencia_4_5a_bis/`.

---

## Bloco 1 — Retificação sobre `agent*` / `agents` e Empacotamento Real

### 1.1 Reprodução Independente (`scratch/inv_4_5a_bis_bloco1.py`)

- **Leitura direta de `pyproject.toml` (`[tool.setuptools.packages.find]`, `pyproject.toml:96-111`):** `include = ['core*', 'storage*', 'ingestion*', 'services*', 'interface*', 'agent*', 'scripts*']`, `exclude = ['tests*', 'data*', 'docs*', '.git*']`, `py-modules = ['main']` (`fato`).
- **`setuptools.find_packages(...)` (Setuptools `84.2.1`):** retornou `['agent', 'agents', 'core', 'ingestion', 'interface', 'services', 'storage', 'core.parsers']` (`fato`). Como `include` aplica globbing `fnmatch`, o padrão `"agent*"` (`pyproject.toml:103`) casa tanto com `agent` quanto com `agents`.
- **Construção real de wheel em diretório temporário (`setuptools.build_meta.build_wheel`):** sucesso=`True`, arquivo `concierge_graph-3.8.2-py3-none-any.whl` (**70 entradas**) (`fato`).
  - Diretórios/arquivos no topo do `.whl`: `['agent', 'agents', 'concierge_graph-3.8.2.dist-info', 'core', 'ingestion', 'interface', 'main.py', 'scripts', 'services', 'storage']`.
  - Presença explícita no `.whl`: `agents/__init__.py`, `agents/revisor_critico.py` (e também `scripts/bootstrap_core_memory.py`).
  - Evidência bruta: `scratch/evidencia_4_5a_bis/bloco1_packaging.txt`.

### 1.2 Varredura de Ocorrências e Retificações Aplicadas

- Varredura por `agents*`, `não é empacotado` e `omite` em `audits/`, `scratch/evidencia_4_5a/` e scripts `scratch/inv_4_5a*.py` / `scratch/build_4_5a*.py` (`scratch/evidencia_4_5a_bis/bloco1_grep_audit.txt`):
  - **3 ocorrências do erro nos documentos `.md` corrigidas no lugar + registradas em `Errata 4.5a-bis`:**
    1. `audits/relatorio_4_5a.md:15` (atualizado para refletir `pyproject.toml:103` `agent*` e inclusão real de `agents`, além de adicionada a seção datada `## Errata 4.5a-bis (2026-11-12)` no início).
    2. `audits/inventario_4_5a.md:131` (tabela do Bloco 3, linha `pyproject.toml`).
    3. `audits/inventario_4_5a.md:171` (Bloco 4.3 `Empacotamento em pyproject.toml`).
  - **Artefatos brutos de evidência (`scratch/evidencia_4_5a/`):** **0 ocorrências** desse erro encontradas (`bloco1_grep_audit.txt`); nenhuma evidência bruta foi editada.
  - **`audits/fase4-roadmap.md`:** **0 ocorrências** desse erro.
  - **Script histórico `scratch/build_4_5a_docs.py:416, 489, 567`:** preservado intocado como registro histórico da 4.5a (anotado explicitamente na errata de `audits/relatorio_4_5a.md`).
  - Demais ocorrências de `omite` em `audits/grafo-dashboard-web.md:53` e `audits/storage.md:27` são achados técnicos antigos não relacionados a empacotamento.

### 1.3 Efeito Factual sobre a 4.5b se `agents/` ou `interface/` Mudarem de Lugar (Sem Recomendação)

- `archive*` não consta em `[tool.setuptools.packages.find].include` (`pyproject.toml:97-105`); por isso, mover qualquer pacote/módulo de `agents/`, `agent/`, `core/`, `interface/` ou `storage/` para `archive/v4-experimental/` remove automaticamente esses arquivos do `.whl`/sdist construído (`fato`).
- Enquanto `agents/` permanecer na raiz com `agent*` em `include`, `agents/__init__.py` e `agents/revisor_critico.py` continuam empacotados na distribuição padrão (`fato`).
- Em `interface/`, os arquivos vivos (`interface/__init__.py`, `interface/mcp_server.py`, `interface/cli.py`, entrypoint `concierge = "interface.cli:main"` em `pyproject.toml:87`) permanecem no pacote; se apenas submódulos específicos (`telemetry_api.py`, `watcher.py`, `action_hooks.py`, `queue_writer.py`) saírem de `interface/`, eles deixam o `.whl`. Caso `interface/action_hooks.py` ou `agents/` sejam movidos sem ajuste em `interface/__init__.py:20-25` ou `tests/test_governor_wiring.py:100-105` (`T5`), o lazy export `interface.ActionHooks` passará a falhar com `ModuleNotFoundError`/`ImportError` (`fato`).

---

## Bloco 2 — Classificação dos 4 Módulos "Alcançáveis, mas Não Carregados"

- **Definição proposta de Classe `(iv)` — Opt-in / lazy, não carregado por desenho no runtime MCP (`fato`):** módulos que possuem caminho estático no grafo AST a partir das raízes (`interface/__init__.py:20-25` via PEP 562 `__getattr__`, ou `core/hybrid_search.py:252` condicionado a `enable_probabilistic=True`), mas que ficam propositalmente fora de `sys.modules` durante o boot e execução padrão do servidor MCP/CLI. Diferenciam-se de `(i)` (sem caminho vivo de entrada), `(ii)` (duplicata superada) e `(iii)` (promessa sem código ou sem ligação viva).
- **Método de busca por acionadores vivos (`scratch/inv_4_5a_bis_bloco2_3.py`):** varredura AST + regex nos **38 arquivos `.py` de produção** (`main.py`, `agent/`, `agents/`, `core/`, `ingestion/`, `interface/`, `services/`, `storage/`, `scripts/`) procurando referências a `agents`, `RevisorCritico`, `revisor_critico`, `ActionHooks`, `action_hooks`, `ThompsonRetriever`, `probabilistic_retriever`, `enable_probabilistic`, `_apply_thompson_sampling` e flags `GRAFO_*` (`bloco2_3_probe.txt:1-46`): **`env_flags_prob_or_hooks = 0` — nenhum acionador vivo encontrado**.

| Módulo (LOC) | Como é carregado (`arquivo:linha`) | Acionador vivo em produção (`arquivo:linha`) | Testes (`arquivo:linha` e contagem) | Promessas públicas e status vivo | Classe proposta (`fato`) |
|---|---|---|---:|---|---|
| `agents` (`14L`, `agents/__init__.py`) | Indiretamente ao importar `agents.revisor_critico`: `interface/__init__.py:20-25` → `interface/action_hooks.py:32` → `agents/__init__.py:10` | **Nenhum acionador vivo encontrado** (AST/regex em produção + `scripts/` e flags `GRAFO_*`) | `0` imports diretos em `tests/`; asserção negativa em `tests/test_governor_wiring.py:21-32` (`test_t1_...` exige ausência em `mcp_server`) | `README.md:6,106` (menção arquitetural genérica), `pyproject.toml:11` (descrição genérica); `docs-grafo-concierge/01_ARCHITECTURE.md:3,32,337`. Inativo no MCP. | **Classe `(iv)`** (lazy PEP 562 por cadeia) / candidata D0 `(i)` se contrato `ActionHooks` for suspenso |
| `agents.revisor_critico` (`610L`, `agents/revisor_critico.py`) | Importado por `agents/__init__.py:10` e `interface/action_hooks.py:32`; só carregado se `interface.ActionHooks` for acessado via `interface/__init__.py:20-25` | **Nenhum acionador vivo encontrado** | `tests/test_revisor_critico.py:9` (`11T`: 9 dormente, 2 usa `core.config`), `tests/colossus_benchmark.py` (`0T`), `tests/stress_test_v2_setup.py` (`0T`), ref. negativa `tests/test_governor_wiring.py:21-32` | `docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md:95` (cita caminho legado `core/critical_revisor.py`). Desacoplado do servidor desde 4.2. | **Classe `(iv)`** / candidata D0 `(i)` se contrato `ActionHooks` for suspenso |
| `interface.action_hooks` (`261L`, `interface/action_hooks.py`) | PEP 562 `__getattr__` em `interface/__init__.py:20-25` (`from interface import ActionHooks`) | **Nenhum acionador vivo encontrado** | `tests/test_interface_contracts.py:20,116-175` (`22T`: 17 mistos, 5 só-vivos), `tests/stress_test_v2_setup.py` (`0T`), `tests/test_governor_wiring.py:100-105` (`test_t5_action_hooks_lazy_export_preserves_contract` dentro de `5T`) | `0` menções em `README*` e `docs-grafo-concierge/`; apenas docstrings internas (`core/middleware.py:13`, `interface/__init__.py:6`). Inativo no MCP/CLI. | **Classe `(iv)`** (opt-in por contrato Python externo testado por `T5`) / candidata D0 `(i)` se contrato for suspenso |
| `core.probabilistic_retriever` (`108L`, `core/probabilistic_retriever.py`) | Import tardio dentro de `HybridSearchEngine._apply_thompson_sampling` (`core/hybrid_search.py:252`), condicionado a `enable_probabilistic=True` (`L215`) | **Nenhum acionador vivo encontrado**: default `enable_probabilistic: bool = False` (`core/hybrid_search.py:86`); `core/middleware.py:264`, `interface/mcp_server.py:1142` e `interface/cli.py` não passam `True`; `0` env vars `GRAFO_*` | `tests/test_probabilistic_retriever.py:15` (`3T`: `test_update_memory_utility` L32-53 só-vivo + 2 testes de `ThompsonRetriever` L60-149) | Prometido ativamente em `README.md:40,74,171`, `README.pt-BR.md:40,74,171`, `docs-grafo-concierge/01_ARCHITECTURE.md:20,78,351-352`, `02_MCP_TOOLS_REFERENCE.md:248`, `03_COGNITIVE_MEMORY_AND_FACTS.md:141-159`. `concierge_feedback` grava α/β em SQLite, mas a busca viva nunca amostra. | **Classe `(iv)` pura** (+ lacuna `(iii)` operacional na doc pública) |

- **Total atualizado de módulos candidatos para decisão na 4.5b (`audits/inventario_4_5a.md`, Seção 2.2):** **`28 + 1 + 4 = 33` módulos (`5.603` linhas)** de `63` totais (`19.800` linhas): `28` `UNREACHABLE` (`4.306L`) + `1` `ANNOTATION_ONLY_RUNTIME` (`interface.queue_writer`, `304L`) + `4` `Classe (iv)` (`993L`).

---

## Bloco 3 — Reconciliação das Contagens de Testes e Matriz Unificada

### 3.1 Reconciliação Exata (`26 / 197` vs. `21 / 160`)

- **Coleta oficial atual (`pytest --collect-only -q`):** **478 testes** distribuídos em **67 arquivos `.py`** sob `tests/`.
- **Medição do auditor (`21 arquivos / 160 testes`):** corresponde ao conjunto dos **28 módulos `UNREACHABLE`** **excluindo `tests/test_watcher_ignore.py`** (21 arquivos / 160 testes — `fato`).
- **Inclusão de `tests/test_watcher_ignore.py` (`4` testes, carga por `importlib.util.spec_from_file_location("interface.watcher", ...)` em `tests/test_watcher_ignore.py:21-25`):** eleva o recorte dos **28 `UNREACHABLE`** para **22 arquivos / 164 testes** (`fato`).
- **Diferença até `26 arquivos / 197 testes` (4.5a):** exatamente os **4 arquivos (33 testes)** que importam **somente** módulos PEP 562 de Classe `(iv)` (`agents.revisor_critico` / `interface.action_hooks`), sem importar nenhum dos 28 `UNREACHABLE`:
  1. `tests/colossus_benchmark.py` (`0` testes; importa `agents.revisor_critico`)
  2. `tests/stress_test_v2_setup.py` (`0` testes; importa `agents.revisor_critico`, `interface.action_hooks`)
  3. `tests/test_interface_contracts.py` (`22` testes; importa `interface.action_hooks`)
  4. `tests/test_revisor_critico.py` (`11` testes; importa `agents.revisor_critico`)
  *(Verificação aritmética: `21 + 1 + 4 = 26 arquivos`; `160 + 4 + 33 = 197 testes`.)*
- **Efeito de incluir `core.probabilistic_retriever` (4.º módulo de Classe `(iv)`):** adiciona `tests/test_probabilistic_retriever.py` (**`3` testes**, sendo 1 só-vivo e 2 dormentes), elevando para **`27 arquivos / 200 testes`** (excl. `queue_writer`-only), ou **`33 arquivos / 228 testes`** incluindo os **`6 arquivos / 28 testes`** exclusivos de `interface.queue_writer` (`test_agent_checkpointer.py` [4], `test_concurrency_stress.py` [2], `test_graph_rag_loops.py` [3], `test_mcp_server_extensions.py` [3], `test_queue_writer_batching.py` [2], `test_queue_writer_resilience.py` [14]).

### 3.2 Tabela Resumo Unificada (`(i)` vs. `(i) + (ii)/(iii) + (iv)`)

- **Significado de `misto` e limite superior:** cada linha soma o total de testes coletados por **arquivo inteiro**. Um arquivo é `misto` quando importa pelo menos um módulo do recorte e pelo menos um módulo vivo (ou contém testes separados por tipo). Se o módulo dormente for movido sem atualizar o import no topo do arquivo, todos os testes do arquivo quebram na coleta/execução (limite superior).
- Nota de granularidade: `test_adaptive_gating.py` (`13`), `test_multilang_parser.py` (`8`) e `test_watcher_ignore.py` (`4`) são `só-dormente` reais (`test_watcher_ignore.py:29` importa `interface` apenas para registrar `sys.modules['interface'].watcher` exigido por `tests/conftest.py`); em sentido inverso, `tests/test_vector_reconciler.py` (`2`) tem funções aparentemente só-vivas por AST, mas instancia `self.search_engine`/`self.reconciler` dormentes no `setUp`.

| Categoria (arquivo inteiro; limite superior) | Recorte `(i)` estrito *(14 `UNREACHABLE` D0)* | Recorte `28 UNREACHABLE` *(i + ii/iii inalc.)* | Recorte `(i) + (ii)/(iii) + (iv)` *(32 mód., excl. QW)* |
|---|---:|---:|---:|
| **`só-dormente`** | `4 arquivos / 28 testes` | `7 arquivos / 50 testes` | `7 arquivos / 50 testes` |
| **`misto`** *(contém funções mistas e/ou só-vivas preserváveis)* | `11 arquivos / 101 testes` | `15 arquivos / 114 testes` | `20 arquivos / 150 testes` |
| **`só-queue_writer`** *(exclusivo `interface.queue_writer` entre os 33)* | `6 arquivos / 28 testes` | `6 arquivos / 28 testes` | `6 arquivos / 28 testes` |
| **`só-vivo`** *(restante não afetado pelo recorte)* | `46 arquivos / 321 testes` | `39 arquivos / 286 testes` | `34 arquivos / 250 testes` |
| **Total (`pytest --collect-only -q`)** | **`67 arquivos / 478 testes`** | **`67 arquivos / 478 testes`** | **`67 arquivos / 478 testes`** |

---

## Bloco 4 — Limites do Traço sob `GRAFO_LIGHTWEIGHT_MODE=true` e `ChromaDB unavailable`

- **Cobertura das 31 ferramentas MCP sob o traço da 4.5a:** todas as 31 ferramentas responderam ao traço síncrono com `GRAFO_LIGHTWEIGHT_MODE=true` + chaves fake + ausência de `chromadb` (`CHROMADB_AVAILABLE = False` em `storage/vector_store.py:34-36`), onde `EmbeddingManager` retorna `None` (`storage/vector_store.py:148`) e `ChromaVectorStore` atua como NO-OP (`storage/vector_store.py:297-308`, incluindo `logger.warning("reset_collection ignored: ChromaDB unavailable.")` em `storage/vector_store.py:653`).
- **6 / 31 ferramentas com caminhos de código não exercitados sem embeddings/vetores reais (`fato`):**
  1. `concierge_mine` (`interface/mcp_server.py:325-340` → `core/middleware.py:213-233` → `ingestion/orchestrator.py:787-843`): fallback sem vetores (`embeddings_stored=0, embeddings_failed=4`); `SentenceTransformer.encode(...)` (`storage/vector_store.py:202, 242`) e upsert real em coleção não executaram.
  2. `concierge_search` (`interface/mcp_server.py:352-377` → `core/middleware.py:239-271` → `core/hybrid_search.py:140-212`): `query_embedding is None` acionou `_fts_only_fallback` (`core/hybrid_search.py:141-144, 272-308`), não exercitando `self._vector.search(...)` (`L147`) nem merge de `vector_scores` (`L157-180`).
  3. `concierge_store_fact` (`interface/mcp_server.py:587-602` → `core/middleware.py:512-592`): além de LLM real no extrator, o ramo `if isinstance(self._vector, QdrantVectorStore)` + `self._embedder.embed` + `self._vector.store_embedding` (`core/middleware.py:567-588`) não rodou (backend era `ChromaVectorStore`).
  4. `delete_project` (`interface/mcp_server.py:740-746` → `core/middleware.py:389-410`): `self._vector.delete_batch(doc_ids)` (`core/middleware.py:403`) foi NO-OP.
  5. `count_embeddings` (`interface/mcp_server.py:843-849` → `core/middleware.py:745-754`): `self._vector.count(project_uuid)` (`core/middleware.py:754`) retornou `0` em NO-OP (`bloco1_runtime_trace.txt:36`).
  6. `reset_collection` (`interface/mcp_server.py:859-861` → `core/middleware.py:756-767`): `self._vector.reset_collection()` (`core/middleware.py:764`) caiu no guard `storage/vector_store.py:653` (`reset_collection ignored: ChromaDB unavailable.`) retornando `{'success': False}`, sem destruir/recriar a coleção (`L656-668`).
- **Risco de carga tardia de módulos dormentes exclusivamente nesses caminhos (`fato`):** a inspeção AST de **todos os 66 imports indentados/condicionais nos 26 arquivos vivos** (`scratch/evidencia_4_5a_bis/bloco4_probe.txt:89-155`) prova que **nenhum** dos 28 `UNREACHABLE`, `interface.queue_writer`, `agents`, `agents.revisor_critico` ou `interface.action_hooks` é importado dentro desses fluxos. Os únicos imports tardios ligados a vetor/embedding são dependências externas opcionais (`sentence_transformers` em `storage/vector_store.py:158`, `openai` em `storage/vector_store.py:175` e `ingestion/summarizer.py:313,366`, `qdrant_client` em `core/vector_backend.py:21-22`, `google.genai` em `ingestion/summarizer.py:279,291`) e `core/vector_backend.py` (`core/middleware.py:566`, já carregado no traço). O único import tardio de módulo Classe `(iv)` nos caminhos vivos (`core/hybrid_search.py:252`, `ThompsonRetriever`) depende exclusivamente da flag opt-in `enable_probabilistic=True` (`L86, 215`), nunca ativada pelos chamadores vivos.
- Conteúdo completo também incorporado em `audits/relatorio_4_5a.md` (Seção 3).
