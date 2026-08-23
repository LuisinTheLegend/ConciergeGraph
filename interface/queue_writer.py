"""
interface/queue_writer.py — SDD-SURVIVAL-10

Fila de Escrita Serializada com Auto-Batching Oportunista e Fallback Atômico.

Thread daemon dedicada que consome operações de gravação de uma fila
thread-safe (queue.Queue), garantindo que apenas uma thread escreva no
SQLite por vez. Elimina completamente erros de "database is locked" em
cenários de concorrência de múltiplos subagentes.

Arquitetura (SDD-SURVIVAL-10):
  - Conexão física única e persistente na thread escritora (WAL + NORMAL sync)
  - Threads externas enfileiram escritas via execute_write() e bloqueiam
    de forma segura até receberem o resultado via response_queue
  - Auto-Batching Oportunista: se a fila tiver backlog, drena até 50 itens
    pendentes sem bloquear (get_nowait) e grava todos em uma única transação
  - Fallback Atômico de Item Único: se a transação em lote falhar, reverte
    e tenta gravar cada item individualmente, resgatando os saudáveis
  - Sinal de desligamento gracioso via None na fila
"""

import queue
import logging
import threading
import sqlite3
from typing import Tuple, Any

logger = logging.getLogger(__name__)

_MAX_BATCH_SIZE = 50


class SerializedWriteQueue(threading.Thread):
    """
    Thread daemon dedicada que consome operações de gravação de uma fila thread-safe,
    garantindo que apenas uma thread escreva no SQLite por vez e evitando Database Locks.

    Suporta Auto-Batching Oportunista (SDD-SURVIVAL-10): quando há acúmulo de
    itens na fila, agrupa-os em uma única transação para maximizar throughput.
    Em caso de falha no lote, aplica Fallback Atômico de Item Único para
    resgatar gravações saudáveis.
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
            # ── Passo 1: Aguardar o primeiro item (bloqueante) ────────
            task = self.queue.get()
            if task is None:
                # Sinal de desligamento gracioso
                self.queue.task_done()
                break

            # ── Passo 2: Acúmulo Oportunista (não-bloqueante) ─────────
            batch = [task]
            while len(batch) < _MAX_BATCH_SIZE:
                try:
                    next_item = self.queue.get_nowait()
                    if next_item is None:
                        # Sinalizador de parada encontrado durante dreno;
                        # devolve à fila para que o próximo ciclo o capture
                        self.queue.put(None)
                        break
                    batch.append(next_item)
                except queue.Empty:
                    break

            # ── Passo 3: Gravação Resiliente ──────────────────────────
            if len(batch) == 1:
                # Item único: execução direta sem overhead de transação explícita
                self._execute_single(conn, batch[0])
            else:
                # Lote: transação agrupada com fallback atômico
                self._execute_batch(conn, batch)

            # Marca todos os itens do lote como processados na fila
            for _ in batch:
                self.queue.task_done()

        conn.close()

    def _execute_single(
        self, conn: sqlite3.Connection, task: Tuple
    ) -> None:
        """Executa uma única gravação em sua própria transação atômica implícita."""
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
        Tenta gravar todos os itens do lote em uma única transação agrupada.
        Se falhar, aplica Single-Item Fallback para resgatar itens saudáveis.
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
            # Transação agrupada bem-sucedida: notifica todos os chamadores
            for response_queue, lastrowid in results:
                response_queue.put((True, lastrowid))
        except Exception as batch_error:
            # ── Fallback Atômico de Item Único ────────────────────
            logger.warning(
                "Falha na transação em lote (%d itens): %s. "
                "Iniciando Single-Item Fallback.",
                len(batch),
                batch_error,
            )
            try:
                conn.rollback()
            except Exception:
                pass  # Rollback defensivo; conexão pode já estar limpa

            # Tenta gravar cada item individualmente
            for task in batch:
                self._execute_single(conn, task)

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

