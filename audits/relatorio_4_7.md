# Relatório de Execução — Rodada 4.7 (Hardening HTTP/SSE, Read-TOCTOU no Checkpointer e Higiene de DDL)

- **Base normativa:** `AUDIT_PROTOCOL.md` (Regras 2, 3, 4, 7, 10, 11, 12, 13 e 14), `audits/fase4-decisoes.md` (Seção 8) e Propostas #1, #2 e #4 de `audits/egm/4.6-sintese.md`.
- **HEAD de partida:** `873e8146611acdd36483fbf7dcff65261d94794c` (`873e814`).
- **Nota:** Sem fase Swarm C0 nesta rodada (Regra 15(f)).

## Commits Executados (extraídos mecanicamente via `git log --format="%H %s"`)

| Commit SHA | Mensagem |
| :--- | :--- |
| `b3b14e2879e6baef6beb74828e6461f340553e7a` | fix(security): close read-TOCTOU in checkpointer queries and remove manual DDL in legacy test (4.7-C2) |
| `2dd3be7b20b4efd738713e4939fcac4b20bb328c` | fix(security): harden SSE auth middleware, decouple checkpoint token from Bearer and redact Qdrant key (4.7-C1) |
| `(C3 — commit atual)` | `docs(security): align docs with hardened SSE auth, token separation and 4.7 report (4.7-C3)` |

## 1. Passo 0 — Pré-voo

```text
=== P0 GIT REV ===
873e8146611acdd36483fbf7dcff65261d94794c

873e8146611acdd36483fbf7dcff65261d94794c


=== P0 PYTEST NORMAL ===
........................................................................ [ 20%]

........................................................................ [ 41%]

........................................................................ [ 62%]

........................................................................ [ 82%]

...........................................................              [100%]

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-323

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-325

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-342

  

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



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

347 passed, 24 warnings in 117.32s (0:01:57)


=== P0 PYTEST REVERSE ===
........................................................................ [ 20%]

........................................................................ [ 41%]

........................................................................ [ 62%]

........................................................................ [ 82%]

...........................................................              [100%]

============================== warnings summary ===============================

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-102

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-116

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-121

  

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



tests/test_conversational_db.py::test_semantic_facts_bi_temporal

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.

    show_warning(



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

347 passed, 24 warnings in 116.27s (0:01:56)


=== P0 FLAKE8 ===
0
```

## 2. Etapa C1 — Hardening HTTP/SSE (`auth_middleware`, Separação de Tokens e Redação Qdrant)

### `git show --stat` (C1)
```text
commit 2dd3be7b20b4efd738713e4939fcac4b20bb328c
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Wed Nov 25 17:07:20 2026 -0300

    fix(security): harden SSE auth middleware, decouple checkpoint token from Bearer and redact Qdrant key (4.7-C1)

 interface/mcp_server.py            |  36 ++++++------
 main.py                            |   2 +-
 tests/test_checkpoint_ownership.py |  57 +++++++++++++------
 tests/test_secret_redaction.py     |  17 ++++++
 tests/test_sse_auth_hardening.py   | 111 +++++++++++++++++++++++++++++++++++++
 5 files changed, 185 insertions(+), 38 deletions(-)
```

