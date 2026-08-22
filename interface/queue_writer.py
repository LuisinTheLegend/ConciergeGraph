"""
interface/queue_writer.py — SDD-SURVIVAL-02

Fila de Escrita Serializada contra Database Locks.

Thread daemon dedicada que consome operações de gravação de uma fila
thread-safe (queue.Queue), garantindo que apenas uma thread escreva no
SQLite por vez. Elimina completamente erros de "database is locked" em
cenários de concorrência de múltiplos subagentes.

Arquitetura:
  - Conexão física única e persistente na thread escritora (WAL + NORMAL sync)
  - Threads externas enfileiram escritas via execute_write() e bloqueiam
    de forma segura até receberem o resultado via response_queue
  - Sinal de desligamento gracioso via None na fila
"""

import queue
import threading
import sqlite3
from typing import Tuple, Any


class SerializedWriteQueue(threading.Thread):
    """
    Thread daemon dedicada que consome operações de gravação de uma fila thread-safe,
    garantindo que apenas uma thread escreva no SQLite por vez e evitando Database Locks.
    """

    def __init__(self, db_path: str):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.queue: queue.Queue = queue.Queue()

    def run(self):
        # Conexão persistente e única na thread escritora
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        while True:
            task = self.queue.get()
            if task is None:
                # Sinal de desligamento gracioso
                self.queue.task_done()
                break

            query, params, response_queue = task
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                # Retorna ID inserido ou contagem de linhas afetadas
                response_queue.put((True, cursor.lastrowid))
            except Exception as e:
                conn.rollback()
                response_queue.put((False, e))
            finally:
                self.queue.task_done()

        conn.close()

    def execute_write(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> Tuple[bool, Any]:
        """
        Ponto de entrada síncrono para threads externas enfileirarem escritas
        e bloquearem de forma segura até que o resultado seja entregue.
        """
        response_queue: queue.Queue = queue.Queue()
        self.queue.put((query, params, response_queue))
        success, result = response_queue.get()
        return success, result
