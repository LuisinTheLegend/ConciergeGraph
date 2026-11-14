import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Nexus-Memory\GrafoConcierge")
OUT = ROOT / "scratch" / "evidencia_4_5c_bis" / "task3_repro_3_erros.txt"
sys.path.insert(0, str(ROOT))


def _call_mcp_sync(server, name: str, args: dict):
    async def _run():
        return await server.mcp._tool_manager.call_tool(name, args)

    return asyncio.run(_run())


def _extract_result(res):
    if isinstance(res, dict):
        return res
    if hasattr(res, "content") and res.content:
        texts = [getattr(c, "text", str(c)) for c in res.content]
        joined = "\n".join(texts)
        try:
            return json.loads(joined)
        except Exception:
            return joined
    if isinstance(res, list) and res:
        texts = [getattr(c, "text", str(c)) for c in res]
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except Exception:
                return texts[0]
        return texts
    return repr(res)


def run_case(lightweight: bool, log: list[str]) -> None:
    mode = "LIGHTWEIGHT=true" if lightweight else "LIGHTWEIGHT=false (real Chroma PersistentClient)"
    log.append(f"\n================ {mode} ================")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        proj = tmp_path / "sample_proj"
        proj.mkdir()
        (proj / "app.py").write_text(
            "def helper(x: int) -> int:\n"
            "    return x + 1\n\n"
            "def run_flow(v: int) -> int:\n"
            "    return helper(v) * 2\n",
            encoding="utf-8",
        )
        (proj / "utils.ts").write_text(
            "export function greet(name: string): string {\n"
            "  return 'hi ' + name;\n"
            "}\n",
            encoding="utf-8",
        )

        os.environ["GRAFO_DB_PATH"] = str(tmp_path / "concierge.db")
        os.environ["GRAFO_CHROMA_PATH"] = str(tmp_path / "chroma")
        os.environ["GRAFO_CHROMA_COLLECTION"] = f"grafo_45cbis_{'lw' if lightweight else 'full'}"
        os.environ["GRAFO_LLM_MODEL"] = "none"
        os.environ["GRAFO_LLM_PROVIDER"] = "none"
        os.environ["GRAFO_LLM_API_KEY"] = "sk-fake-45cbis"
        os.environ["GRAFO_API_KEY"] = "fake-api-key-45cbis"
        os.environ["GRAFO_LIGHTWEIGHT_MODE"] = "true" if lightweight else "false"
        os.environ["GRAFO_VECTOR_BACKEND"] = "chroma"
        os.environ["GRAFO_DEFAULT_STATE"] = "MAINTENANCE"
        os.environ["GRAFO_JANITOR_INTERVAL"] = "99999"
        os.environ["GRAFO_TRANSPORT"] = "stdio"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        import dotenv

        dotenv.load_dotenv = lambda *a, **kw: False

        # Ensure fresh config/vector store per mode if tested in same process
        import core.config as cfg_mod

        if hasattr(cfg_mod, "_config_instance"):
            cfg_mod._config_instance = None

        import main as app_main

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        server = janitor = store = None
        try:
            server, janitor, store = app_main.bootstrap()
            server.governor.set_session_state("default", "MAINTENANCE")

            reg = _extract_result(
                _call_mcp_sync(
                    server,
                    "concierge_register",
                    {
                        "project_path": str(proj),
                        "wing": "core",
                        "privacy_level": "PUBLIC",
                        "summary": "Repro project 4.5c-bis",
                    },
                )
            )
            log.append(f"concierge_register => {reg}")
            real_uuid = reg["project_uuid"]

            rows = store.list_projects()
            log.append(f"store.list_projects() keys => {list(rows[0].keys()) if rows else []}")

            mine = _extract_result(
                _call_mcp_sync(
                    server,
                    "concierge_mine",
                    {"path": str(proj), "project_identifier": real_uuid, "auto_tag": True},
                )
            )
            log.append(f"concierge_mine => {mine}")

            syms = _extract_result(
                _call_mcp_sync(
                    server,
                    "search_symbols",
                    {"query": "helper", "project_identifier": real_uuid},
                )
            )
            log.append(f"search_symbols => {syms}")
            real_node_id = syms["symbols"][0]["id"]
            log.append(f"Selected mined node_id={real_node_id} (type={type(real_node_id).__name__})")

            if lightweight:
                # 1. concierge_commit via real MCP call_tool:
                # 1a: synthetic bug in 4.5a script passed folder_name ('sample_proj') as project_uuid
                res_1a = _extract_result(
                    _call_mcp_sync(
                        server,
                        "concierge_commit",
                        {
                            "project_uuid": "sample_proj",
                            "phase": "4.5a",
                            "technical_changes": "Repro with folder_name",
                            "updated_pointers": ["app.py"],
                        },
                    )
                )
                log.append(f"[1a] concierge_commit(project_uuid='sample_proj', call_tool) => {res_1a}")

                # 1b: valid args (real UUID + list[str] updated_pointers + mined node_ids) via call_tool
                res_1b = _extract_result(
                    _call_mcp_sync(
                        server,
                        "concierge_commit",
                        {
                            "project_uuid": real_uuid,
                            "phase": "build",
                            "technical_changes": "Valid commit with real UUID",
                            "updated_pointers": ["app.py::helper"],
                            "node_ids": [real_node_id],
                        },
                    )
                )
                log.append(f"[1b] concierge_commit(valid project_uuid={real_uuid}, call_tool) => {res_1b}")

                # 2. concierge_load:
                # 2a: direct tool_obj.fn(node_id=str(real_node_id)) bypassing FastMCP Pydantic (4.5a trace)
                tool_load = next(
                    t for t in server.mcp._tool_manager.list_tools() if t.name == "concierge_load"
                )
                res_2a = tool_load.fn(node_id=str(real_node_id))
                log.append(f"[2a] concierge_load via fn(node_id={str(real_node_id)!r}) => {res_2a}")

                # 2b: str via real MCP call_tool (FastMCP Pydantic coercion/validation)
                try:
                    res_2b = _extract_result(
                        _call_mcp_sync(server, "concierge_load", {"node_id": str(real_node_id)})
                    )
                except Exception as exc:
                    res_2b = f"{type(exc).__name__}: {exc}"
                log.append(f"[2b] concierge_load via call_tool(node_id={str(real_node_id)!r}) => {res_2b}")

                # 2c: valid int via real MCP call_tool
                res_2c = _extract_result(
                    _call_mcp_sync(server, "concierge_load", {"node_id": int(real_node_id)})
                )
                log.append(
                    f"[2c] concierge_load via call_tool(node_id={int(real_node_id)}) => "
                    f"success={res_2c.get('success')}, node_id={res_2c.get('node', {}).get('id')}, "
                    f"label={res_2c.get('node', {}).get('label')}"
                )

            # 3. reset_collection via real MCP call_tool
            vstore = server._gc._vector
            log.append(
                f"VectorStore status: available={getattr(vstore, '_available', None)}, "
                f"client_is_none={getattr(vstore, '_client', None) is None}"
            )
            res_3 = _extract_result(_call_mcp_sync(server, "reset_collection", {}))
            log.append(f"[3] reset_collection via call_tool() => {res_3}")
        finally:
            os.chdir(old_cwd)
            if janitor is not None:
                try:
                    janitor.stop()
                except Exception:
                    pass
            if store is not None:
                try:
                    store.close()
                except Exception:
                    pass


def main() -> None:
    log: list[str] = ["=== TASK 3 REPRO: 3 ERROS DO TRACE 4.5a VIA MCP REAL ==="]
    run_case(lightweight=True, log=log)
    run_case(lightweight=False, log=log)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(log) + "\n", encoding="utf-8")
    print("Task 3 repro finished OK.")


if __name__ == "__main__":
    main()
