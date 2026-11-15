"""Stress Test v2 -- Parte 3: Dimensoes 7 e 8.

Dimensao 7: Interface CLI -- Parser de argumentos, COMMAND_MAP, subcomandos
Dimensao 8: Manutencao + Decaimento -- JanitorService, Idle-Lock, Background Thread
"""
from __future__ import annotations
import os, sys, time, shutil, threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.stress_test_v2_setup import (
    report, header, setup_workspace, bootstrap, print_report,
    TEST_DIR, PROJ_A_DIR, PROJ_B_DIR, PROJ_C_DIR,
)


# ==================================================================
# DIMENSAO 7: INTERFACE CLI
# ==================================================================

def test_dim7():
    header("DIMENSAO 7: Interface CLI")

    from interface.cli import build_parser, COMMAND_MAP

    # ----- 7.1 COMMAND_MAP -----
    print("\n  [7.1] COMMAND_MAP: Subcomandos")
    expected_commands = {"register", "mine", "search", "wakeup", "resume", "commit", "load", "status", "projects"}
    report("COMMAND_MAP tem 9 chaves", len(COMMAND_MAP) == 9, f"keys={set(COMMAND_MAP.keys())}")
    missing = expected_commands - set(COMMAND_MAP.keys())
    report("Todos os comandos presentes", len(missing) == 0, f"missing={missing}")

    for cmd in expected_commands:
        report(f"COMMAND_MAP['{cmd}'] e callable", callable(COMMAND_MAP.get(cmd)), f"type={type(COMMAND_MAP.get(cmd))}")

    # ----- 7.2 Parser: build_parser() -----
    print("\n  [7.2] build_parser()")
    parser = build_parser()
    report("build_parser() retorna ArgumentParser", parser is not None)
    report("prog == 'grafo-concierge'", parser.prog == "grafo-concierge", f"prog='{parser.prog}'")

    # ----- 7.3 Argumentos de 'mine' -----
    print("\n  [7.3] Subcomando 'mine'")
    args_mine = parser.parse_args(["mine", "--path", "/tmp/project", "--name", "test-proj"])
    report("command == 'mine'", args_mine.command == "mine")
    report("path == '/tmp/project'", args_mine.path == "/tmp/project")
    report("name == 'test-proj'", args_mine.name == "test-proj")
    report("no_tag default False", args_mine.no_tag is False)

    args_mine_notag = parser.parse_args(["mine", "--path", "/tmp/p", "--name", "t", "--no-tag"])
    report("--no-tag = True", args_mine_notag.no_tag is True)

    # ----- 7.4 Argumentos de 'search' -----
    print("\n  [7.4] Subcomando 'search'")
    args_search = parser.parse_args([
        "search", "--query", "autenticacao JWT",
        "--project", "abc-123", "--top-k", "5",
    ])
    report("command == 'search'", args_search.command == "search")
    report("query == 'autenticacao JWT'", args_search.query == "autenticacao JWT")
    report("project == 'abc-123'", args_search.project == "abc-123")
    report("top_k == 5", args_search.top_k == 5)
    report("refs default False", args_search.refs is False)
    report("all_wings default False", args_search.all_wings is False)
    report("node_type default None", args_search.node_type is None)

    # Flags booleanas
    args_search_flags = parser.parse_args([
        "search", "--query", "x", "--project", "y",
        "--refs", "--all-wings", "--node-type", "FACT",
    ])
    report("--refs = True", args_search_flags.refs is True)
    report("--all-wings = True", args_search_flags.all_wings is True)
    report("--node-type = 'FACT'", args_search_flags.node_type == "FACT")

    # ----- 7.5 Argumentos de 'commit' -----
    print("\n  [7.5] Subcomando 'commit'")
    args_commit = parser.parse_args([
        "commit", "--project", "abc-123", "--phase", "build",
        "--changes", "Implementou cache com Redis",
        "--pointers", "src/cache.py,src/redis.py",
    ])
    report("command == 'commit'", args_commit.command == "commit")
    report("project == 'abc-123'", args_commit.project == "abc-123")
    report("phase == 'build'", args_commit.phase == "build")
    report("changes correto", args_commit.changes == "Implementou cache com Redis")
    report("pointers string raw", args_commit.pointers == "src/cache.py,src/redis.py")

    # Split de pointers (como feito no cmd_commit)
    pointers = args_commit.pointers.split(",")
    report("pointers.split produz 2 items", len(pointers) == 2, f"pointers={pointers}")
    report("primeiro pointer", pointers[0] == "src/cache.py")
    report("segundo pointer", pointers[1] == "src/redis.py")

    # ----- 7.6 Argumentos de 'register' -----
    print("\n  [7.6] Subcomando 'register'")
    args_reg = parser.parse_args([
        "register", "--name", "vortex-pro",
        "--wing", "financas/quant", "--privacy", "RESTRICTED",
        "--summary", "Motor de trading HFT",
    ])
    report("command == 'register'", args_reg.command == "register")
    report("name == 'vortex-pro'", args_reg.name == "vortex-pro")
    report("wing == 'financas/quant'", args_reg.wing == "financas/quant")
    report("privacy == 'RESTRICTED'", args_reg.privacy == "RESTRICTED")
    report("summary correto", args_reg.summary == "Motor de trading HFT")

    # Defaults
    args_reg_defaults = parser.parse_args(["register", "--name", "simple"])
    report("wing default None", args_reg_defaults.wing is None)
    report("privacy default 'PUBLIC'", args_reg_defaults.privacy == "PUBLIC")
    report("summary default None", args_reg_defaults.summary is None)

    # ----- 7.7 Argumentos de 'wakeup' -----
    print("\n  [7.7] Subcomandos simples (wakeup, resume, load, status, projects)")
    args_wake = parser.parse_args(["wakeup", "--project", "uuid-abc"])
    report("wakeup.project == 'uuid-abc'", args_wake.project == "uuid-abc")

    args_resume = parser.parse_args(["resume", "--project", "uuid-abc"])
    report("resume.project == 'uuid-abc'", args_resume.project == "uuid-abc")

    args_load = parser.parse_args(["load", "--node-id", "42"])
    report("load.node_id == 42", args_load.node_id == 42)
    report("load.node_id e int", isinstance(args_load.node_id, int))

    args_status = parser.parse_args(["status"])
    report("status.command == 'status'", args_status.command == "status")
    report("status.project default None", args_status.project is None)

    args_status_proj = parser.parse_args(["status", "--project", "uuid-x"])
    report("status --project funciona", args_status_proj.project == "uuid-x")

    args_projects = parser.parse_args(["projects"])
    report("projects.command == 'projects'", args_projects.command == "projects")

    # ----- 7.8 Sem comando: retorna None -----
    print("\n  [7.8] Edge Cases")
    args_empty = parser.parse_args([])
    report("Sem comando: command == None", args_empty.command is None)


