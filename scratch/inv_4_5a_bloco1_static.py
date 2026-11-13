#!/usr/bin/env python3
"""
Bloco 1 (Estático) — Inventário 4.5a
Calcula o grafo estático de imports por AST a partir das raízes de produção,
distinguindo imports em tempo de carga, diferidos (em funções), PEP 562 __getattr__,
imports usados só em anotações de tipo, TYPE_CHECKING, e rastreia imports dinâmicos.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scratch" / "evidencia_4_5a"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROD_DIRS = ("core", "storage", "ingestion", "interface", "services", "agent", "agents")


def discover_prod_modules() -> dict[str, Path]:
    """Descobre todos os módulos Python rastreados nas pastas de produção + main.py."""
    res = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    modules: dict[str, Path] = {}
    for rel in sorted(res.stdout.splitlines()):
        rel = rel.strip()
        if not rel:
            continue
        parts = rel.split("/")
        if rel == "main.py":
            modules["main"] = ROOT / rel
        elif parts[0] in PROD_DIRS:
            if parts[-1] == "__init__.py":
                mod_name = ".".join(parts[:-1])
            else:
                mod_name = ".".join(parts[:-1] + [parts[-1][:-3]])
            modules[mod_name] = ROOT / rel
    return modules


def is_type_checking_test(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == "TYPE_CHECKING":
        return True
    if isinstance(node, ast.Attribute) and node.attr == "TYPE_CHECKING":
        return True
    return False


class UsageCollector(ast.NodeVisitor):
    """Coleta onde cada identificador importado é usado (só anotação vs valor em runtime)."""

    def __init__(self) -> None:
        self.in_annotation = 0
        self.runtime_names: set[str] = set()
        self.annotation_names: set[str] = set()

    def _visit_ann(self, node: ast.AST | None) -> None:
        if node is None:
            return
        self.in_annotation += 1
        self.visit(node)
        self.in_annotation -= 1

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if self.in_annotation > 0:
                self.annotation_names.add(node.id)
            else:
                self.runtime_names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for dec in node.decorator_list:
            self.visit(dec)
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self._visit_ann(arg.annotation)
        if node.args.vararg:
            self._visit_ann(node.args.vararg.annotation)
        if node.args.kwarg:
            self._visit_ann(node.args.kwarg.annotation)
        for d in node.args.defaults + node.args.kw_defaults:
            if d is not None:
                self.visit(d)
        self._visit_ann(node.returns)
        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._visit_ann(node.annotation)
        if node.value is not None:
            self.visit(node.value)

    def visit_Import(self, node: ast.Import) -> None:
        pass

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        pass


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, mod_name: str, is_pkg: bool, all_modules: set[str], runtime_names: set[str], annotation_names: set[str]):
        self.mod_name = mod_name
        self.is_pkg = is_pkg
        self.all_modules = all_modules
        self.runtime_names = runtime_names
        self.annotation_names = annotation_names
        self.in_func = 0
        self.in_getattr_func = 0
        self.in_type_checking = 0
        # list of (target_mod, lineno, kind, raw, ann_only_usage)
        self.edges: list[tuple[str, int, str, str, bool]] = []

    def _current_kind(self) -> str:
        if self.in_type_checking > 0:
            return "type_checking"
        if self.in_getattr_func > 0:
            return "pep562_getattr"
        if self.in_func > 0:
            return "deferred"
        return "load"

    def _resolve_base_pkg(self, level: int) -> list[str]:
        parts = self.mod_name.split(".")
        up = level - 1 if self.is_pkg else level
        if up == 0:
            return parts
        if up > len(parts):
            return []
        return parts[:-up]

    def _add_if_project_mod(self, candidate: str, lineno: int, kind: str, raw: str, ann_only: bool) -> None:
        if candidate in self.all_modules:
            self.edges.append((candidate, lineno, kind, raw, ann_only))
        parts = candidate.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent in self.all_modules:
                self.edges.append((parent, lineno, kind, f"{raw} (parent pkg {parent})", ann_only))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        is_ga = node.name == "__getattr__" and self.in_func == 0
        self.in_func += 1
        if is_ga:
            self.in_getattr_func += 1
        self.generic_visit(node)
        if is_ga:
            self.in_getattr_func -= 1
        self.in_func -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.in_func += 1
        self.generic_visit(node)
        self.in_func -= 1

    def visit_If(self, node: ast.If) -> None:
        if is_type_checking_test(node.test):
            self.in_type_checking += 1
            for stmt in node.body:
                self.visit(stmt)
            self.in_type_checking -= 1
            for stmt in node.orelse:
                self.visit(stmt)
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        kind = self._current_kind()
        for alias in node.names:
            bound = alias.asname or alias.name.split(".")[0]
            ann_only = (bound in self.annotation_names) and (bound not in self.runtime_names)
            raw = f"import {alias.name}"
            self._add_if_project_mod(alias.name, node.lineno, kind, raw, ann_only)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        kind = self._current_kind()
        if node.level > 0:
            base_parts = self._resolve_base_pkg(node.level)
            if node.module:
                target_base = ".".join(base_parts + node.module.split(".")) if base_parts else node.module
            else:
                target_base = ".".join(base_parts)
        else:
            target_base = node.module or ""

        if not target_base:
            return

        names_str = ", ".join(a.name for a in node.names)
        raw = f"from {'.' * node.level}{node.module or ''} import {names_str}"

        bound_names = [a.asname or a.name for a in node.names if a.name != "*"]
        ann_only = bool(bound_names) and all(
            (b in self.annotation_names and b not in self.runtime_names) for b in bound_names
        ) and not self.is_pkg

        self._add_if_project_mod(target_base, node.lineno, kind, raw, ann_only)
        for alias in node.names:
            if alias.name == "*":
                continue
            sub_cand = f"{target_base}.{alias.name}"
            if sub_cand in self.all_modules:
                self._add_if_project_mod(sub_cand, node.lineno, kind, raw, ann_only)


def analyze_file_imports(mod_name: str, path: Path, all_modules: set[str]) -> list[tuple[str, int, str, str, bool]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text, filename=str(path))
    uc = UsageCollector()
    uc.visit(tree)
    is_pkg = path.name == "__init__.py"
    visitor = ImportVisitor(mod_name, is_pkg, all_modules, uc.runtime_names, uc.annotation_names)
    visitor.visit(tree)
    seen = set()
    unique = []
    for item in visitor.edges:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def bfs_reach(
    roots: list[str],
    graph: dict[str, list[tuple[str, int, str, str, bool]]],
    allowed_kinds: set[str],
    exclude_ann_only: bool = False,
) -> dict[str, list[str]]:
    visited: dict[str, list[str]] = {}
    q = deque()
    for r in roots:
        if r not in visited:
            visited[r] = [r]
            q.append(r)
    while q:
        curr = q.popleft()
        for target, lineno, kind, raw, ann_only in graph.get(curr, []):
            if kind in allowed_kinds and not (exclude_ann_only and ann_only):
                if target not in visited:
                    visited[target] = visited[curr] + [f"{target} ({kind}{':ann_only' if ann_only else ''}@{curr}:{lineno})"]
                    q.append(target)
    return visited


def count_lines(path: Path) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    non_empty = sum(1 for l in lines if l.strip())
    return len(lines), non_empty


def scan_dynamic_imports(modules: dict[str, Path]) -> list[dict]:
    patterns = [
        ("importlib", re.compile(r"\bimportlib\b")),
        ("__import__", re.compile(r"\b__import__\b")),
        ("pkgutil", re.compile(r"\bpkgutil\b")),
        ("runpy", re.compile(r"\brunpy\b")),
        ("getattr_call", re.compile(r"\bgetattr\s*\(")),
        ("mod_string", re.compile(r"""['"](?:core|storage|ingestion|interface|services|agent|agents)\.[a-zA-Z0-9_.]+['"]""")),
        ("sys_modules", re.compile(r"\bsys\.modules\b")),
    ]
    hits = []
    for mod_name, path in sorted(modules.items()):
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, start=1):
            for tag, pat in patterns:
                if pat.search(line):
                    hits.append({
                        "file": rel,
                        "line": idx,
                        "tag": tag,
                        "code": line.strip(),
                    })
    return hits


