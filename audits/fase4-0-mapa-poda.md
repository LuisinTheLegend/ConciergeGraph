# Mapa de Dependências para Poda de Escopo (Fase 4, Rodada 4.0)

> **Documento Normativo de Auditoria e Arquitetura**  
> **Fase:** Fase 4 — Correções de Código | **Rodada:** 4.0 | **Natureza:** SOMENTE LEITURA E DOCUMENTAÇÃO  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e Regras 1 a 7 da Fase 4 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Hash de Base:** `5f641c3bbad6ab9ebf0880b98382006e201a5551`  
> **Data:** 15/10/2026  
> **Status:** PARADA NO GATE (Nenhum código de produção nem testes foi alterado; nenhum arquivo foi movido ou removido)

---

## 1. Passo 0 — Sincronização e Estado do Repositório

Comandos executados no início da rodada:
```powershell
git pull
git rev-parse HEAD
git status
```

**Saída literal:**
```
Already up to date.
5f641c3bbad6ab9ebf0880b98382006e201a5551
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## 2. Passo 1 — Fichas de Dependência por Módulo Candidato à Poda

Foram analisados os 8 módulos candidatos à poda (proposta de arquivamento em `archive/v4-experimental`).  
Cada ficha detalha volume de código, acoplamentos em produção, simulação isolada de remoção executada em worktree descartável fora do repositório, suítes de teste afetadas, documentos de referência, itens do backlog associados e o desacoplamento cirúrgico mínimo necessário.

---

### 2.1 Candidato 1: `agent/run_agent.py`

- **Linhas de Código:** 266 linhas
- **Importadores em Produção:**
  - [`agent/__init__.py:11`](file:///c:/Nexus-Memory/GrafoConcierge/agent/__init__.py#L11): `from agent.run_agent import CognitiveAgentRunner, HermesAgentRunner`
  *(Nenhum outro módulo de `core/`, `interface/`, `storage/`, `ingestion/` ou `services/` importa `run_agent.py`)*
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 324 testes coletados (-13 testes)
    - **Saída literal do erro de coleta:**
      ```
      tests\test_agent_hsm_coupling.py:15: in <module>
          from agent.agent_prompts import DynamicPromptBuilder
      agent\__init__.py:11: in <module>
          from agent.run_agent import CognitiveAgentRunner, HermesAgentRunner
      E   ModuleNotFoundError: No module named 'agent.run_agent'
      ERROR tests/test_agent_hsm_coupling.py
      324 tests collected, 1 error in 17.99s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_agent_hsm_coupling.py` (13 testes, indiretamente via `agent/__init__.py`)
- **Documentos que o Citam:**
  - `docs-grafo-concierge/01_ARCHITECTURE.md`
  - `docs-grafo-concierge/03_COGNITIVE_MEMORY_AND_FACTS.md`
  - `docs-grafo-concierge/README.md`
  - `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-014`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L299) (🟠 GRAVE): Desconexão Total do Runtime Cognitivo no Servidor MCP (`agent/run_agent.py`, `core/hsm_engine.py`, `interface/mcp_server.py`) — **DEPENDE**: Se `run_agent.py` for para quarentena, o MCP não precisa integrá-lo, mantendo apenas as ferramentas nativas de FSM.
  - [`BL-077`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L837) (🔴 CRÍTICA): Contaminação de Turnos Multi-Sessão no Circuit Breaker (`agent/run_agent.py:47, 82, 95`) — **QUARENTENA**: Fica inativo junto com o módulo.
  - [`BL-080`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L863) (🟠 GRAVE): Dessincronização de Estado e Diretrizes em `step()` (`agent/run_agent.py:151–217`) — **QUARENTENA**: Fica inativo junto com o módulo.
  - [`BL-082`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L880) (🟡 MÉDIA): Incompatibilidade com Corrotinas em `execute_tool` (`agent/run_agent.py:243–262`) — **QUARENTENA**: Fica inativo junto com o módulo.
- **Desacoplamento Necessário para Remoção Segura:**
  - [`agent/__init__.py:11-13`](file:///c:/Nexus-Memory/GrafoConcierge/agent/__init__.py#L11): Remover as importações e o `__all__` que exportam `CognitiveAgentRunner` e `HermesAgentRunner`.
  - [`tests/test_agent_hsm_coupling.py:15`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_agent_hsm_coupling.py#L15): Mover para quarentena junto com o pacote `agent/`.

---

### 2.2 Candidato 2: `agent/agent_prompts.py`

- **Linhas de Código:** 176 linhas
- **Importadores em Produção:**
  - [`agent/run_agent.py:23`](file:///c:/Nexus-Memory/GrafoConcierge/agent/run_agent.py#L23): `from agent.agent_prompts import DynamicPromptBuilder`
  *(Nenhum outro módulo de produção importa `agent_prompts.py`)*
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 324 testes coletados (-13 testes)
    - **Saída literal do erro de coleta:**
      ```
      agent\__init__.py:11: in <module>
          from agent.run_agent import CognitiveAgentRunner, HermesAgentRunner
      agent\run_agent.py:23: in <module>
          from agent.agent_prompts import DynamicPromptBuilder
      E   ModuleNotFoundError: No module named 'agent.agent_prompts'
      ERROR tests/test_agent_hsm_coupling.py
      324 testes coletados, 1 error in 17.23s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_agent_hsm_coupling.py` (13 testes, importa `DynamicPromptBuilder`)
- **Documentos que o Citam:**
  - Nenhum documento em `docs-grafo-concierge/` cita nominalmente o arquivo (é citado apenas genericamente como parte do Runtime Cognitivo).
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-083`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L889) (🟡 MÉDIA): Dessincronização entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX` (`agent/agent_prompts.py:82–132`) — **QUARENTENA**: Fica inativo junto com o módulo.
- **Desacoplamento Necessário para Remoção Segura:**
  - Arquivado conjuntamente com `agent/run_agent.py`. Se `run_agent.py` for para quarentena, `agent_prompts.py` fica sem nenhum chamador.

---

### 2.3 Candidato 3: `agents/revisor_critico.py`

- **Linhas de Código:** 610 linhas
- **Importadores em Produção:**
  - [`agents/__init__.py:10`](file:///c:/Nexus-Memory/GrafoConcierge/agents/__init__.py#L10): `from agents.revisor_critico import RevisorCritico`
  - [`interface/action_hooks.py:32`](file:///c:/Nexus-Memory/GrafoConcierge/interface/action_hooks.py#L32): `from agents.revisor_critico import RevisorCritico` (instanciado por padrão na linha 56: `self._revisor = revisor or RevisorCritico()`)
  - [`interface/__init__.py:11`](file:///c:/Nexus-Memory/GrafoConcierge/interface/__init__.py#L11): `from interface.action_hooks import ActionHooks` (efeito cascata: importar qualquer coisa de `interface` dispara a carga de `RevisorCritico`)
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **FALHA** (retorno 1)
    - **Saída literal:**
      ```
      Traceback (most recent call last):
        File "<string>", line 1, in <module>
          import interface.mcp_server; print('OK')
        File "...\interface\__init__.py", line 11, in <module>
          from interface.action_hooks import ActionHooks
        File "...\interface\action_hooks.py", line 32, in <module>
          from agents.revisor_critico import RevisorCritico
        File "...\agents\__init__.py", line 10, in <module>
          from agents.revisor_critico import RevisorCritico
      ModuleNotFoundError: No module named 'agents.revisor_critico'
      ```
  - `python -c "import main"`: **OK** (retorno 0, pois `main.py` importa diretamente `from interface.mcp_server import GrafoConciergeServer`, mas a falha ocorre se o pacote `interface` for resolvido em nível de topo ou em testes)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 301 testes coletados (-36 testes)
    - **Saída literal do erro de coleta:**
      ```
      ERROR tests/test_durable_checkpoints_timetravel.py
      ERROR tests/test_interface_contracts.py
      ERROR tests/test_revisor_critico.py
      301 tests collected, 3 errors in 19.91s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_revisor_critico.py` (11 testes)
  - `tests/test_interface_contracts.py` (falha na coleta por import de `interface`)
  - `tests/test_durable_checkpoints_timetravel.py` (falha na coleta por import de `interface.action_hooks`)
  - Scripts de benchmark: `tests/colossus_benchmark.py`, `tests/stress_test_v2_setup.py`
- **Documentos que o Citam:**
  - `docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md`
  - `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-078`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L846) (🔴 CRÍTICA): Vazamento de Privacidade por Fallback Inseguro Fail-Open em `check_contamination` (`agents/revisor_critico.py:555–573`) — **QUARENTENA**
  - [`BL-079`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L855) (🟠 GRAVE): Aprovação Espúria de Commits Inválidos em `audit_with_retry` (`agents/revisor_critico.py:331, 362–381`) — **QUARENTENA**
  - [`BL-081`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L872) (🟠 GRAVE): Falhas de Tipagem e Crash em Reranking (`agents/revisor_critico.py:433, 490–498, 504–513`) — **QUARENTENA**
- **Desacoplamento Necessário para Remoção Segura:**
  - [`agents/__init__.py:10`](file:///c:/Nexus-Memory/GrafoConcierge/agents/__init__.py#L10): Remover `from agents.revisor_critico import RevisorCritico`.
  - [`interface/action_hooks.py:32, 53, 56`](file:///c:/Nexus-Memory/GrafoConcierge/interface/action_hooks.py#L32): Tornar a dependência opcional (`revisor: Optional[Any] = None`, `self._revisor = revisor`), sem instanciar `RevisorCritico()` por padrão no construtor.

---

### 2.4 Candidato 4: `interface/telemetry_api.py`

- **Linhas de Código:** 595 linhas
- **Importadores em Produção:**
  - [`interface/mcp_server.py:151`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L151):
    ```python
    try:
        from interface.telemetry_api import mcp_governor
        governor = mcp_governor
    except Exception:
        from core.mcp_governor import MCPToolGovernor
        governor = MCPToolGovernor()
    ```
    *Graças ao bloco `try/except` pré-existente, o `mcp_server.py` sobrevive nativamente à ausência de `telemetry_api.py`!*
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0, ativou o fallback para `core.mcp_governor.MCPToolGovernor`)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 324 testes coletados (-13 testes)
    - **Saída literal do erro de coleta:**
      ```
      tests\test_telemetry_api.py:24: in <module>
          from interface.telemetry_api import app, get_db_manager
      E   ModuleNotFoundError: No module named 'interface.telemetry_api'
      ERROR tests/test_durable_checkpoints_timetravel.py
      ERROR tests/test_progressive_tool_disclosure.py
      ERROR tests/test_telemetry_api.py
      324 tests collected, 3 errors in 18.58s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_telemetry_api.py` (5 testes)
  - `tests/test_progressive_tool_disclosure.py` (5 testes)
  - `tests/test_durable_checkpoints_timetravel.py` (3 testes)
  - `tests/test_hierarchical_state_machine.py` (43 testes, importa schemas)
- **Documentos que o Citam:**
  - `docs-grafo-concierge/01_ARCHITECTURE.md`
  - `docs-grafo-concierge/06_DEPLOY_AND_CONFIGURATION.md`
  - `docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md`
  - `docs-grafo-concierge/README.md`
  - `README.md`
  - `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-062`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L713) (🔴 CRÍTICA): Falha Fatal e Crash HTTP 500 na Telemetria por Tabelas Inexistentes — **QUARENTENA**
  - [`BL-063`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L722) (🔴 CRÍTICA): Inoperância Fora da Caixa por Dependência `get_db_manager` Não Configurada — **QUARENTENA**
  - [`BL-064`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L731) (🟠 GRAVE): Falso Stream Contínuo por Limite Hardcoded (`max_checks = 5`) — **QUARENTENA**
  - [`BL-065`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L739) (🟠 GRAVE): Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico — **QUARENTENA**
  - [`BL-066`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L747) (🟠 GRAVE): Insegurança Total de CORS e Falta de Autenticação em Rotas Mutantes — **QUARENTENA**
  - [`BL-067`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L756) (🟡 MÉDIA): Crash de Tipagem em Timestamps na Telemetria (`NoneType` e `str`) — **QUARENTENA**
  - [`BL-068`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L765) (🟡 MÉDIA): Thread Daemônica Órfã Iniciada no Import de `telemetry_api` — **QUARENTENA**
  - [`BL-070`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L780) (🔴 CRÍTICA): Flapping SSE a cada 8s (cruza com dashboard) — **DEPENDE**
- **Desacoplamento Necessário para Remoção Segura:**
  - [`interface/mcp_server.py:149-156`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L149): Substituir o bloco `try/except` por instanciação direta `governor = MCPToolGovernor()`.

---

### 2.5 Candidato 5: `core/rate_governor.py`

- **Linhas de Código:** 280 linhas
- **Importadores em Produção:**
  - [`interface/telemetry_api.py:44`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L44): `from core.rate_governor import RateGovernor`
  - [`interface/telemetry_api.py:61`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L61): `rate_governor_service = RateGovernor(rpm_limit=60, tpm_limit=40000); rate_governor_service.start()`
  *(Nenhum outro módulo de produção em `core/`, `storage/`, `ingestion/` ou `services/` importa `rate_governor.py`)*
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 303 testes coletados (-34 testes)
    - **Saída literal do erro de coleta:**
      ```
      ERROR tests/test_agent_hsm_coupling.py
      ERROR tests/test_durable_checkpoints_timetravel.py
      ERROR tests/test_progressive_tool_disclosure.py
      ERROR tests/test_rate_governor_priority.py
      ERROR tests/test_telemetry_api.py
      303 tests collected, 5 errors in 17.97s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_rate_governor_priority.py` (8 testes)
  - `tests/test_agent_hsm_coupling.py` (13 testes)
- **Documentos que o Citam:**
  - `docs-grafo-concierge/01_ARCHITECTURE.md`
  - `docs-grafo-concierge/05_HYBRID_SEARCH_AND_ROUTING.md`
  - `docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md`
  - `docs-grafo-concierge/README.md`
  - `README.md`, `CONTRIBUTING.md`, `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-047`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L588) (🔴 CRÍTICA): Vazamento de `unfinished_tasks` na `PriorityQueue` e Starvation (`core/rate_governor.py:250`) — **QUARENTENA**
  - [`BL-048`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L597) (🟠 GRAVE): Starvation de Tarefas LOW Envelhecidas (`core/rate_governor.py:231–252`) — **QUARENTENA**
  - [`BL-049`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L605) (🟠 GRAVE): Data Race / Lost Updates em `get_current_metrics()` (`core/rate_governor.py:91`) — **QUARENTENA**
  - [`BL-050`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L614) (🟠 GRAVE): Deadlock Eterno em `submit_request` (`core/rate_governor.py:196–203`) — **QUARENTENA**
  - [`BL-051`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L622) (🟡 MÉDIA): Cegueira de RPM no Fast-Path (`core/rate_governor.py:185–194`) — **QUARENTENA**
- **Desacoplamento Necessário para Remoção Segura:**
  - Se `interface/telemetry_api.py` for para quarentena, `rate_governor.py` fica com ZERO importadores no sistema.
  - Se `telemetry_api.py` fosse mantido, as linhas 44 e 61-62 de `telemetry_api.py` precisariam ser removidas.

---

### 2.6 Candidato 6: `core/gating_interceptor.py`

- **Linhas de Código:** 176 linhas
- **Importadores em Produção:**
  - [`interface/telemetry_api.py:42`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L42): `from core.gating_interceptor import GatingInterceptor`
  - [`interface/telemetry_api.py:67`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L67): `gating_interceptor_service = GatingInterceptor(security_guard_service)`
  *(Nenhum outro módulo de produção em `core/`, `storage/`, `ingestion/` ou `services/` importa `gating_interceptor.py`)*
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`:
    - **Antes:** 337 testes coletados
    - **Depois:** 299 testes coletados (-38 testes)
    - **Saída literal do erro de coleta:**
      ```
      ERROR tests/test_adaptive_gating.py
      ERROR tests/test_agent_hsm_coupling.py
      ERROR tests/test_durable_checkpoints_timetravel.py
      ERROR tests/test_progressive_tool_disclosure.py
      ERROR tests/test_telemetry_api.py
      299 tests collected, 5 errors in 19.00s
      ```
