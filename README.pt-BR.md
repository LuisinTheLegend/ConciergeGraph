[English](README.md) · Português (Brasil)
---

# 🧠 Grafo Concierge v3.8.2

**O Palácio de Memórias Cognitivas de Longo Prazo (LTM) Open-Source para Agentes de IA, IDEs e Ambientes de Desenvolvimento**

[![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
[![Suporte Docker](https://img.shields.io/badge/Docker-Pronto-blue)](docker-compose.yml)

O Grafo Concierge é um servidor de memória cognitiva local de alta performance projetado para resolver a "amnésia" dos LLMs e a poluição de contexto. Diferente de scripts simples de RAG (Retrieval-Augmented Generation), o Grafo Concierge funciona como um motor de memória bi-temporal com auto-recuperação que combina persistência SQL relacional, busca vetorial, síntese hierárquica de contexto (Zoom Gear) e manutenção autônoma em background (Janitor Loop).

---

## 💡 O que é o Grafo Concierge? (Para Leigos e Devs Seniores)

### 👶 Explicação Simples (A Analogia)
> Imagine contratar um engenheiro de software sênior brilhante que sofre de perda de memória de curto prazo. Toda vez que você abre um novo chat no Cursor ou no Claude Desktop, ele esquece a estrutura do seu projeto, os padrões do seu código e as decisões arquiteturais tomadas ontem.
>
> **O Grafo Concierge é o cérebro externo permanente desse engenheiro.** Conectado de forma transparente pelo protocolo padrão Model Context Protocol (MCP), seu assistente de IA consulta, aprende e atualiza esse cérebro automaticamente em milissegundos — sem que você precise ficar copiando e colando trechos de código manualmente!

### 🧙‍♂️ Aprofundamento Técnico (Para Engenheiros)
O Grafo Concierge é um daemon local ou de VPS que oferece:
1. **Persistência Bi-Temporal de Fatos**: Registra fatos semânticos e entidades de código rastreando tempo válido e tempo de transação.
2. **Motor de Busca Híbrida v4**: Equilibra similaridade vetorial densa (50%), busca exata de tokens/símbolos via SQLite FTS5 BM25 (25%) e sinais de grafo (25% combinando centralidade e decaimento temporal exponencial $W = W_0 \cdot e^{-\lambda t}$).
3. **Ingestão Apex Sensível a AST**: Varre e analisa arquivos em Python, TypeScript, JS, Go, Rust, Java, C/C++ criando nós estruturais de AST com delta-hashing (SHA-256) para ignorar códigos não modificados.
4. **Manutenção Autônoma com Auto-Recuperação (Janitor Loop)**: Executa em uma thread isolada para reconciliar tabelas do SQLite com coleções vetoriais, podar embeddings órfãos e aplicar decaimento em contextos inativos.

---

## 🛡️ Vantagens Arquiteturais (Soluções para Armadilhas de Memória)

| Problema em Memórias Tradicionais | Como o Grafo Concierge v3.8.2 Resolve |
| :--- | :--- |
| **"Falso Negativo da Gaveta Incorreta"** | **Escopo Dinâmico com Fallback**: A busca recorre automaticamente a Alas de Referência (`all_wings=True`) se a relevância local ficar abaixo do limiar. Sem bloqueios rígidos. |
| **Memórias Obsoletas & Contradições** | **Invalidação Bi-Temporal & Decaimento Exponencial**: `concierge_store_fact` invalida fatos substituídos com timestamps de validade/transação enquanto o Janitor aplica decaimento $W = W_0 \cdot e^{-\lambda t}$. |
| **Latência de Consulta Dupla (I/O)** | **Latência Sub-40ms (Benchmark Colossus)**: Utiliza `SerializedWriteQueue` com SQLite em modo WAL e leituras thread-local para resposta ultra-rápida em P50 (41ms). |
| **Bloqueio por SDK Proprietária** | **PadrãoMCP Nativo**: Opera via Model Context Protocol (JSON-RPC/SSE) da Anthropic. Sem dependência de fornecedor; funciona no Cursor, Claude Desktop, LangChain ou scripts. |

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
                     │ 🧠 Grafo Concierge Server   │
                     │  (Local / VPS - Porta 8000) │
                     └─────────────────────────────┘
```

* 💻 **Cursor e Windsurf**: O agente da sua IDE varre, busca e recupera memórias do projeto dinamicamente enquanto você programa.
* 💬 **Claude Desktop**: Dá ao seu assistente de desktop conhecimento macro imediato de todas as suas bases de código.
* 🤖 **Agentes Autônomos e Workflows**: Conecte rotinas em n8n, LangChain, AutoGen ou scripts Python customizados via endpoints SSE.

---

## ⚡ Guia de Início Rápido (3 Minutos)

### Opção 1: Instalação via PyPI (Recomendado para a maioria dos usuários)

```bash
# Instalar o pacote Grafo Concierge e o CLI global
pip install concierge-graph

# Atualizar ou Desinstalar a qualquer momento
pip install concierge-graph --upgrade # para atualizar
pip uninstall concierge-graph         # para desinstalar
```

### Opção 2: Configuração Local via Código-Fonte (Para Desenvolvedores)

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
   Insira sua chave de API do Gemini ou OpenAI:
   ```env
   GRAFO_LLM_API_KEY=sua_chave_gemini_aqui
   GRAFO_LLM_MODEL=gemini-2.0-flash
   ```

3. **Iniciar o Servidor MCP**:
   ```bash
   concierge-mcp
   # ou: python main.py
   ```

---

### Opção 2: Implantação em VPS (Direta via `pip` ou via `Docker`) 🌐

Você pode hospedar o Grafo Concierge em qualquer VPS Linux (Ubuntu/Debian) de duas formas:

#### A) Instalação Direta (Nativa via `pip`)
```bash
# 1. Instalar diretamente na VPS
pip install concierge-graph

# 2. Configurar variáveis de ambiente (ou criar um arquivo .env)
export GRAFO_LLM_API_KEY="sua_chave_gemini"
export GRAFO_HOST="0.0.0.0"
export GRAFO_API_KEY="sua_chave_remota_segura"

# 3. Iniciar o servidor
concierge-mcp
```

#### B) Instalação Containerizada (Docker 🐳)
```bash
# Definir a chave de autenticação no .env
echo "GRAFO_API_KEY=sua_chave_remota_segura" >> .env

# Subir os containers em background
docker compose up -d
```

---

## 💻 Configuração em 1 Clique para IDEs e Claude Desktop

### Para Claude Desktop (`claude_desktop_config.json`)
Adicione o Grafo Concierge ao seu arquivo de configuração:

```json
{
  "mcpServers": {
    "concierge-graph": {
      "command": "python",
      "args": ["-m", "interface.mcp_server"],
      "cwd": "/caminho/para/GrafoConcierge",
      "env": {
        "GRAFO_LLM_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

### Para VPS Remota / Conexões SSE (Cursor / Scripts Customizados)
Quando executado em um servidor remoto:
```json
{
  "mcpServers": {
    "concierge-graph": {
      "url": "http://ip-da-sua-vps:8000/sse",
      "headers": {
        "Authorization": "Bearer sua_chave_remota_segura"
      }
    }
  }
}
```

---

## 🚀 Benchmarks de Desempenho (Colossus Protocol)

Testado contra 20.000 nós de código sob o **Colossus Protocol**:

| Métrica | Resultado (20.000 nós) |
| --- | --- |
| **Latência de Busca (P50)** | 41.69 ms |
| **Latência de Busca (P99)** | 112.75 ms |
| **Fator de Escalabilidade** | 0.93x (Desempenho linear preservado em alto volume) |
| **Vazão de Ingestão (SQLite)** | ~536 nós/segundo |
| **Vazão de Ingestão (ChromaDB)** | ~914 vetores/segundo |
| **Manutenção em Background (Janitor)** | 20.000 vetores órfãos limpos em ~11s |

---

## 🛠️ Fórmula da Busca Híbrida v4

Os scores de relevância são calculados compondo três sinais distintos:

$$\text{Score} = (0.50 \times \text{Similaridade Vetorial}) + (0.25 \times \text{FTS5 BM25 Normalizado}) + (0.25 \times \max(\text{Recência}, \text{Centralidade}))$$

1. **Similaridade Vetorial (50%)**: Captura significado semântico profundo usando embeddings densos.
2. **FTS5 BM25 (25%)**: Correspondência de tokens exatos para nomes de funções, classes e símbolos.
3. **Sinais de Grafo (25%)**:
   - **Centralidade**: Conectividade relativa de um nó (grau de entrada normalizado).
   - **Recência**: Decaimento exponencial baseado no tempo, garantindo envelhecimento suave do contexto:
     $$W = W_0 \cdot e^{-\lambda t}$$

---

## 🔌 Referência Rápida das Ferramentas MCP

* **`concierge_mine`**: Varre um diretório, extrai nós de código (AST), gera tags e resumos hierárquicos (L0/L1/L2).
* **`concierge_search`**: Executa a Busca Híbrida v4 em todos os projetos indexados.
* **`concierge_wakeup`**: Reativa a consciência do agente ao iniciar a sessão retornando a Bússola de Contexto, alas de referência e commits recentes.
* **`concierge_resume`**: Recupera a Bússola de Contexto macro do projeto (ideal para injeção em system prompts).
* **`concierge_load`**: Carregador sob demanda (lazy load) do conteúdo completo, conexões e dependências de um nó.
* **`concierge_commit`**: Registra alterações arquiteturais auditadas no ledger cognitivo.
* **`concierge_store_fact`**: Armazena preferências do usuário e regras com invalidação bi-temporal.

---

## 🛠️ Referência dos Subcomandos Globais do CLI (`concierge`)

Após executar `pip install concierge-graph`, dois comandos globais no terminal são instalados via `pyproject.toml`:
1. **`concierge-mcp`**: Inicializa o daemon do servidor FastMCP.
2. **`concierge`**: Utilitário CLI multifuncional que suporta os seguintes subcomandos:

```bash
# 1. Registrar um novo workspace/projeto
concierge register --name meu-projeto --wing backend --privacy PUBLIC

# 2. Minerar / Ingerir um diretório de código na memória
concierge mine --path /caminho/para/codigo --name meu-projeto

# 3. Executar Busca Híbrida v4 na memória indexada
concierge search --query "middleware de autenticação" --project meu-projeto

# 4. Reativar consciência do agente (Bússola + Alas + Commits)
concierge wakeup --project meu-projeto

# 5. Recuperar o resumo macro da Bússola de Contexto
concierge resume --project meu-projeto

# 6. Registrar um commit arquitetural auditado no ledger
concierge commit --project <uuid> --phase build --technical_changes "Adicionado JWT"

# 7. Carregar um único nó sob demanda (Lazy Load)
concierge load --node_id 42

# 8. Exibir a saúde do sistema, contadores e status dos bancos
concierge status

# 9. Listar todos os projetos registrados no banco local
concierge projects

# 10. Expurgar um projeto e todos os registros relacionais e vetoriais
concierge delete --project meu-projeto
```

---

## 🧪 Suíte de Testes e Diagnóstico

Executar todos os testes de unidade e estresse:
```bash
python -m pytest
```

Executar diagnóstico de integridade da memória:
```bash
python -m tests.check_brain
```

---

## 📄 Licença
Distribuído sob a Licença MIT. Veja `LICENSE` para mais informações.

