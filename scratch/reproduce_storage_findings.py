"""
scratch/reproduce_storage_findings.py

Empirical reproduction script for 9 verified findings in storage/ directory.
Tests:
1. SerializedWriteQueue Deadlock on re-entrant / nested writes.
2. ConnectionManager memory leak of dead-thread SQLite connections.
3. SerializedWriteQueue failure to restart after stop() (RuntimeError: threads can only be started once).
4. Contract incompatibility: init_fsm_checkpoints_schema fails silently on SqliteStore / ConnectionManager.
5. GraphLogic._calculate_decay fails with TypeError on ISO timestamps with tzinfo, corrupting score to 0.01.
6. ChromaVectorStore.search leaks across projects when project_uuids is empty (Strict Scoping bypass).
7. ChromaVectorStore.search crashes with ValueError when node_id in metadata is empty or None.
8. Recursive CTE in GraphLogic duplicates nodes reached via multiple paths due to depth in SELECT DISTINCT.
9. Architectural encapsulation breach: SqliteStore lacks semantic facts facade methods, forcing external modules to access private _conn_mgr.
"""

import os
import sys
import time
import queue
import sqlite3
import threading
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from storage.connection import ConnectionManager, SerializedWriteQueue
from storage.store import SqliteStore
from storage.schema import SchemaManager
from storage.logic import GraphLogic
from storage.relational_db import init_fsm_checkpoints_schema
from storage.vector_store import ChromaVectorStore, EmbeddingManager, CHROMADB_AVAILABLE
import storage.semantic_logic as semantic_logic


def test_finding_1_nested_write_deadlock():
    print("\n--- [ACHADO 1] Deadlock em Chamadas de Escrita Reentrante / Aninhadas no SerializedWriteQueue ---")
    db_file = "scratch/test_deadlock.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    conn_mgr = ConnectionManager(db_file)
    conn_mgr.start()

    def inner_write(conn):
        return "inner_done"

    def outer_write(conn):
        print("  [outer_write] Executando no worker thread:", threading.current_thread().name)
        print("  [outer_write] Tentando submeter escrita aninhada...")
        return conn_mgr.write(inner_write)

    result_box = {"status": "pending", "result": None}
    def caller():
        try:
            result_box["result"] = conn_mgr.write(outer_write)
            result_box["status"] = "success"
        except Exception as e:
            result_box["status"] = f"error: {e}"

    t = threading.Thread(target=caller, daemon=True)
    t.start()
    t.join(timeout=1.5)

    if t.is_alive():
        print("  [RESULTADO] Deadlock confirmado! A thread chamadora esta bloqueada em job.result_event.wait().")
        print("  Worker thread name:", conn_mgr._write_queue._thread.name, "is_alive:", conn_mgr._write_queue._thread.is_alive())
        result_box["status"] = "DEADLOCK"
    else:
        print("  [RESULTADO] Retornou:", result_box)

    conn_mgr.close()


def test_finding_2_connection_leak():
    print("\n--- [ACHADO 2] Vazamento de Conexoes SQLite de Threads Finalizadas no ConnectionManager ---")
    db_file = "scratch/test_leak.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    conn_mgr = ConnectionManager(db_file)
    conn_mgr.start()

    initial_conns = len(conn_mgr._read_connections)
    print(f"  Conexoes registradas inicialmente: {initial_conns}")

    def worker_thread():
        conn = conn_mgr.get_read_connection()
        conn.execute("SELECT 1").fetchall()

    threads = []
    num_threads = 5
    for i in range(num_threads):
        time.sleep(0.05)
        t = threading.Thread(target=worker_thread)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"  Todas as {num_threads} threads foram finalizadas (is_alive = False).")
    active_threads = [t.is_alive() for t in threads]
    print(f"  Status is_alive das threads: {active_threads}")

    accumulated_conns = len(conn_mgr._read_connections)
    print(f"  Conexoes retidas em _read_connections apos threads morrerem: {accumulated_conns}")
    print(f"  Quantidade de conexoes zumbis vazadas em memoria: {accumulated_conns}")
    
    conn_mgr.close()


def test_finding_3_queue_restart_failure():
    print("\n--- [ACHADO 3] Falha Critica ao Reiniciar SerializedWriteQueue (RuntimeError) ---")
    db_file = "scratch/test_restart.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    queue_writer = SerializedWriteQueue(db_file)
    queue_writer.start()
    print("  Fila iniciada pela primeira vez. is_alive:", queue_writer._thread.is_alive())
    queue_writer.stop()
    print("  Fila parada via stop(). is_alive:", queue_writer._thread.is_alive())

    print("  Tentando reiniciar via start()...")
    try:
        queue_writer.start()
        print("  Reiniciou com sucesso!")
    except RuntimeError as e:
        print(f"  [EXCECAO CAPTURADA]: {type(e).__name__}: {e}")


def test_finding_4_contract_incompatibility_relational_db():
    print("\n--- [ACHADO 4] Incompatibilidade de Contrato: init_fsm_checkpoints_schema falha silenciosamente ---")
    db_file = "scratch/test_fsm_schema.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    store = SqliteStore(db_file)
    print("  SqliteStore inicializado.")

    print("  Chamando init_fsm_checkpoints_schema(store)...")
    res = init_fsm_checkpoints_schema(store)
    print(f"  Retorno de init_fsm_checkpoints_schema: {res}")

    with store._conn_mgr.read() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fsm_checkpoints'")
        table = cursor.fetchone()
    print(f"  Tabela 'fsm_checkpoints' existe no banco? {table is not None}")

    store.close()


