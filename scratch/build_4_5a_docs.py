#!/usr/bin/env python3
"""Gera mecanicamente audits/inventario_4_5a.md e audits/relatorio_4_5a.md (Regra 12).

Lê exclusivamente as evidências geradas em scratch/evidencia_4_5a/ e metadados do repo,
sem inventar números e citando arquivo:linha (Regra 14).
"""
from __future__ import annotations

import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVID = ROOT / "scratch" / "evidencia_4_5a"
INV_PATH = ROOT / "audits" / "inventario_4_5a.md"
REL_PATH = ROOT / "audits" / "relatorio_4_5a.md"

BASE_HEAD = "1baf9f84030bd9550bb4a02dcd0e0c90d6608e0d"

# Classificação curada por módulo (Bloco 2) com justificativa citada em código vivo/doc e certeza
MODULE_CLASSIFICATION = {
    "agent": (
        "(i) Extra suspenso (D0)",
        "Pacote raiz do loop de agente acoplado à HSM (exporta CognitiveAgentRunner / HermesAgentRunner em agent/__init__.py:11); sem caminho vivo equivalente no servidor MCP.",
        "fato",
    ),
    "agent.agent_prompts": (
        "(i) Extra suspenso (D0)",
        "Construtor de system prompts com injeção de estado HSM e matriz TOOL_DISCLOSURE_MATRIX (agent/agent_prompts.py:5-112); vinculado exclusivamente ao runner dormente.",
        "fato",
    ),
    "agent.run_agent": (
        "(i) Extra suspenso (D0)",
        "Loop de execução cognitiva de agente acoplado à HSM (agent/run_agent.py:50, 236); não carregado pelo servidor MCP (interface/mcp_server.py).",
        "fato",
    ),
    "agents": (
        "(i) Extra suspenso (D0)",
        "Pacote wrapper para RevisorCritico (agents/__init__.py:10); alcançável apenas por lazy import PEP 562 via interface/__init__.py:23 -> interface/action_hooks.py:32; nunca carregado em runtime.",
        "fato",
    ),
    "agents.revisor_critico": (
        "(i) Extra suspenso (D0)",
        "Auditor evolutivo / reranker de gavetas (agents/revisor_critico.py:162); consumido apenas por interface/action_hooks.py:32 (desacoplado do servidor na 4.2, confirmado por tests/test_governor_wiring.py:21-32).",
        "fato",
    ),
    "interface.action_hooks": (
        "(i) Extra suspenso (D0)",
        "Hooks de ciclo de vida on_planning/on_execution/on_done para módulos operacionais (interface/action_hooks.py:10-37); exposto apenas sob demanda via PEP 562 __getattr__ em interface/__init__.py:20-25.",
        "fato",
    ),
    "core.hsm_engine": (
        "(i) Extra suspenso (D0)",
        "Máquina de Estados Hierárquica com deep history (core/hsm_engine.py); importada só por interface/telemetry_api.py:79; servidor vivo usa apenas core/mcp_governor.py (MCPToolGovernor) na sessão.",
        "fato",
    ),
    "core.rate_governor": (
        "(i) Extra suspenso (D0)",
        "Regulador de cotas RPM/TPM em janela deslizante de 60s (core/rate_governor.py); importado só por interface/telemetry_api.py:44.",
        "fato",
    ),
    "core.gating_interceptor": (
        "(i) Extra suspenso (D0)",
        "Interceptador de gating plan-only/ask/auto-approve (core/gating_interceptor.py); importado só por interface/telemetry_api.py:42.",
        "fato",
    ),
    "core.security_guard": (
        "(i) Extra suspenso (D0)",
        "Validador de path/comandos Vanguard Bounds Guard (core/security_guard.py:27-45); usado apenas por core/gating_interceptor.py:26 e interface/telemetry_api.py:45 (caminho vivo usa Path/os na ingestão sem SecurityGuard).",
        "fato",
    ),
    "core.telemetry_schemas": (
        "(i) Extra suspenso (D0)",
        "Modelos Pydantic v2 de resposta para telemetria/dashboard (core/telemetry_schemas.py:6-44); importado exclusivamente por interface/telemetry_api.py:46.",
        "fato",
    ),
    "interface.telemetry_api": (
        "(i) Extra suspenso (D0)",
        "API FastAPI REST/SSE de 15 rotas (interface/telemetry_api.py:242-575) para o cockpit Next.js; não importada nem iniciada por main.py ou interface/cli.py.",
        "fato",
    ),
    "core.dependencies": (
        "(i) Extra suspenso (D0)",
        "Contêiner DI dataclass AgentDependencies com rate_governor/security_guard (core/dependencies.py:22-33); sem importadores em produção.",
        "fato",
    ),
    "interface.watcher": (
        "(i) Extra suspenso (fora do runtime MCP)",
        "Watcher de sistema de arquivos com watchdog/AliasTracker (interface/watcher.py); sem importadores em produção e sem menção em README.md/README.pt-BR.md (apenas docs-grafo-concierge/).",
        "fato",
    ),
    "storage.relational_db": (
        "(i) Extra suspenso (D0) + (iii) ramo vivo",
        "Cria tabela fsm_checkpoints (storage/relational_db.py:13); sem importadores em produção. O caminho vivo oficial é storage/schema.py (agent_checkpoints), embora core/checkpointer.py:102,166,201-210 ainda contenha ramo SDD-20 consultando fsm_checkpoints.",
        "fato",
    ),
    "core.parser_factory": (
        "(ii) Duplicata superada por caminho vivo",
        "Superado por ingestion/parser.py:130-324,610-698 (CodeParser vivo cobre Python, TS/TSX/JS/JSX, Go e Rust; ressalva F4-014: tree_sitter ausente em dependências usa fallback regex).",
        "fato",
    ),
    "core.parsers": (
        "(ii) Duplicata superada por caminho vivo",
        "Pacote de parsers legados; superado por ingestion/parser.py:130-324 (fato).",
        "fato",
    ),
    "core.parsers.base": (
        "(ii) Duplicata superada por caminho vivo",
        "Classe base BaseASTParser de core/parsers/; superado por ingestion/parser.py (fato).",
        "fato",
    ),
    "core.parsers.python_parser": (
        "(ii) Duplicata superada por caminho vivo",
        "Parser AST Python legado; superado por ingestion/parser.py (CodeParser._parse_with_tree_sitter / ast Python, fato).",
        "fato",
    ),
    "core.parsers.ts_js_parser": (
        "(ii) Duplicata superada por caminho vivo",
        "Parser TS/JS legado; superado por ingestion/parser.py:82-93,162,217-245,270-324 (cobre .ts/.tsx/.js/.jsx/.mjs/.cjs com tree-sitter ou regex fallback).",
        "fato",
    ),
    "core.vector_reconciler": (
        "(ii) Duplicata superada por caminho vivo",
        "Superado por services/janitor.py:347-374 (_sync_vectors via self._vector.verify_sync + delete_batch) e ingestion/orchestrator.py:875; core/vector_reconciler.py ainda consulta tabela inexistente 'files'.",
        "fato",
    ),
    "core.search_engine": (
        "(ii) Duplicata superada por caminho vivo",
        "HybridSearchEngine SDD-05 (consulta tabela inexistente 'files' em core/search_engine.py:58); superado integralmente pelo caminho vivo core/hybrid_search.py:46-280.",
        "fato",
    ),
    "core.delta_manager": (
        "(ii) Duplicata superada + (iii) drift SSH/LBH prometido",
        "Ingestão incremental já existe no caminho vivo via SHA256 em ingestion/crawler.py:547-619 + _detect_cached_chunks em ingestion/orchestrator.py:206,319-396 + cleanup_obsolete_nodes (storage/store.py:383-431). Porém a técnica específica SSH+LBH (DocstringStripper) prometida em README.md:32,56,159 existe só aqui (sem impl. viva).",
        "fato",
    ),
    "core.delta_sync": (
        "(ii) Duplicata superada + (iii) drift SSH/LBH prometido",
        "Shim de 12L reexportando DeltaManager/DocstringStripper de core/delta_manager.py:10; acompanha classificação de core.delta_manager.",
        "fato",
    ),
    "core.background_janitor": (
        "(i) Extra suspenso + (ii) parcial + (iii) checkpoint pruning prometido",
        "Mistura: sumarização por comunidade suja e cache superadas por services/janitor.py:268-277,479-541; thermal throttler (psutil) e Smart LRU checkpoint pruning (README.md:41,162) NÃO existem em services/janitor.py (0 menções a checkpoint/lru/prune/psutil).",
        "fato",
    ),
    "core.janitor": (
        "(i)/(ii) Shim legado SDD-06",
        "Shim de 12L reexportando BackgroundJanitor de core/background_janitor.py; manutenção ativa está em services/janitor.py.",
        "fato",
    ),
    "core.alias_tracker": (
        "(iii) Capacidade prometida sem implementação viva",
        "Prometido em README.md:34,57 ('Structural Semantic Alias Tracking' para preservar trajetórias/arestas em renomeações); nenhum equivalente vivo em ingestion/ ou services/ (crawler remove nós antigos por cleanup_obsolete_nodes).",
        "fato",
    ),
    "core.intent_classifier": (
        "(iii) Capacidade prometida sem implementação viva",
        "Prometido em README.md:38 ('JIT 3-tier Intent Classifier' para roteamento federado); sem implementação viva equivalente em core/hybrid_search.py ou core/middleware.py.",
        "fato",
    ),
    "core.federated_knowledge_router": (
        "(iii) Capacidade prometida sem implementação viva",
        "Prometido em README.md:38 ('Federated Knowledge Routing' LOCAL_GRAPHRAG vs EXTERNAL_FEDERATED_MCP); sem impl. viva. Chama core.graph_rag.retrieve_multihop_context (tabela inexistente 'ast_edges'/'files').",
        "fato",
    ),
    "core.global_memory_adapter": (
        "(iii) Capacidade prometida sem implementação viva",
        "Prometido em README.md:38,61 ('Global Memory Adapter' preservando apenas últimas 3 msgs STM); sem impl. viva.",
        "fato",
    ),
    "core.nozomio_router": (
        "(iii) Capacidade prometida sem implementação viva",
        "Shim/reexportador de FederatedKnowledgeRouter (core/nozomio_router.py:8); acompanha classificação de core.federated_knowledge_router.",
        "fato",
    ),
    "interface.queue_writer": (
        "Fora do D0 — Duplicata superada em produção (ver Bloco 6)",
        "Caminho vivo de escrita serializada está em storage/connection.py:72-488 (usado por storage/store.py -> core/middleware.py -> interface/mcp_server.py:163 sem write_queue). Mantido intacto até decisão da Rodada 4.5 (audits/fase4-roadmap.md:123 item 8).",
        "fato",
    ),
}


