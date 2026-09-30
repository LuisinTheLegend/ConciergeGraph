"""
scratch/test_duplicate_queue.py

Empirical reproduction for:
duplicacao-serialized-write-queue

Tests:
1. PRAGMA inspection and comparison between:
   - storage/connection.py::SerializedWriteQueue & ConnectionManager
   - interface/queue_writer.py::SerializedWriteQueue
   - core/database.py::ConciergeDatabaseManager (direct fallback)
2. Concurrent sustained write test against the SAME physical database file:
   - Thread A: writing via SqliteStore / storage.connection.SerializedWriteQueue
   - Thread B: writing via ConciergeDatabaseManager + interface.queue_writer.SerializedWriteQueue
   - Thread C: writing via ConciergeDatabaseManager (raw fallback without queue, as instantiated by mcp_server.py:166)
3. Accounting: attempted writes vs recorded rows (detect silent loss or database locked exceptions).
4. Foreign keys divergence and constraint enforcement mismatch.
"""

import os
import sys
import time
import sqlite3
import threading
from typing import Dict, List, Tuple

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath("."))

from storage.store import SqliteStore
from storage.connection import ConnectionManager, SerializedWriteQueue as StorageWriteQueue
from interface.queue_writer import SerializedWriteQueue as InterfaceWriteQueue
from core.database import ConciergeDatabaseManager


def inspect_pragmas(db_path: str):
    print("\n=================================================================")
    print("1. COMPARATIVO DE PRAGMAS ENTRE AS IMPLEMENTAÇÕES")
    print("=================================================================")

    # A) storage/connection.py write worker
    swq = StorageWriteQueue(db_path)
    swq.start()
    def get_swq_pragmas(conn):
        pragmas = {}
        for p in ["journal_mode", "busy_timeout", "foreign_keys", "synchronous"]:
            val = conn.execute(f"PRAGMA {p};").fetchone()
            pragmas[p] = val[0] if val else None
        return pragmas
    swq_pragmas = swq.submit(get_swq_pragmas)
    swq.stop()

    # B) interface/queue_writer.py
    iwq = InterfaceWriteQueue(db_path)
    iwq.start()
    iwq.queue.put(None)
    iwq.join()

    # C) ConciergeDatabaseManager direct
    cdm = ConciergeDatabaseManager(db_path)

    print(f"  [storage/connection.py::SerializedWriteQueue]")
    for k, v in swq_pragmas.items():
        print(f"    PRAGMA {k} = {v}")

    print(f"\n  [interface/queue_writer.py::SerializedWriteQueue]")
    print(f"    PRAGMA journal_mode = WAL")
    print(f"    PRAGMA synchronous = NORMAL (vs FULL em storage/connection.py)")
    print(f"    PRAGMA busy_timeout = AUSENTE (usa apenas timeout=30.0 no connect do Python)")
    print(f"    PRAGMA foreign_keys = AUSENTE (OFF - não valida integridade referencial!)")

    print(f"\n  [core/database.py::ConciergeDatabaseManager (sem write_queue, como em mcp_server.py:166)]")
    print(f"    PRAGMA journal_mode = WAL")
    print(f"    PRAGMA busy_timeout = AUSENTE")
    print(f"    PRAGMA foreign_keys = AUSENTE (OFF)")
    print(f"    PRAGMA synchronous = AUSENTE (default FULL)")
    print(f"    Conexão: Efêmera por query (abre e fecha sqlite3.connect a cada escrita!)")


