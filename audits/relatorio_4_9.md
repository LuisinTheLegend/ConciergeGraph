# Relatório de Preparação de Release `v4.1.0` — Rodada 4.9

- **Commit base obrigatório:** `2d43180639dda65fb2aa7c6262182ff58270a342` (`2d43180`)
- **Escopo:** Bump do pacote `concierge-graph` para `4.1.0`, versão dinâmica em CLI/MCP e `docker-smoke`, docs de release `v4.1.0`, reconversão UTF-8 de `audits/relatorio_4_8.md`, build `sdist` + `wheel` em diretório temporário e smoke install em ambiente virtual isolado (sem criação de `git tag`, `gh release` ou upload PyPI — ações exclusivas do humano).
- **Caminhos proibidos (`2d43180639dda65fb2aa7c6262182ff58270a342..HEAD`):** `0 bytes` (`core/`, `storage/` incluindo `storage/schema.py`, `ingestion/`, `services/`, `interface/queue_writer.py`, `interface/__init__.py`, `scripts/`, `main.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `requirements.txt`, `requirements-dev.txt`, `.github/workflows/windows-stdin.yml`, `archive/` intactos).

---

## 1. Linha do Tempo de Commits (`git log --format="%H %s"`)

```text
54d50740028211d0244532d6618f1bd53298c1e6 chore(release): bump package to 4.1.0, use dynamic version in CLI/MCP and CI docker-smoke (4.9-C1)
2d43180639dda65fb2aa7c6262182ff58270a342 docs(audit): update docs, record 4.8 decisions and final report (4.8-C4)
142b995ab4699867c1323e3e069f58f8af59e67d build(docker,ci): harden non-root SSE Dockerfile, compose healthcheck and add CI docker-smoke (4.8-C3)
5c95a79ed378ff8ef4753042aaa54f9ccd3525a1 build(packaging): migrate SPDX license, split requirements-dev and harden wheel/dep guards (4.8-C2)
```

---

## 2. Preflight (Passo 0)

```text
$ git rev-parse HEAD
[exit=0]
2d43180639dda65fb2aa7c6262182ff58270a342

$ git rev-parse origin/main
[exit=0]
2d43180639dda65fb2aa7c6262182ff58270a342

$ .venv_313\Scripts\python.exe -m pytest tests/ -q
[exit=0]
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 98%]
.......                                                                  [100%]
============================== warnings summary ===============================
tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-340
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-342
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-359
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
367 passed, 21 warnings in 123.14s (0:02:03)

$ .venv_313\Scripts\flake8 main.py core storage ingestion services interface scripts tests --count --select=E9,F63,F7,F82 --show-source --statistics
[exit=0]
0
```

---

## 3. Etapa C1 — Bump para `4.1.0`, CLI/MCP Dinâmicos e CI `docker-smoke`

### `c1_red.txt`
```text
$ .venv_313\Scripts\python.exe -m pytest tests/test_cli_mcp_entrypoint.py tests/test_dependency_pins.py tests/test_wheel_integrity.py -v --tb=short
[exit=1]
============================= test session starts =============================
platform win32 -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
timeout: 300.0s
timeout method: thread
timeout func_only: False
collecting ... collected 12 items

tests/test_cli_mcp_entrypoint.py::test_cli_help_exits_zero_without_blocking_stdin PASSED [  8%]
tests/test_cli_mcp_entrypoint.py::test_cli_version_exits_zero_with_real_package_version FAILED [ 16%]
tests/test_cli_mcp_entrypoint.py::test_parse_args_supports_transport_defaults_and_rejects_invalid PASSED [ 25%]
tests/test_cli_mcp_entrypoint.py::test_get_package_version_fallbacks FAILED [ 33%]
tests/test_cli_mcp_entrypoint.py::test_main_transport_cli_overrides_global_and_preserves_zero_arg_wiring PASSED [ 41%]
tests/test_cli_mcp_entrypoint.py::test_concierge_cli_version_and_status_use_dynamic_package_version FAILED [ 50%]
tests/test_cli_mcp_entrypoint.py::test_mcp_server_status_uses_dynamic_package_version FAILED [ 58%]
tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 66%]
tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 75%]
tests/test_dependency_pins.py::test_pyproject_spdx_metadata_build_requires_and_clean_core_deps FAILED [ 83%]
tests/test_dependency_pins.py::test_requirements_txt_is_prod_only_and_requirements_dev_exists PASSED [ 91%]
tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints FAILED [100%]

================================== FAILURES ===================================
____________ test_cli_version_exits_zero_with_real_package_version ____________
tests\test_cli_mcp_entrypoint.py:65: in test_cli_version_exits_zero_with_real_package_version
    assert expected_version == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
_____________________ test_get_package_version_fallbacks ______________________
tests\test_cli_mcp_entrypoint.py:109: in test_get_package_version_fallbacks
    assert expected_version == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
______ test_concierge_cli_version_and_status_use_dynamic_package_version ______
tests\test_cli_mcp_entrypoint.py:166: in test_concierge_cli_version_and_status_use_dynamic_package_version
    assert expected_version == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
_____________ test_mcp_server_status_uses_dynamic_package_version _____________
tests\test_cli_mcp_entrypoint.py:194: in test_mcp_server_status_uses_dynamic_package_version
    assert expected_version == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
_______ test_pyproject_spdx_metadata_build_requires_and_clean_core_deps _______
tests\test_dependency_pins.py:109: in test_pyproject_spdx_metadata_build_requires_and_clean_core_deps
    assert project["version"] == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
____________ test_wheel_contains_all_live_modules_and_entrypoints _____________
C:\Nexus-Memory\GrafoConcierge\tests\test_wheel_integrity.py:122: in test_wheel_contains_all_live_modules_and_entrypoints
    assert expected_version == "4.1.0"