- **Testes que Importam o Módulo:**
  - `tests/test_adaptive_gating.py` (12 testes)
  - `tests/test_agent_hsm_coupling.py` (13 testes)
- **Documentos que o Citam:**
  - `docs-grafo-concierge/01_ARCHITECTURE.md`
  - `docs-grafo-concierge/07_MIGRATION_AND_OPERATIONS.md`
  - `docs-grafo-concierge/README.md`
  - `README.md`, `CONTRIBUTING.md`, `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - Nenhum BL tem o arquivo como fonte primária direta de falha (os achados de segurança de filesystem concentram-se em [`core/security_guard.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/security_guard.py), que é ativo: BL-052 a BL-056).
- **Desacoplamento Necessário para Remoção Segura:**
  - Se `interface/telemetry_api.py` for para quarentena, `core/gating_interceptor.py` fica com ZERO importadores no sistema.

---

### 2.7 Candidato 7: `core/nozomio_router.py` (Shim Deprecated)

- **Linhas de Código:** 21 linhas
- **Importadores em Produção:**
  - **ZERO importadores.** Ninguém importa `nozomio_router.py` em produção nem em testes.
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`: **337 testes coletados (0 erros, 100% idêntico)**.
- **Testes que Importam o Módulo:**
  - ZERO testes.
- **Documentos que o Citam:**
  - `docs-grafo-concierge/05_HYBRID_SEARCH_AND_ROUTING.md`
  - `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - Nenhum item do backlog.
