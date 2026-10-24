# Relatório da Rodada 4.2b — Limite de Versão do `mcp` (F4-013), Prova de Instalação Limpa e Correção do T4

> **Status:** Concluído com Sucesso e Validado  
> **Data:** 2026-10-24  
> **Base Normativa:** Regras 2, 3, 4, 7, 10, 11 e 12 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md)  
> **Escopo:** Pin de versão `mcp>=1.27,<2` em `pyproject.toml` e `requirements.txt` (F4-013), teste-guarda de dependências, script cliente MCP de prova de boot real via stdio (`scratch/boot_check.py`), prova do vermelho e verde em venvs isolados com `mcp 2.3.0`, `mcp 1.27.0` e `mcp 1.30.0`, correção do T4 com isolamento de sentinelas globais e validação mutante em worktree, documentação de observações da instalação limpa (F4-014).  
> **Fora de Escopo:** Publicação no PyPI, alteração da versão do pacote (3.8.2), BL-015, BL-011, 4.3 a 4.5, migração para a API de `mcp 2.x`, qualquer banco de dados real (`data/`).  
> **Regra 12 de Evidência:** Toda evidência (código, saída de comando, diff) foi gerada por redirecionamento físico para `scratch/evidencia_4_2b/<nome>.txt 2>&1` e incluída por cópia mecânica direta.

---

## 1. Parte 1 — Script de Prova de Inicialização Real (`scratch/boot_check.py`)

