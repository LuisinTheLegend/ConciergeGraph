"""Stress Test v2 -- Parte 2: Dimensoes 4, 5 e 6.

Dimensao 4: Agents (RevisorCritico) -- Auditoria, Reranking, Contaminacao
Dimensao 5: Interface MCP (GrafoConciergeServer) -- Handlers unitarios
Dimensao 6: Interface ActionHooks -- Ciclo de vida reativo
"""
from __future__ import annotations
import os, sys, time, shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.stress_test_v2_setup import (
    report, header, setup_workspace, bootstrap, print_report,
    TEST_DIR, PROJ_A_DIR, PROJ_B_DIR, PROJ_C_DIR,
)


# ==================================================================
# DIMENSAO 4: AGENTS (RevisorCritico)
# ==================================================================

def test_dim4(revisor):
    header("DIMENSAO 4: Agents (RevisorCritico)")

    # ----- 4.1 Auditoria: Commit Valido -----
    print("\n  [4.1] Auditoria de Commit")
    draft_ok = {
        "phase": "build",
        "technical_changes": "Refatorou TradingEngine adicionando momentum strategy com janela movel de 20 periodos",
        "updated_pointers": ["src/trading.py", "src/utils.py"],
        "source_wing": "financas/quant",
    }
    r1 = revisor.audit(draft_ok)
    report("Commit valido aprovado", r1.approved, f"reason='{r1.reason[:60]}'")
    report("AuditResult.to_dict() funciona", "approved" in r1.to_dict(), f"keys={list(r1.to_dict().keys())}")

    # ----- 4.2 Commit Vazio -----
    draft_empty = {
        "phase": "build",
        "technical_changes": "",
        "updated_pointers": ["a.py"],
    }
    r2 = revisor.audit(draft_empty)
    report("Commit vazio rejeitado", not r2.approved, f"reason='{r2.reason[:60]}'")
    report("Motivo menciona 'vazio'", "vazio" in r2.reason.lower(), f"reason='{r2.reason[:80]}'")

    # ----- 4.3 Commit com technical_changes apenas espacos -----
    draft_spaces = {
        "phase": "build",
        "technical_changes": "     \t\n   ",
        "updated_pointers": ["a.py"],
    }
    r3 = revisor.audit(draft_spaces)
    report("Commit com espacos rejeitado", not r3.approved, f"reason='{r3.reason[:60]}'")

    # ----- 4.4 Commit Muito Curto -----
    draft_short = {
        "phase": "done",
        "technical_changes": "fix",
        "updated_pointers": ["a.py"],
    }
    r4 = revisor.audit(draft_short)
    report("Commit muito curto rejeitado", not r4.approved, f"reason='{r4.reason[:80]}'")
    report("Motivo menciona 'curto'", "curto" in r4.reason.lower(), f"reason='{r4.reason[:80]}'")

    # ----- 4.5 Commit sem Ponteiros -----
    draft_no_ptr = {
        "phase": "build",
        "technical_changes": "Implementou autenticacao JWT com refresh tokens completa",
        "updated_pointers": [],
    }
    r5 = revisor.audit(draft_no_ptr)
    report("Commit sem ponteiros rejeitado", not r5.approved, f"reason='{r5.reason[:80]}'")
    report("Motivo menciona 'ponteiro'", "ponteiro" in r5.reason.lower(), f"reason='{r5.reason[:80]}'")

    # ----- 4.6 Ponteiros Invalidos (strings vazias) -----
    draft_bad_ptr = {
        "phase": "build",
        "technical_changes": "Mudanca completa no modulo de autenticacao com testes",
        "updated_pointers": ["", "  "],
    }
    r6 = revisor.audit(draft_bad_ptr)
    report("Ponteiros vazios rejeitado", not r6.approved, f"reason='{r6.reason[:80]}'")
    report("Motivo menciona 'invalido'", "inv" in r6.reason.lower(), f"reason='{r6.reason[:80]}'")

    # ----- 4.7 audit_with_retry: Sempre rejeita -> partial_audit -----
    print("\n  [4.7] audit_with_retry (Loop de 3 tentativas)")
    bad_draft = {
        "phase": "build",
        "technical_changes": "x",
        "updated_pointers": [],
    }

    def gen_bad(feedback):
        return {"phase": "build", "technical_changes": "y", "updated_pointers": []}

    r7 = revisor.audit_with_retry(bad_draft, generate_fn=gen_bad)
    report("partial_audit=True apos max_loops", r7.partial_audit, f"partial={r7.partial_audit}")
    report("approved=True (fallback)", r7.approved, f"approved={r7.approved}")
    report("loop_count == max_loops (3)", r7.loop_count == 3, f"loops={r7.loop_count}")

    # ----- 4.8 audit_with_retry: Aprovacao na 2a tentativa -----
    attempt_counter = {"n": 0}

    def gen_improve(feedback):
        attempt_counter["n"] += 1
        if attempt_counter["n"] >= 1:
            return {
                "phase": "build",
                "technical_changes": "Refatorou o modulo de cache com TTL e fallback in-memory",
                "updated_pointers": ["src/cache.py"],
            }
        return {"phase": "build", "technical_changes": "y", "updated_pointers": []}

    r8 = revisor.audit_with_retry(bad_draft, generate_fn=gen_improve)
    report("Aprovado na 2a tentativa", r8.approved and not r8.partial_audit, f"loops={r8.loop_count}, partial={r8.partial_audit}")
    report("loop_count == 2", r8.loop_count == 2, f"loops={r8.loop_count}")

    # ----- 4.9 audit_with_retry sem generate_fn -----
    r9 = revisor.audit_with_retry(bad_draft, generate_fn=None)
    report("Sem generate_fn retorna rejeicao", not r9.approved or r9.partial_audit, f"approved={r9.approved}")

    # ----- 4.10 Reranking Heuristico -----
    print("\n  [4.10] Reranking de Gavetas")
    candidates = [
        {"node_id": 1, "score_final": 0.95, "score_breakdown": {"vetorial": 0.5, "frequencia": 0.25, "recencia": 0.1, "centralidade": 0.1}},
        {"node_id": 2, "score_final": 0.80, "score_breakdown": {"vetorial": 0.4, "frequencia": 0.2, "recencia": 0.1, "centralidade": 0.1}},
        {"node_id": 3, "score_final": 0.60, "score_breakdown": {"vetorial": 0.3, "frequencia": 0.15, "recencia": 0.1, "centralidade": 0.05}},
        {"node_id": 4, "score_final": 0.20, "score_breakdown": {"vetorial": 0.1, "frequencia": 0.05, "recencia": 0.03, "centralidade": 0.02}},
        {"node_id": 5, "score_final": 0.05, "score_breakdown": {"vetorial": 0.02, "frequencia": 0.01, "recencia": 0.01, "centralidade": 0.01}},
    ]
    reranked = revisor.rerank(candidates, "buscar modulo de trading", max_results=5)
    report("Reranking filtra candidatos", len(reranked) < len(candidates), f"antes={len(candidates)}, depois={len(reranked)}")
    report("Garante pelo menos 1 resultado", len(reranked) >= 1, f"count={len(reranked)}")

    # Valida que os melhores passaram
    reranked_ids = {c["node_id"] for c in reranked}
    report("Top scorer (node_id=1) mantido", 1 in reranked_ids, f"ids={reranked_ids}")

    # Score baixo (0.05) deve ser filtrado: threshold = 0.95 * 0.30 = 0.285
    report("Noise (node_id=5, score=0.05) filtrado", 5 not in reranked_ids, f"ids={reranked_ids}")

    # ----- 4.11 Reranking Lista Vazia -----
    reranked_empty = revisor.rerank([], "qualquer busca")
    report("Reranking lista vazia retorna []", reranked_empty == [], f"result={reranked_empty}")

    # ----- 4.12 Reranking com 1 candidato -----
    reranked_one = revisor.rerank([candidates[0]], "busca")
    report("Reranking com 1 candidato preserva", len(reranked_one) == 1, f"count={len(reranked_one)}")

    # ----- 4.13 Barreira de Contaminacao -----
    print("\n  [4.13] Barreira de Contaminacao")
    proj_restricted = {"folder_name": "vault-secrets", "privacy_level": "RESTRICTED"}
    proj_internal = {"folder_name": "fintech-api", "privacy_level": "INTERNAL"}
    proj_public = {"folder_name": "marketing-dash", "privacy_level": "PUBLIC"}

    # RESTRICTED -> PUBLIC (BLOQUEIO)
    safe1, reason1 = revisor.check_contamination(proj_restricted, proj_public)
    report("RESTRICTED->PUBLIC BLOQUEADO", not safe1, f"reason='{reason1[:60]}'")
    report("Motivo menciona CONTAMINACAO", "contamin" in reason1.lower(), f"reason='{reason1[:60]}'")

    # RESTRICTED -> INTERNAL (BLOQUEIO)
    safe2, reason2 = revisor.check_contamination(proj_restricted, proj_internal)
    report("RESTRICTED->INTERNAL BLOQUEADO", not safe2, f"reason='{reason2[:60]}'")

    # PUBLIC -> INTERNAL (OK)
    safe3, reason3 = revisor.check_contamination(proj_public, proj_internal)
    report("PUBLIC->INTERNAL permitido", safe3, f"reason='{reason3[:40]}'")

    # INTERNAL -> RESTRICTED (OK - nivel sobe)
    safe4, reason4 = revisor.check_contamination(proj_internal, proj_restricted)
    report("INTERNAL->RESTRICTED permitido", safe4, f"reason='{reason4[:40]}'")

    # PUBLIC -> PUBLIC (OK - mesmo nivel)
    safe5, _ = revisor.check_contamination(proj_public, proj_public)
    report("PUBLIC->PUBLIC permitido", safe5)

    # INTERNAL -> PUBLIC (BLOQUEIO)
    safe6, reason6 = revisor.check_contamination(proj_internal, proj_public)
    report("INTERNAL->PUBLIC BLOQUEADO", not safe6, f"reason='{reason6[:60]}'")

    # RESTRICTED -> RESTRICTED (OK - mesmo nivel)
    safe7, _ = revisor.check_contamination(proj_restricted, proj_restricted)
    report("RESTRICTED->RESTRICTED permitido", safe7)

    # ----- 4.14 Funcoes utilitarias -----
    print("\n  [4.14] Utilitarios do Revisor")
    parsed = revisor._extract_json('{"approved": true, "reason": "ok"}')
    report("_extract_json parseia JSON valido", parsed is not None and parsed["approved"] is True)

    parsed_md = revisor._extract_json('```json\n{"key": "value"}\n```')
    report("_extract_json parseia JSON em markdown", parsed_md is not None and parsed_md.get("key") == "value")

    parsed_none = revisor._extract_json("texto sem json aqui")
    report("_extract_json retorna None para texto invalido", parsed_none is None)

    parsed_empty = revisor._extract_json("")
    report("_extract_json retorna None para string vazia", parsed_empty is None)


