# 🧠 Grafo Concierge v3.8.2
**O Palácio de Memórias de Longo Prazo (LTM) para Agentes de IA**

O Grafo Concierge é uma infraestrutura de memória cognitiva local projetada para resolver a "amnésia" dos LLMs em projetos complexos. Diferente de sistemas de RAG simples, ele utiliza uma arquitetura robusta que combina persistência relacional, busca vetorial, síntese hierárquica e um sistema de manutenção autônomo.

## 💡 O Problema que Resolvemos (Em Termos Simples)
Imagine que você está construindo um software gigante com a ajuda de uma Inteligência Artificial. Com o passar do tempo, a IA começa a "esquecer" como os arquivos se conectam ou as regras que vocês definiram no passado, simplesmente porque a "memória de curto prazo" (context window) dela lotou.

O **Grafo Concierge** age como um **cérebro externo e permanente** para a IA. Ele rastreia todo o seu projeto, entende as conexões entre os arquivos e sempre entrega à IA exatamente a informação que ela precisa para trabalhar, sem esquecer o passado.

## 🚀 Performance Colossal (Benchmarks)
Validado pelo **Colossus Protocol**, o sistema demonstrou escalabilidade linear e latência sub-segundo em ambientes de Big Data.

| Métrica | Resultado (20.000 nós) |
| --- | --- |
| **Latência de Busca (P50)** | 41.69 ms |
| **Latência de Busca (P99)** | 112.75 ms |
| **Fator de Escalabilidade** | 0.93x (Performance preservada em alto volume) |
| **Ingestão (SQLite)** | ~536 nós/segundo |
| **Ingestão (ChromaDB)** | ~914 vetores/segundo |
| **Manutenção (Janitor)** | 20.000 órfãos limpos em ~11s |

### Entendendo os Termos e Métricas
- **P50 (Percentil 50 / Mediana):** Indica que 50% das buscas retornaram resultados neste tempo ou mais rápido. É a latência "típica" sentida pelo usuário.
- **P99 (Percentil 99):** Indica que 99% das buscas foram mais rápidas que este tempo. É a métrica que representa o "pior caso" (worst-case scenario), provando a estabilidade do sistema sob pressão.
- **Nós (Nodes):** São as unidades fundamentais de memória no Grafo. Um nó não é apenas texto: ele pode representar um fato arquitetural, uma regra de negócio, um arquivo de código ou uma decisão tomada, tudo interligado.
- **Engrenagem de Zoom (L0/L1/L2):** Nosso algoritmo autônomo de compressão de contexto hierárquico.
  - **L0 (Micro):** Resumo detalhado de um único arquivo ou função.
  - **L1 (Meso):** Síntese de vários L0, descrevendo o propósito de um módulo ou diretório inteiro.
  - **L2 (Macro - Bússola):** Visão arquitetural global do projeto. É usada para dar o contexto inicial perfeito aos Agentes de IA sem estourar o limite de tokens (Context Window).


## 🏛️ Arquitetura: Divisão de Camadas
O sistema é dividido em camadas modulares para garantir que a memória seja organizada, auditada e duradoura:

- **`core/` (O Sistema Nervoso):** Centraliza a lógica de Busca Híbrida v4 (Vetorial + FTS5 + Sinais de Grafo) e a fachada central do sistema.
- **`storage/` (A Fundação):** Gerenciamento atômico thread-safe de conexões de leitura SQLite e escrita serializada isolada (WAL mode), além de persistência vetorial via ChromaDB.
- **`ingestion/` (O Motor Apex):** Pipeline de extração de código, crawling inteligente, detecção de AST multilinguagem compatível e a Engrenagem de Zoom (L0/L1/L2).
- **`agents/` (Os Guardiões):** Agentes de IA dedicados ao Reranking semântico e auditoria cirúrgica de commits, prevenindo contaminação de contexto.
- **`services/` (A Manutenção):** O Janitor, um serviço de background autônomo que lida com o decaimento temporal e o controle de histórico de manutenção livre de memory leaks.
- **`interface/` (O Portal):** Servidor nativo MCP (Model Context Protocol) estendido para o ciclo de vida completo de projetos e painel CLI.

## 🛠️ Tecnologia de Busca Híbrida v4
A relevância é calculada através de uma composição ponderada que prioriza o contexto exato e a recência da informação:

1. **Busca Vetorial (50%):** Similaridade semântica profunda via embeddings.
2. **Busca FTS5 (25%):** Correspondência exata de palavras-chave (BM25 normalizado).
3. **Sinais de Grafo (25%):** Maior valor entre a Recência temporal e a Centralidade do nó (peso relacional).

A recência segue a fórmula de decaimento exponencial, garantindo que a memória "envelheça" graciosamente e dê espaço para novos fatos com o tempo:
$$W = W_0 \cdot e^{-\lambda t}$$

## 🔧 Instalação e Uso

**Pré-requisitos:**
- Python 3.10+
- Chave de API (Google Gemini / OpenAI) para a Engrenagem de Zoom e Auditores.

**Configuração:**
1. Clone o repositório.
2. Crie um arquivo `.env` na raiz (o arquivo está ignorado de forma segura no `.gitignore`):
```env
GRAFO_LLM_API_KEY=sua_chave_aqui
GRAFO_LLM_MODEL=gemini-2.5-flash
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```

