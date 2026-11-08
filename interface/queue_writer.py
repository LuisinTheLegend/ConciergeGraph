"""
interface/queue_writer.py — SDD-SURVIVAL-10

Serialized Write Queue with Opportunistic Auto-Batching and Atomic Single-Item Fallback.

Dedicated daemon thread consuming write operations from a thread-safe
queue (queue.Queue), guaranteeing that only one thread writes to SQLite at any time.
Completely eliminates "database is locked" errors in multi-subagent concurrency scenarios.

Architecture (SDD-SURVIVAL-10):
  - Single persistent physical connection on writer thread (WAL + synchronous=NORMAL)
  - Resilient startup with exponential backoff on OperationalError ("database is locked"/"busy")
  - Readiness handshake via threading.Event
  - Non-blocking execution loop in execute_write with liveness and startup error checks
  - Fail-fast handling of worker thread termination
  - Opportunistic Auto-Batching: drains up to 50 pending items non-blocking (get_nowait)
  - Atomic Single-Item Fallback: rolls back batch and executes individually upon failure
  - Graceful shutdown signal via None sentinel in queue
"""

import logging
import queue
import sqlite3
import threading
import time
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

_MAX_BATCH_SIZE = 50

# Constantes nomeadas de resiliência e concorrência (F4-029)
MAX_CONNECT_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 0.05
MAX_BACKOFF_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 10.0
EXECUTE_TIMEOUT_SECONDS = 30.0
POLL_INTERVAL_SECONDS = 0.05