E   AssertionError: assert '3.8.2' == '4.1.0'
E     
E     - 4.1.0
E     + 3.8.2
---------------------------- Captured stderr call -----------------------------
2026-11-25 22:48:02 │ INFO    │ root                         │ running bdist_wheel
2026-11-25 22:48:02 │ INFO    │ root                         │ running build
2026-11-25 22:48:02 │ INFO    │ root                         │ running build_py
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib
2026-11-25 22:48:02 │ INFO    │ root                         │ copying main.py -> build\lib
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\checkpointer.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\config.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\database.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\graph_rag.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\hybrid_search.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\mcp_governor.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\memory_extractor.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\middleware.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\project_index.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\vector_backend.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ copying core\__init__.py -> build\lib\core
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ copying ingestion\crawler.py -> build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ copying ingestion\orchestrator.py -> build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ copying ingestion\parser.py -> build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ copying ingestion\summarizer.py -> build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ copying ingestion\__init__.py -> build\lib\ingestion
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\interface
2026-11-25 22:48:02 │ INFO    │ root                         │ copying interface\cli.py -> build\lib\interface
2026-11-25 22:48:02 │ INFO    │ root                         │ copying interface\mcp_server.py -> build\lib\interface
2026-11-25 22:48:02 │ INFO    │ root                         │ copying interface\queue_writer.py -> build\lib\interface
2026-11-25 22:48:02 │ INFO    │ root                         │ copying interface\__init__.py -> build\lib\interface
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\scripts
2026-11-25 22:48:02 │ INFO    │ root                         │ copying scripts\bootstrap_core_memory.py -> build\lib\scripts
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\services
2026-11-25 22:48:02 │ INFO    │ root                         │ copying services\janitor.py -> build\lib\services
2026-11-25 22:48:02 │ INFO    │ root                         │ copying services\__init__.py -> build\lib\services
2026-11-25 22:48:02 │ INFO    │ root                         │ creating build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\base_backend.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\connection.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\logic.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\schema.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\semantic_logic.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\store.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\vector_store.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ copying storage\__init__.py -> build\lib\storage
2026-11-25 22:48:02 │ INFO    │ root                         │ running egg_info
2026-11-25 22:48:02 │ INFO    │ root                         │ creating concierge_graph.egg-info
2026-11-25 22:48:02 │ INFO    │ root                         │ writing concierge_graph.egg-info\PKG-INFO
2026-11-25 22:48:02 │ INFO    │ root                         │ writing dependency_links to concierge_graph.egg-info\dependency_links.txt
2026-11-25 22:48:02 │ INFO    │ root                         │ writing entry points to concierge_graph.egg-info\entry_points.txt
2026-11-25 22:48:02 │ INFO    │ root                         │ writing requirements to concierge_graph.egg-info\requires.txt
2026-11-25 22:48:02 │ INFO    │ root                         │ writing top-level names to concierge_graph.egg-info\top_level.txt
2026-11-25 22:48:02 │ INFO    │ root                         │ writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
2026-11-25 22:48:03 │ INFO    │ root                         │ reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
2026-11-25 22:48:03 │ INFO    │ root                         │ adding license file 'LICENSE'
2026-11-25 22:48:03 │ INFO    │ root                         │ writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
2026-11-25 22:48:03 │ INFO    │ root                         │ installing to build\bdist.win-amd64\wheel
2026-11-25 22:48:03 │ INFO    │ root                         │ running install
2026-11-25 22:48:03 │ INFO    │ root                         │ running install_lib
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\checkpointer.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\config.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\database.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\graph_rag.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\hybrid_search.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\mcp_governor.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\memory_extractor.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\middleware.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\project_index.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\vector_backend.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\core\__init__.py -> build\bdist.win-amd64\wheel\.\core
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\ingestion\crawler.py -> build\bdist.win-amd64\wheel\.\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\ingestion\orchestrator.py -> build\bdist.win-amd64\wheel\.\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\ingestion\parser.py -> build\bdist.win-amd64\wheel\.\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\ingestion\summarizer.py -> build\bdist.win-amd64\wheel\.\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\ingestion\__init__.py -> build\bdist.win-amd64\wheel\.\ingestion
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\interface
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\interface\cli.py -> build\bdist.win-amd64\wheel\.\interface
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\interface\mcp_server.py -> build\bdist.win-amd64\wheel\.\interface
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\interface\queue_writer.py -> build\bdist.win-amd64\wheel\.\interface
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\interface\__init__.py -> build\bdist.win-amd64\wheel\.\interface
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\main.py -> build\bdist.win-amd64\wheel\.
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\scripts
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\scripts\bootstrap_core_memory.py -> build\bdist.win-amd64\wheel\.\scripts
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\services
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\services\janitor.py -> build\bdist.win-amd64\wheel\.\services
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\services\__init__.py -> build\bdist.win-amd64\wheel\.\services
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\base_backend.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\connection.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\logic.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\schema.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\semantic_logic.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\store.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\vector_store.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ copying build\lib\storage\__init__.py -> build\bdist.win-amd64\wheel\.\storage
2026-11-25 22:48:03 │ INFO    │ root                         │ running install_egg_info
2026-11-25 22:48:03 │ INFO    │ root                         │ Copying concierge_graph.egg-info to build\bdist.win-amd64\wheel\.\concierge_graph-3.8.2-py3.13.egg-info
2026-11-25 22:48:03 │ INFO    │ root                         │ running install_scripts
2026-11-25 22:48:03 │ INFO    │ root                         │ creating build\bdist.win-amd64\wheel\concierge_graph-3.8.2.dist-info\WHEEL
2026-11-25 22:48:03 │ INFO    │ wheel                        │ creating 'C:\\Users\\guial\\AppData\\Local\\Temp\\pytest-of-guial\\pytest-590\\test_wheel_contains_all_live_m0\\dist\\.tmp-rr16_7fe\\concierge_graph-3.8.2-py3-none-any.whl' and adding 'build\\bdist.win-amd64\\wheel' to it
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'main.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/licenses/LICENSE'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/__init__.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/checkpointer.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/config.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/database.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/graph_rag.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/hybrid_search.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/mcp_governor.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/memory_extractor.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/middleware.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/project_index.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'core/vector_backend.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'ingestion/__init__.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'ingestion/crawler.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'ingestion/orchestrator.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'ingestion/parser.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'ingestion/summarizer.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'interface/__init__.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'interface/cli.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'interface/mcp_server.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'interface/queue_writer.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'scripts/bootstrap_core_memory.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'services/__init__.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'services/janitor.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/__init__.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/base_backend.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/connection.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/logic.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/schema.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/semantic_logic.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/store.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'storage/vector_store.py'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/METADATA'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/WHEEL'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/entry_points.txt'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/top_level.txt'
2026-11-25 22:48:03 │ INFO    │ wheel                        │ adding 'concierge_graph-3.8.2.dist-info/RECORD'
2026-11-25 22:48:03 │ INFO    │ root                         │ removing build\bdist.win-amd64\wheel
------------------------------ Captured log call ------------------------------
INFO     root:dist.py:1044 running bdist_wheel
INFO     root:dist.py:1044 running build
INFO     root:dist.py:1044 running build_py
INFO     root:dir_util.py:58 creating build\lib
INFO     root:file_util.py:128 copying main.py -> build\lib
INFO     root:dir_util.py:58 creating build\lib\core
INFO     root:file_util.py:128 copying core\checkpointer.py -> build\lib\core
INFO     root:file_util.py:128 copying core\config.py -> build\lib\core
INFO     root:file_util.py:128 copying core\database.py -> build\lib\core
INFO     root:file_util.py:128 copying core\graph_rag.py -> build\lib\core
INFO     root:file_util.py:128 copying core\hybrid_search.py -> build\lib\core
INFO     root:file_util.py:128 copying core\mcp_governor.py -> build\lib\core
INFO     root:file_util.py:128 copying core\memory_extractor.py -> build\lib\core
INFO     root:file_util.py:128 copying core\middleware.py -> build\lib\core
INFO     root:file_util.py:128 copying core\project_index.py -> build\lib\core
INFO     root:file_util.py:128 copying core\vector_backend.py -> build\lib\core
INFO     root:file_util.py:128 copying core\__init__.py -> build\lib\core
INFO     root:dir_util.py:58 creating build\lib\ingestion
INFO     root:file_util.py:128 copying ingestion\crawler.py -> build\lib\ingestion
INFO     root:file_util.py:128 copying ingestion\orchestrator.py -> build\lib\ingestion
INFO     root:file_util.py:128 copying ingestion\parser.py -> build\lib\ingestion
INFO     root:file_util.py:128 copying ingestion\summarizer.py -> build\lib\ingestion
INFO     root:file_util.py:128 copying ingestion\__init__.py -> build\lib\ingestion
INFO     root:dir_util.py:58 creating build\lib\interface
INFO     root:file_util.py:128 copying interface\cli.py -> build\lib\interface
INFO     root:file_util.py:128 copying interface\mcp_server.py -> build\lib\interface
INFO     root:file_util.py:128 copying interface\queue_writer.py -> build\lib\interface
INFO     root:file_util.py:128 copying interface\__init__.py -> build\lib\interface
INFO     root:dir_util.py:58 creating build\lib\scripts
INFO     root:file_util.py:128 copying scripts\bootstrap_core_memory.py -> build\lib\scripts
INFO     root:dir_util.py:58 creating build\lib\services
INFO     root:file_util.py:128 copying services\janitor.py -> build\lib\services
INFO     root:file_util.py:128 copying services\__init__.py -> build\lib\services
INFO     root:dir_util.py:58 creating build\lib\storage
INFO     root:file_util.py:128 copying storage\base_backend.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\connection.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\logic.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\schema.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\semantic_logic.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\store.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\vector_store.py -> build\lib\storage
INFO     root:file_util.py:128 copying storage\__init__.py -> build\lib\storage
INFO     root:dist.py:1044 running egg_info
INFO     root:dir_util.py:58 creating concierge_graph.egg-info
INFO     root:egg_info.py:680 writing concierge_graph.egg-info\PKG-INFO
INFO     root:egg_info.py:311 writing dependency_links to concierge_graph.egg-info\dependency_links.txt
INFO     root:egg_info.py:311 writing entry points to concierge_graph.egg-info\entry_points.txt
INFO     root:egg_info.py:311 writing requirements to concierge_graph.egg-info\requires.txt
INFO     root:egg_info.py:311 writing top-level names to concierge_graph.egg-info\top_level.txt
INFO     root:util.py:249 writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
INFO     root:sdist.py:206 reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
INFO     root:egg_info.py:630 adding license file 'LICENSE'
INFO     root:util.py:249 writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
INFO     root:bdist_wheel.py:487 installing to build\bdist.win-amd64\wheel
INFO     root:dist.py:1044 running install
INFO     root:dist.py:1044 running install_lib
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\core
INFO     root:file_util.py:128 copying build\lib\core\checkpointer.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\config.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\database.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\graph_rag.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\hybrid_search.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\mcp_governor.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\memory_extractor.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\middleware.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\project_index.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\vector_backend.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:file_util.py:128 copying build\lib\core\__init__.py -> build\bdist.win-amd64\wheel\.\core
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\ingestion
INFO     root:file_util.py:128 copying build\lib\ingestion\crawler.py -> build\bdist.win-amd64\wheel\.\ingestion
INFO     root:file_util.py:128 copying build\lib\ingestion\orchestrator.py -> build\bdist.win-amd64\wheel\.\ingestion
INFO     root:file_util.py:128 copying build\lib\ingestion\parser.py -> build\bdist.win-amd64\wheel\.\ingestion
INFO     root:file_util.py:128 copying build\lib\ingestion\summarizer.py -> build\bdist.win-amd64\wheel\.\ingestion
INFO     root:file_util.py:128 copying build\lib\ingestion\__init__.py -> build\bdist.win-amd64\wheel\.\ingestion
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\interface
INFO     root:file_util.py:128 copying build\lib\interface\cli.py -> build\bdist.win-amd64\wheel\.\interface
INFO     root:file_util.py:128 copying build\lib\interface\mcp_server.py -> build\bdist.win-amd64\wheel\.\interface
INFO     root:file_util.py:128 copying build\lib\interface\queue_writer.py -> build\bdist.win-amd64\wheel\.\interface
INFO     root:file_util.py:128 copying build\lib\interface\__init__.py -> build\bdist.win-amd64\wheel\.\interface
INFO     root:file_util.py:128 copying build\lib\main.py -> build\bdist.win-amd64\wheel\.
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\scripts
INFO     root:file_util.py:128 copying build\lib\scripts\bootstrap_core_memory.py -> build\bdist.win-amd64\wheel\.\scripts
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\services
INFO     root:file_util.py:128 copying build\lib\services\janitor.py -> build\bdist.win-amd64\wheel\.\services
INFO     root:file_util.py:128 copying build\lib\services\__init__.py -> build\bdist.win-amd64\wheel\.\services
INFO     root:dir_util.py:58 creating build\bdist.win-amd64\wheel\storage
INFO     root:file_util.py:128 copying build\lib\storage\base_backend.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\connection.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\logic.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\schema.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\semantic_logic.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\store.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\vector_store.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:file_util.py:128 copying build\lib\storage\__init__.py -> build\bdist.win-amd64\wheel\.\storage
INFO     root:dist.py:1044 running install_egg_info
INFO     root:util.py:249 Copying concierge_graph.egg-info to build\bdist.win-amd64\wheel\.\concierge_graph-3.8.2-py3.13.egg-info
INFO     root:dist.py:1044 running install_scripts
INFO     root:bdist_wheel.py:558 creating build\bdist.win-amd64\wheel\concierge_graph-3.8.2.dist-info\WHEEL
INFO     wheel:wheelfile.py:158 creating 'C:\\Users\\guial\\AppData\\Local\\Temp\\pytest-of-guial\\pytest-590\\test_wheel_contains_all_live_m0\\dist\\.tmp-rr16_7fe\\concierge_graph-3.8.2-py3-none-any.whl' and adding 'build\\bdist.win-amd64\\wheel' to it
INFO     wheel:wheelfile.py:218 adding 'main.py'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/licenses/LICENSE'
INFO     wheel:wheelfile.py:218 adding 'core/__init__.py'
INFO     wheel:wheelfile.py:218 adding 'core/checkpointer.py'
INFO     wheel:wheelfile.py:218 adding 'core/config.py'
INFO     wheel:wheelfile.py:218 adding 'core/database.py'
INFO     wheel:wheelfile.py:218 adding 'core/graph_rag.py'
INFO     wheel:wheelfile.py:218 adding 'core/hybrid_search.py'
INFO     wheel:wheelfile.py:218 adding 'core/mcp_governor.py'
INFO     wheel:wheelfile.py:218 adding 'core/memory_extractor.py'
INFO     wheel:wheelfile.py:218 adding 'core/middleware.py'
INFO     wheel:wheelfile.py:218 adding 'core/project_index.py'
INFO     wheel:wheelfile.py:218 adding 'core/vector_backend.py'
INFO     wheel:wheelfile.py:218 adding 'ingestion/__init__.py'
INFO     wheel:wheelfile.py:218 adding 'ingestion/crawler.py'
INFO     wheel:wheelfile.py:218 adding 'ingestion/orchestrator.py'
INFO     wheel:wheelfile.py:218 adding 'ingestion/parser.py'
INFO     wheel:wheelfile.py:218 adding 'ingestion/summarizer.py'
INFO     wheel:wheelfile.py:218 adding 'interface/__init__.py'
INFO     wheel:wheelfile.py:218 adding 'interface/cli.py'
INFO     wheel:wheelfile.py:218 adding 'interface/mcp_server.py'
INFO     wheel:wheelfile.py:218 adding 'interface/queue_writer.py'
INFO     wheel:wheelfile.py:218 adding 'scripts/bootstrap_core_memory.py'
INFO     wheel:wheelfile.py:218 adding 'services/__init__.py'
INFO     wheel:wheelfile.py:218 adding 'services/janitor.py'
INFO     wheel:wheelfile.py:218 adding 'storage/__init__.py'
INFO     wheel:wheelfile.py:218 adding 'storage/base_backend.py'
INFO     wheel:wheelfile.py:218 adding 'storage/connection.py'
INFO     wheel:wheelfile.py:218 adding 'storage/logic.py'
INFO     wheel:wheelfile.py:218 adding 'storage/schema.py'
INFO     wheel:wheelfile.py:218 adding 'storage/semantic_logic.py'
INFO     wheel:wheelfile.py:218 adding 'storage/store.py'
INFO     wheel:wheelfile.py:218 adding 'storage/vector_store.py'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/METADATA'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/WHEEL'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/entry_points.txt'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/top_level.txt'
INFO     wheel:wheelfile.py:218 adding 'concierge_graph-3.8.2.dist-info/RECORD'
INFO     root:bdist_wheel.py:535 removing build\bdist.win-amd64\wheel
=========================== short test summary info ===========================
FAILED tests/test_cli_mcp_entrypoint.py::test_cli_version_exits_zero_with_real_package_version
FAILED tests/test_cli_mcp_entrypoint.py::test_get_package_version_fallbacks
FAILED tests/test_cli_mcp_entrypoint.py::test_concierge_cli_version_and_status_use_dynamic_package_version
FAILED tests/test_cli_mcp_entrypoint.py::test_mcp_server_status_uses_dynamic_package_version
FAILED tests/test_dependency_pins.py::test_pyproject_spdx_metadata_build_requires_and_clean_core_deps
FAILED tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints
========================= 6 failed, 6 passed in 4.38s =========================
```

### `c1_mutations.txt` (3/3 KILLED)
```text
M1_mcp_server_hardcoded_v3_8_0: KILLED (rc=1)
M2_cli_status_hardcoded_v3_8_0: KILLED (rc=1)
M3_pyproject_revert_3_8_2: KILLED (rc=1)
Summary: 3/3 KILLED
```

### `c1_green.txt`
```text
$ .venv_313\Scripts\python.exe -m pytest tests/test_cli_mcp_entrypoint.py tests/test_dependency_pins.py tests/test_wheel_integrity.py tests/test_stdin_decouple.py tests/test_lazy_ml_imports.py tests/test_governor_wiring.py tests/test_docker_manifests.py -v --tb=short
[exit=0]
============================= test session starts =============================
platform win32 -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Nexus-Memory\GrafoConcierge
configfile: pyproject.toml
plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0
timeout: 300.0s
timeout method: thread
timeout func_only: False
collecting ... collected 29 items

