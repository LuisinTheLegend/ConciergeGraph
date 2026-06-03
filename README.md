# 🧠 Grafo Concierge v3.8.0
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


## 🏛️ Arquitetura: O Prédio de 10 Andares
O sistema é dividido em camadas modulares para garantir que a memória seja organizada, auditada e duradoura:

- **`core/` (O Sistema Nervoso):** Centraliza a lógica de Busca Híbrida v4 (Vetorial + FTS5 + Sinais de Grafo) e a fachada central do sistema.
- **`storage/` (A Fundação):** Gerenciamento atômico de banco de dados SQLite e persistência vetorial local via ChromaDB.
- **`ingestion/` (O Motor Apex):** Pipeline de extração de código, crawling inteligente e a Engrenagem de Zoom (L0/L1/L2) para resumos hierárquicos.
- **`agents/` (Os Guardiões):** Agentes de IA dedicados ao Reranking semântico e auditoria cirúrgica de commits, prevenindo contaminação de contexto.
- **`services/` (A Manutenção):** O Janitor, um serviço de background autônomo que lida com o decaimento temporal da informação e a limpeza vetorial.
- **`interface/` (O Portal):** Servidor nativo MCP (Model Context Protocol) para integração fluida com IDEs (Cursor/Claude) e painel CLI.

## 🛠️ Tecnologia de Busca Híbrida v4
A relevância é calculada através de uma composição ponderada que prioriza o contexto exato e a recência da informação:

1. **Busca Vetorial (50%):** Similaridade semântica profunda via embeddings.
2. **Busca FTS5 (25%):** Correspondência exata de palavras-chave (BM25).
3. **Sinais de Grafo (25%):** Maior valor entre a Recência temporal e a Centralidade do nó (peso relacional).

A recência segue a fórmula de decaimento exponencial, garantindo que a memória "envelheça" graciosamente e dê espaço para novos fatos com o tempo:
$$W = W_0 \cdot e^{-\lambda t}$$

## 🔧 Instalação e Uso

**Pré-requisitos:**
- Python 3.10+
- Chave de API (Google Gemini / OpenAI) para a Engrenagem de Zoom e Auditores.

**Configuração:**
1. Clone o repositório.
2. Crie um arquivo `.env` na raiz:
```env
GRAFO_LLM_API_KEY=sua_chave_aqui
GRAFO_LLM_MODEL=gemini-2.0-flash
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```

**Execução:**
Para iniciar o servidor MCP e expor as ferramentas de memória:
```bash
python -m interface.mcp_server
```

## 🧪 Suíte de Testes (Absolute Solidity)
O projeto conta com o **Stress Test v2**, uma suíte exaustiva cobrindo 8 dimensões de estresse, concorrência, integridade e isolamento (Strict Scoping).

Para rodar os exatos **262 testes automatizados** e os benchmarks:
```bash
# Validação Estrutural e de Agentes
python tests/stress_test_v2_parte1.py
python tests/stress_test_v2_parte2.py
python tests/stress_test_v2_parte3.py

# Benchmark de Big Data
python tests/colossus_benchmark.py
```

## 📄 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.3