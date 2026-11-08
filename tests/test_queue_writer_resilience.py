"""
tests/test_queue_writer_resilience.py — Testes de Resiliência da SerializedWriteQueue (F4-029)

Valida a correção de F4-029:
- T1: sqlite3.connect falha persistentemente com OperationalError ('database is locked')
      -> execute_write deve falhar rápido (<5s), retornando (False, ...), sem travar o chamador.
- T2: sqlite3.connect falha 2 vezes e sucede na 3ª
      -> worker sobe, executa escrita com sucesso (True, ...) e logs registram 2 retries em WARNING.
- T3: thread worker morre após inicialização
      -> chamadas subsequentes e pendentes a execute_write falham rápido sem travar.
- T4: caminho normal sem falha continua inalterado com mesmo throughput.
"""

import os
import queue
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

import pytest

import interface.queue_writer as qw_module
from interface.queue_writer import SerializedWriteQueue


class TestQueueWriterResilience(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_qw_resilience_")
        self.db_path = os.path.join(self.temp_dir, "test_resilience.db")

    def tearDown(self):
        # Limpeza de arquivos temporários
        for ext in ("", "-wal", "-shm"):
            p = self.db_path + ext
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass

    def test_t1_connect_persistent_failure_fails_fast_without_hanging(self):
        """T1: sqlite3.connect falha persistentemente com 'database is locked'.

        execute_write deve falhar rápido (bem abaixo do timeout do teste), retornando (False, ...),
        sem pendurar a thread requisitante.
        """
        qw = SerializedWriteQueue(self.db_path)

        with patch("interface.queue_writer.sqlite3.connect", side_effect=sqlite3.OperationalError("database is locked")):
            qw.start()

            start_t = time.perf_counter()
            # Chama execute_write em thread separada com timeout estrito de 5s para não pendurar o runner
            result_container = []
            def _caller():
                res = qw.execute_write("CREATE TABLE t1 (id INT);")
                result_container.append(res)

            th = threading.Thread(target=_caller, daemon=True)
            th.start()
            th.join(timeout=5.0)

            elapsed = time.perf_counter() - start_t

            # Se th ainda estiver vivo após 5s, o código antigo travou no response_queue.get()
            self.assertFalse(th.is_alive(), f"execute_write travou indefinidamente (esperou {elapsed:.2f}s)")
            self.assertTrue(len(result_container) == 1, "execute_write não retornou resultado")
            success, err = result_container[0]
            self.assertFalse(success, "execute_write deveria ter retornado (False, ...)")
            self.assertIsInstance(err, Exception, "Resultado com erro deve ser uma Exception")
            self.assertLess(elapsed, 5.0, f"Tempo decorrido ({elapsed:.2f}s) deve ser inferior a 5.0s")

    def test_t2_connect_retry_and_eventual_success(self):
        """T2: sqlite3.connect falha 2 vezes com 'database is locked' e sucede na 3ª.

        O worker deve subir com sucesso após o retry, executar uma escrita e os logs
        devem conter os 2 avisos de retry.
        """
        real_connect = sqlite3.connect

        attempts = [0]
        def _mock_connect(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] <= 2:
                raise sqlite3.OperationalError("database is locked")
            return real_connect(*args, **kwargs)

        qw = SerializedWriteQueue(self.db_path)

        with patch("interface.queue_writer.sqlite3.connect", side_effect=_mock_connect):
            with self.assertLogs("interface.queue_writer", level="WARNING") as log_capture:
                qw.start()
                self.assertTrue(hasattr(qw, "_ready") and isinstance(qw._ready, threading.Event), "SerializedWriteQueue deve possuir Event _ready")
                # Cria tabela para testar escrita
                success, val = qw.execute_write("CREATE TABLE t2 (id INTEGER PRIMARY KEY, v TEXT);")
                self.assertTrue(success, f"Escrita deveria ter sucedido após retry, falhou com: {val}")
                self.assertTrue(qw._ready.is_set(), "Event _ready deve estar sinalizado após startup")

                success2, rowid = qw.execute_write("INSERT INTO t2 (v) VALUES (?);", ("alpha",))
                self.assertTrue(success2, f"Insert deveria ter sucedido: {rowid}")
                self.assertEqual(rowid, 1)

            # Valida que houve pelo menos 2 registros de aviso de retry
            retry_logs = [record for record in log_capture.output if "retry" in record.lower() or "tentativa" in record.lower() or "locked" in record.lower()]
            self.assertGreaterEqual(len(retry_logs), 2, f"Deveria ter registrado pelo menos 2 tentativas nos logs: {log_capture.output}")

        # Encerra thread do worker
        qw.queue.put(None)
        qw.join(timeout=3.0)

    def test_t3_worker_thread_late_death_fails_pending_and_future_fast(self):
        """T3: simula a thread worker morrendo após a inicialização.

        Chamadas subsequentes e itens enfileirados devem falhar rápido sem travar.
        """
        qw = SerializedWriteQueue(self.db_path)
        qw.start()

        # 1. Escrita normal de inicialização para certificar que subiu
        ok, res = qw.execute_write("CREATE TABLE t3 (id INTEGER PRIMARY KEY, name TEXT);")
        self.assertTrue(ok, f"Inicialização falhou: {res}")

        # 2. Força encerramento/morte da thread do worker simulando queda
        qw.queue.put(None)
        qw.join(timeout=3.0)
        self.assertFalse(qw.is_alive(), "Worker deveria ter terminado")

        # 3. Chamada subsequente com worker morto deve falhar rápido sem travar
        start_t = time.perf_counter()
        result_container = []
        def _caller():
            res = qw.execute_write("INSERT INTO t3 (name) VALUES ('beta');")
            result_container.append(res)

        th = threading.Thread(target=_caller, daemon=True)
        th.start()
        th.join(timeout=3.0)
        elapsed = time.perf_counter() - start_t

        self.assertFalse(th.is_alive(), f"Chamada com thread morta travou indefinidamente ({elapsed:.2f}s)")
        self.assertTrue(len(result_container) == 1, "execute_write não retornou")
        success, err = result_container[0]
        self.assertFalse(success, "Deveria ter retornado (False, ...)")
        self.assertIsInstance(err, Exception)
        self.assertLess(elapsed, 3.0, f"Chamada deveria falhar rápido, demorou {elapsed:.2f}s")

    def test_t4_normal_path_unaltered_throughput(self):
        """T4: caminho normal (sem falhas) opera perfeitamente com alto rendimento."""
        qw = SerializedWriteQueue(self.db_path)
        qw.start()

        try:
            ok, res = qw.execute_write("CREATE TABLE t4 (id INTEGER PRIMARY KEY, val TEXT);")
            self.assertTrue(ok, f"Create table falhou: {res}")

            count = 50
            start_t = time.perf_counter()
            for i in range(count):
                ok, rowid = qw.execute_write("INSERT INTO t4 (val) VALUES (?);", (f"val_{i}",))
                self.assertTrue(ok, f"Insert {i} falhou")
                self.assertEqual(rowid, i + 1)
            duration = time.perf_counter() - start_t

            # 50 escritas em fila devem levar menos de 2s em SQLite local
            self.assertLess(duration, 2.0, f"Tempo excessivo para 50 escritas: {duration:.3f}s")
        finally:
            qw.queue.put(None)
            qw.join(timeout=3.0)