### Evidência RED (C1)
```text
FFF....F......................F                                          [100%]
================================== FAILURES ===================================
_________________ test_sse_rejects_query_param_token_with_401 _________________

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-550/test_sse_rejects_query_param_t0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000002237712FA80>

    def test_sse_rejects_query_param_token_with_401(tmp_path, monkeypatch):
        """Query string ?token=<key> não é aceita em nenhuma rota (GET /sse ou POST /messages/)."""
        api_key = "test-sse-api-key-query-reject-alpha"
>       client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_sse_auth_hardening.py:38: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_sse_auth_hardening.py:31: in _make_sse_client
    app = server.mcp.sse_app()
          ^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

args = (), kwargs = {}

    def custom_sse_app(*args, **kwargs):
        app = original_sse_app(*args, **kwargs)
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import JSONResponse
    
        cfg = getattr(self._gc, "config", None)
        api_key = (getattr(cfg, "api_key", None) if cfg else None) or os.environ.get("GRAFO_API_KEY")
        cors_origins_env = os.environ.get("GRAFO_CORS_ORIGINS")
        if cors_origins_env:
            origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        elif cfg and hasattr(cfg, "cors_origins"):
            origins = list(cfg.cors_origins)
        else:
            origins = ["*"]
    
        # 1. API Key Authentication Middleware (if configured)
        if api_key:
>           @app.middleware("http")
             ^^^^^^^^^^^^^^
E           AttributeError: 'Starlette' object has no attribute 'middleware'. Did you mean: 'add_middleware'?

interface\mcp_server.py:199: AttributeError
___________ test_sse_rejects_missing_wrong_empty_or_non_bearer_auth ___________

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-550/test_sse_rejects_missing_wrong0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000022376F9E060>

    def test_sse_rejects_missing_wrong_empty_or_non_bearer_auth(tmp_path, monkeypatch):
        """Credenciais ausentes, vazias, inválidas ou não-Bearer retornam HTTP 401."""
        api_key = "test-sse-api-key-creds-alpha"
>       client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_sse_auth_hardening.py:52: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_sse_auth_hardening.py:31: in _make_sse_client
    app = server.mcp.sse_app()
          ^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

args = (), kwargs = {}

    def custom_sse_app(*args, **kwargs):
        app = original_sse_app(*args, **kwargs)
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import JSONResponse
    
        cfg = getattr(self._gc, "config", None)
        api_key = (getattr(cfg, "api_key", None) if cfg else None) or os.environ.get("GRAFO_API_KEY")
        cors_origins_env = os.environ.get("GRAFO_CORS_ORIGINS")
        if cors_origins_env:
            origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        elif cfg and hasattr(cfg, "cors_origins"):
            origins = list(cfg.cors_origins)
        else:
            origins = ["*"]
    
        # 1. API Key Authentication Middleware (if configured)
        if api_key:
>           @app.middleware("http")
             ^^^^^^^^^^^^^^
E           AttributeError: 'Starlette' object has no attribute 'middleware'. Did you mean: 'add_middleware'?

interface\mcp_server.py:199: AttributeError
__ test_sse_accepts_bearer_and_case_insensitive_scheme_using_compare_digest ___

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-550/test_sse_accepts_bearer_and_ca0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000002237726E0F0>

    def test_sse_accepts_bearer_and_case_insensitive_scheme_using_compare_digest(tmp_path, monkeypatch):
        """Aceita Bearer / bearer case-insensitive e compara com hmac.compare_digest."""
        api_key = "test-sse-api-key-bearer-alpha"
>       client, store = _make_sse_client(tmp_path, monkeypatch, api_key)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_sse_auth_hardening.py:72: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\test_sse_auth_hardening.py:31: in _make_sse_client
    app = server.mcp.sse_app()
          ^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

args = (), kwargs = {}

    def custom_sse_app(*args, **kwargs):
        app = original_sse_app(*args, **kwargs)
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import JSONResponse
    
        cfg = getattr(self._gc, "config", None)
        api_key = (getattr(cfg, "api_key", None) if cfg else None) or os.environ.get("GRAFO_API_KEY")
        cors_origins_env = os.environ.get("GRAFO_CORS_ORIGINS")
        if cors_origins_env:
            origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        elif cfg and hasattr(cfg, "cors_origins"):
            origins = list(cfg.cors_origins)
        else:
            origins = ["*"]
    
        # 1. API Key Authentication Middleware (if configured)
        if api_key:
>           @app.middleware("http")
             ^^^^^^^^^^^^^^
E           AttributeError: 'Starlette' object has no attribute 'middleware'. Did you mean: 'add_middleware'?

interface\mcp_server.py:199: AttributeError
_______ test_mcp_http_sse_decoupled_agent_token_and_ephemeral_isolation _______

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-550/test_mcp_http_sse_decoupled_ag0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000223771AF550>

    def test_mcp_http_sse_decoupled_agent_token_and_ephemeral_isolation(tmp_path, monkeypatch):
        """HTTP/SSE lê exclusivamente X-Grafo-Agent-Token (sem fallback para Bearer) ou isola via segredo efêmero."""
        db_path = tmp_path / "bl012_mcp_sse.db"
        monkeypatch.delenv("GRAFO_AGENT_TOKEN", raising=False)
    
        server, store = _make_server(db_path, monkeypatch, default_state="EXECUTION")
        try:
            sess1 = DummyTransportSession("sse-1")
            sess2 = DummyTransportSession("sse-2")
    
            # 1. X-Grafo-Agent-Token identifica o dono independentemente de Authorization: Bearer
            _call_with_req_ctx(
                server,
                sess1,
                SimpleNamespace(
                    headers={
                        "X-Grafo-Agent-Token": "test-sse-header-owner",
                        "Authorization": "Bearer test-sse-bearer-client-a",
                    }
                ),
                "agent_save_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1", "state_dict": {"sse": 1}},
            )
    
            # Reconexão em outra sessão com mesmo X-Grafo-Agent-Token (e outro Bearer) recupera normalmente
            assert _call_with_req_ctx(
                server,
                sess2,
                SimpleNamespace(
                    headers={
                        "X-Grafo-Agent-Token": "test-sse-header-owner",
                        "Authorization": "Bearer test-sse-bearer-client-b",
                    }
                ),
                "agent_get_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1"},
            ) == {"sse": 1}
    
            # Mesmo com Bearer igual, outro X-Grafo-Agent-Token não acessa
            with pytest.raises((PermissionError, ToolError)) as exc_info:
                _call_with_req_ctx(
                    server,
                    sess2,
                    SimpleNamespace(
                        headers={
                            "X-Grafo-Agent-Token": "test-sse-header-attacker",
                            "Authorization": "Bearer test-sse-bearer-client-a",
                        }
                    ),
                    "agent_get_checkpoint",
                    {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1"},
                )
            if isinstance(exc_info.value, ToolError):
                assert isinstance(exc_info.value.__cause__, PermissionError)
    
            # 2. Decisão 2A (4.7): mesmo Authorization: Bearer SEM X-Grafo-Agent-Token NÃO compartilha posse
            shared_bearer = "Bearer test-shared-sse-api-key-alpha"
            _call_with_req_ctx(
                server,
                sess1,
                SimpleNamespace(headers={"Authorization": shared_bearer}),
                "agent_save_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1", "state_dict": {"b": 2}},
            )
            assert _call_with_req_ctx(
                server,
                sess1,
                SimpleNamespace(headers={"Authorization": shared_bearer}),
                "agent_get_checkpoint",
                {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1"},
            ) == {"b": 2}
    
            for tool_name, tool_args in (
                ("agent_get_checkpoint", {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1"}),
                ("agent_list_checkpoints", {"agent_id": "sse_ag", "session_id": "sse_s_bearer"}),
                ("agent_save_checkpoint", {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1", "state_dict": {"hijack": 1}}),
            ):
>               with pytest.raises((PermissionError, ToolError)) as exc_info:
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E               Failed: DID NOT RAISE any of (PermissionError, ToolError)

tests\test_checkpoint_ownership.py:427: Failed
_____________ test_r4b_exact_env_qdrant_api_key_value_is_redacted _____________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000223774A47D0>

    def test_r4b_exact_env_qdrant_api_key_value_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
        """GRAFO_QDRANT_API_KEY do ambiente (>= 8 chars) deve ser redigida em redact_log_secrets e nos logs."""
        qdrant_secret = "test_qdrant_cluster_secret_987654"
        monkeypatch.setenv("GRAFO_QDRANT_API_KEY", qdrant_secret)
    
>       assert qdrant_secret not in main_mod.redact_log_secrets(f"qdrant_key={qdrant_secret}")
E       AssertionError: assert 'test_qdrant...ecret_987654' not in 'qdrant_key=...ecret_987654'
E         
E         'test_qdrant_cluster_secret_987654' is contained here:
E           qdrant_key=test_qdrant_cluster_secret_987654

tests\test_secret_redaction.py:299: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_sse_auth_hardening.py::test_sse_rejects_query_param_token_with_401
FAILED tests/test_sse_auth_hardening.py::test_sse_rejects_missing_wrong_empty_or_non_bearer_auth
FAILED tests/test_sse_auth_hardening.py::test_sse_accepts_bearer_and_case_insensitive_scheme_using_compare_digest
FAILED tests/test_checkpoint_ownership.py::test_mcp_http_sse_decoupled_agent_token_and_ephemeral_isolation
FAILED tests/test_secret_redaction.py::test_r4b_exact_env_qdrant_api_key_value_is_redacted
5 failed, 26 passed in 3.13s
```

