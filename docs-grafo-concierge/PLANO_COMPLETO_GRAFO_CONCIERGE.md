# Grafo Concierge — Plano Mestre v3.8 (Absolute Solidity)

## Visão Geral

| Item | Definição |
|------|----------|
| **Objetivo** | Substrato Cognitivo e Memória Infinita para Agentes Autônomos |
| **Base** | Concierge Core (sistema standalone — sem dependências externas) |
| **Armazenamento** | SQLite (grafo + metadados + FTS5) + Backend Vetorial Plugável (Stateless) |
| **Conectividade** | Servidor MCP nativo (Claude Desktop, Cursor, IDEs) |
| **Tokens no resumo** | 200-300 máx por projeto (com redução adicional via Engrenagem de Zoom e Amnésia Seletiva) |
| **Versão** | 3.8.0 (Absolute Solidity) |

---

## Motivação e Evolução Soberana

O Grafo Concierge não é apenas um acessório; ele é a **Infraestrutura de Memória Permanente (LTM)** onde a inteligência reside. Ele foi desenhado para **prover persistência de conhecimento, evolução semântica e soberania de dados para a inteligência**, tratando Módulos Operacionais apenas como clientes de execução.

> **Nota de Evolução (Skills & Engenharia Reversa)**: O Grafo suporta nativamente o armazenamento de **Skills** obtidas via Engenharia Reversa. Através do módulo de **Trajetórias Episódicas**, as skills obtidas são constantemente refinadas e corrigidas com base no histórico de falhas e sucessos, permitindo que o Agente aprenda de forma orgânica e atinja a soberania tecnológica.

Como Memória de Longo Prazo, a versão **Apex Sovereign** transcende sistemas de recuperação comuns com a injeção de 4 módulos de alta performance:

1. **Engrenagem de Zoom (Recursive Hierarchical Summarization)**: Resumos em pirâmide (L0: Arquivos, L1: Clusters, L2: Global) viabilizam uma busca Top-Down, evitando gargalos de informação e consumo excessivo de tokens.
2. **Ontologia de Memória Tipada (Typed DNA)**: O conteúdo possui tipagem estrita (FACT, SKILL, INSIGHT, TRAJECTORY, PATCH), permitindo filtros cirúrgicos na recuperação de contexto.
3. **Motor de Reflexão Dual (Background Janitor)**: Processos assíncronos que rodam enquanto o agente está ocioso para deduplicar, cruzar links e evoluir conversas soltas em fatos estruturados. Inclui o **Reconciliation Loop** para garantir sincronização absoluta entre o SQLite e o banco vetorial, e a heurística de **Idle-Lock** (o Janitor entra em suspensão imediata se houver atividade da IA para evitar contenção de I/O).
4. **Trajetórias Episódicas (Learning Loop)**: Uma 'biografia' de tentativas, falhas e correções passadas para que o agente nunca repita um erro já mapeado. Conta com o mecanismo de **Decaimento (Version-Binding)** para inativar trajetórias obsoletas.
5. **AST / Semantic Chunking**: Fatiamento inteligente do código baseado em abstrações lógicas (classes, funções) ou cabeçalhos Markdown, evitando quebras prejudiciais à semântica.

---

