"""
core/database.py — SDD-SURVIVAL-02

Orquestrador de Conexão Híbrida SQLite.

Gerencia leituras concorrentes diretas (SELECT) e delega todas as mutações
(INSERT, UPDATE, DELETE) para a SerializedWriteQueue, garantindo performance
híbrida e estabilidade absoluta em modo WAL.

Padrão arquitetural:
  - Leituras: conexão efêmera local por chamada (concorrência total)
  - Escritas: delegação síncrona para thread dedicada (zero locks)
"""

import sqlite3
from interface.queue_writer import SerializedWriteQueue


class ConciergeDatabaseManager:
    """
    Gerencia a leitura síncrona concorrente direta do arquivo SQLite e
    delega todas as mutações e transações de escrita para a SerializedWriteQueue.
    """

    def __init__(self, db_path: str, write_queue: SerializedWriteQueue):
        self.db_path = db_path
        self.write_queue = write_queue
        self._init_tables()

    def _init_tables(self):
        """Cria tabelas via fila de escrita, respeitando o escritor único."""
        self.write_queue.execute_write(
            "CREATE TABLE IF NOT EXISTS test_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "thread_name TEXT, "
            "val INTEGER"
            ");",
        )

    def read_query(self, query: str, params: tuple = ()):
        """Leitura rápida e concorrente direta do banco (sem usar a fila de escrita)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def write_query(self, query: str, params: tuple = ()):
        """Gravação segura delegada para o executor serializado de escrita."""
        return self.write_queue.execute_write(query, params)