### Mutações Obrigatórias (C1)
```text
M1: KILLED (exit=1) - Re-enable ?token= query param auth in auth_middleware | 1 failed, 30 passed in 3.19s
M2: KILLED (exit=1) - Replace hmac.compare_digest with == in auth_middleware | 1 failed, 30 passed in 3.16s
M3: KILLED (exit=1) - Restore Authorization: Bearer fallback in _resolve_checkpoint_owner_token | 1 failed, 30 passed in 2.72s
M4: KILLED (exit=1) - Remove GRAFO_QDRANT_API_KEY from redact_log_secrets | 1 failed, 30 passed in 2.77s
TOTAL: 4/4 KILLED
```

### Evidência GREEN (`pytest` normal + `--reverse` + `flake8`) (C1)
```text
=== C1 PYTEST NORMAL ===
........................................................................ [ 20%]

........................................................................ [ 41%]

........................................................................ [ 61%]

........................................................................ [ 82%]

...............................................................          [100%]

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-323

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-325

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-342

  

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



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

351 passed, 24 warnings in 126.38s (0:02:06)


=== C1 PYTEST REVERSE ===
........................................................................ [ 20%]

........................................................................ [ 41%]

........................................................................ [ 61%]

........................................................................ [ 82%]

...............................................................          [100%]

============================== warnings summary ===============================

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-116

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-130

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-135

  

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

351 passed, 24 warnings in 119.60s (0:01:59)


=== C1 FLAKE8 ===
0
```

