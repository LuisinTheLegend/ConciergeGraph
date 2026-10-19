# Decisões Arquiteturais e Planejamento — Fase 4

> **Status:** Registrado e Homologado pelo Usuário  
> **Data:** 18/10/2026  
> **Base Normativa:** Regras 2, 3, 4, 7, 10 e 11 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Contexto:** Rodada 4.1/B — Correção do F4-006 e Alinhamento Estratégico  

---

## 1. Decisões Oficiais do Usuário

1. **Caminho B Aprovado (Schema Reduzido & Quarentena Segura):**
   - No dilema arquitetural do schema relacional, o **Caminho B** foi oficialmente selecionado e aprovado.
   - O schema oficial de produção receberá exclusivamente a DDL da tabela `agent_checkpoints` (única das 5 tabelas ausentes do inventário que o Caminho B cria) para desbloquear as ferramentas `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`.
   - Das 5 tabelas ausentes catalogadas no inventário ([`audits/fase4-1-inventario-ddl.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-1-inventario-ddl.md)):
     - `agent_checkpoints` será criada em produção pelo Caminho B.
     - As outras 4 tabelas (`files`, `communities`, `ast_edges` e `fsm_checkpoints`), associadas aos motores Delta/Survival e HSM legado, permanecem dormentes e **não serão criadas** no schema de produção.
   - O código dormente associado será transferido para quarentena em `archive/v4-experimental` **somente após o desacoplamento seguro** de suas dependências ativas.

2. **Elevação de Severidade do F4-006 para CRÍTICA:**
   - O achado **F4-006** (crash de formatação de log em `ingestion/orchestrator.py:222`) foi elevado de 🟠 GRAVE para **🔴 CRÍTICA**, uma vez que a presença do `RichHandler` no processo real aborta o pipeline de mineração antes da geração e armazenamento de embeddings, deixando o banco vetorial vazio e a busca híbrida sem sinal semântico (`vector_score: 0.0`).

3. **Diretriz Técnica para `concierge_get_call_chain`:**
   - A ferramenta `concierge_get_call_chain` será reorientada para retornar caminhos de arquivo (*file paths*), navegando exclusivamente pelas arestas do tipo `calls` na tabela relacional `edges`.
   - A implementação e testes desta alteração ficam postergados para uma rodada futura específica.

4. **Remoção Definitiva do Dicionário de Alas (`wing_keywords`):**
   - O dicionário hardcoded de palavras-chave de domínio (`wing_keywords` em `core/config.py`) será removido em definitivo do sistema para garantir neutralidade de domínio, acompanhado de teste-guarda.
   - Esta remoção também fica agendada para uma rodada futura.

5. **Desenho Aprovado para F4-008/F4-009 (Alternativa A + Relato Honesto):**
   - Aprovada a **Alternativa A** (Reparo de vetores ausentes em `repair_missing_vectors` executado a cada mineração antes do atalho noop e após o passo 6) com **relato honesto do resultado** (`embeddings_failed`, `embeddings_repaired` e detalhamento em `errors` em caso de Semantic Fallback).
   - As alternativas B, C e D ficam oficialmente descartadas.

6. **Severidades Homologadas:**
   - **F4-008:** 🔴 **CRÍTICA**
   - **F4-009:** 🟠 **GRAVE**
   - **F4-010:** 🟠 **GRAVE**

7. **Escopo do F4-010 (Sumários L0):**
   - O F4-010 foi incluído na Rodada 4.1/D como commit separado, persistindo `chunk.cached_summary` no nó SQLite. Não há backfill de bancos existentes nesta rodada.

---

## 2. Ordem de Execução Planejada

> [!WARNING]
> **Status:** `PLANEJADO, NÃO AUTORIZADO`  
> Nenhuma das etapas 4.2 a 4.5 possui autorização de execução nesta rodada. Cada etapa depende de validação prévia e autorização humana explícita (GATE — Regra 7).

1. **Rodada 4.1/B (Concluída):**
   - Investigação de causa raiz completa do F4-006.
   - Teste de regressão e teste-guarda com RichHandler.
   - Correção pontual e cirúrgica na linha 222 de `ingestion/orchestrator.py`.
   - Prova ponta a ponta com modelo real (Chroma + SentenceTransformers) contrastada com a condição "Antes".

2. **Rodada 4.1/C (Concluída):**
   - Investigação empírica com 4 sondas (offline, falha parcial de lotes, reset_collection e sumários).
   - Elaboração e análise de 4 alternativas arquiteturais (A, B, C, D) para F4-008/F4-009.

3. **Rodada 4.1/D (Esta Rodada — Concluída):**
   - Implementação do reparo de vetores ausentes (Alternativa A) e relato honesto (F4-008, F4-009).
   - Implementação da persistência de sumários L0 nos nós SQLite (F4-010).
   - Prova ponta a ponta com modelo real `all-MiniLM-L6-v2` confrontada com baseline `76e6a7e`.

4. **Rodada 4.2 (Planejado, Não Autorizado):**
   - Desacoplamento do `mcp_governor` em relação a `interface.telemetry_api`.
   - Corte definitivo da cadeia `interface/__init__` → `ActionHooks` → `RevisorCritico` / `telemetry_api`.

5. **Rodada 4.3 (Planejado, Não Autorizado):**
   - Implementação do Schema Reduzido (DDL de `agent_checkpoints`).
   - Implementação e refatoração de `concierge_get_call_chain` navegando arestas `calls` em `edges`.

6. **Rodada 4.4 (Planejado, Não Autorizado):**
   - Remoção definitiva de `wing_keywords` em `core/config.py` e adaptação do `ProjectIndex`.
   - Teste-guarda de neutralidade de domínio.

7. **Rodada 4.5 (Planejado, Não Autorizado):**
   - Movimentação do motor Delta/Survival dormente e de seus módulos associados para quarentena isolada em `archive/v4-experimental`.
