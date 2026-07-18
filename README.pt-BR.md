[English](README.md) · Português (Brasil)
---

# 🧠 Grafo Concierge v3.8.2

**O Palácio de Memórias de Longo Prazo (LTM) para Agentes de IA e Ambientes de Desenvolvimento**

O Grafo Concierge é uma infraestrutura de memória cognitiva local de alta performance projetada para resolver a "amnésia" e a poluição de contexto dos LLMs em bases de código complexas e de grande escala. Diferente de sistemas tradicionais de RAG (Retrieval-Augmented Generation) simples, o Grafo Concierge utiliza uma arquitetura híbrida bi-temporal que combina persistência relacional SQL, busca vetorial, síntese de contexto hierárquica e um sistema de manutenção autônomo com autocorreção.

---

## 💡 O Problema que Resolvemos

Ao colaborar com agentes de IA em bases de código massivas, os modelos de IA inevitavelmente começam a "esquecer" relações de arquivos, decisões históricas ou regras de arquitetura assim que sua memória de curto prazo (janela de contexto) fica cheia.

O **Grafo Concierge** funciona como um **cérebro externo permanente**. Ele:
1. Indexa toda a estrutura do código-fonte (classes, métodos, módulos) e documentação.
2. Aprende seus hábitos, preferências e regras de arquitetura como fatos semânticos explícitos.
3. Serve como uma fonte única de verdade que alimenta trechos de contexto altamente filtrados para qualquer cliente de IA.

---

## 🔌 Integração Simultânea Multi-Cliente via MCP

O Grafo Concierge é alimentado pelo protocolo **Model Context Protocol (MCP)**. Isso permite que você execute uma única instância do servidor e a conecte **simultaneamente** a várias ferramentas e ambientes de desenvolvimento:

* 💻 **Cursor / Windsurf**: Permita que o agente da sua IDE varra, pesquise e recupere nós do grafo de memória de forma dinâmica conforme você escreve código.
* 💬 **Claude Desktop**: Dê ao seu assistente de desktop awareness completo dos seus projetos e topologias de código-fonte.
* 🤖 **Agentes Autônomos / Scripts Customizados**: Conecte scripts de orquestração personalizados (como n8n, LangChain ou rotinas de LLM customizadas) usando endpoints JSON-RPC 2.0 padrão sobre Server-Sent Events (SSE).

---

## 🌐 Backends Vetoriais Plulgáveis (Local e Qdrant Cloud)

A arquitetura suporta backends de banco de dados plugáveis para armazenamento vetorial, adaptando-se a qualquer requisito de escalabilidade:

1. **ChromaDB (Padrão - Local)**: Banco de dados local com configuração zero que armazena os embeddings no diretório local `data/`.
2. **Qdrant (Local e Nuvem)**: Alterne para o Qdrant para terceirizar o processamento de embeddings. Suporta clusters do **Qdrant Cloud** para alta disponibilidade, persistência remota e configurações multi-usuário.

---

## 🚀 Benchmarks de Performance (Colossus Protocol)

Validado sob o **Colossus Protocol**, o sistema demonstra latência sub-segundo e escalabilidade linear mesmo com volumes massivos de dados.

| Métrica | Resultado (20.000 nós) |
| --- | --- |
| **Latência de Busca (P50)** | 41.69 ms |
| **Latência de Busca (P99)** | 112.75 ms |
| **Fator de Escalabilidade** | 0.93x (Performance preservada em alto volume) |
| **Ingestão (SQLite)** | ~536 nós/segundo |
| **Ingestão (ChromaDB)** | ~914 vetores/segundo |
| **Manutenção (Janitor)** | 20.000 órfãos limpos em ~11s |

---

## 🏛️ Arquitetura do Sistema em Camadas

O Grafo Concierge é construído desde o início para ser modular, robusto e thread-safe:

* **`core/` (Sistema Nervoso)**: Orquestra o **Motor de Busca Híbrida v4** (combinando FTS5, similaridade vetorial de cosseno e sinais de grafo de centralidade/recência) e a fachada central do sistema.
* **`storage/` (Camada de Retenção)**: Garante acesso atômico e thread-safe ao banco relacional SQLite (modo WAL, fila de escrita serializada) e armazenamento vetorial.
* **`ingestion/` (Motor de Ingestão Apex)**: Varre diretórios (respeitando `.gitignore`), analisa arquivos de código-fonte em chunks semânticos de AST (Python, JS/TS, Markdown), extrai metadados e aciona a **Engrenagem de Zoom** hierárquica.
* **`agents/` (Auditoria e Reranking)**: Agentes de IA projetados para re-ranquear resultados de busca usando LLM-as-a-judge e auditar declarações de commits antes de gravá-los no ledger cognitivo.
* **`services/` (Manutenção Autônoma)**: Abriga o **Background Janitor**, que roda em uma thread isolada para lidar com decaimento temporal, reconciliar SQLite ↔ coleções vetoriais, podar vetores órfãos e reconstruir índices de busca.
* **`interface/` (Portal Operacional)**: Expõe o servidor MCP e o utilitário CLI.

---

## 🛠️ Fórmula da Busca Híbrida v4

