"""
Blocos 3, 4, 5 e 6 - PEDIDO 4.5a
Gera evidência estruturada em scratch/evidencia_4_5a/:
  - bloco3_promises.json / .txt
  - bloco4_non_python_deps.json / .txt
  - bloco5_tests_ci.json / .txt
  - bloco6_queue_writer.json / .txt
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "scratch" / "evidencia_4_5a"


# ---------------------------------------------------------------------------
# BLOCO 3: Promessas públicas
# ---------------------------------------------------------------------------

PROMISE_KEYWORDS = [
    (re.compile(r"\bhsm\b|hierarchical state machine|history node|\$h\^\*\$|h\*|circuit breaker|error\.pause|re_index", re.I),
     "core.hsm_engine / agent.run_agent"),
    (re.compile(r"rate governor|rate_governor|60 rpm|40,?000 tpm|40k tpm|http 429|priority queue|quota", re.I),
     "core.rate_governor"),
    (re.compile(r"gating|gating_interceptor|security_guard|plan-only|auto-approve|monorepo boundar", re.I),
     "core.gating_interceptor / core.security_guard"),
    (re.compile(r"telemetry|telemetria|/api/telemetry|telemetry_api|15 endpoint|15-endpoint|8001|sse.*cockpit|stream.*telemetry", re.I),
     "interface.telemetry_api / core.telemetry_schemas"),
    (re.compile(r"cockpit|next\.js 16|grafo-dashboard-web|2x2|npm run dev:all|force-directed|60fps", re.I),
     "grafo-dashboard-web / interface.telemetry_api"),
    (re.compile(r"delta sync|dual-hash|dual hash|\bssh\b.*\blbh\b|\blbh\b|docstringstripper|delta_manager|delta_sync", re.I),
     "core.delta_manager / core.delta_sync"),
    (re.compile(r"alias_tracker|alias tracking|rastreamento de alias|1-second atomic ssh|1s via ssh", re.I),
     "core.alias_tracker"),
    (re.compile(r"parser_factory|polyglot|fábrica de parsers|multilíngue|tree-sitter", re.I),
     "core.parser_factory / core.parsers.* (vs ingestion.parser)"),
    (re.compile(r"intent classifier|classificador jit|federated knowledge|roteamento federado|nozomio|globalmemoryadapter|global memory adapter|stm.*ltm|últimas 3 mensagens|last 3 immediate", re.I),
     "core.intent_classifier / core.federated_knowledge_router / core.global_memory_adapter"),
    (re.compile(r"backgroundjanitor|auto-poda|auto-pruning|smart lru|checkpoint.*init|pruning", re.I),
     "core.background_janitor (vs services.janitor)"),
    (re.compile(r"thompson sampling|probabilistic_retriever|amostragem de thompson", re.I),
     "core.probabilistic_retriever (import condicional em hybrid_search.py:252)"),
    (re.compile(r"watcher|watchdog|file watcher|conciergeignore.*watcher|filesystemhandler", re.I),
     "interface.watcher"),
    (re.compile(r"fsm_checkpoints|time-travel|relational_db", re.I),
     "storage.relational_db / core.checkpointer (ramo fsm_checkpoints)"),
    (re.compile(r"revisor[ _]?cr[ií]tico|action[ _]?hooks|ActionHooks|RevisorCritico", re.I),
     "agents.revisor_critico / interface.action_hooks"),
    (re.compile(r"30 tools|30 ferramentas|326 passed|326 aprovados|326 tests", re.I),
     "Contagem desatualizada em README (real: 31 tools MCP, 478 testes pytest)"),
    (re.compile(r"serializedwritequeue|auto-batching|auto-batch", re.I),
     "storage.connection vs interface.queue_writer (produção usa storage.connection)"),
]


def run_bloco3() -> dict:
    doc_files = [
        ROOT / "README.md",
        ROOT / "README.pt-BR.md",
        ROOT / "CHANGELOG.md",
        ROOT / "pyproject.toml",
    ]
    docs_dir = ROOT / "docs-grafo-concierge"
    if docs_dir.exists():
        doc_files.extend(sorted(p for p in docs_dir.rglob("*") if p.is_file()))

    hits = []
    for df in doc_files:
        if not df.exists():
            continue
        rel = df.relative_to(ROOT).as_posix()
        for lineno, line in enumerate(df.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            matched_mods = []
            for pat, target in PROMISE_KEYWORDS:
                if pat.search(stripped):
                    matched_mods.append(target)
            if matched_mods:
                hits.append({
                    "file": rel,
                    "line": lineno,
                    "quote": stripped[:220],
                    "targets": matched_mods,
                })

    by_file = {}
    for h in hits:
        by_file.setdefault(h["file"], []).append(h)

    res = {"total_hits": len(hits), "by_file": by_file}
    (EVID / "bloco3_promises.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"=== BLOCO 3: PROMESSAS PÚBLICAS ({len(hits)} linhas encontradas) ==="]
    for f, items in by_file.items():
        lines.append(f"\n[{f}] ({len(items)} ocorrências)")
        for it in items:
            lines.append(f"  L{it['line']}: {it['quote']}")
            lines.append(f"     -> alvos: {', '.join(it['targets'])}")
    (EVID / "bloco3_promises.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return res


# ---------------------------------------------------------------------------
# BLOCO 4: Dependências fora do Python (Dashboard, SQL Schema, Packaging)
# ---------------------------------------------------------------------------

def run_bloco4() -> dict:
    # 4.1 Dashboard endpoints & URLs
    dash_res = subprocess.run(
        ["git", "ls-files", "grafo-dashboard-web"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    dash_files = sorted(
        ROOT / rel.strip() for rel in dash_res.stdout.splitlines()
        if rel.strip() and (ROOT / rel.strip()).is_file()
    )
    url_pat = re.compile(r"(/api/[\w/\-{}?$]+|https?://[^\s'\"`)]+|EventSource\([^)]+\)|fetch\([^)]+\))")
    dash_endpoints = []
    for df in dash_files:
        rel = df.relative_to(ROOT).as_posix()
        txt = df.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(txt.splitlines(), start=1):
            m = url_pat.search(line)
            if m:
                dash_endpoints.append({
                    "file": rel,
                    "line": lineno,
                    "match": m.group(0)[:140],
                    "line_text": line.strip()[:180],
                })

    # Routes in telemetry_api.py and mcp_server.py
    tele_src = (ROOT / "interface" / "telemetry_api.py").read_text(encoding="utf-8")
    tele_routes = []
    for lineno, line in enumerate(tele_src.splitlines(), start=1):
        m = re.search(r'@app\.(get|post|put|delete)\("([^"]+)"', line)
        if m:
            tele_routes.append({"line": lineno, "method": m.group(1).upper(), "route": m.group(2)})

    mcp_src = (ROOT / "interface" / "mcp_server.py").read_text(encoding="utf-8")
    mcp_routes = []
    for lineno, line in enumerate(mcp_src.splitlines(), start=1):
        if "custom_route" in line or "@app." in line or "FastAPI" in line or "sse" in line.lower():
            if "route" in line.lower() or "@app." in line:
                mcp_routes.append({"line": lineno, "text": line.strip()[:140]})

    # 4.2 SQL Schema audit
    py_prod_dirs = ["core", "storage", "ingestion", "interface", "services", "agent", "agents"]
    prod_pys = [ROOT / "main.py"]
    for d in py_prod_dirs:
        p = ROOT / d
        if p.exists():
            prod_pys.extend(sorted(p.rglob("*.py")))

    create_table_re = re.compile(r"CREATE\s+(?:VIRTUAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.I)
    sql_ref_re = re.compile(
        r"\b(?:FROM|INTO|UPDATE|JOIN|DELETE\s+FROM)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        r"|PRAGMA\s+table_info\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)",
        re.I,
    )
    static_data = json.loads((EVID / "bloco1_static_reach.json").read_text(encoding="utf-8"))
    mod_by_path = {v["path"]: (m, v["status"]) for m, v in static_data["modules"].items()}

    tables_created = {}
    table_queries = {}
    SQL_STOPWORDS = {
        "the", "sqlite_master", "temp", "select", "where", "values", "set", "null", "not",
        "files_or_similar", "each", "a", "an", "sql", "which", "memory", "this", "disk",
        "our", "your", "any", "all", "one", "two", "both", "local", "other",
    }

    for pf in prod_pys:
        rel = pf.relative_to(ROOT).as_posix()
        mod_name, status = mod_by_path.get(rel, (rel, "UNKNOWN"))
        lines_pf = pf.read_text(encoding="utf-8", errors="replace").splitlines()
        # only inspect AST string constants so docstrings/comments aren't confused unless they contain real SQL strings
        # Better: use AST to collect string literals that look like SQL statements
        tree = ast.parse("\n".join(lines_pf))
        sql_consts: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # ignore module/class/function docstrings
                sql_consts.append((node.lineno, node.value))
            elif isinstance(node, ast.JoinedStr):
                txt = "".join(
                    v.value if isinstance(v, ast.Constant) else "{EXPR}" for v in node.values
                )
                sql_consts.append((node.lineno, txt))

        # Collect docstring nodes to skip docstrings
        docstring_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    docstring_ids.add(id(node.body[0].value))

        for node in ast.walk(tree):
            if id(node) in docstring_ids:
                continue
            sval = None
            lineno = getattr(node, "lineno", 0)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                sval = node.value
            elif isinstance(node, ast.JoinedStr):
                sval = "".join(v.value if isinstance(v, ast.Constant) else " {X} " for v in node.values)
            if not sval:
                continue
            if not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE\s+(?:VIRTUAL\s+)?TABLE|PRAGMA\s+table_info)\b", sval, re.I):
                continue

            for m in create_table_re.finditer(sval):
                tname = m.group(1)
                tables_created.setdefault(tname, []).append({"file": rel, "line": lineno, "status": status})

            for m in sql_ref_re.finditer(sval):
                tname = (m.group(1) or m.group(2) or "").strip()
                if not tname or tname.lower() in SQL_STOPWORDS or tname.startswith("{"):
                    continue
                # verify statement actually starts/contains SQL DML/DDL
                if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|PRAGMA)\b", sval, re.I):
                    table_queries.setdefault(tname, []).append({"file": rel, "line": lineno, "status": status, "snippet": sval.strip().replace("\n", " ")[:110]})

    # Cross-check tables_created in storage/schema.py vs queried
    schema_tables = {t for t, locs in tables_created.items() if any(l["file"] == "storage/schema.py" for l in locs)}
    discrepancies = []
    for tname, qlist in sorted(table_queries.items()):
        in_prod_schema = tname in schema_tables
        in_dormant_schema = tname in tables_created and not in_prod_schema
        statuses = sorted({q["status"] for q in qlist})
        discrepancies.append({
            "table": tname,
            "in_storage_schema": in_prod_schema,
            "created_elsewhere": tables_created.get(tname, []),
            "queried_by_statuses": statuses,
            "query_count": len(qlist),
            "sample_queries": qlist[:8],
        })

    # 4.3 Packaging analysis
    pyproject_txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile_txt = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose_txt = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    # Check third-party imports exclusive to dormant modules
    all_imports_by_mod = {}
    for m, info in static_data["modules"].items():
        src = (ROOT / info["path"]).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
        imps = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imps.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imps.add(node.module.split(".")[0])
        all_imports_by_mod[m] = imps

    live_mods = [m for m, info in static_data["modules"].items() if info["status"] in ("REACHABLE_LOAD", "REACHABLE_DEFERRED")]
    dorm_mods = [m for m, info in static_data["modules"].items() if info["status"] == "UNREACHABLE"]
    live_3p = set().union(*(all_imports_by_mod[m] for m in live_mods))
    dorm_3p = set().union(*(all_imports_by_mod[m] for m in dorm_mods))
    only_dormant_imports = sorted(dorm_3p - live_3p - {"core", "storage", "ingestion", "interface", "services", "agent", "agents", "main"})

    out = {
        "dashboard_endpoints": dash_endpoints,
        "telemetry_api_routes": tele_routes,
        "mcp_server_routes": mcp_routes,
        "dashboard_in_dockerfile": "grafo-dashboard-web" in dockerfile_txt,
        "dashboard_in_pyproject": "grafo-dashboard-web" in pyproject_txt,
        "dashboard_in_compose": "grafo-dashboard-web" in compose_txt,
        "sql_tables_created_in_schema_py": sorted(schema_tables),
        "sql_tables_created_all": tables_created,
        "sql_discrepancies": discrepancies,
        "third_party_imports_only_in_dormant": only_dormant_imports,
    }
    (EVID / "bloco4_non_python_deps.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["=== BLOCO 4: DEPENDÊNCIAS FORA DO PYTHON ==="]
    lines.append("\n--- 4.1 Dashboard (grafo-dashboard-web/) vs telemetry_api.py ---")
    lines.append(f"Dashboard no Dockerfile: {out['dashboard_in_dockerfile']} | no pyproject.toml: {out['dashboard_in_pyproject']} | no docker-compose.yml: {out['dashboard_in_compose']}")
    lines.append(f"Rotas FastAPI em interface/telemetry_api.py ({len(tele_routes)}): " + ", ".join(f"{r['method']} {r['route']} (L{r['line']})" for r in tele_routes))
    lines.append(f"Chamadas encontradas em grafo-dashboard-web/ ({len(dash_endpoints)}):")
    for ep in dash_endpoints:
        lines.append(f"  - {ep['file']}:{ep['line']} -> {ep['match']} | {ep['line_text']}")
    lines.append("\n--- 4.2 Esquema SQL ---")
    lines.append(f"Tabelas em storage/schema.py: {sorted(schema_tables)}")
    for d in discrepancies:
        if not d["in_storage_schema"]:
            lines.append(f"  [DISCREPÂNCIA] Tabela '{d['table']}' NÃO está em storage/schema.py! created_elsewhere={d['created_elsewhere']} | queried_by_statuses={d['queried_by_statuses']}")
            for sq in d["sample_queries"]:
                lines.append(f"      -> {sq['file']}:{sq['line']} ({sq['status']}): {sq['snippet']}")
    lines.append("\n--- 4.3 Empacotamento (imports externos só nos módulos dormentes) ---")
    lines.append(f"Imports apenas em dormentes: {only_dormant_imports}")
    (EVID / "bloco4_non_python_deps.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# BLOCO 5: Impacto em testes e CI
# ---------------------------------------------------------------------------

def run_bloco5() -> dict:
    inv = json.loads((EVID / "bloco2_inventory.json").read_text(encoding="utf-8"))
    static_data = json.loads((EVID / "bloco1_static_reach.json").read_text(encoding="utf-8"))
    pytest_raw = (EVID / "pytest_collect_raw.txt").read_text(encoding="utf-8").splitlines()

    nodes_by_file: dict[str, list[str]] = {}
    for line in pytest_raw:
        s = line.strip()
        if not s or "::" not in s or s.startswith(("=", "-")):
            continue
        fpath = s.split("::", 1)[0].replace("\\", "/")
        nodes_by_file.setdefault(fpath, []).append(s)

    total_collected = sum(len(v) for v in nodes_by_file.values())

    # Map test_file -> {dormant_mods, live_mods, test_count}
    file_map: dict[str, dict] = {}
    for mod, entry in inv.items():
        for t in entry["importing_tests"]:
            tf = t["test_file"]
            rec = file_map.setdefault(tf, {
                "test_file": tf,
                "test_count": t["test_count"],
                "dormant_imported": set(),
                "live_imported": set(t["also_imports_live"]),
                "status_of_imported": set(),
            })
            rec["dormant_imported"].add(mod)
            rec["status_of_imported"].add(entry["status"])

    # Also check ALL tests importing live modules directly via inv_4_5a_bloco2's logic
    # Inspect inside each affected test file which individual test functions touch live vs dormant symbols
    # Define scenarios:
    # (i) Extra suspenso: HSM, RateGovernor, Gating, TelemetryAPI, Dashboard/Watcher, Federated/Intent/GlobalMemory,
    #     AgentRunner, BackgroundJanitor, storage.relational_db, core.dependencies, interface.action_hooks, agents.revisor_critico
    # (ii) Duplicata superada por caminho vivo: core.delta_manager, core.delta_sync, core.parser_factory, core.parsers.*,
    #      core.vector_reconciler, core.search_engine, core.alias_tracker
    # Note: interface.queue_writer treated separately in Bloco 6!
    CLASS_I = {
        "agent", "agent.agent_prompts", "agent.run_agent",
        "agents", "agents.revisor_critico",
        "core.background_janitor", "core.janitor",
        "core.dependencies",
        "core.federated_knowledge_router", "core.nozomio_router",
        "core.gating_interceptor", "core.security_guard",
        "core.global_memory_adapter", "core.hsm_engine",
        "core.intent_classifier", "core.rate_governor",
        "core.telemetry_schemas", "interface.telemetry_api",
        "interface.watcher", "interface.action_hooks",
        "storage.relational_db",
    }
    CLASS_II = {
        "core.alias_tracker",
        "core.delta_manager", "core.delta_sync",
        "core.parser_factory", "core.parsers", "core.parsers.base",
        "core.parsers.python_parser", "core.parsers.ts_js_parser",
        "core.search_engine", "core.vector_reconciler",
    }
    QUEUE_WRITER = {"interface.queue_writer"}

    affected_details = []
    for tf, rec in sorted(file_map.items()):
        dorm = sorted(rec["dormant_imported"])
        live = sorted(rec["live_imported"])
        has_i = bool(rec["dormant_imported"] & CLASS_I)
        has_ii = bool(rec["dormant_imported"] & CLASS_II)
        has_qw = bool(rec["dormant_imported"] & QUEUE_WRITER)

        # Parse test file to inspect each test_ function / method body for references to live vs dormant
        src = (ROOT / tf).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
        test_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                segment = "\n".join(src.splitlines()[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
                test_methods.append({"name": node.name, "line": node.lineno, "len": len(segment.splitlines())})

        affected_details.append({
            "test_file": tf,
            "test_count": rec["test_count"],
            "dormant_imported": dorm,
            "live_imported": live,
            "touches_class_i": has_i,
            "touches_class_ii": has_ii,
            "touches_queue_writer": has_qw,
            "pure_dormant_only": (len(live) == 0),
            "test_defs_count": len(test_methods),
        })

    # Totals:
    any_unreachable_or_lazy = [d for d in affected_details if (set(d["dormant_imported"]) - QUEUE_WRITER)]
    only_qw = [d for d in affected_details if set(d["dormant_imported"]) == QUEUE_WRITER]

    scenario_i_files = [d for d in affected_details if d["touches_class_i"]]
    scenario_i_ii_files = [d for d in affected_details if d["touches_class_i"] or d["touches_class_ii"]]

    out = {
        "total_collected": total_collected,
        "affected_files": affected_details,
        "summary": {
            "files_importing_any_non_load_incl_qw": len(affected_details),
            "tests_in_files_any_non_load_incl_qw": sum(d["test_count"] for d in affected_details),
            "files_importing_dormant_excl_qw": len(any_unreachable_or_lazy),
            "tests_in_files_dormant_excl_qw": sum(d["test_count"] for d in any_unreachable_or_lazy),
            "files_importing_only_qw": len(only_qw),
            "tests_in_files_only_qw": sum(d["test_count"] for d in only_qw),
            "scenario_i_files_count": len(scenario_i_files),
            "scenario_i_tests_upper_bound": sum(d["test_count"] for d in scenario_i_files),
            "scenario_i_ii_files_count": len(scenario_i_ii_files),
            "scenario_i_ii_tests_upper_bound": sum(d["test_count"] for d in scenario_i_ii_files),
        },
    }
    (EVID / "bloco5_tests_ci.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"=== BLOCO 5: IMPACTO EM TESTES E CI (Total pytest={total_collected}) ==="]
    lines.append(f"Resumo: {json.dumps(out['summary'], indent=2)}")
    lines.append("\n--- ARQUIVOS DE TESTE AFETADOS ---")
    for d in affected_details:
        lines.append(
            f"  - {d['test_file']}: {d['test_count']} testes | pure_dormant={d['pure_dormant_only']} | "
            f"I={d['touches_class_i']} II={d['touches_class_ii']} QW={d['touches_queue_writer']} | "
            f"dormant={d['dormant_imported']} | live={d['live_imported']}"
        )
    (EVID / "bloco5_tests_ci.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# BLOCO 6: interface/queue_writer.py
# ---------------------------------------------------------------------------

def run_bloco6() -> dict:
    inv = json.loads((EVID / "bloco2_inventory.json").read_text(encoding="utf-8"))
    qw = inv["interface.queue_writer"]
    qw_src = (ROOT / "interface" / "queue_writer.py").read_text(encoding="utf-8")
    conn_src = (ROOT / "storage" / "connection.py").read_text(encoding="utf-8")
    db_src = (ROOT / "core" / "database.py").read_text(encoding="utf-8")

    # Search all references to SerializedWriteQueue or write_queue across repo tracked .py files
    refs = []
    tracked_res = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    for rel in sorted(tracked_res.stdout.splitlines()):
        rel = rel.strip().replace("\\", "/")
        if not rel or rel.startswith(("scratch/", "archive/")):
            continue
        p = ROOT / rel
        for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if "queue_writer" in line or "SerializedWriteQueue" in line or "write_queue" in line:
                refs.append({"file": rel, "line": lineno, "text": line.strip()[:140]})

    # Test files dedicated to queue_writer vs storage/connection queue
    qw_test_files = [
        "tests/test_queue_writer_batching.py",
        "tests/test_queue_writer_resilience.py",
        "tests/test_connection_queue_resilience.py",
        "tests/test_concurrency_stress.py",
    ]
    suites_info = {}
    pytest_raw = (EVID / "pytest_collect_raw.txt").read_text(encoding="utf-8").splitlines()
    for tf in qw_test_files:
        nodeids = [l.strip() for l in pytest_raw if l.strip().startswith(tf + "::")]
        suites_info[tf] = {"count": len(nodeids), "nodeids": nodeids}

    out = {
        "module_info": qw,
        "references": refs,
        "suites_comparison": suites_info,
        "queue_writer_loc": len(qw_src.splitlines()),
        "storage_connection_loc": len(conn_src.splitlines()),
        "core_database_loc": len(db_src.splitlines()),
    }
    (EVID / "bloco6_queue_writer.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["=== BLOCO 6: INVENTÁRIO DE interface/queue_writer.py ==="]
    lines.append(f"LOC queue_writer.py: {out['queue_writer_loc']} | storage/connection.py: {out['storage_connection_loc']} | core/database.py: {out['core_database_loc']}")
    lines.append(f"Importadores em produção: {qw['prod_importers']}")
    lines.append(f"Testes que importam interface.queue_writer ({qw['total_tests_in_importing_files']} em {len(qw['importing_tests'])} arquivos):")
    for t in qw["importing_tests"]:
        lines.append(f"  - {t['test_file']} ({t['test_count']} testes): linhas={t['lines']}")
    lines.append("\n--- SUÍTES RELACIONADAS ---")
    for tf, info in suites_info.items():
        lines.append(f"  [{tf}] ({info['count']} testes)")
        for nid in info["nodeids"]:
            lines.append(f"    * {nid}")
    lines.append("\n--- REFERÊNCIAS A queue_writer / SerializedWriteQueue / write_queue ---")
    for r in refs:
        lines.append(f"  - {r['file']}:{r['line']}: {r['text']}")
    (EVID / "bloco6_queue_writer.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    b3 = run_bloco3()
    b4 = run_bloco4()
    b5 = run_bloco5()
    b6 = run_bloco6()
    print("Bloco 3 hits:", b3["total_hits"])
    print("Bloco 4 dashboard endpoints:", len(b4["dashboard_endpoints"]), "| non-schema SQL tables:", [d["table"] for d in b4["sql_discrepancies"] if not d["in_storage_schema"]])
    print("Bloco 5 summary:", b5["summary"])
    print("Bloco 6 queue_writer refs:", len(b6["references"]))