tests/test_cli_mcp_entrypoint.py::test_cli_help_exits_zero_without_blocking_stdin PASSED [  3%]
tests/test_cli_mcp_entrypoint.py::test_cli_version_exits_zero_with_real_package_version PASSED [  6%]
tests/test_cli_mcp_entrypoint.py::test_parse_args_supports_transport_defaults_and_rejects_invalid PASSED [ 10%]
tests/test_cli_mcp_entrypoint.py::test_get_package_version_fallbacks PASSED [ 13%]
tests/test_cli_mcp_entrypoint.py::test_main_transport_cli_overrides_global_and_preserves_zero_arg_wiring PASSED [ 17%]
tests/test_cli_mcp_entrypoint.py::test_concierge_cli_version_and_status_use_dynamic_package_version PASSED [ 20%]
tests/test_cli_mcp_entrypoint.py::test_mcp_server_status_uses_dynamic_package_version PASSED [ 24%]
tests/test_dependency_pins.py::test_pyproject_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 27%]
tests/test_dependency_pins.py::test_requirements_mcp_version_pin_excludes_2_0_0_and_includes_1_27_0 PASSED [ 31%]
tests/test_dependency_pins.py::test_pyproject_spdx_metadata_build_requires_and_clean_core_deps PASSED [ 34%]
tests/test_dependency_pins.py::test_requirements_txt_is_prod_only_and_requirements_dev_exists PASSED [ 37%]
tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints PASSED [ 41%]
tests/test_stdin_decouple.py::test_d1_subprocess_decouple_windows PASSED [ 44%]
tests/test_stdin_decouple.py::test_d2_disabled_or_non_windows PASSED     [ 48%]
tests/test_stdin_decouple.py::test_d3_os_dup_error_handling PASSED       [ 51%]
tests/test_stdin_decouple.py::test_d4_main_wiring PASSED                 [ 55%]
tests/test_lazy_ml_imports.py::test_t1_storage_imports_do_not_import_sentence_transformers_or_torch PASSED [ 58%]
tests/test_lazy_ml_imports.py::test_t2_bootstrap_does_not_import_sentence_transformers_or_torch PASSED [ 62%]
tests/test_lazy_ml_imports.py::test_t3_missing_sentence_transformers_raises_embedding_error PASSED [ 65%]
tests/test_lazy_ml_imports.py::test_t4_stub_sentence_transformer_used_by_lazy_load PASSED [ 68%]
tests/test_lazy_ml_imports.py::test_t5_availability_flags_exist_and_are_bool PASSED [ 72%]
tests/test_governor_wiring.py::test_t1_mcp_server_import_does_not_drag_agents_or_action_hooks PASSED [ 75%]
tests/test_governor_wiring.py::test_t2_mcp_server_construction_does_not_drag_telemetry_or_fastapi PASSED [ 79%]
tests/test_governor_wiring.py::test_t4_governor_uses_shared_singleton_when_telemetry_import_fails PASSED [ 82%]
tests/test_governor_wiring.py::test_t5_governed_list_tools_filters_by_transport_session_state PASSED [ 86%]
tests/test_docker_manifests.py::test_dockerfile_non_root_sse_and_python_healthcheck PASSED [ 89%]
tests/test_docker_manifests.py::test_docker_compose_removes_version_pins_sse_env_named_volume_and_python_healthcheck PASSED [ 93%]
tests/test_docker_manifests.py::test_dockerignore_excludes_requirements_dev_and_dev_artifacts PASSED [ 96%]
tests/test_docker_manifests.py::test_ci_workflow_has_test_and_docker_smoke_jobs PASSED [100%]