- **Desacoplamento Necessário para Remoção Segura:**
  - **Nenhum.** Pode ser removido ou arquivado imediatamente sem qualquer edição em outro arquivo.

---

### 2.8 Candidato 8: `grafo-dashboard-web/`

- **Linhas de Código:** 43 arquivos, 14.384 linhas (aplicação Next.js / TypeScript / React 19)
- **Importadores em Produção:**
  - **ZERO importadores em Python.** Não há dependência de importação cruzada da aplicação Python sobre o frontend.
- **Simulação de Remoção (em worktree temporário descartável):**
  - `python -c "import interface.mcp_server"`: **OK** (retorno 0)
  - `python -c "import main"`: **OK** (retorno 0)
  - `pytest tests/ --collect-only -q`: **337 testes coletados (0 erros, 100% idêntico)**.
- **Testes que Importam o Módulo:**
  - ZERO testes unitários Python (possui testes próprios em npm/jest se configurado).
- **Documentos que o Citam:**
  - `docs-grafo-concierge/01_ARCHITECTURE.md`
  - `docs-grafo-concierge/04_INGESTION_AND_AST.md`
  - `docs-grafo-concierge/06_DEPLOY_AND_CONFIGURATION.md`
  - `docs-grafo-concierge/README.md`
  - `README.md`, `ATTRIBUTION_AND_LINEAGE.md`
