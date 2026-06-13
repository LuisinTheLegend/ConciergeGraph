🧭 ACTIVE BLUEPRINT: URGÊNCIA 1 - PARTE C (CONECTORES LÓGICOS TEMPORAIS)
🟢 STATUS DA FASE: EM EXECUÇÃO
ATUALIZAÇÃO DOS MUTADORES CRUD (Repositório: Grafo Concierge)
Componente Alvo: storage/relational_db.py (ou o módulo correspondente que abriga as funções de inserção/mutação no Grafo Concierge)
.
Provedor Sugerido no Antigravity: Claude 3.5 Sonnet ou Opus 4.7 (devido à precisão em ler contratos lógicos via MCP e mapear os novos parâmetros sem quebrar as transações puras).
Contrato de Alteração de Lógica de Inserção:
Mapeamento de Novos Parâmetros em insert_node: Atualizar a assinatura da função e a query SQL de inserção/atualização (UPSERT/ON CONFLICT) para receber e persistir os campos opcionais valid_from_commit e valid_to_commit.
Mapeamento de Novos Parâmetros em insert_edge: Atualizar a assinatura da função e a query SQL para receber e gravar valid_from_commit, valid_to_commit e confidence_tag. Garantir que confidence_tag possua o valor padrão (fallback) interno de 'EXTRACTED' caso o payload venha vazio, respeitando a trava (CHECK constraint) do banco de dados
.
Preservação da Regra de Ouro (Single-Writer Thread): É estritamente proibido adicionar lógicas de commit(), rollback() ou cursor.close() dentro dessas funções. Elas devem permanecer como funções puras que aceitam o parâmetro obrigatório conn: sqlite3.Connection e apenas executam as instruções, delegando o escopo da transação ao barramento de eventos (Event Bus)
.
Atualização de Leitura (Opcional): Atualizar as funções de busca e recuperação (get_node, get_edge) para que os dicionários retornados incluam os novos campos temporais e de confiança, permitindo que o Agente Master consuma essas informações no futuro.