Desenvolvido o script [`scratch/boot_check.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/boot_check.py) exercitando o cliente MCP real (`mcp.client.stdio.stdio_client` + `ClientSession`):
1. Inicia o servidor como processo filho com o Python do venv sob teste (`<venv>/Scripts/python main.py` ou console script `<venv>/Scripts/concierge-mcp.exe`);
2. Aponta `GRAFO_DB_PATH` e `GRAFO_CHROMA_PATH` para diretório temporário isolado (`tempfile.mkdtemp()`), com `GRAFO_TRANSPORT=stdio`, garantindo que **nunca** toque em `data/`;
3. Executa `initialize`, obtém `list_tools` e afirma estritamente 31 ferramentas;
4. Executa `concierge_status` e valida o retorno sem erro;
5. Encerra o processo de forma limpa com timeout configurável (default: 180s);
6. Códigos de saída estritos: `0` = sucesso total, `1` = falha com impressão de erro e stacktrace.

---

## 2. Parte 2 — Vermelho Real (Estado Anterior Sem Pins Superiores)

Criado venv novo e temporário `%TEMP%\inst_red` e instalado o repositório em seu estado antes da correção de pins.

### 2.1 Versão Resolvida do `mcp` no `pip freeze`
Origem: `scratch/evidencia_4_2b/p2_pip_freeze_red.txt` (filtrado por `mcp`)
```text
mcp==2.3.0
mcp-types==2.3.0
```

### 2.2 Execução do `boot_check.py` no Venv Red (Falha Provada)
Origem: `scratch/evidencia_4_2b/p2_boot_check_red.txt`
```text
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   Grafo Concierge v3.8.0 ─ Absolute Solidity
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   DB:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_concierge.db
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   ChromaDB: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_chroma (test_boot_collection)
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   Embedding: all-MiniLM-L6-v2
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   LLM:      gemini-2.0-flash
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   Janitor:  300s
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   Transport: stdio
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │   Log Level: INFO
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-10-24 18:50:05 │ INFO    │ grafo-concierge.main         │ Initializing SqliteStore: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_concierge.db
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.schema       │ Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.store        │ Schema v3.8.0 verified - all tables and triggers OK.
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.connection   │ SerializedWriteQueue started successfully (db: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_concierge.db)
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.store        │ SqliteStore initialized: C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_concierge.db
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.main         │ Initializing EmbeddingManager: tier=FLASH
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.vector-store │ EmbeddingManager initialized: tier=flash, model=all-MiniLM-L6-v2, dims=384
2026-10-24 18:51:47 │ INFO    │ grafo-concierge.main         │ Initializing ChromaVectorStore: path=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_chroma, collection=test_boot_collection
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.vector-store │ ChromaVectorStore initialized: dir=C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_chroma, collection=test_boot_collection, tier=flash
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.main         │ Initializing ZoomSummarizer: model=gemini-2.0-flash
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.summarizer   │ LLMAdapter inicializado: model=gemini-2.0-flash, custom_fn=False
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.main         │ Initializing IngestionManager
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.crawler      │ ProjectCrawler initialized: 22 active ignore patterns.
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.orchestrator │ IngestionManager inicializado: summarizer=ON, embedder_tier=flash
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.main         │ Initializing JanitorService: interval=300s
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.janitor      │ JanitorService initialized: stale=30d, zoom_threshold=10, inactive=60d, super_node_threshold=10
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConcierge Central Facade
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.middleware   │ GrafoConcierge (Facade) initialized successfully.
2026-10-24 18:51:48 │ INFO    │ grafo-concierge.main         │ Initializing GrafoConciergeServer
2026-10-24 18:51:49 │ CRITICAL │ grafo-concierge.main         │ Fatal error during execution: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import MCPServer) and other APIs changed; see the migration guide at https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver or pin 'mcp<2' to keep running v1 code.
Traceback (most recent call last):
  File "C:\Nexus-Memory\GrafoConcierge\main.py", line 234, in main
    server, janitor, store = bootstrap()
                             ~~~~~~~~~^^
  File "C:\Nexus-Memory\GrafoConcierge\main.py", line 196, in bootstrap
    from interface.mcp_server import GrafoConciergeServer
  File "C:\Nexus-Memory\GrafoConcierge\interface\__init__.py", line 12, in <module>
    from interface.mcp_server import GrafoConciergeServer
  File "C:\Nexus-Memory\GrafoConcierge\interface\mcp_server.py", line 47, in <module>
    from mcp.server.fastmcp import FastMCP
  File "C:\Users\guial\AppData\Local\Temp\inst_red\Lib\site-packages\mcp\server\fastmcp.py", line 16, in <module>
    raise ModuleNotFoundError(_MESSAGE, name=__name__)
ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import MCPServer) and other APIs changed; see the migration guide at https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver or pin 'mcp<2' to keep running v1 code.
2026-10-24 18:51:49 │ INFO    │ grafo-concierge.main         │ Graceful shutdown initiated...
2026-10-24 18:51:49 │ INFO    │ grafo-concierge.main         │ ============================================================
2026-10-24 18:51:49 │ INFO    │ grafo-concierge.main         │   Grafo Concierge encerrado com sucesso.
2026-10-24 18:51:49 │ INFO    │ grafo-concierge.main         │ ============================================================

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
BOOT CHECK FAILED: unhandled errors in a TaskGroup (1 sub-exception)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

======================================================================
BOOT CHECK ─ Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Users\guial\AppData\Local\Temp\inst_red\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 2.3.0
Entrypoint Mode:    python-main
Timeout:            180.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_dgyn_8m7\test_chroma
======================================================================
Executando comando: C:\Users\guial\AppData\Local\Temp\inst_red\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
```

---

## 3. Parte 3 — Teste-Guarda do Limite (`tests/test_dependency_pins.py`)

Criado [`tests/test_dependency_pins.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_dependency_pins.py) validando que `pyproject.toml` e `requirements.txt` rejeitem `"2.0.0"` e aceitem `"1.27.0"`.