### Secret Scan (C1)
```text
��scanned_files=1575

files_with_findings=0

total_pattern_hits=0
```

### CI GitHub Actions (C1)
```text
Stage C1 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45691880229 sha=2dd3be7b20b4efd738713e4939fcac4b20bb328c status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45691880229
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
Stage C1 CI Run (CI): id=45691880611 sha=2dd3be7b20b4efd738713e4939fcac4b20bb328c status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45691880611
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
```

## 3. Etapa C2 — Fechamento Read-TOCTOU em `core/checkpointer.py` + Higiene DDL

### `git show --stat` (C2)
```text
commit b3b14e2879e6baef6beb74828e6461f340553e7a
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Wed Nov 25 17:30:12 2026 -0300

    fix(security): close read-TOCTOU in checkpointer queries and remove manual DDL in legacy test (4.7-C2)

 core/checkpointer.py               | 10 +++--
 tests/test_agent_checkpointer.py   | 25 +++++-------
 tests/test_checkpoint_ownership.py | 81 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 97 insertions(+), 19 deletions(-)
```

### Evidência RED (C2)
```text
��.....FF                                                                  [100%]

================================== FAILURES ===================================

___________ test_read_toctou_get_checkpoint_never_leaks_victim_row ____________



tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-557/test_read_toctou_get_checkpoin0')



    def test_read_toctou_get_checkpoint_never_leaks_victim_row(tmp_path):

        """Fecha janela read-TOCTOU em get_checkpoint entre pre-check vazio e leitura do blob."""

        db_path = tmp_path / "bl012_toctou_get.db"

        store, db_mgr, cp = _make_db_and_cp(db_path)

        try:

            victim_tok = "test-owner-token-victim-toctou"

            attacker_tok = "test-owner-token-attacker-toctou"

            victim_hash = hashlib.sha256(victim_tok.encode("utf-8")).hexdigest()

    

            orig_read_query = db_mgr.read_query

            race_injected = False

    

            def _racy_read_query(query: str, params: tuple = ()):

                nonlocal race_injected

                rows = orig_read_query(query, params)

                if not race_injected and "DISTINCT owner_hash" in query:

                    race_injected = True

                    assert rows == []

                    with sqlite3.connect(str(db_path)) as conn:

                        conn.execute(

                            "INSERT INTO agent_checkpoints "

                            "(agent_id, session_id, checkpoint_id, state_blob, owner_hash) "

                            "VALUES (?, ?, ?, ?, ?);",

                            ("ag-race", "sess-race", "cp-1", json.dumps({"secret": "victim-race-data"}), victim_hash),

                        )

                        conn.commit()

                return rows

    

            db_mgr.read_query = _racy_read_query

            got = cp.get_checkpoint("ag-race", "sess-race", "cp-1", owner_token=attacker_tok)

>           assert got == {}

E           AssertionError: assert {'secret': 'victim-race-data'} == {}

E             

E             Left contains 1 more item:

E             {'secret': 'victim-race-data'}

E             Use -v to get more diff



tests\test_checkpoint_ownership.py:488: AssertionError

__________ test_read_toctou_list_checkpoints_never_leaks_victim_row ___________



tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-557/test_read_toctou_list_checkpoi0')



    def test_read_toctou_list_checkpoints_never_leaks_victim_row(tmp_path):

        """Fecha janela read-TOCTOU em list_checkpoints entre pre-check vazio e listagem."""

        db_path = tmp_path / "bl012_toctou_list.db"

        store, db_mgr, cp = _make_db_and_cp(db_path)

        try:

            victim_tok = "test-owner-token-victim-toctou-list"

            attacker_tok = "test-owner-token-attacker-toctou-list"

            victim_hash = hashlib.sha256(victim_tok.encode("utf-8")).hexdigest()

    

            orig_read_query = db_mgr.read_query

            race_injected = False

    

            def _racy_read_query(query: str, params: tuple = ()):

                nonlocal race_injected

                rows = orig_read_query(query, params)

                if not race_injected and "DISTINCT owner_hash" in query:

                    race_injected = True

                    assert rows == []

                    with sqlite3.connect(str(db_path)) as conn:

                        conn.execute(

                            "INSERT INTO agent_checkpoints "

                            "(agent_id, session_id, checkpoint_id, state_blob, owner_hash) "

                            "VALUES (?, ?, ?, ?, ?);",

                            ("ag-race", "sess-race", "cp-secret", json.dumps({"s": 1}), victim_hash),

                        )

                        conn.commit()

                return rows

    

            db_mgr.read_query = _racy_read_query

            listed = cp.list_checkpoints("ag-race", "sess-race", owner_token=attacker_tok)

>           assert listed == []

E           AssertionError: assert [{'checkpoint...25 20:13:11'}] == []

E             

E             Left contains one more item: {'checkpoint_id': 'cp-secret', 'created_at': '2026-11-25 20:13:11'}

E             Use -v to get more diff



tests\test_checkpoint_ownership.py:529: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_checkpoint_ownership.py::test_read_toctou_get_checkpoint_never_leaks_victim_row

FAILED tests/test_checkpoint_ownership.py::test_read_toctou_list_checkpoints_never_leaks_victim_row

2 failed, 5 passed in 2.48s
```

