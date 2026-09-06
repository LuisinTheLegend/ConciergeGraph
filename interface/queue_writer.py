"""
interface/queue_writer.py — SDD-SURVIVAL-10

Serialized Write Queue with Opportunistic Auto-Batching and Atomic Single-Item Fallback.

Dedicated daemon thread consuming write operations from a thread-safe
queue (queue.Queue), guaranteeing that only one thread writes to SQLite at any time.
Completely eliminates "database is locked" errors in multi-subagent concurrency scenarios.

Architecture (SDD-SURVIVAL-10):
  - Single persistent physical connection on writer thread (WAL + synchronous=NORMAL)
  - External threads enqueue writes via execute_write() and block safely
    until receiving result via response_queue
  - Opportunistic Auto-Batching: if queue has backlog, drains up to 50 pending
    items non-blocking (get_nowait) and executes all within a single transaction
  - Atomic Single-Item Fallback: if batch transaction fails, rolls back and
    executes each item individually, rescuing healthy writes
  - Graceful shutdown signal via None sentinel in queue
"""

import logging
import queue
import sqlite3
import threading
from typing import Any, Tuple

logger = logging.getLogger(__name__)

_MAX_BATCH_SIZE = 50


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

    def run(self):
        # Dedicated persistent connection for writer thread
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

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

        conn.close()

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
                pass  # Defensive rollback

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
        response_queue: queue.Queue = queue.Queue()
        self.queue.put((query, params, response_queue))
        success, result = response_queue.get()
        return success, result
