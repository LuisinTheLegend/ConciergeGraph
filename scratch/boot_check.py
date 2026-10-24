"""
scratch/boot_check.py — Script de prova de inicializacao real do servidor MCP.

Usa o cliente MCP (mcp.client.stdio.stdio_client + ClientSession) para:
  (a) Iniciar o servidor como processo filho com o Python do venv sob teste
      ('<venv>/Scripts/python main.py' ou console script 'concierge-mcp'),
      com GRAFO_DB_PATH e GRAFO_CHROMA_PATH apontando para pasta TEMPORARIA (NUNCA data/),
      GRAFO_TRANSPORT=stdio;
  (b) Fazer initialize e list_tools; afirmar 31 ferramentas;
  (c) Chamar concierge_status e registrar o resultado;
  (d) Encerrar o processo; timeout total configuravel (default: 180s);
      codigos de saida claros: 0 = ok, 1 = falha com a mensagem do erro.
Imprime a versao do mcp instalada e sys.version no ambiente de destino.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_target_info(target_python: str) -> tuple[str, str]:
    """Obtem versao do Python e versao do MCP no venv de destino."""
    try:
        py_ver_out = subprocess.check_output(
            [target_python, "-c", "import sys; print(sys.version)"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception as e:
        py_ver_out = f"Erro ao obter sys.version: {e}"

    try:
        mcp_ver_out = subprocess.check_output(
            [
                target_python,
                "-c",
                "import importlib.metadata; print(importlib.metadata.version('mcp'))",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception as e:
        mcp_ver_out = f"Nao instalado ou erro: {e}"

    return py_ver_out, mcp_ver_out


def find_console_script(target_python: str) -> str:
    """Localiza o script 'concierge-mcp' correspondente ao target_python."""
    py_path = Path(target_python).resolve()
    scripts_dir = py_path.parent
    candidates = [
        scripts_dir / "concierge-mcp.exe",
        scripts_dir / "concierge-mcp",
        scripts_dir.parent / "bin" / "concierge-mcp",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    # Se nao encontrado diretamente no diretorio do python, tenta shutil.which
    which_res = shutil.which("concierge-mcp")
    if which_res:
        return which_res
    raise FileNotFoundError(
        f"Console script 'concierge-mcp' nao encontrado em {scripts_dir} nem no PATH."
    )


async def run_boot_check(
    target_python: str,
    entrypoint: str,
    timeout: float,
) -> None:
    # Importacao do cliente MCP
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        print(f"ERRO: MCP Client nao disponivel no executor atual: {e}", file=sys.stderr)
        sys.exit(1)

    py_ver, mcp_ver = get_target_info(target_python)
    print("=" * 70)
    print("BOOT CHECK — Grafo Concierge MCP Server")
    print("=" * 70)
    print(f"Target Python:      {target_python}")
    print(f"Target Python Ver:  {py_ver}")
    print(f"Target MCP Version: {mcp_ver}")
    print(f"Entrypoint Mode:    {entrypoint}")
    print(f"Timeout:            {timeout}s")
    print(f"Repo Root:          {REPO_ROOT}")

    # Diretorio temporario isolado
    tmp_dir = tempfile.mkdtemp(prefix="grafo_boot_check_")
    db_path = os.path.join(tmp_dir, "test_concierge.db")
    chroma_path = os.path.join(tmp_dir, "test_chroma")
    print(f"Temp DB Path:       {db_path}")
    print(f"Temp Chroma Path:   {chroma_path}")
    print("=" * 70)

    # Variaveis de ambiente para o processo filho
    env = os.environ.copy()
    env["GRAFO_DB_PATH"] = db_path
    env["GRAFO_CHROMA_PATH"] = chroma_path
    env["GRAFO_CHROMA_COLLECTION"] = "test_boot_collection"
    env["GRAFO_TRANSPORT"] = "stdio"
    env["GRAFO_LOG_LEVEL"] = "INFO"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)

    if entrypoint == "python-main":
        command = target_python
        args = ["main.py"]
    elif entrypoint == "console-script":
        command = find_console_script(target_python)
        args = []
    else:
        raise ValueError(f"Entrypoint desconhecido: {entrypoint}")

    print(f"Executando comando: {command} {' '.join(args)}")

    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env,
        cwd=REPO_ROOT,
    )

    async def _check_logic():
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("Iniciando sessao MCP e enviando initialize...")
                init_res = await session.initialize()
                print(f"[OK] MCP Initialized: {init_res.serverInfo}")

                print("Listando ferramentas com list_tools...")
                tools_res = await session.list_tools()
                tool_names = [t.name for t in tools_res.tools]
                num_tools = len(tool_names)
                print(f"[OK] Total de ferramentas registradas: {num_tools}")
                if num_tools != 31:
                    raise AssertionError(
                        f"Esperado 31 ferramentas, mas servidor registrou {num_tools}: {tool_names}"
                    )

                print("Executando chamada a 'concierge_status'...")
                status_res = await session.call_tool("concierge_status", arguments={})
                print(f"[OK] concierge_status resultado: isError={status_res.isError}")
                if status_res.content:
                    for c in status_res.content:
                        if hasattr(c, "text"):
                            print(f"     Status Content: {c.text}")
                if status_res.isError:
                    raise RuntimeError(f"concierge_status retornou erro: {status_res}")

                print("=" * 70)
                print("BOOT CHECK SUCCESS: 31 ferramentas ativas e concierge_status OK.")
                print("=" * 70)

    try:
        await asyncio.wait_for(_check_logic(), timeout=timeout)
    except Exception as exc:
        print("\n" + "!" * 70, file=sys.stderr)
        print(f"BOOT CHECK FAILED: {exc}", file=sys.stderr)
        print("!" * 70 + "\n", file=sys.stderr)
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grafo Concierge MCP Boot Check")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Caminho do executavel Python a ser testado (default: sys.executable)",
    )
    parser.add_argument(
        "--entrypoint",
        choices=["python-main", "console-script"],
        default="python-main",
        help="Modo de inicializacao: 'python-main' ou 'console-script'",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Timeout total em segundos (default: 180.0)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            run_boot_check(
                target_python=args.python,
                entrypoint=args.entrypoint,
                timeout=args.timeout,
            )
        )
    except Exception as e:
        sys.exit(1)


if __name__ == "__main__":
    main()