### Mutações Obrigatórias (C2)
```text
M1: KILLED (exit=1) - Remove AND owner_hash = ? from get_checkpoint SQL query | 1 failed, 6 passed in 2.34s
M2: KILLED (exit=1) - Remove AND owner_hash = ? from list_checkpoints SQL query | 1 failed, 6 passed in 2.32s
TOTAL: 2/2 KILLED
```

### Evidência GREEN (`pytest` normal + `--reverse` + `flake8`) (C2)
```text
=== C2 PYTEST NORMAL ===
........................................................................ [ 20%]

........................................................................ [ 40%]

........................................................................ [ 61%]

........................................................................ [ 81%]

.................................................................        [100%]

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-325

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-327

  

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

  MemoryError: Simulated catastrophic crash

  

  Enable tracemalloc to get traceback where the object was allocated.

  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

353 passed, 24 warnings in 123.32s (0:02:03)


=== C2 PYTEST REVERSE ===
........................................................................ [ 20%]

........................................................................ [ 40%]

........................................................................ [ 61%]

........................................................................ [ 81%]

.................................................................        [100%]

============================== warnings summary ===============================

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-116

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-130

  

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



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-135

  

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

353 passed, 24 warnings in 122.60s (0:02:02)


=== C2 FLAKE8 ===
0
```