# ==================================================================
# DIMENSAO 5: INTERFACE MCP SERVER
# ==================================================================

def test_dim5(gc, store, uid_a):
    header("DIMENSAO 5: Interface MCP Server")

    # 5.1 Instanciacao
    print("\n  [5.1] Instanciacao do GrafoConciergeServer")
    from interface.mcp_server import GrafoConciergeServer
    try:
        server = GrafoConciergeServer(concierge=gc)
        report("Instanciacao sem erro", True)
    except Exception as e:
        report("Instanciacao sem erro", False, str(e))
        return

    report("server._gc e GrafoConcierge", server._gc is gc)
    report("server._mcp e FastMCP", hasattr(server, '_mcp') and server._mcp is not None)

    # 5.2 Contagem de Tools
    print("\n  [5.2] Tools Registradas")
    tool_names_expected = {
        "concierge_register", "concierge_mine", "concierge_search",
        "concierge_commit", "concierge_wakeup", "concierge_resume",
        "concierge_load", "concierge_status",
    }
    # FastMCP armazena tools internamente - verificamos via _tools ou list_tools
    has_tools = hasattr(server._mcp, '_tools') or hasattr(server._mcp, 'list_tools')
    report("FastMCP tem registro de tools", has_tools)

    if hasattr(server._mcp, '_tools'):
        registered = set(server._mcp._tools.keys()) if isinstance(server._mcp._tools, dict) else set()
        missing = tool_names_expected - registered
        extra = registered - tool_names_expected
        report("Tools esperadas registradas", len(missing) == 0, f"missing={missing}, extra={extra}")
        report("Total de tools >= 7", len(registered) >= 7, f"count={len(registered)}, names={registered}")
    else:
        report("[INFO] Nao foi possivel inspecionar _tools", True, "FastMCP API pode variar")

    # 5.3 Handler: _handle_register
    print("\n  [5.3] Handlers unitarios")
    r_reg = server._handle_register("teste-mcp-project", "geral", "PUBLIC", "Projeto de teste MCP")
    report("_handle_register sucesso", r_reg.get("success") is True, f"uuid={r_reg.get('project_uuid','?')[:12]}")
    report("retorna project_uuid", r_reg.get("project_uuid") is not None)
    report("retorna folder_name", r_reg.get("folder_name") == "teste-mcp-project", f"folder={r_reg.get('folder_name')}")
    report("retorna duration_seconds", "duration_seconds" in r_reg, f"dur={r_reg.get('duration_seconds')}")

    # 5.4 Handler: _handle_search
    r_search = server._handle_search("trading engine", uid_a, 5, None, False, False)
    report("_handle_search sucesso", r_search.get("success") is True, f"count={r_search.get('results_count')}")
    report("retorna results lista", isinstance(r_search.get("results"), list))
    report("retorna query echo", r_search.get("query") == "trading engine")

    if r_search.get("results"):
        first = r_search["results"][0]
        report("Resultado enriquecido tem label", "label" in first, f"keys={list(first.keys())}")
        report("Resultado enriquecido tem hybrid_score", "hybrid_score" in first, f"score={first.get('hybrid_score')}")

    # 5.5 Handler: _handle_commit
    r_commit = server._handle_commit(uid_a, "build", "Adicionou momentum strategy via MCP handler", ["src/trading.py"], None)
    report("_handle_commit sucesso", r_commit.get("success") is True, f"commit_id={r_commit.get('commit_id')}")
    report("retorna commit_id > 0", isinstance(r_commit.get("commit_id"), int) and r_commit["commit_id"] > 0)
    report("retorna phase echo", r_commit.get("phase") == "build")

    # 5.6 Handler: _handle_wakeup
    r_wake = server._handle_wakeup(uid_a)
    report("_handle_wakeup sucesso", r_wake.get("success") is True)
    report("retorna project", "project" in r_wake, f"keys={list(r_wake.keys())}")
    report("retorna resume", "resume" in r_wake)

    # 5.7 Handler: _handle_resume
    r_resume = server._handle_resume(uid_a)
    report("_handle_resume sucesso", r_resume.get("success") is True)
    report("retorna resume string", isinstance(r_resume.get("resume"), str))
    report("retorna stats", "stats" in r_resume)
    report("retorna primary_wing", "primary_wing" in r_resume, f"wing={r_resume.get('primary_wing')}")

    # 5.8 Handler: _handle_load
    nodes = store.get_nodes_by_project(uid_a, status="ACTIVE")
    if nodes:
        nid = nodes[0]["id"]
        r_load = server._handle_load(nid)
        report("_handle_load sucesso", r_load.get("success") is True, f"node_id={nid}")
        report("retorna node dict", isinstance(r_load.get("node"), dict))
    else:
        report("_handle_load (sem nodes p/ testar)", True, "skip")

    # 5.9 Handler: _handle_status (global)
    r_status_global = server._handle_status(None)
    report("_handle_status global sucesso", r_status_global.get("success") is True)
    report("retorna system version", "system" in r_status_global, f"system={r_status_global.get('system')}")
    report("retorna components.sqlite", "sqlite" in r_status_global.get("components", {}))
    sqlite_health = r_status_global.get("components", {}).get("sqlite", {})
    report("sqlite status healthy", sqlite_health.get("status") == "healthy", f"status={sqlite_health.get('status')}")

    # 5.10 Handler: _handle_status (com projeto)
    r_status_proj = server._handle_status(uid_a)
    report("_handle_status com projeto", r_status_proj.get("success") is True)
    report("retorna project stats", "project" in r_status_proj, f"keys={list(r_status_proj.keys())}")

    # 5.11 Handler: Erro Gracioso (UUID inexistente)
    print("\n  [5.11] Erro Gracioso")
    r_wake_bad = server._handle_wakeup("uuid-inexistente-12345")
    report("_handle_wakeup UUID invalido", r_wake_bad.get("success") is False, f"error={r_wake_bad.get('error','')[:60]}")
    report("retorna error message", "error" in r_wake_bad and len(r_wake_bad["error"]) > 0)

    r_resume_bad = server._handle_resume("uuid-inexistente-12345")
    report("_handle_resume UUID invalido", r_resume_bad.get("success") is False)

    r_load_bad = server._handle_load(999999)
    report("_handle_load node_id invalido", r_load_bad.get("success") is False)

    # 5.12 Cleanup: remove projeto de teste
    try:
        if r_reg.get("project_uuid"):
            gc.delete_project(r_reg["project_uuid"])
    except Exception:
        pass


