"""
tests/test_connection_queue_resilience.py — Testes P1–P9 para storage/connection.py (F4-031, Rodada 4.4d)

Verifica os invariantes e o endurecimento da fila de escrita de produção
(storage/connection.py::SerializedWriteQueue e ConnectionManager):
- P1: connect do worker levanta 'database is locked' em todas as tentativas -> falha rápido (< 10 s).
- P2: falha 2 vezes com 'database is locked' e depois funciona -> escrita tem sucesso e tentativas == 3.
- P3: OperationalError('disk I/O error') na partida falha na hora (1 tentativa, sem retry) e fecha a conexão.
- P4: morte tardia por exceção no laço -> chamador ativo, múltiplos jobs pendentes e chamadas seguintes
      falham em poucos segundos sem ficar pendurados, e a fila é drenada (is_empty() == True).
- P5: job longo (~2 s) termina com sucesso (prova que não há prazo total para job em execução).
- P6: submit antes do start() levanta RuntimeError imediatamente.
- P7: lendo a conexão dentro de um job, PRAGMA busy_timeout = 5000, journal_mode = wal,
      foreign_keys = 1 e row_factory is sqlite3.Row.
- P8: start() duas vezes é no-op (idempotente); stop() encerra a thread.
- P9: ao nível do SqliteStore, uma partida da fila que falha não trava a construção nem o primeiro write.
"""

import os
import sqlite3
import tempfile
import threading
import time
from typing import Any, Callable
from unittest.mock import patch

import pytest

import storage.connection as conn_module
from storage.connection import ConnectionManager, SerializedWriteQueue
from storage.store import SqliteStore


