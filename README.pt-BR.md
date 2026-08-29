[English](README.md) · Português (Brasil)
---

# 🧠 Grafo Concierge v4.0.0

**O Palácio de Memórias Cognitivas de Longo Prazo (LTM) Open-Source para Agentes de IA, IDEs e Ambientes de Desenvolvimento**

[![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Suporte Docker](https://img.shields.io/badge/Docker-Pronto-blue)](docker-compose.yml)

O Grafo Concierge é um servidor de memória cognitiva local-first de alta performance projetado para resolver a "amnésia" dos LLMs, a poluição de contexto e as faturas astronômicas de APIs de nuvem. Operando sob a **Engenharia de Sobrevivência e Resiliência Extrema**, o Grafo Concierge atua como um motor soberano de Memória de Longo Prazo (LTM), combinando persistência relacional SQLite WAL com auto-batching adaptativo, sincronização delta por dual-hash (SSH + LBH Semantic Drift Guard), GraphRAG frugal com guardas estritas de ciclo, rastreamento de alias por hash estrutural, parsing AST multilíngue (Python, TypeScript, JavaScript), checkpoints duráveis com time-travel cognitivo, governança por ocultação progressiva de ferramentas e roteamento federado de conhecimento (Nozomio RAG) com adaptador de memória global híbrida.

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
3. **Rastreamento de Alias por Hash Estrutural (`core/alias_tracker.py`)**: Resolve renomeações e movimentações de arquivos atomicamente em $< 1\text{s}$ via Structural Semantic Hashing (SSH). Propaga atualizações em cascata por `ast_edges`, `files` e `nodes` sem reconstruir o grafo, com timer de expurgo para evitar nós zumbis em exclusões reais.
4. **Fábrica de Parsers Multilíngue (`core/parser_factory.py`)**: Estende a inteligência AST para TypeScript e JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) via Tree-sitter e fallback léxico de alta performance, filtrando pacotes npm externos e hooks nativos do React.
5. **GraphRAG Frugal, Filtro de Supernó e Guardas Estritas de Ciclo em CTEs**: Combina mapeamento topológico natural ($O(1)$) com **Filtro de Desvio de Grau para Supernós** (`detect_logical_communities`), isolando hubs globais (ex: `utils.py`) em clusters `hub_satellite_{dir}` para evitar o colapso do grafo, enquanto executa buscas multi-hop via `WITH RECURSIVE` protegido por pipes (`|node|` com `instr()`).
6. **Checkpoints Duráveis e Time-Travel Cognitivo (`core/checkpointer.py`)**: Persiste snapshots de execução resilientes na tabela `fsm_checkpoints` com sanitização recursiva de objetos não-serializáveis e reversão cronológica de estado, expurgando passos futuros e remarcando arquivos como sujos.
7. **Governança por Ocultação Progressiva de Ferramentas (`core/mcp_governor.py`)**: Firewall cognitivo que impõe controle em duas camadas com base no estado FSM do agente (`PLANNING`, `DISCOVERY`, `EXECUTION`, `TDD_GREEN`, `REFACTORING`, `MAINTENANCE`). Oculta ferramentas de mutação/perigosas no planejamento e bloqueia ativamente invocações diretas no runtime, levantando `SecurityException`.
8. **Roteamento Federado de Conhecimento (Nozomio RAG) e Adaptador de Memória Global Híbrida**: Classificador JIT de intenção em 3 camadas (Regex < 1ms, entidades SQLite e SLM Ollama) que roteia consultas entre o `LOCAL_GRAPHRAG` privado (`is_private: True`) e documentações públicas via MCP federado (`is_private: False`). O `GlobalMemoryAdapter` monta uma janela mista: as últimas 3 mensagens do chat (STM) combinadas com o substrato estruturado de longo prazo (LTM) do grafo.
9. **Throttler Térmico de Hardware e Rate Governor (`BackgroundJanitor`)**: Inspeciona o uso de CPU do host ($< 40\%$) e períodos de ociosidade de digitação via `psutil` antes de disparar resumos locais via SLMs (Ollama) em prioridade operacional rebaixada (`IDLE_PRIORITY_CLASS` / `nice(15)`).
10. **Camada de Telemetria em Tempo Real e Streaming SSE (`interface/telemetry_api.py`)**: Disponibiliza endpoints FastAPI para observabilidade de dashboards, emitindo snapshots tipados em Pydantic v2 (`/api/telemetry/snapshot`), stream contínuo Server-Sent Events (`/api/telemetry/stream`), checkpoints (`/api/checkpoints/*`), governança (`/api/mcp/*`) e gatilhos manuais de reconciliação.
11. **Amostragem de Thompson Nativa Zero-NumPy (`core/probabilistic_retriever.py`)**: Substitui a biblioteca externa `numpy` pela função nativa da biblioteca padrão `random.betavariate()` com sanitização defensiva (`max(val, 1e-5)`), economizando ~30MB sem perdas estatísticas.
12. **Auto-Poda Inteligente de Checkpoints (`BackgroundJanitor`)**: Algoritmo Smart LRU por sessão que evita o inchaço do banco `state.db`. Protege o checkpoint inicial `"init"` (ponto zero fundamental para hard resets), preserva os $N$ passos mais recentes e elimina registros intermediários obsoletos em lote paginado.
13. **Auto-Cura Vetorial em Tempo de Execução (Query-Time Self-Healing)**: Intercepta buscas vetoriais e descarta vetores órfãos instantaneamente ($O(1)$) sem a lentidão de Two-Phase Commits (2PC), enquanto um Janitor expurga órfãos físicos em segundo plano por diferença de conjuntos $O(N)$.
14. **Persistência Bi-Temporal de Fatos**: Registra fatos semânticos com rastreamento temporal (`t_valid` / `t_invalid`) e aprendizado Bayesiano por reforço sobre a utilidade das memórias.
15. **Watcher Reativo com Early Exit**: Filtra eventos do sistema de arquivos via `.conciergeignore` / `pathspec` antes de ler o disco, eliminando gargalos de I/O em pastas como `node_modules` e `.git`.

---

## 🛡️ Vantagens Arquiteturais (Soluções para Armadilhas de Memória)

| Problema em Memórias Tradicionais | Como o Grafo Concierge v4.0.0 Resolve |
| :--- | :--- |
| **Travamentos por "Database is Locked"** | **`SerializedWriteQueue` com Auto-Batching**: Fila serializada com transações em lote de até 50 itens, Fallback Atômico e leituras concorrentes ultrarrápidas (< 5ms). |
| **Deriva Semântica Silenciosa e Custos de Token** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignora formatações/docstrings (zero custo de token), mas detecta mudanças reais de lógica mantendo a memória exata. |
| **Renomeação de Arquivos Destruindo Trajetórias** | **Rastreamento de Alias por Hash Estrutural**: Buffer atômico de 1s via SSH detecta renomeações e migra relações em `files`, `ast_edges` e `nodes` sem reconstruir o grafo. |
| **Ponto Cego em Projetos Multilinguagem** | **Fábrica de Parsers Multilíngue**: Suporte nativo a Python e TypeScript/JavaScript/React (`.ts`, `.tsx`, `.js`, `.jsx`) com filtro inteligente de pacotes npm. |
| **Colapso do Grafo em Componente Único Gigante** | **Filtro de Desvio de Supernó**: Isola dinamicamente hubs utilitários (`utils.py`) em clusters `hub_satellite_{dir}` via Union-Find, preservando a granularidade das comunidades. |
| **Inchaço de Tokens e Mutação Prematura de Código** | **Ocultação Progressiva de Ferramentas**: Oculta ferramentas de escrita na fase de `PLANNING` e desbloqueia em `EXECUTION`, estourando `SecurityException` em tentativas de injeção. |
| **Inchaço Linear do Histórico de Conversação** | **Adaptador de Memória Global Híbrida**: Preserva estritamente as últimas 3 mensagens do chat (STM) e substitui o histórico antigo por um bloco LTM estruturado do grafo. |
| **Picos de CPU e Ventoinhas com SLMs Locais** | **Throttler Térmico de Hardware**: Usa `psutil` para validar CPU < 40% e período de ociosidade, executando SLMs locais em prioridade rebaixada no SO. |
| **Dependências Matemáticas Pesadas** | **Thompson Sampling Zero-NumPy**: Substituiu o NumPy pelo `random.betavariate()` nativo e sanitizado, enxugando ~30MB do pacote. |
| **Recursão Infinita em Grafos Cíclicos** | **Guarda Estrita Delimitada em CTEs**: Acumuladores de caminho delimitados por pipes (`\|node\|`) bloqueiam ciclos e impedem falsos positivos em arquivos de nomes parecidos. |
| **Inchaço Descontrolado do Banco de Dados** | **Auto-Poda Inteligente (Smart LRU)**: Elimina checkpoints intermediários obsoletos preservando o baseline `"init"` e os $N$ passos recentes. |
| **Memória Desatualizada e Vetores Zumbis** | **Auto-Cura JIT + Janitor**: Arquivos deletados são descartados da busca vetorial em tempo real e purgados em massa em background. |
| **Bloqueio por SDK Proprietária** | **Padrão MCP Nativo (30 Ferramentas) + FastAPI SSE**: Opera via Model Context Protocol (JSON-RPC/SSE) e FastAPI REST/SSE para total integração com dashboards. |

---

## ⚙️ Destaques de Engenharia Avançada

* ⚡ **DX Concorrente Unificado (`npm run dev:all`)**: Inicia simultaneamente o frontend Next.js (`grafo-dashboard-web`) e o backend FastAPI/FastMCP em um único terminal com logs coloridos via `concurrently`.
* ⚡ **Modo Lightweight com Economia de RAM (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Permite rodar o Grafo Concierge em hardware modesto ou VPS de $4/mês (< 35MB RAM) desativando modelos neurais e usando SQLite FTS5 BM25.
* 📊 **Stream de Telemetria SSE em Tempo Real (`GET /api/telemetry/stream`)**: Envia mutações de estado ao vivo (arquivos sujos, auto-cura, checkpoints) para dashboards Next.js / Electron sem overhead de polling.
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
                     └──────────────┬──────────────┘
                                    │  FastAPI REST / SSE
                                    ▼
                     ┌─────────────────────────────┐
                     │ 📊 Dashboard / UI em Tempo  │
                     │    Real (Next.js / Web)     │
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: O agente da sua IDE pesquisa, recupera e consolida memória de projeto enquanto você coda.
* 💬 **Claude Desktop**: Concede ao assistente consciência macro instantânea dos seus repositórios.
* 📊 **Dashboard ao Vivo (Next.js)**: Recebe Server-Sent Events de baixa latência exibindo a saúde da memória em tempo real.
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

O Grafo Concierge conta com uma suíte rigorosa de testes automatizados cobrindo todos os módulos de sobrevivência, o fechamento completo do Pilar 2 (Cognição) e a integração E2E com **100% dos testes verdes (86 passed, 1 skipped de 87 testes)**:

```bash
python -m pytest tests/ -v
```

---

## 📄 Licença
Distribuído sob a Licença MIT. Consulte `LICENSE` para obter mais detalhes.
