[English](README.md) · Português (Brasil)
---

# 🧠 Grafo Concierge v4.0.0

**O Palácio de Memórias Cognitivas de Longo Prazo (LTM) Open-Source para Agentes de IA, IDEs e Ambientes de Desenvolvimento**

[![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Suporte Docker](https://img.shields.io/badge/Docker-Pronto-blue)](docker-compose.yml)

O Grafo Concierge é um servidor de memória cognitiva local-first de alta performance projetado para resolver a "amnésia" dos LLMs, a poluição de contexto e as faturas astronômicas de APIs de nuvem. Diferente de scripts simples de RAG (Retrieval-Augmented Generation), o Grafo Concierge opera sob a **Engenharia de Sobrevivência e Resiliência Extrema**, combinando persistência relacional SQLite WAL com auto-batching adaptativo, sincronização delta por dual-hash (SSH + LBH Semantic Drift Guard), GraphRAG frugal com guardas estritas de ciclo, auto-poda inteligente de checkpoints (Smart LRU) e checkpointing agnóstico com Time-Travel.

---

## 💡 O que é o Grafo Concierge? (Para Leigos e Devs Seniores)

### 👶 Explicação Simples (A Analogia)
> Imagine contratar um engenheiro de software sênior brilhante que sofre de perda de memória de curto prazo. Toda vez que você abre um novo chat no Cursor ou no Claude Desktop, ele esquece a estrutura do seu projeto, os padrões do seu código e as decisões arquiteturais tomadas ontem.
>
> **O Grafo Concierge é o cérebro externo permanente desse engenheiro.** Conectado de forma transparente pelo protocolo padrão Model Context Protocol (MCP), seu assistente de IA consulta, aprende e atualiza esse cérebro automaticamente em milissegundos — sem que você precise ficar copiando e colando trechos de código manualmente!

### 🧙‍♂️ Aprofundamento Técnico (Para Engenheiros)
O Grafo Concierge é um daemon local-first/VPS que oferece:
1. **Concorrência Zero-Lock e Auto-Batching (`SerializedWriteQueue`)**: Canaliza todas as escritas através de uma thread daemon dedicada no SQLite WAL. Possui Auto-Batching Adaptativo (agrupa até 50 operações da fila em blocos `BEGIN IMMEDIATE ... COMMIT`) e Fallback Atômico de Item Único para resgatar gravações saudáveis caso ocorra violação de restrição.
2. **Sincronização Delta Dual-Hash (SSH + LBH Semantic Drift Guard)**: Combina o hash de assinaturas (SSH) com o hash de corpo lógico (LBH) via `DocstringStripper(ast.NodeTransformer)`. Detecta alterações de lógica real (`is_dirty = 1`) enquanto ignora comentários, espaços, quebras de linha e docstrings, economizando 100% dos tokens de IA.
3. **GraphRAG Frugal com Guardas Estritas de Ciclo em CTEs**: Substitui partições pesadas de rede por mapeamento topológico natural de diretórios ($O(1)$) e executa buscas multi-hop em milissegundos via `WITH RECURSIVE` com acumulador delimitado por pipes (`|node|` com `instr()`), bloqueando ciclos indiretos ($A \rightarrow B \rightarrow C \rightarrow A$) e colisões de substring (`auth.js` vs `oauth.js`).
4. **Auto-Poda Inteligente de Checkpoints (`BackgroundJanitor`)**: Algoritmo Smart LRU por sessão que evita o inchaço do banco `state.db`. Protege o checkpoint inicial `"init"` (ponto zero fundamental para hard resets), preserva os $N$ passos mais recentes e elimina registros intermediários obsoletos em lote paginado.
5. **Auto-Cura Vetorial em Tempo de Execução (Query-Time Self-Healing)**: Intercepta buscas vetoriais e descarta vetores órfãos instantaneamente ($O(1)$) sem a lentidão de Two-Phase Commits (2PC), enquanto um Janitor expurga órfãos físicos em segundo plano por diferença de conjuntos $O(N)$.
6. **Checkpointing de Estados Agnóstico e Time-Travel**: Persiste dicionários de estado de qualquer IA como blobs JSON sob chaves compostas `(agent_id, session_id, checkpoint_id)`, viabilizando isolamento hermético entre agentes e viagens no tempo cronológicas.
7. **Persistência Bi-Temporal de Fatos e Thompson Sampling**: Registra fatos semânticos com rastreamento temporal (`t_valid` / `t_invalid`) e aprendizado Bayesiano por reforço sobre a utilidade das memórias.
8. **Watcher Reativo com Early Exit**: Filtra eventos do sistema de arquivos via `.conciergeignore` / `pathspec` antes de ler o disco, eliminando gargalos de I/O em pastas como `node_modules` e `.git`.

---

## 🛡️ Vantagens Arquiteturais (Soluções para Armadilhas de Memória)

| Problema em Memórias Tradicionais | Como o Grafo Concierge v4.0.0 Resolve |
| :--- | :--- |
| **Travamentos por "Database is Locked"** | **`SerializedWriteQueue` com Auto-Batching**: Fila serializada com transações em lote de até 50 itens, Fallback Atômico e leituras concorrentes ultrarrápidas (< 5ms). |
| **Deriva Semântica Silenciosa e Custos de Token** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignora formatações/docstrings (zero custo de token), mas detecta mudanças reais de lógica mantendo a memória exata. |
| **Recursão Infinita em Grafos Cíclicos** | **Guarda Estrita Delimitada em CTEs**: Acumuladores de caminho delimitados por pipes (`\|node\|`) bloqueiam ciclos e impedem falsos positivos em arquivos de nomes parecidos. |
| **Inchaço Descontrolado do Banco de Dados** | **Auto-Poda Inteligente (Smart LRU)**: Elimina checkpoints intermediários obsoletos preservando o baseline `"init"` e os $N$ passos recentes. |
| **Memória Desatualizada e Vetores Zumbis** | **Auto-Cura JIT + Janitor**: Arquivos deletados são descartados da busca vetorial em tempo real e purgados em massa em background. |
| **Estouro de RAM com Grafos Complexos** | **Motor GraphRAG Frugal**: Comunidades topológicas naturais em $O(1)$ e resolução recursiva de chamadas diretamente no SQLite WAL via CTEs. |
| **Bloqueio por SDK Proprietária** | **Padrão MCP Nativo (30 Ferramentas)**: Opera via Model Context Protocol (JSON-RPC/SSE) da Anthropic. Compatível com Cursor, Windsurf, Claude Desktop e enxames de agentes. |

---

## ⚙️ Destaques de Engenharia Avançada

* ⚡ **Modo Lightweight com Economia de RAM (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Permite rodar o Grafo Concierge em hardware modesto ou VPS de $4/mês (< 35MB RAM) desativando modelos neurais e usando SQLite FTS5 BM25.
* 🔒 **Segurança Local-First por Padrão (`CONCIERGE_BIND_ADDRESS=127.0.0.1`)**: Escuta exclusivamente o localhost para proteção em Wi-Fi público, facilmente configurável para `0.0.0.0` para malhas seguras do Tailscale.
* 🔍 **Engrenagem de Zoom Hierárquica (L0 ➔ L1 ➔ L2)**: Sintetiza blocos de código (L0) em módulos de pasta (L1) e Bússolas de Contexto (L2) com amnésia seletiva.
* 🎯 **Amostragem de Thompson Bayesiana**: Loop de feedback em tempo real (`concierge_feedback`) que ajusta dinamicamente os pesos de busca com base em reforço.
* 🔐 **Isolamento de Asas de Privacidade**: Separação estrutural entre asas `PUBLIC`, `INTERNAL` e `RESTRICTED`.

---

## 🔌 Integração Simultânea Multi-Cliente via MCP

Alimentado pelo protocolo **Model Context Protocol (MCP)** da Anthropic, uma única instância do servidor Grafo Concierge comunica-se **simultaneamente** com todas as suas ferramentas favoritas:

```
    ┌───────────────────────────┐      ┌───────────────────────────┐
    │     Cursor / Windsurf     │      │       Claude Desktop      │
    └─────────────┬─────────────┘      └─────────────┬─────────────┘
                  │                                  │
                  │        JSON-RPC / SSE (MCP)      │
                  └─────────────────┬────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────┐
                     │ 🧠 Servidor Grafo Concierge │
                     │  (Local / VPS - Porta 8000) │
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: O agente da sua IDE pesquisa, recupera e consolida memória de projeto enquanto você coda.
* 💬 **Claude Desktop**: Concede ao assistente consciência macro instantânea dos seus repositórios.
* 🤖 **Agentes Autônomos e Enxames**: Conecte n8n, LangChain, AutoGen ou scripts Python via endpoints SSE.

---

## ⚡ Guia de Início Rápido (3 Minutos)

### Opção 1: Instalação via PyPI (Recomendada)

```bash
# Instalar pacote e CLI do Grafo Concierge
pip install concierge-graph

# Iniciar o Servidor FastMCP
concierge-mcp
```

### Opção 2: Instalação Local via Código-Fonte

1. **Clonar e Instalar em Modo Editável**:
   ```bash
   git clone https://github.com/LuisinTheLegend/GrafoConcierge.git
   cd GrafoConcierge
   pip install -e .[dev]
   ```

2. **Configurar Ambiente (`.env`)**:
   ```bash
   cp .env.example .env
   ```
   Adicione sua chave Gemini ou OpenAI:
   ```env
   GRAFO_LLM_API_KEY=sua_chave_aqui
   GRAFO_LLM_MODEL=gemini-2.0-flash
   CONCIERGE_BIND_ADDRESS=127.0.0.1
   ```

3. **Iniciar o Servidor MCP**:
   ```bash
   concierge-mcp
   ```

---

## 🔌 Referência Rápida das Ferramentas MCP (30 Ferramentas)

* **`concierge_mine`**: Ingestão de diretório com filtro early-exit, análise AST, dual-hash (SSH + LBH) e resumos L0/L1/L2.
* **`concierge_search`**: Busca híbrida v4 (50% vetor, 25% FTS5, 25% grafo) com auto-cura em tempo de execução.
* **`concierge_get_call_chain`**: Descoberta recursiva de dependências de chamada via CTE com proteção anti-loop estrita delimitada.
* **`agent_save_checkpoint`**: Persistência de estados genéricos de agentes no SQLite WAL (com auto-poda Smart LRU).
* **`agent_get_checkpoint`**: Recuperação e decodificação de estados salvos para um determinado passo.
* **`agent_list_checkpoints`**: Linha do tempo cronológica de checkpoints para Time-Travel Debugging.
* **`concierge_wakeup`**: Reativa a consciência do agente (Bússola de Contexto, asas de referência e commits recentes).
* **`concierge_resume`**: Retorna o resumo executivo conciso do projeto para injeção em prompts.
* **`concierge_load`**: Carregamento preguiçoso (Lazy Load) de nós, arestas e dependências.
* **`concierge_commit`**: Registra alterações técnicas auditadas no livro-razão de memória.
* **`concierge_store_fact`**: Registra fatos e regras de negócio com invalidação bi-temporal.
* **`concierge_list_facts`**: Lista fatos semânticos ativos por escopo com IDs primários estáveis.
* **`concierge_feedback`**: Registra feedback de utilidade para otimização Bayesiana por Thompson Sampling.

---

## 🧪 Suíte de Testes e Auditoria E2E

O Grafo Concierge conta com uma suíte rigorosa de testes automatizados cobrindo todos os módulos de sobrevivência, resiliência de Fase 4 e integração E2E com **100% dos testes verdes**:

```bash
python -m pytest tests/test_checkpoint_pruning.py \
                 tests/test_queue_writer_batching.py \
                 tests/test_delta_sync_drift.py \
                 tests/test_graph_rag_loops.py \
                 tests/test_agent_checkpointer.py \
                 tests/test_delta_sync.py \
                 tests/test_graph_rag_janitor.py \
                 tests/test_vector_reconciler.py \
                 tests/test_mcp_server_extensions.py \
                 tests/test_e2e_concierge_integration.py \
                 tests/test_dependency_injection.py \
                 tests/test_concurrency_stress.py -v
```

---

## 📄 Licença
Distribuído sob a Licença MIT. Consulte `LICENSE` para obter mais detalhes.
