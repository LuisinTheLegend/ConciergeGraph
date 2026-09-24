# Relatório de Auditoria: `bypass-governanca-por-session-id` (Achado Transversal de Segurança)

> **Data:** 23 de Setembro de 2026  
> **Status:** AUDITADO / PARADO NO GATE (Regra 7)  
> **Prioridade:** 🔴🔴 **PRIORIDADE MÁXIMA / FALHA DE DESIGN ESTRUTURAL**  
> **Arquivos Envolvidos:**
> - [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py)
> - [`core/mcp_governor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py)
> - [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py)
> - [`core/hsm_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py)

---

## 1. Resumo Executivo

Durante a preparação para a auditoria de `agent/` e `agents/`, investigou-se como o controle de acesso de ferramentas por estado mental do agente (*Progressive Tool Disclosure*) opera em produção. A análise estática e a reprodução empírica comprovaram uma **falha de segurança estrutural de severidade máxima**: o modelo de governança de ferramentas do `MCPToolGovernor` é **completamente contornável por qualquer cliente ou agente LLM**, a partir de qualquer estado mental (mesmo `PLANNING`), permitindo a execução imediata de ferramentas destrutivas (`DANGEROUS`), como a aniquilação completa da base vetorial via `reset_collection`.

Adicionalmente, comprovou-se que todo o subsistema de máquinas de estado hierárquicas (`core/hsm_engine.py`) e o runner cognitivo de agentes (`agent/run_agent.py`) estão **100% desconectados do servidor FastMCP em produção**: não existe nenhuma máquina de estados autônoma gerenciando sessões no servidor; o "estado" do servidor resume-se a uma string manipulada manualmente num dicionário em memória. Por fim, a camada passiva de descoberta de ferramentas vaza 100% das 31 ferramentas registradas para qualquer cliente MCP padrão.

---

## 2. SEÇÃO ESPECIAL: Falha Arquitetural de Design — Duas Falhas Independentes Ancoradas na Ilusão de Autenticidade do `session_id`

> [!CAUTION]
> ### Alerta de Risco Sistêmico: `session_id` como Vetor de Falsa Segurança e Independência das Falhas
> Esta investigação revelou que a vulnerabilidade **não é um bug isolado de implementação**, mas uma **falha conceitual de design** que contamina transversalmente a arquitetura do Grafo Concierge em **duas frentes totalmente independentes**:
>
> **A Premissa Falsa:**
> A arquitetura assumiu que `session_id` é um identificador seguro, estável e inviolável do chamador, capaz de ancorar tanto políticas de controle de acesso a ferramentas quanto o isolamento de memória e checkpoints.
>
> **A Realidade do Código:**
> `session_id` (assim como `agent_id`) é apenas uma **string arbitrária fornecida pelo próprio cliente no payload JSON-RPC**. Não há autenticação de sessão, não há tokens criptográficos assinados, não há amarração com conexões de transporte e não há verificação de posse (*ownership*).
>
> **Duas Causas-Raiz Diferentes e Não Interdependentes:**
> 1. **Achado #1 (Controle de Estado / Escalação de Privilégios):** Trata-se da quebra da máquina de estados do `MCPToolGovernor`. O chamador manipula `session_id` para alternar estados e desbloquear ferramentas `DANGEROUS` (como `reset_collection`).
> 2. **Achado #2 (Ausência de Verificação de Posse em Checkpoints):** Trata-se da ausência total de controle de acesso/posse em `agent_get_checkpoint` e `agent_save_checkpoint`. **Este achado NÃO depende do bypass do Achado #1 nem de manipulação de estado**:
>    - No estado padrão do servidor (`EXECUTION`), a matriz de governança já autoriza:
>      `TOOL_DISCLOSURE_MATRIX['EXECUTION']['allowed_categories'] = ['READ_ONLY', 'LOCAL_MUTATION']`.
>    - Como `agent_get_checkpoint` é categorizada como `READ_ONLY` e `agent_save_checkpoint` como `LOCAL_MUTATION`, **ambas as ferramentas já estão 100% abertas por padrão** para qualquer chamador.
>    - Mesmo em um ambiente onde o `MCPToolGovernor` funcionasse com 100% de perfeição e sem bypass, o ataque do Achado #2 seria executado com sucesso imediato no estado `EXECUTION` normal de trabalho.
>
> **Implicação Crítica para a Remediação (Fase 3):**
> A correção do Achado #1 (proteger a transição de estados) **NÃO resolve** o Achado #2 (roubo e envenenamento de checkpoints). Da mesma forma, corrigir a posse de checkpoints **NÃO resolve** a escalação de privilégios para ferramentas destrutivas. São duas falhas com causas-raiz distintas que exigem correções estruturais separadas.