Os scores de relevância são calculados compondo três sinais distintos para retornar apenas contextos altamente qualificados:

$$\text{Score} = (0.50 \times \text{Similaridade Vetorial}) + (0.25 \times \text{FTS5 BM25 Normalizado}) + (0.25 \times \max(\text{Recência}, \text{Centralidade}))$$

1. **Similaridade Vetorial (50%)**: Significado semântico profundo dos chunks.
2. **FTS5 BM25 (25%)**: Correspondência de tokens para assinaturas exatas de símbolos.
3. **Sinais de Grafo (25%)**:
   - **Centralidade**: Conectividade relativa de um nó (grau de entrada normalizado).
   - **Recência**: Decaimento exponencial baseado no tempo, garantindo que o contexto envelheça graciosamente:
     $$W = W_0 \cdot e^{-\lambda t}$$

---

## 🔌 Ferramentas MCP Detalhadas e Comandos CLI

### 1. Ingestão e Ciclo de Vida
* **`concierge_register`**: Registra uma nova pasta de projeto/workspace.
  * *Comando CLI*: `python -m interface.cli register --name <nome_do_projeto> [--wing <ala>] [--privacy <nivel>]`
* **`concierge_mine`**: Varre o projeto, divide arquivos em chunks, gera resumos, calcula embeddings e armazena os dados.
  * *Comando CLI*: `python -m interface.cli mine --path <caminho_absoluto> --name <nome_do_projeto>`
* **`delete_project`**: Expurgamento completo de um projeto e todos os registros relacionais/vetoriais associados.
  * *Comando CLI*: `python -m interface.cli delete --project <uuid_ou_nome>`
* **`update_project`**: Modifica detalhes do registro (nome, ala, níveis de privacidade, descrição).
* **`concierge_list_projects`**: Lista todos os projetos no banco de dados local.
  * *Comando CLI*: `python -m interface.cli projects`

### 2. Busca Avançada
* **`concierge_search`**: Executa o pipeline completo da Busca Híbrida v4.
  * *Comando CLI*: `python -m interface.cli search --query "<busca>" --project <uuid_ou_nome> [--top_k <k>]`
  * *Integração no Agente*: A principal ferramenta de busca usada para localizar arquivos relacionados, contexto e implementações anteriores.
* **`search_symbols`**: Busca assinaturas de classes/funções instantaneamente no índice FTS5.
* **`get_implementations`**: Retorna o bloco de código completo para um dado ID de símbolo sob demanda.
* **`get_callers`**: Lista todos os nós chamadores que apontam para o símbolo especificado.
* **`find_similar`**: Busca outros workspaces registrados sob a mesma ala técnica.

### 3. Contexto Cognitivo e Trajetórias
* **`concierge_wakeup`**: Reativa a memória do agente para um workspace buscando a Bússola de Contexto L2, Alas de Referência e commits recentes.
  * *Comando CLI*: `python -m interface.cli wakeup --project <uuid>`
  * *Integração no Agente*: Executado no início de uma sessão para "acordar" a memória do agente sobre a base de código.
* **`concierge_resume`**: Recupera a Bússola de Contexto (resumo macro recursivo) do projeto.
  * *Comando CLI*: `python -m interface.cli resume --project <uuid>`
* **`concierge_load`**: Carregador de nós sob demanda (Lazy Load) contendo metadados, conteúdo e relações.
* **`get_trajectories`**: Recupera o histórico detalhado bi-temporal das etapas de navegação.

### 4. Fatos e Preferências
* **`concierge_store_fact`**: Avalia e grava um fato semântico (preferências/regras) usando invalidação bi-temporal.
* **`concierge_set_memory`**: Armazena blocos de memória core do usuário (ex: `preferred_language`, `persona`).
* **`concierge_get_memory`**: Recupera blocos de memória core salvos.
* **`concierge_feedback`**: Registra feedback de busca para otimizar os pesos de relevância (Thompson Sampling Bayesiano).

---

## 🔧 Instalação e Configuração

### Pré-requisitos
* Python 3.10+
* Chave de API Google Gemini ou OpenAI (necessária para resumos e auditoria via LLM).

### Configuração
1. Clone o repositório.
2. Crie um arquivo `.env` no diretório raiz:
```env
# Configuração do Provedor de LLM
GRAFO_LLM_API_KEY=sua_chave_de_api_aqui
GRAFO_LLM_MODEL=gemini-2.5-flash

# Backend Vetorial (Chroma ou Qdrant)
GRAFO_VECTOR_BACKEND=chroma

# (Opcional) Configuração do Qdrant Cloud
# GRAFO_VECTOR_BACKEND=qdrant
# QDRANT_URL=https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-1-0.aws.cloud.qdrant.io:6333
# QDRANT_API_KEY=sua_chave_de_api_do_qdrant_cloud
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Rodando o Servidor MCP
Para inicializar o servidor do Model Context Protocol:
```bash
python -m interface.mcp_server
```

---

## 🧪 Suíte de Testes e Verificação

Para rodar a suíte de testes automatizados:
```bash
python -m pytest
```

Para rodar os testes de diagnóstico de integridade nos sistemas de memória:
```bash
python -m tests.check_brain
```

---

## 📄 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
