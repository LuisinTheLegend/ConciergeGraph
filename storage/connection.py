"""
storage/connection.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Gerenciamento de conexões SQLite thread-safe com Fila Serializada.

Responsabilidades:
    - _WriteJob: dataclass que encapsula uma operação de escrita pendente.
    - SerializedWriteQueue: thread dedicada que processa todas as escritas
      de forma sequencial, eliminando o erro 'database is locked'.
    - ConnectionManager: fornece conexões de leitura thread-local (uma por
      thread via threading.local) e uma única conexão de escrita serializada.
      Configura WAL mode, busy_timeout=5000ms e foreign_keys=ON em TODAS
      as conexões criadas.
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
# _WriteJob — unidade atômica de escrita na fila
# ---------------------------------------------------------------------------

@dataclass
class _WriteJob:
    """Encapsula uma operação de escrita pendente na fila serializada.

    Attributes:
        fn: Callable que recebe (sqlite3.Connection, *args, **kwargs).
        args: Argumentos posicionais para fn.
        kwargs: Argumentos nomeados para fn.
        result_event: Event sinalizado quando a execução termina.
        result: Valor de retorno de fn (preenchido pela worker thread).
        error: Exceção capturada durante a execução (None se sucesso).
    """
    fn: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    result_event: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: Optional[Exception] = None


# ---------------------------------------------------------------------------
# SerializedWriteQueue — thread dedicada de escrita
# ---------------------------------------------------------------------------

class SerializedWriteQueue:
    """Fila que serializa TODAS as escritas SQLite em uma única thread.

    Arquitetura:
        - Uma thread daemon ('sqlite-writer') consome _WriteJobs da fila.
        - Cada job é executado dentro de uma transação implícita.
        - Em caso de erro, faz rollback e propaga a exceção ao chamador.
        - O chamador bloqueia em job.result_event.wait() até conclusão.

    Ciclo de vida:
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
        """Inicia a thread worker. Idempotente (chamadas duplicadas são no-op)."""
        if self._running:
            logger.debug("SerializedWriteQueue já está em execução para %s", self._db_path)
            return
        
        self._running = True
        self._thread.start()
        logger.info("SerializedWriteQueue iniciada com sucesso (db: %s)", self._db_path)

    def is_empty(self) -> bool:
        """Retorna True se a fila de escrita não tem tarefas pendentes."""
        return self._queue.empty()

    def stop(self, timeout: float = 5.0) -> None:
        """Envia sentinel e aguarda a thread finalizar.

        Args:
            timeout: Segundos máximos de espera pelo join da thread.
        """
        if not self._running:
            logger.debug("SerializedWriteQueue já estava parada.")
            return
        
        logger.info("Solicitando parada da SerializedWriteQueue...")
        self._running = False
        self._queue.put(None)  # sentinel value to break the loop
        self._thread.join(timeout=timeout)
        logger.info("SerializedWriteQueue finalizada.")

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Enfileira um _WriteJob e bloqueia até a execução completar.

        Args:
            fn: Callable(conn, *args, **kwargs) a ser executado na writer thread.
            *args: Argumentos posicionais passados para fn.
            **kwargs: Argumentos nomeados passados para fn.

        Returns:
            O valor de retorno de fn.

        Raises:
            RuntimeError: Se a fila não estiver rodando.
            Qualquer exceção lançada por fn é re-levantada no thread chamador.
        """
        if not self._running:
            raise RuntimeError("SerializedWriteQueue não está em execução. Chame start() primeiro.")

        job = _WriteJob(fn=fn, args=args, kwargs=kwargs)
        self._queue.put(job)
        
        # Bloqueia até que a thread worker finalize o job
        job.result_event.wait()
        
        if job.error is not None:
            logger.error("Falha na execução do job submetido: %s", job.error)
            raise job.error
        
        return job.result

    def _worker(self) -> None:
        """Loop principal da thread writer.

        Abre a conexão de escrita com WAL+busy_timeout+foreign_keys,
        consome jobs até receber sentinel (None), e fecha a conexão
        no bloco finally.
        """
        logger.debug("Worker thread (sqlite-writer) iniciada. Conectando ao banco...")
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        
        # Configurações de performance e robustez (Absolute Solidity)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA busy_timeout=5000;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        
        logger.debug("Worker thread configurou WAL e busy_timeout com sucesso.")
        
        try:
            while self._running:
                try:
                    # Timeout curto permite verificar self._running periodicamente
                    job = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                if job is None:
                    # Recebido sentinel para terminar
                    logger.debug("Worker thread recebeu sentinel de parada.")
                    break
                
                start_time = time.time()
                try:
                    # Executa a operação
                    job.result = job.fn(self._conn, *job.args, **job.kwargs)
                    self._conn.commit()
                    duration = (time.time() - start_time) * 1000
                    logger.debug("Job executado com sucesso em %.2fms", duration)
                except Exception as exc:
                    self._conn.rollback()
                    job.error = exc
                    logger.error("Erro na thread de escrita (transaction rolled back): %s", exc)
                finally:
                    # Sinaliza a thread chamadora de que terminamos
                    job.result_event.set()
        finally:
            if self._conn:
                logger.debug("Fechando conexão da worker thread.")
                self._conn.close()


# ---------------------------------------------------------------------------
# ConnectionManager — orquestra leitura e escrita
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Gerencia conexões SQLite com separação leitura/escrita.

    Leituras: Uma conexão por thread (threading.local), readonly.
    Escritas: Delegadas à SerializedWriteQueue (thread única).

    Todas as conexões são configuradas com:
        - PRAGMA journal_mode=WAL
        - PRAGMA busy_timeout=5000
        - PRAGMA foreign_keys=ON

    Args:
        db_path: Caminho absoluto ou relativo para o arquivo .db.
                 O diretório pai é criado automaticamente se não existir.
    """

    PRAGMAS: list[str] = [
        "PRAGMA journal_mode=WAL;",
        "PRAGMA busy_timeout=5000;",
        "PRAGMA foreign_keys=ON;",
    ]

    def __init__(self, db_path: str) -> None:
        self._db_path = str(Path(db_path).expanduser().absolute())
        
        # Cria o diretório pai caso não exista
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Conexões thread-local para leitura concorrente (sem bloqueio)
        self._local = threading.local()
        
        # Fila serializada para escritas isoladas
        self._write_queue = SerializedWriteQueue(self._db_path)

        # Registro global e thread-safe de conexões de leitura para prevenir vazamentos
        self._read_conns_lock = threading.Lock()
        self._read_connections: list[sqlite3.Connection] = []

    def is_write_queue_empty(self) -> bool:
        """Retorna True se a SerializedWriteQueue está vazia (sem jobs pendentes)."""
        return self._write_queue.is_empty()

    def start(self) -> None:
        """Inicia a SerializedWriteQueue. Chamar após __init__."""
        self._write_queue.start()

    def close(self) -> None:
        """Para a fila de escrita e fecha as conexões de leitura de todas as threads."""
        self._write_queue.stop()
        with self._read_conns_lock:
            for conn in self._read_connections:
                try:
                    conn.close()
                    logger.debug("Conexão de leitura fechada com sucesso.")
                except Exception as e:
                    logger.warning("Falha ao fechar conexão de leitura: %s", e)
            self._read_connections.clear()
        
        # Reseta o thread local
        self._local = threading.local()

    def get_read_connection(self) -> sqlite3.Connection:
        """Retorna a conexão de leitura da thread atual (cria se necessário).

        Returns:
            sqlite3.Connection configurada com row_factory=sqlite3.Row.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            logger.debug("Criando nova conexão de leitura para a thread atual.")
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
        """Context manager para operações de leitura.

        Yields:
            sqlite3.Connection da thread atual.
        """
        yield self.get_read_connection()

    def write(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Delega uma operação de escrita para a SerializedWriteQueue.

        Args:
            fn: Callable(conn, *args, **kwargs).
            *args: Argumentos posicionais.
            **kwargs: Argumentos nomeados.

        Returns:
            Valor de retorno de fn.
        """
        return self._write_queue.submit(fn, *args, **kwargs)

    def execute_raw_read(self, sql: str, params: tuple = ()) -> list[dict]:
        """Executa uma query SQL de leitura e retorna lista de dicts.

        Args:
            sql: Query SQL (SELECT).
            params: Parâmetros para binding.

        Returns:
            Lista de dicionários (cada row é um dict).
        """
        with self.read() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