---

## 3. Tabela Geral de Achados do Relatório

| # | Arquivo(s) | Linha(s) | Severidade | Mecanismo Resumido | Status |
|---|---|---|---|---|---|
| **#1** | [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L249-L259) <br> [`core/mcp_governor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L128-L193) | `mcp_server.py:249-259` <br> `mcp_governor.py:100, 128` | 🔴🔴 **CRÍTICA MÁXIMA** | **Bypass Total da Governança de Ferramentas via Injeção de `session_id` Fantasma**: `concierge_set_state` é `READ_ONLY` (sempre liberada). Qualquer agente restrito em `PLANNING` pode criar uma sessão efêmera `X` em `MAINTENANCE` e invocar qualquer ferramenta `DANGEROUS` (ex.: `reset_collection`) injetando `{"session_id": "X"}`. O interceptor valida `X` como permitido, e o FastMCP descarta o argumento extra não declarado e executa a operação destrutiva. | **CONFIRMADO E REPRODUZIDO** |
| **#2** | [`core/checkpointer.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L138-L144) <br> [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L897-L960) | `core/checkpointer.py:138, 226` <br> `interface/mcp_server.py:897, 1731` | 🔴 **CRÍTICA** | **Ausência Total de Verificação de Posse em Checkpoints (Independente do Achado #1)**: `agent_get_checkpoint` (`READ_ONLY`) e `agent_save_checkpoint` (`LOCAL_MUTATION`) já estão abertas por padrão no estado `EXECUTION`. Sem autenticação ou verificação de posse de `agent_id`/`session_id`, qualquer chamador pode roubar credenciais da vítima e sobrescrever/envenenar checkpoints alheios sem precisar burlar o governor nem alterar nenhum estado. | **CONFIRMADO E REPRODUZIDO** |
| **#3** | [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L261-L270) | `mcp_server.py:261-270` | 🟠 **GRAVE** | **Vazamento de 100% do Catálogo em `list_tools()` (Falha no Progressive Disclosure)**: `governed_list_tools` só filtra se `session_id` for fornecido. Clientes MCP oficiais (`tools/list`) nunca passam `session_id`. O servidor sempre expõe todas as 31 ferramentas, poluindo o contexto e revelando comandos perigosos. | **CONFIRMADO E REPRODUZIDO** |
| **#4** | [`agent/run_agent.py`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L28-L57) <br> [`core/hsm_engine.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L123) <br> [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L1-L1786) | Todo o arquivo | 🟠 **GRAVE** | **Desconexão Total do Runtime Cognitivo (`CognitiveAgentRunner` e `HSMEngine` Órfãos)**: A infraestrutura de Harel Statecharts (HSM), Deep History Nodes ($H^*$) e Circuit Breaker de sub-estados nunca é instanciada pelo servidor MCP em produção. O "estado" do servidor é uma mera string em memória, sem transição autônoma. | **CONFIRMADO** |
| **#5** | [`core/mcp_governor.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L37-L38) | `mcp_governor.py:37-38` | 🟡 **MÉDIA** | **Inicialização Insegura por Padrão (`default_state = "EXECUTION"`)**: O governor não inicia em `PLANNING`. Ferramentas de mutação física local (`LOCAL_MUTATION`, ex.: `concierge_mine`, `write_file`) ficam abertas imediatamente após o boot do servidor. | **CONFIRMADO E REPRODUZIDO** |

---

## 4. Detalhamento Técnico dos Achados e Mecanismos de Falha

