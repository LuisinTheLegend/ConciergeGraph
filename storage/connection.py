"""
storage/connection.py - Grafo Concierge v3.8.0 (Absolute Solidity)

Thread-safe SQLite connection management with Serialized Queue.

Responsibilities:
    - _WriteJob: dataclass that encapsulates a pending write operation.
    - SerializedWriteQueue: dedicated thread that processes all writes
      sequentially, eliminating the 'database is locked' error.
    - ConnectionManager: provides thread-local read connections (one per
      thread via threading.local) and a single serialized write connection.
      Configures WAL mode, busy_timeout=5000ms and foreign_keys=ON on ALL
      created connections.
"""

from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator, Optional

logger = logging.getLogger("grafo-concierge.connection")


# ---------------------------------------------------------------------------
# _WriteJob — atomic unit of write in the queue
# ---------------------------------------------------------------------------

@dataclass
class _WriteJob:
    """Encapsulates a pending write operation in the serialized queue.

    Attributes:
        fn: Callable that receives (sqlite3.Connection, *args, **kwargs).
        args: Positional arguments for fn.
        kwargs: Keyword arguments for fn.
        result_event: Event signaled when execution finishes.
        result: Return value of fn (filled by worker thread).
        error: Exception caught during execution (None if success).
    """
    fn: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    result_event: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: Optional[Exception] = None


# ---------------------------------------------------------------------------
# SerializedWriteQueue — Resilience & Regime Constants (SDD / F4-031)
# ---------------------------------------------------------------------------

MAX_CONNECT_RETRIES: int = 5
STARTUP_CONNECT_TIMEOUT_SECONDS: float = 1.5
INITIAL_BACKOFF_SECONDS: float = 0.05
MAX_BACKOFF_SECONDS: float = 1.0
READY_TIMEOUT_SECONDS: float = 10.0
POLL_INTERVAL_SECONDS: float = 0.05
REGIME_BUSY_TIMEOUT_MS: int = 5000


# ---------------------------------------------------------------------------
# SerializedWriteQueue — dedicated write thread
# ---------------------------------------------------------------------------