def main() -> None:
    modules = discover_prod_modules()
    all_mod_names = set(modules.keys())

    graph: dict[str, list[tuple[str, int, str, str, bool]]] = {}
    reverse_graph: dict[str, list[dict]] = defaultdict(list)
    line_counts: dict[str, dict] = {}

    for mod_name, path in sorted(modules.items()):
        total_l, non_empty_l = count_lines(path)
        line_counts[mod_name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "total_lines": total_l,
            "non_empty_lines": non_empty_l,
        }
        edges = analyze_file_imports(mod_name, path, all_mod_names)
        graph[mod_name] = edges
        for target, lineno, kind, raw, ann_only in edges:
            reverse_graph[target].append({
                "importer": mod_name,
                "importer_path": path.relative_to(ROOT).as_posix(),
                "line": lineno,
                "kind": kind,
                "ann_only": ann_only,
                "raw": raw,
            })

    roots = ["main", "interface.cli"]
    # 1) Load-time strict (excluding ann_only? No, Python executes top-level imports even if ann_only! Let's track both!)
    reach_load_only = bfs_reach(roots, graph, {"load"})
    reach_runtime_no_getattr = bfs_reach(roots, graph, {"load", "deferred"})
    reach_runtime_semantic = bfs_reach(roots, graph, {"load", "deferred"}, exclude_ann_only=True)
    reach_with_pep562 = bfs_reach(roots, graph, {"load", "deferred", "pep562_getattr"})
    reach_with_types = bfs_reach(roots, graph, {"load", "deferred", "pep562_getattr", "type_checking"})

    util_script = ROOT / "scripts" / "bootstrap_core_memory.py"
    util_edges = analyze_file_imports("scripts.bootstrap_core_memory", util_script, all_mod_names)
    util_reach = bfs_reach(["__util__"], {"__util__": util_edges, **graph}, {"load", "deferred"})

    classified = {}
    for mod_name in sorted(all_mod_names):
        if mod_name in reach_load_only:
            status = "REACHABLE_LOAD"
        elif mod_name in reach_runtime_semantic:
            status = "REACHABLE_DEFERRED"
        elif mod_name in reach_runtime_no_getattr:
            status = "REACHABLE_ANNOTATION_ONLY_RUNTIME"
        elif mod_name in reach_with_pep562:
            status = "REACHABLE_PEP562_LAZY"
        elif mod_name in reach_with_types:
            status = "REACHABLE_TYPE_CHECKING"
        else:
            status = "UNREACHABLE"
        classified[mod_name] = {
            **line_counts[mod_name],
            "status": status,
            "importers": reverse_graph.get(mod_name, []),
        }

    dynamic_hits = scan_dynamic_imports(modules)

    summary = {
        "total_modules": len(all_mod_names),
        "roots": roots,
        "counts": {
            k: sum(1 for v in classified.values() if v["status"] == k)
            for k in (
                "REACHABLE_LOAD",
                "REACHABLE_DEFERRED",
                "REACHABLE_ANNOTATION_ONLY_RUNTIME",
                "REACHABLE_PEP562_LAZY",
                "REACHABLE_TYPE_CHECKING",
                "UNREACHABLE",
            )
        },
        "lines": {
            **{
                k: sum(v["total_lines"] for v in classified.values() if v["status"] == k)
                for k in (
                    "REACHABLE_LOAD",
                    "REACHABLE_DEFERRED",
                    "REACHABLE_ANNOTATION_ONLY_RUNTIME",
                    "REACHABLE_PEP562_LAZY",
                    "REACHABLE_TYPE_CHECKING",
                    "UNREACHABLE",
                )
            },
            "TOTAL_ALL": sum(v["total_lines"] for v in classified.values()),
        },
        "modules": classified,
        "utility_script_bootstrap_core_memory": {
            "direct_edges": util_edges,
            "reachable_modules": sorted(k for k in util_reach if k != "__util__"),
        },
        "dynamic_import_scans": dynamic_hits,
    }

    json_path = OUT_DIR / "bloco1_static_reach.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    out_lines = [
        "=== BLOCO 1 (ESTÁTICO): GRAFO DE IMPORTS AST ===",
        f"Total de módulos de produção descobertos: {summary['total_modules']}",
        f"Raízes de produção: {', '.join(roots)}",
        "",
        "Contagem por categoria:",
    ]
    for k, cnt in summary["counts"].items():
        out_lines.append(f"  {k}: {cnt} módulos ({summary['lines'][k]} linhas totais)")
    out_lines.append(f"  TOTAL GERAL: {summary['total_modules']} módulos ({summary['lines']['TOTAL_ALL']} linhas totais)")
    out_lines.append("")
    out_lines.append("--- LISTA COMPLETA POR STATUS ---")
    for status in (
        "REACHABLE_LOAD",
        "REACHABLE_DEFERRED",
        "REACHABLE_ANNOTATION_ONLY_RUNTIME",
        "REACHABLE_PEP562_LAZY",
        "REACHABLE_TYPE_CHECKING",
        "UNREACHABLE",
    ):
        out_lines.append(f"\n[{status}]")
        for mod_name, info in classified.items():
            if info["status"] == status:
                importers_str = ", ".join(
                    f"{i['importer_path']}:{i['line']}({i['kind']}{':ann' if i['ann_only'] else ''})"
                    for i in info["importers"]
                ) or "(nenhum)"
                out_lines.append(
                    f"  - {mod_name:35s} | {info['path']:40s} | {info['total_lines']:4d}L | importadores: {importers_str}"
                )

    out_lines.append("\n--- SCRIPT UTILITÁRIO (scripts/bootstrap_core_memory.py) ---")
    out_lines.append(f"  Imports diretos: {util_edges}")
    out_lines.append(f"  Alcançáveis: {summary['utility_script_bootstrap_core_memory']['reachable_modules']}")

    out_lines.append("\n--- SCANNER DE IMPORTS DINÂMICOS E STRINGS ---")
    for h in dynamic_hits:
        out_lines.append(f"  [{h['tag']}] {h['file']}:{h['line']} -> {h['code']}")

    txt_path = OUT_DIR / "bloco1_static_reach.txt"
    txt_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Counts: {summary['counts']}")
    print(f"Lines: {summary['lines']}")


if __name__ == "__main__":
    main()