### Achado #1: Bypass Total da Governança de Ferramentas via Injeção de `session_id` Fantasma
- **Severidade:** 🔴🔴 **CRÍTICA MÁXIMA / FALHA DE DESIGN**
- **Arquivos:** [`interface/mcp_server.py:249-259`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L249-L259), [`core/mcp_governor.py:100, 128-193`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L100)
- **Mecanismo da Falha:**
  A barreira de segurança ativa de ferramentas no FastMCP foi construída no método `_setup_tool_governance`:
  ```python
  async def governed_call_tool(name: str, arguments: dict, *args, **kwargs):
      session_id = (
          arguments.get("session_id", "default")
          if isinstance(arguments, dict)
          else "default"
      )
      # Validação ativa de execução
      self._governor.validate_tool_execution(session_id, name)
      return await original_tm_call_tool(name, arguments, *args, **kwargs)
  ```
  A vulnerabilidade decorre da conjunção de quatro fatores:
  1. **`concierge_set_state` é classificada como `READ_ONLY` (`core/mcp_governor.py:100`):** Isso significa que ela é permitida em **qualquer estado**, inclusive `PLANNING`, `DISCOVERY` ou `STALL`.
  2. **`set_session_state(session_id, state)` aceita qualquer identificador:** Não há lista de sessões permitidas nem autenticação. Se o chamador enviar `session_id="token_fantasma"`, o governor cria a chave no dicionário `sessions_state["token_fantasma"] = "MAINTENANCE"`.
  3. **Leitura de argumentos antes do FastMCP descartar parâmetros extras:** `governed_call_tool` extrai `session_id` do dicionário bruto de argumentos JSON-RPC recebido pela rede (`arguments.get("session_id")`).
  4. **FastMCP com `validate_input=False` e descarte de argumentos não declarados:** Ao despachar para a função Python registrada (`def reset_collection() -> dict`), o FastMCP inspeciona a assinatura, descarta os argumentos que a função não recebe (como `session_id`) e executa a função sem erros de validação.

  **Roteiro do Ataque de Bypass (Reproduzido com Sucesso):**
  1. O agente opera na sessão legítima `agent_session_1`, cujo estado foi travado em `PLANNING`.
  2. O agente tenta invocar `reset_collection({"session_id": "agent_session_1"})` -> **Bloqueado** com `SecurityException`.
  3. O agente invoca a ferramenta pública `concierge_set_state(state_name="MAINTENANCE", session_id="bypass_token")` -> **Sucesso** (ferramenta `READ_ONLY` é permitida em `PLANNING`).
  4. O agente invoca `reset_collection({"session_id": "bypass_token"})`:
     - `governed_call_tool` consulta o estado de `"bypass_token"` -> `MAINTENANCE`.
     - `validate_tool_execution` valida que `DANGEROUS` é permitido em `MAINTENANCE` -> **Aprovado**.
     - FastMCP descarta `session_id="bypass_token"` e chama `_handle_reset_collection()`.
     - **A base vetorial ChromaDB é inteiramente destruída e recriada.**

---

