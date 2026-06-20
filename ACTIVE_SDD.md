### 🧭 ACTIVE BLUEPRINT: CAMADA CONVERSACIONAL - SEPARAÇÃO DE NAMESPACES (PASSO 1)
#### 🟢 STATUS: CONCLUÍDO

#### OBJETIVO TÉCNICO
Expandir a arquitetura de persistência do Grafo Concierge para suportar a "Arquitetura Federada de Memória". O sistema deve armazenar perfis de usuários, histórico episódico e fatos semânticos em tabelas e coleções completamente isoladas das tabelas de AST de código (`nodes`, `edges`, `commit_log`). 

#### 🛠️ ESPECIFICAÇÕES DE CONTRATO (DDL E VECTOR STORE)

**1. Separação Estrita de Escopo (Namespaces)**
*   Inspirado no Mem0, todo novo registro de memória deve conter obrigatoriamente os campos `scope_type` (ex: 'user', 'session', 'agent', 'org') e `scope_id` (o UUID correspondente) [1]. Isso garante o isolamento multi-tenant absoluto [2, 3].

**2. Tabelas Relacionais (SQLite em storage/schema.py ou equivalente)**
Devem ser criadas de forma idempotente (`CREATE TABLE IF NOT EXISTS`) as seguintes tabelas exclusivas para a memória:
*   **`user_core_memory` (Padrão Letta):** Armazena blocos de texto editáveis que compõem o perfil persistente do usuário e a persona do agente [4, 5].
    *   Campos: `id` (PK), `scope_type`, `scope_id`, `block_label` (ex: 'persona', 'human'), `content` (TEXT), `updated_at`.
*   **`semantic_facts` (Padrão Zep Bi-Temporal):** Armazena as preferências e fatos estruturados extraídos das conversas, aplicando o raciocínio temporal [6, 7].
    *   Campos: `id` (PK), `scope_type`, `scope_id`, `fact_statement` (TEXT), `t_valid` (TIMESTAMP - quando o fato se tornou verdade), `t_invalid` (TIMESTAMP NULL - preenchido apenas quando o fato expirar ou for substituído), `created_at`.

**3. Isolamento Vetorial (Qdrant em core/vector_backend.py)**
*   O motor do Qdrant não deve misturar vetores de conversa com vetores de código.
*   **Ação:** O inicializador do Qdrant deve garantir a existência de uma nova coleção independente chamada `episodic_memory` (reservada para logs de conversa e interações) [2, 8].
*   O payload desta coleção deve exigir a presença das chaves `scope_type`, `scope_id` e `timestamp` para indexação temporal.

**4. Regra de Ouro da Imutabilidade do Código**
*   As tabelas originais do Grafo Concierge voltadas para engenharia de software (`projects`, `nodes`, `edges` com `node_type` técnico) **NÃO** devem ser alteradas. A nova estrutura corre em paralelo.
