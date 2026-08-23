"""
tests/test_queue_writer_batching.py — SDD-SURVIVAL-10

Suíte TDD de estresse para validar o Auto-Batching Oportunista
e o Fallback Atômico de Item Único da SerializedWriteQueue.

Cenários cobertos:
  1. Vazão concorrente: 30 inserções rápidas são todas persistidas com sucesso.
  2. Fallback atômico: uma falha de chave duplicada no lote não descarta
     os itens saudáveis — eles são resgatados individualmente.
"""

import unittest
import tempfile
import os
import sqlite3
import time
from interface.queue_writer import SerializedWriteQueue
from core.database import ConciergeDatabaseManager


class TestQueueWriterBatching(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.write_queue = SerializedWriteQueue(self.db_path)
        self.write_queue.start()
        self.db_manager = ConciergeDatabaseManager(self.db_path, self.write_queue)

        # Cria uma tabela de teste com uma chave primária rígida para simular erros de constraint
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS test_batch_table ("
            "id INTEGER PRIMARY KEY, name TEXT UNIQUE"
            ");"
        )
        # Dá um tempo para garantir a criação física antes do fluxo concorrente
        time.sleep(0.1)

    def tearDown(self):
        self.write_queue.queue.put(None)
        self.write_queue.join()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_opportunistic_batch_throughput(self):
        """Valida que múltiplas inserções concorrentes são salvas com sucesso em modo batch"""
        num_items = 30

        # Enfileira as inserções rapidamente para forçar o acúmulo na fila
        for i in range(num_items):
            self.db_manager.write_query(
                "INSERT INTO test_batch_table (id, name) VALUES (?, ?);",
                (i, f"item_{i}")
            )

        # Pequena pausa síncrona para permitir o esvaziamento da fila
        time.sleep(0.3)

        # Verifica se todos os registros físicos foram gravados corretamente em disco
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_batch_table;")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, num_items)

    def test_single_item_fallback_on_integrity_error(self):
        """Provoca uma falha de chave duplicada no lote e valida se itens saudáveis sobrevivem"""
        # Garante um registro prévio na tabela
        self.db_manager.write_query("INSERT INTO test_batch_table (id, name) VALUES (100, 'unique_anchor');")
        time.sleep(0.1)

        # Prepara um lote concorrente:
        # Item 1: Válido (id 101)
        # Item 2: Inválido (id 100 - Duplicará a chave primária e quebrará a transação do SQLite)
        # Item 3: Válido (id 102)
        self.db_manager.write_query("INSERT INTO test_batch_table (id, name) VALUES (101, 'salvável_1');")
        self.db_manager.write_query("INSERT INTO test_batch_table (id, name) VALUES (100, 'causador_de_erro_chave_duplicada');")
        self.db_manager.write_query("INSERT INTO test_batch_table (id, name) VALUES (102, 'salvável_2');")

        # Pausa para dar tempo ao Fallback Atômico processar e isolar as escritas
        time.sleep(0.3)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Recupera os dados gravados
        cursor.execute("SELECT id, name FROM test_batch_table ORDER BY id ASC;")
        records = cursor.fetchall()
        conn.close()

        # O registro inválido (id 100 com nome duplicador) deve ter sido revertido e descartado,
        # mas os dois registros irmãos saudáveis (101 e 102) DEVEM estar persistidos no banco!
        ids_presentes = [r[0] for r in records]
        self.assertIn(101, ids_presentes)
        self.assertIn(102, ids_presentes)
        self.assertNotIn("causador_de_erro_chave_duplicada", [r[1] for r in records])

        # Placar final deve conter a âncora inicial (100) + os 2 itens que foram resgatados pelo fallback
        self.assertEqual(len(records), 3)