### Secret Scan (C2)
```text
��scanned_files=1581

files_with_findings=0

total_pattern_hits=0
```

### CI GitHub Actions (C2)
```text
Stage C2 CI Run (CI): id=45695576720 sha=b3b14e2879e6baef6beb74828e6461f340553e7a status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45695576720
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
Stage C2 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45695576736 sha=b3b14e2879e6baef6beb74828e6461f340553e7a status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45695576736
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
```

## 4. Etapa C3 — Documentação, Diff Integral e Verificação Final

### Checagem Documental (`c3_doc_check.txt`)
```text
doc_grep_exit=1 (0 hits expected when exit=1)
```

### Caminhos Proibidos (`c3_prohibited_diff.txt`)
- Tamanho: **0 bytes**.
```text
<vazio — 0 bytes de diff nos caminhos proibidos>
```

### Suíte Direcionada, Suíte Completa (Normal + `--reverse`) e `flake8` (C3)
```text
=== C3 TARGETED DOC & GUARD TESTS ===
============================= test session starts =============================

platform win32 -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0 -- C:\Nexus-Memory\GrafoConcierge\.venv_313\Scripts\python.exe

cachedir: .pytest_cache

rootdir: C:\Nexus-Memory\GrafoConcierge

configfile: pyproject.toml

plugins: anyio-4.16.0, reverse-1.9.0, timeout-2.4.0

timeout: 300.0s

timeout method: thread

timeout func_only: False

collecting ... collected 24 items



tests/test_env_example_provider.py::test_env_example_does_not_define_active_llm_provider PASSED [  4%]

tests/test_config.py::TestConciergeConfigDefaults::test_default_instance_exists PASSED [  8%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_1_hybrid_search_weights PASSED [ 12%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_2_recency_parameters PASSED [ 16%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_3_centrality PASSED [ 20%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_4_fts5_bm25 PASSED [ 25%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_5_wings PASSED [ 29%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_6_ingestion_limits_and_filters PASSED [ 33%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_7_summarization_tokens PASSED [ 37%]

tests/test_config.py::TestConciergeConfigDefaults::test_section_8_mcp_runtime PASSED [ 41%]

tests/test_config.py::TestConciergeConfigImmutabilityAndCustomization::test_custom_instance_overrides PASSED [ 45%]

tests/test_config.py::TestConciergeConfigImmutabilityAndCustomization::test_immutability_raises_frozen_instance_error PASSED [ 50%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_api_key_override PASSED [ 54%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_cors_origins_empty_string_preserves_default PASSED [ 58%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_cors_origins_parsing PASSED [ 62%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_lightweight_mode_disabled PASSED [ 66%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_env_lightweight_mode_enabled PASSED [ 70%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_explicit_api_key_has_precedence_over_env PASSED [ 75%]

tests/test_config.py::TestConciergeConfigEnvironmentVariables::test_explicit_lightweight_mode_not_overridden_by_env_false PASSED [ 79%]

tests/test_domain_neutrality_guard.py::test_g1_concierge_config_has_no_wing_keywords PASSED [ 83%]

tests/test_domain_neutrality_guard.py::test_g2_no_retired_domain_strings_in_product_code PASSED [ 87%]

tests/test_domain_neutrality_guard.py::test_g3_real_mining_never_alters_primary_wing PASSED [ 91%]

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project PASSED [ 95%]

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints PASSED [100%]



============================== warnings summary ===============================

tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project

  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

======================= 24 passed, 4 warnings in 15.50s =======================


=== C3 PYTEST NORMAL ===
........................................................................ [ 20%]

........................................................................ [ 40%]

........................................................................ [ 61%]

........................................................................ [ 81%]

.................................................................        [100%]

============================== warnings summary ===============================

tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.

    show_warning(



tests/test_domain_neutrality_guard.py::test_g4_free_text_wings_and_update_project

tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields

tests/test_mcp_server_handlers.py::TestHandleUpdateProject::test_update_project_fields

  C:\Nexus-Memory\GrafoConcierge\storage\store.py:162: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    updates["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-325

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-327

  

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

  MemoryError: Simulated catastrophic crash

  

  Enable tracemalloc to get traceback where the object was allocated.

  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

353 passed, 24 warnings in 121.92s (0:02:01)


=== C3 PYTEST REVERSE ===
........................................................................ [ 20%]

........................................................................ [ 40%]

........................................................................ [ 61%]

........................................................................ [ 81%]

.................................................................        [100%]

============================== warnings summary ===============================

tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:82: SetuptoolsDeprecationWarning: `project.license` as a TOML table is deprecated

  !!

  

          ********************************************************************************

          Please use a simple string containing a SPDX expression for `project.license`. You can also use `project.license-files`. (Both options available on setuptools>=77.0.0).

  

          By 2027-Feb-18, you need to update your project and remove deprecated calls

          or your builds will no longer be supported.

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    corresp(dist, value, root_dir)



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py:61: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    dist._finalize_license_expression()



tests/test_wheel_integrity.py::test_wheel_contains_all_live_modules_and_entrypoints

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\setuptools\dist.py:765: SetuptoolsDeprecationWarning: License classifiers are deprecated.

  !!

  

          ********************************************************************************

          Please consider removing the following classifiers in favor of a SPDX license expression:

  

          License :: OSI Approved :: MIT License

  

          See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.

          ********************************************************************************

  

  !!

    self._finalize_license_expression()



tests/test_storage_logic.py: 14 warnings

  C:\Nexus-Memory\GrafoConcierge\storage\logic.py:342: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

    now = datetime.utcnow()



tests/test_queue_writer_resilience.py::TestQueueWriterResilience::test_t6_batch_fatal_error_notifies_all_batched_callers

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-116

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-130

  

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

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-135

  

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



tests/test_conversational_db.py::test_semantic_facts_bi_temporal

  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.

    show_warning(



-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

353 passed, 24 warnings in 119.46s (0:01:59)


=== C3 FLAKE8 ===
0
```

