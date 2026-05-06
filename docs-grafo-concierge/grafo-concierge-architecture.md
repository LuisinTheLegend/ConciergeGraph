# Grafo Concierge — Arquitetura de Memória Permanente (LTM) v3.8.0

## Visão Geral

| Item | Definição |
|------|----------|
| **Objetivo** | Substrato Cognitivo e Memória Infinita para Agentes Autônomos |
| **Base** | Concierge Core (sistema standalone — sem dependências externas) |
| **Armazenamento** | SQLite (grafo + metadados + arestas, FTS5) [Fila Serializada] + Backend Vetorial Plugável |
| **Conectividade** | Servidor MCP nativo (Claude Desktop, Cursor, IDEs) |
| **Tokens no resumo** | 200-300 máx por projeto (L2 Global) |
| **Versão** | 3.8.0 (Absolute Solidity) |

---

## Motivação e Evolução Soberana

O Grafo Concierge não é apenas um acessório; ele é a **Infraestrutura de Memória Permanente (LTM)** onde a inteligência reside. Ele foi desenhado para **prover persistência de conhecimento, evolução semântica e soberania de dados para a inteligência**, tratando Módulos Operacionais apenas como clientes de execução.

Como Memória de Longo Prazo, o Grafo resolve os desafios cognitivos através de:

1. **Substrato Cognitivo** — IA acessa o "mapa mental" do conhecimento (200-300 tokens)
2. **Retenção de Longo Prazo** — Persistência absoluta via hashing e blindagem técnica v3.4
3. **Evolução Semântica** — Identificar e integrar padrões de código entre projetos
4. **Busca Híbrida v4** — Recuperação precisa de conhecimento antigo e novo
5. **Soberania MCP** — O Agente vive no grafo e o consulta através de qualquer interface (Claude, Cursor, IDEs)

---

## Arquitetura do Concierge Core

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  CONCIERGE CORE v3.8 (Absolute Solidity)                     │
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
│  └── file_scanner.py           (Leitura + hash check + AST/Semantic Chunking)│
│                                                                              │
│  core/                         ← Cérebro do Agente                           │
│  ├── middleware.py              (Consultas recursivas SQL / Stateless)       │
│  ├── project_index.py           (GPS de Conhecimento / Alas)                │
│  ├── lazy_loader.py             (Recuperação on-demand de memórias)          │
│  ├── hybrid_search.py           (Busca Híbrida v4 — Top-Down / Zoom Gear)   │
│  └── config.py                  (Parâmetros de Retenção)                    │
│                                                                              │
│  agents/                       ← Guardiões da Inteligência                   │
│  ├── sumarizador.py             (Resumos em Pirâmide + Escudo de Sanitização)│
│  ├── revisor_critico.py         (Auditoria + Reranking LLM via hooks)        │
│  ├── background_janitor.py      (Deduplicação, Sincronização + Amnésia Sel.) │
│                                                                              │
│  interface/                    ← Módulos de Execução (Ações)                 │
│  ├── mcp_server.py              (Servidor MCP — Porta de Entrada Soberana)  │
│  ├── action_hooks.py            (Skills e Módulos Operacionais)             │
│  ├── memory_commit.py           (Commit de Memória Soberana)                │
│  ├── context_loader.py          (Carregamento lazy de contexto)             │
│  └── cli.py                     (Interface de Controle LTM)                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Servidor MCP (Model Context Protocol)

O Concierge Core atua como um **servidor MCP** nativo, permitindo que qualquer cliente MCP (Claude Desktop, Cursor, IDEs com suporte) se conecte diretamente ao grafo de memória.

### Especificação (`interface/mcp_server.py`)

| Aspecto | Definição |
|---------|----------|
| **Protocolo** | Model Context Protocol (MCP) via stdio ou SSE |
| **Tools expostas** | `concierge_resume`, `concierge_load`, `concierge_commit`, `concierge_search`, `concierge_mine`, `concierge_wakeup` |
| **Resources** | Lista de projetos registrados, alas disponíveis, status do grafo |
| **Prompts** | Template da Bússola de Contexto, template de commit auditado |

### Tools MCP