- **Itens do Backlog Associados em "Arquivos & Linhas":**
  - [`BL-069`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L772) (🔴 CRÍTICA): Código Morto em Handlers SSE e Telemetria Reativa Congelada — **QUARENTENA**
  - [`BL-070`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L780) (🔴 CRÍTICA): Ciclo Infinito de Flapping SSE a cada 8s — **DEPENDE**
  - [`BL-071`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L789) (🔴 CRÍTICA): Colisão de Portas 8000, Falha no `dev:all` e Desconexão do FastMCP — **QUARENTENA**
  - [`BL-072`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L797) (🟠 GRAVE): Incompatibilidade de Autenticação FastMCP e Rejeição HTTP 401 — **DEPENDE** (o servidor MCP pode ser consumido por outros clientes FastMCP)
  - [`BL-073`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L805) (🟠 GRAVE): Omissão de Metadados em `get_full_topology` e Esvaziamento do `InspectorDrawer` — **DEPENDE** (`storage/store.py` precisa enriquecer `get_full_topology` para a ferramenta FastMCP homônima)
  - [`BL-074`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L813) (🟡 MÉDIA): Risco de Data Inválida (`Invalid Date`) por Concatenação `+ "Z"` — **QUARENTENA**
  - [`BL-075`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L821) (🟡 MÉDIA): Rotas Mutantes `/api/hsm/transition` Órfãs e Cliques Inertes no HUD — **QUARENTENA**
  - [`BL-076`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L829) (🟡 MÉDIA): 37 Erros de Linter e Violação de Pureza no React 19 — **QUARENTENA**
- **Desacoplamento Necessário para Remoção Segura:**
  - **Nenhum no backend Python.** Caso seja arquivado em `archive/v4-experimental/grafo-dashboard-web`, o script `npm run dev:all` no `package.json` raiz (se existente) deve ser ajustado para não tentar iniciar o Next.js.

---

## 3. Passo 2 — Respostas às Perguntas de Investigação (Regra 3)

### 3a. Quem escreve em `ast_edges` e `communities` em produção?

Executada busca literal com exclusão de testes, scratch e relatórios de auditoria:
```powershell
git grep -n -i -E "ast_edges|communities" -- . ':!tests' ':!scratch' ':!audits'
```

