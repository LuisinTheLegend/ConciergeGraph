"""Probe Bloco 4 da 4.5a-bis: mapeamento completo das 31 ferramentas MCP -> handlers -> middleware -> branches vetor/embedding."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scratch" / "evidencia_4_5a_bis"

LIVE_FILES = [
    "main.py",
    "interface/__init__.py",
    "interface/cli.py",
    "interface/mcp_server.py",
    "core/middleware.py",
    "core/hybrid_search.py",
    "core/memory_extractor.py",
    "core/checkpointer.py",
    "core/database.py",
    "core/project_index.py",
    "core/graph_rag.py",
    "core/vector_backend.py",
    "core/config.py",
    "core/mcp_governor.py",
    "ingestion/orchestrator.py",
    "ingestion/crawler.py",
    "ingestion/parser.py",
    "ingestion/summarizer.py",
    "services/janitor.py",
    "storage/vector_store.py",
    "storage/store.py",
    "storage/base_backend.py",
    "storage/connection.py",
    "storage/logic.py",
    "storage/schema.py",
    "storage/semantic_logic.py",
]


def scan_lightweight_chroma_branches() -> list[dict]:
    pat = re.compile(
        r"GRAFO_LIGHTWEIGHT_MODE|CHROMADB_AVAILABLE|SENTENCE_TRANSFORMERS_AVAILABLE|"
        r"ChromaDB unavailable|reset_collection|embedding_manager|vector_store|"
        r"lightweight|ChromaVectorStore|QdrantVectorStore|generate_embedding|embed_query|encode\("
    )
    hits = []
    for rel in LIVE_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, start=1):
            if pat.search(line):
                hits.append({"file": rel, "line": idx, "text": line.strip()})
    return hits


def scan_deferred_imports_in_live() -> list[dict]:
    """Todos os imports dentro de funcoes/blocos (col_offset > 0) nos modulos vivos."""
    results = []
    for rel in LIVE_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.col_offset > 0:
                if isinstance(node, ast.Import):
                    results.append(
                        {
                            "file": rel,
                            "line": node.lineno,
                            "kind": "import",
                            "targets": [a.name for a in node.names],
                        }
                    )
                else:
                    results.append(
                        {
                            "file": rel,
                            "line": node.lineno,
                            "kind": "from",
                            "module": node.module,
                            "names": [a.name for a in node.names],
                        }
                    )
    return results


def parse_methods(path: Path) -> dict[str, dict]:
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(path))
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = ast.get_source_segment(src, node) or ""
            methods[node.name] = {
                "start_line": node.lineno,
                "end_line": node.end_lineno,
                "source": seg,
            }
    return methods


def trace_31_mcp_tools() -> list[dict]:
    mcp_path = ROOT / "interface" / "mcp_server.py"
    mw_path = ROOT / "core" / "middleware.py"
    mcp_src = mcp_path.read_text(encoding="utf-8", errors="replace")
    mcp_tree = ast.parse(mcp_src, filename="interface/mcp_server.py")

    mcp_methods = parse_methods(mcp_path)
    mw_methods = parse_methods(mw_path)

    tools = []
    for node in ast.walk(mcp_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list:
            tool_name = None
            for dec in node.decorator_list:
                seg = ast.get_source_segment(mcp_src, dec) or ""
                if "mcp.tool" in seg:
                    m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', seg)
                    tool_name = m.group(1) if m else node.name
            if not tool_name:
                continue

            body_seg = ast.get_source_segment(mcp_src, node) or ""
            handler_calls = re.findall(r"server\.(_handle_[a-zA-Z0-9_]+)\(", body_seg)
            # Also find direct self._gc.* or store.* calls
            handler_details = []
            for hname in handler_calls:
                hinfo = mcp_methods.get(hname, {})
                hsrc = hinfo.get("source", "")
                gc_calls = re.findall(r"self\._gc\.([a-zA-Z0-9_]+)\(", hsrc)
                vec_hits_in_handler = [
                    kw
                    for kw in ("_vector", "_embedder", "embedding", "vector", "reset_collection")
                    if kw in hsrc
                ]
                mw_details = []
                for gname in sorted(set(gc_calls)):
                    minfo = mw_methods.get(gname, {})
                    msrc = minfo.get("source", "")
                    vec_kw = [
                        kw
                        for kw in (
                            "_vector",
                            "_embedder",
                            "_orchestrator",
                            "_search_engine",
                            "_janitor",
                            "_extractor",
                            "embedding",
                            "vector",
                            "QdrantVectorStore",
                            "generate_embedding",
                            "count_embeddings",
                            "find_similar",
                            "reset_collection",
                        )
                        if kw in msrc
                    ]
                    mw_details.append(
                        {
                            "middleware_method": gname,
                            "lines": f"core/middleware.py:{minfo.get('start_line')}-{minfo.get('end_line')}",
                            "vector_keywords": vec_kw,
                        }
                    )
                handler_details.append(
                    {
                        "handler": hname,
                        "lines": f"interface/mcp_server.py:{hinfo.get('start_line')}-{hinfo.get('end_line')}",
                        "gc_calls": mw_details,
                        "handler_vec_keywords": vec_hits_in_handler,
                    }
                )
            tools.append(
                {
                    "tool_name": tool_name,
                    "tool_lines": f"interface/mcp_server.py:{node.lineno}-{node.end_lineno}",
                    "handlers": handler_details,
                }
            )
    return sorted(tools, key=lambda t: int(t["tool_lines"].split(":")[1].split("-")[0]))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    branches = scan_lightweight_chroma_branches()
    deferred = scan_deferred_imports_in_live()
    tools = trace_31_mcp_tools()

    out = {
        "tools_count": len(tools),
        "tools_trace": tools,
        "lightweight_chroma_hits": branches,
        "indented_or_conditional_imports_in_live": deferred,
    }
    (OUT_DIR / "bloco4_probe.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [f"=== 31 MCP TOOLS TRACE ({len(tools)}) ==="]
    for t in tools:
        lines.append(f"- {t['tool_name']} ({t['tool_lines']}):")
        for h in t["handlers"]:
            lines.append(f"    handler {h['handler']} ({h['lines']}) h_vec={h['handler_vec_keywords']}")
            for g in h["gc_calls"]:
                lines.append(
                    f"      -> {g['middleware_method']} ({g['lines']}) vec_kw={g['vector_keywords']}"
                )
        if not t["handlers"]:
            lines.append("    [no server._handle_* match]")

    lines.append(f"\n=== INDENTED / CONDITIONAL IMPORTS IN LIVE FILES ({len(deferred)}) ===")
    for d in deferred:
        lines.append(f"  {d['file']}:{d['line']}: {d}")

    (OUT_DIR / "bloco4_probe.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Done: {len(tools)} tools traced")


if __name__ == "__main__":
    main()
