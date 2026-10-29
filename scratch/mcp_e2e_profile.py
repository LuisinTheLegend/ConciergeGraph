"""
scratch/mcp_e2e_profile.py — [DEPRECADO / INVÁLIDO — Ver F4-016 e scratch/evidencia_4_2e/mcp_e2e_v2.py]

AVISO DA RODADA 4.2e:
Este script chamava concierge_mine com 'project_name' (parâmetro inexistente) e concierge_search
sem project_identifier nem all_wings=True, além de não verificar isError.
Os tempos de ~0,0018s medidos nas rodadas 4.2c e 4.2d refletiam erro imediato de validação,
não mineração nem carga real de embedding.
Utilize exclusivamente scratch/evidencia_4_2e/mcp_e2e_v2.py.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


async def run_e2e_profile(target_python: str, timeout: float = 180.0) -> dict[str, float]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    results: dict[str, float] = {}

    # Criar pasta temporaria de banco e projeto
    tmp_dir = tempfile.mkdtemp(prefix="grafo_e2e_profile_")
    db_path = os.path.join(tmp_dir, "e2e_concierge.db")
    chroma_path = os.path.join(tmp_dir, "e2e_chroma")
    project_dir = os.path.join(tmp_dir, "min_project")
    os.makedirs(project_dir, exist_ok=True)

    # Cria 1 arquivo pequeno de codigo Python
    sample_file = os.path.join(project_dir, "math_utils.py")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("def calculate_area(width: float, height: float) -> float:\n    \"\"\"Calculates rectangle area.\"\"\"\n    return width * height\n")

    print("=" * 75)
    print("GRAFO CONCIERGE — MCP E2E PROFILE (CLIENTE STDIO REAL)")
    print("=" * 75)
    print(f"Target Python:      {target_python}")
    print(f"Temp DB:            {db_path}")
    print(f"Temp Chroma:        {chroma_path}")
    print(f"Sample Project Dir: {project_dir}")
    print("=" * 75)

    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = db_path
    env["GRAFO_CHROMA_PATH"] = chroma_path
    env["GRAFO_CHROMA_COLLECTION"] = "e2e_profile_collection"
    env["GRAFO_TRANSPORT"] = "stdio"
    env["GRAFO_LOG_LEVEL"] = "INFO"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)

    server_params = StdioServerParameters(
        command=target_python,
        args=["main.py"],
        env=env,
        cwd=REPO_ROOT,
    )

    t_spawn = time.perf_counter()

    async def _logic():
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # (a) Initialize
                print("[1/5] Enviando initialize...")
                init_res = await session.initialize()
                t_init = time.perf_counter()
                elapsed_init = t_init - t_spawn
                results["(a) Tempo ate resposta initialize"] = elapsed_init
                print(f"      -> Concluido em {elapsed_init:.4f}s apos o spawn")

                # (b) List Tools
                print("[2/5] Solicitando list_tools...")
                t_before_list = time.perf_counter()
                tools_res = await session.list_tools()
                t_list = time.perf_counter()
                elapsed_list_from_spawn = t_list - t_spawn
                elapsed_list_op = t_list - t_before_list
                results["(b) Tempo ate list_tools (desde spawn)"] = elapsed_list_from_spawn
                results["(b.1) Tempo da operacao list_tools"] = elapsed_list_op
                print(f"      -> {len(tools_res.tools)} ferramentas listadas em {elapsed_list_from_spawn:.4f}s desde spawn ({elapsed_list_op:.4f}s roundtrip)")

                # (c) Registrar projeto
                print("[3/5] Registrando projeto temporario (concierge_register)...")
                t0_reg = time.perf_counter()
                reg_res = await session.call_tool(
                    "concierge_register",
                    arguments={"name": "min_proj", "path": project_dir},
                )
                t_reg = time.perf_counter() - t0_reg
                results["(c.1) concierge_register"] = t_reg
                print(f"      -> Registrado em {t_reg:.4f}s")

                # (d) Minerar projeto (Gera embeddings e salva no Chroma)
                print("[4/5] Minerando projeto (concierge_mine) — dispara primeira carga de embedding...")
                t0_mine = time.perf_counter()
                mine_res = await session.call_tool(
                    "concierge_mine",
                    arguments={"project_name": "min_proj"},
                )
                t_mine = time.perf_counter() - t0_mine
                results["(c.2) concierge_mine (1o embedding / carga)"] = t_mine
                print(f"      -> Mineração concluida em {t_mine:.4f}s")

                # (e) Busca semantica (concierge_search)
                print("[5/5] Realizando busca semantica (concierge_search)...")
                t0_search = time.perf_counter()
                search_res = await session.call_tool(
                    "concierge_search",
                    arguments={"query": "rectangle area calculation"},
                )
                t_search = time.perf_counter() - t0_search
                results["(c.3) concierge_search (busca vetorial)"] = t_search
                print(f"      -> Busca concluida em {t_search:.4f}s")

                total_e2e = time.perf_counter() - t_spawn
                results["TOTAL E2E (spawn ate fim da busca)"] = total_e2e

    try:
        await asyncio.wait_for(_logic(), timeout=timeout)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 75)
    print("RESUMO DE MEDICOES PONTA A PONTA (E2E)")
    print("=" * 75)
    for k, v in results.items():
        print(f"{k:<50} | {v:>10.4f}s")
    print("=" * 75)
    return results


def main():
    parser = argparse.ArgumentParser(description="MCP E2E Profile")
    parser.add_argument("--python", default=sys.executable, help="Python target")
    parser.add_argument("--timeout", type=float, default=180.0, help="Timeout in seconds")
    args = parser.parse_args()

    asyncio.run(run_e2e_profile(target_python=args.python, timeout=args.timeout))


if __name__ == "__main__":
    main()