```json
{
  "tools": [
    {
      "name": "concierge_resume",
      "description": "Retorna a Bússola de Contexto do projeto (200-300 tokens)",
      "parameters": {
        "project_id": "string (UUID)",
        "max_tokens": "integer (default: 300)"
      }
    },
    {
      "name": "concierge_load",
      "description": "Carrega uma gaveta específica on-demand",
      "parameters": {
        "drawer_path": "string (uuid/pasta/arquivo)"
      }
    },
    {
      "name": "concierge_commit",
      "description": "Registra resultado no grafo (campos auditados obrigatórios)",
      "parameters": {
        "project_id": "string (UUID)",
        "technical_changes": "string",
        "updated_pointers": "array[string]",
        "revisor_approved": "boolean"
      }
    },
    {
      "name": "concierge_search",
      "description": "Busca Híbrida v4 com Strict Scoping",
      "parameters": {
        "query": "string",
        "project_id": "string (UUID)",
        "node_type": "string (FACT, SKILL, INSIGHT, TRAJECTORY, PATCH)",
        "include_references": "boolean (default: false)"
      }
    },
    {
      "name": "concierge_register",
      "description": "Registra um novo projeto e define Nível de Privacidade",
      "parameters": {
        "project_path": "string",
        "wing": "string",
        "privacy_level": "string (PUBLIC, INTERNAL, RESTRICTED)"
      }
    },
    {
      "name": "concierge_mine",
      "description": "Ingestão inteligente — scan, hash check, chunking e garbage collection",
      "parameters": {
        "project_id": "string (UUID)",
        "source_path": "string"
      }
    },
    {
      "name": "concierge_wakeup",
      "description": "Pré-carrega Bússola + Reference Wings para sessão",
      "parameters": {
        "project_id": "string (UUID)"
      }
    }
  ]
}
```

### Configuração do Cliente

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "grafo-concierge": {
      "command": "python",
      "args": ["-m", "interface.mcp_server"],
      "env": {
        "CONCIERGE_DATA_DIR": "~/.grafo-concierge"
      }
    }
  }
}
```

---

## Backends Plugáveis (`storage/base_backend.py`)

O sistema permite trocar o backend vetorial sem alterar a lógica do grafo, graças a uma camada de abstração.

### Interface Abstrata

```python
# storage/base_backend.py
from abc import ABC, abstractmethod

class BaseVectorBackend(ABC):
    """Interface abstrata para backends vetoriais plugáveis."""

    @abstractmethod
    def store_embedding(self, doc_id: str, embedding: list[float], metadata: dict) -> None:
        """
        Armazena um embedding com metadados.
        Metadata obrigatório: 'node_id' (int) e 'project_uuid' (str).
        """
        ...

    @abstractmethod
    def search(self, query_embedding: list[float], project_uuids: list[str], top_k: int = 10, filters: dict = None) -> list[dict]:
        """Busca por similaridade vetorial com pré-filtro por lista de projetos."""
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove um embedding."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica se o backend está operacional."""
        ...
```

### Backends Disponíveis

| Backend | Módulo | Uso recomendado | Dependência |
|---------|--------|----------------|------------|
| **ChromaDB** (padrão) | `storage/chroma_backend.py` | Projetos locais, dev solo | `chromadb>=0.4.0` |
| **Qdrant** | `storage/qdrant_backend.py` | Local, permite exclusão nativa (CRUD) | `qdrant-client>=1.7.0` |
| **Pinecone** | `storage/pinecone_backend.py` | Produção cloud, equipes distribuídas | `pinecone-client>=3.0` |

### Configuração

```python
# core/config.py
class ConciergeConfig:
    # Backend vetorial (troque aqui para mudar o storage)
    VECTOR_BACKEND = "chroma"  # "chroma" | "qdrant" | "pinecone"

    # Configurações específicas por backend
    CHROMA_SETTINGS = {"persist_dir": "~/.grafo-concierge/chroma"}
    QDRANT_SETTINGS = {"url": "http://localhost:6333"}
    PINECONE_SETTINGS = {"api_key": "...", "environment": "us-east-1"}
```

---

## Motor de Busca Híbrida v4 (`core/hybrid_search.py`)

O motor combina **três sinais** para resultados de alta precisão:

### Sinais de Relevância

| Sinal | Peso Padrão | Descrição |
|-------|------------|-----------|
| **Similaridade Vetorial** | 0.50 | Cosine similarity entre embeddings (via backend plugável) |
| **Frequência (FTS5)** | 0.25 | Busca nativa no SQLite (BM25 em C) sobre a Primary Wing atual |
| **Max(Recência, Centralidade)**| 0.25 | Protege código "Core" estável através de sua centralidade (arestas de entrada), penalizando apenas código solto e desatualizado |

### Fórmula de Score

```
score_final = (w_vetorial × sim_vetorial)
            + (w_frequencia × score_fts5_normalizado)
            + (w_recencia × max(score_recencia, score_centralidade))