### 3.1 Prova do Vermelho (Código Anterior com `mcp>=1.0`)
Origem: `scratch/evidencia_4_2b/p3_test_pins_red.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 2 items

tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 FAILED [ 50%]
tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 FAILED [100%]

================================== FAILURES ===================================
______ test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 ______

    def test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0():
        """Garante que pyproject.toml rejeite mcp 2.0.0 e aceite mcp 1.27.0."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        assert pyproject_path.is_file(), f"Arquivo nao encontrado: {pyproject_path}"
    
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    
        dependencies = data.get("project", {}).get("dependencies", [])
        mcp_req = None
        for dep_str in dependencies:
            req = Requirement(dep_str)
            if req.name == "mcp":
                mcp_req = req
                break
    
        assert mcp_req is not None, "Dependencia 'mcp' nao encontrada em pyproject.toml"
>       assert Version("2.0.0") not in mcp_req.specifier, (
            f"pyproject.toml permite indevidamente mcp 2.0.0: specifier={mcp_req.specifier}"
        )
E       AssertionError: pyproject.toml permite indevidamente mcp 2.0.0: specifier=>=1.0
E       assert <Version('2.0.0')> not in <SpecifierSet('>=1.0')>
E        +  where <Version('2.0.0')> = Version('2.0.0')
E        +  and   <SpecifierSet('>=1.0')> = <Requirement('mcp>=1.0')>.specifier

tests\test_dependency_pins.py:43: AssertionError
____ test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 _____

    def test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0():
        """Garante que requirements.txt rejeite mcp 2.0.0 e aceite mcp 1.27.0."""
        requirements_path = REPO_ROOT / "requirements.txt"
        assert requirements_path.is_file(), f"Arquivo nao encontrado: {requirements_path}"
    
        mcp_req = None
        with open(requirements_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                req = Requirement(line)
                if req.name == "mcp":
                    mcp_req = req
                    break
    
        assert mcp_req is not None, "Dependencia 'mcp' nao encontrada em requirements.txt"
>       assert Version("2.0.0") not in mcp_req.specifier, (
            f"requirements.txt permite indevidamente mcp 2.0.0: specifier={mcp_req.specifier}"
        )
E       AssertionError: requirements.txt permite indevidamente mcp 2.0.0: specifier=>=1.0.0
E       assert <Version('2.0.0')> not in <SpecifierSet('>=1.0.0')>
E        +  where <Version('2.0.0')> = Version('2.0.0')
E        +  and   <SpecifierSet('>=1.0.0')> = <Requirement('mcp>=1.0.0')>.specifier

tests\test_dependency_pins.py:68: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0
FAILED tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0
============================== 2 failed in 0.33s ==============================
```

### 3.2 Prova do Verde (Após Pin `mcp>=1.27,<2`)
Origem: `scratch/evidencia_4_2b/p3_test_pins_green.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 2 items

tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 50%]
tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [100%]

============================== 2 passed in 0.12s ==============================
```

---

## 4. Parte 4 — Correção Mínima de Dependências e Provas de Boot

### 4.1 Validação Experimental dos Limites 1.x
Origem: `scratch/evidencia_4_2b/p4_pip_index_mcp.txt`
- Versões 1.x disponíveis: `1.0.0` a `1.30.0`.
- Menor versão testada: `1.27.0`. Maior versão 1.x disponível: `1.30.0`.
- Ambas testadas em venvs limpos dedicados com `boot_check.py` obtendo código de saída 0 e 31 ferramentas ativas:
  - `mcp==1.27.0`: `scratch/evidencia_4_2b/p4_boot_check_1_27.txt` (`BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK`)
  - `mcp==1.30.0`: `scratch/evidencia_4_2b/p4_boot_check_1_30.txt` (`BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK`)

### 4.2 Prova de Verde da Instalação Limpa em `%TEMP%\inst_green`
Instalação limpa via `pip install <repo>` em `%TEMP%\inst_green`.
Origem: `scratch/evidencia_4_2b/p4_pip_freeze_green.txt`
```text
mcp==1.30.0
```

#### Modo 1 — Execução via `python main.py`
Origem: `scratch/evidencia_4_2b/p4_boot_check_green_main.txt` (trecho final)
```text
======================================================================
BOOT CHECK ─ Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Users\guial\AppData\Local\Temp\inst_green\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.30.0
Entrypoint Mode:    python-main
Timeout:            180.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_6q8_4amd\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_6q8_4amd\test_chroma
======================================================================
Executando comando: C:\Users\guial\AppData\Local\Temp\inst_green\Scripts\python.exe main.py
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.30.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.002
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
```

