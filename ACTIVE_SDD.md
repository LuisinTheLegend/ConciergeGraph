🧭 ACTIVE BLUEPRINT: URGÊNCIA 1 - PARTE A (GRAFO TEMPORAL & TAGS)
🟢 STATUS DA FASE: EM EXECUÇÃO
MUTAÇÃO DO SCHEMA RELACIONAL (Repositório: Grafo Concierge)
Componente Alvo: storage/schema.py (Script de inicialização do banco de dados DDL).
Provedor Sugerido no Antigravity: Gemini 3.5 High (Alta Densidade Transacional).
Contrato de Alteração de Estrutura (DDL):
Dimensão Temporal nos Nós e Arestas: Alterar as instruções de criação (CREATE TABLE) das tabelas nodes e edges para incluir obrigatoriamente duas novas colunas:
valid_from_commit (TEXT NULL): Armazena o hash do commit a partir do qual este fato ou nó passou a existir.
valid_to_commit (TEXT NULL): Armazena o hash do commit em que este fato deixou de existir (marcando-o como obsoleto, mas sem deletá-lo fisicamente).
Tags de Confiança nas Arestas: Adicionar à tabela edges a coluna confidence_tag (TEXT NOT NULL DEFAULT 'EXTRACTED').
Constraint de Domínio (CHECK): Garantir via regra SQLite nativa (CHECK constraint) na tabela edges que a coluna confidence_tag aceite estritamente os valores: ('EXTRACTED', 'INFERRED', 'AMBIGUOUS').
Preservação do Legado: Certificar-se de que todas as outras configurações vitais do schema (PRAGMAs de performance WAL, foreign keys com CASCADE e os triggers nativos do FTS5) permaneçam intactas e funcionais após a adição destas colunas.