**Execução:**
Para iniciar o servidor MCP e expor todas as ferramentas de memória cognitiva e ciclo de vida ao LLM:
```bash
python -m interface.mcp_server
```


## 🔌 Ferramentas Model Context Protocol (MCP)
O servidor do Grafo Concierge expõe um conjunto robusto de ferramentas via protocolo MCP para permitir que agentes de IA (como Claude no Cursor, Claude Desktop ou Copilot) interajam nativamente com o grafo de memória.

### 🛠️ Diretório de Ferramentas e Padrões de Uso

#### 1. Ingestão e Ciclo de Vida
* **`concierge_register`**: Registra uma nova pasta de projeto e define sua política de privacidade (`PUBLIC`, `INTERNAL`, `RESTRICTED`).
  * *Uso CLI*: `python -m interface.cli register --name <nome_do_projeto> [--wing <ala>] [--privacy <nivel>]`
  * *Uso no Agente*: Chamado nativamente quando o agente detecta um novo workspace para indexação.
* **`concierge_mine`**: Ingere arquivos, executa análise semântica e AST, gera resumos hierárquicos L0/L1/L2, calcula embeddings vetoriais e sincroniza o banco SQLite com o ChromaDB.
  * *Uso CLI*: `python -m interface.cli mine --path <caminho_absoluto> --name <nome_do_projeto>`
  * *Uso no Agente*: Disparado após alterações no código ou para construir a base inicial de contexto.
* **`delete_project`**: Expurgamento físico de um projeto e todos os seus nós, arestas, commits e embeddings associados.
  * *Uso CLI*: `python -m interface.cli delete --project <uuid_ou_nome>`
* **`update_project`**: Atualiza metadados do projeto (nome da pasta, ala primária, nível de privacidade ou descrição).
* **`concierge_list_projects`**: Lista todos os projetos cadastrados no banco de dados de memória.
  * *Uso CLI*: `python -m interface.cli projects`

#### 2. Busca e Recuperação Avançada
* **`concierge_search`**: Busca Híbrida v4 combinando similaridade vetorial (cosseno), frequência FTS5 (BM25) e sinais de grafo (centralidade e recência temporal) para retornar os trechos de código ou fatos mais relevantes.
  * *Uso CLI*: `python -m interface.cli search --query "<texto>" --project <uuid> [--top_k <k>]`
  * *Uso no Agente*: Ferramenta principal de busca usada para localizar trechos de código, documentações e regras de negócio.
* **`search_symbols`**: Busca assinaturas de classes, métodos e funções no índice de texto completo FTS5.
* **`get_implementations`**: Carrega o bloco de código AST correspondente ao ID de um símbolo sob demanda.
* **`get_callers`**: Navega pelas arestas de dependência do grafo para retornar quem chama um determinado símbolo.
* **`find_similar`**: Busca outros projetos pertencentes à mesma ala técnica (domínio de especialização técnica).

#### 3. Contexto Cognitivo e Trajetórias
* **`concierge_wakeup`**: Reativa a consciência do agente retornando a Bússola de Contexto, Alas de Referência, commits recentes e estatísticas do sistema.
  * *Uso CLI*: `python -m interface.cli wakeup --project <uuid>`
  * *Uso no Agente*: Executado no início de uma sessão de trabalho para que o agente resgate a memória e contexto do projeto.
* **`concierge_resume`**: Obtém a Bússola de Contexto (resumo global L2) do projeto.
  * *Uso CLI*: `python -m interface.cli resume --project <uuid>`
* **`concierge_load`**: Carregador de nós sob demanda (Lazy Load) contendo código completo, metadados e relações ativas.
* **`get_trajectories`**: Recupera o histórico detalhado de trajetórias cognitivas (passos de navegação bi-temporal).

#### 4. Memória Episódica e Preferências
* **`concierge_store_fact`**: Avalia e insere um fato semântico via SemanticExtractor, tomando decisões de ADD/UPDATE/DELETE/NOOP.
* **`concierge_set_memory`**: Armazena blocos persistentes de memória core do usuário/sessão (ex: linguagem preferida, persona, diretrizes de estilo).
* **`concierge_get_memory`**: Consulta blocos de memória core gravados.
* **`concierge_feedback`**: Registra feedback de utilidade sobre fatos semânticos para alimentar o Thompson Sampling (aprendizado bayesiano).

#### 5. Utilitários do Sistema
* **`get_full_topology`**: Retorna conexões de nós e arestas em formato leve para o Dashboard Web 3D.
* **`concierge_status`**: Provê telemetria do ChromaDB, estatísticas de nós e logs do Janitor Service.
  * *Uso CLI*: `python -m interface.cli status`
* **`reset_collection`**: Ferramenta de emergência para reconstruir fisicamente a coleção de vetores.

## 🧪 Suíte de Testes & Integração Contínua (Absolute Solidity)
O projeto conta com uma suíte exaustiva de testes integrados e unitários com descoberta automática nativa configurada em `pyproject.toml` e pipeline de CI via **GitHub Actions** (`ci.yml`).

Para rodar os testes da suíte automatizada:
```bash
python -m pytest
```

Para rodar o diagnóstico completo de integridade e sanitização da memória local:
```bash
python tests/check_brain.py
```

## 📄 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