### Achado #2: Ausência Total de Verificação de Posse em Checkpoints (Independente do Achado #1)
- **Severidade:** 🔴 **CRÍTICA**
- **Arquivos:** [`core/checkpointer.py:138-144, 226-234`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L138), [`interface/mcp_server.py:897-960, 1731-1775`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L897), [`core/mcp_governor.py:52-55, 101-109`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L52)
- **Status de Certeza:** **CONFIRMADO E REPRODUZIDO EMPIRICAMENTE** (via [`scratch/test_checkpoint_impersonation.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_checkpoint_impersonation.py))
- **Mecanismo:**
  Este achado possui causa-raiz **completamente independente** da governança de estados do Achado #1:
  - O `MCPToolGovernor` classifica `agent_get_checkpoint` e `agent_list_checkpoints` como `READ_ONLY` (`core/mcp_governor.py:101-102`), e `agent_save_checkpoint` como `LOCAL_MUTATION` (`core/mcp_governor.py:109`).
  - No estado padrão do servidor (`EXECUTION`), a matriz de autorização define:
    ```python
    "EXECUTION": {
        "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
        "allowed_tools": ["get_telemetry_snapshot"],
    }
    ```
  - Portanto, **todas as ferramentas de checkpoint já estão plenamente autorizadas por padrão**, sem necessidade de contornar estados, forçar `MAINTENANCE` ou invocar `concierge_set_state`.
  - A falha reside exclusivamente na **ausência de verificação de posse (*Broken Object Level Authorization / Missing Authentication*)** no subsistema de checkpoints:
    1. **Identificadores Livres no JSON-RPC:** As ferramentas recebem `agent_id` e `session_id` como simples strings declaradas no payload de entrada da chamada, sem qualquer verificação criptográfica, token de autenticação ou vinculação ao socket/transporte do chamador.
    2. **Exfiltração de Segredos (Leitura Não Autorizada):** Qualquer chamador pode invocar `agent_get_checkpoint(agent_id="legitimate_worker_agent", session_id="victim_session", checkpoint_id="critical_step_42")` e receber imediatamente todos os segredos (chaves de API, credenciais corporativas e dados confidenciais) persistidos pela vítima.
    3. **Envenenamento de Estado (Sobrescrita Arbitrária):** Em `core/checkpointer.py:139`, a persistência executa `INSERT OR REPLACE INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob) VALUES (?, ?, ?, ?)`. Qualquer chamador pode enviar um payload contendo comandos maliciosos ou estado corrompido para a mesma tupla `(agent_id, session_id, checkpoint_id)`. O SQLite WAL sobrescreve silenciosamente o checkpoint legítimo da vítima. Quando a vítima retoma seu trabalho via `agent_get_checkpoint`, carrega o estado envenenado sem nenhum alerta ou verificação de integridade.
    4. **Isolamento de `agent_id`:** O teste empírico comprovou que se o atacante usar um `agent_id` diferente (`"different_unauthorized_agent"`), a query SQLite `WHERE agent_id = ? AND session_id = ?` retorna vazio `{}`. Porém, como `agent_id` é um argumento arbitrariamente fornecido pelo cliente e os identificadores de agentes no Grafo Concierge são previsíveis e padronizados (`primary_agent`, `revisor_critico`, `scout`, `coder`), a falsificação de identidade (*impersonation*) é direta e imediata.


---

### Achado #3: Vazamento de 100% das Ferramentas em `list_tools()` para Clientes MCP Padrão
- **Severidade:** 🟠 **GRAVE**
- **Arquivo:** [`interface/mcp_server.py:261-270`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L261-L270)
- **Mecanismo:**
  O método `governed_list_tools` foi projetado para ocultar ferramentas proibidas do catálogo de ferramentas enviado ao LLM:
  ```python
  async def governed_list_tools(session_id: Optional[str] = None):
      tools = await original_mcp_list_tools()
      if session_id:
          return self._governor.filter_tools(session_id, tools)
      return tools
  ```
  No entanto, o protocolo padrão do Model Context Protocol (especificação JSON-RPC oficial) para listar ferramentas (`tools/list`) opera sem parâmetros de sessão por chamada (`params: {}`).
  Portanto:
  - `session_id` é rigorosamente `None` em todas as conexões via stdio ou SSE originadas de clientes MCP oficiais.
  - A condição `if session_id:` nunca é satisfeita.
  - O servidor retorna a lista integral de **31 ferramentas** (incluindo `reset_collection`, `purge_database`, `delete_project`), inflando desnecessariamente o context window do modelo e apresentando ações destrutivas para agentes em fase de planejamento.

---

### Achado #4: Desconexão Total do Runtime Cognitivo (`CognitiveAgentRunner` e `HSMEngine` Órfãos)
- **Severidade:** 🟠 **GRAVE**
- **Arquivos:** [`agent/run_agent.py:28-57`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L28-L57), [`core/hsm_engine.py:123`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L123), [`interface/mcp_server.py`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py)
- **Mecanismo:**
  A documentação de arquitetura (`docs-grafo-concierge/01_ARCHITECTURE.md`) e os arquivos de linhagem citam a máquina de estados hierárquica (HSM) com *Deep History Nodes* ($H^*$) e o *Sub-State Circuit Breaker* do `CognitiveAgentRunner` como pilares de segurança e sobrevivência do Grafo Concierge.
  Porém, a análise do código de produção revelou:
  - `main.py` inicializa o servidor sem instanciar `CognitiveAgentRunner` nem `HierarchicalStateMachine`.
  - `interface/mcp_server.py` não contém nenhuma linha de importação ou referência a `hsm_engine.py` ou `run_agent.py`.
  - O único acoplamento existente é com o `MCPToolGovernor`, que é um dicionário estático de strings (`sessions_state: Dict[str, str]`).
  - Todo o código sofisticado de restauração de nós de histórico, transições hierárquicas e circuit breakers em `agent/` e `core/hsm_engine.py` existe como **código morto em produção**, sendo executado apenas por testes unitários isolados.

---

### Achado #5: Inicialização Insegura por Padrão (`default_state = "EXECUTION"`)
- **Severidade:** 🟡 **MÉDIA**
- **Arquivo:** [`core/mcp_governor.py:37-38`](file:///c:/Nexus-Memory/GrafoConcierge/core/mcp_governor.py#L37-L38)
- **Mecanismo:**
  O construtor do `MCPToolGovernor` define:
  ```python
  env_default = os.environ.get("GRAFO_DEFAULT_STATE", "EXECUTION")
  self.default_state = env_default.upper()
  ```
  Caso a variável de ambiente não esteja explicitamente configurada como `PLANNING`, o servidor é iniciado no modo `EXECUTION`. Nesse estado:
  - Todas as ferramentas `LOCAL_MUTATION` (`concierge_mine`, `concierge_commit`, `write_file`, `delete_file`) estão autorizadas de imediato.
  - Isso viola o princípio do menor privilégio e o objetivo central do SDD-SURVIVAL-21, que prescrevia iniciar em modo estrito de leitura (`PLANNING`) para evitar mutações acidentais na fase de descoberta.

---

## 5. Saída Bruta Completa da Reprodução Empírica

### 5.1 Achado #1: Bypass do Governor via Ghost Token e FastMCP Descarte de Parâmetros
Execução do script de verificação de segurança [`scratch/test_governor_dispatch.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_governor_dispatch.py):

