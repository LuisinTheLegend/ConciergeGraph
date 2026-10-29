"""
scratch/evidencia_4_2e/mcp_e2e_v2.py — Ferramenta de medição E2E com cliente MCP real (STDIO).

Substitui e corrige de ponta a ponta o script legado scratch/mcp_e2e_profile.py (F4-016).
Requisitos e funcionalidades:
  1. Cria projeto temporário com 5 arquivos Python pequenos e distintos.
  2. Chamadas com parâmetros reais:
     - concierge_register(project_path=..., wing=..., privacy_level=..., summary=...)
     - count_embeddings(project_identifier=...)
     - concierge_mine(path=..., project_identifier=..., auto_tag=...)
     - concierge_search(query=..., project_identifier=..., top_k=...)
  3. Validação estrita: se isError=True ou success=False, imprime o erro e termina com código != 0.
  4. Valida nós criados > 0, vetores no Chroma > antes, e resultado de busca condizente.
  5. Cronometra: spawn->initialize, list_tools, register, mine (1o embedding), search (1a busca), 2a search.
  6. Opções:
     --warmup {on,off}
     --delay-before-mine SEGUNDOS
     --probe-during-warmup SEGUNDOS (Adendo B)
     --measure-rss (Adendo C)
     --offline (Adendo D)
     --self-test-bad-args (Passo 1.7)
     --out ARQUIVO
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def create_sample_project(project_dir: str) -> list[str]:
    """Cria 5 arquivos Python pequenos e distintos no diretório do projeto."""
    os.makedirs(project_dir, exist_ok=True)
    files = {}

    files["math_operations.py"] = (
        '"""Módulo de cálculos geométricos básicos."""\n\n'
        'def calculate_rectangle_area(width: float, height: float) -> float:\n'
        '    """Calcula a área de um retângulo a partir da largura e altura."""\n'
        '    return width * height\n\n'
        'def calculate_circle_area(radius: float) -> float:\n'
        '    """Calcula a área de um círculo a partir do raio."""\n'
        '    import math\n'
        '    return math.pi * radius * radius\n'
    )

    files["file_storage.py"] = (
        '"""Módulo utilitário para operações em arquivos de texto."""\n\n'
        'def read_text_lines(filepath: str) -> list[str]:\n'
        '    """Lê todas as linhas de um arquivo de texto em UTF-8."""\n'
        '    with open(filepath, "r", encoding="utf-8") as f:\n'
        '        return f.readlines()\n\n'
        'def write_text_content(filepath: str, content: str) -> int:\n'
        '    """Escreve conteúdo de texto em arquivo UTF-8."""\n'
        '    with open(filepath, "w", encoding="utf-8") as f:\n'
        '        return f.write(content)\n'
    )

    files["string_manipulator.py"] = (
        '"""Módulo utilitário de manipulação e higienização de strings."""\n\n'
        'def slugify_string(text: str) -> str:\n'
        '    """Converte um título em slug amigável para URLs."""\n'
        '    import re\n'
        '    return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")\n\n'
        'def truncate_text(text: str, max_chars: int = 100) -> str:\n'
        '    """Trunca o texto caso exceda o limite de caracteres."""\n'
        '    return text[:max_chars] if len(text) > max_chars else text\n'
    )

    files["finance_tools.py"] = (
        '"""Módulo de fórmulas financeiras fundamentais."""\n\n'
        'def compute_compound_interest(principal: float, annual_rate: float, months: int) -> float:\n'
        '    """Calcula montante de juros compostos a taxa nominal mensal."""\n'
        '    monthly_rate = annual_rate / 12.0\n'
        '    return principal * ((1.0 + monthly_rate) ** months)\n'
    )

    files["network_utils.py"] = (
        '"""Módulo de utilitários de requisição e query strings."""\n\n'
        'def build_query_string(params: dict[str, str]) -> str:\n'
        '    """Formata dicionário de parâmetros em string de query URL."""\n'
        '    import urllib.parse\n'
        '    return urllib.parse.urlencode(params)\n'
    )

    created_paths = []
    for fname, content in files.items():
        p = os.path.join(project_dir, fname)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        created_paths.append(p)

    return created_paths


def parse_mcp_result(call_res: Any, tool_name: str) -> dict[str, Any]:
    """Valida retorno do MCP: se isError ou success=False, levanta exceção."""
    if getattr(call_res, "isError", False):
        raise RuntimeError(f"Tool {tool_name} returned isError=True: {call_res}")

    text_content = ""
    for c in getattr(call_res, "content", []):
        if hasattr(c, "text"):
            text_content += c.text

    if not text_content:
        raise RuntimeError(f"Tool {tool_name} returned empty content: {call_res}")

    try:
        data = json.loads(text_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Tool {tool_name} returned non-JSON text: {text_content}") from exc

    if isinstance(data, dict) and not data.get("success", True):
        raise RuntimeError(f"Tool {tool_name} returned success=False: {data}")

    return data


def log_ts(msg: str) -> None:
    """Imprime mensagem com timestamp e flush imediato para diagnóstico em tempo real."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def get_process_rss_mb(server_process_pid: int | None) -> float | None:
    """Retorna RSS do processo do servidor em MB usando psutil."""
    if not PSUTIL_AVAILABLE or server_process_pid is None:
        return None
    try:
        p = psutil.Process(server_process_pid)
        return p.memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return None