# ==================================================================
# DIMENSAO 6: INTERFACE ACTION HOOKS
# ==================================================================

def test_dim6(gc, store, hooks, uid_a):
    header("DIMENSAO 6: Interface ActionHooks")

    # 6.1 on_planning
    print("\n  [6.1] on_planning")
    plan = hooks.on_planning(uid_a, "implementar autenticacao JWT com refresh tokens")
    report("on_planning retorna dict", isinstance(plan, dict), f"keys={list(plan.keys())}")
    report("retorna wake_up", "wake_up" in plan)
    report("retorna relevant_nodes", "relevant_nodes" in plan and isinstance(plan["relevant_nodes"], list))
    report("retorna task echo", plan.get("task") == "implementar autenticacao JWT com refresh tokens")

    if plan.get("wake_up"):
        wake = plan["wake_up"]
        report("wake_up tem project", "project" in wake, f"keys={list(wake.keys())}")
        report("wake_up tem resume", "resume" in wake)
        report("wake_up tem recent_commits", "recent_commits" in wake)

    # 6.2 on_planning com node_type
    plan_fact = hooks.on_planning(uid_a, "buscar fatos sobre trading", node_type="FACT")
    report("on_planning com node_type=FACT", isinstance(plan_fact.get("relevant_nodes"), list))

    # 6.3 on_execution com rerank
    print("\n  [6.3] on_execution")
    exec_results = hooks.on_execution(uid_a, "buscar modulo de trading engine", rerank=True)
    report("on_execution retorna lista", isinstance(exec_results, list), f"count={len(exec_results)}")
    if exec_results:
        report("Resultados tem score_final", "score_final" in exec_results[0], f"keys={list(exec_results[0].keys())}")

    # 6.4 on_execution sem rerank
    exec_no_rerank = hooks.on_execution(uid_a, "buscar qualquer coisa", rerank=False)
    report("on_execution sem rerank", isinstance(exec_no_rerank, list), f"count={len(exec_no_rerank)}")

    # 6.5 on_execution com include_references
    exec_refs = hooks.on_execution(uid_a, "trading", include_references=True, rerank=False)
    report("on_execution com references", isinstance(exec_refs, list), f"count={len(exec_refs)}")

    # 6.6 on_done com commit valido
    print("\n  [6.6] on_done")
    done_valid = hooks.on_done(uid_a, {
        "phase": "build",
        "technical_changes": "Implementou autenticacao JWT com refresh tokens e validacao de expiracoes",
        "updated_pointers": ["src/auth.py", "src/middleware.py"],
    })
    report("on_done retorna dict", isinstance(done_valid, dict), f"keys={list(done_valid.keys())}")
    report("retorna audit", "audit" in done_valid)
    report("audit e dict", isinstance(done_valid.get("audit"), dict))
    report("commit_id int ou None", isinstance(done_valid.get("commit_id"), (int, type(None))), f"commit_id={done_valid.get('commit_id')}")

    audit_data = done_valid.get("audit", {})
    report("audit.approved e bool", isinstance(audit_data.get("approved"), bool), f"approved={audit_data.get('approved')}")

    if audit_data.get("approved"):
        report("Commit valido gravado", done_valid.get("commit_id") is not None and done_valid["commit_id"] > 0, f"id={done_valid.get('commit_id')}")

    # 6.7 on_done com trajetoria episodica
    print("\n  [6.7] on_done com trajetoria episodica")
    done_traj = hooks.on_done(uid_a, {
        "phase": "build",
        "technical_changes": "Tentou implementar cache Redis com cluster de 3 nodes e replicacao",
        "updated_pointers": ["src/cache.py"],
        "task": "Implementar cache distribuido",
        "erro_encontrado": "ConnectionRefusedError: Redis nao disponivel na porta 6379",
        "solucao_aplicada": "Fallback para cache in-memory com TTL de 300 segundos",
    })
    report("on_done com erro retorna trajectory_id", "trajectory_id" in done_traj, f"traj_id={done_traj.get('trajectory_id')}")
    if done_traj.get("trajectory_id"):
        report("trajectory_id e int > 0", isinstance(done_traj["trajectory_id"], int) and done_traj["trajectory_id"] > 0)

    # Verifica que a trajetoria foi registrada no banco
    trajs = store.get_trajectories(uid_a)
    has_redis = any("Redis" in str(t.get("erro_encontrado", "")) for t in trajs)
    report("Trajetoria aparece no banco", has_redis, f"total_trajs={len(trajs)}")

    # 6.8 on_done com commit invalido (rejeitado pelo revisor)
    print("\n  [6.8] on_done com commit invalido")
    done_invalid = hooks.on_done(uid_a, {
        "phase": "build",
        "technical_changes": "",
        "updated_pointers": [],
    })
    report("Commit invalido rejeitado", done_invalid.get("commit_id") is None, f"commit_id={done_invalid.get('commit_id')}")
    invalid_audit = done_invalid.get("audit", {})
    report("audit.approved == False", invalid_audit.get("approved") is False, f"approved={invalid_audit.get('approved')}")

    # 6.9 on_done com commit curto (rejeitado)
    done_short = hooks.on_done(uid_a, {
        "phase": "done",
        "technical_changes": "fix",
        "updated_pointers": ["a.py"],
    })
    report("Commit curto rejeitado", done_short.get("commit_id") is None, f"commit_id={done_short.get('commit_id')}")

    # 6.10 on_done com ponteiros invalidos (rejeitado)
    done_bad_ptr = hooks.on_done(uid_a, {
        "phase": "build",
        "technical_changes": "Mudanca completa no modulo de autenticacao com testes de integracao",
        "updated_pointers": ["", "  "],
    })
    report("Ponteiros invalidos rejeitados", done_bad_ptr.get("commit_id") is None, f"commit_id={done_bad_ptr.get('commit_id')}")


