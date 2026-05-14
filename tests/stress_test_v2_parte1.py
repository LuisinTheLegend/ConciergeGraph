"""Stress Test v2 — Parte 1: Dimensoes 1, 2 e 3."""
from __future__ import annotations
import os, sys, time, uuid, shutil

# Garante imports do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.stress_test_v2_setup import (
    report, header, setup_workspace, bootstrap, print_report,
    TEST_DIR, PROJ_A_DIR, PROJ_B_DIR, PROJ_C_DIR, DB_PATH,
)


# ═══════════════════════════════════════════════════════════════
# DIMENSAO 1: STORAGE (SqliteStore + ChromaVectorStore)
# ═══════════════════════════════════════════════════════════════

def test_dim1(store, vector, embedder):
    header("DIMENSAO 1: Storage (Absolute Solidity)")
    uid_a, uid_b, uid_c = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    # 1.1 CRUD Projetos
    print("\n  [1.1] CRUD de Projetos")
    store.create_project(uuid=uid_a, folder_name="fintech-api", primary_wing="financas/quant", privacy_level="INTERNAL", summary="Motor de trading")
    store.create_project(uuid=uid_b, folder_name="obsidian-vault", primary_wing="marketing/vendas", privacy_level="PUBLIC", summary="Dashboard marketing")
    store.create_project(uuid=uid_c, folder_name="personal-wiki", primary_wing="gestao/saas", privacy_level="RESTRICTED", summary="Wiki pessoal")

    proj_a = store.get_project(uid_a)
    report("create+get projeto por UUID", proj_a["uuid"] == uid_a, f"folder={proj_a['folder_name']}")

    proj_by_name = store.get_project("fintech-api")
    report("get projeto por folder_name", proj_by_name["uuid"] == uid_a)

    projects = store.list_projects()
    report("list_projects retorna 3", len(projects) >= 3, f"count={len(projects)}")

    report("privacy_level persistido", proj_a.get("privacy_level") == "INTERNAL", f"privacy={proj_a.get('privacy_level')}")

    store.update_project(uid_a, summary="Motor de trading HFT atualizado")
    proj_upd = store.get_project(uid_a)
    report("update_project altera summary", "atualizado" in proj_upd.get("summary",""), f"summary='{proj_upd.get('summary','')[:50]}'")

    # 1.2 CRUD Nos
    print("\n  [1.2] CRUD de Nos")
    nid1 = store.create_node(uid_a, "src/trading.py", "Motor de trading HFT", node_type="FACT", tags=["trading","hft"], file_hash="abc123")
    nid2 = store.create_node(uid_a, "src/risk.py", "Calculo de VaR", node_type="SKILL", tags=["risk","var"])
    nid3 = store.create_node(uid_a, "src/utils.py", "Utilitarios", node_type="FACT")
    nid4 = store.create_node(uid_b, "src/analytics.py", "Analytics tracker", node_type="INSIGHT")
    report("create_node retorna IDs", all(isinstance(n, int) and n > 0 for n in [nid1,nid2,nid3,nid4]), f"ids={[nid1,nid2,nid3,nid4]}")

    node1 = store.get_node(nid1)
    report("get_node retorna campos", node1["label"] == "src/trading.py" and node1["node_type"] == "FACT")

    report("tags persistidas como lista", isinstance(node1.get("tags"), list) and "trading" in node1["tags"], f"tags={node1.get('tags')}")

    nodes_a = store.get_nodes_by_project(uid_a)
    report("get_nodes_by_project filtra", len(nodes_a) == 3, f"count={len(nodes_a)}")

    nodes_active = store.get_nodes_by_project(uid_a, status="ACTIVE")
    report("filtro status=ACTIVE", len(nodes_active) == 3)

    found = store.find_node_by_hash(uid_a, "abc123")
    report("find_node_by_hash encontra", found is not None and found["id"] == nid1)

    store.touch_node_commit(nid1)
    touched = store.get_node(nid1)
    report("touch_node_commit atualiza timestamp", touched.get("last_commit_at") is not None)

    # 1.3 Arestas
    print("\n  [1.3] Arestas (Grafo)")
    store.create_edge(nid1, nid2, "depends_on")
    store.create_edge(nid1, nid3, "imports")
    store.create_edge(nid2, nid3, "uses")

    edges_out = store.get_edges_from(nid1)
    report("get_edges_from retorna arestas", len(edges_out) == 2, f"count={len(edges_out)}")

    edges_in = store.get_edges_to(nid3)
    report("get_edges_to retorna arestas", len(edges_in) == 2, f"count={len(edges_in)}")

    in_deg = store.get_in_degree(nid3)
    report("get_in_degree correto", in_deg == 2, f"in_degree={in_deg}")

    store.delete_edge(nid2, nid3)
    in_deg2 = store.get_in_degree(nid3)
    report("delete_edge remove aresta", in_deg2 == 1, f"in_degree_apos={in_deg2}")

    dep_tree = store.get_dependency_tree(nid1)
    report("get_dependency_tree CTE funciona", isinstance(dep_tree, list))

    # 1.4 Commits
    print("\n  [1.4] Commits")
    cid1 = store.create_commit(uid_a, "build", "Implementou TradingEngine", ["src/trading.py"])
    import time as _time; _time.sleep(0.1)  # garante timestamps distintos
    cid2 = store.create_commit(uid_a, "done", "Finalizou modulo de risco", ["src/risk.py", "src/utils.py"])
    report("create_commit retorna IDs", cid1 > 0 and cid2 > cid1, f"ids={cid1},{cid2}")

    recent = store.get_recent_commits(uid_a, limit=2)
    report("get_recent_commits retorna 2", len(recent) == 2, f"count={len(recent)}")

    last_phase = store.get_last_commit_phase(uid_a)
    report("get_last_commit_phase retorna fase", last_phase is not None, f"phase={last_phase}")

    # 1.5 Trajetorias
    print("\n  [1.5] Trajetorias Episodicas")
    tid = store.create_trajectory(uid_a, "Implementar cache", "Tentou Redis", "ConnectionRefused", "Fallback in-memory")
    report("create_trajectory retorna ID", tid > 0, f"id={tid}")

    trajs = store.get_trajectories(uid_a)
    report("get_trajectories lista", len(trajs) >= 1, f"count={len(trajs)}")

    # 1.6 FTS5
    print("\n  [1.6] FTS5 (Full-Text Search)")
    fts_r1 = store.fts_search("trading", project_uuid=uid_a)
    report("FTS5 encontra 'trading'", len(fts_r1) > 0, f"count={len(fts_r1)}")

    fts_r2 = store.fts_search("analytics tracker", project_uuid=uid_b)
    report("FTS5 encontra 'analytics' no proj B", len(fts_r2) > 0, f"count={len(fts_r2)}")

    fts_r3 = store.fts_search("xyznonexistent_query_abc")
    report("FTS5 retorna vazio p/ query sem match", len(fts_r3) == 0)

    store.fts_rebuild()
    report("fts_rebuild executa sem erro", True)

    # 1.7 ChromaDB
    print("\n  [1.7] ChromaDB (Sincronizacao Atomica)")
    embs = []
    for i, nid in enumerate([nid1, nid2, nid3]):
        emb = embedder.embed(f"test embedding content {i}")
        if emb:
            embs.append({"doc_id": f"node_{nid}", "embedding": emb, "metadata": {"node_id": nid, "project_uuid": uid_a}})
    stored = vector.store_embeddings_batch(embs)
    report("store_embeddings_batch armazena", stored == len(embs), f"stored={stored}")

    count_before = vector.count()
    report("vector.count() apos batch", count_before >= len(embs), f"count={count_before}")

    q_emb = embedder.embed("trading engine calculation")
    if q_emb:
        vr = vector.search(query_embedding=q_emb, project_uuids=[uid_a], top_k=3)
        report("vector.search retorna resultados", len(vr) > 0, f"count={len(vr)}")
        if vr:
            report("project_uuid nos metadados", vr[0].project_uuid == uid_a, f"uuid={vr[0].project_uuid}")
    else:
        report("embed da query", False, "retornou None")

    vector.delete(f"node_{nid3}")
    count_after = vector.count()
    report("vector.delete remove embedding", count_after < count_before, f"before={count_before} after={count_after}")

    # 1.8 Stats
    print("\n  [1.8] Estatisticas")
    stats = store.get_project_stats(uid_a)
    report("get_project_stats retorna dict", isinstance(stats, dict), f"stats_keys={list(stats.keys()) if stats else 'None'}")

    # Cleanup dos projetos temporarios (nao do workspace)
    store.delete_project(uid_a)
    store.delete_project(uid_b)
    store.delete_project(uid_c)

    return True