#### Modo 2 — Execução via Console Script `concierge-mcp`
Origem: `scratch/evidencia_4_2b/p4_boot_check_green_console.txt` (trecho final)
```text
======================================================================
BOOT CHECK ─ Grafo Concierge MCP Server
======================================================================
Target Python:      C:\Users\guial\AppData\Local\Temp\inst_green\Scripts\python.exe
Target Python Ver:  3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
Target MCP Version: 1.30.0
Entrypoint Mode:    console-script
Timeout:            180.0s
Repo Root:          C:\Nexus-Memory\GrafoConcierge
Temp DB Path:       C:\Users\guial\AppData\Local\Temp\grafo_boot_check_1nplcvyn\test_concierge.db
Temp Chroma Path:   C:\Users\guial\AppData\Local\Temp\grafo_boot_check_1nplcvyn\test_chroma
======================================================================
Executando comando: C:\Users\guial\AppData\Local\Temp\inst_green\Scripts\concierge-mcp.exe 
Iniciando sessao MCP e enviando initialize...
[OK] MCP Initialized: name='Grafo Concierge' title=None version='1.30.0' websiteUrl=None icons=None
Listando ferramentas com list_tools...
[OK] Total de ferramentas registradas: 31
Executando chamada a 'concierge_status'...
[OK] concierge_status resultado: isError=False
     Status Content: {
  "success": true,
  "system": "Grafo Concierge v3.8.0",
  "components": {
    "sqlite": {
      "status": "healthy",
      "total_projects": 0
    },
    "janitor": {
      "status": "idle",
      "total_runs": 0
    }
  },
  "duration_seconds": 0.002
}
======================================================================
BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.
======================================================================
```

---

## 5. Parte 5 — Correção do T4 e Prova Cabal com Mutante