class SerializedWriteQueue(threading.Thread):
    """
    Dedicated daemon thread consuming write operations from a thread-safe queue,
    guaranteeing that only one thread writes to SQLite at a time, avoiding Database Locks.

    Supports Opportunistic Auto-Batching (SDD-SURVIVAL-10): when items accumulate in queue,
    groups them into a single transaction to maximize throughput. Upon batch failure,
    applies Atomic Single-Item Fallback to rescue healthy operations.
    """

    def __init__(self, db_path: str):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.queue: queue.Queue = queue.Queue()
        self._ready = threading.Event()
        self._startup_error: Optional[Exception] = None
        self._is_stopped = False

    def run(self):
        # ── Step 0: Resilient Connection Setup with Exponential Backoff ──
        conn = None
        backoff = INITIAL_BACKOFF_SECONDS
        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                self._ready.set()
                break
            except sqlite3.OperationalError as e:
                err_msg = str(e).lower()
                if "database is locked" in err_msg or "database is busy" in err_msg or "locked" in err_msg:
                    logger.warning(
                        "SerializedWriteQueue startup connection attempt %d/%d failed with '%s'. Retrying in %.3fs...",
                        attempt,
                        MAX_CONNECT_RETRIES,
                        e,
                        backoff,
                    )
                    if conn:
                        try:
                            conn.close()
                        except Exception:
                            logger.debug("Failed closing conn after retry failure", exc_info=True)
                        conn = None
                    if attempt == MAX_CONNECT_RETRIES:
                        self._startup_error = e
                        self._ready.set()
                        self._fail_all_pending(e)
                        return
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                else:
                    logger.error("SerializedWriteQueue startup failed with unexpected OperationalError: %s", e)
                    self._startup_error = e
                    self._ready.set()
                    self._fail_all_pending(e)
                    return
            except Exception as e:
                logger.error("SerializedWriteQueue startup failed with unexpected error: %s", e)
                self._startup_error = e
                self._ready.set()
                self._fail_all_pending(e)
                return

        # ── Main Worker Processing Loop ───────────────────────────────────
        try:
            while True:
                # ── Step 1: Await first item (blocking) ────────────────────
                task = self.queue.get()
                if task is None:
                    # Graceful shutdown sentinel
                    self.queue.task_done()
                    break

                # ── Step 2: Opportunistic Accumulation (non-blocking) ──────
                batch = [task]
                while len(batch) < _MAX_BATCH_SIZE:
                    try:
                        next_item = self.queue.get_nowait()
                        if next_item is None:
                            # Sentinel found during drain; re-queue for next cycle
                            self.queue.put(None)
                            break
                        batch.append(next_item)
                    except queue.Empty:
                        break

                # ── Step 3: Resilient Execution ────────────────────────────
                if len(batch) == 1:
                    # Single item: direct execution without explicit transaction overhead
                    self._execute_single(conn, batch[0])
                else:
                    # Batch: grouped transaction with atomic fallback
                    self._execute_batch(conn, batch)

                # Mark all items in batch as processed
                for _ in batch:
                    self.queue.task_done()
        except Exception as loop_error:
            logger.error("SerializedWriteQueue daemon thread loop encountered fatal error: %s", loop_error, exc_info=True)
            self._fail_all_pending(loop_error)
            raise
        finally:
            self._is_stopped = True
            if conn:
                try:
                    conn.close()
                except Exception:
                    logger.debug("Error closing sqlite connection during worker termination", exc_info=True)

    def _fail_all_pending(self, error: Exception) -> None:
        """Drains any tasks remaining in self.queue and notifies their response_queue with (False, error)."""
        while True:
            try:
                task = self.queue.get_nowait()
                if task is not None:
                    _, _, resp_q = task
                    resp_q.put((False, error))
                self.queue.task_done()
            except queue.Empty:
                break

    def _execute_single(
        self, conn: sqlite3.Connection, task: Tuple
    ) -> None:
        """Executes a single write operation in its own implicit atomic transaction."""
        query, params, response_queue = task
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            response_queue.put((True, cursor.lastrowid))
        except Exception as e:
            conn.rollback()
            response_queue.put((False, e))

    def _execute_batch(
        self, conn: sqlite3.Connection, batch: list
    ) -> None:
        """
        Attempts to write all batch items within a single grouped transaction.
        If it fails, applies Single-Item Fallback to rescue healthy operations.
        """
        try:
            conn.execute("BEGIN IMMEDIATE;")
            results = []
            for task in batch:
                query, params, response_queue = task
                cursor = conn.cursor()
                cursor.execute(query, params)
                results.append((response_queue, cursor.lastrowid))
            conn.commit()
            # Batch transaction succeeded: notify all callers
            for response_queue, lastrowid in results:
                response_queue.put((True, lastrowid))
        except Exception as batch_error:
            # ── Atomic Single-Item Fallback ────────────────────────────
            logger.warning(
                "Batch transaction failed (%d items): %s. "
                "Starting Single-Item Fallback.",
                len(batch),
                batch_error,
            )
            try:
                conn.rollback()
            except Exception:
                logger.debug("Defensive rollback failed", exc_info=True)

            # Execute each item individually
            for task in batch:
                self._execute_single(conn, task)

    def execute_write(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> Tuple[bool, Any]:
        """
        Synchronous entry point for external threads to enqueue writes
        and block safely until the result is delivered.
        """
        # Checa erro prévio de inicialização
        if self._startup_error is not None:
            return False, self._startup_error

        # Aguarda sinalização do handshake de inicialização se a thread estiver rodando
        if self.is_alive() and not self._ready.is_set():
            self._ready.wait(timeout=READY_TIMEOUT_SECONDS)

        if self._startup_error is not None:
            return False, self._startup_error

        if not self.is_alive():
            err = RuntimeError("SerializedWriteQueue worker thread is not alive.")
            return False, err

        response_queue: queue.Queue = queue.Queue()
        self.queue.put((query, params, response_queue))

        deadline = time.perf_counter() + EXECUTE_TIMEOUT_SECONDS
        while time.perf_counter() < deadline:
            try:
                success, result = response_queue.get(timeout=POLL_INTERVAL_SECONDS)
                return success, result
            except queue.Empty:
                if self._startup_error is not None:
                    return False, self._startup_error
                if not self.is_alive():
                    return False, RuntimeError("SerializedWriteQueue worker thread died while awaiting response.")

        return False, TimeoutError(f"execute_write timed out after {EXECUTE_TIMEOUT_SECONDS}s.")