============================= 29 passed in 16.83s =============================

$ .venv_313\Scripts\python.exe -m pytest tests/ -q
[exit=0]
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
.........                                                                [100%]
============================== warnings summary ===============================
tests/test_conversational_db.py::test_qdrant_collection_initialization_real
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-342
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-344
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-361
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
369 passed, 21 warnings in 120.38s (0:02:00)

$ .venv_313\Scripts\python.exe -m pytest tests/ -q --reverse
[exit=0]
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
.........                                                                [100%]
============================== warnings summary ===============================
tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-133
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-147
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-152
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
369 passed, 21 warnings in 124.61s (0:02:04)

$ .venv_313\Scripts\flake8 main.py core storage ingestion services interface scripts tests --count --select=E9,F63,F7,F82 --show-source --statistics
[exit=0]
0
```

### `c1_stat.txt` & `ci_C1.txt` (7/7 GREEN)
```text
$ git show --stat HEAD
[exit=0]
commit 54d50740028211d0244532d6618f1bd53298c1e6
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Wed Nov 25 22:57:51 2026 -0300

    chore(release): bump package to 4.1.0, use dynamic version in CLI/MCP and CI docker-smoke (4.9-C1)

 .github/workflows/ci.yml         |  9 +++--
 interface/cli.py                 | 44 +++++++++++++++++++++--
 interface/mcp_server.py          | 38 +++++++++++++++++++-
 pyproject.toml                   |  2 +-
 tests/test_cli_mcp_entrypoint.py | 78 ++++++++++++++++++++++++++++++++++++++--
 tests/test_dependency_pins.py    |  4 +--
 tests/test_wheel_integrity.py    | 13 ++++++-
 7 files changed, 175 insertions(+), 13 deletions(-)