```text
[09/23/26 22:47:42] INFO     GrafoConciergeServer initialized mcp_server.py:233
                             - 31 tools registered.                            
                    INFO     reset_collection OK:           vector_store.py:650
                             collection 'grafo_concierge'                      
                             destroyed and recreated (0                        
                             embeddings eliminated).                           
                    WARNING  reset_collection: vector         middleware.py:779
                             collection destroyed and                          
                             recreated.                                        
                    INFO     reset_collection OK: True       mcp_server.py:1715
======================================================================
1. ESTADO INICIAL DO GOVERNOR NO SERVIDOR
======================================================================
Default state configurado: EXECUTION
Estado da sessao 'default': EXECUTION
Sessoes ativas no governor: {}

======================================================================
2. LISTAGEM DE FERRAMENTAS (list_tools)
======================================================================
Total de ferramentas retornadas por list_tools() sem session_id: 31
Ferramentas retornadas por list_tools(session_id='default') em EXECUTION: 29

======================================================================
3. TESTE DE DISPATCH REAL: ESTADO 'EXECUTION' (DEFAULT)
======================================================================
Categoria de 'reset_collection': DANGEROUS
Permitido em EXECUTION? False
RESULTADO: BLOQUEADO pelo SecurityException: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocked during state 'EXECUTION' for session 'default'.

======================================================================
4. MUDANCA DE ESTADO VIA concierge_set_state('PLANNING')
======================================================================
Retorno de concierge_set_state: [TextContent(type='text', text='{\n  "success": true,\n  "session_id": "default",\n  "active_state": "PLANNING"\n}', annotations=None, meta=None)]
Estado de 'default' apos set_state: PLANNING

======================================================================
5. TESTE DE DISPATCH REAL: ESTADO 'PLANNING'
======================================================================
Categoria de 'concierge_mine': LOCAL_MUTATION
RESULTADO: BLOQUEADO pelo SecurityException: Access denied: tool 'concierge_mine' (category 'LOCAL_MUTATION') is blocked during state 'PLANNING' for session 'default'.
RESULTADO: BLOQUEADO pelo SecurityException: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocked during state 'PLANNING' for session 'default'.

======================================================================
6. BYPASS DE SESSION_ID: SESSAO CUSTOMIZADA VS DEFAULT
======================================================================
Estado de 'agente_1': PLANNING
Estado de 'default': PLANNING
Chamada a reset_collection({}) -> BLOQUEADA: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocked during state 'PLANNING' for session 'default'.

======================================================================
8. DEMONSTRACAO DE BYPASS REAL: AGENTE EM PLANNING DESTROI BASE VETORIAL
======================================================================
Estado de 'agent_session_1': PLANNING
Chamada com session_id='agent_session_1' -> Bloqueada corretamente: Access denied: tool 'reset_collection' (category 'DANGEROUS') is blocked during state 'PLANNING' for session 'agent_session_1'.
Agente registrou 'bypass_token' como MAINTENANCE via concierge_set_state (READ_ONLY).
RESULTADO DO BYPASS: reset_collection EXECUTADA COM SUCESSO! -> [TextContent(type='text', text='{\n  "success": true,\n  "duration_seconds": 0.027\n}', annotations=None, meta=None)]
Vulnerabilidade comprovada: FastMCP descartou session_id e executou a operacao DANGEROUS!
```

