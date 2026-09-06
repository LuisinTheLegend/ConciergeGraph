"""
core/database.py — SDD-SURVIVAL-02

SQLite Hybrid Connection Orchestrator.

Manages direct concurrent reads (SELECT) and delegates all mutations
(INSERT, UPDATE, DELETE) to SerializedWriteQueue, ensuring hybrid performance
and absolute stability under WAL mode.

Architectural Pattern:
  - Reads: Local ephemeral connection per query (full concurrency)
  - Writes: Synchronous delegation to dedicated thread (zero locking)
"""

import sqlite3
from typing import Optional

from interface.queue_writer import SerializedWriteQueue


class ConciergeDatabaseManager:
    """
    Manages direct concurrent reads from SQLite file while delegating
    all mutations and write transactions to SerializedWriteQueue.
    """

    def __init__(self, db_path: str, write_queue: Optional[SerializedWriteQueue] = None):
        self.db_path = db_path
        self.write_queue = write_queue
        self._init_tables()

    def _init_tables(self):
        """Creates tables via write queue or direct connection, respecting single-writer rule."""
        self.write_query(
            "CREATE TABLE IF NOT EXISTS test_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "thread_name TEXT, "
            "val INTEGER"
            ");",
        )

    def read_query(self, query: str, params: tuple = ()):
        """Fast concurrent read query directly from database (bypasses write queue)."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
        finally:
            conn.close()

    def execute_write(self, query: str, params: tuple = ()):
        """Safe write operation delegated to serialized writer or direct connection."""
        if self.write_queue is not None:
            return self.write_queue.execute_write(query, params)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            last_id = cursor.lastrowid
            return True, last_id
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def write_query(self, query: str, params: tuple = ()):
        """Safe write query delegating to execute_write."""
        return self.execute_write(query, params)