# ═══════════════════════════════════════════════════════════════
# DIMENSAO 2: INGESTAO (Motor Apex)
# ═══════════════════════════════════════════════════════════════

def test_dim2(store, vector, embedder, manager, gc):
    header("DIMENSAO 2: Ingestao (Motor Apex)")

    # 2.1 Mine Projeto A
    print("\n  [2.1] Mine fintech-api")
    uid_a = gc.register_project("fintech-api", wing="financas/quant", privacy_level="INTERNAL")
    t0 = time.perf_counter()
    result_a = gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
    elapsed = time.perf_counter() - t0
    report("Mine fintech-api executou", result_a.get("files_processed",0) > 0, f"files={result_a.get('files_processed')}, nodes={result_a.get('nodes_created')}, embs={result_a.get('embeddings_stored')}, {elapsed:.1f}s")
    report("Nodes criados > 0", result_a.get("nodes_created",0) > 0, f"nodes={result_a.get('nodes_created')}")
    report("Embeddings stored > 0", result_a.get("embeddings_stored",0) > 0, f"embs={result_a.get('embeddings_stored')}")
    report("Files skipped processado", True, f"skipped={result_a.get('files_skipped', 0)}")

    # 2.2 Mine Projeto B
    print("\n  [2.2] Mine obsidian-vault")
    uid_b = gc.register_project("obsidian-vault", wing="marketing/vendas", privacy_level="PUBLIC")
    result_b = gc.mine(uid_b, PROJ_B_DIR, auto_tag=True)
    report("Mine obsidian-vault executou", result_b.get("files_processed",0) > 0, f"files={result_b.get('files_processed')}, nodes={result_b.get('nodes_created')}")

    # 2.3 Re-mine (idempotencia)
    print("\n  [2.3] Re-mine (idempotencia via hash check)")
    result_remine = gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
    report("Re-mine nao cria nodes duplicados", result_remine.get("nodes_created",0) == 0, f"nodes_created={result_remine.get('nodes_created')}")

    # 2.4 Mine apos modificacao
    print("\n  [2.4] Mine apos modificacao de arquivo")
    trading_path = os.path.join(PROJ_A_DIR, "src", "trading.py")
    with open(trading_path, "a", encoding="utf-8") as f:
        f.write('\n    def momentum_strategy(self, window: int = 20) -> float:\n        """Estrategia de momentum com janela movel."""\n        return 0.0\n')
    result_mod = gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
    report("Mine detectou modificacao", result_mod.get("files_processed",0) > 0, f"processed={result_mod.get('files_processed')}")

    # 2.5 Mine apos delecao
    print("\n  [2.5] Mine apos delecao de arquivo")
    risk_path = os.path.join(PROJ_A_DIR, "src", "risk.py")
    if os.path.exists(risk_path):
        os.remove(risk_path)
    result_del = gc.mine(uid_a, PROJ_A_DIR, auto_tag=True)
    report("Mine detectou delecao", result_del.get("files_deleted",0) > 0, f"deleted={result_del.get('files_deleted')}")

    # 2.6 Hierarquia Zoom (L1/L2)
    print("\n  [2.6] Engrenagem de Zoom (L1/L2)")
    context = manager.generate_project_context(uid_a)
    report("generate_project_context executou", context is not None and isinstance(context, dict), f"type={type(context).__name__}")
    if context:
        l1 = context.get("l1_count", 0)
        l2 = str(context.get("l2_summary", ""))
        report("L1 clusters gerados", l1 > 0, f"l1_count={l1}")
        has_content = len(l2) > 10
        is_dumb = "dumb" in l2.lower()
        report("L2 Bussola gerada", has_content, f"dumb={'sim' if is_dumb else 'nao'}, len={len(l2)}")
        if is_dumb:
            report("[INFO] L2 Dumb Summary (LLM falhou)", True, "Verificar GRAFO_LLM_API_KEY")

    return uid_a, uid_b