### 5.2 Achado #2: Impersonation de Sessão, Exfiltração de Segredos e Envenenamento de Checkpoints
Execução do script de verificação de segurança [`scratch/test_checkpoint_impersonation.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/test_checkpoint_impersonation.py):

```text
[09/23/26 22:56:51] INFO     GrafoConciergeServer initialized mcp_server.py:233
                             - 31 tools registered.                            
======================================================================
TESTE DE IMPERSONATION E ENVENENAMENTO DE CHECKPOINTS VIA session_id
======================================================================
1. Vítima salvou checkpoint 'critical_step_42' em 'victim_session':
   Resposta: ([TextContent(type='text', text='{"success": true, "message": "Checkpoint \'critical_step_42\' saved successfully for agent \'legitimate_worker_agent\'"}', annotations=None, meta=None)], {'result': '{"success": true, "message": "Checkpoint \'critical_step_42\' saved successfully for agent \'legitimate_worker_agent\'"}'})

2. Atacante B impersona a vítima e lista checkpoints:
   Checkpoints descobertos: [TextContent(type='text', text='{\n  "checkpoint_id": "critical_step_42",\n  "created_at": "2026-09-24 01:56:51"\n}', annotations=None, meta=None)]

3. Atacante B lê o checkpoint da vítima (agent_get_checkpoint):
   Dados roubados: [TextContent(type='text', text='{\n  "user_email": "ceo@enterprise.com",\n  "api_secret_key": "sk-proj-SUPER_CONFIDENTIAL_KEY_XYZ",\n  "work_status": "in_progress",\n  "approved_budget": 500000\n}', annotations=None, meta=None)]
   -> [COMPROVADO] LEITURA NÃO AUTORIZADA: Atacante exfiltrou 'api_secret_key' da vítima!

4. Atacante B sobrescreve o checkpoint da vítima com payload malicioso:
   Resposta: ([TextContent(type='text', text='{"success": true, "message": "Checkpoint \'critical_step_42\' saved successfully for agent \'legitimate_worker_agent\'"}', annotations=None, meta=None)], {'result': '{"success": true, "message": "Checkpoint \'critical_step_42\' saved successfully for agent \'legitimate_worker_agent\'"}'})

5. Vítima retoma a sessão e lê seu checkpoint:
   Estado recuperado: [TextContent(type='text', text='{\n  "user_email": "hacker@evil.com",\n  "api_secret_key": "sk-proj-POISONED_KEY",\n  "work_status": "corrupted",\n  "approved_budget": 0,\n  "backdoor_payload": "rm -rf /"\n}', annotations=None, meta=None)]
   -> [COMPROVADO] ENVENENAMENTO DE ESTADO: O checkpoint da vítima foi substituído pelo payload do atacante!

6. Atacante tenta ler com agent_id='different_unauthorized_agent' e session_id='victim_session':
   Resposta: [TextContent(type='text', text='{}', annotations=None, meta=None)]

======================================================================
SÍNTESE DOS RESULTADOS:
- Impersonation de Identidade / Exfiltração de Segredos: CONFIRMADA
- Envenenamento e Sobrescrita Arbitrária de Checkpoint: CONFIRMADA
- Classificação de Gravidade: CRÍTICA (Nenhuma autenticação de sessão ou agente)
======================================================================
```

---

## 6. Recomendações Estruturais para a Fase 3 (Backlog Consolidado)

1. **Eliminar a Confiança Cega em `session_id` não Autenticado:**
   - O `session_id` deve ser vinculado à conexão ou ao token de autenticação (ex.: `Bearer token` extraído no handshake do SSE/Starlette), e **nunca** aceito como um parâmetro solto dentro dos argumentos da ferramenta.
2. **Restringir `concierge_set_state` para Categoria `DANGEROUS` ou Autenticada:**
   - A ferramenta `concierge_set_state` jamais poderia ser classificada como `READ_ONLY`. Mudar o regime cognitivo do servidor de `PLANNING` para `MAINTENANCE` é uma operação de mutação de privilégios (*Privilege Escalation*).
3. **Validação Estrita de Parâmetros no Interceptor:**
   - O `governed_call_tool` deve rejeitar chamadas que injetem argumentos não declarados na assinatura da ferramenta (impedindo o truque de passar `session_id` fantasma para ferramentas que não o aceitam).
4. **Acoplamento Real ou Depreciação do HSM:**
   - Se o `HierarchicalStateMachine` e o `CognitiveAgentRunner` forem mantidos no projeto, eles devem ser instanciados e efetivamente amarrados ao ciclo de vida do servidor MCP em `main.py`. Caso contrário, devem ser formalmente marcados como protótipos experimentais e isolados do código de produção.
5. **Configurar `PLANNING` como Estado Inicial Mandatório:**
   - Alterar o valor padrão de `GRAFO_DEFAULT_STATE` em `core/mcp_governor.py` de `"EXECUTION"` para `"PLANNING"`.