## Arquitetura do Concierge Core

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      CONCIERGE CORE v3.8 (Absolute Solidity)                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  storage/                     ← Camada de Retenção (Plugável)                │
│  ├── base_backend.py           (Interface abstrata para backends vetoriais)  │
│  ├── store.py                  (Fachada unificada — SqliteStore)             │
│  ├── connection.py             (Fila Serializada / Connection Pool)          │
│  ├── schema.py                 (DDL, CHECK constraints, FTS5 triggers)       │
│  ├── logic.py                  (Centralidade, Recência, Hybrid Search)       │
│  ├── chroma_backend.py         (Backend ChromaDB — padrão)                  │
│  ├── qdrant_backend.py         (Backend Qdrant — recomendado)               │
│  ├── pinecone_backend.py       (Backend Pinecone — opcional)               │
│  └── file_scanner.py           (Leitura + classificação + hashing + chunking)│
│                                                                              │
│  core/                         ← Cérebro do Agente                           │
│  ├── middleware.py              (Consultas recursivas SQL / Stateless)       │
│  ├── project_index.py           (GPS de Conhecimento / Alas)                │
│  ├── lazy_loader.py             (Recuperação on-demand de memórias)          │
│  ├── hybrid_search.py           (Motor de Busca Híbrida v4)                 │
│  └── config.py                  (Parâmetros de Retenção)                    │
│                                                                              │
│  agents/                       ← Guardiões da Inteligência                   │
│  ├── sumarizador.py             (Codificador de Memória)                    │
│  └── revisor_critico.py         (Auditor de Evolução + Reranking)           │
│                                                                              │
│  interface/                    ← Módulos de Execução (Ações)                 │
│  ├── mcp_server.py              (Servidor MCP — Porta de Entrada Soberana)  │
│  ├── action_hooks.py            (Integração com Módulos Operacionais)       │
│  ├── memory_commit.py           (Commit de Memória Soberana)                │
│  ├── context_loader.py          (Carregamento lazy de contexto)             │
│  └── cli.py                     (Interface de Controle LTM)                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Schema do Banco de Dados (SQLite)

> **Blindagem de Retenção de Longo Prazo (v3.4.0+)**: Para suportar a soberania e integridade da memória, a infraestrutura mantém as proteções de alta performance: `journal_mode=WAL` e `busy_timeout=5000`.

```sql
CREATE TABLE projects (
    uuid          TEXT PRIMARY KEY,
    folder_name   TEXT NOT NULL,
    primary_wing  TEXT NOT NULL DEFAULT 'geral',
    summary       TEXT,          -- Bússola de Contexto do Projeto
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE nodes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    label         TEXT NOT NULL,
    summary       TEXT,
    node_type     TEXT NOT NULL DEFAULT 'FACT', -- FACT, SKILL, INSIGHT, TRAJECTORY, PATCH
    type          TEXT NOT NULL DEFAULT 'file',
    tags          TEXT,          -- JSON array, ex: '["python","fastapi","jwt"]'
    file_hash     TEXT,          -- SHA256 do arquivo para delta updates
    last_accessed TEXT,
    last_commit_at TEXT          -- Recência super-rápida (atualizado no commit)
);

CREATE TABLE edges (
    source_id     INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id     INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL DEFAULT 'depends_on',
    weight        REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id)
);

CREATE TABLE reference_wings (
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    wing_name     TEXT NOT NULL,
    PRIMARY KEY (project_uuid, wing_name)
);

CREATE TABLE trajectories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid      TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    prompt_origem     TEXT NOT NULL,
    tentativa_execucao TEXT NOT NULL,
    erro_encontrado   TEXT,
    solucao_aplicada  TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE commit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    phase         TEXT NOT NULL,
    technical_changes TEXT NOT NULL,
    updated_pointers  TEXT NOT NULL,
    revisor_approved  INTEGER NOT NULL DEFAULT 0,
    partial_audit     INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_nodes_project ON nodes(project_uuid);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_refwings_project ON reference_wings(project_uuid);
CREATE INDEX idx_trajectories_project ON trajectories(project_uuid);
CREATE INDEX idx_commitlog_project ON commit_log(project_uuid);
CREATE INDEX idx_commitlog_date ON commit_log(created_at);

-- Tabela Virtual FTS5 para busca nativa de Frequência (BM25)
CREATE VIRTUAL TABLE nodes_fts USING fts5(label, tags, summary, content='nodes', content_rowid='id');

-- Triggers FTS5 (obrigatórios para sincronização)
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary) VALUES (new.id, new.label, new.tags, new.summary);
END;
CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary) VALUES('delete', old.id, old.label, old.tags, old.summary);
END;
CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary) VALUES('delete', old.id, old.label, old.tags, old.summary);
  INSERT INTO nodes_fts(rowid, label, tags, summary) VALUES (new.id, new.label, new.tags, new.summary);
END;
```

