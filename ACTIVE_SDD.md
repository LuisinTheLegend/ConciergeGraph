🧭 ACTIVE BLUEPRINT: FASE 2 - GRAPHRAG RELACIONAL LOCAL E SUMARIZAÇÃO
🟢 STATUS DA FASE: EM EXECUÇÃO
🔑 CREDENCIAIS DE MEMÓRIA (MCP)
Nome do Projeto: Grafo Concierge
Project UUID Obrigatório: 9c36c408-ced0-4f35-948d-51c4df85b4ed
PREENCHIMENTO DO MOTOR DE SUMARIZAÇÃO (Repositório: Grafo Concierge)
Componente Alvo Principal: services/janitor.py (Background Janitor).
Componente Secundário Sugerido: Integração com a lógica de busca do SQLite e atualização de payload no Qdrant local.
Contrato da Fase 2 (GraphRAG Relacional Local Pipeline):
Detecção de Comunidades (Algoritmo de Leiden): O Janitor deve executar queries relacionais hierárquicas complexas através de WITH RECURSIVE diretamente na tabela de arestas (edges) e usar o SQLite FTS5 para agrupar super-nós com grau de entrada (in_degree) ≥10.
Sumarização e Injeção no Qdrant: O Janitor sintetizará resumos dessas macro-estruturas lógicas e injetará os IDs de comunidade nos payloads metadados do Qdrant local de forma direta.
Heurística de Idle-Lock (Proteção de Concorrência): Este processo pesado deve ser ativado exclusivamente durante estados de ociosidade do sistema (Event Bus vazio). Se uma requisição MCP externa (como uma chamada do Nexus Agent) der entrada, o Janitor deve sofrer uma suspensão imediata (yield/suspend), limpando a fila para liberar o banco.
Preservação da Regra de Ouro: Garantir a criação de testes rigorosos e mocks assegurando que a suite mantenha 100% de sucesso sem hardcodes de disco.