# ==================================================================
# MAIN
# ==================================================================

def main() -> int:
    print()
    print("+" + "=" * 62 + "+")
    print("|   GRAFO CONCIERGE v3.8.0 -- STRESS TEST v2 (PARTE 2)        |")
    print("|   Dimensoes 4, 5, 6: Agents + MCP Server + Action Hooks     |")
    print("+" + "=" * 62 + "+")

    t_global = time.perf_counter()
    store = None

    try:
        header("SETUP: Preparando workspace")
        setup_workspace()
        print("  Workspace criado com 3 projetos fake")

        store, vector, embedder, manager, gc, revisor, hooks = bootstrap()
        print("  Componentes inicializados (REAIS, com LLM)")

        # Pre-seed: Mine para ter dados para testes de busca
        print("  Pre-seeding: Mine fintech-api + obsidian-vault...")
        uid_a = gc.register_project("fintech-api", wing="financas/quant", privacy_level="INTERNAL")
        gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
        uid_b = gc.register_project("obsidian-vault", wing="marketing/vendas", privacy_level="PUBLIC")
        gc.mine(uid_b, PROJ_B_DIR, auto_tag=True)
        gc.commit_memory(uid_a, "build", "Implementou TradingEngine com 5 metodos", ["src/trading.py"])
        print("  Pre-seeding concluido")

        # --- Dimensao 4 ---
        test_dim4(revisor)

        # --- Dimensao 5 ---
        test_dim5(gc, store, uid_a)

        # --- Dimensao 6 ---
        test_dim6(gc, store, hooks, uid_a)

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