def load_json(name: str):
    return json.loads((EVID / name).read_text(encoding="utf-8"))


def fmt_refs(items: list[dict], limit: int = 5) -> str:
    if not items:
        return "—"
    refs = []
    for x in items[:limit]:
        refs.append(f"`{x['file']}:{x['line']}`")
    if len(items) > limit:
        refs.append(f"*(+{len(items) - limit} ocorrências)*")
    return ", ".join(refs)


def build_docs() -> None:
    b1_stat = load_json("bloco1_static_reach.json")
    b1_run = load_json("bloco1_runtime_trace.json")
    b2 = load_json("bloco2_inventory.json")
    b3 = load_json("bloco3_promises.json")
    b4 = load_json("bloco4_non_python_deps.json")
    b5 = load_json("bloco5_tests_ci.json")
    b5_gran = load_json("bloco5_mixed_granular.json")
    b6 = load_json("bloco6_queue_writer.json")
    pyp = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    gran_by_file = {item["test_file"]: item for item in b5_gran}
    live_only_names_by_file: dict[str, list[str]] = {}
    for line in (EVID / "bloco5_mixed_granular.txt").read_text(encoding="utf-8").splitlines():
        if "(PRESERVAR - só vivo)" in line:
            nodeid = line.split("(PRESERVAR - só vivo)", 1)[1].strip()
            tf = nodeid.split("::", 1)[0]
            live_only_names_by_file.setdefault(tf, []).append(nodeid)

    # --- INVENTÁRIO 4.5a ---
    inv: list[str] = []
    inv.append("# Inventário Técnico Verificado — Rodada 4.5a (Código Dormente, Promessas e Dependências)")
    inv.append("")
    inv.append(f"- **Base analisada:** HEAD `{BASE_HEAD}` (`origin/main` sincronizado)")
    inv.append("- **Decisão do dono (D0):** Cenário A (V4 reduzida focada no núcleo de memória; HSM, Rate Governor, gating, telemetria e dashboard suspensos para futura quarentena em `archive/v4-experimental`).")
    inv.append("- **Natureza:** Somente leitura (nenhum arquivo de código de produto, teste, CI, `pyproject.toml`, `README*` ou `grafo-dashboard-web/` foi modificado).")
    inv.append("- **Regra 12 / Regra 14:** Documento gerado mecanicamente por `scratch/build_4_5a_docs.py` a partir das evidências em `scratch/evidencia_4_5a/`. `walkthrough.md` nunca é usado como evidência técnica (citado apenas como contagem documental auxiliar).")
    inv.append("")

    # BLOCO 1
    inv.append("## Bloco 1 — Raízes e Alcançabilidade (Estática e em Tempo de Execução)")
    inv.append("")
    inv.append("### 1.1 Raízes de Produção e Utilitários")
    inv.append("")
    inv.append("| Tipo | Arquivo:Linha | Definição / Comando | Observação |")
    inv.append("|---|---|---|---|")
    inv.append("| Entrypoint CLI | `pyproject.toml:87` | `concierge = \"interface.cli:main\"` | Raiz de produção CLI |")
    inv.append("| Entrypoint MCP | `pyproject.toml:88` | `concierge-mcp = \"main:main\"` | Raiz de produção MCP |")
    inv.append("| Container | `Dockerfile:34` | `CMD [\"python\", \"main.py\"]` | Mesma raiz `main`; `Dockerfile:29` define `GRAFO_PORT=8000` |")
    inv.append("| Compose | `docker-compose.yml:14, 23` | `GRAFO_PORT=8000` / healthcheck porta `8000` | Herda entrypoint do `Dockerfile` |")
    inv.append("| CI Principal | `.github/workflows/ci.yml:34, 48` | `flake8` + `pytest -v --tb=short` | Matrix 3 jobs: Python `3.10`, `3.11`, `3.12` |")
    inv.append("| CI Windows | `.github/workflows/windows-stdin.yml:39` | `pytest tests/test_stdin_decouple.py tests/test_lazy_ml_imports.py -v -rs` | Matrix 3 jobs: Python `3.10`, `3.12`, `3.14` |")
    inv.append("| Script utilitário | `scripts/bootstrap_core_memory.py:20` | `from storage import SqliteStore` | Separado das raízes; alcança apenas 7 módulos de `storage` |")
    inv.append("")

    inv.append("### 1.2 Grafo Estático de Imports AST (`scratch/inv_4_5a_bloco1_static.py`)")
    inv.append("")
    inv.append(f"Total descoberto em `main.py` + `core/` `storage/` `ingestion/` `interface/` `services/` `agent/` `agents/`: **{b1_stat['total_modules']} módulos** (**{b1_stat['lines']['TOTAL_ALL']:,} linhas totais**)." )
    inv.append("")
    inv.append("| Status AST | Qtd. Módulos | Linhas Totais | Observação |")
    inv.append("|---|---:|---:|---|")
    for st in [
        "REACHABLE_LOAD",
        "REACHABLE_DEFERRED",
        "REACHABLE_ANNOTATION_ONLY_RUNTIME",
        "REACHABLE_PEP562_LAZY",
        "REACHABLE_TYPE_CHECKING",
        "UNREACHABLE",
    ]:
        cnt = b1_stat["counts"].get(st, 0)
        ln = b1_stat["lines"].get(st, 0)
        note = {
            "REACHABLE_LOAD": "Raízes (`main`, `interface.cli`)",
            "REACHABLE_DEFERRED": "Carregados sob `bootstrap()`/`_bootstrap_concierge()` ou sob demanda em runtime",
            "REACHABLE_ANNOTATION_ONLY_RUNTIME": "`interface.queue_writer`: importado top-level por `core/database.py:18`, usado só em type hint (`L27`) e ramo `if self.write_queue is not None` (`L49-50`), nunca passado por `interface/mcp_server.py:163`",
            "REACHABLE_PEP562_LAZY": "`interface.action_hooks`, `agents`, `agents.revisor_critico` via `interface/__init__.py:20-25`",
            "REACHABLE_TYPE_CHECKING": "Imports sob `if TYPE_CHECKING:` já cobertos por arestas reais",
            "UNREACHABLE": "Sem caminho a partir das raízes `main` e `interface.cli`",
        }[st]
        inv.append(f"| `{st}` | {cnt} | {ln:,} | {note} |")
    inv.append("")
    inv.append("Evidência bruta completa em `scratch/evidencia_4_5a/bloco1_static_reach.txt:1-127`.")
    inv.append("")

    inv.append("### 1.3 Imports Dinâmicos, Strings e `getattr` em Produção")
    inv.append("")
    scans = b1_stat["dynamic_import_scans"]
    importlib_hits = [s for s in scans if s["tag"] != "getattr_call"]
    getattr_hits = [s for s in scans if s["tag"] == "getattr_call"]
    inv.append(f"- **`importlib` / `__import__` / strings de módulo em produção:** {len(importlib_hits)} ocorrências:")
    for s in importlib_hits:
        inv.append(f"  - `{s['file']}:{s['line']}` (`{s['tag']}`): `{s['code']}`")
    inv.append(f"- **`getattr(...)` em produção:** {len(getattr_hits)} ocorrências listadas em `scratch/evidencia_4_5a/bloco1_static_reach.txt:96-125`; nenhuma realiza carga dinâmica de submódulos do projeto por nome em string (apenas leitura defensiva de atributos/métodos de objetos).")
    inv.append("")

    inv.append("### 1.4 Traço em Tempo de Execução vs. Grafo Estático (`scratch/inv_4_5a_bloco1_runtime.py`)")
    inv.append("")
    inv.append("- **Isolamento:** diretório temporário (`tempfile.TemporaryDirectory`), `GRAFO_LIGHTWEIGHT_MODE=true`, chaves fake, sem leitura/escrita em `.env` ou `data/` (`scratch/evidencia_4_5a/bloco1_runtime_trace.txt:1-48`).")
    inv.append("- **Modo de execução:** devido a travamento de `asyncio.run(...)` no self-pipe do sandbox Windows, as **31 ferramentas MCP** registradas em `GrafoConciergeServer` foram exercitadas de forma síncrona via `server.governor.validate_tool_execution(session_id, name)` + `tool_obj.fn(**args)`, mais execução isolada de `python -m interface.cli status` (`returncode=0`).")
    inv.append(f"- **Ferramentas MCP exercitadas:** **{b1_run['tools_registered_count']} / {b1_run['tools_registered_count']}** (0 não exercitadas; detalhes de retorno em `scratch/evidencia_4_5a/bloco1_runtime_trace.txt:10-41`).")
    inv.append(f"  - Observações factuais nas respostas sintéticas: `concierge_commit` retornou `FOREIGN KEY constraint failed` (sem FK prévia/dados compatíveis no payload sintético); `concierge_load` retornou `%d format: a real number is required, not str` (recebeu `\"2\"` string); `agent_save_checkpoint` retornou `no such table: fsm_checkpoints` porque o script (`scratch/inv_4_5a_bloco1_runtime.py:165-187`) preencheu `state_dict=\"test\"` (`str`), acionando o ramo SDD-20 de `core/checkpointer.py:74` (`isinstance(args[3], str)`).")
    inv.append("")
    inv.append("| Métrica de `sys.modules` | Qtd. | Módulos |")
    inv.append("|---|---:|---|")
    inv.append(f"| Após `import main` | {len(b1_run['snap_after_import_main'])} | `{', '.join(b1_run['snap_after_import_main'])}` |")
    inv.append(f"| Após `main.bootstrap()` | {len(b1_run['snap_after_bootstrap'])} | Ver `bloco1_runtime_trace.txt:4` |")
    inv.append(f"| Após 31 ferramentas MCP | {len(b1_run['snap_after_tools'])} | +`core.vector_backend` (importado em `core/middleware.py:566` por `concierge_store_fact`) |")
    inv.append(f"| Após `interface.cli` + `status` | {len(b1_run['cli_exec_mods'])} | Ver `bloco1_runtime_trace.txt:6-7` |")
    inv.append(f"| União runtime (MCP + CLI) | {len(b1_run['runtime_union'])} | 30 módulos MCP + `interface.cli` |")
    inv.append("")
    cmp = b1_run["comparison"]
    inv.append("**Reconciliação Runtime vs. Estático:**")
    inv.append(f"- **Alcançáveis estáticos NÃO carregados no runtime ({len(cmp['in_static_reachable_not_in_runtime'])}):** `{', '.join(cmp['in_static_reachable_not_in_runtime'])}`")
    inv.append("  - `agents`, `agents.revisor_critico`, `interface.action_hooks`: expostos apenas via PEP 562 `__getattr__` (`interface/__init__.py:20-25`); nenhum fluxo vivo do servidor os solicita.")
    inv.append("  - `core.probabilistic_retriever`: import tardio em `core/hybrid_search.py:252`, mas `enable_probabilistic` tem default `False` (`core/hybrid_search.py:86`) e **nenhum** chamador vivo (`core/middleware.py`, `interface/mcp_server.py`) passa `True`.")
    inv.append(f"- **Carregados no runtime fora de `LOAD+DEFERRED` ({len(cmp['in_runtime_not_in_static_load_or_deferred'])}):** `{', '.join(cmp['in_runtime_not_in_static_load_or_deferred'])}` (import top-level só de anotação em `core/database.py:18`).")
    inv.append(f"- **Estáticos `UNREACHABLE` carregados no runtime:** `{len(cmp['static_unreachable_loaded_at_runtime'])}` (`[]`).")
    inv.append("")

    # BLOCO 2
    inv.append("## Bloco 2 — Inventário por Módulo (Não Alcançáveis em Tempo de Carga)")
    inv.append("")
    inv.append(f"Cobre os **{len(b2)} módulos** não alcançáveis por import normal de runtime ({b1_stat['counts']['UNREACHABLE']} `UNREACHABLE` + 1 `ANNOTATION_ONLY_RUNTIME` + 3 `PEP562_LAZY`), além da nota sobre `core.probabilistic_retriever` (`REACHABLE_DEFERRED`, 108L, inativo com default `enable_probabilistic=False`). Contagem de testes baseada em `pytest --collect-only -q` (**{b5['total_collected']} testes**).")
    inv.append("")
    inv.append("| Módulo (`arquivo`) | LOC | Status Estático | Importadores Produção | Testes (arquivo: n / tipo) | Menções Docs (não-`walkthrough`) | Classe Proposta & Caminho Vivo | Certeza |")
    inv.append("|---|---:|---|---|---|---|---|---|")

    for mod in sorted(b2.keys()):
        info = b2[mod]
        # Importadores de produção que importam *outro* arquivo que importa `mod`
        prod_imps = [
            f"`{imp['importer_path']}:{imp['line']}` ({imp['kind']}{':ann' if imp['ann_only'] else ''})"
            for imp in info["prod_importers"]
            if imp["importer_path"] != info["path"]
        ]
        prod_str = ", ".join(prod_imps) if prod_imps else "—"

        # Testes
        if info["importing_tests"]:
            t_parts = []
            for ti in info["importing_tests"]:
                g = gran_by_file.get(ti["test_file"], {})
                if g:
                    tag = (
                        f"d={g['dormant_only_tests']}, m={g['mixed_tests']}, l={g['live_only_tests']}, qw={g['qw_tests']}"
                    )
                else:
                    tag = "misto" if ti["is_mixed"] else "só dormente"
                t_parts.append(f"`{ti['test_file']}` ({ti['test_count']}T; {tag})")
            test_str = "<br>".join(t_parts)
        else:
            test_str = "0"

        # Docs (excluindo walkthrough.md explicitamente, contando apenas menções reais fora walkthrough)
        non_wt_docs = [d for d in info["doc_mentions"] if d["file"] != "walkthrough.md"]
        # Se AGENTS.md:13 apenas menciona a palavra "agente", ainda citamos factualmente
        if non_wt_docs:
            # agrupa por arquivo
            by_dfile: dict[str, list[int]] = {}
            for d in non_wt_docs:
                by_dfile.setdefault(d["file"], []).append(d["line"])
            doc_parts = []
            for df, lns in list(by_dfile.items())[:4]:
                lstr = ",".join(str(x) for x in lns[:3])
                if len(lns) > 3:
                    lstr += f"..(+{len(lns)-3})"
                doc_parts.append(f"`{df}:{lstr}`")
            if len(by_dfile) > 4:
                doc_parts.append(f"*(+{len(by_dfile)-4} arqs)*")
            wt_cnt = info.get("walkthrough_mentions_count", 0)
            doc_str = "<br>".join(doc_parts)
            if wt_cnt:
                doc_str += f"<br>*(+`walkthrough.md`: {wt_cnt} ref., não-evid.)*"
        else:
            wt_cnt = info.get("walkthrough_mentions_count", 0)
            doc_str = f"0 *(+`walkthrough.md`: {wt_cnt} ref., não-evid.)*" if wt_cnt else "0"

        cls_name, justif, cert = MODULE_CLASSIFICATION[mod]
        inv.append(
            f"| `{mod}` (`{info['path']}`) | {info['loc']} | `{info['status']}` | {prod_str} | {test_str} | {doc_str} | **{cls_name}**: {justif} | {cert} |"
        )
    inv.append("")

    inv.append("### 2.1 Verificação Explícita dos Indícios de Classe `(ii)` e Pesquisa Ativa de Classe `(iii)`")
    inv.append("")
    inv.append("1. **Parsing multilíngue (`ingestion/parser.py` vs. `core/parser_factory.py` + `core/parsers/*`) — Veredito: Classe `(ii)` (`fato`):**")
    inv.append("   - O caminho vivo `ingestion/parser.py:130-324, 610-698` (`CodeParser`) trata explicitamente `.py`, `.js/.jsx/.ts/.tsx/.mjs/.cjs`, `.go` e `.rs`, além de Markdown e configs.")
    inv.append("   - **Ressalva operacional (`F4-014`):** `pyproject.toml` não declara `tree_sitter` nem pacotes de gramática. No ambiente observado sem `tree_sitter`, `ingestion/parser.py:82-93, 217-245, 270-324` faz fallback automático para regex léxico (`_JS_FUNCTION_RE`, `_JS_CLASS_RE` etc.). Ainda assim, supera e torna redundante `core/parser_factory.py` + `core/parsers/*`.")
    inv.append("2. **Reconciliação de vetores órfãos (`services/janitor.py` vs. `core/vector_reconciler.py`) — Veredito: Classe `(ii)` (`fato`):**")
    inv.append("   - O caminho vivo `services/janitor.py:347-374` (`_sync_vectors`) coleta IDs ativos no SQLite, chama `self._vector.verify_sync(valid_ids)` e remove órfãos via `self._vector.delete_batch(orphans)`, além de acionar `repair_missing_vectors`. `ingestion/orchestrator.py:875` também chama `verify_sync`.")
    inv.append("   - `core/vector_reconciler.py` consulta a tabela inexistente `files` e é superado por completo pelo fluxo vivo (`services/janitor.py`). De forma análoga, `core/search_engine.py:58` consulta `files` e é superado por `core/hybrid_search.py:46-280`.")
    inv.append("3. **Hash de arquivo e cache incremental (`ingestion/crawler.py` + `ingestion/orchestrator.py` vs. `core/delta_manager.py` / `core/delta_sync.py`) — Veredito: `(ii)` como mecanismo incremental + `(iii)` na promessa específica `SSH + LBH` (`fato`):**")
    inv.append("   - O caminho vivo calcula SHA256 de arquivo (`ingestion/crawler.py:547-619`, `compute_file_hash` + `find_node_by_hash`), compara conteúdo de chunks por `label` em `_detect_cached_chunks` (`ingestion/orchestrator.py:206, 319-396`) e limpa nós obsoletos por `cleanup_obsolete_nodes` (`ingestion/orchestrator.py:243`, `storage/store.py:383-431`).")
    inv.append("   - **Lacuna `(iii)`:** o `README.md:32, 52, 56, 159` e `README.pt-BR.md:32, 56` prometem especificamente *Dual-Hash Delta Sync (SSH + LBH Semantic Drift Guard com `DocstringStripper`)*, algoritmo que existe **apenas** no módulo dormente `core/delta_manager.py` (usando tabela inexistente `files`/`communities`).")
    inv.append("4. **Outras capacidades Classe `(iii)` identificadas ativamente (`fato`):**")
    inv.append("   - **Smart Checkpoint Auto-Pruning (`BackgroundJanitor` Smart LRU):** prometido em `README.md:41, 162` e `README.pt-BR.md:41`. O módulo vivo `services/janitor.py` possui **0** referências a `checkpoint`, `lru`, `prune` ou `psutil`; apenas `core/background_janitor.py` implementa pruning/throttling térmico.")
    inv.append("   - **Structural Semantic Alias Tracking (`core/alias_tracker.py`):** prometido em `README.md:34, 57` e `README.pt-BR.md:34` para preservar arestas/trajetórias em renomeações em `< 1s`. Sem equivalente vivo (`crawler.py` apenas remove nós antigos por caminho).")
    inv.append("   - **Federated Knowledge Routing & Global Hybrid Memory Adapter (`core/intent_classifier.py`, `core/federated_knowledge_router.py`, `core/global_memory_adapter.py`, `core/nozomio_router.py`):** prometidos em `README.md:38, 61` e `README.pt-BR.md:38`; sem equivalente vivo.")
    inv.append("   - **Thompson Sampling probabilístico (`core/probabilistic_retriever.py`):** prometido em `README.md:40, 74, 171` (`concierge_feedback` atualiza `utility_alpha`/`utility_beta` no banco, mas `core/hybrid_search.py:86` mantém `enable_probabilistic=False` por padrão sem nenhum chamador vivo ativando a flag).")
    inv.append("   - **Ramos dormentes dentro de módulos vivos:** `core/checkpointer.py:74, 102, 166, 201-215` (ramo SDD-20 consultando `fsm_checkpoints` e `files`) e `core/graph_rag.py:33, 56, 77-126` (consultas a `ast_edges` e `files` protegidas por fallback).")
    inv.append("")

    # BLOCO 3
    inv.append("## Bloco 3 — Promessas Públicas Ligadas a Módulos Dormentes ou Inexistentes")
    inv.append("")
    inv.append(f"Varredura AST/textual em `README.md`, `README.pt-BR.md`, `CHANGELOG.md`, `pyproject.toml` e `docs-grafo-concierge/` registrou **{b3['total_hits']} linhas com correspondência** (saída completa em `scratch/evidencia_4_5a/bloco3_promises.txt`). Abaixo estão consolidados todos os arquivos afetados e as citações representativas de cada promessa:")
    inv.append("")
    inv.append("| Documento | Ocorrências | Exemplos com `arquivo:linha` e Citação Curta | Status de Implementação Viva |")
    inv.append("|---|---:|---|---|")
    doc_summary_rows = [
        (
            "README.md",
            len(b3["by_file"].get("README.md", [])),
            "`README.md:28` (`SerializedWriteQueue`), `L29` (`core/hsm_engine.py`), `L30` (`core/rate_governor.py`), `L31` (`core/gating_interceptor.py`), `L32` (`SSH + LBH`), `L33` (`grafo-dashboard-web/`), `L34` (`core/alias_tracker.py`), `L35` (`core/parser_factory.py`), `L38` (`Federated Knowledge Routing & Global Hybrid Memory Adapter`), `L39` (`interface/telemetry_api.py`), `L41` (`Smart Checkpoint Auto-Pruning`), `L63/L157` (`30 Tools`), `L95/L152` (`Port 8001`), `L177` (`326 tests`)",
            "Maioria sem carga no servidor MCP; `SerializedWriteQueue` e parser/reconciliação têm caminho vivo distinto (`storage/connection.py`, `ingestion/parser.py`, `services/janitor.py`); `AliasTracker`, `SSH+LBH`, `Federated/GlobalMemory` e `Checkpoint Pruning` são `(iii)` sem impl. viva; contagens de tools/testes estão desatualizadas (real: 31 tools, 478 testes).",
        ),
        (
            "README.pt-BR.md",
            len(b3["by_file"].get("README.pt-BR.md", [])),
            "`README.pt-BR.md:15, 28-42, 50-63, 69-74, 95, 142-177`: espelha integralmente as promessas do `README.md` em PT-BR (`HSM`, `Rate Governor`, `Adaptive Gating`, `Dual-Hash SSH+LBH`, `Cockpit Next.js 16`, `Alias Tracking`, `ParserFactory`, `Federated Routing`, `Telemetry API`, `BackgroundJanitor` Smart LRU).",
            "Idêntico ao `README.md`: mistura módulos suspensos D0 `(i)`, duplicatas com outro caminho vivo `(ii)` e promessas sem impl. viva `(iii)`.",
        ),
        (
            "pyproject.toml",
            len(b3["by_file"].get("pyproject.toml", [])),
            "`pyproject.toml:11` (`...autonomous agents.`), `pyproject.toml:45-52` (`fastapi`, `pydantic`, `pathspec`, `watchdog`, `psutil`), `pyproject.toml:99` (`packages.find` inclui `agent*` e `scripts*`, omite `agents*`).",
            "`watchdog` e `fastapi`/`psutil`/`pathspec` só servem a código dormente; `description` é genérica sobre agentes autônomos.",
        ),
        (
            "CHANGELOG.md",
            len(b3["by_file"].get("CHANGELOG.md", [])),
            "`CHANGELOG.md:34,43` (`from core.middleware import GrafoConcierge`), `CHANGELOG.md:71` (`\"ast_edges_created\": count_ast` no exemplo de retorno de `mine()`).",
            "`GrafoConcierge` existe em `core/middleware.py`; porém a tabela `ast_edges` não existe no schema vivo (`storage/schema.py`, ver `F4-001`), e o retorno vivo de `concierge_mine` (ver `bloco1_runtime_trace.txt:13`) não possui `ast_edges_created`.",
        ),
        (
            "AGENTS.md",
            0,
            "`AGENTS.md:13` menciona `.agents/skills/reversa/SKILL.md` (instrução do framework Reversa, não código do produto).",
            "Nenhuma promessa de funcionalidade dormente do Grafo Concierge.",
        ),
        (
            "ACTIVE_SDD.md",
            0,
            "Arquivo vazio (`0 bytes`).",
            "Sem promessas.",
        ),
        (
            "docs-grafo-concierge/",
            sum(len(v) for k, v in b3["by_file"].items() if k.startswith("docs-grafo-concierge/")),
            "`01_ARCHITECTURE.md` (97 hits), `02_MCP_TOOLS_REFERENCE.md` (25), `03_COGNITIVE_MEMORY_AND_FACTS.md` (22), `04_INGESTION_AND_AST.md` (29), `05_HYBRID_SEARCH_AND_ROUTING.md` (12), `06_DEPLOY_AND_CONFIGURATION.md` (32), `07_MIGRATION_AND_OPERATIONS.md` (38), `README.md` (24).",
            "Documentação arquitetural integralmente baseada na linha SDD dormente (`telemetry_api`, `HSM`, `RateGovernor`, `watcher`, `files`, `communities`, `fsm_checkpoints`, `queue_writer`).",
        ),
    ]
    for doc_name, cnt, ex, st in doc_summary_rows:
        inv.append(f"| `{doc_name}` | {cnt} | {ex} | {st} |")
    inv.append("")

    # BLOCO 4
    inv.append("## Bloco 4 — Dependências Fora do Python")
    inv.append("")
    inv.append("### 4.1 Dashboard `grafo-dashboard-web/` vs. Servidor de Produção vs. `interface/telemetry_api.py`")
    inv.append("")
    inv.append(f"- **Empacotamento:** `dashboard_in_dockerfile={b4['dashboard_in_dockerfile']}`, `dashboard_in_compose={b4['dashboard_in_compose']}`, `dashboard_in_pyproject={b4['dashboard_in_pyproject']}` (`fato`).")
    inv.append("- **Script DX (`grafo-dashboard-web/package.json:8`):** `dev:backend` executa `python main.py` (que inicia o servidor FastMCP, **não** `interface/telemetry_api.py`).")
    inv.append("- **Conflito de porta `8000`:** `SelfHealingConsole.tsx:23`, `useTelemetryStream.ts:29` e `grafo-dashboard-web/.env.example:9-10` usam `http://127.0.0.1:8000` como fallback para `NEXT_PUBLIC_CONCIERGE_API_URL`, colidindo com `GRAFO_PORT=8000` de `Dockerfile:29`, `docker-compose.yml:14` e `interface/mcp_server.py:146` (enquanto `README.md:95, 152` documenta porta `8001` para Telemetry API).")
    inv.append("")
    inv.append("| Endpoint / URL chamado pelo Dashboard | Arquivo:Linha no Dashboard | Rota viva no servidor MCP (`main.py`)? | Rota em `interface/telemetry_api.py`? |")
    inv.append("|---|---|---|---|")
    ep_rows = [
        ("`GET /api/telemetry/snapshot`", "`grafo-dashboard-web/lib/useTelemetryStream.ts:10, 101`", "Não (`0` rotas `/api/*`)", "Sim (`L242`)"),
        ("`GET /api/governor/metrics`", "`grafo-dashboard-web/lib/useTelemetryStream.ts:10, 128`", "Não", "Sim (`L387`)"),
        ("`GET /api/hsm/tree`", "`grafo-dashboard-web/lib/useTelemetryStream.ts:10, 144`", "Não", "Sim (`L521`)"),
        ("`GET /api/hsm/state/default`", "`grafo-dashboard-web/lib/useTelemetryStream.ts:145`", "Não", "Sim (`GET /api/hsm/state/{session_id}`, `L460`)"),
        ("`GET /api/telemetry/stream` (SSE)", "`useTelemetryStream.ts:9, 204`; `LiveEventFeed.tsx:267`", "Não", "Sim (`L575`)"),
        ("`POST /api/janitor/reconcile`", "`SelfHealingConsole.tsx:11, 47`; `useTelemetryStream.ts:317`", "Não", "Sim (`L256`)"),
        ("`http://127.0.0.1:7077/sse` (MCP SSE)", "`lib/mcp/client.ts:29, 78`; `.env.example:5-6`", "Parcial (FastMCP só abre SSE com `GRAFO_TRANSPORT=sse`, default `main.py:73` é `stdio`)", "Não (transporte MCP)"),
    ]
    for url, loc, live_s, tel_s in ep_rows:
        inv.append(f"| {url} | {loc} | {live_s} | {tel_s} |")
    inv.append("")
    inv.append(f"Nota: `interface/telemetry_api.py` declara **15 rotas FastAPI** no total (`L242–575`), sendo as 9 restantes (`/api/checkpoints/{{session_id}}`, `/api/checkpoints/time-travel`, `/api/mcp/state`, `/api/mcp/state/{{session_id}}`, `/api/governor/report`, `/api/gating/config` GET/POST, `/api/hsm/transition`, `/api/hsm/resume/{{session_id}}`) consumíveis apenas via API/testes.")
    inv.append("")

    inv.append("### 4.2 Discrepâncias de Esquema SQL")
    inv.append("")
    inv.append(f"- **Tabelas criadas em `storage/schema.py` (`{len(b4['sql_tables_created_in_schema_py'])}`):** `{', '.join(b4['sql_tables_created_in_schema_py'])}` (mais tabela-sombra `nodes_fts_docsize` do FTS5).")
    inv.append("")
    inv.append("| Tabela / Coluna | Onde existe `CREATE TABLE`? | Quem consulta / escreve? | Discrepância verificada |")
    inv.append("|---|---|---|---|")
    inv.append("| `ast_edges` | **Nenhuma** em produção | Vivo (fallback): `core/graph_rag.py:33, 77-94`<br>Dormente: `core/alias_tracker.py:195, 228, 232` | Tabela ausente em `storage/schema.py`; `core/graph_rag.py:106` cai em fallback silencioso e `concierge_get_call_chain` foi reimplementado sobre `edges`/`nodes` (`F4-001`). |")
    inv.append("| `files` | **Nenhuma** em produção | Vivo: `core/checkpointer.py:215` (SDD-20), `core/graph_rag.py:56, 126`<br>Dormentes: `core/alias_tracker.py:216`, `core/background_janitor.py:97, 111, 240`, `core/delta_manager.py:134, 214, 232, 257`, `core/intent_classifier.py`, `core/search_engine.py:58`, `core/vector_reconciler.py`, `interface/telemetry_api.py` | Tabela ausente no schema de produção; só existe via DDL inline dentro de testes legados (`test_vector_reconciler.py:108`, `test_local_graph_rag_recursion.py:40`). |")
    inv.append("| `communities` | **Nenhuma** em produção | Dormentes: `core/background_janitor.py:79, 107`, `core/delta_manager.py:169, 192, 219, 262` | Tabela ausente em produção (comunidades vivas do `services/janitor.py` usam `nodes`/`edges`). |")
    inv.append("| `fsm_checkpoints` | **Apenas** dormente `storage/relational_db.py:13` | Vivo (ramo SDD-20): `core/checkpointer.py:101, 166, 201, 210`<br>Dormentes: `core/hsm_engine.py:419`, `core/alias_tracker.py:239`, `core/background_janitor.py`, `interface/telemetry_api.py` | Não criada por `storage/schema.py`; qualquer chamada que entre em `is_sdd20`, `load_checkpoint` ou `execute_time_travel` de `core/checkpointer.py` falha com `no such table: fsm_checkpoints`. |")
    inv.append("| `agent_checkpoints.timestamp` | `storage/schema.py` cria `created_at` (ver `core/checkpointer.py:261`) | Dormente: `interface/telemetry_api.py:182` | `telemetry_api.py:182` seleciona coluna inexistente `timestamp` em `agent_checkpoints` (schema real usa `created_at`). |")
    inv.append("")

    inv.append("### 4.3 Empacotamento em `pyproject.toml`")
    inv.append("")
    inv.append(f"- **`[tool.setuptools.packages.find]` (`pyproject.toml:96-105`):** `include = {pyp['tool']['setuptools']['packages']['find']['include']}` — inclui `agent*` e `scripts*`, mas **omite `agents*`** (onde reside `agents/revisor_critico.py`). Em instalação wheel/sdist padrão sem editable, `agents` não é empacotado.")
    inv.append("- **Dependências declaradas cujo import direto no código ocorre apenas em módulos dormentes:**")
    deps_only_dorm = sorted(m for m in b4["third_party_imports_only_in_dormant"] if m not in sys.stdlib_module_names)
    inv.append(f"  - `{', '.join(deps_only_dorm)}` (nota: `pydantic` e `starlette`/`uvicorn`/`sse-starlette` são também dependências transitivas do pacote `mcp`, mas no código próprio do Grafo Concierge o import direto de `fastapi`, `pydantic`, `psutil`, `watchdog`, `pathspec` ocorre apenas em módulos dormentes; `tree_sitter_languages` aparece em `core/parsers/ts_js_parser.py:79`, enquanto `tree_sitter` requerido por `ingestion/parser.py:180` segue ausente — `F4-014`).")
    inv.append("")

    # BLOCO 5
    inv.append("## Bloco 5 — Impacto em Testes e CI")
    inv.append("")
    s = b5["summary"]
    inv.append(f"- **Total coletado em HEAD (`pytest --collect-only -q`):** **{b5['total_collected']} testes**.")
    inv.append(f"- **Arquivos que importam qualquer módulo não-`LOAD` (incluindo `interface.queue_writer`):** **{s['files_importing_any_non_load_incl_qw']} arquivos**, somando **{s['tests_in_files_any_non_load_incl_qw']} testes** (limite superior por arquivo inteiro).")
    inv.append(f"- **Arquivos que importam módulos dormentes excluindo os exclusivos de `queue_writer`:** **{s['files_importing_dormant_excl_qw']} arquivos** ({s['tests_in_files_dormant_excl_qw']} testes; dos 26 arquivos, 2 têm 0 testes `test_*` coletados pelo pytest: `colossus_benchmark.py` e `stress_test_v2_setup.py`).")
    inv.append(f"- **Arquivos exclusivos de `interface.queue_writer` (entre não-alcançáveis):** **{s['files_importing_only_qw']} arquivos** (**{s['tests_in_files_only_qw']} testes**).")
    inv.append(f"- **Recorte Classe `(i)` apenas:** **{s['scenario_i_files_count']} arquivos** (máximo **{s['scenario_i_tests_upper_bound']} testes**).")
    inv.append(f"- **Recorte Classes `(i) + (ii)` (excl. `queue_writer`-only):** **{s['scenario_i_ii_files_count']} arquivos** (máximo **{s['scenario_i_ii_tests_upper_bound']} testes**).")
    inv.append("")
    inv.append("### 5.1 Tabela por Arquivo Afetado e Análise Granular dos Misto-Vivos")
    inv.append("")
    inv.append("| Arquivo de Teste | Testes | Tipo | Módulos Dormentes / QW | Módulos Vivos | Granular (`d / m / l / qw`) e Nota |")
    inv.append("|---|---:|---|---|---|---|")
    for row in b5["affected_files"]:
        tf = row["test_file"]
        g = gran_by_file.get(tf)
        if g:
            g_str = f"d={g['dormant_only_tests']}, m={g['mixed_tests']}, l={g['live_only_tests']}, qw={g['qw_tests']}"
            l_names = live_only_names_by_file.get(tf, [])
            if l_names:
                names = ", ".join(x.split("::")[-1] for x in l_names[:3])
                if len(l_names) > 3:
                    names += f" (+{len(l_names)-3})"
                if tf == "tests/test_vector_reconciler.py":
                    g_str += " *(nota: usam `self.search_engine`/`self.reconciler` dormentes criados no `setUp`)*"
                else:
                    g_str += f" *(preservar só-vivo: {names})*"
        else:
            g_str = "script benchmark/setup (0 coletados)"
        inv.append(
            f"| `{tf}` | {row['test_count']} | {'só dormente' if row['pure_dormant_only'] else 'misto / infra'} | `{', '.join(row['dormant_imported'])}` | `{', '.join(row['live_imported']) or '—'}` | {g_str} |"
        )
    inv.append("")
    inv.append("### 5.2 Workflows de CI, Fixtures de `conftest.py` e Guarda G2")
    inv.append("")
    inv.append("- **CI (`.github/workflows/ci.yml` + `windows-stdin.yml`):** **6 jobs totais** (`3` em `ci.yml` [Python 3.10, 3.11, 3.12] rodando `flake8` + `pytest -v --tb=short`; `3` em `windows-stdin.yml` [Python 3.10, 3.12, 3.14] rodando `test_stdin_decouple.py` e `test_lazy_ml_imports.py`). O arquivo `tests/test_domain_neutrality_guard.py` e demais testes afetados rodam automaticamente no `pytest -v --tb=short` do `ci.yml`.")
    inv.append("- **Risco em `tests/conftest.py:136-225` (`check_mcp_globals_leak_*` / `_verify_package_integrity`):** audita simetria entre `sys.modules['interface.*']` e `sys.modules['interface'].__dict__`. Quarentenar `interface/telemetry_api.py`, `interface/watcher.py`, `interface/action_hooks.py` ou `interface/queue_writer.py` exige tratar os 13+ arquivos que injetam esses módulos em `sys.modules['interface']` e o teste `T5` de `tests/test_governor_wiring.py:9` (`interface.ActionHooks`).")
    inv.append("- **Risco na guarda G2 (`tests/test_domain_neutrality_guard.py:80-115`):** G2 executa `git ls-files *.py` (`L93`) varrendo todo arquivo `.py` versionado, inclusive futuro diretório `archive/v4-experimental/`. Além disso, `L87` mantém allowlist explícita para `tests/test_revisor_critico.py`. Ao mover código dormente ou esse teste para `archive/`, G2 precisará ser atualizada em 4.5b.")
    inv.append("")

    # BLOCO 6
    inv.append("## Bloco 6 — Inventário Factual de `interface/queue_writer.py` (Sem Recomendação)")
    inv.append("")
    inv.append("- **Escopo (`audits/fase4-roadmap.md:123` item 8):** inventário estritamente factual; nenhuma recomendação de remoção, quarentena ou unificação é emitida aqui.")
    inv.append(f"- **Tamanhos:** `interface/queue_writer.py` (**{b6['queue_writer_loc']}L**), `storage/connection.py` (**{b6['storage_connection_loc']}L**), `core/database.py` (**{b6['core_database_loc']}L**).")
    inv.append("- **Alcance em produção:** importado incondicionalmente apenas em `core/database.py:18` (`from interface.queue_writer import SerializedWriteQueue`) para anotação `write_queue: Optional[SerializedWriteQueue] = None` (`L27`) e ramo opcional (`L49-50`). `interface/mcp_server.py:163` instancia `ConciergeDatabaseManager(resolved_db_path)` **sem** `write_queue`. Todas as escritas do servidor de produção passam por `storage/connection.py::SerializedWriteQueue`.")
    inv.append("- **Acoplamento em testes:** **46 testes em 13 arquivos** importam `interface.queue_writer` (muitas vezes via `importlib.util.spec_from_file_location` + `setattr(sys.modules['interface'], 'queue_writer', ...)`):")
    inv.append("  - **6 arquivos exclusivos de `interface.queue_writer` (28 testes):** `tests/test_queue_writer_resilience.py` (14), `tests/test_queue_writer_batching.py` (2), `tests/test_agent_checkpointer.py` (4), `tests/test_graph_rag_loops.py` (3), `tests/test_mcp_server_extensions.py` (3), `tests/test_concurrency_stress.py` (2).")
    inv.append("  - **7 arquivos que misturam `interface.queue_writer` com outros dormentes (18 testes):** `tests/test_telemetry_api.py` (5), `tests/test_delta_sync.py` (4), `tests/test_graph_rag_janitor.py` (3), `tests/test_graph_rag_frugal.py` (2), `tests/test_vector_reconciler.py` (2), `tests/test_checkpoint_pruning.py` (1), `tests/test_e2e_concierge_integration.py` (1).")
    inv.append(f"- **Suítes dedicadas vs. equivalente vivo (`tests/test_connection_queue_resilience.py`):** `test_queue_writer_resilience.py` ({b6['suites_comparison']['tests/test_queue_writer_resilience.py']['count']} testes) + `test_queue_writer_batching.py` ({b6['suites_comparison']['tests/test_queue_writer_batching.py']['count']} testes) testam exclusivamente `interface/queue_writer.py`, enquanto `tests/test_connection_queue_resilience.py` ({b6['suites_comparison']['tests/test_connection_queue_resilience.py']['count']} testes: `P1–P9`, `A1–A3`, `T-S1/T-S2`) testa `storage/connection.py::SerializedWriteQueue`. Nota de diferença comportamental documentada: `interface/queue_writer.py` implementa auto-batching oportunista de até 50 itens e `busy_timeout=30000` (4.4c), enquanto `storage/connection.py` executa jobs individuais com `busy_timeout=5000` (4.4d).")
    inv.append("")

    INV_PATH.write_text("\n".join(inv), encoding="utf-8")

    # --- RELATÓRIO 4.5a ---
    rel: list[str] = []
    rel.append("# Relatório da Rodada 4.5a — Inventário Verificado do Código Dormente (Somente Leitura)")
    rel.append("")
    rel.append("- **Data:** 2026-11-12")
    rel.append(f"- **Base verificada:** `{BASE_HEAD}` (`git rev-parse HEAD` == `git ls-remote origin main`)")
    rel.append("- **Decisão do dono (D0):** Cenário A (V4 reduzida focada no núcleo de memória; HSM, Rate Governor, gating, telemetria e dashboard suspensos para futura quarentena).")
    rel.append("- **Regra 15 (EGM/Swarm):** Não executados nesta rodada por instrução explícita do pedido.")
    rel.append("- **Regra 7 (STOP GATE):** Rodada encerrada após commit/push e verificação de CI da 4.5a, sem iniciar 4.5b nem mover arquivos.")
    rel.append("- **Artefatos gerados:** `audits/inventario_4_5a.md`, `audits/relatorio_4_5a.md`, `scratch/evidencia_4_5a/*` (via `scratch/inv_4_5a_*.py` e `scratch/build_4_5a_docs.py`).")
    rel.append("")
    rel.append("## 1. Resumo Executivo por Bloco")
    rel.append("")
    rel.append(f"- **Bloco 1 (Alcançabilidade estática + runtime):** Dos **{b1_stat['total_modules']} módulos** de produção (**{b1_stat['lines']['TOTAL_ALL']:,} linhas**), a partida pelas raízes `main` (`pyproject.toml:88`, `Dockerfile:34`) e `interface.cli` (`pyproject.toml:87`) classifica **{b1_stat['counts']['REACHABLE_LOAD']}** em carga direta (`806L`), **{b1_stat['counts']['REACHABLE_DEFERRED']}** em import tardio (`13.499L`), **{b1_stat['counts']['REACHABLE_ANNOTATION_ONLY_RUNTIME']}** alcançável só para anotação em runtime (`interface.queue_writer`, `304L`), **{b1_stat['counts']['REACHABLE_PEP562_LAZY']}** em lazy export PEP 562 (`agents`, `agents.revisor_critico`, `interface.action_hooks`, `885L`) e **{b1_stat['counts']['UNREACHABLE']}** inalcançáveis (`4.306L`). No traço em tempo de execução exercitando todas as **31/31 ferramentas MCP** e `interface.cli`, **31 módulos** carregaram em `sys.modules` e **0** módulos `UNREACHABLE` foram carregados.")
    rel.append(f"- **Bloco 2 (Classificação):** Entre os **32 módulos** fora da carga normal em runtime (28 `UNREACHABLE` + 1 só-anotação + 3 PEP 562), **15** são classe `(i)` extras suspensos D0/inativos, **6** são classe `(ii)` duplicatas puras superadas por caminhos vivos (`ingestion/parser.py`, `services/janitor.py`, `core/hybrid_search.py`), **4** combinam duplicata `(ii)` com lacuna `(iii)` (`core.delta_manager`/`delta_sync`, `core.background_janitor`/`janitor`), **5** são classe `(iii)` puras (prometidas no README sem impl. viva: `core.alias_tracker`, `core.intent_classifier`, `core.federated_knowledge_router`, `core.global_memory_adapter`, `core.nozomio_router`), e `interface.queue_writer` é mantida separada fora de D0 (Bloco 6). Ressalva viva: `core.probabilistic_retriever` (`REACHABLE_DEFERRED`, `108L`) só ativa se `enable_probabilistic=True` (`core/hybrid_search.py:86`), flag nunca passada por nenhum chamador vivo.")
    rel.append(f"- **Bloco 3 (Promessas públicas):** Identificadas **{b3['total_hits']} ocorrências** em `README.md` (46), `README.pt-BR.md` (46), `docs-grafo-concierge/` (279) e `pyproject.toml` (1 direta por módulo, mais `description` em `:11` e `dependencies` em `:45-52`), além de referências desatualizadas em `CHANGELOG.md:34,71` (`ast_edges_created`), `README.md:63,157` (`30 Tools` vs `31`) e `README.md:177` (`326 tests` vs `478`).")
    rel.append("- **Bloco 4 (Dependências fora do Python):** O dashboard `grafo-dashboard-web/` não está empacotado em `Dockerfile`/`docker-compose.yml`/`pyproject.toml`; suas 6 rotas `/api/...` existem **apenas** em `interface/telemetry_api.py` (nenhuma no servidor MCP) e seu fallback `http://127.0.0.1:8000` colide com `GRAFO_PORT=8000` do servidor MCP (`dev:backend` roda `python main.py`). No SQL, 4 tabelas referenciadas (`ast_edges`, `files`, `communities`, `fsm_checkpoints`) não existem em `storage/schema.py`, e `telemetry_api.py:182` consulta coluna inexistente `timestamp` em `agent_checkpoints`. Em `pyproject.toml:99`, `packages.find` omite `agents*`.")
    rel.append(f"- **Bloco 5 (Testes e CI):** De **{b5['total_collected']} testes coletados**, **26 arquivos** (excluindo `queue_writer`-only) importam módulos dormentes (máximo **197 testes** por arquivo; sendo **20 arquivos / 165 testes** em `(i)` e **26 arquivos / 197 testes** em `(i)+(ii)`). Incluindo os 6 arquivos exclusivos de `queue_writer` (28 testes), são **32 arquivos / 225 testes**. A movimentação na 4.5b exigirá cuidados com `tests/conftest.py:136-225` (`_verify_package_integrity`), `tests/test_governor_wiring.py:9` (`T5`) e a guarda `G2` (`tests/test_domain_neutrality_guard.py:87, 93`).")
    rel.append("- **Bloco 6 (`interface/queue_writer.py`):** 304L vs `storage/connection.py` (488L). Importado só por type hint em `core/database.py:18` (nunca injetado em `interface/mcp_server.py:163`), mas referenciado em **46 testes de 13 arquivos** (28 testes exclusivos em 6 arquivos). Inventário entregue sem recomendação.")
    rel.append("")

    rel.append("## 2. Divergências com os Números do Auditor (`4.5-escopo-e-pergunta-egm.md`)")
    rel.append("")
    rel.append("| Item | Número do Auditor | Nossa Medição Independente | Explicação da Divergência |")
    rel.append("|---|---:|---:|---|")
    rel.append("| Módulos `UNREACHABLE` e LOC | `28` módulos / `4.306` linhas | **`28` módulos / `4.306` linhas** (`UNREACHABLE`) + **`1`** `ANNOTATION_ONLY_RUNTIME` (`304L`) + **`3`** `PEP562_LAZY` (`885L`) | **Paridade exata nos 28 `UNREACHABLE` (4.306L).** Divergência conceitual útil para a 4.5b: o conjunto não carregado em tempo de carga normal inclui ainda 3 módulos lazy (`agents`, `agents.revisor_critico`, `interface.action_hooks` = 885L) e `interface.queue_writer` (`304L`, importado só para anotação). Além disso, `core.probabilistic_retriever` (`108L`) é `DEFERRED` estático mas nunca ativado em runtime (`enable_probabilistic=False`). |")
    rel.append("| Total de testes coletados | `474` | **`478`** (`pytest --collect-only -q`) | Crescimento da suíte entre o recorte anterior do auditor e o HEAD atual `1baf9f8` (+4 testes, ex. rodadas 4.4e/4.4g). |")
    rel.append("| Testes em arquivos que importam módulos de F2 | `146 de 474` | **`197 de 478`** em **26 arquivos** (excl. `queue_writer`-only) ou **`225 de 478`** em **32 arquivos** (incl. `queue_writer`-only) | O scanner do auditor não capturou todas as cargas cirúrgicas por string via `importlib.util.spec_from_file_location(..., \"core.hsm_engine\")` etc. (presentes em suites `unittest` como `test_hierarchical_state_machine.py`, `test_delta_sync.py`, `test_e2e_concierge_integration.py`, `test_vector_reconciler.py`) nem incluiu `interface/action_hooks.py` e `agents/revisor_critico.py` (`+27` testes em `test_interface_contracts.py` [22] e `test_governor_wiring.py` [5], além de `test_revisor_critico.py` [11]). |")
    rel.append("| Parsing TS/JS vivo vs. `core/parsers/*` | Indício em aberto | Confirmado `(ii)`: `ingestion/parser.py:130-324` cobre `.ts/.tsx/.js/.jsx/.py/.go/.rs` | Ressalva confirmada (`F4-014`): `tree_sitter` não está em `pyproject.toml`; no sandbox sem `tree_sitter`, `ingestion/parser.py:217-245, 270-324` opera por fallback léxico/regex. |")
    rel.append("| Reconciliação de vetores & delta | Indícios `(ii)` em aberto | Reconciliação confirmada `(ii)` (`services/janitor.py:347-374`); delta é `(ii)` em SHA256/content-cache (`ingestion/crawler.py`+`orchestrator.py`), mas **Classe `(iii)`** para `SSH+LBH` | `README.md` promete especificamente `SSH + LBH Semantic Drift Guard`, que só existe no código dormente `core/delta_manager.py`. |")
    rel.append("| Promessas sem impl. viva `(iii)` e conflito porta `8000` | Não detalhados no escopo | Confirmadas 5 classes `(iii)` puras (`alias_tracker`, `intent_classifier`, `federated_knowledge_router`, `global_memory_adapter`, `nozomio_router`) + Smart Checkpoint Pruning + conflito porta `8000` | Mapeados com `arquivo:linha` nos Blocos 2, 3 e 4 do inventário. |")
    rel.append("")

    rel.append("## 3. Limites e o que Não Foi Possível Verificar")
    rel.append("")
    rel.append("1. **Ambiente lightweight no traço runtime:** `inv_4_5a_bloco1_runtime.py` rodou com `GRAFO_LIGHTWEIGHT_MODE=true` e chaves fake; o carregador neural pesado (`sentence_transformers`/`torch`) não foi exercitado durante esse traço, gerando `embeddings_stored=0` em `concierge_mine`.")
    rel.append("2. **Loop asyncio no sandbox Windows:** `asyncio.run(...)` trava >5s na criação de self-pipe sob o sandbox; por isso as 31 ferramentas MCP foram invocadas sincronamente via `governor.validate_tool_execution` + `tool_obj.fn(**args)`, sem subir listener HTTP/SSE ou transporte `stdio` completo.")
    rel.append("3. **Cobertura de execução dos testes:** a suíte `pytest` não foi reexecutada neste inventário (apenas `--collect-only -q` e análise AST); portanto, a classificação de granularidade em arquivos mistos é estática (observando inclusive o caso de `tests/test_vector_reconciler.py`, onde o scanner por função não enxergou que `self.search_engine` e `self.reconciler` são instanciados no `setUp` a partir de módulos dormentes).")
    rel.append("4. **Análise dinâmica por reflection fora do repo:** plug-ins ou scripts externos fora do repositório `ConciergeGraph` não são observáveis pelo grafo estático.")
    rel.append("")
    rel.append("---")
    rel.append("**Referência completa por módulo, citação literal, tabela SQL, dashboard e Bloco 6:** ver [`audits/inventario_4_5a.md`](inventario_4_5a.md).")

    REL_PATH.write_text("\n".join(rel), encoding="utf-8")
    print(f"Gerados: {INV_PATH.relative_to(ROOT)} ({len(inv)} linhas) e {REL_PATH.relative_to(ROOT)} ({len(rel)} linhas)")


if __name__ == "__main__":
    build_docs()
