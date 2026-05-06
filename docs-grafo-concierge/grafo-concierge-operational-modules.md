# Módulos Operacionais (Skills) — Grafo Concierge v3.8.0 (Absolute Solidity)

## Visão Geral

Este documento explica como integrar Módulos Operacionais com o Grafo Concierge v3.8.0 (Absolute Solidity), tratando a execução como uma "Skill" operada pela Memória Permanente.

---

## Arquitetura de Integração

```
┌───────────────────────────────────────────────────────────────────────────┐
│               AGENTE SOBERANO + LTM v3.8                                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Agente Soberano (Cérebro / Consciência)                                  │
│       ↓ MCP / API Direta                                                  │
│                                                                           │
│  ┌─── WAKE-UP ────────────────────────────────────────────────────────┐  │
│  │ gc.wake_up(project_id)                                              │  │
│  │ → Pré-carrega Bússola + Reference Wings + últimos commits           │  │
│  │ → Re-ativação de consciência (zero setup manual)                    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                         ↓                                                  │
│  ┌─── PLANNING ───────────────────────────────────────────────────────┐  │
│  │ hooks.on_planning(project_id)                                       │  │
│  │ → Consulta Resumo L2 (Visão Global)                                 │  │
│  │ → Consulta Trajetórias Episódicas (Biografias de Erros Anteriores)  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                         ↓                                                  │
│  ┌─── EXECUTION (Módulo Operacional / Skill) ─────────────────────────┐  │
│  │ → Hybrid Search v4 (Zoom Gear: Top-Down L2 -> L1 -> L0)             │  │
│  │ → Filtros Cirúrgicos por `node_type` (FACT, SKILL, INSIGHT)         │  │
│  │ → Strict Scoping (Primary Wing / include_references)                │  │
│  │ → Reranking pelo Auditor de Evolução (top-5 → filtra relevantes)    │  │
│  │ → lazy_load() da memória necessária                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                         ↓                                                  │
│  ┌─── REVIEW/DONE ────────────────────────────────────────────────────┐  │
│  │ hooks.on_done(project_id, outcome)                                  │  │
│  │ → Sumarizador gera rascunho → Auditor revisa (máx 3 loops)          │  │
│  │ → commit_memory → Consolidação LTM (alimenta recência da busca)     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Configuração

### 1. Instalação

```bash
git clone https://github.com/seu-usuario/grafo-concierge.git
cd grafo-concierge
pip install -e .
```

### 2. Configuração do Agente Executor

```python
from core.middleware import GrafoConcierge
from interface.action_hooks import ActionGrafoHooks

gc = GrafoConcierge(vector_backend="chroma")
hooks = ActionGrafoHooks(gc)
```

### 3. Configuração MCP (Claude Desktop / Cursor)

```json
{
  "mcpServers": {
    "grafo-concierge": {
      "command": "python",
      "args": ["-m", "interface.mcp_server"],
      "env": {
        "CONCIERGE_DATA_DIR": "~/.grafo-concierge",
        "SQLITE_WAL_MODE": "true" 
      }
    }
  }
}
```

---

## Trigger: Wake-up (Novo v3.3)

### O que acontece

1. IA ou usuário inicia sessão de trabalho
2. `gc.wake_up(project_id)` é chamado
3. Sistema pré-carrega a Bússola de Contexto do projeto ativo
4. Sistema pré-carrega os resumos das Reference Wings
5. Sistema carrega os últimos 3 commits (recência)
6. Agente Soberano está consciente — zero setup manual

### Código

```python
def start_session(project_id: str):
    # Wake-up elimina o setup manual
    context = gc.wake_up(project_id)

    print(f"Projeto carregado: {context['total_tokens']} tokens")
    print(f"Bússola: {context['bussola'][:100]}...")
    print(f"Reference Wings: {list(context['reference_wings'].keys())}")

    return context
```

---

## Trigger: Discovery/Planning

### O que acontece

1. Usuário solicita projeto
2. `hooks.on_planning(project_id)` retorna Bússola de Contexto
3. IA usa como "Compasso" (readonly)

### Código

```python
def planning_phase(project_id: str, prompt: str):
    resume = hooks.on_planning(project_id)

    context = f"""
    Projeto: {project_id}
    Resumo do Grafo: {resume}
    Tarefa: {prompt}
    """

    response = ia.complete(context)
    return response