```

> **Nota de Normalização (v3.4)**:
> - **Centralidade**: O in-degree deve ser normalizado `min(in_degree / 10, 1.0)`.
> - **Frequência**: O score BM25 do FTS5 deve ser normalizado no intervalo `[0, 1]` antes da combinação.

### Score de Frequência — SQLite FTS5 (Resolvido C2)

O score de frequência é calculado nativamente pelo banco de dados utilizando a extensão **FTS5** sobre a tabela virtual `nodes_fts`. Ele processa a matemática do BM25 em velocidade C sem carregar a base para a RAM do Python:

| Parâmetro | Valor Padrão | Descrição |
|-----------|-------------|-----------|
| `k1` | 1.5 | Saturação de frequência de termos |
| `b` | 0.75 | Normalização pelo tamanho do documento |
| `campos` | `label`, `tags` | Campos indexados para BM25 |
| `corpus` | Nós da Primary Wing | Escopo do cálculo |

### Score de Recência — Decaimento Exponencial (P3 Resolvido)

O score de recência usa **decaimento exponencial** baseado na tabela `commit_log`:

```
score_recencia = e^(-λ × t)
onde λ = ln(2) / 7 ≈ 0.0990
      t = dias desde o último commit que referencia o nó
```

| Parâmetro | Valor | Descrição |
|-----------|------|-----------|
| **Meia-vida** | 7 dias | Após 7 dias, score de recência original = 0.50 |
| **Fonte** | `commit_log.created_at` | Timestamp do último commit que referencia o nó |
| **Centralidade** | in-degree | Número de arquivos que dependem deste (target_id em edges) |
| **Score mínimo** | 0.01 | Nós muito antigos nunca são zerados |

### Strict Scoping (Filtro Físico)

As buscas são **fisicamente restritas** à Primary Wing do projeto, a menos que o parâmetro `include_references=True` seja passado explicitamente.

```python
# Busca na Primary Wing apenas (padrão)
results = gc.hybrid_search("autenticação JWT", project_id=uuid)

# Busca incluindo Reference Wings
results = gc.hybrid_search("autenticação JWT", project_id=uuid, include_references=True)

# Busca global (todas as alas — requer permissão explícita)
results = gc.hybrid_search("autenticação JWT", project_id=uuid, all_wings=True)
```

### Fluxo da Busca (Top-Down via Engrenagem de Zoom)

```
Query do usuário + Filtro Cirúrgico (ex: node_type='INSIGHT')
       ↓
  Strict Scoping (Filtro por project_uuid no Backend Vetorial)
       ↓
  Avaliação L2 (Resumo Global da Ala/Projeto)
       ↓
  Avaliação L1 (Resumos de Cluster — localiza a vizinhança correta)
       ↓
  Busca L0 (Backend Vetorial + FTS5 nativo SQLite em arquivos atômicos)
       ↓
  Score de Recência vs Centralidade (preserva código core)
       ↓
  Combinação ponderada → Score Final
       ↓
  Reranking pelo Auditor de Evolução (top-5 → filtra relevantes)
       ↓
  Resultado final para a IA