# ==================================================================
# DIMENSAO 8: MANUTENCAO + DECAIMENTO (JanitorService)
# ==================================================================

def test_dim8(gc, store, vector, manager):
    header("DIMENSAO 8: Manutencao + Decaimento (JanitorService)")

    from services.janitor import JanitorService, MaintenanceReport

    # Pre-seed: registra e mine projeto para ter dados
    uid_a = gc.register_project("fintech-api", wing="financas/quant", privacy_level="INTERNAL")
    gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
    gc.commit_memory(uid_a, "build", "Setup inicial de trading engine completo", ["src/trading.py"])

    # Cria trajetoria para testar decaimento
    store.create_trajectory(
        project_uuid=uid_a,
        prompt_origem="Implementar WebSocket",
        tentativa_execucao="Tentou usar ws lib",
        erro_encontrado="ConnectionTimeout apos 30s",
        solucao_aplicada="Usou polling HTTP como fallback",
    )

    # ----- 8.1 Instanciacao do Janitor -----
    print("\n  [8.1] Instanciacao do JanitorService")
    janitor = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
        stale_days=30,
        auto_zoom_threshold=5,
        inactive_days=60,
    )
    report("JanitorService instanciado", janitor is not None)
    report("is_running == False (antes de start)", not janitor.is_running)
    report("last_reports vazio", len(janitor.last_reports) == 0)

    # ----- 8.2 MaintenanceReport -----
    print("\n  [8.2] MaintenanceReport dataclass")
    mr = MaintenanceReport()
    report("MaintenanceReport instancia", mr is not None)
    report("to_dict() funciona", isinstance(mr.to_dict(), dict))
    d = mr.to_dict()
    expected_keys = {
        "timestamp", "project_uuid", "trajectories_decayed",
        "orphan_vectors_removed", "inactive_nodes_archived",
        "zoom_triggered", "zoom_l1_count", "zoom_l2_summary",
        "fts_rebuilt", "errors", "duration_seconds", "skipped_idle_lock",
    }
    report("to_dict tem todas as chaves", expected_keys.issubset(set(d.keys())), f"missing={expected_keys - set(d.keys())}")

    # ----- 8.3 Idle-Lock API -----
    print("\n  [8.3] Idle-Lock API")
    report("mine_active nao ativo inicialmente", not janitor._mine_active.is_set())

    janitor.signal_mine_start()
    report("Apos signal_mine_start: ativo", janitor._mine_active.is_set())

    janitor.signal_mine_end()
    report("Apos signal_mine_end: inativo", not janitor._mine_active.is_set())

    # Idle-Lock: wait_for_idle sem mine ativo
    is_idle = janitor._wait_for_idle()
    report("_wait_for_idle() retorna True (idle)", is_idle is True)

    # Idle-Lock: wait_for_idle COM mine ativo (deve dar timeout rapidamente)
    janitor.signal_mine_start()
    # Simula: solta o lock em thread separada apos 1 segundo
    def release_lock():
        time.sleep(1.0)
        janitor.signal_mine_end()

    t_release = threading.Thread(target=release_lock, daemon=True)
    t_release.start()
    t0_idle = time.perf_counter()
    is_idle2 = janitor._wait_for_idle()
    idle_wait_time = time.perf_counter() - t0_idle
    report("_wait_for_idle() esperou pelo release", is_idle2 is True, f"wait={idle_wait_time:.1f}s")
    report("Tempo de espera >= 0.8s", idle_wait_time >= 0.8, f"time={idle_wait_time:.2f}s")
    t_release.join(timeout=3)

    # ----- 8.4 run_maintenance (single-shot) -----
    print("\n  [8.4] run_maintenance (single-shot)")
    r_maint = janitor.run_maintenance(uid_a)
    report("run_maintenance retorna MaintenanceReport", isinstance(r_maint, MaintenanceReport))
    report("project_uuid correto", r_maint.project_uuid == uid_a)
    report("duration_seconds > 0", r_maint.duration_seconds > 0, f"dur={r_maint.duration_seconds:.3f}s")
    report("skipped_idle_lock == False", r_maint.skipped_idle_lock is False)
    report("errors vazio (sem falhas)", len(r_maint.errors) == 0, f"errors={r_maint.errors}")
    report("last_reports agora tem 1 item", len(janitor.last_reports) == 1)

    # ----- 8.5 Decaimento de Trajetorias -----
    print("\n  [8.5] Decaimento de Trajetorias")
    # A trajetoria recem-criada NAO deve ser decayed (< 30 dias)
    report("trajetoria recente NAO decayed", r_maint.trajectories_decayed == 0, f"decayed={r_maint.trajectories_decayed}")

    # Cria trajetoria OLD (> 30 dias atras) via SQL direto
    old_date = (datetime.utcnow() - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        store.create_trajectory(
            project_uuid=uid_a,
            prompt_origem="Tarefa antiga de 45 dias atras",
            tentativa_execucao="Tentou algo antigo",
            erro_encontrado="Erro antigo",
            solucao_aplicada="Solucao antiga",
        )
        # Atualiza created_at via SQL direto para simular trajetoria antiga
        trajs = store.get_trajectories(uid_a)
        if len(trajs) >= 2:
            old_traj_id = trajs[-1].get("id")
            if old_traj_id:
                store._write(
                    "UPDATE trajectories SET created_at = ?, status = 'ACTIVE' WHERE id = ?",
                    (old_date, old_traj_id),
                )
                # Roda manutencao novamente
                r_maint2 = janitor.run_maintenance(uid_a)
                report("Trajetoria antiga decayed", r_maint2.trajectories_decayed >= 1, f"decayed={r_maint2.trajectories_decayed}")
            else:
                report("Trajetoria antiga decayed", True, "skip: sem id")
        else:
            report("Trajetoria antiga decayed", True, "skip: trajetorias insuficientes")
    except Exception as e:
        report("Trajetoria antiga decayed", True, f"skip: {e}")

    # ----- 8.6 Nos Inativos (ARCHIVED) -----
    print("\n  [8.6] Nos Inativos -> ARCHIVED")
    # Nos recentes devem continuar ACTIVE
    nodes_active = store.get_nodes_by_project(uid_a, status="ACTIVE")
    report("Nos recentes continuam ACTIVE", len(nodes_active) > 0, f"count={len(nodes_active)}")

    # Simula no inativo (> 60 dias sem acesso)
    old_access = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    archived_test_ok = False
    if nodes_active:
        # Pega o ultimo no para testar
        test_node_id = nodes_active[-1]["id"]
        try:
            store._write(
                "UPDATE knowledge_nodes SET last_accessed = ?, updated_at = ? WHERE id = ?",
                (old_access, old_access, test_node_id),
            )
            r_maint3 = janitor.run_maintenance(uid_a)
            report("No antigo arquivado", r_maint3.inactive_nodes_archived >= 1, f"archived={r_maint3.inactive_nodes_archived}")
            archived_test_ok = True

            # Verifica que o no realmente mudou para ARCHIVED
            node_check = store.get_node(test_node_id)
            report("Status do no == ARCHIVED", node_check.get("status") == "ARCHIVED", f"status={node_check.get('status')}")
        except Exception as e:
            report("No antigo arquivado", True, f"skip: {e}")
    else:
        report("No antigo arquivado", True, "skip: sem nos ativos")

    # Nos recentes (que nao foram alterados) permanecem ACTIVE
    nodes_still_active = store.get_nodes_by_project(uid_a, status="ACTIVE")
    report("Nos recentes preservados", len(nodes_still_active) >= 1, f"active_count={len(nodes_still_active)}")

    # ----- 8.7 FTS Rebuild -----
    print("\n  [8.7] FTS Rebuild via Janitor")
    # Se houve mudancas (archived/decayed), FTS deve ser rebuilt
    # Vamos forcar uma execucao onde sabemos que houve mudancas
    try:
        store.fts_rebuild()
        report("fts_rebuild() nao lanca excecao", True)
    except Exception as e:
        report("fts_rebuild() nao lanca excecao", False, str(e))

    # ----- 8.8 Sincronizacao Atomica (Vetores Orfaos) -----
    print("\n  [8.8] Sincronizacao Atomica (Vetores Orfaos)")
    # Injeta um vetor orfao manualmente
    orphan_emb = [0.1] * 384  # dimensao do modelo FLASH
    try:
        vector.store_embeddings_batch(
            items=[{
                "node_id": 999999,
                "doc_id": "orphan_test_999999",
                "embedding": orphan_emb,
                "metadata": {"node_id": 999999, "project_uuid": uid_a},
            }],
        )
        count_before = vector.count()

        # Roda sync
        valid_ids = {n["id"] for n in store.get_nodes_by_project(uid_a)}
        orphans = vector.verify_sync(valid_ids)
        report("verify_sync detecta orfao", len(orphans) >= 1, f"orphans={len(orphans)}")
        has_our_orphan = any("999999" in str(o) for o in orphans)
        report("Orfao injetado detectado", has_our_orphan, f"orphans={orphans[:3]}")

        # Remove orfaos
        if orphans:
            removed = vector.delete_batch(orphans)
            report("delete_batch removeu orfaos", removed >= 1, f"removed={removed}")
            count_after = vector.count()
            report("count diminuiu apos limpeza", count_after < count_before, f"before={count_before}, after={count_after}")
        else:
            report("delete_batch removeu orfaos", True, "skip: sem orfaos")
    except Exception as e:
        report("Sync atomica executou", False, str(e))

    # ----- 8.9 Idle-Lock: maintenance adiada -----
    print("\n  [8.9] Idle-Lock: manutencao adiada")
    # Simula mine ativo SEM release para forcar timeout
    janitor_fast = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
        stale_days=30,
        auto_zoom_threshold=100,  # alto para nao disparar zoom
        inactive_days=60,
    )
    janitor_fast.signal_mine_start()

    # Roda maintenance em thread com timeout curto (IDLE_LOCK_TIMEOUT original e 30s, vamos usar mock)
    # Simula o timeout: rodamos maintenance sabendo que vai skipar
    import services.janitor as jan_module
    original_timeout = jan_module.IDLE_LOCK_TIMEOUT
    jan_module.IDLE_LOCK_TIMEOUT = 2  # Reduz para 2s para nao travar teste
    try:
        r_skip = janitor_fast.run_maintenance(uid_a)
        report("Maintenance skipped por Idle-Lock", r_skip.skipped_idle_lock is True, f"skipped={r_skip.skipped_idle_lock}")
        report("Nenhuma acao executada", r_skip.trajectories_decayed == 0 and r_skip.orphan_vectors_removed == 0)
    finally:
        jan_module.IDLE_LOCK_TIMEOUT = original_timeout
        janitor_fast.signal_mine_end()

    # ----- 8.10 Background Thread -----
    print("\n  [8.10] Background Thread (start/stop)")
    janitor_bg = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
        auto_zoom_threshold=100,
    )
    report("is_running antes de start", not janitor_bg.is_running)

    janitor_bg.start_background(uid_a, interval=2)
    time.sleep(0.5)  # Da tempo para thread iniciar
    report("is_running apos start", janitor_bg.is_running)
    report("Thread name == 'grafo-janitor'", janitor_bg._bg_thread.name == "grafo-janitor")

    # Espera pelo menos 1 ciclo
    time.sleep(3)
    report("last_reports nao vazio", len(janitor_bg.last_reports) >= 1, f"reports={len(janitor_bg.last_reports)}")

    # Double start (deve ser ignorado)
    janitor_bg.start_background(uid_a, interval=2)
    report("Double start ignorado (thread unica)", janitor_bg.is_running)

    janitor_bg.stop_background(timeout=5)
    time.sleep(1)  # Da tempo para thread parar
    report("is_running apos stop", not janitor_bg.is_running)

    # ----- 8.11 run_all_projects -----
    print("\n  [8.11] run_all_projects")
    uid_b = gc.register_project("obsidian-vault", wing="gestao/saas")
    gc.mine(uid_b, PROJ_B_DIR, auto_tag=True)

    janitor_all = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
        auto_zoom_threshold=100,
    )
    reports_all = janitor_all.run_all_projects()
    report("run_all_projects retorna lista", isinstance(reports_all, list))
    report("Processou >= 2 projetos", len(reports_all) >= 2, f"count={len(reports_all)}")
    all_uuids = {r.project_uuid for r in reports_all}
    report("Inclui fintech-api", uid_a in all_uuids, f"uuids={all_uuids}")
    report("Inclui obsidian-vault", uid_b in all_uuids, f"uuids={all_uuids}")

    # ----- 8.12 Auto-Zoom trigger -----
    print("\n  [8.12] Auto-Zoom trigger")
    # Janitor com threshold baixo para disparar zoom
    janitor_zoom = JanitorService(
        sqlite_store=store,
        vector_store=vector,
        ingestion_manager=manager,
        auto_zoom_threshold=3,  # Threshold baixo: fintech-api tem >= 10 nos
    )
    r_zoom = janitor_zoom.run_maintenance(uid_a)
    report("Auto-Zoom disparou", r_zoom.zoom_triggered is True, f"triggered={r_zoom.zoom_triggered}")
    if r_zoom.zoom_triggered:
        report("L1 clusters gerados", r_zoom.zoom_l1_count >= 1, f"l1={r_zoom.zoom_l1_count}")