No início de `test_t4_governor_uses_shared_singleton_when_telemetry_import_fails` em [`tests/test_governor_wiring.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_governor_wiring.py), foi adicionado o isolamento explícito de sentinelas:
```python
    monkeypatch.setattr("interface.mcp_server.governor", None)
    monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
    monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
```

### 5.1 Prova Cabal com Mutante em Worktree Descartável
Criado worktree temporário descartável (`git worktree add --detach %TEMP%\mutant_worktree HEAD`), restaurado o código antigo mutante em `interface/mcp_server.py` (`try: from interface.telemetry_api import mcp_governor ... except: MCPToolGovernor()`) e executado o **arquivo inteiro** de teste.  
Origem: `scratch/evidencia_4_2b/p5_mutant_test_fails.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\guial\AppData\Local\Temp\mutant_worktree
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 20%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi FAILED [ 40%]
tests/test_governor_wiring.py::test_t3_governor_identity_matches_telemetry_mcp_governor PASSED [ 60%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails FAILED [ 80%]
tests/test_governor_wiring.py::test_t5_action_hooks_lazy_export_preserves_contract PASSED [100%]

================================== FAILURES ===================================
_____ test_t4_governor_uses_shared_singleton_when_telemetry_import_fails ______

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-57/test_t4_governor_uses_shared_s0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000016D46D91350>

    def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path, monkeypatch):
        """T4: Com sys.modules['interface.telemetry_api'] = None (import quebrado), o servidor usa o MESMO singleton compartilhado."""
        # Zera sentinelas globais para garantir isolamento estrito e independencia de ordem
        monkeypatch.setattr("interface.mcp_server.governor", None)
        monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
        monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
        monkeypatch.setattr("interface.mcp_server.graph_rag", None, raising=False)
    
        import core.mcp_governor
        assert hasattr(core.mcp_governor, "get_shared_governor"), "core.mcp_governor deve expor get_shared_governor()"
        shared_gov = core.mcp_governor.get_shared_governor()
    
        # Simula falha total ao importar interface.telemetry_api
        monkeypatch.setitem(sys.modules, "interface.telemetry_api", None)
    
        db_file = str(tmp_path / "test_t4.db")
        store = SqliteStore(db_file)
        gc = MagicMock()
        gc._store = store
        server = GrafoConciergeServer(concierge=gc)
    
>       assert server._governor is shared_gov, "Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar"
E       AssertionError: Servidor deve usar o singleton get_shared_governor() mesmo se telemetry_api falhar
E       assert <core.mcp_governor.MCPToolGovernor object at 0x0000016D46D96FD0> is <core.mcp_governor.MCPToolGovernor object at 0x0000016D469E30E0>
E        +  where <core.mcp_governor.MCPToolGovernor object at 0x0000016D46D96FD0> = <interface.mcp_server.GrafoConciergeServer object at 0x0000016D46D96E90>._governor

tests\test_governor_wiring.py:91: AssertionError
```
O worktree foi sumariamente descartado via `git worktree remove --force %TEMP%\mutant_worktree`.

### 5.2 Suíte de Wiring 100% Verde no Código Atual
Origem: `scratch/evidencia_4_2b/p5_test_wiring_all_green.txt`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 5 items

tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 20%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi PASSED [ 40%]
tests/test_governor_wiring.py::test_t3_governor_identity_matches_telemetry_mcp_governor PASSED [ 60%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails PASSED [ 80%]
tests/test_governor_wiring.py::test_t5_action_hooks_lazy_export_preserves_contract PASSED [100%]

============================== warnings summary ===============================
..\..\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\guial\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 5 passed, 1 warning in 43.07s ========================
```

---

## 6. Parte 6 — Observações da Instalação Limpa (Achado F4-014)

1. **Ausência de módulos `tree_sitter`:**
   Origem: `scratch/evidencia_4_2b/p6_tree_sitter_probe.txt`
   ```text
   Python version: 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
   ============================================================
   tree_sitter              : NOT INSTALLED (No module named 'tree_sitter')
   tree_sitter_python       : NOT INSTALLED (No module named 'tree_sitter_python')
   tree_sitter_javascript   : NOT INSTALLED (No module named 'tree_sitter_javascript')
   tree_sitter_typescript   : NOT INSTALLED (No module named 'tree_sitter_typescript')
   tree_sitter_go           : NOT INSTALLED (No module named 'tree_sitter_go')
   tree_sitter_rust         : NOT INSTALLED (No module named 'tree_sitter_rust')
   ```
   *Impacto:* Para código Python, o ingestor recorre a `ast` nativo sem prejuízo. Porém, para JavaScript, TypeScript, Go e Rust, o ingestor emite warning e degrada para regex ou chunking `_parse_raw` (sem extração de chamadas estruturadas). Registrado como **F4-014** (🟡 MÉDIA, ABERTO).
2. **Aviso de `pydantic_settings`:**
   Em `pydantic_settings/sources/utils.py:51`, detectado aviso `IncompleteFieldDefinitionWarning: Field 'lifespan' has an incomplete definition...`.
3. **Depreciações de bibliotecas de terceiros no Python 3.14:**
   - ChromaDB OpenTelemetry: `'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16`.
   - `datetime.datetime.utcnow()` no SQLite store/logic.

---

## 7. Baseline da Suíte Completa de Testes

Execução completa em `scratch/baseline_fase4_20261024_rodada4_2b.txt`:
```text
FAILED tests/test_progressive_tool_disclosure.py::TestProgressiveToolDisclosure::test_telemetry_api_mcp_state_endpoints
1 failed, 356 passed, 1 skipped, 22 warnings in 90.66s (0:01:30)
```
- **356 passed** (354 anteriores + 2 novos testes de pins);
- **1 skipped**;
- **1 failed** (`test_telemetry_api_mcp_state_endpoints` de BL-015, baseline conhecido fora de escopo).

---

## 8. Preservação de Quebras de Linha (`git diff --stat`)

A verificação por `git diff --stat` nos commits de código comprovou que apenas as linhas estritamente necessárias foram alteradas, preservando os line endings nativos de cada arquivo:
```text
 pyproject.toml                 | 2 +-
 requirements.txt               | 2 +-
 tests/test_governor_wiring.py  | 6 ++++++
 3 files changed, 8 insertions(+), 2 deletions(-)
```
