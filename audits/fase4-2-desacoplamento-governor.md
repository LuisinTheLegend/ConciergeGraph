# Relatório da Rodada 4.2 — Desacoplamento do Governor da Telemetria e Corte da Cadeia de Imports

> **Status:** Concluído com Sucesso e Validado  
> **Data:** 2026-10-21  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e 12 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Escopo:** Desacoplar `mcp_governor` de `interface.telemetry_api` e cortar a cadeia eager `interface/__init__.py` → `ActionHooks` → `RevisorCritico`.  
> **Fora de Escopo:** BL-015 (estado padrão EXECUTION mantido), BL-011 (autoescalada via set_state), quarentena (4.5), DDL de checkpoints (4.3).  
> **Regra 12 de Evidência:** Toda evidência (código, saída de comando, diff) foi gerada por redirecionamento físico para `scratch/evidencia_4_2/<nome>.txt 2>&1` e incluída por cópia mecânica direta.

---

## 1. Contexto Provado pelo Auditor (Pré-Execução)

### 1.1 Fiação Legada em `interface/mcp_server.py:150-155`
Origem: `scratch/evidencia_4_2/ctx_mcp_server_150_155.txt`
```python
        # Initialize sentinels for checkpoint, graph tools, and governor if not injected
        global db_manager, checkpointer, graph_rag, governor
        if governor is None:
            try:
                from interface.telemetry_api import mcp_governor
                governor = mcp_governor
            except Exception:
                from core.mcp_governor import MCPToolGovernor
                governor = MCPToolGovernor()

        self._governor = governor
```

### 1.2 Criação do Singleton em `interface/telemetry_api.py:57`
Origem: `scratch/evidencia_4_2/ctx_telemetry_57.txt`
```python
logger = logging.getLogger(__name__)

# Global singleton instance for MCP tool governance
mcp_governor = MCPToolGovernor()

# RateGovernor daemon singleton (SDD-SURVIVAL-23)
```

### 1.3 Import Eager em `interface/__init__.py` e Cadeia de Dependências
Origem: `scratch/evidencia_4_2/ctx_interface_init.txt`, `scratch/evidencia_4_2/ctx_action_hooks_32.txt`, `scratch/evidencia_4_2/ctx_agents_init_10.txt`
```python
from interface.mcp_server import GrafoConciergeServer
from interface.action_hooks import ActionHooks

__all__ = [
    "GrafoConciergeServer",
    "ActionHooks",
]
```
```python
from agents.revisor_critico import RevisorCritico
```
```python
from agents.revisor_critico import RevisorCritico

__all__ = [
    "RevisorCritico",
]
```

### 1.4 Diagnóstico da Cadeia de Carga Indevida Antes da Correção
Origem: `scratch/evidencia_4_2/ctx_import_drag_before.txt`
```text
['agents', 'agents.revisor_critico', 'interface.action_hooks']
```
Comprovado: a simples instrução `import interface.mcp_server` arrastava imediatamente os módulos `interface.action_hooks`, `agents` e `agents.revisor_critico`.

---

## 2. Parte 0 — Registro do Achado F4-013 (Incompatibilidade com MCP 2.x)

### 2.1 Versões Disponíveis de `mcp` no PyPI
Origem: `scratch/evidencia_4_2/p0_pip_index_mcp.txt`
```text
mcp (2.3.0)
Available versions: 2.3.0, 2.2.0, 2.1.1, 2.1.0, 2.0.1, 2.0.0, 1.30.0, 1.29.1, 1.29.0, 1.28.1, 1.28.0, 1.27.2, 1.27.1, 1.27.0, 1.26.0, 1.25.0, 1.24.0, 1.23.3, 1.23.2, 1.23.1, 1.23.0, 1.22.0, 1.21.2, 1.21.1, 1.21.0, 1.20.0, 1.19.0, 1.18.0, 1.17.0, 1.16.0, 1.15.0, 1.14.1, 1.14.0, 1.13.1, 1.13.0, 1.12.4, 1.12.3, 1.12.2, 1.12.1, 1.12.0, 1.11.0, 1.10.1, 1.10.0, 1.9.4, 1.9.3, 1.9.2, 1.9.1, 1.9.0, 1.8.1, 1.8.0, 1.7.1, 1.7.0, 1.6.0, 1.5.0, 1.4.1, 1.4.0, 1.3.0, 1.2.1, 1.2.0, 1.1.3, 1.1.2, 1.1.1, 1.1.0, 1.0.0, 0.9.1
  INSTALLED: 1.27.0
  LATEST:    2.3.0
```

