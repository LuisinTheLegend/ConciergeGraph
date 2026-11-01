"""scratch/evidencia_4_2h2/run_item1e_mcp_filenames.py

Prova funcional real do Item 1e (F4-022):
- Projeto temporario (nunca data/) com 3 arquivos .md cujos nomes contem 'sk-' interno:
    1) risk-assessment-notes.md
    2) disk-cache-manifest.md
    3) task-scheduler-config.md
- Servidor MCP real em transporte stdio (main.py), GRAFO_LLM_MODEL=none,
  GRAFO_LLM_API_KEY falsa explicita, GRAFO_LOG_LEVEL=DEBUG (para que os nomes dos
  arquivos processados aparecam no stderr via logger.debug("Cleanup post-ingestion: obsolete nodes of %s removed.")).
- Fluxo por repeticao (n=3 sequenciais):
    initialize -> list_tools -> concierge_register -> concierge_mine
- Compara:
    (A) Commit c5e1c2c (antes do fix de F4-022, via git worktree): mostra que os nomes
        apareciam corrompidos no stderr ('ri[REDACTED].md', 'di[REDACTED].md', 'ta[REDACTED].md')
        e '[REDACTED]' > 0.
    (B) Codigo corrigido atual (HEAD + fix Item 1): mostra que os 3 nomes aparecem
        INTACTOS no stderr em todas as 3 repeticoes e que a contagem de '[REDACTED]'
        no stderr e 0.
"""

from __future__ import annotations

import asyncio
import json
import os
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
WT_C5E1C2C = Path(r"C:\Nexus-Memory\_wt_4_2e\c5e1c2c")

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scratch" / "evidencia_4_2e"))

import mcp_e2e_v2 as v2  # noqa: E402

try:
    import psutil
except ImportError:
    psutil = None

TARGET_FILENAMES = [
    "risk-assessment-notes.md",
    "disk-cache-manifest.md",
    "task-scheduler-config.md",
]


def create_project_files(proj_dir: Path) -> None:
    proj_dir.mkdir(parents=True, exist_ok=True)
    contents = {
        "risk-assessment-notes.md": (
            "# Risk Assessment Notes\n\n"
            "Documento de avaliacao de riscos operacionais e controles preventivos para "
            "servicos de indexacao local sem dependencia de chamadas externas.\n"
        ),
        "disk-cache-manifest.md": (
            "# Disk Cache Manifest\n\n"
            "Especificacao de manifesto de cache em disco para verificacao incremental "
            "de hashes SHA-256 durante a etapa de varredura de arquivos.\n"
        ),
        "task-scheduler-config.md": (
            "# Task Scheduler Configuration\n\n"
            "Parametros de agendamento de manutencao em segundo plano e reconciliacao "
            "periodica entre armazenamento relacional SQLite e indices vetoriais.\n"
        ),
    }
    for fname, text in contents.items():
        (proj_dir / fname).write_text(text, encoding="utf-8")


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


def ensure_worktree_c5e1c2c() -> Path:
    WT_C5E1C2C.parent.mkdir(parents=True, exist_ok=True)
    if WT_C5E1C2C.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(WT_C5E1C2C)],
            cwd=str(REPO_ROOT),
            capture_output=True,
        )
        if WT_C5E1C2C.exists():
            shutil.rmtree(WT_C5E1C2C, ignore_errors=True)
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(WT_C5E1C2C), "c5e1c2c"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
    )
    return WT_C5E1C2C


def remove_worktree_c5e1c2c() -> None:
    if WT_C5E1C2C.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(WT_C5E1C2C)],
            cwd=str(REPO_ROOT),
            capture_output=True,
        )
        if WT_C5E1C2C.exists():
            shutil.rmtree(WT_C5E1C2C, ignore_errors=True)


