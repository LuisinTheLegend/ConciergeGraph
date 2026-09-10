[English](README.md) · Português (Brasil)
---

# 🧠 Grafo Concierge v4.2.0

**O Palácio de Memórias Cognitivas de Longo Prazo (LTM), Motor Hierárquico de Estados e Cockpit em Tempo Real para Agentes de IA, IDEs e Ambientes de Desenvolvimento**

[![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Next.js 16](https://img.shields.io/badge/Cockpit-Next.js%2016-black)](grafo-dashboard-web/)
[![Testes Aprovados](https://img.shields.io/badge/Testes-326%20Aprovados-brightgreen.svg)](tests/)
[![Suporte Docker](https://img.shields.io/badge/Docker-Pronto-blue)](docker-compose.yml)

O Grafo Concierge é um servidor de memória cognitiva local-first de alta performance projetado para eliminar a "amnésia" dos LLMs, prevenir a poluição de janelas de contexto, isolar o esgotamento de cotas HTTP 429 e governar a autonomia multi-agente. Operando sob o **Paradigma de Engenharia de Sobrevivência e Resiliência Extrema**, o Grafo Concierge combina persistência relacional SQLite WAL com auto-batching adaptativo, uma Máquina de Estados Hierárquica (HSM) com Deep History Nodes ($H^*$), um Rate Governor prioritário (60 RPM / 40.000 TPM), interceptador de gating adaptativo, sincronização delta por dual-hash (SSH + LBH Semantic Drift Guard), parsing AST multilíngue (Python, TypeScript, JavaScript) e um **Cockpit de Observabilidade Passiva em Next.js 16**.

---

## 💡 O que é o Grafo Concierge? (Para Leigos e Devs Seniores)

### 👶 Explicação Simples (A Analogia)
> Imagine contratar um engenheiro de software sênior brilhante que sofre de perda de memória de curto prazo. Toda vez que você abre um novo chat no Cursor ou no Claude Desktop, ele esquece a estrutura do seu projeto, os padrões do seu código, as decisões arquiteturais tomadas e em qual etapa estava trabalhando.
>
> **O Grafo Concierge é o cérebro externo permanente e sistema nervoso desse engenheiro.** Conectado de forma transparente pelo protocolo padrão Model Context Protocol (MCP), seu assistente de IA consulta, aprende, opera dentro de limites hierárquicos e atualiza esse cérebro automaticamente em milissegundos — sem que você precise ficar copiando e colando contexto manualmente!

### 🧙‍♂️ Aprofundamento Técnico (Para Engenheiros)
O Grafo Concierge é um daemon local-first/VPS com interface reativa que oferece:
1. **Concorrência Zero-Lock e Auto-Batching (`SerializedWriteQueue`)**: Canaliza todas as escritas através de uma thread daemon dedicada no SQLite WAL. Possui Auto-Batching Adaptativo (agrupa até 50 operações da fila em blocos `BEGIN IMMEDIATE ... COMMIT`) e Fallback Atômico de Item Único para resgatar gravações saudáveis caso ocorra violação de restrição.
2. **Máquina de Estados Hierárquica e Deep History Nodes (`core/hsm_engine.py`)**: Modela a execução do agente em uma árvore de estados interativa (`PLANNING`, `EXECUTION`, `MAINTENANCE`, `ERROR`) com ganchos de ciclo de vida hierárquicos (`on_enter`/`on_exit`), Deep History Nodes ($H^*$) para restauração instantânea de contexto e um Circuit Breaker de 5 turnos contra loops de auto-cura infinitos.
3. **Rate Governor com Fila de Prioridades (`core/rate_governor.py`)**: Regulador de cotas em janela deslizante de 60 segundos (60 RPM, 40.000 TPM) com fila de 3 prioridades (HIGH, MEDIUM, LOW). Congela reativamente tarefas de background a 85% e 95% da capacidade para evitar erros HTTP 429 sem interromper a interação com o usuário.
4. **Adaptive Gating Interceptor e Security Guard (`core/gating_interceptor.py`, `core/security_guard.py`)**: Impõe réguas de fronteira no monorepo com níveis configuráveis de autonomia (`plan-only`, `ask`, `auto-approve`), confinamento estrito na raiz do projeto, sanitização de path traversal e bloqueio de injeção de comandos.
5. **Sincronização Delta Dual-Hash (SSH + LBH Semantic Drift Guard)**: Combina o hash de assinaturas (SSH) com o hash de corpo lógico (LBH) via `DocstringStripper(ast.NodeTransformer)`. Detecta alterações de lógica real (`is_dirty = 1`) enquanto ignora comentários, espaços e docstrings (100% de economia de tokens). Realiza auditoria de delta em tempo de execução durante o resume para detectar deriva de código no disco.
6. **Cockpit de Observabilidade Passiva Next.js 16 (`grafo-dashboard-web/`)**: Grid de monitoramento 2x2 em tempo real com visualizador de grafos de código 2D Force-Directed com nós pulsantes a 60fps para arquivos dirty, gauges circulares de RPM/TPM com avisos de congelamento, árvore colapsável da HSM com botão de resume em 1 clique e feed de logs de auto-cura via SSE.
7. **Rastreamento de Alias por Hash Estrutural (`core/alias_tracker.py`)**: Resolve renomeações e movimentações de arquivos atomicamente em $< 1\text{s}$ via Structural Semantic Hashing (SSH). Propaga atualizações em cascata por `ast_edges`, `files` e `nodes` sem reconstruir o grafo.
8. **Fábrica de Parsers Multilíngue (`core/parser_factory.py`)**: Estende a inteligência AST para TypeScript e JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`) via Tree-sitter e fallback léxico de alta performance, filtrando pacotes npm externos e hooks nativos do React.
9. **GraphRAG Frugal e Guardas Estritas de Ciclo em CTEs**: Combina mapeamento topológico natural ($O(1)$) com **Filtro de Desvio de Grau para Supernós** (`detect_logical_communities`), isolando hubs utilitários (`utils.py`) para evitar o colapso do grafo, enquanto executa buscas multi-hop via `WITH RECURSIVE` protegido por acumuladores pipe (`|node|`).
10. **Governança por Ocultação Progressiva de Ferramentas (`core/mcp_governor.py`)**: Firewall cognitivo que impõe controle em duas camadas com base no estado ativo da HSM. Oculta ferramentas de mutação/perigosas no planejamento para economizar contexto e bloqueia invocações diretas no runtime, levantando `SecurityException`.
11. **Roteamento Federado de Conhecimento e Adaptador de Memória Global Híbrida**: Classificador JIT de intenção em 3 camadas (Regex < 1ms, entidades SQLite e SLM Ollama) que roteia consultas entre o `LOCAL_GRAPHRAG` privado (`is_private: True`) e documentações públicas via MCP federado (`is_private: False`). O `GlobalMemoryAdapter` monta uma janela mista: as últimas 3 mensagens do chat (STM) combinadas com o substrato estruturado de longo prazo (LTM) do grafo.
12. **API REST e Telemetria Mestra com 15 Endpoints (`interface/telemetry_api.py`)**: Expõe rotas FastAPI para observabilidade ao vivo, fornecendo snapshots Pydantic v2, stream Server-Sent Events (`/api/telemetry/stream`), métricas do Rate Governor, controle da HSM e time-travel de checkpoints.
13. **Amostragem de Thompson Nativa Zero-NumPy (`core/probabilistic_retriever.py`)**: Substitui a biblioteca externa `numpy` pela função nativa `random.betavariate()` com sanitização defensiva (`max(val, 1e-5)`), economizando ~30MB sem perdas estatísticas.
14. **Auto-Poda Inteligente de Checkpoints (`BackgroundJanitor`)**: Algoritmo Smart LRU por sessão que evita o inchaço do banco relacional. Protege o checkpoint inicial `"init"` (ponto zero fundamental para hard resets), preserva os $N$ passos mais recentes e elimina registros intermediários obsoletos em lote.
15. **Auto-Cura Vetorial em Tempo de Execução (Query-Time Self-Healing)**: Intercepta buscas vetoriais e descarta vetores órfãos instantaneamente ($O(1)$) sem a lentidão de Two-Phase Commits (2PC), enquanto um Janitor expurga órfãos físicos em segundo plano por diferença de conjuntos.

---

## 🛡️ Vantagens Arquiteturais (Soluções para Armadilhas de IA)

| Problema em Ferramentas Tradicionais | Como o Grafo Concierge v4.2.0 Resolve |
| :--- | :--- |
| **Travamentos por Esgotamento de Quotas HTTP 429** | **Rate Governor Prioritário (SDD-23)**: Janela de 60s isola tráfego em HIGH/MEDIUM/LOW, congelando tarefas de background a 85%/95% para preservar o chat. |
| **Loops Infinitos e Desorientação do Agente** | **HSM e Circuit Breaker de 5 Turnos (SDD-25/26)**: Árvore de estados limita turnos por sub-estado, disparando para `ERROR.PAUSE` antes de estourar custos. |
| **Deriva Silenciosa de Código no Resume** | **Auditoria de Delta Dual-Hash (SDD-27)**: Detecta mudanças feitas no disco durante paradas e auto-redireciona o agente para `EXECUTION.RE_INDEX`. |
| **Mutações Indesejadas em Monorepos** | **Adaptive Gating Interceptor (SDD-24)**: Confinamento na raiz do projeto e modos de autonomia (`plan-only`, `ask`, `auto-approve`) impedem edições fora de escopo. |
| **Falta de Visibilidade do Estado do Agente** | **Cockpit Passivo Next.js 16 (SDD-28)**: Dashboard 2x2 em tempo real exibe nós ativos da HSM, gauges de cota e arquivos dirty a 60fps via SSE. |
| **Travamentos por "Database is Locked"** | **`SerializedWriteQueue` com Auto-Batching**: Fila serializada com lotes de até 50 itens, Fallback Atômico e leituras concorrentes ultrarrápidas (< 5ms). |
| **Deriva Semântica Silenciosa e Desperdício de Tokens** | **Dual-Hash Delta Sync (SSH + LBH)**: `DocstringStripper` ignora formatações/docstrings (zero custo de token), mas detecta alterações reais de lógica. |
| **Renomeação de Arquivos Destruindo Trajetórias** | **Rastreamento de Alias por Hash Estrutural**: Buffer atômico de 1s via SSH detecta renomeações e propaga alterações sem reconstruir o grafo. |
| **Ponto Cego em Projetos Multilinguagem** | **Fábrica de Parsers Multilíngue**: Suporte nativo a Python e TypeScript/JavaScript/React (`.ts`, `.tsx`, `.js`, `.jsx`) com filtro inteligente de pacotes npm. |
| **Colapso do Grafo em Componente Único Gigante** | **Filtro de Desvio de Supernó**: Isola dinamicamente hubs utilitários (`utils.py`) em clusters satélites via Union-Find, preservando as fronteiras das comunidades. |
| **Inchaço de Tokens e Mutação Prematura de Código** | **Ocultação Progressiva de Ferramentas**: Oculta ferramentas de escrita na fase de `PLANNING` e desbloqueia em `EXECUTION`, levantando `SecurityException`. |
| **Inchaço Linear do Histórico de Conversação** | **Adaptador de Memória Global Híbrida**: Preserva estritamente as últimas 3 mensagens do chat (STM) e substitui o histórico antigo por um bloco LTM estruturado do grafo. |
| **Recursão Infinita em Grafos Cíclicos** | **Guarda Estrita Delimitada em CTEs**: Acumuladores de caminho delimitados por pipes (`\|node\|`) bloqueiam ciclos e impedem colisões de substring. |
| **Bloqueio por SDK Proprietária** | **Padrão MCP Nativo (30 Ferramentas) + FastAPI SSE**: Opera via Model Context Protocol (JSON-RPC/SSE) e FastAPI REST/SSE para total integração com IDEs e dashboards. |

---

## ⚙️ Destaques de Engenharia Avançada

* ⚡ **DX Concorrente Unificado (`npm run dev:all`)**: Inicia simultaneamente o frontend Next.js 16 (`grafo-dashboard-web`) e o backend FastAPI/FastMCP em um único terminal com logs coloridos via `concurrently`.
* 📊 **Stream de Telemetria SSE em Tempo Real (`GET /api/telemetry/stream`)**: Envia mutações de estado ao vivo (arquivos sujos, atualizações de cotas, transições da HSM) para o cockpit sem overhead de polling.
* ⚡ **Modo Lightweight com Economia de RAM (`GRAFO_LIGHTWEIGHT_MODE=true`)**: Permite rodar o Grafo Concierge em hardware modesto ou VPS de $4/mês (< 35MB RAM) desativando modelos neurais e usando SQLite FTS5 BM25.
* 🔒 **Segurança Local-First por Padrão (`CONCIERGE_BIND_ADDRESS=127.0.0.1`)**: Escuta exclusivamente o localhost para proteção em Wi-Fi público, facilmente configurável para `0.0.0.0` para malhas seguras do Tailscale.
* 🔍 **Engrenagem de Zoom Hierárquica (L0 ➔ L1 ➔ L2)**: Sintetiza blocos de código (L0) em módulos de pasta (L1) e Bússolas de Contexto (L2) com amnésia seletiva.
* 🎯 **Amostragem de Thompson Bayesiana**: Loop de feedback em tempo real (`concierge_feedback`) que ajusta dinamicamente os pesos de busca com base em reforço.

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
                                    │  FastAPI REST / SSE (Porta 8001)
                                    ▼
                     ┌─────────────────────────────┐
                     │ 📊 Cockpit Next.js 16       │
                     │  (Observabilidade 2x2 Grid) │
                     └─────────────────────────────┘
```

* 💻 **Cursor & Windsurf**: O agente da sua IDE pesquisa, recupera e consolida memória de projeto enquanto você coda.
* 💬 **Claude Desktop**: Concede ao assistente consciência macro instantânea dos seus repositórios.
* 📊 **Cockpit Next.js 16 (`grafo-dashboard-web/`)**: Recebe Server-Sent Events de baixa latência exibindo a saúde da memória, gauges de cota e estados ativos da HSM em tempo real.
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

### Opção 2: Instalação Local via Código-Fonte e Dashboard (Para Desenvolvedores)

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
   Adicione suas chaves e limites:
   ```env
   GRAFO_LLM_API_KEY=sua_chave_aqui
   GRAFO_LLM_MODEL=gemini-2.0-flash
   CONCIERGE_BIND_ADDRESS=127.0.0.1
   GRAFO_RPM_LIMIT=60
   GRAFO_TPM_LIMIT=40000
   GRAFO_GATING_MODE=plan-only
   ```

3. **Iniciar Backend e Cockpit Concorrentemente**:
   ```bash
   cd grafo-dashboard-web
   npm install
   npm run dev:all
   ```
   * **Cockpit UI**: `http://localhost:3000`
   * **API de Telemetria**: `http://localhost:8001`
   * **Servidor FastMCP**: `http://localhost:8000`

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

## 🧪 Suíte de Testes Mestra e Auditoria E2E

O Grafo Concierge conta com uma suíte rigorosa de testes automatizados cobrindo todos os módulos de sobrevivência, transições da HSM, limites do rate governor, segurança de gating e integração E2E com **100% de status verde (326 testes coletados em 47 suítes)**:

```bash
python -m pytest tests/ -v
```

---

## 📄 Licença
Distribuído sob a Licença MIT. Consulte `LICENSE` para obter mais detalhes.