---

## Estrutura de Alas (Wings)

| Ala (Wing) | Descrição | Exemplos |
|-----------|-----------|---------|
| **Marketing/Vendas** | Marketing e vendas | Zero Riscos |
| **Finanças/Quant** | Financeiro e quantitativo | Robô de DayTrade |
| **Gestão/SaaS** | Gestão e SaaS | Mentor.IA |
| **Automação/RH** | Automação e RH | Excel Automation |
| **Estatística** | Estatística | Lotofácil |
| **Geral** | Outros | — |

**Alas Híbridas:**
- **Primary Wing**: Isolamento central. Strict Scoping restringe buscas a esta ala por padrão.
- **Reference Wings**: Arestas de consulta semântica — acessíveis com `include_references=True`.

---

## Equipe de Agentes

### Sumarizador

| Aspecto | Definição |
|---------|----------|
| **Papel** | Gera rascunho do resumo baseado no diff |
| **Output** | `draft` com `technical_changes`, `updated_pointers`, `summary_text` |

### Revisor Crítico

| Aspecto | Definição |
|---------|----------|
| **Papel 1** | Auditoria de commit (valida rascunho do Sumarizador, máx 3 loops) |
| **Papel 2** | Reranking de gavetas (filtra top-5 da busca híbrida por relevância técnica) |
| **Critérios** | Nomes de funções, dependências, relevância para tarefa atual |

---

## Motor de Busca Híbrida v4

### Sinais de Relevância

| Sinal | Peso | Fonte |
|-------|------|-------|
| **Similaridade Vetorial** | 0.50 | Backend plugável (ChromaDB / Qdrant / Pinecone) |
| **Frequência (BM25)** | 0.25 | Busca Nativa via SQLite FTS5 na Primary Wing |
| **Max(Recência, Centralidade)**| 0.25 | Recência (0-1) vs Centralidade (normalizada 0-1) |

### Strict Scoping

| Escopo | Parâmetro |
|--------|----------|
| Primary Wing apenas | Padrão |
| + Reference Wings | `include_references=True` |
| Todas as alas | `all_wings=True` |

### Fluxo

Query → Strict Scoping (Pré-filtro no Qdrant: list[project_uuid])
  → Backend Vetorial (Agregação: GROUP BY node_id, MAX(score))
  → Score Frequência (SQLite FTS5) → Max(Recência, Centralidade) → Combinação ponderada
  → Reranking pelo Revisor Crítico (top-5 → filtra ruído)
  → Resultado final
```

---

## Servidor MCP

O Concierge Core atua como servidor MCP, permitindo conexão nativa com Claude Desktop, Cursor e IDEs.

**Tools expostas:** `concierge_resume`, `concierge_load`, `concierge_commit`, `concierge_search`, `concierge_mine`, `concierge_wakeup`

**Configuração:**
```json
{
  "mcpServers": {
    "grafo-concierge": {
      "command": "python",
      "args": ["-m", "interface.mcp_server"]
    }
  }
}
```

---

## Backends Plugáveis

| Backend | Módulo | Uso |
|---------|--------|-----|
| **ChromaDB** (padrão) | `storage/chroma_backend.py` | Dev solo, local |
| **Qdrant** | `storage/qdrant_backend.py` | Local, operações de deleção eficientes |
| **Pinecone** | `storage/pinecone_backend.py` | Cloud, equipes |

class MyBackend(BaseVectorBackend):
    def store_embedding(self, doc_id: str, embedding: list[float], metadata: dict) -> None: 
        """
        Obrigatório no metadata: 
        - 'node_id': ID do nó no SQLite (para agrupar chunks)
        - 'project_uuid': UUID do projeto (para Strict Scoping)
        """
        ...

---

## Estrutura de Diretórios

```
grafo-concierge/
├── storage/
│   ├── __init__.py
│   ├── base_backend.py
│   ├── sqlite_store.py
│   ├── chroma_backend.py
│   ├── qdrant_backend.py
│   ├── pinecone_backend.py
│   └── file_scanner.py
│
├── core/
│   ├── __init__.py
│   ├── middleware.py
│   ├── project_index.py
│   ├── lazy_loader.py
│   ├── hybrid_search.py
│   └── config.py
│
├── agents/
│   ├── __init__.py
│   ├── sumarizador.py
│   └── revisor_critico.py
│
├── interface/
│   ├── __init__.py
│   ├── mcp_server.py
│   ├── action_hooks.py
│   ├── memory_commit.py
│   ├── context_loader.py
│   └── cli.py
│
├── tests/
│   ├── test_sqlite_store.py
│   ├── test_base_backend.py
│   ├── test_hybrid_search.py
│   ├── test_middleware.py
│   ├── test_project_index.py
│   ├── test_lazy_loader.py
│   ├── test_sumarizador.py
│   ├── test_revisor_critico.py
│   ├── test_action_hooks.py
│   ├── test_mcp_server.py
│   └── fixtures/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── OPERATIONAL_MODULES.md
│   ├── MIGRATION.md
│   └── ALA_CATEGORIES.md
│
├── requirements.txt
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