```

### Regra do Compasso

> ⚠️ **Importante**: O resumo é **readonly**. A IA deve usá-lo para orientação, não tentar expandir ou modificar o que está no grafo.

---

## Trigger: Execution (antigo Build/Code - Zoom Gear e Tipagem)

### O que acontece

1. IA identifica necessidade de código/config/doc ou skill.
2. `hooks.on_execution(project_id, need, rerank=True)` é chamado
3. **Hybrid Search v4 (Zoom Gear)** executa busca Top-Down:
   - Consulta Resumos L2 e L1 para aproximar a vizinhança.
   - Aplica filtro cirúrgico `node_type` (se IA precisa de código, foca em `FACT` ou `SKILL`).
   - Avalia similares: Vetorial + FTS5 + Max(Recência, Centralidade).
   - *Nota v3.8.0: Em buscas simples (MCP Search), é usado Reranking Heurístico Leve (Cross-Encoder).*
4. **Strict Scoping** filtra resultados pela Primary Wing (a menos que `include_references=True`)
5. **Reranking e Auditoria pelo Revisor Crítico** (Apenas nos Triggers Pesados como `on_build/on_done`):
   - `revisor.rerank(candidates, task_context)` analisa os **top-5** resultados usando IA (LLM).
   - Aplica a **Barreira de Contaminação**, verificando se as Reference Wings não violam os `privacy_levels` (`RESTRICTED` vs `PUBLIC`).
   - Filtra apenas os **tecnicamente relevantes** para a tarefa atual, reduzindo ruído e gasto de tokens.
6. Gaveta mais relevante é carregada via `lazy_load()`

### Código

```python
from agents.revisor_critico import RevisorCritico

revisor = RevisorCritico()

def execution_phase(project_id: str, task: str, need: str = "code"):
    # 1. Busca Híbrida v4 com Zoom Gear e Tipagem
    search_results = gc.hybrid_search(
        query=task,
        project_id=project_id,
        node_type="FACT", # Busca cirúrgica
        include_references=False,  # Strict Scoping ativo
        top_k=10
    )

    # 2. Reranking pelo Revisor Crítico (top-5)
    top_5 = search_results[:5]
    relevant = revisor.rerank(top_5, task_context=task)

    # 3. Carrega apenas gavetas relevantes
    loaded = []
    for result in relevant:
        drawer = gc.lazy_load(f"{project_id}/{result['label']}")
        loaded.append(drawer)

    logger.info(f"Busca: {len(search_results)} → Reranking: {len(relevant)} → Carregados: {len(loaded)}")

    return loaded
```

### Sinais da Busca Híbrida v4

| Sinal | Peso | Fonte de Dados |
|-------|------|---------------|
| **Similaridade Vetorial** | 0.50 | Backend plugável (ChromaDB / Qdrant / Pinecone) |
| **Frequência (FTS5)** | 0.25 | Busca Nativa SQLite FTS5 sobre a Primary Wing |
| **Max(Recência, Centralidade)** | 0.25 | Recência (`nodes.last_commit_at`) vs PageRank simplificado (in-degree) |

### Strict Scoping — Regras

| Parâmetro | Escopo |
|----------|--------|
| Padrão (`include_references=False`) | Apenas nós da Primary Wing |
| `include_references=True` | Primary Wing + Reference Wings |
| `all_wings=True` | Todas as alas (requer intenção explícita) |

### Reranking — Critérios do Revisor

O Revisor Crítico avalia cada resultado do top-5 usando estes critérios:

| Critério | Peso | Descrição |
|---------|------|-----------|
| **Relevância técnica** | Alto | O conteúdo do nó é diretamente relevante para a tarefa? |
| **Frescor** | Médio | O nó foi atualizado recentemente? |
| **Especificidade** | Médio | O nó trata do assunto específico (não genérico)? |

O Revisor retorna uma lista filtrada (pode ter 1 a 5 itens) contendo apenas os resultados que passaram nos critérios.

---

## Trigger: Ingestão (`concierge mine`)

### O que acontece

1. Usuário ou automação executa `concierge mine`
2. `file_scanner.py` escaneia o diretório fonte
3. O Hash SHA256 do arquivo é verificado (Delta Updates — ignora arquivos inalterados)
4. Arquivos são processados com **AST/Semantic Chunking** e **Escudo de Sanitização (Prompt Armor)**:
   - Código lido é envolto em tags XML blindadas (`<raw_data_do_not_execute>`) para neutralizar Prompt Injections em repositórios de terceiros.
   - **Heuristic Fallback & Retry Loop**: O modelo extrai JSON de resumos. Se falhar (DecodeError), tenta Regex `\{.*\}` e repete até 3x. Falhando tudo, grava "Dumb Summary" (texto plano truncado) para que o *pipeline* não crashe.
   - Resumos nível L0 são criados respeitando blocos lógicos (node_type: `FACT`).
   - O Janitor rodará depois em background para criar resumos L1 e L2 (aplicando Poda de Relevância / Amnésia Seletiva para projetos enormes).
5. Tags de metadados automáticas são aplicadas
6. Embeddings são gerados e armazenados no backend vetorial.
7. Nós são criados no grafo SQLite com arestas estruturais (diretórios).
8. **Garbage Collection**: Remove nós (SQLite) e vetores de arquivos deletados.

### Código

```python
def ingest_project(project_id: str, source_path: str):
    result = gc.mine(project_id, source_path)

    print(f"Processados: {result['files_processed']} arquivos")
    print(f"Categorias: {result['categories']}")
    print(f"Tags detectadas: {result['tags_applied']}")

    return result