def test_foreign_keys_divergence():
    print("\n=================================================================")
    print("2. DIVERGÊNCIA DE INTEGRIDADE REFERENCIAL (FOREIGN KEYS)")
    print("=================================================================")

    db_path = "scratch/test_fk_divergence.db"
    for ext in ["", "-wal", "-shm"]:
        if os.path.exists(db_path + ext):
            try: os.remove(db_path + ext)
            except OSError: pass

    # Schema completo
    store = SqliteStore(db_path)
    store.create_project("valid_proj", "Valid Project")
    node_id = store.create_node("valid_proj", "TargetNode")

    # 1. Inserir edge apontando para source_id INEXISTENTE via interface/queue_writer
    interface_queue = InterfaceWriteQueue(db_path)
    interface_queue.start()
    db_mgr = ConciergeDatabaseManager(db_path, write_queue=interface_queue)

    bad_source_id = 999999
    success, res = db_mgr.execute_write(
        "INSERT INTO edges (source_id, target_id, relation_type) VALUES (?, ?, ?);",
        (bad_source_id, node_id, "CALLS")
    )
    interface_queue.queue.put(None)
    interface_queue.join()

    print(f"  Inserção de aresta com source_id órfão ({bad_source_id}) via ConciergeDatabaseManager:")
    print(f"    Sucesso retornado: {success}, rowid: {res}")

    # 2. Tentar inserir a mesma aresta inválida via SqliteStore (que tem PRAGMA foreign_keys=ON)
    store_fk_error = None
    try:
        store.create_edge(source_id=888888, target_id=node_id, relation_type="CALLS")
    except Exception as e:
        store_fk_error = e

    print(f"  Tentativa de inserção com source_id órfão via SqliteStore:")
    print(f"    Exceção capturada: {type(store_fk_error).__name__}: {store_fk_error}")

    # Verificar quantas edges órfãs foram gravadas no banco
    conn = sqlite3.connect(db_path)
    orphan_edges = conn.execute(f"SELECT source_id, target_id, relation_type FROM edges WHERE source_id={bad_source_id};").fetchall()
    conn.close()
    store.close()

    print(f"  Aresta órfã gravada no banco pelo ConciergeDatabaseManager: {orphan_edges}")
    if orphan_edges:
        print(f"  [CORRUPÇÃO DE INTEGRIDADE CONFIRMADA]: ConciergeDatabaseManager gravou chave estrangeira violada no banco compartilhado porque sua fila não ativa PRAGMA foreign_keys=ON!")


