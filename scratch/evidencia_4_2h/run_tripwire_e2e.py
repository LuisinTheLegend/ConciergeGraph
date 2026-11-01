"""scratch/evidencia_4_2h/run_tripwire_e2e.py

Executa a prova de rede E2E com Tripwire Proxy (Passo 6 da Rodada 4.2h):
- Cenários (n=3 cada, sequenciais):
  * E1: GRAFO_LLM_MODEL=none, chave falsa explicita, sem provedor explicito
  * E2: GRAFO_LLM_MODEL=gpt-4o-mini, chave falsa explicita, sem provedor explicito
  * E3: GRAFO_LLM_MODEL=gpt-4o-mini, chave falsa explicita, GRAFO_LLM_PROVIDER=openai
- Alvos:
  * Commit antigo: 96ba4d0 (em worktree C:\\Nexus-Memory\\_wt_4_2e\\96ba4d0)
  * Commit novo: HEAD atual (em C:\\Nexus-Memory\\GrafoConcierge)
- Registra para cada execucao:
  * requisicoes/CONNECT capturadas pelo Tripwire Proxy (hosts, metodo, horario)
  * nos criados no SQLite temporario, vetores no Chroma temporario, contagem de summary NULL vs NOT NULL
  * contagem de linhas "Event loop is closed" e "Task exception was never retrieved" no stderr
  * contagem detalhada de linhas ERROR e WARNING por tipo/categoria no stderr
"""

from __future__ import annotations

import asyncio
import collections
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
WT_96BA4D0 = Path(r"C:\Nexus-Memory\_wt_4_2e\96ba4d0")

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2e"))

import main as current_main  # noqa: E402
import mcp_e2e_v2 as v2  # noqa: E402
from tripwire_proxy import TripwireProxyServer  # noqa: E402

try:
    import psutil
except ImportError:
    psutil = None


def create_three_file_project(proj_dir: Path) -> None:
    """Cria 3 arquivos .md (>50 tokens estimados cada = 3 chunks regulares) em diretorio temporario."""
    proj_dir.mkdir(parents=True, exist_ok=True)
    docs = {
        "arquitetura_rede.md": (
            "# Arquitetura de Rede e Roteamento\n\n"
            "Este documento descreve a topologia de sub-redes, balanceadores de carga e "
            "políticas de firewall para isolamento de serviços internos de armazenamento "
            "relacional e vetorial em ambientes corporativos distribuídos de alta disponibilidade.\n"
        ),
        "politica_seguranca.md": (
            "# Política de Segurança de Credenciais\n\n"
            "Toda chave de provedor externo deve ser validada explicitamente antes de qualquer "
            "conexão de saída. Provedores desativados nunca devem instanciar clientes HTTP nem "
            "disparar resolução de nomes ou handshakes TLS para serviços de terceiros.\n"
        ),
        "pipeline_ingestao.md": (
            "# Pipeline de Ingestão e Indexação\n\n"
            "O processo de mineração percorre os arquivos do projeto, extrai fragmentos "
            "estruturados, armazena os metadados no banco relacional SQLite e calcula os "
            "vetores densos localmente para consulta semântica híbrida.\n"
        ),
    }
    for name, content in docs.items():
        (proj_dir / name).write_text(content, encoding="utf-8")


def kill_tree(proc: Any) -> None:
    if proc is None:
        return
    try:
        for ch in proc.children(recursive=True):
            try:
                ch.kill()
            except Exception:
                pass
        proc.kill()
    except Exception:
        pass


def normalize_log_category(line: str, level: str) -> str:
    """Agrupa linhas de ERROR/WARNING por tipo de mensagem sem expor segredos ou IDs variáveis."""
    safe_line = current_main.redact_log_secrets(line.strip())
    # Remove prefixo de timestamp e nivel
    idx = safe_line.find(level)
    body = safe_line[idx + len(level) :].strip(" :-|") if idx >= 0 else safe_line
    # Normaliza enderecos de memoria e portas efemeras
    body = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", body)
    body = re.sub(r"127\.0\.0\.1:\d+", "127.0.0.1:PORT", body)
    if len(body) > 140:
        body = body[:140] + "..."
    return body