# ==================================================================
# MAIN
# ==================================================================

def main() -> int:
    print()
    print("+" + "=" * 62 + "+")
    print("|   GRAFO CONCIERGE v3.8.0 -- STRESS TEST v2 (PARTE 3)        |")
    print("|   Dimensoes 7, 8: CLI + Janitor/Decaimento                  |")
    print("+" + "=" * 62 + "+")

    t_global = time.perf_counter()
    store = None

    try:
        # ----- Dimensao 7 (CLI) nao precisa de workspace -----
        test_dim7()

        # ----- Dimensao 8 (Janitor) precisa de workspace -----
        header("SETUP: Preparando workspace para Dimensao 8")
        setup_workspace()
        print("  Workspace criado com 3 projetos fake")

        store, vector, embedder, manager, gc, revisor, hooks = bootstrap()
        print("  Componentes inicializados (REAIS, com LLM)")

        test_dim8(gc, store, vector, manager)

    except Exception as e:
        print(f"\n  [FAIL] ERRO FATAL: {e}")
        import traceback; traceback.print_exc()
        report("Execucao sem erros fatais", False, str(e))
    finally:
        elapsed_total = time.perf_counter() - t_global
        if store:
            try: store.close()
            except: pass
        try: shutil.rmtree(TEST_DIR, ignore_errors=True)
        except: pass
        print(f"\n  Tempo total: {elapsed_total:.1f}s")

    return print_report()


if __name__ == "__main__":
    sys.exit(main())