async def run_probes(session: Any, duration: float, interval: float = 0.5) -> list[dict[str, Any]]:
    """Adendo B: Executa chamadas periódicas a concierge_status e list_tools durante o warm-up."""
    records: list[dict[str, Any]] = []
    t_end = time.perf_counter() + duration
    probe_id = 0

    while time.perf_counter() < t_end:
        probe_id += 1
        # 1. concierge_status
        t0 = time.perf_counter()
        status_res = await session.call_tool("concierge_status", arguments={})
        t_status = time.perf_counter() - t0
        parse_mcp_result(status_res, "concierge_status (probe)")

        # 2. list_tools
        t0 = time.perf_counter()
        tools_res = await session.list_tools()
        t_tools = time.perf_counter() - t0

        records.append({
            "probe_id": probe_id,
            "timestamp": time.perf_counter(),
            "status_latency_s": t_status,
            "list_tools_latency_s": t_tools,
        })
        await asyncio.sleep(interval)

    return records


async def main_async(args: argparse.Namespace) -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tmp_dir = tempfile.mkdtemp(prefix="grafo_e2e_v2_")
    db_path = os.path.join(tmp_dir, "e2e_v2_concierge.db")
    chroma_path = os.path.join(tmp_dir, "e2e_v2_chroma")
    project_dir = os.path.join(tmp_dir, "sample_project")

    created_files = create_sample_project(project_dir)

    print("=" * 75)
    print("GRAFO CONCIERGE — MCP E2E V2 PROFILE (STDIO REAL)")
    print("=" * 75)
    print(f"Target Python:      {args.target_python}")
    print(f"Temp DB:            {db_path}")
    print(f"Temp Chroma:        {chroma_path}")
    print(f"Sample Project Dir: {project_dir} ({len(created_files)} files)")
    print(f"Warmup:             {args.warmup}")
    print(f"Delay before mine:  {args.delay_before_mine}s")
    print(f"Probe duration:     {args.probe_during_warmup}s")
    print(f"Offline:            {args.offline}")
    print(f"Self-test bad args: {args.self_test_bad_args}")
    print("=" * 75)

    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = db_path
    env["GRAFO_CHROMA_PATH"] = chroma_path
    env["GRAFO_CHROMA_COLLECTION"] = "e2e_v2_collection"
    env["GRAFO_TRANSPORT"] = "stdio"
    env["GRAFO_LOG_LEVEL"] = "INFO"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["TQDM_DISABLE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)

    # Configuração de Warm-up
    if args.warmup == "on":
        env["GRAFO_EMBED_WARMUP"] = "true"
    elif args.warmup == "off":
        env["GRAFO_EMBED_WARMUP"] = "false"

    # Configuração de Offline
    if args.offline:
        env["HF_HUB_OFFLINE"] = "1"

    server_params = StdioServerParameters(
        command=args.target_python,
        args=["main.py"],
        env=env,
        cwd=REPO_ROOT,
    )

    results: dict[str, Any] = {
        "params": {
            "warmup": args.warmup,
            "delay_before_mine": args.delay_before_mine,
            "offline": args.offline,
            "probe_duration": args.probe_during_warmup,
        },
        "timings": {},
        "rss_mb": {},
        "probes": [],
        "success": False,
    }

    stderr_log_path = os.path.join(tmp_dir, "server_stderr.log")
    t_spawn = time.perf_counter()

    try:
        with open(stderr_log_path, "w", encoding="utf-8") as errlog_file:
            async with stdio_client(server_params, errlog=errlog_file) as (read_stream, write_stream), \
                       ClientSession(read_stream, write_stream) as session:
                # Identificar PID do filho para RSS
                server_pid = None
                if PSUTIL_AVAILABLE:
                    curr_p = psutil.Process()
                    children = [c for c in curr_p.children(recursive=True) if "python" in c.name().lower()]
                    if children:
                        server_pid = children[0].pid
                        results["server_pid"] = server_pid

                # 1. Initialize
                log_ts("[1/6] Enviando initialize...")
                init_res = await session.initialize()
                t_init = time.perf_counter()
                elapsed_init = t_init - t_spawn
                results["timings"]["initialize"] = elapsed_init
                log_ts(f"      -> Concluido em {elapsed_init:.4f}s apos spawn")

                if args.measure_rss:
                    rss_init = get_process_rss_mb(server_pid)
                    results["rss_mb"]["after_initialize"] = rss_init
                    log_ts(f"      -> RSS apos initialize: {rss_init:.2f} MB" if rss_init else "      -> RSS: não disponível")

                # 2. List tools
                log_ts("[2/6] Solicitando list_tools...")
                t0_list = time.perf_counter()
                tools_res = await session.list_tools()
                t_list = time.perf_counter() - t0_list
                results["timings"]["list_tools"] = t_list
                log_ts(f"      -> {len(tools_res.tools)} ferramentas listadas em {t_list:.4f}s")
                if len(tools_res.tools) != 31:
                    raise RuntimeError(f"Esperado 31 ferramentas, obteve {len(tools_res.tools)}")

                # Probes durante warmup se configurado (Adendo B)
                if args.probe_during_warmup > 0:
                    log_ts(f"[Probe] Executando probes concorrentes por {args.probe_during_warmup}s...")
                    probe_records = await run_probes(session, args.probe_during_warmup)
                    results["probes"] = probe_records
                    log_ts(f"      -> {len(probe_records)} ciclos de probe executados.")

                # Delay antes da mineração (se configurado)
                if args.delay_before_mine > 0:
                    log_ts(f"[*] Aguardando delay configurado de {args.delay_before_mine}s antes da mineração...")
                    await asyncio.sleep(args.delay_before_mine)

                if args.measure_rss:
                    rss_delay = get_process_rss_mb(server_pid)
                    results["rss_mb"]["after_warmup_or_delay"] = rss_delay
                    log_ts(f"      -> RSS apos warmup/delay: {rss_delay:.2f} MB" if rss_delay else "      -> RSS: não disponível")

                # Teste Negativo (Passo 1.7)
                if args.self_test_bad_args:
                    log_ts("[Self-Test Negativo] Chamando concierge_mine com argumentos incorretos ('project_name')...")
                    res_bad = await session.call_tool("concierge_mine", arguments={"project_name": "invalid_proj"})
                    # Isto DEVE falhar ou retornar success=False
                    parse_mcp_result(res_bad, "concierge_mine (self-test bad args)")
                    raise RuntimeError("Self-test falhou: concierge_mine aceitou argumentos incorretos sem erro!")

                # 3. concierge_register com parâmetros reais
                log_ts("[3/6] Registrando projeto (concierge_register)...")
                t0_reg = time.perf_counter()
                reg_res = await session.call_tool(
                    "concierge_register",
                    arguments={
                        "project_path": project_dir,
                        "wing": "geral",
                        "privacy_level": "PUBLIC",
                        "summary": "Projeto de teste E2E v2 com 5 módulos Python",
                    },
                )
                t_reg = time.perf_counter() - t0_reg
                reg_data = parse_mcp_result(reg_res, "concierge_register")
                project_uuid = reg_data["project_uuid"]
                results["timings"]["concierge_register"] = t_reg
                results["project_uuid"] = project_uuid
                log_ts(f"      -> Projeto registrado em {t_reg:.4f}s: UUID={project_uuid}")

                # 4. Checar contagem inicial de vetores (count_embeddings)
                count_res_pre = await session.call_tool("count_embeddings", arguments={"project_identifier": project_uuid})
                count_data_pre = parse_mcp_result(count_res_pre, "count_embeddings (pre)")
                initial_vector_count = count_data_pre.get("count", 0)
                log_ts(f"      -> Contagem inicial de vetores no Chroma: {initial_vector_count}")

                # 5. concierge_mine com parâmetros reais
                log_ts("[4/6] Minerando projeto (concierge_mine) — DISPARA 1o EMBEDDING REAL...")
                t0_mine = time.perf_counter()
                mine_res = await session.call_tool(
                    "concierge_mine",
                    arguments={
                        "path": project_dir,
                        "project_identifier": project_uuid,
                        "auto_tag": True,
                    },
                )
                t_mine = time.perf_counter() - t0_mine
                mine_data = parse_mcp_result(mine_res, "concierge_mine")
                results["timings"]["concierge_mine"] = t_mine
                files_processed = mine_data.get("files_processed", 0)
                nodes_created = mine_data.get("nodes_created", 0)
                log_ts(f"      -> Mineração concluída em {t_mine:.4f}s: files={files_processed}, nodes={nodes_created}")

                if nodes_created <= 0:
                    raise RuntimeError(f"Mineração gerou 0 nós no grafo: {mine_data}")

                # Validar aumento de vetores no Chroma
                count_res_post = await session.call_tool("count_embeddings", arguments={"project_identifier": project_uuid})
                count_data_post = parse_mcp_result(count_res_post, "count_embeddings (post)")
                post_vector_count = count_data_post.get("count", 0)
                log_ts(f"      -> Contagem de vetores no Chroma após mineração: {post_vector_count}")
                if post_vector_count <= initial_vector_count:
                    raise RuntimeError(f"Contagem de vetores não aumentou: pre={initial_vector_count}, post={post_vector_count}")

                if args.measure_rss:
                    rss_mine = get_process_rss_mb(server_pid)
                    results["rss_mb"]["after_mine"] = rss_mine
                    log_ts(f"      -> RSS apos mineração: {rss_mine:.2f} MB" if rss_mine else "      -> RSS: não disponível")

                # 6. concierge_search (1ª busca vetorial)
                log_ts("[5/6] Executando 1ª busca vetorial (concierge_search)...")
                t0_search1 = time.perf_counter()
                search1_res = await session.call_tool(
                    "concierge_search",
                    arguments={
                        "query": "calculate rectangle area width height",
                        "project_identifier": project_uuid,
                        "top_k": 5,
                    },
                )
                t_search1 = time.perf_counter() - t0_search1
                search1_data = parse_mcp_result(search1_res, "concierge_search (1)")
                results["timings"]["concierge_search_1"] = t_search1
                s1_results = search1_data.get("results", [])
                log_ts(f"      -> 1ª busca concluída em {t_search1:.4f}s: {len(s1_results)} resultados")

                if not s1_results:
                    raise RuntimeError("1ª busca retornou 0 resultados!")

                first_match = s1_results[0]
                log_ts("      -> Top 1 resultado da busca:")
                log_ts(f"         node_id:      {first_match.get('node_id')}")
                log_ts(f"         label:        {first_match.get('label')}")
                log_ts(f"         summary:      {first_match.get('summary')}")
                log_ts(f"         node_type:    {first_match.get('node_type')}")
                log_ts(f"         hybrid_score: {first_match.get('hybrid_score')}")
                log_ts(f"         vector_score: {first_match.get('vector_score')}")

                # Valida que o resultado corresponde à query
                matched = any(
                    "rectangle" in (r.get("label", "") + " " + r.get("summary", "")).lower()
                    for r in s1_results
                )
                if not matched:
                    raise RuntimeError(f"Nenhum resultado corresponde ao termo 'rectangle': {s1_results}")

                # 7. concierge_search (2ª busca vetorial)
                log_ts("[6/6] Executando 2ª busca vetorial (concierge_search)...")
                t0_search2 = time.perf_counter()
                search2_res = await session.call_tool(
                    "concierge_search",
                    arguments={
                        "query": "read text lines from file storage",
                        "project_identifier": project_uuid,
                        "top_k": 5,
                    },
                )
                t_search2 = time.perf_counter() - t0_search2
                search2_data = parse_mcp_result(search2_res, "concierge_search (2)")
                results["timings"]["concierge_search_2"] = t_search2
                s2_results = search2_data.get("results", [])
                log_ts(f"      -> 2ª busca concluída em {t_search2:.4f}s: {len(s2_results)} resultados")

                if not s2_results:
                    raise RuntimeError("2ª busca retornou 0 resultados!")

                results["success"] = True
                log_ts("=" * 75)
                log_ts("E2E V2 PROFILE CONCLUÍDO COM SUCESSO TOTAL!")
                log_ts("=" * 75)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Imprimir tabela resumo
    print("\n" + "=" * 75)
    print("RESUMO DE MEDIÇÕES E2E V2:")
    print("-" * 75)
    for k, v in results["timings"].items():
        print(f"{k:<35} : {v:>10.4f} s")
    if results["rss_mb"]:
        print("-" * 75)
        for k, v in results["rss_mb"].items():
            print(f"RSS: {k:<30} : {v:>10.2f} MB" if v else f"RSS: {k:<30} : não medido")
    print("=" * 75)

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Resultados salvos em JSON: {args.out}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Grafo Concierge MCP E2E v2 Profile")
    parser.add_argument("--target-python", default=sys.executable, help="Python executable to run server")
    parser.add_argument("--warmup", choices=["on", "off"], default="off", help="Control GRAFO_EMBED_WARMUP")
    parser.add_argument("--delay-before-mine", type=float, default=0.0, help="Delay after list_tools before mine")
    parser.add_argument("--probe-during-warmup", type=float, default=0.0, help="Probe latency for N seconds after init")
    parser.add_argument("--measure-rss", action="store_true", help="Measure server process RSS memory")
    parser.add_argument("--offline", action="store_true", help="Set HF_HUB_OFFLINE=1")
    parser.add_argument("--self-test-bad-args", action="store_true", help="Run negative self-test with bad arguments")
    parser.add_argument("--out", default=None, help="JSON output file path")

    args = parser.parse_args()

    try:
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except Exception as exc:
        print(f"\n[FALHA FATAL NO E2E V2]: {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