# ═══════════════════════════════════════════════════════════════
# DIMENSAO 3: CORE (Busca Hibrida v4 + GPS de Conhecimento)
# ═══════════════════════════════════════════════════════════════

def test_dim3(store, vector, embedder, gc, uid_a, uid_b):
    header("DIMENSAO 3: Core (Busca Hibrida v4 + GPS)")

    # 3.1 ConciergeConfig
    print("\n  [3.1] ConciergeConfig")
    from core.config import ConciergeConfig, DEFAULT_CONFIG
    report("DEFAULT_CONFIG instanciado", DEFAULT_CONFIG is not None)
    report("weight_vector = 0.50", DEFAULT_CONFIG.weight_vector == 0.50, f"w={DEFAULT_CONFIG.weight_vector}")
    report("weight_fts5 = 0.25", DEFAULT_CONFIG.weight_fts5 == 0.25, f"w={DEFAULT_CONFIG.weight_fts5}")
    report("weight_recency_centrality = 0.25", DEFAULT_CONFIG.weight_recency_centrality == 0.25, f"w={DEFAULT_CONFIG.weight_recency_centrality}")
    report("recency_lambda ~0.099", abs(DEFAULT_CONFIG.recency_lambda - 0.09902) < 0.001, f"lambda={DEFAULT_CONFIG.recency_lambda:.5f}")

    frozen_ok = False
    try:
        DEFAULT_CONFIG.weight_vector = 0.99
    except Exception:
        frozen_ok = True
    report("Config e frozen (imutavel)", frozen_ok)

    # 3.2 ProjectIndex: Auto-Categorizacao
    print("\n  [3.2] GPS de Conhecimento (ProjectIndex)")
    pi = gc.project_index
    wing_a = pi.auto_categorize_project(uid_a)
    report("fintech-api -> financas/quant", "finan" in wing_a.lower(), f"wing='{wing_a}'")

    wing_b = pi.auto_categorize_project(uid_b)
    report("obsidian-vault categorizou", wing_b != "geral", f"wing='{wing_b}'")

    uid_rnd = gc.register_project("random-xyz-project-12345")
    wing_rnd = pi.auto_categorize_project(uid_rnd)
    report("random-project -> geral (fallback)", wing_rnd == "geral", f"wing='{wing_rnd}'")

    # 3.3 Strict Scoping
    print("\n  [3.3] Strict Scoping")
    scope_strict = pi.resolve_scoped_uuids(uid_a, include_references=False, all_wings=False)
    report("Strict scope retorna lista", isinstance(scope_strict, list) and len(scope_strict) >= 1, f"uuids={len(scope_strict)}")

    scope_refs = pi.resolve_scoped_uuids(uid_a, include_references=True, all_wings=False)
    report("Scope com references >= strict", len(scope_refs) >= len(scope_strict), f"strict={len(scope_strict)}, refs={len(scope_refs)}")

    scope_all = pi.resolve_scoped_uuids(uid_a, include_references=False, all_wings=True)
    report("Scope all_wings >= refs", len(scope_all) >= len(scope_refs), f"all={len(scope_all)}")

    # 3.4 HybridSearch Pipeline
    print("\n  [3.4] Busca Hibrida v4 (Pipeline Tri-Sinal)")
    results = gc.hybrid_search("trading engine risk calculation", uid_a, top_k=5)
    report("hybrid_search retorna resultados", len(results) > 0, f"count={len(results)}")

    if results:
        top = results[0]
        report("score_final > 0", top.get("score_final",0) > 0, f"score={top.get('score_final',0):.4f}")
        bd = top.get("score_breakdown", {})
        has_breakdown = all(k in bd for k in ["vetorial", "frequencia", "recencia", "centralidade"])
        report("score_breakdown completo", has_breakdown, f"keys={list(bd.keys())}")

        scores = [r.get("score_final",0) for r in results]
        is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        report("Resultados ordenados DESC", is_sorted, f"scores={[round(s,3) for s in scores]}")

    # 3.5 Busca com filtro node_type
    print("\n  [3.5] Busca com filtro node_type")
    results_fact = gc.hybrid_search("trading", uid_a, node_type="FACT")
    report("Busca com node_type=FACT", isinstance(results_fact, list), f"count={len(results_fact)}")

    # 3.6 Middleware: commit_memory
    print("\n  [3.6] GrafoConcierge: commit + wake_up + resume")
    cid = gc.commit_memory(uid_a, "build", "Refatorou TradingEngine com momentum strategy", ["src/trading.py"])
    report("commit_memory retorna ID", isinstance(cid, int) and cid > 0, f"commit_id={cid}")

    recent = store.get_recent_commits(uid_a, limit=1)
    report("Commit aparece em recent_commits", len(recent) > 0 and recent[0]["id"] == cid)

    # 3.7 wake_up
    wake = gc.wake_up(uid_a)
    report("wake_up retorna dict completo", all(k in wake for k in ["project","resume","reference_wings","recent_commits","stats"]), f"keys={list(wake.keys())}")

    # 3.8 get_resume
    resume = gc.get_resume(uid_a)
    report("get_resume retorna string", isinstance(resume, str) and len(resume) > 5, f"len={len(resume)}")

    # 3.9 lazy_load
    print("\n  [3.9] Lazy Load + Status")
    nodes = store.get_nodes_by_project(uid_a, status="ACTIVE")
    if nodes:
        nid = nodes[0]["id"]
        loaded = gc.lazy_load(nid)
        report("lazy_load retorna node + edges_out", "edges_out" in loaded, f"node_id={nid}")

        reloaded = store.get_node(nid)
        report("last_accessed atualizado", reloaded.get("last_accessed") is not None)

    # 3.10 status
    st = gc.status(uid_a)
    report("status retorna project + stats", "project" in st and "stats" in st, f"keys={list(st.keys())}")

    # 3.11 find_similar
    similar = gc.find_similar(uid_a)
    report("find_similar retorna lista", isinstance(similar, list), f"count={len(similar)}")

    # 3.12 delete_project
    print("\n  [3.12] delete_project (cascata)")
    uid_c = gc.register_project("personal-wiki", wing="gestao/saas", privacy_level="RESTRICTED")
    gc.mine(uid_c, PROJ_C_DIR, auto_tag=True)
    nodes_before = store.get_nodes_by_project(uid_c)
    gc.delete_project(uid_c)
    try:
        store.get_project(uid_c)
        report("delete_project remove projeto", False, "projeto ainda existe")
    except Exception:
        report("delete_project remove projeto", True, f"nodes_antes={len(nodes_before)}")

    nodes_after = store.get_nodes_by_project(uid_c)
    report("Nos do projeto deletados em cascata", len(nodes_after) == 0, f"restantes={len(nodes_after)}")

    # Cleanup do random project
    try: gc.delete_project(uid_rnd)
    except: pass


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    print()
    print("+" + "=" * 62 + "+")
    print("|   GRAFO CONCIERGE v3.8.0 — STRESS TEST v2 (PARTE 1)        |")
    print("|   Dimensoes 1, 2, 3: Storage + Ingestao + Core             |")
    print("+" + "=" * 62 + "+")

    t_global = time.perf_counter()
    store = None

    try:
        header("SETUP: Preparando workspace")
        setup_workspace()
        print("  Workspace criado com 3 projetos fake (9 arquivos)")

        store, vector, embedder, manager, gc, revisor, hooks = bootstrap()
        print("  Componentes inicializados (REAIS, com LLM)")

        # --- Dimensao 1 ---
        test_dim1(store, vector, embedder)

        # --- Dimensao 2 ---
        uid_a, uid_b = test_dim2(store, vector, embedder, manager, gc)

        # --- Dimensao 3 ---
        test_dim3(store, vector, embedder, gc, uid_a, uid_b)

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