---

## Fases de Implementação

### Fase 1: Setup e Concierge Core Base
- [ ] Criar repositório standalone
- [ ] Criar `requirements.txt` (networkx, pyyaml, pytest, click, chromadb)
- [ ] Configurar `pyproject.toml`
- [ ] Implementar `storage/sqlite_store.py` com schema oficial (incluindo `commit_log`)
- [ ] Testar CRUD básico do SQLite

### Fase 2: Camada Core (Stateless) e Backends Plugáveis
- [ ] Criar `storage/base_backend.py` (interface abstrata)
- [ ] Implementar `storage/chroma_backend.py` (backend padrão)
- [ ] Criar `core/middleware.py` (Consultas Recursivas SQL / Stateless)
- [ ] Criar métodos: `get_resume()`, `lazy_load()`, `commit_memory()`
- [ ] Implementar `register_project()` com geração de `.concierge_id`

### Fase 3: Project Index, ID Persistente e Busca Híbrida
- [ ] Criar `core/project_index.py`
- [ ] Suporte a `.concierge_id` (UUID v4) como ID primário
- [ ] Implementar categorização Híbrida (Primary/Reference Wings)
- [ ] Implementar `core/hybrid_search.py` (vetorial + frequência + recência)
- [ ] Implementar Strict Scoping (filtro por Primary Wing)
- [ ] Implementar `delete_project` com modos total, parcial e custom

### Fase 3.5: Robustez e Concorrência (v3.8)
- [ ] Implementar Fila de Escrita Serializada (ou Connection Pool robusto) para acesso ao SQLite
- [ ] Mitigar concorrência pesada (Servidor MCP vs Background Janitor)
- [ ] Integrar Semantic/AST Chunking na leitura de arquivos, substituindo chunking ingênuo
- [ ] Implementar Refactoring de Identidade (Path-Agnostic Node ID via Hash Tracking)

### Fase 4: Equipe de Agentes e Módulos Operacionais
- [ ] Implementar `agents/sumarizador.py` com Escudo de Sanitização (Prompt Armor via XML)
- [ ] Implementar `agents/revisor_critico.py` (auditoria de commit + reranking de gavetas em `on_build/on_done`)
- [ ] Implementar Barreira de Contaminação (Privacy Levels) no Auditor de Evolução
- [ ] Implementar o `Background Janitor` com rotina de Reconciliation Loop (Sincronização Absoluta)
- [ ] Implementar Poda por Relevância (Amnésia Seletiva L2) no Janitor
- [ ] Implementar Decaimento de Trajetórias (Stale/Archived) baseado no delta de arquivos
- [ ] Criar `interface/action_hooks.py`
- [ ] Implementar triggers: `on_planning()`, `on_build()`, `on_done()`
- [ ] Implementar `concierge mine` com Semantic/AST Chunking em substituição a cortes fixos
- [ ] Otimização FTS5: Rebuild manual via `INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');` para grandes cargas.
- [ ] Implementar `concierge wake-up` (pré-carga: Bússola + Reference Wings + últimos commits)
- [ ] Testar integração com orchestrator

