### 🧭 ACTIVE BLUEPRINT: PATCH ARQUITETURAL - ERRADICAÇÃO DE HARDCODES (MCP)
#### ✅ STATUS DA FASE: CONCLUÍDO

#### 🎯 OBJETIVO TÉCNICO
Localizar e erradicar qualquer caminho absoluto (hardcoded) presente no código-fonte do Servidor MCP e nas configurações do Grafo Concierge. O sistema deve ser 100% portátil, descobrindo seus diretórios dinamicamente em tempo de execução.

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (DÍVIDA TÉCNICA ZERO)

**1. Varredura e Substituição Dinâmica**
*   **Ação:** Inspecionar os arquivos de inicialização do servidor MCP (ex: `mcp_server.py`, `config.py` ou `main.py`) e identificar strings de caminhos estáticos (ex: `C:\...`).
*   **Contrato:** Todos os caminhos de arquivos, bancos de dados SQLite ou diretórios de persistência DEVEM ser resolvidos usando a biblioteca nativa `pathlib`.
*   **Padrão Exigido:** Utilizar `Path(__file__).parent.resolve()` (ou similar) para ancorar o caminho base dinamicamente, construindo os subdiretórios a partir dele.

**2. Portabilidade Transparente**
*   **Contrato:** O comportamento do servidor não pode ser alterado. Os bancos de dados e logs devem continuar sendo salvos nas mesmas pastas relativas de sempre, apenas a forma matemática de chegar até elas no código é que deve mudar.

**3. Validação de Inicialização**
*   **Ação:** Após a refatoração, o servidor MCP deve conseguir inicializar perfeitamente e expor as 17 ferramentas sem erros de "File Not Found".