class SerializedWriteQueue:
    """Queue that serializes ALL SQLite writes in a single thread.

    Architecture:
        - A daemon thread ('sqlite-writer') consumes _WriteJobs from the queue.
        - Startup handshake retries transient 'database is locked'/'database is busy'
          errors with bounded exponential backoff, then restores regime
          PRAGMA busy_timeout=5000.
        - Each job is executed inside an implicit transaction.
        - In case of error, it rolls back and propagates the exception to the caller.
        - The caller waits in a short liveness-polling loop (no total execution
          timeout for running jobs) until completion or worker death.

    Lifecycle:
        start() → submit() → ... → stop()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._queue: queue.Queue[Optional[_WriteJob]] = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="sqlite-writer"
        )
        self._started = False
        self._stopped = False
        self._running = False
        self._ready = threading.Event()
        self._startup_error: Optional[BaseException] = None
        self._fatal_error: Optional[BaseException] = None
        self._conn: Optional[sqlite3.Connection] = None

    def start(self) -> None:
        """Starts the worker thread and waits for the startup handshake.

        Idempotent: duplicate calls while running are no-op.

        Raises:
            RuntimeError: If the startup handshake fails or times out, chained
                with the underlying startup error.
        """
        if (
            self._started
            and self._thread.is_alive()
            and self._startup_error is None
            and self._fatal_error is None
        ):
            logger.debug("SerializedWriteQueue is already running for %s", self._db_path)
            return

        if not self._started:
            self._started = True
            self._running = True
            self._thread.start()

        ready_ok = self._ready.wait(timeout=READY_TIMEOUT_SECONDS)
        if not ready_ok:
            timeout_err = RuntimeError(
                f"SerializedWriteQueue failed to complete startup handshake within {READY_TIMEOUT_SECONDS}s"
            )
            self._startup_error = timeout_err
            self._running = False
            raise timeout_err

        if self._startup_error is not None:
            raise RuntimeError(
                f"SerializedWriteQueue startup failed: {self._startup_error}"
            ) from self._startup_error

        logger.info("SerializedWriteQueue started successfully (db: %s)", self._db_path)

    def is_empty(self) -> bool:
        """Returns True if the write queue has no pending tasks."""
        return self._queue.empty()

    def stop(self, timeout: float = 5.0) -> None:
        """Sends sentinel and waits for the thread to finish.

        Args:
            timeout: Maximum seconds to wait for thread join.
        """
        if not self._started or self._stopped:
            logger.debug("SerializedWriteQueue was already stopped.")
            return

        logger.info("Requesting stop of SerializedWriteQueue...")
        self._stopped = True
        self._running = False
        self._queue.put(None)  # sentinel value to break the loop
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("SerializedWriteQueue finished.")

    def _build_worker_dead_error(self) -> RuntimeError:
        """Builds a RuntimeError chained with the underlying startup or fatal cause."""
        cause = (
            self._fatal_error
            or self._startup_error
            or RuntimeError("sqlite-writer thread terminated unexpectedly")
        )
        err = RuntimeError(f"write worker died: {cause}")
        err.__cause__ = cause
        return err

    def _drain_pending_with_error(self, cause: BaseException) -> None:
        """Drains all pending jobs from the queue and notifies their callers with error."""
        while True:
            try:
                pending = self._queue.get_nowait()
            except queue.Empty:
                break
            if pending is None:
                continue
            if not pending.result_event.is_set():
                err = RuntimeError(f"write worker died: {cause}")
                err.__cause__ = cause
                pending.error = err
                pending.result_event.set()

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Queues a _WriteJob and blocks until execution completes or worker dies.

        Args:
            fn: Callable(conn, *args, **kwargs) to be executed on the writer thread.
            *args: Positional arguments passed to fn.
            **kwargs: Keyword arguments passed to fn.

        Returns:
            The return value of fn.

        Raises:
            RuntimeError: If the queue was not started, was stopped, or if the
                worker thread died during startup or execution.
            Any exception thrown by fn is re-raised in the calling thread.
        """
        if not self._started or self._stopped:
            raise RuntimeError("SerializedWriteQueue is not running. Call start() first.")

        if (
            self._startup_error is not None
            or self._fatal_error is not None
            or not self._thread.is_alive()
        ):
            raise self._build_worker_dead_error()

        job = _WriteJob(fn=fn, args=args, kwargs=kwargs)
        self._queue.put(job)

        # Wait in short liveness-polling increments without imposing a total job timeout
        while not job.result_event.wait(timeout=POLL_INTERVAL_SECONDS):
            if not self._thread.is_alive() and not job.result_event.is_set():
                raise self._build_worker_dead_error()

        if job.error is not None:
            logger.error("Job execution failed: %s", job.error)
            raise job.error

        return job.result

    def _worker(self) -> None:
        """Main loop of the writer thread.

        Opens the write connection with bounded startup retry on lock contention,
        restores regime PRAGMAs (WAL, busy_timeout=5000, foreign_keys=ON),
        consumes jobs until receiving sentinel (None), and drains pending jobs
        if an unexpected fatal error terminates the loop.
        """
        logger.debug("Worker thread (sqlite-writer) started. Connecting to database...")
        conn: Optional[sqlite3.Connection] = None

        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                conn = sqlite3.connect(
                    self._db_path, timeout=STARTUP_CONNECT_TIMEOUT_SECONDS
                )
                conn.row_factory = sqlite3.Row

                # Handshake PRAGMAs + restore regime busy_timeout=5000ms (Invariant 1)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(f"PRAGMA busy_timeout={REGIME_BUSY_TIMEOUT_MS};")
                conn.execute("PRAGMA foreign_keys=ON;")
                self._conn = conn
                break
            except sqlite3.OperationalError as exc:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception as close_exc:
                        logger.debug("Error closing failed startup connection: %s", close_exc)
                    conn = None

                msg_lower = str(exc).lower()
                is_lock_err = (
                    "database is locked" in msg_lower or "database is busy" in msg_lower
                )
                if is_lock_err and attempt < MAX_CONNECT_RETRIES:
                    backoff = min(
                        INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1)),
                        MAX_BACKOFF_SECONDS,
                    )
                    logger.warning(
                        "SerializedWriteQueue startup attempt %d/%d failed with '%s'. Retrying in %.3fs...",
                        attempt,
                        MAX_CONNECT_RETRIES,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue

                logger.error(
                    "SerializedWriteQueue startup failed on attempt %d/%d: %s",
                    attempt,
                    MAX_CONNECT_RETRIES,
                    exc,
                )
                self._startup_error = exc
                self._running = False
                self._drain_pending_with_error(exc)
                self._ready.set()
                return
            except BaseException as exc:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception as close_exc:
                        logger.debug("Error closing failed startup connection: %s", close_exc)
                    conn = None

                logger.error("SerializedWriteQueue unexpected startup failure: %s", exc)
                self._startup_error = exc
                self._running = False
                self._drain_pending_with_error(exc)
                self._ready.set()
                return

        logger.debug("Worker thread configured WAL and busy_timeout successfully.")
        self._ready.set()

        try:
            while self._running:
                try:
                    job = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if job is None:
                    logger.debug("Worker thread received stop sentinel.")
                    break

                start_time = time.time()
                try:
                    job.result = job.fn(self._conn, *job.args, **job.kwargs)
                    self._conn.commit()
                    duration = (time.time() - start_time) * 1000
                    logger.debug("Job executed successfully in %.2fms", duration)
                except Exception as exc:
                    try:
                        self._conn.rollback()
                    except BaseException as rb_exc:
                        logger.error(
                            "Fatal error rolling back transaction in sqlite-writer: %s",
                            rb_exc,
                        )
                        raise rb_exc from exc
                    job.error = exc
                    logger.error("Error in write thread (transaction rolled back): %s", exc)
                    job.result_event.set()
                else:
                    job.result_event.set()
        except BaseException as fatal_exc:
            logger.error("Fatal error in sqlite-writer loop: %s", fatal_exc)
            self._fatal_error = fatal_exc
            self._running = False
        finally:
            self._running = False
            if self._fatal_error is not None:
                self._drain_pending_with_error(self._fatal_error)
            elif not self._stopped:
                self._drain_pending_with_error(
                    RuntimeError("sqlite-writer terminated unexpectedly")
                )
            if self._conn is not None:
                logger.debug("Closing connection of the worker thread.")
                try:
                    self._conn.close()
                except Exception as close_exc:
                    logger.debug("Error closing worker connection: %s", close_exc)
                self._conn = None


# ---------------------------------------------------------------------------
# ConnectionManager — orchestrates read and write
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages SQLite connections with read/write separation.

    Reads: One connection per thread (threading.local), readonly.
    Writes: Delegated to SerializedWriteQueue (single thread).

    All connections are configured with:
        - PRAGMA journal_mode=WAL
        - PRAGMA busy_timeout=5000
        - PRAGMA foreign_keys=ON

    Args:
        db_path: Absolute or relative path to the .db file.
                 Parent directory is automatically created if it doesn't exist.
    """

    PRAGMAS: list[str] = [
        "PRAGMA journal_mode=WAL;",
        "PRAGMA busy_timeout=5000;",
        "PRAGMA foreign_keys=ON;",
    ]

    def __init__(self, db_path: str) -> None:
        self._db_path = str(Path(db_path).expanduser().absolute())
        
        # Creates the parent directory if it doesn't exist
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local connections for concurrent reading (without locking)
        self._local = threading.local()
        
        # Serialized queue for isolated writes
        self._write_queue = SerializedWriteQueue(self._db_path)

        # Global and thread-safe registry of read connections to prevent leaks
        self._read_conns_lock = threading.Lock()
        self._read_connections: list[sqlite3.Connection] = []

    def is_write_queue_empty(self) -> bool:
        """Returns True if the SerializedWriteQueue is empty (no pending jobs)."""
        return self._write_queue.is_empty()

    def start(self) -> None:
        """Starts the SerializedWriteQueue. Call after __init__."""
        self._write_queue.start()

    def close(self) -> None:
        """Stops the write queue and closes the read connections of all threads."""
        self._write_queue.stop()
        with self._read_conns_lock:
            for conn in self._read_connections:
                try:
                    conn.close()
                    logger.debug("Read connection closed successfully.")
                except Exception as e:
                    logger.warning("Failed to close read connection: %s", e)
            self._read_connections.clear()
        
        # Resets the thread local
        self._local = threading.local()

    def get_read_connection(self) -> sqlite3.Connection:
        """Returns the read connection of the current thread (creates if necessary).

        Returns:
            sqlite3.Connection configured with row_factory=sqlite3.Row.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            logger.debug("Creating new read connection for the current thread.")
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            for pragma in self.PRAGMAS:
                conn.execute(pragma)
            self._local.conn = conn
            with self._read_conns_lock:
                self._read_connections.append(conn)
        return conn

    @contextmanager
    def read(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for read operations.

        Yields:
            sqlite3.Connection of the current thread.
        """
        yield self.get_read_connection()

    def write(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Delegates a write operation to the SerializedWriteQueue.

        Args:
            fn: Callable(conn, *args, **kwargs).
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Return value of fn.
        """
        return self._write_queue.submit(fn, *args, **kwargs)

    def execute_raw_read(self, sql: str, params: tuple = ()) -> list[dict]:
        """Executes a read SQL query and returns list of dicts.

        Args:
            sql: SQL query (SELECT).
            params: Parameters for binding.

        Returns:
            List of dictionaries (each row is a dict).
        """
        with self.read() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