#### Leituras, Escritas e SQLs Montados:
1. **Tabela `ast_edges`:**
   - **Leituras:**
     - [`core/graph_rag.py:84, 94`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L84): CTE recursivo em `retrieve_multihop_context()` (`FROM ast_edges`).
     - [`core/graph_rag.py:179`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L179): CTE recursivo em `get_call_chain()` (`FROM ast_edges e`).
     - [`core/graph_rag.py:210`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L210): `SELECT child_node, COUNT(*) as in_degree FROM ast_edges GROUP BY child_node`.
     - [`core/graph_rag.py:219`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py#L219): `SELECT parent_node, child_node FROM ast_edges;`.
   - **Escritas / Mutações:**
     - [`core/alias_tracker.py:228, 232`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py#L228): `UPDATE ast_edges SET {parent_col} = ? WHERE {parent_col} = ?;`
   - **`INSERT INTO ast_edges` em Produção:**
     - **ABSOLUTAMENTE NENHUM.** Não existe nenhum `INSERT INTO ast_edges` em todo o código de produção de `core/`, `interface/`, `storage/`, `ingestion/` ou `services/`.
2. **Tabela `communities`:**
   - **Leituras:**
     - [`core/background_janitor.py:79`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L79): `SELECT id FROM communities WHERE is_dirty = 1;`.
     - [`core/delta_manager.py:169`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L169): `SELECT is_dirty, summary_text FROM communities WHERE id = ?;`.
   - **Escritas / Mutações:**
     - [`core/background_janitor.py:107`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L107): `UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;`.
     - [`core/delta_manager.py:192, 219, 242, 262`](file:///c:/Nexus-Memory/GrafoConcierge/core/delta_manager.py#L192): `UPDATE communities SET ... WHERE id = ?;`.
   - **`INSERT INTO communities` em Produção:**
     - **ABSOLUTAMENTE NENHUM.** O `delta_manager.py:219` tenta fazer `UPDATE communities SET is_dirty = 1 WHERE id = ?;` quando um novo arquivo é inserido, mas se a linha da comunidade não existir previamente, o UPDATE atualiza 0 linhas e nenhuma linha é criada.

#### Onde as Arestas Reais de AST são Gravadas?
As verdadeiras arestas de código da aplicação são persistidas na tabela **`edges`** (tabela oficial v3.8.0), via:
- [`ingestion/orchestrator.py:644-727`](file:///c:/Nexus-Memory/GrafoConcierge/ingestion/orchestrator.py#L644): O pipeline de ingestão AST mapeia dependências estruturais (`directory -> file`, `file -> symbol`) e de chamada (`call edges`) e as persiste em lote através de [`storage/store.py:384-465`](file:///c:/Nexus-Memory/GrafoConcierge/storage/store.py#L384) (`create_nodes_and_edges_bulk`) com a instrução:
  ```sql
  INSERT OR REPLACE INTO edges (source_id, target_id, relation_type, weight, confidence_tag) VALUES (?, ?, ?, ?, ?);
  ```
- E as comunidades oficiais de grafo são detectadas por [`services/janitor.py:506-557`](file:///c:/Nexus-Memory/GrafoConcierge/services/janitor.py#L506) navegando a tabela `edges` com queries recursivas `WITH RECURSIVE on edges`!

#### Funções que Leem de Tabelas que Ninguém Popula em Produção:
1. `core/graph_rag.py::retrieve_multihop_context()` (lê de `ast_edges`, que está sempre vazia em produção).
2. `core/graph_rag.py::get_call_chain()` (lê de `ast_edges`, retorna vazio em produção).
3. `core/graph_rag.py::detect_logical_communities()` (lê de `ast_edges`, retorna dicionário vazio em produção).
4. `core/background_janitor.py::run_idle_summarization()` (lê de `communities`, retorna zero comunidades em produção).

---

### 3b. Como o projeto chega às consultas de `files`?

Foram auditadas todas as 23 consultas à tabela `files` em produção. Nenhuma delas possui cláusula `WHERE project_uuid = ?` nem possui coluna de projeto na tabela.

#### Mapeamento por Ponto de Entrada:
1. **`DeltaManager.process_file_change(file_path, new_content, community_id)`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.** O método não recebe `project_uuid`.
   - *Chamadores reais:* Chamado exclusivamente em testes (`test_delta_sync.py`, `test_e2e_concierge_integration.py`).
2. **`Watcher.hydrate_known_hashes(db_manager)`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.** O handler recebe apenas `project_path` (caminho no disco), sem qualquer identificador relacional do projeto.
   - *Caminho:* Consulta `SELECT path FROM files;` globalmente.
3. **`AliasTracker.apply_alias_migration(old_path, new_path)`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.** O tracker não armazena nem recebe projeto.
   - *Caminho:* Executa `UPDATE files SET path = ? WHERE path = ?;` sem escopo.
4. **`Checkpointer.execute_time_travel(session_id, checkpoint_id)`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.** Opera apenas por `session_id`.
   - *Caminho:* Executa `UPDATE files SET is_dirty = 1 WHERE path = ?;` usando `task_id` como caminho.
5. **`BackgroundJanitor.run_idle_summarization()`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.**
   - *Caminho:* Executa `SELECT content FROM files WHERE community_id = ?;` de forma cega.
6. **`GraphRAG.retrieve_multihop_context(entry_node)`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.**
   - *Caminho:* Executa `SELECT path, community_id FROM files WHERE path = ?;`.
7. **`TelemetryAPI.get_telemetry_snapshot()`:**  
   - *Disponibilidade de `project_uuid`:* **NÃO.**
   - *Caminho:* Executa `SELECT COUNT(*) FROM files;` agregando todos os arquivos indiscriminadamente.

#### Quantidade de Locais a Mudar para Escopar por Projeto:
Para introduzir `project_uuid` na tabela `files`:
- DDL de `files`: adicionar `project_uuid TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE` e PK composta `PRIMARY KEY (project_uuid, path)`.
- Mutações e Consultas em Produção: **23 queries em 6 módulos** (`core/delta_manager.py`, `core/alias_tracker.py`, `core/checkpointer.py`, `core/background_janitor.py`, `core/graph_rag.py`, `interface/watcher.py`, `interface/telemetry_api.py`).
- Assinaturas de Métodos de Negócio: **8 assinaturas de métodos públicos**.

#### Demonstração de Colisão em Banco Limpo:
Executado script [`scratch/demonstrate_files_collision.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/demonstrate_files_collision.py) simulando dois projetos distintos (`proj-alpha` e `proj-beta`) contendo o mesmo arquivo relativo (`src/utils.py`):

```powershell
python scratch/demonstrate_files_collision.py
```

**Saída literal comprovada:**
```
--- 1. Projeto Alpha insere 'src/utils.py' ---
Alpha inserido com sucesso. Linhas na tabela files:
  ('src/utils.py', 'def alpha_fn(): pass', 'community_alpha')

--- 2. Projeto Beta tenta inserir 'src/utils.py' ---
COLISAO DETECTADA (IntegrityError): UNIQUE constraint failed: files.path

--- 3. E se usar INSERT OR REPLACE (ou ON CONFLICT)? ---
Resultado apos INSERT OR REPLACE:
  ('src/utils.py', 'def beta_fn(): pass', 'community_beta')
SOBREESCRITA SILENCIOSA: O arquivo do Projeto Beta apagou os dados do Projeto Alpha!
```

---

### 3c. O REST de estado de sessão (`/api/mcp/state`) é o único meio de alterar estado fora do MCP?

- **Chamadores em Produção:** **ZERO chamadores.** Nenhum módulo de produção chama `/api/mcp/state`.
- **Chamadores no Dashboard:** **ZERO chamadores.** O frontend `grafo-dashboard-web` nunca invoca esta rota.
- **Chamadores em Testes:** Apenas `tests/test_progressive_tool_disclosure.py:94`.
- **Mecanismo Nativo do FastMCP:** O servidor MCP já expõe a ferramenta nativa **`concierge_set_state`** em [`interface/mcp_server.py:423`](file:///c:/Nexus-Memory/GrafoConcierge/interface/mcp_server.py#L423):
  ```python
  @self._mcp.tool(name="concierge_set_state")
  def concierge_set_state(state_name: str, session_id: str = "default") -> dict:
      upper_state = state_name.upper()
      server._governor.set_session_state(session_id, upper_state)
      return {"success": True, "session_id": session_id, "active_state": ...}
  ```
- **Conclusão:** `/api/mcp/state` é completamente redundante em relação à ferramenta nativa FastMCP e não é utilizado por nenhum componente do sistema.

---

### 3d. Semântica do DELETE do `SemanticExtractor`

Auditado o fluxo de extração semântica em [`core/memory_extractor.py:177-194`](file:///c:/Nexus-Memory/GrafoConcierge/core/memory_extractor.py#L177) e [`storage/semantic_logic.py:53-71`](file:///c:/Nexus-Memory/GrafoConcierge/storage/semantic_logic.py#L53):

1. **Confirmação de Invalidação Temporal:**  
   Quando o modelo de extração emite uma ação `DELETE`, a função executa exclusivamente:
   ```python
   invalidate_semantic_fact(conn, t_id)
   ```
   A função `invalidate_semantic_fact` executa estritamente:
   ```sql
   UPDATE semantic_facts SET t_invalid = datetime('now') WHERE id = ?
   ```
   Portanto, **nenhum registro é apagado do disco**. O fato é apenas invalidado temporalmente.
2. **Deleção Física em `semantic_facts`:**  
   Busca exaustiva em todo o repositório confirmou que **NÃO EXISTE NENHUMA FUNÇÃO QUE EXECUTE `DELETE FROM semantic_facts`**. O banco opera sob retenção imutável para auditoria e histórico bayesiano.
3. **Reativação de Fatos Invalidados:**  
   **NÃO EXISTE NENHUMA FUNÇÃO QUE REATIVE UM FATO INVALIDADO.** Não há nenhuma instrução `UPDATE semantic_facts SET t_invalid = NULL`. Se um fato voltar a ser verdadeiro, o sistema insere uma NOVA linha via `insert_semantic_fact` com novo `id`, novo `t_valid` e `t_invalid = NULL`.

---

## 4. Passo 3 — Status Proposto por BL (Classificação dos 88 Itens)

A tabela abaixo classifica cada um dos 88 itens do backlog executivo em **ATIVO**, **QUARENTENA** ou **DEPENDE**, sem alterar numeração, títulos ou severidades:

### Resumo das Contagens:
- 🟢 **ATIVO:** 59 itens
- 🟡 **DEPENDE:** 5 itens ([`BL-014`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L299), [`BL-015`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L309), [`BL-070`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L780), [`BL-072`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L797), [`BL-073`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#L805))
- 🔴 **QUARENTENA:** 24 itens
- **Total:** 88 itens

### Tabela Completa dos 88 Itens:

| BL ID | Título | Severidade | Status Proposto | Justificativa Sintética |
| :--- | :--- | :--- | :--- | :--- |
| [`BL-001`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-001) | Omissão Estrutural de 5 Tabelas no Bootstrap Oficial de Produção | 🔴🔴 PRIORIDADE MÁXIMA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-002`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-002) | Inoperância Funcional de 12 Subsistemas Analíticos em Instalação Limpa | 🔴🔴 PRIORIDADE MÁXIMA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-003`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-003) | Padrão Test Mirage: 17 Suítes de Teste Criam Tabelas Privadas em `setUp()` | 🔴 CRÍTICA | **ATIVO** | Essencial para purgar Test Mirage e unificar schema oficial no core, mesmo que suítes de módulos podados sejam arquivadas. |
| [`BL-004`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-004) | Mascaramento de Erros DDL e Falsa Confirmação de Integridade no Boot | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-005`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-005) | Abandono da Especificação Arquitetural Formal (`01_ARCHITECTURE.md`) | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-006`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-006) | Colisão Estrutural entre Fila Real (`storage/`) e Zero Fila (`core/`) sobre o Banco | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-007`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-007) | Código Morto em Produção: `interface/queue_writer.py` | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-008`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-008) | Divergência de Integridade Referencial (`foreign_keys=OFF` no core vs `ON` em storage) | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-009`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-009) | Timeout Assimétrico de Conexão (5s em storage vs 30s no core) | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-010`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-010) | Quebra de Encapsulamento Privado `_gc._store._conn_mgr._db_path` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-011`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-011) | Bypass Total da Governança de Ferramentas via Injeção de `session_id` Fantasma | 🔴🔴 PRIORIDADE MÁXIMA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-012`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-012) | Ausência Total de Verificação de Posse em Checkpoints de Agentes | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-013`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-013) | Vazamento de 100% do Catálogo de Ferramentas em `list_tools()` | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-014`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-014) | Desconexão Total do Runtime Cognitivo no Servidor MCP | 🟠 GRAVE | **DEPENDE** | Cruza agent/run_agent.py (candidato), core/hsm_engine.py e interface/mcp_server.py (ativos). Se podar run_agent, o MCP não integra com runner mas mantém FSM. |
| [`BL-015`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-015) | Inicialização Insegura por Padrão (`default_state = "EXECUTION"`) | 🟡 MÉDIA | **DEPENDE** | Cruza core/mcp_governor.py (ativo) e interface/telemetry_api.py:357 (candidato). O MCPToolGovernor precisa de correção de estado inicial independentemente da telemetria. |
| [`BL-016`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-016) | Deadlock Inevitável em Escritas Aninhadas/Reentrantes no `SerializedWriteQueue` | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-017`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-017) | Bypass de Strict Scoping na Busca Vetorial com `project_uuids=[]` | 🔴 CRÍTICA (Vazamento Cross-Project) | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-018`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-018) | Vazamento Perpétuo de Conexões SQLite em Threads Finalizadas | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-019`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-019) | Incompatibilidade de Contrato em `init_fsm_checkpoints_schema` | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-020`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-020) | Falha de Tipo em `_calculate_decay` com Timestamps ISO Offset-Aware | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-021`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-021) | Falha ao Reiniciar `SerializedWriteQueue` após `stop()` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-022`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-022) | Crash com `ValueError` em Busca Vetorial com `node_id=None` ou Vazio | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-023`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-023) | Duplicação de Nós na CTE Recursiva `get_dependency_tree` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-024`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-024) | Isolamento de `semantic_logic.py` Força Violação de Encapsulamento | 🔵 BAIXA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-025`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-025) | Perda Total no Grafo na Renomeação de Arquivos | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-026`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-026) | Descarte Silencioso de 100% dos Resumos L0 com Gravação de `NULL` | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-027`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-027) | Falha Silenciosa de Persistência do L2 Compass no SQLite | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-028`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-028) | Acúmulo Perpétuo de Vetores Zumbis no ChromaDB | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-029`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-029) | Crash com `AttributeError` em Ingestão sem Summarizer | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-030`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-030) | Descarte Arbitrário de `requirements.txt` por `*.txt` no Ignore Padrão | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-031`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-031) | Poluição de Tags Semânticas por Substrings Ingênuas | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-032`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-032) | Truncamento de Código JS/TS por Contagem Ingênua de Chaves `{}` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-033`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-033) | Invocação de Método Fantasma `self.vector_db.get_all_ids()` | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-034`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-034) | Purga Garantida de 100% dos Vetores por Incompatibilidade `int` vs `str` | 🔴 CRÍTICA (Perda Catastrófica de Dados) | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-035`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-035) | Race Condition Destrutiva TOCTOU no Reconciliador Vetorial | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-036`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-036) | Falta de Paginação em `delete_batch` no Reconciliador Vetorial | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-037`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-037) | Despacho Ambíguo em `save_checkpoint` Corrompe Metadados e Apaga Estado | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-038`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-038) | Mascaramento de Falhas e Transação Não Atômica em `execute_time_travel` | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-039`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-039) | Granularidade Temporal de 1s Falha em Deletar Checkpoints em Rajadas | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-040`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-040) | Crash `json.JSONDecodeError` Não Tratado em `get_checkpoint` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-041`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-041) | Tipagem Insegura Mypy no Checkpointer (`None` Not Callable) | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-042`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-042) | Slice Negativo `[-0:]` com `keep_limit = 0` Preserva 100% dos Checkpoints | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-043`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-043) | Degradação Irreversível da Prioridade do Servidor para IDLE | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-044`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-044) | Deleção Cruzada de Checkpoints entre Agentes na Mesma Sessão | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-045`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-045) | Crash com `TypeError` em `_summarize_community` com `files.content = NULL` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-046`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-046) | TOCTOU / Descarte Cego de `is_dirty = 0` sobre Edições Recentes | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-047`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-047) | Vazamento de `unfinished_tasks` na `PriorityQueue` e Starvation | 🔴 CRÍTICA | **QUARENTENA** | Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento. |
| [`BL-048`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-048) | Starvation de Tarefas LOW Envelhecidas em Carga de 75% a 100% | 🟠 GRAVE | **QUARENTENA** | Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento. |
| [`BL-049`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-049) | Data Race / Lost Updates em `get_current_metrics()` sem Lock | 🟠 GRAVE | **QUARENTENA** | Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento. |
| [`BL-050`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-050) | Deadlock Eterno em `submit_request` sem Timeout e Após `shutdown()` | 🟠 GRAVE | **QUARENTENA** | Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento. |
| [`BL-051`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-051) | Cegueira de RPM no Fast-Path do RateGovernor | 🟡 MÉDIA | **QUARENTENA** | Mecanismo complexo de rate limiting multi-thread (core/rate_governor.py) proposto para arquivamento. |
| [`BL-052`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-052) | Evasão da Blacklist de Comandos Destrutivos do SecurityGuard | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-053`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-053) | `classify_command(None)` Lança `TypeError` Não Tratado | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-054`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-054) | Bug de Barra Dupla `C:\\\\` na Raiz Bloqueia 100% dos Arquivos em `is_safe_path` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-055`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-055) | Resolução de Caminhos Relativos Ancorada ao CWD do Processo e Não a `project_root` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-056`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-056) | Falsos Positivos de WARNING em Comandos Inofensivos Contendo `"build"` | 🔵 BAIXA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-057`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-057) | Método Fantasma `has_structural_change()` no DeltaManager | 🔴 CRÍTICA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-058`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-058) | Cegueira de LBH em Non-Python e SSH Incompleto | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-059`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-059) | Dupla Conexão Efêmera Crua por Mutação no DeltaManager | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-060`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-060) | TypeError em `compile_community_summary_jit()` quando `files.content` é NULL | 🔵 BAIXA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-061`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-061) | SSH Context-Free Captura Declarações Independentemente de Indentação | 🔵 BAIXA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-062`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-062) | Falha Fatal e Crash HTTP 500 na Telemetria por Tabelas Inexistentes | 🔴 CRÍTICA | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-063`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-063) | Inoperância Fora da Caixa por Dependência `get_db_manager` Não Configurada | 🔴 CRÍTICA | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-064`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-064) | Falso Stream Contínuo por Limite Hardcoded (`max_checks = 5`) | 🟠 GRAVE | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-065`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-065) | Invalidação Perpétua do SHA-256 no SSE por Timestamp Dinâmico | 🟠 GRAVE | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-066`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-066) | Insegurança Total de CORS e Falta de Autenticação em Rotas Mutantes | 🟠 GRAVE | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-067`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-067) | Crash de Tipagem em Timestamps na Telemetria (`NoneType` e `str`) | 🟡 MÉDIA | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-068`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-068) | Thread Daemônica Órfã Iniciada no Import de `telemetry_api` | 🟡 MÉDIA | **QUARENTENA** | Módulo periférico interface/telemetry_api.py proposto para arquivamento temporário. |
| [`BL-069`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-069) | Código Morto em Handlers SSE e Telemetria Reativa Congelada | 🔴 CRÍTICA | **QUARENTENA** | Frontend periférico grafo-dashboard-web proposto para arquivamento temporário. |
| [`BL-070`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-070) | Ciclo Infinito de Flapping SSE a cada 8s e Inundação do Feed de Eventos | 🔴 CRÍTICA | **DEPENDE** | Cruza grafo-dashboard-web e interface/telemetry_api.py:556. Se ambos forem podados, vai para QUARENTENA; se um for mantido, permanece ativo. |
| [`BL-071`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-071) | Colisão de Portas 8000, Falha no `dev:all` e Desconexão do FastMCP | 🔴 CRÍTICA | **QUARENTENA** | Frontend periférico grafo-dashboard-web proposto para arquivamento temporário. |
| [`BL-072`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-072) | Incompatibilidade de Autenticação FastMCP e Rejeição HTTP 401 | 🟠 GRAVE | **DEPENDE** | Cruza grafo-dashboard-web (candidato) e interface/mcp_server.py:186 (ativo). A rejeição HTTP 401 afeta o cliente MCP do dashboard e qualquer cliente FastMCP externo. |
| [`BL-073`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-073) | Omissão de Metadados em `get_full_topology` e Esvaziamento do `InspectorDrawer` | 🟠 GRAVE | **DEPENDE** | Cruza storage/store.py (ativo) e InspectorDrawer.tsx (candidato). A omissão de metadados em get_full_topology afeta a ferramenta MCP de topologia do núcleo. |
| [`BL-074`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-074) | Risco de Data Inválida (`Invalid Date`) por Concatenação `+ "Z"` | 🟡 MÉDIA | **QUARENTENA** | Frontend periférico grafo-dashboard-web proposto para arquivamento temporário. |
| [`BL-075`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-075) | Rotas Mutantes `/api/hsm/transition` Órfãs e Cliques Inertes no HUD | 🟡 MÉDIA | **QUARENTENA** | Frontend periférico grafo-dashboard-web proposto para arquivamento temporário. |
| [`BL-076`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-076) | 37 Erros de Linter e Violação de Pureza no React 19 | 🟡 MÉDIA | **QUARENTENA** | Frontend periférico grafo-dashboard-web proposto para arquivamento temporário. |
| [`BL-077`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-077) | Contaminação de Turnos Multi-Sessão no Circuit Breaker | 🔴 CRÍTICA CONDICIONAL | **QUARENTENA** | Runtime de agente experimental (agent/run_agent.py ou agent_prompts.py) proposto para arquivamento. |
| [`BL-078`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-078) | Vazamento de Privacidade por Fallback Inseguro Fail-Open em `check_contamination` | 🔴 CRÍTICA CONDICIONAL | **QUARENTENA** | Agente de auditoria periférico (agents/revisor_critico.py) proposto para arquivamento. |
| [`BL-079`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-079) | Aprovação Espúria de Commits Inválidos em `audit_with_retry` | 🟠 GRAVE CONDICIONAL | **QUARENTENA** | Agente de auditoria periférico (agents/revisor_critico.py) proposto para arquivamento. |
| [`BL-080`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-080) | Dessincronização de Estado e Diretrizes em `step(target_transition=...)` | 🟠 GRAVE CONDICIONAL | **QUARENTENA** | Runtime de agente experimental (agent/run_agent.py ou agent_prompts.py) proposto para arquivamento. |
| [`BL-081`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-081) | Falhas de Tipagem e Crash em Reranking (`NoneType` e `int` vs `str`) | 🟠 GRAVE CONDICIONAL | **QUARENTENA** | Agente de auditoria periférico (agents/revisor_critico.py) proposto para arquivamento. |
| [`BL-082`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-082) | Incompatibilidade Universal com Corrotinas e Bypass do RateGovernor em `execute_tool` | 🟡 MÉDIA CONDICIONAL | **QUARENTENA** | Runtime de agente experimental (agent/run_agent.py ou agent_prompts.py) proposto para arquivamento. |
| [`BL-083`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-083) | Dessincronização entre Sub-Estados do HSM e `TOOL_DISCLOSURE_MATRIX` | 🟡 MÉDIA CONDICIONAL | **QUARENTENA** | Runtime de agente experimental (agent/run_agent.py ou agent_prompts.py) proposto para arquivamento. |
| [`BL-084`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-084) | Contrato Fantasma de Cliente MCP Federado em `FederatedKnowledgeRouter` | 🟠 GRAVE | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-085`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-085) | Método Fantasma `insert()` em MockVectorDatabase Mascara Contrato de Inserção de Vetores | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-086`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-086) | Incompatibilidade de Assinatura e Retorno em `MockGraphRAGEngine.retrieve_multihop_context` | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-087`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-087) | Mock Permissivo com `*args, **kwargs` e Divergência de Interface em `_MockVectorStore` | 🔵 BAIXA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |
| [`BL-088`](file:///c:/Nexus-Memory/GrafoConcierge/audits/backlog-final.md#bl-088) | Falha de Atomicidade em `apply_alias_migration` (Migração Parcial sem Rollback) | 🟡 MÉDIA | **ATIVO** | Núcleo essencial do sistema mantido em produção. |

---

## 5. Passo 4 — Impacto nas Decisões de Desenho do Passo A

Analisa-se o impacto da quarentena dos candidatos sobre as 5 Decisões Humanas formuladas na Rodada 4.1 / Passo A ([`audits/fase4-1-inventario-ddl.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-1-inventario-ddl.md)):

