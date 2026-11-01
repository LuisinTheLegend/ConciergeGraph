"""E2E MCP Proof for Bloco 1 (F4-018 & F4-024).
Tests real MCP server bootstrap, mining of files with sentinel words and diacritics/identifiers only in the body,
and searches via concierge_search and fts_search.
"""
import os
import pathlib
import sys
import tempfile

# Force test configuration
tmp_base = tempfile.mkdtemp(prefix="grafo_e2e_mcp_")
db_file = os.path.join(tmp_base, "concierge_e2e.db")
chroma_dir = os.path.join(tmp_base, "chroma_e2e")
repo_dir = os.path.join(tmp_base, "sample_repo")
os.makedirs(repo_dir, exist_ok=True)

# Create test files with terms ONLY in body (generic filenames and labels)
(pathlib.Path(repo_dir) / "fiscal_core.py").write_text(
    "# Core fiscal calculation routines\n"
    "def process_taxes(amount):\n"
    "    aliquota = 0.15  # aplicação de alíquota diferenciada\n"
    "    resultado = calcular_imposto_renda(amount, aliquota)\n"
    "    return resultado\n",
    encoding="utf-8",
)

(pathlib.Path(repo_dir) / "musica_acustica.py").write_text(
    "# Audio acoustic module\n"
    "def play_symphony():\n"
    "    instrument = 'violoncelo-ômega'\n"
    "    marker = 'ZEBRA-42'\n"
    "    return f'{instrument}:{marker}'\n",
    encoding="utf-8",
)

(pathlib.Path(repo_dir) / "transacao_bancaria.py").write_text(
    "# Banking transaction reconciliation\n"
    "def reconcile():\n"
    "    sentinela_1 = 'abacaxi-zeta'\n"
    "    sentinela_2 = 'farol-sigma'\n"
    "    status_a = 'reembolso'\n"
    "    # linha intermediaria de log de auditoria\n"
    "    status_b = 'estorno'\n"
    "    return (sentinela_1, sentinela_2, status_a, status_b)\n",
    encoding="utf-8",
)

os.environ["GRAFO_DB_PATH"] = db_file
os.environ["GRAFO_CHROMA_PATH"] = chroma_dir
os.environ["GRAFO_LLM_MODEL"] = "none"
os.environ["GRAFO_LLM_PROVIDER"] = "none"
os.environ["GRAFO_LLM_API_KEY"] = "AQ.FAKEFAKEFAKE0001"
os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "true"
os.environ["PYTHONIOENCODING"] = "utf-8"

print(f"Starting E2E MCP with db={db_file}, chroma={chroma_dir}")
import main as main_mod

server, janitor, store = main_mod.bootstrap()

proj_uuid = "proj-e2e-mcp-01"
# 1. Register project
reg_res = server._handle_register(project_path=repo_dir, wing="geral", privacy_level="PUBLIC", summary="Projeto E2E")
proj_uuid = reg_res.get("project_uuid", proj_uuid)
print(f"Register project result: success={reg_res.get('success', False)}, uuid={proj_uuid}")

# 2. Mine repository with LLM disabled (summaries will be NULL)
mine_res = server._handle_mine(path=repo_dir, project_identifier=proj_uuid, auto_tag=False)
print(f"Mine result: success={mine_res.get('success')}, files_processed={mine_res.get('files_processed')}")

# 3. Test queries
queries = [
    "abacaxi-zeta",
    "violoncelo-omega",
    "farol-sigma",
    "aliquota",
    "calcular_imposto_renda",
    "ZEBRA-42",
    "reembolso estorno",
]

failures = []
for q in queries:
    fts_res = store.fts_search(query=q, project_uuid=proj_uuid)
    mcp_res = server._handle_search(
        query=q,
        project_identifier=proj_uuid,
        top_k=10,
        node_type=None,
        include_references=False,
        all_wings=False,
    )
    mcp_results = mcp_res.get("results", []) if isinstance(mcp_res, dict) else []

    fts_found = len(fts_res) > 0
    mcp_found = len(mcp_results) > 0
    print(f"Query: {q!r:28s} -> FTS={len(fts_res)} nodes, MCP={len(mcp_results)} nodes")
    if not fts_found or not mcp_found:
        failures.append(f"Query {q!r} FAILED: FTS found {len(fts_res)}, MCP found {len(mcp_results)}")

store.close()

if failures:
    print(f"\n[E2E RED] {len(failures)}/{len(queries)} queries failed:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
else:
    print(f"\n[E2E GREEN] All {len(queries)} queries passed via real MCP server and FTS!")
    sys.exit(0)