def _run_with_deadlock_guard(timeout_s: float, fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """Executa `fn` em uma thread auxiliar daemon para detectar travamento (deadlock) rápido."""
    outcome: dict[str, Any] = {"done": False, "result": None, "error": None}

    def _target() -> None:
        try:
            outcome["result"] = fn(*args, **kwargs)
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            outcome["done"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if not outcome["done"]:
        pytest.fail(f"DEADLOCK DETECTADO: chamada bloqueou por mais de {timeout_s}s sem retornar.")
    if outcome["error"] is not None:
        raise outcome["error"]
    return outcome["result"]


@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test_conn_resilience.db")


# ---------------------------------------------------------------------------
# P1: connect levanta 'database is locked' em todas as tentativas -> falha rápido
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p1_connect_persistent_locked_fails_fast(tmp_db_path):
    """P1: Se sqlite3.connect levantar 'database is locked' em todas as tentativas,
    a partida falha rápido (< 10 s) levantando RuntimeError com causa encadeada, sem travar.
    """
    attempts = {"count": 0}

    def _always_locked(*args, **kwargs):
        attempts["count"] += 1
        raise sqlite3.OperationalError("database is locked")

    q = SerializedWriteQueue(tmp_db_path)
    t0 = time.monotonic()
    with patch.object(conn_module.sqlite3, "connect", side_effect=_always_locked), \
         patch.object(conn_module, "INITIAL_BACKOFF_SECONDS", 0.01, create=True), \
         patch.object(conn_module, "MAX_BACKOFF_SECONDS", 0.05, create=True):

        with pytest.raises(RuntimeError) as exc_info:
            _run_with_deadlock_guard(4.0, q.start)

        with pytest.raises(RuntimeError) as submit_exc_info:
            _run_with_deadlock_guard(1.0, q.submit, lambda conn: conn.execute("SELECT 1"))

    elapsed = time.monotonic() - t0
    assert elapsed < 10.0, f"Partida deveria falhar em < 10s, levou {elapsed:.2f}s"
    assert attempts["count"] >= 2, f"Deveria ter tentado múltiplas vezes (retries), tentou {attempts['count']}"
    assert isinstance(exc_info.value.__cause__, sqlite3.OperationalError)
    assert "database is locked" in str(exc_info.value).lower()
    assert isinstance(submit_exc_info.value.__cause__, sqlite3.OperationalError)
    assert "database is locked" in str(submit_exc_info.value).lower()


# ---------------------------------------------------------------------------
# P2: falha 2 vezes com 'database is locked' e depois funciona
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p2_startup_retries_twice_on_locked_then_succeeds(tmp_db_path):
    """P2: Se sqlite3.connect falhar 2 vezes com 'database is locked' e funcionar na 3ª,
    o handshake conclui com sucesso e a escrita funciona normalmente.
    """
    real_connect = sqlite3.connect
    attempts = {"count": 0}

    def _flaky_connect(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] <= 2:
            raise sqlite3.OperationalError("database is locked")
        return real_connect(*args, **kwargs)

    q = SerializedWriteQueue(tmp_db_path)
    try:
        with patch.object(conn_module.sqlite3, "connect", side_effect=_flaky_connect), \
             patch.object(conn_module, "INITIAL_BACKOFF_SECONDS", 0.01, create=True):
            _run_with_deadlock_guard(4.0, q.start)

        assert attempts["count"] == 3, f"Esperadas exatas 3 tentativas (2 falhas + 1 sucesso), obteve {attempts['count']}"

        def _create_and_insert(conn):
            conn.execute("CREATE TABLE IF NOT EXISTS t_p2 (id INTEGER PRIMARY KEY, val TEXT)")
            conn.execute("INSERT INTO t_p2 (val) VALUES ('ok')")
            row = conn.execute("SELECT val FROM t_p2 WHERE id = 1").fetchone()
            return row["val"]

        val = _run_with_deadlock_guard(4.0, q.submit, _create_and_insert)
        assert val == "ok"
    finally:
        q.stop()


# ---------------------------------------------------------------------------
# P3: OperationalError('disk I/O error') na partida falha na hora e fecha conexão
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p3_non_lock_operational_error_fails_immediately_and_closes_conn(tmp_db_path):
    """P3: Um sqlite3.OperationalError('disk I/O error') durante os PRAGMAs de partida
    não faz retry (1 única tentativa), fecha a conexão aberta e falha imediatamente.
    """
    real_connect = sqlite3.connect
    stats = {"connect_calls": 0, "close_calls": 0}

    class _InstrumentedConn:
        def __init__(self, raw_conn):
            self._raw = raw_conn
            self.row_factory = None

        def execute(self, sql, *args, **kwargs):
            if "journal_mode" in sql.lower():
                raise sqlite3.OperationalError("disk I/O error")
            return self._raw.execute(sql, *args, **kwargs)

        def close(self):
            stats["close_calls"] += 1
            return self._raw.close()

    def _connect_failing_pragma(*args, **kwargs):
        stats["connect_calls"] += 1
        raw = real_connect(*args, **kwargs)
        return _InstrumentedConn(raw)

    q = SerializedWriteQueue(tmp_db_path)
    with patch.object(conn_module.sqlite3, "connect", side_effect=_connect_failing_pragma):
        def _start_and_submit():
            q.start()
            q.submit(lambda conn: None)

        with pytest.raises(RuntimeError) as exc_info:
            _run_with_deadlock_guard(3.0, _start_and_submit)

    assert stats["connect_calls"] == 1, f"Erro não-lock não deve fazer retry; fez {stats['connect_calls']} chamadas"
    assert stats["close_calls"] == 1, f"Conexão aberta na tentativa falha deve ser fechada; close_calls={stats['close_calls']}"
    assert isinstance(exc_info.value.__cause__, sqlite3.OperationalError)
    assert "disk i/o error" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# P4: morte tardia por exceção no laço -> ativo, pendentes e seguintes falham rápido
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p4_worker_late_death_in_loop_notifies_active_pending_and_subsequent(tmp_db_path):
    """P4: Se a thread sqlite-writer morrer depois da partida (ex.: BaseException fatal ou
    exceção no rollback fora do except do job), o job em execução, múltiplos jobs pendentes
    na fila e chamadas seguintes a submit() falham em poucos segundos com RuntimeError
    ('write worker died'), sem deixar nenhum chamador pendurado e drenando a fila.
    """
    q = SerializedWriteQueue(tmp_db_path)
    q.start()

    job1_entered = threading.Event()
    release_job1 = threading.Event()

    def _crashing_job(conn):
        job1_entered.set()
        release_job1.wait(timeout=5.0)
        # Levanta BaseException para simular morte inesperada do laço do worker
        # fora do `except Exception` normal do job (sem sinalizar job.result_event no bloco do job)
        raise BaseException("fatal loop crash in sqlite-writer")

    errors: list[BaseException] = []
    errors_lock = threading.Lock()

    def _caller(fn):
        try:
            q.submit(fn)
        except BaseException as exc:
            with errors_lock:
                errors.append(exc)

    t_active = threading.Thread(target=_caller, args=(_crashing_job,), daemon=True)
    t_active.start()
    assert job1_entered.wait(timeout=3.0), "Job ativo não iniciou no worker"

    # Enfileira 3 jobs pendentes enquanto o job ativo está segurando o worker
    pending_threads = [
        threading.Thread(target=_caller, args=(lambda conn, i=i: conn.execute("SELECT ?", (i,)),), daemon=True)
        for i in range(3)
    ]
    for pt in pending_threads:
        pt.start()

    # Garante que os jobs pendentes entraram na fila antes da morte do worker
    deadline = time.monotonic() + 2.0
    while q._queue.qsize() < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert q._queue.qsize() == 3, f"Esperados 3 jobs pendentes na fila, encontrou {q._queue.qsize()}"

    # Libera o job ativo para matar a thread do worker
    release_job1.set()

    t_active.join(timeout=3.0)
    for pt in pending_threads:
        pt.join(timeout=3.0)

    assert not t_active.is_alive(), "Chamador do job ativo ficou pendurado após morte do worker!"
    for idx, pt in enumerate(pending_threads):
        assert not pt.is_alive(), f"Chamador pendente {idx} ficou pendurado após morte do worker!"

    assert len(errors) == 4, f"Todos os 4 chamadores (1 ativo + 3 pendentes) devem receber erro, recebeu {len(errors)}"
    for err in errors:
        assert isinstance(err, RuntimeError), f"Esperado RuntimeError, obteve {type(err)}: {err}"
        assert "write worker died" in str(err).lower()

    # Verifica que a fila de pendentes foi efetivamente drenada no encerramento do worker (mata Re)
    assert q.is_empty(), "A fila de jobs pendentes deve estar vazia (drenada) após a morte do worker"

    # Chamada subsequente após a morte do worker deve falhar na hora (< 0.5 s)
    t0 = time.monotonic()
    with pytest.raises(RuntimeError) as sub_exc:
        _run_with_deadlock_guard(1.0, q.submit, lambda conn: conn.execute("SELECT 1"))
    assert (time.monotonic() - t0) < 0.5
    assert "write worker died" in str(sub_exc.value).lower()


# ---------------------------------------------------------------------------
# P5: job longo (~2 s) termina com sucesso (sem prazo total para job rodando)
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p5_long_running_job_2s_succeeds_without_total_timeout(tmp_db_path):
    """P5: Um job legítimo que leva ~2 s em execução conclui com sucesso, provando que
    a espera em submit() é por liveness do worker e não impõe TimeoutError total ao job.
    """
    cm = ConnectionManager(tmp_db_path)
    cm.start()
    try:
        def _long_write(conn):
            conn.execute("CREATE TABLE t_p5 (id INTEGER PRIMARY KEY, v TEXT)")
            time.sleep(2.0)
            conn.execute("INSERT INTO t_p5 (v) VALUES ('completed_after_2s')")
            return conn.execute("SELECT v FROM t_p5 WHERE id = 1").fetchone()["v"]

        res = cm.write(_long_write)
        assert res == "completed_after_2s"
    finally:
        cm.close()


# ---------------------------------------------------------------------------
# P6: submit antes do start() levanta RuntimeError imediatamente
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p6_submit_before_start_raises_runtime_error_immediately(tmp_db_path):
    """P6: Chamar submit() antes de start() levanta RuntimeError imediatamente."""
    q = SerializedWriteQueue(tmp_db_path)
    t0 = time.monotonic()
    with pytest.raises(RuntimeError, match="Call start\\(\\) first"):
        q.submit(lambda conn: conn.execute("SELECT 1"))
    assert (time.monotonic() - t0) < 0.2


# ---------------------------------------------------------------------------
# P7: PRAGMA busy_timeout = 5000, journal_mode = wal, foreign_keys = 1 e Row
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p7_regime_pragmas_and_row_factory(tmp_db_path):
    """P7: Lendo a conexão dentro de um job em regime, verifica os invariantes:
    - PRAGMA busy_timeout == 5000
    - PRAGMA journal_mode == 'wal'
    - PRAGMA foreign_keys == 1
    - conn.row_factory is sqlite3.Row
    """
    cm = ConnectionManager(tmp_db_path)
    cm.start()
    try:
        def _inspect_conn(conn):
            bt = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            jm = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            rf = conn.row_factory
            return bt, jm, fk, rf

        busy_timeout, journal_mode, foreign_keys, row_factory = cm.write(_inspect_conn)
        assert busy_timeout == 5000, f"Invariante violado: busy_timeout de regime deve ser 5000, obteve {busy_timeout}"
        assert str(journal_mode).lower() == "wal", f"Esperado journal_mode='wal', obteve {journal_mode}"
        assert foreign_keys == 1, f"Esperado foreign_keys=1, obteve {foreign_keys}"
        assert row_factory is sqlite3.Row, f"Esperado row_factory=sqlite3.Row, obteve {row_factory}"
    finally:
        cm.close()


# ---------------------------------------------------------------------------
# P8: start() duas vezes é no-op; stop() encerra a thread
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p8_start_idempotent_and_stop_terminates_thread(tmp_db_path):
    """P8: Chamar start() duas vezes seguidas é no-op (mesma thread permanece viva);
    chamar stop() encerra a thread sqlite-writer.
    """
    q = SerializedWriteQueue(tmp_db_path)
    q.start()
    first_thread = q._thread
    assert first_thread.is_alive()

    # Segunda chamada a start() deve ser no-op
    q.start()
    assert q._thread is first_thread
    assert first_thread.is_alive()

    q.stop()
    assert not first_thread.is_alive(), "stop() deve encerrar a thread sqlite-writer"


# ---------------------------------------------------------------------------
# P9: ao nível do SqliteStore, partida que falha não trava construção nem write
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_p9_sqlitestore_startup_failure_does_not_hang(tmp_db_path):
    """P9: Ao nível do SqliteStore, se a partida da SerializedWriteQueue falhar
    (ex.: sqlite3.connect do worker levantando OperationalError), a construção do
    SqliteStore (ou o primeiro write) falha rápido com RuntimeError sem travar.
    """
    real_connect = sqlite3.connect

    def _connect_fail_on_worker(*args, **kwargs):
        if threading.current_thread().name == "sqlite-writer":
            raise sqlite3.OperationalError("database is locked")
        return real_connect(*args, **kwargs)

    with patch.object(conn_module.sqlite3, "connect", side_effect=_connect_fail_on_worker), \
         patch.object(conn_module, "INITIAL_BACKOFF_SECONDS", 0.01, create=True), \
         patch.object(conn_module, "MAX_BACKOFF_SECONDS", 0.05, create=True):

        def _boot_store_and_write():
            store = SqliteStore(tmp_db_path)
            store.create_project("p9-uuid", "p9-folder")

        with pytest.raises(RuntimeError) as exc_info:
            _run_with_deadlock_guard(4.0, _boot_store_and_write)

    assert "database is locked" in str(exc_info.value).lower()