### 5.1 Decisão Humana 1: Coluna `structural_hash` em `files`
- **Situação da Poda:** O leitor de `structural_hash` é [`interface/watcher.py:86, 208`](file:///c:/Nexus-Memory/GrafoConcierge/interface/watcher.py#L86). O `watcher.py` **NÃO está na lista de candidatos à poda** e permanece ativo.
- **Impacto:** **NENHUM.** A decisão permanece ativa e necessária. Se `watcher.py` for mantido, `structural_hash` deve constar no DDL de `files` ou `watcher.py` deve ser ajustado para consultar `ssh_hash`.

### 5.2 Decisão Humana 2: Default e Tipo de `last_modified` em `files`
- **Situação da Poda:** Embora `interface/telemetry_api.py:160` seja candidato à quarentena, [`core/checkpointer.py:201`](file:///c:/Nexus-Memory/GrafoConcierge/core/checkpointer.py#L201) e [`core/background_janitor.py:240`](file:///c:/Nexus-Memory/GrafoConcierge/core/background_janitor.py#L240) também consultam e atualizam `last_modified`, e ambos permanecem **ATIVOS**.
- **Impacto:** **NENHUM.** A Decisão 2 permanece necessária para evitar valores `NULL` que quebrem os módulos ativos de checkpointer e janitor.

### 5.3 Decisão Humana 3: Nomenclatura das Colunas de `ast_edges` (`parent_node` vs `parent_node_id`)
- **Situação da Poda:** [`core/graph_rag.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/graph_rag.py) e [`core/alias_tracker.py`](file:///c:/Nexus-Memory/GrafoConcierge/core/alias_tracker.py) são módulos centrais do core que permanecem **ATIVOS**.
- **Impacto:** **NENHUM.** A Decisão 3 permanece indispensável: consolidar `parent_node, child_node` no DDL para evitar que `graph_rag.py` quebre em `detect_logical_communities()`.

### 5.4 Decisão Humana 4: Nomenclatura Temporal em `agent_checkpoints` (`created_at` vs `timestamp`)
- **Situação da Poda:** O único leitor em produção que exige a coluna `timestamp` é [`interface/telemetry_api.py:183`](file:///c:/Nexus-Memory/GrafoConcierge/interface/telemetry_api.py#L183).
- **Impacto:** **IMPACTO DIRETO.** Se `telemetry_api.py` for enviado para quarentena, **a coluna `timestamp` perde 100% de seus consumidores em produção**. O DDL canônico de `agent_checkpoints` pode adotar estritamente `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` sem necessidade de redundância ou campo duplicado!

### 5.5 Decisão Humana 5: Tipo de Dado de `created_at` em `fsm_checkpoints` (`REAL` vs `TIMESTAMP`)
- **Situação da Poda:** O consumidor que executa `float(created_at)` é [`core/hsm_engine.py:457`](file:///c:/Nexus-Memory/GrafoConcierge/core/hsm_engine.py#L457), que permanece **ATIVO**.
- **Impacto:** **NENHUM.** A Decisão 5 permanece mandatória: o campo deve ser `REAL` para não causar `ValueError` na retomada de sessões do HSM.

---

## 6. Conclusão e Ponto de Parada (Gate)

Este relatório consolida todas as evidências objetivas e reprodutíveis para a decisão da poda de escopo:
1. Módulos periféricos como `telemetry_api.py`, `grafo-dashboard-web`, `rate_governor.py`, `revisor_critico.py`, `run_agent.py` e `nozomio_router.py` podem ser isolados com mudanças mínimas de desacoplamento, reduzindo drasticamente a carga do backlog (24 itens em quarentena imediata).
2. O núcleo de produção (`storage/`, `ingestion/`, `services/janitor.py`, `core/middleware.py`, `interface/mcp_server.py`) opera de forma autônoma e robusta sem esses periféricos.
3. A quarentena de `telemetry_api.py` simplifica diretamente o DDL canônico de `agent_checkpoints` (Decisão 4).

Em estrito cumprimento à **Regra 7 (Gates)**, nada é movido, removido ou desacoplado. A execução é interrompida aguardando a deliberação do usuário módulo a módulo.
