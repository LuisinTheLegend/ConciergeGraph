# Relatório de Execução — Rodada 4.6 (Segurança de Fronteira e Governança MCP)

- **Base normativa:** `AUDIT_PROTOCOL.md` (Regras 2, 3, 4, 7, 10, 11, 12, 13, 14 e 15), `audits/bypass-governanca-por-session-id.md`, `audits/backlog-final.md` (Track 3: `BL-011`, `BL-012`, `BL-013`, `BL-014`, `BL-015`) e `audits/fase4-decisoes.md`.
- **HEAD de partida:** `e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d` (`e5bd4e1`).
- **HEAD pré-C4 (após C0–C3):** `79afa2cca2abd4241742eecf1fbc75018e796cd4`.
- **Regra 12:** Todas as saídas, diffs, resultados de mutação, scans de segredos e status de CI abaixo foram copiados mecanicamente de `scratch/evidencia_4_6/*`.

## Resumo de Commits e CI (C0–C3)

| Etapa | Commit SHA | Escopo | Mutações | Testes | CI (6 jobs) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| C0 | `0cf527189d4d8e3e6b630e076577e0044b5f9ff4` | EGM + Swarm 4.6 (`audits/egm/4.6-*.md`) | N/A | N/A | 6/6 GREEN |
| C1 | `279f75189d4d8e3e6b630e076577e0044b5f9ff4` | `MCPToolGovernor` 3 estados + teto `max_state` + `PLANNING` (`BL-014`, `BL-015`, Prop. #5) | 5/5 KILLED | 337 passed (normal & `--reverse`) | 6/6 GREEN |
| C2 | `e196005114e2f5c7d9018c642372d632a0af1bf7` | Sessão por transporte (`WeakKeyDictionary`), allowlist estrita e dupla vinculação `list_tools` (`BL-011`, `BL-013`) | 5/5 KILLED | 342 passed (normal & `--reverse`) | 6/6 GREEN |
| C3 | `79afa2cca2abd4241742eecf1fbc75018e796cd4` | Posse persistente `owner_hash` em `agent_checkpoints` + migração `ALTER TABLE` (`BL-012`) | 5/5 KILLED | 347 passed (normal & `--reverse`) | 6/6 GREEN |
| C4 | Commit atual (`docs(security)`) | Documentação viva, verificação final e `audits/relatorio_4_6.md` | N/A | 347 passed (normal & `--reverse`) | Pendente push deste commit (registrado em `ci_C4.txt` e no chat) |

## 1. Preflight (Passo 0)

```text
=== GIT HEAD vs ORIGIN/MAIN ===
HEAD=e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d
origin/main=e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d

=== FLAKE8 CI (exit=0) ===
0

=== PYTEST NORMAL (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
...............................................                          [100%]
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-311
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-313
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-330
  
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
335 passed, 24 warnings in 121.51s (0:02:01)

=== PYTEST REVERSE (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
...............................................                          [100%]
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

tests/test_conversational_db.py::test_user_core_memory_scope_constraint
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
335 passed, 24 warnings in 120.05s (0:02:00)

=== REFERENCE storage/schema.py L145-171, 245-380 ===
145: 
146: CREATE TABLE IF NOT EXISTS agent_checkpoints (
147:     agent_id      TEXT NOT NULL,
148:     session_id    TEXT NOT NULL,
149:     checkpoint_id TEXT NOT NULL,
150:     state_blob    TEXT NOT NULL,
151:     created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
152:     PRIMARY KEY (agent_id, session_id, checkpoint_id)
153: );
154: """
155: 
156: INDEXES_SQL: str = """
157: CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project_uuid);
158: CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
159: CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
160: CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
161: CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
162: CREATE INDEX IF NOT EXISTS idx_refwings_project ON reference_wings(project_uuid);
163: CREATE INDEX IF NOT EXISTS idx_trajectories_project ON trajectories(project_uuid);
164: CREATE INDEX IF NOT EXISTS idx_trajectories_status ON trajectories(status);
165: CREATE INDEX IF NOT EXISTS idx_commitlog_project ON commit_log(project_uuid);
166: CREATE INDEX IF NOT EXISTS idx_commitlog_date ON commit_log(created_at);
167: CREATE INDEX IF NOT EXISTS idx_user_core_memory_scope ON user_core_memory(scope_type, scope_id);
168: CREATE INDEX IF NOT EXISTS idx_semantic_facts_scope ON semantic_facts(scope_type, scope_id);
169: CREATE INDEX IF NOT EXISTS idx_semantic_facts_temporal ON semantic_facts(t_valid, t_invalid);
170: CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_lookup ON agent_checkpoints(agent_id, session_id, created_at);
171: """
...
245:         """
246:         logger.debug("Starting application of Schema v%s", self.SCHEMA_VERSION)
247:         try:
248:             self._conn.executescript(TABLES_SQL)
249:             self._conn.executescript(INDEXES_SQL)
250:             self._conn.executescript(FTS5_TABLE_SQL)
251:             self._conn.executescript(FTS5_TRIGGERS_SQL)
252:             self._conn.commit()
253:             
254:             # Ensure the column 'content' exists (retroactive migration for legacy databases)
255:             cursor = self._conn.execute("PRAGMA table_info(nodes)")
256:             cols = [row[1] for row in cursor.fetchall()]
257:             if "content" not in cols:
258:                 self._conn.execute("ALTER TABLE nodes ADD COLUMN content TEXT;")
259:                 self._conn.commit()
260:                 logger.info("Migration: 'content' column added to table 'nodes'.")
261: 
262:             # Ensure 'utility_alpha' and 'utility_beta' columns exist in semantic_facts
263:             cursor = self._conn.execute("PRAGMA table_info(semantic_facts)")
264:             sem_cols = [row[1] for row in cursor.fetchall()]
265:             if "utility_alpha" not in sem_cols:
266:                 self._conn.execute("ALTER TABLE semantic_facts ADD COLUMN utility_alpha REAL NOT NULL DEFAULT 1.0;")
267:                 self._conn.commit()
268:                 logger.info("Migration: 'utility_alpha' column added to table 'semantic_facts'.")
269:             if "utility_beta" not in sem_cols:
270:                 self._conn.execute("ALTER TABLE semantic_facts ADD COLUMN utility_beta REAL NOT NULL DEFAULT 1.0;")
271:                 self._conn.commit()
272:                 logger.info("Migration: 'utility_beta' column added to table 'semantic_facts'.")
273: 
274:             # FTS5 Migration: upgrade nodes_fts to 4 columns (label, tags, summary, content)
275:             # with unicode61 remove_diacritics 2.
276:             cursor = self._conn.execute(
277:                 "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
278:             )
279:             fts_row = cursor.fetchone()
280:             needs_fts_upgrade = False
281:             if fts_row and fts_row[0]:
282:                 fts_sql = fts_row[0].lower()
283:                 if "content," not in fts_sql and "content)" not in fts_sql:
284:                     needs_fts_upgrade = True
285:                 elif "remove_diacritics 2" not in fts_sql:
286:                     needs_fts_upgrade = True
287:             elif not fts_row:
288:                 needs_fts_upgrade = True
289: 
290:             if needs_fts_upgrade and fts_row:
291:                 # Non-new database with old nodes_fts schema:
292:                 # 1. Check if database has nodes; if so, create backup before modifying.
293:                 node_count = 0
294:                 try:
295:                     cur_cnt = self._conn.execute("SELECT COUNT(*) FROM nodes")
296:                     node_count = cur_cnt.fetchone()[0]
297:                 except Exception:
298:                     pass
299: 
300:                 if node_count > 0:
301:                     try:
302:                         db_list = self._conn.execute("PRAGMA database_list").fetchall()
303:                         db_path = None
304:                         for db_entry in db_list:
305:                             if db_entry[1] == "main" and db_entry[2]:
306:                                 db_path = db_entry[2]
307:                                 break
308:                         if db_path and os.path.exists(db_path) and db_path != ":memory:":
309:                             bak_path = f"{db_path}.pre_fts_v2.bak"
310:                             # Use SQLite online backup API
311:                             backup_conn = sqlite3.connect(bak_path)
312:                             self._conn.backup(backup_conn)
313:                             backup_conn.close()
314:                             logger.info("FTS Migration: backup created at %s (melhor esforço)", bak_path)
315:                     except Exception as bak_err:
316:                         logger.warning("FTS Migration backup warning (melhor esforço, prosseguindo com migração atômica): %s", bak_err)
317: 
318:                 # 2. Atomic FTS Migration: Execute DROP, CREATE, TRIGGERS, REBUILD and INTEGRITY-CHECK
319:                 # in a single explicit transaction using execute() (never executescript(), which commits implicitly).
320:                 # All-or-nothing: if an interruption occurs at any point, the entire block is rolled back.
321:                 self._conn.execute("BEGIN IMMEDIATE;")
322:                 try:
323:                     self._conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
324:                     self._conn.execute("DROP TRIGGER IF EXISTS nodes_ad;")
325:                     self._conn.execute("DROP TRIGGER IF EXISTS nodes_au;")
326:                     self._conn.execute("DROP TABLE IF EXISTS nodes_fts;")
327: 
328:                     self._conn.execute(FTS5_TABLE_SQL.strip())
329:                     for trig_sql in FTS5_TRIGGER_STATEMENTS:
330:                         self._conn.execute(trig_sql.strip())
331: 
332:                     self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
333:                     self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
334:                     self._conn.execute("COMMIT;")
335:                     logger.info("FTS Migration: nodes_fts upgraded to 4 columns with unicode61 remove_diacritics 2.")
336:                 except Exception as mig_err:
337:                     self._conn.execute("ROLLBACK;")
338:                     logger.error("FTS Migration failed and was rolled back atomically: %s", mig_err)
339:                     raise
340: 
341:             # Ensure the current version is saved in DB.
342:             current_version = self.get_schema_version()
343:             if not current_version or current_version != self.SCHEMA_VERSION:
344:                 self.set_schema_version(self.SCHEMA_VERSION)
345: 
346:             # Retroactive migration: UNIQUE(scope_type, scope_id, block_label) in user_core_memory.
347:             # Databases created before this version do not have the unique index — without it the
348:             # INSERT OR REPLACE does not work as upsert.
349:             cursor = self._conn.execute(
350:                 "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_core_memory_scope_label'"
351:             )
352:             if cursor.fetchone() is None:
353:                 try:
354:                     # Removes duplicates keeping only the most recent record
355:                     self._conn.execute("""
356:                         DELETE FROM user_core_memory
357:                         WHERE id NOT IN (
358:                             SELECT MAX(id) FROM user_core_memory
359:                             GROUP BY scope_type, scope_id, block_label
360:                         )
361:                     """)
362:                     self._conn.execute("""
363:                         CREATE UNIQUE INDEX IF NOT EXISTS uq_core_memory_scope_label
364:                         ON user_core_memory(scope_type, scope_id, block_label)
365:                     """)
366:                     self._conn.commit()
367:                     logger.info("Migration: UNIQUE index 'uq_core_memory_scope_label' created in user_core_memory.")
368:                 except Exception as idx_err:
369:                     logger.warning("Migration UNIQUE index user_core_memory failed (may already exist): %s", idx_err)
370: 
371:             # Independent startup consistency check for FTS5 index.
372:             # Verifies that nodes table and nodes_fts_docsize are in sync;
373:             # repairs any index left empty or corrupted by prior crashes.
374:             self._check_and_repair_fts_consistency()
375: 
376:         except Exception as e:
377:             self._conn.rollback()
378:             logger.error("Failed to apply schema: %s", e)
379:             raise
380: 

=== REFERENCE storage/store.py L84-110 ===
84:     def _boot_schema(self, db_path: str) -> None:
85:         """Opens temporary connection to apply the schema idempotently."""
86:         conn = sqlite3.connect(db_path)
87:         try:
88:             conn.execute("PRAGMA journal_mode=WAL;")
89:             conn.execute("PRAGMA busy_timeout=5000;")
90:             conn.execute("PRAGMA foreign_keys=ON;")
91:             mgr = SchemaManager(conn)
92:             mgr.apply_full_schema()
93: 
94:             # Verification log
95:             tables = mgr.verify_tables_exist()
96:             missing = [t for t, exists in tables.items() if not exists]
97:             if missing:
98:                 logger.error("Missing tables after boot: %s", missing)
99:                 raise RuntimeError(f"Incomplete schema: {missing}")
100: 
101:             triggers = mgr.verify_triggers_exist()
102:             missing_t = [t for t, exists in triggers.items() if not exists]
103:             if missing_t:
104:                 logger.error("Missing FTS5 triggers: %s", missing_t)
105:                 raise RuntimeError(f"Missing triggers: {missing_t}")
106: 
107:             logger.info("Schema v%s verified - all tables and triggers OK.", SchemaManager.SCHEMA_VERSION)
108:         finally:
109:             conn.close()
110:
```

## 2. Etapa C0 — EGM + Swarm Pré-Execução

### `git show --stat` (C0)
```text
0cf5271 docs(audit): 4.6-C0 relatórios Swarm pré-execução (segurança MCP BL-011..BL-015)
 audits/egm/4.6-critic.md  | 216 +++++++++++++++++++++++++++++++++++++++++
 audits/egm/4.6-design.md  | 234 ++++++++++++++++++++++++++++++++++++++++++++
 audits/egm/4.6-fatos.md   | 243 ++++++++++++++++++++++++++++++++++++++++++++++
 audits/egm/4.6-sintese.md | 100 +++++++++++++++++++
 4 files changed, 793 insertions(+)
```

### Secret Scan (C0)
```text
scanned_files=1540
files_with_findings=0
total_pattern_hits=0
```

### CI GitHub Actions (C0)
```text
Stage C0 CI Run (CI): id=45666208185 sha=0cf527186902dc771c07c4d0b3273146614275f7 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45666208185
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
Stage C0 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45666208368 sha=0cf527186902dc771c07c4d0b3273146614275f7 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45666208368
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
```

## 3. Etapa C1 — Governança 3 Estados, Teto de Privilégio e `PLANNING` Padrão (`BL-014`, `BL-015`)

### `git show --stat` (C1)
```text
279f751 fix(security): enforce PLANNING default, privilege ceiling and 3-state matrix (BL-014, BL-015, 4.6-C1)
 core/mcp_governor.py              | 119 ++++++++++++++++++++++----------------
 tests/test_governor_wiring.py     |   5 +-
 tests/test_interface_contracts.py |  23 +++-----
 tests/test_mcp_governor.py        | 101 ++++++++++++++++++++++++--------
 4 files changed, 159 insertions(+), 89 deletions(-)
```

### Evidência RED (C1)
```text
FFFFFFFFFF                                                               [100%]
================================== FAILURES ===================================
_ TestMCPToolGovernor.test_classification_partition_and_three_state_disclosure_matrix _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_classification_partition_and_three_state_disclosure_matrix>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_default_state_is_planning_and_fail_fast_validation _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_default_state_is_planning_and_fail_fast_validation>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_privilege_ceiling_blocks_escalation_and_allows_downgrade _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_privilege_ceiling_blocks_escalation_and_allows_downgrade>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_session_state_normalization_invalid_preservation_and_isolation _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_session_state_normalization_invalid_preservation_and_isolation>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
___ TestMCPToolGovernor.test_should_disclose_all_tools_in_maintenance_state ___

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_should_disclose_all_tools_in_maintenance_state>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_should_disclose_mutation_tools_in_execution_state __

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_should_disclose_mutation_tools_in_execution_state>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_______ TestMCPToolGovernor.test_should_filter_tools_in_planning_state ________

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_should_filter_tools_in_planning_state>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_should_raise_security_exception_on_direct_call_attempt _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_should_raise_security_exception_on_direct_call_attempt>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_unknown_and_removed_tools_blocked_in_execution_and_planning _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_unknown_and_removed_tools_blocked_in_execution_and_planning>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
_ TestMCPToolGovernor.test_unknown_and_removed_tools_filtered_out_fail_closed _

self = <test_mcp_governor.TestMCPToolGovernor testMethod=test_unknown_and_removed_tools_filtered_out_fail_closed>

    def setUp(self):
        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
>       self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: MCPToolGovernor.__init__() got an unexpected keyword argument 'max_state'

tests\test_mcp_governor.py:21: TypeError
=========================== short test summary info ===========================
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_classification_partition_and_three_state_disclosure_matrix
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_default_state_is_planning_and_fail_fast_validation
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_privilege_ceiling_blocks_escalation_and_allows_downgrade
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_session_state_normalization_invalid_preservation_and_isolation
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_all_tools_in_maintenance_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_disclose_mutation_tools_in_execution_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_filter_tools_in_planning_state
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_should_raise_security_exception_on_direct_call_attempt
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_blocked_in_execution_and_planning
FAILED tests/test_mcp_governor.py::TestMCPToolGovernor::test_unknown_and_removed_tools_filtered_out_fail_closed
10 failed in 1.28s
```

### Mutações Obrigatórias (C1)
```text
BASE CHECK exit=0

[KILLED] M1: reverter default 'PLANNING' -> 'EXECUTION' (exit=1)
  1 failed, 29 passed in 1.50s

[KILLED] M2: desabilitar checagem de teto (rank > max_state) em set_session_state (exit=1)
  1 failed, 29 passed in 1.55s

[KILLED] M3: reverter concierge_set_state para READ_ONLY (exit=1)
  5 failed, 25 passed in 1.63s

[KILLED] M4: remover validacao fail-fast de default_state invalido no __init__ (exit=1)
  1 failed, 29 passed in 1.51s

[KILLED] M5: reinserir estado legado DISCOVERY em TOOL_DISCLOSURE_MATRIX (exit=1)
  3 failed, 27 passed in 1.50s

RESULTADO MUTACOES C1: TODAS MORTAS (5/5)
```

### Evidência GREEN (`pytest` normal + `--reverse` + `flake8`) (C1)
```text
=== PYTEST NORMAL (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
.................................................                        [100%]
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-313
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-315
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-332
  
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
337 passed, 24 warnings in 123.18s (0:02:03)

=== PYTEST REVERSE (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
.................................................                        [100%]
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

tests/test_conversational_db.py::test_qdrant_vector_store_payload_validation
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
337 passed, 24 warnings in 113.17s (0:01:53)

=== FLAKE8 CI (exit=0) ===
0
```

### Secret Scan (C1)
```text
scanned_files=1546
files_with_findings=0
total_pattern_hits=0
```

### CI GitHub Actions (C1)
```text
Stage C1 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45668909555 sha=279f75189d4d8e3e6b630e076577e0044b5f9ff4 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45668909555
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.10): status=completed conclusion=success
Stage C1 CI Run (CI): id=45668909867 sha=279f75189d4d8e3e6b630e076577e0044b5f9ff4 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45668909867
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
```

### `git diff` Integral (C1)
```diff
diff --git a/core/mcp_governor.py b/core/mcp_governor.py
index 48179ca..fc2a70a 100644
--- a/core/mcp_governor.py
+++ b/core/mcp_governor.py
@@ -1,16 +1,16 @@
 """
-core/mcp_governor.py — SDD-SURVIVAL-21
+core/mcp_governor.py — SDD-SURVIVAL-21 (Hardened V4 Governance)
 
 Progressive Tool Disclosure on FastMCP Server.
 
 Acts as a dynamic cognitive firewall for AI agents, intercepting
-and filtering disclosed and executed tools based on the current state
-of their finite state machine (FSM).
+and filtering disclosed and executed tools based on the active
+operational state and configured privilege ceiling (max_state).
 
 Protection Layers:
   1. filter_tools: Passive listing filter (Discovery/Context Window Optimization).
   2. validate_tool_execution: Active execution barrier that blocks direct command injection
-     and raises SecurityException upon scope violations.
+     and raises SecurityException (PermissionError) upon scope violations.
 """
 
 import logging
@@ -19,7 +19,7 @@ from typing import Any, Dict, List, Optional, Union
 logger = logging.getLogger(__name__)
 
 
-class SecurityException(Exception):
+class SecurityException(PermissionError):
     """Exception raised when an agent attempts to bypass tool governance rules."""
     pass
 
@@ -29,55 +29,71 @@ class MCPToolGovernor:
     FastMCP progressive tool disclosure and governance controller.
     """
 
-    def __init__(self, default_state: Optional[str] = None):
+    STATE_PRIVILEGE_RANK: Dict[str, int] = {
+        "PLANNING": 0,
+        "EXECUTION": 1,
+        "MAINTENANCE": 2,
+    }
+
+    def __init__(
+        self,
+        default_state: Optional[str] = None,
+        max_state: Optional[str] = None,
+    ):
         import os
-        if default_state is not None:
-            self.default_state = default_state.upper()
-        else:
-            env_default = os.environ.get("GRAFO_DEFAULT_STATE", "EXECUTION")
-            self.default_state = env_default.upper()
-        # Active session state dict: {session_id: current_fsm_state}
-        self.sessions_state: Dict[str, str] = {}
 
-        # Strict Visibility Matrix Definition
+        # Strict Visibility Matrix Definition (3 operational states)
         self.TOOL_DISCLOSURE_MATRIX: Dict[str, Dict[str, List[str]]] = {
             "PLANNING": {
                 "allowed_categories": ["READ_ONLY"],
                 "allowed_tools": [],
             },
-            "DISCOVERY": {
-                "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": [],
-            },
             "EXECUTION": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
                 "allowed_tools": [],
             },
-            "TDD_GREEN": {
-                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
-                "allowed_tools": [],
-            },
-            "REFACTORING": {
-                "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION"],
-                "allowed_tools": [],
-            },
             "MAINTENANCE": {
                 "allowed_categories": ["READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"],
                 "allowed_tools": [],
             },
-            "STALL": {
-                "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": [],
-            },
-            "SUCCESS": {
-                "allowed_categories": ["READ_ONLY"],
-                "allowed_tools": [],
-            },
         }
 
-        # Static tool classification catalog (31 live MCP tools)
+        if default_state is not None:
+            resolved_default = default_state.strip().upper()
+        else:
+            resolved_default = os.environ.get("GRAFO_DEFAULT_STATE", "PLANNING").strip().upper()
+
+        if resolved_default not in self.TOOL_DISCLOSURE_MATRIX:
+            raise ValueError(
+                f"Invalid GRAFO_DEFAULT_STATE/default_state '{resolved_default}'. "
+                f"Expected one of {sorted(self.TOOL_DISCLOSURE_MATRIX)}."
+            )
+        self.default_state = resolved_default
+
+        if max_state is not None:
+            resolved_max = max_state.strip().upper()
+        else:
+            resolved_max = self.default_state
+
+        if resolved_max not in self.TOOL_DISCLOSURE_MATRIX:
+            raise ValueError(
+                f"Invalid max_state '{resolved_max}'. "
+                f"Expected one of {sorted(self.TOOL_DISCLOSURE_MATRIX)}."
+            )
+
+        if self.STATE_PRIVILEGE_RANK[resolved_max] < self.STATE_PRIVILEGE_RANK[self.default_state]:
+            raise ValueError(
+                f"Invalid privilege bounds: max_state '{resolved_max}' cannot be lower than "
+                f"default_state '{self.default_state}'."
+            )
+        self.max_state = resolved_max
+
+        # Active session state dict: {session_id: current_fsm_state}
+        self.sessions_state: Dict[str, str] = {}
+
+        # Static tool classification catalog (31 live MCP tools: 17 READ_ONLY, 12 LOCAL_MUTATION, 2 DANGEROUS)
         self.TOOL_CLASSIFICATION: Dict[str, str] = {
-            # READ_ONLY
+            # READ_ONLY (17)
             "get_full_topology": "READ_ONLY",
             "get_trajectories": "READ_ONLY",
             "find_similar": "READ_ONLY",
@@ -93,11 +109,11 @@ class MCPToolGovernor:
             "get_callers": "READ_ONLY",
             "count_embeddings": "READ_ONLY",
             "concierge_get_call_chain": "READ_ONLY",
-            "concierge_set_state": "READ_ONLY",
             "agent_get_checkpoint": "READ_ONLY",
             "agent_list_checkpoints": "READ_ONLY",
 
-            # LOCAL_MUTATION
+            # LOCAL_MUTATION (12)
+            "concierge_set_state": "LOCAL_MUTATION",
             "agent_save_checkpoint": "LOCAL_MUTATION",
             "concierge_register": "LOCAL_MUTATION",
             "concierge_mine": "LOCAL_MUTATION",
@@ -110,22 +126,29 @@ class MCPToolGovernor:
             "remove_reference_wing": "LOCAL_MUTATION",
             "update_project": "LOCAL_MUTATION",
 
-            # DANGEROUS
+            # DANGEROUS (2)
             "reset_collection": "DANGEROUS",
             "delete_project": "DANGEROUS",
         }
 
     def set_session_state(self, session_id: str, state_name: str) -> None:
-        """Sets active FSM state for a session."""
-        upper_state = state_name.upper()
-        if upper_state in self.TOOL_DISCLOSURE_MATRIX:
-            self.sessions_state[session_id] = upper_state
-        else:
+        """Sets active operational state for a session within the max_state privilege ceiling."""
+        upper_state = state_name.strip().upper()
+        if upper_state not in self.TOOL_DISCLOSURE_MATRIX:
             logger.warning(
                 "[MCP-GOVERNOR] Unknown state '%s' for session '%s'. Preserving current state.",
                 state_name,
                 session_id,
             )
+            return
+
+        if self.STATE_PRIVILEGE_RANK[upper_state] > self.STATE_PRIVILEGE_RANK[self.max_state]:
+            raise SecurityException(
+                f"Access denied: cannot elevate session '{session_id}' to state '{upper_state}' "
+                f"above configured privilege ceiling '{self.max_state}'."
+            )
+
+        self.sessions_state[session_id] = upper_state
 
     def get_session_state(self, session_id: str) -> str:
         """Retrieves active state of a session (or returns default_state)."""
@@ -141,9 +164,7 @@ class MCPToolGovernor:
         Supports both dictionaries (e.g. `{'name': 'concierge_commit'}`) and Tool instances.
         """
         current_state = self.get_session_state(session_id)
-        rules = self.TOOL_DISCLOSURE_MATRIX.get(
-            current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
-        )
+        rules = self.TOOL_DISCLOSURE_MATRIX[current_state]
 
         filtered = []
         for tool in tools_list:
@@ -168,9 +189,7 @@ class MCPToolGovernor:
         if a blocked tool is invoked.
         """
         current_state = self.get_session_state(session_id)
-        rules = self.TOOL_DISCLOSURE_MATRIX.get(
-            current_state, self.TOOL_DISCLOSURE_MATRIX[self.default_state]
-        )
+        rules = self.TOOL_DISCLOSURE_MATRIX[current_state]
         category = self.TOOL_CLASSIFICATION.get(tool_name, "DANGEROUS")
 
         if category in rules["allowed_categories"] or tool_name in rules["allowed_tools"]:
diff --git a/tests/test_governor_wiring.py b/tests/test_governor_wiring.py
index 82b7d89..f9220f2 100644
--- a/tests/test_governor_wiring.py
+++ b/tests/test_governor_wiring.py
@@ -154,11 +154,13 @@ def test_t5_governed_list_tools_filters_by_explicit_session_id(tmp_path, monkeyp
         # Sessão explícita não-"default" mantendo "default" intocado
         sid = "sess_wiring_list"
         assert "default" not in server.governor.sessions_state
+        monkeypatch.setattr(server.governor, "max_state", "MAINTENANCE")
 
         server.governor.set_session_state(sid, "PLANNING")
         planning_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
-        assert len(planning_names) == 18
+        assert len(planning_names) == 17
         assert "get_full_topology" in planning_names
+        assert "concierge_set_state" not in planning_names
         assert "concierge_commit" not in planning_names
         assert "delete_project" not in planning_names
         assert "reset_collection" not in planning_names
@@ -166,6 +168,7 @@ def test_t5_governed_list_tools_filters_by_explicit_session_id(tmp_path, monkeyp
         server.governor.set_session_state(sid, "EXECUTION")
         exec_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
         assert len(exec_names) == 29
+        assert "concierge_set_state" in exec_names
         assert "concierge_commit" in exec_names
         assert "delete_project" not in exec_names
         assert "reset_collection" not in exec_names
diff --git a/tests/test_interface_contracts.py b/tests/test_interface_contracts.py
index 775168a..9a4de75 100644
--- a/tests/test_interface_contracts.py
+++ b/tests/test_interface_contracts.py
@@ -245,15 +245,11 @@ class TestMCPToolRegistration:
     def test_governor_disclosure_matrix_clean_and_valid(self, server):
         expected_states = {
             "PLANNING",
-            "DISCOVERY",
             "EXECUTION",
-            "TDD_GREEN",
-            "REFACTORING",
             "MAINTENANCE",
-            "STALL",
-            "SUCCESS",
         }
         assert set(server.governor.TOOL_DISCLOSURE_MATRIX.keys()) == expected_states
+        assert server.governor.TOOL_CLASSIFICATION["concierge_set_state"] == "LOCAL_MUTATION"
         classified = set(server.governor.TOOL_CLASSIFICATION.keys())
         valid_categories = {"READ_ONLY", "LOCAL_MUTATION", "DANGEROUS"}
         for state_name, rules in server.governor.TOOL_DISCLOSURE_MATRIX.items():
@@ -296,6 +292,7 @@ class TestMCPToolRegistration:
         # so restore sessions_state["default"] without leaking an injected key.
         had_default = "default" in server.governor.sessions_state
         orig_default = server.governor.sessions_state.get("default")
+        orig_max_state = server.governor.max_state
         try:
             server.governor.set_session_state("default", "PLANNING")
             with pytest.raises(SecurityException):
@@ -310,16 +307,10 @@ class TestMCPToolRegistration:
                 )
 
             # 2. Transition session state to MAINTENANCE and exercise lightweight-safe tools
-            # NOTE (BL-011 dependency): transitioning PLANNING -> MAINTENANCE via
-            # concierge_set_state relies on BL-011 (MCP privilege escalation still open).
-            # After BL-011 is closed, transition the test directly via:
-            # server.governor.set_session_state("default", "MAINTENANCE")
-            state_res = call_governed(
-                "concierge_set_state",
-                {"state_name": "MAINTENANCE", "session_id": "default"},
-            )
-            assert state_res["success"] is True
-            assert state_res["active_state"] == "MAINTENANCE"
+            server.governor.max_state = "MAINTENANCE"
+            server.governor.set_session_state("default", "MAINTENANCE")
+            server.governor.set_session_state("sess_contract_maint", "MAINTENANCE")
+            assert server.governor.get_session_state("default") == "MAINTENANCE"
 
             status_res = call_governed("concierge_status", {})
             assert status_res["success"] is True
@@ -452,6 +443,8 @@ class TestMCPToolRegistration:
             assert isinstance(list_cp_res, list)
             assert len(list_cp_res) >= 1
         finally:
+            server.governor.max_state = orig_max_state
+            server.governor.sessions_state.pop("sess_contract_maint", None)
             if had_default:
                 server.governor.sessions_state["default"] = orig_default
             else:
diff --git a/tests/test_mcp_governor.py b/tests/test_mcp_governor.py
index d428347..881da03 100644
--- a/tests/test_mcp_governor.py
+++ b/tests/test_mcp_governor.py
@@ -1,51 +1,48 @@
 """
-tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21).
+tests/test_mcp_governor.py — Testes unitários isolados do MCPToolGovernor (SDD-21 / BL-014 / BL-015).
 
 Valida o catálogo vivo das 31 ferramentas MCP sem depender de mocks fantasmas
-ou módulos em quarentena, cobrindo camadas passiva (`filter_tools`) e ativa
-(`validate_tool_execution`) além da garantia fail-closed.
+ou módulos em quarentena, cobrindo matriz de 3 estados, default seguro PLANNING,
+teto de privilégio (max_state), classificação de concierge_set_state como
+LOCAL_MUTATION, validação fail-fast e garantia fail-closed.
 """
 
+import os
 from types import SimpleNamespace
 import unittest
+from unittest.mock import patch
 
 from core.mcp_governor import MCPToolGovernor, SecurityException
 
 
 class TestMCPToolGovernor(unittest.TestCase):
     def setUp(self):
-        self.governor = MCPToolGovernor(default_state="PLANNING")
+        # Governor com teto MAINTENANCE para exercitar todas as faixas nos testes de matriz
+        self.governor = MCPToolGovernor(default_state="PLANNING", max_state="MAINTENANCE")
 
         # Ferramentas vivas registradas no FastMCP cobrindo todas as 3 categorias
-        # (incluindo ambas as ferramentas DANGEROUS vivas)
+        # (incluindo concierge_set_state em LOCAL_MUTATION e ambas DANGEROUS vivas)
         self.live_tools = [
             {"name": "get_full_topology", "description": "Lê topologia"},
             {"name": "concierge_search", "description": "Busca híbrida"},
+            {"name": "concierge_set_state", "description": "Transiciona estado"},
             {"name": "concierge_commit", "description": "Registra commit"},
             {"name": "delete_project", "description": "Remove projeto"},
             {"name": "reset_collection", "description": "Reseta coleção vetorial"},
         ]
 
-    def test_classification_partition_and_clean_disclosure_matrix(self):
-        """Valida partição exata 18/11/2 (31 tools) e allowed_tools vazio nos 8 estados."""
+    def test_classification_partition_and_three_state_disclosure_matrix(self):
+        """Valida partição exata 17/12/2 (31 tools), concierge_set_state=LOCAL_MUTATION e matriz de 3 estados."""
         counts = {"READ_ONLY": 0, "LOCAL_MUTATION": 0, "DANGEROUS": 0}
         for tool_name, category in self.governor.TOOL_CLASSIFICATION.items():
             self.assertIn(category, counts, f"Categoria inesperada em {tool_name}: {category}")
             counts[category] += 1
 
         self.assertEqual(len(self.governor.TOOL_CLASSIFICATION), 31)
-        self.assertEqual(counts, {"READ_ONLY": 18, "LOCAL_MUTATION": 11, "DANGEROUS": 2})
-
-        expected_states = {
-            "PLANNING",
-            "DISCOVERY",
-            "EXECUTION",
-            "TDD_GREEN",
-            "REFACTORING",
-            "MAINTENANCE",
-            "STALL",
-            "SUCCESS",
-        }
+        self.assertEqual(self.governor.TOOL_CLASSIFICATION["concierge_set_state"], "LOCAL_MUTATION")
+        self.assertEqual(counts, {"READ_ONLY": 17, "LOCAL_MUTATION": 12, "DANGEROUS": 2})
+
+        expected_states = {"PLANNING", "EXECUTION", "MAINTENANCE"}
         self.assertEqual(set(self.governor.TOOL_DISCLOSURE_MATRIX.keys()), expected_states)
         for state_name, rules in self.governor.TOOL_DISCLOSURE_MATRIX.items():
             self.assertEqual(
@@ -54,14 +51,67 @@ class TestMCPToolGovernor(unittest.TestCase):
                 f"Estado '{state_name}' deveria ter allowed_tools vazio",
             )
 
+    def test_default_state_is_planning_and_fail_fast_validation(self):
+        """BL-015 / Decisão 4A: default sem env é PLANNING; estados inválidos ou max < default levantam ValueError."""
+        with patch.dict(os.environ, {}, clear=False):
+            os.environ.pop("GRAFO_DEFAULT_STATE", None)
+            gov = MCPToolGovernor()
+            self.assertEqual(gov.default_state, "PLANNING")
+            self.assertEqual(gov.max_state, "PLANNING")
+            self.assertEqual(gov.get_session_state("new_sess"), "PLANNING")
+
+        with self.assertRaises(ValueError):
+            MCPToolGovernor(default_state="INVALID")
+
+        with self.assertRaises(ValueError):
+            MCPToolGovernor(default_state="INVALID", max_state="PLANNING")
+
+        with patch.dict(os.environ, {"GRAFO_DEFAULT_STATE": "INVALID"}, clear=False):
+            with self.assertRaises(ValueError):
+                MCPToolGovernor()
+
+        with self.assertRaises(ValueError):
+            MCPToolGovernor(default_state="PLANNING", max_state="DISCOVERY")
+
+        with self.assertRaises(ValueError):
+            MCPToolGovernor(default_state="MAINTENANCE", max_state="EXECUTION")
+
+    def test_privilege_ceiling_blocks_escalation_and_allows_downgrade(self):
+        """Decisão 1A: set_session_state bloqueia elevação acima de max_state com SecurityException(PermissionError)."""
+        gov_plan = MCPToolGovernor(default_state="PLANNING")
+        for forbidden in ("EXECUTION", "MAINTENANCE"):
+            with self.assertRaises(SecurityException) as ctx:
+                gov_plan.set_session_state("sess_plan", forbidden)
+            self.assertIsInstance(ctx.exception, PermissionError)
+            self.assertEqual(gov_plan.get_session_state("sess_plan"), "PLANNING")
+        gov_plan.set_session_state("sess_plan", "planning")
+        self.assertEqual(gov_plan.get_session_state("sess_plan"), "PLANNING")
+
+        gov_exec = MCPToolGovernor(default_state="EXECUTION")
+        self.assertEqual(gov_exec.max_state, "EXECUTION")
+        gov_exec.set_session_state("sess_exec", "PLANNING")
+        self.assertEqual(gov_exec.get_session_state("sess_exec"), "PLANNING")
+        gov_exec.set_session_state("sess_exec", "EXECUTION")
+        self.assertEqual(gov_exec.get_session_state("sess_exec"), "EXECUTION")
+        with self.assertRaises(SecurityException) as ctx_up:
+            gov_exec.set_session_state("sess_exec", "MAINTENANCE")
+        self.assertIsInstance(ctx_up.exception, PermissionError)
+        self.assertEqual(gov_exec.get_session_state("sess_exec"), "EXECUTION")
+
+        # concierge_set_state (LOCAL_MUTATION) bloqueada em PLANNING
+        with self.assertRaises(SecurityException) as ctx_set:
+            gov_plan.validate_tool_execution("sess_plan", "concierge_set_state")
+        self.assertIsInstance(ctx_set.exception, PermissionError)
+
     def test_should_filter_tools_in_planning_state(self):
-        """Valida que apenas ferramentas READ_ONLY passam em PLANNING."""
+        """Valida que apenas ferramentas READ_ONLY passam em PLANNING (excluindo concierge_set_state)."""
         self.governor.set_session_state("session_123", "PLANNING")
 
         filtered = self.governor.filter_tools("session_123", self.live_tools)
         tool_names = {t["name"] for t in filtered}
 
         self.assertEqual(tool_names, {"get_full_topology", "concierge_search"})
+        self.assertNotIn("concierge_set_state", tool_names)
         self.assertNotIn("concierge_commit", tool_names)
         self.assertNotIn("delete_project", tool_names)
         self.assertNotIn("reset_collection", tool_names)
@@ -72,13 +122,16 @@ class TestMCPToolGovernor(unittest.TestCase):
         self.assertEqual(filtered_attr, {"get_full_topology", "concierge_search"})
 
     def test_should_disclose_mutation_tools_in_execution_state(self):
-        """Valida que LOCAL_MUTATION é exposta em EXECUTION, mas DANGEROUS segue oculta."""
+        """Valida que LOCAL_MUTATION (incluindo concierge_set_state) é exposta em EXECUTION, mas DANGEROUS segue oculta."""
         self.governor.set_session_state("session_123", "EXECUTION")
 
         filtered = self.governor.filter_tools("session_123", self.live_tools)
         tool_names = {t["name"] for t in filtered}
 
-        self.assertEqual(tool_names, {"get_full_topology", "concierge_search", "concierge_commit"})
+        self.assertEqual(
+            tool_names,
+            {"get_full_topology", "concierge_search", "concierge_set_state", "concierge_commit"},
+        )
         self.assertNotIn("delete_project", tool_names)
         self.assertNotIn("reset_collection", tool_names)
 
@@ -93,6 +146,7 @@ class TestMCPToolGovernor(unittest.TestCase):
             {
                 "get_full_topology",
                 "concierge_search",
+                "concierge_set_state",
                 "concierge_commit",
                 "delete_project",
                 "reset_collection",
@@ -103,11 +157,12 @@ class TestMCPToolGovernor(unittest.TestCase):
         """Valida barreira ativa em validate_tool_execution para PLANNING, EXECUTION e MAINTENANCE."""
         self.governor.set_session_state("session_999", "PLANNING")
         self.assertTrue(self.governor.validate_tool_execution("session_999", "get_full_topology"))
-        for blocked in ("concierge_commit", "delete_project", "reset_collection"):
+        for blocked in ("concierge_set_state", "concierge_commit", "delete_project", "reset_collection"):
             with self.assertRaises(SecurityException):
                 self.governor.validate_tool_execution("session_999", blocked)
 
         self.governor.set_session_state("session_999", "EXECUTION")
+        self.assertTrue(self.governor.validate_tool_execution("session_999", "concierge_set_state"))
         self.assertTrue(self.governor.validate_tool_execution("session_999", "concierge_commit"))
         for dangerous in ("delete_project", "reset_collection"):
             with self.assertRaises(SecurityException):
```

## 4. Etapa C2 — Sessão por Transporte, Allowlist de Parâmetros e `list_tools` (`BL-011`, `BL-013`)

### `git show --stat` (C2)
```text
commit e196005114e2f5c7d9018c642372d632a0af1bf7
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Wed Nov 25 15:09:12 2026 -0300

    fix(security): bind MCP session to transport, reject extra kwargs and filter list_tools (BL-011, BL-013, 4.6-C2)

 interface/mcp_server.py               |  85 ++++++++---
 tests/test_governor_wiring.py         |  77 ++++++----
 tests/test_interface_contracts.py     |   2 -
 tests/test_mcp_security_governance.py | 278 ++++++++++++++++++++++++++++++++++
 4 files changed, 389 insertions(+), 53 deletions(-)
```

### Evidência RED (C2)
```text
FFFFF                                                                    [100%]
================================== FAILURES ===================================
____ test_bl011_ghost_session_id_injection_blocked_even_when_pre_elevated _____

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-516/test_bl011_ghost_session_id_in0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001CCF3DE7100>

    def test_bl011_ghost_session_id_injection_blocked_even_when_pre_elevated(tmp_path, monkeypatch):
        """Exploit BL-011: passar {'session_id': 'bypass_token'} a reset_collection não contorna a sessão ativa."""
        server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="MAINTENANCE")
        try:
            # Mesmo se outra sessão estivesse em MAINTENANCE no governor, a sessão ativa está em EXECUTION
            server.governor.set_session_state("bypass_token", "MAINTENANCE")
    
>           with pytest.raises(SecurityException):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           Failed: DID NOT RAISE SecurityException

tests\test_mcp_security_governance.py:64: Failed
_______ test_bl011_concierge_set_state_signature_ceiling_and_downgrade ________

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-516/test_bl011_concierge_set_state0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001CCF3DE5BA0>

    def test_bl011_concierge_set_state_signature_ceiling_and_downgrade(tmp_path, monkeypatch):
        """concierge_set_state não aceita session_id, respeita teto max_state e permite downgrade."""
        server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
        try:
            tool = server.mcp._tool_manager.get_tool("concierge_set_state")
            assert tool is not None
            props = set((tool.parameters.get("properties") or {}).keys())
>           assert props == {"state_name"}
E           AssertionError: assert {'session_id', 'state_name'} == {'state_name'}
E             
E             Extra items in the left set:
E             'session_id'
E             Use -v to get more diff

tests\test_mcp_security_governance.py:100: AssertionError
_____ test_bl011_extra_undeclared_kwargs_and_malformed_arguments_rejected _____

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-516/test_bl011_extra_undeclared_kw0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001CCF3FC20F0>

    def test_bl011_extra_undeclared_kwargs_and_malformed_arguments_rejected(tmp_path, monkeypatch):
        """Qualquer argumento extra não declarado ou payload não-dict é rejeitado antes do handler."""
        server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING")
        try:
>           with pytest.raises(SecurityException):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           Failed: DID NOT RAISE SecurityException

tests\test_mcp_security_governance.py:154: Failed
_______ test_transport_session_isolation_meta_spoofing_immunity_and_gc ________

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-516/test_transport_session_isolati0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001CCF40D4C00>

    def test_transport_session_isolation_meta_spoofing_immunity_and_gc(tmp_path, monkeypatch):
        """Sessões de transporte distintas ficam isoladas, ignoram _meta.client_id e são coletadas pelo GC."""
        server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
        try:
            sess_a = _DummyTransportSession()
            sess_b = _DummyTransportSession()
    
            # Sessão A faz downgrade para PLANNING (ignorando _meta.client_id forjado)
            tok_a = request_ctx.set(
                RequestContext(
                    request_id="ra",
                    meta=SimpleNamespace(client_id="default"),
                    session=sess_a,
                    lifespan_context=None,
                )
            )
            try:
                res_a = asyncio.run(
                    server.mcp._tool_manager.call_tool("concierge_set_state", {"state_name": "PLANNING"})
                )
                sid_a = res_a["session_id"]
            finally:
                request_ctx.reset(tok_a)
    
            # Sessão B continua em EXECUTION e tenta falsificar _meta.client_id = sid_a
            tok_b = request_ctx.set(
                RequestContext(
                    request_id="rb",
                    meta=SimpleNamespace(client_id=sid_a),
                    session=sess_b,
                    lifespan_context=None,
                )
            )
            try:
                tools_b = asyncio.run(server.mcp.list_tools())
>               assert len(tools_b) == 29
E               AssertionError: assert 31 == 29
E                +  where 31 = len([Tool(name='concierge_register', title=None, description='Registers a new project and defines Privacy Level.', inputSc...t_stateArguments', 'type': 'object'}, outputSchema=None, icons=None, annotations=None, meta=None, execution=None), ...])

tests\test_mcp_security_governance.py:206: AssertionError
______ test_bl013_list_tools_and_lowlevel_handler_always_filter_by_state ______

tmp_path = WindowsPath('C:/Users/guial/AppData/Local/Temp/pytest-of-guial/pytest-516/test_bl013_list_tools_and_lowl0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001CCF3FFE8B0>

    def test_bl013_list_tools_and_lowlevel_handler_always_filter_by_state(tmp_path, monkeypatch):
        """BL-013: server.mcp.list_tools() e ListToolsRequest low-level filtram sempre (17 / 29 / 31)."""
        server, _, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING", max_state="MAINTENANCE")
        try:
            list_handler = server.mcp._mcp_server.request_handlers[types.ListToolsRequest]
            sess = _DummyTransportSession()
    
            # 1. PLANNING (default) -> 17 READ_ONLY apenas
            tools_plan = asyncio.run(server.mcp.list_tools())
            names_plan = {t.name for t in tools_plan}
>           assert len(names_plan) == 17
E           AssertionError: assert 31 == 17
E            +  where 31 = len({'add_reference_wing', 'agent_get_checkpoint', 'agent_list_checkpoints', 'agent_save_checkpoint', 'concierge_commit', 'concierge_feedback', ...})

tests\test_mcp_security_governance.py:239: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_mcp_security_governance.py::test_bl011_ghost_session_id_injection_blocked_even_when_pre_elevated
FAILED tests/test_mcp_security_governance.py::test_bl011_concierge_set_state_signature_ceiling_and_downgrade
FAILED tests/test_mcp_security_governance.py::test_bl011_extra_undeclared_kwargs_and_malformed_arguments_rejected
FAILED tests/test_mcp_security_governance.py::test_transport_session_isolation_meta_spoofing_immunity_and_gc
FAILED tests/test_mcp_security_governance.py::test_bl013_list_tools_and_lowlevel_handler_always_filter_by_state
5 failed in 2.05s
```

### Mutações Obrigatórias (C2)
```text
BASE CHECK exit=0

[KILLED] M1: restaurar arguments.get('session_id', 'default') em governed_call_tool (exit=1)
  2 failed, 7 passed in 10.88s

[KILLED] M2: desabilitar rejeicao de kwargs extras em governed_call_tool (exit=1)
  2 failed, 7 passed in 10.14s

[KILLED] M3a: restaurar bypass sem filtro em governed_list_tools (quando fora de request / sem arg) (exit=1)
  3 failed, 6 passed in 10.60s

[KILLED] M3b: remover re-registro no handler low-level _mcp_server.list_tools() (exit=1)
  1 failed, 8 passed in 10.21s

[KILLED] M4: desabilitar validate_tool_execution em governed_call_tool (exit=1)
  1 failed, 8 passed in 10.42s

RESULTADO MUTACOES C2: TODAS MORTAS (5/5)
```

### Evidência GREEN (`pytest` normal + `--reverse` + `flake8`) (C2)
```text
=== PYTEST NORMAL (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
......................................................                   [100%]
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-318
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-320
  
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
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\_pytest\threadexception.py:54: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-337
  
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
342 passed, 24 warnings in 118.36s (0:01:58)

=== PYTEST REVERSE (exit=0) ===
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
......................................................                   [100%]
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

tests/test_conversational_db.py::test_conversational_tables_creation
  C:\Nexus-Memory\GrafoConcierge\.venv_313\Lib\site-packages\qdrant_client\qdrant_remote.py:295: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
    show_warning(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
342 passed, 24 warnings in 116.15s (0:01:56)

=== FLAKE8 CI (exit=0) ===
0
```

### Secret Scan (C2)
```text
scanned_files=1552
files_with_findings=0
total_pattern_hits=0
```

### CI GitHub Actions (C2)
```text
Stage C2 CI Run (CI): id=45672189497 sha=e196005114e2f5c7d9018c642372d632a0af1bf7 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45672189497
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
Stage C2 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45672189743 sha=e196005114e2f5c7d9018c642372d632a0af1bf7 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45672189743
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
  - Windows (3.12): status=completed conclusion=success
```

### `git diff` Integral (C2)
```diff
diff --git a/interface/mcp_server.py b/interface/mcp_server.py
index c6d1158..dafa7ed 100644
--- a/interface/mcp_server.py
+++ b/interface/mcp_server.py
@@ -39,9 +39,11 @@ from __future__ import annotations
 import functools
 import logging
 import os
+import secrets
 import time
 import traceback
-from typing import Callable, Optional
+import weakref
+from typing import Any, Callable, Optional
 
 from mcp.server.fastmcp import FastMCP
 
@@ -171,6 +173,7 @@ class GrafoConciergeServer:
 
         # Creates the FastMCP server
         self._mcp = FastMCP("Grafo Concierge", host=host, port=port)
+        self._transport_sessions: weakref.WeakKeyDictionary[Any, str] = weakref.WeakKeyDictionary()
 
         # Enables CORS and optional API Key Authentication on Starlette sse_app
         original_sse_app = self._mcp.sse_app
@@ -238,31 +241,74 @@ class GrafoConciergeServer:
         """Access to the active MCPToolGovernor on the server."""
         return self._governor
 
+    def _resolve_transport_session_id(self) -> str:
+        """Resolves a server-side session identifier bound strictly to the MCP transport session."""
+        from core.mcp_governor import SecurityException
+
+        try:
+            req_ctx = self._mcp._mcp_server.request_context
+        except (AttributeError, LookupError):
+            req_ctx = None
+
+        if req_ctx is None:
+            return "default"
+
+        session_obj = getattr(req_ctx, "session", None)
+        if session_obj is None:
+            return "default"
+
+        try:
+            sid = self._transport_sessions.get(session_obj)
+            if sid is None:
+                sid = f"mcp-sess-{secrets.token_hex(16)}"
+                self._transport_sessions[session_obj] = sid
+            return sid
+        except TypeError as exc:
+            raise SecurityException(
+                "Access denied: MCP transport session does not support weak-reference binding."
+            ) from exc
+
     def _setup_tool_governance(self) -> None:
         """Configures FastMCP listing and execution interceptors under MCPToolGovernor."""
+        from core.mcp_governor import SecurityException
+
         original_tm_call_tool = self._mcp._tool_manager.call_tool
 
-        async def governed_call_tool(name: str, arguments: dict, *args, **kwargs):
-            session_id = (
-                arguments.get("session_id", "default")
-                if isinstance(arguments, dict)
-                else "default"
-            )
-            # Second Layer: Active execution validation
+        async def governed_call_tool(name: str, arguments: Any = None, *args, **kwargs):
+            session_id = self._resolve_transport_session_id()
+            if arguments is None:
+                arguments = {}
+            elif not isinstance(arguments, dict):
+                raise SecurityException(
+                    f"Access denied: invalid arguments payload type '{type(arguments).__name__}' for tool '{name}'."
+                )
+
+            # Second Layer: Active execution validation (strictly transport-bound session)
             self._governor.validate_tool_execution(session_id, name)
+
+            # Strict schema parameter allowlist: reject undeclared kwargs before FastMCP silently drops them
+            tool = self._mcp._tool_manager.get_tool(name)
+            if tool is not None:
+                declared = set((tool.parameters or {}).get("properties", {}).keys())
+                extra = sorted(set(arguments.keys()) - declared)
+                if extra:
+                    raise SecurityException(
+                        f"Access denied: undeclared arguments {extra} rejected for tool '{name}'."
+                    )
+
             return await original_tm_call_tool(name, arguments, *args, **kwargs)
 
         self._mcp._tool_manager.call_tool = governed_call_tool
 
         original_mcp_list_tools = self._mcp.list_tools
 
-        async def governed_list_tools(session_id: Optional[str] = None):
+        async def governed_list_tools():
             tools = await original_mcp_list_tools()
-            if session_id:
-                return self._governor.filter_tools(session_id, tools)
-            return tools
+            session_id = self._resolve_transport_session_id()
+            return self._governor.filter_tools(session_id, tools)
 
         self._mcp.list_tools = governed_list_tools
+        self._mcp._mcp_server.list_tools()(governed_list_tools)
 
     # ===================================================================
     # TOOL REGISTRATION
@@ -412,26 +458,25 @@ class GrafoConciergeServer:
         @self._mcp.tool(
             name="concierge_set_state",
             description=(
-                "Transitions agent mental state in MCPToolGovernor between PLANNING, "
-                "EXECUTION, and MAINTENANCE to regulate progressive tool disclosure."
+                "Transitions agent operational state in MCPToolGovernor within configured "
+                "privilege bounds for the active transport session."
             ),
         )
         def concierge_set_state(
             state_name: str,
-            session_id: str = "default",
         ) -> dict:
-            """Transitions session FSM state.
+            """Transitions active transport session operational state.
 
             Args:
                 state_name: Target state (e.g. PLANNING, EXECUTION, MAINTENANCE).
-                session_id: Target session identifier (default: 'default').
             """
+            active_sid = server._resolve_transport_session_id()
             upper_state = state_name.upper()
-            server._governor.set_session_state(session_id, upper_state)
+            server._governor.set_session_state(active_sid, upper_state)
             return {
                 "success": True,
-                "session_id": session_id,
-                "active_state": server._governor.get_session_state(session_id),
+                "session_id": active_sid,
+                "active_state": server._governor.get_session_state(active_sid),
             }
 
         # --- concierge_wakeup ---
diff --git a/tests/test_governor_wiring.py b/tests/test_governor_wiring.py
index f9220f2..fd11d65 100644
--- a/tests/test_governor_wiring.py
+++ b/tests/test_governor_wiring.py
@@ -6,7 +6,7 @@ Testes de fiação e isolamento do MCPToolGovernor no GrafoConciergeServer:
 - T2: construção de GrafoConciergeServer não arrasta archive/nem frameworks web externos,
       conecta ao singleton compartilhado get_shared_governor() e expõe catálogo limpo (31 == 31)
 - T4: governador usa o singleton compartilhado mesmo se telemetry_api falhar no import
-- T5: governed_list_tools filtra ferramentas FastMCP reais por session_id explícito não-"default"
+- T5: governed_list_tools filtra ferramentas FastMCP reais pela sessão ativa do transporte (sem expor catálogo sem filtro)
 """
 import asyncio
 from pathlib import Path
@@ -132,8 +132,9 @@ def test_t4_governor_uses_shared_singleton_when_telemetry_import_fails(tmp_path,
         store.close()
 
 
-def test_t5_governed_list_tools_filters_by_explicit_session_id(tmp_path, monkeypatch):
-    """T5: governed_list_tools aplica filter_tools sobre Tool reais do FastMCP por session_id explícito."""
+def test_t5_governed_list_tools_filters_by_transport_session_state(tmp_path, monkeypatch):
+    """T5: governed_list_tools sempre filtra Tool reais do FastMCP pelo estado da sessão de transporte."""
+    monkeypatch.delenv("GRAFO_DEFAULT_STATE", raising=False)
     monkeypatch.setattr("interface.mcp_server.governor", None)
     monkeypatch.setattr("interface.mcp_server.db_manager", None, raising=False)
     monkeypatch.setattr("interface.mcp_server.checkpointer", None, raising=False)
@@ -147,36 +148,50 @@ def test_t5_governed_list_tools_filters_by_explicit_session_id(tmp_path, monkeyp
         gc._store = store
         server = GrafoConciergeServer(concierge=gc)
 
-        # Sem session_id explícito -> todas as 31 ferramentas registradas
+        # Sem request_ctx ativo -> sessão "default" em PLANNING (17 ferramentas READ_ONLY)
         unscoped = asyncio.run(server.mcp.list_tools())
-        assert len(unscoped) == 31
-
-        # Sessão explícita não-"default" mantendo "default" intocado
-        sid = "sess_wiring_list"
+        assert len(unscoped) == 17
         assert "default" not in server.governor.sessions_state
-        monkeypatch.setattr(server.governor, "max_state", "MAINTENANCE")
 
-        server.governor.set_session_state(sid, "PLANNING")
-        planning_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
-        assert len(planning_names) == 17
-        assert "get_full_topology" in planning_names
-        assert "concierge_set_state" not in planning_names
-        assert "concierge_commit" not in planning_names
-        assert "delete_project" not in planning_names
-        assert "reset_collection" not in planning_names
-
-        server.governor.set_session_state(sid, "EXECUTION")
-        exec_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
-        assert len(exec_names) == 29
-        assert "concierge_set_state" in exec_names
-        assert "concierge_commit" in exec_names
-        assert "delete_project" not in exec_names
-        assert "reset_collection" not in exec_names
-
-        server.governor.set_session_state(sid, "MAINTENANCE")
-        maint_names = {t.name for t in asyncio.run(server.mcp.list_tools(session_id=sid))}
-        assert len(maint_names) == 31
-        assert {"delete_project", "reset_collection"}.issubset(maint_names)
-        assert "default" not in server.governor.sessions_state
+        # Em request_ctx com sessão de transporte dedicada -> "default" segue intocado
+        from mcp.server.lowlevel.server import request_ctx
+        from mcp.shared.context import RequestContext
+
+        class _Sess:
+            pass
+
+        sess = _Sess()
+        monkeypatch.setattr(server.governor, "max_state", "MAINTENANCE")
+        tok = request_ctx.set(
+            RequestContext(request_id="t5", meta=None, session=sess, lifespan_context=None)
+        )
+        try:
+            sid = server._resolve_transport_session_id()
+            assert sid != "default"
+
+            server.governor.set_session_state(sid, "PLANNING")
+            planning_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
+            assert len(planning_names) == 17
+            assert "get_full_topology" in planning_names
+            assert "concierge_set_state" not in planning_names
+            assert "concierge_commit" not in planning_names
+            assert "delete_project" not in planning_names
+            assert "reset_collection" not in planning_names
+
+            server.governor.set_session_state(sid, "EXECUTION")
+            exec_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
+            assert len(exec_names) == 29
+            assert "concierge_set_state" in exec_names
+            assert "concierge_commit" in exec_names
+            assert "delete_project" not in exec_names
+            assert "reset_collection" not in exec_names
+
+            server.governor.set_session_state(sid, "MAINTENANCE")
+            maint_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
+            assert len(maint_names) == 31
+            assert {"delete_project", "reset_collection"}.issubset(maint_names)
+            assert "default" not in server.governor.sessions_state
+        finally:
+            request_ctx.reset(tok)
     finally:
         store.close()
diff --git a/tests/test_interface_contracts.py b/tests/test_interface_contracts.py
index 9a4de75..a5a0869 100644
--- a/tests/test_interface_contracts.py
+++ b/tests/test_interface_contracts.py
@@ -309,7 +309,6 @@ class TestMCPToolRegistration:
             # 2. Transition session state to MAINTENANCE and exercise lightweight-safe tools
             server.governor.max_state = "MAINTENANCE"
             server.governor.set_session_state("default", "MAINTENANCE")
-            server.governor.set_session_state("sess_contract_maint", "MAINTENANCE")
             assert server.governor.get_session_state("default") == "MAINTENANCE"
 
             status_res = call_governed("concierge_status", {})
@@ -444,7 +443,6 @@ class TestMCPToolRegistration:
             assert len(list_cp_res) >= 1
         finally:
             server.governor.max_state = orig_max_state
-            server.governor.sessions_state.pop("sess_contract_maint", None)
             if had_default:
                 server.governor.sessions_state["default"] = orig_default
             else:
diff --git a/tests/test_mcp_security_governance.py b/tests/test_mcp_security_governance.py
new file mode 100644
index 0000000..49e2bb6
--- /dev/null
+++ b/tests/test_mcp_security_governance.py
@@ -0,0 +1,278 @@
+"""
+tests/test_mcp_security_governance.py — Testes adversariais e de regressão para BL-011 e BL-013 (Rodada 4.6-C2).
+
+Valida:
+  - BL-011: fechamento de injeção de `session_id` fantasma, remoção de `session_id` em
+    `concierge_set_state`, rejeição de argumentos extras não declarados e de payload não-dict,
+    vinculação da sessão ao objeto `session` do transporte MCP (WeakKeyDictionary),
+    e resistência a spoofing via `_meta.client_id`.
+  - BL-013: filtragem obrigatória de `list_tools()` e do handler low-level `ListToolsRequest`
+    do servidor MCP em `PLANNING` (17), `EXECUTION` (29) e `MAINTENANCE` (31).
+"""
+
+from __future__ import annotations
+
+import asyncio
+import gc as py_gc
+from types import SimpleNamespace
+from unittest.mock import MagicMock
+
+import mcp.types as types
+from mcp.server.fastmcp.exceptions import ToolError
+from mcp.server.lowlevel.server import request_ctx
+from mcp.shared.context import RequestContext
+import pytest
+
+from core.mcp_governor import MCPToolGovernor, SecurityException
+import interface.mcp_server as mcp_server_mod
+from interface.mcp_server import GrafoConciergeServer
+from storage.store import SqliteStore
+
+
+class _DummyTransportSession:
+    """Sessão MCP simulada com suporte a weakref (como mcp.server.session.ServerSession)."""
+
+
+class _NonWeakrefSession:
+    __slots__ = ()
+
+
+def _make_server(tmp_path, monkeypatch, default_state: str = "PLANNING", max_state: str | None = None):
+    monkeypatch.setattr(mcp_server_mod, "governor", None)
+    monkeypatch.setattr(mcp_server_mod, "db_manager", None)
+    monkeypatch.setattr(mcp_server_mod, "checkpointer", None)
+    monkeypatch.setattr(mcp_server_mod, "graph_rag", None)
+    gov = MCPToolGovernor(default_state=default_state, max_state=max_state)
+    monkeypatch.setattr("core.mcp_governor._shared_governor", gov)
+
+    store = SqliteStore(str(tmp_path / f"sec_{default_state}.db"))
+    gc_facade = MagicMock()
+    gc_facade.config = None
+    gc_facade._store = store
+    gc_facade.reset_collection = MagicMock(return_value=True)
+    gc_facade.status = MagicMock(return_value={"status": "ok"})
+    server = GrafoConciergeServer(concierge=gc_facade)
+    return server, gc_facade, store
+
+
+def test_bl011_ghost_session_id_injection_blocked_even_when_pre_elevated(tmp_path, monkeypatch):
+    """Exploit BL-011: passar {'session_id': 'bypass_token'} a reset_collection não contorna a sessão ativa."""
+    server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="MAINTENANCE")
+    try:
+        # Mesmo se outra sessão estivesse em MAINTENANCE no governor, a sessão ativa está em EXECUTION
+        server.governor.set_session_state("bypass_token", "MAINTENANCE")
+
+        with pytest.raises(SecurityException):
+            asyncio.run(
+                server.mcp._tool_manager.call_tool("reset_collection", {"session_id": "bypass_token"})
+            )
+        gc_facade.reset_collection.assert_not_called()
+
+        # Mesmo em protocolo CallToolRequest real (low-level server retorna CallToolResult isError=True)
+        call_handler = server.mcp._mcp_server.request_handlers[types.CallToolRequest]
+        req = types.CallToolRequest(
+            method="tools/call",
+            params=types.CallToolRequestParams(
+                name="reset_collection",
+                arguments={"session_id": "bypass_token"},
+            ),
+        )
+        sess = _DummyTransportSession()
+        tok = request_ctx.set(
+            RequestContext(request_id="req-1", meta=None, session=sess, lifespan_context=None)
+        )
+        try:
+            res = asyncio.run(call_handler(req))
+        finally:
+            request_ctx.reset(tok)
+        assert res.root.isError is True
+        gc_facade.reset_collection.assert_not_called()
+    finally:
+        store.close()
+
+
+def test_bl011_concierge_set_state_signature_ceiling_and_downgrade(tmp_path, monkeypatch):
+    """concierge_set_state não aceita session_id, respeita teto max_state e permite downgrade."""
+    server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
+    try:
+        tool = server.mcp._tool_manager.get_tool("concierge_set_state")
+        assert tool is not None
+        props = set((tool.parameters.get("properties") or {}).keys())
+        assert props == {"state_name"}
+
+        sess = _DummyTransportSession()
+        tok = request_ctx.set(
+            RequestContext(request_id="req-set", meta=None, session=sess, lifespan_context=None)
+        )
+        try:
+            # Tentar passar session_id extra deve ser rejeitado com SecurityException
+            with pytest.raises(SecurityException):
+                asyncio.run(
+                    server.mcp._tool_manager.call_tool(
+                        "concierge_set_state",
+                        {"state_name": "EXECUTION", "session_id": "other_sess"},
+                    )
+                )
+
+            # Tentar escalar acima do teto EXECUTION -> MAINTENANCE bloqueado
+            with pytest.raises((SecurityException, ToolError)) as exc_up:
+                asyncio.run(
+                    server.mcp._tool_manager.call_tool(
+                        "concierge_set_state",
+                        {"state_name": "MAINTENANCE"},
+                    )
+                )
+            err_up = exc_up.value
+            if isinstance(err_up, ToolError):
+                assert isinstance(err_up.__cause__, SecurityException)
+
+            # Downgrade EXECUTION -> PLANNING permitido na sessão de transporte ativa
+            down = asyncio.run(
+                server.mcp._tool_manager.call_tool(
+                    "concierge_set_state",
+                    {"state_name": "PLANNING"},
+                )
+            )
+            assert down["success"] is True
+            assert down["active_state"] == "PLANNING"
+            assert down["session_id"] != "default"
+
+            # Agora em PLANNING, concierge_set_state (LOCAL_MUTATION) está bloqueada
+            with pytest.raises(SecurityException):
+                asyncio.run(
+                    server.mcp._tool_manager.call_tool(
+                        "concierge_set_state",
+                        {"state_name": "EXECUTION"},
+                    )
+                )
+        finally:
+            request_ctx.reset(tok)
+    finally:
+        store.close()
+
+
+def test_bl011_extra_undeclared_kwargs_and_malformed_arguments_rejected(tmp_path, monkeypatch):
+    """Qualquer argumento extra não declarado ou payload não-dict é rejeitado antes do handler."""
+    server, gc_facade, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING")
+    try:
+        with pytest.raises(SecurityException):
+            asyncio.run(
+                server.mcp._tool_manager.call_tool("concierge_status", {"extra_injected": "x"})
+            )
+        gc_facade.status.assert_not_called()
+
+        with pytest.raises(SecurityException):
+            asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", "not-a-dict"))
+        gc_facade.status.assert_not_called()
+
+        # arguments=None é normalizado para {} e funciona em READ_ONLY
+        ok = asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", None))
+        assert ok["success"] is True
+    finally:
+        store.close()
+
+
+def test_transport_session_isolation_meta_spoofing_immunity_and_gc(tmp_path, monkeypatch):
+    """Sessões de transporte distintas ficam isoladas, ignoram _meta.client_id e são coletadas pelo GC."""
+    server, _, store = _make_server(tmp_path, monkeypatch, default_state="EXECUTION", max_state="EXECUTION")
+    try:
+        sess_a = _DummyTransportSession()
+        sess_b = _DummyTransportSession()
+
+        # Sessão A faz downgrade para PLANNING (ignorando _meta.client_id forjado)
+        tok_a = request_ctx.set(
+            RequestContext(
+                request_id="ra",
+                meta=SimpleNamespace(client_id="default"),
+                session=sess_a,
+                lifespan_context=None,
+            )
+        )
+        try:
+            res_a = asyncio.run(
+                server.mcp._tool_manager.call_tool("concierge_set_state", {"state_name": "PLANNING"})
+            )
+            sid_a = res_a["session_id"]
+        finally:
+            request_ctx.reset(tok_a)
+
+        # Sessão B continua em EXECUTION e tenta falsificar _meta.client_id = sid_a
+        tok_b = request_ctx.set(
+            RequestContext(
+                request_id="rb",
+                meta=SimpleNamespace(client_id=sid_a),
+                session=sess_b,
+                lifespan_context=None,
+            )
+        )
+        try:
+            tools_b = asyncio.run(server.mcp.list_tools())
+            assert len(tools_b) == 29
+        finally:
+            request_ctx.reset(tok_b)
+
+        assert len(server._transport_sessions) == 2
+        del sess_a
+        py_gc.collect()
+        assert len(server._transport_sessions) == 1
+
+        # Sessão não-weakref falha fechado
+        non_weak = _NonWeakrefSession()
+        tok_nw = request_ctx.set(
+            RequestContext(request_id="rnw", meta=None, session=non_weak, lifespan_context=None)
+        )
+        try:
+            with pytest.raises(SecurityException):
+                asyncio.run(server.mcp._tool_manager.call_tool("concierge_status", {}))
+        finally:
+            request_ctx.reset(tok_nw)
+    finally:
+        store.close()
+
+
+def test_bl013_list_tools_and_lowlevel_handler_always_filter_by_state(tmp_path, monkeypatch):
+    """BL-013: server.mcp.list_tools() e ListToolsRequest low-level filtram sempre (17 / 29 / 31)."""
+    server, _, store = _make_server(tmp_path, monkeypatch, default_state="PLANNING", max_state="MAINTENANCE")
+    try:
+        list_handler = server.mcp._mcp_server.request_handlers[types.ListToolsRequest]
+        sess = _DummyTransportSession()
+
+        # 1. PLANNING (default) -> 17 READ_ONLY apenas
+        tools_plan = asyncio.run(server.mcp.list_tools())
+        names_plan = {t.name for t in tools_plan}
+        assert len(names_plan) == 17
+        assert not (names_plan & {"reset_collection", "delete_project", "concierge_commit", "concierge_set_state"})
+
+        tok = request_ctx.set(
+            RequestContext(request_id="r-list", meta=None, session=sess, lifespan_context=None)
+        )
+        try:
+            low_plan = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
+            assert {t.name for t in low_plan.root.tools} == names_plan
+            # Chamada interna de cache miss passa req=None
+            low_none = asyncio.run(list_handler(None))
+            assert len(low_none.root.tools) == 17
+
+            # 2. EXECUTION na sessão ativa -> 29 tools (sem DANGEROUS)
+            sid = server._resolve_transport_session_id()
+            server.governor.set_session_state(sid, "EXECUTION")
+            assert len(asyncio.run(server.mcp.list_tools())) == 29
+            low_exec = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
+            exec_names = {t.name for t in low_exec.root.tools}
+            assert len(exec_names) == 29
+            assert "concierge_commit" in exec_names
+            assert "concierge_set_state" in exec_names
+            assert "delete_project" not in exec_names
+            assert "reset_collection" not in exec_names
+
+            # 3. MAINTENANCE na sessão ativa -> 31 tools
+            server.governor.set_session_state(sid, "MAINTENANCE")
+            assert len(asyncio.run(server.mcp.list_tools())) == 31
+            low_maint = asyncio.run(list_handler(types.ListToolsRequest(method="tools/list")))
+            maint_names = {t.name for t in low_maint.root.tools}
+            assert len(maint_names) == 31
+            assert {"delete_project", "reset_collection"}.issubset(maint_names)
+        finally:
+            request_ctx.reset(tok)
+    finally:
+        store.close()
```

## 5. Etapa C3 — Posse Persistente `owner_hash` em Checkpoints (`BL-012`)

### `git show --stat` (C3)
```text
commit 79afa2cca2abd4241742eecf1fbc75018e796cd4
Author: LuisinTheLegend <luisfilipe.lfal@gmail.com>
Date:   Wed Nov 25 15:36:39 2026 -0300

    fix(security): enforce persistent owner_hash verification on agent checkpoints (BL-012, 4.6-C3)

 core/checkpointer.py               |  91 +++++++-
 interface/mcp_server.py            | 120 ++++++++++-
 main.py                            |   2 +-
 storage/schema.py                  |  11 +
 tests/test_checkpoint_ownership.py | 432 +++++++++++++++++++++++++++++++++++++
 5 files changed, 641 insertions(+), 15 deletions(-)
```

### Evidência RED (C3)
```text
��F F F F F                                                                                                                                         [ 1 0 0 % ] 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   F A I L U R E S   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 _ _ _ _ _ _ _ _   t e s t _ d i r e c t _ c h e c k p o i n t e r _ b l o c k s _ a l l _ f o u r _ c r o s s _ o w n e r _ v e c t o r s   _ _ _ _ _ _ _ _ _ 
 
 
 
 t m p _ p a t h   =   W i n d o w s P a t h ( ' C : / U s e r s / g u i a l / A p p D a t a / L o c a l / T e m p / p y t e s t - o f - g u i a l / p y t e s t - 5 2 9 / t e s t _ d i r e c t _ c h e c k p o i n t e r _ b l o c k 0 ' ) 
 
 
 
         d e f   t e s t _ d i r e c t _ c h e c k p o i n t e r _ b l o c k s _ a l l _ f o u r _ c r o s s _ o w n e r _ v e c t o r s ( t m p _ p a t h ) : 
 
                 " " " B l o q u e i a   g e t ,   l i s t ,   o v e r w r i t e   e   i n j e � � o   d e   n o v o   c h e c k p o i n t _ i d   e m   n a m e s p a c e   a l h e i o . " " " 
 
                 d b _ p a t h   =   t m p _ p a t h   /   " b l 0 1 2 _ d i r e c t . d b " 
 
                 s t o r e ,   _ ,   c p   =   _ m a k e _ d b _ a n d _ c p ( d b _ p a t h ) 
 
                 t r y : 
 
                         v i c t i m _ t o k   =   " t e s t - o w n e r - t o k e n - v i c t i m - a l p h a " 
 
                         a t t a c k e r _ t o k   =   " t e s t - o w n e r - t o k e n - a t t a c k e r - b e t a " 
 
         
 
                         o k ,   e r r   =   c p . s a v e _ c h e c k p o i n t _ d e t a i l e d ( 
 
                                 " a g - 1 " ,   " s e s s - 1 " ,   " c p - 1 " ,   { " s e c r e t " :   " c l a s s i f i e d " } ,   o w n e r _ t o k e n = v i c t i m _ t o k 
 
                         ) 
 
                         a s s e r t   ( o k ,   e r r )   = =   ( T r u e ,   N o n e ) 
 
         
 
                         #   D o n o   l e g � t i m o   a c e s s a   n o r m a l m e n t e 
 
 >                       a s s e r t   c p . g e t _ c h e c k p o i n t ( " a g - 1 " ,   " s e s s - 1 " ,   " c p - 1 " ,   o w n e r _ t o k e n = v i c t i m _ t o k )   = =   { 
 
                                       ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
                                 " s e c r e t " :   " c l a s s i f i e d " 
 
                         } 
 
 E                       T y p e E r r o r :   A g n o s t i c C h e c k p o i n t e r . g e t _ c h e c k p o i n t ( )   g o t   a n   u n e x p e c t e d   k e y w o r d   a r g u m e n t   ' o w n e r _ t o k e n ' 
 
 
 
 t e s t s \ t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : 8 7 :   T y p e E r r o r 
 
 _ _ _ _ _ _ _   t e s t _ o w n e r s h i p _ p e r s i s t s _ a c r o s s _ r e s t a r t _ a n d _ n e v e r _ l e a k s _ s e c r e t s   _ _ _ _ _ _ _ _ 
 
 
 
 t m p _ p a t h   =   W i n d o w s P a t h ( ' C : / U s e r s / g u i a l / A p p D a t a / L o c a l / T e m p / p y t e s t - o f - g u i a l / p y t e s t - 5 2 9 / t e s t _ o w n e r s h i p _ p e r s i s t s _ a c r o s s 0 ' ) 
 
 m o n k e y p a t c h   =   < _ p y t e s t . m o n k e y p a t c h . M o n k e y P a t c h   o b j e c t   a t   0 x 0 0 0 0 0 2 2 D 9 C 1 7 5 B A 0 > 
 
 
 
         d e f   t e s t _ o w n e r s h i p _ p e r s i s t s _ a c r o s s _ r e s t a r t _ a n d _ n e v e r _ l e a k s _ s e c r e t s ( t m p _ p a t h ,   m o n k e y p a t c h ) : 
 
                 " " " P o s s e   s o b r e v i v e   a o   r e s t a r t   e m   S Q L i t e ,   g r a v a   a p e n a s   S H A - 2 5 6   h e x   e   r e d i g e   e n v   v a r . " " " 
 
                 d b _ p a t h   =   t m p _ p a t h   /   " b l 0 1 2 _ r e s t a r t . d b " 
 
                 v i c t i m _ t o k   =   " t e s t - o w n e r - t o k e n - p e r s i s t e n t - v 1 " 
 
                 a t t a c k e r _ t o k   =   " t e s t - o w n e r - t o k e n - p e r s i s t e n t - v 2 " 
 
                 e x p e c t e d _ h a s h   =   h a s h l i b . s h a 2 5 6 ( v i c t i m _ t o k . e n c o d e ( " u t f - 8 " ) ) . h e x d i g e s t ( ) 
 
         
 
                 s t o r e 1 ,   _ ,   c p 1   =   _ m a k e _ d b _ a n d _ c p ( d b _ p a t h ) 
 
                 t r y : 
 
                         s t a t e _ b e f o r e   =   d i c t ( v a r s ( c p 1 ) ) 
 
                         o k ,   e r r   =   c p 1 . s a v e _ c h e c k p o i n t _ d e t a i l e d ( 
 
                                 " a g - r " ,   " s e s s - r " ,   " c p - r " ,   { " s t e p " :   1 0 } ,   o w n e r _ t o k e n = v i c t i m _ t o k 
 
                         ) 
 
                         a s s e r t   ( o k ,   e r r )   = =   ( T r u e ,   N o n e ) 
 
                         a s s e r t   v a r s ( c p 1 )   = =   s t a t e _ b e f o r e 
 
                 f i n a l l y : 
 
                         s t o r e 1 . c l o s e ( ) 
 
         
 
                 #   V e r i f i c a r   d i r e t o   n o   S Q L i t e   q u e   p l a i n t e x t   n � o   f o i   s a l v o   e   a p e n a s   o   h a s h   S H A - 2 5 6   e x i s t e 
 
                 w i t h   s q l i t e 3 . c o n n e c t ( s t r ( d b _ p a t h ) )   a s   c o n n : 
 
 >                       r o w   =   c o n n . e x e c u t e ( 
 
                                 " S E L E C T   o w n e r _ h a s h   F R O M   a g e n t _ c h e c k p o i n t s   W H E R E   a g e n t _ i d = ' a g - r '   A N D   s e s s i o n _ i d = ' s e s s - r '   A N D   c h e c k p o i n t _ i d = ' c p - r ' " 
 
                         ) . f e t c h o n e ( ) 
 
 E                       s q l i t e 3 . O p e r a t i o n a l E r r o r :   n o   s u c h   c o l u m n :   o w n e r _ h a s h 
 
 
 
 t e s t s \ t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : 1 6 3 :   O p e r a t i o n a l E r r o r 
 
 _ _   t e s t _ l e g a c y _ f i v e _ c o l u m n _ s c h e m a _ m i g r a t e s _ o n _ s t o r e _ b o o t _ a n d _ i s _ f a i l _ c l o s e d   _ _ _ 
 
 
 
 t m p _ p a t h   =   W i n d o w s P a t h ( ' C : / U s e r s / g u i a l / A p p D a t a / L o c a l / T e m p / p y t e s t - o f - g u i a l / p y t e s t - 5 2 9 / t e s t _ l e g a c y _ f i v e _ c o l u m n _ s c h e m a 0 ' ) 
 
 
 
         d e f   t e s t _ l e g a c y _ f i v e _ c o l u m n _ s c h e m a _ m i g r a t e s _ o n _ s t o r e _ b o o t _ a n d _ i s _ f a i l _ c l o s e d ( t m p _ p a t h ) : 
 
                 " " " M i g r a   t a b e l a   l e g a d a   d e   5   c o l u n a s   n o   b o o t   d o   S q l i t e S t o r e   s e m   p e r d e r   d a d o s   e   s e m   a d o � � o   s i l e n c i o s a . " " " 
 
                 d b _ p a t h   =   t m p _ p a t h   /   " b l 0 1 2 _ l e g a c y . d b " 
 
                 w i t h   s q l i t e 3 . c o n n e c t ( s t r ( d b _ p a t h ) )   a s   c o n n : 
 
                         c o n n . e x e c u t e ( 
 
                                 " C R E A T E   T A B L E   a g e n t _ c h e c k p o i n t s   ( " 
 
                                 " a g e n t _ i d   T E X T   N O T   N U L L ,   " 
 
                                 " s e s s i o n _ i d   T E X T   N O T   N U L L ,   " 
 
                                 " c h e c k p o i n t _ i d   T E X T   N O T   N U L L ,   " 
 
                                 " s t a t e _ b l o b   T E X T   N O T   N U L L ,   " 
 
                                 " c r e a t e d _ a t   T I M E S T A M P   D E F A U L T   C U R R E N T _ T I M E S T A M P ,   " 
 
                                 " P R I M A R Y   K E Y   ( a g e n t _ i d ,   s e s s i o n _ i d ,   c h e c k p o i n t _ i d ) " 
 
                                 " ) ; " 
 
                         ) 
 
                         c o n n . e x e c u t e ( 
 
                                 " I N S E R T   I N T O   a g e n t _ c h e c k p o i n t s   ( a g e n t _ i d ,   s e s s i o n _ i d ,   c h e c k p o i n t _ i d ,   s t a t e _ b l o b )   " 
 
                                 " V A L U E S   ( ' l e g a c y _ a g ' ,   ' l e g a c y _ s e s s ' ,   ' l e g a c y _ c p ' ,   ' { \ " s t e p \ " :   4 2 } ' ) ; " 
 
                         ) 
 
                         c o n n . c o m m i t ( ) 
 
         
 
                 #   B o o t   a p e n a s   d o   S q l i t e S t o r e   ( s e m   i n s t a n c i a r   A g n o s t i c C h e c k p o i n t e r   a n t e s ) 
 
                 s t o r e 1   =   S q l i t e S t o r e ( s t r ( d b _ p a t h ) ) 
 
                 s t o r e 1 . c l o s e ( ) 
 
         
 
                 w i t h   s q l i t e 3 . c o n n e c t ( s t r ( d b _ p a t h ) )   a s   c o n n : 
 
                         c o l s   =   { r o w [ 1 ] :   r o w   f o r   r o w   i n   c o n n . e x e c u t e ( " P R A G M A   t a b l e _ i n f o ( a g e n t _ c h e c k p o i n t s ) " ) . f e t c h a l l ( ) } 
 
 >                       a s s e r t   " o w n e r _ h a s h "   i n   c o l s 
 
 E                       A s s e r t i o n E r r o r :   a s s e r t   ' o w n e r _ h a s h '   i n   { ' a g e n t _ i d ' :   ( 0 ,   ' a g e n t _ i d ' ,   ' T E X T ' ,   1 ,   N o n e ,   1 ) ,   ' s e s s i o n _ i d ' :   ( 1 ,   ' s e s s i o n _ i d ' ,   ' T E X T ' ,   1 ,   N o n e ,   2 ) ,   ' c h e c k p o i n t _ i d ' :   ( 2 ,   ' c h e c k p o i n t _ i d ' ,   ' T E X T ' ,   1 ,   N o n e ,   3 ) ,   ' s t a t e _ b l o b ' :   ( 3 ,   ' s t a t e _ b l o b ' ,   ' T E X T ' ,   1 ,   N o n e ,   0 ) ,   . . . } 
 
 
 
 t e s t s \ t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : 2 1 7 :   A s s e r t i o n E r r o r 
 
 _ _ _ _ _ _ _ _ _ _ _ _ _   t e s t _ m c p _ s t d i o _ e n v _ a n d _ e p h e m e r a l _ s e s s i o n _ i s o l a t i o n   _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
 
 
 
 t m p _ p a t h   =   W i n d o w s P a t h ( ' C : / U s e r s / g u i a l / A p p D a t a / L o c a l / T e m p / p y t e s t - o f - g u i a l / p y t e s t - 5 2 9 / t e s t _ m c p _ s t d i o _ e n v _ a n d _ e p h e m e r 0 ' ) 
 
 m o n k e y p a t c h   =   < _ p y t e s t . m o n k e y p a t c h . M o n k e y P a t c h   o b j e c t   a t   0 x 0 0 0 0 0 2 2 D 9 C 3 2 0 6 4 0 > 
 
 
 
         d e f   t e s t _ m c p _ s t d i o _ e n v _ a n d _ e p h e m e r a l _ s e s s i o n _ i s o l a t i o n ( t m p _ p a t h ,   m o n k e y p a t c h ) : 
 
                 " " " s t d i o   u s a   G R A F O _ A G E N T _ T O K E N   q u a n d o   d e f i n i d o   o u   s e g r e d o   e f � m e r o   p o r   S e r v e r S e s s i o n . " " " 
 
                 d b _ p a t h   =   t m p _ p a t h   /   " b l 0 1 2 _ m c p _ s t d i o . d b " 
 
         
 
                 #   C a s o   1 :   G R A F O _ A G E N T _ T O K E N   d e f i n i d o   e m   s t d i o   ( p e r s i s t e   e n t r e   i n s t � n c i a s   d e   s e r v i d o r ) 
 
                 m o n k e y p a t c h . s e t e n v ( " G R A F O _ A G E N T _ T O K E N " ,   " t e s t - s t d i o - o w n e r - t o k e n - a l p h a " ) 
 
                 s r v _ o w n e r ,   s t o r e _ o w n e r   =   _ m a k e _ s e r v e r ( d b _ p a t h ,   m o n k e y p a t c h ,   d e f a u l t _ s t a t e = " E X E C U T I O N " ) 
 
                 t r y : 
 
                         s e s s _ a   =   D u m m y T r a n s p o r t S e s s i o n ( " s t d i o - A " ) 
 
                         s a v e _ r e s   =   _ c a l l _ w i t h _ r e q _ c t x ( 
 
                                 s r v _ o w n e r , 
 
                                 s e s s _ a , 
 
                                 N o n e , 
 
                                 " a g e n t _ s a v e _ c h e c k p o i n t " , 
 
                                 { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 1 " ,   " s t a t e _ d i c t " :   { " o k " :   1 } } , 
 
                         ) 
 
                         p a y l o a d   =   j s o n . l o a d s ( s a v e _ r e s )   i f   i s i n s t a n c e ( s a v e _ r e s ,   s t r )   e l s e   s a v e _ r e s 
 
                         a s s e r t   p a y l o a d [ " s u c c e s s " ]   i s   T r u e 
 
         
 
                         #   T e n t a t i v a   d e   p a s s a r   o w n e r _ t o k e n   f o r j a d o   c o m o   a r g u m e n t o   d e v e   s e r   r e j e i t a d a   p e l o   g o v e r n o r 
 
                         w i t h   p y t e s t . r a i s e s ( S e c u r i t y E x c e p t i o n ) : 
 
                                 _ c a l l _ w i t h _ r e q _ c t x ( 
 
                                         s r v _ o w n e r , 
 
                                         s e s s _ a , 
 
                                         N o n e , 
 
                                         " a g e n t _ s a v e _ c h e c k p o i n t " , 
 
                                         { 
 
                                                 " a g e n t _ i d " :   " m c p _ a g " , 
 
                                                 " s e s s i o n _ i d " :   " m c p _ s 1 " , 
 
                                                 " c h e c k p o i n t _ i d " :   " c p 1 " , 
 
                                                 " s t a t e _ d i c t " :   { " o k " :   2 } , 
 
                                                 " o w n e r _ t o k e n " :   " f o r g e d " , 
 
                                         } , 
 
                                 ) 
 
                 f i n a l l y : 
 
                         s t o r e _ o w n e r . c l o s e ( ) 
 
         
 
                 #   N o v o   s e r v i d o r   c o m   m e s m o   t o k e n   ( s i m u l a n d o   r e s t a r t )   r e c u p e r a   n o r m a l m e n t e 
 
                 s r v _ r e s t a r t ,   s t o r e _ r e s t a r t   =   _ m a k e _ s e r v e r ( d b _ p a t h ,   m o n k e y p a t c h ,   d e f a u l t _ s t a t e = " E X E C U T I O N " ) 
 
                 t r y : 
 
                         a s s e r t   _ c a l l _ w i t h _ r e q _ c t x ( 
 
                                 s r v _ r e s t a r t , 
 
                                 D u m m y T r a n s p o r t S e s s i o n ( " s t d i o - A 2 " ) , 
 
                                 N o n e , 
 
                                 " a g e n t _ g e t _ c h e c k p o i n t " , 
 
                                 { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 1 " } , 
 
                         )   = =   { " o k " :   1 } 
 
                 f i n a l l y : 
 
                         s t o r e _ r e s t a r t . c l o s e ( ) 
 
         
 
                 #   N o v o   s e r v i d o r   c o m   o u t r o   G R A F O _ A G E N T _ T O K E N   d e v e   s e r   b l o q u e a d o   e m   g e t ,   l i s t ,   o v e r w r i t e   e   i n j e � � o 
 
                 m o n k e y p a t c h . s e t e n v ( " G R A F O _ A G E N T _ T O K E N " ,   " t e s t - s t d i o - o w n e r - t o k e n - b e t a " ) 
 
                 s r v _ a t t a c k e r ,   s t o r e _ a t t a c k e r   =   _ m a k e _ s e r v e r ( d b _ p a t h ,   m o n k e y p a t c h ,   d e f a u l t _ s t a t e = " E X E C U T I O N " ) 
 
                 t r y : 
 
                         s e s s _ b   =   D u m m y T r a n s p o r t S e s s i o n ( " s t d i o - B " ) 
 
                         f o r   t o o l _ n a m e ,   t o o l _ a r g s   i n   ( 
 
                                 ( " a g e n t _ g e t _ c h e c k p o i n t " ,   { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 1 " } ) , 
 
                                 ( " a g e n t _ l i s t _ c h e c k p o i n t s " ,   { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " } ) , 
 
                                 ( " a g e n t _ s a v e _ c h e c k p o i n t " ,   { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 1 " ,   " s t a t e _ d i c t " :   { " h a c k " :   1 } } ) , 
 
                                 ( " a g e n t _ s a v e _ c h e c k p o i n t " ,   { " a g e n t _ i d " :   " m c p _ a g " ,   " s e s s i o n _ i d " :   " m c p _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 2 " ,   " s t a t e _ d i c t " :   { " h a c k " :   2 } } ) , 
 
                         ) : 
 
 >                               w i t h   p y t e s t . r a i s e s ( ( P e r m i s s i o n E r r o r ,   T o o l E r r o r ) )   a s   e x c _ i n f o : 
 
                                           ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
 E                               F a i l e d :   D I D   N O T   R A I S E   a n y   o f   ( P e r m i s s i o n E r r o r ,   T o o l E r r o r ) 
 
 
 
 t e s t s \ t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : 3 0 7 :   F a i l e d 
 
 _ _ _ _ _ _ _ _ _ _   t e s t _ m c p _ h t t p _ s s e _ h e a d e r _ p r e c e d e n c e _ b e a r e r _ a n d _ e p h e m e r a l   _ _ _ _ _ _ _ _ _ _ _ 
 
 
 
 t m p _ p a t h   =   W i n d o w s P a t h ( ' C : / U s e r s / g u i a l / A p p D a t a / L o c a l / T e m p / p y t e s t - o f - g u i a l / p y t e s t - 5 2 9 / t e s t _ m c p _ h t t p _ s s e _ h e a d e r _ p r e c e 0 ' ) 
 
 m o n k e y p a t c h   =   < _ p y t e s t . m o n k e y p a t c h . M o n k e y P a t c h   o b j e c t   a t   0 x 0 0 0 0 0 2 2 D 9 C 3 1 5 0 1 0 > 
 
 
 
         d e f   t e s t _ m c p _ h t t p _ s s e _ h e a d e r _ p r e c e d e n c e _ b e a r e r _ a n d _ e p h e m e r a l ( t m p _ p a t h ,   m o n k e y p a t c h ) : 
 
                 " " " H T T P / S S E   r e s o l v e   X - G r a f o - A g e n t - T o k e n   >   A u t h o r i z a t i o n :   B e a r e r   >   s e g r e d o   e f � m e r o   d a   s e s s � o . " " " 
 
                 d b _ p a t h   =   t m p _ p a t h   /   " b l 0 1 2 _ m c p _ s s e . d b " 
 
                 m o n k e y p a t c h . d e l e n v ( " G R A F O _ A G E N T _ T O K E N " ,   r a i s i n g = F a l s e ) 
 
         
 
                 s e r v e r ,   s t o r e   =   _ m a k e _ s e r v e r ( d b _ p a t h ,   m o n k e y p a t c h ,   d e f a u l t _ s t a t e = " E X E C U T I O N " ) 
 
                 t r y : 
 
                         s e s s 1   =   D u m m y T r a n s p o r t S e s s i o n ( " s s e - 1 " ) 
 
                         s e s s 2   =   D u m m y T r a n s p o r t S e s s i o n ( " s s e - 2 " ) 
 
         
 
                         #   1 .   X - G r a f o - A g e n t - T o k e n   t e m   p r e c e d � n c i a   s o b r e   A u t h o r i z a t i o n :   B e a r e r 
 
                         _ c a l l _ w i t h _ r e q _ c t x ( 
 
                                 s e r v e r , 
 
                                 s e s s 1 , 
 
                                 S i m p l e N a m e s p a c e ( 
 
                                         h e a d e r s = { 
 
                                                 " X - G r a f o - A g e n t - T o k e n " :   " t e s t - s s e - h e a d e r - o w n e r " , 
 
                                                 " A u t h o r i z a t i o n " :   " B e a r e r   t e s t - s s e - b e a r e r - o t h e r " , 
 
                                         } 
 
                                 ) , 
 
                                 " a g e n t _ s a v e _ c h e c k p o i n t " , 
 
                                 { " a g e n t _ i d " :   " s s e _ a g " ,   " s e s s i o n _ i d " :   " s s e _ s 1 " ,   " c h e c k p o i n t _ i d " :   " c p 1 " ,   " s t a t e _ d i c t " :   { " s s e " :   1 } } , 
 
                         ) 
 
         
 
                         #   M e s m o   c o m   B e a r e r   i g u a l ,   o u t r o   X - G r a f o - A g e n t - T o k e n   n � o   a c e s s a 
 
 >                       w i t h   p y t e s t . r a i s e s ( ( P e r m i s s i o n E r r o r ,   T o o l E r r o r ) )   a s   e x c _ i n f o : 
 
                                   ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
 E                       F a i l e d :   D I D   N O T   R A I S E   a n y   o f   ( P e r m i s s i o n E r r o r ,   T o o l E r r o r ) 
 
 
 
 t e s t s \ t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : 3 7 5 :   F a i l e d 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = =   s h o r t   t e s t   s u m m a r y   i n f o   = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 F A I L E D   t e s t s / t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : : t e s t _ d i r e c t _ c h e c k p o i n t e r _ b l o c k s _ a l l _ f o u r _ c r o s s _ o w n e r _ v e c t o r s 
 
 F A I L E D   t e s t s / t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : : t e s t _ o w n e r s h i p _ p e r s i s t s _ a c r o s s _ r e s t a r t _ a n d _ n e v e r _ l e a k s _ s e c r e t s 
 
 F A I L E D   t e s t s / t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : : t e s t _ l e g a c y _ f i v e _ c o l u m n _ s c h e m a _ m i g r a t e s _ o n _ s t o r e _ b o o t _ a n d _ i s _ f a i l _ c l o s e d 
 
 F A I L E D   t e s t s / t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : : t e s t _ m c p _ s t d i o _ e n v _ a n d _ e p h e m e r a l _ s e s s i o n _ i s o l a t i o n 
 
 F A I L E D   t e s t s / t e s t _ c h e c k p o i n t _ o w n e r s h i p . p y : : t e s t _ m c p _ h t t p _ s s e _ h e a d e r _ p r e c e d e n c e _ b e a r e r _ a n d _ e p h e m e r a l 
 
 5   f a i l e d   i n   2 . 2 6 s 
 
 
```

### Mutações Obrigatórias (C3)
```text
M1: KILLED (exit=1) - Disable owner_hash verification in get_checkpoint | 5 failed in 2.09s
M2: KILLED (exit=1) - Disable owner_hash verification in list_checkpoints | 3 failed, 2 passed in 2.18s
M3: KILLED (exit=1) - Disable owner_hash verification in save_checkpoint_detailed | 3 failed, 2 passed in 1.79s
M4: KILLED (exit=1) - Store plaintext owner_token instead of SHA-256 hex in _hash_owner_token | 1 failed, 4 passed in 2.00s
M5: KILLED (exit=1) - Disable ALTER TABLE migration of owner_hash in SchemaManager.apply_full_schema | 1 failed, 4 passed in 2.01s
TOTAL: 5/5 KILLED
```

### Evidência GREEN (`pytest` normal + `--reverse` + `flake8`) (C3)
```text
=== C3 PYTEST NORMAL ===
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   2 0 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   4 1 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   6 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   8 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                             [ 1 0 0 % ] 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   w a r n i n g s   s u m m a r y   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 t e s t s / t e s t _ c o n v e r s a t i o n a l _ d b . p y : : t e s t _ q d r a n t _ v e c t o r _ s t o r e _ p a y l o a d _ v a l i d a t i o n 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ q d r a n t _ c l i e n t \ q d r a n t _ r e m o t e . p y : 2 9 5 :   U s e r W a r n i n g :   F a i l e d   t o   o b t a i n   s e r v e r   v e r s i o n .   U n a b l e   t o   c h e c k   c l i e n t - s e r v e r   c o m p a t i b i l i t y .   S e t   c h e c k _ c o m p a t i b i l i t y = F a l s e   t o   s k i p   v e r s i o n   c h e c k . 
 
         s h o w _ w a r n i n g ( 
 
 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ s t o r e . p y : 1 6 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         u p d a t e s [ " u p d a t e d _ a t " ]   =   d a t e t i m e . u t c n o w ( ) . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 0 _ w o r k e r _ d e a t h _ i n _ l o o p _ f a i l s _ w a i t i n g _ a n d _ s u b s e q u e n t _ c a l l e r s _ f a s t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 2 3 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   F a t a l   w o r k e r   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 1 _ m u l t i p l e _ q u e u e d _ i t e m s _ f a i l _ f a s t _ w h e n _ l o o p _ d i e s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 2 5 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   S i m u l a t e d   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 6 _ b a t c h _ f a t a l _ e r r o r _ n o t i f i e s _ a l l _ b a t c h e d _ c a l l e r s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 4 2 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 4 2 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ b a t c h ( c o n n ,   b a t c h ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     M e m o r y E r r o r :   S i m u l a t e d   c a t a s t r o p h i c   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ s t o r a g e _ l o g i c . p y :   1 4   w a r n i n g s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ l o g i c . p y : 3 4 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         n o w   =   d a t e t i m e . u t c n o w ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 8 2 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   ` p r o j e c t . l i c e n s e `   a s   a   T O M L   t a b l e   i s   d e p r e c a t e d 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   u s e   a   s i m p l e   s t r i n g   c o n t a i n i n g   a   S P D X   e x p r e s s i o n   f o r   ` p r o j e c t . l i c e n s e ` .   Y o u   c a n   a l s o   u s e   ` p r o j e c t . l i c e n s e - f i l e s ` .   ( B o t h   o p t i o n s   a v a i l a b l e   o n   s e t u p t o o l s > = 7 7 . 0 . 0 ) . 
 
     
 
                     B y   2 0 2 7 - F e b - 1 8 ,   y o u   n e e d   t o   u p d a t e   y o u r   p r o j e c t   a n d   r e m o v e   d e p r e c a t e d   c a l l s 
 
                     o r   y o u r   b u i l d s   w i l l   n o   l o n g e r   b e   s u p p o r t e d . 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         c o r r e s p ( d i s t ,   v a l u e ,   r o o t _ d i r ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 6 1 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         d i s t . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ d i s t . p y : 7 6 5 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         s e l f . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 - -   D o c s :   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l 
 
 3 4 7   p a s s e d ,   2 4   w a r n i n g s   i n   1 2 0 . 3 9 s   ( 0 : 0 2 : 0 0 ) 
 
 
=== C3 PYTEST REVERSE ===
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   2 0 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   4 1 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   6 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   8 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                             [ 1 0 0 % ] 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   w a r n i n g s   s u m m a r y   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 8 2 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   ` p r o j e c t . l i c e n s e `   a s   a   T O M L   t a b l e   i s   d e p r e c a t e d 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   u s e   a   s i m p l e   s t r i n g   c o n t a i n i n g   a   S P D X   e x p r e s s i o n   f o r   ` p r o j e c t . l i c e n s e ` .   Y o u   c a n   a l s o   u s e   ` p r o j e c t . l i c e n s e - f i l e s ` .   ( B o t h   o p t i o n s   a v a i l a b l e   o n   s e t u p t o o l s > = 7 7 . 0 . 0 ) . 
 
     
 
                     B y   2 0 2 7 - F e b - 1 8 ,   y o u   n e e d   t o   u p d a t e   y o u r   p r o j e c t   a n d   r e m o v e   d e p r e c a t e d   c a l l s 
 
                     o r   y o u r   b u i l d s   w i l l   n o   l o n g e r   b e   s u p p o r t e d . 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         c o r r e s p ( d i s t ,   v a l u e ,   r o o t _ d i r ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 6 1 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         d i s t . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ d i s t . p y : 7 6 5 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         s e l f . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ s t o r a g e _ l o g i c . p y :   1 4   w a r n i n g s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ l o g i c . p y : 3 4 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         n o w   =   d a t e t i m e . u t c n o w ( ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 6 _ b a t c h _ f a t a l _ e r r o r _ n o t i f i e s _ a l l _ b a t c h e d _ c a l l e r s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 0 2 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 4 2 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ b a t c h ( c o n n ,   b a t c h ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     M e m o r y E r r o r :   S i m u l a t e d   c a t a s t r o p h i c   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 1 _ m u l t i p l e _ q u e u e d _ i t e m s _ f a i l _ f a s t _ w h e n _ l o o p _ d i e s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 1 6 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 4 2 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ b a t c h ( c o n n ,   b a t c h ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   S i m u l a t e d   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 0 _ w o r k e r _ d e a t h _ i n _ l o o p _ f a i l s _ w a i t i n g _ a n d _ s u b s e q u e n t _ c a l l e r s _ f a s t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 2 1 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   F a t a l   w o r k e r   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ s t o r e . p y : 1 6 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         u p d a t e s [ " u p d a t e d _ a t " ]   =   d a t e t i m e . u t c n o w ( ) . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
 
 
 t e s t s / t e s t _ c o n v e r s a t i o n a l _ d b . p y : : t e s t _ s e m a n t i c _ f a c t s _ b i _ t e m p o r a l 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ q d r a n t _ c l i e n t \ q d r a n t _ r e m o t e . p y : 2 9 5 :   U s e r W a r n i n g :   F a i l e d   t o   o b t a i n   s e r v e r   v e r s i o n .   U n a b l e   t o   c h e c k   c l i e n t - s e r v e r   c o m p a t i b i l i t y .   S e t   c h e c k _ c o m p a t i b i l i t y = F a l s e   t o   s k i p   v e r s i o n   c h e c k . 
 
         s h o w _ w a r n i n g ( 
 
 
 
 - -   D o c s :   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l 
 
 3 4 7   p a s s e d ,   2 4   w a r n i n g s   i n   1 1 4 . 9 8 s   ( 0 : 0 1 : 5 4 ) 
 
 
=== C3 FLAKE8 ===
. \ . v e n v _ 3 1 0 \ L i b \ s i t e - p a c k a g e s \ s y m p y \ p o l y s \ n u m b e r f i e l d s \ r e s o l v e n t _ l o o k u p . p y :   " p y f l a k e s [ F ] "   f a i l e d   d u r i n g   e x e c u t i o n   d u e   t o   R e c u r s i o n E r r o r ( ' m a x i m u m   r e c u r s i o n   d e p t h   e x c e e d e d ' ) 
 
 R u n   f l a k e 8   w i t h   g r e a t e r   v e r b o s i t y   t o   s e e   m o r e   d e t a i l s 
 
 0 
 
 
=== C3 FLAKE8 (excluding local venvs) ===
. \ . v e n v _ 3 1 1 \ L i b \ s i t e - p a c k a g e s \ s y m p y \ p o l y s \ n u m b e r f i e l d s \ r e s o l v e n t _ l o o k u p . p y :   " p y f l a k e s [ F ] "   f a i l e d   d u r i n g   e x e c u t i o n   d u e   t o   R e c u r s i o n E r r o r ( ' m a x i m u m   r e c u r s i o n   d e p t h   e x c e e d e d ' ) 
 
 R u n   f l a k e 8   w i t h   g r e a t e r   v e r b o s i t y   t o   s e e   m o r e   d e t a i l s 
 
 0 
 
 
=== C3 FLAKE8 (repo dirs, excluding local venvs) ===
0 
 
 
```

### Secret Scan (C3)
```text
��s c a n n e d _ f i l e s = 1 5 6 0 
 
 f i l e s _ w i t h _ f i n d i n g s = 0 
 
 t o t a l _ p a t t e r n _ h i t s = 0 
 
 
```

### CI GitHub Actions (C3)
```text
Stage C3 CI Run (CI): id=45676931411 sha=79afa2cca2abd4241742eecf1fbc75018e796cd4 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45676931411
  - Test (Python 3.10): status=completed conclusion=success
  - Test (Python 3.12): status=completed conclusion=success
  - Test (Python 3.11): status=completed conclusion=success
Stage C3 CI Run (Windows Stdin Decouple & Lazy ML Imports): id=45676931338 sha=79afa2cca2abd4241742eecf1fbc75018e796cd4 status=completed conclusion=success url=https://github.com/LuisinTheLegend/ConciergeGraph/actions/runs/45676931338
  - Windows (3.12): status=completed conclusion=success
  - Windows (3.10): status=completed conclusion=success
  - Windows (3.14): status=completed conclusion=success
```

### `git diff` Integral (C3)
```diff
diff --git a/core/checkpointer.py b/core/checkpointer.py
index 7abec52..ab6e8ee 100644
--- a/core/checkpointer.py
+++ b/core/checkpointer.py
@@ -16,7 +16,11 @@ Design Invariants:
     in V4 (D0) and fail explicitly without writing to SQLite.
 """
 
+import hashlib
+import hmac
 import json
+import sqlite3
+import threading
 from typing import Any, Dict, List, Optional, Tuple
 
 
@@ -30,6 +34,63 @@ class AgnosticCheckpointer:
         self.db_manager = db_manager
         self.db = db_manager
         self.last_error: Optional[str] = None
+        self._write_lock = threading.Lock()
+
+    @staticmethod
+    def _hash_owner_token(owner_token: Optional[str]) -> str:
+        """Returns SHA-256 hex digest of owner_token, or empty string when absent."""
+        if not owner_token:
+            return ""
+        return hashlib.sha256(owner_token.encode("utf-8")).hexdigest()
+
+    def _read_namespace_hashes(self, agent_id: str, session_id: str) -> List[str]:
+        """Reads distinct owner_hash values for (agent_id, session_id), migrating 5-column tables if needed."""
+        query = (
+            "SELECT DISTINCT owner_hash FROM agent_checkpoints "
+            "WHERE agent_id = ? AND session_id = ?;"
+        )
+        try:
+            rows = self.db_manager.read_query(query, (agent_id, session_id))
+        except sqlite3.OperationalError as exc:
+            err_lower = str(exc).lower()
+            if "no such column" in err_lower and "owner_hash" in err_lower:
+                write_fn = getattr(self.db, "write_query", getattr(self.db, "execute_write", None))
+                if callable(write_fn):
+                    write_fn(
+                        "ALTER TABLE agent_checkpoints ADD COLUMN owner_hash TEXT NOT NULL DEFAULT '';",
+                        (),
+                    )
+                rows = self.db_manager.read_query(query, (agent_id, session_id))
+            else:
+                raise
+        if not rows or not isinstance(rows, (list, tuple)):
+            return []
+        hashes: List[str] = []
+        for row in rows:
+            val = row[0] if isinstance(row, (list, tuple)) and row else ""
+            hashes.append("" if val is None else str(val))
+        return hashes
+
+    def _verify_namespace_ownership(
+        self,
+        agent_id: str,
+        session_id: str,
+        owner_token: Optional[str],
+    ) -> None:
+        """Verifies caller ownership for an existing (agent_id, session_id) namespace."""
+        existing_hashes = self._read_namespace_hashes(agent_id, session_id)
+        if not existing_hashes:
+            return
+        if len(existing_hashes) > 1:
+            raise PermissionError(
+                "Access denied: inconsistent checkpoint ownership metadata for this agent/session namespace."
+            )
+        caller_hash = self._hash_owner_token(owner_token)
+        stored_hash = existing_hashes[0]
+        if not hmac.compare_digest(stored_hash, caller_hash):
+            raise PermissionError(
+                "Access denied: checkpoint ownership verification failed for this agent/session namespace."
+            )
 
     # ── Non-Serializable Object Sanitization ───────────────────────
 
@@ -55,6 +116,7 @@ class AgnosticCheckpointer:
     def save_checkpoint_detailed(
         self,
         *args,
+        owner_token: Optional[str] = None,
         **kwargs,
     ) -> Tuple[bool, Optional[str]]:
         """
@@ -112,18 +174,27 @@ class AgnosticCheckpointer:
                 state_blob = json.dumps(cleaned, ensure_ascii=False)
 
             write_fn = getattr(self.db, "write_query", getattr(self.db, "execute_write", None))
-            success, res = write_fn(
-                "INSERT OR REPLACE INTO agent_checkpoints "
-                "(agent_id, session_id, checkpoint_id, state_blob) "
-                "VALUES (?, ?, ?, ?);",
-                (agent_id, session_id, checkpoint_id, state_blob),
-            )
+            owner_hash = self._hash_owner_token(owner_token)
+            with self._write_lock:
+                try:
+                    self._verify_namespace_ownership(agent_id, session_id, owner_token)
+                except sqlite3.OperationalError as exc:
+                    if "no such table" in str(exc).lower():
+                        return (False, str(exc))
+                    raise
+                success, res = write_fn(
+                    "INSERT OR REPLACE INTO agent_checkpoints "
+                    "(agent_id, session_id, checkpoint_id, state_blob, owner_hash) "
+                    "VALUES (?, ?, ?, ?, ?);",
+                    (agent_id, session_id, checkpoint_id, state_blob, owner_hash),
+                )
             err = None if success else (str(res) if res is not None else "Unknown write error")
             return bool(success), err
 
     def save_checkpoint(
         self,
         *args,
+        owner_token: Optional[str] = None,
         **kwargs,
     ) -> bool:
         """
@@ -132,7 +203,7 @@ class AgnosticCheckpointer:
 
         Legacy wrapper returning bool, updating self.last_error for backward compatibility.
         """
-        success, err = self.save_checkpoint_detailed(*args, **kwargs)
+        success, err = self.save_checkpoint_detailed(*args, owner_token=owner_token, **kwargs)
         self.last_error = err
         return success
 
@@ -143,6 +214,8 @@ class AgnosticCheckpointer:
         agent_id: str,
         session_id: str,
         checkpoint_id: str,
+        *,
+        owner_token: Optional[str] = None,
     ) -> Dict[str, Any]:
         """
         Retrieves saved state under composite key (agent_id, session_id, checkpoint_id)
@@ -150,6 +223,7 @@ class AgnosticCheckpointer:
 
         Returns {} if checkpoint does not exist (agnostic fail-safe).
         """
+        self._verify_namespace_ownership(agent_id, session_id, owner_token)
         rows = self.db_manager.read_query(
             "SELECT state_blob FROM agent_checkpoints "
             "WHERE agent_id = ? AND session_id = ? AND checkpoint_id = ?;",
@@ -169,6 +243,8 @@ class AgnosticCheckpointer:
         self,
         agent_id: str,
         session_id: str,
+        *,
+        owner_token: Optional[str] = None,
     ) -> List[Dict[str, str]]:
         """
         Lists all checkpoints for an agent/session ordered chronologically
@@ -176,6 +252,7 @@ class AgnosticCheckpointer:
 
         Returns list of dicts with checkpoint_id and created_at.
         """
+        self._verify_namespace_ownership(agent_id, session_id, owner_token)
         rows = self.db_manager.read_query(
             "SELECT checkpoint_id, created_at FROM agent_checkpoints "
             "WHERE agent_id = ? AND session_id = ? "
diff --git a/interface/mcp_server.py b/interface/mcp_server.py
index dafa7ed..10612c5 100644
--- a/interface/mcp_server.py
+++ b/interface/mcp_server.py
@@ -174,6 +174,8 @@ class GrafoConciergeServer:
         # Creates the FastMCP server
         self._mcp = FastMCP("Grafo Concierge", host=host, port=port)
         self._transport_sessions: weakref.WeakKeyDictionary[Any, str] = weakref.WeakKeyDictionary()
+        self._session_owner_tokens: weakref.WeakKeyDictionary[Any, str] = weakref.WeakKeyDictionary()
+        self._fallback_owner_token: str = secrets.token_hex(32)
 
         # Enables CORS and optional API Key Authentication on Starlette sse_app
         original_sse_app = self._mcp.sse_app
@@ -268,6 +270,66 @@ class GrafoConciergeServer:
                 "Access denied: MCP transport session does not support weak-reference binding."
             ) from exc
 
+    def _resolve_checkpoint_owner_token(self) -> str:
+        """Resolves the checkpoint ownership token strictly from transport/server context."""
+        from core.mcp_governor import SecurityException
+
+        try:
+            req_ctx = self._mcp._mcp_server.request_context
+        except (AttributeError, LookupError):
+            req_ctx = None
+
+        if req_ctx is not None:
+            request_obj = getattr(req_ctx, "request", None)
+            session_obj = getattr(req_ctx, "session", None)
+            if request_obj is not None:
+                headers = getattr(request_obj, "headers", None)
+                agent_hdr = ""
+                auth_hdr = ""
+                if headers is not None:
+                    if hasattr(headers, "items") and isinstance(headers, dict):
+                        lower_map = {str(k).lower(): str(v) for k, v in headers.items()}
+                        agent_hdr = lower_map.get("x-grafo-agent-token", "").strip()
+                        auth_hdr = lower_map.get("authorization", "").strip()
+                    else:
+                        agent_hdr = str(
+                            headers.get("X-Grafo-Agent-Token")
+                            or headers.get("x-grafo-agent-token")
+                            or ""
+                        ).strip()
+                        auth_hdr = str(
+                            headers.get("Authorization")
+                            or headers.get("authorization")
+                            or ""
+                        ).strip()
+                if agent_hdr:
+                    return agent_hdr
+                if auth_hdr.lower().startswith("bearer "):
+                    bearer_tok = auth_hdr[7:].strip()
+                    if bearer_tok:
+                        return bearer_tok
+            else:
+                env_tok = os.environ.get("GRAFO_AGENT_TOKEN", "").strip()
+                if env_tok:
+                    return env_tok
+
+            if session_obj is not None:
+                try:
+                    tok = self._session_owner_tokens.get(session_obj)
+                    if tok is None:
+                        tok = secrets.token_hex(32)
+                        self._session_owner_tokens[session_obj] = tok
+                    return tok
+                except TypeError as exc:
+                    raise SecurityException(
+                        "Access denied: MCP transport session does not support weak-reference binding."
+                    ) from exc
+
+        env_tok = os.environ.get("GRAFO_AGENT_TOKEN", "").strip()
+        if env_tok:
+            return env_tok
+        return self._fallback_owner_token
+
     def _setup_tool_governance(self) -> None:
         """Configures FastMCP listing and execution interceptors under MCPToolGovernor."""
         from core.mcp_governor import SecurityException
@@ -957,7 +1019,13 @@ class GrafoConciergeServer:
             Returns:
                 JSON string with 'success' (bool) and 'message' (str).
             """
-            return agent_save_checkpoint(agent_id, session_id, checkpoint_id, state_dict)
+            return agent_save_checkpoint(
+                agent_id,
+                session_id,
+                checkpoint_id,
+                state_dict,
+                owner_token=server._resolve_checkpoint_owner_token(),
+            )
 
         # --- agent_get_checkpoint ---
         @self._mcp.tool(
@@ -981,7 +1049,12 @@ class GrafoConciergeServer:
             Returns:
                 Decoded state dictionary, or {} if not found.
             """
-            return agent_get_checkpoint(agent_id, session_id, checkpoint_id)
+            return agent_get_checkpoint(
+                agent_id,
+                session_id,
+                checkpoint_id,
+                owner_token=server._resolve_checkpoint_owner_token(),
+            )
 
         # --- agent_list_checkpoints ---
         @self._mcp.tool(
@@ -1003,7 +1076,11 @@ class GrafoConciergeServer:
             Returns:
                 List of dicts with 'checkpoint_id' and 'created_at' ordered ASC.
             """
-            return agent_list_checkpoints(agent_id, session_id)
+            return agent_list_checkpoints(
+                agent_id,
+                session_id,
+                owner_token=server._resolve_checkpoint_owner_token(),
+            )
 
     def _resolve_project_identifier(self, project_identifier: str) -> str:
         """Resolves project_identifier (UUID or folder_name) to project_uuid.
@@ -1780,6 +1857,7 @@ def agent_save_checkpoint(
     session_id: str,
     checkpoint_id: str,
     state_dict: dict,
+    owner_token: Optional[str] = None,
 ) -> str:
     """MCP Tool: Persists agent state in SQLite WAL via AgnosticCheckpointer.
 
@@ -1787,11 +1865,29 @@ def agent_save_checkpoint(
     """
     save_fn = getattr(checkpointer, "save_checkpoint_detailed", None)
     if callable(save_fn):
-        success, raw_err = save_fn(agent_id, session_id, checkpoint_id, state_dict)
+        if owner_token is not None:
+            success, raw_err = save_fn(
+                agent_id,
+                session_id,
+                checkpoint_id,
+                state_dict,
+                owner_token=owner_token,
+            )
+        else:
+            success, raw_err = save_fn(agent_id, session_id, checkpoint_id, state_dict)
     else:
-        success = checkpointer.save_checkpoint(
-            agent_id, session_id, checkpoint_id, state_dict
-        )
+        if owner_token is not None:
+            success = checkpointer.save_checkpoint(
+                agent_id,
+                session_id,
+                checkpoint_id,
+                state_dict,
+                owner_token=owner_token,
+            )
+        else:
+            success = checkpointer.save_checkpoint(
+                agent_id, session_id, checkpoint_id, state_dict
+            )
         raw_err = getattr(checkpointer, "last_error", None)
 
     if success:
@@ -1814,22 +1910,32 @@ def agent_get_checkpoint(
     agent_id: str,
     session_id: str,
     checkpoint_id: str,
+    owner_token: Optional[str] = None,
 ) -> dict:
     """MCP Tool: Retrieves agent state from SQLite WAL via AgnosticCheckpointer.
 
     Returns the decoded state dictionary, or {} if not found.
     """
+    if owner_token is not None:
+        return checkpointer.get_checkpoint(
+            agent_id, session_id, checkpoint_id, owner_token=owner_token
+        )
     return checkpointer.get_checkpoint(agent_id, session_id, checkpoint_id)
 
 
 def agent_list_checkpoints(
     agent_id: str,
     session_id: str,
+    owner_token: Optional[str] = None,
 ) -> list:
     """MCP Tool: Returns the chronological timeline of checkpoints for Time-Travel.
 
     Returns a list of dicts with 'checkpoint_id' and 'created_at', ordered ASC.
     """
+    if owner_token is not None:
+        return checkpointer.list_checkpoints(
+            agent_id, session_id, owner_token=owner_token
+        )
     return checkpointer.list_checkpoints(agent_id, session_id)
 
 
diff --git a/main.py b/main.py
index e235b7a..43c22dc 100644
--- a/main.py
+++ b/main.py
@@ -100,7 +100,7 @@ def redact_log_secrets(text: str) -> str:
         return text
 
     result = text
-    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY"):
+    for env_var in ("GRAFO_LLM_API_KEY", "GRAFO_API_KEY", "GEMINI_API_KEY", "GRAFO_AGENT_TOKEN"):
         secret_val = os.environ.get(env_var, "").strip()
         if len(secret_val) >= 8 and secret_val in result:
             result = result.replace(secret_val, "[REDACTED]")
diff --git a/storage/schema.py b/storage/schema.py
index d934898..647e7f8 100644
--- a/storage/schema.py
+++ b/storage/schema.py
@@ -148,6 +148,7 @@ CREATE TABLE IF NOT EXISTS agent_checkpoints (
     session_id    TEXT NOT NULL,
     checkpoint_id TEXT NOT NULL,
     state_blob    TEXT NOT NULL,
+    owner_hash    TEXT NOT NULL DEFAULT '',
     created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     PRIMARY KEY (agent_id, session_id, checkpoint_id)
 );
@@ -271,6 +272,16 @@ class SchemaManager:
                 self._conn.commit()
                 logger.info("Migration: 'utility_beta' column added to table 'semantic_facts'.")
 
+            # Ensure 'owner_hash' column exists in agent_checkpoints (BL-012)
+            cursor = self._conn.execute("PRAGMA table_info(agent_checkpoints)")
+            cp_cols = [row[1] for row in cursor.fetchall()]
+            if "owner_hash" not in cp_cols:
+                self._conn.execute(
+                    "ALTER TABLE agent_checkpoints ADD COLUMN owner_hash TEXT NOT NULL DEFAULT '';"
+                )
+                self._conn.commit()
+                logger.info("Migration: 'owner_hash' column added to table 'agent_checkpoints'.")
+
             # FTS5 Migration: upgrade nodes_fts to 4 columns (label, tags, summary, content)
             # with unicode61 remove_diacritics 2.
             cursor = self._conn.execute(
diff --git a/tests/test_checkpoint_ownership.py b/tests/test_checkpoint_ownership.py
new file mode 100644
index 0000000..2f6a867
--- /dev/null
+++ b/tests/test_checkpoint_ownership.py
@@ -0,0 +1,432 @@
+"""Testes de propriedade persistente em checkpoints (BL-012 / Rodada 4.6-C3)."""
+from __future__ import annotations
+
+import asyncio
+import hashlib
+import json
+import sqlite3
+from pathlib import Path
+from types import SimpleNamespace
+from unittest.mock import MagicMock
+
+import pytest
+from mcp.server.fastmcp.exceptions import ToolError
+from mcp.server.lowlevel.server import request_ctx
+from mcp.shared.context import RequestContext
+
+from core.checkpointer import AgnosticCheckpointer
+from core.database import ConciergeDatabaseManager
+from core.mcp_governor import MCPToolGovernor, SecurityException
+import interface.mcp_server as mcp_server_mod
+from interface.mcp_server import GrafoConciergeServer
+from main import redact_log_secrets
+from storage.store import SqliteStore
+
+
+class DummyTransportSession:
+    """Objeto weakref-compatível para simular ServerSession MCP em testes."""
+
+    def __init__(self, label: str) -> None:
+        self.label = label
+
+
+def _make_db_and_cp(db_path: Path) -> tuple[SqliteStore, ConciergeDatabaseManager, AgnosticCheckpointer]:
+    store = SqliteStore(str(db_path))
+    db_mgr = ConciergeDatabaseManager(str(db_path))
+    cp = AgnosticCheckpointer(db_mgr)
+    return store, db_mgr, cp
+
+
+def _make_server(db_path: Path, monkeypatch, default_state: str = "EXECUTION", max_state: str | None = None):
+    monkeypatch.setattr(mcp_server_mod, "governor", None)
+    monkeypatch.setattr(mcp_server_mod, "db_manager", None)
+    monkeypatch.setattr(mcp_server_mod, "checkpointer", None)
+    monkeypatch.setattr(mcp_server_mod, "graph_rag", None)
+    gov = MCPToolGovernor(default_state=default_state, max_state=max_state)
+    monkeypatch.setattr("core.mcp_governor._shared_governor", gov)
+
+    store = SqliteStore(str(db_path))
+    gc_facade = MagicMock()
+    gc_facade.config = None
+    gc_facade._store = store
+    server = GrafoConciergeServer(concierge=gc_facade)
+    return server, store
+
+
+def _call_with_req_ctx(server: GrafoConciergeServer, session, request_obj, tool_name: str, args: dict):
+    """Executa call_tool com ContextVar request_ctx oficial da sessão MCP."""
+    tok = request_ctx.set(
+        RequestContext(
+            request_id="req-bl012",
+            meta=None,
+            session=session,
+            lifespan_context=None,
+            request=request_obj,
+        )
+    )
+    try:
+        return asyncio.run(server.mcp._tool_manager.call_tool(tool_name, args))
+    finally:
+        request_ctx.reset(tok)
+
+
+def test_direct_checkpointer_blocks_all_four_cross_owner_vectors(tmp_path):
+    """Bloqueia get, list, overwrite e injeção de novo checkpoint_id em namespace alheio."""
+    db_path = tmp_path / "bl012_direct.db"
+    store, _, cp = _make_db_and_cp(db_path)
+    try:
+        victim_tok = "test-owner-token-victim-alpha"
+        attacker_tok = "test-owner-token-attacker-beta"
+
+        ok, err = cp.save_checkpoint_detailed(
+            "ag-1", "sess-1", "cp-1", {"secret": "classified"}, owner_token=victim_tok
+        )
+        assert (ok, err) == (True, None)
+
+        # Dono legítimo acessa normalmente
+        assert cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=victim_tok) == {
+            "secret": "classified"
+        }
+        assert len(cp.list_checkpoints("ag-1", "sess-1", owner_token=victim_tok)) == 1
+
+        # Vetor 1: get_checkpoint por outro dono ou sem token
+        with pytest.raises(PermissionError):
+            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=attacker_tok)
+        with pytest.raises(PermissionError):
+            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token="")
+        with pytest.raises(PermissionError):
+            cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=None)
+
+        # Vetor 2: list_checkpoints por outro dono ou sem token
+        with pytest.raises(PermissionError):
+            cp.list_checkpoints("ag-1", "sess-1", owner_token=attacker_tok)
+        with pytest.raises(PermissionError):
+            cp.list_checkpoints("ag-1", "sess-1", owner_token="")
+        with pytest.raises(PermissionError):
+            cp.list_checkpoints("ag-1", "sess-1", owner_token=None)
+
+        # Vetor 3: sobrescrever checkpoint existente no namespace alheio
+        with pytest.raises(PermissionError):
+            cp.save_checkpoint_detailed(
+                "ag-1", "sess-1", "cp-1", {"tampered": True}, owner_token=attacker_tok
+            )
+        with pytest.raises(PermissionError):
+            cp.save_checkpoint(
+                "ag-1", "sess-1", "cp-1", {"tampered": True}, owner_token=""
+            )
+
+        # Vetor 4: injetar novo checkpoint_id dentro do namespace (ag-1, sess-1) alheio
+        with pytest.raises(PermissionError):
+            cp.save_checkpoint_detailed(
+                "ag-1", "sess-1", "cp-injected", {"evil": 1}, owner_token=attacker_tok
+            )
+        with pytest.raises(PermissionError):
+            cp.save_checkpoint(
+                "ag-1", "sess-1", "cp-injected", {"evil": 1}, owner_token=None
+            )
+
+        # Namespace diferente pertence normalmente ao outro dono
+        assert cp.save_checkpoint(
+            "ag-1", "sess-other", "cp-1", {"own": True}, owner_token=attacker_tok
+        ) is True
+
+        # Conteúdo original do dono legítimo permanece intacto
+        assert cp.get_checkpoint("ag-1", "sess-1", "cp-1", owner_token=victim_tok) == {
+            "secret": "classified"
+        }
+        timeline = cp.list_checkpoints("ag-1", "sess-1", owner_token=victim_tok)
+        assert [row["checkpoint_id"] for row in timeline] == ["cp-1"]
+    finally:
+        store.close()
+
+
+def test_ownership_persists_across_restart_and_never_leaks_secrets(tmp_path, monkeypatch):
+    """Posse sobrevive ao restart em SQLite, grava apenas SHA-256 hex e redige env var."""
+    db_path = tmp_path / "bl012_restart.db"
+    victim_tok = "test-owner-token-persistent-v1"
+    attacker_tok = "test-owner-token-persistent-v2"
+    expected_hash = hashlib.sha256(victim_tok.encode("utf-8")).hexdigest()
+
+    store1, _, cp1 = _make_db_and_cp(db_path)
+    try:
+        state_before = dict(vars(cp1))
+        ok, err = cp1.save_checkpoint_detailed(
+            "ag-r", "sess-r", "cp-r", {"step": 10}, owner_token=victim_tok
+        )
+        assert (ok, err) == (True, None)
+        assert vars(cp1) == state_before
+    finally:
+        store1.close()
+
+    # Verificar direto no SQLite que plaintext não foi salvo e apenas o hash SHA-256 existe
+    with sqlite3.connect(str(db_path)) as conn:
+        row = conn.execute(
+            "SELECT owner_hash FROM agent_checkpoints WHERE agent_id='ag-r' AND session_id='sess-r' AND checkpoint_id='cp-r'"
+        ).fetchone()
+    assert row is not None
+    assert row[0] == expected_hash
+    assert victim_tok not in row[0]
+
+    # Simular restart completo: novas instâncias de Store e Checkpointer
+    store2, _, cp2 = _make_db_and_cp(db_path)
+    try:
+        assert cp2.get_checkpoint("ag-r", "sess-r", "cp-r", owner_token=victim_tok) == {"step": 10}
+        with pytest.raises(PermissionError) as exc_info:
+            cp2.get_checkpoint("ag-r", "sess-r", "cp-r", owner_token=attacker_tok)
+        msg = str(exc_info.value)
+        assert victim_tok not in msg
+        assert attacker_tok not in msg
+        assert expected_hash not in msg
+        assert expected_hash[:12] not in msg
+    finally:
+        store2.close()
+
+    # main.redact_log_secrets deve redigir GRAFO_AGENT_TOKEN
+    monkeypatch.setenv("GRAFO_AGENT_TOKEN", victim_tok)
+    redacted = redact_log_secrets(f"token={victim_tok} connected")
+    assert victim_tok not in redacted
+    assert "[REDACTED]" in redacted
+
+
+def test_legacy_five_column_schema_migrates_on_store_boot_and_is_fail_closed(tmp_path):
+    """Migra tabela legada de 5 colunas no boot do SqliteStore sem perder dados e sem adoção silenciosa."""
+    db_path = tmp_path / "bl012_legacy.db"
+    with sqlite3.connect(str(db_path)) as conn:
+        conn.execute(
+            "CREATE TABLE agent_checkpoints ("
+            "agent_id TEXT NOT NULL, "
+            "session_id TEXT NOT NULL, "
+            "checkpoint_id TEXT NOT NULL, "
+            "state_blob TEXT NOT NULL, "
+            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
+            "PRIMARY KEY (agent_id, session_id, checkpoint_id)"
+            ");"
+        )
+        conn.execute(
+            "INSERT INTO agent_checkpoints (agent_id, session_id, checkpoint_id, state_blob) "
+            "VALUES ('legacy_ag', 'legacy_sess', 'legacy_cp', '{\"step\": 42}');"
+        )
+        conn.commit()
+
+    # Boot apenas do SqliteStore (sem instanciar AgnosticCheckpointer antes)
+    store1 = SqliteStore(str(db_path))
+    store1.close()
+
+    with sqlite3.connect(str(db_path)) as conn:
+        cols = {row[1]: row for row in conn.execute("PRAGMA table_info(agent_checkpoints)").fetchall()}
+        assert "owner_hash" in cols
+        row = conn.execute(
+            "SELECT state_blob, owner_hash FROM agent_checkpoints "
+            "WHERE agent_id='legacy_ag' AND session_id='legacy_sess' AND checkpoint_id='legacy_cp'"
+        ).fetchone()
+        assert row is not None
+        assert json.loads(row[0]) == {"step": 42}
+        assert row[1] == ""
+
+    # 2o boot para provar idempotência da migração
+    store2, _, cp = _make_db_and_cp(db_path)
+    try:
+        # Chamador legado sem token continua compatível com linha legacy owner_hash == ''
+        assert cp.get_checkpoint("legacy_ag", "legacy_sess", "legacy_cp") == {"step": 42}
+        assert len(cp.list_checkpoints("legacy_ag", "legacy_sess")) == 1
+
+        # Chamador autenticado NÃO adota nem lê linha legacy (hash diferente de '')
+        with pytest.raises(PermissionError):
+            cp.get_checkpoint(
+                "legacy_ag", "legacy_sess", "legacy_cp", owner_token="test-owner-token-claimer"
+            )
+        with pytest.raises(PermissionError):
+            cp.save_checkpoint_detailed(
+                "legacy_ag", "legacy_sess", "legacy_cp2", {"step": 99}, owner_token="test-owner-token-claimer"
+            )
+    finally:
+        store2.close()
+
+
+def test_mcp_stdio_env_and_ephemeral_session_isolation(tmp_path, monkeypatch):
+    """stdio usa GRAFO_AGENT_TOKEN quando definido ou segredo efêmero por ServerSession."""
+    db_path = tmp_path / "bl012_mcp_stdio.db"
+
+    # Caso 1: GRAFO_AGENT_TOKEN definido em stdio (persiste entre instâncias de servidor)
+    monkeypatch.setenv("GRAFO_AGENT_TOKEN", "test-stdio-owner-token-alpha")
+    srv_owner, store_owner = _make_server(db_path, monkeypatch, default_state="EXECUTION")
+    try:
+        sess_a = DummyTransportSession("stdio-A")
+        save_res = _call_with_req_ctx(
+            srv_owner,
+            sess_a,
+            None,
+            "agent_save_checkpoint",
+            {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1", "state_dict": {"ok": 1}},
+        )
+        payload = json.loads(save_res) if isinstance(save_res, str) else save_res
+        assert payload["success"] is True
+
+        # Tentativa de passar owner_token forjado como argumento deve ser rejeitada pelo governor
+        with pytest.raises(SecurityException):
+            _call_with_req_ctx(
+                srv_owner,
+                sess_a,
+                None,
+                "agent_save_checkpoint",
+                {
+                    "agent_id": "mcp_ag",
+                    "session_id": "mcp_s1",
+                    "checkpoint_id": "cp1",
+                    "state_dict": {"ok": 2},
+                    "owner_token": "forged",
+                },
+            )
+    finally:
+        store_owner.close()
+
+    # Novo servidor com mesmo token (simulando restart) recupera normalmente
+    srv_restart, store_restart = _make_server(db_path, monkeypatch, default_state="EXECUTION")
+    try:
+        assert _call_with_req_ctx(
+            srv_restart,
+            DummyTransportSession("stdio-A2"),
+            None,
+            "agent_get_checkpoint",
+            {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1"},
+        ) == {"ok": 1}
+    finally:
+        store_restart.close()
+
+    # Novo servidor com outro GRAFO_AGENT_TOKEN deve ser bloqueado em get, list, overwrite e injeção
+    monkeypatch.setenv("GRAFO_AGENT_TOKEN", "test-stdio-owner-token-beta")
+    srv_attacker, store_attacker = _make_server(db_path, monkeypatch, default_state="EXECUTION")
+    try:
+        sess_b = DummyTransportSession("stdio-B")
+        for tool_name, tool_args in (
+            ("agent_get_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1"}),
+            ("agent_list_checkpoints", {"agent_id": "mcp_ag", "session_id": "mcp_s1"}),
+            ("agent_save_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp1", "state_dict": {"hack": 1}}),
+            ("agent_save_checkpoint", {"agent_id": "mcp_ag", "session_id": "mcp_s1", "checkpoint_id": "cp2", "state_dict": {"hack": 2}}),
+        ):
+            with pytest.raises((PermissionError, ToolError)) as exc_info:
+                _call_with_req_ctx(srv_attacker, sess_b, None, tool_name, tool_args)
+            if isinstance(exc_info.value, ToolError):
+                assert isinstance(exc_info.value.__cause__, PermissionError)
+    finally:
+        store_attacker.close()
+
+    # Caso 2: sem GRAFO_AGENT_TOKEN, cada ServerSession em stdio ganha seu segredo efêmero distinto
+    monkeypatch.delenv("GRAFO_AGENT_TOKEN", raising=False)
+    srv_ephem, store_ephem = _make_server(db_path, monkeypatch, default_state="EXECUTION")
+    try:
+        eph_s1 = DummyTransportSession("ephem-1")
+        eph_s2 = DummyTransportSession("ephem-2")
+
+        _call_with_req_ctx(
+            srv_ephem,
+            eph_s1,
+            None,
+            "agent_save_checkpoint",
+            {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1", "state_dict": {"e": 1}},
+        )
+        assert _call_with_req_ctx(
+            srv_ephem,
+            eph_s1,
+            None,
+            "agent_get_checkpoint",
+            {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1"},
+        ) == {"e": 1}
+
+        with pytest.raises((PermissionError, ToolError)) as exc_info:
+            _call_with_req_ctx(
+                srv_ephem,
+                eph_s2,
+                None,
+                "agent_get_checkpoint",
+                {"agent_id": "eph_ag", "session_id": "eph_s", "checkpoint_id": "cp1"},
+            )
+        if isinstance(exc_info.value, ToolError):
+            assert isinstance(exc_info.value.__cause__, PermissionError)
+    finally:
+        store_ephem.close()
+
+
+def test_mcp_http_sse_header_precedence_bearer_and_ephemeral(tmp_path, monkeypatch):
+    """HTTP/SSE resolve X-Grafo-Agent-Token > Authorization: Bearer > segredo efêmero da sessão."""
+    db_path = tmp_path / "bl012_mcp_sse.db"
+    monkeypatch.delenv("GRAFO_AGENT_TOKEN", raising=False)
+
+    server, store = _make_server(db_path, monkeypatch, default_state="EXECUTION")
+    try:
+        sess1 = DummyTransportSession("sse-1")
+        sess2 = DummyTransportSession("sse-2")
+
+        # 1. X-Grafo-Agent-Token tem precedência sobre Authorization: Bearer
+        _call_with_req_ctx(
+            server,
+            sess1,
+            SimpleNamespace(
+                headers={
+                    "X-Grafo-Agent-Token": "test-sse-header-owner",
+                    "Authorization": "Bearer test-sse-bearer-other",
+                }
+            ),
+            "agent_save_checkpoint",
+            {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1", "state_dict": {"sse": 1}},
+        )
+
+        # Mesmo com Bearer igual, outro X-Grafo-Agent-Token não acessa
+        with pytest.raises((PermissionError, ToolError)) as exc_info:
+            _call_with_req_ctx(
+                server,
+                sess2,
+                SimpleNamespace(
+                    headers={
+                        "X-Grafo-Agent-Token": "test-sse-header-attacker",
+                        "Authorization": "Bearer test-sse-bearer-other",
+                    }
+                ),
+                "agent_get_checkpoint",
+                {"agent_id": "sse_ag", "session_id": "sse_s1", "checkpoint_id": "cp1"},
+            )
+        if isinstance(exc_info.value, ToolError):
+            assert isinstance(exc_info.value.__cause__, PermissionError)
+
+        # 2. Sem X-Grafo-Agent-Token, usa Authorization: Bearer
+        _call_with_req_ctx(
+            server,
+            sess1,
+            SimpleNamespace(headers={"Authorization": "Bearer test-sse-bearer-owner"}),
+            "agent_save_checkpoint",
+            {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1", "state_dict": {"b": 2}},
+        )
+        assert _call_with_req_ctx(
+            server,
+            sess2,
+            SimpleNamespace(headers={"Authorization": "Bearer test-sse-bearer-owner"}),
+            "agent_get_checkpoint",
+            {"agent_id": "sse_ag", "session_id": "sse_s_bearer", "checkpoint_id": "cp1"},
+        ) == {"b": 2}
+        with pytest.raises((PermissionError, ToolError)):
+            _call_with_req_ctx(
+                server,
+                sess2,
+                SimpleNamespace(headers={"Authorization": "Bearer test-sse-bearer-wrong"}),
+                "agent_list_checkpoints",
+                {"agent_id": "sse_ag", "session_id": "sse_s_bearer"},
+            )
+
+        # 3. Sem nenhum header de token em SSE, isola por ServerSession efêmero
+        _call_with_req_ctx(
+            server,
+            sess1,
+            SimpleNamespace(headers={}),
+            "agent_save_checkpoint",
+            {"agent_id": "sse_ag", "session_id": "sse_s_eph", "checkpoint_id": "cp1", "state_dict": {"e": 3}},
+        )
+        with pytest.raises((PermissionError, ToolError)):
+            _call_with_req_ctx(
+                server,
+                sess2,
+                SimpleNamespace(headers={}),
+                "agent_get_checkpoint",
+                {"agent_id": "sse_ag", "session_id": "sse_s_eph", "checkpoint_id": "cp1"},
+            )
+    finally:
+        store.close()
```

## 6. Etapa C4 — Documentação Viva e Verificação Final de Invariantes

### Verificação de Caminhos Proibidos (`e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d` até working tree C4)
- Tamanho de `scratch/evidencia_4_6/c4_prohibited_diff.txt`: **0 bytes**.
```text
<vazio — 0 bytes de diff nos caminhos proibidos>
```

### Suíte Direcionada, Suíte Completa (Normal + `--reverse`) e `flake8` (C4)
```text
=== C4 TARGETED DOC & GUARD TESTS ===
= = = = = = = = = = = = = = = = = = = = = = = = = = = = =   t e s t   s e s s i o n   s t a r t s   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 p l a t f o r m   w i n 3 2   - -   P y t h o n   3 . 1 3 . 1 8 ,   p y t e s t - 9 . 2 . 0 ,   p l u g g y - 1 . 7 . 0   - -   C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ S c r i p t s \ p y t h o n . e x e 
 
 c a c h e d i r :   . p y t e s t _ c a c h e 
 
 r o o t d i r :   C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e 
 
 c o n f i g f i l e :   p y p r o j e c t . t o m l 
 
 p l u g i n s :   a n y i o - 4 . 1 6 . 0 ,   r e v e r s e - 1 . 9 . 0 ,   t i m e o u t - 2 . 4 . 0 
 
 t i m e o u t :   3 0 0 . 0 s 
 
 t i m e o u t   m e t h o d :   t h r e a d 
 
 t i m e o u t   f u n c _ o n l y :   F a l s e 
 
 c o l l e c t i n g   . . .   c o l l e c t e d   2 4   i t e m s 
 
 
 
 t e s t s / t e s t _ e n v _ e x a m p l e _ p r o v i d e r . p y : : t e s t _ e n v _ e x a m p l e _ d o e s _ n o t _ d e f i n e _ a c t i v e _ l l m _ p r o v i d e r   P A S S E D   [     4 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ d e f a u l t _ i n s t a n c e _ e x i s t s   P A S S E D   [     8 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 1 _ h y b r i d _ s e a r c h _ w e i g h t s   P A S S E D   [   1 2 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 2 _ r e c e n c y _ p a r a m e t e r s   P A S S E D   [   1 6 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 3 _ c e n t r a l i t y   P A S S E D   [   2 0 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 4 _ f t s 5 _ b m 2 5   P A S S E D   [   2 5 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 5 _ w i n g s   P A S S E D   [   2 9 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 6 _ i n g e s t i o n _ l i m i t s _ a n d _ f i l t e r s   P A S S E D   [   3 3 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 7 _ s u m m a r i z a t i o n _ t o k e n s   P A S S E D   [   3 7 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g D e f a u l t s : : t e s t _ s e c t i o n _ 8 _ m c p _ r u n t i m e   P A S S E D   [   4 1 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g I m m u t a b i l i t y A n d C u s t o m i z a t i o n : : t e s t _ c u s t o m _ i n s t a n c e _ o v e r r i d e s   P A S S E D   [   4 5 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g I m m u t a b i l i t y A n d C u s t o m i z a t i o n : : t e s t _ i m m u t a b i l i t y _ r a i s e s _ f r o z e n _ i n s t a n c e _ e r r o r   P A S S E D   [   5 0 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e n v _ a p i _ k e y _ o v e r r i d e   P A S S E D   [   5 4 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e n v _ c o r s _ o r i g i n s _ e m p t y _ s t r i n g _ p r e s e r v e s _ d e f a u l t   P A S S E D   [   5 8 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e n v _ c o r s _ o r i g i n s _ p a r s i n g   P A S S E D   [   6 2 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e n v _ l i g h t w e i g h t _ m o d e _ d i s a b l e d   P A S S E D   [   6 6 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e n v _ l i g h t w e i g h t _ m o d e _ e n a b l e d   P A S S E D   [   7 0 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e x p l i c i t _ a p i _ k e y _ h a s _ p r e c e d e n c e _ o v e r _ e n v   P A S S E D   [   7 5 % ] 
 
 t e s t s / t e s t _ c o n f i g . p y : : T e s t C o n c i e r g e C o n f i g E n v i r o n m e n t V a r i a b l e s : : t e s t _ e x p l i c i t _ l i g h t w e i g h t _ m o d e _ n o t _ o v e r r i d d e n _ b y _ e n v _ f a l s e   P A S S E D   [   7 9 % ] 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 1 _ c o n c i e r g e _ c o n f i g _ h a s _ n o _ w i n g _ k e y w o r d s   P A S S E D   [   8 3 % ] 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 2 _ n o _ r e t i r e d _ d o m a i n _ s t r i n g s _ i n _ p r o d u c t _ c o d e   P A S S E D   [   8 7 % ] 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 3 _ r e a l _ m i n i n g _ n e v e r _ a l t e r s _ p r i m a r y _ w i n g   P A S S E D   [   9 1 % ] 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t   P A S S E D   [   9 5 % ] 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s   P A S S E D   [ 1 0 0 % ] 
 
 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   w a r n i n g s   s u m m a r y   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ s t o r e . p y : 1 6 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         u p d a t e s [ " u p d a t e d _ a t " ]   =   d a t e t i m e . u t c n o w ( ) . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 8 2 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   ` p r o j e c t . l i c e n s e `   a s   a   T O M L   t a b l e   i s   d e p r e c a t e d 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   u s e   a   s i m p l e   s t r i n g   c o n t a i n i n g   a   S P D X   e x p r e s s i o n   f o r   ` p r o j e c t . l i c e n s e ` .   Y o u   c a n   a l s o   u s e   ` p r o j e c t . l i c e n s e - f i l e s ` .   ( B o t h   o p t i o n s   a v a i l a b l e   o n   s e t u p t o o l s > = 7 7 . 0 . 0 ) . 
 
     
 
                     B y   2 0 2 7 - F e b - 1 8 ,   y o u   n e e d   t o   u p d a t e   y o u r   p r o j e c t   a n d   r e m o v e   d e p r e c a t e d   c a l l s 
 
                     o r   y o u r   b u i l d s   w i l l   n o   l o n g e r   b e   s u p p o r t e d . 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         c o r r e s p ( d i s t ,   v a l u e ,   r o o t _ d i r ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 6 1 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         d i s t . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ d i s t . p y : 7 6 5 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         s e l f . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 - -   D o c s :   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l 
 
 = = = = = = = = = = = = = = = = = = = = = = =   2 4   p a s s e d ,   4   w a r n i n g s   i n   1 6 . 9 9 s   = = = = = = = = = = = = = = = = = = = = = = = 
 
 
=== C4 PYTEST NORMAL ===
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   2 0 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   4 1 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   6 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   8 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                             [ 1 0 0 % ] 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   w a r n i n g s   s u m m a r y   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 t e s t s / t e s t _ c o n v e r s a t i o n a l _ d b . p y : : t e s t _ q d r a n t _ c o l l e c t i o n _ i n i t i a l i z a t i o n _ r e a l 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ q d r a n t _ c l i e n t \ q d r a n t _ r e m o t e . p y : 2 9 5 :   U s e r W a r n i n g :   F a i l e d   t o   o b t a i n   s e r v e r   v e r s i o n .   U n a b l e   t o   c h e c k   c l i e n t - s e r v e r   c o m p a t i b i l i t y .   S e t   c h e c k _ c o m p a t i b i l i t y = F a l s e   t o   s k i p   v e r s i o n   c h e c k . 
 
         s h o w _ w a r n i n g ( 
 
 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ s t o r e . p y : 1 6 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         u p d a t e s [ " u p d a t e d _ a t " ]   =   d a t e t i m e . u t c n o w ( ) . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 0 _ w o r k e r _ d e a t h _ i n _ l o o p _ f a i l s _ w a i t i n g _ a n d _ s u b s e q u e n t _ c a l l e r s _ f a s t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 2 3 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   F a t a l   w o r k e r   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 1 _ m u l t i p l e _ q u e u e d _ i t e m s _ f a i l _ f a s t _ w h e n _ l o o p _ d i e s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 2 5 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   S i m u l a t e d   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 6 _ b a t c h _ f a t a l _ e r r o r _ n o t i f i e s _ a l l _ b a t c h e d _ c a l l e r s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 3 4 2 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 4 2 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ b a t c h ( c o n n ,   b a t c h ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     M e m o r y E r r o r :   S i m u l a t e d   c a t a s t r o p h i c   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ s t o r a g e _ l o g i c . p y :   1 4   w a r n i n g s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ l o g i c . p y : 3 4 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         n o w   =   d a t e t i m e . u t c n o w ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 8 2 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   ` p r o j e c t . l i c e n s e `   a s   a   T O M L   t a b l e   i s   d e p r e c a t e d 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   u s e   a   s i m p l e   s t r i n g   c o n t a i n i n g   a   S P D X   e x p r e s s i o n   f o r   ` p r o j e c t . l i c e n s e ` .   Y o u   c a n   a l s o   u s e   ` p r o j e c t . l i c e n s e - f i l e s ` .   ( B o t h   o p t i o n s   a v a i l a b l e   o n   s e t u p t o o l s > = 7 7 . 0 . 0 ) . 
 
     
 
                     B y   2 0 2 7 - F e b - 1 8 ,   y o u   n e e d   t o   u p d a t e   y o u r   p r o j e c t   a n d   r e m o v e   d e p r e c a t e d   c a l l s 
 
                     o r   y o u r   b u i l d s   w i l l   n o   l o n g e r   b e   s u p p o r t e d . 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         c o r r e s p ( d i s t ,   v a l u e ,   r o o t _ d i r ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 6 1 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         d i s t . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ d i s t . p y : 7 6 5 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         s e l f . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 - -   D o c s :   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l 
 
 3 4 7   p a s s e d ,   2 4   w a r n i n g s   i n   1 2 0 . 3 1 s   ( 0 : 0 2 : 0 0 ) 
 
 
=== C4 PYTEST REVERSE ===
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   2 0 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   4 1 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   6 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .   [   8 2 % ] 
 
 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                             [ 1 0 0 % ] 
 
 = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =   w a r n i n g s   s u m m a r y   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 8 2 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   ` p r o j e c t . l i c e n s e `   a s   a   T O M L   t a b l e   i s   d e p r e c a t e d 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   u s e   a   s i m p l e   s t r i n g   c o n t a i n i n g   a   S P D X   e x p r e s s i o n   f o r   ` p r o j e c t . l i c e n s e ` .   Y o u   c a n   a l s o   u s e   ` p r o j e c t . l i c e n s e - f i l e s ` .   ( B o t h   o p t i o n s   a v a i l a b l e   o n   s e t u p t o o l s > = 7 7 . 0 . 0 ) . 
 
     
 
                     B y   2 0 2 7 - F e b - 1 8 ,   y o u   n e e d   t o   u p d a t e   y o u r   p r o j e c t   a n d   r e m o v e   d e p r e c a t e d   c a l l s 
 
                     o r   y o u r   b u i l d s   w i l l   n o   l o n g e r   b e   s u p p o r t e d . 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         c o r r e s p ( d i s t ,   v a l u e ,   r o o t _ d i r ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ c o n f i g \ _ a p p l y _ p y p r o j e c t t o m l . p y : 6 1 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         d i s t . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ w h e e l _ i n t e g r i t y . p y : : t e s t _ w h e e l _ c o n t a i n s _ a l l _ l i v e _ m o d u l e s _ a n d _ e n t r y p o i n t s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ s e t u p t o o l s \ d i s t . p y : 7 6 5 :   S e t u p t o o l s D e p r e c a t i o n W a r n i n g :   L i c e n s e   c l a s s i f i e r s   a r e   d e p r e c a t e d . 
 
     ! ! 
 
     
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
                     P l e a s e   c o n s i d e r   r e m o v i n g   t h e   f o l l o w i n g   c l a s s i f i e r s   i n   f a v o r   o f   a   S P D X   l i c e n s e   e x p r e s s i o n : 
 
     
 
                     L i c e n s e   : :   O S I   A p p r o v e d   : :   M I T   L i c e n s e 
 
     
 
                     S e e   h t t p s : / / p a c k a g i n g . p y t h o n . o r g / e n / l a t e s t / g u i d e s / w r i t i n g - p y p r o j e c t - t o m l / # l i c e n s e   f o r   d e t a i l s . 
 
                     * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
 
     
 
     ! ! 
 
         s e l f . _ f i n a l i z e _ l i c e n s e _ e x p r e s s i o n ( ) 
 
 
 
 t e s t s / t e s t _ s t o r a g e _ l o g i c . p y :   1 4   w a r n i n g s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ l o g i c . p y : 3 4 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         n o w   =   d a t e t i m e . u t c n o w ( ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 6 _ b a t c h _ f a t a l _ e r r o r _ n o t i f i e s _ a l l _ b a t c h e d _ c a l l e r s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 0 2 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 4 2 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ b a t c h ( c o n n ,   b a t c h ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     M e m o r y E r r o r :   S i m u l a t e d   c a t a s t r o p h i c   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 1 _ m u l t i p l e _ q u e u e d _ i t e m s _ f a i l _ f a s t _ w h e n _ l o o p _ d i e s 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 1 6 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   S i m u l a t e d   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ q u e u e _ w r i t e r _ r e s i l i e n c e . p y : : T e s t Q u e u e W r i t e r R e s i l i e n c e : : t e s t _ t 1 0 _ w o r k e r _ d e a t h _ i n _ l o o p _ f a i l s _ w a i t i n g _ a n d _ s u b s e q u e n t _ c a l l e r s _ f a s t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ _ p y t e s t \ t h r e a d e x c e p t i o n . p y : 5 4 :   P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g :   E x c e p t i o n   i n   t h r e a d   T h r e a d - 1 2 1 
 
     
 
     T r a c e b a c k   ( m o s t   r e c e n t   c a l l   l a s t ) : 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ t h r e a d i n g . p y " ,   l i n e   1 0 4 4 ,   i n   _ b o o t s t r a p _ i n n e r 
 
             s e l f . r u n ( ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ 
 
         F i l e   " C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ i n t e r f a c e \ q u e u e _ w r i t e r . p y " ,   l i n e   1 3 9 ,   i n   r u n 
 
             s e l f . _ e x e c u t e _ s i n g l e ( c o n n ,   b a t c h [ 0 ] ) 
 
             ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 6 9 ,   i n   _ _ c a l l _ _ 
 
             r e t u r n   s e l f . _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 1 7 3 ,   i n   _ m o c k _ c a l l 
 
             r e t u r n   s e l f . _ e x e c u t e _ m o c k _ c a l l ( * a r g s ,   * * k w a r g s ) 
 
                           ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ 
 
         F i l e   " C : \ U s e r s \ g u i a l \ A p p D a t a \ R o a m i n g \ u v \ p y t h o n \ c p y t h o n - 3 . 1 3 - w i n d o w s - x 8 6 _ 6 4 - n o n e \ L i b \ u n i t t e s t \ m o c k . p y " ,   l i n e   1 2 3 4 ,   i n   _ e x e c u t e _ m o c k _ c a l l 
 
             r a i s e   e f f e c t 
 
     S y s t e m E r r o r :   F a t a l   w o r k e r   l o o p   c r a s h 
 
     
 
     E n a b l e   t r a c e m a l l o c   t o   g e t   t r a c e b a c k   w h e r e   t h e   o b j e c t   w a s   a l l o c a t e d . 
 
     S e e   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l # r e s o u r c e - w a r n i n g s   f o r   m o r e   i n f o . 
 
         w a r n i n g s . w a r n ( p y t e s t . P y t e s t U n h a n d l e d T h r e a d E x c e p t i o n W a r n i n g ( m s g ) ) 
 
 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ m c p _ s e r v e r _ h a n d l e r s . p y : : T e s t H a n d l e U p d a t e P r o j e c t : : t e s t _ u p d a t e _ p r o j e c t _ f i e l d s 
 
 t e s t s / t e s t _ d o m a i n _ n e u t r a l i t y _ g u a r d . p y : : t e s t _ g 4 _ f r e e _ t e x t _ w i n g s _ a n d _ u p d a t e _ p r o j e c t 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ s t o r a g e \ s t o r e . p y : 1 6 2 :   D e p r e c a t i o n W a r n i n g :   d a t e t i m e . d a t e t i m e . u t c n o w ( )   i s   d e p r e c a t e d   a n d   s c h e d u l e d   f o r   r e m o v a l   i n   a   f u t u r e   v e r s i o n .   U s e   t i m e z o n e - a w a r e   o b j e c t s   t o   r e p r e s e n t   d a t e t i m e s   i n   U T C :   d a t e t i m e . d a t e t i m e . n o w ( d a t e t i m e . U T C ) . 
 
         u p d a t e s [ " u p d a t e d _ a t " ]   =   d a t e t i m e . u t c n o w ( ) . s t r f t i m e ( " % Y - % m - % d   % H : % M : % S " ) 
 
 
 
 t e s t s / t e s t _ c o n v e r s a t i o n a l _ d b . p y : : t e s t _ q d r a n t _ v e c t o r _ s t o r e _ p a y l o a d _ v a l i d a t i o n 
 
     C : \ N e x u s - M e m o r y \ G r a f o C o n c i e r g e \ . v e n v _ 3 1 3 \ L i b \ s i t e - p a c k a g e s \ q d r a n t _ c l i e n t \ q d r a n t _ r e m o t e . p y : 2 9 5 :   U s e r W a r n i n g :   F a i l e d   t o   o b t a i n   s e r v e r   v e r s i o n .   U n a b l e   t o   c h e c k   c l i e n t - s e r v e r   c o m p a t i b i l i t y .   S e t   c h e c k _ c o m p a t i b i l i t y = F a l s e   t o   s k i p   v e r s i o n   c h e c k . 
 
         s h o w _ w a r n i n g ( 
 
 
 
 - -   D o c s :   h t t p s : / / d o c s . p y t e s t . o r g / e n / s t a b l e / h o w - t o / c a p t u r e - w a r n i n g s . h t m l 
 
 3 4 7   p a s s e d ,   2 4   w a r n i n g s   i n   1 1 5 . 7 9 s   ( 0 : 0 1 : 5 5 ) 
 
 
=== C4 FLAKE8 ===
0 
 
 
```

### `git diff` da Documentação (C4 pré-commit)
```diff
diff --git a/.env.example b/.env.example
index 3e36813..a57546d 100644
--- a/.env.example
+++ b/.env.example
@@ -88,8 +88,19 @@ GRAFO_PORT=8000
 CONCIERGE_BIND_ADDRESS=127.0.0.1
 
 # -----------------------------------------------------------------------------
-# 7. SECURITY, REMOTE AUTHENTICATION & CORS
+# 7. SECURITY, MCP GOVERNANCE, REMOTE AUTHENTICATION & CORS
 # -----------------------------------------------------------------------------
+# Initial and ceiling MCP governance state (3-state least-privilege hierarchy):
+#   PLANNING (17 READ_ONLY tools, default) < EXECUTION (29 tools) < MAINTENANCE (31 tools)
+# Sessions start in GRAFO_DEFAULT_STATE and cannot escalate above this ceiling.
+GRAFO_DEFAULT_STATE=PLANNING
+
+# Optional checkpoint ownership secret for 'stdio' MCP transport (BL-012)
+# Prevents cross-session read/list/overwrite of agent_checkpoints via SHA-256 owner_hash.
+# Over HTTP/SSE, pass header 'X-Grafo-Agent-Token: <token>' (or 'Authorization: Bearer <token>').
+# If omitted, each MCP ServerSession receives an ephemeral per-session secret.
+GRAFO_AGENT_TOKEN=
+
 # Optional Bearer token authentication for SSE requests (recommended for VPS)
 # When set, requests require 'Authorization: Bearer <key>' or '?token=<key>'
 GRAFO_API_KEY=
diff --git a/CHANGELOG.md b/CHANGELOG.md
index a4ae7c7..b09453b 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -5,6 +5,21 @@ O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.
 
 ## [Unreleased]
 
+### Rodada 4.6 — Segurança de Fronteira e Governança MCP (BL-011, BL-012, BL-013, BL-014, BL-015)
+
+- **Teto de Privilégio e Governança de 3 Estados (`core/mcp_governor.py` — BL-011, BL-014, BL-015):**
+  - Alterado o estado padrão `GRAFO_DEFAULT_STATE` de `"EXECUTION"` para `"PLANNING"` (menor privilégio) e imposto o teto `max_state` (`PLANNING < EXECUTION < MAINTENANCE`) com exceção explícita `SecurityException(PermissionError)` em tentativas de escalonamento acima do teto; estados `default_state` / `max_state` inválidos falham imediatamente (`ValueError`) no `__init__`.
+  - Consolidada a `TOOL_DISCLOSURE_MATRIX` de 8 para **3 estados** (`PLANNING`, `EXECUTION`, `MAINTENANCE`, todos com `"allowed_tools": []`).
+  - Reclassificada `concierge_set_state` de `READ_ONLY` para `LOCAL_MUTATION` (`17 READ_ONLY / 12 LOCAL_MUTATION / 2 DANGEROUS`).
+- **Isolamento de Sessão por Transporte e Filtragem de `list_tools` (`interface/mcp_server.py` — BL-011, BL-013):**
+  - Removido o parâmetro `session_id` controlado pelo cliente em `concierge_set_state(state_name)` e vinculada a sessão de governança estritamente à instância de transporte MCP em `WeakKeyDictionary`.
+  - Implementada allowlist estrita de parâmetros em `governed_call_tool` (rejeitando argumentos extras não declarados e payloads não-`dict` antes da invocação) e dupla vinculação de `governed_list_tools()` em `self._mcp.list_tools` e no handler low-level `ListToolsRequest`.
+- **Propriedade Persistente em Checkpoints (`storage/schema.py`, `core/checkpointer.py`, `interface/mcp_server.py`, `main.py` — BL-012):**
+  - Adicionada coluna `owner_hash TEXT NOT NULL DEFAULT ''` à tabela `agent_checkpoints` com migração idempotente `ALTER TABLE` em bancos SQLite pré-existentes sem perda de dados.
+  - Aplicada verificação constante (`hmac.compare_digest` sobre SHA-256) no namespace `(agent_id, session_id)` em `save_checkpoint_detailed`, `save_checkpoint`, `get_checkpoint` e `list_checkpoints` com política *fail-closed* (`PermissionError`).
+  - Resolvido o token de posse pelo servidor MCP (`X-Grafo-Agent-Token` > `Authorization: Bearer` em HTTP/SSE; `GRAFO_AGENT_TOKEN` em `stdio`; fallback efêmero por `ServerSession` em `WeakKeyDictionary`) e adicionada `GRAFO_AGENT_TOKEN` à função `main.py::redact_log_secrets`.
+  - Cobertura de regressão ampliada para **347 testes aprovados** (incluindo `tests/test_mcp_security_governance.py` e `tests/test_checkpoint_ownership.py`).
+
 ### Rodada 4.5g — Governança MCP, Empacotamento/Docker e Documentação Viva
 
 - **Governança MCP (`core/mcp_governor.py`):**
diff --git a/README.md b/README.md
index 4f56f43..b34f93b 100644
--- a/README.md
+++ b/README.md
@@ -9,7 +9,7 @@ English · [Português (Brasil)](README.pt-BR.md)
 [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
 [![Protocol MCP](https://img.shields.io/badge/Protocol-MCP-purple.svg)](https://modelcontextprotocol.io/)
 [![MCP Tools](https://img.shields.io/badge/MCP%20Tools-31-blue.svg)](docs-grafo-concierge/README.md)
-[![Tests Passing](https://img.shields.io/badge/Tests-335%20Passed-brightgreen.svg)](tests/)
+[![Tests Passing](https://img.shields.io/badge/Tests-347%20Passed-brightgreen.svg)](tests/)
 
 Concierge Graph is a local-first memory server built around the **Model Context Protocol (MCP)** that gives AI coding assistants (Cursor, Claude Desktop, and autonomous agents) persistent project memory, hybrid retrieval, recursive call-chain queries, durable agent checkpoints, and governed tool disclosure — backed by **SQLite WAL (with FTS5)** and pluggable vector storage (**ChromaDB** by default, optional **Qdrant**).
 
@@ -23,8 +23,8 @@ Concierge Graph is a local-first memory server built around the **Model Context
 2. **Tri-Signal Hybrid Search v4 (`core/hybrid_search.py`)**: Blends dense vector similarity (`sentence-transformers` + ChromaDB/Qdrant), SQLite FTS5 BM25 lexical scoring, and topological/recency signals with strict project/wing scoping and query-time orphan vector filtering.
 3. **Python AST Ingestion & Self-Healing Vectors (`ingestion/`, `services/janitor.py`)**: Crawls repositories, extracts Python AST chunks and call edges, repairs missing embeddings during mining with honest failure reporting, and supports on-demand vector reconciliation (`concierge sync-vector`).
 4. **Recursive Call-Chain GraphRAG (`core/graph_rag.py`)**: Traverses multi-hop `calls` dependencies over SQLite `edges` using `WITH RECURSIVE` CTEs protected by strict pipe-delimited cycle guards (`|node|`).
-5. **Durable Agent Checkpoints (`core/checkpointer.py`)**: Persists and retrieves structured agent state dictionaries in `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint`, and `agent_list_checkpoints` with strict argument resolution and corrupt-JSON detection.
-6. **Progressive MCP Tool Disclosure (`core/mcp_governor.py`)**: Classifies all **31 live MCP tools** into `READ_ONLY` (18), `LOCAL_MUTATION` (11), and `DANGEROUS` (2), enforcing both discovery filtering (`filter_tools`) and runtime execution checks (`validate_tool_execution`) with fail-closed defaults for unclassified tools.
+5. **Durable Agent Checkpoints with Ownership Binding (`core/checkpointer.py`)**: Persists and retrieves structured agent state dictionaries in `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint`, and `agent_list_checkpoints` with strict argument resolution, corrupt-JSON detection, and SHA-256 `owner_hash` namespace verification (`GRAFO_AGENT_TOKEN` over `stdio`, or `X-Grafo-Agent-Token` / `Authorization: Bearer` over HTTP/SSE, falling back to an ephemeral per-`ServerSession` secret).
+6. **Least-Privilege MCP Governance (`core/mcp_governor.py`)**: Classifies all **31 live MCP tools** into `READ_ONLY` (17), `LOCAL_MUTATION` (12), and `DANGEROUS` (2) across a 3-state hierarchy (`PLANNING < EXECUTION < MAINTENANCE`), defaulting to `PLANNING` (`GRAFO_DEFAULT_STATE`) as a hard privilege ceiling (`max_state`). Sessions are bound server-side to the MCP transport (`WeakKeyDictionary`), undeclared tool arguments are rejected, and both `list_tools` (`ListToolsRequest`) and runtime execution enforce fail-closed governance filtering.
 7. **Domain Neutrality & Free-Form Wings**: Project wings are strictly user- or agent-defined free-form strings — no hardcoded business taxonomies exist in product code, enforced by AST guard tests (`tests/test_domain_neutrality_guard.py`).
 8. **Optional Lightweight Mode & Optional LLM Summaries**: Set `GRAFO_LIGHTWEIGHT_MODE=true` to operate without heavy vector models using SQLite FTS5 BM25, and `GRAFO_LLM_MODEL=none` to run fully offline without external LLM calls.
 
@@ -119,8 +119,8 @@ Concierge Graph is a local-first memory server built around the **Model Context
 
 | Category | Count | Tools |
 | :--- | :---: | :--- |
-| **`READ_ONLY`** | 18 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `concierge_set_state`, `agent_get_checkpoint`, `agent_list_checkpoints` |
-| **`LOCAL_MUTATION`** | 11 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
+| **`READ_ONLY`** | 17 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `agent_get_checkpoint`, `agent_list_checkpoints` |
+| **`LOCAL_MUTATION`** | 12 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
 | **`DANGEROUS`** | 2 | `delete_project`, `reset_collection` |
 
 See [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) for architecture details and the full list of CLI subcommands.
@@ -129,7 +129,7 @@ See [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) for archi
 
 ## Testing & Verification
 
-The active V4 core is covered by **335 passing automated tests** (verified in normal and `--reverse` order, plus CI across Linux and Windows):
+The active V4 core is covered by **347 passing automated tests** (verified in normal and `--reverse` order, plus CI across Linux and Windows):
 
 ```bash
 python -m pytest tests/ -q
diff --git a/README.pt-BR.md b/README.pt-BR.md
index 8a7f9c4..8d21318 100644
--- a/README.pt-BR.md
+++ b/README.pt-BR.md
@@ -9,7 +9,7 @@
 [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
 [![Protocolo MCP](https://img.shields.io/badge/Protocolo-MCP-purple.svg)](https://modelcontextprotocol.io/)
 [![Ferramentas MCP](https://img.shields.io/badge/Ferramentas%20MCP-31-blue.svg)](docs-grafo-concierge/README.md)
-[![Testes Aprovados](https://img.shields.io/badge/Testes-335%20Aprovados-brightgreen.svg)](tests/)
+[![Testes Aprovados](https://img.shields.io/badge/Testes-347%20Aprovados-brightgreen.svg)](tests/)
 
 O Grafo Concierge é um servidor de memória local-first baseado no **Model Context Protocol (MCP)** que fornece a assistentes de código (Cursor, Claude Desktop e agentes autônomos) memória persistente de projetos, busca híbrida, rastreamento recursivo de chamadas, checkpoints duráveis de agentes e governança progressiva de ferramentas — apoiado em **SQLite WAL (com FTS5)** e armazenamento vetorial plugável (**ChromaDB** por padrão, **Qdrant** opcional).
 
@@ -23,8 +23,8 @@ O Grafo Concierge é um servidor de memória local-first baseado no **Model Cont
 2. **Busca Híbrida Tri-Sinal v4 (`core/hybrid_search.py`)**: Combina similaridade vetorial densa (`sentence-transformers` + ChromaDB/Qdrant), pontuação lexical SQLite FTS5 BM25 e sinais topológicos/de recência com escopo estrito por projeto/ala e filtragem de vetores órfãos em tempo de consulta.
 3. **Ingestão AST Python e Reparo de Vetores (`ingestion/`, `services/janitor.py`)**: Percorre repositórios, extrai blocos AST Python e arestas de chamada, repara embeddings ausentes durante a mineração com relato explícito de falhas e oferece reconciliação sob demanda (`concierge sync-vector`).
 4. **GraphRAG Recursivo de Cadeia de Chamadas (`core/graph_rag.py`)**: Percorre dependências multi-hop `calls` na tabela `edges` via CTEs `WITH RECURSIVE` protegidas por guarda de ciclo delimitada por pipes (`|node|`).
-5. **Checkpoints Duráveis de Agentes (`core/checkpointer.py`)**: Persiste e recupera dicionários de estado de agentes em `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`, com resolução estrita de argumentos e detecção de JSON corrompido.
-6. **Governança Progressiva de Ferramentas MCP (`core/mcp_governor.py`)**: Classifica todas as **31 ferramentas MCP vivas** em `READ_ONLY` (18), `LOCAL_MUTATION` (11) e `DANGEROUS` (2), aplicando filtragem na descoberta (`filter_tools`) e validação em tempo de execução (`validate_tool_execution`) com política *fail-closed* para nomes não classificados.
+5. **Checkpoints Duráveis de Agentes com Posse Persistente (`core/checkpointer.py`)**: Persiste e recupera dicionários de estado de agentes em `agent_checkpoints` via `agent_save_checkpoint`, `agent_get_checkpoint` e `agent_list_checkpoints`, com resolução estrita de argumentos, detecção de JSON corrompido e verificação de posse por `owner_hash` SHA-256 (`GRAFO_AGENT_TOKEN` em `stdio`, ou `X-Grafo-Agent-Token` / `Authorization: Bearer` em HTTP/SSE, com fallback efêmero por `ServerSession`).
+6. **Governança MCP de Menor Privilégio (`core/mcp_governor.py`)**: Classifica todas as **31 ferramentas MCP vivas** em `READ_ONLY` (17), `LOCAL_MUTATION` (12) e `DANGEROUS` (2) em uma hierarquia de 3 estados (`PLANNING < EXECUTION < MAINTENANCE`), iniciando em `PLANNING` (`GRAFO_DEFAULT_STATE`) como teto de privilégio (`max_state`). As sessões são vinculadas ao transporte no servidor (`WeakKeyDictionary`), argumentos extras não declarados são rejeitados e tanto `list_tools` (`ListToolsRequest`) quanto a execução aplicam filtragem *fail-closed*.
 7. **Neutralidade de Domínio e Alas Livres**: As alas de projetos são strings livres definidas exclusivamente pelo usuário ou agente — sem taxonomias fixas de domínio no código de produto, garantido por testes-guarda AST (`tests/test_domain_neutrality_guard.py`).
 8. **Modo Lightweight e Resumos LLM Opcionais**: Defina `GRAFO_LIGHTWEIGHT_MODE=true` para operar sem modelos vetoriais pesados usando SQLite FTS5 BM25, e `GRAFO_LLM_MODEL=none` para operar 100% offline sem chamadas externas a LLMs.
 
@@ -119,8 +119,8 @@ O Grafo Concierge é um servidor de memória local-first baseado no **Model Cont
 
 | Categoria | Qtd. | Ferramentas |
 | :--- | :---: | :--- |
-| **`READ_ONLY`** | 18 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `concierge_set_state`, `agent_get_checkpoint`, `agent_list_checkpoints` |
-| **`LOCAL_MUTATION`** | 11 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
+| **`READ_ONLY`** | 17 | `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`, `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`, `agent_get_checkpoint`, `agent_list_checkpoints` |
+| **`LOCAL_MUTATION`** | 12 | `concierge_register`, `concierge_mine`, `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`, `update_project`, `add_reference_wing`, `remove_reference_wing`, `agent_save_checkpoint` |
 | **`DANGEROUS`** | 2 | `delete_project`, `reset_collection` |
 
 Consulte [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) para detalhes da arquitetura e a lista completa dos 10 subcomandos da CLI.
@@ -129,7 +129,7 @@ Consulte [`docs-grafo-concierge/README.md`](docs-grafo-concierge/README.md) para
 
 ## Testes e Verificação
 
-O núcleo ativo V4 é coberto por **335 testes automatizados aprovados** (verificados em ordem normal e `--reverse`, além de CI em Linux e Windows):
+O núcleo ativo V4 é coberto por **347 testes automatizados aprovados** (verificados em ordem normal e `--reverse`, além de CI em Linux e Windows):
 
 ```bash
 python -m pytest tests/ -q
diff --git a/audits/fase4-decisoes.md b/audits/fase4-decisoes.md
index 9504eb6..647de77 100644
--- a/audits/fase4-decisoes.md
+++ b/audits/fase4-decisoes.md
@@ -206,4 +206,23 @@ Encerramento da série `4.5` (D4, D7, D8 de `audits/egm/4.5b-sintese.md`), execu
   6. Guardas de empacotamento em `tests/test_wheel_integrity.py` e `tests/test_dependency_pins.py` (bloquear retorno de pacotes dormentes).
   7. Higiene local de diretórios órfãos com apenas `__pycache__` (`agent/`, `agents/`, `core/parsers/`).
 
+---
+
+## 8. Rodada 4.6 — Segurança de Fronteira e Governança MCP (2026-11-25)
+
+Remediação integral da Track 3 (`BL-011`, `BL-012`, `BL-013`, `BL-014`, `BL-015`) e da Proposta #5 da Rodada `4.5g`, executada a partir do commit base `e5bd4e1b608d7ce99ad2c05c7a86b4ce0813688d` com CI 6/6 GREEN por etapa:
+
+- **Decisões Arquiteturais Homologadas pelo Humano:**
+  - **Decisão 1A (`BL-011` / `BL-015` — Teto de Privilégio + Sessão Vinculada ao Transporte):** `GRAFO_DEFAULT_STATE` passa de `"EXECUTION"` para `"PLANNING"` (menor privilégio). `MCPToolGovernor` impõe `max_state` (`PLANNING < EXECUTION < MAINTENANCE`) igual ao `default_state` configurado no boot, levantando `SecurityException(PermissionError)` em qualquer tentativa de elevação acima de `max_state`. `concierge_set_state(state_name)` passa para `LOCAL_MUTATION` sem parâmetro `session_id`. `governed_call_tool` nunca lê `arguments.get("session_id")` e rejeita argumentos extras não declarados no schema da ferramenta.
+  - **Decisão 2A (`BL-012` — Posse Persistente em Checkpoints):** Adicionada coluna `owner_hash TEXT NOT NULL DEFAULT ''` em `agent_checkpoints` (`storage/schema.py`) com migração idempotente `ALTER TABLE`. O servidor MCP resolve `owner_token` na ordem `X-Grafo-Agent-Token` -> `Authorization: Bearer` -> segredo efêmero em `WeakKeyDictionary` (HTTP/SSE), ou `GRAFO_AGENT_TOKEN` -> segredo efêmero (stdio). `core/checkpointer.py` verifica SHA-256 com `hmac.compare_digest` no namespace `(agent_id, session_id)` em `save`, `get` e `list` (política *fail-closed* sem adoção silenciosa de linhas legadas `owner_hash == ''` por chamadores autenticados), e `main.py::redact_log_secrets` passa a redigir `GRAFO_AGENT_TOKEN`.
+  - **Decisão 3A (`BL-013` — Filtragem de `list_tools`):** `governed_list_tools` filtra sempre pela sessão vinculada ao transporte e é registrada tanto em `self._mcp.list_tools` quanto em `self._mcp._mcp_server.list_tools()`.
+  - **Decisão 4A (`BL-014` + Proposta #5 da `4.5g`):** `TOOL_DISCLOSURE_MATRIX` consolidada para os 3 estados (`PLANNING`, `EXECUTION`, `MAINTENANCE`, todos com `"allowed_tools": []`); estados `default_state`/`max_state` inválidos levantam `ValueError` no `__init__`.
+- **Commits Executados na Rodada 4.6:**
+  - **C0 (`0cf527189d4d8e3e6b630e076577e0044b5f9ff4`):** Revisão pré-execução EGM + Swarm (`audits/egm/4.6-{fatos,design,critic,sintese}.md`). CI 6/6 GREEN.
+  - **C1 (`279f75189d4d8e3e6b630e076577e0044b5f9ff4`):** Governança de 3 estados, teto `max_state`, `PLANNING` padrão e reclassificação de `concierge_set_state` em `core/mcp_governor.py` (`17 READ_ONLY / 12 LOCAL_MUTATION / 2 DANGEROUS`; 5/5 mutantes mortos; 337 testes). CI 6/6 GREEN.
+  - **C2 (`e196005114e2f5c7d9018c642372d632a0af1bf7`):** Vínculo de sessão ao transporte (`WeakKeyDictionary`), remoção de `session_id` em `concierge_set_state`, allowlist estrita de kwargs e dupla vinculação de `list_tools` em `interface/mcp_server.py` + `tests/test_mcp_security_governance.py` (5/5 mutantes mortos; 342 testes). CI 6/6 GREEN.
+  - **C3 (`79afa2cca2abd4241742eecf1fbc75018e796cd4`):** Propriedade persistente `owner_hash` em `storage/schema.py`, `core/checkpointer.py`, `interface/mcp_server.py`, `main.py` + `tests/test_checkpoint_ownership.py` (5/5 mutantes mortos; 347 testes). CI 6/6 GREEN.
+  - **C4 (`docs(security)`):** Documentação viva (`.env.example`, `README.md`, `README.pt-BR.md`, `docs-grafo-concierge/README.md`, `CHANGELOG.md`, `audits/fase4-decisoes.md`) e relatório final `audits/relatorio_4_6.md`.
+
+
 
diff --git a/docs-grafo-concierge/README.md b/docs-grafo-concierge/README.md
index 7854bac..80e68ed 100644
--- a/docs-grafo-concierge/README.md
+++ b/docs-grafo-concierge/README.md
@@ -24,21 +24,26 @@ Concierge Graph is organized around six live Python packages plus the root entry
 
 ## 2. MCP Tools Reference (31 Live Tools)
 
-All **31 MCP tools** registered in `interface/mcp_server.py` are classified in `core/mcp_governor.py` (`TOOL_CLASSIFICATION`) and governed by `MCPToolGovernor` with fail-closed defaults for unclassified names:
+All **31 MCP tools** registered in `interface/mcp_server.py` are classified in `core/mcp_governor.py` (`TOOL_CLASSIFICATION`) and governed by `MCPToolGovernor` across a 3-state privilege hierarchy (`PLANNING < EXECUTION < MAINTENANCE`) with fail-closed defaults for unclassified names:
 
-### `READ_ONLY` (18 tools)
+### `READ_ONLY` (17 tools)
 - **Retrieval & Context:** `concierge_search`, `concierge_resume`, `concierge_load`, `concierge_status`, `concierge_list_projects`, `concierge_list_facts`, `concierge_get_memory`
 - **Graph & Code Symbols:** `get_full_topology`, `get_trajectories`, `find_similar`, `search_symbols`, `get_implementations`, `get_callers`, `concierge_get_call_chain`, `count_embeddings`
-- **Governance & Checkpoints:** `concierge_set_state`, `agent_get_checkpoint`, `agent_list_checkpoints`
+- **Checkpoints:** `agent_get_checkpoint`, `agent_list_checkpoints`
 
-### `LOCAL_MUTATION` (11 tools)
+### `LOCAL_MUTATION` (12 tools)
 - **Project & Ingestion:** `concierge_register`, `concierge_mine`, `update_project`, `add_reference_wing`, `remove_reference_wing`
-- **Memory & Facts:** `concierge_commit`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`
+- **Memory & Governance:** `concierge_commit`, `concierge_set_state`, `concierge_wakeup`, `concierge_store_fact`, `concierge_set_memory`, `concierge_feedback`
 - **Checkpoints:** `agent_save_checkpoint`
 
 ### `DANGEROUS` (2 tools)
 - **Destructive Operations:** `delete_project`, `reset_collection`
 
+### Governance & Checkpoint Security Model
+- **Default state & ceiling:** `GRAFO_DEFAULT_STATE` defaults to `PLANNING` (least privilege: 17 `READ_ONLY` tools) and sets `max_state`. `concierge_set_state(state_name)` no longer accepts client `session_id`, operates strictly on the transport-bound session (`WeakKeyDictionary`), and cannot escalate above `max_state`.
+- **Discovery & parameter enforcement:** Both `FastMCP.list_tools` and low-level `ListToolsRequest` filter exposed tools by the active session state, while `governed_call_tool` rejects undeclared extra arguments before execution.
+- **Persistent checkpoint ownership:** `agent_checkpoints` stores SHA-256 `owner_hash` verified via `hmac.compare_digest` over `(agent_id, session_id)` on save, get, and list. MCP resolves the owner token from `X-Grafo-Agent-Token` / `Authorization: Bearer` (HTTP/SSE) or `GRAFO_AGENT_TOKEN` (`stdio`), falling back to an ephemeral per-`ServerSession` secret when unset.
+
 ---
 
 ## 3. CLI Reference (`concierge` — 10 Subcommands)
```