def test_finding_5_decay_tz_typeerror():
    print("\n--- [ACHADO 5] Falha de Tipo em _calculate_decay com Timestamp ISO Aware (Degradacao para 0.01) ---")
    db_file = "scratch/test_decay.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    conn_mgr = ConnectionManager(db_file)
    conn_mgr.start()
    logic = GraphLogic(conn_mgr)

    now_iso = datetime.now(timezone.utc).isoformat()
    print(f"  Testando commit gerado agora ha 0 segundos: '{now_iso}'")
    
    score = logic._calculate_decay(now_iso)
    print(f"  Score calculado: {score}")
    print(f"  Score esperado para commit de agora: ~1.0")
    print(f"  Score retornado e igual ao RECENCY_MIN_SCORE (0.01)? {score == logic.RECENCY_MIN_SCORE}")

    conn_mgr.close()


def test_finding_6_cross_project_search_leak():
    print("\n--- [ACHADO 6] Vazamento Cross-Project em ChromaVectorStore.search com project_uuids=[] ---")
    if not CHROMADB_AVAILABLE:
        print("  ChromaDB nao disponivel, pulando.")
        return

    chroma_dir = "scratch/test_chroma_leak"
    store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="test_leak")
    
    dummy_vec = [0.1] * 384
    store.store_embedding(
        doc_id="node_101",
        embedding=dummy_vec,
        metadata={"node_id": 101, "project_uuid": "proj_secret_999", "node_type": "FACT"}
    )

    results = store.search(
        query_embedding=dummy_vec,
        project_uuids=[],
        filters={"node_type": "FACT"},
        top_k=5
    )

    print(f"  Busca com project_uuids=[] retornou {len(results)} resultados!")
    for r in results:
        print(f"    Vazou: doc_id={r.doc_id}, project_uuid={r.project_uuid}, node_id={r.node_id}")

    store.reset_collection()


def test_finding_7_node_id_empty_crash():
    print("\n--- [ACHADO 7] Crash ValueError em ChromaVectorStore.search quando node_id e None ou string vazia ---")
    if not CHROMADB_AVAILABLE:
        print("  ChromaDB nao disponivel, pulando.")
        return

    chroma_dir = "scratch/test_chroma_crash"
    store = ChromaVectorStore(persist_dir=chroma_dir, collection_name="test_crash")

    dummy_vec = [0.1] * 384
    store.store_embedding(
        doc_id="node_corrupt",
        embedding=dummy_vec,
        metadata={"node_id": None, "project_uuid": "proj_123"}
    )

    try:
        results = store.search(
            query_embedding=dummy_vec,
            project_uuids=["proj_123"],
            top_k=5
        )
        print(f"  Resultados: {results}")
    except ValueError as e:
        print(f"  [EXCECAO CAPTURADA]: {type(e).__name__}: {e}")

    store.reset_collection()


def test_finding_8_cte_duplicate_nodes():
    print("\n--- [ACHADO 8] CTE get_dependency_tree Duplica Nos Quando Ha Multiplos Caminhos ou Ciclos ---")
    db_file = "scratch/test_cte.db"
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except OSError: pass

    store = SqliteStore(db_file)
    p_uuid = "p_test"
    store.create_project(p_uuid, "test_proj")

    id_a = store.create_node(p_uuid, "A")
    id_b = store.create_node(p_uuid, "B")
    id_c = store.create_node(p_uuid, "C")

    store.create_edge(source_id=id_a, target_id=id_b)
    store.create_edge(source_id=id_b, target_id=id_c)
    store.create_edge(source_id=id_a, target_id=id_c)

    dep_tree = store.get_dependency_tree(id_a, max_depth=5)
    print("  Arvore de dependencia para no A:")
    for item in dep_tree:
        print(f"    id={item['id']}, label={item['label']}, depth={item['depth']}")

    c_occurrences = [x for x in dep_tree if x['id'] == id_c]
    print(f"  No C apareceu {len(c_occurrences)} vezes na saida de get_dependency_tree!")

    store.close()


def test_finding_9_semantic_logic_isolation():
    print("\n--- [ACHADO 9] Isolamento de semantic_logic.py e Quebra de Encapsulamento de SqliteStore ---")
    store_methods = [m for m in dir(SqliteStore) if not m.startswith("_")]
    print(f"  Total de metodos publicos em SqliteStore: {len(store_methods)}")
    
    semantic_methods = [m for m in dir(semantic_logic) if not m.startswith("_") and callable(getattr(semantic_logic, m))]
    print(f"  Funcoes de mutacao/leitura em semantic_logic.py: {semantic_methods}")
    
    missing_in_store = [m for m in semantic_methods if not hasattr(SqliteStore, m)]
    print(f"  Funcoes de semantic_logic ausentes na fachada SqliteStore: {missing_in_store}")
    print("  Consequencia: middleware.py (linha 632) eh obrigado a acessar store._conn_mgr.read() diretamente para ler fatos.")


if __name__ == "__main__":
    print("=================================================================")
    print("EXECUCAO DO PROTOCOLO DE AUDITORIA: STORAGE/")
    print("=================================================================")
    test_finding_1_nested_write_deadlock()
    test_finding_2_connection_leak()
    test_finding_3_queue_restart_failure()
    test_finding_4_contract_incompatibility_relational_db()
    test_finding_5_decay_tz_typeerror()
    test_finding_6_cross_project_search_leak()
    test_finding_7_node_id_empty_crash()
    test_finding_8_cte_duplicate_nodes()
    test_finding_9_semantic_logic_isolation()
    print("\n=================================================================")
    print("FIM DA EXECUCAO")
    print("=================================================================")