### Fase 5: Conectividade e Performance
- [ ] Implementar `interface/mcp_server.py` (servidor MCP via stdio/SSE)
- [ ] Configurar tools, resources e prompts MCP
- [ ] Testar conexão com Claude Desktop e Cursor
- [ ] Implementar Reranking Heurístico de Latência Zero (Cross-Encoder) para MCP `search`
- [ ] Implementar backends opcionais (Qdrant, Pinecone)
- [ ] Benchmark de performance da Busca Híbrida v4

### Fase 6: Extensões e Polimento
- [ ] Suporte a ingestão de PDFs e Docs no `concierge mine`
- [ ] Suporte a ingestão de conversas (logs de chat)
- [ ] Implementar `interface/cli.py` com todos os comandos
- [ ] Testes unitários e de integração completos
- [ ] Documentação final e README
- [ ] Publicação no PyPI

---

## Fluxo de Dados v3.0 (Diagrama Final)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                    FLUXO DE DADOS v3.8 — ABSOLUTE SOLIDITY                   │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │  CLIENTES                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │   │
│  │  │ Claude       │  │ Cursor       │  │ CLI          │  │ Agente   │  │   │
│  │  │ Desktop      │  │ IDE          │  │              │  │ Executor │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  │   │
│  │         │ MCP              │ MCP              │ API           │ API    │   │
│  └─────────┼──────────────────┼──────────────────┼──────────────┼────────┘   │
│            └──────────────────┴──────────────────┴──────────────┘            │
│                                    ↓                                          │
│  ┌─── INTERFACE LAYER ──────────────────────────────────────────────────────┐ │
│  │  mcp_server.py / action_hooks.py / cli.py                               │ │
│  │  Tools: resume, load, commit, search, mine, wakeup                      │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                          │
│  ┌─── CORE LAYER ──────────────────────────────────────────────────────────┐ │
│  │                                                                          │ │
│  │  ┌── wake_up ──┐  ┌── on_planning ──┐  ┌───── on_build ─────────────┐  │ │
│  │  │ Bússola     │  │ Bússola (300t)  │  │ Hybrid Search v4           │  │ │
│  │  │ Ref Wings   │  │ Readonly        │  │ ┌─ Vetorial (0.50) ──────┐ │  │ │
│  │  │ Commits     │  │                 │  │ │ Frequência FTS5 (0.25) │ │  │ │
│  │  └─────────────┘  └─────────────────┘  │ │ Max(Rec/Cent) (0.25)   │ │  │ │
│  │                                         │ └───────────────────────┘ │  │ │
│  │                                         │ Strict Scoping            │  │ │
│  │                                         │ Reranking (Revisor top-5) │  │ │
│  │                                         │ → lazy_load()             │  │ │
│  │                                         └───────────────────────────┘  │ │
│  │                                                                          │ │
│  │  ┌── mine ─────────────────┐  ┌── on_done ────────────────────────────┐ │ │
│  │  │ Hash Check → Chunking  │  │ Sumarizador → Revisor (3 loops)      │ │ │
│  │  │ Embed (Qdrant = N)     │  │ → commit (cria arestas + last_commit) │ │ │
│  │  │ Index Básico (SQLite=1)│  └────────────────────────────────────────┘ │ │
│  │  │ → Garbage Collection   │                                             │ │
│  │  └────────────────────────┘                                             │ │
│  │                                                                          │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                          │
│  ┌─── STORAGE LAYER ───────────────────────────────────────────────────────┐ │
│  │  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐ │ │
│  │  │ SQLite         │  │ Backend Vetorial     │  │ Consultas SQL (Mem) │ │ │
│  │  │ • projects     │  │ ┌─────────────────┐  │  │ Recursivas (CTE)    │ │ │
│  │  │ • nodes (hash) │  │ │ ChromaDB (def.) │  │  │                     │ │ │
│  │  │ • edges        │  │ │ Qdrant (opt.)   │  │  │                     │ │ │
│  │  │ • ref_wings    │  │ │ Pinecone (opt.) │  │  │                     │ │ │
│  │  │ • commit_log   │  │ └─────────────────┘  │  │                     │ │ │
│  │  └────────────────┘  └─────────────────────┘  └──────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## API Principal