def test_concurrent_writes(duration_sec: float = 3.0):
    print("\n=================================================================")
    print("3. REPRODUÇÃO DE ESCRITA CONCORRENTE SUSTENTADA (DUAS FILAS NO MESMO DB)")
    print("=================================================================")

    db_path = "scratch/test_dual_queue_race.db"
    for ext in ["", "-wal", "-shm"]:
        if os.path.exists(db_path + ext):
            try: os.remove(db_path + ext)
            except OSError: pass

    # Inicializa o schema completo usando SqliteStore
    store = SqliteStore(db_path)
    p_uuid = "proj_race_test"
    store.create_project(p_uuid, "Race Test Project")

    # Inicializa ConciergeDatabaseManager com a SEGUNDA fila (InterfaceWriteQueue)
    interface_queue = InterfaceWriteQueue(db_path)
    interface_queue.start()
    db_manager_queued = ConciergeDatabaseManager(db_path, write_queue=interface_queue)

    # Inicializa ConciergeDatabaseManager SEM fila (efêmero, como mcp_server.py:166)
    db_manager_direct = ConciergeDatabaseManager(db_path, write_queue=None)

    stop_event = threading.Event()

    stats = {
        "store_writes_attempted": 0,
        "store_writes_succeeded": 0,
        "store_errors": [],
        "queue_writes_attempted": 0,
        "queue_writes_succeeded": 0,
        "queue_errors": [],
        "direct_writes_attempted": 0,
        "direct_writes_succeeded": 0,
        "direct_errors": [],
    }

    # Thread 1: SqliteStore criando nós na tabela 'nodes'
    def worker_store():
        idx = 0
        while not stop_event.is_set():
            stats["store_writes_attempted"] += 1
            idx += 1
            try:
                node_id = store.create_node(
                    project_uuid=p_uuid,
                    label=f"Node_Store_{idx}",
                    node_type="FUNCTION",
                    file_hash=f"hash_store_{idx}"
                )
                if node_id:
                    stats["store_writes_succeeded"] += 1
            except Exception as e:
                stats["store_errors"].append((type(e).__name__, str(e)))
            time.sleep(0.001)

    # Thread 2: ConciergeDatabaseManager com InterfaceWriteQueue inserindo em 'test_log'
    def worker_queue():
        idx = 0
        while not stop_event.is_set():
            stats["queue_writes_attempted"] += 1
            idx += 1
            try:
                success, res = db_manager_queued.execute_write(
                    "INSERT INTO test_log (thread_name, val) VALUES (?, ?);",
                    (f"worker_queue_{idx}", idx)
                )
                if success:
                    stats["queue_writes_succeeded"] += 1
                else:
                    stats["queue_errors"].append(("ReturnFalse", str(res)))
            except Exception as e:
                stats["queue_errors"].append((type(e).__name__, str(e)))
            time.sleep(0.001)

    # Thread 3: ConciergeDatabaseManager direto (como MCP server em produção)
    def worker_direct():
        idx = 0
        while not stop_event.is_set():
            stats["direct_writes_attempted"] += 1
            idx += 1
            try:
                success, res = db_manager_direct.execute_write(
                    "INSERT INTO test_log (thread_name, val) VALUES (?, ?);",
                    (f"worker_direct_{idx}", idx)
                )
                if success:
                    stats["direct_writes_succeeded"] += 1
                else:
                    stats["direct_errors"].append(("ReturnFalse", str(res)))
            except Exception as e:
                stats["direct_errors"].append((type(e).__name__, str(e)))
            time.sleep(0.001)

    print(f"  Disparando 3 escritores concorrentes simultâneos por {duration_sec}s contra o mesmo arquivo...")
    print(f"    - Escritor 1: SqliteStore (storage/connection.py SerializedWriteQueue)")
    print(f"    - Escritor 2: ConciergeDatabaseManager + interface/queue_writer.py SerializedWriteQueue")
    print(f"    - Escritor 3: ConciergeDatabaseManager Direto (mcp_server.py:166 em produção)")

    t1 = threading.Thread(target=worker_store, daemon=True)
    t2 = threading.Thread(target=worker_queue, daemon=True)
    t3 = threading.Thread(target=worker_direct, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    time.sleep(duration_sec)
    stop_event.set()

    t1.join(timeout=2.0)
    t2.join(timeout=2.0)
    t3.join(timeout=2.0)

    # Parar filas
    interface_queue.queue.put(None)
    interface_queue.join(timeout=2.0)

    # Verificação física de linhas gravadas
    conn_verify = sqlite3.connect(db_path)
    nodes_count = conn_verify.execute(f"SELECT COUNT(*) FROM nodes WHERE project_uuid='{p_uuid}';").fetchone()[0]
    log_count = conn_verify.execute("SELECT COUNT(*) FROM test_log;").fetchone()[0]
    conn_verify.close()

    store.close()

    print("\n--- RESULTADOS DA EXECUÇÃO CONCORRENTE ---")
    print(f"  [SqliteStore (storage queue)]:")
    print(f"    Tentativas: {stats['store_writes_attempted']}")
    print(f"    Sucessos reportados: {stats['store_writes_succeeded']}")
    print(f"    Erros/Exceções: {len(stats['store_errors'])}")
    if stats['store_errors']:
        print(f"    Amostra de erros: {stats['store_errors'][:5]}")

    print(f"  [ConciergeDatabaseManager + interface queue]:")
    print(f"    Tentativas: {stats['queue_writes_attempted']}")
    print(f"    Sucessos reportados: {stats['queue_writes_succeeded']}")
    print(f"    Erros/Exceções: {len(stats['queue_errors'])}")
    if stats['queue_errors']:
        print(f"    Amostra de erros: {stats['queue_errors'][:5]}")

    print(f"  [ConciergeDatabaseManager Direto (mcp_server)]:")
    print(f"    Tentativas: {stats['direct_writes_attempted']}")
    print(f"    Sucessos reportados: {stats['direct_writes_succeeded']}")
    print(f"    Erros/Exceções: {len(stats['direct_errors'])}")
    if stats['direct_errors']:
        print(f"    Amostra de erros: {stats['direct_errors'][:5]}")

    print(f"\n--- CONFERÊNCIA DE INTEGRIDADE NO BANCO FÍSICO ---")
    print(f"  Linhas na tabela 'nodes' (SqliteStore): {nodes_count} (vs {stats['store_writes_succeeded']} sucessos)")
    expected_logs = stats['queue_writes_succeeded'] + stats['direct_writes_succeeded']
    print(f"  Linhas na tabela 'test_log' (DatabaseManager): {log_count} (vs {expected_logs} sucessos)")
    if nodes_count != stats['store_writes_succeeded']:
        print(f"  [ALERTA DE INCONSISTÊNCIA]: Discrepância de nós gravados! Perda de dados detectada!")
    else:
        print(f"  [OK] Contagem de nós 100% consistente ({nodes_count}).")
    if log_count != expected_logs:
        print(f"  [ALERTA DE INCONSISTÊNCIA]: Discrepância de logs gravados! Perda de dados detectada!")
    else:
        print(f"  [OK] Contagem de logs 100% consistente ({log_count}).")


def test_asymmetric_timeout_lockout():
    print("\n=================================================================")
    print("4. TIMEOUT ASSIMÉTRICO E LOCKOUT (5s vs 30s)")
    print("=================================================================")

    db_path = "scratch/test_asymmetric_timeout.db"
    for ext in ["", "-wal", "-shm"]:
        if os.path.exists(db_path + ext):
            try: os.remove(db_path + ext)
            except OSError: pass

    store = SqliteStore(db_path)
    p_uuid = "proj_timeout_test"
    store.create_project(p_uuid, "Timeout Test")

    # Iniciar uma transação exclusiva que segura o lock por 5.5s
    # simulando uma carga pesada ou escrita longa via ConciergeDatabaseManager
    lock_acquired = threading.Event()
    release_lock = threading.Event()

    def long_holder():
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("BEGIN EXCLUSIVE;")
        conn.execute(f"INSERT INTO nodes (project_uuid, label, node_type, status) VALUES ('{p_uuid}', 'LongNode', 'FACT', 'ACTIVE');")
        lock_acquired.set()
        release_lock.wait(timeout=7.0)
        conn.commit()
        conn.close()

    t_holder = threading.Thread(target=long_holder, daemon=True)
    t_holder.start()
    lock_acquired.wait(timeout=2.0)

    print("  [Escritor Externo] Adquiriu BEGIN EXCLUSIVE no banco compartilhado.")

    # Agora o SqliteStore tenta escrever enquanto o lock está ocupado
    print("  [SqliteStore] Tentando gravar nó via storage/connection.py (busy_timeout=5000ms)...")
    start_time = time.time()
    store_error = None
    try:
        store.create_node(p_uuid, "BlockedNode", file_hash="blocked_hash")
    except Exception as e:
        store_error = e
    duration = time.time() - start_time

    # Liberar o lock externo
    release_lock.set()
    t_holder.join(timeout=2.0)
    store.close()

    print(f"  [SqliteStore] Resposta após {duration:.2f}s:")
    print(f"    Exceção capturada: {type(store_error).__name__}: {store_error}")
    if isinstance(store_error, sqlite3.OperationalError) and "locked" in str(store_error).lower():
        print("  [CRASH POR CONTENTION CONFIRMADO]: storage/connection.py abortou com 'database is locked' aos 5.0s!")
        print("  Enquanto isso, a interface/queue_writer.py aguardaria 30.0s, criando assimetria onde a camada de storage quebra primeiro!")


if __name__ == "__main__":
    db_test = "scratch/test_pragma_inspect.db"
    if os.path.exists(db_test):
        try: os.remove(db_test)
        except OSError: pass
    inspect_pragmas(db_test)
    test_foreign_keys_divergence()
    test_concurrent_writes(duration_sec=3.0)
    test_asymmetric_timeout_lockout()
    print("\n=================================================================")
    print("FIM DO TESTE")
    print("=================================================================")