async def run_single_rep(target_repo: Path, label: str, rep: int) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tmp = Path(tempfile.mkdtemp(prefix=f"item1e_{label}_r{rep}_"))
    db_path = tmp / "test.db"
    chroma_path = tmp / "chroma"
    proj_path = tmp / "proj_filenames"
    errlog_path = tmp / "stderr.log"

    create_project_files(proj_path)

    env = os.environ.copy()
    for k in ["GRAFO_LLM_PROVIDER", "GRAFO_LLM_BASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        env.pop(k, None)

    env.update({
        "GRAFO_DB_PATH": str(db_path),
        "GRAFO_CHROMA_PATH": str(chroma_path),
        "GRAFO_CHROMA_COLLECTION": f"col_1e_{label}_{rep}",
        "GRAFO_TRANSPORT": "stdio",
        "GRAFO_LOG_LEVEL": "DEBUG",
        "GRAFO_LLM_MODEL": "none",
        "GRAFO_LLM_API_KEY": "AQ." + "FAKEFAKEFAKE0001",
        "GRAFO_EMBED_WARMUP": "false",
        "HF_HUB_OFFLINE": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TQDM_DISABLE": "1",
        "PYTHONPATH": str(target_repo),
    })

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "main.py"],
        env=env,
        cwd=str(target_repo),
    )

    t0 = time.perf_counter()
    status = "ERRO"
    files_processed = 0
    nodes_created = 0
    server_proc = None

    try:
        with open(errlog_path, "w", encoding="utf-8") as errlog:
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
                            "summary": f"Item 1e {label} rep {rep}",
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
                    nodes_created = int(mine_data.get("nodes_created", 0))
                    status = "OK"
            finally:
                kill_tree(server_proc)

        await asyncio.sleep(0.3)
        stderr_text = errlog_path.read_text(encoding="utf-8", errors="replace") if errlog_path.exists() else ""

        intact_counts = {fn: stderr_text.count(fn) for fn in TARGET_FILENAMES}
        corrupted_counts = {
            "ri[REDACTED].md": stderr_text.count("ri[REDACTED].md"),
            "di[REDACTED].md": stderr_text.count("di[REDACTED].md"),
            "ta[REDACTED].md": stderr_text.count("ta[REDACTED].md"),
        }
        redacted_total = stderr_text.count("[REDACTED]")

        matching_lines = [
            ln.strip()
            for ln in stderr_text.splitlines()
            if any(fn in ln for fn in TARGET_FILENAMES)
            or any(cf in ln for cf in corrupted_counts)
            or "[REDACTED]" in ln
        ]

        # Confere labels no SQLite
        db_labels: list[str] = []
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            try:
                rows = conn.execute("SELECT label FROM nodes ORDER BY id").fetchall()
                db_labels = [r[0] for r in rows]
            finally:
                conn.close()

        return {
            "label": label,
            "rep": rep,
            "status": status,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "files_processed": files_processed,
            "nodes_created": nodes_created,
            "intact_counts_in_stderr": intact_counts,
            "corrupted_counts_in_stderr": corrupted_counts,
            "redacted_total_in_stderr": redacted_total,
            "matching_stderr_lines": matching_lines,
            "db_labels": db_labels,
        }
    finally:
        kill_tree(server_proc)
        shutil.rmtree(tmp, ignore_errors=True)


async def main_async() -> int:
    wt = ensure_worktree_c5e1c2c()
    all_results: list[dict[str, Any]] = []
    try:
        for label, repo_dir in [("before_c5e1c2c", wt), ("after_fix", REPO_ROOT)]:
            for rep in range(1, 4):
                res = await run_single_rep(repo_dir, label, rep)
                all_results.append(res)
    finally:
        remove_worktree_c5e1c2c()

    out_json = HERE / "item1_e_mcp_filenames.json"
    out_txt = HERE / "item1_e_mcp_filenames.txt"
    out_json.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines: list[str] = []
    lines.append("=== ITEM 1e: PROVA FUNCIONAL MCP STDIO (NOMES DE ARQUIVO COM 'sk-' INTERNO, n=3 SEQUENCIAIS) ===")
    lines.append("Arquivos no projeto de teste: risk-assessment-notes.md, disk-cache-manifest.md, task-scheduler-config.md")
    lines.append("Configuracao: GRAFO_LLM_MODEL=none, GRAFO_LLM_API_KEY=<falsa explicita>, GRAFO_LOG_LEVEL=DEBUG")
    lines.append("")
    header = (
        f"{'Alvo':<15} | {'Rep':<3} | {'St':<4} | {'t(s)':<6} | {'Files':<5} | {'Nodes':<5} | "
        f"{'risk-..':<7} | {'disk-..':<7} | {'task-..':<7} | {'[REDACTED]':<10}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in all_results:
        ic = r["intact_counts_in_stderr"]
        lines.append(
            f"{r['label']:<15} | {r['rep']:<3} | {r['status']:<4} | {r['elapsed_s']:<6.2f} | "
            f"{r['files_processed']:<5} | {r['nodes_created']:<5} | "
            f"{ic['risk-assessment-notes.md']:<7} | {ic['disk-cache-manifest.md']:<7} | "
            f"{ic['task-scheduler-config.md']:<7} | {r['redacted_total_in_stderr']:<10}"
        )
    lines.append("-" * len(header))
    lines.append("")
    lines.append("=== LINHAS LITERAIS DO STDERR CONTENDO OS NOMES DOS ARQUIVOS OU '[REDACTED]' ===")
    for r in all_results:
        lines.append(f"\n[{r['label']} | rep={r['rep']}] redacted_total={r['redacted_total_in_stderr']} db_labels={r['db_labels']}")
        for ln in r["matching_stderr_lines"]:
            lines.append(f"  {ln}")

    summary_text = "\n".join(lines) + "\n"
    out_txt.write_text(summary_text, encoding="utf-8")
    sys.stdout.buffer.write(summary_text.encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))