def analyze_stderr(stderr_text: str) -> dict[str, Any]:
    safe_text = current_main.redact_log_secrets(stderr_text)
    lines = safe_text.splitlines()
    event_loop_closed = sum(1 for ln in lines if "Event loop is closed" in ln)
    task_exc_never_retrieved = sum(1 for ln in lines if "Task exception was never retrieved" in ln)

    error_counts: collections.Counter[str] = collections.Counter()
    warning_counts: collections.Counter[str] = collections.Counter()

    for ln in lines:
        # Detecta linhas de log padrao ou do Rich/logging
        if re.search(r"\bERROR\b", ln):
            cat = normalize_log_category(ln, "ERROR")
            error_counts[cat] += 1
        elif re.search(r"\bWARNING\b", ln):
            cat = normalize_log_category(ln, "WARNING")
            warning_counts[cat] += 1

    return {
        "event_loop_closed_count": event_loop_closed,
        "task_exception_never_retrieved_count": task_exc_never_retrieved,
        "error_total_lines": sum(error_counts.values()),
        "warning_total_lines": sum(warning_counts.values()),
        "error_by_type": dict(error_counts),
        "warning_by_type": dict(warning_counts),
    }


async def run_one_case(
    target_repo: Path,
    commit_label: str,
    scenario: str,
    rep: int,
) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tmp = Path(tempfile.mkdtemp(prefix=f"tw42h_{commit_label}_{scenario}_{rep}_"))
    db_path = tmp / "test.db"
    chroma_path = tmp / "chroma"
    proj_path = tmp / "sample_proj"
    errlog_tmp = tmp / "server_stderr.log"

    create_three_file_project(proj_path)

    fake_aq = "AQ." + "FAKEFAKEFAKE0001"
    fake_sk = "sk-" + "FAKEFAKEFAKE0001"

    with TripwireProxyServer() as proxy:
        env = os.environ.copy()
        # Remove eventuais variaveis de LLM pre-existentes
        for k in ["GRAFO_LLM_PROVIDER", "GRAFO_LLM_BASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            env.pop(k, None)

        env.update({
            "GRAFO_DB_PATH": str(db_path),
            "GRAFO_CHROMA_PATH": str(chroma_path),
            "GRAFO_CHROMA_COLLECTION": f"col_{commit_label}_{scenario}_{rep}",
            "GRAFO_TRANSPORT": "stdio",
            "GRAFO_LOG_LEVEL": "INFO",
            "GRAFO_EMBED_WARMUP": "false",
            "HTTPS_PROXY": proxy.proxy_url,
            "HTTP_PROXY": proxy.proxy_url,
            "ALL_PROXY": proxy.proxy_url,
            "https_proxy": proxy.proxy_url,
            "http_proxy": proxy.proxy_url,
            "all_proxy": proxy.proxy_url,
            "NO_PROXY": "",
            "no_proxy": "",
            "HF_HUB_OFFLINE": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "TQDM_DISABLE": "1",
            "PYTHONPATH": str(target_repo),
        })

        if scenario == "E1":
            env["GRAFO_LLM_MODEL"] = "none"
            env["GRAFO_LLM_API_KEY"] = fake_aq
            env["GRAFO_LLM_PROVIDER"] = ""
        elif scenario == "E2":
            env["GRAFO_LLM_MODEL"] = "gpt-4o-mini"
            env["GRAFO_LLM_API_KEY"] = fake_sk
            env["GRAFO_LLM_PROVIDER"] = ""
        elif scenario == "E3":
            env["GRAFO_LLM_MODEL"] = "gpt-4o-mini"
            env["GRAFO_LLM_API_KEY"] = fake_sk
            env["GRAFO_LLM_PROVIDER"] = "openai"
        else:
            raise ValueError(f"Cenario desconhecido: {scenario}")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-u", "main.py"],
            env=env,
            cwd=str(target_repo),
        )

        t0 = time.perf_counter()
        status = "ERRO"
        files_processed = 0
        vectors_stored = 0
        error_detail = ""
        server_proc = None

        try:
            with open(errlog_tmp, "w", encoding="utf-8") as errlog:
                try:
                    async with stdio_client(server_params, errlog=errlog) as (read_stream, write_stream), \
                               ClientSession(read_stream, write_stream) as session:
                        if psutil is not None:
                            curr_p = psutil.Process()
                            children = [c for c in curr_p.children(recursive=True) if "python" in c.name().lower()]
                            if children:
                                server_proc = children[-1]

                        await asyncio.wait_for(session.initialize(), timeout=30.0)
                        await asyncio.wait_for(session.list_tools(), timeout=15.0)

                        reg_res = await asyncio.wait_for(
                            session.call_tool("concierge_register", arguments={
                                "project_path": str(proj_path),
                                "wing": "geral",
                                "privacy_level": "PUBLIC",
                                "summary": f"Tripwire 4.2h {commit_label} {scenario} rep {rep}",
                            }),
                            timeout=30.0,
                        )
                        reg_data = v2.parse_mcp_result(reg_res, "concierge_register")
                        proj_uuid = reg_data["project_uuid"]

                        mine_res = await asyncio.wait_for(
                            session.call_tool("concierge_mine", arguments={
                                "path": str(proj_path),
                                "project_identifier": proj_uuid,
                                "auto_tag": True,
                            }),
                            timeout=120.0,
                        )
                        mine_data = v2.parse_mcp_result(mine_res, "concierge_mine")
                        files_processed = int(mine_data.get("files_processed", 0))

                        cnt_res = await asyncio.wait_for(
                            session.call_tool("count_embeddings", arguments={
                                "project_identifier": proj_uuid,
                            }),
                            timeout=30.0,
                        )
                        cnt_data = v2.parse_mcp_result(cnt_res, "count_embeddings")
                        vectors_stored = int(cnt_data.get("count", 0))
                        status = "OK"
                except BaseException as exc:
                    kill_tree(server_proc)
                    if status != "OK":
                        status = "ERRO"
                        error_detail = current_main.redact_log_secrets(f"{type(exc).__name__}: {exc}")
        finally:
            kill_tree(server_proc)

        elapsed = round(time.perf_counter() - t0, 2)
        await asyncio.sleep(0.3)
        proxy_events = proxy.snapshot_events()

    # Inspeciona banco SQLite temporario (somente leitura)
    nodes_total = 0
    nodes_summary_null = 0
    nodes_summary_not_null = 0
    if db_path.exists():
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            cur = conn.cursor()
            nodes_total = int(cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
            nodes_summary_null = int(
                cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NULL OR TRIM(summary) = ''").fetchone()[0]
            )
            nodes_summary_not_null = int(
                cur.execute("SELECT COUNT(*) FROM nodes WHERE summary IS NOT NULL AND TRIM(summary) != ''").fetchone()[0]
            )
        finally:
            conn.close()

    stderr_raw = errlog_tmp.read_text(encoding="utf-8", errors="replace") if errlog_tmp.exists() else ""
    stderr_stats = analyze_stderr(stderr_raw)

    shutil.rmtree(tmp, ignore_errors=True)

    openai_connects = sum(1 for e in proxy_events if "openai.com" in e["target"].lower())
    google_connects = sum(1 for e in proxy_events if "googleapis.com" in e["target"].lower())
    unique_targets = sorted({f"{e['method']} {e['target']}" for e in proxy_events})

    return {
        "commit": commit_label,
        "scenario": scenario,
        "rep": rep,
        "status": status,
        "elapsed_s": elapsed,
        "files_processed": files_processed,
        "nodes_total": nodes_total,
        "vectors_stored": vectors_stored,
        "nodes_summary_null": nodes_summary_null,
        "nodes_summary_not_null": nodes_summary_not_null,
        "proxy_total_requests": len(proxy_events),
        "proxy_openai_requests": openai_connects,
        "proxy_google_requests": google_connects,
        "proxy_unique_targets": unique_targets,
        "proxy_events": proxy_events,
        "stderr_stats": stderr_stats,
        "error_detail": error_detail,
    }


def format_report_text(all_results: list[dict[str, Any]], old_sha: str, new_sha: str) -> str:
    lines: list[str] = []
    lines.append("=== PASSO 6A: PROVA DE REDE COM TRIPWIRE PROXY (E2E MCP STDIO) ===")
    lines.append(f"Commit antigo (worktree): {old_sha}")
    lines.append(f"Commit novo (HEAD):       {new_sha}")
    lines.append("")
    header = (
        f"{'Commit':<9} | {'Cen':<3} | {'Rep':<3} | {'St':<4} | {'t(s)':<6} | "
        f"{'Nodes':<5} | {'Vecs':<4} | {'SumNULL':<7} | {'Sum!=NULL':<9} | "
        f"{'PrxTot':<6} | {'OpenAI':<6} | {'Google':<6} | {'LoopCl':<6} | {'TaskEx':<6} | "
        f"{'ERR':<4} | {'WARN':<4}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in all_results:
        st_err = r["stderr_stats"]
        lines.append(
            f"{r['commit']:<9} | {r['scenario']:<3} | {r['rep']:<3} | {r['status']:<4} | "
            f"{r['elapsed_s']:<6.2f} | {r['nodes_total']:<5} | {r['vectors_stored']:<4} | "
            f"{r['nodes_summary_null']:<7} | {r['nodes_summary_not_null']:<9} | "
            f"{r['proxy_total_requests']:<6} | {r['proxy_openai_requests']:<6} | "
            f"{r['proxy_google_requests']:<6} | {st_err['event_loop_closed_count']:<6} | "
            f"{st_err['task_exception_never_retrieved_count']:<6} | "
            f"{st_err['error_total_lines']:<4} | {st_err['warning_total_lines']:<4}"
        )
    lines.append("-" * len(header))
    lines.append("")
    lines.append("=== DETALHAMENTO DE EVENTOS DO PROXY E CONTAGEM DE ERROR / WARNING POR EXECUÇÃO ===")
    for r in all_results:
        st_err = r["stderr_stats"]
        lines.append(
            f"\n[{r['commit']} | {r['scenario']} | rep={r['rep']}] "
            f"proxy_total={r['proxy_total_requests']} targets={r['proxy_unique_targets']}"
        )
        if r["proxy_events"]:
            lines.append(f"  Amostra eventos proxy (ate 5): {json.dumps(r['proxy_events'][:5], ensure_ascii=False)}")
        lines.append(
            f"  stderr: Event loop is closed={st_err['event_loop_closed_count']}, "
            f"Task exception was never retrieved={st_err['task_exception_never_retrieved_count']}"
        )
        lines.append(f"  ERROR lines ({st_err['error_total_lines']} total): {json.dumps(st_err['error_by_type'], ensure_ascii=False)}")
        lines.append(f"  WARNING lines ({st_err['warning_total_lines']} total): {json.dumps(st_err['warning_by_type'], ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


async def main_async() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old_sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=str(WT_96BA4D0), text=True
    ).strip()
    new_sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO_ROOT), text=True
    ).strip()

    all_results: list[dict[str, Any]] = []
    targets = [
        (WT_96BA4D0, f"old_{old_sha}"),
        (REPO_ROOT, f"new_{new_sha}"),
    ]

    for repo_path, commit_label in targets:
        for scenario in ["E1", "E2", "E3"]:
            for rep in range(1, 4):
                msg_start = f"[Tripwire E2E] Rodando {commit_label} | {scenario} | rep {rep}/3 ..."
                print(msg_start, flush=True)
                with (HERE / "p6_tripwire_progress.log").open("a", encoding="utf-8") as pf:
                    pf.write(msg_start + "\n")
                res = await run_one_case(repo_path, commit_label, scenario, rep)
                all_results.append(res)
                msg_end = (
                    f"  -> status={res['status']} elapsed={res['elapsed_s']}s "
                    f"nodes={res['nodes_total']} vecs={res['vectors_stored']} "
                    f"openai_req={res['proxy_openai_requests']} "
                    f"loop_closed={res['stderr_stats']['event_loop_closed_count']}"
                )
                print(msg_end, flush=True)
                with (HERE / "p6_tripwire_progress.log").open("a", encoding="utf-8") as pf:
                    pf.write(msg_end + "\n")

    (HERE / "p6_tripwire_results.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    txt = format_report_text(all_results, old_sha, new_sha)
    (HERE / "p6_tripwire_summary.txt").write_text(txt, encoding="utf-8")
    print("\n" + txt, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))

