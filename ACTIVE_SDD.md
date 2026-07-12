### 🧭 ACTIVE BLUEPRINT: OPERATION LIGHTWEIGHT MODE (WAVE 6)
#### ⚫ STATUS: CONCLUÍDO

#### OBJETIVO TÉCNICO
Implementar o "Modo Lightweight" (Versão 4.0) para permitir que o Grafo Concierge opere em hardwares com recursos estritamente limitados. O sistema deverá ser capaz de desativar completamente a inicialização da infraestrutura vetorial pesada e rotear todas as pesquisas de forma graciosa para o motor de busca textual do SQLite (FTS5).

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (PATCHES DE ARQUITETURA)

**1. A Chave de Ignição (Toggle de Configuração)**
*   **Arquivos Alvo:** `.env` (template) e carregador de configurações globais.
*   **Ação:** Criar a variável de ambiente `GRAFO_LIGHTWEIGHT_MODE=false` (padrão).
*   **Contrato:** Quando configurada para `true`, essa variável deve ser propagada para o ciclo de inicialização do sistema para alterar o comportamento da *engine*.

**2. Desligamento do Motor Vetorial (Economia de RAM)**
*   **Arquivos Alvo:** Inicializador do `EmbeddingManager` e gerenciadores de banco de dados (`Qdrant`/`ChromaDB`).
*   **Ação:** Impedir o carregamento da infraestrutura pesada na memória.
*   **Contrato:** Se `GRAFO_LIGHTWEIGHT_MODE` for verdadeiro, o sistema deve ignorar (fazer bypass) a instanciação do modelo local `sentence-transformers` (poupando ~500MB de RAM) e não deve inicializar nem conectar aos clientes de banco de dados vetoriais.

**3. Fallback Gracioso de Busca (Roteamento para FTS5)**
*   **Arquivos Alvo:** `Orchestrator`, `ProbabilisticRetriever` (ou classe de busca) e Handlers do MCP Server (ferramentas de search).
*   **Ação:** Redirecionar as requisições de busca vetorial para a busca textual.
*   **Contrato:** Interceptar as chamadas de busca semântica. Se o modo *lightweight* estiver ativo (vetores indisponíveis), rotear as *queries* diretamente para o motor FTS5 (Full-Text Search) do SQLite. A API e a resposta do retriever devem manter o mesmo formato esperado pelo LLM, operando de forma transparente para o usuário final.