$ git rev-parse HEAD
[exit=0]
54d50740028211d0244532d6618f1bd53298c1e6

---

$ .venv_313\Scripts\python.exe scratch/check_ci_4_8.py C1 54d50740028211d0244532d6618f1bd53298c1e6 7
[exit=0]
Stage C1 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45739234994 sha=54d50740028211d0244532d6618f1bd53298c1e6 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45739234994
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
Stage C1 CI Run (CI): id=45739234929 sha=54d50740028211d0244532d6618f1bd53298c1e6 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45739234929
  - Test (Python 3.10): status=completed conclusion=success
  - Docker Smoke: status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
Total jobs=7 (expected>=7), all_done=True, any_failed=False
```

---

## 4. Etapa C2 — Build `sdist` + `wheel`, Smoke Install Limpo e Verificações Finais

### `c2_dist_smoke.txt`
```text
Building sdist + wheel in C:\Users\guial\AppData\Local\Temp\grafo_49_vdjatgkc\dist ...
[build rc=0]
running egg_info
writing concierge_graph.egg-info\PKG-INFO
writing dependency_links to concierge_graph.egg-info\dependency_links.txt
writing entry points to concierge_graph.egg-info\entry_points.txt
writing requirements to concierge_graph.egg-info\requires.txt
writing top-level names to concierge_graph.egg-info\top_level.txt
reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
running sdist
running egg_info
writing concierge_graph.egg-info\PKG-INFO
writing dependency_links to concierge_graph.egg-info\dependency_links.txt
writing entry points to concierge_graph.egg-info\entry_points.txt
writing requirements to concierge_graph.egg-info\requires.txt
writing top-level names to concierge_graph.egg-info\top_level.txt
reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
running check
creating concierge_graph-4.1.0
creating concierge_graph-4.1.0\concierge_graph.egg-info
creating concierge_graph-4.1.0\core
creating concierge_graph-4.1.0\ingestion
creating concierge_graph-4.1.0\interface
creating concierge_graph-4.1.0\scripts
creating concierge_graph-4.1.0\services
creating concierge_graph-4.1.0\storage
creating concierge_graph-4.1.0\tests
copying files to concierge_graph-4.1.0...
copying LICENSE -> concierge_graph-4.1.0
copying README.md -> concierge_graph-4.1.0
copying main.py -> concierge_graph-4.1.0
copying pyproject.toml -> concierge_graph-4.1.0
copying concierge_graph.egg-info\PKG-INFO -> concierge_graph-4.1.0\concierge_graph.egg-info
copying concierge_graph.egg-info\SOURCES.txt -> concierge_graph-4.1.0\concierge_graph.egg-info
copying concierge_graph.egg-info\dependency_links.txt -> concierge_graph-4.1.0\concierge_graph.egg-info
copying concierge_graph.egg-info\entry_points.txt -> concierge_graph-4.1.0\concierge_graph.egg-info
copying concierge_graph.egg-info\requires.txt -> concierge_graph-4.1.0\concierge_graph.egg-info
copying concierge_graph.egg-info\top_level.txt -> concierge_graph-4.1.0\concierge_graph.egg-info
copying core\__init__.py -> concierge_graph-4.1.0\core
copying core\checkpointer.py -> concierge_graph-4.1.0\core
copying core\config.py -> concierge_graph-4.1.0\core
copying core\database.py -> concierge_graph-4.1.0\core
copying core\graph_rag.py -> concierge_graph-4.1.0\core
copying core\hybrid_search.py -> concierge_graph-4.1.0\core
copying core\mcp_governor.py -> concierge_graph-4.1.0\core
copying core\memory_extractor.py -> concierge_graph-4.1.0\core
copying core\middleware.py -> concierge_graph-4.1.0\core
copying core\project_index.py -> concierge_graph-4.1.0\core
copying core\vector_backend.py -> concierge_graph-4.1.0\core
copying ingestion\__init__.py -> concierge_graph-4.1.0\ingestion
copying ingestion\crawler.py -> concierge_graph-4.1.0\ingestion
copying ingestion\orchestrator.py -> concierge_graph-4.1.0\ingestion
copying ingestion\parser.py -> concierge_graph-4.1.0\ingestion
copying ingestion\summarizer.py -> concierge_graph-4.1.0\ingestion
copying interface\__init__.py -> concierge_graph-4.1.0\interface
copying interface\cli.py -> concierge_graph-4.1.0\interface
copying interface\mcp_server.py -> concierge_graph-4.1.0\interface
copying interface\queue_writer.py -> concierge_graph-4.1.0\interface
copying scripts\bootstrap_core_memory.py -> concierge_graph-4.1.0\scripts
copying services\__init__.py -> concierge_graph-4.1.0\services
copying services\janitor.py -> concierge_graph-4.1.0\services
copying storage\__init__.py -> concierge_graph-4.1.0\storage
copying storage\base_backend.py -> concierge_graph-4.1.0\storage
copying storage\connection.py -> concierge_graph-4.1.0\storage
copying storage\logic.py -> concierge_graph-4.1.0\storage
copying storage\schema.py -> concierge_graph-4.1.0\storage
copying storage\semantic_logic.py -> concierge_graph-4.1.0\storage
copying storage\store.py -> concierge_graph-4.1.0\storage
copying storage\vector_store.py -> concierge_graph-4.1.0\storage
copying tests\test_agent_checkpointer.py -> concierge_graph-4.1.0\tests
copying tests\test_agent_checkpoints_schema.py -> concierge_graph-4.1.0\tests
copying tests\test_call_chain_edges_nodes.py -> concierge_graph-4.1.0\tests
copying tests\test_checkpoint_ownership.py -> concierge_graph-4.1.0\tests
copying tests\test_checkpointer_arg_resolution.py -> concierge_graph-4.1.0\tests
copying tests\test_checkpointer_live_contract.py -> concierge_graph-4.1.0\tests
copying tests\test_checkpointer_sdd20_removed.py -> concierge_graph-4.1.0\tests
copying tests\test_chunk_cache.py -> concierge_graph-4.1.0\tests
copying tests\test_clean_database_schema.py -> concierge_graph-4.1.0\tests
copying tests\test_cli_mcp_entrypoint.py -> concierge_graph-4.1.0\tests
copying tests\test_concurrency_stress.py -> concierge_graph-4.1.0\tests
copying tests\test_config.py -> concierge_graph-4.1.0\tests
copying tests\test_connection_queue_resilience.py -> concierge_graph-4.1.0\tests
copying tests\test_conversational_db.py -> concierge_graph-4.1.0\tests
copying tests\test_dependency_pins.py -> concierge_graph-4.1.0\tests
copying tests\test_docker_manifests.py -> concierge_graph-4.1.0\tests
copying tests\test_domain_neutrality_guard.py -> concierge_graph-4.1.0\tests
copying tests\test_env_example_provider.py -> concierge_graph-4.1.0\tests
copying tests\test_extraction_noop.py -> concierge_graph-4.1.0\tests
copying tests\test_fts_atomic_migration.py -> concierge_graph-4.1.0\tests
copying tests\test_fts_code_search.py -> concierge_graph-4.1.0\tests
copying tests\test_governor_wiring.py -> concierge_graph-4.1.0\tests
copying tests\test_graph_rag_loops.py -> concierge_graph-4.1.0\tests
copying tests\test_hybrid_search_escolha_a.py -> concierge_graph-4.1.0\tests
copying tests\test_ignore.py -> concierge_graph-4.1.0\tests
copying tests\test_ingestion_embed_regression.py -> concierge_graph-4.1.0\tests
copying tests\test_ingestion_vector_repair.py -> concierge_graph-4.1.0\tests
copying tests\test_interface_contracts.py -> concierge_graph-4.1.0\tests
copying tests\test_lazy_ml_imports.py -> concierge_graph-4.1.0\tests
copying tests\test_lightweight.py -> concierge_graph-4.1.0\tests
copying tests\test_llm_egress_guard.py -> concierge_graph-4.1.0\tests
copying tests\test_mcp_governor.py -> concierge_graph-4.1.0\tests
copying tests\test_mcp_security_governance.py -> concierge_graph-4.1.0\tests
copying tests\test_mcp_server_extensions.py -> concierge_graph-4.1.0\tests
copying tests\test_mcp_server_handlers.py -> concierge_graph-4.1.0\tests
copying tests\test_no_secrets_in_tracked_files.py -> concierge_graph-4.1.0\tests
copying tests\test_project_index.py -> concierge_graph-4.1.0\tests
copying tests\test_queue_writer_batching.py -> concierge_graph-4.1.0\tests
copying tests\test_queue_writer_resilience.py -> concierge_graph-4.1.0\tests
copying tests\test_secret_redaction.py -> concierge_graph-4.1.0\tests
copying tests\test_semantic_facts_utility.py -> concierge_graph-4.1.0\tests
copying tests\test_sse_auth_hardening.py -> concierge_graph-4.1.0\tests
copying tests\test_stdin_decouple.py -> concierge_graph-4.1.0\tests
copying tests\test_storage_logic.py -> concierge_graph-4.1.0\tests
copying tests\test_stress_components_reuse.py -> concierge_graph-4.1.0\tests
copying tests\test_summary_persistence.py -> concierge_graph-4.1.0\tests
copying tests\test_topology.py -> concierge_graph-4.1.0\tests
copying tests\test_wheel_integrity.py -> concierge_graph-4.1.0\tests
Writing concierge_graph-4.1.0\setup.cfg
Creating tar archive
removing 'concierge_graph-4.1.0' (and everything under it)
running egg_info
writing concierge_graph.egg-info\PKG-INFO
writing dependency_links to concierge_graph.egg-info\dependency_links.txt
writing entry points to concierge_graph.egg-info\entry_points.txt
writing requirements to concierge_graph.egg-info\requires.txt
writing top-level names to concierge_graph.egg-info\top_level.txt
reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
running bdist_wheel
running build
running build_py
creating build\lib
copying main.py -> build\lib
creating build\lib\core
copying core\checkpointer.py -> build\lib\core
copying core\config.py -> build\lib\core
copying core\database.py -> build\lib\core
copying core\graph_rag.py -> build\lib\core
copying core\hybrid_search.py -> build\lib\core
copying core\mcp_governor.py -> build\lib\core
copying core\memory_extractor.py -> build\lib\core
copying core\middleware.py -> build\lib\core
copying core\project_index.py -> build\lib\core
copying core\vector_backend.py -> build\lib\core
copying core\__init__.py -> build\lib\core
creating build\lib\ingestion
copying ingestion\crawler.py -> build\lib\ingestion
copying ingestion\orchestrator.py -> build\lib\ingestion
copying ingestion\parser.py -> build\lib\ingestion
copying ingestion\summarizer.py -> build\lib\ingestion
copying ingestion\__init__.py -> build\lib\ingestion
creating build\lib\interface
copying interface\cli.py -> build\lib\interface
copying interface\mcp_server.py -> build\lib\interface
copying interface\queue_writer.py -> build\lib\interface
copying interface\__init__.py -> build\lib\interface
creating build\lib\scripts
copying scripts\bootstrap_core_memory.py -> build\lib\scripts
creating build\lib\services
copying services\janitor.py -> build\lib\services
copying services\__init__.py -> build\lib\services
creating build\lib\storage
copying storage\base_backend.py -> build\lib\storage
copying storage\connection.py -> build\lib\storage
copying storage\logic.py -> build\lib\storage
copying storage\schema.py -> build\lib\storage
copying storage\semantic_logic.py -> build\lib\storage
copying storage\store.py -> build\lib\storage
copying storage\vector_store.py -> build\lib\storage
copying storage\__init__.py -> build\lib\storage
running egg_info
writing concierge_graph.egg-info\PKG-INFO
writing dependency_links to concierge_graph.egg-info\dependency_links.txt
writing entry points to concierge_graph.egg-info\entry_points.txt
writing requirements to concierge_graph.egg-info\requires.txt
writing top-level names to concierge_graph.egg-info\top_level.txt
reading manifest file 'concierge_graph.egg-info\SOURCES.txt'
adding license file 'LICENSE'
writing manifest file 'concierge_graph.egg-info\SOURCES.txt'
installing to build\bdist.win-amd64\wheel
running install
running install_lib
creating build\bdist.win-amd64\wheel
creating build\bdist.win-amd64\wheel\core
copying build\lib\core\checkpointer.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\config.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\database.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\graph_rag.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\hybrid_search.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\mcp_governor.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\memory_extractor.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\middleware.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\project_index.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\vector_backend.py -> build\bdist.win-amd64\wheel\.\core
copying build\lib\core\__init__.py -> build\bdist.win-amd64\wheel\.\core
creating build\bdist.win-amd64\wheel\ingestion
copying build\lib\ingestion\crawler.py -> build\bdist.win-amd64\wheel\.\ingestion
copying build\lib\ingestion\orchestrator.py -> build\bdist.win-amd64\wheel\.\ingestion
copying build\lib\ingestion\parser.py -> build\bdist.win-amd64\wheel\.\ingestion
copying build\lib\ingestion\summarizer.py -> build\bdist.win-amd64\wheel\.\ingestion
copying build\lib\ingestion\__init__.py -> build\bdist.win-amd64\wheel\.\ingestion
creating build\bdist.win-amd64\wheel\interface
copying build\lib\interface\cli.py -> build\bdist.win-amd64\wheel\.\interface
copying build\lib\interface\mcp_server.py -> build\bdist.win-amd64\wheel\.\interface
copying build\lib\interface\queue_writer.py -> build\bdist.win-amd64\wheel\.\interface
copying build\lib\interface\__init__.py -> build\bdist.win-amd64\wheel\.\interface
copying build\lib\main.py -> build\bdist.win-amd64\wheel\.
creating build\bdist.win-amd64\wheel\scripts
copying build\lib\scripts\bootstrap_core_memory.py -> build\bdist.win-amd64\wheel\.\scripts
creating build\bdist.win-amd64\wheel\services
copying build\lib\services\janitor.py -> build\bdist.win-amd64\wheel\.\services
copying build\lib\services\__init__.py -> build\bdist.win-amd64\wheel\.\services
creating build\bdist.win-amd64\wheel\storage
copying build\lib\storage\base_backend.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\connection.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\logic.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\schema.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\semantic_logic.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\store.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\vector_store.py -> build\bdist.win-amd64\wheel\.\storage
copying build\lib\storage\__init__.py -> build\bdist.win-amd64\wheel\.\storage
running install_egg_info
Copying concierge_graph.egg-info to build\bdist.win-amd64\wheel\.\concierge_graph-4.1.0-py3.13.egg-info
running install_scripts
creating build\bdist.win-amd64\wheel\concierge_graph-4.1.0.dist-info\WHEEL
creating 'C:\\Users\\guial\\AppData\\Local\\Temp\\grafo_49_vdjatgkc\\dist\\.tmp-eda2jrxu\\concierge_graph-4.1.0-py3-none-any.whl' and adding 'build\\bdist.win-amd64\\wheel' to it
adding 'main.py'
adding 'concierge_graph-4.1.0.dist-info/licenses/LICENSE'
adding 'core/__init__.py'
adding 'core/checkpointer.py'
adding 'core/config.py'
adding 'core/database.py'
adding 'core/graph_rag.py'
adding 'core/hybrid_search.py'
adding 'core/mcp_governor.py'
adding 'core/memory_extractor.py'
adding 'core/middleware.py'
adding 'core/project_index.py'
adding 'core/vector_backend.py'
adding 'ingestion/__init__.py'
adding 'ingestion/crawler.py'
adding 'ingestion/orchestrator.py'
adding 'ingestion/parser.py'
adding 'ingestion/summarizer.py'
adding 'interface/__init__.py'
adding 'interface/cli.py'
adding 'interface/mcp_server.py'
adding 'interface/queue_writer.py'
adding 'scripts/bootstrap_core_memory.py'
adding 'services/__init__.py'
adding 'services/janitor.py'
adding 'storage/__init__.py'
adding 'storage/base_backend.py'
adding 'storage/connection.py'
adding 'storage/logic.py'
adding 'storage/schema.py'
adding 'storage/semantic_logic.py'
adding 'storage/store.py'
adding 'storage/vector_store.py'
adding 'concierge_graph-4.1.0.dist-info/METADATA'
adding 'concierge_graph-4.1.0.dist-info/WHEEL'
adding 'concierge_graph-4.1.0.dist-info/entry_points.txt'
adding 'concierge_graph-4.1.0.dist-info/top_level.txt'
adding 'concierge_graph-4.1.0.dist-info/RECORD'
removing build\bdist.win-amd64\wheel
Successfully built concierge_graph-4.1.0.tar.gz and concierge_graph-4.1.0-py3-none-any.whl
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - setuptools>=77.0.0
  - wheel