```python
class GrafoConcierge:
    def register_project(self, project_path, wing="geral") -> str: ...
    def get_resume(self, project_id, max_tokens=300) -> str: ...
    def lazy_load(self, drawer_path) -> dict: ...
    def hybrid_search(self, query, project_id, include_references=False, top_k=10) -> list: ...
    def commit_memory(self, project_id, outcome) -> None: ...  # Requer campos auditados
    def mine(self, project_id, source_path, auto_tag=True) -> dict: ...
    def wake_up(self, project_id) -> dict: ...
    def delete_project(self, project_id, mode="parcial", targets=None) -> None: ...
    def find_similar_projects(self, project_id, limit=5) -> list: ...
```

---

## Tokens por Fase

| Fase (Ação) | Dados | Objetivo LTM |
|------------|-------|--------------|
| **Wake-up** | Bússola + Ref Wings + commits | Re-ativação de consciência |
| **Planning** | Bússola (readonly) | Orientação Estratégica |
| **Execution** | Memória filtrada (Reranking) | Integração de Conhecimento |
| **Mine** | Ingestão Soberana | Expansão de Conhecimento |
| **Review/Done** | Commit de memória | Consolidação de LTM |

---

## Dependências

```txt
# requirements.txt (MVP)
networkx>=3.0
pyyaml>=6.0
pytest>=7.0
click>=8.0
chromadb>=0.4.0

# Opcionais
# qdrant-client>=1.7.0
# pinecone-client>=3.0
```

---

## Sustentabilidade e Tiering de Modelos

Para evitar explosões de custos operacionais (token burn) com os recursos avançados da versão Apex, o Grafo Concierge dita uma política severa de **Model Tiering**:

- **Modelos Leves/Rápidos (Ex: Gemini 2.0 Flash, Claude Haiku, Llama 3 local)**: Devem ser utilizados massivamente para as rotinas de Ingestão (`concierge mine`), sumarização L0-L1-L2 e pelas rotinas assíncronas do **Background Janitor**.
- **Modelos de Alta Performance (Ex: Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro)**: Exclusivamente preservados para a **Execução Final**, Raciocínio Complexo e Refatoração Ativa guiados pelos Módulos Operacionais.

---

## Configuração

```python
class ConciergeConfig:
    MAX_RESUME_TOKENS = 300
    MAX_COMMIT_TOKENS = 100
    MAX_REVISOR_LOOPS = 3
    VECTOR_BACKEND = "chroma"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Local, 384 dims (alt: text-embedding-3-small)
    EMBEDDING_DIMENSIONS = 384
    HYBRID_WEIGHTS = {"vetorial": 0.50, "frequencia": 0.25, "recencia": 0.25}
    BM25_K1 = 1.5
    BM25_B = 0.75
    BM25_FIELDS = ["label", "tags", "summary"]
    RECENCY_HALF_LIFE_DAYS = 7
    RECENCY_LAMBDA = 0.0990              # ln(2)/7
    RECENCY_MIN_SCORE = 0.01
    DEFAULT_SCOPE = "primary_wing"
    WING_KEYWORDS = { ... }
    IGNORE_DIRS = [".git", "node_modules", ".next", "dist", "build"]
```

---

## Licença

MIT License — see LICENSE file.

---

**Versão**: 3.8.0 (Absolute Solidity)
**Data**: 2026-05-03
**Autor**: LuisinTheLegend