### 🧭 ACTIVE BLUEPRINT: POLIMENTO DO GRAFO CONCIERGE (MCP SERVER)
#### 🟢 STATUS DA FASE: EM EXECUÇÃO

#### 1. DIRETRIZES DE ENGENHARIA - MINERAÇÃO TIPADA (FIM DO MODO "DUMB")
*   **Problema Atual:** As ferramentas de navegação simbólica do MCP (`nexus_search_symbols`, `nexus_get_implementations`) retornam vazias porque a ferramenta `concierge_mine` está salvando todos os nós minerados com o tipo genérico `node_type="FACT"` [1, 2].
*   **Contrato de Implementação:** Refatorar o pipeline de extração na ferramenta de mineração (`concierge_mine` ou classe equivalente). Utilizar a Árvore Sintática (AST) via Tree-sitter para identificar e rotular corretamente as estruturas de código. Os nós devem ser salvos no SQLite com seus tipos específicos, como `CLASS`, `FUNCTION`, `METHOD`, eliminando o fallback genérico [2].

#### 2. DIRETRIZES DE ENGENHARIA - REATIVAÇÃO DE EMBEDDINGS (BUSCA SEMÂNTICA)
*   **Problema Atual:** A busca híbrida está operando 100% no texto exato (FTS5). O relatório aponta que `vector_score` retorna sempre `0.0` e `embeddings_stored` é `0` [2]. A pipeline de embeddings está desabilitada.
*   **Contrato de Implementação:** Reativar e configurar o pipeline de geração de vetores (na ingestão de chunks). O código deve processar os pedaços de texto e chamar o modelo de embeddings (utilizar preferencialmente a biblioteca `sentence-transformers` com `all-MiniLM-L6-v2` local, ou a API designada no projeto) e garantir que esses arrays vetoriais sejam persistidos no backend do banco de dados vetorial (`vector_backend` / Qdrant local), permitindo que a busca semântica do `concierge_search` volte a calcular a similaridade de cosseno.
