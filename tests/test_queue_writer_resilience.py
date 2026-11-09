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

    def test_t5_unready_worker_handshake_timeout_fails_fast_without_enqueuing(self):
        """T5: worker ainda não sinalizou prontidão (_ready.is_set() == False) e estoura READY_TIMEOUT.
        
        execute_write deve retornar (False, TimeoutError) imediatamente sem empurrar a tarefa
        na fila de um worker não inicializado (fila permanece vazia).
        """
        from unittest.mock import PropertyMock
        qw = SerializedWriteQueue(self.db_path)
        with patch.object(SerializedWriteQueue, "ident", new_callable=PropertyMock(return_value=99999)):
            with patch.object(qw, "is_alive", return_value=True):
                with patch("interface.queue_writer.READY_TIMEOUT_SECONDS", 0.05):
                    ok, err = qw.execute_write("CREATE TABLE t5 (id INT);")
                    self.assertFalse(ok)
                    self.assertIsInstance(err, TimeoutError)
                    self.assertIn("failed to initialize", str(err).lower())
                    self.assertTrue(qw.queue.empty(), "Tarefa NÃO deve ser enfileirada se o worker não estiver pronto")

    def test_t6_batch_fatal_error_notifies_all_batched_callers(self):
        """T6: falha catastrófica durante _execute_batch.
        
        Todos os itens retirados da fila para compor o batch ativo devem receber
        (False, loop_error) em seus response_queues, sem ficar órfãos.
        """
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            qw.execute_write("CREATE TABLE t6 (id INTEGER PRIMARY KEY, v TEXT);")
            
            q1 = queue.Queue()
            q2 = queue.Queue()
            task1 = ("INSERT INTO t6 (v) VALUES ('a');", (), q1)
            task2 = ("INSERT INTO t6 (v) VALUES ('b');", (), q2)
            
            with patch.object(qw, "_execute_batch", side_effect=MemoryError("Simulated catastrophic crash")):
                qw.queue.put(task1)
                qw.queue.put(task2)
                
                res1 = q1.get(timeout=3.0)
                res2 = q2.get(timeout=3.0)
                
                self.assertFalse(res1[0])
                self.assertIsInstance(res1[1], MemoryError)
                self.assertFalse(res2[0])
                self.assertIsInstance(res2[1], MemoryError)
        finally:
            if qw.is_alive():
                qw.queue.put(None)
                qw.join(timeout=3.0)

    def test_t7_expired_deadline_task_skipped_without_executing(self):
        """T7: tarefa cujo deadline já expirou é descartada com TimeoutError sem executar no disco."""
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            qw.execute_write("CREATE TABLE t7 (id INTEGER PRIMARY KEY, v TEXT);")
            
            q = queue.Queue()
            expired_deadline = time.perf_counter() - 10.0
            task = ("INSERT INTO t7 (v) VALUES ('stale');", (), q, expired_deadline)
            qw.queue.put(task)
            
            success, err = q.get(timeout=3.0)
            self.assertFalse(success)
            self.assertIsInstance(err, TimeoutError)
            
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM t7;")
            count = cur.fetchone()[0]
            conn.close()
            self.assertEqual(count, 0, "Query com deadline expirado não deveria ter sido gravada no disco")
        finally:
            if qw.is_alive():
                qw.queue.put(None)
                qw.join(timeout=3.0)

    def test_t8_reader_read_query_does_not_execute_pragma_wal(self):
        """T8: ConciergeDatabaseManager.read_query não executa 'PRAGMA journal_mode=WAL' a cada leitura."""
        from core.database import ConciergeDatabaseManager
        db_mgr = ConciergeDatabaseManager(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE t8 (id INT);")
        conn.commit()
        conn.close()
        
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            db_mgr.read_query("SELECT * FROM t8;")
            
            executed_sql = [call.args[0] for call in mock_conn.execute.call_args_list if call.args]
            self.assertNotIn("PRAGMA journal_mode=WAL;", executed_sql, "read_query não deve executar PRAGMA journal_mode=WAL a cada chamada de leitura")

    def test_t9_busy_timeout_regime_allows_lock_held_for_3s_to_succeed(self):
        """T9: regressão de busy timeout. Outra conexão segura BEGIN IMMEDIATE por ~3s.
        
        Com timeout de regime de 30s (restaurado após handshake), a escrita deve suceder
        após a liberação do lock, sem falhar prematuramente em 1.5s.
        """
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            ok, res = qw.execute_write("CREATE TABLE t9 (id INTEGER PRIMARY KEY, v TEXT);")
            self.assertTrue(ok, f"Setup falhou: {res}")
            
            conn_external = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            conn_external.execute("BEGIN IMMEDIATE;")
            
            lock_released_event = threading.Event()
            
            def _release_lock_after_delay():
                time.sleep(3.0)
                try:
                    conn_external.commit()
                    conn_external.close()
                finally:
                    lock_released_event.set()
            
            releaser = threading.Thread(target=_release_lock_after_delay, daemon=True)
            releaser.start()
            
            start_t = time.perf_counter()
            success, result = qw.execute_write("INSERT INTO t9 (v) VALUES ('held');")
            elapsed = time.perf_counter() - start_t
            
            self.assertTrue(success, f"Escrita deveria ter sucedido após lock liberado, mas falhou com: {result}")
            self.assertGreaterEqual(elapsed, 2.8, "Deveria ter aguardado a liberação do lock (~3s)")
            self.assertLess(elapsed, 10.0, "Não deveria demorar excessivamente além da liberação")
        finally:
            qw.queue.put(None)
            qw.join(timeout=3.0)

    def test_execute_write_before_start_fails_fast_without_handshake_wait(self):
        """1.3: execute_write chamado antes de start() deve falhar imediatamente (<0.2s) com RuntimeError.
        
        Não deve esperar os 10s de READY_TIMEOUT_SECONDS nem retornar TimeoutError.
        """
        qw = SerializedWriteQueue(self.db_path)
        # start() NÃO é chamado
        start_t = time.perf_counter()
        success, err = qw.execute_write("CREATE TABLE t_pre (id INT);")
        elapsed = time.perf_counter() - start_t
        
        self.assertFalse(success)
        self.assertIsInstance(err, RuntimeError)
        self.assertIn("not been started", str(err).lower())
        self.assertLess(elapsed, 0.2, f"Deveria falhar na hora (<0.2s), demorou {elapsed:.2f}s")

    def test_startup_budget_strictly_less_than_ready_timeout(self):
        """1.1: prova por teste que o orçamento de partida é estritamente menor que READY_TIMEOUT_SECONDS."""
        backoff = qw_module.INITIAL_BACKOFF_SECONDS
        total_backoff = 0.0
        for _ in range(qw_module.MAX_CONNECT_RETRIES - 1):
            total_backoff += backoff
            backoff = min(backoff * 2, qw_module.MAX_BACKOFF_SECONDS)
        
        max_startup_budget = (
            qw_module.MAX_CONNECT_RETRIES * qw_module.STARTUP_CONNECT_TIMEOUT_SECONDS
            + total_backoff
        )
        self.assertLess(
            max_startup_budget,
            qw_module.READY_TIMEOUT_SECONDS,
            f"Orçamento de partida ({max_startup_budget:.2f}s) deve ser menor que READY_TIMEOUT_SECONDS ({qw_module.READY_TIMEOUT_SECONDS}s)"
        )

    def test_t10_worker_death_in_loop_fails_waiting_and_subsequent_callers_fast(self):
        """T10: o worker morre por exceção no laço enquanto um chamador espera.
        
        O chamador deve receber (False, ...) em poucos segundos (<5s), e a chamada
        subsequente também (<1s). Mata as mutações Qb e Qg.
        """
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            ok, res = qw.execute_write("CREATE TABLE t10 (id INT);")
            self.assertTrue(ok)
            
            with patch.object(qw, "_execute_single", side_effect=SystemError("Fatal worker loop crash")):
                start_t = time.perf_counter()
                success, err = qw.execute_write("INSERT INTO t10 (id) VALUES (1);")
                elapsed = time.perf_counter() - start_t
                
                self.assertFalse(success)
                self.assertIsInstance(err, Exception)
                self.assertLess(elapsed, 5.0, f"Chamador deveria receber falha rápido (<5.0s), demorou {elapsed:.2f}s")
                
                # Chamada seguinte também deve falhar rápido sem travar
                start_t2 = time.perf_counter()
                success2, err2 = qw.execute_write("INSERT INTO t10 (id) VALUES (2);")
                elapsed2 = time.perf_counter() - start_t2
                
                self.assertFalse(success2)
                self.assertIsInstance(err2, RuntimeError)
                self.assertLess(elapsed2, 1.0, f"Chamada pós-morte deve falhar rápido (<1.0s), demorou {elapsed2:.2f}s")
        finally:
            if qw.is_alive():
                qw.queue.put(None)
                qw.join(timeout=3.0)

    def test_t11_multiple_queued_items_fail_fast_when_loop_dies(self):
        """T11: vários itens na fila quando o laço morre. Nenhum chamador pode ficar pendurado."""
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            ok, res = qw.execute_write("CREATE TABLE t11 (id INT);")
            self.assertTrue(ok)
            
            # Bloqueia a execução temporariamente para acumular chamadas
            barrier = threading.Barrier(4)
            results = []
            
            def _caller(item_id):
                barrier.wait(timeout=3.0)
                r = qw.execute_write("INSERT INTO t11 (id) VALUES (?);", (item_id,))
                results.append((item_id, r))
            
            with patch.object(qw, "_execute_single", side_effect=SystemError("Simulated loop crash")):
                with patch.object(qw, "_execute_batch", side_effect=SystemError("Simulated loop crash")):
                    threads = [threading.Thread(target=_caller, args=(i,), daemon=True) for i in range(1, 4)]
                    for th in threads:
                        th.start()
                    
                    # Libera barreira
                    barrier.wait(timeout=3.0)
                    
                    # Todos os threads devem encerrar em <5.0s
                    for th in threads:
                        th.join(timeout=5.0)
                        self.assertFalse(th.is_alive(), "Thread chamadora não deveria ter travado")
                    
                    self.assertEqual(len(results), 3, "Todos os 3 chamadores devem ter recebido resposta")
                    for item_id, (success, err) in results:
                        self.assertFalse(success)
                        self.assertIsInstance(err, Exception)
        finally:
            if qw.is_alive():
                qw.queue.put(None)
                qw.join(timeout=3.0)

    def test_characterization_inflight_write_may_apply_after_timeout(self):
        """1.4 Teste de caracterização: escrita em voo já iniciada quando o chamador desiste
        continua sendo aplicada no SQLite (não-cancelável).
        """
        qw = SerializedWriteQueue(self.db_path)
        qw.start()
        try:
            ok, res = qw.execute_write("CREATE TABLE t_char (id INT, val TEXT);")
            self.assertTrue(ok)
            
            inflight_entered = threading.Event()

            def _inflight_single(conn, task):
                cursor = conn.cursor()
                cursor.execute(task[0], task[1])
                inflight_entered.set()
                # Simula lentidão na transação/disco após o início da execução (em voo)
                time.sleep(0.3)
                conn.commit()
                task[2].put((True, cursor.lastrowid))

            with patch.object(qw, "_execute_single", side_effect=_inflight_single):
                # Chamador submete tarefa com deadline longo na fila (5s), mas desiste localmente após 0.1s
                resp_q = queue.Queue()
                task = ("INSERT INTO t_char (id, val) VALUES (42, 'committed_after_timeout');", (), resp_q, time.perf_counter() + 5.0)
                qw.queue.put(task)

                # Chamador desiste após 0.1s com timeout
                with self.assertRaises(queue.Empty):
                    resp_q.get(timeout=0.1)

            # Aguarda a thread trabalhadora concluir a gravação que já estava em voo (espera robusta de até 3s)
            committed = False
            for _ in range(30):
                time.sleep(0.1)
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT val FROM t_char WHERE id = 42;")
                row = cur.fetchone()
                conn.close()
                if row is not None and row[0] == "committed_after_timeout":
                    committed = True
                    break

            self.assertTrue(committed, "Escrita em voo deve ter sido persistida no banco após o timeout do chamador")
        finally:
            qw.queue.put(None)
            qw.join(timeout=3.0)