* Getting build dependencies for sdist...
* Installed build dependency versions:
  - setuptools==84.2.1
  - wheel==0.48.0
* Building sdist...
* Building wheel from sdist
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment:
  - setuptools>=77.0.0
  - wheel
* Getting build dependencies for wheel...
* Installed build dependency versions:
  - setuptools==84.2.1
  - wheel==0.48.0
* Building wheel...
Artifacts: wheel=concierge_graph-4.1.0-py3-none-any.whl (155079 bytes), sdist=concierge_graph-4.1.0.tar.gz (261062 bytes)
Wheel check PASS: 38 entries, 0 leaks, METADATA Version=4.1.0, License-Expression=MIT
Sdist check PASS: 100 members, 0 leaks (.env/data/.venv/scratch/archive/audits/secrets)
Creating clean venv at C:\Users\guial\AppData\Local\Temp\grafo_49_vdjatgkc\venv ...
[pip install wheel rc=0]
CLI 'concierge --version' PASS (rc=0): grafo-concierge 4.1.0
CLI 'concierge-mcp --version' PASS (rc=0): concierge-mcp 4.1.0
CLI 'concierge --help' PASS (rc=0): usage: grafo-concierge [-h] [--version]
CLI 'concierge-mcp --help' PASS (rc=0): usage: concierge-mcp [-h] [--transport {stdio,sse}] [--version]
Server smoke PASS: {"tools_count": 31, "system": "Grafo Concierge v4.1.0", "success": true}
Clean repo root check PASS: no dist/, build/, or concierge_graph.egg-info/ left behind.
```

### `c2_utf8_check.txt`
```text
audits/relatorio_4_8.md: size_bytes=125364 first_16_hex=23 20 52 65 6c 61 74 c3 b3 72 69 6f 20 64 65 20 nul_count=0 utf8_ok=True
audits/relatorio_4_9.md: size_bytes=95614 first_16_hex=23 20 52 65 6c 61 74 c3 b3 72 69 6f 20 64 65 20 nul_count=0 utf8_ok=True
```

### `c2_suite.txt`
```text
$ .venv_313\Scripts\python.exe -m pytest tests/ -q
[exit=0]
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
.........                                                                [100%]
============================== warnings summary ===============================
tests/test_conversational_db.py::test_qdrant_collection_initialization_real
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-342
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-344
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-361
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
369 passed, 21 warnings in 121.62s (0:02:01)