```

---

## Schema do Banco de Dados (SQLite)

> **Nota Crítica de Produção (v3.7)**: Para evitar o erro `database is locked` sob carga concorrente (MCP Server vs Janitor), a conexão DEVE utilizar:
> - `PRAGMA journal_mode=WAL;`
> - `PRAGMA busy_timeout=5000;`
> - **Acesso Serializado**: Uma Fila de Escrita Serializada em memória ou um Connection Pool robusto garantindo transações atômicas seguras.

```sql
CREATE TABLE projects (
    uuid          TEXT PRIMARY KEY,
    folder_name   TEXT NOT NULL,
    primary_wing  TEXT NOT NULL DEFAULT 'geral',
    privacy_level TEXT NOT NULL DEFAULT 'PUBLIC', -- PUBLIC, INTERNAL, RESTRICTED
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
    file_hash     TEXT,          -- SHA256 para delta updates (evita re-processamento)
    last_accessed TEXT,          -- Para cache L1
    last_commit_at TEXT          -- Recência instantânea (atualizado no commit_memory)
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

-- NOVO v3.6: Learning Loop / Biografia de Falhas e Sucessos
CREATE TABLE trajectories (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid      TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    prompt_origem     TEXT NOT NULL,
    tentativa_execucao TEXT NOT NULL,
    erro_encontrado   TEXT,
    solucao_aplicada  TEXT,
    status            TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, STALE, ARCHIVED
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Log de commits para cálculo de recência
CREATE TABLE commit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid  TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
    phase         TEXT NOT NULL,
    technical_changes TEXT NOT NULL,
    updated_pointers  TEXT NOT NULL,  -- JSON array
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

-- Tabela Virtual para Busca Nativa (FTS5)
CREATE VIRTUAL TABLE nodes_fts USING fts5(label, tags, summary, content='nodes', content_rowid='id');

-- Triggers de Sincronização do FTS5
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

| Ala (Wing) | Descrição | Exemplos de Projetos |
|-----------|-----------|---------------------|
| **Marketing/Vendas** | Projetos de marketing e vendas | Zero Riscos |
| **Finanças/Quant** | Projetos financeiros e quantitativos | Robô de DayTrade |
| **Gestão/SaaS** | Projetos de gestão e SaaS | Mentor.IA |
| **Automação/RH** | Automação e recursos humanos | Excel Automation |
| **Estatística** | Projetos estatísticos | Lotofácil |
| **Geral** | Projetos que não se encaixam em alas específicas | — |

**Alas Híbridas:**
- **Primary Wing**: Ala principal — isolamento central. O Strict Scoping restringe buscas a esta ala por padrão.
- **Reference Wings**: Arestas de consulta semântica — acessíveis apenas via `include_references=True`.

### Identificação de Projetos

- **ID Persistente (Primário)**: Arquivo `.concierge_id` contendo UUID v4 na raiz do projeto.
- **Ala (Wing)**: Categoria automática + override manual (Primary e Reference Wings).

---

## Equipe de Agentes — Especificação

### Sumarizador (`agents/sumarizador.py`)

| Aspecto | Definição |
|---------|----------|
| **Papel** | Gera o rascunho do resumo de memória baseado no diff da tarefa |
| **Input** | `task_description` (str), `outcome` (dict) |
| **Output** | `draft` (dict com `technical_changes`, `updated_pointers`, `summary_text`) |
| **Regra** | Deve conter nomes de funções alteradas e novas dependências |

### Revisor Crítico (`agents/revisor_critico.py`)

| Aspecto | Definição |
|---------|----------|
| **Papel 1 — Auditoria de Commit** | Valida rascunhos do Sumarizador antes do commit |
| **Papel 2 — Barreira de Contaminação**| Valida se as Reference Wings não violam os `privacy_levels` do projeto |
| **Papel 3 — Reranking de Gavetas** | Em `on_build/on_done` (pesado), usa LLM para filtrar top-5 |
| **Critérios de commit** | Nomes de funções, dependências, lista de pointers |
| **Critérios de reranking** | Relevância técnica para a tarefa atual (elimina ruído) |
| **Se rejeitar commit** | Volta ao Sumarizador (máx 3 loops) |
| **Limite de loops** | 3 tentativas → fallback `partial_audit=True` |

### Fluxo do Reranking (Novo v3.0)

```
IA solicita gaveta (on_build)
       ↓
  Hybrid Search v4 → top-10 candidatos
       ↓
  Revisor Crítico analisa top-5
       ↓
  Filtra por relevância técnica para a tarefa
       ↓
  Retorna apenas gavetas relevantes (reduz ruído e tokens)
```

---

## Formato Oficial do Resumo (Bússola de Contexto)

```
Projeto: <nome> | UUID: <uuid_curto>
Ala: <primary_wing> | Ref: [<ref_wing_1>, ...]
Tech: <tech_1>, <tech_2>, ...
Fase Atual: <phase>
Última Sessão: <data>
Resumo: <descrição concisa do estado atual e últimas alterações>
Pointers: <arquivo_1>, <arquivo_2>, ...
```

---

## Estrutura de Diretórios

```
grafo-concierge/
├── .git/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
│
├── storage/
│   ├── __init__.py
│   ├── base_backend.py          ← Interface abstrata (plugável)
│   ├── sqlite_store.py          ← Schema + CRUD do SQLite (FTS5)
│   ├── chroma_backend.py        ← Backend ChromaDB (padrão)
│   ├── qdrant_backend.py        ← Backend Qdrant (recomendado)
│   ├── pinecone_backend.py      ← Backend Pinecone (opcional)
│   └── file_scanner.py          ← Leitura, Hash Check e AST/Semantic Chunking
│
├── core/
│   ├── __init__.py
│   ├── middleware.py            ← Consultas Recursivas SQL / Stateless
│   ├── project_index.py
│   ├── lazy_loader.py
│   ├── hybrid_search.py         ← Motor de Busca Híbrida v4
│   └── config.py
│
├── agents/
│   ├── __init__.py
│   ├── sumarizador.py
│   └── revisor_critico.py       ← Auditoria + Reranking
│
├── interface/
│   ├── __init__.py
│   ├── mcp_server.py            ← Interface Soberana
│   ├── action_hooks.py          ← Skills e Módulos Operacionais
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
│       ├── sample_projects/
│       └── sample_graph.json
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    ├── OPERATIONAL_MODULES.md
    ├── MIGRATION.md
    └── ALA_CATEGORIES.md
```

---

## Fases de Implementação

### Fase 1: Setup e Concierge Core Base
- [ ] Criar repositório standalone
- [ ] Criar `requirements.txt` com dependências
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

### Fase 4: Guardiões e Módulos Operacionais
- [ ] Implementar `agents/sumarizador.py` (Codificador de Memória)
- [ ] Implementar `agents/revisor_critico.py` (Auditor de Evolução + Reranking)
- [ ] Implementar `agents/background_janitor.py` com Reconciliation Loop e **Heurística de Idle-Lock** (suspende imediatamente operações de banco se houver requisição MCP ativa)
- [ ] Criar `interface/action_hooks.py`
- [ ] Implementar triggers: `on_planning()`, `on_build()`, `on_done()`
- [ ] Implementar `concierge mine` (ingestão com hashing e chunking 512t)
- [ ] Implementar `concierge wake-up` (pré-carga de sessão)
- [ ] Testar integração com Agente Executor

### Fase 5: Conectividade e Performance
- [ ] Implementar `interface/mcp_server.py` (servidor MCP)
- [ ] Configurar tools, resources e prompts MCP
- [ ] Testar conexão com Claude Desktop e Cursor
- [ ] Otimizar Reranking do Revisor Crítico para latência baixa
- [ ] Implementar backends opcionais (Qdrant, Pinecone)

### Fase 6: Extensões e Polimento
- [ ] Suporte a ingestão de PDFs/Docs no `concierge mine`
- [ ] Implementar `interface/cli.py` com todos os comandos
- [ ] Testes unitários e de integração completos
- [ ] Documentação final e README

---

## Módulos Operacionais (Skills) — Fluxo de Dados v3.5

```
┌───────────────────────────────────────────────────────────────────────────┐
│                   FLUXO DE DADOS v3.5 — AGENTE SOBERANO + LTM             │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─── ENTRADA ──────────────────────────────────────────────────────────┐ │
│  │ Cliente (Claude Desktop / Cursor / CLI / Agente Executor)            │ │
│  │                        ↓ MCP / API                                   │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── FASE: WAKE-UP ───────────────────────────────────────────────────┐ │
│  │ concierge wake-up → Lê .concierge_id (UUID)                         │ │
│  │ → Pré-carrega Bússola de Contexto (200-300 tokens)                  │ │
│  │ → Pré-carrega Reference Wings no contexto                           │ │
│  │ → IA pronta para trabalhar (zero setup manual)                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── FASE: PLANNING ─────────────────────────────────────────────────┐ │
│  │ on_planning(project_id)                                             │ │
│  │ → Retorna Bússola de Contexto (readonly)                            │ │
│  │ → IA usa como Compasso                                              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── FASE: BUILD ────────────────────────────────────────────────────┐ │
│  │ on_build(project_id, need)                                          │ │
│  │ → Hybrid Search v4 (vetorial + frequência + recência)               │ │
│  │ → Strict Scoping (Primary Wing / include_references)                │ │
│  │ → Reranking pelo Revisor Crítico (top-5 → filtra ruído)            │ │
│  │ → lazy_load() da gaveta mais relevante                              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── FASE: INGESTÃO (sob demanda) ───────────────────────────────────┐ │
│  │ concierge mine --project <UUID> --source <path>                     │ │
│  │ → File Scanner faz Chunking (512t) e Hash Check (Delta)             │ │
│  │ → Indexa no backend vetorial + cria nós no grafo SQLite             │ │
│  │ → Arestas são geradas iterativamente apenas no commit_memory        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── FASE: REVIEW/DONE ─────────────────────────────────────────────┐ │
│  │ on_done(project_id, outcome)                                        │ │
│  │ → Sumarizador gera rascunho (diff da tarefa)                        │ │
│  │ → Revisor Crítico audita (máx 3 loops)                              │ │
│  │ → commit_memory (technical_changes, updated_pointers, approved)     │ │
│  │ → Grava no commit_log (recência para Hybrid Search)                 │ │
│  │ → Atualiza arestas do grafo                                         │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                            ↓                                              │
│  ┌─── STORAGE ─────────────────────────────────────────────────────────┐ │
│  │  SQLite (grafo + metadados + commit_log + FTS5)                     │ │
│  │  Backend Vetorial (ChromaDB / Qdrant / Pinecone)                    │ │
│  │  Estado Stateless (Consultas recursivas SQL em tempo real)          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### Resumo de Tokens por Fase

| Fase | Dados Carregados | Tokens Estimados |
|------|-----------------|-----------------|
| **Wake-up** | Bússola + Reference Wings | 300-500 |
| **Planning** | Resumo (Bússola) | 200-300 |
| **Build** | Gaveta filtrada (Reranking) | Variável (reduzido pelo Revisor) |
| **Mine** | Ingestão — sem custo de token para a IA | 0 |
| **Review/Done** | Commit de memória | 50-100 |

---

## Especificações Técnicas

### Dependências

```txt
# requirements.txt (MVP)
networkx>=3.0
pyyaml>=6.0
pytest>=7.0
click>=8.0
chromadb>=0.4.0

# Opcionais (backends alternativos)
# qdrant-client>=1.7.0
# pinecone-client>=3.0
```

> **Nota:** SQLite é nativo do Python. O MCP server usa o protocolo padrão via stdio.

### Configuração

```python
# core/config.py
class ConciergeConfig:
    MAX_RESUME_TOKENS = 300
    MAX_COMMIT_TOKENS = 100
    MAX_REVISOR_LOOPS = 3

    # Backend vetorial plugável
    VECTOR_BACKEND = "chroma"  # "chroma" | "qdrant" | "pinecone"

    # Modelo de Embedding
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Local, gratuito, 384 dims
    # Alternativa: "text-embedding-3-small" (OpenAI API, 1536 dims)
    EMBEDDING_DIMENSIONS = 384

    # Pesos da Busca Híbrida v4
    HYBRID_WEIGHTS = {
        "vetorial": 0.50,
        "frequencia": 0.25,
        "recencia": 0.25
    }

    # BM25 (Score de Frequência)
    BM25_K1 = 1.5
    BM25_B = 0.75
    BM25_FIELDS = ["label", "tags"]

    # Recência (Decaimento Exponencial)
    RECENCY_HALF_LIFE_DAYS = 7         # Meia-vida: 7 dias
    RECENCY_LAMBDA = 0.0990            # ln(2)/7
    RECENCY_MIN_SCORE = 0.01           # Score mínimo (nunca zera)

    # Strict Scoping
    DEFAULT_SCOPE = "primary_wing"  # "primary_wing" | "with_references" | "all"

    # Categorização de Alas
    WING_KEYWORDS = {
        "marketing/vendas": ["marketing", "venda", "copy", "conversão"],
        "finanças/quant": ["finança", "quant", "trade", "investimento"],
        "gestão/saas": ["saas", "dashboard", "gestão", "erp"],
        "automação/rh": ["automação", "rh", "excel", "planilha"],
        "estatística": ["estatística", "análise", "dados", "média"]
    }

    IGNORE_DIRS = [".git", "node_modules", ".next", "dist", "build"]
```

---

## Contribuindo

1. Fork o repositório
2. Crie uma branch `feature/`
3. Faça suas alterações
4. Adicione testes
5. Envie um Pull Request

---

## Licença

MIT License — see LICENSE file.

---

## Consultas Recursivas (v3.4)

Para garantir estabilidade em grafos complexos ou com dependências circulares, todas as consultas `WITH RECURSIVE` devem implementar um limite de profundidade.

```sql
WITH RECURSIVE graph_path(id, label, depth) AS (
    SELECT id, label, 0 FROM nodes WHERE id = ?
    UNION ALL
    SELECT n.id, n.label, gp.depth + 1
    FROM nodes n
    JOIN edges e ON n.id = e.target_id
    JOIN graph_path gp ON e.source_id = gp.id
    WHERE gp.depth < 10
)
SELECT * FROM graph_path;
```

---

**Versão**: 3.6.0 (Apex Sovereign)
**Data**: 2026-05-03
**Autor**: LuisinTheLegend