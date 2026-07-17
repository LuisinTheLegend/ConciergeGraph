### 🧭 ACTIVE BLUEPRINT: PATCH BACKEND-6.1 (EXPANSÃO DO ARSENAL MCP)
#### 🟢 STATUS DA FASE: EM EXECUÇÃO

#### 🎯 OBJETIVO TÉCNICO
Expor de forma segura as funcionalidades primárias do Cérebro (Backend) como ferramentas no Servidor MCP (`interface/mcp_server.py`). O objetivo é garantir ao agente total autonomia sobre o ciclo de vida dos projetos, telemetria cognitiva e manutenção emergencial, mantendo as operações de baixo nível e de infraestrutura estritamente ocultas.

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (DÍVIDA TÉCNICA ZERO)

**1. Gerenciamento do Ciclo de Vida do Projeto (Exposição Obrigatória)**
*   **`delete_project(project_uuid)`:** Criar ferramenta MCP que remova fisicamente um projeto e todos os registros atrelados, apagando os vetores no banco vetorial antes de disparar a exclusão em cascata no SQLite [1].
*   **`update_project()`, `add_reference_wing()` e `remove_reference_wing()`:** Criar ferramentas MCP para alterações cadastrais e conexões de conhecimento, permitindo alterar campos do projeto e associar alas recomendadas [2].

**2. Busca Avançada e Telemetria (Exposição Obrigatória)**
*   **`find_similar(project_uuid, limit)`:** Expor esta ferramenta para permitir que a IA busque outros projetos no banco de dados que compartilham o mesmo domínio de especialização técnica [1].
*   **`get_trajectories(project_uuid)`:** Expor a recuperação do histórico detalhado de trajetórias cognitivas para que o agente possa ler os seus passos de navegação anteriores [3].

**3. Administração Vetorial Emergencial (Exposição Obrigatória)**
*   **`count_embeddings()` e `reset_collection()`:** Criar ferramentas de diagnóstico para retornar a contagem exata de vetores e, em caso de necessidade de reparo, efetuar a destruição total e recriação da coleção física de vetores [4].

**4. Zona de Bloqueio de Segurança (O que NÃO expor ao MCP)**
*   É estritamente **proibido** expor métodos de manipulação cirúrgica da AST, como `create_edge()`, `delete_edge()` ou `delete_node()`, pois a criação de arestas deve ser delegada exclusivamente ao parser estático [2].
*   É estritamente **proibido** expor os serviços autônomos do Janitor (como `clean_stale_data()` ou `vacuum_sqlite()`), pois eles operam em background para otimização de espaço e remoção de dados inativos [5].
*   É **proibido** expor métodos de cálculos internos como `decay_trajectory()` [3] ou a recuperação de vetores matemáticos puros via `get_embeddings_batch()` [4].
