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
# SerializedWriteQueue — dedicated write thread
# ---------------------------------------------------------------------------

class SerializedWriteQueue:
    """Queue that serializes ALL SQLite writes in a single thread.

    Architecture:
        - A daemon thread ('sqlite-writer') consumes _WriteJobs from the queue.
        - Each job is executed inside an implicit transaction.
        - In case of error, it rolls back and propagates the exception to the caller.
        - The caller blocks on job.result_event.wait() until completion.

    Lifecycle:
        start() → submit() → ... → stop()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._queue: queue.Queue[Optional[_WriteJob]] = queue.Queue()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="sqlite-writer"
        )
        self._running = False
        self._conn: Optional[sqlite3.Connection] = None

    def start(self) -> None:
        """Starts the worker thread. Idempotent (duplicate calls are no-op)."""
        if self._running:
            logger.debug("SerializedWriteQueue is already running for %s", self._db_path)
            return
        
        self._running = True
        self._thread.start()
        logger.info("SerializedWriteQueue started successfully (db: %s)", self._db_path)

    def is_empty(self) -> bool:
        """Returns True if the write queue has no pending tasks."""
        return self._queue.empty()

    def stop(self, timeout: float = 5.0) -> None:
        """Sends sentinel and waits for the thread to finish.

        Args:
            timeout: Maximum seconds to wait for thread join.
        """
        if not self._running:
            logger.debug("SerializedWriteQueue was already stopped.")
            return
        
        logger.info("Requesting stop of SerializedWriteQueue...")
        self._running = False
        self._queue.put(None)  # sentinel value to break the loop
        self._thread.join(timeout=timeout)
        logger.info("SerializedWriteQueue finished.")

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Queues a _WriteJob and blocks until execution completes.

        Args:
            fn: Callable(conn, *args, **kwargs) to be executed on the writer thread.
            *args: Positional arguments passed to fn.
            **kwargs: Keyword arguments passed to fn.

        Returns:
            The return value of fn.

        Raises:
            RuntimeError: If the queue is not running.
            Any exception thrown by fn is re-raised in the calling thread.
        """
        if not self._running:
            raise RuntimeError("SerializedWriteQueue is not running. Call start() first.")

        job = _WriteJob(fn=fn, args=args, kwargs=kwargs)
        self._queue.put(job)
        
        # Bloqueia até que a thread worker finalize o job
        job.result_event.wait()
        
        if job.error is not None:
            logger.error("Job execution failed: %s", job.error)
            raise job.error
        
        return job.result

    def _worker(self) -> None:
        """Main loop of the writer thread.

        Opens the write connection with WAL+busy_timeout+foreign_keys,
        consumes jobs until receiving sentinel (None), and closes the connection
        in the finally block.
        """
        logger.debug("Worker thread (sqlite-writer) started. Connecting to database...")
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        
        # Performance and robustness settings (Absolute Solidity)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA busy_timeout=5000;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        
        logger.debug("Worker thread configured WAL and busy_timeout successfully.")
        
        try:
            while self._running:
                try:
                    # Timeout curto permite verificar self._running periodicamente
                    job = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                if job is None:
                    # Sentinel received to stop
                    logger.debug("Worker thread received stop sentinel.")
                    break
                
                start_time = time.time()
                try:
                    # Execute the operation
                    job.result = job.fn(self._conn, *job.args, **job.kwargs)
                    self._conn.commit()
                    duration = (time.time() - start_time) * 1000
                    logger.debug("Job executed successfully in %.2fms", duration)
                except Exception as exc:
                    self._conn.rollback()
                    job.error = exc
                    logger.error("Error in write thread (transaction rolled back): %s", exc)
                finally:
                    # Signals the calling thread that we finished
                    job.result_event.set()
        finally:
            if self._conn:
                logger.debug("Closing connection of the worker thread.")
                self._conn.close()


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