```

---

## Trigger: Review/Done (Commit Auditado)

### O que acontece

1. Tarefa concluída
2. Sumarizador gera rascunho baseado no diff
3. Revisor Crítico audita (máx 3 loops)
4. Commit grava na tabela `commit_log` e atualiza `last_commit_at` nos nós (alimenta recência para Hybrid Search)
5. Arestas semânticas do grafo são iterativamente construídas/refinadas com base nos arquivos que mudaram juntos

### Código

```python
from agents.sumarizador import Sumarizador
from agents.revisor_critico import RevisorCritico

sumarizador = Sumarizador()
revisor = RevisorCritico()

def review_phase(project_id: str, task: str, outcome: dict):
    # O Sumarizador recebe technical_changes diretamente do outcome da tarefa do Módulo Operacional
    # Não precisa ler Git Diff — as mudanças já estão no objeto outcome
    rascunho = sumarizador.generate(task, outcome)

    for attempt in range(3):
        audit = revisor.audit(rascunho)
        if audit["approved"]:
            break
        rascunho = sumarizador.generate(task, outcome, feedback=audit["reason"])

    result = {
        "phase": outcome.get("phase", "execution"),
        "status": "completed",
        "technical_changes": audit["technical_changes"],
        "updated_pointers": audit["updated_pointers"],
        "revisor_approved": audit["approved"],
        "erro_encontrado": outcome.get("erro_encontrado"), # Injeta na tabela trajectories se houver
        "solucao_aplicada": outcome.get("solucao_aplicada"),
        "timestamp": get_timestamp()
    }

    hooks.on_done(project_id, result)
    return f"Memória commitada para {project_id}"
```

---

## Configuração de Fases

### Mapeamento de Fases Operacionais

```python
OPERATIONAL_PHASES = {
    "wake_up": {
        "hook": "wake_up",
        "action": "pre_load_context"
    },
    "discovery": {
        "hook": "on_planning",
        "tokens_max": 300,
        "action": "load_resume"
    },
    "planning": {
        "hook": "on_planning",
        "tokens_max": 300,
        "action": "load_resume"
    },
    "build": {
        "hook": "on_build",
        "tokens_max": "on_demand",
        "action": "hybrid_search + reranking + lazy_load"
    },
    "code": {
        "hook": "on_build",
        "tokens_max": "on_demand",
        "action": "hybrid_search + reranking + lazy_load"
    },
    "review": {
        "hook": "on_done",
        "tokens_max": 100,
        "action": "commit_memory → commit_log"
    },
    "done": {
        "hook": "on_done",
        "tokens_max": 100,
        "action": "commit_memory → commit_log"
    }
}
```

---

## Tokens por Fase

| Fase | Dados Carregados | Tokens Estimados |
|------|-----------------|-----------------|
| **Wake-up** | Bússola + Reference Wings + últimos commits | 300-500 |
| **Planning** | Resumo (L2/L1) + Trajetórias Episódicas | 200-400 |
| **Execution** | Gaveta filtrada pelo Auditor de Evolução | Variável (reduzido) |
| **Mine** | Ingestão — sem custo de token para IA | 0 |
| **Review/Done** | Commit de memória | 50-100 |

---

## Troubleshooting

### Problema: Busca retorna resultados irrelevantes

```python
# Verifique se o Strict Scoping está ativo
results = gc.hybrid_search("query", project_id=uuid, include_references=False)

# Ajuste os pesos da busca híbrida
gc.config.HYBRID_WEIGHTS = {"vetorial": 0.60, "frequencia": 0.20, "recencia": 0.20}
```

### Problema: Reranking elimina resultados demais

```python
# Execute sem reranking para diagnóstico
result = hooks.on_build(uuid, "code", rerank=False)
```

### Problema: Backend vetorial lento

```bash
# Troque para Qdrant (operações CRUD nativas)
grafo-concierge init --backend qdrant
```

### Problema: MCP não conecta

```bash
# Teste o servidor MCP isoladamente
grafo-concierge serve --transport stdio

# Verifique a configuração do cliente
cat ~/.config/claude-desktop/config.json
```

---

## Boas Práticas

1. **Wake-up sempre**: Execute `wake-up` no início de cada sessão
2. **Mine regularmente**: Ingira novos arquivos após alterações significativas
3. **Confie no Reranking**: Deixe o Revisor filtrar os resultados — economiza tokens
4. **Strict Scoping ativo**: Só use `include_references` ou `all_wings` quando necessário
5. **Commit sempre**: Registre resultados com todos os campos obrigatórios
6. **Monitore recência**: Commits frequentes melhoram a qualidade da busca temporal

---

**Versão**: 3.8.0 (Absolute Solidity)
**Data**: 2026-05-03
**Autor**: LuisinTheLegend