### 2.2 Declaração Sem Teto Superior em `pyproject.toml` e `requirements.txt`
Origem: `scratch/evidencia_4_2/p0_grep_mcp_pins.txt`
```text
pyproject.toml:19:    "mcp", "memory", "graph", "ai-agents", "rag",
pyproject.toml:39:    "mcp>=1.0",
pyproject.toml:80:#   concierge-mcp                 (instead of python main.py)
pyproject.toml:84:concierge-mcp = "main:main"
requirements.txt:5:mcp>=1.0.0
```

### 2.3 Prova Experimental com `mcp>=2` em Venv Isolado
Origem: `scratch/evidencia_4_2/p0_mcp2_import_fail.txt`
```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    from mcp.server.fastmcp import FastMCP
  File "C:\Users\guial\AppData\Local\Temp\mcp2_venv\Lib\site-packages\mcp\server\fastmcp.py", line 16, in <module>
    raise ModuleNotFoundError(_MESSAGE, name=__name__)
ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import MCPServer) and other APIs changed; see the migration guide at https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver or pin 'mcp<2' to keep running v1 code.
```
Registrado formalmente em [`audits/fase4-achados.md`](file:///c:/Nexus-Memory/GrafoConcierge/audits/fase4-achados.md) como **F4-013** (🔴 CRÍTICA, Status ABERTO, aguardando decisão do dono).

---

## 3. Parte 1 — Testes Primeiro (Prova do Vermelho)

Criado [`tests/test_governor_wiring.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_governor_wiring.py) com 5 testes de contrato e fiação (T1 a T5), sem DDL e sem alterar banco de dados.

### 3.1 Execução no Código Anterior (Vermelho Provado)
Origem: `scratch/evidencia_4_2/p1_test_wiring_red.txt`
```text
tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks FAILED [ 20%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi FAILED [ 40%]
tests/test_governor_wiring.py::test_t3_governor_identity_matches_telemetry_mcp_governor PASSED [ 60%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails FAILED [ 80%]
tests/test_governor_wiring.py::test_t5_action_hooks_lazy_export_preserves_contract PASSED [100%]

================================== FAILURES ===================================
_______ test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks ________
E       AssertionError: Módulos arrastados indevidamente no import de interface.mcp_server: DRAGGED: ['agents.revisor_critico', 'agents', 'interface.action_hooks'] 

_____ test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi ______
E       AssertionError: Módulos arrastados na construção de GrafoConciergeServer: DRAGGED: ['interface.telemetry_api', 'fastapi']

_____ test_t4_governor_uses_shared_singleton_when_telemetry_import_fails ______
E       AssertionError: core.mcp_governor deve expor get_shared_governor()

=================== 3 failed, 2 passed, 1 warning in 43.00s ===================
```

---

## 4. Parte 2 — Implementação Mínima

Executada em dois commits separados conforme exigência:
1. **Commit 1 (`8640165`):** 2.1 + 2.2 + 2.3
   - `core/mcp_governor.py`: adicionado `get_shared_governor()` com instância lazy única compartilhada.
   - `interface/mcp_server.py`: obtenção do governor via `get_shared_governor()`, eliminando o import de `interface.telemetry_api` e o fallback duplicador.
   - `interface/telemetry_api.py`: `mcp_governor = get_shared_governor()`, mantendo compatibilidade com todos os testes que consom a telemetria.
2. **Commit 2 (`0244183`):** 2.4
   - `interface/__init__.py`: exportação de `ActionHooks` via `__getattr__` (PEP 562), mantendo `__all__ = ["GrafoConciergeServer", "ActionHooks"]` e eliminando imports de nível superior de `action_hooks.py` e `agents`.

---

## 5. Parte 3 — Verificação e Provas do Verde

### 5.1 Testes T1 a T5 Verdes
Origem: `scratch/evidencia_4_2/p3_test_wiring_green.txt`
```text
tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 20%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi PASSED [ 40%]
tests/test_governor_wiring.py::test_t3_governor_identity_matches_telemetry_mcp_governor PASSED [ 60%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails PASSED [ 80%]
tests/test_governor_wiring.py::test_t5_action_hooks_lazy_export_preserves_contract PASSED [100%]

======================== 5 passed, 1 warning in 43.61s ========================
```

### 5.2 Prova de Alcance Vazia (Item 3.4)
Origem: `scratch/evidencia_4_2/p3_reach_proof.txt`
```text
[]
```
Ao executar `import interface.mcp_server`, nenhum dos 5 módulos (`agents`, `agents.revisor_critico`, `interface.action_hooks`, `interface.telemetry_api`, `fastapi`) reside em `sys.modules`.

### 5.3 Regressão de Runtime da Matriz de Ferramentas (Item 3.3)
Reexecutado `scratch/fase4_0c_tool_matrix.py` e confrontado com a matriz da 4.0c via `scratch/compare_matrix.py`.  
Origem: `scratch/evidencia_4_2/p3_matrix_diff.txt`
```text
======================================================================
COMPARACAO DA MATRIZ DE FERRAMENTAS MCP (31 FERRAMENTAS)
======================================================================
Total de ferramentas testadas original: 31
Total de ferramentas testadas atual:    31
  [IDENTICO] add_reference_wing         -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] agent_get_checkpoint       -> Original: EXCEÇÃO                | Atual: EXCEÇÃO
  [IDENTICO] agent_list_checkpoints     -> Original: EXCEÇÃO                | Atual: EXCEÇÃO
  [IDENTICO] agent_save_checkpoint      -> Original: ERRO DE NEGÓCIO        | Atual: ERRO DE NEGÓCIO
  [IDENTICO] concierge_commit           -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_feedback         -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_get_call_chain   -> Original: EXCEÇÃO                | Atual: EXCEÇÃO
  [IDENTICO] concierge_get_memory       -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_list_facts       -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_list_projects    -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_load             -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_mine             -> Original: SUCESSO VAZIO          | Atual: SUCESSO VAZIO
  [IDENTICO] concierge_register         -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_resume           -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_search           -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_set_memory       -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_set_state        -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_status           -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_store_fact       -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] concierge_wakeup           -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [DIVERGENTE] count_embeddings           -> Original: SUCESSO VAZIO          | Atual: SUCESSO COM DADOS
  [IDENTICO] delete_project             -> Original: NEGADO PELO GOVERNOR   | Atual: NEGADO PELO GOVERNOR
  [IDENTICO] find_similar               -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] get_callers                -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] get_full_topology          -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] get_implementations        -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] get_trajectories           -> Original: SUCESSO VAZIO          | Atual: SUCESSO VAZIO
  [IDENTICO] remove_reference_wing      -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] reset_collection           -> Original: NEGADO PELO GOVERNOR   | Atual: NEGADO PELO GOVERNOR
  [IDENTICO] search_symbols             -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS
  [IDENTICO] update_project             -> Original: SUCESSO COM DADOS      | Atual: SUCESSO COM DADOS

--- RESUMO DA COMPARACAO ---
ATENCAO: 1 divergencias encontradas:
  - count_embeddings: SUCESSO VAZIO -> SUCESSO COM DADOS
======================================================================
```
*Nota Técnica sobre a Divergência Positiva de `count_embeddings`:* Na Rodada 4.0c, a ferramenta `count_embeddings` retornava contagem 0 ("SUCESSO VAZIO") porque o Bug F4-006 do `RichHandler` abortava a mineração antes de gravar vetores. Com a correção de F4-006 na Rodada 4.1/B e geração real de embeddings, o fixture persiste 9 embeddings no banco vetorial temporário, fazendo `count_embeddings` retornar `count: 9` ("SUCESSO COM DADOS"). Todas as outras 30 ferramentas mantiveram comportamento estritamente idêntico.

### 5.4 Suíte Completa de Testes (Item 3.2)
Origem: `scratch/baseline_fase4_20261021_rodada4_2.txt`
```text
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 354 passed, 1 skipped, 22 warnings in 89.63s (0:01:29)
```
Resultado: **354 passed (+5 testes novos de wiring), 1 skipped, 1 failed (BL-015, baseline conhecido fora de escopo)**. Zero regressões.