### Diff Integral (`interface/mcp_server.py`, `main.py`, `core/checkpointer.py`, `.env.example`)
```diff
diff --git a/.env.example b/.env.example
index a57546d..62e53d8 100644
--- a/.env.example
+++ b/.env.example
@@ -97,12 +97,12 @@ GRAFO_DEFAULT_STATE=PLANNING
 
 # Optional checkpoint ownership secret for 'stdio' MCP transport (BL-012)
 # Prevents cross-session read/list/overwrite of agent_checkpoints via SHA-256 owner_hash.
-# Over HTTP/SSE, pass header 'X-Grafo-Agent-Token: <token>' (or 'Authorization: Bearer <token>').
+# Over HTTP/SSE, pass header 'X-Grafo-Agent-Token: <token>' (decoupled from transport Bearer auth).
 # If omitted, each MCP ServerSession receives an ephemeral per-session secret.
 GRAFO_AGENT_TOKEN=
 
 # Optional Bearer token authentication for SSE requests (recommended for VPS)
-# When set, requests require 'Authorization: Bearer <key>' or '?token=<key>'
+# When set, requests require header 'Authorization: Bearer <key>' validated via hmac.compare_digest.
 GRAFO_API_KEY=
 
 # Allowed CORS origins (comma-separated). Default: *
diff --git a/core/checkpointer.py b/core/checkpointer.py
index ab6e8ee..b2f0d69 100644
--- a/core/checkpointer.py
+++ b/core/checkpointer.py
@@ -224,10 +224,11 @@ class AgnosticCheckpointer:
         Returns {} if checkpoint does not exist (agnostic fail-safe).
         """
         self._verify_namespace_ownership(agent_id, session_id, owner_token)
+        caller_hash = self._hash_owner_token(owner_token)
         rows = self.db_manager.read_query(
             "SELECT state_blob FROM agent_checkpoints "
-            "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ?;",
-            (agent_id, session_id, checkpoint_id),
+            "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ? AND owner_hash = ?;",
+            (agent_id, session_id, checkpoint_id, caller_hash),
         )
         if not rows:
             return {}
@@ -253,11 +254,12 @@ class AgnosticCheckpointer:
         Returns list of dicts with checkpoint_id and created_at.
         """
         self._verify_namespace_ownership(agent_id, session_id, owner_token)
+        caller_hash = self._hash_owner_token(owner_token)
         rows = self.db_manager.read_query(
             "SELECT checkpoint_id, created_at FROM agent_checkpoints "
-            "WHERE agent_id = ? AND session_id = ? "
+            "WHERE agent_id = ? AND session_id = ? AND owner_hash = ? "
             "ORDER BY created_at ASC, rowid ASC;",
-            (agent_id, session_id),
+            (agent_id, session_id, caller_hash),
         )
         return [
             {"checkpoint_id": row[0], "created_at": row[1]}
diff --git a/interface/mcp_server.py b/interface/mcp_server.py
index 10612c5..6bda495 100644
--- a/interface/mcp_server.py
+++ b/interface/mcp_server.py
@@ -37,6 +37,7 @@ Architecture:
 from __future__ import annotations
 
 import functools
+import hmac
 import logging
 import os
 import secrets
@@ -195,23 +196,29 @@ class GrafoConciergeServer:
                 origins = ["*"]
 
             # 1. API Key Authentication Middleware (if configured)
-            if api_key:
-                @app.middleware("http")
+            if api_key and str(api_key).strip():
+                from starlette.middleware.base import BaseHTTPMiddleware
+
+                expected_key = str(api_key).strip()
+
                 async def auth_middleware(request, call_next):
-                    # Check Authorization header (Bearer token) or query param ?token=
+                    # Validate exclusively Authorization: Bearer <key> in constant time
                     auth_header = request.headers.get("Authorization", "")
-                    token_param = request.query_params.get("token", "")
-                    
                     is_valid = False
-                    if auth_header.startswith("Bearer "):
-                        is_valid = (auth_header[7:].strip() == api_key)
-                    elif token_param:
-                        is_valid = (token_param.strip() == api_key)
+                    if auth_header[:7].lower() == "bearer ":
+                        provided_tok = auth_header[7:].strip()
+                        if provided_tok:
+                            is_valid = hmac.compare_digest(
+                                provided_tok.encode("utf-8"),
+                                expected_key.encode("utf-8"),
+                            )
 
                     if not is_valid:
                         return JSONResponse({"error": "Unauthorized access to Grafo Concierge MCP"}, status_code=401)
                     return await call_next(request)
 
+                app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
+
             # 2. CORS Middleware
             allow_creds = True if origins != ["*"] else False
             app.add_middleware(
@@ -285,29 +292,18 @@ class GrafoConciergeServer:
             if request_obj is not None:
                 headers = getattr(request_obj, "headers", None)
                 agent_hdr = ""
-                auth_hdr = ""
                 if headers is not None:
                     if hasattr(headers, "items") and isinstance(headers, dict):
                         lower_map = {str(k).lower(): str(v) for k, v in headers.items()}
                         agent_hdr = lower_map.get("x-grafo-agent-token", "").strip()
-                        auth_hdr = lower_map.get("authorization", "").strip()
                     else:
                         agent_hdr = str(
                             headers.get("X-Grafo-Agent-Token")
                             or headers.get("x-grafo-agent-token")
                             or ""
                         ).strip()
-                        auth_hdr = str(
-                            headers.get("Authorization")
-                            or headers.get("authorization")
-                            or ""
-                        ).strip()
                 if agent_hdr:
                     return agent_hdr
-                if auth_hdr.lower().startswith("bearer "):
-                    bearer_tok = auth_hdr[7:].strip()
-                    if bearer_tok:
-                        return bearer_tok
             else:
                 env_tok = os.environ.get("GRAFO_AGENT_TOKEN", "").strip()
                 if env_tok:
diff --git a/main.py b/main.py
index 43c22dc..52bdae9 100644
--- a/main.py
+++ b/main.py
@@ -100,7 +100,7 @@ def redact_log_secrets(text: str) -> str:
         return text
 
     result = text
-    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY", "GRAFO_AGENT_TOKEN"):
+    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY", "GRAFO_AGENT_TOKEN", "GRAFO_QDRANT_API_KEY"):
         secret_val = os.environ.get(env_var, "").strip()
         if len(secret_val) >= 8 and secret_val in result:
             result = result.replace(secret_val, "[REDACTED]")
```