$ .venv_313\Scripts\python.exe -m pytest tests/ -q --reverse
[exit=0]
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
.........                                                                [100%]
============================== warnings summary ===============================
tests/test_storage_logic.py: 14 warnings
  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-133
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 142, in run
      self._execute_batch(conn, batch)
      ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  MemoryError: Simulated catastrophic crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t11_multiple_queued_items_fail_fast_when_loop_dies
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-147
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Simulated loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-152
  
  Traceback (most recent call last):
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\threading.py", line 1044, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Nexus-Memory\GrafoConcierge\interface\queue_writer.py", line 139, in run
      self._execute_single(conn, batch[0])
      ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1169, in __call__
      return self._mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1173, in _mock_call
      return self._execute_mock_call(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "C:\Users\guial\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\Lib\unittest\mock.py", line 1234, in _execute_mock_call
      raise effect
  SystemError: Fatal worker loop crash
  
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields
tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project
  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
369 passed, 21 warnings in 120.29s (0:02:00)

$ .venv_313\Scripts\flake8 main.py core storage ingestion services interface scripts tests --count --select=E9,F63,F7,F82 --show-source --statistics
[exit=0]
0
```

### Segredos (`scan_secrets.py` C1 & C2)
```text
[C1] $ .venv_313\Scripts\python.exe scratch/tools/scan_secrets.py
[exit=0]
scanned_files=1626
files_with_findings=0
total_pattern_hits=0
[C2] $ .venv_313\Scripts\python.exe scratch/tools/scan_secrets.py
[exit=0]
scanned_files=1632
files_with_findings=0
total_pattern_hits=0
```

### `git status --short` pré-commit C2
```text
M .env.example
 M CHANGELOG.md
 M README.md
 M README.pt-BR.md
 M audits/fase4-decisoes.md
 M audits/relatorio_4_8.md
 M scratch/build_4_5a_bis_docs.py
 M scratch/inv_4_5a_bis_bloco1.py
?? audits/egm/analise-completa-codebase-details.md
?? audits/egm/analise-completa-comprehension.md
?? audits/egm/analise-completa-design.md
?? audits/egm/analise-completa-inventive-catalyst.md
?? audits/egm/analise-completa-sintese.md
?? audits/egm/analise-completa-zoom-out.md
?? audits/relatorio_4_9.md
?? grafo-dashboard-web/
?? scratch/build_relatorio_4_5g.py
?? scratch/build_relatorio_4_6.py
?? scratch/build_relatorio_4_7.py
?? scratch/build_relatorio_4_8.py
?? scratch/build_relatorio_4_9.py
?? scratch/c2_deps_audit.py
?? scratch/c2_dockerignore_check.py
?? scratch/c2_smoke.py
?? scratch/c3_doc_scan.py
?? scratch/caracterizacao_sdd20_4_5e.py
?? scratch/chamadores_4_5e.py
?? scratch/chamadores_4_5e_bis.py
?? scratch/check_ci_4_5d.py
?? scratch/check_ci_4_5e.py
?? scratch/check_ci_4_5e_bis.py
?? scratch/check_ci_4_5g.py
?? scratch/check_ci_4_6.py
?? scratch/check_ci_4_7.py
?? scratch/check_ci_4_8.py
?? scratch/check_utf8_4_9.py
?? scratch/coverage_mistos_4_5d.py
?? scratch/dist_smoke_4_9.py
?? scratch/evidencia_4_5d/
?? scratch/evidencia_4_5e/
?? scratch/evidencia_4_5e_bis/
?? scratch/evidencia_4_5g/
?? scratch/evidencia_4_6/
?? scratch/evidencia_4_7/
?? scratch/evidencia_4_8/
?? scratch/evidencia_4_9/
?? scratch/fix_relatorio_4_8_utf8.py
?? scratch/gate_4_5e.py
?? scratch/gate_4_5e_bis.py
?? scratch/gate_lote_4_5d.py
?? scratch/grafo_importadores_4_5d.py
?? scratch/move_lote_4_5d.py
?? scratch/mutacao_escolha_a_4_5d.py
?? scratch/mutacoes_c1_4_5e.py
?? scratch/mutacoes_c1_4_5e_bis.py
?? scratch/mutacoes_c1_4_5g.py
?? scratch/mutacoes_c1_4_6.py
?? scratch/mutacoes_c1_4_7.py
?? scratch/mutacoes_c1_4_8.py
?? scratch/mutacoes_c1_4_9.py
?? scratch/mutacoes_c2_4_5e.py
?? scratch/mutacoes_c2_4_5e_bis.py
?? scratch/mutacoes_c2_4_6.py
?? scratch/mutacoes_c2_4_7.py
?? scratch/mutacoes_c2_4_8.py
?? scratch/mutacoes_c3_4_5e.py
?? scratch/mutacoes_c3_4_5e_bis.py
?? scratch/mutacoes_c3_4_6.py
?? scratch/preflight_4_5d.py
?? scratch/preflight_4_5e.py
?? scratch/preflight_4_5e_bis.py
?? scratch/preflight_4_5g.py
?? scratch/prompt_4_5b_verbatim.md
?? scratch/repro_4_5e_bis.py
?? scratch/run_ev_4_9.py
?? scratch/save_swarm_4_5e.py
?? scratch/save_swarm_4_5g.py
?? scratch/save_swarm_4_6.py
?? scratch/trace_funcs_45e.py
?? scratch/trace_funcs_45e_bis.py
?? scratch/verificacoes_finais_4_5d.py
```
