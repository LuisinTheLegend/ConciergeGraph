🧭 ACTIVE BLUEPRINT: INDEXAÇÃO AST (TREE-SITTER) & NAVEGAÇÃO SEMÂNTICA MCP
🟢 STATUS: EM EXECUÇÃO
1. ESPECIFICAÇÃO DE ARQUITETURA: FIM DO GREP CEGO
Componentes Alvo: concierge_mine.py (Ingestão), logic.py (Mapeamento Relacional) e mcp_server.py (Ferramentas Expostas).
Objetivo: Substituir a varredura textual bruta pela análise de Árvore de Sintaxe Abstrata (AST) usando py-tree-sitter-languages
, mapeando definições e referências (arestas) no banco SQLite para alimentar o cálculo de centralidade e disponibilizar buscas estruturais via MCP
.
📋 1.1. O Motor de Ingestão AST (concierge_mine.py & logic.py)
Tree-sitter Parsing: O processo de ingestão de arquivos de código (Python, TS, JS, Go, Rust, etc.) deve ser interceptado. Em vez de fazer o chunking cego por limite de caracteres, o motor deve usar o py-tree-sitter-languages para fazer o parsing do arquivo
.
Extração de Nós (Nodes): Cada Definição de Classe e Função deve ser extraída como um fragmento independente e injetada na tabela nodes (cujo gatilho FTS5 já sincronizará o nome do símbolo automaticamente para buscas instantâneas)
.
Mapeamento de Dependências (Edges): O parser deve identificar referências e chamadas de função (ex: Classe A chamando Função B) e inserir esses relacionamentos na tabela relacional edges. Isso alimentará a nossa fórmula nativa de centralidade (PageRank baseado em in_degree)
.
🔌 1.2. A Expansão do Servidor MCP (mcp_server.py)
O servidor MCP existente do Grafo Concierge deve ser expandido para registrar três novas ferramentas inspiradas na arquitetura CodeRLM, utilizando as tabelas WAL read-only
:
search_symbols(query): Realiza um SELECT rápido utilizando a extensão em C do SQLite FTS5 (nodes_fts) para encontrar a assinatura exata de uma classe ou função e retornar seu arquivo e ID
.
get_implementations(symbol_id): Retorna o bloco de código exato da AST armazenado no nó, evitando o carregamento do arquivo inteiro na memória
.
get_callers(symbol_id): Consulta a tabela edges para encontrar e retornar todos os nós (arquivos/funções) que chamam a função especificada
.
